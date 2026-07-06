"""Runtime adapter factory."""

import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from core.autonomy_level import ResolvedAutonomySettings, resolve_autonomy_settings

from ..cli_profiles import CLI_RUNNER_PROFILES
from ..direct_api_autonomy import DIRECT_API_AUTONOMOUS_PROVIDERS
from .claude import ClaudeAgentRuntimeSession
from .codex_cli import CodexCliRuntimeSession
from .completion import CompletionRuntimeSession
from .direct_api_autonomous import DirectApiAutonomousRuntimeSession
from .generic_cli import GenericCliRuntimeSession
from .generic_edit import GenericEditRuntimeSession
from .patch_proposal import PatchProposalRuntimeSession

logger = logging.getLogger(__name__)

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
    write_scope_guard: tuple[str, ...] | list[str] | None = None,
    changeset_export: bool = False,
    autonomy_settings: ResolvedAutonomySettings | None = None,
) -> Any:
    """Create a runtime adapter for a provider session.

    ``write_scope_guard`` confines a Generic Edit session (or its promoted
    direct-API variant) to a declared write scope; the runtime then blocks
    mutations outside that scope. ``changeset_export`` additionally makes the
    session stage its mutations and export them as a changeset at finish
    instead of committing them to the shared workspace. Together they build
    mutating subagent child sessions whose write contract is enforced, not
    advisory.

    ``autonomy_settings`` lets callers inject their already-resolved autonomy
    level; when omitted it is resolved from the environment, so the level is
    logged for every session regardless of the call path (P3·T3).
    """

    provider_name = provider_name.lower()
    runtime_mode = runtime_mode.lower().replace("-", "_")

    autonomy = (
        autonomy_settings
        if autonomy_settings is not None
        else resolve_autonomy_settings()
    )
    logger.info(
        "[runtime-factory] provider=%s mode=%s agent=%s autonomy=%s",
        provider_name,
        runtime_mode,
        agent_type or "-",
        autonomy.level.value,
    )

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
            write_scope_guard=write_scope_guard,
            changeset_export=changeset_export,
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
            write_scope_guard=write_scope_guard,
            changeset_export=changeset_export,
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
