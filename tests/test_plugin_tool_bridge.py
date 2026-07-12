"""Unit tests for the Direct-API <-> plugin hook tool-name normalization layer.

Slice 1: the module under test is pure (no plugin loading, no execution). These
tests lock the full native->canonical mapping table, the read-only gating flag,
the control-plane exclusions, and the block-decision translation.

The regression anchor at the bottom is the reason this layer exists: it proves
that a native ``run_command`` invoking a skill script is only caught by
skill-pack-runtime's guard AFTER normalization to ``Bash`` — and that feeding
the guard the un-normalized native name silently fails to block.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure apps/backend and the skill-pack plugin package root are importable.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "backend"))
sys.path.insert(
    0,
    str(REPO_ROOT / "apps" / "backend" / "plugins" / "system" / "skill-pack-runtime"),
)

from agents.runtime.local_actions import ToolActionResult
from agents.runtime.plugin_tool_bridge import (
    NO_HOOK_TOOLS,
    READ_ONLY_TOOLS,
    CanonicalTool,
    decision_to_result,
    to_canonical_result,
    to_canonical_tool,
)
from skill_pack_runtime.runtime import SkillPackRuntime

# --- mutating / command actions: always hooked -----------------------------

MUTATING_CASES = [
    (
        {"tool": "run_command", "command": "pytest -q", "timeout": 30},
        CanonicalTool("Bash", {"command": "pytest -q", "timeout": 30}),
    ),
    (
        {"tool": "run_command", "command": "pytest -q"},
        CanonicalTool("Bash", {"command": "pytest -q"}),
    ),
    (
        {"tool": "write_file", "path": "src/a.py", "content": "x = 1"},
        CanonicalTool("Write", {"file_path": "src/a.py", "content": "x = 1"}),
    ),
    (
        {
            "tool": "replace_text",
            "path": "src/a.py",
            "old": "x",
            "new": "y",
            "count": 3,
        },
        CanonicalTool(
            "Edit",
            {"file_path": "src/a.py", "old_string": "x", "new_string": "y"},
        ),
    ),
    (
        {"tool": "delete_file", "path": "src/gone.py"},
        CanonicalTool("Delete", {"file_path": "src/gone.py"}),
    ),
    (
        {
            "tool": "move_file",
            "source": "a.py",
            "destination": "b.py",
            "overwrite": True,
        },
        CanonicalTool("Move", {"source": "a.py", "destination": "b.py"}),
    ),
]


@pytest.mark.parametrize("action, expected", MUTATING_CASES)
def test_mutating_actions_map_to_canonical(action, expected):
    assert to_canonical_tool(action) == expected


def test_replace_text_drops_count_from_view_only():
    # `count` is intentionally absent from the inspection view; the executor
    # still honors it at execution time (normalization is inspection-only).
    canonical = to_canonical_tool(
        {"tool": "replace_text", "path": "a.py", "old": "x", "new": "y", "count": 5}
    )
    assert "count" not in canonical.tool_input


def test_apply_patch_parses_touched_paths():
    patch = (
        "--- a/src/one.py\n"
        "+++ b/src/one.py\n"
        "@@ -1 +1 @@\n"
        "-old\n+new\n"
        "--- /dev/null\n"
        "+++ b/src/two.py\n"
    )
    canonical = to_canonical_tool({"tool": "apply_patch", "patch": patch})
    assert canonical.tool_name == "ApplyPatch"
    assert canonical.tool_input["patch"] == patch
    # /dev/null skipped, a//b/ prefixes stripped, sorted + de-duplicated.
    assert canonical.tool_input["file_paths"] == ["src/one.py", "src/two.py"]


# --- read-only actions: gated behind include_read_only ---------------------

READ_ONLY_CASES = [
    (
        {"tool": "read_file", "path": "a.py"},
        CanonicalTool("Read", {"file_path": "a.py"}),
    ),
    (
        {"tool": "read_file_range", "path": "a.py", "start_line": 10, "max_lines": 5},
        CanonicalTool("Read", {"file_path": "a.py", "offset": 10, "limit": 5}),
    ),
    (
        {"tool": "read_many_files", "paths": ["a.py", "b.py"]},
        CanonicalTool("Read", {"file_paths": ["a.py", "b.py"]}),
    ),
    (
        {"tool": "search_text", "query": "TODO", "path": "src"},
        CanonicalTool("Grep", {"pattern": "TODO", "path": "src"}),
    ),
    ({"tool": "list_files", "path": "src"}, CanonicalTool("LS", {"path": "src"})),
    ({"tool": "stat_path", "path": "src"}, CanonicalTool("LS", {"path": "src"})),
    ({"tool": "git_status"}, CanonicalTool("Bash", {"command": "git status"})),
    ({"tool": "git_diff"}, CanonicalTool("Bash", {"command": "git diff"})),
]


@pytest.mark.parametrize("action, expected", READ_ONLY_CASES)
def test_read_only_actions_gated_off_by_default(action, expected):
    assert to_canonical_tool(action) is None
    assert to_canonical_tool(action, include_read_only=True) == expected


def test_read_only_set_matches_cases():
    assert {a["tool"] for a, _ in READ_ONLY_CASES} == set(READ_ONLY_TOOLS)


def test_git_actions_reflect_scope_in_command():
    # Scope (path/cached/stat) must survive into the canonical command so a hook
    # consumer can tell a scoped/staged request from a bare one.
    status = to_canonical_tool(
        {"tool": "git_status", "path": "src", "include_untracked": True},
        include_read_only=True,
    )
    assert status.tool_input["command"] == "git status -- src"
    assert status.tool_input["include_untracked"] is True

    diff = to_canonical_tool(
        {"tool": "git_diff", "path": "src", "cached": True, "stat": True},
        include_read_only=True,
    )
    assert diff.tool_input["command"] == "git diff --cached --stat -- src"


# --- control-plane / unknown: never hooked ---------------------------------


@pytest.mark.parametrize("tool", sorted(NO_HOOK_TOOLS))
def test_control_plane_actions_are_not_hooked(tool):
    assert to_canonical_tool({"tool": tool}) is None


def test_unknown_and_empty_actions_are_not_hooked():
    assert to_canonical_tool({"tool": "totally_unknown"}) is None
    assert to_canonical_tool({}) is None


def test_mcp_actions_pass_through_unchanged():
    action = {"tool": "mcp__ctx7__search", "query": "abc", "limit": 5}
    canonical = to_canonical_tool(action)
    assert canonical == CanonicalTool("mcp__ctx7__search", {"query": "abc", "limit": 5})


# --- result / decision translation -----------------------------------------


def test_to_canonical_result_reflects_action_result():
    result = ToolActionResult(
        tool="write_file", ok=True, message="wrote", data={"n": 1}
    )
    assert to_canonical_result(result) == result.to_dict()


def test_decision_to_result_produces_failed_result():
    decision = {"decision": "block", "reason": "Plugin X blocked tool use: nope"}
    result = decision_to_result(decision, "run_command")
    assert result.ok is False
    assert result.tool == "run_command"
    assert result.message == "Plugin X blocked tool use: nope"
    assert result.data == {"blocked_by": "plugin_runtime"}


def test_decision_to_result_defaults_reason_and_tool():
    result = decision_to_result({"decision": "block"}, "")
    assert result.ok is False
    assert result.tool == "unknown"
    assert result.message == "blocked by plugin runtime hook"


# --- regression anchor: normalization is what makes the guard fire ----------

_SKILL_SCRIPT_COMMAND = "python skills/my-skill/scripts/run.py"


def test_skill_pack_guard_blocks_only_after_normalization():
    """The whole point of Slice B: a native run_command that executes a skill
    script must reach skill-pack-runtime's guard as ``Bash``.
    """
    guard = SkillPackRuntime(REPO_ROOT, granted_permissions=[])
    action = {"tool": "run_command", "command": _SKILL_SCRIPT_COMMAND}

    # Un-normalized native name: guard does NOT match {"bash","shell"} -> bypass.
    assert (
        guard.should_block_script_command(
            "run_command", {"command": _SKILL_SCRIPT_COMMAND}
        )
        is False
    )

    # Normalized: canonical name is Bash, guard blocks.
    canonical = to_canonical_tool(action)
    assert canonical.tool_name == "Bash"
    assert guard.should_block_script_command(*canonical) is True


def test_skill_pack_guard_allows_benign_command_after_normalization():
    guard = SkillPackRuntime(REPO_ROOT, granted_permissions=[])
    canonical = to_canonical_tool({"tool": "run_command", "command": "pytest -q"})
    assert guard.should_block_script_command(*canonical) is False
