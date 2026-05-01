"""Provider-neutral subagent orchestration primitives."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .capabilities import RuntimeRequirements
from .result import AgentRunResult
from .session_engine import run_runtime_session

RuntimeSessionFactory = Callable[["RuntimeSubagentTask"], Awaitable[Any] | Any]


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

    def to_dict(self) -> dict[str, Any]:
        """Serialize run for artifact output."""
        return {
            "status": self.status,
            "cancelled": self.cancelled,
            "artifact_path": self.artifact_path,
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
    ):
        self.session_factory = session_factory
        self.spec_dir = spec_dir
        self.max_concurrency = max(1, max_concurrency)
        self._cancel_event = asyncio.Event()
        self._running_tasks: set[asyncio.Task] = set()

    async def cancel(self) -> None:
        """Request cancellation and forward it to running child tasks."""
        self._cancel_event.set()
        for task in tuple(self._running_tasks):
            task.cancel()

    async def run(
        self,
        tasks: list[RuntimeSubagentTask],
        *,
        verbose: bool = False,
        phase: Any = None,
        artifact_name: str = "runtime_subagents.json",
    ) -> RuntimeSubagentRun:
        """Run delegated tasks with bounded parallelism and persist results."""
        if not tasks:
            run = RuntimeSubagentRun(status="complete", results=[])
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
                    result: AgentRunResult = await run_runtime_session(
                        runtime_session,
                        build_subagent_prompt(task),
                        self.spec_dir,
                        verbose=verbose,
                        phase=phase,
                        requirements=task.requirements,
                        subtask_id=task.subtask_id or task.id,
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
                    return RuntimeSubagentResult(
                        id=task.id,
                        role=task.role,
                        status="cancelled",
                        response_text="Subagent task was cancelled.",
                    )
                except Exception as e:
                    return RuntimeSubagentResult(
                        id=task.id,
                        role=task.role,
                        status="error",
                        response_text="",
                        error=str(e),
                    )

        running = [asyncio.create_task(run_one(task)) for task in tasks]
        self._running_tasks.update(running)
        try:
            results = await asyncio.gather(*running)
        finally:
            self._running_tasks.difference_update(running)

        run_status = summarize_subagent_status(results)
        run = RuntimeSubagentRun(
            status=run_status,
            results=results,
            cancelled=any(result.status == "cancelled" for result in results),
        )
        run.artifact_path = save_subagent_artifact(
            spec_dir=self.spec_dir,
            artifact_name=artifact_name,
            run=run,
        )
        return run


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
