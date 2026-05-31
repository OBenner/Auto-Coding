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
        side_effect=lambda name: (
            "/usr/bin/sandbox-exec" if name == "sandbox-exec" else None
        ),
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
        side_effect=lambda name: (
            "/usr/bin/sandbox-exec" if name == "sandbox-exec" else None
        ),
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
        side_effect=lambda name: (
            "/usr/bin/sandbox-exec" if name == "sandbox-exec" else None
        ),
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


# ---------------------------------------------------------------------
# Phase 1.3 step 2 — wrap_command
# ---------------------------------------------------------------------

from pathlib import Path

from core.sandbox import (
    SandboxPolicy,
    build_bubblewrap_argv,
    build_seatbelt_profile,
    wrap_command,
)


def test_wrap_passthrough_when_backend_unavailable():
    info = SandboxBackendInfo(
        backend=SandboxBackend.UNAVAILABLE,
        platform="haiku",
        available=False,
        reason="No backend.",
    )
    policy = SandboxPolicy(project_dir=Path("/repo"))

    wrapped = wrap_command(["echo", "hi"], info=info, policy=policy)

    assert wrapped.wrapped is False
    assert wrapped.argv == ["echo", "hi"]
    assert wrapped.reason == "No backend."


def test_wrap_seatbelt_inserts_sandbox_exec_with_profile():
    info = SandboxBackendInfo(
        backend=SandboxBackend.SEATBELT,
        platform="darwin",
        available=True,
        reason="ok",
        executable="/usr/bin/sandbox-exec",
    )
    policy = SandboxPolicy(project_dir=Path("/repo"))

    wrapped = wrap_command(["git", "status"], info=info, policy=policy)

    assert wrapped.wrapped is True
    assert wrapped.argv[:3] == ["/usr/bin/sandbox-exec", "-p", wrapped.profile]
    assert wrapped.argv[-2:] == ["git", "status"]
    assert "(version 1)" in wrapped.profile
    assert '(allow file-write* (subpath "/repo"))' in wrapped.profile


def test_seatbelt_profile_includes_allowed_writes_and_network():
    # Path() literals are fixture values for assertion checks only; no
    # real filesystem I/O happens against these paths.
    extra_write = Path("/sandbox-fixture-cache")
    policy = SandboxPolicy(
        project_dir=Path("/repo"),
        allowed_writes=(extra_write,),
        allow_network=False,
    )
    profile = build_seatbelt_profile(policy)

    # Seatbelt only runs on macOS, so the builder always emits POSIX paths
    # even when the tests execute on Windows runners (where ``str(Path("/x"))``
    # would otherwise yield ``\\x``).
    assert '(subpath "/repo")' in profile
    assert f'(subpath "{extra_write.as_posix()}")' in profile
    assert "(deny network*)" in profile
    assert "(allow network*)" not in profile


def test_seatbelt_profile_escapes_path_quotes():
    policy = SandboxPolicy(project_dir=Path('/repo"weird'))
    profile = build_seatbelt_profile(policy)

    assert '\\"weird' in profile


def test_wrap_bubblewrap_returns_bwrap_argv_with_project_bind():
    info = SandboxBackendInfo(
        backend=SandboxBackend.BUBBLEWRAP,
        platform="linux",
        available=True,
        reason="ok",
        executable="/usr/bin/bwrap",
    )
    policy = SandboxPolicy(project_dir=Path("/repo"))

    wrapped = wrap_command(["ls"], info=info, policy=policy)

    assert wrapped.wrapped is True
    assert wrapped.argv[0] == "/usr/bin/bwrap"
    assert "--bind" in wrapped.argv
    bind_index = wrapped.argv.index("--bind")
    assert wrapped.argv[bind_index : bind_index + 3] == [
        "--bind",
        "/repo",
        "/repo",
    ]
    assert wrapped.argv[-2:] == ["--", "ls"][-1:] or wrapped.argv[-1] == "ls"


def test_build_bubblewrap_argv_includes_allowed_writes_and_network_share():
    # Path() literals are fixture values for assertion checks only; no
    # real filesystem I/O happens against these paths.
    write_a = Path("/sandbox-fixture-cache")
    write_b = Path("/sandbox-fixture-log")
    policy = SandboxPolicy(
        project_dir=Path("/repo"),
        allowed_writes=(write_a, write_b),
        allow_network=True,
    )
    argv = build_bubblewrap_argv(
        ["python", "build.py"],
        executable="/usr/bin/bwrap",
        policy=policy,
    )

    # Every allowed-write entry binds writable. bwrap only runs on Linux, so
    # the builder always emits POSIX paths even when the tests execute on
    # Windows runners (where ``str(Path("/x"))`` would otherwise yield ``\\x``).
    for path in ("/repo", write_a.as_posix(), write_b.as_posix()):
        idx = None
        for i, token in enumerate(argv):
            if token == "--bind" and argv[i + 1] == path:
                idx = i
                break
        assert idx is not None, f"missing --bind for {path} in {argv}"

    assert "--share-net" in argv
    assert "--unshare-net" not in argv
    assert "--unshare-pid" in argv
    assert "--unshare-user" in argv


def test_build_bubblewrap_argv_unshares_net_when_disabled():
    policy = SandboxPolicy(
        project_dir=Path("/repo"),
        allow_network=False,
    )
    argv = build_bubblewrap_argv(["true"], executable="/usr/bin/bwrap", policy=policy)

    assert "--unshare-net" in argv
    assert "--share-net" not in argv


def test_wrap_appcontainer_is_passthrough_with_explicit_reason():
    """AppContainer wrapping is still a TODO — pass through honestly."""
    info = SandboxBackendInfo(
        backend=SandboxBackend.APPCONTAINER,
        platform="win32",
        available=True,
        reason="ok",
    )
    policy = SandboxPolicy(project_dir=Path("C:/repo"))

    wrapped = wrap_command(["cmd.exe", "/c", "dir"], info=info, policy=policy)

    assert wrapped.wrapped is False
    assert wrapped.argv == ["cmd.exe", "/c", "dir"]
    assert "AppContainer" in wrapped.reason


def test_wrap_seatbelt_without_executable_falls_through():
    info = SandboxBackendInfo(
        backend=SandboxBackend.SEATBELT,
        platform="darwin",
        available=True,
        reason="ok",
        executable=None,
    )
    policy = SandboxPolicy(project_dir=Path("/repo"))

    wrapped = wrap_command(["true"], info=info, policy=policy)

    assert wrapped.wrapped is False
    assert "missing" in wrapped.reason
