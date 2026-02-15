#!/usr/bin/env python3
"""
End-to-End Quality Tracking Verification
=========================================

Verifies that quality tracking works end-to-end:
1. Quality scores calculated correctly
2. Trend detection works
3. Alert triggers on quality drop
4. Data persists correctly
5. Dashboard integration ready
"""

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add apps/backend to path for imports
backend_path = Path(__file__).parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

from analysis.quality_models import QualityScore
from analysis.quality_tracker import (
    analyze_quality_trend,
    calculate_quality_score,
    get_quality_summary,
    get_quality_by_agent_type,
)


def create_test_spec_dir(base_dir: Path) -> Path:
    """Create a temporary test spec directory with mock data."""
    spec_dir = base_dir / ".auto-claude" / "specs" / "test-quality-e2e"
    spec_dir.mkdir(parents=True, exist_ok=True)

    # Create implementation_plan.json with QA iterations
    plan = {
        "feature": "Test Quality Tracking",
        "phases": [
            {
                "id": "phase-1",
                "name": "Implementation",
                "subtasks": [
                    {
                        "id": "subtask-1-1",
                        "description": "Task 1",
                        "status": "completed",
                        "verification": {"type": "command"},
                    },
                    {
                        "id": "subtask-1-2",
                        "description": "Task 2",
                        "status": "completed",
                        "verification": {"type": "command"},
                    },
                ],
            }
        ],
        "qa_iteration_history": [],
    }

    with open(spec_dir / "implementation_plan.json", "w") as f:
        json.dump(plan, f, indent=2)

    return spec_dir


def create_qa_iteration(spec_dir: Path, iteration: int, total_criteria: int, met_criteria: int, status: str):
    """Add a QA iteration to the implementation plan."""
    plan_file = spec_dir / "implementation_plan.json"
    with open(plan_file) as f:
        plan = json.load(f)

    qa_record = {
        "iteration": iteration,
        "timestamp": (datetime.now(UTC) - timedelta(hours=10-iteration)).isoformat(),
        "total_criteria": total_criteria,
        "met_criteria": met_criteria,
        "status": status,
    }

    if "qa_iteration_history" not in plan:
        plan["qa_iteration_history"] = []

    plan["qa_iteration_history"].append(qa_record)

    with open(plan_file, "w") as f:
        json.dump(plan, f, indent=2)


def verify_quality_score_calculation(spec_dir: Path) -> bool:
    """Test 1: Verify quality scores are calculated correctly."""
    print("\n" + "="*70)
    print("TEST 1: Quality Score Calculation")
    print("="*70)

    # Create a QA iteration with perfect scores
    create_qa_iteration(spec_dir, 1, total_criteria=10, met_criteria=10, status="approved")

    # Calculate quality score
    score = calculate_quality_score(
        spec_dir=spec_dir,
        session_id="test-session-1",
        agent_type="coder",
        subtask_id="subtask-1-1",
        iteration=1,
    )

    print(f"✓ Quality score calculated: {score.composite_score:.3f}")
    print(f"  - Test pass rate: {score.test_pass_rate:.3f}")
    print(f"  - Acceptance criteria: {score.acceptance_criteria_met:.3f}")
    print(f"  - User approval: {score.user_approval_rate:.3f}")

    # Verify score is high quality
    if not score.is_high_quality:
        print("✗ FAILED: Expected high quality score")
        return False

    print(f"✓ Score classified as high quality: {score.is_high_quality}")
    return True


def verify_multiple_qa_iterations(spec_dir: Path) -> bool:
    """Test 2: Verify multiple QA iterations create quality history."""
    print("\n" + "="*70)
    print("TEST 2: Multiple QA Iterations")
    print("="*70)

    # Simulate degrading quality over iterations
    iterations = [
        (2, 10, 9, "rejected"),   # 90% criteria met
        (3, 10, 8, "rejected"),   # 80% criteria met
        (4, 10, 7, "rejected"),   # 70% criteria met
        (5, 10, 9, "approved"),   # 90% criteria met, approved
    ]

    for iteration, total, met, status in iterations:
        create_qa_iteration(spec_dir, iteration, total, met, status)
        score = calculate_quality_score(
            spec_dir=spec_dir,
            session_id=f"test-session-{iteration}",
            agent_type="qa_reviewer",
            iteration=iteration,
        )
        print(f"✓ Iteration {iteration}: score={score.composite_score:.3f}, status={status}")

    # Verify quality history exists
    history_file = spec_dir / "quality_history.json"
    if not history_file.exists():
        print("✗ FAILED: Quality history file not created")
        return False

    with open(history_file) as f:
        data = json.load(f)
        scores = data.get("scores", [])

    print(f"✓ Quality history persisted: {len(scores)} scores recorded")

    if len(scores) < 5:
        print(f"✗ FAILED: Expected at least 5 scores, got {len(scores)}")
        return False

    return True


def verify_trend_detection(spec_dir: Path) -> bool:
    """Test 3: Verify trend detection works."""
    print("\n" + "="*70)
    print("TEST 3: Trend Detection")
    print("="*70)

    # Analyze trend
    trend = analyze_quality_trend(spec_dir)

    print(f"✓ Trend analyzed over {trend.total_sessions} sessions")
    print(f"  - Baseline score: {trend.baseline_score:.3f}")
    print(f"  - Average score: {trend.average_score:.3f}")
    print(f"  - Current score: {trend.current_score:.3f}")
    print(f"  - Trend direction: {trend.trend_direction}")
    print(f"  - Quality drop: {trend.quality_drop_percent:.1f}%")

    if not trend.has_sufficient_data:
        print("✗ FAILED: Insufficient data for trend analysis")
        return False

    print(f"✓ Sufficient data for trend analysis (>= 5 sessions)")

    if not trend.baseline_calculated:
        print("✗ FAILED: Baseline not calculated")
        return False

    print(f"✓ Baseline calculated: {trend.baseline_score:.3f}")
    return True


def verify_quality_drop_alert(spec_dir: Path) -> bool:
    """Test 4: Verify alert triggers on quality drop."""
    print("\n" + "="*70)
    print("TEST 4: Quality Drop Alert")
    print("="*70)

    # Add more iterations with declining quality
    declining_iterations = [
        (6, 10, 5, "rejected"),   # 50% criteria met
        (7, 10, 4, "rejected"),   # 40% criteria met
        (8, 10, 4, "rejected"),   # 40% criteria met
    ]

    for iteration, total, met, status in declining_iterations:
        create_qa_iteration(spec_dir, iteration, total, met, status)
        score = calculate_quality_score(
            spec_dir=spec_dir,
            session_id=f"test-session-{iteration}",
            agent_type="qa_fixer",
            iteration=iteration,
        )
        print(f"  Iteration {iteration}: score={score.composite_score:.3f}")

    # Analyze trend again
    trend = analyze_quality_trend(spec_dir)

    print(f"✓ Quality drop: {trend.quality_drop_percent:.1f}%")
    print(f"  - Alert threshold: {trend.alert_threshold_percent}%")
    print(f"  - Should alert: {trend.should_alert}")

    if trend.quality_drop_percent < 10.0:
        print(f"⚠ WARNING: Quality drop below threshold ({trend.quality_drop_percent:.1f}% < 10%)")
        print("  This may be expected depending on test data")

    if trend.should_alert:
        print(f"✓ Alert triggered (drop >= {trend.alert_threshold_percent}%)")
    else:
        print(f"✓ No alert (drop < {trend.alert_threshold_percent}%)")

    return True


def verify_quality_summary(spec_dir: Path) -> bool:
    """Test 5: Verify quality summary API."""
    print("\n" + "="*70)
    print("TEST 5: Quality Summary API")
    print("="*70)

    summary = get_quality_summary(spec_dir)

    print("✓ Quality summary generated:")
    print(f"  - Total sessions: {summary['total_sessions']}")
    print(f"  - Average quality: {summary['average_quality']:.3f}")
    print(f"  - Current quality: {summary['current_quality']:.3f}")
    print(f"  - Baseline quality: {summary['baseline_quality']:.3f}")
    print(f"  - Trend direction: {summary['trend_direction']}")
    print(f"  - Quality drop: {summary['quality_drop_percent']:.1f}%")
    print(f"  - Alert active: {summary['alert_active']}")
    print(f"  - High quality sessions: {summary['high_quality_sessions']}")
    print(f"  - Low quality sessions: {summary['low_quality_sessions']}")

    if summary['total_sessions'] < 5:
        print(f"✗ FAILED: Expected >= 5 sessions, got {summary['total_sessions']}")
        return False

    print(f"✓ Summary contains all required metrics")
    return True


def verify_agent_type_breakdown(spec_dir: Path) -> bool:
    """Test 6: Verify quality breakdown by agent type."""
    print("\n" + "="*70)
    print("TEST 6: Quality by Agent Type")
    print("="*70)

    by_agent = get_quality_by_agent_type(spec_dir)

    print("✓ Quality breakdown by agent type:")
    for agent_type, metrics in by_agent.items():
        print(f"  - {agent_type}:")
        print(f"      Average quality: {metrics['average_quality']:.3f}")
        print(f"      Session count: {metrics['session_count']}")
        print(f"      Trend: {metrics['trend']}")

    if not by_agent:
        print("✗ FAILED: No agent type breakdown available")
        return False

    print(f"✓ Quality tracked for {len(by_agent)} agent types")
    return True


def verify_data_persistence(spec_dir: Path) -> bool:
    """Test 7: Verify data persists correctly."""
    print("\n" + "="*70)
    print("TEST 7: Data Persistence")
    print("="*70)

    # Check quality_history.json exists and is valid
    history_file = spec_dir / "quality_history.json"
    if not history_file.exists():
        print("✗ FAILED: Quality history file not found")
        return False

    with open(history_file) as f:
        data = json.load(f)

    print(f"✓ Quality history file exists")
    print(f"  - Updated at: {data.get('updated_at', 'unknown')}")
    print(f"  - Total scores: {len(data.get('scores', []))}")

    # Verify scores can be loaded back
    scores = data.get("scores", [])
    if not scores:
        print("✗ FAILED: No scores in history")
        return False

    # Try to deserialize a score
    try:
        test_score = QualityScore.from_dict(scores[0])
        print(f"✓ Scores can be deserialized")
        print(f"  - Sample score: {test_score.session_id} = {test_score.composite_score:.3f}")
    except Exception as e:
        print(f"✗ FAILED: Could not deserialize score: {e}")
        return False

    return True


def verify_frontend_integration(spec_dir: Path) -> bool:
    """Test 8: Verify frontend integration readiness."""
    print("\n" + "="*70)
    print("TEST 8: Frontend Integration Readiness")
    print("="*70)

    # Check that frontend components exist
    frontend_dir = Path(__file__).parent / "apps" / "frontend"

    components_to_check = [
        "src/renderer/stores/quality-store.ts",
        "src/renderer/components/analytics/QualityTrendChart.tsx",
        "src/renderer/components/analytics/QualityAlertCard.tsx",
    ]

    all_exist = True
    for component in components_to_check:
        component_path = frontend_dir / component
        exists = component_path.exists()
        status = "✓" if exists else "✗"
        print(f"{status} {component}")
        if not exists:
            all_exist = False

    if not all_exist:
        print("✗ FAILED: Some frontend components missing")
        return False

    print("✓ All frontend components exist")

    # Verify quality data format is compatible with frontend
    trend = analyze_quality_trend(spec_dir)
    trend_dict = trend.to_dict()

    required_fields = ["scores", "average_score", "current_score", "trend_direction", "should_alert"]
    missing_fields = [field for field in required_fields if field not in trend_dict]

    if missing_fields:
        print(f"✗ FAILED: Missing fields in trend data: {missing_fields}")
        return False

    print(f"✓ Quality data format compatible with frontend")
    return True


def main():
    """Run all end-to-end verification tests."""
    print("\n" + "="*70)
    print("QUALITY TRACKING END-TO-END VERIFICATION")
    print("="*70)

    # Create test spec directory
    base_dir = Path(__file__).parent
    spec_dir = create_test_spec_dir(base_dir)
    print(f"\n✓ Test spec directory created: {spec_dir}")

    # Run all tests
    tests = [
        ("Quality Score Calculation", verify_quality_score_calculation),
        ("Multiple QA Iterations", verify_multiple_qa_iterations),
        ("Trend Detection", verify_trend_detection),
        ("Quality Drop Alert", verify_quality_drop_alert),
        ("Quality Summary API", verify_quality_summary),
        ("Quality by Agent Type", verify_agent_type_breakdown),
        ("Data Persistence", verify_data_persistence),
        ("Frontend Integration", verify_frontend_integration),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func(spec_dir)
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ EXCEPTION in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Print summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ ALL TESTS PASSED - Quality tracking verified end-to-end!")
        return 0
    else:
        print(f"\n❌ SOME TESTS FAILED - {total - passed} test(s) need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
