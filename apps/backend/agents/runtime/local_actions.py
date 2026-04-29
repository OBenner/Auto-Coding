"""Reusable local action executor for provider-neutral runtimes."""

from __future__ import annotations

import asyncio
import logging
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.platform import is_windows
from security import split_command_segments, validate_command

from .adapters.patch_proposal import (
    PatchProposalError,
    apply_git_patch,
    validate_patch_paths,
    validate_workspace_relative_path,
)

logger = logging.getLogger(__name__)

MAX_TOOL_OUTPUT_CHARS = 12000
MAX_READ_FILE_CHARS = 20000
MAX_COMMAND_TIMEOUT_SECONDS = 120
DEFAULT_COMMAND_TIMEOUT_SECONDS = 60


class LocalActionError(RuntimeError):
    """Raised when a local action request is malformed or unsafe."""


@dataclass
class ToolActionResult:
    """Structured result for one local action."""

    tool: str
    ok: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize result for traces and model observations."""
        return {
            "tool": self.tool,
            "ok": self.ok,
            "message": self.message,
            "data": self.data,
        }


class LocalActionExecutor:
    """Execute a small, provider-neutral set of local workspace actions."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    async def execute(self, action: dict[str, Any]) -> ToolActionResult:
        """Execute one local action and return a structured result."""
        tool = action_tool(action)
        try:
            if tool == "read_file":
                return self._read_file(action)
            if tool == "write_file":
                return self._write_file(action)
            if tool == "apply_patch":
                return self._apply_patch(action)
            if tool == "run_command":
                return await self._run_command(action)
            if tool == "finish":
                return ToolActionResult(
                    tool=tool,
                    ok=True,
                    message=str(action.get("summary") or "Local actions completed"),
                )
            return ToolActionResult(
                tool=tool or "unknown",
                ok=False,
                message=f"Unknown tool: {tool or '<missing>'}",
            )
        except (LocalActionError, PatchProposalError) as e:
            return ToolActionResult(tool=tool or "unknown", ok=False, message=str(e))
        except Exception as e:
            logger.error("Local action failed", exc_info=True)
            return ToolActionResult(
                tool=tool or "unknown",
                ok=False,
                message=f"Action failed unexpectedly: {e}",
            )

    def _read_file(self, action: dict[str, Any]) -> ToolActionResult:
        path = require_string(action, "path")
        target = resolve_workspace_path(self.project_dir, path)
        if not target.exists() or not target.is_file():
            return ToolActionResult(
                tool="read_file",
                ok=False,
                message=f"File not found: {path}",
            )

        max_chars = int(action.get("max_chars") or MAX_READ_FILE_CHARS)
        max_chars = max(1, min(max_chars, MAX_READ_FILE_CHARS))
        content = target.read_text(encoding="utf-8", errors="replace")
        truncated = len(content) > max_chars
        if truncated:
            content = content[:max_chars]

        return ToolActionResult(
            tool="read_file",
            ok=True,
            message=f"Read {path}",
            data={
                "path": path,
                "content": content,
                "truncated": truncated,
            },
        )

    def _write_file(self, action: dict[str, Any]) -> ToolActionResult:
        path = require_string(action, "path")
        content = require_string(action, "content")
        target = resolve_workspace_path(self.project_dir, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolActionResult(
            tool="write_file",
            ok=True,
            message=f"Wrote {path}",
            data={"path": path, "bytes": len(content.encode("utf-8"))},
        )

    def _apply_patch(self, action: dict[str, Any]) -> ToolActionResult:
        patch = require_string(action, "patch")
        validate_patch_paths(patch, self.project_dir)
        apply_git_patch(patch, self.project_dir)
        return ToolActionResult(
            tool="apply_patch",
            ok=True,
            message="Patch applied",
            data={"bytes": len(patch.encode("utf-8"))},
        )

    async def _run_command(self, action: dict[str, Any]) -> ToolActionResult:
        command = require_string(action, "command")
        timeout = int(action.get("timeout") or DEFAULT_COMMAND_TIMEOUT_SECONDS)
        timeout = max(1, min(timeout, MAX_COMMAND_TIMEOUT_SECONDS))

        if len(split_command_segments(command)) != 1:
            return ToolActionResult(
                tool="run_command",
                ok=False,
                message=(
                    "run_command supports one command at a time; split chained "
                    "commands into separate actions."
                ),
            )

        try:
            args = parse_command_args(command)
        except ValueError as e:
            return ToolActionResult(
                tool="run_command",
                ok=False,
                message=f"Invalid command syntax: {e}",
            )

        if any(token in {"|", ">", ">>", "<", "2>", "2>&1", "&>"} for token in args):
            return ToolActionResult(
                tool="run_command",
                ok=False,
                message="run_command does not support shell pipes or redirection.",
            )

        is_allowed, reason = validate_command(command, self.project_dir)
        if not is_allowed:
            return ToolActionResult(
                tool="run_command",
                ok=False,
                message=f"Command blocked by security validation: {reason}",
            )

        completed = await asyncio.to_thread(
            subprocess.run,
            args,
            cwd=self.project_dir,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        output = "\n".join(
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part and part.strip()
        )
        if len(output) > MAX_TOOL_OUTPUT_CHARS:
            output = output[:MAX_TOOL_OUTPUT_CHARS] + "\n...[truncated]"

        return ToolActionResult(
            tool="run_command",
            ok=completed.returncode == 0,
            message=f"Command exited with code {completed.returncode}",
            data={
                "command": command,
                "exit_code": completed.returncode,
                "output": output,
            },
        )


def safe_action_for_trace(action: dict[str, Any]) -> dict[str, Any]:
    """Avoid duplicating full file contents in trace request sections."""
    safe = dict(action)
    if "content" in safe:
        content = str(safe["content"])
        safe["content_excerpt"] = content[:500]
        safe["content_bytes"] = len(content.encode("utf-8"))
        del safe["content"]
    if "patch" in safe:
        patch = str(safe["patch"])
        safe["patch_excerpt"] = patch[:1000]
        safe["patch_bytes"] = len(patch.encode("utf-8"))
        del safe["patch"]
    return safe


def action_tool(action: dict[str, Any]) -> str:
    """Return a normalized tool/action name."""
    return str(action.get("tool") or action.get("name") or action.get("type") or "")


def require_string(action: dict[str, Any], field_name: str) -> str:
    """Read a required string action field."""
    value = action.get(field_name)
    if not isinstance(value, str) or not value:
        raise LocalActionError(f"Action field '{field_name}' must be a string")
    return value


def resolve_workspace_path(project_dir: Path, path: str) -> Path:
    """Validate and resolve a workspace-relative file path."""
    validate_workspace_relative_path(path)
    resolved_project = project_dir.resolve()
    target = (resolved_project / path).resolve()
    if not target.is_relative_to(resolved_project):
        raise LocalActionError(f"Path escapes workspace: {path}")
    return target


def parse_command_args(command: str) -> list[str]:
    """Parse a single command without invoking a shell."""
    if is_windows():
        raw_args = shlex.split(command, posix=False)
        return [
            arg[1:-1]
            if len(arg) >= 2 and arg[0] == arg[-1] and arg[0] in ('"', "'")
            else arg
            for arg in raw_args
        ]
    return shlex.split(command)


def normalize_string_list(value: Any) -> list[str]:
    """Normalize scalar/list values into display strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return [str(value)]
