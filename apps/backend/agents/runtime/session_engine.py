"""Shared runtime session execution."""

from pathlib import Path
from typing import Any

from .capabilities import RuntimeCapabilityError, RuntimeRequirements
from .result import AgentRunResult


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

    if not capabilities.supports(requirements):
        raise RuntimeCapabilityError(
            provider_name=runtime_session.provider_name,
            runtime_name=runtime_session.name,
            requirements=requirements,
            capabilities=capabilities,
        )

    return await runtime_session.run(
        message=message,
        spec_dir=spec_dir,
        verbose=verbose,
        phase=phase,
        subtask_id=subtask_id,
    )
