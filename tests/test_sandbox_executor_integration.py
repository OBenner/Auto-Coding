"""LocalActionExecutor sandbox integration.

Phase 1.3 step 2: when constructed with a SandboxPolicy + a backend
that reports ``available=True``, the executor must wrap ``run_command``
argv through ``core.sandbox.wrap_command`` before
``asyncio.create_subprocess_exec`` runs. These tests intercept the
subprocess call so no real shell command executes.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.runtime.local_actions import LocalActionExecutor
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


def _make_fake_process():
    process = MagicMock()
    process.stdout = MagicMock()
    process.stderr = MagicMock()
    process.returncode = 0
    process.wait = AsyncMock(return_value=0)
    process.terminate = MagicMock()
    process.kill = MagicMock()
    return process


@pytest.mark.asyncio
async def test_executor_wraps_argv_with_seatbelt_when_policy_given(tmp_path):
    executor = LocalActionExecutor(
        project_dir=tmp_path,
        sandbox_policy=SandboxPolicy(project_dir=tmp_path),
        sandbox_backend=_ready_seatbelt(),
    )

    captured = {}

    async def fake_create(*args, **kwargs):
        captured["args"] = args
        return _make_fake_process()

    with patch(
        "agents.runtime.local_actions.asyncio.create_subprocess_exec",
        new=fake_create,
    ), patch(
        "agents.runtime.local_actions.capture_process_stream",
        new=AsyncMock(return_value=None),
    ), patch(
        "agents.runtime.local_actions.wait_for_process_streams",
        new=AsyncMock(return_value=False),
    ), patch(
        "agents.runtime.local_actions.ensure_process_finished",
        new=AsyncMock(return_value=None),
    ):
        await executor._run_subprocess_bounded(["git", "status"], timeout_seconds=10)

    argv = list(captured["args"])
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

    async def fake_create(*args, **kwargs):
        captured["args"] = args
        return _make_fake_process()

    with patch(
        "agents.runtime.local_actions.asyncio.create_subprocess_exec",
        new=fake_create,
    ), patch(
        "agents.runtime.local_actions.capture_process_stream",
        new=AsyncMock(return_value=None),
    ), patch(
        "agents.runtime.local_actions.wait_for_process_streams",
        new=AsyncMock(return_value=False),
    ), patch(
        "agents.runtime.local_actions.ensure_process_finished",
        new=AsyncMock(return_value=None),
    ):
        await executor._run_subprocess_bounded(["ls"], timeout_seconds=5)

    argv = list(captured["args"])
    assert argv[0] == "/usr/bin/bwrap"
    assert "--unshare-net" in argv  # allow_network=False
    assert argv[-1] == "ls"


@pytest.mark.asyncio
async def test_executor_passes_through_when_no_policy(tmp_path):
    """Default constructor (no sandbox) keeps the legacy unwrapped argv."""
    executor = LocalActionExecutor(project_dir=tmp_path)

    captured = {}

    async def fake_create(*args, **kwargs):
        captured["args"] = args
        return _make_fake_process()

    with patch(
        "agents.runtime.local_actions.asyncio.create_subprocess_exec",
        new=fake_create,
    ), patch(
        "agents.runtime.local_actions.capture_process_stream",
        new=AsyncMock(return_value=None),
    ), patch(
        "agents.runtime.local_actions.wait_for_process_streams",
        new=AsyncMock(return_value=False),
    ), patch(
        "agents.runtime.local_actions.ensure_process_finished",
        new=AsyncMock(return_value=None),
    ):
        await executor._run_subprocess_bounded(["echo", "hi"], timeout_seconds=5)

    assert list(captured["args"]) == ["echo", "hi"]


@pytest.mark.asyncio
async def test_executor_passes_through_when_backend_unavailable(tmp_path):
    """Policy without an available backend falls through to legacy argv."""
    executor = LocalActionExecutor(
        project_dir=tmp_path,
        sandbox_policy=SandboxPolicy(project_dir=tmp_path),
        sandbox_backend=_unavailable(),
    )

    captured = {}

    async def fake_create(*args, **kwargs):
        captured["args"] = args
        return _make_fake_process()

    with patch(
        "agents.runtime.local_actions.asyncio.create_subprocess_exec",
        new=fake_create,
    ), patch(
        "agents.runtime.local_actions.capture_process_stream",
        new=AsyncMock(return_value=None),
    ), patch(
        "agents.runtime.local_actions.wait_for_process_streams",
        new=AsyncMock(return_value=False),
    ), patch(
        "agents.runtime.local_actions.ensure_process_finished",
        new=AsyncMock(return_value=None),
    ):
        await executor._run_subprocess_bounded(["pwd"], timeout_seconds=5)

    assert list(captured["args"]) == ["pwd"]


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
    assert session._executor._sandbox_policy.project_dir == tmp_path


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
    from agents.runtime.adapters.direct_api_autonomous import (
        DirectApiAutonomousRuntimeSession,
    )

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
    assert session._executor._sandbox_policy.project_dir == tmp_path
