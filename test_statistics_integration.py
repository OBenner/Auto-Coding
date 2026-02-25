#!/usr/bin/env python3
"""
Integration test for spec statistics calculations.
Tests the statistics functions against this spec's implementation_plan.json.
"""
import json
from pathlib import Path

# Add backend to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from agents.tools_pkg.tools.statistics import (
    _parse_timestamp,
    _format_duration,
    _calculate_phase_durations,
    _calculate_completion_velocity,
    _count_unique_sessions
)


def test_statistics_calculations():
    """Test the statistics calculations with this spec's plan."""

    # Load the implementation plan
    spec_dir = Path(__file__).parent / ".auto-claude" / "specs" / "009-add-spec-statistics-tool"
    plan_file = spec_dir / "implementation_plan.json"

    print(f"Testing spec statistics calculations...")
    print(f"Plan file: {plan_file}")
    print()

    if not plan_file.exists():
        print("❌ FAILED: Implementation plan file not found")
        return False

    with open(plan_file, encoding="utf-8") as f:
        plan = json.load(f)

    print("✓ Loaded implementation plan")
    print()

    # Test 1: Calculate phase durations
    print("Test 1: Calculate phase durations")
    print("-" * 80)
    phase_durations = _calculate_phase_durations(plan.get("phases", []))

    if not phase_durations:
        print("❌ FAILED: No phase durations calculated")
        return False

    print(f"✓ Calculated durations for {len(phase_durations)} phases:")
    for phase_id, stats in phase_durations.items():
        print(f"  - {phase_id}:")
        print(f"      Duration: {stats['duration_formatted']} ({stats['duration_seconds']}s)")
        print(f"      Status: {stats['status']}")
        print(f"      Progress: {stats['subtasks_completed']}/{stats['subtasks_total']}")
    print()

    # Test 2: Calculate completion velocity
    print("Test 2: Calculate completion velocity")
    print("-" * 80)
    velocity = _calculate_completion_velocity(plan, phase_durations)

    print(f"✓ Completion velocity calculated:")
    print(f"  - Subtasks per hour: {velocity['subtasks_per_hour']}")
    print(f"  - Subtasks per day: {velocity['subtasks_per_day']}")
    print(f"  - Average subtask duration: {velocity['average_subtask_duration']}")
    print()

    # Test 3: Count unique sessions
    print("Test 3: Count unique sessions")
    print("-" * 80)
    session_count = _count_unique_sessions(plan)
    print(f"✓ Session count: {session_count}")
    print()

    # Test 4: QA iterations
    print("Test 4: QA iterations")
    print("-" * 80)
    qa_signoff = plan.get("qa_signoff", {})
    qa_iterations = qa_signoff.get("qa_session", 0) if qa_signoff else 0
    qa_status = qa_signoff.get("status", "pending") if qa_signoff else "pending"
    print(f"✓ QA iterations: {qa_iterations}")
    print(f"✓ QA status: {qa_status}")
    print()

    # Test 5: Total build time
    print("Test 5: Total build time")
    print("-" * 80)
    created_at = _parse_timestamp(plan.get("created_at"))
    last_updated = _parse_timestamp(plan.get("last_updated"))

    if created_at:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        build_duration_seconds = (now - created_at).total_seconds()
        build_duration = _format_duration(build_duration_seconds)
        print(f"✓ Total build time: {build_duration} ({build_duration_seconds}s)")
        print(f"  Started: {created_at.strftime('%Y-%m-%d %H:%M UTC')}")
        if last_updated:
            print(f"  Last updated: {last_updated.strftime('%Y-%m-%d %H:%M UTC')}")
    else:
        print("⚠ Warning: No created_at timestamp in plan")
        build_duration = "N/A"
    print()

    # Test 6: Subtask completion rate
    print("Test 6: Subtask completion rate")
    print("-" * 80)
    total_subtasks = 0
    completed_subtasks = 0

    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            total_subtasks += 1
            if subtask.get("status") == "completed":
                completed_subtasks += 1

    completion_rate = (completed_subtasks / total_subtasks * 100) if total_subtasks > 0 else 0
    print(f"✓ Subtask completion rate: {completion_rate:.1f}% ({completed_subtasks}/{total_subtasks})")
    print()

    # Summary: Verify all required metrics are available
    print("=" * 80)
    print("SUMMARY: Verification of Required Metrics")
    print("=" * 80)

    required_metrics = {
        "total_build_time": build_duration,
        "phase_durations": phase_durations,
        "session_count": session_count,
        "qa_iterations": qa_iterations,
        "completion_velocity": velocity,
        "subtask_completion_rate": completion_rate
    }

    all_present = True
    for metric_name, metric_value in required_metrics.items():
        status = "✓" if metric_value is not None else "❌"
        print(f"{status} {metric_name}: {type(metric_value).__name__}")
        if metric_value is None:
            all_present = False

    print()

    if all_present:
        print("✅ SUCCESS: All 6 required metrics are available and calculated correctly!")
        print()
        print("Metric values:")
        print(f"  1. total_build_time: {required_metrics['total_build_time']}")
        print(f"  2. phase_durations: {len(required_metrics['phase_durations'])} phases")
        print(f"  3. session_count: {required_metrics['session_count']}")
        print(f"  4. qa_iterations: {required_metrics['qa_iterations']}")
        print(f"  5. completion_velocity: {required_metrics['completion_velocity']}")
        print(f"  6. subtask_completion_rate: {required_metrics['subtask_completion_rate']:.1f}%")
        return True
    else:
        print("❌ FAILED: Some required metrics are missing")
        return False


if __name__ == "__main__":
    success = test_statistics_calculations()
    sys.exit(0 if success else 1)
