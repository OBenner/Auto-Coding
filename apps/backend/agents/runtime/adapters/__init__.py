"""Runtime adapter factory."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from ..cli_profiles import CLI_RUNNER_PROFILES
from ..direct_api_autonomy import DIRECT_API_AUTONOMOUS_PROVIDERS
from .claude import ClaudeAgentRuntimeSession
from .codex_cli import CodexCliRuntimeSession
from .completion import CompletionRuntimeSession
from .direct_api_autonomous import DirectApiAutonomousRuntimeSession
from .generic_cli import GenericCliRuntimeSession
from .generic_edit import GenericEditRuntimeSession
from .patch_proposal import PatchProposalRuntimeSession

CLI_RUNTIME_PROVIDER_NAMES = {
    profile.runner_id
    for profile in CLI_RUNNER_PROFILES
    if profile.runner_id != "codex_cli"
}


def create_runtime_session(
    *,
    provider_name: str,
    agent_session: Any,
    claude_session_runner: Callable[..., Awaitable[tuple]] | None = None,
    runtime_mode: str = "full_autonomous",
    project_dir: Path | None = None,
    agent_type: str | None = None,
    subagent_session_factory: Callable[..., Awaitable[Any] | Any] | None = None,
    allow_direct_api_autonomous: bool = False,
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
            agent_type=agent_type,
            subagent_session_factory=subagent_session_factory,
        )

    if (
        runtime_mode == "full_autonomous"
        and allow_direct_api_autonomous
        and provider_name in DIRECT_API_AUTONOMOUS_PROVIDERS
    ):
        if project_dir is None:
            raise ValueError(
                "project_dir is required for direct API autonomous runtime"
            )
        return DirectApiAutonomousRuntimeSession(
            provider_name=provider_name,
            agent_session=agent_session,
            project_dir=project_dir,
            agent_type=agent_type,
            subagent_session_factory=subagent_session_factory,
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

    if provider_name == "codex":
        if project_dir is None:
            raise ValueError("project_dir is required for Codex CLI runtime")
        return CodexCliRuntimeSession(
            agent_session=agent_session,
            project_dir=project_dir,
        )

    if provider_name in CLI_RUNTIME_PROVIDER_NAMES:
        if project_dir is None:
            raise ValueError("project_dir is required for generic CLI runtime")
        return GenericCliRuntimeSession(
            runner_id=provider_name,
            agent_session=agent_session,
            project_dir=project_dir,
        )

    return CompletionRuntimeSession(
        provider_name=provider_name,
        agent_session=agent_session,
    )
