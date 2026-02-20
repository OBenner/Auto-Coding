"""
Test script to verify merge analytics recording.

This script tests that:
1. MergeAnalyticsRecorder correctly records merge operations
2. All required fields are present in the recorded data
3. Data can be loaded and queried properly
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from merge.analytics_recorder import (
    MergeAnalyticsRecorder,
)
from merge.models import MergeReport, MergeStats


def test_analytics_recording():
    """Test that analytics recording works correctly."""
    print("Testing merge analytics recording...")

    # Setup test directory
    test_dir = Path(".auto-claude")
    analytics_dir = test_dir / "merge_analytics"

    # Initialize recorder
    recorder = MergeAnalyticsRecorder(test_dir)
    print(f"✓ Initialized analytics recorder at {analytics_dir}")

    # Create a test merge report
    stats = MergeStats(
        files_processed=5,
        files_auto_merged=3,
        files_ai_merged=1,
        files_need_review=1,
        files_failed=0,
        conflicts_detected=2,
        conflicts_auto_resolved=1,
        conflicts_ai_resolved=1,
        ai_calls_made=2,
        estimated_tokens_used=1500,
        duration_seconds=45.5,
    )

    report = MergeReport(
        tasks_merged=["test-task-001", "test-task-002"],
        started_at=datetime.now(),
        stats=stats,
        success=True,
        error=None,
        file_results={},
    )

    # Record the operation
    operation_id = "test-merge-001"
    recorder.record_merge_operation(operation_id, report)
    print(f"✓ Recorded merge operation: {operation_id}")

    # Verify the file was created
    operations_file = analytics_dir / "operations.json"
    if not operations_file.exists():
        print(f"✗ FAILED: operations.json not created at {operations_file}")
        return False
    print(f"✓ Operations file created: {operations_file}")

    # Load and verify the data
    with open(operations_file, 'r') as f:
        data = json.load(f)

    if not data or len(data) == 0:
        print("✗ FAILED: No operations recorded in operations.json")
        return False
    print(f"✓ Found {len(data)} operation(s) in operations.json")

    # Check the recorded operation
    recorded_op = data[0]

    # Verify all required fields are present
    required_fields = [
        "operation_id",
        "timestamp",
        "tasks_merged",
        "stats",
        "success",
        "duration_seconds",
    ]

    missing_fields = [field for field in required_fields if field not in recorded_op]
    if missing_fields:
        print(f"✗ FAILED: Missing required fields: {missing_fields}")
        return False
    print(f"✓ All required fields present: {required_fields}")

    # Verify operation_id matches
    if recorded_op["operation_id"] != operation_id:
        print(f"✗ FAILED: operation_id mismatch: {recorded_op['operation_id']} != {operation_id}")
        return False
    print(f"✓ Operation ID matches: {operation_id}")

    # Verify timestamp is valid ISO format
    try:
        timestamp = datetime.fromisoformat(recorded_op["timestamp"])
        print(f"✓ Timestamp is valid ISO format: {timestamp}")
    except ValueError as e:
        print(f"✗ FAILED: Invalid timestamp format: {e}")
        return False

    # Verify stats are present
    stats_data = recorded_op["stats"]
    required_stats = [
        "files_processed",
        "conflicts_detected",
        "ai_calls_made",
        "duration_seconds",
    ]
    missing_stats = [stat for stat in required_stats if stat not in stats_data]
    if missing_stats:
        print(f"✗ FAILED: Missing required stats: {missing_stats}")
        return False
    print(f"✓ All required stats present")

    # Verify tasks_merged is a list
    if not isinstance(recorded_op["tasks_merged"], list):
        print(f"✗ FAILED: tasks_merged is not a list")
        return False
    if len(recorded_op["tasks_merged"]) != 2:
        print(f"✗ FAILED: Expected 2 tasks, got {len(recorded_op['tasks_merged'])}")
        return False
    print(f"✓ Tasks merged: {recorded_op['tasks_merged']}")

    # Test analytics aggregation
    analytics = recorder.get_analytics()
    if analytics.total_operations != 1:
        print(f"✗ FAILED: Expected 1 operation, got {analytics.total_operations}")
        return False
    print(f"✓ Analytics aggregation works: {analytics.total_operations} operation(s)")

    # Test operation history
    history = recorder.get_operation_history(limit=10)
    if len(history) != 1:
        print(f"✗ FAILED: Expected 1 operation in history, got {len(history)}")
        return False
    print(f"✓ Operation history works: {len(history)} operation(s)")

    # Verify the history record has correct structure
    hist_op = history[0]
    if hist_op.operation_id != operation_id:
        print(f"✗ FAILED: History operation_id mismatch")
        return False
    if hist_op.stats.files_processed != 5:
        print(f"✗ FAILED: Stats mismatch in history")
        return False
    print(f"✓ History record structure correct")

    print("\n" + "="*60)
    print("✓ ALL TESTS PASSED!")
    print("="*60)
    print(f"\nAnalytics Summary:")
    print(f"  Total Operations: {analytics.total_operations}")
    print(f"  Total Files Merged: {analytics.total_files_merged}")
    print(f"  Total Conflicts: {analytics.total_conflicts}")
    print(f"  Success Rate: {analytics.success_rate * 100:.1f}%")
    print(f"  Average Duration: {analytics.average_duration_seconds:.1f}s")

    return True


if __name__ == "__main__":
    try:
        success = test_analytics_recording()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
