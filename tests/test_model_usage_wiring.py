"""Tests for cost aggregation wiring (P5.T2).

save_token_stats() must attribute cost per session into the spec's
cost_report.json (role + phase + $) and refresh the project-level
.auto-claude/model_usage_summary.json; aggregation must expose cost_by_phase
and survive the summary serialization round-trip.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from agents import session as session_mod  # noqa: E402
from agents.session import save_token_stats  # noqa: E402
from analysis import model_usage_analytics as analytics_mod  # noqa: E402
from analysis.analytics_utils import parse_timestamp  # noqa: E402
from analysis.model_usage_analytics import (  # noqa: E402
    ModelUsageSummary,
    aggregate_model_usage,
    write_model_usage_summary,
)
from core.cost_tracking import CostTracker, UsageRecord  # noqa: E402

MODEL = "claude-sonnet-4-5-20250929"


def make_spec_dir(tmp_path: Path, name: str = "001-test") -> Path:
    spec_dir = tmp_path / ".auto-claude" / "specs" / name
    spec_dir.mkdir(parents=True)
    return spec_dir


def read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class TestCostRecordWiring:
    def test_save_token_stats_appends_cost_record(self, tmp_path, monkeypatch):
        monkeypatch.setattr(session_mod, "_resolve_active_provider", lambda: "claude")
        spec_dir = make_spec_dir(tmp_path)

        assert save_token_stats(spec_dir, "coding", 1000, 500, model=MODEL)

        report = read_json(spec_dir / "cost_report.json")
        assert len(report["records"]) == 1
        record = report["records"][0]
        assert record["agent_type"] == "coder"  # derived from the phase
        assert record["phase"] == "coding"
        assert record["model"] == MODEL
        assert record["provider"] == "claude"
        assert record["cost"] > 0

    def test_agent_type_override_wins_over_phase_mapping(self, tmp_path):
        spec_dir = make_spec_dir(tmp_path)

        assert save_token_stats(
            spec_dir, "coding", 10, 5, model=MODEL, agent_type="qa_fixer"
        )

        record = read_json(spec_dir / "cost_report.json")["records"][0]
        assert record["agent_type"] == "qa_fixer"
        assert record["phase"] == "coding"

    def test_cost_record_timestamp_is_parseable(self, tmp_path):
        # Regression: isoformat() + "Z" produced "+00:00Z", which
        # parse_timestamp rejected — aggregation silently dropped every record.
        spec_dir = make_spec_dir(tmp_path)

        CostTracker(spec_dir).log_usage("coder", MODEL, 10, 5)

        record = read_json(spec_dir / "cost_report.json")["records"][0]
        assert parse_timestamp(record["timestamp"]) is not None


class TestProjectSummaryWiring:
    def test_summary_written_and_accumulates(self, tmp_path, monkeypatch):
        monkeypatch.setattr(session_mod, "_resolve_active_provider", lambda: "claude")
        spec_dir = make_spec_dir(tmp_path)

        assert save_token_stats(spec_dir, "planning", 1000, 500, model=MODEL)
        assert save_token_stats(spec_dir, "coding", 2000, 1000, model=MODEL)

        summary = read_json(tmp_path / ".auto-claude" / "model_usage_summary.json")
        assert summary["total_usage_records"] == 2
        assert summary["total_input_tokens"] == 3000
        assert summary["total_output_tokens"] == 1500
        assert summary["total_cost"] > 0
        assert summary["cost_by_agent"]["planner"] > 0
        assert summary["cost_by_agent"]["coder"] > 0
        assert summary["cost_by_phase"]["planning"] > 0
        assert summary["cost_by_phase"]["coding"] > 0

    def test_spec_outside_canonical_layout_skips_summary(self, tmp_path):
        spec_dir = tmp_path / "adhoc-spec"
        spec_dir.mkdir()

        assert save_token_stats(spec_dir, "coding", 10, 5, model=MODEL)

        assert (spec_dir / "cost_report.json").exists()
        assert not (tmp_path / ".auto-claude").exists()

    def test_summary_failure_does_not_break_save(self, tmp_path, monkeypatch):
        def boom(_project_dir):
            raise RuntimeError("summary exploded")

        # _record_cost_usage imports the function at call time, so patching
        # the module attribute intercepts it.
        monkeypatch.setattr(analytics_mod, "write_model_usage_summary", boom)
        spec_dir = make_spec_dir(tmp_path)

        assert save_token_stats(spec_dir, "coding", 10, 5, model=MODEL)
        assert (spec_dir / "cost_report.json").exists()

    def test_write_model_usage_summary_returns_path(self, tmp_path):
        spec_dir = make_spec_dir(tmp_path)
        CostTracker(spec_dir).log_usage("coder", MODEL, 100, 50, phase="coding")

        out = write_model_usage_summary(tmp_path)

        assert out is not None
        assert out.exists()
        assert read_json(out)["cost_by_phase"]["coding"] > 0


class TestAggregationPhaseBreakdown:
    def test_records_without_phase_land_in_unknown(self, tmp_path):
        spec_dir = make_spec_dir(tmp_path)
        tracker = CostTracker(spec_dir)
        tracker.log_usage("coder", MODEL, 100, 50, phase="coding")
        tracker.log_usage("coder", MODEL, 100, 50)  # legacy record: no phase

        summary = aggregate_model_usage(tmp_path)

        assert set(summary.cost_by_phase) == {"coding", "unknown"}
        assert summary.cost_by_phase["coding"] > 0
        assert summary.cost_by_phase["unknown"] > 0

    def test_summary_serialization_round_trip(self, tmp_path):
        # Regression: to_dict()/from_dict() crashed on the summary's
        # nonexistent total_usage_count field.
        spec_dir = make_spec_dir(tmp_path)
        CostTracker(spec_dir).log_usage("planner", MODEL, 100, 50, phase="planning")

        summary = aggregate_model_usage(tmp_path)
        data = summary.to_dict()
        restored = ModelUsageSummary.from_dict(data)

        assert restored.to_dict() == data
        assert data["cost_by_phase"]["planning"] > 0


class TestUsageRecordPhase:
    def test_round_trip_with_phase(self):
        record = UsageRecord(
            agent_type="coder",
            model=MODEL,
            input_tokens=1,
            output_tokens=2,
            cost=0.5,
            timestamp="2026-07-05T10:00:00+00:00",
            provider="claude",
            phase="coding",
        )
        assert UsageRecord.from_dict(record.to_dict()).phase == "coding"

    def test_legacy_dict_without_phase(self):
        record = UsageRecord.from_dict(
            {
                "agent_type": "coder",
                "model": MODEL,
                "input_tokens": 1,
                "output_tokens": 2,
                "cost": 0.1,
                "timestamp": "2026-07-05T10:00:00+00:00",
            }
        )
        assert record.phase is None
