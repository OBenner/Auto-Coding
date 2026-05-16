"""Provider-neutral local edit/tool runtime."""

import hashlib
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
- Use begin_batch before a multi-step mutation group, then commit_batch or abort_batch before finish.
- Use rollback_transaction when you choose to restore a partial transaction from mutation snapshots.
- Use repair_mutation after repairing or intentionally accepting a partial transaction's affected paths.
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
- Use begin_batch before a multi-step mutation group, then commit_batch or abort_batch before finish.
- Use rollback_transaction when you choose to restore a partial transaction from mutation snapshots.
- Use repair_mutation after repairing or intentionally accepting a partial transaction's affected paths.
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


def generic_edit_resume_artifact_error(
    message: str,
    *,
    artifact: str,
    reason: str,
    path: Path | str | None = None,
    **details: Any,
) -> GenericEditRuntimeError:
    """Return a structured resume-blocking artifact error."""
    health: dict[str, Any] = {
        "status": "blocked",
        "artifact": artifact,
        "reason": reason,
    }
    if path is not None:
        health["path"] = str(path)
    for key, value in details.items():
        if value is not None:
            health[key] = value
    return GenericEditRuntimeError(
        message,
        data={"resume_artifact_health": health},
    )


def generic_edit_resume_error_health(
    error: GenericEditRuntimeError,
    *,
    artifact: str,
    path: Path | str | None = None,
) -> dict[str, Any]:
    """Return structured artifact health for a resume preflight error."""
    health = error.data.get("resume_artifact_health")
    if isinstance(health, dict):
        return dict(health)
    fallback: dict[str, Any] = {
        "status": "blocked",
        "artifact": artifact,
        "reason": "validation_error",
        "message": str(error),
    }
    if path is not None:
        fallback["path"] = str(path)
    return fallback


def generic_edit_required_resume_artifact_error(
    message: str,
    *,
    owner_artifact: str,
    owner_path: Path,
    artifact_name: str,
    artifact_path: str | None,
    reason: str,
) -> GenericEditRuntimeError:
    """Return a structured error for a missing required resume artifact."""
    artifact = {
        "trace_artifact": "trace",
        "event_artifact": "events",
        "recovery_plan_artifact": "recovery_plan",
        "mutation_snapshot_artifact": "mutation_snapshots",
        "transaction_group_artifact": "transaction_groups",
    }.get(artifact_name, artifact_name)
    return generic_edit_resume_artifact_error(
        message,
        artifact=artifact,
        reason=reason,
        path=artifact_path,
        artifact_name=artifact_name,
        owner_artifact=owner_artifact,
        owner_path=str(owner_path),
    )


def generic_edit_resume_blocked_preflight(
    *,
    checkpoint_path: Path,
    spec_dir: Path,
    project_dir: Path,
    artifact_health: dict[str, Any],
    artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a read-only resume preflight payload for a blocked resume."""
    return {
        "runtime": "generic_edit",
        "status": "blocked",
        "requested_path": str(checkpoint_path),
        "spec_dir": str(spec_dir),
        "project_dir": str(project_dir),
        "artifacts": dict(artifacts or {}),
        "resume_artifact_health": dict(artifact_health),
        "blockers": [dict(artifact_health)],
    }


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
REPAIR_MUTATION_TOOL = "repair_mutation"
BEGIN_BATCH_TOOL = "begin_batch"
COMMIT_BATCH_TOOL = "commit_batch"
ABORT_BATCH_TOOL = "abort_batch"
BATCH_CONTROL_TOOLS = frozenset({BEGIN_BATCH_TOOL, COMMIT_BATCH_TOOL, ABORT_BATCH_TOOL})
MUTATING_LOCAL_ACTIONS = frozenset(
    {
        "write_file",
        "replace_text",
        "delete_file",
        "move_file",
        "apply_patch",
        "run_command",
        ROLLBACK_TRANSACTION_TOOL,
        REPAIR_MUTATION_TOOL,
        ABORT_BATCH_TOOL,
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
    REPAIR_MUTATION_TOOL,
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
        "open_batch",
        "parse_error",
        "unresolved_partial_failure",
    }
)
GENERIC_EDIT_ARTIFACT_MANIFEST_SCHEMA_VERSION = 1
GENERIC_EDIT_ARTIFACT_MANIFEST_RECENT_EVENT_LIMIT = 5
GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_TIMELINE_LIMIT = 20
GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_ACTION_LIMIT = 10
GENERIC_EDIT_ARTIFACT_MANIFEST_RECENT_EVENT_FIELDS = (
    "sequence",
    "event_type",
    "tool",
    "ok",
    "message",
    "status",
    "transaction_id",
    "batch_id",
    "batch_status",
    "group_id",
    "path",
    "iteration",
    "from_loop",
    "to_loop",
    "reason",
    "tool_schema_count",
    "action_index",
    "timeline_stage",
    "recovery_required",
    "requires_user_action",
    "failed_action_count",
    "recovery_attempt_count",
    "failed_recovery_attempt_count",
    "strategy",
    "finish_blocked",
    "can_resume",
    "checkpoint_artifact",
    "recovery_plan_artifact",
    "required_resolution_action_kinds",
    "required_artifacts",
    "unresolved_partial_failure_ids",
    "unresolved_transaction_group_ids",
    "open_transaction_batch_ids",
    "workspace_guard_status",
    "workspace_guard_drift_count",
    "workspace_guard_unverified_path_count",
    "active_batch_id",
    "start_iteration",
    "previous_status",
    "previous_stop_reason",
    "preferred_strategy",
    "next_action_count",
)
GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_TIMELINE_STAGES = frozenset(
    {
        "partial_failure",
        "recovery_policy",
        "recovery_action",
        "recovery_resolved",
        "resume",
        "resume_clean",
        "resume_policy",
        "batch_open",
        "batch_boundary_blocked",
    }
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
        self._active_batch_id: str | None = None
        self._batch_recovery_blockers: dict[str, list[str]] = {}

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
        self._active_batch_id = None
        self._batch_recovery_blockers = {}
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
        self._active_batch_id = None
        self._batch_recovery_blockers = {}
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
        validate_generic_edit_checkpoint_trace_consistency(
            checkpoint=checkpoint,
            trace=trace,
        )
        self._mutation_snapshots = load_generic_edit_mutation_snapshots(
            generic_edit_mutation_snapshot_path_for_checkpoint(checkpoint_path)
        )
        self._active_batch_id = generic_edit_resume_open_batch_id(
            checkpoint=checkpoint,
            trace=trace,
        )
        self._refresh_batch_recovery_guards(trace)
        workspace_guard = validate_generic_edit_resume_workspace_guard(
            project_dir=self._executor.project_dir,
            mutation_snapshots=self._mutation_snapshots,
        )
        checkpoint["workspace_guard"] = workspace_guard
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
            workspace_guard=workspace_guard,
            active_batch_id=self._active_batch_id,
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
            self._refresh_batch_recovery_guards(trace)
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
        try:
            validate_batch_boundary_actions(actions)
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
                    stop_reason="batch_boundary_violation",
                    summary="Generic edit runtime rejected a batch boundary violation.",
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
            self._refresh_batch_recovery_guards_before_action(
                action=action,
                trace=trace,
                iteration_entry=iteration_entry,
                loop="json_actions",
                iteration=iteration,
                actions=execution.executed_actions,
                results=execution.action_results,
            )
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
        if has_open_transaction_batch(finish_trace):
            return self._open_batch_finish_result(
                trace=finish_trace,
                spec_dir=spec_dir,
                observation_path=observation_path,
                subtask_id=subtask_id,
            )
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
            trace=trace,
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
        self._refresh_batch_recovery_guards(trace)
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
        try:
            validate_batch_boundary_actions([action for _, action in tool_actions])
        except GenericEditRuntimeError as e:
            iteration_entry["error"] = str(e)
            trace.append(iteration_entry)
            artifacts = save_generic_edit_artifacts(
                spec_dir=spec_dir,
                provider_name=self.provider_name,
                subtask_id=subtask_id,
                status="error",
                stop_reason="batch_boundary_violation",
                message=str(e),
                trace=trace,
                summary="Generic edit runtime rejected a batch boundary violation.",
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
        trace: list[dict[str, Any]],
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
            self._refresh_batch_recovery_guards_before_action(
                action=action,
                trace=trace,
                iteration_entry=iteration_entry,
                loop="native_tool_calls",
                iteration=iteration,
                actions=execution.executed_actions,
                results=execution.action_results,
            )
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
        if has_open_transaction_batch(finish_trace):
            return self._open_batch_finish_result(
                trace=finish_trace,
                spec_dir=spec_dir,
                observation_path=observation_path,
                subtask_id=subtask_id,
            )
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

    def _open_batch_finish_result(
        self,
        *,
        trace: list[dict[str, Any]],
        spec_dir: Path,
        observation_path: Path,
        subtask_id: str | None,
    ) -> AgentRunResult:
        """Reject finish while a runtime-managed transaction batch is open."""
        transaction_summary = summarize_generic_edit_transactions(trace)
        open_batch_ids = transaction_summary["open_transaction_batch_ids"]
        message = (
            "Generic edit runtime rejected finish because transaction batch(es) "
            f"remain open: {', '.join(open_batch_ids)}."
        )
        artifacts = save_generic_edit_artifacts(
            spec_dir=spec_dir,
            provider_name=self.provider_name,
            subtask_id=subtask_id,
            status="error",
            stop_reason="open_batch",
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
        elif action_tool(action) in BATCH_CONTROL_TOOLS:
            result = self._batch_control_action(action)
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

    def _batch_control_action(self, action: dict[str, Any]) -> ToolActionResult:
        """Open, commit, or abort one runtime-managed transaction batch."""
        tool = action_tool(action)
        try:
            batch_id = generic_edit_batch_id(action)
        except GenericEditRuntimeError as e:
            return ToolActionResult(tool=tool, ok=False, message=str(e))
        if tool == BEGIN_BATCH_TOOL:
            if self._active_batch_id is not None:
                return ToolActionResult(
                    tool=tool,
                    ok=False,
                    message=(
                        "Cannot begin batch "
                        f"{batch_id}: batch {self._active_batch_id} is already open."
                    ),
                )
            self._active_batch_id = batch_id
            return ToolActionResult(
                tool=tool,
                ok=True,
                message=f"Opened batch {batch_id}.",
                data={
                    "batch_id": batch_id,
                    "batch_action": BEGIN_BATCH_TOOL,
                    "batch_status": "open",
                },
            )

        if self._active_batch_id != batch_id:
            return ToolActionResult(
                tool=tool,
                ok=False,
                message=(
                    f"Cannot {tool} {batch_id}: active batch is "
                    f"{self._active_batch_id or '<none>'}."
                ),
            )

        if tool == COMMIT_BATCH_TOOL:
            blockers = self._batch_recovery_blockers.get(batch_id) or []
            if blockers:
                return ToolActionResult(
                    tool=tool,
                    ok=False,
                    message=(
                        f"Cannot commit batch {batch_id}: unresolved recovery "
                        "group(s) remain inside the batch: "
                        f"{', '.join(blockers)}."
                    ),
                    data={
                        "batch_id": batch_id,
                        "batch_action": COMMIT_BATCH_TOOL,
                        "batch_boundary_error": True,
                        "batch_boundary_error_reason": "unresolved_batch_recovery",
                        "blocked_transaction_group_ids": blockers,
                    },
                )
            self._active_batch_id = None
            return ToolActionResult(
                tool=tool,
                ok=True,
                message=f"Committed batch {batch_id}.",
                data={
                    "batch_id": batch_id,
                    "batch_action": COMMIT_BATCH_TOOL,
                    "batch_status": "committed",
                },
            )

        try:
            result = execute_generic_edit_batch_abort(
                batch_id=batch_id,
                project_dir=self._executor.project_dir,
                mutation_snapshots=self._mutation_snapshots,
            )
        except GenericEditRuntimeError as e:
            return ToolActionResult(
                tool=tool,
                ok=False,
                message=str(e),
                data=dict(e.data),
            )
        self._active_batch_id = None
        return result

    def _refresh_batch_recovery_guards(self, trace: list[dict[str, Any]]) -> None:
        """Refresh per-batch unresolved recovery blockers from the trace."""
        transaction_summary = summarize_generic_edit_transactions(trace)
        transaction_group_summary = summarize_generic_edit_transaction_groups(
            transaction_summary=transaction_summary,
            mutation_snapshots=self._mutation_snapshots,
        )
        linked_summary = link_generic_edit_transaction_batches_to_groups(
            transaction_summary=transaction_summary,
            transaction_group_summary=transaction_group_summary,
        )
        blockers: dict[str, list[str]] = {}
        for batch in linked_summary.get("transaction_batches") or []:
            if not isinstance(batch, dict):
                continue
            batch_id = str(batch.get("id") or "")
            unresolved = normalize_string_list(
                batch.get("unresolved_transaction_group_ids")
            )
            if batch_id and unresolved:
                blockers[batch_id] = unresolved
        self._batch_recovery_blockers = blockers

    def _refresh_batch_recovery_guards_before_action(
        self,
        *,
        action: dict[str, Any],
        trace: list[dict[str, Any]],
        iteration_entry: dict[str, Any],
        loop: str,
        iteration: int,
        actions: list[dict[str, Any]],
        results: list[ToolActionResult],
    ) -> None:
        """Include same-turn recovery actions before evaluating batch commits."""
        if action_tool(action) != COMMIT_BATCH_TOOL:
            return
        if not actions or not results:
            self._refresh_batch_recovery_guards(trace)
            return
        pending_iteration = dict(iteration_entry)
        pending_iteration["transaction"] = build_generic_edit_transaction(
            loop=loop,
            iteration=iteration,
            actions=actions,
            results=results,
        )
        self._refresh_batch_recovery_guards([*trace, pending_iteration])

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
            batch_id=self._active_batch_id,
        )

    def _record_mutation_snapshot_result(
        self,
        snapshot: dict[str, Any] | None,
        result: ToolActionResult,
    ) -> None:
        """Attach a successful mutation snapshot to result metadata and artifacts."""
        if snapshot is None or not result.ok:
            return
        snapshot["postimages"] = [
            build_generic_edit_file_preimage(
                project_dir=self._executor.project_dir,
                path=str(path),
            )
            for path in snapshot.get("paths", [])
            if isinstance(path, str) and path
        ]
        snapshot["workspace_guard"] = build_generic_edit_snapshot_workspace_guard(
            snapshot
        )
        self._mutation_snapshots.append(snapshot)
        result.data = {
            **result.data,
            "mutation_snapshot_id": snapshot["id"],
            "rollback_available": snapshot["rollback"]["restorable"],
        }
        if snapshot.get("batch_id"):
            result.data["batch_id"] = snapshot["batch_id"]

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


def validate_batch_boundary_actions(actions: list[dict[str, Any]]) -> None:
    """Reject mutating actions after a batch closes in the same provider turn."""
    closing_tool: str | None = None
    for action in actions:
        tool = action_tool(action)
        if not tool:
            continue
        if closing_tool and (
            tool in MUTATING_LOCAL_ACTIONS or tool in BATCH_CONTROL_TOOLS
        ):
            raise GenericEditRuntimeError(
                f"Generic edit action {tool} cannot run after {closing_tool} "
                "in the same provider turn. Start a new provider iteration "
                "before additional mutations."
            )
        if tool in {COMMIT_BATCH_TOOL, ABORT_BATCH_TOOL}:
            closing_tool = tool


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
    mutation_snapshot_ids.extend(
        str(snapshot_id)
        for result in results
        if result.ok
        for snapshot_id in result.data.get("mutation_snapshot_ids") or []
    )
    mutation_snapshot_ids = list(dict.fromkeys(mutation_snapshot_ids))
    rollback_transaction_ids = [
        str(action.get("transaction_id")).strip()
        for action in actions
        if action_tool(action) == ROLLBACK_TRANSACTION_TOOL
        and str(action.get("transaction_id") or "").strip()
    ]
    batch_actions = [tool for tool in tool_sequence if tool in BATCH_CONTROL_TOOLS]
    batch_ids = list(
        dict.fromkeys(
            [
                *(
                    str(action.get("batch_id")).strip()
                    for action in actions
                    if action_tool(action) in BATCH_CONTROL_TOOLS
                    and str(action.get("batch_id") or "").strip()
                ),
                *(
                    str(result.data.get("batch_id")).strip()
                    for result in results
                    if result.ok and str(result.data.get("batch_id") or "").strip()
                ),
            ]
        )
    )
    batch_status = next(
        (
            str(result.data.get("batch_status"))
            for result in reversed(results)
            if result.ok and result.data.get("batch_status")
        ),
        None,
    )
    batch_boundary_errors = [
        {
            "tool": result.tool,
            "batch_id": str(result.data.get("batch_id") or ""),
            "reason": str(result.data.get("batch_boundary_error_reason") or ""),
            "blocked_transaction_group_ids": normalize_string_list(
                result.data.get("blocked_transaction_group_ids")
            ),
        }
        for result in results
        if result.data.get("batch_boundary_error")
    ]
    restored_paths = sorted(
        dict.fromkeys(
            str(path)
            for result in results
            for path in result.data.get("restored_paths") or []
        )
    )
    deleted_paths = sorted(
        dict.fromkeys(
            str(path)
            for result in results
            for path in result.data.get("deleted_paths") or []
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
        "mutation_snapshot_ids": mutation_snapshot_ids,
        "recovery_required": status == "partial_failure",
        "can_resolve_partial_failure": transaction_can_resolve_partial_failure(
            status=status,
            tool_sequence=tool_sequence,
        ),
    }
    if rollback_transaction_ids:
        transaction["rollback_transaction_ids"] = rollback_transaction_ids
    if batch_ids:
        transaction["batch_ids"] = batch_ids
        if len(batch_ids) == 1:
            transaction["batch_id"] = batch_ids[0]
    if batch_actions:
        transaction["batch_actions"] = batch_actions
    if batch_status:
        transaction["batch_status"] = batch_status
    if batch_boundary_errors:
        transaction["batch_boundary_errors"] = batch_boundary_errors
        transaction["batch_boundary_error_count"] = len(batch_boundary_errors)
        transaction["batch_boundary_error_reasons"] = list(
            dict.fromkeys(
                error["reason"] for error in batch_boundary_errors if error["reason"]
            )
        )
    if restored_paths:
        transaction["restored_paths"] = restored_paths
    if deleted_paths:
        transaction["deleted_paths"] = deleted_paths
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
    else:
        action = {
            "id": f"repair-{transaction_id}",
            "kind": REPAIR_MUTATION_TOOL,
            "tool": REPAIR_MUTATION_TOOL,
            "action": {
                "tool": REPAIR_MUTATION_TOOL,
                "transaction_id": transaction_id,
                "paths": inspect_paths,
            },
            "transaction_id": transaction_id,
            "paths": inspect_paths,
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
    resolution_strategies = [REPAIR_MUTATION_TOOL]
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
        resolution_strategies = [ROLLBACK_TRANSACTION_TOOL, REPAIR_MUTATION_TOOL]
    transaction_batch_policies = build_generic_edit_transaction_batch_policies(
        transaction_summary,
    )
    blocked_transaction_batch_ids = [
        policy["batch_id"]
        for policy in transaction_batch_policies
        if policy["finish_blocked"]
    ]
    policy = {
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
    if transaction_batch_policies:
        policy["blocked_transaction_batch_ids"] = blocked_transaction_batch_ids
        policy["transaction_batch_policy_count"] = len(transaction_batch_policies)
        policy["transaction_batch_policies"] = transaction_batch_policies
    return policy


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
        "batch_ids": list(group.get("batch_ids") or []),
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
    batch_id: str | None = None,
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
        "batch_id": batch_id,
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


def generic_edit_batch_id(action: dict[str, Any]) -> str:
    """Return a required batch id from a batch control action."""
    batch_id = str(action.get("batch_id") or "").strip()
    if not batch_id:
        raise GenericEditRuntimeError("Batch action requires batch_id.")
    if len(batch_id) > 80:
        raise GenericEditRuntimeError("Batch id must be at most 80 characters.")
    return batch_id


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
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "line_count": len(content.splitlines()),
        }
    )
    return payload


def build_generic_edit_snapshot_workspace_guard(
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Return guard metadata for one mutation snapshot's captured post-state."""
    postimages = [
        postimage
        for postimage in snapshot.get("postimages") or []
        if isinstance(postimage, dict)
    ]
    verifiable_paths = [
        str(postimage.get("path"))
        for postimage in postimages
        if generic_edit_file_state_is_verifiable(postimage)
    ]
    tracked_paths = [
        str(postimage.get("path")) for postimage in postimages if postimage.get("path")
    ]
    return {
        "status": "captured" if postimages else "unavailable",
        "tracked_paths": tracked_paths,
        "tracked_path_count": len(tracked_paths),
        "verifiable_path_count": len(verifiable_paths),
        "unverifiable_path_count": len(tracked_paths) - len(verifiable_paths),
    }


def validate_generic_edit_resume_workspace_guard(
    *,
    project_dir: Path,
    mutation_snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate that snapshot-tracked files did not drift before resume."""
    guard = build_generic_edit_resume_workspace_guard(
        project_dir=project_dir,
        mutation_snapshots=mutation_snapshots,
    )
    if guard["status"] != "drifted":
        return guard

    drift_paths = [
        str(drift.get("path"))
        for drift in guard["drifts"]
        if isinstance(drift, dict) and drift.get("path")
    ]
    raise GenericEditRuntimeError(
        "Generic edit resume blocked by workspace drift on path(s): "
        + ", ".join(drift_paths[:10])
        + ".",
        data={
            "workspace_guard": guard,
            "resume_artifact_health": {
                "status": "blocked",
                "artifact": "workspace_guard",
                "reason": "workspace_drift",
                "drift_paths": drift_paths,
            },
        },
    )


def build_generic_edit_resume_workspace_guard(
    *,
    project_dir: Path,
    mutation_snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare persisted mutation postimages with the current workspace."""
    checks: list[dict[str, Any]] = []
    for snapshot in mutation_snapshots:
        postimages = snapshot.get("postimages")
        if not isinstance(postimages, list):
            continue
        for postimage in postimages:
            if not isinstance(postimage, dict):
                continue
            path = str(postimage.get("path") or "")
            if not path:
                continue
            current = build_generic_edit_file_preimage(
                project_dir=project_dir,
                path=path,
            )
            checks.append(
                compare_generic_edit_file_state(
                    expected=postimage,
                    current=current,
                    snapshot=snapshot,
                )
            )

    drifts = [check for check in checks if check["status"] == "drifted"]
    unverified = [check for check in checks if check["status"] == "unverified"]
    if drifts:
        status = "drifted"
    elif checks:
        status = "clean"
    else:
        status = "unavailable"
    return {
        "status": status,
        "checked_path_count": len(checks) - len(unverified),
        "unverified_path_count": len(unverified),
        "drift_count": len(drifts),
        "drifts": drifts,
        "unverified": unverified,
    }


def compare_generic_edit_file_state(
    *,
    expected: dict[str, Any],
    current: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Return one drift check without embedding file contents."""
    path = str(expected.get("path") or current.get("path") or "")
    base = {
        "path": path,
        "snapshot_id": str(snapshot.get("id") or ""),
        "transaction_id": str(snapshot.get("transaction_id") or ""),
        "expected": generic_edit_file_state_fingerprint(expected),
        "current": generic_edit_file_state_fingerprint(current),
    }
    if not generic_edit_file_state_is_verifiable(expected):
        return {
            **base,
            "status": "unverified",
            "reason": "expected_state_unverifiable",
        }
    if not generic_edit_file_state_is_verifiable(current):
        return {
            **base,
            "status": "drifted",
            "reason": "current_state_unverifiable",
        }
    if generic_edit_file_state_signature(expected) != generic_edit_file_state_signature(
        current
    ):
        return {
            **base,
            "status": "drifted",
            "reason": "workspace_state_changed",
        }
    return {**base, "status": "clean"}


def generic_edit_file_state_is_verifiable(state: dict[str, Any]) -> bool:
    """Return true when a captured file state can be compared exactly."""
    if state.get("type") == "missing" and state.get("exists") is False:
        return True
    return (
        state.get("type") == "file"
        and state.get("exists") is True
        and state.get("content_encoding") == "utf-8"
        and state.get("content_truncated") is False
        and isinstance(state.get("content_sha256"), str)
    )


def generic_edit_file_state_signature(state: dict[str, Any]) -> tuple[Any, ...]:
    """Return a comparable file-state signature without raw content."""
    if state.get("type") == "missing" and state.get("exists") is False:
        return (False, "missing")
    return (
        True,
        "file",
        state.get("bytes"),
        state.get("content_sha256"),
        state.get("line_count"),
    )


def generic_edit_file_state_fingerprint(state: dict[str, Any]) -> dict[str, Any]:
    """Return safe file-state metadata for guard diagnostics."""
    fingerprint: dict[str, Any] = {
        "exists": bool(state.get("exists")),
        "type": str(state.get("type") or "unknown"),
    }
    for key in (
        "bytes",
        "content_encoding",
        "content_truncated",
        "content_bytes_limit",
        "content_sha256",
        "line_count",
    ):
        if key in state:
            fingerprint[key] = state[key]
    return fingerprint


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


def execute_generic_edit_batch_abort(
    *,
    batch_id: str,
    project_dir: Path,
    mutation_snapshots: list[dict[str, Any]],
) -> ToolActionResult:
    """Rollback all captured mutation snapshots for one open batch."""
    selected = [
        snapshot
        for snapshot in mutation_snapshots
        if str(snapshot.get("batch_id") or "") == batch_id
    ]
    restored_paths: list[str] = []
    deleted_paths: list[str] = []
    rollback_transaction_ids: list[str] = []
    mutation_snapshot_ids: list[str] = []

    for snapshot in reversed(selected):
        transaction_id = str(snapshot.get("transaction_id") or "")
        snapshot_id = str(snapshot.get("id") or "")
        if not transaction_id or not snapshot_id:
            continue
        result = execute_generic_edit_transaction_rollback(
            action={
                "tool": ROLLBACK_TRANSACTION_TOOL,
                "transaction_id": transaction_id,
                "snapshot_ids": [snapshot_id],
            },
            project_dir=project_dir,
            mutation_snapshots=mutation_snapshots,
        )
        rollback_transaction_ids.append(transaction_id)
        mutation_snapshot_ids.extend(
            str(item) for item in result.data.get("mutation_snapshot_ids") or []
        )
        restored_paths.extend(
            str(path) for path in result.data.get("restored_paths") or []
        )
        deleted_paths.extend(
            str(path) for path in result.data.get("deleted_paths") or []
        )

    affected_paths = sorted(dict.fromkeys([*restored_paths, *deleted_paths]))
    return ToolActionResult(
        tool=ABORT_BATCH_TOOL,
        ok=True,
        message=(
            f"Aborted batch {batch_id} and rolled back "
            f"{len(mutation_snapshot_ids)} mutation snapshot(s)."
        ),
        data={
            "batch_id": batch_id,
            "batch_action": ABORT_BATCH_TOOL,
            "batch_status": "aborted",
            "mutation_snapshot_ids": list(dict.fromkeys(mutation_snapshot_ids)),
            "rollback_transaction_ids": list(dict.fromkeys(rollback_transaction_ids)),
            "affected_paths": affected_paths,
            "mutated_paths": affected_paths,
            "restored_paths": sorted(dict.fromkeys(restored_paths)),
            "deleted_paths": sorted(dict.fromkeys(deleted_paths)),
            "recovery_strategy": ABORT_BATCH_TOOL,
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
    transaction_summary = link_generic_edit_transaction_batches_to_groups(
        transaction_summary=transaction_summary,
        transaction_group_summary=transaction_group_summary,
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
            "events": paths["events"],
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
    events = build_generic_edit_events(
        trace=trace,
        provider_name=provider_name,
        subtask_id=subtask_id,
        transaction_group_summary=transaction_group_summary,
        resume_metadata=resume_metadata,
        recovery_checkpoint=recovery_checkpoint,
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
        "open_transaction_batch_ids": transaction_summary["open_transaction_batch_ids"],
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
        state["resume_policy"] = None
        return state

    resume = recovery_checkpoint["resume"]
    resume_inputs = build_generic_edit_resume_input_artifacts(
        artifact_refs=artifact_refs,
        recovery_plan=recovery_plan,
        mutation_snapshots=mutation_snapshots,
        transaction_group_summary=transaction_group_summary,
    )
    state["resume_action"] = {
        "runtime": "generic_edit",
        "checkpoint_path": recovery_checkpoint["artifact_path"],
        "strategy": resume["strategy"],
        "next_iteration": recovery_checkpoint["next_iteration"],
    }
    state["resume_inputs"] = resume_inputs
    state["resume_policy"] = build_generic_edit_resume_policy(
        strategy=resume["strategy"],
        checkpoint_path=recovery_checkpoint["artifact_path"],
        next_iteration=recovery_checkpoint["next_iteration"],
        resume_inputs=resume_inputs,
        transaction_summary=transaction_summary,
        transaction_group_summary=transaction_group_summary,
        recovery_plan=recovery_plan,
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
                "resume_policy": recovery_checkpoint["resume_policy"],
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
        elif isinstance(value, list):
            compact[field] = [
                str(item)[:300] for item in value[:20] if isinstance(item, str)
            ]
    return compact


def build_generic_edit_manifest_recovery_timeline(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return bounded recovery-significant events for UI timelines."""
    timeline_events = [
        event
        for event in events
        if str(event.get("timeline_stage") or "")
        in GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_TIMELINE_STAGES
    ]
    if len(timeline_events) > GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_TIMELINE_LIMIT:
        timeline_events = timeline_events[
            -GENERIC_EDIT_ARTIFACT_MANIFEST_RECOVERY_TIMELINE_LIMIT:
        ]
    compact_events: list[dict[str, Any]] = []
    for event in timeline_events:
        compact = compact_generic_edit_manifest_event(event)
        if compact:
            compact_events.append(compact)
    return compact_events


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


def compact_generic_edit_batch_boundary_errors(
    value: Any,
) -> list[dict[str, Any]]:
    """Return bounded batch-boundary errors without dropping blocker IDs."""
    if not isinstance(value, list):
        return []
    compact_errors: list[dict[str, Any]] = []
    for error in value[:GENERIC_EDIT_ARTIFACT_MANIFEST_RECENT_EVENT_LIMIT]:
        if not isinstance(error, dict):
            continue
        compact_errors.append(
            {
                "tool": str(error.get("tool") or "")[:120],
                "batch_id": str(error.get("batch_id") or "")[:120],
                "reason": str(error.get("reason") or "")[:120],
                "blocked_transaction_group_ids": normalize_string_list(
                    error.get("blocked_transaction_group_ids")
                ),
            }
        )
    return compact_errors


def compact_generic_edit_manifest_transaction_batches(
    transaction_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return bounded transaction batch summaries for UI manifests."""
    batches = transaction_summary.get("transaction_batches")
    if not isinstance(batches, list):
        return []
    compact_batches: list[dict[str, Any]] = []
    for batch in batches[:GENERIC_EDIT_ARTIFACT_MANIFEST_RECENT_EVENT_LIMIT]:
        if not isinstance(batch, dict):
            continue
        compact: dict[str, Any] = {
            "id": str(batch.get("id") or "")[:120],
            "status": str(batch.get("status") or "unknown")[:120],
            "recovery_status": str(batch.get("recovery_status") or "clean")[:120],
            "finish_blocked": bool(batch.get("finish_blocked")),
            "transaction_ids": normalize_string_list(batch.get("transaction_ids")),
            "mutation_snapshot_ids": normalize_string_list(
                batch.get("mutation_snapshot_ids")
            ),
            "staged_mutation_ids": normalize_string_list(
                batch.get("staged_mutation_ids")
            ),
            "staged_mutated_paths": normalize_string_list(
                batch.get("staged_mutated_paths")
            ),
            "staged_restored_paths": normalize_string_list(
                batch.get("staged_restored_paths")
            ),
            "staged_deleted_paths": normalize_string_list(
                batch.get("staged_deleted_paths")
            ),
            "staged_mutation_count": int(batch.get("staged_mutation_count") or 0),
            "staged_path_count": int(batch.get("staged_path_count") or 0),
            "boundary_error_count": int(batch.get("boundary_error_count") or 0),
            "boundary_errors": compact_generic_edit_batch_boundary_errors(
                batch.get("boundary_errors")
            ),
            "boundary_error_reasons": normalize_string_list(
                batch.get("boundary_error_reasons")
            ),
            "transaction_group_ids": normalize_string_list(
                batch.get("transaction_group_ids")
            ),
            "unresolved_transaction_group_ids": normalize_string_list(
                batch.get("unresolved_transaction_group_ids")
            ),
            "required_next_action_kinds": normalize_string_list(
                batch.get("required_next_action_kinds")
            ),
            "resolution_strategies": normalize_string_list(
                batch.get("resolution_strategies")
            ),
            "recovery_outcome_count": int(batch.get("recovery_outcome_count") or 0),
        }
        if compact["id"]:
            compact_batches.append(compact)
    return compact_batches


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


def build_generic_edit_resume_input_artifacts(
    *,
    artifact_refs: dict[str, Path | None],
    recovery_plan: dict[str, Any] | None,
    mutation_snapshots: list[dict[str, Any]],
    transaction_group_summary: dict[str, Any],
) -> dict[str, str]:
    """Return artifact inputs needed by a generic_edit resume action."""
    resume_inputs: dict[str, str] = {}
    trace_path = artifact_refs.get("trace")
    event_path = artifact_refs.get("events")
    if trace_path is not None:
        resume_inputs["trace_artifact"] = str(trace_path)
    if event_path is not None:
        resume_inputs["event_artifact"] = str(event_path)
    if recovery_plan is not None:
        resume_inputs["recovery_plan_artifact"] = recovery_plan["artifact_path"]
    mutation_snapshot_path = artifact_refs.get("mutation_snapshots")
    if mutation_snapshots and mutation_snapshot_path is not None:
        resume_inputs["mutation_snapshot_artifact"] = str(mutation_snapshot_path)
    transaction_group_path = artifact_refs.get("transaction_groups")
    if (
        transaction_group_summary["transaction_group_count"]
        and transaction_group_path is not None
    ):
        resume_inputs["transaction_group_artifact"] = str(transaction_group_path)
    return resume_inputs


def generic_edit_required_resolution_action_kinds(
    recovery_plan: dict[str, Any] | None,
) -> list[str]:
    """Return required recovery action kinds in plan order without duplicates."""
    if recovery_plan is None:
        return []
    action_kinds: list[str] = []

    def append_action_kind(value: Any) -> None:
        if isinstance(value, str) and value and value not in action_kinds:
            action_kinds.append(value)

    for action in recovery_plan.get("next_actions") or []:
        if (
            not isinstance(action, dict)
            or action.get("required_before_finish") is not True
        ):
            continue
        append_action_kind(action.get("kind"))
    for group in recovery_plan.get("unresolved_transaction_groups") or []:
        if not isinstance(group, dict):
            continue
        recovery_policy = group.get("recovery_policy")
        if not isinstance(recovery_policy, dict):
            continue
        for kind in recovery_policy.get("required_next_action_kinds") or []:
            append_action_kind(kind)
    return action_kinds


def build_generic_edit_resume_policy(
    *,
    strategy: str,
    checkpoint_path: str,
    next_iteration: int,
    resume_inputs: dict[str, str],
    transaction_summary: dict[str, Any],
    transaction_group_summary: dict[str, Any],
    recovery_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a compact resume policy for UI and orchestrator control planes."""
    unresolved_partial_failure_ids = list(
        transaction_summary["unresolved_partial_failure_ids"]
    )
    unresolved_transaction_group_ids = list(
        transaction_group_summary["unresolved_transaction_group_ids"]
    )
    open_transaction_batch_ids = list(
        transaction_summary.get("open_transaction_batch_ids") or []
    )
    finish_blocked = bool(
        unresolved_partial_failure_ids
        or unresolved_transaction_group_ids
        or open_transaction_batch_ids
    )
    required_resolution_action_kinds = generic_edit_required_resolution_action_kinds(
        recovery_plan
    )
    if open_transaction_batch_ids:
        for action_kind in (COMMIT_BATCH_TOOL, ABORT_BATCH_TOOL):
            if action_kind not in required_resolution_action_kinds:
                required_resolution_action_kinds.append(action_kind)
    required_artifacts = [
        artifact_name
        for artifact_name in (
            "trace_artifact",
            "event_artifact",
            "recovery_plan_artifact",
            "mutation_snapshot_artifact",
            "transaction_group_artifact",
        )
        if artifact_name in resume_inputs
    ]
    policy = {
        "version": GENERIC_EDIT_RECOVERY_POLICY_VERSION,
        "runtime": "generic_edit",
        "status": "requires_resolution" if finish_blocked else "ready",
        "can_resume": True,
        "finish_blocked": finish_blocked,
        "strategy": strategy,
        "checkpoint_path": checkpoint_path,
        "next_iteration": next_iteration,
        "required_resolution_action_kinds": required_resolution_action_kinds,
        "required_artifacts": required_artifacts,
        "unresolved_partial_failure_ids": unresolved_partial_failure_ids,
        "unresolved_transaction_group_ids": unresolved_transaction_group_ids,
    }
    if open_transaction_batch_ids:
        policy["open_transaction_batch_ids"] = open_transaction_batch_ids
    return policy


def build_generic_edit_manifest_resume_inputs(
    *,
    recovery_checkpoint: dict[str, Any] | None,
    paths: dict[str, Path],
    recovery_plan: dict[str, Any] | None,
    mutation_snapshots: list[dict[str, Any]],
    transaction_group_summary: dict[str, Any],
) -> dict[str, str]:
    """Return artifact inputs needed by a generic_edit resume action."""
    if recovery_checkpoint is None:
        return {}
    return build_generic_edit_resume_input_artifacts(
        artifact_refs=paths,
        recovery_plan=recovery_plan,
        mutation_snapshots=mutation_snapshots,
        transaction_group_summary=transaction_group_summary,
    )


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
    resume_inputs = build_generic_edit_manifest_resume_inputs(
        recovery_checkpoint=recovery_checkpoint,
        paths=paths,
        recovery_plan=recovery_plan,
        mutation_snapshots=mutation_snapshots,
        transaction_group_summary=transaction_group_summary,
    )
    resume_policy = None
    if recovery_checkpoint is not None:
        resume = recovery_checkpoint.get("resume")
        if isinstance(resume, dict):
            resume_policy = build_generic_edit_resume_policy(
                strategy=str(resume["strategy"]),
                checkpoint_path=str(recovery_checkpoint["artifact_path"]),
                next_iteration=int(recovery_checkpoint["next_iteration"]),
                resume_inputs=resume_inputs,
                transaction_summary=transaction_summary,
                transaction_group_summary=transaction_group_summary,
                recovery_plan=recovery_plan,
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
            "transaction_batch_count": transaction_summary["transaction_batch_count"],
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
        "recovery_timeline": build_generic_edit_manifest_recovery_timeline(events),
        "native_tool_fallbacks": compact_generic_edit_native_tool_fallbacks(
            trace_summary.get("native_tool_fallbacks")
        ),
        "transaction_batches": compact_generic_edit_manifest_transaction_batches(
            transaction_summary
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
        "resume_inputs": resume_inputs,
        "resume_policy": resume_policy,
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
    event_path = artifact_refs["events"]
    checkpoint_path = artifact_refs["checkpoint"]
    mutation_snapshot_path = artifact_refs["mutation_snapshots"]
    transaction_group_path = artifact_refs["transaction_groups"]
    observation_path = artifact_refs.get("observation")
    if (
        trace_path is None
        or event_path is None
        or checkpoint_path is None
        or mutation_snapshot_path is None
        or transaction_group_path is None
    ):
        raise GenericEditRuntimeError(
            "Generic edit recovery artifact paths are incomplete."
        )
    resume_inputs = build_generic_edit_resume_input_artifacts(
        artifact_refs=artifact_refs,
        recovery_plan=recovery_plan,
        mutation_snapshots=mutation_snapshots,
        transaction_group_summary=transaction_group_summary,
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
        "event_artifact": str(event_path),
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
        "resume_inputs": resume_inputs,
        "resume_policy": build_generic_edit_resume_policy(
            strategy=strategy,
            checkpoint_path=str(checkpoint_path),
            next_iteration=next_iteration,
            resume_inputs=resume_inputs,
            transaction_summary=transaction_summary,
            transaction_group_summary=transaction_group_summary,
            recovery_plan=recovery_plan,
        ),
        "recent_actions": list(trace_summary.get("action_timeline") or [])[-10:],
        "transaction_summary": transaction_summary,
        "transaction_group_summary": transaction_group_summary,
        "unresolved_partial_failure_ids": transaction_summary[
            "unresolved_partial_failure_ids"
        ],
        "unresolved_transaction_group_ids": transaction_group_summary[
            "unresolved_transaction_group_ids"
        ],
        "open_transaction_batch_ids": transaction_summary["open_transaction_batch_ids"],
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
        raise generic_edit_resume_artifact_error(
            f"Generic edit recovery checkpoint not found: {checkpoint_path}",
            artifact="recovery_checkpoint",
            reason="missing",
            path=checkpoint_path,
        ) from e
    except json.JSONDecodeError as e:
        raise generic_edit_resume_artifact_error(
            f"Generic edit recovery checkpoint is not valid JSON: {e}",
            artifact="recovery_checkpoint",
            reason="corrupt_json",
            path=checkpoint_path,
        ) from e

    if not isinstance(payload, dict):
        raise generic_edit_resume_artifact_error(
            "Generic edit recovery checkpoint must be a JSON object.",
            artifact="recovery_checkpoint",
            reason="invalid_schema",
            path=checkpoint_path,
        )
    if payload.get("recoverable") is not True:
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint is not marked recoverable."
        )
    if not isinstance(payload.get("resume"), dict):
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint is missing resume metadata."
        )
    resume_policy = payload.get("resume_policy")
    if not isinstance(resume_policy, dict):
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint is missing resume policy metadata."
        )
    if resume_policy.get("runtime") != "generic_edit":
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint resume policy targets an unexpected runtime."
        )
    policy_checkpoint_path = resume_policy.get("checkpoint_path")
    if (
        not isinstance(policy_checkpoint_path, str)
        or not policy_checkpoint_path
        or Path(policy_checkpoint_path).resolve() != checkpoint_path.resolve()
    ):
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint resume policy must reference the "
            "canonical recovery checkpoint."
        )
    if resume_policy.get("can_resume") is not True:
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint resume policy is not resumable."
        )
    resume = payload["resume"]
    if resume_policy.get("strategy") != resume.get("strategy") or resume_policy.get(
        "next_iteration"
    ) != payload.get("next_iteration"):
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint resume policy does not match resume metadata."
        )
    unresolved_policy_ids = [
        *normalize_string_list(resume_policy.get("unresolved_partial_failure_ids")),
        *normalize_string_list(resume_policy.get("unresolved_transaction_group_ids")),
    ]
    if unresolved_policy_ids and (
        resume_policy.get("finish_blocked") is not True
        or str(resume_policy.get("status") or "") == "ready"
    ):
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint resume policy cannot mark unresolved "
            "failures as unblocked."
        )
    resume_inputs = payload.get("resume_inputs")
    if not isinstance(resume_inputs, dict):
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint is missing resume input metadata."
        )
    for artifact_name in normalize_string_list(resume_policy.get("required_artifacts")):
        artifact_path = resume_inputs.get(artifact_name)
        if not isinstance(artifact_path, str) or not artifact_path:
            raise generic_edit_required_resume_artifact_error(
                "Generic edit recovery checkpoint is missing required resume artifact: "
                f"{artifact_name}.",
                owner_artifact="recovery_checkpoint",
                owner_path=checkpoint_path,
                artifact_name=artifact_name,
                artifact_path=None,
                reason="missing_path",
            )
        if not Path(artifact_path).exists():
            raise generic_edit_required_resume_artifact_error(
                "Generic edit recovery checkpoint required resume artifact does not "
                f"exist: {artifact_name}.",
                owner_artifact="recovery_checkpoint",
                owner_path=checkpoint_path,
                artifact_name=artifact_name,
                artifact_path=artifact_path,
                reason="missing",
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
        raise generic_edit_resume_artifact_error(
            f"Generic edit session state not found: {session_state_path}",
            artifact="session_state",
            reason="missing",
            path=session_state_path,
        ) from e
    except json.JSONDecodeError as e:
        raise generic_edit_resume_artifact_error(
            f"Generic edit session state is not valid JSON: {e}",
            artifact="session_state",
            reason="corrupt_json",
            path=session_state_path,
        ) from e

    if not isinstance(payload, dict):
        raise generic_edit_resume_artifact_error(
            "Generic edit session state must be a JSON object.",
            artifact="session_state",
            reason="invalid_schema",
            path=session_state_path,
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
    resume_inputs = payload.get("resume_inputs")
    if not isinstance(resume_inputs, dict):
        raise GenericEditRuntimeError(
            "Generic edit session state is missing resume input metadata."
        )
    resume_policy = payload.get("resume_policy")
    if not isinstance(resume_policy, dict):
        raise GenericEditRuntimeError(
            "Generic edit session state is missing resume policy metadata."
        )
    if resume_policy.get("runtime") != "generic_edit":
        raise GenericEditRuntimeError(
            "Generic edit session state resume policy targets an unexpected runtime."
        )
    policy_checkpoint_path = resume_policy.get("checkpoint_path")
    if (
        not isinstance(policy_checkpoint_path, str)
        or not policy_checkpoint_path
        or Path(policy_checkpoint_path).resolve() != expected_checkpoint_path.resolve()
    ):
        raise GenericEditRuntimeError(
            "Generic edit session state resume policy must reference the "
            "canonical recovery checkpoint."
        )
    for artifact_name in normalize_string_list(resume_policy.get("required_artifacts")):
        artifact_path = resume_inputs.get(artifact_name)
        if not isinstance(artifact_path, str) or not artifact_path:
            raise generic_edit_required_resume_artifact_error(
                "Generic edit session state is missing required resume artifact: "
                f"{artifact_name}.",
                owner_artifact="session_state",
                owner_path=session_state_path,
                artifact_name=artifact_name,
                artifact_path=None,
                reason="missing_path",
            )
    if resume_policy.get("can_resume") is not True:
        raise GenericEditRuntimeError(
            "Generic edit session state resume policy is not resumable."
        )
    if resume_policy.get("strategy") != resume_action.get(
        "strategy"
    ) or resume_policy.get("next_iteration") != resume_action.get("next_iteration"):
        raise GenericEditRuntimeError(
            "Generic edit session state resume policy does not match resume action."
        )
    unresolved_policy_ids = [
        *normalize_string_list(resume_policy.get("unresolved_partial_failure_ids")),
        *normalize_string_list(resume_policy.get("unresolved_transaction_group_ids")),
    ]
    if unresolved_policy_ids and (
        resume_policy.get("finish_blocked") is not True
        or str(resume_policy.get("status") or "") == "ready"
    ):
        raise GenericEditRuntimeError(
            "Generic edit session state resume policy cannot mark unresolved "
            "failures as unblocked."
        )
    for artifact_name in normalize_string_list(resume_policy.get("required_artifacts")):
        artifact_path = Path(str(resume_inputs[artifact_name]))
        if not artifact_path.exists():
            raise generic_edit_required_resume_artifact_error(
                "Generic edit session state required resume artifact does not exist: "
                f"{artifact_name}.",
                owner_artifact="session_state",
                owner_path=session_state_path,
                artifact_name=artifact_name,
                artifact_path=str(artifact_path),
                reason="missing",
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
    if not all(isinstance(snapshot, dict) for snapshot in snapshots):
        raise GenericEditRuntimeError(
            "Generic edit mutation snapshot artifact contains invalid snapshot entries."
        )
    expected_count = payload.get("snapshot_count")
    if isinstance(expected_count, int) and expected_count != len(snapshots):
        raise GenericEditRuntimeError(
            "Generic edit mutation snapshot count does not match snapshots."
        )
    return snapshots


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


def generic_edit_artifact_manifest_path_for_checkpoint(checkpoint_path: Path) -> Path:
    """Return the trusted artifact manifest path colocated with a checkpoint."""
    return checkpoint_path.parent / "generic_edit_artifact_manifest.json"


def load_generic_edit_artifact_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load and validate the optional generic_edit artifact manifest."""
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise generic_edit_resume_artifact_error(
            f"Generic edit artifact manifest not found: {manifest_path}",
            artifact="artifact_manifest",
            reason="missing",
            path=manifest_path,
        ) from e
    except json.JSONDecodeError as e:
        raise generic_edit_resume_artifact_error(
            f"Generic edit artifact manifest is not valid JSON: {e}",
            artifact="artifact_manifest",
            reason="corrupt_json",
            path=manifest_path,
        ) from e

    if not isinstance(payload, dict):
        raise generic_edit_resume_artifact_error(
            "Generic edit artifact manifest must be a JSON object.",
            artifact="artifact_manifest",
            reason="invalid_schema",
            path=manifest_path,
        )
    if payload.get("artifact_type") != "generic_edit_artifact_manifest":
        raise generic_edit_resume_artifact_error(
            "Generic edit artifact manifest has unexpected artifact type.",
            artifact="artifact_manifest",
            reason="invalid_schema",
            path=manifest_path,
        )
    return payload


def load_generic_edit_checkpoint_trace(
    trace_path: Path,
) -> list[dict[str, Any]]:
    """Load the trace referenced by a recovery checkpoint."""
    try:
        payload = json.loads(trace_path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise generic_edit_resume_artifact_error(
            f"Generic edit recovery trace not found: {trace_path}",
            artifact="trace",
            reason="missing",
            path=trace_path,
        ) from e
    except json.JSONDecodeError as e:
        raise generic_edit_resume_artifact_error(
            f"Generic edit recovery trace is not valid JSON: {e}",
            artifact="trace",
            reason="corrupt_json",
            path=trace_path,
        ) from e

    trace = payload.get("trace") if isinstance(payload, dict) else None
    if not isinstance(trace, list) or not all(isinstance(item, dict) for item in trace):
        raise generic_edit_resume_artifact_error(
            "Generic edit recovery trace must contain a trace object list.",
            artifact="trace",
            reason="invalid_schema",
            path=trace_path,
        )
    return trace


def validate_generic_edit_checkpoint_trace_consistency(
    *,
    checkpoint: dict[str, Any],
    trace: list[dict[str, Any]],
) -> None:
    """Reject recovery when checkpoint metadata and trace contents diverge."""
    next_iteration = checkpoint.get("next_iteration")
    if isinstance(next_iteration, int) and next_iteration > 0:
        expected_trace_length = next_iteration - 1
        if len(trace) != expected_trace_length:
            raise generic_edit_resume_artifact_error(
                "Generic edit recovery trace does not match checkpoint metadata: "
                f"expected {expected_trace_length} iteration(s), found {len(trace)}.",
                artifact="trace",
                reason="checkpoint_mismatch",
                expected_iterations=expected_trace_length,
                actual_iterations=len(trace),
            )
    transaction_summary = checkpoint.get("transaction_summary")
    if isinstance(transaction_summary, dict):
        expected_transaction_count = transaction_summary.get("transaction_count")
        actual_transaction_count = summarize_generic_edit_transactions(trace)[
            "transaction_count"
        ]
        if (
            isinstance(expected_transaction_count, int)
            and expected_transaction_count != actual_transaction_count
        ):
            raise generic_edit_resume_artifact_error(
                "Generic edit recovery trace does not match checkpoint transaction "
                "metadata: expected "
                f"{expected_transaction_count}, found {actual_transaction_count}.",
                artifact="trace",
                reason="checkpoint_mismatch",
                expected_transaction_count=expected_transaction_count,
                actual_transaction_count=actual_transaction_count,
            )


def validate_generic_edit_session_state_checkpoint_consistency(
    *,
    session_state: dict[str, Any],
    checkpoint: dict[str, Any],
    session_state_path: Path,
) -> None:
    """Reject resume when session_state and checkpoint describe different runs."""
    session_resume_action = session_state.get("resume_action")
    checkpoint_resume = checkpoint.get("resume")
    if not isinstance(session_resume_action, dict) or not isinstance(
        checkpoint_resume, dict
    ):
        return

    checkpoint_policy = checkpoint.get("resume_policy")
    session_policy = session_state.get("resume_policy")
    if session_policy != checkpoint_policy:
        raise generic_edit_resume_artifact_error(
            "Generic edit session state resume policy does not match recovery checkpoint.",
            artifact="session_state",
            reason="checkpoint_mismatch",
            path=session_state_path,
        )
    if session_resume_action.get("strategy") != checkpoint_resume.get(
        "strategy"
    ) or session_resume_action.get("next_iteration") != checkpoint.get(
        "next_iteration"
    ):
        raise generic_edit_resume_artifact_error(
            "Generic edit session state resume action does not match recovery checkpoint.",
            artifact="session_state",
            reason="checkpoint_mismatch",
            path=session_state_path,
        )
    if session_state.get("resume_inputs") != checkpoint.get("resume_inputs"):
        raise generic_edit_resume_artifact_error(
            "Generic edit session state resume inputs do not match recovery checkpoint.",
            artifact="session_state",
            reason="checkpoint_mismatch",
            path=session_state_path,
        )


def generic_edit_expected_resume_counts(
    *,
    checkpoint: dict[str, Any],
    trace: list[dict[str, Any]],
) -> dict[str, int]:
    """Return canonical resume counters derived from checkpoint and trace."""
    trace_summary = summarize_generic_edit_trace(trace)
    transaction_summary = summarize_generic_edit_transactions(trace)
    return {
        "iteration_count": len(trace),
        "action_count": int(trace_summary.get("action_count") or 0),
        "failed_action_count": int(trace_summary.get("failed_action_count") or 0),
        "transaction_count": int(transaction_summary.get("transaction_count") or 0),
        "next_iteration": int(checkpoint.get("next_iteration") or len(trace) + 1),
    }


def generic_edit_validate_resume_count_fields(
    *,
    count_payload: dict[str, Any],
    expected_counts: dict[str, int],
    artifact: str,
    path: Path,
) -> None:
    """Reject stale resume counters when artifacts expose them."""
    for field, expected_value in expected_counts.items():
        actual_value = count_payload.get(field)
        if actual_value is None:
            continue
        if actual_value != expected_value:
            raise generic_edit_resume_artifact_error(
                f"Generic edit {artifact} {field} does not match checkpoint trace.",
                artifact=artifact,
                reason="checkpoint_mismatch",
                path=path,
                **{
                    f"expected_{field}": expected_value,
                    f"actual_{field}": actual_value,
                },
            )


def validate_generic_edit_session_state_trace_counts(
    *,
    session_state: dict[str, Any],
    checkpoint: dict[str, Any],
    trace: list[dict[str, Any]],
    session_state_path: Path,
) -> None:
    """Reject session state counters that disagree with checkpoint trace contents."""
    generic_edit_validate_resume_count_fields(
        count_payload=session_state,
        expected_counts=generic_edit_expected_resume_counts(
            checkpoint=checkpoint,
            trace=trace,
        ),
        artifact="session_state",
        path=session_state_path,
    )


def generic_edit_raise_manifest_mismatch(message: str, manifest_path: Path) -> None:
    """Raise a structured manifest/checkpoint mismatch error."""
    raise generic_edit_resume_artifact_error(
        message,
        artifact="artifact_manifest",
        reason="checkpoint_mismatch",
        path=manifest_path,
    )


def validate_generic_edit_manifest_trace_counts(
    *,
    manifest: dict[str, Any],
    checkpoint: dict[str, Any],
    trace: list[dict[str, Any]],
    manifest_path: Path,
) -> None:
    """Reject manifest counters that disagree with checkpoint trace contents."""
    counts = manifest.get("counts")
    if not isinstance(counts, dict):
        return
    generic_edit_validate_resume_count_fields(
        count_payload=counts,
        expected_counts=generic_edit_expected_resume_counts(
            checkpoint=checkpoint,
            trace=trace,
        ),
        artifact="artifact_manifest",
        path=manifest_path,
    )


def validate_generic_edit_manifest_resume_action(
    *,
    manifest: dict[str, Any],
    checkpoint: dict[str, Any],
    checkpoint_path: Path,
    manifest_path: Path,
) -> None:
    """Reject manifest resume actions that disagree with the checkpoint."""
    resume_action = manifest.get("resume_action")
    checkpoint_resume = checkpoint.get("resume")
    if not isinstance(resume_action, dict) or not isinstance(checkpoint_resume, dict):
        generic_edit_raise_manifest_mismatch(
            "Generic edit artifact manifest is missing resume action metadata.",
            manifest_path,
        )
    checkpoint_path_value = resume_action.get("checkpoint_path")
    if (
        not isinstance(checkpoint_path_value, str)
        or Path(checkpoint_path_value).resolve() != checkpoint_path.resolve()
    ):
        generic_edit_raise_manifest_mismatch(
            "Generic edit artifact manifest resume action references a different checkpoint.",
            manifest_path,
        )
    if resume_action.get("strategy") != checkpoint_resume.get(
        "strategy"
    ) or resume_action.get("next_iteration") != checkpoint.get("next_iteration"):
        generic_edit_raise_manifest_mismatch(
            "Generic edit artifact manifest resume action does not match checkpoint.",
            manifest_path,
        )


def validate_generic_edit_manifest_entrypoints(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    session_state_path: Path,
    trace_path: Path,
) -> None:
    """Reject manifest entrypoints that point away from canonical resume artifacts."""
    entrypoints = manifest.get("entrypoints")
    if not isinstance(entrypoints, dict):
        generic_edit_raise_manifest_mismatch(
            "Generic edit artifact manifest is missing entrypoints.",
            manifest_path,
        )
    expected_paths = {
        "session_state": session_state_path.resolve(),
        "trace": trace_path.resolve(),
    }
    for name, expected_path in expected_paths.items():
        value = entrypoints.get(name)
        if not isinstance(value, str) or Path(value).resolve() != expected_path:
            generic_edit_raise_manifest_mismatch(
                f"Generic edit artifact manifest {name} entrypoint is stale.",
                manifest_path,
            )


def validate_generic_edit_artifact_manifest_checkpoint_consistency(
    *,
    manifest: dict[str, Any],
    checkpoint: dict[str, Any],
    checkpoint_path: Path,
    session_state_path: Path,
    trace_path: Path,
    manifest_path: Path,
) -> None:
    """Reject resume when manifest, checkpoint, and canonical paths diverge."""
    flags = manifest.get("flags")
    if not isinstance(flags, dict) or flags.get("resumable") is not True:
        generic_edit_raise_manifest_mismatch(
            "Generic edit artifact manifest is not marked resumable.",
            manifest_path,
        )
    if manifest.get("resume_policy") != checkpoint.get("resume_policy"):
        generic_edit_raise_manifest_mismatch(
            "Generic edit artifact manifest resume policy does not match checkpoint.",
            manifest_path,
        )
    if manifest.get("resume_inputs") != checkpoint.get("resume_inputs"):
        generic_edit_raise_manifest_mismatch(
            "Generic edit artifact manifest resume inputs do not match checkpoint.",
            manifest_path,
        )
    validate_generic_edit_manifest_resume_action(
        manifest=manifest,
        checkpoint=checkpoint,
        checkpoint_path=checkpoint_path,
        manifest_path=manifest_path,
    )
    validate_generic_edit_manifest_entrypoints(
        manifest=manifest,
        manifest_path=manifest_path,
        session_state_path=session_state_path,
        trace_path=trace_path,
    )


def collect_generic_edit_mutation_snapshot_ids(value: Any) -> list[str]:
    """Collect mutation snapshot references from checkpoint metadata."""
    snapshot_ids: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "mutation_snapshot_ids":
                snapshot_ids.extend(normalize_string_list(item))
            else:
                snapshot_ids.extend(collect_generic_edit_mutation_snapshot_ids(item))
    elif isinstance(value, list):
        for item in value:
            snapshot_ids.extend(collect_generic_edit_mutation_snapshot_ids(item))
    return list(dict.fromkeys(snapshot_ids))


def validate_generic_edit_checkpoint_mutation_snapshots(
    *,
    checkpoint: dict[str, Any],
    mutation_snapshots: list[dict[str, Any]],
    mutation_snapshot_path: Path,
) -> None:
    """Reject resume when checkpoint references snapshots absent from artifact."""
    expected_snapshot_ids = collect_generic_edit_mutation_snapshot_ids(checkpoint)
    if not expected_snapshot_ids:
        return
    actual_snapshot_ids = {
        str(snapshot.get("id"))
        for snapshot in mutation_snapshots
        if isinstance(snapshot.get("id"), str) and snapshot.get("id")
    }
    missing_snapshot_ids = [
        snapshot_id
        for snapshot_id in expected_snapshot_ids
        if snapshot_id not in actual_snapshot_ids
    ]
    if missing_snapshot_ids:
        raise generic_edit_resume_artifact_error(
            "Generic edit mutation snapshot artifact is missing checkpoint "
            "snapshot reference(s): " + ", ".join(missing_snapshot_ids[:10]) + ".",
            artifact="mutation_snapshots",
            reason="checkpoint_mismatch",
            path=mutation_snapshot_path,
            missing_snapshot_ids=missing_snapshot_ids,
            expected_snapshot_ids=expected_snapshot_ids,
            actual_snapshot_ids=sorted(actual_snapshot_ids),
        )


def checkpoint_next_iteration(
    checkpoint: dict[str, Any],
    trace: list[dict[str, Any]],
) -> int:
    """Return the next iteration number for a resumed generic_edit loop."""
    next_iteration = checkpoint.get("next_iteration")
    if isinstance(next_iteration, int) and next_iteration > 0:
        return max(next_iteration, len(trace) + 1)
    return len(trace) + 1


def generic_edit_resume_open_batch_id(
    *,
    checkpoint: dict[str, Any],
    trace: list[dict[str, Any]],
) -> str | None:
    """Return the single open batch that must remain active across resume."""
    open_batch_ids = normalize_string_list(checkpoint.get("open_transaction_batch_ids"))
    if not open_batch_ids:
        transaction_summary = checkpoint.get("transaction_summary")
        if isinstance(transaction_summary, dict):
            open_batch_ids = normalize_string_list(
                transaction_summary.get("open_transaction_batch_ids")
            )
    if not open_batch_ids:
        open_batch_ids = summarize_generic_edit_transactions(trace)[
            "open_transaction_batch_ids"
        ]
    if len(open_batch_ids) > 1:
        raise GenericEditRuntimeError(
            "Generic edit recovery checkpoint contains multiple open batches; "
            "resume supports one active transaction batch."
        )
    return open_batch_ids[0] if open_batch_ids else None


def inspect_generic_edit_resume_artifacts(
    *,
    checkpoint_path: Path,
    spec_dir: Path,
    project_dir: Path,
) -> dict[str, Any]:
    """Return read-only diagnostics for a generic_edit resume checkpoint."""
    artifacts: dict[str, Any] = {}
    try:
        resolved_checkpoint_path = resolve_generic_edit_resume_checkpoint_path(
            checkpoint_path=checkpoint_path,
            spec_dir=spec_dir,
        )
    except GenericEditRuntimeError as e:
        return generic_edit_resume_blocked_preflight(
            checkpoint_path=checkpoint_path,
            spec_dir=spec_dir,
            project_dir=project_dir,
            artifact_health=generic_edit_resume_error_health(
                e,
                artifact="resume_checkpoint_path",
                path=checkpoint_path,
            ),
            artifacts=artifacts,
        )

    artifacts["recovery_checkpoint"] = {
        "status": "pending",
        "path": str(resolved_checkpoint_path),
    }
    session_state_path = (
        spec_dir / "artifacts" / "generic_edit_session_state.json"
    ).resolve()
    session_state: dict[str, Any] | None = None
    if session_state_path.exists():
        try:
            session_state = load_generic_edit_session_state(
                session_state_path,
                expected_checkpoint_path=resolved_checkpoint_path,
            )
        except GenericEditRuntimeError as e:
            return generic_edit_resume_blocked_preflight(
                checkpoint_path=checkpoint_path,
                spec_dir=spec_dir,
                project_dir=project_dir,
                artifact_health=generic_edit_resume_error_health(
                    e,
                    artifact="session_state",
                    path=session_state_path,
                ),
                artifacts=artifacts,
            )
        artifacts["session_state"] = {
            "status": "ready",
            "path": str(session_state_path),
        }
    else:
        artifacts["session_state"] = {
            "status": "missing_optional",
            "path": str(session_state_path),
        }

    try:
        checkpoint = load_generic_edit_recovery_checkpoint(resolved_checkpoint_path)
    except GenericEditRuntimeError as e:
        return generic_edit_resume_blocked_preflight(
            checkpoint_path=checkpoint_path,
            spec_dir=spec_dir,
            project_dir=project_dir,
            artifact_health=generic_edit_resume_error_health(
                e,
                artifact="recovery_checkpoint",
                path=resolved_checkpoint_path,
            ),
            artifacts=artifacts,
        )
    artifacts["recovery_checkpoint"]["status"] = "ready"
    if session_state is not None:
        try:
            validate_generic_edit_session_state_checkpoint_consistency(
                session_state=session_state,
                checkpoint=checkpoint,
                session_state_path=session_state_path,
            )
        except GenericEditRuntimeError as e:
            return generic_edit_resume_blocked_preflight(
                checkpoint_path=checkpoint_path,
                spec_dir=spec_dir,
                project_dir=project_dir,
                artifact_health=generic_edit_resume_error_health(
                    e,
                    artifact="session_state",
                    path=session_state_path,
                ),
                artifacts=artifacts,
            )

    trace_path = generic_edit_trace_path_for_checkpoint(resolved_checkpoint_path)
    artifact_manifest_path = generic_edit_artifact_manifest_path_for_checkpoint(
        resolved_checkpoint_path,
    )
    artifact_manifest: dict[str, Any] | None = None
    artifacts["artifact_manifest"] = {
        "status": "pending",
        "path": str(artifact_manifest_path),
    }
    if artifact_manifest_path.exists():
        try:
            artifact_manifest = load_generic_edit_artifact_manifest(
                artifact_manifest_path
            )
            validate_generic_edit_artifact_manifest_checkpoint_consistency(
                manifest=artifact_manifest,
                checkpoint=checkpoint,
                checkpoint_path=resolved_checkpoint_path,
                session_state_path=session_state_path,
                trace_path=trace_path,
                manifest_path=artifact_manifest_path,
            )
        except GenericEditRuntimeError as e:
            return generic_edit_resume_blocked_preflight(
                checkpoint_path=checkpoint_path,
                spec_dir=spec_dir,
                project_dir=project_dir,
                artifact_health=generic_edit_resume_error_health(
                    e,
                    artifact="artifact_manifest",
                    path=artifact_manifest_path,
                ),
                artifacts=artifacts,
            )
        artifacts["artifact_manifest"] = {
            "status": "ready",
            "path": str(artifact_manifest_path),
            "schema_version": artifact_manifest.get("schema_version"),
        }
    else:
        artifacts["artifact_manifest"] = {
            "status": "missing_optional",
            "path": str(artifact_manifest_path),
        }

    artifacts["trace"] = {"status": "pending", "path": str(trace_path)}
    try:
        trace = load_generic_edit_checkpoint_trace(trace_path)
        validate_generic_edit_checkpoint_trace_consistency(
            checkpoint=checkpoint,
            trace=trace,
        )
    except GenericEditRuntimeError as e:
        return generic_edit_resume_blocked_preflight(
            checkpoint_path=checkpoint_path,
            spec_dir=spec_dir,
            project_dir=project_dir,
            artifact_health=generic_edit_resume_error_health(
                e,
                artifact="trace",
                path=trace_path,
            ),
            artifacts=artifacts,
        )
    artifacts["trace"] = {
        "status": "ready",
        "path": str(trace_path),
        "iteration_count": len(trace),
    }
    if session_state is not None:
        try:
            validate_generic_edit_session_state_trace_counts(
                session_state=session_state,
                checkpoint=checkpoint,
                trace=trace,
                session_state_path=session_state_path,
            )
        except GenericEditRuntimeError as e:
            return generic_edit_resume_blocked_preflight(
                checkpoint_path=checkpoint_path,
                spec_dir=spec_dir,
                project_dir=project_dir,
                artifact_health=generic_edit_resume_error_health(
                    e,
                    artifact="session_state",
                    path=session_state_path,
                ),
                artifacts=artifacts,
            )
    if artifact_manifest is not None:
        try:
            validate_generic_edit_manifest_trace_counts(
                manifest=artifact_manifest,
                checkpoint=checkpoint,
                trace=trace,
                manifest_path=artifact_manifest_path,
            )
        except GenericEditRuntimeError as e:
            return generic_edit_resume_blocked_preflight(
                checkpoint_path=checkpoint_path,
                spec_dir=spec_dir,
                project_dir=project_dir,
                artifact_health=generic_edit_resume_error_health(
                    e,
                    artifact="artifact_manifest",
                    path=artifact_manifest_path,
                ),
                artifacts=artifacts,
            )

    mutation_snapshot_path = generic_edit_mutation_snapshot_path_for_checkpoint(
        resolved_checkpoint_path,
    )
    artifacts["mutation_snapshots"] = {
        "status": "pending",
        "path": str(mutation_snapshot_path),
    }
    try:
        mutation_snapshots = load_generic_edit_mutation_snapshots(
            mutation_snapshot_path,
        )
    except GenericEditRuntimeError as e:
        return generic_edit_resume_blocked_preflight(
            checkpoint_path=checkpoint_path,
            spec_dir=spec_dir,
            project_dir=project_dir,
            artifact_health=generic_edit_resume_error_health(
                e,
                artifact="mutation_snapshots",
                path=mutation_snapshot_path,
            ),
            artifacts=artifacts,
        )
    artifacts["mutation_snapshots"] = {
        "status": "ready" if mutation_snapshot_path.exists() else "missing_optional",
        "path": str(mutation_snapshot_path),
        "snapshot_count": len(mutation_snapshots),
    }
    try:
        validate_generic_edit_checkpoint_mutation_snapshots(
            checkpoint=checkpoint,
            mutation_snapshots=mutation_snapshots,
            mutation_snapshot_path=mutation_snapshot_path,
        )
    except GenericEditRuntimeError as e:
        return generic_edit_resume_blocked_preflight(
            checkpoint_path=checkpoint_path,
            spec_dir=spec_dir,
            project_dir=project_dir,
            artifact_health=generic_edit_resume_error_health(
                e,
                artifact="mutation_snapshots",
                path=mutation_snapshot_path,
            ),
            artifacts=artifacts,
        )

    try:
        active_batch_id = generic_edit_resume_open_batch_id(
            checkpoint=checkpoint,
            trace=trace,
        )
        workspace_guard = validate_generic_edit_resume_workspace_guard(
            project_dir=project_dir,
            mutation_snapshots=mutation_snapshots,
        )
    except GenericEditRuntimeError as e:
        return generic_edit_resume_blocked_preflight(
            checkpoint_path=checkpoint_path,
            spec_dir=spec_dir,
            project_dir=project_dir,
            artifact_health=generic_edit_resume_error_health(
                e,
                artifact="workspace_guard",
            ),
            artifacts=artifacts,
        )

    resume = (
        checkpoint.get("resume") if isinstance(checkpoint.get("resume"), dict) else {}
    )
    resume_policy = (
        checkpoint.get("resume_policy")
        if isinstance(checkpoint.get("resume_policy"), dict)
        else {}
    )
    return {
        "runtime": "generic_edit",
        "status": "ready",
        "requested_path": str(checkpoint_path),
        "checkpoint_path": str(resolved_checkpoint_path),
        "spec_dir": str(spec_dir),
        "project_dir": str(project_dir),
        "artifacts": artifacts,
        "resume": {
            "strategy": str(resume.get("strategy") or "unknown"),
            "next_iteration": checkpoint_next_iteration(checkpoint, trace),
            "active_batch_id": active_batch_id,
        },
        "resume_policy": {
            "status": resume_policy.get("status", "unknown"),
            "can_resume": bool(resume_policy.get("can_resume")),
            "finish_blocked": bool(resume_policy.get("finish_blocked")),
            "required_resolution_action_kinds": normalize_string_list(
                resume_policy.get("required_resolution_action_kinds")
            ),
            "required_artifacts": normalize_string_list(
                resume_policy.get("required_artifacts")
            ),
            "unresolved_partial_failure_ids": normalize_string_list(
                resume_policy.get("unresolved_partial_failure_ids")
            ),
            "unresolved_transaction_group_ids": normalize_string_list(
                resume_policy.get("unresolved_transaction_group_ids")
            ),
            "open_transaction_batch_ids": normalize_string_list(
                resume_policy.get("open_transaction_batch_ids")
            ),
        },
        "workspace_guard": workspace_guard,
        "blockers": [],
    }


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
    resume_policy = checkpoint.get("resume_policy")
    if isinstance(resume_policy, dict):
        policy_status = resume_policy.get("status")
        if isinstance(policy_status, str) and policy_status:
            lines.append(f"Resume policy: {policy_status}")
        required_actions = normalize_string_list(
            resume_policy.get("required_resolution_action_kinds")
        )
        if required_actions:
            lines.append("Required recovery actions: " + ", ".join(required_actions))
        required_artifacts = normalize_string_list(
            resume_policy.get("required_artifacts")
        )
        if required_artifacts:
            lines.append("Required resume artifacts: " + ", ".join(required_artifacts))
        unresolved_failures = normalize_string_list(
            resume_policy.get("unresolved_partial_failure_ids")
        )
        if unresolved_failures:
            lines.append(
                "Unresolved partial failures: " + ", ".join(unresolved_failures)
            )
        unresolved_groups = normalize_string_list(
            resume_policy.get("unresolved_transaction_group_ids")
        )
        if unresolved_groups:
            lines.append(
                "Unresolved transaction groups: " + ", ".join(unresolved_groups)
            )
    recovery_plan_artifact = checkpoint.get("recovery_plan_artifact")
    if isinstance(recovery_plan_artifact, str) and recovery_plan_artifact:
        lines.append(f"Recovery plan artifact: {recovery_plan_artifact}")
    mutation_snapshot_artifact = checkpoint.get("mutation_snapshot_artifact")
    if isinstance(mutation_snapshot_artifact, str) and mutation_snapshot_artifact:
        lines.append(f"Mutation snapshot artifact: {mutation_snapshot_artifact}")
    transaction_group_artifact = checkpoint.get("transaction_group_artifact")
    if isinstance(transaction_group_artifact, str) and transaction_group_artifact:
        lines.append(f"Transaction group artifact: {transaction_group_artifact}")
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
    workspace_guard: dict[str, Any] | None = None,
    active_batch_id: str | None = None,
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
    if workspace_guard is not None:
        metadata["workspace_guard"] = workspace_guard
    if active_batch_id:
        metadata["active_batch_id"] = active_batch_id
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
    if transaction_summary["open_transaction_batch_count"] > 0:
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
    if transaction_summary["open_transaction_batch_count"] > 0:
        return "resolve_open_batch"
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
    elif strategy == "resolve_open_batch":
        open_batch_ids = transaction_summary.get("open_transaction_batch_ids") or []
        prompt_lines.extend(
            [
                "Open transaction batch(es): " + ", ".join(open_batch_ids),
                "Commit each open batch with commit_batch, or abort it with "
                "abort_batch to rollback staged mutations, before calling finish.",
                "Inspect current workspace state before choosing commit or abort.",
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
    recovery_checkpoint: dict[str, Any] | None,
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
    resume_policy_event = build_generic_edit_resume_policy_event(
        recovery_checkpoint=recovery_checkpoint,
        provider_name=provider_name,
        subtask_id=subtask_id,
    )
    if resume_policy_event is not None:
        events.append(resume_policy_event)
    for sequence, event in enumerate(events, start=1):
        enrich_generic_edit_timeline_event(event)
        event["sequence"] = sequence
    return events


def enrich_generic_edit_timeline_event(event: dict[str, Any]) -> None:
    """Attach UI-facing timeline semantics to normalized runtime events."""
    event_type = str(event.get("event_type") or "")
    if event_type == "resume":
        workspace_guard_status = str(event.get("workspace_guard_status") or "")
        event["timeline_stage"] = (
            "resume_clean" if workspace_guard_status == "clean" else "resume"
        )
        return
    if event_type == "transaction" and event.get("status") == "partial_failure":
        event["timeline_stage"] = "partial_failure"
        event["requires_user_action"] = True
        return
    if event_type == "transaction" and event.get("batch_status") == "open":
        event["timeline_stage"] = "batch_open"
        event["requires_user_action"] = True
        return
    if event_type == "transaction_group":
        if event.get("status") == "unresolved":
            event["timeline_stage"] = "recovery_policy"
            event["requires_user_action"] = True
            return
        if event.get("status") == "resolved":
            event["timeline_stage"] = "recovery_resolved"
            return
    if event_type == "resume_policy":
        event["timeline_stage"] = "resume_policy"
        if event.get("finish_blocked"):
            event["requires_user_action"] = True
        return
    if event_type == "action_result" and event.get("batch_boundary_error"):
        event["timeline_stage"] = "batch_boundary_blocked"
        event["requires_user_action"] = True
        return
    if event_type == "action_result" and event.get("tool") in {
        ROLLBACK_TRANSACTION_TOOL,
        REPAIR_MUTATION_TOOL,
        ABORT_BATCH_TOOL,
    }:
        event["timeline_stage"] = "recovery_action"
        return


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
    active_batch_id = resume_metadata.get("active_batch_id")
    if isinstance(active_batch_id, str) and active_batch_id:
        event["active_batch_id"] = active_batch_id
    for key in (
        "recovery_plan_artifact",
        "mutation_snapshot_artifact",
        "transaction_group_artifact",
    ):
        value = resume_metadata.get(key)
        if isinstance(value, str) and value:
            event[key] = value
    workspace_guard = resume_metadata.get("workspace_guard")
    if isinstance(workspace_guard, dict):
        event["workspace_guard_status"] = str(
            workspace_guard.get("status") or "unknown"
        )
        event["workspace_guard_drift_count"] = int(
            workspace_guard.get("drift_count") or 0
        )
        event["workspace_guard_unverified_path_count"] = int(
            workspace_guard.get("unverified_path_count") or 0
        )
    return event


def build_generic_edit_resume_policy_event(
    *,
    recovery_checkpoint: dict[str, Any] | None,
    provider_name: str,
    subtask_id: str | None,
) -> dict[str, Any] | None:
    """Return a normalized event for newly created resume policy metadata."""
    if recovery_checkpoint is None:
        return None
    resume_policy = recovery_checkpoint.get("resume_policy")
    if not isinstance(resume_policy, dict):
        return None

    event = {
        "event_type": "resume_policy",
        "provider": provider_name,
        "subtask_id": subtask_id,
        "status": str(resume_policy.get("status") or "unknown"),
        "strategy": str(resume_policy.get("strategy") or "unknown"),
        "finish_blocked": bool(resume_policy.get("finish_blocked")),
        "can_resume": bool(resume_policy.get("can_resume")),
        "checkpoint_artifact": str(
            recovery_checkpoint.get("artifact_path")
            or resume_policy.get("checkpoint_path")
            or ""
        ),
        "required_resolution_action_kinds": normalize_string_list(
            resume_policy.get("required_resolution_action_kinds")
        ),
        "required_artifacts": normalize_string_list(
            resume_policy.get("required_artifacts")
        ),
        "unresolved_partial_failure_ids": normalize_string_list(
            resume_policy.get("unresolved_partial_failure_ids")
        ),
        "unresolved_transaction_group_ids": normalize_string_list(
            resume_policy.get("unresolved_transaction_group_ids")
        ),
    }
    open_batch_ids = normalize_string_list(
        resume_policy.get("open_transaction_batch_ids")
    )
    if open_batch_ids:
        event["open_transaction_batch_ids"] = open_batch_ids
    recovery_plan_artifact = recovery_checkpoint.get("recovery_plan_artifact")
    if isinstance(recovery_plan_artifact, str) and recovery_plan_artifact:
        event["recovery_plan_artifact"] = recovery_plan_artifact
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
    if data.get("batch_id"):
        event["batch_id"] = str(data["batch_id"])
    if data.get("batch_status"):
        event["batch_status"] = str(data["batch_status"])
    if data.get("batch_boundary_error"):
        event["batch_boundary_error"] = True
        event["batch_boundary_error_reason"] = str(
            data.get("batch_boundary_error_reason") or ""
        )
        event["blocked_transaction_group_ids"] = normalize_string_list(
            data.get("blocked_transaction_group_ids")
        )
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
    event = {
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
    if transaction.get("batch_id"):
        event["batch_id"] = str(transaction["batch_id"])
    if transaction.get("batch_status"):
        event["batch_status"] = str(transaction["batch_status"])
    if transaction.get("batch_actions"):
        event["batch_actions"] = list(transaction["batch_actions"])
    if transaction.get("batch_boundary_error_count"):
        event["batch_boundary_error_count"] = int(
            transaction["batch_boundary_error_count"]
        )
        event["batch_boundary_error_reasons"] = normalize_string_list(
            transaction.get("batch_boundary_error_reasons")
        )
    return event


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
        "batch_ids": list(group.get("batch_ids") or []),
        "mutation_snapshot_ids": list(group.get("mutation_snapshot_ids") or []),
    }
    if isinstance(group.get("recovery_outcome"), dict):
        event["recovery_outcome"] = group["recovery_outcome"]
    if isinstance(group.get("recovery_policy"), dict):
        recovery_policy = group["recovery_policy"]
        event["recovery_policy"] = recovery_policy
        event["preferred_strategy"] = str(
            recovery_policy.get("preferred_strategy") or ""
        )
        event["required_next_action_kinds"] = normalize_string_list(
            recovery_policy.get("required_next_action_kinds")
        )
        event["resolution_strategies"] = normalize_string_list(
            recovery_policy.get("resolution_strategies")
        )
    next_actions = group.get("next_actions")
    if isinstance(next_actions, list):
        event["next_action_count"] = len(next_actions)
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
    unresolved_partial_failure_ids: list[str] = []
    for partial_index in partial_failure_indexes:
        partial_failure = transactions[partial_index]
        next_partial_index = next(
            (index for index in partial_failure_indexes if index > partial_index),
            len(transactions),
        )
        resolved = False
        for index, transaction in enumerate(
            transactions[partial_index + 1 : next_partial_index],
            start=partial_index + 1,
        ):
            if transaction_resolves_partial_failure(
                transaction=transaction,
                partial_failure=partial_failure,
            ):
                recovery_transaction_ids.append(str(transaction.get("id") or index))
                resolved = True
                break
        if not resolved:
            unresolved_partial_failure_ids.append(
                str(partial_failure.get("id") or partial_index)
            )
    recovery_resolved = not unresolved_partial_failure_ids
    partial_failure_count = status_counts.get("partial_failure", 0)
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
    transaction_batch_summary = summarize_generic_edit_transaction_batches(transactions)
    return {
        "transactions": transactions,
        "transaction_count": len(transactions),
        "transaction_status_counts": status_counts,
        **transaction_batch_summary,
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


def summarize_generic_edit_transaction_batches(
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return batch summaries stitched from transaction metadata."""
    batches: dict[str, dict[str, Any]] = {}
    for transaction in transactions:
        transaction_id = str(transaction.get("id") or "")
        for batch_id in normalize_string_list(transaction.get("batch_ids")):
            batch = batches.setdefault(
                batch_id,
                {
                    "id": batch_id,
                    "status": "open",
                    "transaction_ids": [],
                    "mutation_snapshot_ids": [],
                    "restored_paths": [],
                    "deleted_paths": [],
                    "batch_actions": [],
                    "staged_mutation_ids": [],
                    "staged_mutated_paths": [],
                    "staged_restored_paths": [],
                    "staged_deleted_paths": [],
                    "boundary_errors": [],
                    "boundary_error_reasons": [],
                },
            )
            if transaction_id and transaction_id not in batch["transaction_ids"]:
                batch["transaction_ids"].append(transaction_id)
            for field_name in (
                "mutation_snapshot_ids",
                "restored_paths",
                "deleted_paths",
                "batch_actions",
            ):
                for value in normalize_string_list(transaction.get(field_name)):
                    if value not in batch[field_name]:
                        batch[field_name].append(value)
            for source_field, staged_field in (
                ("mutation_snapshot_ids", "staged_mutation_ids"),
                ("mutated_paths", "staged_mutated_paths"),
                ("restored_paths", "staged_restored_paths"),
                ("deleted_paths", "staged_deleted_paths"),
            ):
                for value in normalize_string_list(transaction.get(source_field)):
                    if value not in batch[staged_field]:
                        batch[staged_field].append(value)
            for error in transaction.get("batch_boundary_errors") or []:
                if not isinstance(error, dict):
                    continue
                compact_error = {
                    "tool": str(error.get("tool") or ""),
                    "batch_id": str(error.get("batch_id") or batch_id),
                    "reason": str(error.get("reason") or ""),
                    "blocked_transaction_group_ids": normalize_string_list(
                        error.get("blocked_transaction_group_ids")
                    ),
                }
                if compact_error not in batch["boundary_errors"]:
                    batch["boundary_errors"].append(compact_error)
                reason = compact_error["reason"]
                if reason and reason not in batch["boundary_error_reasons"]:
                    batch["boundary_error_reasons"].append(reason)
            if transaction.get("batch_status"):
                batch["status"] = str(transaction["batch_status"])

    ordered_batches = list(batches.values())
    batch_status_counts: dict[str, int] = {}
    for batch in ordered_batches:
        status = str(batch.get("status") or "open")
        batch_status_counts[status] = batch_status_counts.get(status, 0) + 1
        batch["staged_mutation_count"] = len(
            normalize_string_list(batch.get("staged_mutation_ids"))
        )
        staged_paths = {
            path
            for field_name in (
                "staged_mutated_paths",
                "staged_restored_paths",
                "staged_deleted_paths",
            )
            for path in normalize_string_list(batch.get(field_name))
        }
        batch["staged_path_count"] = len(staged_paths)
        batch["boundary_error_count"] = len(batch["boundary_errors"])
    open_batch_ids = [
        str(batch["id"])
        for batch in ordered_batches
        if str(batch.get("status") or "open") not in {"committed", "aborted"}
    ]
    return {
        "transaction_batch_count": len(ordered_batches),
        "transaction_batch_ids": [batch["id"] for batch in ordered_batches],
        "transaction_batches": ordered_batches,
        "transaction_batch_status_counts": batch_status_counts,
        "open_transaction_batch_count": len(open_batch_ids),
        "open_transaction_batch_ids": open_batch_ids,
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
            "batch_ids": transaction_group_field_values(
                group_transactions,
                "batch_ids",
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


def link_generic_edit_transaction_batches_to_groups(
    *,
    transaction_summary: dict[str, Any],
    transaction_group_summary: dict[str, Any],
) -> dict[str, Any]:
    """Attach recovery group and outcome links to transaction batch summaries."""
    batches = [
        dict(batch)
        for batch in transaction_summary.get("transaction_batches") or []
        if isinstance(batch, dict)
    ]
    if not batches:
        return transaction_summary

    batches_by_id = {str(batch.get("id") or ""): batch for batch in batches}
    for group in transaction_group_summary.get("transaction_groups") or []:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("id") or "")
        if not group_id:
            continue
        for batch_id in normalize_string_list(group.get("batch_ids")):
            batch = batches_by_id.get(batch_id)
            if batch is None:
                continue
            append_unique_string(batch, "transaction_group_ids", group_id)
            if str(group.get("status") or "") == "unresolved":
                append_unique_string(
                    batch,
                    "unresolved_transaction_group_ids",
                    group_id,
                )
                link_generic_edit_unresolved_group_policy_to_batch(
                    batch=batch,
                    group=group,
                )
            recovery_outcome = group.get("recovery_outcome")
            if isinstance(recovery_outcome, dict):
                outcomes = batch.setdefault("recovery_outcomes", [])
                if all(
                    outcome.get("transaction_group_id") != group_id
                    for outcome in outcomes
                    if isinstance(outcome, dict)
                ):
                    outcomes.append(recovery_outcome)

    for batch in batches:
        transaction_group_ids = normalize_string_list(
            batch.get("transaction_group_ids")
        )
        unresolved_group_ids = normalize_string_list(
            batch.get("unresolved_transaction_group_ids")
        )
        recovery_outcomes = [
            outcome
            for outcome in batch.get("recovery_outcomes") or []
            if isinstance(outcome, dict)
        ]
        if transaction_group_ids:
            batch["transaction_group_count"] = len(transaction_group_ids)
        if unresolved_group_ids:
            batch["unresolved_transaction_group_count"] = len(unresolved_group_ids)
        if recovery_outcomes:
            batch["recovery_outcome_count"] = len(recovery_outcomes)
        batch["recovery_status"] = generic_edit_transaction_batch_recovery_status(
            batch,
        )
        batch["finish_blocked"] = batch["recovery_status"] in {
            "requires_resolution",
            "open",
        }

    return {
        **transaction_summary,
        "transaction_batches": batches,
    }


def link_generic_edit_unresolved_group_policy_to_batch(
    *,
    batch: dict[str, Any],
    group: dict[str, Any],
) -> None:
    """Attach unresolved group policy hints to a batch summary."""
    policy = group.get("recovery_policy")
    if not isinstance(policy, dict):
        return
    for kind in policy.get("required_next_action_kinds") or []:
        append_unique_string(batch, "required_next_action_kinds", str(kind))
    for strategy in policy.get("resolution_strategies") or []:
        append_unique_string(batch, "resolution_strategies", str(strategy))


def generic_edit_transaction_batch_recovery_status(batch: dict[str, Any]) -> str:
    """Return the batch-level recovery status for control-plane consumers."""
    if normalize_string_list(batch.get("unresolved_transaction_group_ids")):
        return "requires_resolution"
    if str(batch.get("status") or "open") not in {"committed", "aborted"}:
        return "open"
    if batch.get("recovery_outcome_count"):
        return "resolved"
    return "clean"


def build_generic_edit_transaction_batch_policies(
    transaction_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return per-batch recovery policy summaries."""
    policies: list[dict[str, Any]] = []
    for batch in transaction_summary.get("transaction_batches") or []:
        if not isinstance(batch, dict):
            continue
        batch_id = str(batch.get("id") or "")
        if not batch_id:
            continue
        recovery_status = generic_edit_transaction_batch_recovery_status(batch)
        policy: dict[str, Any] = {
            "batch_id": batch_id,
            "status": recovery_status,
            "finish_blocked": recovery_status in {"requires_resolution", "open"},
        }
        unresolved_group_ids = normalize_string_list(
            batch.get("unresolved_transaction_group_ids")
        )
        if unresolved_group_ids:
            policy["unresolved_transaction_group_ids"] = unresolved_group_ids
        required_kinds = normalize_string_list(batch.get("required_next_action_kinds"))
        if required_kinds:
            policy["required_next_action_kinds"] = required_kinds
        strategies = normalize_string_list(batch.get("resolution_strategies"))
        if strategies:
            policy["resolution_strategies"] = strategies
        policies.append(policy)
    return policies


def append_unique_string(target: dict[str, Any], field_name: str, value: str) -> None:
    """Append a string to a list field if it is not already present."""
    values = normalize_string_list(target.get(field_name))
    if value not in values:
        values.append(value)
    target[field_name] = values


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


def has_open_transaction_batch(trace: list[dict[str, Any]]) -> bool:
    """Return true when finish would leave a transaction batch uncommitted."""
    return (
        summarize_generic_edit_transactions(trace)["open_transaction_batch_count"] > 0
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
    non_targeted_recovery_tools = WORKSPACE_RECOVERY_TOOLS - {ROLLBACK_TRANSACTION_TOOL}
    if tool_sequence & non_targeted_recovery_tools:
        return True

    if ROLLBACK_TRANSACTION_TOOL in tool_sequence:
        partial_transaction_id = str(partial_failure.get("id") or "")
        rollback_transaction_ids = normalize_string_list(
            transaction.get("rollback_transaction_ids")
        )
        if partial_transaction_id and rollback_transaction_ids:
            return partial_transaction_id in rollback_transaction_ids

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
