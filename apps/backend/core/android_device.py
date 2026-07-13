"""
Android Device Access
=====================

Thin adb wrapper used by the QA agents' Android tools: screenshots,
input injection, and logcat reads. Mirrors the Electron MCP capabilities
for native Android apps running on an emulator or attached device.

All functions shell out to adb with fixed argv structures (never through
a shell) and degrade to clear error strings when adb or a device is
missing.
"""

import base64
import io
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ADB_TIMEOUT_SECONDS = 30

# Screenshots must stay under the Claude SDK's 1MB JSON message buffer
MAX_SCREENSHOT_BASE64_BYTES = 700_000
SCREENSHOT_MAX_WIDTH = 1280
SCREENSHOT_JPEG_QUALITY = 60

# adb `input text` is evaluated by the device shell, so shell
# metacharacters (; | & $ ` quotes parentheses) must be rejected
_SAFE_TEXT = re.compile(r"^[\w\s.,:@%+=/?!-]*$")
_KEYEVENT = re.compile(r"^(KEYCODE_[A-Z0-9_]+|\d{1,4})$")

_ANDROID_BUILD_FILES = (
    "build.gradle",
    "build.gradle.kts",
    "app/build.gradle",
    "app/build.gradle.kts",
)


@dataclass
class AdbResult:
    """Outcome of an adb invocation."""

    ok: bool
    output: str


def is_android_project(project_dir: Path) -> bool:
    """Check if the project is an Android Gradle project."""
    for build_file in _ANDROID_BUILD_FILES:
        path = Path(project_dir) / build_file
        if not path.exists():
            continue
        try:
            if "com.android" in path.read_text(encoding="utf-8"):
                return True
        except (OSError, UnicodeDecodeError):
            continue
    return False


def _adb(args: list[str], serial: str | None) -> list[str]:
    """Build an adb argv, optionally targeting a specific device."""
    argv = ["adb"]
    if serial:
        argv += ["-s", serial]
    return argv + args


def _run_adb_text(args: list[str], serial: str | None) -> AdbResult:
    """Run adb and capture text output."""
    try:
        proc = subprocess.run(
            _adb(args, serial),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=ADB_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return AdbResult(False, "adb not found - is the Android SDK installed?")
    except subprocess.TimeoutExpired:
        return AdbResult(False, "adb timed out")

    if proc.returncode != 0:
        return AdbResult(False, (proc.stderr or proc.stdout or "adb failed").strip())
    return AdbResult(True, proc.stdout)


def take_screenshot(serial: str | None = None) -> tuple[bytes | None, str]:
    """
    Capture a screenshot from the device.

    Returns:
        (image_bytes, mime_type) on success, (None, error_message) on failure
    """
    try:
        proc = subprocess.run(
            _adb(["exec-out", "screencap", "-p"], serial),
            capture_output=True,
            timeout=ADB_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return None, "adb not found - is the Android SDK installed?"
    except subprocess.TimeoutExpired:
        return None, "adb screencap timed out"

    if proc.returncode != 0 or not proc.stdout:
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        return None, stderr or "screencap produced no output (is a device running?)"

    return _fit_screenshot(proc.stdout)


def _fit_screenshot(png_bytes: bytes) -> tuple[bytes | None, str]:
    """Compress the screenshot to fit the SDK message limit."""
    compressed = _compress_with_pillow(png_bytes)
    if compressed is not None:
        return compressed, "image/jpeg"

    # Pillow unavailable: pass the PNG through if it is small enough
    if len(base64.b64encode(png_bytes)) <= MAX_SCREENSHOT_BASE64_BYTES:
        return png_bytes, "image/png"
    return None, (
        "Screenshot too large for the SDK message limit and Pillow is not "
        "installed - install Pillow to enable compression"
    )


def _compress_with_pillow(png_bytes: bytes) -> bytes | None:
    """Downscale and JPEG-encode the screenshot; None if Pillow is missing."""
    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        image = Image.open(io.BytesIO(png_bytes)).convert("RGB")
        if image.width > SCREENSHOT_MAX_WIDTH:
            ratio = SCREENSHOT_MAX_WIDTH / image.width
            image = image.resize(
                (SCREENSHOT_MAX_WIDTH, max(1, int(image.height * ratio)))
            )
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=SCREENSHOT_JPEG_QUALITY)
        return buffer.getvalue()
    except OSError:
        return None


def send_tap(x: int, y: int, serial: str | None = None) -> AdbResult:
    """Tap at screen coordinates."""
    return _run_adb_text(["shell", "input", "tap", str(int(x)), str(int(y))], serial)


def send_swipe(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    duration_ms: int = 300,
    serial: str | None = None,
) -> AdbResult:
    """Swipe between two coordinates."""
    return _run_adb_text(
        [
            "shell",
            "input",
            "swipe",
            str(int(x1)),
            str(int(y1)),
            str(int(x2)),
            str(int(y2)),
            str(int(duration_ms)),
        ],
        serial,
    )


def send_text(text: str, serial: str | None = None) -> AdbResult:
    """Type text into the focused field."""
    if not _SAFE_TEXT.match(text):
        return AdbResult(False, "Text contains characters adb input cannot send safely")
    # adb `input text` requires spaces encoded as %s
    return _run_adb_text(["shell", "input", "text", text.replace(" ", "%s")], serial)


def send_keyevent(key: str, serial: str | None = None) -> AdbResult:
    """Send a key event (KEYCODE_* name or numeric code)."""
    key = key.strip().upper()
    if not _KEYEVENT.match(key):
        return AdbResult(False, "Key must be a KEYCODE_* name or a numeric key code")
    return _run_adb_text(["shell", "input", "keyevent", key], serial)


def read_logcat(
    lines: int = 200,
    filter_text: str | None = None,
    serial: str | None = None,
) -> AdbResult:
    """
    Read recent logcat output without blocking.

    Args:
        lines: Number of most recent lines to fetch
        filter_text: Optional substring filter applied to the output
        serial: Optional device serial

    Returns:
        AdbResult with the (optionally filtered) log lines
    """
    lines = max(1, min(int(lines), 2000))
    result = _run_adb_text(["logcat", "-d", "-t", str(lines)], serial)
    if not result.ok or not filter_text:
        return result

    matching = [ln for ln in result.output.splitlines() if filter_text in ln]
    return AdbResult(True, "\n".join(matching))


__all__ = [
    "AdbResult",
    "is_android_project",
    "take_screenshot",
    "send_tap",
    "send_swipe",
    "send_text",
    "send_keyevent",
    "read_logcat",
]
