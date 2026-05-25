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
