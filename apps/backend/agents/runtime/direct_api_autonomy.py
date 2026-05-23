"""Direct API provider full-autonomous activation gates."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DIRECT_API_AUTONOMOUS_ENV = "AUTO_CODE_DIRECT_API_FULL_AUTONOMOUS"
DIRECT_API_AUTONOMOUS_PROVIDERS = (
    "openai",
    "google",
    "openrouter",
    "litellm",
    "zhipuai",
    "ollama",
)
DIRECT_API_AUTONOMOUS_ALLOWED_PHASES = ("coding",)
DIRECT_API_AUTONOMOUS_MIN_STABLE_RUNS = 3
DIRECT_API_AUTONOMOUS_MAX_HISTORY_AGE = timedelta(days=7)
DIRECT_API_AUTONOMOUS_REQUIRED_LIVE_FAULT_CASES = (
    "gateway_model_limitations",
    "unsupported_tools",
)
DIRECT_API_AUTONOMOUS_REQUIRED_LIVE_TASK_FAMILIES = (
    "multi_step_edit",
    "recovery_resume",
    "single_file_edit",
    "transaction_batching",
)
DIRECT_API_AUTONOMOUS_HISTORY_PATH = Path(
    ".auto-Codex",
    "provider-smoke-history.json",
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
) -> DirectApiAutonomousGate:
    """Return whether a direct provider may use the autonomous local runtime."""
    provider = provider_name.lower()
    history_path = project_dir / DIRECT_API_AUTONOMOUS_HISTORY_PATH
    if provider not in DIRECT_API_AUTONOMOUS_PROVIDERS:
        return DirectApiAutonomousGate(
            provider=provider,
            allowed=False,
            status="not_applicable",
            reason="provider_not_direct_api",
            missing_requirements=[],
            history_path=str(DIRECT_API_AUTONOMOUS_HISTORY_PATH),
        )
    if phase not in DIRECT_API_AUTONOMOUS_ALLOWED_PHASES:
        return DirectApiAutonomousGate(
            provider=provider,
            allowed=False,
            status="blocked",
            reason="direct_api_autonomous_phase_blocked",
            missing_requirements=["coding_phase"],
            history_path=str(DIRECT_API_AUTONOMOUS_HISTORY_PATH),
        )
    if not direct_api_autonomous_env_enabled(env):
        return DirectApiAutonomousGate(
            provider=provider,
            allowed=False,
            status="disabled",
            reason="direct_api_autonomous_env_disabled",
            missing_requirements=[DIRECT_API_AUTONOMOUS_ENV],
            history_path=str(DIRECT_API_AUTONOMOUS_HISTORY_PATH),
        )

    provider_stats, history_error = _load_provider_stats(history_path, provider)
    if history_error is not None:
        return DirectApiAutonomousGate(
            provider=provider,
            allowed=False,
            status="blocked",
            reason=history_error,
            missing_requirements=["provider_e2e_history"],
            history_path=str(DIRECT_API_AUTONOMOUS_HISTORY_PATH),
        )

    missing = _direct_api_autonomous_missing_requirements(provider_stats)
    if missing:
        return DirectApiAutonomousGate(
            provider=provider,
            allowed=False,
            status="blocked",
            reason="direct_api_autonomous_requirements_missing",
            missing_requirements=missing,
            history_path=str(DIRECT_API_AUTONOMOUS_HISTORY_PATH),
        )
    return DirectApiAutonomousGate(
        provider=provider,
        allowed=True,
        status="passed",
        reason="direct_api_autonomous_gate_passed",
        missing_requirements=[],
        history_path=str(DIRECT_API_AUTONOMOUS_HISTORY_PATH),
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
) -> list[str]:
    """Return stable requirement ids blocking direct API full-autonomous activation."""
    missing: list[str] = []
    if provider_stats.get("last_status") != "passed" or (
        provider_stats.get("last_runtime_mode") != "provider_e2e"
    ):
        missing.append("provider_e2e_passed")
    if provider_stats.get("last_provider_e2e_status") != "passed":
        _append_missing(missing, "provider_e2e_passed")
    if provider_stats.get("last_reliability_status") != "complete":
        missing.append("provider_reliability_complete")
    if not _stable_history_complete(provider_stats):
        missing.append("stable_history_runs")
    if not _fresh_history_complete(provider_stats):
        missing.append("fresh_provider_history")
    if not _live_fault_coverage_complete(provider_stats):
        missing.append("live_fault_probe_coverage")
    if not _live_task_family_coverage_complete(provider_stats):
        missing.append("live_task_family_coverage")
    if not _promotion_gate_complete(provider_stats):
        missing.append("promotion_gate")
    return missing


def _stable_history_complete(provider_stats: dict[str, Any]) -> bool:
    recent_window = _int_payload(provider_stats.get("recent_window"))
    if recent_window is None:
        recent_window = _int_payload(provider_stats.get("total_runs"))
    consecutive_passes = _int_payload(provider_stats.get("consecutive_passes"))
    if consecutive_passes is None:
        consecutive_passes = _int_payload(provider_stats.get("passed_runs"))
    return (
        provider_stats.get("trend") == "provider_history_stable"
        and (recent_window or 0) >= DIRECT_API_AUTONOMOUS_MIN_STABLE_RUNS
        and (consecutive_passes or 0) >= DIRECT_API_AUTONOMOUS_MIN_STABLE_RUNS
    )


def _fresh_history_complete(provider_stats: dict[str, Any]) -> bool:
    last_run_at = provider_stats.get("last_run_at")
    if not isinstance(last_run_at, str) or not last_run_at.strip():
        return False
    try:
        parsed = datetime.fromisoformat(last_run_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - parsed <= DIRECT_API_AUTONOMOUS_MAX_HISTORY_AGE


def _live_fault_coverage_complete(provider_stats: dict[str, Any]) -> bool:
    if provider_stats.get("last_live_fault_probe_status") != "passed":
        return False
    covered = set(_string_list(provider_stats.get("live_fault_probe_covered_cases")))
    return set(DIRECT_API_AUTONOMOUS_REQUIRED_LIVE_FAULT_CASES).issubset(covered)


def _live_task_family_coverage_complete(provider_stats: dict[str, Any]) -> bool:
    if provider_stats.get("last_live_task_family_status") != "passed":
        return False
    covered = set(_string_list(provider_stats.get("live_task_family_covered_families")))
    return set(DIRECT_API_AUTONOMOUS_REQUIRED_LIVE_TASK_FAMILIES).issubset(covered)


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
