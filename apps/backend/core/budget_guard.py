"""Per-spec cost budget guard (P5.T4).

Reads an optional USD budget from ``AUTO_CODE_COST_LIMIT`` and compares it
against the spec's accumulated cost (``cost_report.json`` via
:class:`~core.cost_tracking.CostTracker`). The build loops (coder + QA) call
:func:`evaluate_budget` at the top of each iteration and stop cleanly once the
budget is exhausted, so a runaway agent can't silently burn past a configured
cap.

The guard is opt-in and fail-open: with no limit set — or on any error reading
the cost report — it returns an inactive status that never blocks a build.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# USD budget per spec; unset/invalid/non-positive disables the guard.
COST_LIMIT_ENV = "AUTO_CODE_COST_LIMIT"

# Emit a warning once spend crosses this fraction of the limit.
WARN_FRACTION = 0.8


@dataclass(frozen=True)
class BudgetStatus:
    """Outcome of a budget check for a spec."""

    limit: float | None  # configured USD cap, or None when the guard is off
    total_cost: float  # accumulated spec cost in USD
    exceeded: bool  # True when total_cost >= limit
    warning: bool  # True when in [WARN_FRACTION * limit, limit)
    message: str | None  # human-readable status, or None when inactive/quiet

    @property
    def active(self) -> bool:
        """Whether a budget is configured at all."""
        return self.limit is not None


def resolve_cost_limit(env: Mapping[str, str] | None = None) -> float | None:
    """Resolve the per-spec USD budget from ``AUTO_CODE_COST_LIMIT``.

    Returns ``None`` when unset, unparseable, or non-positive (guard disabled).
    Never raises — a bad value must not break a build.
    """
    env_map = os.environ if env is None else env
    raw = env_map.get(COST_LIMIT_ENV, "").strip()
    if not raw:
        return None
    try:
        limit = float(raw)
    except (TypeError, ValueError):
        logger.warning("Invalid %s=%r; ignoring cost budget.", COST_LIMIT_ENV, raw)
        return None
    if limit <= 0:
        return None
    return limit


def _read_total_cost(spec_dir: Path) -> float:
    """Best-effort read of the spec's accumulated cost; 0.0 on any failure."""
    try:
        from core.cost_tracking import CostTracker

        return CostTracker(spec_dir).get_total_cost()
    except Exception as exc:  # pragma: no cover - defensive, cost is optional
        logger.warning("Failed to read spec cost for budget check: %s", exc)
        return 0.0


def evaluate_budget(
    spec_dir: Path,
    env: Mapping[str, str] | None = None,
) -> BudgetStatus:
    """Compare the spec's accumulated cost against the configured budget.

    Args:
        spec_dir: Spec directory holding ``cost_report.json``.
        env: Environment mapping (defaults to ``os.environ``).

    Returns:
        A :class:`BudgetStatus`. When no budget is configured the status is
        inactive (``exceeded`` and ``warning`` both False, ``message`` None).
    """
    limit = resolve_cost_limit(env)
    total = _read_total_cost(spec_dir)

    if limit is None:
        return BudgetStatus(None, total, False, False, None)

    exceeded = total >= limit
    warning = not exceeded and total >= limit * WARN_FRACTION

    message: str | None = None
    if exceeded:
        message = (
            f"Cost budget exceeded: ${total:.2f} of ${limit:.2f} limit "
            f"({COST_LIMIT_ENV}). Stopping the build."
        )
    elif warning:
        message = (
            f"Cost budget warning: ${total:.2f} of ${limit:.2f} limit "
            f"({COST_LIMIT_ENV})."
        )

    return BudgetStatus(limit, total, exceeded, warning, message)
