"""Integration tests for plugin pre_tool hooks on the Direct-API in-process
runtime (Slice 2 wiring in GenericEditRuntimeSession).

These assert the wiring — native action -> canonical normalization -> plugin
pre_tool dispatch -> block translation -> read-only gating -> funnel through
``_execute_action`` — using a fake hook-capable plugin. The real skill-pack
guard behavior is covered separately (test_plugin_tool_bridge, test_skill_pack_runtime).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "backend"))

from agents.runtime.adapters.generic_edit import GenericEditRuntimeSession
from plugins.base import PluginCapability
from plugins.runtime import build_agent_context
from plugins.sdk.agent import ToolHookDecision


class _FakePlugin:
    """Minimal hook-capable plugin: enabled + generic_edit capability."""

    def __init__(self, predicate=None, *, post_predicate=None, name="fake-blocker"):
        self.name = name
        self.is_enabled = True
        self.metadata = SimpleNamespace(capabilities=[PluginCapability.GENERIC_EDIT])
        self._predicate = predicate or (lambda _n, _i: False)
        self._post_predicate = post_predicate

    def pre_tool(self, context, tool_name, tool_input):
        if self._predicate(tool_name, tool_input):
            return ToolHookDecision.block(f"{self.name} blocked {tool_name}")
        return None

    def post_tool(self, context, tool_name, tool_input, tool_result):
        if self._post_predicate and self._post_predicate(
            tool_name, tool_input, tool_result
        ):
            return ToolHookDecision.block(f"{self.name} post-blocked {tool_name}")
        return None


def _session(tmp_path: Path) -> GenericEditRuntimeSession:
    return GenericEditRuntimeSession(
        provider_name="openai",
        agent_session=SimpleNamespace(),
        project_dir=tmp_path,
        agent_type="coder",
    )


def _wire(
    session: GenericEditRuntimeSession,
    tmp_path: Path,
    predicate=None,
    *,
    post_predicate=None,
) -> None:
    """Attach a hook-capable plugin + a real AgentContext, bypassing run()."""
    session._tool_hook_plugins = [_FakePlugin(predicate, post_predicate=post_predicate)]
    session._plugin_hook_context = build_agent_context(
        tmp_path, tmp_path, "coder", metadata=None
    )


def _block_all(_tool_name, _tool_input) -> bool:
    return True


def _block_skill_scripts(tool_name, tool_input) -> bool:
    command = str(tool_input.get("command") or "")
    return tool_name == "Bash" and "skills/" in command


async def test_pre_tool_blocks_mutating_action(tmp_path):
    session = _session(tmp_path)
    _wire(session, tmp_path, _block_all)

    result = await session._run_plugin_pre_tool_hook(
        {"tool": "write_file", "path": "a.py", "content": "x"}, "write_file"
    )

    assert result is not None
    assert result.ok is False
    assert result.data == {"blocked_by": "plugin_runtime"}
    assert "blocked Write" in result.message


async def test_pre_tool_blocks_skill_script_run_command(tmp_path):
    session = _session(tmp_path)
    _wire(session, tmp_path, _block_skill_scripts)

    blocked = await session._run_plugin_pre_tool_hook(
        {"tool": "run_command", "command": "python skills/x/scripts/run.py"},
        "run_command",
    )
    allowed = await session._run_plugin_pre_tool_hook(
        {"tool": "run_command", "command": "pytest -q"}, "run_command"
    )

    assert blocked is not None and blocked.ok is False
    assert allowed is None


async def test_pre_tool_gates_read_only_actions(tmp_path):
    session = _session(tmp_path)
    _wire(session, tmp_path, _block_all)  # would block everything if reached

    # Read-only actions are gated off: the hook never runs, so no block.
    assert (
        await session._run_plugin_pre_tool_hook(
            {"tool": "read_file", "path": "a.py"}, "read_file"
        )
        is None
    )
    # A mutating action with the same plugin still blocks (control).
    assert (
        await session._run_plugin_pre_tool_hook(
            {"tool": "write_file", "path": "a.py", "content": "x"}, "write_file"
        )
        is not None
    )


async def test_no_plugins_is_a_noop(tmp_path):
    session = _session(tmp_path)
    session._tool_hook_plugins = []
    session._plugin_hook_context = None

    assert (
        await session._run_plugin_pre_tool_hook(
            {"tool": "write_file", "path": "a.py", "content": "x"}, "write_file"
        )
        is None
    )


async def test_execute_action_funnels_block_before_executing(tmp_path):
    session = _session(tmp_path)
    _wire(session, tmp_path, _block_all)
    target = tmp_path / "should_not_exist.py"

    result = await session._execute_action(
        {"tool": "write_file", "path": "should_not_exist.py", "content": "x = 1"},
        loop="main",
        iteration=0,
        action_index=0,
        spec_dir=tmp_path,
        verbose=False,
        phase=None,
        subtask_id=None,
    )

    assert result.ok is False
    assert result.data.get("blocked_by") == "plugin_runtime"
    # Blocked before the executor ran -> the file was never written.
    assert not target.exists()


async def test_post_tool_annotates_without_failing(tmp_path):
    from agents.runtime.local_actions import ToolActionResult

    session = _session(tmp_path)
    _wire(session, tmp_path, post_predicate=lambda _n, _i, _r: True)
    result = ToolActionResult(tool="write_file", ok=True, message="wrote", data={})

    await session._run_plugin_post_tool_hook(
        {"tool": "write_file", "path": "a.py", "content": "x"}, "write_file", result
    )

    # Observational: success is preserved, the post-block is only annotated.
    assert result.ok is True
    assert "post-blocked Write" in result.data["plugin_post_tool_block"]


async def test_execute_action_runs_post_tool_on_success(tmp_path):
    session = _session(tmp_path)
    _wire(session, tmp_path, post_predicate=lambda _n, _i, _r: True)
    target = tmp_path / "post_written.py"

    result = await session._execute_action(
        {"tool": "write_file", "path": "post_written.py", "content": "x = 1"},
        loop="main",
        iteration=0,
        action_index=0,
        spec_dir=tmp_path,
        verbose=False,
        phase=None,
        subtask_id=None,
    )

    # The write succeeded AND post_tool observed it (mutation not rolled back).
    assert result.ok is True
    assert target.exists()
    assert "plugin_post_tool_block" in result.data


async def test_resume_prepares_plugin_hook_context(tmp_path):
    # resume() drives _execute_action like run(), so it must build the hook
    # context too; otherwise tool hooks are a no-op on resumed runs.
    session = _session(tmp_path)
    seen = {}

    class _Sentinel(Exception):
        pass

    def _spy(spec_dir, subtask_id):
        seen["args"] = (spec_dir, subtask_id)
        raise _Sentinel

    session._prepare_plugin_hook_context = _spy

    with pytest.raises(_Sentinel):
        await session.resume(
            checkpoint_path=tmp_path / "ckpt.json",
            spec_dir=tmp_path,
            verbose=False,
            phase=None,
            subtask_id="s1",
        )

    assert seen["args"] == (tmp_path, "s1")
