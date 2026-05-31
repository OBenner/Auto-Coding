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

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from agents.runtime import (
    get_runtime_mode,
    resolve_runtime_mode_with_fallback,
    save_runtime_fallback_artifact,
)
from agents.runtime.direct_api_autonomy import resolve_direct_api_autonomous_gate
from core.autonomy_policy import autonomy_policy_for
from core.providers.config import ProviderConfig
from debug import debug_error

# Opt-in: route a *promoted* direct-API provider's read-only qa_reviewer
# through the provider-neutral runtime layer instead of the Claude SDK.
# Default off, so the Claude QA path is unchanged unless an operator both
# sets this AND the provider passes the direct-API promotion gate.
QA_DIRECT_RUNTIME_ENV = "AUTO_CODE_QA_DIRECT_RUNTIME"
_TRUTHY = {"1", "true", "yes", "on"}

# Only the read-only reviewer is ported so far; qa_fixer mutates source and
# stays on the Claude SDK until its runtime path is proven.
PORTABLE_QA_AGENTS = frozenset({"qa_reviewer"})


class QaRuntimeUnsupportedError(RuntimeError):
    """Raised when a QA agent cannot run with the requested provider/runtime."""


@dataclass(frozen=True)
class QaRuntimeDecision:
    """How a QA phase should execute.

    ``use_runtime_layer`` is ``False`` for the default Claude Agent SDK
    path and ``True`` when a promoted direct-API provider may run the
    read-only reviewer through ``create_runtime_session`` /
    ``run_runtime_session``.
    """

    agent_type: str
    provider_name: str
    runtime_mode: str
    use_runtime_layer: bool


def _qa_direct_runtime_opt_in(env: Mapping[str, str]) -> bool:
    """Return whether the operator opted into the direct-API QA reviewer path."""
    return env.get(QA_DIRECT_RUNTIME_ENV, "").strip().lower() in _TRUTHY


def resolve_qa_runtime(
    *,
    agent_type: str,
    spec_dir: Path,
    qa_iteration: int,
    project_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> QaRuntimeDecision:
    """Resolve how a QA phase should execute, before its session starts.

    Always persists a ``runtime_fallback`` artifact and returns a
    :class:`QaRuntimeDecision`:

    * Claude + ``full_autonomous`` -> ``use_runtime_layer=False`` (the
      existing Claude SDK path).
    * A promoted direct-API provider running ``qa_reviewer`` with the
      ``AUTO_CODE_QA_DIRECT_RUNTIME`` opt-in -> ``use_runtime_layer=True``.

    Raises :class:`QaRuntimeUnsupportedError` for every other non-Claude /
    non-``full_autonomous`` request (qa_fixer, un-promoted providers, or
    providers without the opt-in), so the default safety contract holds.
    """
    env_map = os.environ if env is None else env
    provider_config = ProviderConfig.from_env(agent_type=agent_type)
    provider_name = provider_config.provider
    requested_runtime_mode = get_runtime_mode(agent_type)

    runtime_decision = resolve_runtime_mode_with_fallback(
        provider_name=provider_name,
        requested_mode=requested_runtime_mode,
        phase="coding",
    )
    selected_mode = runtime_decision.selected_mode

    artifact_path = save_runtime_fallback_artifact(
        spec_dir=spec_dir,
        decision=runtime_decision,
        phase=agent_type,
        session_num=qa_iteration,
    )

    # Default Claude SDK path — unchanged.
    if provider_name == "claude" and selected_mode == "full_autonomous":
        return QaRuntimeDecision(
            agent_type=agent_type,
            provider_name=provider_name,
            runtime_mode=selected_mode,
            use_runtime_layer=False,
        )

    # Opt-in direct-API path for the read-only reviewer, gated on the
    # provider having passed the direct-API promotion gate (evidence-backed
    # trust). qa_fixer mutates source and is intentionally excluded.
    if (
        agent_type in PORTABLE_QA_AGENTS
        and provider_name != "claude"
        and _qa_direct_runtime_opt_in(env_map)
    ):
        gate = resolve_direct_api_autonomous_gate(
            provider_name=provider_name,
            project_dir=project_dir or spec_dir,
            phase="coding",
            env=env_map,
        )
        if gate.allowed:
            return QaRuntimeDecision(
                agent_type=agent_type,
                provider_name=provider_name,
                runtime_mode="generic_edit",
                use_runtime_layer=True,
            )
        message = (
            f"QA phase '{agent_type}' opted into the direct-API runtime "
            f"({QA_DIRECT_RUNTIME_ENV}) for provider={provider_name}, but the "
            f"direct-API promotion gate is not satisfied (status={gate.status}, "
            f"reason={gate.reason}, missing={gate.missing_requirements}). "
            f"Runtime decision saved to {artifact_path}."
        )
        debug_error("qa_runtime_routing", message)
        raise QaRuntimeUnsupportedError(message)

    policy = autonomy_policy_for(provider_name)
    message = (
        f"QA phase '{agent_type}' cannot run with provider={provider_name} "
        f"runtime={selected_mode}. QA agents require the Claude Agent SDK "
        "full_autonomous surface (multi-turn tool loop, Electron MCP, "
        f"recovery hooks). Set AGENT_PROVIDER_{agent_type.upper()}=claude and "
        f"AGENT_RUNTIME_MODE_{agent_type.upper()}=full_autonomous to run this "
        "phase. Direct API providers are being enabled by Phase 1 of "
        "docs/roadmap/non-claude-provider-autonomy.md; the read-only "
        f"qa_reviewer can opt in via {QA_DIRECT_RUNTIME_ENV}=true once its "
        "provider passes the promotion gate "
        f"(autonomy policy snapshot: {policy.to_dict()}; "
        f"runtime decision saved to {artifact_path})."
    )
    debug_error("qa_runtime_routing", message)
    raise QaRuntimeUnsupportedError(message)
