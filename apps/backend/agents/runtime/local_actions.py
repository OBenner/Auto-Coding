"""Reusable local action executor for provider-neutral runtimes."""

from __future__ import annotations

import asyncio
import json
import logging
import shlex
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.platform import is_windows, run_process
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
TRACE_STRING_PREVIEW_CHARS = 1000
TRACE_REDACTED_FIELDS = {"content", "output", "patch", "raw_response"}


class LocalActionError(RuntimeError):
    """Raised when a local action request is malformed or unsafe."""


@dataclass(frozen=True)
class LocalActionToolSpec:
    """Provider-neutral schema for one local action tool."""

    name: str
    description: str
    parameters: dict[str, dict[str, Any]]
    required: tuple[str, ...] = ()
    example: dict[str, Any] = field(default_factory=dict)

    def parameter_schema(self) -> dict[str, Any]:
        """Return the JSON schema for provider-native function arguments."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": deepcopy(self.parameters),
            "additionalProperties": False,
        }
        if self.required:
            schema["required"] = list(self.required)
        return schema

    def action_schema(self) -> dict[str, Any]:
        """Return the JSON schema for the generic_edit action-loop shape."""
        schema = self.parameter_schema()
        schema["properties"] = {
            "tool": {
                "type": "string",
                "enum": [self.name],
                "description": "Local action tool name.",
            },
            **schema["properties"],
        }
        schema["required"] = ["tool", *self.required]
        return schema

    def provider_tool_schema(self) -> dict[str, Any]:
        """Return a provider-neutral function/tool schema for future adapters."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameter_schema(),
        }

    def prompt_line(self) -> str:
        """Render the compact action example used in JSON-loop prompts."""
        return f"- {self.name}: {json.dumps(self.example, ensure_ascii=False)}"


LOCAL_ACTION_TOOL_SPECS: tuple[LocalActionToolSpec, ...] = (
    LocalActionToolSpec(
        name="read_file",
        description="Read a UTF-8 text file from the workspace.",
        parameters={
            "path": {
                "type": "string",
                "description": "Workspace-relative file path.",
            },
            "max_chars": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_READ_FILE_CHARS,
                "description": "Maximum number of characters to return.",
            },
        },
        required=("path",),
        example={
            "tool": "read_file",
            "path": "relative/path.py",
            "max_chars": 12000,
        },
    ),
    LocalActionToolSpec(
        name="write_file",
        description="Write complete UTF-8 text content to a workspace file.",
        parameters={
            "path": {
                "type": "string",
                "description": "Workspace-relative file path.",
            },
            "content": {
                "type": "string",
                "description": "Complete replacement file content.",
            },
        },
        required=("path", "content"),
        example={
            "tool": "write_file",
            "path": "relative/path.py",
            "content": "complete file content",
        },
    ),
    LocalActionToolSpec(
        name="apply_patch",
        description="Apply a unified diff inside the workspace.",
        parameters={
            "patch": {
                "type": "string",
                "description": "Unified diff to validate and apply.",
            },
        },
        required=("patch",),
        example={"tool": "apply_patch", "patch": "unified diff"},
    ),
    LocalActionToolSpec(
        name="run_command",
        description="Run one security-validated command without a shell.",
        parameters={
            "command": {
                "type": "string",
                "description": "Single command, without pipes or redirection.",
            },
            "timeout": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_COMMAND_TIMEOUT_SECONDS,
                "description": "Command timeout in seconds.",
            },
        },
        required=("command",),
        example={
            "tool": "run_command",
            "command": "pytest tests/test_file.py -q",
            "timeout": DEFAULT_COMMAND_TIMEOUT_SECONDS,
        },
    ),
    LocalActionToolSpec(
        name="finish",
        description="Finish the local action loop with a summary.",
        parameters={
            "summary": {
                "type": "string",
                "description": "Short summary of the completed work.",
            },
            "tests": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Verification commands that were run or suggested.",
            },
            "risks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Known residual risks or limitations.",
            },
        },
        example={
            "tool": "finish",
            "summary": "what changed",
            "tests": ["commands run"],
            "risks": [],
        },
    ),
)
LOCAL_ACTION_TOOL_NAMES = frozenset(spec.name for spec in LOCAL_ACTION_TOOL_SPECS)


def local_action_tool_specs() -> tuple[LocalActionToolSpec, ...]:
    """Return the local action tool manifest."""
    return LOCAL_ACTION_TOOL_SPECS


def local_action_tool_schemas() -> list[dict[str, Any]]:
    """Return provider-neutral schemas for native function-calling adapters."""
    return [spec.provider_tool_schema() for spec in LOCAL_ACTION_TOOL_SPECS]


def local_action_response_schema() -> dict[str, Any]:
    """Return the JSON response schema for the generic_edit action loop."""
    return {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "Short planning note.",
            },
            "actions": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "oneOf": [spec.action_schema() for spec in LOCAL_ACTION_TOOL_SPECS]
                },
            },
        },
        "required": ["actions"],
        "additionalProperties": False,
    }


def render_local_action_prompt() -> str:
    """Render local action examples for the generic_edit prompt."""
    return "\n".join(spec.prompt_line() for spec in LOCAL_ACTION_TOOL_SPECS)


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
        with target.open("r", encoding="utf-8", errors="replace") as handle:
            content = handle.read(max_chars + 1)
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
        validate_patch_paths(patch)
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
            run_process,
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
        safe["content_bytes"] = len(content.encode("utf-8"))
        safe["content_redacted"] = True
        del safe["content"]
    if "patch" in safe:
        patch = str(safe["patch"])
        safe["patch_bytes"] = len(patch.encode("utf-8"))
        safe["patch_redacted"] = True
        del safe["patch"]
    return safe


def safe_result_for_trace(result: ToolActionResult) -> dict[str, Any]:
    """Serialize a local action result without persisting raw file/output data."""
    return {
        "tool": result.tool,
        "ok": result.ok,
        "message": result.message,
        "data": redact_trace_data(result.data),
    }


def redact_trace_data(value: Any) -> Any:
    """Redact sensitive or large values before writing runtime trace artifacts."""
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, str) and key in TRACE_REDACTED_FIELDS:
                safe[f"{key}_redacted"] = True
                safe[f"{key}_bytes"] = len(item.encode("utf-8"))
                safe[f"{key}_line_count"] = len(item.splitlines())
            else:
                safe[key] = redact_trace_data(item)
        return safe
    if isinstance(value, list):
        return [redact_trace_data(item) for item in value]
    if isinstance(value, str) and len(value) > TRACE_STRING_PREVIEW_CHARS:
        return {
            "excerpt": value[:TRACE_STRING_PREVIEW_CHARS],
            "bytes": len(value.encode("utf-8")),
            "truncated": True,
        }
    return value


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
