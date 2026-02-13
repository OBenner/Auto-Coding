"""
Unit Tests for Cost Tracking System

Tests the CostTracker class, UsageRecord dataclass, and related functionality.
Coverage ensures cost calculation accuracy, data persistence, and analytics generation.
"""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Import from backend modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from core.cost_tracking import (
    MODEL_PRICING,
    CostTracker,
    UsageRecord,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def temp_spec_dir():
    """Create a temporary spec directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir) / "specs" / "test_spec"
        spec_dir.mkdir(parents=True)
        yield spec_dir


@pytest.fixture
def tracker(temp_spec_dir):
    """Create a CostTracker instance with temp directory."""
    return CostTracker(spec_dir=temp_spec_dir)


@pytest.fixture
def sample_record():
    """Create a sample UsageRecord for testing."""
    return UsageRecord(
        agent_type="coder",
        model="claude-sonnet-4-5-20250929",
        input_tokens=5000,
        output_tokens=2000,
        cost=0.045,  # Pre-calculated: 5k * $3 + 2k * $15 per 1M tokens
        timestamp=datetime.now(UTC).isoformat() + "Z",
    )


# =============================================================================
# USAGE RECORD TESTS
# =============================================================================

class TestUsageRecord:
    """Test UsageRecord dataclass functionality."""

    def test_to_dict(self, sample_record):
        """Test UsageRecord converts to dict correctly."""
        data = sample_record.to_dict()

        assert data["agent_type"] == "coder"
        assert data["model"] == "claude-sonnet-4-5-20250929"
        assert data["input_tokens"] == 5000
        assert data["output_tokens"] == 2000
        assert data["cost"] == 0.045
        assert "timestamp" in data

    def test_from_dict(self, sample_record):
        """Test UsageRecord creates from dict correctly."""
        data = sample_record.to_dict()
        restored = UsageRecord.from_dict(data)

        assert restored.agent_type == sample_record.agent_type
        assert restored.model == sample_record.model
        assert restored.input_tokens == sample_record.input_tokens
        assert restored.output_tokens == sample_record.output_tokens
        assert restored.cost == sample_record.cost
        assert restored.timestamp == sample_record.timestamp

    def test_round_trip_serialization(self, sample_record):
        """Test UsageRecord survives dict round-trip."""
        data = sample_record.to_dict()
        restored = UsageRecord.from_dict(data)

        # Check all fields match
        assert restored.agent_type == sample_record.agent_type
        assert restored.model == sample_record.model
        assert restored.input_tokens == sample_record.input_tokens
        assert restored.output_tokens == sample_record.output_tokens
        assert restored.cost == sample_record.cost


# =============================================================================
# COST TRACKER INITIALIZATION TESTS
# =============================================================================

class TestCostTrackerInit:
    """Test CostTracker initialization and setup."""

    def test_initialization_creates_report_file_path(self, tracker):
        """Test CostTracker sets _report_file correctly."""
        assert tracker._report_file == tracker.spec_dir / "cost_report.json"

    def test_initialization_loads_existing_records(self, temp_spec_dir):
        """Test CostTracker loads existing records on init."""
        # Create a pre-existing cost_report.json
        report_file = temp_spec_dir / "cost_report.json"
        sample_data = {
            "spec_dir": str(temp_spec_dir),
            "total_cost": 0.045,
            "records": [
                {
                    "agent_type": "coder",
                    "model": "claude-sonnet-4-5-20250929",
                    "input_tokens": 5000,
                    "output_tokens": 2000,
                    "cost": 0.045,
                    "timestamp": datetime.now(UTC).isoformat() + "Z",
                }
            ],
            "last_updated": datetime.now(UTC).isoformat() + "Z",
        }

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(sample_data, f)

        # Create tracker - should load existing record
        tracker = CostTracker(spec_dir=temp_spec_dir)
        assert len(tracker.records) == 1
        assert tracker.records[0].agent_type == "coder"
        assert tracker.records[0].cost == 0.045

    def test_initialization_with_empty_directory(self, temp_spec_dir):
        """Test CostTracker starts with empty records when no file exists."""
        tracker = CostTracker(spec_dir=temp_spec_dir)
        assert len(tracker.records) == 0
        assert tracker.get_total_cost() == 0.0

    def test_initialization_handles_corrupted_json(self, temp_spec_dir):
        """Test CostTracker handles corrupted JSON gracefully."""
        # Create corrupted JSON file
        report_file = temp_spec_dir / "cost_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("{invalid json content")

        # Should start fresh without crashing
        tracker = CostTracker(spec_dir=temp_spec_dir)
        assert len(tracker.records) == 0


# =============================================================================
# COST CALCULATION TESTS
# =============================================================================

class TestCostCalculation:
    """Test cost calculation accuracy."""

    def test_calculate_cost_sonnet(self, tracker):
        """Test cost calculation for claude-sonnet-4-5-20250929."""
        # Sonnet: $3 input, $15 output per 1M tokens
        cost = tracker.calculate_cost(
            model="claude-sonnet-4-5-20250929",
            input_tokens=5_000,
            output_tokens=2_000,
        )

        expected = (5_000 / 1_000_000) * 3.0 + (2_000 / 1_000_000) * 15.0
        assert abs(cost - expected) < 0.0001  # Allow for floating point error
        assert abs(cost - 0.045) < 0.0001

    def test_calculate_cost_opus(self, tracker):
        """Test cost calculation for claude-opus-4-5-20251101."""
        # Opus: $15 input, $75 output per 1M tokens
        cost = tracker.calculate_cost(
            model="claude-opus-4-5-20251101",
            input_tokens=10_000,
            output_tokens=5_000,
        )

        expected = (10_000 / 1_000_000) * 15.0 + (5_000 / 1_000_000) * 75.0
        assert abs(cost - expected) < 0.0001
        assert abs(cost - 0.525) < 0.0001

    def test_calculate_cost_haiku(self, tracker):
        """Test cost calculation for claude-haiku-4-5-20251001."""
        # Haiku: $0.80 input, $4 output per 1M tokens
        cost = tracker.calculate_cost(
            model="claude-haiku-4-5-20251001",
            input_tokens=100_000,
            output_tokens=50_000,
        )

        expected = (100_000 / 1_000_000) * 0.8 + (50_000 / 1_000_000) * 4.0
        assert abs(cost - expected) < 0.0001
        assert abs(cost - 0.28) < 0.0001

    def test_calculate_cost_unknown_model_uses_default(self, tracker):
        """Test unknown models use default pricing (sonnet pricing)."""
        cost = tracker.calculate_cost(
            model="unknown-model-v1",
            input_tokens=5_000,
            output_tokens=2_000,
        )

        # Should use default pricing (sonnet)
        expected = (5_000 / 1_000_000) * 3.0 + (2_000 / 1_000_000) * 15.0
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_with_zero_tokens(self, tracker):
        """Test cost calculation with zero tokens."""
        cost = tracker.calculate_cost(
            model="claude-sonnet-4-5-20250929",
            input_tokens=0,
            output_tokens=0,
        )

        assert cost == 0.0

    def test_model_pricing_configuration_completeness(self):
        """Test all known models have pricing configured."""
        required_models = [
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-5-20250929",
            "claude-haiku-4-5-20251001",
            "claude-sonnet-4-5-20250929-thinking",
            "claude-opus-4-5-20251101-thinking",
        ]

        for model in required_models:
            assert model in MODEL_PRICING, f"Model {model} missing from pricing"
            assert "input" in MODEL_PRICING[model], f"Model {model} missing input price"
            assert "output" in MODEL_PRICING[model], f"Model {model} missing output price"
            assert MODEL_PRICING[model]["input"] > 0, f"Model {model} has zero input price"
            assert MODEL_PRICING[model]["output"] > 0, f"Model {model} has zero output price"


# =============================================================================
# USAGE LOGGING TESTS
# =============================================================================

class TestUsageLogging:
    """Test usage logging functionality."""

    def test_log_usage_saves_record(self, tracker):
        """Test log_usage creates and saves a record."""
        cost = tracker.log_usage(
            agent_type="coder",
            model="claude-sonnet-4-5-20250929",
            input_tokens=5000,
            output_tokens=2000,
        )

        assert len(tracker.records) == 1
        assert tracker.records[0].agent_type == "coder"
        assert tracker.records[0].model == "claude-sonnet-4-5-20250929"
        assert tracker.records[0].input_tokens == 5000
        assert tracker.records[0].output_tokens == 2000
        assert abs(cost - 0.045) < 0.0001

    def test_log_usage_persists_to_file(self, tracker, temp_spec_dir):
        """Test log_usage saves to cost_report.json."""
        tracker.log_usage(
            agent_type="coder",
            model="claude-sonnet-4-5-20250929",
            input_tokens=5000,
            output_tokens=2000,
        )

        # Verify file was created
        report_file = temp_spec_dir / "cost_report.json"
        assert report_file.exists()

        # Verify file contents
        with open(report_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["total_cost"] > 0
        assert len(data["records"]) == 1
        assert data["records"][0]["agent_type"] == "coder"

    def test_log_session_usage_convenience_method(self, tracker):
        """Test log_session_usage extracts tokens from metadata dict."""
        cost = tracker.log_session_usage(
            agent_type="planner",
            model="claude-sonnet-4-5-20250929",
            usage_metadata={
                "input_tokens": 10_000,
                "output_tokens": 5_000,
            },
        )

        assert len(tracker.records) == 1
        assert tracker.records[0].agent_type == "planner"
        assert tracker.records[0].input_tokens == 10_000
        assert tracker.records[0].output_tokens == 5_000
        assert abs(cost - 0.105) < 0.0001  # 10k * $3 + 5k * $15 per 1M

    def test_log_session_usage_handles_missing_tokens(self, tracker):
        """Test log_session_usage handles missing token keys gracefully."""
        cost = tracker.log_session_usage(
            agent_type="coder",
            model="claude-sonnet-4-5-20250929",
            usage_metadata={},  # Missing token keys
        )

        assert len(tracker.records) == 1
        assert tracker.records[0].input_tokens == 0
        assert tracker.records[0].output_tokens == 0
        assert cost == 0.0

    def test_multiple_records_accumulate(self, tracker):
        """Test multiple log_usage calls accumulate records."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("planner", "claude-opus-4-5-20251101", 10000, 5000)
        tracker.log_usage("qa_reviewer", "claude-haiku-4-5-20251001", 100000, 50000)

        assert len(tracker.records) == 3


# =============================================================================
# RECORD SAVING AND LOADING TESTS
# =============================================================================

class TestRecordPersistence:
    """Test JSON persistence functionality."""

    def test_save_records_creates_directory(self):
        """Test _save_records creates spec directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            non_existent_dir = Path(tmpdir) / "non_existent" / "path"
            tracker = CostTracker(spec_dir=non_existent_dir)

            # Should not crash - creates directory
            tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 1000, 500)

            assert non_existent_dir.exists()

    def test_save_records_valid_json_format(self, tracker, temp_spec_dir):
        """Test saved JSON has correct format and fields."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        report_file = temp_spec_dir / "cost_report.json"
        with open(report_file, encoding="utf-8") as f:
            data = json.load(f)

        # Verify required fields
        assert "spec_dir" in data
        assert "total_cost" in data
        assert "records" in data
        assert "last_updated" in data

        # Verify timestamp format
        assert data["last_updated"].endswith("Z")

    def test_load_records_restores_state(self, temp_spec_dir):
        """Test loading records restores tracker state."""
        # Create tracker and add record
        tracker1 = CostTracker(spec_dir=temp_spec_dir)
        tracker1.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        # Create new tracker instance - should load saved records
        tracker2 = CostTracker(spec_dir=temp_spec_dir)

        assert len(tracker2.records) == 1
        assert tracker2.records[0].agent_type == "coder"
        assert abs(tracker2.get_total_cost() - 0.045) < 0.0001


# =============================================================================
# COST SUMMARY TESTS
# =============================================================================

class TestCostSummary:
    """Test get_cost_summary() functionality."""

    def test_cost_summary_with_no_records(self, tracker):
        """Test cost summary with no usage recorded."""
        summary = tracker.get_cost_summary()
        assert summary == "No usage recorded yet."

    def test_cost_summary_format(self, tracker):
        """Test cost summary has correct format and sections."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10000, 5000)

        summary = tracker.get_cost_summary()

        # Verify key sections present
        assert "COST SUMMARY" in summary
        assert "Total Cost:" in summary
        assert "Cost by Agent Type:" in summary
        assert "Cost by Model:" in summary
        assert "Token Usage:" in summary

        # Verify separators
        assert "=" in summary
        assert "-" in summary

    def test_cost_summary_shows_totals(self, tracker):
        """Test cost summary displays total cost correctly."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        summary = tracker.get_cost_summary()
        assert "$0.0450" in summary or "$0.045" in summary

    def test_cost_summary_breakdown_by_agent(self, tracker):
        """Test cost summary shows breakdown by agent type."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10000, 5000)

        summary = tracker.get_cost_summary()

        # Should show both agent types
        assert "coder" in summary.lower()
        assert "planner" in summary.lower()

    def test_cost_summary_breakdown_by_model(self, tracker):
        """Test cost summary shows breakdown by model."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("coder", "claude-opus-4-5-20251101", 10000, 5000)

        summary = tracker.get_cost_summary()

        # Should show both models (shortened names)
        assert "opus-4-5" in summary
        assert "sonnet-4-5" in summary

    def test_cost_summary_shows_percentages(self, tracker):
        """Test cost summary includes percentage breakdowns."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10000, 5000)

        summary = tracker.get_cost_summary()

        # Should contain percentage signs
        assert "%" in summary

    def test_cost_summary_shows_token_usage(self, tracker):
        """Test cost summary includes token statistics."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        summary = tracker.get_cost_summary()

        # Should show token counts
        assert "Input Tokens:" in summary
        assert "Output Tokens:" in summary
        assert "Total Tokens:" in summary
        assert "5,000" in summary or "5000" in summary


# =============================================================================
# ANALYTICS DATA TESTS
# =============================================================================

class TestAnalyticsData:
    """Test get_analytics_data() functionality."""

    def test_analytics_data_structure(self, tracker):
        """Test analytics data has correct structure."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        data = tracker.get_analytics_data()

        # Verify top-level keys
        assert "total_cost" in data
        assert "cost_by_agent" in data
        assert "cost_by_model" in data
        assert "token_usage" in data
        assert "timeline" in data
        assert "record_count" in data

    def test_analytics_data_total_cost(self, tracker):
        """Test analytics data includes total cost."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        data = tracker.get_analytics_data()
        assert abs(data["total_cost"] - 0.045) < 0.0001

    def test_analytics_data_cost_by_agent(self, tracker):
        """Test analytics data breaks down by agent type."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10000, 5000)

        data = tracker.get_analytics_data()

        assert "coder" in data["cost_by_agent"]
        assert "planner" in data["cost_by_agent"]
        assert abs(data["cost_by_agent"]["coder"] - 0.045) < 0.0001
        assert abs(data["cost_by_agent"]["planner"] - 0.105) < 0.0001

    def test_analytics_data_cost_by_model(self, tracker):
        """Test analytics data breaks down by model."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("coder", "claude-opus-4-5-20251101", 10000, 5000)

        data = tracker.get_analytics_data()

        assert "claude-sonnet-4-5-20250929" in data["cost_by_model"]
        assert "claude-opus-4-5-20251101" in data["cost_by_model"]

    def test_analytics_data_token_usage(self, tracker):
        """Test analytics data includes token statistics."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        data = tracker.get_analytics_data()

        assert data["token_usage"]["input_tokens"] == 5000
        assert data["token_usage"]["output_tokens"] == 2000
        assert data["token_usage"]["total_tokens"] == 7000

    def test_analytics_data_timeline(self, tracker):
        """Test analytics data includes timeline of records."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        data = tracker.get_analytics_data()

        assert len(data["timeline"]) == 1
        assert data["timeline"][0]["agent_type"] == "coder"
        assert data["timeline"][0]["model"] == "claude-sonnet-4-5-20250929"
        assert data["timeline"][0]["input_tokens"] == 5000
        assert data["timeline"][0]["output_tokens"] == 2000
        assert "timestamp" in data["timeline"][0]

    def test_analytics_data_record_count(self, tracker):
        """Test analytics data includes record count."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10000, 5000)

        data = tracker.get_analytics_data()
        assert data["record_count"] == 2


# =============================================================================
# FILTERING TESTS
# =============================================================================

class TestRecordFiltering:
    """Test get_records_by_agent() and get_records_by_model() filtering."""

    def test_get_records_by_agent(self, tracker):
        """Test filtering records by agent type."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10000, 5000)
        tracker.log_usage("coder", "claude-opus-4-5-20251101", 10000, 5000)

        coder_records = tracker.get_records_by_agent("coder")

        assert len(coder_records) == 2
        assert all(r.agent_type == "coder" for r in coder_records)

    def test_get_records_by_agent_no_matches(self, tracker):
        """Test filtering by agent with no matching records."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        planner_records = tracker.get_records_by_agent("planner")

        assert len(planner_records) == 0

    def test_get_records_by_model(self, tracker):
        """Test filtering records by model."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("coder", "claude-opus-4-5-20251101", 10000, 5000)
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10000, 5000)

        sonnet_records = tracker.get_records_by_model("claude-sonnet-4-5-20250929")

        assert len(sonnet_records) == 2
        assert all(r.model == "claude-sonnet-4-5-20250929" for r in sonnet_records)

    def test_get_records_by_model_no_matches(self, tracker):
        """Test filtering by model with no matching records."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        opus_records = tracker.get_records_by_model("claude-opus-4-5-20251101")

        assert len(opus_records) == 0


# =============================================================================
# TOTAL COST TESTS
# =============================================================================

class TestTotalCost:
    """Test get_total_cost() functionality."""

    def test_get_total_cost_empty(self, tracker):
        """Test total cost is zero with no records."""
        assert tracker.get_total_cost() == 0.0

    def test_get_total_cost_single_record(self, tracker):
        """Test total cost with single record."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        total = tracker.get_total_cost()
        assert abs(total - 0.045) < 0.0001

    def test_get_total_cost_multiple_records(self, tracker):
        """Test total cost accumulates across records."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)  # $0.045
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10000, 5000)  # $0.105

        total = tracker.get_total_cost()
        assert abs(total - 0.15) < 0.0001

    def test_get_total_cost_different_models(self, tracker):
        """Test total cost across different models."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)  # $0.045
        tracker.log_usage("coder", "claude-opus-4-5-20251101", 10000, 5000)  # $0.525

        total = tracker.get_total_cost()
        assert abs(total - 0.57) < 0.0001


# =============================================================================
# TOKEN USAGE TESTS
# =============================================================================

class TestTokenUsage:
    """Test get_token_usage() functionality."""

    def test_get_token_usage_empty(self, tracker):
        """Test token usage is zero with no records."""
        usage = tracker.get_token_usage()

        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0
        assert usage["total_tokens"] == 0

    def test_get_token_usage_single_record(self, tracker):
        """Test token usage with single record."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        usage = tracker.get_token_usage()

        assert usage["input_tokens"] == 5000
        assert usage["output_tokens"] == 2000
        assert usage["total_tokens"] == 7000

    def test_get_token_usage_multiple_records(self, tracker):
        """Test token usage aggregates across records."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10000, 5000)

        usage = tracker.get_token_usage()

        assert usage["input_tokens"] == 15000
        assert usage["output_tokens"] == 7000
        assert usage["total_tokens"] == 22000


# =============================================================================
# COST BREAKDOWN TESTS
# =============================================================================

class TestCostBreakdown:
    """Test get_cost_by_agent() and get_cost_by_model() functionality."""

    def test_get_cost_by_agent_single_agent(self, tracker):
        """Test cost breakdown by agent with one agent type."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        costs = tracker.get_cost_by_agent()

        assert len(costs) == 1
        assert "coder" in costs
        assert abs(costs["coder"] - 0.045) < 0.0001

    def test_get_cost_by_agent_multiple_agents(self, tracker):
        """Test cost breakdown by agent with multiple types."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("planner", "claude-sonnet-4-5-20250929", 10000, 5000)
        tracker.log_usage("qa_reviewer", "claude-haiku-4-5-20251001", 100000, 50000)

        costs = tracker.get_cost_by_agent()

        assert len(costs) == 3
        assert "coder" in costs
        assert "planner" in costs
        assert "qa_reviewer" in costs

    def test_get_cost_by_model_single_model(self, tracker):
        """Test cost breakdown by model with one model."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)

        costs = tracker.get_cost_by_model()

        assert len(costs) == 1
        assert "claude-sonnet-4-5-20250929" in costs
        assert abs(costs["claude-sonnet-4-5-20250929"] - 0.045) < 0.0001

    def test_get_cost_by_model_multiple_models(self, tracker):
        """Test cost breakdown by model with multiple models."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("coder", "claude-opus-4-5-20251101", 10000, 5000)
        tracker.log_usage("planner", "claude-haiku-4-5-20251001", 100000, 50000)

        costs = tracker.get_cost_by_model()

        assert len(costs) == 3
        assert "claude-sonnet-4-5-20250929" in costs
        assert "claude-opus-4-5-20251101" in costs
        assert "claude-haiku-4-5-20251001" in costs


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_log_usage_with_negative_tokens(self, tracker):
        """Test handling of negative token counts (should still work)."""
        # This tests robustness - negative tokens shouldn't crash
        cost = tracker.log_usage("coder", "claude-sonnet-4-5-20250929", -100, -50)

        # Should create a record (even if mathematically odd)
        assert len(tracker.records) == 1
        assert cost < 0  # Negative cost from negative tokens

    def test_cost_calculation_accuracy_edge_cases(self, tracker):
        """Test cost calculation with edge case token counts."""
        # Very small numbers
        cost1 = tracker.calculate_cost("claude-sonnet-4-5-20250929", 1, 1)
        assert cost1 > 0

        # Very large numbers
        cost2 = tracker.calculate_cost("claude-sonnet-4-5-20250929", 10_000_000, 5_000_000)
        assert cost2 > 0

    def test_multiple_agents_same_type_accumulate(self, tracker):
        """Test multiple sessions with same agent type accumulate correctly."""
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2000)
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 10000, 5000)

        costs = tracker.get_cost_by_agent()
        assert abs(costs["coder"] - 0.15) < 0.0001

    def test_cost_summary_sorting(self, tracker):
        """Test cost summary sorts by cost (highest first)."""
        tracker.log_usage("agent_a", "claude-sonnet-4-5-20250929", 1000, 500)   # ~$0.0105
        tracker.log_usage("agent_b", "claude-sonnet-4-5-20250929", 10000, 5000) # ~$0.105
        tracker.log_usage("agent_c", "claude-sonnet-4-5-20250929", 5000, 2000)   # ~$0.045

        summary = tracker.get_cost_summary()

        # Extract agent lines ( crude parsing for testing)
        lines = summary.split("\n")
        agent_lines = [l for l in lines if "agent_" in l]

        # agent_b should appear before agent_a (higher cost)
        agent_b_idx = next(i for i, l in enumerate(agent_lines) if "agent_b" in l)
        agent_a_idx = next(i for i, l in enumerate(agent_lines) if "agent_a" in l)

        assert agent_b_idx < agent_a_idx, "Should be sorted by cost descending"
