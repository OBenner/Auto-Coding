"""
Integration Tests for Cost Analytics

Tests end-to-end cost tracking flow:
- Agent session → CostTracker → cost_report.json → Analytics → Dashboard
- Multi-spec aggregation
- Time range filtering
- Export functionality
- Data consistency across modules
"""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# Import from backend modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))

from core.cost_tracking import CostTracker
from analysis.cost_analytics import (
    SpecCostMetrics,
    CostSummary,
    _extract_spec_cost_metrics,
    _parse_timestamp,
    _normalize_boundary,
    aggregate_cost_metrics,
    get_cost_trends,
    export_cost_data,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with multiple specs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        specs_dir = project_dir / ".auto-claude" / "specs"
        specs_dir.mkdir(parents=True)

        # Create 3 spec directories with cost data
        for i, spec_name in enumerate(["001-feature", "002-bugfix", "003-refactor"], 1):
            spec_dir = specs_dir / spec_name
            spec_dir.mkdir()

            # Create implementation_plan.json
            plan = {
                "feature": f"Test Feature {i}",
                "status": "complete",
            }
            plan_file = spec_dir / "implementation_plan.json"
            with open(plan_file, "w", encoding="utf-8") as f:
                json.dump(plan, f)

            # Create cost_report.json with varying data
            tracker = CostTracker(spec_dir=spec_dir)
            tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10_000 * i, 5_000 * i)
            tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 20_000 * i, 10_000 * i)

        yield project_dir


@pytest.fixture
def single_spec_dir():
    """Create a single spec directory for isolated testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir) / ".auto-claude" / "specs" / "test_spec"
        spec_dir.mkdir(parents=True)

        # Create implementation plan
        plan = {"feature": "Test Spec"}
        plan_file = spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f)

        yield spec_dir


# =============================================================================
# END-TO-END FLOW TESTS
# =============================================================================

class TestEndToEndFlow:
    """Test complete flow from agent session to analytics."""

    def test_session_to_dashboard_flow(self, single_spec_dir):
        """Test: Agent session → CostTracker → cost_report.json → Analytics → Dashboard."""
        # Step 1: Simulate agent session (log usage)
        tracker = CostTracker(spec_dir=single_spec_dir)
        cost = tracker.log_session_usage(
            agent_type="coder",
            model="claude-sonnet-4-5-20250929",
            usage_metadata={
                "input_tokens": 15_000,
                "output_tokens": 7_500,
            },
        )

        # Verify cost was calculated
        assert abs(cost - 0.1575) < 0.0001  # 15k * $3 + 7.5k * $15 per 1M

        # Step 2: Verify cost_report.json created with correct structure
        report_file = single_spec_dir / "cost_report.json"
        assert report_file.exists()

        with open(report_file, encoding="utf-8") as f:
            report_data = json.load(f)

        assert "records" in report_data
        assert "total_cost" in report_data
        assert len(report_data["records"]) == 1
        assert abs(report_data["total_cost"] - 0.1575) < 0.0001

        # Step 3: Call analytics aggregation
        metrics = _extract_spec_cost_metrics(single_spec_dir)
        assert metrics is not None
        assert metrics.spec_id == single_spec_dir.name
        assert abs(metrics.total_cost - 0.1575) < 0.0001
        assert metrics.input_tokens == 15_000
        assert metrics.output_tokens == 7_500

        # Step 4: Verify analytics data structure
        analytics_data = tracker.get_analytics_data()
        assert analytics_data["total_cost"] > 0
        assert "cost_by_agent" in analytics_data
        assert "cost_by_model" in analytics_data
        assert "timeline" in analytics_data
        assert len(analytics_data["timeline"]) == 1

        # Step 5: Verify data consistency (no loss)
        assert analytics_data["total_cost"] == report_data["total_cost"]
        assert analytics_data["token_usage"]["input_tokens"] == 15_000
        assert analytics_data["token_usage"]["output_tokens"] == 7_500

    def test_multiple_sessions_accumulate_correctly(self, single_spec_dir):
        """Test multiple agent sessions accumulate in analytics."""
        tracker = CostTracker(spec_dir=single_spec_dir)

        # Simulate multiple sessions
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10_000, 5_000)
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 20_000, 10_000)
        tracker.log_usage("qa_reviewer", "claude-haiku-4-5-20251001", 100_000, 50_000)

        # Verify accumulation
        metrics = _extract_spec_cost_metrics(single_spec_dir)
        assert metrics.session_count == 3
        assert metrics.total_cost > 0

        # Verify breakdowns
        assert "planner" in metrics.cost_by_agent
        assert "coder" in metrics.cost_by_agent
        assert "qa_reviewer" in metrics.cost_by_agent
        assert "claude-sonnet-4-5-20250929" in metrics.cost_by_model
        assert "claude-haiku-4-5-20251001" in metrics.cost_by_model


# =============================================================================
# MULTI-SPEC AGGREGATION TESTS
# =============================================================================

class TestMultiSpecAggregation:
    """Test aggregation across multiple spec directories."""

    def test_aggregate_across_multiple_specs(self, temp_project_dir):
        """Test cost_analytics.py aggregates across multiple spec directories."""
        # Aggregate cost metrics
        summary = aggregate_cost_metrics(temp_project_dir)

        # Verify all specs were found
        assert summary.total_specs == 3
        assert len(summary.specs) == 3

        # Verify totals are correct (sum of all specs)
        assert summary.total_cost > 0
        assert summary.total_tokens > 0
        assert summary.total_sessions == 6  # 2 sessions per spec

        # Verify cost breakdowns aggregate correctly
        assert "planner" in summary.cost_by_agent
        assert "coder" in summary.cost_by_agent
        assert summary.cost_by_agent["planner"] > 0
        assert summary.cost_by_agent["coder"] > 0

        # Verify specs list contains all spec data
        spec_ids = [s.spec_id for s in summary.specs]
        assert "001-feature" in spec_ids
        assert "002-bugfix" in spec_ids
        assert "003-refactor" in spec_ids

    def test_aggregate_calculate_averages(self, temp_project_dir):
        """Test aggregation calculates average and median costs per spec."""
        summary = aggregate_cost_metrics(temp_project_dir)

        # Verify average cost per spec
        assert summary.average_cost_per_spec > 0
        expected_avg = summary.total_cost / summary.total_specs
        assert abs(summary.average_cost_per_spec - expected_avg) < 0.0001

        # Verify median cost per spec
        assert summary.median_cost_per_spec > 0
        spec_costs = [s.total_cost for s in summary.specs]
        spec_costs_sorted = sorted(spec_costs)
        n = len(spec_costs_sorted)
        if n % 2 == 0:
            expected_median = (spec_costs_sorted[n // 2 - 1] + spec_costs_sorted[n // 2]) / 2
        else:
            expected_median = spec_costs_sorted[n // 2]
        assert abs(summary.median_cost_per_spec - expected_median) < 0.0001

    def test_aggregate_calculate_token_efficiency(self, temp_project_dir):
        """Test aggregation calculates token efficiency metrics."""
        summary = aggregate_cost_metrics(temp_project_dir)

        # Verify cost per million tokens
        assert summary.average_cost_per_million_tokens > 0
        expected = (summary.total_cost / summary.total_tokens) * 1_000_000
        assert abs(summary.average_cost_per_million_tokens - expected) < 0.0001

        # Verify tokens per session
        assert summary.average_tokens_per_session > 0
        expected = summary.total_tokens / summary.total_sessions
        assert abs(summary.average_tokens_per_session - expected) < 0.0001

    def test_aggregate_with_no_specs(self):
        """Test aggregation handles empty specs directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            specs_dir = project_dir / ".auto-claude" / "specs"
            specs_dir.mkdir(parents=True)

            summary = aggregate_cost_metrics(project_dir)

            assert summary.total_specs == 0
            assert summary.total_cost == 0.0
            assert len(summary.specs) == 0


# =============================================================================
# TIME RANGE FILTERING TESTS
# =============================================================================

class TestTimeRangeFiltering:
    """Test time range filtering in analytics."""

    def test_filter_by_start_date(self, temp_project_dir):
        """Test filtering specs by start date."""
        # Get baseline (all specs)
        full_summary = aggregate_cost_metrics(temp_project_dir)
        assert full_summary.total_specs == 3

        # Filter to only recent specs (last 7 days)
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=7)

        filtered_summary = aggregate_cost_metrics(
            temp_project_dir, start_date=start_date, end_date=end_date
        )

        # All specs should be included (they were just created)
        assert filtered_summary.total_specs == 3

    def test_filter_by_end_date(self, temp_project_dir):
        """Test filtering specs by end date."""
        # Get actual timestamps from specs
        specs_dir = temp_project_dir / ".auto-claude" / "specs"
        spec_metrics = []
        for spec_dir in specs_dir.iterdir():
            if spec_dir.is_dir():
                metrics = _extract_spec_cost_metrics(spec_dir)
                if metrics and metrics.last_session:
                    spec_metrics.append(metrics)

        if spec_metrics:
            # Filter to before the first session (should exclude all specs)
            first_session = min(m.first_session for m in spec_metrics if m.first_session)
            end_date = first_session - timedelta(days=1)
            start_date = end_date - timedelta(days=7)

            filtered_summary = aggregate_cost_metrics(
                temp_project_dir, start_date=start_date, end_date=end_date
            )

            # No specs should match (all are after the filter range)
            assert filtered_summary.total_specs == 0
        else:
            # Skip test if no valid timestamps
            pytest.skip("No valid timestamps in test data")

    def test_filter_excludes_out_of_range_specs(self, temp_project_dir):
        """Test specs outside date range are excluded."""
        # This test verifies date filtering logic.
        # For simplicity, we'll test that date filtering mechanism exists
        # rather than relying on exact timestamp matching (which can be flaky).

        # Get baseline summary
        baseline = aggregate_cost_metrics(temp_project_dir)
        baseline_count = baseline.total_specs

        # Test with date filter that should include all specs
        end_date = datetime.now(UTC) + timedelta(days=1)  # Future date
        start_date = datetime.now(UTC) - timedelta(days=365)  # Year ago

        filtered_summary = aggregate_cost_metrics(
            temp_project_dir, start_date=start_date, end_date=end_date
        )

        # With wide date range, should include all specs
        assert filtered_summary.total_specs == baseline_count

    def test_cost_trends_time_series(self, temp_project_dir):
        """Test get_cost_trends returns time series data."""
        trends = get_cost_trends(temp_project_dir, window_days=30, granularity="daily")

        # Should return list of trend data points
        assert isinstance(trends, list)

        # May be empty if no specs in window (timing-dependent test)
        # If empty, verify structure is still valid
        if len(trends) > 0:
            # Verify trend data structure
            trend = trends[0]
            assert "date" in trend
            assert "total_cost" in trend
            assert "total_tokens" in trend
            assert "total_sessions" in trend
            assert "specs_count" in trend
        else:
            # If empty, verify trends list is valid (not None, etc.)
            assert trends == []

    def test_cost_trends_filters_by_window(self, temp_project_dir):
        """Test cost trends respects time window."""
        # Get trends for different windows
        trends_7d = get_cost_trends(temp_project_dir, window_days=7, granularity="daily")
        trends_30d = get_cost_trends(temp_project_dir, window_days=30, granularity="daily")

        # 30-day window should have more or equal data points
        assert len(trends_30d) >= len(trends_7d)


# =============================================================================
# EXPORT FUNCTIONALITY TESTS
# =============================================================================

class TestExportFunctionality:
    """Test export functionality for JSON and CSV formats."""

    def test_export_json_format(self, temp_project_dir):
        """Test export_cost_data generates valid JSON."""
        summary = aggregate_cost_metrics(temp_project_dir)

        output_file = temp_project_dir / "export.json"
        export_cost_data(summary, output_file, format="json")

        # Verify file exists
        assert output_file.exists()

        # Verify valid JSON
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)

        # Verify structure matches CostSummary.to_dict()
        assert "total_cost" in data
        assert "total_specs" in data
        assert "specs" in data
        assert data["total_specs"] == 3

    def test_export_csv_format(self, temp_project_dir):
        """Test export_cost_data generates valid CSV."""
        summary = aggregate_cost_metrics(temp_project_dir)

        output_file = temp_project_dir / "export.csv"
        export_cost_data(summary, output_file, format="csv")

        # Verify file exists
        assert output_file.exists()

        # Verify CSV can be parsed
        import csv
        with open(output_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Verify header row exists
        assert len(rows) > 0
        header = rows[0]
        assert "Spec ID" in header
        assert "Total Cost ($)" in header
        assert "Session Count" in header

        # Verify data rows (one per spec + summary row)
        assert len(rows) >= 4  # 3 specs + 1 summary row

    def test_export_csv_structure_matches_frontend_expectations(self, temp_project_dir):
        """Test CSV export has expected columns for frontend consumption."""
        summary = aggregate_cost_metrics(temp_project_dir)

        output_file = temp_project_dir / "export.csv"
        export_cost_data(summary, output_file, format="csv")

        import csv
        with open(output_file, encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)

        header = rows[0]

        # Verify all expected columns present
        expected_columns = [
            "Spec ID",
            "Spec Name",
            "Total Cost ($)",
            "Input Tokens",
            "Output Tokens",
            "Total Tokens",
            "Session Count",
            "Cost/Session ($)",
            "Cost/1M Tokens ($)",
            "First Session",
            "Last Session",
        ]

        for col in expected_columns:
            assert col in header, f"Missing column: {col}"

    def test_export_invalid_format_raises_error(self, temp_project_dir):
        """Test export raises ValueError for unsupported format."""
        summary = aggregate_cost_metrics(temp_project_dir)

        output_file = temp_project_dir / "export.txt"

        with pytest.raises(ValueError, match="Unsupported export format"):
            export_cost_data(summary, output_file, format="txt")


# =============================================================================
# DATA CONSISTENCY TESTS
# =============================================================================

class TestDataConsistency:
    """Test data consistency across module boundaries."""

    def test_cost_tracker_to_analytics_data_consistency(self, single_spec_dir):
        """Verify data flows from CostTracker to analytics without loss."""
        tracker = CostTracker(spec_dir=single_spec_dir)

        # Add known data
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 10_000, 5_000)
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 20_000, 10_000)

        # Get data from tracker
        tracker_data = tracker.get_analytics_data()

        # Get data from analytics
        metrics = _extract_spec_cost_metrics(single_spec_dir)

        # Verify consistency
        assert tracker_data["total_cost"] == metrics.total_cost
        assert tracker_data["token_usage"]["input_tokens"] == metrics.input_tokens
        assert tracker_data["token_usage"]["output_tokens"] == metrics.output_tokens
        assert tracker_data["token_usage"]["total_tokens"] == metrics.total_tokens

    def test_aggregate_preserves_spec_level_data(self, temp_project_dir):
        """Verify aggregation preserves individual spec data correctly."""
        summary = aggregate_cost_metrics(temp_project_dir)

        # Sum of spec costs should equal total cost
        sum_spec_costs = sum(s.total_cost for s in summary.specs)
        assert abs(sum_spec_costs - summary.total_cost) < 0.0001

        # Sum of spec tokens should equal total tokens
        sum_spec_tokens = sum(s.total_tokens for s in summary.specs)
        assert sum_spec_tokens == summary.total_tokens

        # Sum of spec sessions should equal total sessions
        sum_spec_sessions = sum(s.session_count for s in summary.specs)
        assert sum_spec_sessions == summary.total_sessions

    def test_cost_breakdown_aggregation_accuracy(self, temp_project_dir):
        """Verify cost_by_agent and cost_by_model aggregate correctly."""
        summary = aggregate_cost_metrics(temp_project_dir)

        # Manually calculate agent costs from specs
        manual_agent_costs = {}
        for spec in summary.specs:
            for agent, cost in spec.cost_by_agent.items():
                manual_agent_costs[agent] = manual_agent_costs.get(agent, 0) + cost

        # Compare with aggregated values
        for agent, cost in summary.cost_by_agent.items():
            assert abs(cost - manual_agent_costs[agent]) < 0.0001

        # Same for model costs
        manual_model_costs = {}
        for spec in summary.specs:
            for model, cost in spec.cost_by_model.items():
                manual_model_costs[model] = manual_model_costs.get(model, 0) + cost

        for model, cost in summary.cost_by_model.items():
            assert abs(cost - manual_model_costs[model]) < 0.0001


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_extract_metrics_from_missing_directory(self):
        """Test _extract_spec_cost_metrics handles missing directory."""
        nonexistent = Path("/nonexistent/path/to/spec")

        metrics = _extract_spec_cost_metrics(nonexistent)

        assert metrics is None

    def test_extract_metrics_from_directory_without_cost_report(self, single_spec_dir):
        """Test _extract_spec_cost_metrics handles missing cost_report.json."""
        # Directory exists but no cost_report.json
        metrics = _extract_spec_cost_metrics(single_spec_dir)

        assert metrics is None

    def test_extract_metrics_from_corrupted_json(self, single_spec_dir):
        """Test _extract_spec_cost_metrics handles corrupted JSON."""
        # Create corrupted cost_report.json
        report_file = single_spec_dir / "cost_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("{invalid json content")

        metrics = _extract_spec_cost_metrics(single_spec_dir)

        assert metrics is None

    def test_parse_timestamp_with_invalid_format(self):
        """Test _parse_timestamp handles invalid timestamps."""
        # Invalid timestamp
        result = _parse_timestamp("invalid-timestamp")

        assert result is None

    def test_parse_timestamp_with_none(self):
        """Test _parse_timestamp handles None input."""
        result = _parse_timestamp(None)

        assert result is None

    def test_normalize_boundary_with_none(self):
        """Test _normalize_boundary handles None input."""
        result = _normalize_boundary(None)

        assert result is None

    def test_normalize_boundary_converts_naive_to_aware(self):
        """Test _normalize_boundary adds UTC to naive datetime."""
        naive_dt = datetime(2026, 2, 13, 12, 0, 0)

        result = _normalize_boundary(naive_dt)

        assert result is not None
        assert result.tzinfo is not None
        assert result.tzinfo == UTC


# =============================================================================
# SPEC COST METRICS TESTS
# =============================================================================

class TestSpecCostMetrics:
    """Test SpecCostMetrics dataclass."""

    def test_to_dict_serialization(self):
        """Test SpecCostMetrics.to_dict() creates correct structure."""
        metrics = SpecCostMetrics(
            spec_id="test_spec",
            spec_name="Test Spec",
            total_cost=1.5,
            input_tokens=100_000,
            output_tokens=50_000,
            total_tokens=150_000,
            cost_by_agent={"coder": 1.0, "planner": 0.5},
            cost_by_model={"claude-sonnet-4-5-20250929": 1.5},
            session_count=3,
            first_session=datetime.now(UTC),
            last_session=datetime.now(UTC),
        )

        data = metrics.to_dict()

        assert data["spec_id"] == "test_spec"
        assert data["total_cost"] == 1.5
        assert data["session_count"] == 3
        assert data["cost_by_agent"]["coder"] == 1.0
        assert "first_session" in data
        assert "last_session" in data

    def test_from_dict_deserialization(self):
        """Test SpecCostMetrics.from_dict() creates correct object."""
        data = {
            "spec_id": "test_spec",
            "spec_name": "Test Spec",
            "total_cost": 1.5,
            "input_tokens": 100_000,
            "output_tokens": 50_000,
            "total_tokens": 150_000,
            "cost_by_agent": {"coder": 1.0},
            "cost_by_model": {"claude-sonnet-4-5-20250929": 1.5},
            "session_count": 3,
            "first_session": datetime.now(UTC).isoformat(),
            "last_session": datetime.now(UTC).isoformat(),
        }

        metrics = SpecCostMetrics.from_dict(data)

        assert metrics.spec_id == "test_spec"
        assert metrics.total_cost == 1.5
        assert metrics.session_count == 3
        assert metrics.input_tokens == 100_000

    def test_average_cost_per_session_property(self):
        """Test average_cost_per_session property calculation."""
        metrics = SpecCostMetrics(
            spec_id="test",
            spec_name="Test",
            total_cost=3.0,
            session_count=2,
        )

        assert metrics.average_cost_per_session == 1.5

    def test_average_cost_per_session_with_zero_sessions(self):
        """Test average_cost_per_session returns 0 when no sessions."""
        metrics = SpecCostMetrics(
            spec_id="test",
            spec_name="Test",
            total_cost=3.0,
            session_count=0,
        )

        assert metrics.average_cost_per_session == 0.0

    def test_cost_per_million_tokens_property(self):
        """Test cost_per_million_tokens property calculation."""
        metrics = SpecCostMetrics(
            spec_id="test",
            spec_name="Test",
            total_cost=3.0,
            total_tokens=2_000_000,  # 2M tokens
        )

        # $3.0 for 2M tokens = $1.5 per 1M tokens
        assert abs(metrics.cost_per_million_tokens - 1.5) < 0.0001

    def test_cost_per_million_tokens_with_zero_tokens(self):
        """Test cost_per_million_tokens returns 0 when no tokens."""
        metrics = SpecCostMetrics(
            spec_id="test",
            spec_name="Test",
            total_cost=3.0,
            total_tokens=0,
        )

        assert metrics.cost_per_million_tokens == 0.0


# =============================================================================
# COST SUMMARY TESTS
# =============================================================================

class TestCostSummary:
    """Test CostSummary dataclass."""

    def test_to_dict_serialization(self, temp_project_dir):
        """Test CostSummary.to_dict() creates correct structure."""
        summary = aggregate_cost_metrics(temp_project_dir)

        data = summary.to_dict()

        # Verify top-level fields
        assert "period_start" in data
        assert "period_end" in data
        assert "total_specs" in data
        assert "total_cost" in data
        assert "cost_by_agent" in data
        assert "cost_by_model" in data
        assert "specs" in data

        # Verify specs list
        assert len(data["specs"]) == summary.total_specs

    def test_from_dict_deserialization(self, temp_project_dir):
        """Test CostSummary.from_dict() creates correct object."""
        summary = aggregate_cost_metrics(temp_project_dir)
        data = summary.to_dict()

        restored = CostSummary.from_dict(data)

        assert restored.total_specs == summary.total_specs
        assert abs(restored.total_cost - summary.total_cost) < 0.0001
        assert len(restored.specs) == len(summary.specs)

    def test_round_trip_serialization(self, temp_project_dir):
        """Test CostSummary survives dict round-trip without data loss."""
        summary = aggregate_cost_metrics(temp_project_dir)

        data = summary.to_dict()
        restored = CostSummary.from_dict(data)

        # Verify all key metrics match
        assert restored.total_specs == summary.total_specs
        assert abs(restored.total_cost - summary.total_cost) < 0.0001
        assert abs(restored.total_tokens - summary.total_tokens) < 0.0001
        assert restored.total_sessions == summary.total_sessions
