"""
Android QA Harness Tools
========================

MCP tools that let QA agents drive an Android app on an emulator or
attached device via adb: screenshots, input injection, and logcat reads.
The Android analog of the Electron MCP toolset.

Only registered when the project is an Android Gradle project, keeping
tool context clean for everything else.
"""

import base64
import logging
from pathlib import Path
from typing import Any

try:
    from claude_agent_sdk import tool

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

LOGCAT_TAIL_CHARS = 8_000


def create_android_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create Android device tools for QA agents.

    Args:
        spec_dir: Path to the spec directory (unused, kept for registry symmetry)
        project_dir: Path to the project root; gates registration

    Returns:
        List of tool functions (empty for non-Android projects)
    """
    if not SDK_AVAILABLE:
        return []

    try:
        from core.android_device import is_android_project
    except ImportError:
        return []

    if not is_android_project(project_dir):
        return []

    tools = []

    @tool(
        "android_screenshot",
        "Take a screenshot of the Android emulator or attached device via "
        "adb. Use it to visually verify UI state after launching the app or "
        "interacting with it. Optionally pass a device serial when several "
        "devices are connected.",
        {"serial": str},
    )
    async def android_screenshot(args: dict[str, Any]) -> dict[str, Any]:
        """Capture and return a device screenshot."""
        from core.android_device import take_screenshot

        try:
            image, mime_or_error = take_screenshot(
                serial=(args.get("serial") or "").strip() or None
            )
        except Exception as e:
            logging.exception("Error during android_screenshot")
            return _text_result(f"Error taking screenshot: {e}")

        if image is None:
            return _text_result(f"Screenshot failed: {mime_or_error}")

        return {
            "content": [
                {
                    "type": "image",
                    "data": base64.b64encode(image).decode("ascii"),
                    "mimeType": mime_or_error,
                }
            ]
        }

    tools.append(android_screenshot)

    @tool(
        "android_input",
        "Send input to the Android emulator or attached device via adb. "
        "Actions: 'tap' (x, y), 'swipe' (x, y, x2, y2, optional "
        "duration_ms), 'text' (text typed into the focused field), "
        "'keyevent' (key: KEYCODE_* name or numeric code, e.g. KEYCODE_BACK). "
        "Use android_screenshot before and after to verify the effect.",
        {
            "action": str,
            "x": int,
            "y": int,
            "x2": int,
            "y2": int,
            "duration_ms": int,
            "text": str,
            "key": str,
            "serial": str,
        },
    )
    async def android_input(args: dict[str, Any]) -> dict[str, Any]:
        """Inject a tap, swipe, text, or key event."""
        from core.android_device import (
            send_keyevent,
            send_swipe,
            send_tap,
            send_text,
        )

        action = (args.get("action") or "").strip().lower()
        serial = (args.get("serial") or "").strip() or None

        try:
            if action == "tap":
                result = send_tap(args.get("x") or 0, args.get("y") or 0, serial)
            elif action == "swipe":
                result = send_swipe(
                    args.get("x") or 0,
                    args.get("y") or 0,
                    args.get("x2") or 0,
                    args.get("y2") or 0,
                    args.get("duration_ms") or 300,
                    serial,
                )
            elif action == "text":
                result = send_text(args.get("text") or "", serial)
            elif action == "keyevent":
                result = send_keyevent(args.get("key") or "", serial)
            else:
                return _text_result("Unknown action: use tap, swipe, text, or keyevent")
        except Exception as e:
            logging.exception("Error during android_input")
            return _text_result(f"Error sending input: {e}")

        status = "OK" if result.ok else "FAILED"
        detail = result.output.strip()
        return _text_result(f"{status}: {action}" + (f"\n{detail}" if detail else ""))

    tools.append(android_input)

    @tool(
        "android_logcat",
        "Read recent Android log output (adb logcat) for debugging. "
        "Optionally filter lines by a substring (e.g. your app's tag or "
        "package name) and limit the number of recent lines.",
        {"lines": int, "filter_text": str, "serial": str},
    )
    async def android_logcat(args: dict[str, Any]) -> dict[str, Any]:
        """Fetch recent logcat lines."""
        from core.android_device import read_logcat

        try:
            result = read_logcat(
                lines=args.get("lines") or 200,
                filter_text=(args.get("filter_text") or "").strip() or None,
                serial=(args.get("serial") or "").strip() or None,
            )
        except Exception as e:
            logging.exception("Error during android_logcat")
            return _text_result(f"Error reading logcat: {e}")

        if not result.ok:
            return _text_result(f"logcat failed: {result.output}")

        output = result.output[-LOGCAT_TAIL_CHARS:]
        return _text_result(output if output.strip() else "(no matching log lines)")

    tools.append(android_logcat)

    return tools


def _text_result(text: str) -> dict[str, Any]:
    """Wrap text in the MCP tool result envelope."""
    return {"content": [{"type": "text", "text": text}]}


__all__ = ["create_android_tools"]
