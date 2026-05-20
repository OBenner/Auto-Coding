"""Text formatting helpers for provider autonomous-readiness requirements."""

from __future__ import annotations

from typing import Any


def _requirement_int(value: Any) -> int | None:
    """Return a non-bool integer readiness requirement value."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _requirement_bool(value: Any) -> str | None:
    """Return a compact yes/no readiness requirement value."""
    if not isinstance(value, bool):
        return None
    return "yes" if value else "no"


def _string_list(value: Any) -> list[str]:
    """Return a safe string list from a diagnostics payload."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value[:20] if isinstance(item, str) and item]


def _stable_run_parts(requirements: dict[str, Any]) -> list[str]:
    """Return stable-run requirement summary parts."""
    parts: list[str] = []
    min_stable_runs = _requirement_int(requirements.get("min_stable_runs"))
    observed_recent_window = _requirement_int(
        requirements.get("observed_recent_window")
    )
    if min_stable_runs is not None and observed_recent_window is not None:
        parts.append(f"stable runs {observed_recent_window}/{min_stable_runs}")

    observed_consecutive_passes = _requirement_int(
        requirements.get("observed_consecutive_passes")
    )
    if min_stable_runs is not None and observed_consecutive_passes is not None:
        parts.append(
            f"consecutive passes {observed_consecutive_passes}/{min_stable_runs}"
        )
    return parts


def _history_freshness_part(requirements: dict[str, Any]) -> str:
    """Return latest-run freshness requirement summary."""
    history_fresh = _requirement_bool(requirements.get("history_freshness_complete"))
    if history_fresh is None:
        return ""

    details: list[str] = []
    last_run_at = requirements.get("last_run_at")
    if isinstance(last_run_at, str) and last_run_at:
        details.append(f"last run {last_run_at}")
    max_age = _requirement_int(requirements.get("max_history_age_seconds"))
    if max_age is not None:
        details.append(f"max age {max_age}s")
    suffix = f" ({', '.join(details)})" if details else ""
    return f"history fresh {history_fresh}{suffix}"


def _live_fault_coverage_part(requirements: dict[str, Any]) -> str:
    """Return live fault coverage requirement summary."""
    live_fault_coverage = _requirement_bool(
        requirements.get("live_fault_coverage_complete")
    )
    if live_fault_coverage is None:
        return ""

    missing_cases = _string_list(requirements.get("live_fault_missing_cases"))
    suffix = f" (missing {', '.join(missing_cases)})" if missing_cases else ""
    return f"live fault coverage {live_fault_coverage}{suffix}"


def format_autonomous_readiness_requirements(
    requirements: Any,
    *,
    empty: str = "",
) -> str:
    """Return compact autonomous-readiness requirement evidence for text output."""
    if not isinstance(requirements, dict):
        return empty

    parts = [
        *_stable_run_parts(requirements),
        _history_freshness_part(requirements),
        _live_fault_coverage_part(requirements),
    ]
    return ", ".join(part for part in parts if part) or empty
