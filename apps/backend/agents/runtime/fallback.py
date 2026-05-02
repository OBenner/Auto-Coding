"""Runtime-aware fallback decisions.

Model fallback answers "which model should we try next?". Runtime fallback
answers the separate question "which execution surface can this provider safely
use?". Non-Claude providers must not be treated as Claude full-autonomous
sessions just because a fallback model exists.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from .capabilities import RuntimeCapabilities, RuntimeRequirements
from .cli_profiles import select_cli_runner_profiles
from .modes import RuntimeMode, normalize_runtime_mode

RuntimePhase = Literal["planning", "coding", "analysis"]

RUNTIME_FALLBACK_ENV = "AUTO_CODE_RUNTIME_FALLBACK"
_TRUTHY = {"1", "true", "yes", "on"}
_DEGRADED_FALLBACKS: dict[RuntimeMode, tuple[RuntimeMode, ...]] = {
    "full_autonomous": ("generic_edit", "patch_proposal", "analysis_only"),
    "generic_edit": ("patch_proposal", "analysis_only"),
    "patch_proposal": ("analysis_only",),
    "analysis_only": (),
}


@dataclass(frozen=True)
class RuntimeFallbackDecision:
    """Selected runtime mode plus the reason for the decision."""

    provider_name: str
    requested_mode: RuntimeMode
    selected_mode: RuntimeMode
    fallback_applied: bool
    reason: str = ""
    missing_capabilities: tuple[str, ...] = ()
    compatible_fallbacks: tuple[RuntimeMode, ...] = ()
    runner_candidates: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize the decision for logs and artifacts."""
        payload: dict[str, object] = {
            "provider": self.provider_name,
            "requested_mode": self.requested_mode,
            "selected_mode": self.selected_mode,
            "fallback_applied": self.fallback_applied,
            "reason": self.reason,
            "missing_capabilities": list(self.missing_capabilities),
            "compatible_fallbacks": list(self.compatible_fallbacks),
        }
        if self.runner_candidates is not None:
            payload["runner_candidates"] = self.runner_candidates
        return payload


def runtime_fallback_enabled() -> bool:
    """Return true when degraded runtime fallback is explicitly enabled."""
    return os.environ.get(RUNTIME_FALLBACK_ENV, "").strip().lower() in _TRUTHY


def capabilities_for_runtime_mode(
    provider_name: str,
    runtime_mode: RuntimeMode,
) -> RuntimeCapabilities:
    """Return static runtime capabilities for a provider/runtime pair."""
    provider_name = provider_name.lower()
    runtime_mode = normalize_runtime_mode(runtime_mode)

    if runtime_mode == "full_autonomous" and provider_name == "claude":
        return RuntimeCapabilities.claude_agent_sdk()
    if runtime_mode == "full_autonomous" and provider_name == "codex":
        return RuntimeCapabilities.codex_cli()
    if runtime_mode == "generic_edit":
        return RuntimeCapabilities.generic_edit()
    if runtime_mode == "patch_proposal":
        return RuntimeCapabilities.patch_proposal()
    return RuntimeCapabilities.completion_only()


def requirements_for_runtime_mode(
    runtime_mode: RuntimeMode,
    *,
    phase: RuntimePhase,
) -> RuntimeRequirements:
    """Return the requirements used when a runtime mode is selected."""
    runtime_mode = normalize_runtime_mode(runtime_mode)
    if runtime_mode == "generic_edit":
        return RuntimeRequirements.generic_edit()
    if runtime_mode == "patch_proposal":
        return RuntimeRequirements.patch_proposal()
    if runtime_mode == "analysis_only":
        return RuntimeRequirements.text_only()
    if phase == "analysis":
        return RuntimeRequirements.text_only()
    if phase == "planning":
        return RuntimeRequirements.planner()
    return RuntimeRequirements.full_coder()


def compatible_fallback_modes(
    *,
    provider_name: str,
    requested_mode: RuntimeMode,
    phase: RuntimePhase,
) -> tuple[RuntimeMode, ...]:
    """Return degraded runtime modes that satisfy their own requirements."""
    compatible: list[RuntimeMode] = []
    for candidate in _DEGRADED_FALLBACKS[requested_mode]:
        candidate_requirements = requirements_for_runtime_mode(candidate, phase=phase)
        candidate_capabilities = capabilities_for_runtime_mode(provider_name, candidate)
        if candidate_capabilities.supports(candidate_requirements):
            compatible.append(candidate)
    return tuple(compatible)


def runner_candidates_for_modes(
    *,
    requested_mode: RuntimeMode,
    selected_mode: RuntimeMode,
    compatible_modes: tuple[RuntimeMode, ...] = (),
) -> dict[str, Any]:
    """Return CLI runner candidates for fallback diagnostics without selecting one."""
    modes = tuple(dict.fromkeys((requested_mode, selected_mode, *compatible_modes)))
    mode_candidates = {
        mode: select_cli_runner_profiles(runtime_mode=mode).to_dict(
            include_detection=False,
        )
        for mode in modes
    }
    selected_mode_candidates = mode_candidates[selected_mode]["selected_runner_ids"]
    return {
        "selection_kind": "runtime_mode_candidate_snapshot",
        "selected_runner_id": None,
        "requested_mode": requested_mode,
        "selected_mode": selected_mode,
        "selected_mode_runner_candidates": selected_mode_candidates,
        "modes": mode_candidates,
    }


def resolve_runtime_mode_with_fallback(
    *,
    provider_name: str,
    requested_mode: str | None,
    phase: RuntimePhase,
    allow_fallback: bool | None = None,
) -> RuntimeFallbackDecision:
    """Resolve a runtime mode without crossing provider capability boundaries.

    By default this preserves fail-fast behavior. When ``allow_fallback`` is true
    (or ``AUTO_CODE_RUNTIME_FALLBACK=true``), incompatible non-Claude full
    autonomous requests degrade to the first compatible limited runtime.
    """
    provider_name = provider_name.lower()
    requested = normalize_runtime_mode(requested_mode)
    allow = runtime_fallback_enabled() if allow_fallback is None else allow_fallback

    requested_capabilities = capabilities_for_runtime_mode(provider_name, requested)
    requested_requirements = requirements_for_runtime_mode(requested, phase=phase)
    missing_capabilities = tuple(requested_capabilities.missing(requested_requirements))
    if requested_capabilities.supports(requested_requirements):
        return RuntimeFallbackDecision(
            provider_name=provider_name,
            requested_mode=requested,
            selected_mode=requested,
            fallback_applied=False,
            runner_candidates=runner_candidates_for_modes(
                requested_mode=requested,
                selected_mode=requested,
            ),
        )

    compatible_modes = compatible_fallback_modes(
        provider_name=provider_name,
        requested_mode=requested,
        phase=phase,
    )

    if not allow:
        return RuntimeFallbackDecision(
            provider_name=provider_name,
            requested_mode=requested,
            selected_mode=requested,
            fallback_applied=False,
            reason=(
                f"{provider_name}/{requested} does not satisfy "
                f"{requested_requirements.mode}; {RUNTIME_FALLBACK_ENV} is disabled"
            ),
            missing_capabilities=missing_capabilities,
            compatible_fallbacks=compatible_modes,
            runner_candidates=runner_candidates_for_modes(
                requested_mode=requested,
                selected_mode=requested,
                compatible_modes=compatible_modes,
            ),
        )

    if compatible_modes:
        candidate = compatible_modes[0]
        return RuntimeFallbackDecision(
            provider_name=provider_name,
            requested_mode=requested,
            selected_mode=candidate,
            fallback_applied=True,
            reason=(
                f"{provider_name}/{requested} cannot provide "
                f"{requested_requirements.mode}; using {candidate}"
            ),
            missing_capabilities=missing_capabilities,
            compatible_fallbacks=compatible_modes,
            runner_candidates=runner_candidates_for_modes(
                requested_mode=requested,
                selected_mode=candidate,
                compatible_modes=compatible_modes,
            ),
        )

    return RuntimeFallbackDecision(
        provider_name=provider_name,
        requested_mode=requested,
        selected_mode=requested,
        fallback_applied=False,
        reason=f"No compatible runtime fallback found for {provider_name}/{requested}",
        missing_capabilities=missing_capabilities,
        runner_candidates=runner_candidates_for_modes(
            requested_mode=requested,
            selected_mode=requested,
        ),
    )
