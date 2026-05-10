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
from .patch_proposal import (
    PatchProposalError,
    extract_patch_paths,
    validate_workspace_relative_path,
)

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
- Use rollback_transaction when you choose to restore a partial transaction from mutation snapshots.
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
- Use rollback_transaction when you choose to restore a partial transaction from mutation snapshots.
- Call finish with a concise summary, verification commands, and risks when complete.

Task:
__AUTO_CODE_TASK_PROMPT__
"""


class GenericEditRuntimeError(RuntimeError):
    """Raised when the generic edit runtime cannot continue safely."""

    def __init__(
        self,
        message: str,
        *,
        data: dict[str, Any] | None = None,
        restored_paths: list[str] | None = None,
        deleted_paths: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.data = dict(data or {})
        self.restored_paths = list(
            restored_paths or self.data.get("restored_paths") or []
        )
        self.deleted_paths = list(deleted_paths or self.data.get("deleted_paths") or [])
        if self.restored_paths:
            self.data.setdefault("restored_paths", self.restored_paths)
        if self.deleted_paths:
            self.data.setdefault("deleted_paths", self.deleted_paths)


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


ROLLBACK_TRANSACTION_TOOL = "rollback_transaction"
MUTATING_LOCAL_ACTIONS = frozenset(
    {
        "write_file",
        "replace_text",
        "delete_file",
        "move_file",
        "apply_patch",
        "run_command",
        ROLLBACK_TRANSACTION_TOOL,
    }
)
WORKSPACE_RECOVERY_TOOLS = frozenset(
    {"git_status", "git_diff", "run_command", ROLLBACK_TRANSACTION_TOOL}
)
GENERIC_EDIT_ROLLBACK_TOOLS = [ROLLBACK_TRANSACTION_TOOL, "git_diff", "apply_patch"]
GENERIC_EDIT_REPAIR_TOOLS = [
    "read_file",
    "git_diff",
    "apply_patch",
    "write_file",
    "run_command",
]
GENERIC_EDIT_RECOVERY_POLICY_VERSION = 1
GENERIC_EDIT_RECOVERY_VERIFICATION_TOOLS = ["git_diff", "run_command"]
GENERIC_EDIT_RECOVERY_DIFF_MAX_CHARS = 8000
MAX_MUTATION_PREIMAGE_BYTES = 20000
SNAPSHOT_MUTATING_ACTIONS = frozenset(
    {"write_file", "replace_text", "delete_file", "move_file", "apply_patch"}
)
RECOVERABLE_GENERIC_EDIT_STOP_REASONS = frozenset(
    {
        "cancelled",
        "max_iterations",
        "native_tool_error",
        "non_terminal_finish",
        "parse_error",
        "unresolved_partial_failure",
    }
)
GENERIC_EDIT_ARTIFACT_MANIFEST_SCHEMA_VERSION = 1
GENERIC_EDIT_ARTIFACT_MANIFEST_RECENT_EVENT_LIMIT = 5
GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_ACTION_LIMIT = 10
GENERIC_EDIT_ARTIFACT_MANIFEST_RECENT_EVENT_FIELDS = (
    "sequence",
    "event_type",
    "tool",
    "ok",
    "message",
    "status",
    "transaction_id",
    "group_id",
    "path",
    "iteration",
    "from_loop",
    "to_loop",
    "reason",
    "tool_schema_count",
    "action_index",
    "recovery_required",
    "failed_action_count",
    "recovery_attempt_count",
    "failed_recovery_attempt_count",
)
GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_ACTION_STRING_FIELDS = (
    "id",
    "kind",
    "tool",
    "transaction_id",
    "transaction_group_id",
    "rollback_operation_id",
)
GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_ACTION_LIST_FIELDS = (
    "paths",
    "mutation_snapshot_ids",
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
        self._mutation_snapshots: list[dict[str, Any]] = []
        self._resume_metadata: dict[str, Any] | None = None

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
        self._mutation_snapshots = []
        self._resume_metadata = None
        self._mcp_bridge = RuntimeMcpBridge.from_agent_session(
            agent_session=self.agent_session,
            spec_dir=spec_dir,
            project_dir=self._executor.project_dir,
            agent_type=self.agent_type,
        )

        try:
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
        finally:
            await self._close_mcp_bridge()

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
        checkpoint_path = resolve_generic_edit_resume_checkpoint_path(
            checkpoint_path=checkpoint_path,
            spec_dir=spec_dir,
        )
        checkpoint = load_generic_edit_recovery_checkpoint(checkpoint_path)
        trace_path = generic_edit_trace_path_for_checkpoint(checkpoint_path)
        trace = load_generic_edit_checkpoint_trace(trace_path)
        self._mutation_snapshots = load_generic_edit_mutation_snapshots(
            generic_edit_mutation_snapshot_path_for_checkpoint(checkpoint_path)
        )
        message = build_generic_edit_checkpoint_resume_message(
            checkpoint=checkpoint,
            trace_path=trace_path,
        )
        next_iteration = checkpoint_next_iteration(checkpoint, trace)
        self._resume_metadata = build_generic_edit_resume_metadata(
            checkpoint=checkpoint,
            checkpoint_path=checkpoint_path,
            trace_path=trace_path,
            start_iteration=next_iteration,
        )

        try:
            return await self._run_json_action_loop(
                message=message,
                spec_dir=spec_dir,
                verbose=verbose,
                phase=phase,
                subtask_id=subtask_id or checkpoint.get("subtask_id"),
                initial_trace=trace,
                start_iteration=next_iteration,
            )
        finally:
            await self._close_mcp_bridge()

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
                return self._cancelled_result(
                    trace=trace,
                    spec_dir=spec_dir,
                    observation_path=observation_path,
                    subtask_id=subtask_id,
                )
            response_text = await self._complete(prompt)
            if self._cancel_requested:
                return self._cancelled_result(
                    trace=trace,
                    spec_dir=spec_dir,
                    observation_path=observation_path,
                    subtask_id=subtask_id,
                )
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
                if execution.executed_actions:
                    iteration_entry["transaction"] = build_generic_edit_transaction(
                        loop="json_actions",
                        iteration=iteration,
                        actions=execution.executed_actions,
                        results=execution.action_results,
                    )
                    trace.append(iteration_entry)
                return self._cancelled_result(
                    trace=trace,
                    spec_dir=spec_dir,
                    observation_path=observation_path,
                    subtask_id=subtask_id,
                )
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
            mutation_snapshots=self._mutation_snapshots,
            mcp_support=self._mcp_support_payload(),
            resume_metadata=self._resume_metadata,
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
                loop="json_actions",
                iteration=iteration,
                action_index=action_index,
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
            mutation_snapshots=self._mutation_snapshots,
            mcp_support=self._mcp_support_payload(),
            resume_metadata=self._resume_metadata,
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
            mutation_snapshots=self._mutation_snapshots,
            mcp_support=self._mcp_support_payload(),
            resume_metadata=self._resume_metadata,
        )
        return AgentRunResult(
            status="error",
            response_text=f"{message}\nArtifacts: {artifacts['generic_edit_trace']}",
        )

    def _cancelled_result(
        self,
        *,
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        subtask_id: str | None,
    ) -> AgentRunResult:
        """Persist resumable cancellation state when cancellation interrupted work."""
        if not trace:
            return generic_edit_cancelled_result()
        artifacts = save_generic_edit_artifacts(
            spec_dir=spec_dir,
            provider_name=self.provider_name,
            subtask_id=subtask_id,
            status="cancelled",
            stop_reason="cancelled",
            message=GENERIC_EDIT_CANCELLED_MESSAGE,
            trace=trace,
            summary=GENERIC_EDIT_CANCELLED_MESSAGE,
            observation_path=observation_path,
            mutation_snapshots=self._mutation_snapshots,
            mcp_support=self._mcp_support_payload(),
            resume_metadata=self._resume_metadata,
        )
        return AgentRunResult(
            status="cancelled",
            response_text=(
                f"{GENERIC_EDIT_CANCELLED_MESSAGE}\n"
                f"Artifacts: {artifacts['generic_edit_trace']}"
            ),
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
            mutation_snapshots=self._mutation_snapshots,
            mcp_support=self._mcp_support_payload(),
            resume_metadata=self._resume_metadata,
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
                mutation_snapshots=self._mutation_snapshots,
                mcp_support=self._mcp_support_payload(),
                resume_metadata=self._resume_metadata,
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
                loop="native_tool_calls",
                iteration=iteration,
                action_index=action_index,
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
            mutation_snapshots=self._mutation_snapshots,
            mcp_support=self._mcp_support_payload(),
            resume_metadata=self._resume_metadata,
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
            mutation_snapshots=self._mutation_snapshots,
            mcp_support=self._mcp_support_payload(),
            resume_metadata=self._resume_metadata,
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

    async def _close_mcp_bridge(self) -> None:
        if self._mcp_bridge is None:
            return
        await self._mcp_bridge.close()

    async def _execute_action(
        self,
        action: dict[str, Any],
        *,
        loop: str,
        iteration: int,
        action_index: int,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None,
    ) -> ToolActionResult:
        mutation_snapshot = self._build_mutation_snapshot(
            action,
            loop=loop,
            iteration=iteration,
            action_index=action_index,
        )
        if action_tool(action) == "run_subagents":
            result = await self._run_subagents_action(
                action,
                spec_dir=spec_dir,
                verbose=verbose,
                phase=phase,
                subtask_id=subtask_id,
            )
        elif action_tool(action) == ROLLBACK_TRANSACTION_TOOL:
            result = self._rollback_transaction_action(action)
        elif self._mcp_bridge is not None and self._mcp_bridge.can_execute(action):
            result = await self._mcp_bridge.execute(action)
        elif is_mcp_action_name(action_tool(action)):
            result = unavailable_mcp_action_result(
                action,
                support=self._mcp_support_payload(),
            )
        else:
            result = await self._executor.execute(action)
        self._record_mutation_snapshot_result(mutation_snapshot, result)
        return result

    def _rollback_transaction_action(self, action: dict[str, Any]) -> ToolActionResult:
        """Restore workspace files from captured mutation snapshots."""
        try:
            return execute_generic_edit_transaction_rollback(
                action=action,
                project_dir=self._executor.project_dir,
                mutation_snapshots=self._mutation_snapshots,
            )
        except GenericEditRuntimeError as e:
            return ToolActionResult(
                tool=ROLLBACK_TRANSACTION_TOOL,
                ok=False,
                message=str(e),
                data=dict(e.data),
            )

    def _build_mutation_snapshot(
        self,
        action: dict[str, Any],
        *,
        loop: str,
        iteration: int,
        action_index: int,
    ) -> dict[str, Any] | None:
        """Capture workspace preimages before a supported file mutation."""
        tool = action_tool(action)
        if tool not in SNAPSHOT_MUTATING_ACTIONS:
            return None
        snapshot_id = f"mutation-{len(self._mutation_snapshots) + 1}"
        return build_generic_edit_mutation_snapshot(
            action=action,
            project_dir=self._executor.project_dir,
            snapshot_id=snapshot_id,
            transaction_id=f"{loop}-{iteration}",
            loop=loop,
            iteration=iteration,
            action_index=action_index,
        )

    def _record_mutation_snapshot_result(
        self,
        snapshot: dict[str, Any] | None,
        result: ToolActionResult,
    ) -> None:
        """Attach a successful mutation snapshot to result metadata and artifacts."""
        if snapshot is None or not result.ok:
            return
        self._mutation_snapshots.append(snapshot)
        result.data = {
            **result.data,
            "mutation_snapshot_id": snapshot["id"],
            "rollback_available": snapshot["rollback"]["restorable"],
        }

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
        dict.fromkeys(
            [
                *(path for action in actions for path in action_path_values(action)),
                *(path for result in results for path in result_path_values(result)),
            ]
        )
    )
    mutated_paths = sorted(
        dict.fromkeys(
            [
                *(
                    path
                    for action in actions
                    if action_tool(action) in MUTATING_LOCAL_ACTIONS
                    for path in action_path_values(action)
                ),
                *(
                    path
                    for result in results
                    for path in result_path_values(result, prefer_mutated=True)
                ),
            ]
        )
    )
    mutation_snapshot_ids = [
        str(result.data["mutation_snapshot_id"])
        for result in results
        if result.ok and result.data.get("mutation_snapshot_id")
    ]
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
        "mutation_snapshot_ids": mutation_snapshot_ids,
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
        transaction["recovery_plan"] = build_transaction_recovery_plan(transaction)
    return transaction


def build_transaction_recovery_plan(transaction: dict[str, Any]) -> dict[str, Any]:
    """Return machine-readable repair/rollback guidance for one transaction."""
    mutated_paths = list(transaction.get("mutated_paths") or [])
    affected_paths = list(transaction.get("affected_paths") or [])
    mutation_snapshot_ids = list(transaction.get("mutation_snapshot_ids") or [])
    return {
        "strategy": "repair_or_rollback",
        "mutated_paths": mutated_paths,
        "affected_paths": affected_paths,
        "rollback": {
            "recommended_tools": GENERIC_EDIT_ROLLBACK_TOOLS,
            "preferred_action": {
                "tool": ROLLBACK_TRANSACTION_TOOL,
                "transaction_id": str(transaction.get("id") or ""),
            },
            "mutation_snapshot_ids": mutation_snapshot_ids,
            "instructions": [
                "Run git_diff scoped to mutated paths to inspect partial changes.",
                "Use rollback_transaction when restoring mutation snapshot preimages is safe.",
                "Use apply_patch with an explicit reverse or corrective patch when a patch-based rollback is safer.",
            ],
        },
        "repair": {
            "recommended_tools": GENERIC_EDIT_REPAIR_TOOLS,
            "instructions": [
                "Read affected files and inspect git_diff before writing more changes.",
                "Apply a focused repair patch or rewrite the affected file, then run targeted verification.",
            ],
        },
        "required_before_finish": [
            "Inspect mutated paths.",
            "Either repair the partial mutation or intentionally roll it back.",
            "Verify workspace consistency before finish.",
        ],
        "policy": build_generic_edit_recovery_policy(
            transaction_id=str(transaction.get("id") or ""),
            transaction_group_id=None,
            affected_paths=affected_paths,
            mutated_paths=mutated_paths,
            rollback_restorable=bool(mutation_snapshot_ids),
        ),
    }


def build_generic_edit_recovery_next_actions(
    *,
    transaction_id: str,
    transaction_group_id: str | None,
    affected_paths: list[str],
    mutated_paths: list[str],
    rollback_operation: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return executable next actions for partial-failure recovery UIs."""
    next_actions: list[dict[str, Any]] = []
    inspect_paths = list(dict.fromkeys(mutated_paths or affected_paths or []))
    if not inspect_paths:
        inspect_paths = ["."]
    for index, path in enumerate(inspect_paths, start=1):
        action: dict[str, Any] = {
            "id": f"inspect-{transaction_id}-{index}",
            "kind": "inspect_diff",
            "tool": "git_diff",
            "action": {
                "tool": "git_diff",
                "path": path,
                "max_chars": GENERIC_EDIT_RECOVERY_DIFF_MAX_CHARS,
            },
            "transaction_id": transaction_id,
            "paths": [path],
            "required_before_finish": True,
        }
        if transaction_group_id is not None:
            action["transaction_group_id"] = transaction_group_id
        next_actions.append(action)

    rollback_action = dict(rollback_operation.get("action") or {})
    if bool(rollback_operation.get("restorable")) and rollback_action:
        action = {
            "id": f"rollback-{transaction_id}",
            "kind": ROLLBACK_TRANSACTION_TOOL,
            "tool": ROLLBACK_TRANSACTION_TOOL,
            "action": rollback_action,
            "transaction_id": transaction_id,
            "rollback_operation_id": str(rollback_operation.get("id") or ""),
            "mutation_snapshot_ids": list(
                rollback_operation.get("mutation_snapshot_ids") or []
            ),
            "required_before_finish": True,
        }
        if transaction_group_id is not None:
            action["transaction_group_id"] = transaction_group_id
        next_actions.append(action)
    return next_actions


def build_generic_edit_recovery_policy(
    *,
    transaction_id: str,
    transaction_group_id: str | None,
    affected_paths: list[str],
    mutated_paths: list[str],
    rollback_restorable: bool,
) -> dict[str, Any]:
    """Return a compact recovery policy for UI/orchestrator decisioning."""
    path_scope = list(dict.fromkeys(mutated_paths or affected_paths or []))
    resolution_strategies = ["repair_mutation"]
    if rollback_restorable:
        resolution_strategies.insert(0, ROLLBACK_TRANSACTION_TOOL)
    required_next_action_kinds = ["inspect_diff"]
    required_next_action_kinds.append(
        ROLLBACK_TRANSACTION_TOOL if rollback_restorable else "repair_mutation"
    )
    policy: dict[str, Any] = {
        "version": GENERIC_EDIT_RECOVERY_POLICY_VERSION,
        "status": "requires_resolution",
        "finish_blocked": True,
        "transaction_id": transaction_id,
        "path_scope": path_scope,
        "resolution_strategies": resolution_strategies,
        "preferred_strategy": resolution_strategies[0],
        "rollback_restorable": rollback_restorable,
        "required_next_action_kinds": required_next_action_kinds,
        "recommended_verification_tools": list(
            GENERIC_EDIT_RECOVERY_VERIFICATION_TOOLS
        ),
    }
    if transaction_group_id is not None:
        policy["transaction_group_id"] = transaction_group_id
    return policy


def build_generic_edit_recovery_plan_policy(
    *,
    transaction_summary: dict[str, Any],
    transaction_group_summary: dict[str, Any],
) -> dict[str, Any]:
    """Return aggregate recovery policy metadata for unresolved failures."""
    resolution_strategies: list[str] = []
    for group in transaction_group_summary["transaction_groups"]:
        if group.get("status") != "unresolved":
            continue
        policy = group.get("recovery_policy")
        if not isinstance(policy, dict):
            continue
        for strategy in policy.get("resolution_strategies") or []:
            strategy_value = str(strategy)
            if strategy_value not in resolution_strategies:
                resolution_strategies.append(strategy_value)
    if not resolution_strategies:
        resolution_strategies = [ROLLBACK_TRANSACTION_TOOL, "repair_mutation"]
    return {
        "version": GENERIC_EDIT_RECOVERY_POLICY_VERSION,
        "status": "requires_resolution",
        "finish_blocked": True,
        "unresolved_transaction_count": transaction_summary[
            "unresolved_partial_failure_count"
        ],
        "unresolved_transaction_group_count": transaction_group_summary[
            "unresolved_transaction_group_count"
        ],
        "resolution_strategies": resolution_strategies,
        "recommended_verification_tools": list(
            GENERIC_EDIT_RECOVERY_VERIFICATION_TOOLS
        ),
    }


def build_generic_edit_recovery_policy_status(
    *,
    strategy: str,
    tool_sequence: list[str],
) -> dict[str, Any]:
    """Return policy status for a resolved recovery group."""
    verification_observed = generic_edit_recovery_verification_observed(tool_sequence)
    warnings = []
    if not verification_observed:
        warnings.append(
            "Recovered transaction resolved without post-recovery verification."
        )
    return {
        "version": GENERIC_EDIT_RECOVERY_POLICY_VERSION,
        "status": "resolved",
        "resolution_strategy": strategy,
        "post_recovery_verification_observed": verification_observed,
        "recommended_verification_tools": list(
            GENERIC_EDIT_RECOVERY_VERIFICATION_TOOLS
        ),
        "warning_count": len(warnings),
        "warnings": warnings,
    }


def generic_edit_recovery_verification_observed(tool_sequence: list[str]) -> bool:
    """Return true when a recovery transaction ran a verification tool."""
    return any(
        tool in GENERIC_EDIT_RECOVERY_VERIFICATION_TOOLS for tool in tool_sequence
    )


def generic_edit_recovery_strategy_for_tools(tool_sequence: list[str]) -> str:
    """Return a normalized recovery strategy label for a tool sequence."""
    if ROLLBACK_TRANSACTION_TOOL in tool_sequence:
        return ROLLBACK_TRANSACTION_TOOL
    if any(tool in MUTATING_LOCAL_ACTIONS for tool in tool_sequence):
        return "repair_mutation"
    if set(tool_sequence) & WORKSPACE_RECOVERY_TOOLS:
        return "inspect_or_verify"
    return "path_coverage"


def build_generic_edit_recovery_outcome(
    *,
    group: dict[str, Any],
    resolution_transaction: dict[str, Any],
) -> dict[str, Any]:
    """Return a compact resolved recovery outcome for UI/session history."""
    tool_sequence = [
        str(tool) for tool in resolution_transaction.get("tool_sequence") or []
    ]
    strategy = generic_edit_recovery_strategy_for_tools(tool_sequence)
    return {
        "transaction_group_id": str(group.get("id") or ""),
        "partial_failure_transaction_id": str(
            group.get("partial_failure_transaction_id") or ""
        ),
        "resolution_transaction_id": str(group.get("resolution_transaction_id") or ""),
        "strategy": strategy,
        "tool_sequence": tool_sequence,
        "recovered_paths": list(group.get("mutated_paths") or []),
        "mutation_snapshot_ids": list(group.get("mutation_snapshot_ids") or []),
        "recovery_attempt_count": int(group.get("recovery_attempt_count") or 0),
        "failed_recovery_attempt_count": int(
            group.get("failed_recovery_attempt_count") or 0
        ),
        "policy_status": build_generic_edit_recovery_policy_status(
            strategy=strategy,
            tool_sequence=tool_sequence,
        ),
    }


def build_generic_edit_recovery_attempt(
    *,
    attempt_number: int,
    transaction: dict[str, Any],
    transaction_index: int,
    partial_failure: dict[str, Any],
) -> dict[str, Any]:
    """Return one compact recovery-attempt entry for a partial-failure group."""
    tool_sequence = [str(tool) for tool in transaction.get("tool_sequence") or []]
    status = str(transaction.get("status") or "")
    if status != "complete":
        strategy = "failed_attempt"
    else:
        strategy = generic_edit_recovery_strategy_for_tools(tool_sequence)
    return {
        "attempt_number": attempt_number,
        "transaction_id": transaction_id_value(transaction, transaction_index),
        "resolved": transaction_resolves_partial_failure(
            transaction=transaction,
            partial_failure=partial_failure,
        ),
        "strategy": strategy,
        "status": status,
        "tool_sequence": tool_sequence,
        "affected_paths": list(transaction.get("affected_paths") or []),
        "mutated_paths": list(transaction.get("mutated_paths") or []),
        "mutation_snapshot_ids": list(transaction.get("mutation_snapshot_ids") or []),
        "post_recovery_verification_observed": (
            generic_edit_recovery_verification_observed(tool_sequence)
        ),
    }


def build_generic_edit_mutation_snapshot(
    *,
    action: dict[str, Any],
    project_dir: Path,
    snapshot_id: str,
    transaction_id: str,
    loop: str,
    iteration: int,
    action_index: int,
) -> dict[str, Any]:
    """Capture file preimages for a supported mutating local action."""
    paths = action_path_values(action)
    preimages = [
        build_generic_edit_file_preimage(project_dir=project_dir, path=path)
        for path in paths
    ]
    restorable = bool(preimages) and all(
        bool(preimage.get("restorable")) for preimage in preimages
    )
    return {
        "id": snapshot_id,
        "transaction_id": transaction_id,
        "loop": loop,
        "iteration": iteration,
        "action_index": action_index,
        "tool": action_tool(action),
        "paths": paths,
        "preimages": preimages,
        "rollback": {
            "strategy": "restore_preimages",
            "restorable": restorable,
            "instructions": [
                "For existing file preimages, restore the captured content.",
                "For missing file preimages, delete the created file if rollback is selected.",
                "If a preimage is not restorable, inspect git_diff and repair manually.",
            ],
        },
    }


def build_generic_edit_file_preimage(
    *,
    project_dir: Path,
    path: str,
) -> dict[str, Any]:
    """Return bounded pre-mutation file state for one workspace path."""
    payload: dict[str, Any] = {
        "path": path,
        "exists": False,
        "type": "missing",
        "restorable": True,
    }
    try:
        target = resolve_snapshot_workspace_path(project_dir, path)
    except GenericEditRuntimeError as e:
        payload.update(
            {
                "type": "invalid",
                "restorable": False,
                "error": str(e),
            }
        )
        return payload
    except OSError as e:
        payload.update(
            {
                "type": "unreadable",
                "restorable": False,
                "error": str(e),
            }
        )
        return payload

    try:
        if not target.exists():
            return payload
        payload["exists"] = True
        if target.is_dir():
            payload.update({"type": "directory", "restorable": False})
            return payload
        if not target.is_file():
            payload.update({"type": "other", "restorable": False})
            return payload

        size = target.stat().st_size
    except OSError as e:
        payload.update(
            {
                "type": "unreadable",
                "restorable": False,
                "error": str(e),
            }
        )
        return payload

    payload.update({"type": "file", "bytes": size})
    if size > MAX_MUTATION_PREIMAGE_BYTES:
        payload.update(
            {
                "content_truncated": True,
                "content_bytes_limit": MAX_MUTATION_PREIMAGE_BYTES,
                "restorable": False,
            }
        )
        return payload

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        payload.update(
            {
                "content_encoding": "unknown",
                "restorable": False,
                "error": "File is not valid UTF-8 text.",
            }
        )
        return payload
    except OSError as e:
        payload.update(
            {
                "restorable": False,
                "error": str(e),
            }
        )
        return payload

    payload.update(
        {
            "content": content,
            "content_encoding": "utf-8",
            "content_truncated": False,
            "line_count": len(content.splitlines()),
        }
    )
    return payload


def execute_generic_edit_transaction_rollback(
    *,
    action: dict[str, Any],
    project_dir: Path,
    mutation_snapshots: list[dict[str, Any]],
) -> ToolActionResult:
    """Apply a snapshot-backed rollback for one generic_edit transaction."""
    transaction_id = str(action.get("transaction_id") or "").strip()
    if not transaction_id:
        raise GenericEditRuntimeError("rollback_transaction requires transaction_id.")
    operation = build_generic_edit_rollback_operation(
        transaction_id=transaction_id,
        mutation_snapshots=mutation_snapshots,
        snapshot_ids=normalize_string_list(action.get("snapshot_ids")),
    )
    if not operation["restorable"]:
        reasons = (
            "; ".join(operation["blocked_reasons"]) or "rollback is not restorable"
        )
        raise GenericEditRuntimeError(
            f"Cannot rollback transaction {transaction_id}: {reasons}"
        )

    steps = validate_generic_edit_rollback_steps(
        project_dir=project_dir,
        steps=operation["steps"],
    )
    restored_paths: list[str] = []
    deleted_paths: list[str] = []
    try:
        for step, target in steps:
            if step["operation"] == "restore_file":
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(str(step["content"]), encoding="utf-8")
                restored_paths.append(str(step["path"]))
                continue
            if target.exists():
                target.unlink()
            deleted_paths.append(str(step["path"]))
    except OSError as e:
        affected_paths = sorted(dict.fromkeys([*restored_paths, *deleted_paths]))
        raise GenericEditRuntimeError(
            f"Failed to rollback transaction {transaction_id}: {e}; "
            f"restored_paths={restored_paths}; deleted_paths={deleted_paths}",
            data={
                "transaction_id": transaction_id,
                "restored_paths": restored_paths,
                "deleted_paths": deleted_paths,
                "affected_paths": affected_paths,
                "mutated_paths": affected_paths,
                "recovery_strategy": ROLLBACK_TRANSACTION_TOOL,
            },
            restored_paths=restored_paths,
            deleted_paths=deleted_paths,
        ) from e

    affected_paths = sorted(dict.fromkeys([*restored_paths, *deleted_paths]))
    return ToolActionResult(
        tool=ROLLBACK_TRANSACTION_TOOL,
        ok=True,
        message=(
            f"Rolled back transaction {transaction_id} from "
            f"{len(operation['mutation_snapshot_ids'])} mutation snapshot(s)."
        ),
        data={
            "transaction_id": transaction_id,
            "rollback_operation_id": operation["id"],
            "mutation_snapshot_ids": operation["mutation_snapshot_ids"],
            "affected_paths": affected_paths,
            "mutated_paths": affected_paths,
            "restored_paths": restored_paths,
            "deleted_paths": deleted_paths,
            "recovery_strategy": ROLLBACK_TRANSACTION_TOOL,
        },
    )


def validate_generic_edit_rollback_steps(
    *,
    project_dir: Path,
    steps: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], Path]]:
    """Validate rollback targets before mutating the workspace."""
    validated: list[tuple[dict[str, Any], Path]] = []
    for step in steps:
        path = str(step.get("path") or "")
        target = resolve_snapshot_workspace_path(project_dir, path)
        try:
            if step.get("operation") == "restore_file":
                parent = target.parent
                if parent.exists() and not parent.is_dir():
                    raise GenericEditRuntimeError(
                        f"Cannot restore {path}: parent path is not a directory."
                    )
            elif target.exists() and target.is_dir():
                raise GenericEditRuntimeError(
                    f"Cannot delete rollback-created path {path}: it is a directory."
                )
        except OSError as e:
            raise GenericEditRuntimeError(
                f"Cannot validate rollback path {path}: {e}"
            ) from e
        validated.append((step, target))
    return validated


def build_generic_edit_rollback_operation(
    *,
    transaction_id: str,
    mutation_snapshots: list[dict[str, Any]],
    snapshot_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build an executable rollback operation from mutation snapshots."""
    selected = select_generic_edit_rollback_snapshots(
        transaction_id=transaction_id,
        mutation_snapshots=mutation_snapshots,
        snapshot_ids=snapshot_ids or [],
    )
    blocked_reasons: list[str] = []
    requested_snapshot_ids = list(
        dict.fromkeys(
            str(snapshot_id) for snapshot_id in (snapshot_ids or []) if snapshot_id
        )
    )
    if requested_snapshot_ids:
        selected_snapshot_ids = {str(snapshot.get("id")) for snapshot in selected}
        missing_snapshot_ids = [
            snapshot_id
            for snapshot_id in requested_snapshot_ids
            if snapshot_id not in selected_snapshot_ids
        ]
        if missing_snapshot_ids:
            blocked_reasons.append(
                "Requested snapshot ids not found: " + ", ".join(missing_snapshot_ids)
            )
    if not selected:
        blocked_reasons.append("No mutation snapshots found for transaction.")

    steps: list[dict[str, Any]] = []
    for snapshot in reversed(selected):
        if not bool(snapshot.get("rollback", {}).get("restorable")):
            blocked_reasons.append(
                f"Snapshot {snapshot.get('id', '<unknown>')} is not restorable."
            )
        for preimage in snapshot.get("preimages") or []:
            step = build_generic_edit_rollback_step(preimage)
            if step is None:
                blocked_reasons.append(
                    "Preimage for "
                    f"{preimage.get('path', '<unknown>')} is not restorable."
                )
                continue
            steps.append(step)

    affected_paths = sorted(
        dict.fromkeys(str(step["path"]) for step in steps if step.get("path"))
    )
    snapshot_id_values = [str(snapshot.get("id")) for snapshot in selected]
    return {
        "id": f"rollback-{transaction_id}",
        "tool": ROLLBACK_TRANSACTION_TOOL,
        "transaction_id": transaction_id,
        "mutation_snapshot_ids": snapshot_id_values,
        "restorable": bool(selected) and not blocked_reasons,
        "blocked_reasons": blocked_reasons,
        "affected_paths": affected_paths,
        "application_order": "reverse_snapshot_order",
        "action": {
            "tool": ROLLBACK_TRANSACTION_TOOL,
            "transaction_id": transaction_id,
        },
        "steps": steps,
    }


def select_generic_edit_rollback_snapshots(
    *,
    transaction_id: str,
    mutation_snapshots: list[dict[str, Any]],
    snapshot_ids: list[str],
) -> list[dict[str, Any]]:
    """Return snapshots selected for one rollback operation."""
    requested_ids = {str(snapshot_id) for snapshot_id in snapshot_ids if snapshot_id}
    return [
        snapshot
        for snapshot in mutation_snapshots
        if str(snapshot.get("transaction_id")) == transaction_id
        and (not requested_ids or str(snapshot.get("id")) in requested_ids)
    ]


def build_generic_edit_rollback_step(
    preimage: dict[str, Any],
) -> dict[str, Any] | None:
    """Return one rollback step without embedding content in recovery plans."""
    path = str(preimage.get("path") or "")
    if not path or not bool(preimage.get("restorable")):
        return None
    if not bool(preimage.get("exists")):
        return {"operation": "delete_created_path", "path": path}
    if preimage.get("type") != "file" or preimage.get("content_encoding") != "utf-8":
        return None
    if "content" not in preimage:
        return None
    return {
        "operation": "restore_file",
        "path": path,
        "content": str(preimage.get("content")),
    }


def rollback_operation_for_plan(operation: dict[str, Any]) -> dict[str, Any]:
    """Return a recovery-plan-safe rollback operation without file contents."""
    return {key: value for key, value in operation.items() if key != "steps"} | {
        "steps": [
            {key: value for key, value in step.items() if key != "content"}
            for step in operation["steps"]
        ]
    }


def resolve_snapshot_workspace_path(project_dir: Path, path: str) -> Path:
    """Resolve a workspace path for preimage capture without escaping root."""
    try:
        validate_workspace_relative_path(path)
    except PatchProposalError as e:
        raise GenericEditRuntimeError(
            f"Mutation snapshot path is unsafe: {path}"
        ) from e
    candidate = Path(path)
    if candidate.is_absolute() or any(
        part in {"", ".", ".."} for part in candidate.parts
    ):
        raise GenericEditRuntimeError(f"Mutation snapshot path is unsafe: {path}")
    root = project_dir.resolve()
    target = (root / candidate).resolve()
    if target != root and root not in target.parents:
        raise GenericEditRuntimeError(
            f"Mutation snapshot path escapes workspace: {path}"
        )
    return target


def action_path_values(action: dict[str, Any]) -> list[str]:
    """Return workspace path fields from an action without reading sensitive data."""
    paths: list[str] = []
    for field_name in ("path", "source", "destination"):
        value = action.get(field_name)
        if isinstance(value, str) and value:
            paths.append(value)
    if action_tool(action) == "apply_patch" and isinstance(action.get("patch"), str):
        paths.extend(sorted(extract_patch_paths(action["patch"])))
    raw_paths = action.get("paths")
    if isinstance(raw_paths, list):
        paths.extend(path for path in raw_paths if isinstance(path, str) and path)
    return list(dict.fromkeys(paths))


def result_path_values(
    result: ToolActionResult,
    *,
    prefer_mutated: bool = False,
) -> list[str]:
    """Return workspace paths reported by an action result."""
    field_names = (
        ("mutated_paths", "restored_paths", "deleted_paths", "affected_paths")
        if prefer_mutated
        else ("affected_paths", "mutated_paths", "restored_paths", "deleted_paths")
    )
    paths: list[str] = []
    for field_name in field_names:
        value = result.data.get(field_name)
        if isinstance(value, list):
            paths.extend(str(path) for path in value if path)
    return list(dict.fromkeys(paths))


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
    mutation_snapshots: list[dict[str, Any]] | None = None,
    mcp_support: dict[str, Any] | None = None,
    resume_metadata: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Persist trace/result artifacts for a generic edit run."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    paths = generic_edit_artifact_paths(artifact_dir)
    timestamp = datetime.now(UTC).isoformat()
    mutation_snapshots = list(mutation_snapshots or [])
    trace_summary = summarize_generic_edit_trace(trace)
    transaction_summary = summarize_generic_edit_transactions(trace)
    transaction_group_summary = summarize_generic_edit_transaction_groups(
        transaction_summary=transaction_summary,
        mutation_snapshots=mutation_snapshots,
    )
    events = build_generic_edit_events(
        trace=trace,
        provider_name=provider_name,
        subtask_id=subtask_id,
        transaction_group_summary=transaction_group_summary,
        resume_metadata=resume_metadata,
    )
    recovery_plan = build_generic_edit_recovery_plan(
        transaction_summary=transaction_summary,
        transaction_group_summary=transaction_group_summary,
        plan_path=paths["recovery_plan"],
        mutation_snapshot_path=paths["mutation_snapshots"],
        mutation_snapshots=mutation_snapshots,
    )
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
        artifact_refs={
            "trace": paths["trace"],
            "observation": observation_path,
            "checkpoint": paths["recovery_checkpoint"],
            "mutation_snapshots": paths["mutation_snapshots"],
            "transaction_groups": paths["transaction_groups"],
        },
        recovery_plan=recovery_plan,
        mutation_snapshots=mutation_snapshots,
        transaction_group_summary=transaction_group_summary,
        mcp_support=mcp_support,
    )
    session_state = build_generic_edit_session_state(
        timestamp=timestamp,
        provider_name=provider_name,
        subtask_id=subtask_id,
        status=status,
        stop_reason=stop_reason,
        message=message,
        trace_summary=trace_summary,
        iteration_count=len(trace),
        transaction_summary=transaction_summary,
        transaction_group_summary=transaction_group_summary,
        artifact_refs={
            "trace": paths["trace"],
            "events": paths["events"],
            "checkpoint": paths["recovery_checkpoint"],
            "recovery_plan": paths["recovery_plan"],
            "mutation_snapshots": paths["mutation_snapshots"],
            "transaction_groups": paths["transaction_groups"],
        },
        recovery_checkpoint=recovery_checkpoint,
        recovery_plan=recovery_plan,
        mutation_snapshots=mutation_snapshots,
        resume_metadata=resume_metadata,
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
    write_generic_edit_events(paths["events"], events)
    write_json_artifact(paths["session_state"], session_state)
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
        transaction_group_summary=transaction_group_summary,
        tests=tests,
        risks=risks,
        mcp_support=mcp_support,
        recovery_checkpoint=recovery_checkpoint,
        recovery_plan=recovery_plan,
        mutation_snapshot_path=paths["mutation_snapshots"],
        mutation_snapshots=mutation_snapshots,
        transaction_group_path=paths["transaction_groups"],
        event_path=paths["events"],
        events=events,
        session_state_path=paths["session_state"],
        artifact_manifest_path=paths["artifact_manifest"],
        resume_metadata=resume_metadata,
    )
    if observation_path is not None:
        result_payload["observation_artifact"] = str(observation_path)
    if recovery_checkpoint is not None:
        write_json_artifact(paths["recovery_checkpoint"], recovery_checkpoint)
    else:
        clear_generic_edit_recovery_checkpoint(paths["recovery_checkpoint"])
    if recovery_plan is not None:
        write_json_artifact(paths["recovery_plan"], recovery_plan)
    else:
        clear_generic_edit_recovery_checkpoint(paths["recovery_plan"])
    if mutation_snapshots:
        write_generic_edit_mutation_snapshots(
            paths["mutation_snapshots"],
            timestamp=timestamp,
            provider_name=provider_name,
            subtask_id=subtask_id,
            mutation_snapshots=mutation_snapshots,
        )
    else:
        clear_generic_edit_recovery_checkpoint(paths["mutation_snapshots"])
    if transaction_group_summary["transaction_group_count"]:
        write_generic_edit_transaction_groups(
            paths["transaction_groups"],
            timestamp=timestamp,
            provider_name=provider_name,
            subtask_id=subtask_id,
            transaction_group_summary=transaction_group_summary,
        )
    else:
        clear_generic_edit_recovery_checkpoint(paths["transaction_groups"])
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
            transaction_group_summary=transaction_group_summary,
            tests=tests,
            risks=risks,
            mcp_support=mcp_support,
            recovery_checkpoint=recovery_checkpoint,
            recovery_plan=recovery_plan,
            mutation_snapshot_path=paths["mutation_snapshots"],
            mutation_snapshots=mutation_snapshots,
            transaction_group_path=paths["transaction_groups"],
            event_path=paths["events"],
            events=events,
            artifact_manifest_path=paths["artifact_manifest"],
        ),
        encoding="utf-8",
    )
    artifact_manifest = build_generic_edit_artifact_manifest(
        timestamp=timestamp,
        provider_name=provider_name,
        subtask_id=subtask_id,
        status=status,
        stop_reason=stop_reason,
        paths=paths,
        observation_path=observation_path,
        trace_summary=trace_summary,
        iteration_count=len(trace),
        transaction_summary=transaction_summary,
        transaction_group_summary=transaction_group_summary,
        recovery_checkpoint=recovery_checkpoint,
        recovery_plan=recovery_plan,
        mutation_snapshots=mutation_snapshots,
        events=events,
        resume_metadata=resume_metadata,
        mcp_support=mcp_support,
    )
    write_json_artifact(paths["artifact_manifest"], artifact_manifest)

    artifacts = generic_edit_artifact_payload(paths)
    artifacts["generic_edit_events"] = str(paths["events"])
    artifacts["generic_edit_session_state"] = str(paths["session_state"])
    artifacts["generic_edit_artifact_manifest"] = str(paths["artifact_manifest"])
    if observation_path is not None:
        artifacts["generic_edit_observations"] = str(observation_path)
    if recovery_checkpoint is not None:
        artifacts["generic_edit_recovery_checkpoint"] = str(
            paths["recovery_checkpoint"]
        )
    if recovery_plan is not None:
        artifacts["generic_edit_recovery_plan"] = str(paths["recovery_plan"])
    if mutation_snapshots:
        artifacts["generic_edit_mutation_snapshots"] = str(paths["mutation_snapshots"])
    if transaction_group_summary["transaction_group_count"]:
        artifacts["generic_edit_transaction_groups"] = str(paths["transaction_groups"])
    return artifacts


def generic_edit_artifact_paths(artifact_dir: Path) -> dict[str, Path]:
    return {
        "trace": artifact_dir / "generic_edit_trace.json",
        "events": artifact_dir / "generic_edit_events.jsonl",
        "session_state": artifact_dir / "generic_edit_session_state.json",
        "timeline": artifact_dir / "generic_edit_timeline.json",
        "transactions": artifact_dir / "generic_edit_transactions.jsonl",
        "transaction_groups": artifact_dir / "generic_edit_transaction_groups.json",
        "recovery_checkpoint": artifact_dir / "generic_edit_recovery_checkpoint.json",
        "recovery_plan": artifact_dir / "generic_edit_recovery_plan.json",
        "mutation_snapshots": artifact_dir / "generic_edit_mutation_snapshots.json",
        "summary": artifact_dir / "generic_edit_summary.md",
        "result": artifact_dir / "generic_edit_result.json",
        "artifact_manifest": artifact_dir / "generic_edit_artifact_manifest.json",
    }


def write_json_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(  # NOSONAR - artifact paths are constructed internally.
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_generic_edit_mutation_snapshots(
    path: Path,
    *,
    timestamp: str,
    provider_name: str,
    subtask_id: str | None,
    mutation_snapshots: list[dict[str, Any]],
) -> None:
    """Persist pre-mutation file snapshots for repair/rollback recovery."""
    write_json_artifact(
        path,
        {
            "artifact_type": "generic_edit_mutation_snapshots",
            "timestamp": timestamp,
            "provider": provider_name,
            "subtask_id": subtask_id,
            "snapshot_count": len(mutation_snapshots),
            "snapshots": mutation_snapshots,
        },
    )


def write_generic_edit_transaction_groups(
    path: Path,
    *,
    timestamp: str,
    provider_name: str,
    subtask_id: str | None,
    transaction_group_summary: dict[str, Any],
) -> None:
    """Persist partial-failure transaction groups for UI/recovery consumers."""
    write_json_artifact(
        path,
        {
            "artifact_type": "generic_edit_transaction_groups",
            "timestamp": timestamp,
            "provider": provider_name,
            "subtask_id": subtask_id,
            "group_count": transaction_group_summary["transaction_group_count"],
            "status_counts": transaction_group_summary[
                "transaction_group_status_counts"
            ],
            "unresolved_group_count": transaction_group_summary[
                "unresolved_transaction_group_count"
            ],
            "unresolved_group_ids": transaction_group_summary[
                "unresolved_transaction_group_ids"
            ],
            "recovery_attempt_count": transaction_group_summary[
                "recovery_attempt_count"
            ],
            "failed_recovery_attempt_count": transaction_group_summary[
                "failed_recovery_attempt_count"
            ],
            "recovery_outcome_count": transaction_group_summary[
                "recovery_outcome_count"
            ],
            "recovery_outcomes": transaction_group_summary["recovery_outcomes"],
            "transaction_groups": transaction_group_summary["transaction_groups"],
        },
    )


def write_generic_edit_events(path: Path, events: list[dict[str, Any]]) -> None:
    """Persist normalized generic_edit events for UI/control-plane consumers."""
    path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )


def build_generic_edit_session_state(
    *,
    timestamp: str,
    provider_name: str,
    subtask_id: str | None,
    status: str,
    stop_reason: str,
    message: str,
    trace_summary: dict[str, Any],
    iteration_count: int,
    transaction_summary: dict[str, Any],
    transaction_group_summary: dict[str, Any],
    artifact_refs: dict[str, Path],
    recovery_checkpoint: dict[str, Any] | None,
    recovery_plan: dict[str, Any] | None,
    mutation_snapshots: list[dict[str, Any]],
    resume_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the compact persisted state contract for resume/control-plane UI."""
    resumable = recovery_checkpoint is not None
    state: dict[str, Any] = {
        "artifact_type": "generic_edit_session_state",
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "stop_reason": stop_reason,
        "message": message,
        "resumed": resume_metadata is not None,
        "resumable": resumable,
        "loop": trace_summary["loop"],
        "iteration_count": iteration_count,
        "action_count": trace_summary["action_count"],
        "failed_action_count": trace_summary["failed_action_count"],
        "transaction_count": transaction_summary["transaction_count"],
        "transaction_group_count": transaction_group_summary["transaction_group_count"],
        "recovery_required": transaction_summary["recovery_required"],
        "recovery_resolved": transaction_summary["recovery_resolved"],
        "unresolved_partial_failure_ids": transaction_summary[
            "unresolved_partial_failure_ids"
        ],
        "unresolved_transaction_group_ids": transaction_group_summary[
            "unresolved_transaction_group_ids"
        ],
        "artifacts": {
            "trace": str(artifact_refs["trace"]),
            "events": str(artifact_refs["events"]),
        },
    }
    if resume_metadata is not None:
        state["resume"] = dict(resume_metadata)
    if recovery_plan is not None:
        state["artifacts"]["recovery_plan"] = recovery_plan["artifact_path"]
    if mutation_snapshots:
        state["artifacts"]["mutation_snapshots"] = str(
            artifact_refs["mutation_snapshots"]
        )
    if transaction_group_summary["transaction_group_count"]:
        state["artifacts"]["transaction_groups"] = str(
            artifact_refs["transaction_groups"]
        )
    if not resumable:
        state["resume_action"] = None
        state["resume_inputs"] = {}
        return state

    resume = recovery_checkpoint["resume"]
    state["resume_action"] = {
        "runtime": "generic_edit",
        "checkpoint_path": recovery_checkpoint["artifact_path"],
        "strategy": resume["strategy"],
        "next_iteration": recovery_checkpoint["next_iteration"],
    }
    state["resume_inputs"] = {
        "trace_artifact": str(artifact_refs["trace"]),
        "event_artifact": str(artifact_refs["events"]),
    }
    if recovery_plan is not None:
        state["resume_inputs"]["recovery_plan_artifact"] = recovery_plan[
            "artifact_path"
        ]
    if mutation_snapshots:
        state["resume_inputs"]["mutation_snapshot_artifact"] = str(
            artifact_refs["mutation_snapshots"]
        )
    return state


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
    transaction_group_summary: dict[str, Any],
    tests: list[str] | None,
    risks: list[str] | None,
    mcp_support: dict[str, Any] | None,
    recovery_checkpoint: dict[str, Any] | None,
    recovery_plan: dict[str, Any] | None,
    mutation_snapshot_path: Path,
    mutation_snapshots: list[dict[str, Any]],
    transaction_group_path: Path,
    event_path: Path,
    events: list[dict[str, Any]],
    session_state_path: Path,
    artifact_manifest_path: Path,
    resume_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = {
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "stop_reason": stop_reason,
        "message": message,
        "mcp_support": mcp_support,
        "resumed": resume_metadata is not None,
        **trace_summary,
        **transaction_summary,
        **transaction_group_summary,
        "iteration_count": len(trace),
        "tests": tests or [],
        "test_count": len(tests or []),
        "risks": risks or [],
        "risk_count": len(risks or []),
        "recoverable": recovery_checkpoint is not None,
        "mutation_snapshot_count": len(mutation_snapshots),
        "event_count": len(events),
        "event_artifact": str(event_path),
        "session_state_artifact": str(session_state_path),
        "artifact_manifest_artifact": str(artifact_manifest_path),
    }
    if resume_metadata is not None:
        payload["resume"] = dict(resume_metadata)
    if recovery_checkpoint is not None:
        payload.update(
            {
                "recovery_checkpoint_artifact": recovery_checkpoint["artifact_path"],
                "recovery_strategy": recovery_checkpoint["resume"]["strategy"],
            }
        )
    if recovery_plan is not None:
        payload["recovery_plan_artifact"] = recovery_plan["artifact_path"]
        payload["recovery_plan"] = recovery_plan
    if mutation_snapshots:
        payload["mutation_snapshot_artifact"] = str(mutation_snapshot_path)
    if transaction_group_summary["transaction_group_count"]:
        payload["transaction_group_artifact"] = str(transaction_group_path)
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


def compact_generic_edit_manifest_event(event: dict[str, Any]) -> dict[str, Any]:
    """Return a bounded event summary suitable for the artifact manifest."""
    compact: dict[str, Any] = {}
    for field in GENERIC_EDIT_ARTIFACT_MANIFEST_RECENT_EVENT_FIELDS:
        if field not in event:
            continue
        value = event.get(field)
        if isinstance(value, str):
            compact[field] = value[:300]
        elif isinstance(value, bool) or isinstance(value, int) or value is None:
            compact[field] = value
    return compact


def compact_generic_edit_native_tool_fallback(
    fallback: dict[str, Any],
) -> dict[str, Any]:
    """Return a stable native fallback summary for UI manifests."""
    return {
        "provider": str(fallback.get("provider") or "unknown")[:120],
        "from_loop": str(fallback.get("from_loop") or "native_tool_calls")[:120],
        "to_loop": str(fallback.get("to_loop") or "json_actions")[:120],
        "reason": str(fallback.get("reason") or "native_tool_request_failed")[:120],
        "message": str(fallback.get("message") or "")[:300],
        "tool_schema_count": int(fallback.get("tool_schema_count") or 0),
    }


def compact_generic_edit_native_tool_fallbacks(value: Any) -> list[dict[str, Any]]:
    """Return bounded native fallback summaries for UI manifests."""
    if not isinstance(value, list):
        return []
    fallbacks: list[dict[str, Any]] = []
    for fallback in value:
        if isinstance(fallback, dict):
            fallbacks.append(compact_generic_edit_native_tool_fallback(fallback))
    return fallbacks[:GENERIC_EDIT_ARTIFACT_MANIFEST_RECENT_EVENT_LIMIT]


def compact_generic_edit_manifest_recovery_action(
    action: dict[str, Any],
) -> dict[str, Any]:
    """Return a bounded recovery action summary for UI control planes."""
    compact: dict[str, Any] = {}
    for field in GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_ACTION_STRING_FIELDS:
        value = action.get(field)
        if isinstance(value, str):
            compact[field] = value[:300]
    for field in GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_ACTION_LIST_FIELDS:
        value = action.get(field)
        if not isinstance(value, list):
            continue
        compact[field] = [
            str(item)[:300] for item in value[:20] if isinstance(item, str)
        ]
    if isinstance(action.get("required_before_finish"), bool):
        compact["required_before_finish"] = action["required_before_finish"]
    return compact


def compact_generic_edit_manifest_recovery_actions(
    recovery_plan: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return bounded recovery next actions from a recovery plan."""
    if not isinstance(recovery_plan, dict):
        return []
    actions = recovery_plan.get("next_actions")
    if not isinstance(actions, list):
        return []
    compact_actions: list[dict[str, Any]] = []
    for action in actions[:GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_ACTION_LIMIT]:
        if not isinstance(action, dict):
            continue
        compact_action = compact_generic_edit_manifest_recovery_action(action)
        if compact_action:
            compact_actions.append(compact_action)
    return compact_actions


def build_generic_edit_manifest_recovery_summary(
    *,
    transaction_group_summary: dict[str, Any],
    recovery_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return aggregate recovery state for lightweight UI control planes."""
    policy = (
        recovery_plan.get("recovery_policy")
        if isinstance(recovery_plan, dict)
        and isinstance(recovery_plan.get("recovery_policy"), dict)
        else {}
    )
    warnings: list[str] = []
    for outcome in transaction_group_summary.get("recovery_outcomes") or []:
        if not isinstance(outcome, dict):
            continue
        policy_status = outcome.get("policy_status")
        if not isinstance(policy_status, dict):
            continue
        warnings.extend(str(warning) for warning in policy_status.get("warnings") or [])
    unresolved_group_ids = list(
        transaction_group_summary.get("unresolved_transaction_group_ids") or []
    )
    finish_blocked = bool(policy.get("finish_blocked")) or bool(unresolved_group_ids)
    status = str(policy.get("status") or "clean")
    if not finish_blocked and warnings:
        status = "resolved_with_warnings"
    return {
        "version": GENERIC_EDIT_RECOVERY_POLICY_VERSION,
        "status": status,
        "finish_blocked": finish_blocked,
        "unresolved_transaction_group_count": int(
            transaction_group_summary.get("unresolved_transaction_group_count") or 0
        ),
        "unresolved_transaction_group_ids": unresolved_group_ids,
        "warning_count": len(warnings),
        "warnings": warnings,
        "resolution_strategies": list(policy.get("resolution_strategies") or []),
        "recommended_verification_tools": list(
            policy.get("recommended_verification_tools")
            or GENERIC_EDIT_RECOVERY_VERIFICATION_TOOLS
        ),
    }


def build_generic_edit_manifest_resume_action(
    recovery_checkpoint: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return the canonical resume action for manifest/control-plane consumers."""
    if not isinstance(recovery_checkpoint, dict):
        return None
    resume = recovery_checkpoint.get("resume")
    if not isinstance(resume, dict):
        return None
    return {
        "runtime": "generic_edit",
        "checkpoint_path": recovery_checkpoint["artifact_path"],
        "strategy": resume["strategy"],
        "next_iteration": recovery_checkpoint["next_iteration"],
    }


def build_generic_edit_manifest_resume_inputs(
    *,
    recovery_checkpoint: dict[str, Any] | None,
    paths: dict[str, Path],
    recovery_plan: dict[str, Any] | None,
    mutation_snapshots: list[dict[str, Any]],
) -> dict[str, str]:
    """Return artifact inputs needed by a generic_edit resume action."""
    if recovery_checkpoint is None:
        return {}
    resume_inputs = {
        "trace_artifact": str(paths["trace"]),
        "event_artifact": str(paths["events"]),
    }
    if recovery_plan is not None:
        resume_inputs["recovery_plan_artifact"] = recovery_plan["artifact_path"]
    if mutation_snapshots:
        resume_inputs["mutation_snapshot_artifact"] = str(paths["mutation_snapshots"])
    return resume_inputs


def build_generic_edit_artifact_manifest(
    *,
    timestamp: str,
    provider_name: str,
    subtask_id: str | None,
    status: str,
    stop_reason: str,
    paths: dict[str, Path],
    observation_path: Path | None,
    trace_summary: dict[str, Any],
    iteration_count: int,
    transaction_summary: dict[str, Any],
    transaction_group_summary: dict[str, Any],
    recovery_checkpoint: dict[str, Any] | None,
    recovery_plan: dict[str, Any] | None,
    mutation_snapshots: list[dict[str, Any]],
    events: list[dict[str, Any]],
    resume_metadata: dict[str, Any] | None,
    mcp_support: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build one stable manifest for generic_edit UI/control-plane artifacts."""
    artifacts = generic_edit_manifest_artifact_entries(
        paths=paths,
        observation_path=observation_path,
        has_recovery_checkpoint=recovery_checkpoint is not None,
        has_recovery_plan=recovery_plan is not None,
        has_mutation_snapshots=bool(mutation_snapshots),
        has_transaction_groups=bool(
            transaction_group_summary["transaction_group_count"]
        ),
    )
    return {
        "artifact_type": "generic_edit_artifact_manifest",
        "schema_version": GENERIC_EDIT_ARTIFACT_MANIFEST_SCHEMA_VERSION,
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "stop_reason": stop_reason,
        "entrypoints": {
            "result": str(paths["result"]),
            "summary": str(paths["summary"]),
            "events": str(paths["events"]),
            "session_state": str(paths["session_state"]),
            "trace": str(paths["trace"]),
        },
        "flags": {
            "recoverable": recovery_checkpoint is not None,
            "resumable": recovery_checkpoint is not None,
            "resumed": resume_metadata is not None,
            "recovery_required": transaction_summary["recovery_required"],
            "recovery_resolved": transaction_summary["recovery_resolved"],
            "has_recovery_plan": recovery_plan is not None,
            "has_mutation_snapshots": bool(mutation_snapshots),
            "has_transaction_groups": bool(
                transaction_group_summary["transaction_group_count"]
            ),
        },
        "counts": {
            "iteration_count": iteration_count,
            "action_count": trace_summary["action_count"],
            "failed_action_count": trace_summary["failed_action_count"],
            "native_tool_fallback_count": int(
                trace_summary.get("native_tool_fallback_count") or 0
            ),
            "event_count": len(events),
            "transaction_count": transaction_summary["transaction_count"],
            "transaction_group_count": transaction_group_summary[
                "transaction_group_count"
            ],
            "mutation_snapshot_count": len(mutation_snapshots),
            "recovery_attempt_count": transaction_group_summary[
                "recovery_attempt_count"
            ],
            "failed_recovery_attempt_count": transaction_group_summary[
                "failed_recovery_attempt_count"
            ],
        },
        "recent_events": [
            compact_generic_edit_manifest_event(event)
            for event in events[-GENERIC_EDIT_ARTIFACT_MANIFEST_RECENT_EVENT_LIMIT:]
        ],
        "native_tool_fallbacks": compact_generic_edit_native_tool_fallbacks(
            trace_summary.get("native_tool_fallbacks")
        ),
        "recovery_actions": compact_generic_edit_manifest_recovery_actions(
            recovery_plan
        ),
        "recovery_summary": build_generic_edit_manifest_recovery_summary(
            transaction_group_summary=transaction_group_summary,
            recovery_plan=recovery_plan,
        ),
        "artifacts": artifacts,
        "mcp_support": mcp_support,
        "resume_action": build_generic_edit_manifest_resume_action(recovery_checkpoint),
        "resume_inputs": build_generic_edit_manifest_resume_inputs(
            recovery_checkpoint=recovery_checkpoint,
            paths=paths,
            recovery_plan=recovery_plan,
            mutation_snapshots=mutation_snapshots,
        ),
        "resume": dict(resume_metadata) if resume_metadata is not None else None,
    }


def generic_edit_manifest_artifact_entries(
    *,
    paths: dict[str, Path],
    observation_path: Path | None,
    has_recovery_checkpoint: bool,
    has_recovery_plan: bool,
    has_mutation_snapshots: bool,
    has_transaction_groups: bool,
) -> list[dict[str, Any]]:
    """Return manifest entries in a stable UI-friendly order."""
    entries = [
        generic_edit_manifest_entry(
            "generic_edit_artifact_manifest",
            paths["artifact_manifest"],
            kind="manifest",
            active=True,
            required=True,
            present=True,
        ),
        generic_edit_manifest_entry(
            "generic_edit_result",
            paths["result"],
            kind="result",
            active=True,
            required=True,
        ),
        generic_edit_manifest_entry(
            "generic_edit_summary",
            paths["summary"],
            kind="summary",
            active=True,
            required=True,
        ),
        generic_edit_manifest_entry(
            "generic_edit_trace",
            paths["trace"],
            kind="trace",
            active=True,
            required=True,
        ),
        generic_edit_manifest_entry(
            "generic_edit_events",
            paths["events"],
            kind="events",
            active=True,
            required=True,
        ),
        generic_edit_manifest_entry(
            "generic_edit_session_state",
            paths["session_state"],
            kind="session_state",
            active=True,
            required=True,
        ),
        generic_edit_manifest_entry(
            "generic_edit_timeline",
            paths["timeline"],
            kind="timeline",
            active=True,
            required=True,
        ),
        generic_edit_manifest_entry(
            "generic_edit_transactions",
            paths["transactions"],
            kind="transactions",
            active=True,
            required=True,
        ),
        generic_edit_manifest_entry(
            "generic_edit_observations",
            observation_path,
            kind="observations",
            active=observation_path is not None,
            required=False,
        ),
        generic_edit_manifest_entry(
            "generic_edit_recovery_checkpoint",
            paths["recovery_checkpoint"],
            kind="checkpoint",
            active=has_recovery_checkpoint,
            required=False,
        ),
        generic_edit_manifest_entry(
            "generic_edit_recovery_plan",
            paths["recovery_plan"],
            kind="recovery_plan",
            active=has_recovery_plan,
            required=False,
        ),
        generic_edit_manifest_entry(
            "generic_edit_mutation_snapshots",
            paths["mutation_snapshots"],
            kind="mutation_snapshots",
            active=has_mutation_snapshots,
            required=False,
        ),
        generic_edit_manifest_entry(
            "generic_edit_transaction_groups",
            paths["transaction_groups"],
            kind="transaction_groups",
            active=has_transaction_groups,
            required=False,
        ),
    ]
    return [entry for entry in entries if entry["path"]]


def generic_edit_manifest_entry(
    name: str,
    path: Path | None,
    *,
    kind: str,
    active: bool,
    required: bool,
    present: bool | None = None,
) -> dict[str, Any]:
    """Return one artifact manifest entry."""
    if path is None:
        return {
            "name": name,
            "kind": kind,
            "path": None,
            "active": active,
            "required": required,
            "present": False,
        }
    return {
        "name": name,
        "kind": kind,
        "path": str(path),
        "active": active,
        "required": required,
        "present": path.exists() if present is None else present,
    }


def build_generic_edit_summary_markdown(
    *,
    provider_name: str,
    subtask_id: str | None,
    status: str,
    stop_reason: str,
    summary: str,
    trace_summary: dict[str, Any],
    transaction_summary: dict[str, Any],
    transaction_group_summary: dict[str, Any],
    tests: list[str] | None,
    risks: list[str] | None,
    mcp_support: dict[str, Any] | None,
    recovery_checkpoint: dict[str, Any] | None,
    recovery_plan: dict[str, Any] | None,
    mutation_snapshot_path: Path,
    mutation_snapshots: list[dict[str, Any]],
    transaction_group_path: Path,
    event_path: Path,
    events: list[dict[str, Any]],
    artifact_manifest_path: Path,
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
        *generic_edit_transaction_group_lines(
            transaction_group_summary=transaction_group_summary,
            transaction_group_path=transaction_group_path,
        ),
        *generic_edit_event_lines(event_path=event_path, events=events),
        *generic_edit_artifact_manifest_lines(artifact_manifest_path),
        *generic_edit_recovery_plan_lines(recovery_plan),
        *generic_edit_mutation_snapshot_lines(
            mutation_snapshot_path=mutation_snapshot_path,
            mutation_snapshots=mutation_snapshots,
        ),
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
    artifact_refs: dict[str, Path | None],
    recovery_plan: dict[str, Any] | None,
    mutation_snapshots: list[dict[str, Any]],
    transaction_group_summary: dict[str, Any],
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
    trace_path = artifact_refs["trace"]
    checkpoint_path = artifact_refs["checkpoint"]
    mutation_snapshot_path = artifact_refs["mutation_snapshots"]
    transaction_group_path = artifact_refs["transaction_groups"]
    observation_path = artifact_refs.get("observation")
    if (
        trace_path is None
        or checkpoint_path is None
        or mutation_snapshot_path is None
        or transaction_group_path is None
    ):
        raise GenericEditRuntimeError(
            "Generic edit recovery artifact paths are incomplete."
        )
    checkpoint = {
        "timestamp": timestamp,
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": status,
        "stop_reason": stop_reason,
        "message": message,
        "artifact_path": str(checkpoint_path),
        "trace_artifact": str(trace_path),
        "observation_artifact": (
            str(observation_path) if observation_path is not None else None
        ),
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
                recovery_plan=recovery_plan,
            ),
        },
        "recent_actions": list(trace_summary.get("action_timeline") or [])[-10:],
        "transaction_summary": transaction_summary,
        "transaction_group_summary": transaction_group_summary,
        "unresolved_partial_failure_ids": transaction_summary[
            "unresolved_partial_failure_ids"
        ],
        "unresolved_transaction_group_ids": transaction_group_summary[
            "unresolved_transaction_group_ids"
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
    if recovery_plan is not None:
        checkpoint["recovery_plan_artifact"] = recovery_plan["artifact_path"]
        checkpoint["recovery_plan"] = recovery_plan
    if mutation_snapshots:
        checkpoint["mutation_snapshot_artifact"] = str(mutation_snapshot_path)
        checkpoint["mutation_snapshot_count"] = len(mutation_snapshots)
    if transaction_group_summary["transaction_group_count"]:
        checkpoint["transaction_group_artifact"] = str(transaction_group_path)
        checkpoint["transaction_group_count"] = transaction_group_summary[
            "transaction_group_count"
        ]
    return checkpoint


def build_generic_edit_recovery_plan(
    *,
    transaction_summary: dict[str, Any],
    transaction_group_summary: dict[str, Any],
    plan_path: Path,
    mutation_snapshot_path: Path,
    mutation_snapshots: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Build a machine-readable recovery plan for unresolved partial failures."""
    unresolved_ids = transaction_summary["unresolved_partial_failure_ids"]
    if not unresolved_ids:
        return None

    unresolved_transactions = [
        transaction
        for transaction in transaction_summary["transactions"]
        if str(transaction.get("id")) in unresolved_ids
    ]
    rollback_operations = [
        rollback_operation_for_plan(
            build_generic_edit_rollback_operation(
                transaction_id=str(transaction.get("id") or ""),
                mutation_snapshots=mutation_snapshots,
                snapshot_ids=list(transaction.get("mutation_snapshot_ids") or []),
            )
        )
        for transaction in unresolved_transactions
    ]
    plan = {
        "strategy": "repair_or_rollback",
        "artifact_path": str(plan_path),
        "unresolved_transaction_ids": unresolved_ids,
        "unresolved_transactions": unresolved_transactions,
        "rollback_operations": rollback_operations,
        "unresolved_transaction_group_ids": transaction_group_summary[
            "unresolved_transaction_group_ids"
        ],
        "recovery_policy": build_generic_edit_recovery_plan_policy(
            transaction_summary=transaction_summary,
            transaction_group_summary=transaction_group_summary,
        ),
        "unresolved_transaction_groups": [
            group
            for group in transaction_group_summary["transaction_groups"]
            if group["status"] == "unresolved"
        ],
        "next_actions": [
            action
            for group in transaction_group_summary["transaction_groups"]
            if group["status"] == "unresolved"
            for action in group.get("next_actions", [])
        ],
        "recommended_next_actions": [
            "Inspect current git status.",
            "Inspect diffs for mutated paths.",
            "Choose either repair or rollback for each unresolved transaction.",
            "Use rollback_transaction when a rollback operation is restorable.",
            "Run focused verification before finish.",
        ],
    }
    if mutation_snapshots:
        plan["mutation_snapshot_artifact"] = str(mutation_snapshot_path)
        plan["mutation_snapshot_count"] = len(mutation_snapshots)
    return plan


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


def load_generic_edit_session_state(
    session_state_path: Path,
    *,
    expected_checkpoint_path: Path,
) -> dict[str, Any]:
    """Load and validate the generic_edit session-state resume manifest."""
    try:
        payload = json.loads(session_state_path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise GenericEditRuntimeError(
            f"Generic edit session state not found: {session_state_path}"
        ) from e
    except json.JSONDecodeError as e:
        raise GenericEditRuntimeError(
            f"Generic edit session state is not valid JSON: {e}"
        ) from e

    if not isinstance(payload, dict):
        raise GenericEditRuntimeError(
            "Generic edit session state must be a JSON object."
        )
    if payload.get("artifact_type") != "generic_edit_session_state":
        raise GenericEditRuntimeError(
            "Generic edit session state has unexpected artifact type."
        )
    if payload.get("resumable") is not True:
        raise GenericEditRuntimeError("Generic edit session state is not resumable.")
    resume_action = payload.get("resume_action")
    if not isinstance(resume_action, dict):
        raise GenericEditRuntimeError(
            "Generic edit session state is missing resume action metadata."
        )
    if resume_action.get("runtime") != "generic_edit":
        raise GenericEditRuntimeError(
            "Generic edit session state targets an unexpected runtime."
        )
    checkpoint_path_value = resume_action.get("checkpoint_path")
    if not isinstance(checkpoint_path_value, str) or not checkpoint_path_value:
        raise GenericEditRuntimeError(
            "Generic edit session state is missing checkpoint path."
        )
    if Path(checkpoint_path_value).resolve() != expected_checkpoint_path.resolve():
        raise GenericEditRuntimeError(
            "Generic edit session state must reference the canonical recovery checkpoint."
        )
    return payload


def load_generic_edit_mutation_snapshots(snapshot_path: Path) -> list[dict[str, Any]]:
    """Load persisted mutation snapshots from the canonical artifact path."""
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        raise GenericEditRuntimeError(
            f"Generic edit mutation snapshot artifact is not valid JSON: {e}"
        ) from e
    if not isinstance(payload, dict):
        raise GenericEditRuntimeError(
            "Generic edit mutation snapshot artifact must be a JSON object."
        )
    if payload.get("artifact_type") != "generic_edit_mutation_snapshots":
        raise GenericEditRuntimeError(
            "Generic edit mutation snapshot artifact has unexpected type."
        )
    snapshots = payload.get("snapshots")
    if not isinstance(snapshots, list):
        raise GenericEditRuntimeError(
            "Generic edit mutation snapshot artifact is missing snapshots."
        )
    return [snapshot for snapshot in snapshots if isinstance(snapshot, dict)]


def resolve_generic_edit_resume_checkpoint_path(
    *,
    checkpoint_path: Path,
    spec_dir: Path,
) -> Path:
    """Return the canonical recovery checkpoint path for a generic_edit resume."""
    expected_path = (
        spec_dir / "artifacts" / "generic_edit_recovery_checkpoint.json"
    ).resolve()
    expected_session_state_path = (
        spec_dir / "artifacts" / "generic_edit_session_state.json"
    ).resolve()
    requested_path = checkpoint_path.resolve()
    if requested_path == expected_path:
        return expected_path
    if requested_path == expected_session_state_path:
        load_generic_edit_session_state(
            expected_session_state_path,
            expected_checkpoint_path=expected_path,
        )
        return expected_path
    raise GenericEditRuntimeError(
        "Generic edit resume checkpoint must be the canonical checkpoint or "
        "session state artifact path."
    )


def generic_edit_trace_path_for_checkpoint(checkpoint_path: Path) -> Path:
    """Return the trusted trace path colocated with a recovery checkpoint."""
    return checkpoint_path.parent / "generic_edit_trace.json"


def generic_edit_mutation_snapshot_path_for_checkpoint(checkpoint_path: Path) -> Path:
    """Return the trusted mutation snapshot path colocated with a checkpoint."""
    return checkpoint_path.parent / "generic_edit_mutation_snapshots.json"


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

    lines = [
        prompt,
        "",
        f"Recovery checkpoint artifact: {checkpoint.get('artifact_path')}",
        f"Previous trace artifact: {trace_path}",
        f"Resume strategy: {resume.get('strategy', 'unknown')}",
    ]
    mutation_snapshot_artifact = checkpoint.get("mutation_snapshot_artifact")
    if isinstance(mutation_snapshot_artifact, str) and mutation_snapshot_artifact:
        lines.append(f"Mutation snapshot artifact: {mutation_snapshot_artifact}")
    lines.append(
        "Use the previous trace as already completed context; inspect "
        "current workspace state before any new mutation."
    )
    return "\n".join(lines)


def build_generic_edit_resume_metadata(
    *,
    checkpoint: dict[str, Any],
    checkpoint_path: Path,
    trace_path: Path,
    start_iteration: int,
) -> dict[str, Any]:
    """Return compact provenance for a run resumed from a checkpoint."""
    resume = (
        checkpoint.get("resume") if isinstance(checkpoint.get("resume"), dict) else {}
    )
    metadata: dict[str, Any] = {
        "checkpoint_artifact": str(checkpoint_path),
        "trace_artifact": str(trace_path),
        "strategy": str(resume.get("strategy") or "unknown"),
        "start_iteration": start_iteration,
        "previous_status": checkpoint.get("status"),
        "previous_stop_reason": checkpoint.get("stop_reason"),
    }
    for key in (
        "recovery_plan_artifact",
        "mutation_snapshot_artifact",
        "transaction_group_artifact",
    ):
        value = checkpoint.get(key)
        if isinstance(value, str) and value:
            metadata[key] = value
    return metadata


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
    if stop_reason in {"cancelled", "max_iterations"}:
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
    recovery_plan: dict[str, Any] | None,
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
                "Use the recovery plan to repair or rollback mutated path(s): "
                + ", ".join(
                    transaction_summary["last_partial_failure_mutated_paths"]
                    or transaction_summary["last_partial_failure_affected_paths"]
                    or ["."]
                ),
                "Do not call finish until the workspace is consistent.",
            ]
        )
        if recovery_plan is not None:
            prompt_lines.append(
                f"Recovery plan artifact: {recovery_plan['artifact_path']}"
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


def generic_edit_recovery_plan_lines(
    recovery_plan: dict[str, Any] | None,
) -> list[str]:
    """Render active repair/rollback plan metadata for the markdown artifact."""
    if recovery_plan is None:
        return []
    return [
        "",
        "## Recovery Plan",
        "",
        f"- Strategy: `{recovery_plan['strategy']}`",
        f"- Plan: `{recovery_plan['artifact_path']}`",
        "- Unresolved transactions: "
        + ", ".join(recovery_plan["unresolved_transaction_ids"]),
    ]


def generic_edit_mutation_snapshot_lines(
    *,
    mutation_snapshot_path: Path,
    mutation_snapshots: list[dict[str, Any]],
) -> list[str]:
    """Render mutation preimage artifact metadata for recovery summaries."""
    if not mutation_snapshots:
        return []
    return [
        "",
        "## Mutation Snapshots",
        "",
        f"- Snapshot count: {len(mutation_snapshots)}",
        f"- Artifact: `{mutation_snapshot_path}`",
    ]


def generic_edit_subtask_lines(subtask_id: str | None) -> list[str]:
    return [f"Subtask: {subtask_id}"] if subtask_id else []


def generic_edit_mcp_lines(mcp_support: dict[str, Any] | None) -> list[str]:
    if not mcp_support:
        return []

    def bridge_server_line(label: str, servers: Any) -> str | None:
        if not servers:
            return None
        return f"- MCP {label} servers: " + ", ".join(str(server) for server in servers)

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
        recommended_runtime_path = bridge_plan.get("recommended_runtime_path")
        if recommended_runtime_path:
            lines.append(
                f"- MCP recommended runtime path: `{recommended_runtime_path}`."
            )
        native_required = bridge_plan.get("native_required_servers") or []
        local_bridge_required = bridge_plan.get("local_bridge_required_servers") or []
        external_bridge_required = (
            bridge_plan.get("external_bridge_required_servers") or []
        )
        unsupported = bridge_plan.get("unsupported_servers") or []
        for line in (
            bridge_server_line("native-required", native_required),
            bridge_server_line("local-bridge-required", local_bridge_required),
            bridge_server_line("external-bridge-required", external_bridge_required),
            bridge_server_line("unsupported", unsupported),
        ):
            if line:
                lines.append(line)
    server_statuses = mcp_support.get("server_statuses")
    if isinstance(server_statuses, list):
        for status in server_statuses:
            if not isinstance(status, dict):
                continue
            server = status.get("display_name") or status.get("server")
            if not server:
                continue
            availability = status.get("availability", "unknown")
            runtime_path = status.get("runtime_path", "unknown")
            reason = status.get("reason")
            line = f"- MCP server `{server}`: {availability} via `{runtime_path}`"
            if reason:
                line += f" - {reason}"
            lines.append(line)
    bridge = mcp_support.get("bridge")
    if isinstance(bridge, dict):
        permission_policy = bridge.get("permission_policy")
        if isinstance(permission_policy, dict):
            mode = permission_policy.get("mode", "unknown")
            allowed_permissions = permission_policy.get("allowed_permissions")
            if allowed_permissions:
                allowed = ", ".join(
                    str(permission) for permission in allowed_permissions
                )
                lines.append(f"- MCP permission policy: `{mode}`; allowed {allowed}.")
            else:
                lines.append(f"- MCP permission policy: `{mode}`.")
        tool_policies = bridge.get("tool_policies")
        if isinstance(tool_policies, list) and tool_policies:
            mutating_count = sum(
                1
                for policy in tool_policies
                if isinstance(policy, dict) and policy.get("mutating") is True
            )
            audit_required_count = sum(
                1
                for policy in tool_policies
                if isinstance(policy, dict)
                and policy.get("audit_required") is not False
            )
            lines.append(
                "- MCP tool policies: "
                f"{len(tool_policies)} tools; "
                f"{mutating_count} mutating; "
                f"{audit_required_count} audit-required."
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


def generic_edit_transaction_group_lines(
    *,
    transaction_group_summary: dict[str, Any],
    transaction_group_path: Path,
) -> list[str]:
    """Render transaction group summary metadata for recovery/UI review."""
    if not transaction_group_summary["transaction_group_count"]:
        return []
    unresolved_count = transaction_group_summary["unresolved_transaction_group_count"]
    return [
        "",
        "## Transaction Groups",
        "",
        f"- Groups: {transaction_group_summary['transaction_group_count']}",
        f"- Unresolved groups: {unresolved_count}",
        f"- Artifact: `{transaction_group_path}`",
    ]


def generic_edit_event_lines(
    *,
    event_path: Path,
    events: list[dict[str, Any]],
) -> list[str]:
    """Render normalized event stream metadata for UI/debug review."""
    if not events:
        return []
    return [
        "",
        "## Runtime Events",
        "",
        f"- Events: {len(events)}",
        f"- Artifact: `{event_path}`",
    ]


def generic_edit_artifact_manifest_lines(artifact_manifest_path: Path) -> list[str]:
    """Render the stable artifact manifest entrypoint for control-plane UIs."""
    return [
        "",
        "## Artifact Manifest",
        "",
        f"- Manifest: `{artifact_manifest_path}`",
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
        "generic_edit_events": str(paths["events"]),
        "generic_edit_session_state": str(paths["session_state"]),
        "generic_edit_artifact_manifest": str(paths["artifact_manifest"]),
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


def build_generic_edit_events(
    *,
    trace: list[dict[str, Any]],
    provider_name: str,
    subtask_id: str | None,
    transaction_group_summary: dict[str, Any],
    resume_metadata: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Build normalized runtime events for UI/control-plane consumers."""
    events: list[dict[str, Any]] = []
    if resume_metadata is not None:
        events.append(
            build_generic_edit_resume_event(
                resume_metadata=resume_metadata,
                provider_name=provider_name,
                subtask_id=subtask_id,
            )
        )
    for iteration in trace:
        fallback = iteration.get("native_tool_fallback")
        if isinstance(fallback, dict):
            events.append(
                build_generic_edit_native_tool_fallback_event(
                    fallback=fallback,
                    provider_name=provider_name,
                    subtask_id=subtask_id,
                    iteration=iteration.get("iteration"),
                )
            )
        transaction = iteration.get("transaction")
        transaction_id = (
            str(transaction.get("id"))
            if isinstance(transaction, dict) and transaction.get("id")
            else None
        )
        for action_index, action_entry in enumerate(
            iteration.get("actions", []),
            start=1,
        ):
            event = build_generic_edit_action_event(
                action_entry=action_entry,
                provider_name=provider_name,
                subtask_id=subtask_id,
                loop=str(iteration.get("loop") or ""),
                iteration=iteration.get("iteration"),
                action_index=action_index,
                transaction_id=transaction_id,
            )
            events.append(event)
        if isinstance(transaction, dict):
            events.append(
                build_generic_edit_transaction_event(
                    transaction=transaction,
                    provider_name=provider_name,
                    subtask_id=subtask_id,
                )
            )
    events.extend(
        build_generic_edit_transaction_group_event(
            group=group,
            provider_name=provider_name,
            subtask_id=subtask_id,
        )
        for group in transaction_group_summary["transaction_groups"]
    )
    for sequence, event in enumerate(events, start=1):
        event["sequence"] = sequence
    return events


def build_generic_edit_native_tool_fallback_event(
    *,
    fallback: dict[str, Any],
    provider_name: str,
    subtask_id: str | None,
    iteration: Any,
) -> dict[str, Any]:
    """Return one normalized native tool fallback event."""
    return {
        "event_type": "native_tool_fallback",
        "provider": str(fallback.get("provider") or provider_name),
        "subtask_id": subtask_id,
        "iteration": iteration,
        "from_loop": str(fallback.get("from_loop") or "native_tool_calls"),
        "to_loop": str(fallback.get("to_loop") or "json_actions"),
        "reason": str(fallback.get("reason") or "native_tool_request_failed"),
        "message": str(fallback.get("message") or "")[:300],
        "tool_schema_count": int(fallback.get("tool_schema_count") or 0),
    }


def build_generic_edit_resume_event(
    *,
    resume_metadata: dict[str, Any],
    provider_name: str,
    subtask_id: str | None,
) -> dict[str, Any]:
    """Return a normalized event marking checkpoint resume provenance."""
    event = {
        "event_type": "resume",
        "provider": provider_name,
        "subtask_id": subtask_id,
        "checkpoint_artifact": resume_metadata["checkpoint_artifact"],
        "trace_artifact": resume_metadata["trace_artifact"],
        "strategy": resume_metadata["strategy"],
        "start_iteration": resume_metadata["start_iteration"],
        "previous_status": resume_metadata.get("previous_status"),
        "previous_stop_reason": resume_metadata.get("previous_stop_reason"),
    }
    for key in (
        "recovery_plan_artifact",
        "mutation_snapshot_artifact",
        "transaction_group_artifact",
    ):
        value = resume_metadata.get(key)
        if isinstance(value, str) and value:
            event[key] = value
    return event


def build_generic_edit_action_event(
    *,
    action_entry: dict[str, Any],
    provider_name: str,
    subtask_id: str | None,
    loop: str,
    iteration: Any,
    action_index: int,
    transaction_id: str | None,
) -> dict[str, Any]:
    """Return one normalized local action result event."""
    request = action_entry.get("request")
    result = action_entry.get("result", action_entry)
    if not isinstance(request, dict):
        request = {}
    if not isinstance(result, dict):
        result = {"tool": "runtime", "ok": True, "message": str(result)}
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    event = {
        "event_type": "action_result",
        "provider": provider_name,
        "subtask_id": subtask_id,
        "loop": loop,
        "iteration": iteration,
        "action_index": action_index,
        "transaction_id": transaction_id,
        "tool": str(result.get("tool") or request.get("tool") or "runtime"),
        "ok": result.get("ok") is not False,
        "message": str(result.get("message") or "")[:300],
    }
    path = request.get("path") or data.get("path")
    if path:
        event["path"] = str(path)
    if data.get("mutation_snapshot_id"):
        event["mutation_snapshot_id"] = str(data["mutation_snapshot_id"])
    if data.get("rollback_available") is not None:
        event["rollback_available"] = bool(data["rollback_available"])
    if data.get("exit_code") is not None:
        event["exit_code"] = data["exit_code"]
    return event


def build_generic_edit_transaction_event(
    *,
    transaction: dict[str, Any],
    provider_name: str,
    subtask_id: str | None,
) -> dict[str, Any]:
    """Return one normalized transaction boundary event."""
    return {
        "event_type": "transaction",
        "provider": provider_name,
        "subtask_id": subtask_id,
        "transaction_id": str(transaction.get("id") or ""),
        "loop": transaction.get("loop"),
        "iteration": transaction.get("iteration"),
        "status": transaction.get("status"),
        "action_count": transaction.get("action_count", 0),
        "failed_action_count": transaction.get("failed_action_count", 0),
        "recovery_required": bool(transaction.get("recovery_required")),
        "mutated_paths": list(transaction.get("mutated_paths") or []),
        "mutation_snapshot_ids": list(transaction.get("mutation_snapshot_ids") or []),
    }


def build_generic_edit_transaction_group_event(
    *,
    group: dict[str, Any],
    provider_name: str,
    subtask_id: str | None,
) -> dict[str, Any]:
    """Return one normalized transaction recovery-group event."""
    event = {
        "event_type": "transaction_group",
        "provider": provider_name,
        "subtask_id": subtask_id,
        "group_id": group["id"],
        "status": group["status"],
        "partial_failure_transaction_id": group["partial_failure_transaction_id"],
        "resolution_transaction_id": group["resolution_transaction_id"],
        "transaction_ids": list(group.get("transaction_ids") or []),
        "recovery_transaction_ids": list(group.get("recovery_transaction_ids") or []),
        "recovery_attempt_ids": list(group.get("recovery_attempt_ids") or []),
        "recovery_attempt_count": int(group.get("recovery_attempt_count") or 0),
        "failed_recovery_attempt_count": int(
            group.get("failed_recovery_attempt_count") or 0
        ),
        "mutated_paths": list(group.get("mutated_paths") or []),
        "mutation_snapshot_ids": list(group.get("mutation_snapshot_ids") or []),
    }
    if isinstance(group.get("recovery_outcome"), dict):
        event["recovery_outcome"] = group["recovery_outcome"]
    if isinstance(group.get("recovery_policy"), dict):
        event["recovery_policy"] = group["recovery_policy"]
    return event


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


def summarize_generic_edit_transaction_groups(
    *,
    transaction_summary: dict[str, Any],
    mutation_snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    """Group partial-failure transactions with their repair/rollback follow-ups."""
    transactions = list(transaction_summary.get("transactions") or [])
    groups: list[dict[str, Any]] = []
    partial_failure_indexes = [
        index
        for index, transaction in enumerate(transactions)
        if str(transaction.get("status") or "") == "partial_failure"
    ]

    for group_number, partial_index in enumerate(partial_failure_indexes, start=1):
        partial_failure = transactions[partial_index]
        next_partial_index = next(
            (index for index in partial_failure_indexes if index > partial_index),
            len(transactions),
        )
        resolution_index: int | None = None
        recovery_transaction_ids: list[str] = []
        recovery_attempts: list[dict[str, Any]] = []
        for index in range(partial_index + 1, next_partial_index):
            transaction = transactions[index]
            recovery_attempt = build_generic_edit_recovery_attempt(
                attempt_number=len(recovery_attempts) + 1,
                transaction=transaction,
                transaction_index=index,
                partial_failure=partial_failure,
            )
            recovery_attempts.append(recovery_attempt)
            if recovery_attempt["resolved"]:
                recovery_transaction_ids.append(
                    transaction_id_value(transaction, index)
                )
                resolution_index = index
                break

        group_end_index = (
            resolution_index + 1 if resolution_index is not None else next_partial_index
        )
        group_transactions = transactions[partial_index:group_end_index]
        rollback_operation = rollback_operation_for_plan(
            build_generic_edit_rollback_operation(
                transaction_id=transaction_id_value(partial_failure, partial_index),
                mutation_snapshots=mutation_snapshots,
                snapshot_ids=list(partial_failure.get("mutation_snapshot_ids") or []),
            )
        )
        group = {
            "id": f"transaction-group-{group_number}",
            "status": "resolved" if resolution_index is not None else "unresolved",
            "partial_failure_transaction_id": transaction_id_value(
                partial_failure,
                partial_index,
            ),
            "resolution_transaction_id": (
                transaction_id_value(
                    transactions[resolution_index],
                    resolution_index,
                )
                if resolution_index is not None
                else None
            ),
            "transaction_ids": [
                transaction_id_value(transaction, index)
                for index, transaction in enumerate(
                    group_transactions,
                    start=partial_index,
                )
            ],
            "recovery_transaction_ids": recovery_transaction_ids,
            "recovery_attempt_ids": [
                str(attempt["transaction_id"]) for attempt in recovery_attempts
            ],
            "recovery_attempt_count": len(recovery_attempts),
            "failed_recovery_attempt_count": sum(
                1 for attempt in recovery_attempts if not bool(attempt["resolved"])
            ),
            "recovery_attempts": recovery_attempts,
            "affected_paths": transaction_group_field_values(
                group_transactions,
                "affected_paths",
            ),
            "mutated_paths": transaction_group_field_values(
                group_transactions,
                "mutated_paths",
            ),
            "mutation_snapshot_ids": transaction_group_field_values(
                group_transactions,
                "mutation_snapshot_ids",
            ),
            "rollback_operation": rollback_operation,
        }
        if group["status"] == "unresolved":
            group["recommended_next_actions"] = [
                "Inspect affected and mutated paths.",
                "Repair the partial mutation or execute the rollback operation.",
                "Run focused verification before finish.",
            ]
            group["next_actions"] = build_generic_edit_recovery_next_actions(
                transaction_id=group["partial_failure_transaction_id"],
                transaction_group_id=group["id"],
                affected_paths=list(group.get("affected_paths") or []),
                mutated_paths=list(group.get("mutated_paths") or []),
                rollback_operation=rollback_operation,
            )
            group["recovery_policy"] = build_generic_edit_recovery_policy(
                transaction_id=group["partial_failure_transaction_id"],
                transaction_group_id=group["id"],
                affected_paths=list(group.get("affected_paths") or []),
                mutated_paths=list(group.get("mutated_paths") or []),
                rollback_restorable=bool(rollback_operation.get("restorable")),
            )
        elif resolution_index is not None:
            group["recovery_outcome"] = build_generic_edit_recovery_outcome(
                group=group,
                resolution_transaction=transactions[resolution_index],
            )
        groups.append(group)

    status_counts: dict[str, int] = {}
    for group in groups:
        increment_count(status_counts, str(group["status"]))
    unresolved_group_ids = [
        str(group["id"]) for group in groups if group["status"] == "unresolved"
    ]
    recovery_outcomes = [
        group["recovery_outcome"]
        for group in groups
        if isinstance(group.get("recovery_outcome"), dict)
    ]
    recovery_attempt_count = sum(
        int(group.get("recovery_attempt_count") or 0) for group in groups
    )
    failed_recovery_attempt_count = sum(
        int(group.get("failed_recovery_attempt_count") or 0) for group in groups
    )
    return {
        "transaction_groups": groups,
        "transaction_group_count": len(groups),
        "transaction_group_status_counts": status_counts,
        "unresolved_transaction_group_count": len(unresolved_group_ids),
        "unresolved_transaction_group_ids": unresolved_group_ids,
        "recovery_attempt_count": recovery_attempt_count,
        "failed_recovery_attempt_count": failed_recovery_attempt_count,
        "recovery_outcome_count": len(recovery_outcomes),
        "recovery_outcomes": recovery_outcomes,
    }


def transaction_id_value(transaction: dict[str, Any], index: int) -> str:
    """Return a stable transaction id with an index fallback for old traces."""
    return str(transaction.get("id") or index)


def transaction_group_field_values(
    transactions: list[dict[str, Any]],
    field_name: str,
) -> list[str]:
    """Return stable unique list values across a transaction group."""
    values: list[str] = []
    for transaction in transactions:
        raw_values = transaction.get(field_name)
        if not isinstance(raw_values, list):
            continue
        values.extend(str(value) for value in raw_values if value)
    return list(dict.fromkeys(values))


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
