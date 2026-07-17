"""
Android QA Harness Tools
========================

MCP tools that let QA agents drive an Android app on an emulator or
attached device via adb: screenshots, input injection, and logcat reads.
The Android analog of the Electron MCP toolset.

Only registered when the project is an Android Gradle project, keeping
tool context clean for everything else.
"""

import asyncio
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

# Full JSON Schemas: the SDK marks every key of a {name: type} dict schema as
# required, but these tools have optional and action-specific fields, so we
# supply explicit schemas that require only what each call genuinely needs.
_SCREENSHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "serial": {
            "type": "string",
            "description": "Device serial when multiple devices are connected",
        }
    },
    "required": [],
}

_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["tap", "swipe", "text", "keyevent"],
            "description": "Input action to perform",
        },
        "x": {"type": "integer", "description": "X coordinate (tap/swipe)"},
        "y": {"type": "integer", "description": "Y coordinate (tap/swipe)"},
        "x2": {"type": "integer", "description": "Swipe end X"},
        "y2": {"type": "integer", "description": "Swipe end Y"},
        "duration_ms": {"type": "integer", "description": "Swipe duration in ms"},
        "text": {"type": "string", "description": "Text to type (action=text)"},
        "key": {
            "type": "string",
            "description": "KEYCODE_* name or numeric code (action=keyevent)",
        },
        "serial": {"type": "string", "description": "Optional device serial"},
    },
    "required": ["action"],
}

_LOGCAT_SCHEMA = {
    "type": "object",
    "properties": {
        "lines": {"type": "integer", "description": "Recent lines to fetch"},
        "filter_text": {
            "type": "string",
            "description": "Substring filter (e.g. app tag or package name)",
        },
        "serial": {"type": "string", "description": "Optional device serial"},
    },
    "required": [],
}


def _opt_int(value: Any, default: int) -> int:
    """Coerce an optional int arg, preserving an explicit 0."""
    return default if value is None else int(value)


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
        _SCREENSHOT_SCHEMA,
    )
    async def android_screenshot(args: dict[str, Any]) -> dict[str, Any]:
        """Capture and return a device screenshot."""
        from core.android_device import take_screenshot

        try:
            image, mime_or_error = await asyncio.to_thread(
                take_screenshot,
                serial=(args.get("serial") or "").strip() or None,
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
        _INPUT_SCHEMA,
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
                result = await asyncio.to_thread(
                    send_tap,
                    _opt_int(args.get("x"), 0),
                    _opt_int(args.get("y"), 0),
                    serial,
                )
            elif action == "swipe":
                result = await asyncio.to_thread(
                    send_swipe,
                    _opt_int(args.get("x"), 0),
                    _opt_int(args.get("y"), 0),
                    _opt_int(args.get("x2"), 0),
                    _opt_int(args.get("y2"), 0),
                    _opt_int(args.get("duration_ms"), 300),
                    serial,
                )
            elif action == "text":
                result = await asyncio.to_thread(
                    send_text, args.get("text") or "", serial
                )
            elif action == "keyevent":
                result = await asyncio.to_thread(
                    send_keyevent, args.get("key") or "", serial
                )
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
        "package name) and limit the number of recent lines. Credential-like "
        "values are redacted from the output.",
        _LOGCAT_SCHEMA,
    )
    async def android_logcat(args: dict[str, Any]) -> dict[str, Any]:
        """Fetch recent logcat lines."""
        from core.android_device import read_logcat

        try:
            result = await asyncio.to_thread(
                read_logcat,
                lines=_opt_int(args.get("lines"), 200),
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
