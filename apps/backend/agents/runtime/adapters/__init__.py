"""Runtime adapter factory."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .claude import ClaudeAgentRuntimeSession
from .completion import CompletionRuntimeSession
from .generic_edit import GenericEditRuntimeSession
from .patch_proposal import PatchProposalRuntimeSession


def create_runtime_session(
    *,
    provider_name: str,
    agent_session: Any,
    claude_session_runner: Callable[..., Awaitable[tuple]] | None = None,
    runtime_mode: str = "full_autonomous",
    project_dir: Path | None = None,
) -> Any:
    """Create a runtime adapter for a provider session."""

    provider_name = provider_name.lower()
    runtime_mode = runtime_mode.lower().replace("-", "_")

    if runtime_mode == "patch_proposal":
        if project_dir is None:
            raise ValueError("project_dir is required for patch proposal runtime")
        return PatchProposalRuntimeSession(
            provider_name=provider_name,
            agent_session=agent_session,
            project_dir=project_dir,
        )

    if runtime_mode == "generic_edit":
        if project_dir is None:
            raise ValueError("project_dir is required for generic edit runtime")
        return GenericEditRuntimeSession(
            provider_name=provider_name,
            agent_session=agent_session,
            project_dir=project_dir,
        )

    if runtime_mode == "analysis_only":
        return CompletionRuntimeSession(
            provider_name=provider_name,
            agent_session=agent_session,
        )

    if provider_name == "claude":
        if claude_session_runner is None:
            raise ValueError("claude_session_runner is required for Claude runtime")
        return ClaudeAgentRuntimeSession(
            agent_session=agent_session,
            session_runner=claude_session_runner,
        )

    return CompletionRuntimeSession(
        provider_name=provider_name,
        agent_session=agent_session,
    )
