"""LocalActionExecutor sandbox integration.

Phase 1.3 step 2: when constructed with a SandboxPolicy + a backend
that reports ``available=True``, the executor must wrap ``run_command``
argv through ``core.sandbox.wrap_command`` before the command runs. These
tests intercept the blocking subprocess runner so no real shell command
executes and assert the argv it receives is the wrapped one.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from agents.runtime.local_actions import CommandExecution, LocalActionExecutor
from core.sandbox import SandboxBackend, SandboxBackendInfo, SandboxPolicy


def _ready_seatbelt() -> SandboxBackendInfo:
    return SandboxBackendInfo(
        backend=SandboxBackend.SEATBELT,
        platform="darwin",
        available=True,
        reason="ok",
        executable="/usr/bin/sandbox-exec",
    )


def _ready_bwrap() -> SandboxBackendInfo:
    return SandboxBackendInfo(
        backend=SandboxBackend.BUBBLEWRAP,
        platform="linux",
        available=True,
        reason="ok",
        executable="/usr/bin/bwrap",
    )


def _unavailable() -> SandboxBackendInfo:
    return SandboxBackendInfo(
        backend=SandboxBackend.UNAVAILABLE,
        platform="haiku",
        available=False,
        reason="No backend.",
    )


def _fake_blocking_runner(captured: dict):
    """Stand in for ``_run_subprocess_blocking``, recording the argv it gets.

    The executor wraps argv with the sandbox before handing it to the
    blocking runner, so capturing the runner's ``args`` proves the wrap.
    """

    def _runner(args, *, cwd, timeout_seconds):
        captured["args"] = list(args)
        captured["cwd"] = cwd
        return CommandExecution(
            returncode=0, output="", truncated=False, timed_out=False
        )

    return _runner


@pytest.mark.asyncio
async def test_executor_wraps_argv_with_seatbelt_when_policy_given(tmp_path):
    executor = LocalActionExecutor(
        project_dir=tmp_path,
        sandbox_policy=SandboxPolicy(project_dir=tmp_path),
        sandbox_backend=_ready_seatbelt(),
    )

    captured = {}
    with patch(
        "agents.runtime.local_actions._run_subprocess_blocking",
        new=_fake_blocking_runner(captured),
    ):
        await executor._run_subprocess_bounded(["git", "status"], timeout_seconds=10)

    argv = captured["args"]
    assert argv[0] == "/usr/bin/sandbox-exec"
    assert argv[1] == "-p"
    # Profile body is the third token; tail is original argv.
    assert argv[-2:] == ["git", "status"]


@pytest.mark.asyncio
async def test_executor_wraps_argv_with_bubblewrap_when_policy_given(tmp_path):
    executor = LocalActionExecutor(
        project_dir=tmp_path,
        sandbox_policy=SandboxPolicy(project_dir=tmp_path, allow_network=False),
        sandbox_backend=_ready_bwrap(),
    )

    captured = {}
    with patch(
        "agents.runtime.local_actions._run_subprocess_blocking",
        new=_fake_blocking_runner(captured),
    ):
        await executor._run_subprocess_bounded(["ls"], timeout_seconds=5)

    argv = captured["args"]
    assert argv[0] == "/usr/bin/bwrap"
    assert "--unshare-net" in argv  # allow_network=False
    assert argv[-1] == "ls"


@pytest.mark.asyncio
async def test_executor_passes_through_when_no_policy(tmp_path):
    """Default constructor (no sandbox) keeps the legacy unwrapped argv."""
    executor = LocalActionExecutor(project_dir=tmp_path)

    captured = {}
    with patch(
        "agents.runtime.local_actions._run_subprocess_blocking",
        new=_fake_blocking_runner(captured),
    ):
        await executor._run_subprocess_bounded(["echo", "hi"], timeout_seconds=5)

    assert captured["args"] == ["echo", "hi"]


@pytest.mark.asyncio
async def test_executor_passes_through_when_backend_unavailable(tmp_path):
    """Policy without an available backend falls through to legacy argv."""
    executor = LocalActionExecutor(
        project_dir=tmp_path,
        sandbox_policy=SandboxPolicy(project_dir=tmp_path),
        sandbox_backend=_unavailable(),
    )

    captured = {}
    with patch(
        "agents.runtime.local_actions._run_subprocess_blocking",
        new=_fake_blocking_runner(captured),
    ):
        await executor._run_subprocess_bounded(["pwd"], timeout_seconds=5)

    assert captured["args"] == ["pwd"]


# ---------------------------------------------------------------------
# Runtime-session wiring.
#
# The executor tests above prove the *mechanism*: given a policy + an
# available backend, run_command argv is wrapped. These tests prove the
# *wiring*: GenericEditRuntimeSession (and the promoted
# DirectApiAutonomousRuntimeSession that subclasses it) actually hand
# that policy + backend to their LocalActionExecutor. Without this, the
# executor-level wrapping is unreachable in production -- the runtime
# would always build a sandbox-less executor.
# ---------------------------------------------------------------------

from agents.runtime.adapters.direct_api_autonomous import (
    DirectApiAutonomousRuntimeSession,
)
from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession


def _patch_backend_everywhere(info: SandboxBackendInfo):
    """Patch ``describe_sandbox_backend`` at both call sites.

    ``resolve_autonomy_settings`` lazily imports it from ``core.sandbox``
    to compute ``sandbox_available``; ``_resolve_sandbox_wiring`` uses the
    copy bound into the ``generic_edit`` module namespace. Both must
    return the same host-independent backend so the test is deterministic
    on every CI OS (Linux runners have no Seatbelt; bwrap may be absent).
    """
    return (
        patch("core.sandbox.describe_sandbox_backend", return_value=info),
        patch(
            "agents.runtime.adapters.generic_edit.describe_sandbox_backend",
            return_value=info,
        ),
    )


def test_generic_edit_injected_sandbox_reaches_executor(tmp_path):
    """An explicitly injected policy + backend wires straight through."""
    backend = _ready_seatbelt()
    policy = SandboxPolicy(project_dir=tmp_path)

    session = GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=MagicMock(),
        project_dir=tmp_path,
        sandbox_policy=policy,
        sandbox_backend=backend,
    )

    assert session._executor._sandbox_policy is policy
    assert session._executor._sandbox_backend is backend


def test_generic_edit_rejects_partial_sandbox_override(tmp_path):
    """A half-supplied (policy XOR backend) pair must fail loudly.

    The executor only wraps when both are present, so accepting one
    would silently run unconfined while looking configured.
    """
    with pytest.raises(ValueError, match="must be provided together"):
        GenericEditRuntimeSession(
            provider_name="openai",
            agent_session=MagicMock(),
            project_dir=tmp_path,
            sandbox_policy=SandboxPolicy(project_dir=tmp_path),
        )

    with pytest.raises(ValueError, match="must be provided together"):
        GenericEditRuntimeSession(
            provider_name="openai",
            agent_session=MagicMock(),
            project_dir=tmp_path,
            sandbox_backend=_ready_seatbelt(),
        )


def test_generic_edit_auto_resolves_sandbox_on_safe(tmp_path, monkeypatch):
    """``AUTO_CODE_AUTONOMY=safe`` + a working backend wires the executor."""
    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "safe")
    monkeypatch.delenv("AUTO_CODE_SANDBOX", raising=False)
    info = _ready_seatbelt()

    p_core, p_mod = _patch_backend_everywhere(info)
    with p_core, p_mod:
        session = GenericEditRuntimeSession(
            provider_name="openai",
            agent_session=MagicMock(),
            project_dir=tmp_path,
        )

    assert session._executor._sandbox_backend is info
    assert session._executor._sandbox_policy is not None
    assert session._executor._sandbox_policy.project_dir == tmp_path.resolve()


def test_generic_edit_no_sandbox_on_claude_level(tmp_path, monkeypatch):
    """The default (claude) level never requests a sandbox.

    A ready backend is patched in to prove the gate is the operator's
    *request*, not mere host availability: claude leaves the executor
    unwrapped even where Seatbelt exists.
    """
    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "claude")
    monkeypatch.delenv("AUTO_CODE_SANDBOX", raising=False)
    info = _ready_seatbelt()

    p_core, p_mod = _patch_backend_everywhere(info)
    with p_core, p_mod:
        session = GenericEditRuntimeSession(
            provider_name="openai",
            agent_session=MagicMock(),
            project_dir=tmp_path,
        )

    assert session._executor._sandbox_policy is None
    assert session._executor._sandbox_backend is None


def test_generic_edit_no_sandbox_when_backend_unavailable(tmp_path, monkeypatch):
    """``safe`` but no host backend => honest unwrapped passthrough."""
    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "safe")
    monkeypatch.delenv("AUTO_CODE_SANDBOX", raising=False)
    info = _unavailable()

    p_core, p_mod = _patch_backend_everywhere(info)
    with p_core, p_mod:
        session = GenericEditRuntimeSession(
            provider_name="openai",
            agent_session=MagicMock(),
            project_dir=tmp_path,
        )

    assert session._executor._sandbox_policy is None
    assert session._executor._sandbox_backend is None


def test_direct_api_autonomous_inherits_sandbox_wiring(tmp_path, monkeypatch):
    """The promoted direct-API runtime confines its shell path too."""
    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "bold")
    monkeypatch.delenv("AUTO_CODE_SANDBOX", raising=False)
    info = _ready_bwrap()

    p_core, p_mod = _patch_backend_everywhere(info)
    with p_core, p_mod:
        session = DirectApiAutonomousRuntimeSession(
            provider_name="openai",
            agent_session=MagicMock(),
            project_dir=tmp_path,
        )

    assert session._executor._sandbox_backend is info
    assert session._executor._sandbox_policy is not None
    assert session._executor._sandbox_policy.project_dir == tmp_path.resolve()


# ---------------------------------------------------------------------
# Scratch-write grants + diagnostics.
#
# Confining writes to project_dir alone would break ordinary build
# tooling that writes to the system temp dir. The grant differs by
# backend: Seatbelt needs an explicit temp allow, bubblewrap gives a
# fresh namespaced tmpfs and must NOT re-bind the host temp.
# ---------------------------------------------------------------------

import tempfile


def test_seatbelt_policy_grants_system_temp_scratch(tmp_path, monkeypatch):
    """Seatbelt has no mount namespacing => the OS temp subtree is granted."""
    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "safe")
    monkeypatch.delenv("AUTO_CODE_SANDBOX", raising=False)
    info = _ready_seatbelt()

    p_core, p_mod = _patch_backend_everywhere(info)
    with p_core, p_mod:
        session = GenericEditRuntimeSession(
            provider_name="openai",
            agent_session=MagicMock(),
            project_dir=tmp_path,
        )

    policy = session._executor._sandbox_policy
    assert policy is not None
    assert Path(tempfile.gettempdir()).resolve() in policy.allowed_writes


def test_bubblewrap_policy_omits_host_temp_to_preserve_tmpfs(tmp_path, monkeypatch):
    """bubblewrap mounts its own tmpfs at /tmp => no host temp grant."""
    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "safe")
    monkeypatch.delenv("AUTO_CODE_SANDBOX", raising=False)
    info = _ready_bwrap()

    p_core, p_mod = _patch_backend_everywhere(info)
    with p_core, p_mod:
        session = GenericEditRuntimeSession(
            provider_name="openai",
            agent_session=MagicMock(),
            project_dir=tmp_path,
        )

    policy = session._executor._sandbox_policy
    assert policy is not None
    assert policy.allowed_writes == ()


def test_sandbox_requested_but_unavailable_warns_unconfined(
    tmp_path, monkeypatch, caplog
):
    """A requested-but-unsatisfiable sandbox surfaces an honest warning."""
    import logging

    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "safe")
    monkeypatch.delenv("AUTO_CODE_SANDBOX", raising=False)
    info = _unavailable()

    p_core, p_mod = _patch_backend_everywhere(info)
    with caplog.at_level(logging.WARNING), p_core, p_mod:
        session = GenericEditRuntimeSession(
            provider_name="openai",
            agent_session=MagicMock(),
            project_dir=tmp_path,
        )

    assert session._executor._sandbox_policy is None
    assert session._executor._sandbox_backend is None
    assert "UNCONFINED" in caplog.text


def test_claude_level_does_not_warn(tmp_path, monkeypatch, caplog):
    """The default level never requests a sandbox => no unconfined warning."""
    import logging

    monkeypatch.setenv("AUTO_CODE_AUTONOMY", "claude")
    monkeypatch.delenv("AUTO_CODE_SANDBOX", raising=False)
    info = _unavailable()

    p_core, p_mod = _patch_backend_everywhere(info)
    with caplog.at_level(logging.WARNING), p_core, p_mod:
        GenericEditRuntimeSession(
            provider_name="openai",
            agent_session=MagicMock(),
            project_dir=tmp_path,
        )

    assert "UNCONFINED" not in caplog.text


# ---------------------------------------------------------------------
# Execution path: the blocking runner must work independently of the
# asyncio event-loop policy. uvloop is installed as an import side effect
# (core/client.py), which left a default asyncio loop consulting a uvloop
# policy with no child watcher -- create_subprocess_exec then raised
# NotImplementedError and crashed every shell command. Running real
# commands through the blocking runner proves it no longer depends on that
# machinery (also removed entirely in Python 3.14).
# ---------------------------------------------------------------------

import sys

from agents.runtime.local_actions import _run_subprocess_blocking


def test_run_subprocess_blocking_works_without_event_loop(tmp_path):
    """The runner uses blocking subprocess only -- no running loop required."""
    result = _run_subprocess_blocking(
        [sys.executable, "-c", "print('hello-subprocess')"],
        cwd=str(tmp_path),
        timeout_seconds=30,
    )
    assert result.returncode == 0
    assert "hello-subprocess" in result.output
    assert result.timed_out is False
    assert result.truncated is False


def test_run_subprocess_blocking_times_out(tmp_path):
    """A command exceeding the wall-clock budget is killed and flagged."""
    result = _run_subprocess_blocking(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=str(tmp_path),
        timeout_seconds=1,
    )
    assert result.timed_out is True
    assert result.returncode != 0


def test_run_subprocess_blocking_truncates_large_output(tmp_path):
    """Output beyond the shared budget is truncated, not unbounded."""
    result = _run_subprocess_blocking(
        [sys.executable, "-c", "print('x' * 100000)"],
        cwd=str(tmp_path),
        timeout_seconds=30,
    )
    assert result.truncated is True
    assert len(result.output) <= 12100  # MAX_TOOL_OUTPUT_CHARS (12000) + slack


@pytest.mark.asyncio
async def test_run_subprocess_bounded_executes_for_real(tmp_path):
    """End-to-end: the async wrapper runs the command via a worker thread."""
    executor = LocalActionExecutor(project_dir=tmp_path)
    result = await executor._run_subprocess_bounded(
        [sys.executable, "-c", "print('real-exec-ok')"],
        timeout_seconds=30,
    )
    assert result.returncode == 0
    assert "real-exec-ok" in result.output
