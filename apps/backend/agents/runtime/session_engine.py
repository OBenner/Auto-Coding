"""Shared runtime session execution."""

from pathlib import Path
from typing import Any

from .capabilities import (
    RuntimeCapabilityError,
    RuntimePolicy,
    RuntimeRequirements,
)
from .result import AgentRunResult


def _runtime_session_policy(runtime_session: Any) -> RuntimePolicy | None:
    """Return the runtime-policy declared on a session, if any."""
    policy = getattr(runtime_session, "runtime_policy", None)
    return policy if isinstance(policy, RuntimePolicy) else None


async def run_runtime_session(
    runtime_session: Any,
    message: str,
    spec_dir: Path,
    verbose: bool = False,
    phase: Any = None,
    requirements: RuntimeRequirements | None = None,
    subtask_id: str | None = None,
) -> AgentRunResult:
    """Run a session through a capability-checked runtime adapter."""

    requirements = requirements or RuntimeRequirements.full_coder()
    capabilities = runtime_session.capabilities
    policy = _runtime_session_policy(runtime_session)

    if not capabilities.supports(requirements, policy=policy):
        raise RuntimeCapabilityError(
            provider_name=runtime_session.provider_name,
            runtime_name=runtime_session.name,
            requirements=requirements,
            capabilities=capabilities,
            policy=policy,
        )

    return await runtime_session.run(
        message=message,
        spec_dir=spec_dir,
        verbose=verbose,
        phase=phase,
        subtask_id=subtask_id,
    )


async def resume_runtime_session(
    runtime_session: Any,
    checkpoint_path: Path | str,
    spec_dir: Path,
    verbose: bool = False,
    phase: Any = None,
    requirements: RuntimeRequirements | None = None,
    subtask_id: str | None = None,
) -> AgentRunResult:
    """Resume a runtime session from a persisted recovery checkpoint."""

    requirements = requirements or RuntimeRequirements.generic_edit()
    capabilities = runtime_session.capabilities
    policy = _runtime_session_policy(runtime_session)

    if not capabilities.supports(requirements, policy=policy):
        raise RuntimeCapabilityError(
            provider_name=runtime_session.provider_name,
            runtime_name=runtime_session.name,
            requirements=requirements,
            capabilities=capabilities,
            policy=policy,
        )

    resume = getattr(runtime_session, "resume", None)
    if not callable(resume):
        raise RuntimeError(
            f"Runtime {runtime_session.name} does not support checkpoint resume."
        )

    return await resume(
        checkpoint_path=Path(checkpoint_path),
        spec_dir=spec_dir,
        verbose=verbose,
        phase=phase,
        subtask_id=subtask_id,
    )
