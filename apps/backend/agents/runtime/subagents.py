"""Provider-neutral subagent orchestration primitives."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from .capabilities import RuntimeCapabilities, RuntimeRequirements
from .result import AgentRunResult
from .session_engine import run_runtime_session

RuntimeSessionFactory = Callable[["RuntimeSubagentTask"], Awaitable[Any] | Any]
SubagentSupportStrategy = Literal["native", "orchestrated", "unavailable"]
DEFAULT_SUBAGENT_TIMEOUT_SECONDS = 180.0


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
    support: RuntimeSubagentSupport | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize run for artifact output."""
        return {
            "status": self.status,
            "cancelled": self.cancelled,
            "artifact_path": self.artifact_path,
            "support": self.support.to_dict() if self.support else None,
            "summary": summarize_subagent_results(self.results),
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

    async def cancel(self) -> None:
        """Request cancellation and forward it to running child tasks."""
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
    ) -> RuntimeSubagentSupport:
        """Return effective subagent support with this orchestrator configured."""
        return resolve_runtime_subagent_support(
            provider_name=provider_name,
            runtime_name=runtime_name,
            capabilities=capabilities,
            orchestrator_available=True,
            child_requirements=child_requirements,
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
            run = RuntimeSubagentRun(
                status="complete",
                results=[],
                support=support,
            )
            run.artifact_path = save_subagent_artifact(
                spec_dir=self.spec_dir,
                artifact_name=artifact_name,
                run=run,
            )
            return run

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def run_one(task: RuntimeSubagentTask) -> RuntimeSubagentResult:
            async with semaphore:
                if self._cancel_event.is_set():
                    return RuntimeSubagentResult(
                        id=task.id,
                        role=task.role,
                        status="cancelled",
                        response_text="Subagent task was cancelled before start.",
                    )

                runtime_session = await maybe_await(self.session_factory(task))
                try:
                    result: AgentRunResult = await asyncio.wait_for(
                        run_runtime_session(
                            runtime_session,
                            build_subagent_prompt(task),
                            self.spec_dir,
                            verbose=verbose,
                            phase=phase,
                            requirements=task.requirements,
                            subtask_id=task.subtask_id or task.id,
                        ),
                        timeout=self.max_task_seconds,
                    )
                    return RuntimeSubagentResult(
                        id=task.id,
                        role=task.role,
                        status=result.status,
                        response_text=result.response_text,
                        usage_metadata=result.usage_metadata,
                        artifacts=result.artifacts,
                    )
                except asyncio.CancelledError:
                    cancel_hook = getattr(runtime_session, "cancel", None)
                    if callable(cancel_hook):
                        await maybe_await(cancel_hook())
                    raise
                except TimeoutError:
                    cancel_hook = getattr(runtime_session, "cancel", None)
                    if callable(cancel_hook):
                        await maybe_await(cancel_hook())
                    return RuntimeSubagentResult(
                        id=task.id,
                        role=task.role,
                        status="error",
                        response_text="",
                        error=(
                            "Subagent task timed out after "
                            f"{self.max_task_seconds:g} seconds."
                        ),
                    )
                except Exception as e:
                    return RuntimeSubagentResult(
                        id=task.id,
                        role=task.role,
                        status="error",
                        response_text="",
                        error=str(e),
                    )

        running = [(task, asyncio.create_task(run_one(task))) for task in tasks]
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
            support=support,
        )
        run.artifact_path = save_subagent_artifact(
            spec_dir=self.spec_dir,
            artifact_name=artifact_name,
            run=run,
        )
        return run


def resolve_runtime_subagent_support(
    *,
    provider_name: str,
    runtime_name: str,
    capabilities: RuntimeCapabilities,
    orchestrator_available: bool = False,
    child_requirements: RuntimeRequirements | None = None,
) -> RuntimeSubagentSupport:
    """Return native or orchestrated subagent support without over-promising."""
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

    missing_capabilities = tuple(capabilities.missing(requirements))
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


def build_subagent_prompt(task: RuntimeSubagentTask) -> str:
    """Build an isolated prompt envelope for one delegated runtime task."""
    metadata = json.dumps(task.metadata, ensure_ascii=False, indent=2)
    return (
        f"You are running as Auto Code subagent `{task.id}` "
        f"with role `{task.role}`.\n\n"
        "Work only on the delegated task below. Return a concise result with "
        "findings, changes, verification, and risks where relevant.\n\n"
        f"Metadata:\n{metadata}\n\n"
        f"Task:\n{task.prompt}"
    )


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

    return {
        "result_count": len(results),
        "status_counts": status_counts,
        "complete_result_ids": complete_result_ids,
        "continue_result_ids": continue_result_ids,
        "error_result_ids": error_result_ids,
        "cancelled_result_ids": cancelled_result_ids,
        "artifact_result_ids": artifact_result_ids,
        "has_errors": bool(error_result_ids),
        "has_cancelled": bool(cancelled_result_ids),
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
        )
    return RuntimeSubagentResult(
        id=task.id,
        role=task.role,
        status="error",
        response_text="",
        error=str(raw_result),
    )


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
