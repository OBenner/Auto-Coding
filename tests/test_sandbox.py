"""Tests for the cross-platform sandbox skeleton (Phase 1.3).

These tests do not exec real Seatbelt/bubblewrap/AppContainer
processes; they pin the detection contract that the autonomy layer
consults before granting the ``sandbox`` capability.
"""

from __future__ import annotations

from unittest.mock import patch

from core.sandbox import (
    SANDBOX_ENV,
    SandboxBackend,
    SandboxBackendInfo,
    describe_sandbox_backend,
    sandbox_available,
)


def test_describe_returns_seatbelt_when_sandbox_exec_present():
    with patch(
        "core.sandbox.shutil.which",
        side_effect=lambda name: "/usr/bin/sandbox-exec" if name == "sandbox-exec" else None,
    ):
        info = describe_sandbox_backend(env={}, platform="darwin")

    assert info.backend is SandboxBackend.SEATBELT
    assert info.available is True
    assert info.executable == "/usr/bin/sandbox-exec"


def test_describe_returns_unavailable_seatbelt_when_sandbox_exec_missing():
    with patch("core.sandbox.shutil.which", return_value=None):
        info = describe_sandbox_backend(env={}, platform="darwin")

    assert info.backend is SandboxBackend.SEATBELT
    assert info.available is False
    assert "sandbox-exec" in info.reason


def test_describe_returns_bubblewrap_on_linux_when_bwrap_present():
    with patch(
        "core.sandbox.shutil.which",
        side_effect=lambda name: "/usr/bin/bwrap" if name == "bwrap" else None,
    ):
        info = describe_sandbox_backend(env={}, platform="linux")

    assert info.backend is SandboxBackend.BUBBLEWRAP
    assert info.available is True
    assert info.executable == "/usr/bin/bwrap"


def test_describe_linux_accepts_bubblewrap_alias():
    def _which(name: str) -> str | None:
        if name == "bwrap":
            return None
        if name == "bubblewrap":
            return "/opt/local/bin/bubblewrap"
        return None

    with patch("core.sandbox.shutil.which", side_effect=_which):
        info = describe_sandbox_backend(env={}, platform="linux")

    assert info.backend is SandboxBackend.BUBBLEWRAP
    assert info.available is True
    assert info.executable == "/opt/local/bin/bubblewrap"


def test_describe_linux_reports_missing_when_bwrap_absent():
    with patch("core.sandbox.shutil.which", return_value=None):
        info = describe_sandbox_backend(env={}, platform="linux")

    assert info.backend is SandboxBackend.BUBBLEWRAP
    assert info.available is False
    assert "bwrap" in info.reason


def test_describe_windows_appcontainer_requires_sdk_env():
    info = describe_sandbox_backend(env={}, platform="win32")

    assert info.backend is SandboxBackend.APPCONTAINER
    assert info.available is False
    assert "WindowsSdkDir" in info.reason


def test_describe_windows_appcontainer_unavailable_without_force_even_with_sdk():
    """SDK env var alone is not proof that AppContainer can spawn processes."""
    info = describe_sandbox_backend(
        env={"WindowsSdkDir": "C:/Program Files/Windows Kits/10"},
        platform="win32",
    )

    assert info.backend is SandboxBackend.APPCONTAINER
    assert info.available is False
    assert "process-spawn wiring is not yet implemented" in info.reason


def test_describe_windows_appcontainer_force_opt_in():
    """Operators can opt into the experimental path with the force env var."""
    info = describe_sandbox_backend(
        env={
            "WindowsSdkDir": "C:/Program Files/Windows Kits/10",
            "AUTO_CODE_SANDBOX_WIN_APPCONTAINER_FORCE": "true",
        },
        platform="win32",
    )

    assert info.backend is SandboxBackend.APPCONTAINER
    assert info.available is True
    assert "force-enabled" in info.reason


def test_describe_unknown_platform_returns_unavailable():
    info = describe_sandbox_backend(env={}, platform="haiku")

    assert info.backend is SandboxBackend.UNAVAILABLE
    assert info.available is False
    assert "haiku" in info.reason


def test_describe_respects_explicit_disable_env_var():
    with patch(
        "core.sandbox.shutil.which",
        side_effect=lambda name: "/usr/bin/sandbox-exec" if name == "sandbox-exec" else None,
    ):
        info = describe_sandbox_backend(
            env={SANDBOX_ENV: "false"},
            platform="darwin",
        )

    assert info.backend is SandboxBackend.SEATBELT
    assert info.available is False
    assert "explicitly disabled" in info.reason


def test_describe_cannot_force_enable_when_backend_missing():
    """Operator setting ``AUTO_CODE_SANDBOX=true`` does not fake availability."""
    with patch("core.sandbox.shutil.which", return_value=None):
        info = describe_sandbox_backend(
            env={SANDBOX_ENV: "true"},
            platform="darwin",
        )

    assert info.available is False


def test_sandbox_available_returns_bool():
    with patch(
        "core.sandbox.shutil.which",
        side_effect=lambda name: "/usr/bin/sandbox-exec" if name == "sandbox-exec" else None,
    ):
        assert sandbox_available(env={}, platform="darwin") is True

    with patch("core.sandbox.shutil.which", return_value=None):
        assert sandbox_available(env={}, platform="darwin") is False


def test_to_dict_is_json_safe():
    info = SandboxBackendInfo(
        backend=SandboxBackend.SEATBELT,
        platform="darwin",
        available=True,
        reason="ok",
        executable="/usr/bin/sandbox-exec",
    )
    payload = info.to_dict()
    assert payload["backend"] == "seatbelt"
    assert payload["platform"] == "darwin"
    assert payload["available"] is True
    assert payload["executable"] == "/usr/bin/sandbox-exec"
