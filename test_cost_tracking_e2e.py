#!/usr/bin/env python3
"""
End-to-End Test for Cost Tracking System
==========================================

Tests the complete cost tracking flow:
1. Simulate agent session cost tracking
2. Verify cost data saved to spec directory
3. Test cost_analytics.py CLI commands
4. Test time range filtering
5. Test export functionality (JSON and CSV)

This test verifies the integration between:
- CostTracker (core/cost_tracking.py)
- Session cost logging (agents/session.py)
- Cost analytics (analysis/cost_analytics.py)
"""

import json
import shutil
import tempfile
from datetime import datetime, timedelta, UTC
from pathlib import Path

# Import the modules we're testing
import sys
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from core.cost_tracking import CostTracker, MODEL_PRICING


def test_1_cost_tracker_saves_data():
    """Test 1: Verify CostTracker saves cost data to spec directory."""
    print("\n" + "=" * 70)
    print("TEST 1: Cost Tracker Saves Data to Spec Directory")
    print("=" * 70)

    # Create temporary spec directory
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir)

        # Create tracker and log some usage
        tracker = CostTracker(spec_dir=spec_dir)

        # Simulate agent sessions (mimicking what session.py does)
        cost1 = tracker.log_session_usage(
            agent_type="planner",
            model="claude-sonnet-4-5-20250929",
            usage_metadata={"input_tokens": 10000, "output_tokens": 5000}
        )
        print(f"✓ Logged planner session: ${cost1:.4f}")

        cost2 = tracker.log_session_usage(
            agent_type="coder",
            model="claude-sonnet-4-5-20250929",
            usage_metadata={"input_tokens": 50000, "output_tokens": 20000}
        )
        print(f"✓ Logged coder session: ${cost2:.4f}")

        cost3 = tracker.log_session_usage(
            agent_type="qa_reviewer",
            model="claude-opus-4-5-20251101",
            usage_metadata={"input_tokens": 15000, "output_tokens": 3000}
        )
        print(f"✓ Logged qa_reviewer session: ${cost3:.4f}")

        # Verify cost_report.json exists
        cost_report_file = spec_dir / "cost_report.json"
        assert cost_report_file.exists(), "cost_report.json not created!"

        # Load and verify contents
        with open(cost_report_file) as f:
            data = json.load(f)

        assert "records" in data, "No records in cost_report.json"
        assert len(data["records"]) == 3, f"Expected 3 records, got {len(data['records'])}"
        assert data["total_cost"] > 0, "Total cost should be > 0"

        print(f"✓ cost_report.json created with {len(data['records'])} records")
        print(f"✓ Total cost: ${data['total_cost']:.4f}")
        print(f"✓ File location: {cost_report_file}")

        # Test get_cost_summary()
        summary = tracker.get_cost_summary()
        assert "Total Cost:" in summary, "Summary missing total cost"
        assert "planner" in summary, "Summary missing planner"
        assert "coder" in summary, "Summary missing coder"
        print("\n" + summary)

        return True


def test_2_cost_calculation_accuracy():
    """Test 2: Verify cost calculations are accurate."""
    print("\n" + "=" * 70)
    print("TEST 2: Cost Calculation Accuracy")
    print("=" * 70)

    # Test known calculations for claude-sonnet-4-5-20250929
    # Pricing: input $3.00/1M, output $15.00/1M
    model = "claude-sonnet-4-5-20250929"
    input_tokens = 1_000_000  # 1M input tokens
    output_tokens = 1_000_000  # 1M output tokens

    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = CostTracker(spec_dir=Path(tmpdir))
        cost = tracker.calculate_cost(model, input_tokens, output_tokens)

        # Expected: $3.00 + $15.00 = $18.00
        expected_cost = 3.00 + 15.00
        assert abs(cost - expected_cost) < 0.0001, f"Cost mismatch: {cost} vs {expected_cost}"
        print(f"✓ 1M input + 1M output tokens = ${cost:.2f} (expected ${expected_cost:.2f})")

        # Test partial million
        input_tokens = 500_000  # 0.5M
        output_tokens = 250_000  # 0.25M
        cost = tracker.calculate_cost(model, input_tokens, output_tokens)

        # Expected: $1.50 + $3.75 = $5.25
        expected_cost = 1.50 + 3.75
        assert abs(cost - expected_cost) < 0.0001, f"Cost mismatch: {cost} vs {expected_cost}"
        print(f"✓ 500K input + 250K output tokens = ${cost:.2f} (expected ${expected_cost:.2f})")

    return True


def test_3_analytics_aggregation():
    """Test 3: Verify cost_analytics.py can aggregate data."""
    print("\n" + "=" * 70)
    print("TEST 3: Cost Analytics Aggregation")
    print("=" * 70)

    try:
        from analysis.cost_analytics import aggregate_cost_metrics, SpecCostMetrics

        # Use current project directory
        project_dir = Path.cwd()

        # Aggregate all cost data
        summary = aggregate_cost_metrics(project_dir)

        print(f"✓ Aggregated data from {summary.total_specs} specs")
        print(f"✓ Total sessions: {summary.total_sessions}")
        print(f"✓ Total cost: ${summary.total_cost:.4f}")
        print(f"✓ Total tokens: {summary.total_tokens:,}")

        if summary.total_specs > 0:
            print("\nCost by Agent Type:")
            for agent, cost in sorted(summary.cost_by_agent.items(), key=lambda x: -x[1]):
                percentage = (cost / summary.total_cost * 100) if summary.total_cost > 0 else 0
                print(f"  {agent:20s} ${cost:7.4f} ({percentage:5.1f}%)")

            print("\nCost by Model:")
            for model, cost in sorted(summary.cost_by_model.items(), key=lambda x: -x[1]):
                percentage = (cost / summary.total_cost * 100) if summary.total_cost > 0 else 0
                model_short = model.replace("claude-", "").replace("-20250929", "").replace("-20251001", "").replace("-20251101", "")
                print(f"  {model_short:20s} ${cost:7.4f} ({percentage:5.1f}%)")

        return True
    except Exception as e:
        print(f"✗ Analytics aggregation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_time_range_filtering():
    """Test 4: Verify time range filtering works."""
    print("\n" + "=" * 70)
    print("TEST 4: Time Range Filtering")
    print("=" * 70)

    try:
        from analysis.cost_analytics import aggregate_cost_metrics
        from datetime import timedelta

        project_dir = Path.cwd()

        # Test 1: Last 7 days
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=7)

        summary_7d = aggregate_cost_metrics(project_dir, start_date, end_date)
        print(f"✓ Last 7 days: {summary_7d.total_specs} specs, ${summary_7d.total_cost:.4f}")

        # Test 2: Last 30 days
        start_date = end_date - timedelta(days=30)
        summary_30d = aggregate_cost_metrics(project_dir, start_date, end_date)
        print(f"✓ Last 30 days: {summary_30d.total_specs} specs, ${summary_30d.total_cost:.4f}")

        # Test 3: All time (no filter)
        summary_all = aggregate_cost_metrics(project_dir)
        print(f"✓ All time: {summary_all.total_specs} specs, ${summary_all.total_cost:.4f}")

        # Verify filtering works (all should include 7d data)
        assert summary_30d.total_cost >= summary_7d.total_cost, "30d cost should be >= 7d"
        assert summary_all.total_cost >= summary_30d.total_cost, "All time cost should be >= 30d"
        print("✓ Time range filtering works correctly")

        return True
    except Exception as e:
        print(f"✗ Time range filtering failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_export_functionality():
    """Test 5: Verify export functionality (JSON and CSV)."""
    print("\n" + "=" * 70)
    print("TEST 5: Export Functionality (JSON and CSV)")
    print("=" * 70)

    try:
        from analysis.cost_analytics import aggregate_cost_metrics, export_cost_data
        from datetime import timedelta

        project_dir = Path.cwd()
        summary = aggregate_cost_metrics(project_dir)

        # Create temp directory for exports
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)

            # Test JSON export
            json_file = export_dir / "cost_export.json"
            export_cost_data(summary, json_file, format="json")
            assert json_file.exists(), "JSON export file not created"

            with open(json_file) as f:
                json_data = json.load(f)
            assert "total_cost" in json_data, "JSON export missing total_cost"
            assert "specs" in json_data, "JSON export missing specs"
            print(f"✓ JSON export created: {json_file.name}")
            print(f"  - Total cost: ${json_data['total_cost']:.4f}")
            print(f"  - Specs: {json_data['total_specs']}")

            # Test CSV export
            csv_file = export_dir / "cost_export.csv"
            export_cost_data(summary, csv_file, format="csv")
            assert csv_file.exists(), "CSV export file not created"

            with open(csv_file) as f:
                csv_content = f.read()
            assert "Spec ID" in csv_content, "CSV missing header"
            assert "Total Cost ($)" in csv_content, "CSV missing cost column"
            print(f"✓ CSV export created: {csv_file.name}")
            print(f"  - Rows: {len(csv_content.splitlines())}")

        return True
    except Exception as e:
        print(f"✗ Export functionality failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_get_analytics_data():
    """Test 6: Verify CostTracker.get_analytics_data() returns proper format."""
    print("\n" + "=" * 70)
    print("TEST 6: CostTracker.get_analytics_data() Format")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmpdir:
        spec_dir = Path(tmpdir)
        tracker = CostTracker(spec_dir=spec_dir)

        # Log some test data
        tracker.log_session_usage(
            agent_type="coder",
            model="claude-sonnet-4-5-20250929",
            usage_metadata={"input_tokens": 10000, "output_tokens": 5000}
        )
        tracker.log_session_usage(
            agent_type="planner",
            model="claude-haiku-4-5-20251001",
            usage_metadata={"input_tokens": 5000, "output_tokens": 2000}
        )

        # Get analytics data
        analytics = tracker.get_analytics_data()

        # Verify structure
        assert "total_cost" in analytics, "Missing total_cost"
        assert "cost_by_agent" in analytics, "Missing cost_by_agent"
        assert "cost_by_model" in analytics, "Missing cost_by_model"
        assert "token_usage" in analytics, "Missing token_usage"
        assert "timeline" in analytics, "Missing timeline"
        assert "record_count" in analytics, "Missing record_count"

        print(f"✓ Analytics data structure verified")
        print(f"  - total_cost: ${analytics['total_cost']:.4f}")
        print(f"  - cost_by_agent: {list(analytics['cost_by_agent'].keys())}")
        print(f"  - cost_by_model: {list(analytics['cost_by_model'].keys())}")
        print(f"  - token_usage: {analytics['token_usage']}")
        print(f"  - timeline entries: {len(analytics['timeline'])}")
        print(f"  - record_count: {analytics['record_count']}")

        # Verify timeline structure
        if analytics['timeline']:
            timeline_entry = analytics['timeline'][0]
            assert "timestamp" in timeline_entry, "Timeline missing timestamp"
            assert "agent_type" in timeline_entry, "Timeline missing agent_type"
            assert "model" in timeline_entry, "Timeline missing model"
            assert "cost" in timeline_entry, "Timeline missing cost"
            assert "input_tokens" in timeline_entry, "Timeline missing input_tokens"
            assert "output_tokens" in timeline_entry, "Timeline missing output_tokens"
            print(f"✓ Timeline structure verified")

        return True


def test_7_model_pricing():
    """Test 7: Verify MODEL_PRICING has all expected models."""
    print("\n" + "=" * 70)
    print("TEST 7: Model Pricing Configuration")
    print("=" * 70)

    expected_models = [
        "claude-opus-4-5-20251101",
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",
        "default"
    ]

    for model in expected_models:
        assert model in MODEL_PRICING, f"Missing pricing for {model}"
        pricing = MODEL_PRICING[model]
        assert "input" in pricing, f"{model} missing input price"
        assert "output" in pricing, f"{model} missing output price"
        assert pricing["input"] > 0, f"{model} input price is 0"
        assert pricing["output"] > 0, f"{model} output price is 0"
        print(f"✓ {model:35s} In: ${pricing['input']:5.2f}/M  Out: ${pricing['output']:5.2f}/M")

    return True


def main():
    """Run all end-to-end tests."""
    print("\n" + "=" * 70)
    print("COST TRACKING END-TO-END TEST SUITE")
    print("=" * 70)
    print(f"Project directory: {Path.cwd()}")
    print(f"Test started at: {datetime.now().isoformat()}")

    tests = [
        ("Cost Tracker Saves Data", test_1_cost_tracker_saves_data),
        ("Cost Calculation Accuracy", test_2_cost_calculation_accuracy),
        ("Analytics Aggregation", test_3_analytics_aggregation),
        ("Time Range Filtering", test_4_time_range_filtering),
        ("Export Functionality", test_5_export_functionality),
        ("get_analytics_data() Format", test_6_get_analytics_data),
        ("Model Pricing Configuration", test_7_model_pricing),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"\n✗ {name} failed with exception: {e}")

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result, _ in results if result)
    total = len(results)

    for name, result, error in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")
        if error:
            print(f"         Error: {error}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
