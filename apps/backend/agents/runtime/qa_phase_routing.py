"""Runtime-modes routing for QA agent phases.

QA agents (``qa_reviewer``, ``qa_fixer``) are kept on the Claude Agent
SDK execution path while the runtime layer learns to provide MCP
execution, mutating subagents, and a Claude-equivalent native tool loop
for direct API providers (see Phase 1 of
``docs/roadmap/non-claude-provider-autonomy.md``).

This module resolves the provider, runtime mode, and AutonomyPolicy for
a QA phase *before* the session starts so that
``AGENT_PROVIDER_<TYPE>`` and ``AGENT_RUNTIME_MODE_<TYPE>`` env
overrides actually reach a decision. A non-Claude provider or a
non-``full_autonomous`` runtime fails fast with a clear capability error
and a persisted ``runtime_fallback_<phase>_*.json`` diagnostic artifact.
"""

from __future__ import annotations

from pathlib import Path

from agents.runtime import (
    get_runtime_mode,
    resolve_runtime_mode_with_fallback,
    save_runtime_fallback_artifact,
)
from core.autonomy_policy import autonomy_policy_for
from core.providers.config import ProviderConfig
from debug import debug_error


class QaRuntimeUnsupportedError(RuntimeError):
    """Raised when a QA agent cannot run with the requested provider/runtime."""


def resolve_qa_runtime(
    *,
    agent_type: str,
    spec_dir: Path,
    qa_iteration: int,
) -> None:
    """Apply runtime-modes policy to a QA agent before its session starts.

    Always persists a ``runtime_fallback`` artifact, raises
    :class:`QaRuntimeUnsupportedError` for non-Claude or non-full-autonomous
    requests, and otherwise returns silently so the caller proceeds with the
    existing Claude SDK path.
    """
    provider_config = ProviderConfig.from_env(agent_type=agent_type)
    provider_name = provider_config.provider
    requested_runtime_mode = get_runtime_mode(agent_type)

    runtime_decision = resolve_runtime_mode_with_fallback(
        provider_name=provider_name,
        requested_mode=requested_runtime_mode,
        phase="coding",
    )

    artifact_path = save_runtime_fallback_artifact(
        spec_dir=spec_dir,
        decision=runtime_decision,
        phase=agent_type,
        session_num=qa_iteration,
    )

    requires_claude_runtime = (
        provider_name != "claude" or runtime_decision.selected_mode != "full_autonomous"
    )
    if not requires_claude_runtime:
        return

    policy = autonomy_policy_for(provider_name)
    message = (
        f"QA phase '{agent_type}' cannot run with provider={provider_name} "
        f"runtime={runtime_decision.selected_mode}. QA agents currently "
        "require the Claude Agent SDK full_autonomous surface (multi-turn "
        "tool loop, Electron MCP, recovery hooks). Set "
        f"AGENT_PROVIDER_{agent_type.upper()}=claude and "
        f"AGENT_RUNTIME_MODE_{agent_type.upper()}=full_autonomous to run "
        "this phase. Direct API providers will be enabled by Phase 1 of "
        "docs/roadmap/non-claude-provider-autonomy.md "
        f"(autonomy policy snapshot: {policy.to_dict()}; "
        f"runtime decision saved to {artifact_path})."
    )
    debug_error("qa_runtime_routing", message)
    raise QaRuntimeUnsupportedError(message)
