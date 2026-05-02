"""Reusable local action executor for provider-neutral runtimes."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
from copy import deepcopy
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
MAX_READ_MANY_FILES = 10
MAX_LIST_FILE_ENTRIES = 200
MAX_SEARCH_MATCHES = 100
MAX_SEARCH_QUERY_CHARS = 512
MAX_SEARCH_FILE_BYTES = 1_000_000
MAX_SEARCH_EXCERPT_CHARS = 300
MAX_COMMAND_TIMEOUT_SECONDS = 120
DEFAULT_COMMAND_TIMEOUT_SECONDS = 60
MAX_READ_RANGE_LINES = 400
DEFAULT_READ_RANGE_LINES = 120
TRACE_STRING_PREVIEW_CHARS = 1000
TRACE_REDACTED_FIELDS = {
    "content",
    "excerpt",
    "output",
    "patch",
    "query",
    "raw_response",
    "text",
}
DEFAULT_LIST_EXCLUDED_DIRS = {
    ".git",
    ".claude",
    ".mcp",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}


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


@dataclass(frozen=True)
class CommandExecution:
    """Captured command result with bounded output."""

    returncode: int
    output: str
    truncated: bool
    timed_out: bool


LOCAL_ACTION_TOOL_SPECS: tuple[LocalActionToolSpec, ...] = (
    LocalActionToolSpec(
        name="stat_path",
        description="Inspect workspace path metadata without reading contents.",
        parameters={
            "path": {
                "type": "string",
                "description": "Workspace-relative path. Defaults to the project root.",
            },
        },
        example={
            "tool": "stat_path",
            "path": "relative/path.py",
        },
    ),
    LocalActionToolSpec(
        name="list_files",
        description="List workspace files and directories without reading contents.",
        parameters={
            "path": {
                "type": "string",
                "description": "Workspace-relative directory path. Defaults to the project root.",
            },
            "recursive": {
                "type": "boolean",
                "description": "Whether to walk nested directories.",
            },
            "include_hidden": {
                "type": "boolean",
                "description": "Whether to include hidden files and directories.",
            },
            "max_entries": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_LIST_FILE_ENTRIES,
                "description": "Maximum number of entries to return.",
            },
        },
        example={
            "tool": "list_files",
            "path": "src",
            "recursive": False,
            "max_entries": 100,
        },
    ),
    LocalActionToolSpec(
        name="search_text",
        description="Search workspace text files for a literal string.",
        parameters={
            "query": {
                "type": "string",
                "description": "Literal text to search for.",
            },
            "path": {
                "type": "string",
                "description": "Workspace-relative file or directory path. Defaults to the project root.",
            },
            "recursive": {
                "type": "boolean",
                "description": "Whether to walk nested directories when path is a directory.",
            },
            "include_hidden": {
                "type": "boolean",
                "description": "Whether to search hidden files and directories.",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether matching should be case-sensitive.",
            },
            "max_matches": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_SEARCH_MATCHES,
                "description": "Maximum number of line matches to return.",
            },
        },
        required=("query",),
        example={
            "tool": "search_text",
            "query": "function_name",
            "path": "src",
            "recursive": True,
            "max_matches": 25,
        },
    ),
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
        name="read_file_range",
        description="Read a bounded line range from a UTF-8 workspace file.",
        parameters={
            "path": {
                "type": "string",
                "description": "Workspace-relative file path.",
            },
            "start_line": {
                "type": "integer",
                "minimum": 1,
                "description": "1-based line number to start reading from.",
            },
            "max_lines": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_READ_RANGE_LINES,
                "description": "Maximum number of lines to read.",
            },
        },
        required=("path",),
        example={
            "tool": "read_file_range",
            "path": "relative/path.py",
            "start_line": 40,
            "max_lines": DEFAULT_READ_RANGE_LINES,
        },
    ),
    LocalActionToolSpec(
        name="read_many_files",
        description="Read several UTF-8 text files from the workspace.",
        parameters={
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": MAX_READ_MANY_FILES,
                "description": "Workspace-relative file paths.",
            },
            "max_chars_per_file": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_READ_FILE_CHARS,
                "description": "Maximum number of characters to return for each file.",
            },
        },
        required=("paths",),
        example={
            "tool": "read_many_files",
            "paths": ["relative/path.py", "relative/other.py"],
            "max_chars_per_file": 8000,
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
            if tool == "stat_path":
                return self._stat_path(action)
            if tool == "list_files":
                return self._list_files(action)
            if tool == "search_text":
                return self._search_text(action)
            if tool == "read_file":
                return self._read_file(action)
            if tool == "read_file_range":
                return self._read_file_range(action)
            if tool == "read_many_files":
                return self._read_many_files(action)
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

    def _stat_path(self, action: dict[str, Any]) -> ToolActionResult:
        path = optional_workspace_path(action, "path")
        target = resolve_workspace_path(self.project_dir, path)
        display_path = path or "."
        if not target.exists():
            return ToolActionResult(
                tool="stat_path",
                ok=True,
                message=f"Path does not exist: {display_path}",
                data={
                    "path": display_path,
                    "exists": False,
                    "type": "missing",
                },
            )

        path_type = (
            "directory" if target.is_dir() else "file" if target.is_file() else "other"
        )
        data: dict[str, Any] = {
            "path": display_path,
            "exists": True,
            "type": path_type,
        }
        if target.is_file():
            try:
                data["bytes"] = target.stat().st_size
            except OSError:
                data["bytes"] = None

        return ToolActionResult(
            tool="stat_path",
            ok=True,
            message=f"Inspected {display_path}",
            data=data,
        )

    def _list_files(self, action: dict[str, Any]) -> ToolActionResult:
        path = optional_workspace_path(action, "path")
        recursive = optional_bool(action, "recursive", default=False)
        include_hidden = optional_bool(action, "include_hidden", default=False)
        max_entries = bounded_positive_int(
            action,
            "max_entries",
            default=MAX_LIST_FILE_ENTRIES,
            maximum=MAX_LIST_FILE_ENTRIES,
        )
        target = resolve_workspace_path(self.project_dir, path)
        if not target.exists() or not target.is_dir():
            return ToolActionResult(
                tool="list_files",
                ok=False,
                message=f"Directory not found: {path or '.'}",
            )

        entries: list[dict[str, Any]] = []
        truncated = False

        def add_entry(candidate: Path) -> bool:
            nonlocal truncated
            relative = candidate.relative_to(self.project_dir.resolve()).as_posix()
            if not is_safe_list_entry(relative, include_hidden=include_hidden):
                return True
            if len(entries) >= max_entries:
                truncated = True
                return False
            entry: dict[str, Any] = {
                "path": relative,
                "type": "directory" if candidate.is_dir() else "file",
            }
            if candidate.is_file():
                try:
                    entry["bytes"] = candidate.stat().st_size
                except OSError:
                    entry["bytes"] = None
            entries.append(entry)
            return True

        if recursive:
            for root, dir_names, file_names in os.walk(target):
                root_path = Path(root)
                dir_names[:] = sorted(
                    name
                    for name in dir_names
                    if should_descend_directory(
                        root_path / name,
                        self.project_dir,
                        include_hidden=include_hidden,
                    )
                )
                for name in [*dir_names, *sorted(file_names)]:
                    if not add_entry(root_path / name):
                        dir_names[:] = []
                        break
                if truncated:
                    break
        else:
            for child in sorted(target.iterdir(), key=lambda item: item.name):
                if not add_entry(child):
                    break

        return ToolActionResult(
            tool="list_files",
            ok=True,
            message=(
                f"Listed {len(entries)} entr"
                f"{'y' if len(entries) == 1 else 'ies'} under {path or '.'}"
            ),
            data={
                "path": path or ".",
                "entries": entries,
                "entry_count": len(entries),
                "truncated": truncated,
            },
        )

    def _search_text(self, action: dict[str, Any]) -> ToolActionResult:
        query = bounded_string(
            action,
            "query",
            maximum=MAX_SEARCH_QUERY_CHARS,
        )
        path = optional_workspace_path(action, "path")
        recursive = optional_bool(action, "recursive", default=True)
        include_hidden = optional_bool(action, "include_hidden", default=False)
        case_sensitive = optional_bool(action, "case_sensitive", default=False)
        max_matches = bounded_positive_int(
            action,
            "max_matches",
            default=MAX_SEARCH_MATCHES,
            maximum=MAX_SEARCH_MATCHES,
        )
        target = resolve_workspace_path(self.project_dir, path)
        if not target.exists():
            return ToolActionResult(
                tool="search_text",
                ok=False,
                message=f"Path not found: {path or '.'}",
            )

        matches: list[dict[str, Any]] = []
        searched_files = 0
        skipped_files = 0
        query_to_match = query if case_sensitive else query.casefold()

        for file_path in iter_search_files(
            target,
            self.project_dir,
            recursive=recursive,
            include_hidden=include_hidden,
        ):
            relative = file_path.relative_to(self.project_dir.resolve()).as_posix()
            try:
                if file_path.stat().st_size > MAX_SEARCH_FILE_BYTES:
                    skipped_files += 1
                    continue
            except OSError:
                skipped_files += 1
                continue

            searched_files += 1
            try:
                with file_path.open("r", encoding="utf-8", errors="replace") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        haystack = line if case_sensitive else line.casefold()
                        if query_to_match not in haystack:
                            continue
                        matches.append(
                            {
                                "path": relative,
                                "line": line_number,
                                "excerpt": build_search_excerpt(line, query),
                            }
                        )
                        if len(matches) >= max_matches:
                            return self._search_text_result(
                                path=path,
                                matches=matches,
                                searched_files=searched_files,
                                skipped_files=skipped_files,
                                truncated=True,
                            )
            except (OSError, UnicodeError):
                skipped_files += 1

        return self._search_text_result(
            path=path,
            matches=matches,
            searched_files=searched_files,
            skipped_files=skipped_files,
            truncated=False,
        )

    def _search_text_result(
        self,
        *,
        path: str,
        matches: list[dict[str, Any]],
        searched_files: int,
        skipped_files: int,
        truncated: bool,
    ) -> ToolActionResult:
        return ToolActionResult(
            tool="search_text",
            ok=True,
            message=(
                f"Found {len(matches)} line match"
                f"{'' if len(matches) == 1 else 'es'} under {path or '.'}"
            ),
            data={
                "path": path or ".",
                "matches": matches,
                "match_count": len(matches),
                "searched_files": searched_files,
                "skipped_files": skipped_files,
                "truncated": truncated,
            },
        )

    def _read_file(self, action: dict[str, Any]) -> ToolActionResult:
        path = require_string(action, "path")
        max_chars = bounded_positive_int(
            action,
            "max_chars",
            default=MAX_READ_FILE_CHARS,
            maximum=MAX_READ_FILE_CHARS,
        )
        file_result = self._read_text_file(path, max_chars=max_chars)
        if not file_result["ok"]:
            return ToolActionResult(
                tool="read_file",
                ok=False,
                message=str(file_result["message"]),
            )

        return ToolActionResult(
            tool="read_file",
            ok=True,
            message=f"Read {path}",
            data={
                "path": path,
                "content": file_result["content"],
                "truncated": file_result["truncated"],
            },
        )

    def _read_many_files(self, action: dict[str, Any]) -> ToolActionResult:
        paths = require_string_list(
            action,
            "paths",
            maximum=MAX_READ_MANY_FILES,
        )
        max_chars = bounded_positive_int(
            action,
            "max_chars_per_file",
            default=MAX_READ_FILE_CHARS,
            maximum=MAX_READ_FILE_CHARS,
        )
        files = [
            {
                "path": path,
                **self._read_text_file(path, max_chars=max_chars),
            }
            for path in paths
        ]
        read_count = sum(1 for file in files if file["ok"])

        return ToolActionResult(
            tool="read_many_files",
            ok=read_count == len(files),
            message=(
                f"Read {read_count} of {len(files)} file"
                f"{'' if len(files) == 1 else 's'}"
            ),
            data={
                "files": files,
                "file_count": len(files),
                "read_count": read_count,
            },
        )

    def _read_file_range(self, action: dict[str, Any]) -> ToolActionResult:
        path = require_string(action, "path")
        start_line = bounded_positive_int(
            action,
            "start_line",
            default=1,
            maximum=1_000_000,
        )
        max_lines = bounded_positive_int(
            action,
            "max_lines",
            default=DEFAULT_READ_RANGE_LINES,
            maximum=MAX_READ_RANGE_LINES,
        )
        target = resolve_workspace_path(self.project_dir, path)
        if not target.exists() or not target.is_file():
            return ToolActionResult(
                tool="read_file_range",
                ok=False,
                message=f"File not found: {path}",
            )

        lines: list[dict[str, Any]] = []
        truncated = False
        with target.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line_number < start_line:
                    continue
                if len(lines) >= max_lines:
                    truncated = True
                    break
                lines.append(
                    {
                        "line": line_number,
                        "text": line.rstrip("\r\n"),
                    }
                )

        end_line = lines[-1]["line"] if lines else start_line - 1
        content = "\n".join(f"{line['line']}: {line['text']}" for line in lines)
        return ToolActionResult(
            tool="read_file_range",
            ok=True,
            message=f"Read {len(lines)} line(s) from {path}",
            data={
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
                "max_lines": max_lines,
                "lines": lines,
                "content": content,
                "line_count": len(lines),
                "truncated": truncated,
            },
        )

    def _read_text_file(self, path: str, *, max_chars: int) -> dict[str, Any]:
        target = resolve_workspace_path(self.project_dir, path)
        if not target.exists() or not target.is_file():
            return {
                "ok": False,
                "message": f"File not found: {path}",
            }

        with target.open("r", encoding="utf-8", errors="replace") as handle:
            content = handle.read(max_chars + 1)
        truncated = len(content) > max_chars
        if truncated:
            content = content[:max_chars]

        return {
            "ok": True,
            "message": f"Read {path}",
            "content": content,
            "truncated": truncated,
        }

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
        timeout = bounded_positive_int(
            action,
            "timeout",
            default=DEFAULT_COMMAND_TIMEOUT_SECONDS,
            maximum=MAX_COMMAND_TIMEOUT_SECONDS,
        )

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

        completed = await self._run_subprocess_bounded(args, timeout)
        output = completed.output
        if completed.truncated:
            output = output[:MAX_TOOL_OUTPUT_CHARS] + "\n...[truncated]"

        message = f"Command exited with code {completed.returncode}"
        if completed.timed_out:
            message = f"Command timed out after {timeout} seconds"
        elif completed.truncated:
            message = (
                f"Command output exceeded {MAX_TOOL_OUTPUT_CHARS} characters "
                "and was terminated"
            )

        return ToolActionResult(
            tool="run_command",
            ok=completed.returncode == 0 and not completed.truncated,
            message=message,
            data={
                "command": command,
                "exit_code": completed.returncode,
                "output": output,
                "truncated": completed.truncated,
                "timed_out": completed.timed_out,
            },
        )

    async def _run_subprocess_bounded(
        self,
        args: list[str],
        timeout: int,
    ) -> CommandExecution:
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(self.project_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        remaining = MAX_TOOL_OUTPUT_CHARS
        truncated = False

        async def capture_stream(
            stream: asyncio.StreamReader | None,
            parts: list[str],
        ) -> None:
            nonlocal remaining, truncated
            if stream is None:
                return
            while True:
                chunk = await stream.read(4096)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                consumed_chars = 0
                if remaining > 0:
                    piece = text[:remaining]
                    parts.append(piece)
                    remaining -= len(piece)
                    consumed_chars = len(piece)
                if len(text) > consumed_chars or remaining <= 0:
                    truncated = True
                    if process.returncode is None:
                        process.terminate()
                    break

        stdout_task = asyncio.create_task(capture_stream(process.stdout, stdout_parts))
        stderr_task = asyncio.create_task(capture_stream(process.stderr, stderr_parts))
        timed_out = False
        try:
            await asyncio.wait_for(
                asyncio.gather(stdout_task, stderr_task),
                timeout=timeout,
            )
        except TimeoutError:
            timed_out = True
            if process.returncode is None:
                process.kill()
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

        if process.returncode is None:
            try:
                await asyncio.wait_for(process.wait(), timeout=1)
            except TimeoutError:
                process.kill()
                await process.wait()

        output = "\n".join(
            part.strip()
            for part in ("".join(stdout_parts), "".join(stderr_parts))
            if part and part.strip()
        )
        return CommandExecution(
            returncode=process.returncode if process.returncode is not None else -1,
            output=output,
            truncated=truncated,
            timed_out=timed_out,
        )


def safe_action_for_trace(action: dict[str, Any]) -> dict[str, Any]:
    """Avoid duplicating full file contents in trace request sections."""
    safe = dict(action)
    if "query" in safe:
        query = str(safe["query"])
        safe["query_bytes"] = len(query.encode("utf-8"))
        safe["query_redacted"] = True
        del safe["query"]
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


def bounded_string(action: dict[str, Any], field_name: str, *, maximum: int) -> str:
    """Read a required non-empty string with a maximum length."""
    value = require_string(action, field_name)
    if len(value) > maximum:
        raise LocalActionError(
            f"Action field '{field_name}' must be at most {maximum} characters"
        )
    return value


def require_string_list(
    action: dict[str, Any],
    field_name: str,
    *,
    maximum: int,
) -> list[str]:
    """Read a required bounded list of non-empty strings."""
    value = action.get(field_name)
    if not isinstance(value, list):
        raise LocalActionError(f"Action field '{field_name}' must be a list")
    if not value:
        raise LocalActionError(f"Action field '{field_name}' must not be empty")
    if len(value) > maximum:
        raise LocalActionError(
            f"Action field '{field_name}' must contain at most {maximum} items"
        )
    strings: list[str] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, str) or not item:
            raise LocalActionError(
                f"Action field '{field_name}' item #{index} must be a string"
            )
        validate_workspace_relative_path(item)
        strings.append(item)
    return strings


def optional_workspace_path(action: dict[str, Any], field_name: str) -> str:
    """Read an optional workspace path, treating root aliases as project root."""
    value = action.get(field_name)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise LocalActionError(f"Action field '{field_name}' must be a string")
    if value in {"", ".", "./"}:
        return ""
    validate_workspace_relative_path(value)
    return value


def optional_bool(action: dict[str, Any], field_name: str, *, default: bool) -> bool:
    """Read an optional boolean without silently accepting strings/numbers."""
    value = action.get(field_name)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise LocalActionError(f"Action field '{field_name}' must be a boolean")
    return value


def bounded_positive_int(
    action: dict[str, Any],
    field_name: str,
    *,
    default: int,
    maximum: int,
) -> int:
    """Read an optional positive integer without treating 0 as a default."""
    value = action.get(field_name)
    if value is None:
        return default
    if isinstance(value, bool):
        raise LocalActionError(
            f"Action field '{field_name}' must be a positive integer"
        )
    try:
        parsed = int(value)
    except (TypeError, ValueError) as e:
        raise LocalActionError(
            f"Action field '{field_name}' must be a positive integer"
        ) from e
    if parsed <= 0:
        raise LocalActionError(f"Action field '{field_name}' must be greater than 0")
    return min(parsed, maximum)


def should_descend_directory(
    directory: Path,
    project_dir: Path,
    *,
    include_hidden: bool,
) -> bool:
    """Return whether recursive listing should walk into a directory."""
    if directory.name in DEFAULT_LIST_EXCLUDED_DIRS:
        return False
    relative = directory.relative_to(project_dir.resolve()).as_posix()
    return is_safe_list_entry(relative, include_hidden=include_hidden)


def is_safe_list_entry(path: str, *, include_hidden: bool) -> bool:
    """Return whether a path is safe and allowed in list_files output."""
    parts = Path(path).parts
    if any(part in DEFAULT_LIST_EXCLUDED_DIRS for part in parts):
        return False
    if not include_hidden and any(part.startswith(".") for part in parts):
        return False
    try:
        validate_workspace_relative_path(path)
    except PatchProposalError:
        return False
    return True


def iter_search_files(
    target: Path,
    project_dir: Path,
    *,
    recursive: bool,
    include_hidden: bool,
):
    """Yield safe searchable files under a target file or directory."""
    resolved_project = project_dir.resolve()
    if target.is_file():
        relative = target.relative_to(resolved_project).as_posix()
        if is_safe_list_entry(relative, include_hidden=include_hidden):
            yield target
        return

    if not target.is_dir():
        return

    if recursive:
        for root, dir_names, file_names in os.walk(target):
            root_path = Path(root)
            dir_names[:] = sorted(
                name
                for name in dir_names
                if should_descend_directory(
                    root_path / name,
                    project_dir,
                    include_hidden=include_hidden,
                )
            )
            for name in sorted(file_names):
                candidate = root_path / name
                relative = candidate.relative_to(resolved_project).as_posix()
                if is_safe_list_entry(relative, include_hidden=include_hidden):
                    yield candidate
        return

    for child in sorted(target.iterdir(), key=lambda item: item.name):
        if not child.is_file():
            continue
        relative = child.relative_to(resolved_project).as_posix()
        if is_safe_list_entry(relative, include_hidden=include_hidden):
            yield child


def build_search_excerpt(line: str, query: str) -> str:
    """Return a compact single-line search excerpt."""
    normalized = " ".join(line.strip().split())
    if len(normalized) <= MAX_SEARCH_EXCERPT_CHARS:
        return normalized

    query_index = normalized.casefold().find(query.casefold())
    if query_index < 0:
        return normalized[:MAX_SEARCH_EXCERPT_CHARS].rstrip() + "..."

    context = max((MAX_SEARCH_EXCERPT_CHARS - len(query)) // 2, 0)
    start = max(query_index - context, 0)
    end = min(start + MAX_SEARCH_EXCERPT_CHARS, len(normalized))
    start = max(end - MAX_SEARCH_EXCERPT_CHARS, 0)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(normalized) else ""
    return prefix + normalized[start:end].strip() + suffix


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
