"""Tests for the per-spec cost budget guard (P5.T4).

The guard reads AUTO_CODE_COST_LIMIT and compares it against the spec's
accumulated cost (cost_report.json). It must be opt-in, fail-open, and produce
a clear message when the budget is exceeded so the build loops can stop.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from core.budget_guard import (  # noqa: E402
    COST_LIMIT_ENV,
    BudgetStatus,
    evaluate_budget,
    resolve_cost_limit,
)
from core.cost_tracking import CostTracker  # noqa: E402

MODEL = "claude-sonnet-4-5-20250929"


def make_spec_with_cost(
    tmp_path: Path, *, input_tokens: int, output_tokens: int
) -> Path:
    """Create a spec dir with a recorded usage so get_total_cost() is > 0."""
    spec_dir = tmp_path / "001-spec"
    spec_dir.mkdir(parents=True)
    CostTracker(spec_dir).log_usage("coder", MODEL, input_tokens, output_tokens)
    return spec_dir


class TestResolveCostLimit:
    def test_unset_returns_none(self, monkeypatch):
        monkeypatch.delenv(COST_LIMIT_ENV, raising=False)
        assert resolve_cost_limit() is None

    def test_valid_value(self, monkeypatch):
        monkeypatch.setenv(COST_LIMIT_ENV, "5.50")
        assert resolve_cost_limit() == 5.5

    def test_whitespace_and_empty_return_none(self, monkeypatch):
        monkeypatch.setenv(COST_LIMIT_ENV, "   ")
        assert resolve_cost_limit() is None

    def test_invalid_returns_none(self, monkeypatch):
        monkeypatch.setenv(COST_LIMIT_ENV, "abc")
        assert resolve_cost_limit() is None

    def test_non_positive_returns_none(self, monkeypatch):
        monkeypatch.setenv(COST_LIMIT_ENV, "0")
        assert resolve_cost_limit() is None
        monkeypatch.setenv(COST_LIMIT_ENV, "-3")
        assert resolve_cost_limit() is None

    def test_explicit_env_mapping_overrides_os_environ(self, monkeypatch):
        monkeypatch.setenv(COST_LIMIT_ENV, "1")
        assert resolve_cost_limit({COST_LIMIT_ENV: "9"}) == 9.0


class TestEvaluateBudget:
    def test_inactive_without_limit(self, tmp_path, monkeypatch):
        monkeypatch.delenv(COST_LIMIT_ENV, raising=False)
        spec_dir = make_spec_with_cost(
            tmp_path, input_tokens=1_000_000, output_tokens=0
        )

        status = evaluate_budget(spec_dir)

        assert isinstance(status, BudgetStatus)
        assert status.active is False
        assert status.exceeded is False
        assert status.warning is False
        assert status.message is None
        assert status.total_cost > 0  # cost still measured, just not enforced

    def test_under_budget_is_quiet(self, tmp_path):
        # 1M input tokens of Sonnet = $3; a $100 limit is nowhere near.
        spec_dir = make_spec_with_cost(
            tmp_path, input_tokens=1_000_000, output_tokens=0
        )

        status = evaluate_budget(spec_dir, {COST_LIMIT_ENV: "100"})

        assert status.active is True
        assert status.exceeded is False
        assert status.warning is False
        assert status.message is None

    def test_warning_band(self, tmp_path):
        # $3 spend against a $3.50 limit -> 85% -> warning, not exceeded.
        spec_dir = make_spec_with_cost(
            tmp_path, input_tokens=1_000_000, output_tokens=0
        )

        status = evaluate_budget(spec_dir, {COST_LIMIT_ENV: "3.50"})

        assert status.exceeded is False
        assert status.warning is True
        assert "warning" in status.message.lower()
        assert "$3.00" in status.message
        assert "$3.50" in status.message

    def test_exceeded_produces_stop_message(self, tmp_path):
        # $3 spend against a $1 limit -> exceeded.
        spec_dir = make_spec_with_cost(
            tmp_path, input_tokens=1_000_000, output_tokens=0
        )

        status = evaluate_budget(spec_dir, {COST_LIMIT_ENV: "1"})

        assert status.exceeded is True
        assert status.warning is False
        assert status.message is not None
        assert "exceeded" in status.message.lower()
        assert "Stopping the build" in status.message
        assert COST_LIMIT_ENV in status.message

    def test_exact_limit_counts_as_exceeded(self, tmp_path):
        # $3 spend against a $3 limit -> total >= limit -> exceeded.
        spec_dir = make_spec_with_cost(
            tmp_path, input_tokens=1_000_000, output_tokens=0
        )

        status = evaluate_budget(spec_dir, {COST_LIMIT_ENV: "3"})

        assert status.exceeded is True

    def test_missing_cost_report_is_zero_cost(self, tmp_path):
        spec_dir = tmp_path / "002-empty"
        spec_dir.mkdir()

        status = evaluate_budget(spec_dir, {COST_LIMIT_ENV: "1"})

        assert status.total_cost == 0.0
        assert status.exceeded is False
        assert status.warning is False
