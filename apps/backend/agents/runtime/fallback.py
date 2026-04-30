"""Runtime-aware fallback decisions.

Model fallback answers "which model should we try next?". Runtime fallback
answers the separate question "which execution surface can this provider safely
use?". Non-Claude providers must not be treated as Claude full-autonomous
sessions just because a fallback model exists.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from .capabilities import RuntimeCapabilities, RuntimeRequirements
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
    if requested_capabilities.supports(requested_requirements):
        return RuntimeFallbackDecision(
            provider_name=provider_name,
            requested_mode=requested,
            selected_mode=requested,
            fallback_applied=False,
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
        )

    for candidate in _DEGRADED_FALLBACKS[requested]:
        candidate_requirements = requirements_for_runtime_mode(candidate, phase=phase)
        candidate_capabilities = capabilities_for_runtime_mode(provider_name, candidate)
        if candidate_capabilities.supports(candidate_requirements):
            return RuntimeFallbackDecision(
                provider_name=provider_name,
                requested_mode=requested,
                selected_mode=candidate,
                fallback_applied=True,
                reason=(
                    f"{provider_name}/{requested} cannot provide "
                    f"{requested_requirements.mode}; using {candidate}"
                ),
            )

    return RuntimeFallbackDecision(
        provider_name=provider_name,
        requested_mode=requested,
        selected_mode=requested,
        fallback_applied=False,
        reason=f"No compatible runtime fallback found for {provider_name}/{requested}",
    )
