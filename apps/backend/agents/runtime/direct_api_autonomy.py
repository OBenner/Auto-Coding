"""Direct API provider full-autonomous activation gates.

Thresholds and the provider allowlist are sourced from ``AutonomyPolicy``
so operators can tune them per provider via env vars or a JSON file
(see ``core/autonomy_policy.py``). The legacy module-level constants
below are kept as backward-compat aliases that mirror the current
defaults.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.autonomy_level import AUTONOMY_LEVEL_ENV, resolve_autonomy_settings
from core.autonomy_policy import (
    DEFAULT_ALLOWED_PHASES,
    DEFAULT_MAX_HISTORY_AGE_DAYS,
    DEFAULT_MIN_STABLE_RUNS,
    DEFAULT_REQUIRED_LIVE_FAULT_CASES,
    DEFAULT_REQUIRED_LIVE_TASK_FAMILIES,
    DIRECT_API_PROVIDERS,
    AutonomyPolicy,
    autonomy_policy_for,
)
from core.paths import (
    AUTO_CODE_RUNTIME_DIR,
    PROVIDER_SMOKE_HISTORY_FILENAME,
    resolve_provider_smoke_history_path,
)

logger = logging.getLogger(__name__)

DIRECT_API_AUTONOMOUS_ENV = "AUTO_CODE_DIRECT_API_FULL_AUTONOMOUS"
# Backward-compat aliases. Prefer ``AutonomyPolicy`` for runtime decisions.
DIRECT_API_AUTONOMOUS_PROVIDERS = DIRECT_API_PROVIDERS
DIRECT_API_AUTONOMOUS_ALLOWED_PHASES = DEFAULT_ALLOWED_PHASES
DIRECT_API_AUTONOMOUS_MIN_STABLE_RUNS = DEFAULT_MIN_STABLE_RUNS
DIRECT_API_AUTONOMOUS_MAX_HISTORY_AGE = timedelta(days=DEFAULT_MAX_HISTORY_AGE_DAYS)
DIRECT_API_AUTONOMOUS_REQUIRED_LIVE_FAULT_CASES = DEFAULT_REQUIRED_LIVE_FAULT_CASES
DIRECT_API_AUTONOMOUS_REQUIRED_LIVE_TASK_FAMILIES = DEFAULT_REQUIRED_LIVE_TASK_FAMILIES
# Canonical relative path under the project. Reads also tolerate the
# legacy ``.auto-Codex`` location via ``resolve_provider_smoke_history_path``.
DIRECT_API_AUTONOMOUS_HISTORY_PATH = (
    AUTO_CODE_RUNTIME_DIR / PROVIDER_SMOKE_HISTORY_FILENAME
)
_TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DirectApiAutonomousGate:
    """Activation decision for a direct API provider autonomous runtime."""

    provider: str
    allowed: bool
    status: str
    reason: str
    missing_requirements: list[str]
    runtime_adapter: str = "direct_api_autonomous"
    underlying_runtime_mode: str = "generic_edit"
    history_path: str = str(DIRECT_API_AUTONOMOUS_HISTORY_PATH)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe gate diagnostic payload."""
        return asdict(self)


def direct_api_autonomous_env_enabled(
    env: Mapping[str, str] | None = None,
) -> bool:
    """Return true when direct API full-autonomous activation is enabled."""
    values = os.environ if env is None else env
    return values.get(DIRECT_API_AUTONOMOUS_ENV, "").strip().lower() in _TRUTHY


def resolve_direct_api_autonomous_gate(
    *,
    provider_name: str,
    project_dir: Path,
    phase: str,
    env: Mapping[str, str] | None = None,
    policy: AutonomyPolicy | None = None,
) -> DirectApiAutonomousGate:
    """Return whether a direct provider may use the autonomous local runtime.

    Thresholds and the provider allowlist come from ``AutonomyPolicy``
    (resolved here unless the caller passed an explicit instance), so
    operators can tune them per provider via env vars or a JSON file.
    """
    provider = provider_name.lower()
    if policy is None:
        policy = autonomy_policy_for(provider, env=env)
    history_path = resolve_provider_smoke_history_path(project_dir)
    history_path_str = str(DIRECT_API_AUTONOMOUS_HISTORY_PATH)
    if not policy.direct_api_eligible:
        return DirectApiAutonomousGate(
            provider=provider,
            allowed=False,
            status="not_applicable",
            reason="provider_not_direct_api",
            missing_requirements=[],
            history_path=history_path_str,
        )
    if phase not in policy.allowed_phases:
        return DirectApiAutonomousGate(
            provider=provider,
            allowed=False,
            status="blocked",
            reason="direct_api_autonomous_phase_blocked",
            missing_requirements=["coding_phase"],
            history_path=history_path_str,
        )
    # Bridge the single AUTO_CODE_AUTONOMY knob (ADR-006) into the gate.
    # ``resolve_autonomy_settings`` already folds the level default and the
    # deprecated ``AUTO_CODE_DIRECT_API_FULL_AUTONOMOUS`` override into one
    # flag, so safe/bold enable the gate without the legacy env var while
    # that env var keeps working for back-compat.
    autonomy = resolve_autonomy_settings(env=env)
    if not autonomy.direct_api_gate_enabled:
        return DirectApiAutonomousGate(
            provider=provider,
            allowed=False,
            status="disabled",
            reason="direct_api_autonomous_disabled",
            missing_requirements=[AUTONOMY_LEVEL_ENV],
            history_path=history_path_str,
        )
    if autonomy.direct_api_skip_gate:
        # bold is the power-user level: it trusts the operator and grants
        # promotion without provider e2e evidence. Surface that loudly so
        # an unproven provider running full-autonomous is never silent.
        logger.warning(
            "Direct-API autonomous gate bypassed for %s via %s=%s: promotion "
            "granted WITHOUT provider e2e evidence (power-user mode).",
            provider,
            AUTONOMY_LEVEL_ENV,
            autonomy.level.value,
        )
        return DirectApiAutonomousGate(
            provider=provider,
            allowed=True,
            status="passed",
            reason="direct_api_autonomous_gate_skipped",
            missing_requirements=[],
            history_path=history_path_str,
        )

    provider_stats, history_error = _load_provider_stats(history_path, provider)
    if history_error is not None:
        return DirectApiAutonomousGate(
            provider=provider,
            allowed=False,
            status="blocked",
            reason=history_error,
            missing_requirements=["provider_e2e_history"],
            history_path=history_path_str,
        )

    missing = _direct_api_autonomous_missing_requirements(provider_stats, policy)
    if missing:
        return DirectApiAutonomousGate(
            provider=provider,
            allowed=False,
            status="blocked",
            reason="direct_api_autonomous_requirements_missing",
            missing_requirements=missing,
            history_path=history_path_str,
        )
    return DirectApiAutonomousGate(
        provider=provider,
        allowed=True,
        status="passed",
        reason="direct_api_autonomous_gate_passed",
        missing_requirements=[],
        history_path=history_path_str,
    )


@dataclass(frozen=True)
class DirectApiAutonomousReadiness:
    """A one-shot promotion-readiness snapshot for a direct-API provider.

    Combines the gate decision (the actionable allowed / missing view), the
    resolved :class:`AutonomyPolicy` thresholds, the operator's current
    autonomy level, and the recorded provider e2e evidence so a single
    command can answer "how close is this provider to full-autonomous
    promotion, and exactly what is missing".
    """

    provider: str
    autonomy_level: str
    gate: DirectApiAutonomousGate
    policy: dict[str, Any]
    evidence: dict[str, Any] | None
    # ``None`` when evidence is present; otherwise a stable id explaining
    # why (``provider_history_missing`` / ``provider_history_unreadable``).
    evidence_status: str | None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe readiness payload."""
        return {
            "provider": self.provider,
            "autonomy_level": self.autonomy_level,
            "gate": self.gate.to_dict(),
            "policy": self.policy,
            "evidence": self.evidence,
            "evidence_status": self.evidence_status,
        }


def resolve_direct_api_autonomous_readiness(
    *,
    provider_name: str,
    project_dir: Path,
    env: Mapping[str, str] | None = None,
    policy: AutonomyPolicy | None = None,
) -> DirectApiAutonomousReadiness:
    """Resolve a full promotion-readiness snapshot for one provider.

    Pure read: evaluates the gate, the policy, and the recorded evidence
    without mutating anything, so it is safe to call from inspection CLIs.
    """
    provider = provider_name.lower()
    if policy is None:
        policy = autonomy_policy_for(provider, env=env)
    autonomy = resolve_autonomy_settings(env=env)
    gate = resolve_direct_api_autonomous_gate(
        provider_name=provider,
        project_dir=project_dir,
        phase="coding",
        env=env,
        policy=policy,
    )
    stats, evidence_status = _load_provider_stats(
        resolve_provider_smoke_history_path(project_dir), provider
    )
    return DirectApiAutonomousReadiness(
        provider=provider,
        autonomy_level=autonomy.level.value,
        gate=gate,
        policy=policy.to_dict(),
        evidence=stats or None,
        evidence_status=evidence_status,
    )


def _load_provider_stats(
    history_path: Path,
    provider: str,
) -> tuple[dict[str, Any], str | None]:
    """Load one provider stats block from the provider smoke history artifact."""
    if not history_path.exists():
        return {}, "provider_history_missing"
    try:
        payload = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, "provider_history_unreadable"
    providers = payload.get("providers") if isinstance(payload, dict) else None
    provider_stats = providers.get(provider) if isinstance(providers, dict) else None
    if not isinstance(provider_stats, dict):
        return {}, "provider_history_missing"
    return provider_stats, None


def _direct_api_autonomous_missing_requirements(
    provider_stats: dict[str, Any],
    policy: AutonomyPolicy,
) -> list[str]:
    """Return stable requirement ids blocking direct API full-autonomous activation."""
    missing: list[str] = []
    if provider_stats.get("last_status") != "passed" or (
        provider_stats.get("last_runtime_mode") != "provider_e2e"
    ):
        _append_missing(missing, "provider_e2e_passed")
    if provider_stats.get("last_provider_e2e_status") != "passed":
        _append_missing(missing, "provider_e2e_passed")
    if provider_stats.get("last_reliability_status") != "complete":
        _append_missing(missing, "provider_reliability_complete")
    if not _stable_history_complete(provider_stats, policy):
        _append_missing(missing, "stable_history_runs")
    if not _fresh_history_complete(provider_stats, policy):
        _append_missing(missing, "fresh_provider_history")
    if not _live_fault_coverage_complete(provider_stats, policy):
        _append_missing(missing, "live_fault_probe_coverage")
    if not _live_task_family_coverage_complete(provider_stats, policy):
        _append_missing(missing, "live_task_family_coverage")
    if not _promotion_gate_complete(provider_stats):
        _append_missing(missing, "promotion_gate")
    return missing


def _stable_history_complete(
    provider_stats: dict[str, Any],
    policy: AutonomyPolicy,
) -> bool:
    threshold = policy.min_stable_runs
    recent_window = _int_payload(provider_stats.get("recent_window"))
    if recent_window is None:
        recent_window = _int_payload(provider_stats.get("total_runs"))
    consecutive_passes = _int_payload(provider_stats.get("consecutive_passes"))
    if consecutive_passes is None:
        consecutive_passes = _int_payload(provider_stats.get("passed_runs"))
    return (
        provider_stats.get("trend") == "provider_history_stable"
        and (recent_window or 0) >= threshold
        and (consecutive_passes or 0) >= threshold
    )


def _fresh_history_complete(
    provider_stats: dict[str, Any],
    policy: AutonomyPolicy,
) -> bool:
    last_run_at = provider_stats.get("last_run_at")
    if not isinstance(last_run_at, str) or not last_run_at.strip():
        return False
    try:
        parsed = datetime.fromisoformat(last_run_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return datetime.now(UTC) - parsed <= policy.max_history_age


def _live_fault_coverage_complete(
    provider_stats: dict[str, Any],
    policy: AutonomyPolicy,
) -> bool:
    if provider_stats.get("last_live_fault_probe_status") != "passed":
        return False
    covered = set(_string_list(provider_stats.get("live_fault_probe_covered_cases")))
    return set(policy.required_live_fault_cases).issubset(covered)


def _live_task_family_coverage_complete(
    provider_stats: dict[str, Any],
    policy: AutonomyPolicy,
) -> bool:
    if provider_stats.get("last_live_task_family_status") != "passed":
        return False
    covered = set(_string_list(provider_stats.get("live_task_family_covered_families")))
    return set(policy.required_live_task_families).issubset(covered)


def _promotion_gate_complete(provider_stats: dict[str, Any]) -> bool:
    return (
        provider_stats.get("last_promotion_gate_status") == "passed"
        and not _string_list(provider_stats.get("promotion_missing_reliability_cases"))
        and not _string_list(provider_stats.get("promotion_missing_e2e_runs"))
    )


def _append_missing(missing: list[str], requirement: str) -> None:
    if requirement not in missing:
        missing.append(requirement)


def _int_payload(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]
