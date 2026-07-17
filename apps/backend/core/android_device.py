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

# Markers of an Android module in a Gradle build file. Covers the classic
# plugin id ("com.android.application"/"library") and the version-catalog
# alias form (alias(libs.plugins.android...)) used by modern projects.
_ANDROID_BUILD_MARKERS = (
    "com.android",
    "libs.plugins.android",
    "android.application",
    "android.library",
)

# Directories skipped when scanning a multi-module project for build files
_SCAN_SKIP_DIRS = frozenset(
    {".git", "node_modules", ".gradle", "build", ".idea", ".venv", "venv"}
)

# Bound the multi-module scan so a huge tree cannot stall registration
_MAX_BUILD_FILES_SCANNED = 200


@dataclass
class AdbResult:
    """Outcome of an adb invocation."""

    ok: bool
    output: str


def is_android_project(project_dir: Path) -> bool:
    """
    Check if the project is an Android Gradle project.

    Scans Gradle build files across modules (not just app/), matching both
    the classic plugin id and version-catalog plugin aliases, so Android
    modules outside app/ and catalog-based projects are recognized.
    """
    root = Path(project_dir)
    scanned = 0
    for path in root.rglob("build.gradle*"):
        if any(part in _SCAN_SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        scanned += 1
        if scanned > _MAX_BUILD_FILES_SCANNED:
            break
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if any(marker in text for marker in _ANDROID_BUILD_MARKERS):
            return True
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


# Credential-ish patterns redacted from logcat before it reaches the agent.
# Device-wide logs can carry tokens/keys from other apps; QA never needs the
# secret value, only the surrounding message.
_REDACT_PATTERNS = (
    # Sensitive key followed by its value: redact from the separator to the
    # end of the line (a single value may be several tokens, e.g. "Bearer x")
    re.compile(
        r"(?im)\b(password|passwd|pwd|token|secret|api[_-]?key|auth|"
        r"authorization|bearer|session|cookie|credential)\b"
        r"(\s*[=:]\s*|\s+).+$"
    ),
    # Standalone JWT-like blobs not preceded by a labelled key
    re.compile(r"\b[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)


def _redact_logcat(text: str) -> str:
    """Redact obvious secrets from logcat output."""
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub(
            lambda m: m.group(0)[: _redact_prefix_len(m.group(0))] + "[REDACTED]",
            text,
        )
    return text


def _redact_prefix_len(match: str) -> int:
    """Keep the leading label of a match, redact the value after it."""
    for sep in ("=", ":"):
        idx = match.find(sep)
        if idx != -1:
            return idx + 1
    # No key=value separator (bearer/blob): redact the whole match
    return 0


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
        AdbResult with the (optionally filtered) log lines. Credential-like
        values are redacted before returning, since device-wide logs may
        contain data from other apps.
    """
    lines = max(1, min(int(lines), 2000))
    result = _run_adb_text(["logcat", "-d", "-t", str(lines)], serial)
    if not result.ok:
        return result

    output = result.output
    if filter_text:
        output = "\n".join(ln for ln in output.splitlines() if filter_text in ln)
    return AdbResult(True, _redact_logcat(output))


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
