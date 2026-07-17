#!/usr/bin/env python3
"""
Tests for the Android device access module and QA tool registration.

Tests cover:
- Android project detection
- adb argv construction and error handling (mocked subprocess)
- Input sanitization (text, keyevents)
- Logcat filtering
- Screenshot size handling
- Android-only tool registration gating
"""

import base64

# Add auto-claude to path for imports
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from core.android_device import (
    MAX_SCREENSHOT_BASE64_BYTES,
    _redact_logcat,
    is_android_project,
    read_logcat,
    send_keyevent,
    send_tap,
    send_text,
    take_screenshot,
)


class TestAndroidProjectDetection:
    """Tests for is_android_project."""

    def test_detects_root_gradle(self, tmp_path):
        (tmp_path / "build.gradle").write_text(
            "apply plugin: 'com.android.application'"
        )
        assert is_android_project(tmp_path) is True

    def test_detects_app_module_kts(self, tmp_path):
        app = tmp_path / "app"
        app.mkdir()
        (app / "build.gradle.kts").write_text('plugins { id("com.android.library") }')
        assert is_android_project(tmp_path) is True

    def test_detects_module_outside_app(self, tmp_path):
        """Android module named something other than app/ is detected."""
        feature = tmp_path / "feature-login"
        feature.mkdir()
        (feature / "build.gradle").write_text("apply plugin: 'com.android.library'")
        assert is_android_project(tmp_path) is True

    def test_detects_version_catalog_alias(self, tmp_path):
        """Version-catalog plugin alias is recognized."""
        (tmp_path / "build.gradle.kts").write_text(
            "plugins { alias(libs.plugins.android.application) }"
        )
        assert is_android_project(tmp_path) is True

    def test_skips_vendor_build_dirs(self, tmp_path):
        """Android markers inside build/ artifacts do not count."""
        buried = tmp_path / "build" / "generated"
        buried.mkdir(parents=True)
        (buried / "build.gradle").write_text("apply plugin: 'com.android.application'")
        assert is_android_project(tmp_path) is False

    def test_plain_jvm_project_is_not_android(self, tmp_path):
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")
        assert is_android_project(tmp_path) is False

    def test_non_gradle_project_is_not_android(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        assert is_android_project(tmp_path) is False


class TestAdbCommands:
    """Tests for adb command construction and error handling."""

    @patch("core.android_device.subprocess.run")
    def test_tap_builds_correct_argv(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = send_tap(100, 250)

        assert result.ok is True
        argv = mock_run.call_args[0][0]
        assert argv == ["adb", "shell", "input", "tap", "100", "250"]

    @patch("core.android_device.subprocess.run")
    def test_serial_is_passed(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        send_tap(1, 2, serial="emulator-5554")

        argv = mock_run.call_args[0][0]
        assert argv[:3] == ["adb", "-s", "emulator-5554"]

    @patch("core.android_device.subprocess.run")
    def test_missing_adb_is_reported(self, mock_run):
        mock_run.side_effect = FileNotFoundError()

        result = send_tap(1, 2)

        assert result.ok is False
        assert "adb not found" in result.output

    @patch("core.android_device.subprocess.run")
    def test_adb_failure_returns_stderr(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="error: no devices found"
        )

        result = send_tap(1, 2)

        assert result.ok is False
        assert "no devices" in result.output


class TestInputSanitization:
    """Tests for input text and keyevent validation."""

    @patch("core.android_device.subprocess.run")
    def test_text_spaces_encoded(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = send_text("hello world")

        assert result.ok is True
        argv = mock_run.call_args[0][0]
        assert argv[-1] == "hello%sworld"

    def test_unsafe_text_rejected(self):
        result = send_text("hello; rm -rf /")

        assert result.ok is False
        assert "cannot send safely" in result.output

    def test_quotes_rejected(self):
        result = send_text('say "hi" $(reboot)')

        assert result.ok is False

    @patch("core.android_device.subprocess.run")
    def test_keyevent_name_accepted(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = send_keyevent("KEYCODE_BACK")

        assert result.ok is True
        assert mock_run.call_args[0][0][-1] == "KEYCODE_BACK"

    def test_arbitrary_keyevent_rejected(self):
        result = send_keyevent("$(reboot)")

        assert result.ok is False


class TestLogcat:
    """Tests for logcat reads."""

    @patch("core.android_device.subprocess.run")
    def test_filter_applied(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="I/MyApp: started\nW/Other: noise\nE/MyApp: crash\n",
            stderr="",
        )

        result = read_logcat(filter_text="MyApp")

        assert result.ok is True
        assert "started" in result.output
        assert "crash" in result.output
        assert "noise" not in result.output

    @patch("core.android_device.subprocess.run")
    def test_line_count_clamped(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        read_logcat(lines=999999)

        argv = mock_run.call_args[0][0]
        assert argv[argv.index("-t") + 1] == "2000"

    @patch("core.android_device.subprocess.run")
    def test_secrets_redacted(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "I/Auth: token=abc123secretvalue\n"
                "I/Net: Authorization: Bearer eyJhbGciOiJIUzI1NiJ9\n"
                "I/App: user logged in ok\n"
            ),
            stderr="",
        )

        result = read_logcat()

        assert "abc123secretvalue" not in result.output
        assert "eyJhbGciOiJIUzI1NiJ9" not in result.output
        assert "[REDACTED]" in result.output
        # Non-secret context is preserved
        assert "user logged in ok" in result.output


class TestRedaction:
    """Direct tests for the logcat redactor."""

    def test_keeps_label_redacts_value(self):
        out = _redact_logcat("password=hunter2")
        assert out.startswith("password=")
        assert "hunter2" not in out

    def test_plain_lines_untouched(self):
        line = "I/MyApp: rendered 42 items in 16ms"
        assert _redact_logcat(line) == line


class TestScreenshot:
    """Tests for screenshot capture and size handling."""

    @patch("core.android_device.subprocess.run")
    def test_no_device_reports_error(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1, stdout=b"", stderr=b"error: no devices/emulators found"
        )

        image, error = take_screenshot()

        assert image is None
        assert "no devices" in error

    @patch("core.android_device._compress_with_pillow", return_value=None)
    @patch("core.android_device.subprocess.run")
    def test_small_png_passthrough_without_pillow(self, mock_run, _mock_pil):
        png = b"\x89PNG small image"
        mock_run.return_value = MagicMock(returncode=0, stdout=png, stderr=b"")

        image, mime = take_screenshot()

        assert image == png
        assert mime == "image/png"

    @patch("core.android_device._compress_with_pillow", return_value=None)
    @patch("core.android_device.subprocess.run")
    def test_oversized_png_without_pillow_errors(self, mock_run, _mock_pil):
        huge = b"x" * (MAX_SCREENSHOT_BASE64_BYTES + 1)
        mock_run.return_value = MagicMock(returncode=0, stdout=huge, stderr=b"")

        image, error = take_screenshot()

        assert image is None
        assert "Pillow" in error

    @patch("core.android_device._compress_with_pillow", return_value=b"jpegdata")
    @patch("core.android_device.subprocess.run")
    def test_compressed_screenshot_is_jpeg(self, mock_run, _mock_pil):
        mock_run.return_value = MagicMock(
            returncode=0, stdout=b"\x89PNG raw", stderr=b""
        )

        image, mime = take_screenshot()

        assert image == b"jpegdata"
        assert mime == "image/jpeg"
        assert base64.b64encode(image)  # encodable for the MCP envelope


class TestToolRegistration:
    """Tests for Android-only tool registration."""

    def test_android_project_gets_tools(self, tmp_path):
        from agents.tools_pkg.tools.android_harness import create_android_tools

        (tmp_path / "build.gradle").write_text(
            "apply plugin: 'com.android.application'"
        )

        tools = create_android_tools(tmp_path, tmp_path)

        assert len(tools) == 3

    def test_non_android_project_gets_no_tools(self, tmp_path):
        from agents.tools_pkg.tools.android_harness import create_android_tools

        (tmp_path / "package.json").write_text("{}")

        tools = create_android_tools(tmp_path, tmp_path)

        assert tools == []

    def test_schemas_require_only_action_specific_fields(self):
        """Optional args must not be forced required by the SDK dict schema.

        The SDK marks every key of a {name: type} dict schema as required, so
        these tools ship full JSON Schemas. Asserting on the module constants
        (not the tool objects, which the test harness mocks) verifies the
        contract directly.
        """
        from agents.tools_pkg.tools import android_harness as ah

        assert ah._SCREENSHOT_SCHEMA["required"] == []
        assert ah._INPUT_SCHEMA["required"] == ["action"]
        assert ah._LOGCAT_SCHEMA["required"] == []
        # action-specific fields exist but stay optional
        assert "text" in ah._INPUT_SCHEMA["properties"]
        assert "text" not in ah._INPUT_SCHEMA["required"]

    def test_qa_agents_have_android_tools(self):
        from agents.tools_pkg.models import (
            TOOL_ANDROID_INPUT,
            TOOL_ANDROID_LOGCAT,
            TOOL_ANDROID_SCREENSHOT,
            get_agent_config,
        )

        for agent_type in ("qa_reviewer", "qa_fixer"):
            config = get_agent_config(agent_type)
            for tool_name in (
                TOOL_ANDROID_SCREENSHOT,
                TOOL_ANDROID_INPUT,
                TOOL_ANDROID_LOGCAT,
            ):
                assert tool_name in config["auto_claude_tools"]
