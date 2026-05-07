"""Provider-neutral local edit/tool runtime."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.providers.exceptions import ProviderConfigError, ProviderNotInstalled

from ..capabilities import RuntimeCapabilities, RuntimeRequirements
from ..local_actions import (
    MAX_SUBAGENT_ID_CHARS,
    MAX_SUBAGENT_PROMPT_CHARS,
    MAX_SUBAGENT_RESULT_CHARS,
    MAX_SUBAGENT_ROLE_CHARS,
    MAX_SUBAGENT_TASKS,
    LocalActionExecutor,
    ToolActionResult,
    action_tool,
    local_action_tool_schemas,
    normalize_string_list,
    render_local_action_prompt,
    safe_action_for_trace,
    safe_result_for_trace,
)
from ..mcp_bridge import (
    RuntimeMcpBridge,
    is_mcp_action_name,
    resolve_runtime_mcp_support,
    unavailable_mcp_action_result,
)
from ..result import AgentRunResult
from ..subagents import (
    DEFAULT_SUBAGENT_MERGE_POLICY,
    MAX_SUBAGENT_ATTEMPTS,
    RuntimeSessionFactory,
    RuntimeSubagentOrchestrator,
    RuntimeSubagentTask,
)
from .completion import CompletionRuntimeSession
from .json_helpers import extract_first_json_object

GENERIC_EDIT_CANCELLED_MESSAGE = "Generic edit runtime was cancelled."

GENERIC_EDIT_PROMPT_TEMPLATE = """You are running in Auto Code generic_edit mode.

You do not have native provider filesystem, shell, or external MCP. Auto Code
exposes a small local action loop. When run_subagents is available, it runs
bounded read-only child sessions for parallel analysis; it is not Claude SDK
Task tool parity. Respond with exactly one JSON object and no prose.

Available actions:
__AUTO_CODE_LOCAL_ACTIONS__

__AUTO_CODE_MCP_BRIDGE__

Rules:
- Use only workspace-relative paths.
- Do not touch .git, .claude, .mcp.json, .env files, shell profiles, secrets, or credential files.
- Use list_files and search_text to locate relevant files before reading them.
- Prefer apply_patch for multi-file edits. Use replace_text, move_file, delete_file,
  or write_file for small targeted file changes.
- run_command supports a single executable command, not shell pipes, redirection, or command chaining.
- Use run_subagents only for read-only exploration, review, or comparison work.
- Treat each actions array as a transaction boundary. If an observation reports partial_failure, inspect/recover before finishing.
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

You do not have provider-native filesystem, shell, or external MCP. Auto Code
exposes a small set of local tools as function calls. Use those tools to inspect
and edit the workspace. When run_subagents is available, it runs bounded
read-only child sessions for parallel analysis; it is not Claude SDK Task tool
parity. Keep iterating until the task is done, then call finish.

__AUTO_CODE_MCP_BRIDGE__

Rules:
- Use only workspace-relative paths.
- Do not touch .git, .claude, .mcp.json, .env files, shell profiles, secrets, or credential files.
- Use list_files and search_text to locate relevant files before reading them.
- Prefer apply_patch for multi-file edits. Use replace_text, move_file, delete_file,
  or write_file for small targeted file changes.
- run_command supports a single executable command, not shell pipes, redirection, or command chaining.
- Use run_subagents only for read-only exploration, review, or comparison work.
- Treat each tool-call batch as a transaction boundary. If an observation reports partial_failure, inspect/recover before finishing.
- Call finish with a concise summary, verification commands, and risks when complete.

Task:
__AUTO_CODE_TASK_PROMPT__
"""


class GenericEditRuntimeError(RuntimeError):
    """Raised when the generic edit runtime cannot continue safely."""


@dataclass
class NativeToolExecutionResult:
    """Actions executed during one native provider tool-call iteration."""

    action_results: list[ToolActionResult]
    executed_actions: list[dict[str, Any]]
    finish_action: dict[str, Any] | None = None
    finish_result: ToolActionResult | None = None
    cancelled: bool = False

    @property
    def finish_ready(self) -> bool:
        """Return true when the terminal finish action completed cleanly."""
        return (
            self.finish_action is not None
            and self.finish_result is not None
            and all(action_result.ok for action_result in self.action_results)
        )


@dataclass
class JsonActionParseResult:
    """Parsed JSON action payload or a terminal parse/validation error."""

    actions: list[dict[str, Any]]
    terminal_result: AgentRunResult | None = None


@dataclass
class JsonActionExecutionResult:
    """Local action execution state for one JSON action iteration."""

    action_results: list[ToolActionResult]
    executed_actions: list[dict[str, Any]]
    terminal_result: AgentRunResult | None = None
    cancelled: bool = False


MUTATING_LOCAL_ACTIONS = frozenset(
    {
        "write_file",
        "replace_text",
        "delete_file",
        "move_file",
        "apply_patch",
        "run_command",
    }
)
WORKSPACE_RECOVERY_TOOLS = frozenset({"git_status", "git_diff", "run_command"})
RECOVERABLE_GENERIC_EDIT_STOP_REASONS = frozenset(
    {
        "max_iterations",
        "native_tool_error",
        "non_terminal_finish",
        "parse_error",
        "unresolved_partial_failure",
    }
)


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
        agent_type: str | None = None,
        subagent_session_factory: RuntimeSessionFactory | None = None,
        max_subagent_concurrency: int = 2,
        max_subagent_task_seconds: float = 180.0,
        max_iterations: int = 8,
    ):
        self.provider_name = provider_name
        self.agent_session = agent_session
        self.agent_type = agent_type
        self._subagent_session_factory = subagent_session_factory
        self._max_subagent_concurrency = max(1, max_subagent_concurrency)
        self._max_subagent_task_seconds = max_subagent_task_seconds
        self._subagent_orchestrator: RuntimeSubagentOrchestrator | None = None
        self._subagent_run_count = 0
        self.max_iterations = max_iterations
        self._completion_runtime = CompletionRuntimeSession(
            provider_name=provider_name,
            agent_session=agent_session,
        )
        self._executor = LocalActionExecutor(project_dir)
        self._mcp_bridge: RuntimeMcpBridge | None = None
        self._cancel_requested = False

    @property
    def context_client(self) -> Any:
        return None

    async def cancel(self) -> bool:
        """Request cancellation for the generic edit loop."""
        self._cancel_requested = True
        completion_cancelled = await self._completion_runtime.cancel()
        if self._subagent_orchestrator is None:
            return completion_cancelled
        await self._subagent_orchestrator.cancel()
        return True

    async def run(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None = None,
    ) -> AgentRunResult:
        self._cancel_requested = False
        self._mcp_bridge = RuntimeMcpBridge.from_agent_session(
            agent_session=self.agent_session,
            spec_dir=spec_dir,
            project_dir=self._executor.project_dir,
            agent_type=self.agent_type,
        )

        if self._supports_native_tool_calls():
            return await self._run_native_tool_loop(
                message=message,
                spec_dir=spec_dir,
                verbose=verbose,
                phase=phase,
                subtask_id=subtask_id,
            )

        return await self._run_json_action_loop(
            message=message,
            spec_dir=spec_dir,
            verbose=verbose,
            phase=phase,
            subtask_id=subtask_id,
        )

    async def resume(
        self,
        *,
        checkpoint_path: Path,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None = None,
    ) -> AgentRunResult:
        """Resume generic_edit execution from a recovery checkpoint artifact."""
        self._cancel_requested = False
        self._mcp_bridge = RuntimeMcpBridge.from_agent_session(
            agent_session=self.agent_session,
            spec_dir=spec_dir,
            project_dir=self._executor.project_dir,
            agent_type=self.agent_type,
        )
        checkpoint = load_generic_edit_recovery_checkpoint(checkpoint_path)
        trace_path = generic_edit_trace_path_for_checkpoint(checkpoint_path)
        trace = load_generic_edit_checkpoint_trace(trace_path)
        message = build_generic_edit_checkpoint_resume_message(
            checkpoint=checkpoint,
            trace_path=trace_path,
        )
        next_iteration = checkpoint_next_iteration(checkpoint, trace)

        return await self._run_json_action_loop(
            message=message,
            spec_dir=spec_dir,
            verbose=verbose,
            phase=phase,
            subtask_id=subtask_id or checkpoint.get("subtask_id"),
            initial_trace=trace,
            start_iteration=next_iteration,
        )

    async def _run_json_action_loop(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None,
        initial_trace: list[dict[str, Any]] | None = None,
        start_iteration: int = 1,
    ) -> AgentRunResult:
        base_prompt = build_generic_edit_prompt(message, self._mcp_bridge)
        prompt = base_prompt
        trace: list[dict[str, Any]] = list(initial_trace or [])
        observation_path = initialize_generic_edit_observations(spec_dir)

        for iteration in range(start_iteration, start_iteration + self.max_iterations):
            if self._cancel_requested:
                return generic_edit_cancelled_result()
            response_text = await self._complete(prompt)
            if self._cancel_requested:
                return generic_edit_cancelled_result()
            iteration_entry = json_action_iteration_entry(iteration, response_text)
            parsed = self._parse_json_actions(
                response_text=response_text,
                iteration_entry=iteration_entry,
                trace=trace,
                spec_dir=spec_dir,
                observation_path=observation_path,
                subtask_id=subtask_id,
            )
            if parsed.terminal_result is not None:
                return parsed.terminal_result

            if not parsed.actions:
                prompt = record_json_empty_actions(
                    base_prompt=base_prompt,
                    iteration_entry=iteration_entry,
                    observation_path=observation_path,
                    provider_name=self.provider_name,
                    subtask_id=subtask_id,
                    iteration=iteration,
                )
                trace.append(iteration_entry)
                continue

            execution = await self._execute_json_action_batch(
                actions=parsed.actions,
                iteration_entry=iteration_entry,
                observation_path=observation_path,
                iteration=iteration,
                spec_dir=spec_dir,
                verbose=verbose,
                phase=phase,
                subtask_id=subtask_id,
                trace=trace,
            )
            if execution.cancelled:
                return generic_edit_cancelled_result()
            if execution.terminal_result is not None:
                return execution.terminal_result

            iteration_entry["transaction"] = build_generic_edit_transaction(
                loop="json_actions",
                iteration=iteration,
                actions=execution.executed_actions,
                results=execution.action_results,
            )
            trace.append(iteration_entry)
            prompt = build_observation_prompt(
                base_prompt=base_prompt,
                results=execution.action_results,
                transaction=iteration_entry["transaction"],
            )

        return self._max_iterations_result(
            loop_label="Generic edit runtime",
            trace=trace,
            spec_dir=spec_dir,
            observation_path=observation_path,
            subtask_id=subtask_id,
        )

    async def _run_native_tool_loop(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None,
    ) -> AgentRunResult:
        prompt: str | None = build_native_tool_edit_prompt(message, self._mcp_bridge)
        trace: list[dict[str, Any]] = []
        observation_path = initialize_generic_edit_observations(spec_dir)

        for iteration in range(1, self.max_iterations + 1):
            if self._cancel_requested:
                return generic_edit_cancelled_result()
            prompt, terminal_result = await self._run_native_tool_iteration(
                iteration=iteration,
                trace=trace,
                spec_dir=spec_dir,
                observation_path=observation_path,
                prompt=prompt,
                message=message,
                verbose=verbose,
                phase=phase,
                subtask_id=subtask_id,
            )
            if terminal_result is not None:
                return terminal_result

        return self._max_iterations_result(
            loop_label="Generic edit native tool-call loop",
            trace=trace,
            spec_dir=spec_dir,
            observation_path=observation_path,
            subtask_id=subtask_id,
        )

    def _parse_json_actions(
        self,
        *,
        response_text: str,
        iteration_entry: dict[str, Any],
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        subtask_id: str | None,
    ) -> JsonActionParseResult:
        """Parse and validate a JSON action response."""
        try:
            response = parse_generic_edit_response(response_text)
            actions = normalize_actions(response)
        except GenericEditRuntimeError as e:
            return JsonActionParseResult(
                actions=[],
                terminal_result=self._json_error_result(
                    error=e,
                    iteration_entry=iteration_entry,
                    trace=trace,
                    spec_dir=spec_dir,
                    observation_path=observation_path,
                    subtask_id=subtask_id,
                    stop_reason="parse_error",
                    summary="Generic edit runtime failed to parse provider actions.",
                    response_prefix=(
                        "Generic edit runtime failed to parse provider actions"
                    ),
                ),
            )

        try:
            validate_terminal_finish(actions)
        except GenericEditRuntimeError as e:
            return JsonActionParseResult(
                actions=[],
                terminal_result=self._json_error_result(
                    error=e,
                    iteration_entry=iteration_entry,
                    trace=trace,
                    spec_dir=spec_dir,
                    observation_path=observation_path,
                    subtask_id=subtask_id,
                    stop_reason="non_terminal_finish",
                    summary="Generic edit runtime rejected a non-terminal finish.",
                    response_prefix="Generic edit runtime rejected provider actions",
                ),
            )
        return JsonActionParseResult(actions=actions)

    def _json_error_result(
        self,
        *,
        error: GenericEditRuntimeError,
        iteration_entry: dict[str, Any],
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        subtask_id: str | None,
        stop_reason: str,
        summary: str,
        response_prefix: str,
    ) -> AgentRunResult:
        """Persist and return a JSON action loop parse/validation error."""
        iteration_entry["error"] = str(error)
        trace.append(iteration_entry)
        artifacts = save_generic_edit_artifacts(
            spec_dir=spec_dir,
            provider_name=self.provider_name,
            subtask_id=subtask_id,
            status="error",
            stop_reason=stop_reason,
            message=str(error),
            trace=trace,
            summary=summary,
            observation_path=observation_path,
            mcp_support=self._mcp_support_payload(),
        )
        return AgentRunResult(
            status="error",
            response_text=(
                f"{response_prefix}: {error}\n"
                f"Artifacts: {artifacts['generic_edit_trace']}"
            ),
        )

    async def _execute_json_action_batch(
        self,
        *,
        actions: list[dict[str, Any]],
        iteration_entry: dict[str, Any],
        observation_path: Path,
        iteration: int,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None,
        trace: list[dict[str, Any]],
    ) -> JsonActionExecutionResult:
        """Execute one JSON action batch through local action handlers."""
        execution = JsonActionExecutionResult(action_results=[], executed_actions=[])
        for action_index, action in enumerate(actions, start=1):
            if self._cancel_requested:
                execution.cancelled = True
                return execution
            result = await self._execute_action(
                action,
                spec_dir=spec_dir,
                verbose=verbose,
                phase=phase,
                subtask_id=subtask_id,
            )
            execution.executed_actions.append(action)
            execution.action_results.append(result)
            record_json_action_result(
                iteration_entry=iteration_entry,
                observation_path=observation_path,
                provider_name=self.provider_name,
                subtask_id=subtask_id,
                iteration=iteration,
                action_index=action_index,
                action=action,
                result=result,
            )
            if action_tool(action) == "finish" and all(
                action_result.ok for action_result in execution.action_results
            ):
                execution.terminal_result = self._finish_json_action_loop(
                    finish_action=action,
                    finish_result=result,
                    actions=actions,
                    action_results=execution.action_results,
                    iteration_entry=iteration_entry,
                    trace=trace,
                    spec_dir=spec_dir,
                    observation_path=observation_path,
                    iteration=iteration,
                    subtask_id=subtask_id,
                )
                return execution
            if not result.ok:
                return execution
        return execution

    def _finish_json_action_loop(
        self,
        *,
        finish_action: dict[str, Any],
        finish_result: ToolActionResult,
        actions: list[dict[str, Any]],
        action_results: list[ToolActionResult],
        iteration_entry: dict[str, Any],
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        iteration: int,
        subtask_id: str | None,
    ) -> AgentRunResult:
        """Persist and return a successful JSON action finish."""
        summary = str(finish_action.get("summary") or finish_result.message)
        tests = normalize_string_list(finish_action.get("tests"))
        risks = normalize_string_list(finish_action.get("risks"))
        iteration_entry["transaction"] = build_generic_edit_transaction(
            loop="json_actions",
            iteration=iteration,
            actions=actions,
            results=action_results,
        )
        finish_trace = [*trace, iteration_entry]
        if has_unresolved_partial_failure(finish_trace):
            return self._unresolved_partial_failure_finish_result(
                trace=finish_trace,
                spec_dir=spec_dir,
                observation_path=observation_path,
                subtask_id=subtask_id,
            )
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
            observation_path=observation_path,
            mcp_support=self._mcp_support_payload(),
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

    async def _run_native_tool_iteration(
        self,
        *,
        iteration: int,
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        prompt: str | None,
        message: str,
        verbose: bool,
        phase: Any,
        subtask_id: str | None,
    ) -> tuple[str | None, AgentRunResult | None]:
        """Run one provider-native tool-call iteration."""
        iteration_entry = native_tool_iteration_entry(iteration)
        response, terminal_result = await self._complete_native_tool_iteration(
            prompt=prompt,
            iteration=iteration,
            iteration_entry=iteration_entry,
            trace=trace,
            spec_dir=spec_dir,
            observation_path=observation_path,
            message=message,
            verbose=verbose,
            phase=phase,
            subtask_id=subtask_id,
        )
        if terminal_result is not None:
            return prompt, terminal_result

        response_content = str(getattr(response, "content", "") or "")
        tool_calls = tuple(getattr(response, "tool_calls", ()) or ())
        iteration_entry["response_excerpt"] = response_content[:1000]
        iteration_entry["response_bytes"] = len(response_content.encode("utf-8"))

        if not tool_calls:
            next_prompt = record_native_empty_tool_response(
                iteration_entry=iteration_entry,
                observation_path=observation_path,
                provider_name=self.provider_name,
                subtask_id=subtask_id,
                iteration=iteration,
            )
            trace.append(iteration_entry)
            return next_prompt, None

        return await self._run_native_tool_actions(
            tool_calls=tool_calls,
            iteration_entry=iteration_entry,
            trace=trace,
            spec_dir=spec_dir,
            observation_path=observation_path,
            iteration=iteration,
            verbose=verbose,
            phase=phase,
            subtask_id=subtask_id,
        )

    async def _run_native_tool_actions(
        self,
        *,
        tool_calls: tuple[Any, ...],
        iteration_entry: dict[str, Any],
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        iteration: int,
        verbose: bool,
        phase: Any,
        subtask_id: str | None,
    ) -> tuple[str | None, AgentRunResult | None]:
        """Validate and execute one native tool-call batch."""
        tool_actions = build_native_tool_actions(tool_calls)
        terminal_result = self._reject_invalid_native_tool_batch(
            tool_actions=tool_actions,
            iteration_entry=iteration_entry,
            trace=trace,
            spec_dir=spec_dir,
            observation_path=observation_path,
            subtask_id=subtask_id,
        )
        if terminal_result is not None:
            return None, terminal_result

        execution = await self._execute_native_tool_actions(
            tool_actions=tool_actions,
            iteration_entry=iteration_entry,
            observation_path=observation_path,
            iteration=iteration,
            spec_dir=spec_dir,
            verbose=verbose,
            phase=phase,
            subtask_id=subtask_id,
        )
        if execution.cancelled:
            return None, generic_edit_cancelled_result()
        if execution.finish_ready:
            terminal_result = self._finish_native_tool_loop(
                finish_action=execution.finish_action or {},
                finish_result=execution.finish_result,
                tool_actions=tool_actions,
                action_results=execution.action_results,
                iteration_entry=iteration_entry,
                trace=trace,
                spec_dir=spec_dir,
                observation_path=observation_path,
                iteration=iteration,
                subtask_id=subtask_id,
            )
            return None, terminal_result

        iteration_entry["transaction"] = build_generic_edit_transaction(
            loop="native_tool_calls",
            iteration=iteration,
            actions=execution.executed_actions,
            results=execution.action_results,
        )
        trace.append(iteration_entry)
        return build_native_recovery_prompt(iteration_entry["transaction"]), None

    def _max_iterations_result(
        self,
        *,
        loop_label: str,
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        subtask_id: str | None,
    ) -> AgentRunResult:
        """Persist and return a max-iterations failure."""
        message = (
            f"{loop_label} reached max iterations ({self.max_iterations}) "
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
            observation_path=observation_path,
            mcp_support=self._mcp_support_payload(),
        )
        return AgentRunResult(
            status="error",
            response_text=f"{message}\nArtifacts: {artifacts['generic_edit_trace']}",
        )

    async def _complete_native_tool_iteration(
        self,
        *,
        prompt: str | None,
        iteration: int,
        iteration_entry: dict[str, Any],
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        message: str,
        verbose: bool,
        phase: Any,
        subtask_id: str | None,
    ) -> tuple[Any, AgentRunResult | None]:
        """Request one native tool-call response or return a terminal result."""
        try:
            response = await self.agent_session.complete_with_tool_calls(
                prompt,
                self._provider_tool_schemas(),
            )
        except Exception as e:
            if (
                iteration == 1
                and callable(getattr(self.agent_session, "complete", None))
                and should_fallback_from_native_tools(e)
            ):
                fallback = await self._run_json_action_loop(
                    message=message,
                    spec_dir=spec_dir,
                    verbose=verbose,
                    phase=phase,
                    subtask_id=subtask_id,
                    initial_trace=[
                        native_tool_fallback_trace_entry(
                            provider_name=self.provider_name,
                            iteration=iteration,
                            error=e,
                            tool_schema_count=len(self._provider_tool_schemas()),
                        )
                    ],
                )
                return None, fallback
            return None, self._native_tool_error_result(
                error=e,
                iteration_entry=iteration_entry,
                trace=trace,
                spec_dir=spec_dir,
                observation_path=observation_path,
                subtask_id=subtask_id,
            )

        if self._cancel_requested:
            return None, generic_edit_cancelled_result()
        return response, None

    def _native_tool_error_result(
        self,
        *,
        error: Exception,
        iteration_entry: dict[str, Any],
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        subtask_id: str | None,
    ) -> AgentRunResult:
        """Persist and return a native tool-call request failure."""
        iteration_entry["error"] = str(error)
        trace.append(iteration_entry)
        artifacts = save_generic_edit_artifacts(
            spec_dir=spec_dir,
            provider_name=self.provider_name,
            subtask_id=subtask_id,
            status="error",
            stop_reason="native_tool_error",
            message=str(error),
            trace=trace,
            summary="Generic edit native tool-call loop failed.",
            observation_path=observation_path,
            mcp_support=self._mcp_support_payload(),
        )
        return AgentRunResult(
            status="error",
            response_text=(
                f"Generic edit native tool-call loop failed: {error}\n"
                f"Artifacts: {artifacts['generic_edit_trace']}"
            ),
        )

    def _reject_invalid_native_tool_batch(
        self,
        *,
        tool_actions: list[tuple[Any, dict[str, Any]]],
        iteration_entry: dict[str, Any],
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        subtask_id: str | None,
    ) -> AgentRunResult | None:
        """Reject provider tool-call batches that violate finish ordering."""
        try:
            validate_terminal_finish([action for _, action in tool_actions])
        except GenericEditRuntimeError as e:
            iteration_entry["error"] = str(e)
            trace.append(iteration_entry)
            artifacts = save_generic_edit_artifacts(
                spec_dir=spec_dir,
                provider_name=self.provider_name,
                subtask_id=subtask_id,
                status="error",
                stop_reason="non_terminal_finish",
                message=str(e),
                trace=trace,
                summary="Generic edit runtime rejected a non-terminal finish.",
                observation_path=observation_path,
                mcp_support=self._mcp_support_payload(),
            )
            return AgentRunResult(
                status="error",
                response_text=(
                    f"Generic edit runtime rejected provider tool calls: {e}\n"
                    f"Artifacts: {artifacts['generic_edit_trace']}"
                ),
            )
        return None

    async def _execute_native_tool_actions(
        self,
        *,
        tool_actions: list[tuple[Any, dict[str, Any]]],
        iteration_entry: dict[str, Any],
        observation_path: Path,
        iteration: int,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None,
    ) -> NativeToolExecutionResult:
        """Execute provider-native tool calls through local action handlers."""
        execution = NativeToolExecutionResult(
            action_results=[],
            executed_actions=[],
        )
        for action_index, (tool_call, action) in enumerate(tool_actions, start=1):
            if self._cancel_requested:
                execution.cancelled = True
                return execution
            result = await self._execute_action(
                action,
                spec_dir=spec_dir,
                verbose=verbose,
                phase=phase,
                subtask_id=subtask_id,
            )
            execution.executed_actions.append(action)
            execution.action_results.append(result)
            safe_request = {
                "tool_call_id": str(getattr(tool_call, "id", "") or ""),
                **safe_action_for_trace(action),
            }
            iteration_entry["actions"].append(
                {
                    "request": safe_request,
                    "result": safe_result_for_trace(result),
                }
            )
            append_generic_edit_observation(
                observation_path=observation_path,
                provider_name=self.provider_name,
                subtask_id=subtask_id,
                loop="native_tool_calls",
                iteration=iteration,
                action_index=action_index,
                request=safe_request,
                result=result,
            )
            self.agent_session.add_tool_result(
                str(getattr(tool_call, "id", "") or ""),
                action_tool(action),
                result.to_dict(),
            )
            if action_tool(action) == "finish":
                execution.finish_action = action
                execution.finish_result = result
            if not result.ok:
                return execution
        return execution

    def _finish_native_tool_loop(
        self,
        *,
        finish_action: dict[str, Any],
        finish_result: ToolActionResult | None,
        tool_actions: list[tuple[Any, dict[str, Any]]],
        action_results: list[ToolActionResult],
        iteration_entry: dict[str, Any],
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        iteration: int,
        subtask_id: str | None,
    ) -> AgentRunResult:
        """Persist and return a successful native tool-call finish."""
        finish_message = finish_result.message if finish_result else "Finished"
        summary = str(finish_action.get("summary") or finish_message)
        tests = normalize_string_list(finish_action.get("tests"))
        risks = normalize_string_list(finish_action.get("risks"))
        iteration_entry["transaction"] = build_generic_edit_transaction(
            loop="native_tool_calls",
            iteration=iteration,
            actions=[action for _, action in tool_actions],
            results=action_results,
        )
        finish_trace = [*trace, iteration_entry]
        if has_unresolved_partial_failure(finish_trace):
            return self._unresolved_partial_failure_finish_result(
                trace=finish_trace,
                spec_dir=spec_dir,
                observation_path=observation_path,
                subtask_id=subtask_id,
            )
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
            observation_path=observation_path,
            mcp_support=self._mcp_support_payload(),
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

    def _unresolved_partial_failure_finish_result(
        self,
        *,
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        subtask_id: str | None,
    ) -> AgentRunResult:
        """Reject finish when an earlier partial mutation has not been recovered."""
        transaction_summary = summarize_generic_edit_transactions(trace)
        unresolved_ids = transaction_summary["unresolved_partial_failure_ids"]
        message = (
            "Generic edit runtime rejected finish because partial-failure "
            f"transaction(s) remain unresolved: {', '.join(unresolved_ids)}."
        )
        artifacts = save_generic_edit_artifacts(
            spec_dir=spec_dir,
            provider_name=self.provider_name,
            subtask_id=subtask_id,
            status="error",
            stop_reason="unresolved_partial_failure",
            message=message,
            trace=trace,
            summary=message,
            observation_path=observation_path,
            mcp_support=self._mcp_support_payload(),
        )
        return AgentRunResult(
            status="error",
            response_text=f"{message}\nArtifacts: {artifacts['generic_edit_trace']}",
        )

    def _supports_native_tool_calls(self) -> bool:
        return callable(
            getattr(self.agent_session, "complete_with_tool_calls", None)
        ) and callable(getattr(self.agent_session, "add_tool_result", None))

    def _provider_tool_schemas(self) -> list[dict[str, Any]]:
        schemas = local_action_tool_schemas()
        if self._mcp_bridge is not None:
            schemas.extend(self._mcp_bridge.provider_tool_schemas())
        return schemas

    async def _execute_action(
        self,
        action: dict[str, Any],
        *,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None,
    ) -> ToolActionResult:
        if action_tool(action) == "run_subagents":
            return await self._run_subagents_action(
                action,
                spec_dir=spec_dir,
                verbose=verbose,
                phase=phase,
                subtask_id=subtask_id,
            )
        if self._mcp_bridge is not None and self._mcp_bridge.can_execute(action):
            return await self._mcp_bridge.execute(action)
        if is_mcp_action_name(action_tool(action)):
            return unavailable_mcp_action_result(
                action,
                support=self._mcp_support_payload(),
            )
        return await self._executor.execute(action)

    async def _run_subagents_action(
        self,
        action: dict[str, Any],
        *,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None,
    ) -> ToolActionResult:
        if self._subagent_session_factory is None:
            return ToolActionResult(
                tool="run_subagents",
                ok=False,
                message=(
                    "Runtime subagents are not configured for this generic_edit "
                    "session."
                ),
            )

        try:
            tasks = parse_runtime_subagent_action_tasks(action, subtask_id=subtask_id)
        except GenericEditRuntimeError as e:
            return ToolActionResult(
                tool="run_subagents",
                ok=False,
                message=str(e),
            )

        self._subagent_run_count += 1
        orchestrator = RuntimeSubagentOrchestrator(
            session_factory=self._subagent_session_factory,
            spec_dir=spec_dir,
            max_concurrency=self._max_subagent_concurrency,
            max_task_seconds=self._max_subagent_task_seconds,
        )
        support = orchestrator.support_for(
            provider_name=self.provider_name,
            runtime_name=self.name,
            capabilities=self.capabilities,
            child_requirements=RuntimeRequirements.text_only(mode="subagent"),
        )
        if not support.available:
            return ToolActionResult(
                tool="run_subagents",
                ok=False,
                message=support.reason,
                data={"support": support.to_dict()},
            )

        self._subagent_orchestrator = orchestrator
        try:
            run = await orchestrator.run(
                tasks,
                verbose=verbose,
                phase=phase,
                artifact_name=generic_edit_subagent_artifact_name(
                    subtask_id=subtask_id,
                    run_count=self._subagent_run_count,
                ),
                support=support,
            )
        finally:
            self._subagent_orchestrator = None

        run_payload = run.to_dict()
        return ToolActionResult(
            tool="run_subagents",
            ok=run.status in {"complete", "continue"},
            message=(
                f"Runtime subagents finished with status {run.status} "
                f"({len(run.results)} task(s))."
            ),
            data={
                "status": run.status,
                "artifact_path": run.artifact_path,
                "cancelled": run.cancelled,
                "support": run_payload["support"],
                "summary": run_payload["summary"],
                "results": [
                    {
                        "id": result.id,
                        "role": result.role,
                        "status": result.status,
                        "attempt_count": result.attempt_count,
                        "max_attempts": result.max_attempts,
                        "merge_policy": result.merge_policy,
                        "artifact_path": result.artifact_path,
                        "response_text": result.response_text[
                            :MAX_SUBAGENT_RESULT_CHARS
                        ],
                        "truncated": (
                            len(result.response_text) > MAX_SUBAGENT_RESULT_CHARS
                        ),
                        "error": result.error,
                    }
                    for result in run.results
                ],
            },
        )

    def _mcp_support_payload(self) -> dict[str, Any]:
        """Return runtime MCP support metadata for generic edit artifacts."""
        if self._mcp_bridge is not None:
            support = self._mcp_bridge.support_for(
                provider_name=self.provider_name,
                runtime_name=self.name,
                capabilities=self.capabilities,
            )
            payload = support.to_dict()
            payload["bridge"] = self._mcp_bridge.report()
            return payload

        return resolve_runtime_mcp_support(
            provider_name=self.provider_name,
            runtime_name=self.name,
            capabilities=self.capabilities,
        ).to_dict()

    async def _complete(self, message: str) -> str:
        chunks: list[str] = []
        async for chunk in self._completion_runtime._stream_text(message):
            chunks.append(chunk)
        return "".join(chunks)


def generic_edit_cancelled_result() -> AgentRunResult:
    """Return the standard generic_edit cancellation result."""
    return AgentRunResult(
        status="cancelled",
        response_text=GENERIC_EDIT_CANCELLED_MESSAGE,
    )


def native_tool_iteration_entry(iteration: int) -> dict[str, Any]:
    """Return the trace scaffold for one native tool-call iteration."""
    return {
        "iteration": iteration,
        "loop": "native_tool_calls",
        "response_excerpt": "",
        "response_bytes": 0,
        "actions": [],
    }


def native_tool_fallback_trace_entry(
    *,
    provider_name: str,
    iteration: int,
    error: Exception,
    tool_schema_count: int,
) -> dict[str, Any]:
    """Return trace metadata when provider-native tools fall back to JSON."""
    error_message = str(error)
    return {
        "iteration": iteration,
        "loop": "native_tool_calls",
        "error": error_message,
        "native_tool_fallback": {
            "provider": provider_name,
            "from_loop": "native_tool_calls",
            "to_loop": "json_actions",
            "reason": "native_tool_request_failed",
            "message": error_message,
            "tool_schema_count": tool_schema_count,
        },
        "actions": [],
    }


NATIVE_TOOL_FATAL_ERROR_MARKERS = (
    "api key",
    "authentication",
    "auth",
    "billing",
    "connection",
    "dns",
    "forbidden",
    "insufficient_quota",
    "invalid key",
    "model not found",
    "permission denied",
    "proxy",
    "quota",
    "rate limit",
    "timed out",
    "timeout",
    "unauthorized",
)
NATIVE_TOOL_FALLBACK_ERROR_MARKERS = (
    "does not support tools",
    "function",
    "invalid tool",
    "json schema",
    "parameters",
    "schema",
    "tool",
    "tool_choice",
    "unsupported tool",
)


def should_fallback_from_native_tools(error: Exception) -> bool:
    """Return true when native tools failed because the model rejected tools."""
    if isinstance(error, (ProviderConfigError, ProviderNotInstalled)):
        return False

    error_text = native_tool_error_text(error)
    if any(marker in error_text for marker in NATIVE_TOOL_FATAL_ERROR_MARKERS):
        return False
    return any(marker in error_text for marker in NATIVE_TOOL_FALLBACK_ERROR_MARKERS)


def native_tool_error_text(error: Exception) -> str:
    """Return a lower-case error chain string for native-tool classification."""
    parts: list[str] = []
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(str(current))
        current = current.__cause__ or current.__context__
    return " ".join(parts).lower()


def json_action_iteration_entry(iteration: int, response_text: str) -> dict[str, Any]:
    """Return the trace scaffold for one JSON action iteration."""
    return {
        "iteration": iteration,
        "loop": "json_actions",
        "response_excerpt": response_text[:1000],
        "response_bytes": len(response_text.encode("utf-8")),
        "actions": [],
    }


def record_json_empty_actions(
    *,
    base_prompt: str,
    iteration_entry: dict[str, Any],
    observation_path: Path,
    provider_name: str,
    subtask_id: str | None,
    iteration: int,
) -> str:
    """Record and prompt for a JSON action response that had no actions."""
    result = ToolActionResult(
        tool="runtime",
        ok=False,
        message="No actions returned; return at least one action.",
    )
    iteration_entry["actions"].append(safe_result_for_trace(result))
    append_generic_edit_observation(
        observation_path=observation_path,
        provider_name=provider_name,
        subtask_id=subtask_id,
        loop="json_actions",
        iteration=iteration,
        action_index=1,
        request={},
        result=result,
    )
    return build_observation_prompt(
        base_prompt=base_prompt,
        results=[result],
    )


def record_json_action_result(
    *,
    iteration_entry: dict[str, Any],
    observation_path: Path,
    provider_name: str,
    subtask_id: str | None,
    iteration: int,
    action_index: int,
    action: dict[str, Any],
    result: ToolActionResult,
) -> None:
    """Record one JSON local action result in trace and observation artifacts."""
    safe_request = safe_action_for_trace(action)
    iteration_entry["actions"].append(
        {
            "request": safe_request,
            "result": safe_result_for_trace(result),
        }
    )
    append_generic_edit_observation(
        observation_path=observation_path,
        provider_name=provider_name,
        subtask_id=subtask_id,
        loop="json_actions",
        iteration=iteration,
        action_index=action_index,
        request=safe_request,
        result=result,
    )


def record_native_empty_tool_response(
    *,
    iteration_entry: dict[str, Any],
    observation_path: Path,
    provider_name: str,
    subtask_id: str | None,
    iteration: int,
) -> str:
    """Record a native provider response that did not include tool calls."""
    result = ToolActionResult(
        tool="runtime",
        ok=False,
        message=(
            "No local tool calls returned; call at least one local tool or finish."
        ),
    )
    iteration_entry["actions"].append(safe_result_for_trace(result))
    append_generic_edit_observation(
        observation_path=observation_path,
        provider_name=provider_name,
        subtask_id=subtask_id,
        loop="native_tool_calls",
        iteration=iteration,
        action_index=1,
        request={},
        result=result,
    )
    return (
        "No local tool calls were returned. Continue the task by calling one or "
        "more local tools, or call finish when complete."
    )


def build_native_tool_actions(
    tool_calls: tuple[Any, ...],
) -> list[tuple[Any, dict[str, Any]]]:
    """Convert provider-native tool call objects into local action payloads."""
    return [
        (
            tool_call,
            {
                "tool": str(getattr(tool_call, "name", "") or ""),
                **dict(getattr(tool_call, "arguments", {}) or {}),
            },
        )
        for tool_call in tool_calls
    ]


def build_generic_edit_prompt(
    message: str,
    mcp_bridge: RuntimeMcpBridge | None = None,
) -> str:
    """Build the generic_edit prompt from the shared local action manifest."""
    return (
        GENERIC_EDIT_PROMPT_TEMPLATE.replace(
            "__AUTO_CODE_LOCAL_ACTIONS__",
            render_local_action_prompt(),
        )
        .replace(
            "__AUTO_CODE_MCP_BRIDGE__",
            render_mcp_bridge_prompt(mcp_bridge),
        )
        .replace(
            "__AUTO_CODE_TASK_PROMPT__",
            message,
        )
    )


def build_native_tool_edit_prompt(
    message: str,
    mcp_bridge: RuntimeMcpBridge | None = None,
) -> str:
    """Build the generic_edit prompt for provider-native tool-call sessions."""
    return NATIVE_TOOL_PROMPT_TEMPLATE.replace(
        "__AUTO_CODE_MCP_BRIDGE__",
        render_mcp_bridge_prompt(mcp_bridge),
    ).replace(
        "__AUTO_CODE_TASK_PROMPT__",
        message,
    )


def render_mcp_bridge_prompt(mcp_bridge: RuntimeMcpBridge | None) -> str:
    """Render bridged local MCP actions for the generic edit prompt."""
    if mcp_bridge is None:
        return (
            "Bridged MCP actions: none. External MCP servers such as Context7, "
            "Graphiti, Linear, Electron, and Puppeteer are not available in "
            "generic_edit mode."
        )
    if not mcp_bridge.has_tools:
        unavailable = ", ".join(mcp_bridge.unavailable_servers) or "none"
        return (
            "Bridged MCP actions: none. Requested MCP servers unavailable in "
            f"generic_edit mode: {unavailable}."
        )

    lines = [
        "Bridged MCP actions available through the generic edit runtime:",
        *mcp_bridge.prompt_lines(),
    ]
    if mcp_bridge.unavailable_servers:
        lines.append(
            "Unavailable external MCP servers in generic_edit mode: "
            + ", ".join(mcp_bridge.unavailable_servers)
        )
    return "\n".join(lines)


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


def validate_terminal_finish(actions: list[dict[str, Any]]) -> None:
    """Reject action batches where finish is followed by another action."""
    for index, action in enumerate(actions[:-1]):
        if action_tool(action) != "finish":
            continue
        if any(action_tool(later_action) for later_action in actions[index + 1 :]):
            raise GenericEditRuntimeError(
                "Generic edit action 'finish' must be the final action"
            )


def parse_runtime_subagent_action_tasks(
    action: dict[str, Any],
    *,
    subtask_id: str | None,
) -> list[RuntimeSubagentTask]:
    """Parse a run_subagents local action into bounded read-only child tasks."""
    raw_tasks = action.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise GenericEditRuntimeError("run_subagents field 'tasks' must be a list")
    if len(raw_tasks) > MAX_SUBAGENT_TASKS:
        raise GenericEditRuntimeError(
            f"run_subagents supports at most {MAX_SUBAGENT_TASKS} tasks"
        )

    tasks: list[RuntimeSubagentTask] = []
    for index, raw_task in enumerate(raw_tasks, start=1):
        if not isinstance(raw_task, dict):
            raise GenericEditRuntimeError(
                f"run_subagents task #{index} must be an object"
            )
        tasks.append(parse_runtime_subagent_action_task(raw_task, index, subtask_id))
    return tasks


def parse_runtime_subagent_action_task(
    raw_task: dict[str, Any],
    index: int,
    subtask_id: str | None,
) -> RuntimeSubagentTask:
    """Parse one run_subagents task payload."""
    task_id = bounded_subagent_string(
        raw_task.get("id") or f"subagent-{index}",
        field_name=f"tasks[{index}].id",
        maximum=MAX_SUBAGENT_ID_CHARS,
    )
    prompt = bounded_subagent_string(
        raw_task.get("prompt"),
        field_name=f"tasks[{index}].prompt",
        maximum=MAX_SUBAGENT_PROMPT_CHARS,
    )
    role = bounded_subagent_string(
        raw_task.get("role") or "worker",
        field_name=f"tasks[{index}].role",
        maximum=MAX_SUBAGENT_ROLE_CHARS,
    )
    metadata = raw_task.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise GenericEditRuntimeError(
            f"run_subagents task #{index} field 'metadata' must be an object"
        )
    context = raw_task.get("context") or {}
    if not isinstance(context, dict):
        raise GenericEditRuntimeError(
            f"run_subagents task #{index} field 'context' must be an object"
        )
    merge_policy = bounded_subagent_string(
        raw_task.get("merge_policy") or DEFAULT_SUBAGENT_MERGE_POLICY,
        field_name=f"tasks[{index}].merge_policy",
        maximum=40,
    )
    if merge_policy != DEFAULT_SUBAGENT_MERGE_POLICY:
        raise GenericEditRuntimeError(
            "run_subagents currently supports only read_only child merge policy"
        )
    max_attempts = bounded_subagent_attempts(
        raw_task.get("max_attempts", 1),
        field_name=f"tasks[{index}].max_attempts",
    )
    return RuntimeSubagentTask(
        id=task_id,
        role=role,
        prompt=prompt,
        requirements=RuntimeRequirements.text_only(mode="subagent"),
        subtask_id=subtask_id,
        metadata=metadata,
        context=context,
        merge_policy=merge_policy,
        max_attempts=max_attempts,
    )


def bounded_subagent_string(value: Any, *, field_name: str, maximum: int) -> str:
    """Read a required bounded run_subagents string field."""
    if not isinstance(value, str) or not value.strip():
        raise GenericEditRuntimeError(
            f"run_subagents field '{field_name}' must be a non-empty string"
        )
    stripped = value.strip()
    if len(stripped) > maximum:
        raise GenericEditRuntimeError(
            f"run_subagents field '{field_name}' must be at most {maximum} characters"
        )
    return stripped


def bounded_subagent_attempts(value: Any, *, field_name: str) -> int:
    """Read a bounded run_subagents retry count."""
    if type(value) is not int:
        raise GenericEditRuntimeError(
            f"run_subagents field '{field_name}' must be an integer"
        )
    if value < 1 or value > MAX_SUBAGENT_ATTEMPTS:
        raise GenericEditRuntimeError(
            "run_subagents field "
            f"'{field_name}' must be between 1 and {MAX_SUBAGENT_ATTEMPTS}"
        )
    return value


def generic_edit_subagent_artifact_name(
    *,
    subtask_id: str | None,
    run_count: int,
) -> str:
    """Return a stable artifact filename for one generic_edit subagent run."""
    raw_scope = subtask_id or "session"
    scope = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_" for char in raw_scope
    )
    return f"generic_edit_subagents_{scope}_{run_count}.json"


def build_observation_prompt(
    *,
    base_prompt: str,
    results: list[ToolActionResult],
    transaction: dict[str, Any] | None = None,
) -> str:
    """Build the next user message containing local action observations."""
    payload = {
        "observations": [result.to_dict() for result in results],
        "instruction": (
            "Continue the task. Return exactly one JSON object with actions. "
            "Use finish when complete."
        ),
    }
    if transaction is not None:
        payload["transaction"] = transaction
        if transaction.get("recovery_required"):
            payload["instruction"] = (
                "A previous action transaction partially failed. Inspect the "
                "workspace as needed, repair or account for partial changes, "
                "then continue. Return exactly one JSON object with actions. "
                "Use finish only when the workspace is consistent."
            )
    return (
        base_prompt.rstrip()
        + "\n\n## Local Action Observations\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def build_native_recovery_prompt(transaction: dict[str, Any]) -> str | None:
    """Return a next-turn prompt only when native tool execution needs recovery."""
    if not transaction.get("recovery_required"):
        return None
    return (
        "The previous local tool-call transaction partially failed. Inspect the "
        "workspace as needed, repair or account for partial changes, then continue. "
        "Call finish only when the workspace is consistent.\n\n"
        + json.dumps({"transaction": transaction}, ensure_ascii=False, indent=2)
    )


def build_generic_edit_transaction(
    *,
    loop: str,
    iteration: int,
    actions: list[dict[str, Any]],
    results: list[ToolActionResult],
) -> dict[str, Any]:
    """Build one transaction-boundary summary for a local action batch."""
    succeeded_count = sum(1 for result in results if result.ok)
    failed_count = sum(1 for result in results if not result.ok)
    tool_sequence = [action_tool(action) for action in actions if action_tool(action)]
    mutating_tools = [
        action_tool(action)
        for action in actions
        if action_tool(action) in MUTATING_LOCAL_ACTIONS
    ]
    affected_paths = sorted(
        dict.fromkeys(path for action in actions for path in action_path_values(action))
    )
    mutated_paths = sorted(
        dict.fromkeys(
            path
            for action in actions
            if action_tool(action) in MUTATING_LOCAL_ACTIONS
            for path in action_path_values(action)
        )
    )
    first_failure_index = next(
        (index for index, result in enumerate(results, start=1) if not result.ok),
        None,
    )
    partial_mutation = False
    if first_failure_index is not None:
        partial_mutation = any(
            result.ok and action_tool(action) in MUTATING_LOCAL_ACTIONS
            for action, result in zip(
                actions[: first_failure_index - 1],
                results[: first_failure_index - 1],
                strict=False,
            )
        )

    if failed_count == 0:
        status = "complete"
    elif partial_mutation:
        status = "partial_failure"
    else:
        status = "failed"

    transaction: dict[str, Any] = {
        "id": f"{loop}-{iteration}",
        "loop": loop,
        "iteration": iteration,
        "status": status,
        "action_count": len(actions),
        "tool_sequence": tool_sequence,
        "succeeded_action_count": succeeded_count,
        "failed_action_count": failed_count,
        "mutating_action_count": len(mutating_tools),
        "mutating_tools": mutating_tools,
        "affected_paths": affected_paths,
        "mutated_paths": mutated_paths,
        "recovery_required": status == "partial_failure",
        "can_resolve_partial_failure": transaction_can_resolve_partial_failure(
            status=status,
            tool_sequence=tool_sequence,
        ),
    }
    if first_failure_index is not None:
        failed_result = results[first_failure_index - 1]
        transaction.update(
            {
                "failed_at_action_index": first_failure_index,
                "failed_tool": failed_result.tool,
                "failure_message": failed_result.message,
            }
        )
    if transaction["recovery_required"]:
        transaction["recovery_message"] = (
            "At least one mutating action succeeded before a later action failed. "
            "Inspect affected paths and repair or confirm the workspace state before finishing."
        )
    return transaction


def action_path_values(action: dict[str, Any]) -> list[str]:
    """Return workspace path fields from an action without reading sensitive data."""
    paths: list[str] = []
    for field_name in ("path", "source", "destination"):
        value = action.get(field_name)
        if isinstance(value, str) and value:
            paths.append(value)
    raw_paths = action.get("paths")
    if isinstance(raw_paths, list):
        paths.extend(path for path in raw_paths if isinstance(path, str) and path)
    return paths


def transaction_can_resolve_partial_failure(
    *,
    status: str,
    tool_sequence: list[str],
) -> bool:
    """Return true when a later transaction can credibly resolve partial edits."""
    if status != "complete":
        return False
    return any(tool and tool != "finish" for tool in tool_sequence)


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


def initialize_generic_edit_observations(spec_dir: Path) -> Path:
    """Create the safe JSONL observation stream for the current generic edit run."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    observation_path = artifact_dir / "generic_edit_observations.jsonl"
    observation_path.write_text("", encoding="utf-8")
    return observation_path


def append_generic_edit_observation(
    *,
    observation_path: Path,
    provider_name: str,
    subtask_id: str | None,
    loop: str,
    iteration: int,
    action_index: int,
    request: dict[str, Any],
    result: ToolActionResult,
) -> None:
    """Append one redacted local action observation for UI/debug consumers."""
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "provider": provider_name,
        "subtask_id": subtask_id,
        "loop": loop,
        "iteration": iteration,
        "action_index": action_index,
        "request": request,
        "result": safe_result_for_trace(result),
    }
    with observation_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False))
        handle.write("\n")


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
    observation_path: Path | None = None,
    mcp_support: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Persist trace/result artifacts for a generic edit run."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    paths = generic_edit_artifact_paths(artifact_dir)
    timestamp = datetime.now(UTC).isoformat()
    trace_summary = summarize_generic_edit_trace(trace)
    transaction_summary = summarize_generic_edit_transactions(trace)
    recovery_checkpoint = build_generic_edit_recovery_checkpoint(
        timestamp=timestamp,
        provider_name=provider_name,
        subtask_id=subtask_id,
        status=status,
        stop_reason=stop_reason,
        message=message,
        next_iteration=len(trace) + 1,
        trace_summary=trace_summary,
        transaction_summary=transaction_summary,
        trace_path=paths["trace"],
        observation_path=observation_path,
        checkpoint_path=paths["recovery_checkpoint"],
        mcp_support=mcp_support,
    )

    write_json_artifact(
        paths["trace"],
        {
            "timestamp": timestamp,
            "provider": provider_name,
            "subtask_id": subtask_id,
            "status": status,
            "stop_reason": stop_reason,
            "message": message,
            "mcp_support": mcp_support,
            "trace": trace,
        },
    )
    write_json_artifact(
        paths["timeline"],
        {
            "timestamp": timestamp,
            "provider": provider_name,
            "subtask_id": subtask_id,
            "status": status,
            "stop_reason": stop_reason,
            "mcp_support": mcp_support,
            "timeline": trace_summary["action_timeline"],
        },
    )
    result_payload = build_generic_edit_result_payload(
        timestamp=timestamp,
        provider_name=provider_name,
        subtask_id=subtask_id,
        status=status,
        stop_reason=stop_reason,
        message=message,
        trace=trace,
        trace_summary=trace_summary,
        transaction_summary=transaction_summary,
        tests=tests,
        risks=risks,
        mcp_support=mcp_support,
        recovery_checkpoint=recovery_checkpoint,
    )
    if observation_path is not None:
        result_payload["observation_artifact"] = str(observation_path)
    if recovery_checkpoint is not None:
        write_json_artifact(paths["recovery_checkpoint"], recovery_checkpoint)
    else:
        clear_generic_edit_recovery_checkpoint(paths["recovery_checkpoint"])
    write_json_artifact(paths["result"], result_payload)
    write_generic_edit_transactions(paths["transactions"], transaction_summary)
    paths["summary"].write_text(
        build_generic_edit_summary_markdown(
            provider_name=provider_name,
            subtask_id=subtask_id,
            status=status,
            stop_reason=stop_reason,
            summary=summary,
            trace_summary=trace_summary,
            transaction_summary=transaction_summary,
            tests=tests,
            risks=risks,
            mcp_support=mcp_support,
            recovery_checkpoint=recovery_checkpoint,
        ),
        encoding="utf-8",
    )

    artifacts = generic_edit_artifact_payload(paths)
    if observation_path is not None:
        artifacts["generic_edit_observations"] = str(observation_path)
    if recovery_checkpoint is not None:
        artifacts["generic_edit_recovery_checkpoint"] = str(
            paths["recovery_checkpoint"]
        )
    return artifacts


def generic_edit_artifact_paths(artifact_dir: Path) -> dict[str, Path]:
    return {
        "trace": artifact_dir / "generic_edit_trace.json",
        "timeline": artifact_dir / "generic_edit_timeline.json",
        "transactions": artifact_dir / "generic_edit_transactions.jsonl",
        "recovery_checkpoint": artifact_dir / "generic_edit_recovery_checkpoint.json",
        "summary": artifact_dir / "generic_edit_summary.md",
        "result": artifact_dir / "generic_edit_result.json",
    }


def write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def clear_generic_edit_recovery_checkpoint(path: Path) -> None:
    """Remove stale recovery checkpoint artifacts after a non-recoverable finish."""
    try:
        path.unlink()
    except FileNotFoundError:
        return


def build_generic_edit_result_payload(
    *,
    timestamp: str,
    provider_name: str,
    subtask_id: str | None,
    status: str,
    stop_reason: str,
    message: str,
    trace: list[dict[str, Any]],
    trace_summary: dict[str, Any],
    transaction_summary: dict[str, Any],
    tests: list[str] | None,
    risks: list[str] | None,
    mcp_support: dict[str, Any] | None,
    recovery_checkpoint: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = {
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "stop_reason": stop_reason,
        "message": message,
        "mcp_support": mcp_support,
        **trace_summary,
        **transaction_summary,
        "iteration_count": len(trace),
        "tests": tests or [],
        "test_count": len(tests or []),
        "risks": risks or [],
        "risk_count": len(risks or []),
        "recoverable": recovery_checkpoint is not None,
    }
    if recovery_checkpoint is not None:
        payload.update(
            {
                "recovery_checkpoint_artifact": recovery_checkpoint["artifact_path"],
                "recovery_strategy": recovery_checkpoint["resume"]["strategy"],
            }
        )
    return payload


def write_generic_edit_transactions(
    path: Path,
    transaction_summary: dict[str, Any],
) -> None:
    path.write_text(
        "".join(
            json.dumps(transaction, ensure_ascii=False) + "\n"
            for transaction in transaction_summary["transactions"]
        ),
        encoding="utf-8",
    )


def build_generic_edit_summary_markdown(
    *,
    provider_name: str,
    subtask_id: str | None,
    status: str,
    stop_reason: str,
    summary: str,
    trace_summary: dict[str, Any],
    transaction_summary: dict[str, Any],
    tests: list[str] | None,
    risks: list[str] | None,
    mcp_support: dict[str, Any] | None,
    recovery_checkpoint: dict[str, Any] | None,
) -> str:
    lines = [
        "# Generic Edit Summary",
        "",
        f"Status: {status}",
        f"Provider: {provider_name}",
        f"Stop reason: {stop_reason}",
        *generic_edit_subtask_lines(subtask_id),
        *generic_edit_mcp_lines(mcp_support),
        *generic_edit_native_fallback_lines(trace_summary),
        "",
        "## Summary",
        "",
        summary,
        *generic_edit_timeline_lines(trace_summary["action_timeline"]),
        *generic_edit_recovery_lines(transaction_summary),
        *generic_edit_resume_lines(recovery_checkpoint),
        *generic_edit_test_lines(tests),
        *generic_edit_risk_lines(risks),
    ]
    return "\n".join(lines) + "\n"


def build_generic_edit_recovery_checkpoint(
    *,
    timestamp: str,
    provider_name: str,
    subtask_id: str | None,
    status: str,
    stop_reason: str,
    message: str,
    next_iteration: int,
    trace_summary: dict[str, Any],
    transaction_summary: dict[str, Any],
    trace_path: Path,
    observation_path: Path | None,
    checkpoint_path: Path,
    mcp_support: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Build resumable generic_edit state for interrupted/error runs."""
    if not should_write_generic_edit_recovery_checkpoint(
        status=status,
        stop_reason=stop_reason,
        transaction_summary=transaction_summary,
    ):
        return None

    strategy = generic_edit_resume_strategy(
        stop_reason=stop_reason,
        transaction_summary=transaction_summary,
    )
    return {
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "stop_reason": stop_reason,
        "message": message,
        "artifact_path": str(checkpoint_path),
        "trace_artifact": str(trace_path),
        "observation_artifact": str(observation_path) if observation_path else None,
        "next_iteration": next_iteration,
        "recoverable": True,
        "resume": {
            "strategy": strategy,
            "prompt": build_generic_edit_resume_prompt(
                strategy=strategy,
                stop_reason=stop_reason,
                message=message,
                trace_path=trace_path,
                observation_path=observation_path,
                transaction_summary=transaction_summary,
            ),
        },
        "recent_actions": list(trace_summary.get("action_timeline") or [])[-10:],
        "transaction_summary": transaction_summary,
        "unresolved_partial_failure_ids": transaction_summary[
            "unresolved_partial_failure_ids"
        ],
        "last_partial_failure_id": transaction_summary["last_partial_failure_id"],
        "last_partial_failure_affected_paths": transaction_summary[
            "last_partial_failure_affected_paths"
        ],
        "last_partial_failure_mutated_paths": transaction_summary[
            "last_partial_failure_mutated_paths"
        ],
        "mcp_support": mcp_support,
    }


def load_generic_edit_recovery_checkpoint(checkpoint_path: Path) -> dict[str, Any]:
    """Load and validate a persisted generic_edit recovery checkpoint."""
    try:
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise GenericEditRuntimeError(
            f"Generic edit recovery checkpoint not found: {checkpoint_path}"
        ) from e
    except json.JSONDecodeError as e:
        raise GenericEditRuntimeError(
            f"Generic edit recovery checkpoint is not valid JSON: {e}"
        ) from e

    if not isinstance(payload, dict):
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint must be a JSON object."
        )
    if payload.get("recoverable") is not True:
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint is not marked recoverable."
        )
    if not isinstance(payload.get("resume"), dict):
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint is missing resume metadata."
        )
    return payload


def generic_edit_trace_path_for_checkpoint(checkpoint_path: Path) -> Path:
    """Return the trusted trace path colocated with a recovery checkpoint."""
    return checkpoint_path.parent / "generic_edit_trace.json"


def load_generic_edit_checkpoint_trace(
    trace_path: Path,
) -> list[dict[str, Any]]:
    """Load the trace referenced by a recovery checkpoint."""
    try:
        payload = json.loads(trace_path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise GenericEditRuntimeError(
            f"Generic edit recovery trace not found: {trace_path}"
        ) from e
    except json.JSONDecodeError as e:
        raise GenericEditRuntimeError(
            f"Generic edit recovery trace is not valid JSON: {e}"
        ) from e

    trace = payload.get("trace") if isinstance(payload, dict) else None
    if not isinstance(trace, list) or not all(isinstance(item, dict) for item in trace):
        raise GenericEditRuntimeError(
            "Generic edit recovery trace must contain a trace object list."
        )
    return trace


def checkpoint_next_iteration(
    checkpoint: dict[str, Any],
    trace: list[dict[str, Any]],
) -> int:
    """Return the next iteration number for a resumed generic_edit loop."""
    next_iteration = checkpoint.get("next_iteration")
    if isinstance(next_iteration, int) and next_iteration > 0:
        return max(next_iteration, len(trace) + 1)
    return len(trace) + 1


def build_generic_edit_checkpoint_resume_message(
    *,
    checkpoint: dict[str, Any],
    trace_path: Path,
) -> str:
    """Build the task prompt for a resumed generic_edit run."""
    resume = checkpoint["resume"]
    prompt = str(resume.get("prompt") or "").strip()
    if not prompt:
        prompt = "Resume this generic_edit run from the persisted checkpoint."

    return "\n".join(
        [
            prompt,
            "",
            f"Recovery checkpoint artifact: {checkpoint.get('artifact_path')}",
            f"Previous trace artifact: {trace_path}",
            f"Resume strategy: {resume.get('strategy', 'unknown')}",
            (
                "Use the previous trace as already completed context; inspect "
                "current workspace state before any new mutation."
            ),
        ]
    )


def should_write_generic_edit_recovery_checkpoint(
    *,
    status: str,
    stop_reason: str,
    transaction_summary: dict[str, Any],
) -> bool:
    """Return true when a generic_edit stop can be resumed or repaired."""
    if status == "complete":
        return False
    if transaction_summary["unresolved_partial_failure_count"] > 0:
        return True
    return stop_reason in RECOVERABLE_GENERIC_EDIT_STOP_REASONS


def generic_edit_resume_strategy(
    *,
    stop_reason: str,
    transaction_summary: dict[str, Any],
) -> str:
    """Return the checkpoint resume strategy for UI/orchestrator consumers."""
    if transaction_summary["unresolved_partial_failure_count"] > 0:
        return "recover_partial_failure"
    if stop_reason == "max_iterations":
        return "continue_from_trace"
    if stop_reason == "native_tool_error":
        return "retry_native_or_json"
    return "repair_provider_response"


def build_generic_edit_resume_prompt(
    *,
    strategy: str,
    stop_reason: str,
    message: str,
    trace_path: Path,
    observation_path: Path | None,
    transaction_summary: dict[str, Any],
) -> str:
    """Build a concise prompt that can restart a generic_edit recovery turn."""
    prompt_lines = [
        "Resume this generic_edit run from the persisted recovery checkpoint.",
        f"Stop reason: {stop_reason}.",
        f"Last message: {message}",
        f"Trace artifact: {trace_path}",
    ]
    if observation_path is not None:
        prompt_lines.append(f"Observation artifact: {observation_path}")

    unresolved_ids = transaction_summary["unresolved_partial_failure_ids"]
    if strategy == "recover_partial_failure":
        prompt_lines.extend(
            [
                "Unresolved partial-failure transaction(s): "
                + ", ".join(unresolved_ids),
                "Inspect or repair mutated path(s): "
                + ", ".join(
                    transaction_summary["last_partial_failure_mutated_paths"]
                    or transaction_summary["last_partial_failure_affected_paths"]
                    or ["."]
                ),
                "Do not call finish until the workspace is consistent.",
            ]
        )
    else:
        prompt_lines.extend(
            [
                "Continue from the recorded trace without repeating successful actions.",
                "Inspect current workspace state before mutating files.",
                "Call finish only when the task is complete.",
            ]
        )
    return "\n".join(prompt_lines)


def generic_edit_resume_lines(
    recovery_checkpoint: dict[str, Any] | None,
) -> list[str]:
    """Render resume checkpoint metadata for the markdown artifact."""
    if recovery_checkpoint is None:
        return []
    return [
        "",
        "## Resume",
        "",
        f"- Recoverable: {str(recovery_checkpoint['recoverable']).lower()}",
        f"- Strategy: `{recovery_checkpoint['resume']['strategy']}`",
        f"- Checkpoint: `{recovery_checkpoint['artifact_path']}`",
    ]


def generic_edit_subtask_lines(subtask_id: str | None) -> list[str]:
    return [f"Subtask: {subtask_id}"] if subtask_id else []


def generic_edit_mcp_lines(mcp_support: dict[str, Any] | None) -> list[str]:
    if not mcp_support:
        return []
    lines = [
        "",
        "## Runtime Support",
        "",
        f"- MCP: `{mcp_support.get('strategy', 'unknown')}` - "
        f"{mcp_support.get('reason', '')}",
    ]
    bridge_plan = mcp_support.get("bridge_plan")
    if isinstance(bridge_plan, dict):
        lines.append(
            "- MCP bridge plan: "
            f"`{bridge_plan.get('status', 'unknown')}`; "
            f"action `{bridge_plan.get('action_required', 'unknown')}`."
        )
        native_required = bridge_plan.get("native_required_servers") or []
        if native_required:
            lines.append(
                "- MCP native-required servers: "
                + ", ".join(str(server) for server in native_required)
            )
    return lines


def generic_edit_native_fallback_lines(trace_summary: dict[str, Any]) -> list[str]:
    fallbacks = trace_summary.get("native_tool_fallbacks")
    if not isinstance(fallbacks, list) or not fallbacks:
        return []
    lines = ["", "## Native Tool Fallback", ""]
    for fallback in fallbacks:
        if not isinstance(fallback, dict):
            continue
        lines.append(
            "- "
            f"{fallback.get('provider', 'unknown')} "
            f"{fallback.get('from_loop', 'native_tool_calls')} -> "
            f"{fallback.get('to_loop', 'json_actions')}: "
            f"{fallback.get('reason', 'native_tool_request_failed')}"
        )
        if fallback.get("message"):
            lines.append(f"  Message: {fallback['message']}")
    return lines


def generic_edit_timeline_lines(action_timeline: list[dict[str, Any]]) -> list[str]:
    if not action_timeline:
        return []
    lines = ["", "## Action Timeline", ""]
    lines.extend(generic_edit_timeline_line(item) for item in action_timeline)
    return lines


def generic_edit_timeline_line(item: dict[str, Any]) -> str:
    status_label = "ok" if item["ok"] else "failed"
    path_suffix = f" `{item['path']}`" if item.get("path") else ""
    return (
        f"- Iteration {item['iteration']}: `{item['tool']}` "
        f"{status_label}{path_suffix} - {item['message']}"
    )


def generic_edit_recovery_lines(transaction_summary: dict[str, Any]) -> list[str]:
    if not transaction_summary["partial_failure_count"]:
        return []
    recovery_state = (
        "resolved" if transaction_summary["recovery_resolved"] else "requires follow-up"
    )
    return [
        "",
        "## Recovery",
        "",
        f"- Partial failures: {transaction_summary['partial_failure_count']}",
        f"- Recovery state: {recovery_state}",
    ]


def generic_edit_test_lines(tests: list[str] | None) -> list[str]:
    if not tests:
        return []
    return [
        "",
        "## Suggested Verification Commands",
        "",
        *[f"- `{test}`" for test in tests],
    ]


def generic_edit_risk_lines(risks: list[str] | None) -> list[str]:
    if not risks:
        return []
    return ["", "## Risks", "", *[f"- {risk}" for risk in risks]]


def generic_edit_artifact_payload(paths: dict[str, Path]) -> dict[str, str]:
    return {
        "generic_edit_trace": str(paths["trace"]),
        "generic_edit_timeline": str(paths["timeline"]),
        "generic_edit_transactions": str(paths["transactions"]),
        "generic_edit_result": str(paths["result"]),
        "generic_edit_summary": str(paths["summary"]),
    }


def summarize_generic_edit_trace(trace: list[dict[str, Any]]) -> dict[str, Any]:
    """Return compact trace counters for result artifacts and UI consumers."""
    loop_kind = "json_actions"
    counters = {"action_count": 0, "failed_action_count": 0}
    tool_counts: dict[str, int] = {}
    failed_tools: dict[str, int] = {}
    action_timeline: list[dict[str, Any]] = []
    native_tool_fallbacks: list[dict[str, Any]] = []

    for iteration in trace:
        iteration_number = iteration.get("iteration")
        if iteration.get("loop"):
            loop_kind = str(iteration["loop"])
        fallback = iteration.get("native_tool_fallback")
        if isinstance(fallback, dict):
            native_tool_fallbacks.append(dict(fallback))
        for action_entry in iteration.get("actions", []):
            summarize_trace_action_entry(
                action_entry=action_entry,
                iteration_number=iteration_number,
                counters=counters,
                tool_counts=tool_counts,
                failed_tools=failed_tools,
                action_timeline=action_timeline,
            )

    return {
        "loop": loop_kind,
        "action_count": counters["action_count"],
        "failed_action_count": counters["failed_action_count"],
        "tool_counts": tool_counts,
        "failed_tools": failed_tools,
        "action_timeline": action_timeline,
        "native_tool_fallback_count": len(native_tool_fallbacks),
        "native_tool_fallbacks": native_tool_fallbacks,
    }


def summarize_trace_action_entry(
    *,
    action_entry: dict[str, Any],
    iteration_number: Any,
    counters: dict[str, int],
    tool_counts: dict[str, int],
    failed_tools: dict[str, int],
    action_timeline: list[dict[str, Any]],
) -> None:
    counters["action_count"] += 1
    result = action_entry.get("result", action_entry)
    request = action_entry.get("request", {})
    if isinstance(result, dict):
        append_dict_trace_action(
            result=result,
            request=request if isinstance(request, dict) else {},
            iteration_number=iteration_number,
            counters=counters,
            tool_counts=tool_counts,
            failed_tools=failed_tools,
            action_timeline=action_timeline,
        )
        return
    if isinstance(result, str):
        increment_count(tool_counts, "runtime")
        action_timeline.append(
            {
                "iteration": iteration_number,
                "tool": "runtime",
                "ok": True,
                "message": result[:300],
            }
        )


def append_dict_trace_action(
    *,
    result: dict[str, Any],
    request: dict[str, Any],
    iteration_number: Any,
    counters: dict[str, int],
    tool_counts: dict[str, int],
    failed_tools: dict[str, int],
    action_timeline: list[dict[str, Any]],
) -> None:
    tool = str(result.get("tool") or "runtime")
    increment_count(tool_counts, tool)
    is_ok = result.get("ok") is not False
    if result.get("ok") is False:
        counters["failed_action_count"] += 1
        increment_count(failed_tools, tool)
    action_timeline.append(
        build_timeline_entry(
            iteration_number=iteration_number,
            tool=tool,
            ok=is_ok,
            message=str(result.get("message") or ""),
            request=request,
            result=result,
        )
    )


def increment_count(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def summarize_generic_edit_transactions(trace: list[dict[str, Any]]) -> dict[str, Any]:
    """Return transaction counters for partial-action recovery reporting."""
    transactions = [
        iteration["transaction"]
        for iteration in trace
        if isinstance(iteration.get("transaction"), dict)
    ]
    status_counts: dict[str, int] = {}
    partial_failure_indexes: list[int] = []
    partial_failure_transaction_ids: list[str] = []
    recovery_transaction_ids: list[str] = []
    for index, transaction in enumerate(transactions):
        status = str(transaction.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == "partial_failure":
            partial_failure_indexes.append(index)
            partial_failure_transaction_ids.append(str(transaction.get("id") or index))
    last_partial_failure_index = (
        max(partial_failure_indexes) if partial_failure_indexes else None
    )
    last_partial_failure = (
        transactions[last_partial_failure_index]
        if last_partial_failure_index is not None
        else None
    )
    recovery_resolved = True
    if last_partial_failure_index is not None:
        recovery_transaction_ids = [
            str(transaction.get("id") or index)
            for index, transaction in enumerate(
                transactions[last_partial_failure_index + 1 :],
                start=last_partial_failure_index + 1,
            )
            if transaction_resolves_partial_failure(
                transaction=transaction,
                partial_failure=last_partial_failure,
            )
        ]
        recovery_resolved = bool(recovery_transaction_ids)
    partial_failure_count = status_counts.get("partial_failure", 0)
    unresolved_partial_failure_ids = (
        [] if recovery_resolved else partial_failure_transaction_ids
    )
    last_partial_failure_id = (
        str(last_partial_failure.get("id"))
        if isinstance(last_partial_failure, dict) and last_partial_failure.get("id")
        else None
    )
    last_partial_failure_affected_paths: list[str] = []
    last_partial_failure_mutated_paths: list[str] = []
    if isinstance(last_partial_failure, dict):
        last_partial_failure_affected_paths = list(
            last_partial_failure.get("affected_paths") or []
        )
        last_partial_failure_mutated_paths = list(
            last_partial_failure.get("mutated_paths") or []
        )
    return {
        "transactions": transactions,
        "transaction_count": len(transactions),
        "transaction_status_counts": status_counts,
        "partial_failure_count": partial_failure_count,
        "partial_failure_transaction_ids": partial_failure_transaction_ids,
        "last_partial_failure_id": last_partial_failure_id,
        "last_partial_failure_affected_paths": last_partial_failure_affected_paths,
        "last_partial_failure_mutated_paths": last_partial_failure_mutated_paths,
        "recovery_transaction_ids": recovery_transaction_ids,
        "recovery_required": partial_failure_count > 0,
        "recovery_resolved": recovery_resolved,
        "unresolved_partial_failure_count": len(unresolved_partial_failure_ids),
        "unresolved_partial_failure_ids": unresolved_partial_failure_ids,
    }


def has_unresolved_partial_failure(trace: list[dict[str, Any]]) -> bool:
    """Return true when finish would leave a partial mutation unresolved."""
    return (
        summarize_generic_edit_transactions(trace)["unresolved_partial_failure_count"]
        > 0
    )


def transaction_resolves_partial_failure(
    *,
    transaction: dict[str, Any],
    partial_failure: dict[str, Any] | None,
) -> bool:
    """Return true when a later transaction covers a partial mutation failure."""
    if partial_failure is None:
        return False
    if not bool(transaction.get("can_resolve_partial_failure")):
        return False

    tool_sequence = {str(tool) for tool in transaction.get("tool_sequence") or ()}
    if tool_sequence & WORKSPACE_RECOVERY_TOOLS:
        return True

    partial_paths = transaction_path_set(partial_failure, prefer_mutated=True)
    if not partial_paths:
        return True

    recovery_paths = transaction_path_set(transaction, prefer_mutated=False)
    return path_sets_overlap(partial_paths, recovery_paths)


def transaction_path_set(
    transaction: dict[str, Any],
    *,
    prefer_mutated: bool,
) -> set[str]:
    """Return normalized transaction paths used for recovery coverage checks."""
    fields = (
        ("mutated_paths", "affected_paths")
        if prefer_mutated
        else ("affected_paths", "mutated_paths")
    )
    paths: set[str] = set()
    for field_name in fields:
        value = transaction.get(field_name)
        if isinstance(value, list):
            paths.update(str(path) for path in value if path)
        if paths and prefer_mutated:
            break
    return paths


def path_sets_overlap(left: set[str], right: set[str]) -> bool:
    """Return true when two workspace path sets overlap or one covers the other."""
    for left_path in left:
        for right_path in right:
            if workspace_paths_overlap(left_path, right_path):
                return True
    return False


def workspace_paths_overlap(left: str, right: str) -> bool:
    """Return true when two workspace-relative paths refer to overlapping scopes."""
    left = normalize_transaction_path(left)
    right = normalize_transaction_path(right)
    if not left or not right:
        return False
    if left == "." or right == "." or left == right:
        return True
    return left.startswith(f"{right}/") or right.startswith(f"{left}/")


def normalize_transaction_path(path: str) -> str:
    """Normalize a transaction path for stable prefix comparisons."""
    normalized = path.replace("\\", "/").strip().strip("/")
    return normalized or "."


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
