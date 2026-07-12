"""Backend-neutral normalization between Direct-API local actions and the
plugin tool-hook vocabulary.

Plugin ``pre_tool``/``post_tool`` hooks were written against the Claude Agent
SDK tool vocabulary (``Bash``, ``Edit``, ``Write``, ``Read`` ...) and the SDK
tool-input shapes (``file_path``, ``old_string`` ...). The Direct-API
in-process runtime speaks its own local-action vocabulary (``run_command``,
``replace_text``, ``write_file`` ...) with different field names. Without a
translation layer, wiring the hooks with native names silently no-ops: e.g.
skill-pack-runtime only blocks when ``tool_name.casefold() in {"bash",
"shell"}``, so a native ``run_command`` would sail straight past the guard.

This module is the translation layer, and nothing more. It is pure and
side-effect-free: it does NOT load plugins, build agent context, or execute
actions. It only maps a native local-action dict to the canonical
``(tool_name, tool_input)`` a hook expects, exposes the post-hook result view,
and back-translates a hook block decision into a ``ToolActionResult``. Wiring
these into the execution loop is a separate slice.

Design decisions (see the plugin-runtime cross-backend discussion):

* Canonical vocabulary = SDK tool names where an SDK equivalent exists, and an
  honest dedicated name (``Delete``/``Move``/``ApplyPatch``) where it does not.
  We deliberately do NOT fabricate a synthetic ``Bash {command: "rm ..."}`` for
  destructive local actions: a guard that believes it can rewrite a shell
  command which will never run as a shell is worse than honest invisibility.
* Normalization is one-directional (native -> inspection view). Hooks may
  ``block`` a tool on Direct-API, but input-rewrite is not supported because we
  never reconstruct a native action from a canonical view.
* Read-only actions are mapped here but their hook invocation is gated behind
  ``include_read_only`` (default off) so plugins do not run on every file read
  unless a caller opts in (e.g. a secret-scanning / exfil guard).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NamedTuple

from .local_actions import ToolActionResult, action_tool


class CanonicalTool(NamedTuple):
    """A native local action expressed in the plugin hook vocabulary."""

    tool_name: str
    tool_input: dict[str, Any]


# Native local actions that neither mutate the workspace nor run commands.
# They are mapped to canonical tools below, but hook invocation on them is
# opt-in via ``include_read_only`` so the common path stays hook-free.
READ_ONLY_TOOLS: frozenset[str] = frozenset(
    {
        "stat_path",
        "list_files",
        "search_text",
        "read_file",
        "read_file_range",
        "read_many_files",
        "git_status",
        "git_diff",
    }
)

# Native local actions that are transaction/orchestration control-plane, not
# tool-use. They carry no meaningful tool semantics for a hook and are never
# translated (``to_canonical_tool`` returns ``None``).
NO_HOOK_TOOLS: frozenset[str] = frozenset(
    {
        "begin_batch",
        "commit_batch",
        "abort_batch",
        "rollback_transaction",
        "repair_mutation",
        "resolve_subagent_conflict",
        "run_subagents",
        "finish",
    }
)


def _include(target: dict[str, Any], key: str, value: Any) -> None:
    """Set ``key`` on ``target`` only when ``value`` is present."""
    if value is not None:
        target[key] = value


def _parse_patch_paths(patch: str) -> list[str]:
    """Extract touched file paths from a unified diff, best-effort.

    Reads ``+++``/``---`` headers, strips ``a/``/``b/`` prefixes, and skips
    ``/dev/null``. Returned sorted and de-duplicated so a file-scoped plugin can
    match an ``apply_patch`` without parsing the diff itself.
    """
    paths: set[str] = set()
    for line in patch.splitlines():
        if not (line.startswith("+++ ") or line.startswith("--- ")):
            continue
        candidate = line[4:].strip()
        # Drop a trailing tab-separated timestamp some diff tools append.
        candidate = candidate.split("\t", 1)[0].strip()
        if not candidate or candidate == "/dev/null":
            continue
        if candidate[:2] in ("a/", "b/"):
            candidate = candidate[2:]
        if candidate:
            paths.add(candidate)
    return sorted(paths)


def _bash(action: dict[str, Any]) -> CanonicalTool:
    tool_input: dict[str, Any] = {}
    _include(tool_input, "command", action.get("command"))
    _include(tool_input, "timeout", action.get("timeout"))
    return CanonicalTool("Bash", tool_input)


def _write(action: dict[str, Any]) -> CanonicalTool:
    tool_input: dict[str, Any] = {}
    _include(tool_input, "file_path", action.get("path"))
    _include(tool_input, "content", action.get("content"))
    return CanonicalTool("Write", tool_input)


def _edit(action: dict[str, Any]) -> CanonicalTool:
    tool_input: dict[str, Any] = {}
    _include(tool_input, "file_path", action.get("path"))
    _include(tool_input, "old_string", action.get("old"))
    _include(tool_input, "new_string", action.get("new"))
    return CanonicalTool("Edit", tool_input)


def _apply_patch(action: dict[str, Any]) -> CanonicalTool:
    patch = str(action.get("patch") or "")
    tool_input: dict[str, Any] = {
        "patch": patch,
        "file_paths": _parse_patch_paths(patch),
    }
    return CanonicalTool("ApplyPatch", tool_input)


def _delete(action: dict[str, Any]) -> CanonicalTool:
    tool_input: dict[str, Any] = {}
    _include(tool_input, "file_path", action.get("path"))
    return CanonicalTool("Delete", tool_input)


def _move(action: dict[str, Any]) -> CanonicalTool:
    tool_input: dict[str, Any] = {}
    _include(tool_input, "source", action.get("source"))
    _include(tool_input, "destination", action.get("destination"))
    return CanonicalTool("Move", tool_input)


def _read(action: dict[str, Any]) -> CanonicalTool:
    tool_input: dict[str, Any] = {}
    _include(tool_input, "file_path", action.get("path"))
    return CanonicalTool("Read", tool_input)


def _read_range(action: dict[str, Any]) -> CanonicalTool:
    tool_input: dict[str, Any] = {}
    _include(tool_input, "file_path", action.get("path"))
    _include(tool_input, "offset", action.get("start_line"))
    _include(tool_input, "limit", action.get("max_lines"))
    return CanonicalTool("Read", tool_input)


def _read_many(action: dict[str, Any]) -> CanonicalTool:
    paths = action.get("paths")
    tool_input: dict[str, Any] = {"file_paths": list(paths) if paths else []}
    return CanonicalTool("Read", tool_input)


def _grep(action: dict[str, Any]) -> CanonicalTool:
    tool_input: dict[str, Any] = {}
    _include(tool_input, "pattern", action.get("query"))
    _include(tool_input, "path", action.get("path"))
    return CanonicalTool("Grep", tool_input)


def _ls(action: dict[str, Any]) -> CanonicalTool:
    tool_input: dict[str, Any] = {}
    _include(tool_input, "path", action.get("path"))
    return CanonicalTool("LS", tool_input)


def _git_status(action: dict[str, Any]) -> CanonicalTool:
    command = "git status"
    path = action.get("path")
    if path:
        command += f" -- {path}"
    tool_input: dict[str, Any] = {"command": command}
    _include(tool_input, "include_untracked", action.get("include_untracked"))
    return CanonicalTool("Bash", tool_input)


def _git_diff(action: dict[str, Any]) -> CanonicalTool:
    command = "git diff"
    if action.get("cached"):
        command += " --cached"
    if action.get("stat"):
        command += " --stat"
    path = action.get("path")
    if path:
        command += f" -- {path}"
    tool_input: dict[str, Any] = {"command": command}
    _include(tool_input, "max_chars", action.get("max_chars"))
    return CanonicalTool("Bash", tool_input)


# native local-action name -> canonical builder.
_BUILDERS: dict[str, Callable[[dict[str, Any]], CanonicalTool]] = {
    "run_command": _bash,
    "write_file": _write,
    "replace_text": _edit,
    "apply_patch": _apply_patch,
    "delete_file": _delete,
    "move_file": _move,
    "read_file": _read,
    "read_file_range": _read_range,
    "read_many_files": _read_many,
    "search_text": _grep,
    "list_files": _ls,
    "stat_path": _ls,
    "git_status": _git_status,
    "git_diff": _git_diff,
}


def _mcp_passthrough(tool: str, action: dict[str, Any]) -> CanonicalTool:
    """MCP tools already carry canonical ``mcp__server__name`` names.

    Pass the name through unchanged and expose the action's non-meta fields as
    the tool input so a plugin sees the same shape it would on the SDK path.
    """
    tool_input = {
        key: value
        for key, value in action.items()
        if key not in ("tool", "name", "type")
    }
    return CanonicalTool(tool, tool_input)


def to_canonical_tool(
    action: dict[str, Any],
    *,
    include_read_only: bool = False,
) -> CanonicalTool | None:
    """Translate a native local action into the plugin hook vocabulary.

    Returns ``None`` when the action should not trigger a hook: control-plane
    actions, unknown tools, or read-only actions when ``include_read_only`` is
    false. MCP actions (``mcp__*``) pass through unchanged.
    """
    tool = action_tool(action)
    if not tool:
        return None
    if tool in NO_HOOK_TOOLS:
        return None
    if tool in READ_ONLY_TOOLS and not include_read_only:
        return None
    if tool.startswith("mcp__"):
        return _mcp_passthrough(tool, action)

    builder = _BUILDERS.get(tool)
    if builder is None:
        return None
    return builder(action)


def to_canonical_result(result: ToolActionResult) -> dict[str, Any]:
    """Return the ``tool_result`` view a ``post_tool`` hook receives.

    Thin today (the native result dict is already a reasonable shape); kept as a
    named seam so the post-hook result shape can evolve without touching the
    execution loop.
    """
    return result.to_dict()


def decision_to_result(decision: dict[str, Any], tool: str) -> ToolActionResult:
    """Convert a plugin hook ``block`` decision into a failed action result.

    ``decision`` is the already-normalized hook response from
    ``run_plugin_pre_tool_hooks`` — ``{"decision": "block", "reason": ...}`` —
    whose reason is human-readable and plugin-attributed.
    """
    reason = decision.get("reason") or "blocked by plugin runtime hook"
    return ToolActionResult(
        tool=tool or "unknown",
        ok=False,
        message=str(reason),
        data={"blocked_by": "plugin_runtime"},
    )
