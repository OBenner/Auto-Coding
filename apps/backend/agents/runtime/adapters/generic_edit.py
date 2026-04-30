"""Provider-neutral local edit/tool runtime."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..capabilities import RuntimeCapabilities
from ..local_actions import (
    LocalActionExecutor,
    ToolActionResult,
    action_tool,
    local_action_tool_schemas,
    normalize_string_list,
    render_local_action_prompt,
    safe_action_for_trace,
    safe_result_for_trace,
)
from ..result import AgentRunResult
from .completion import CompletionRuntimeSession
from .json_helpers import extract_first_json_object

GENERIC_EDIT_PROMPT_TEMPLATE = """You are running in Auto Code generic_edit mode.

You do not have native provider tools, MCP, or subagents. Auto Code exposes a
small local action loop. Respond with exactly one JSON object and no prose.

Available actions:
__AUTO_CODE_LOCAL_ACTIONS__

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

NATIVE_TOOL_PROMPT_TEMPLATE = """You are running in Auto Code generic_edit mode.

You do not have provider-native filesystem, shell, MCP, or subagents. Auto Code
exposes a small set of local tools as function calls. Use those tools to inspect
and edit the workspace. Keep iterating until the task is done, then call finish.

Rules:
- Use only workspace-relative paths.
- Do not touch .git, .claude, .mcp.json, .env files, shell profiles, secrets, or credential files.
- Prefer apply_patch for code edits. Use write_file only when replacing a small text file is clearer.
- run_command supports a single executable command, not shell pipes, redirection, or command chaining.
- Call finish with a concise summary, verification commands, and risks when complete.

Task:
__AUTO_CODE_TASK_PROMPT__
"""


class GenericEditRuntimeError(RuntimeError):
    """Raised when the generic edit runtime cannot continue safely."""


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
        self.max_iterations = max_iterations
        self._completion_runtime = CompletionRuntimeSession(
            provider_name=provider_name,
            agent_session=agent_session,
        )
        self._executor = LocalActionExecutor(project_dir)

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

        if self._supports_native_tool_calls():
            return await self._run_native_tool_loop(
                message=message,
                spec_dir=spec_dir,
                subtask_id=subtask_id,
            )

        return await self._run_json_action_loop(
            message=message,
            spec_dir=spec_dir,
            subtask_id=subtask_id,
        )

    async def _run_json_action_loop(
        self,
        *,
        message: str,
        spec_dir: Path,
        subtask_id: str | None,
    ) -> AgentRunResult:
        base_prompt = build_generic_edit_prompt(message)
        prompt = base_prompt
        trace: list[dict[str, Any]] = []

        for iteration in range(1, self.max_iterations + 1):
            response_text = await self._complete(prompt)
            iteration_entry: dict[str, Any] = {
                "iteration": iteration,
                "response_excerpt": response_text[:1000],
                "response_bytes": len(response_text.encode("utf-8")),
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
                    stop_reason="parse_error",
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
                iteration_entry["actions"].append(safe_result_for_trace(result))
                trace.append(iteration_entry)
                prompt = build_observation_prompt(
                    base_prompt=base_prompt,
                    results=[result],
                )
                continue

            action_results: list[ToolActionResult] = []
            for action in actions:
                result = await self._executor.execute(action)
                action_results.append(result)
                iteration_entry["actions"].append(
                    {
                        "request": safe_action_for_trace(action),
                        "result": safe_result_for_trace(result),
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
                        stop_reason="finish",
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
            prompt = build_observation_prompt(
                base_prompt=base_prompt,
                results=action_results,
            )

        message = (
            f"Generic edit runtime reached max iterations ({self.max_iterations}) "
            "before finish."
        )
        artifacts = save_generic_edit_artifacts(
            spec_dir=spec_dir,
            provider_name=self.provider_name,
            subtask_id=subtask_id,
            status="error",
            stop_reason="max_iterations",
            message=message,
            trace=trace,
            summary=message,
        )
        return AgentRunResult(
            status="error",
            response_text=f"{message}\nArtifacts: {artifacts['generic_edit_trace']}",
        )

    async def _run_native_tool_loop(
        self,
        *,
        message: str,
        spec_dir: Path,
        subtask_id: str | None,
    ) -> AgentRunResult:
        prompt: str | None = build_native_tool_edit_prompt(message)
        trace: list[dict[str, Any]] = []

        for iteration in range(1, self.max_iterations + 1):
            iteration_entry: dict[str, Any] = {
                "iteration": iteration,
                "loop": "native_tool_calls",
                "response_excerpt": "",
                "response_bytes": 0,
                "actions": [],
            }

            try:
                response = await self.agent_session.complete_with_tool_calls(
                    prompt,
                    local_action_tool_schemas(),
                )
            except Exception as e:
                if iteration == 1 and callable(
                    getattr(self.agent_session, "complete", None)
                ):
                    return await self._run_json_action_loop(
                        message=message,
                        spec_dir=spec_dir,
                        subtask_id=subtask_id,
                    )
                iteration_entry["error"] = str(e)
                trace.append(iteration_entry)
                artifacts = save_generic_edit_artifacts(
                    spec_dir=spec_dir,
                    provider_name=self.provider_name,
                    subtask_id=subtask_id,
                    status="error",
                    stop_reason="native_tool_error",
                    message=str(e),
                    trace=trace,
                    summary="Generic edit native tool-call loop failed.",
                )
                return AgentRunResult(
                    status="error",
                    response_text=(
                        f"Generic edit native tool-call loop failed: {e}\n"
                        f"Artifacts: {artifacts['generic_edit_trace']}"
                    ),
                )

            response_content = str(getattr(response, "content", "") or "")
            tool_calls = tuple(getattr(response, "tool_calls", ()) or ())
            iteration_entry["response_excerpt"] = response_content[:1000]
            iteration_entry["response_bytes"] = len(response_content.encode("utf-8"))

            if not tool_calls:
                result = ToolActionResult(
                    tool="runtime",
                    ok=False,
                    message=(
                        "No local tool calls returned; call at least one local "
                        "tool or finish."
                    ),
                )
                iteration_entry["actions"].append(safe_result_for_trace(result))
                trace.append(iteration_entry)
                prompt = (
                    "No local tool calls were returned. Continue the task by "
                    "calling one or more local tools, or call finish when complete."
                )
                continue

            action_results: list[ToolActionResult] = []
            finish_action: dict[str, Any] | None = None
            finish_result: ToolActionResult | None = None
            for tool_call in tool_calls:
                action = {
                    "tool": str(getattr(tool_call, "name", "") or ""),
                    **dict(getattr(tool_call, "arguments", {}) or {}),
                }
                result = await self._executor.execute(action)
                action_results.append(result)
                iteration_entry["actions"].append(
                    {
                        "request": {
                            "tool_call_id": str(getattr(tool_call, "id", "") or ""),
                            **safe_action_for_trace(action),
                        },
                        "result": safe_result_for_trace(result),
                    }
                )
                self.agent_session.add_tool_result(
                    str(getattr(tool_call, "id", "") or ""),
                    action_tool(action),
                    result.to_dict(),
                )

                if action_tool(action) == "finish":
                    finish_action = action
                    finish_result = result

            if (
                finish_action is not None
                and finish_result is not None
                and all(action_result.ok for action_result in action_results)
            ):
                summary = str(finish_action.get("summary") or finish_result.message)
                tests = normalize_string_list(finish_action.get("tests"))
                risks = normalize_string_list(finish_action.get("risks"))
                trace.append(iteration_entry)
                artifacts = save_generic_edit_artifacts(
                    spec_dir=spec_dir,
                    provider_name=self.provider_name,
                    subtask_id=subtask_id,
                    status="complete",
                    stop_reason="finish",
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
            prompt = None

        message = (
            f"Generic edit native tool-call loop reached max iterations "
            f"({self.max_iterations}) before finish."
        )
        artifacts = save_generic_edit_artifacts(
            spec_dir=spec_dir,
            provider_name=self.provider_name,
            subtask_id=subtask_id,
            status="error",
            stop_reason="max_iterations",
            message=message,
            trace=trace,
            summary=message,
        )
        return AgentRunResult(
            status="error",
            response_text=f"{message}\nArtifacts: {artifacts['generic_edit_trace']}",
        )

    def _supports_native_tool_calls(self) -> bool:
        return callable(
            getattr(self.agent_session, "complete_with_tool_calls", None)
        ) and callable(getattr(self.agent_session, "add_tool_result", None))

    async def _complete(self, message: str) -> str:
        chunks: list[str] = []
        async for chunk in self._completion_runtime._stream_text(message):
            chunks.append(chunk)
        return "".join(chunks)


def build_generic_edit_prompt(message: str) -> str:
    """Build the generic_edit prompt from the shared local action manifest."""
    return GENERIC_EDIT_PROMPT_TEMPLATE.replace(
        "__AUTO_CODE_LOCAL_ACTIONS__",
        render_local_action_prompt(),
    ).replace(
        "__AUTO_CODE_TASK_PROMPT__",
        message,
    )


def build_native_tool_edit_prompt(message: str) -> str:
    """Build the generic_edit prompt for provider-native tool-call sessions."""
    return NATIVE_TOOL_PROMPT_TEMPLATE.replace(
        "__AUTO_CODE_TASK_PROMPT__",
        message,
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


def build_observation_prompt(
    *,
    base_prompt: str,
    results: list[ToolActionResult],
) -> str:
    """Build the next user message containing local action observations."""
    payload = {
        "observations": [result.to_dict() for result in results],
        "instruction": (
            "Continue the task. Return exactly one JSON object with actions. "
            "Use finish when complete."
        ),
    }
    return (
        base_prompt.rstrip()
        + "\n\n## Local Action Observations\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


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
    stop_reason: str,
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
    timeline_path = artifact_dir / "generic_edit_timeline.json"
    summary_path = artifact_dir / "generic_edit_summary.md"
    result_path = artifact_dir / "generic_edit_result.json"
    timestamp = datetime.now(UTC).isoformat()
    trace_summary = summarize_generic_edit_trace(trace)

    payload = {
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "stop_reason": stop_reason,
        "message": message,
        "trace": trace,
    }
    trace_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    timeline_payload = {
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "stop_reason": stop_reason,
        "timeline": trace_summary["action_timeline"],
    }
    timeline_path.write_text(
        json.dumps(timeline_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    result_payload = {
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "stop_reason": stop_reason,
        "message": message,
        **trace_summary,
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
        f"Stop reason: {stop_reason}",
    ]
    if subtask_id:
        lines.append(f"Subtask: {subtask_id}")
    lines.extend(["", "## Summary", "", summary])
    if trace_summary["action_timeline"]:
        lines.extend(["", "## Action Timeline", ""])
        for item in trace_summary["action_timeline"]:
            status_label = "ok" if item["ok"] else "failed"
            path_suffix = f" `{item['path']}`" if item.get("path") else ""
            lines.append(
                f"- Iteration {item['iteration']}: `{item['tool']}` "
                f"{status_label}{path_suffix} - {item['message']}"
            )
    if tests:
        lines.extend(["", "## Suggested Verification Commands", ""])
        lines.extend(f"- `{test}`" for test in tests)
    if risks:
        lines.extend(["", "## Risks", ""])
        lines.extend(f"- {risk}" for risk in risks)
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "generic_edit_trace": str(trace_path),
        "generic_edit_timeline": str(timeline_path),
        "generic_edit_result": str(result_path),
        "generic_edit_summary": str(summary_path),
    }


def summarize_generic_edit_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    """Return compact trace counters for result artifacts and UI consumers."""
    loop_kind = "json_actions"
    action_count = 0
    failed_action_count = 0
    tool_counts: dict[str, int] = {}
    failed_tools: dict[str, int] = {}
    action_timeline: list[dict[str, Any]] = []

    for iteration in trace:
        iteration_number = iteration.get("iteration")
        if iteration.get("loop"):
            loop_kind = str(iteration["loop"])
        for action_entry in iteration.get("actions", []):
            action_count += 1
            result = action_entry.get("result", action_entry)
            request = action_entry.get("request", {})
            if isinstance(result, dict):
                tool = str(result.get("tool") or "runtime")
                tool_counts[tool] = tool_counts.get(tool, 0) + 1
                is_ok = result.get("ok") is not False
                if result.get("ok") is False:
                    failed_action_count += 1
                    failed_tools[tool] = failed_tools.get(tool, 0) + 1
                action_timeline.append(
                    build_timeline_entry(
                        iteration_number=iteration_number,
                        tool=tool,
                        ok=is_ok,
                        message=str(result.get("message") or ""),
                        request=request if isinstance(request, dict) else {},
                        result=result,
                    )
                )
            elif isinstance(result, str):
                tool_counts["runtime"] = tool_counts.get("runtime", 0) + 1
                action_timeline.append(
                    {
                        "iteration": iteration_number,
                        "tool": "runtime",
                        "ok": True,
                        "message": result[:300],
                    }
                )

    return {
        "loop": loop_kind,
        "action_count": action_count,
        "failed_action_count": failed_action_count,
        "tool_counts": tool_counts,
        "failed_tools": failed_tools,
        "action_timeline": action_timeline,
    }


def build_timeline_entry(
    *,
    iteration_number: Any,
    tool: str,
    ok: bool,
    message: str,
    request: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Build a compact, safe timeline item for UI/debug artifacts."""
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    entry: dict[str, Any] = {
        "iteration": iteration_number,
        "tool": tool,
        "ok": ok,
        "message": message[:300],
    }
    path = request.get("path") or data.get("path")
    if path:
        entry["path"] = str(path)
    if "exit_code" in data:
        entry["exit_code"] = data["exit_code"]
    if "timed_out" in data:
        entry["timed_out"] = data["timed_out"]
    if "truncated" in data:
        entry["truncated"] = data["truncated"]
    if request.get("tool_call_id"):
        entry["tool_call_id"] = str(request["tool_call_id"])
    return entry


def extract_json_object(text: str) -> str:
    """Extract the first complete JSON object from a text response."""
    return extract_first_json_object(
        text,
        strip_fence=strip_markdown_fence,
        error_factory=GenericEditRuntimeError,
        missing_message="Generic edit response did not contain JSON",
        incomplete_message=(
            "Generic edit response did not contain a complete JSON object"
        ),
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
