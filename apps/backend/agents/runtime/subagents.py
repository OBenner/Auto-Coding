"""Provider-neutral subagent orchestration primitives."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from .capabilities import RuntimeCapabilities, RuntimePolicy, RuntimeRequirements
from .result import AgentRunResult
from .session_engine import run_runtime_session

RuntimeSessionFactory = Callable[["RuntimeSubagentTask"], Awaitable[Any] | Any]
SubagentSupportStrategy = Literal["native", "orchestrated", "unavailable"]
DEFAULT_SUBAGENT_TIMEOUT_SECONDS = 180.0
DEFAULT_SUBAGENT_MAX_ATTEMPTS = 1
MAX_SUBAGENT_ATTEMPTS = 3
DEFAULT_SUBAGENT_MERGE_POLICY = "read_only"
# Phase 1.2: a mutating child confined to its declared write scope. The
# parent applies child changes through transactional staged batches, so the
# policy name describes HOW the result merges, not just that it mutates.
TRANSACTIONAL_WRITE_SUBAGENT_MERGE_POLICY = "transactional_write"
SUPPORTED_SUBAGENT_MERGE_POLICIES = frozenset(
    {
        DEFAULT_SUBAGENT_MERGE_POLICY,
        TRANSACTIONAL_WRITE_SUBAGENT_MERGE_POLICY,
    }
)


def is_mutating_subagent_task(task: RuntimeSubagentTask) -> bool:
    """Return whether a child task may mutate the workspace."""
    return (
        task.merge_policy or DEFAULT_SUBAGENT_MERGE_POLICY
    ) != DEFAULT_SUBAGENT_MERGE_POLICY


@dataclass(frozen=True)
class RuntimeSubagentSupport:
    """Effective subagent support for one runtime surface."""

    provider_name: str
    runtime_name: str
    strategy: SubagentSupportStrategy
    available: bool
    reason: str
    required_capabilities: tuple[str, ...] = ()
    missing_capabilities: tuple[str, ...] = ()
    available_capabilities: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize support metadata for UI, CLI, and artifacts."""
        return {
            "provider": self.provider_name,
            "runtime": self.runtime_name,
            "strategy": self.strategy,
            "available": self.available,
            "reason": self.reason,
            "required_capabilities": list(self.required_capabilities),
            "missing_capabilities": list(self.missing_capabilities),
            "available_capabilities": list(self.available_capabilities),
        }


@dataclass(frozen=True)
class RuntimeSubagentTask:
    """One delegated runtime task."""

    id: str
    prompt: str
    role: str = "worker"
    requirements: RuntimeRequirements = field(
        default_factory=RuntimeRequirements.text_only
    )
    subtask_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    merge_policy: str = DEFAULT_SUBAGENT_MERGE_POLICY
    write_scope: tuple[str, ...] = ()
    max_attempts: int = DEFAULT_SUBAGENT_MAX_ATTEMPTS


@dataclass(frozen=True)
class RuntimeSubagentAttempt:
    """One execution attempt for a child runtime task."""

    attempt: int
    child_context_id: str
    status: str
    started_at: str
    finished_at: str
    duration_ms: int
    error: str | None = None


@dataclass
class RuntimeSubagentResult:
    """Result from one delegated runtime task."""

    id: str
    role: str
    status: str
    response_text: str
    usage_metadata: dict[str, Any] | None = None
    artifacts: dict[str, str] | None = None
    error: str | None = None
    attempt: int = 1
    attempt_count: int = 1
    max_attempts: int = DEFAULT_SUBAGENT_MAX_ATTEMPTS
    attempts: list[RuntimeSubagentAttempt] = field(default_factory=list)
    child_context_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    merge_policy: str = DEFAULT_SUBAGENT_MERGE_POLICY
    write_scope: tuple[str, ...] = ()
    artifact_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize result for artifact output."""
        return asdict(self)


@dataclass
class RuntimeSubagentRun:
    """Summary from a subagent orchestration run."""

    status: str
    results: list[RuntimeSubagentResult]
    artifact_path: str | None = None
    cancelled: bool = False
    cancelled_at: str | None = None
    support: RuntimeSubagentSupport | None = None
    merge_plan: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize run for artifact output."""
        return {
            "status": self.status,
            "cancelled": self.cancelled,
            "cancelled_at": self.cancelled_at,
            "artifact_path": self.artifact_path,
            "support": self.support.to_dict() if self.support else None,
            "summary": summarize_subagent_results(self.results),
            "merge_plan": self.merge_plan or build_subagent_merge_plan(self.results),
            "results": [result.to_dict() for result in self.results],
        }


class RuntimeSubagentOrchestrator:
    """Run child runtime sessions without relying on Claude SDK Task tools."""

    def __init__(
        self,
        *,
        session_factory: RuntimeSessionFactory,
        spec_dir: Path,
        max_concurrency: int = 2,
        max_task_seconds: float = DEFAULT_SUBAGENT_TIMEOUT_SECONDS,
    ):
        self.session_factory = session_factory
        self.spec_dir = spec_dir
        self.max_concurrency = max(1, max_concurrency)
        self.max_task_seconds = (
            max_task_seconds
            if max_task_seconds > 0
            else DEFAULT_SUBAGENT_TIMEOUT_SECONDS
        )
        self._cancel_event = asyncio.Event()
        self._running_tasks: set[asyncio.Task] = set()
        self._cancel_requested_at: str | None = None

    async def cancel(self) -> None:
        """Request cancellation and forward it to running child tasks."""
        self._cancel_requested_at = datetime.now(UTC).isoformat()
        self._cancel_event.set()
        for task in tuple(self._running_tasks):
            task.cancel()
        await asyncio.sleep(0)

    def support_for(
        self,
        *,
        provider_name: str,
        runtime_name: str,
        capabilities: RuntimeCapabilities,
        child_requirements: RuntimeRequirements | None = None,
        policy: RuntimePolicy | None = None,
    ) -> RuntimeSubagentSupport:
        """Return effective subagent support with this orchestrator configured."""
        return resolve_runtime_subagent_support(
            provider_name=provider_name,
            runtime_name=runtime_name,
            capabilities=capabilities,
            orchestrator_available=True,
            child_requirements=child_requirements,
            policy=policy,
        )

    async def run(
        self,
        tasks: list[RuntimeSubagentTask],
        *,
        verbose: bool = False,
        phase: Any = None,
        artifact_name: str = "runtime_subagents.json",
        support: RuntimeSubagentSupport | None = None,
    ) -> RuntimeSubagentRun:
        """Run delegated tasks with bounded parallelism and persist results."""
        if not tasks:
            return self._save_run(
                RuntimeSubagentRun(
                    status="complete",
                    results=[],
                    support=support,
                ),
                artifact_name=artifact_name,
            )

        semaphore = asyncio.Semaphore(self.max_concurrency)
        running = [
            (
                task,
                asyncio.create_task(
                    self._run_one(
                        task,
                        semaphore=semaphore,
                        verbose=verbose,
                        phase=phase,
                    )
                ),
            )
            for task in tasks
        ]
        asyncio_tasks = [asyncio_task for _, asyncio_task in running]
        self._running_tasks.update(asyncio_tasks)
        try:
            raw_results = await asyncio.gather(
                *asyncio_tasks,
                return_exceptions=True,
            )
        finally:
            self._running_tasks.difference_update(asyncio_tasks)

        results = [
            normalize_subagent_result(task, raw_result)
            for (task, _), raw_result in zip(running, raw_results, strict=True)
        ]

        run_status = summarize_subagent_status(results)
        run = RuntimeSubagentRun(
            status=run_status,
            results=results,
            cancelled=any(result.status == "cancelled" for result in results),
            cancelled_at=self._cancel_requested_at
            if any(result.status == "cancelled" for result in results)
            else None,
            support=support,
        )
        return self._save_run(run, artifact_name=artifact_name)

    async def _run_one(
        self,
        task: RuntimeSubagentTask,
        *,
        semaphore: asyncio.Semaphore,
        verbose: bool,
        phase: Any,
    ) -> RuntimeSubagentResult:
        """Run one child task behind the orchestrator semaphore."""
        async with semaphore:
            if self._cancel_event.is_set():
                return cancelled_subagent_result(task, before_start=True)

            attempts: list[RuntimeSubagentAttempt] = []
            max_attempts = bounded_subagent_attempts(task.max_attempts)
            latest_result: RuntimeSubagentResult | None = None
            for attempt in range(1, max_attempts + 1):
                if self._cancel_event.is_set():
                    latest_result = cancelled_subagent_result(task, before_start=False)
                    break

                result, attempt_record = await self._run_attempt(
                    task,
                    attempt=attempt,
                    verbose=verbose,
                    phase=phase,
                )
                attempts.append(attempt_record)
                latest_result = attach_task_contract_to_result(
                    task,
                    result,
                    attempt=attempt,
                    attempts=attempts,
                )
                if not should_retry_subagent_result(
                    latest_result,
                    attempt=attempt,
                    max_attempts=max_attempts,
                ):
                    break

            if latest_result is None:
                latest_result = cancelled_subagent_result(task, before_start=True)
            return latest_result

    async def _run_attempt(
        self,
        task: RuntimeSubagentTask,
        *,
        attempt: int,
        verbose: bool,
        phase: Any,
    ) -> tuple[RuntimeSubagentResult, RuntimeSubagentAttempt]:
        """Run one child task attempt and record its attempt metadata."""
        started_at = datetime.now(UTC)
        started_monotonic = time.perf_counter()
        runtime_session: Any | None = None
        child_context_id = subagent_child_context_id(task, attempt=attempt)
        try:
            runtime_session = await maybe_await(self.session_factory(task))
            confinement_error = mutating_child_confinement_error(task, runtime_session)
            if confinement_error is not None:
                await cancel_runtime_session(runtime_session)
                result = error_subagent_result(task, confinement_error)
            else:
                agent_result = await self._run_child_session(
                    runtime_session,
                    task,
                    attempt=attempt,
                    child_context_id=child_context_id,
                    verbose=verbose,
                    phase=phase,
                )
                result = runtime_result_to_subagent_result(task, agent_result)
        except asyncio.CancelledError:
            if runtime_session is not None:
                await cancel_runtime_session(runtime_session)
            raise
        except TimeoutError:
            if runtime_session is not None:
                await cancel_runtime_session(runtime_session)
            result = timeout_subagent_result(task, self.max_task_seconds)
        except Exception as e:
            if runtime_session is not None:
                await cancel_runtime_session(runtime_session)
            result = error_subagent_result(task, str(e))

        finished_at = datetime.now(UTC)
        duration_ms = int((time.perf_counter() - started_monotonic) * 1000)
        attempt_record = RuntimeSubagentAttempt(
            attempt=attempt,
            child_context_id=child_context_id,
            status=result.status,
            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            error=result.error,
        )
        return result, attempt_record

    async def _run_child_session(
        self,
        runtime_session: Any,
        task: RuntimeSubagentTask,
        *,
        attempt: int,
        child_context_id: str,
        verbose: bool,
        phase: Any,
    ) -> AgentRunResult:
        """Run one child runtime session with the configured timeout."""
        return await asyncio.wait_for(
            run_runtime_session(
                runtime_session,
                build_subagent_prompt(
                    task,
                    attempt=attempt,
                    child_context_id=child_context_id,
                ),
                self.spec_dir,
                verbose=verbose,
                phase=phase,
                requirements=task.requirements,
                subtask_id=task.subtask_id or task.id,
            ),
            timeout=self.max_task_seconds,
        )

    def _save_run(
        self,
        run: RuntimeSubagentRun,
        *,
        artifact_name: str,
    ) -> RuntimeSubagentRun:
        """Persist an orchestration run and return it."""
        attach_child_result_artifacts(
            spec_dir=self.spec_dir,
            artifact_name=artifact_name,
            results=run.results,
        )
        run.merge_plan = build_subagent_merge_plan(run.results)
        run.artifact_path = save_subagent_artifact(
            spec_dir=self.spec_dir,
            artifact_name=artifact_name,
            run=run,
        )
        return run


def runtime_result_to_subagent_result(
    task: RuntimeSubagentTask,
    result: AgentRunResult,
) -> RuntimeSubagentResult:
    """Convert a child runtime result into the subagent result surface."""
    return RuntimeSubagentResult(
        id=task.id,
        role=task.role,
        status=result.status,
        response_text=result.response_text,
        usage_metadata=result.usage_metadata,
        artifacts=result.artifacts,
        max_attempts=bounded_subagent_attempts(task.max_attempts),
    )


def attach_task_contract_to_result(
    task: RuntimeSubagentTask,
    result: RuntimeSubagentResult,
    *,
    attempt: int,
    attempts: list[RuntimeSubagentAttempt],
) -> RuntimeSubagentResult:
    """Attach isolation, merge, and retry metadata to a child result."""
    result.attempt = attempt
    result.attempt_count = len(attempts)
    result.max_attempts = bounded_subagent_attempts(task.max_attempts)
    result.attempts = list(attempts)
    result.child_context_id = attempts[-1].child_context_id if attempts else None
    result.context = dict(task.context)
    result.merge_policy = task.merge_policy or DEFAULT_SUBAGENT_MERGE_POLICY
    result.write_scope = tuple(task.write_scope)
    return result


def should_retry_subagent_result(
    result: RuntimeSubagentResult,
    *,
    attempt: int,
    max_attempts: int,
) -> bool:
    """Return true when a child error should get another isolated attempt."""
    return result.status == "error" and attempt < max_attempts


def bounded_subagent_attempts(value: int) -> int:
    """Clamp child task attempts to the supported retry envelope."""
    if value < DEFAULT_SUBAGENT_MAX_ATTEMPTS:
        return DEFAULT_SUBAGENT_MAX_ATTEMPTS
    return min(value, MAX_SUBAGENT_ATTEMPTS)


def cancelled_subagent_result(
    task: RuntimeSubagentTask,
    *,
    before_start: bool = False,
) -> RuntimeSubagentResult:
    """Return the standard cancelled child-session result."""
    message = (
        "Subagent task was cancelled before start."
        if before_start
        else "Subagent task was cancelled."
    )
    return RuntimeSubagentResult(
        id=task.id,
        role=task.role,
        status="cancelled",
        response_text=message,
        max_attempts=bounded_subagent_attempts(task.max_attempts),
        context=dict(task.context),
        merge_policy=task.merge_policy or DEFAULT_SUBAGENT_MERGE_POLICY,
        write_scope=tuple(task.write_scope),
    )


def timeout_subagent_result(
    task: RuntimeSubagentTask,
    timeout_seconds: float,
) -> RuntimeSubagentResult:
    """Return a timeout result for one child session."""
    return RuntimeSubagentResult(
        id=task.id,
        role=task.role,
        status="error",
        response_text="",
        error=f"Subagent task timed out after {timeout_seconds:g} seconds.",
        max_attempts=bounded_subagent_attempts(task.max_attempts),
        context=dict(task.context),
        merge_policy=task.merge_policy or DEFAULT_SUBAGENT_MERGE_POLICY,
        write_scope=tuple(task.write_scope),
    )


def error_subagent_result(
    task: RuntimeSubagentTask,
    error: str,
) -> RuntimeSubagentResult:
    """Return a child-session error result."""
    return RuntimeSubagentResult(
        id=task.id,
        role=task.role,
        status="error",
        response_text="",
        error=error,
        max_attempts=bounded_subagent_attempts(task.max_attempts),
        context=dict(task.context),
        merge_policy=task.merge_policy or DEFAULT_SUBAGENT_MERGE_POLICY,
        write_scope=tuple(task.write_scope),
    )


async def cancel_runtime_session(runtime_session: Any) -> None:
    """Forward cancellation to a runtime session when supported."""
    cancel_hook = getattr(runtime_session, "cancel", None)
    if callable(cancel_hook):
        await maybe_await(cancel_hook())


def mutating_child_confinement_error(
    task: RuntimeSubagentTask,
    runtime_session: Any,
) -> str | None:
    """Return why a mutating child session is not safely confined, if it isn't.

    A mutating child may only run on a session that carries a
    ``write_scope_guard`` covering no more than the task's declared write
    scope. This makes the write-scope contract enforced by construction:
    a session factory that does not confine the child cannot run it.
    Read-only children are unaffected.
    """
    if not is_mutating_subagent_task(task):
        return None
    guard = getattr(runtime_session, "write_scope_guard", None)
    if guard is None:
        return (
            f"Mutating subagent task '{task.id}' "
            f"(merge_policy={task.merge_policy}) requires a child session "
            "confined by write_scope_guard, but the session factory returned "
            "an unconfined session."
        )
    guard_paths = {str(path) for path in guard}
    declared_paths = set(task.write_scope)
    extra_paths = sorted(guard_paths - declared_paths)
    if extra_paths:
        return (
            f"Mutating subagent task '{task.id}' child session allows paths "
            f"outside the declared write scope: {', '.join(extra_paths)}."
        )
    return None


def resolve_runtime_subagent_support(
    *,
    provider_name: str,
    runtime_name: str,
    capabilities: RuntimeCapabilities,
    orchestrator_available: bool = False,
    child_requirements: RuntimeRequirements | None = None,
    policy: RuntimePolicy | None = None,
) -> RuntimeSubagentSupport:
    """Return native or orchestrated subagent support without over-promising.

    ``policy`` may grant additional capabilities (for example ``subagents``
    via ``RuntimePolicy.mutating_subagents_enabled``), which is how mutating
    child requirements stay behind the autonomy policy.
    """
    provider = provider_name.lower()
    requirements = child_requirements or RuntimeRequirements.text_only(mode="subagent")
    required_capabilities = requirements.required
    available_capabilities = tuple(capabilities.available())

    if capabilities.subagents:
        return RuntimeSubagentSupport(
            provider_name=provider,
            runtime_name=runtime_name,
            strategy="native",
            available=True,
            reason=(f"{provider}/{runtime_name} exposes native runtime subagents."),
            required_capabilities=required_capabilities,
            available_capabilities=available_capabilities,
        )

    missing_capabilities = tuple(capabilities.missing(requirements, policy=policy))
    if not orchestrator_available:
        return RuntimeSubagentSupport(
            provider_name=provider,
            runtime_name=runtime_name,
            strategy="unavailable",
            available=False,
            reason=(
                "Subagent support requires native runtime subagents or an "
                "explicit RuntimeSubagentOrchestrator."
            ),
            required_capabilities=required_capabilities,
            missing_capabilities=missing_capabilities,
            available_capabilities=available_capabilities,
        )

    if missing_capabilities:
        return RuntimeSubagentSupport(
            provider_name=provider,
            runtime_name=runtime_name,
            strategy="unavailable",
            available=False,
            reason=(
                f"RuntimeSubagentOrchestrator cannot run {requirements.mode} "
                "child sessions with the selected runtime capabilities."
            ),
            required_capabilities=required_capabilities,
            missing_capabilities=missing_capabilities,
            available_capabilities=available_capabilities,
        )

    return RuntimeSubagentSupport(
        provider_name=provider,
        runtime_name=runtime_name,
        strategy="orchestrated",
        available=True,
        reason=(
            "RuntimeSubagentOrchestrator can run isolated child sessions; this "
            "is not Claude SDK Task tool parity."
        ),
        required_capabilities=required_capabilities,
        available_capabilities=available_capabilities,
    )


def build_subagent_prompt(
    task: RuntimeSubagentTask,
    *,
    attempt: int = 1,
    child_context_id: str | None = None,
) -> str:
    """Build an isolated prompt envelope for one delegated runtime task."""
    context_id = child_context_id or subagent_child_context_id(task, attempt=attempt)
    metadata = json.dumps(task.metadata, ensure_ascii=False, indent=2)
    context = json.dumps(task.context, ensure_ascii=False, indent=2)
    write_scope = (
        "\n".join(f"- {path}" for path in task.write_scope)
        if task.write_scope
        else "- none"
    )
    return (
        f"You are running as Auto Code subagent `{task.id}` "
        f"with role `{task.role}`.\n"
        f"Child context id: {context_id}.\n"
        f"Attempt: {attempt} of {bounded_subagent_attempts(task.max_attempts)}.\n\n"
        "Isolation contract:\n"
        "- Treat this as an isolated child context; do not assume sibling "
        "subagents share state with you.\n"
        "- Treat each retry as a fresh child context unless the prompt gives you "
        "explicit parent-provided context.\n"
        "- Return findings that the parent runtime can merge explicitly.\n"
        f"- Merge policy: {task.merge_policy or DEFAULT_SUBAGENT_MERGE_POLICY}.\n"
        f"- Write scope:\n{write_scope}\n"
        "- If the merge policy is read_only, do not modify files or run commands "
        "that mutate the workspace.\n"
        "- If the merge policy is transactional_write, modify files only inside "
        "your write scope; writes outside it and shell commands are blocked by "
        "the runtime, and the parent merges your changes transactionally.\n\n"
        "Work only on the delegated task below. Return a concise result with "
        "findings, changes, verification, and risks where relevant.\n\n"
        f"Context:\n{context}\n\n"
        f"Metadata:\n{metadata}\n\n"
        f"Task:\n{task.prompt}"
    )


def subagent_child_context_id(
    task: RuntimeSubagentTask,
    *,
    attempt: int,
) -> str:
    """Return a stable child-context id for one isolated task attempt."""
    return f"child-{safe_artifact_id(task.id)}-attempt-{attempt}"


def summarize_subagent_status(results: list[RuntimeSubagentResult]) -> str:
    """Return aggregate status for a subagent run."""
    if any(result.status == "error" for result in results):
        return "error"
    if any(result.status == "cancelled" for result in results):
        return "cancelled"
    if any(result.status == "continue" for result in results):
        return "continue"
    return "complete"


def summarize_subagent_results(results: list[RuntimeSubagentResult]) -> dict[str, Any]:
    """Return artifact-friendly counters and result ids for child sessions."""
    status_counts: dict[str, int] = {}
    complete_result_ids: list[str] = []
    continue_result_ids: list[str] = []
    error_result_ids: list[str] = []
    cancelled_result_ids: list[str] = []
    artifact_result_ids: list[str] = []
    retried_result_ids: list[str] = []
    max_attempts_exhausted_result_ids: list[str] = []

    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
        if result.status == "complete":
            complete_result_ids.append(result.id)
        elif result.status == "continue":
            continue_result_ids.append(result.id)
        elif result.status == "error":
            error_result_ids.append(result.id)
        elif result.status == "cancelled":
            cancelled_result_ids.append(result.id)
        if result.artifacts:
            artifact_result_ids.append(result.id)
        if result.attempt_count > 1:
            retried_result_ids.append(result.id)
        if result.status == "error" and result.attempt_count >= result.max_attempts:
            max_attempts_exhausted_result_ids.append(result.id)

    return {
        "result_count": len(results),
        "status_counts": status_counts,
        "complete_result_ids": complete_result_ids,
        "continue_result_ids": continue_result_ids,
        "error_result_ids": error_result_ids,
        "cancelled_result_ids": cancelled_result_ids,
        "artifact_result_ids": artifact_result_ids,
        "retried_result_ids": retried_result_ids,
        "max_attempts_exhausted_result_ids": max_attempts_exhausted_result_ids,
        "has_errors": bool(error_result_ids),
        "has_cancelled": bool(cancelled_result_ids),
        "has_retries": bool(retried_result_ids),
        "has_exhausted_retries": bool(max_attempts_exhausted_result_ids),
    }


def normalize_subagent_result(
    task: RuntimeSubagentTask,
    raw_result: RuntimeSubagentResult | BaseException,
) -> RuntimeSubagentResult:
    """Convert gathered child task outcomes into runtime subagent results."""
    if isinstance(raw_result, RuntimeSubagentResult):
        return raw_result
    if isinstance(raw_result, asyncio.CancelledError):
        return RuntimeSubagentResult(
            id=task.id,
            role=task.role,
            status="cancelled",
            response_text="Subagent task was cancelled.",
            max_attempts=bounded_subagent_attempts(task.max_attempts),
            context=dict(task.context),
            merge_policy=task.merge_policy or DEFAULT_SUBAGENT_MERGE_POLICY,
            write_scope=tuple(task.write_scope),
        )
    return RuntimeSubagentResult(
        id=task.id,
        role=task.role,
        status="error",
        response_text="",
        error=str(raw_result),
        max_attempts=bounded_subagent_attempts(task.max_attempts),
        context=dict(task.context),
        merge_policy=task.merge_policy or DEFAULT_SUBAGENT_MERGE_POLICY,
        write_scope=tuple(task.write_scope),
    )


def build_subagent_merge_plan(
    results: list[RuntimeSubagentResult],
) -> dict[str, Any]:
    """Describe how parent runtimes should merge child-session outputs."""
    read_only_result_ids: list[str] = []
    mutating_result_ids: list[str] = []
    write_scopes: dict[str, list[str]] = {}
    scope_owner: dict[str, str] = {}
    conflict_result_ids: list[str] = []

    for result in results:
        if result.merge_policy == DEFAULT_SUBAGENT_MERGE_POLICY:
            read_only_result_ids.append(result.id)
        else:
            mutating_result_ids.append(result.id)
        if result.write_scope:
            write_scopes[result.id] = list(result.write_scope)
        for scope in result.write_scope:
            previous_owner = scope_owner.get(scope)
            if previous_owner and previous_owner != result.id:
                conflict_result_ids.extend([previous_owner, result.id])
            scope_owner[scope] = result.id

    conflict_result_ids = list(dict.fromkeys(conflict_result_ids))
    return {
        "strategy": (
            "read_only" if not mutating_result_ids else "transactional_parent_merge"
        ),
        "requires_parent_merge": bool(mutating_result_ids),
        "read_only_result_ids": read_only_result_ids,
        "mutating_result_ids": mutating_result_ids,
        "write_scopes": write_scopes,
        "conflict_result_ids": conflict_result_ids,
        "has_conflicts": bool(conflict_result_ids),
    }


def attach_child_result_artifacts(
    *,
    spec_dir: Path,
    artifact_name: str,
    results: list[RuntimeSubagentResult],
) -> None:
    """Persist one artifact per child result and attach its path to the result."""
    for result in results:
        result.artifact_path = save_subagent_child_artifact(
            spec_dir=spec_dir,
            artifact_name=artifact_name,
            result=result,
        )


def save_subagent_child_artifact(
    *,
    spec_dir: Path,
    artifact_name: str,
    result: RuntimeSubagentResult,
) -> str:
    """Persist one child result artifact for UI/debug consumers."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    parent_stem = Path(artifact_name).stem
    child_id = safe_artifact_id(result.id)
    artifact_path = artifact_dir / f"{parent_stem}__{child_id}.json"
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "parent_artifact": artifact_name,
        "merge_contract": {
            "merge_policy": result.merge_policy,
            "write_scope": list(result.write_scope),
            "requires_parent_merge": result.merge_policy
            != DEFAULT_SUBAGENT_MERGE_POLICY,
        },
        "result": result.to_dict(),
    }
    artifact_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(artifact_path)


def safe_artifact_id(value: str) -> str:
    """Return a filesystem-safe artifact id."""
    safe = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_" for char in value
    )
    return safe or "subagent"


def save_subagent_artifact(
    *,
    spec_dir: Path,
    artifact_name: str,
    run: RuntimeSubagentRun,
) -> str:
    """Persist one subagent orchestration artifact."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / artifact_name
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        **run.to_dict(),
    }
    artifact_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(artifact_path)


async def maybe_await(value: Awaitable[Any] | Any) -> Any:
    """Await a value when needed."""
    if asyncio.isfuture(value) or hasattr(value, "__await__"):
        return await value
    return value
