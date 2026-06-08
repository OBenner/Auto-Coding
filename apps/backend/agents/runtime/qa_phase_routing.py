"""Runtime-modes routing for QA agent phases.

QA agents (``qa_reviewer``, ``qa_fixer``) run on the Claude Agent SDK by
default, but a direct-API provider that passes the promotion gate
(``AUTO_CODE_AUTONOMY=safe``/``bold`` + recorded evidence) runs them
through the provider-neutral runtime layer instead — there is no separate
QA opt-in. The reviewer is read-only; the fixer mutates source but the
runtime layer confines it (generic_edit snapshots + transaction rollback
+ sandbox) and matches the Claude recovery / model-fallback loop (see
``docs/roadmap/non-claude-provider-autonomy.md``).

This module resolves the provider, runtime mode, and AutonomyPolicy for
a QA phase *before* the session starts so that ``AGENT_PROVIDER_<TYPE>``
and ``AGENT_RUNTIME_MODE_<TYPE>`` env overrides actually reach a decision.
A non-Claude provider that has not passed the promotion gate (or a
non-``full_autonomous`` Claude runtime) fails fast with a clear capability
error and a persisted ``runtime_fallback_<phase>_*.json`` artifact.
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

# QA agents whose runtime path exists and may run on a promoted direct-API
# provider. The reviewer is read-only; the fixer mutates source but the
# runtime layer confines it (generic_edit mutation snapshots + transaction
# rollback + sandbox) and now matches the Claude recovery / model-fallback
# loop. Both promote on the direct-API evidence gate alone (AUTO_CODE_AUTONOMY
# safe/bold + recorded promotion evidence) — there is no separate QA opt-in.
PORTABLE_QA_AGENTS = frozenset({"qa_reviewer", "qa_fixer"})


class QaRuntimeUnsupportedError(RuntimeError):
    """Raised when a QA agent cannot run with the requested provider/runtime."""


@dataclass(frozen=True)
class QaRuntimeDecision:
    """How a QA phase should execute.

    ``use_runtime_layer`` is ``False`` for the default Claude Agent SDK
    path and ``True`` when a promoted direct-API provider may run a portable
    QA agent through ``create_runtime_session`` / ``run_runtime_session``.
    """

    agent_type: str
    provider_name: str
    runtime_mode: str
    use_runtime_layer: bool


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
    * A direct-API provider running a portable QA agent (``qa_reviewer`` or
      ``qa_fixer``) that passes the promotion gate -> ``use_runtime_layer=
      True``. Promotion is gated on ``AUTO_CODE_AUTONOMY=safe``/``bold`` plus
      recorded evidence; there is no separate QA opt-in.

    Raises :class:`QaRuntimeUnsupportedError` for every other non-Claude /
    non-``full_autonomous`` request (un-promoted providers, or a non-Claude
    provider whose promotion gate is unsatisfied), so the default safety
    contract holds.
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

    # Direct-API path for a portable QA agent, gated solely on the direct-API
    # promotion gate (recorded evidence + AUTO_CODE_AUTONOMY=safe/bold via
    # ADR-006). No separate QA opt-in: QA agents promote on the same evidence
    # as the coder. The reviewer is read-only; the fixer mutates source but the
    # runtime layer confines it (generic_edit snapshots + transaction rollback
    # + sandbox) and matches the Claude recovery / model-fallback loop.
    if agent_type in PORTABLE_QA_AGENTS and provider_name != "claude":
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
        policy = autonomy_policy_for(provider_name)
        message = (
            f"QA phase '{agent_type}' cannot run with provider={provider_name}: "
            f"the direct-API promotion gate is not satisfied "
            f"(status={gate.status}, reason={gate.reason}, "
            f"missing={gate.missing_requirements}). Set AUTO_CODE_AUTONOMY=safe "
            "and accumulate provider promotion evidence (see "
            "docs/roadmap/non-claude-provider-autonomy.md), or set "
            f"AGENT_PROVIDER_{agent_type.upper()}=claude to use the Claude SDK "
            f"(autonomy policy snapshot: {policy.to_dict()}; "
            f"runtime decision saved to {artifact_path})."
        )
        debug_error("qa_runtime_routing", message)
        raise QaRuntimeUnsupportedError(message)

    policy = autonomy_policy_for(provider_name)
    message = (
        f"QA phase '{agent_type}' cannot run with provider={provider_name} "
        f"runtime={selected_mode}. QA agents require either Claude "
        "full_autonomous or a promoted direct-API provider running "
        f"generic_edit. Set AGENT_PROVIDER_{agent_type.upper()}=claude and "
        f"AGENT_RUNTIME_MODE_{agent_type.upper()}=full_autonomous to run this "
        "phase (see docs/roadmap/non-claude-provider-autonomy.md; autonomy "
        f"policy snapshot: {policy.to_dict()}; "
        f"runtime decision saved to {artifact_path})."
    )
    debug_error("qa_runtime_routing", message)
    raise QaRuntimeUnsupportedError(message)
