"""Provider-neutral local edit/tool runtime."""

from __future__ import annotations

import asyncio
import json
import logging
import shlex
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.platform import is_windows
from security import split_command_segments, validate_command

from ..capabilities import RuntimeCapabilities
from ..result import AgentRunResult
from .completion import CompletionRuntimeSession
from .patch_proposal import (
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

GENERIC_EDIT_PROMPT_TEMPLATE = """You are running in Auto Code generic_edit mode.

You do not have native provider tools, MCP, or subagents. Auto Code exposes a
small local action loop. Respond with exactly one JSON object and no prose.

Available actions:
- read_file: {"tool": "read_file", "path": "relative/path.py", "max_chars": 12000}
- write_file: {"tool": "write_file", "path": "relative/path.py", "content": "complete file content"}
- apply_patch: {"tool": "apply_patch", "patch": "unified diff"}
- run_command: {"tool": "run_command", "command": "pytest tests/test_file.py -q", "timeout": 60}
- finish: {"tool": "finish", "summary": "what changed", "tests": ["commands run"], "risks": []}

Rules:
- Use only workspace-relative paths.
- Do not touch .git, .claude, .mcp.json, .env files, shell profiles, secrets, or credential files.
- Prefer apply_patch for code edits. Use write_file only when replacing a small text file is clearer.
- run_command supports a single executable command, not shell pipes, redirection, or command chaining.
- Keep iterating until the task is done, then call finish.

Return schema:
{
  "thought": "short private planning note",
  "actions": [
    {"tool": "read_file", "path": "relative/path.py"}
  ]
}

Task:
__AUTO_CODE_TASK_PROMPT__
"""


class GenericEditRuntimeError(RuntimeError):
    """Raised when the generic edit runtime cannot continue safely."""


@dataclass
class ToolActionResult:
    """Structured result for one local action."""

    tool: str
    ok: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "ok": self.ok,
            "message": self.message,
            "data": self.data,
        }


class GenericEditRuntimeSession:
    """Runtime that turns model-emitted JSON actions into local workspace work."""

    name = "generic_edit"
    capabilities = RuntimeCapabilities.generic_edit()

    def __init__(
        self,
        *,
        provider_name: str,
        agent_session: Any,
        project_dir: Path,
        max_iterations: int = 8,
    ):
        self.provider_name = provider_name
        self.agent_session = agent_session
        self.project_dir = project_dir
        self.max_iterations = max_iterations
        self._completion_runtime = CompletionRuntimeSession(
            provider_name=provider_name,
            agent_session=agent_session,
        )

    @property
    def context_client(self) -> Any:
        return None

    async def run(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None = None,
    ) -> AgentRunResult:
        del verbose, phase

        prompt = GENERIC_EDIT_PROMPT_TEMPLATE.replace(
            "__AUTO_CODE_TASK_PROMPT__",
            message,
        )
        trace: list[dict[str, Any]] = []

        for iteration in range(1, self.max_iterations + 1):
            response_text = await self._complete(prompt)
            iteration_entry: dict[str, Any] = {
                "iteration": iteration,
                "response": response_text,
                "actions": [],
            }

            try:
                response = parse_generic_edit_response(response_text)
                actions = normalize_actions(response)
            except GenericEditRuntimeError as e:
                iteration_entry["error"] = str(e)
                trace.append(iteration_entry)
                artifacts = save_generic_edit_artifacts(
                    spec_dir=spec_dir,
                    provider_name=self.provider_name,
                    subtask_id=subtask_id,
                    status="error",
                    message=str(e),
                    trace=trace,
                    summary="Generic edit runtime failed to parse provider actions.",
                )
                return AgentRunResult(
                    status="error",
                    response_text=(
                        f"Generic edit runtime failed to parse provider actions: {e}\n"
                        f"Artifacts: {artifacts['generic_edit_trace']}"
                    ),
                )

            if not actions:
                result = ToolActionResult(
                    tool="runtime",
                    ok=False,
                    message="No actions returned; return at least one action.",
                )
                iteration_entry["actions"].append(result.to_dict())
                trace.append(iteration_entry)
                prompt = build_observation_prompt([result])
                continue

            action_results: list[ToolActionResult] = []
            for action in actions:
                result = await self._execute_action(action)
                action_results.append(result)
                iteration_entry["actions"].append(
                    {
                        "request": safe_action_for_trace(action),
                        "result": result.to_dict(),
                    }
                )

                if action_tool(action) == "finish":
                    if any(not action_result.ok for action_result in action_results):
                        continue
                    summary = str(action.get("summary") or result.message)
                    tests = normalize_string_list(action.get("tests"))
                    risks = normalize_string_list(action.get("risks"))
                    trace.append(iteration_entry)
                    artifacts = save_generic_edit_artifacts(
                        spec_dir=spec_dir,
                        provider_name=self.provider_name,
                        subtask_id=subtask_id,
                        status="complete",
                        message=summary,
                        trace=trace,
                        summary=summary,
                        tests=tests,
                        risks=risks,
                    )
                    response_lines = build_generic_edit_response(
                        summary=summary,
                        artifacts=artifacts,
                        tests=tests,
                        risks=risks,
                    )
                    return AgentRunResult(
                        status="continue",
                        response_text="\n".join(response_lines),
                    )

            trace.append(iteration_entry)
            prompt = build_observation_prompt(action_results)

        message = (
            f"Generic edit runtime reached max iterations ({self.max_iterations}) "
            "before finish."
        )
        artifacts = save_generic_edit_artifacts(
            spec_dir=spec_dir,
            provider_name=self.provider_name,
            subtask_id=subtask_id,
            status="error",
            message=message,
            trace=trace,
            summary=message,
        )
        return AgentRunResult(
            status="error",
            response_text=f"{message}\nArtifacts: {artifacts['generic_edit_trace']}",
        )

    async def _complete(self, message: str) -> str:
        chunks: list[str] = []
        async for chunk in self._completion_runtime._stream_text(message):
            chunks.append(chunk)
        return "".join(chunks)

    async def _execute_action(self, action: dict[str, Any]) -> ToolActionResult:
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
                    message=str(action.get("summary") or "Generic edit completed"),
                )
            return ToolActionResult(
                tool=tool or "unknown",
                ok=False,
                message=f"Unknown tool: {tool or '<missing>'}",
            )
        except (GenericEditRuntimeError, PatchProposalError) as e:
            return ToolActionResult(tool=tool or "unknown", ok=False, message=str(e))
        except Exception as e:
            logger.error("Generic edit action failed", exc_info=True)
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


def parse_generic_edit_response(text: str) -> dict[str, Any]:
    """Parse the model JSON response for generic_edit mode."""
    candidate = extract_json_object(text)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise GenericEditRuntimeError(f"Generic edit response is not valid JSON: {e}")

    if not isinstance(parsed, dict):
        raise GenericEditRuntimeError("Generic edit response must be a JSON object")
    return parsed


def normalize_actions(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize supported action response shapes."""
    actions = response.get("actions")
    if actions is None and isinstance(response.get("action"), dict):
        actions = [response["action"]]
    if actions is None and response.get("tool"):
        actions = [response]
    if actions is None:
        return []
    if not isinstance(actions, list):
        raise GenericEditRuntimeError("Generic edit field 'actions' must be a list")

    normalized: list[dict[str, Any]] = []
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            raise GenericEditRuntimeError(
                f"Generic edit action #{index + 1} must be an object"
            )
        normalized.append(action)
    return normalized


def build_observation_prompt(results: list[ToolActionResult]) -> str:
    """Build the next user message containing local action observations."""
    payload = {
        "observations": [result.to_dict() for result in results],
        "instruction": (
            "Continue the task. Return exactly one JSON object with actions. "
            "Use finish when complete."
        ),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_generic_edit_response(
    *,
    summary: str,
    artifacts: dict[str, str],
    tests: list[str],
    risks: list[str],
) -> list[str]:
    """Build concise user-facing generic edit output."""
    response_lines = [
        summary,
        "",
        "Generic edit runtime completed local actions.",
        "",
        "Artifacts:",
    ]
    response_lines.extend(f"- {name}: {path}" for name, path in artifacts.items())
    if tests:
        response_lines.extend(["", "Suggested verification commands:"])
        response_lines.extend(f"- {test}" for test in tests)
    if risks:
        response_lines.extend(["", "Risks:"])
        response_lines.extend(f"- {risk}" for risk in risks)
    return response_lines


def save_generic_edit_artifacts(
    *,
    spec_dir: Path,
    provider_name: str,
    subtask_id: str | None,
    status: str,
    message: str,
    trace: list[dict[str, Any]],
    summary: str,
    tests: list[str] | None = None,
    risks: list[str] | None = None,
) -> dict[str, str]:
    """Persist trace/result artifacts for a generic edit run."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    trace_path = artifact_dir / "generic_edit_trace.json"
    summary_path = artifact_dir / "generic_edit_summary.md"
    result_path = artifact_dir / "generic_edit_result.json"
    timestamp = datetime.now(UTC).isoformat()

    payload = {
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "message": message,
        "trace": trace,
    }
    trace_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    result_payload = {
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "message": message,
        "iteration_count": len(trace),
        "tests": tests or [],
        "test_count": len(tests or []),
        "risks": risks or [],
        "risk_count": len(risks or []),
    }
    result_path.write_text(
        json.dumps(result_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "# Generic Edit Summary",
        "",
        f"Status: {status}",
        f"Provider: {provider_name}",
    ]
    if subtask_id:
        lines.append(f"Subtask: {subtask_id}")
    lines.extend(["", "## Summary", "", summary])
    if tests:
        lines.extend(["", "## Suggested Verification Commands", ""])
        lines.extend(f"- `{test}`" for test in tests)
    if risks:
        lines.extend(["", "## Risks", ""])
        lines.extend(f"- {risk}" for risk in risks)
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "generic_edit_trace": str(trace_path),
        "generic_edit_result": str(result_path),
        "generic_edit_summary": str(summary_path),
    }


def safe_action_for_trace(action: dict[str, Any]) -> dict[str, Any]:
    """Avoid duplicating full file contents in the trace request section."""
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
        raise GenericEditRuntimeError(f"Action field '{field_name}' must be a string")
    return value


def resolve_workspace_path(project_dir: Path, path: str) -> Path:
    """Validate and resolve a workspace-relative file path."""
    validate_workspace_relative_path(path)
    resolved_project = project_dir.resolve()
    target = (resolved_project / path).resolve()
    if not target.is_relative_to(resolved_project):
        raise GenericEditRuntimeError(f"Path escapes workspace: {path}")
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


def extract_json_object(text: str) -> str:
    """Extract the first complete JSON object from a text response."""
    stripped = strip_markdown_fence(text)
    start = stripped.find("{")
    if start < 0:
        raise GenericEditRuntimeError("Generic edit response did not contain JSON")

    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(stripped[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return stripped[start : index + 1]

    raise GenericEditRuntimeError(
        "Generic edit response did not contain a complete JSON object"
    )


def strip_markdown_fence(text: str) -> str:
    """Remove a simple markdown JSON fence when present."""
    stripped = text.strip()
    lines = stripped.splitlines()
    if len(lines) < 2:
        return stripped

    opening = lines[0].strip().lower()
    closing = lines[-1].strip()
    if opening in {"```", "```json"} and closing == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped
