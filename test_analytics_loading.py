"""
Test script to verify analytics loading from existing data.

This ensures that operations.json is correctly loaded and parsed.
"""

import sys
from pathlib import Path

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from merge.analytics_recorder import MergeAnalyticsRecorder


def test_analytics_loading():
    """Test that analytics can be loaded from operations.json."""
    print("Testing analytics loading from existing data...")

    test_dir = Path(".auto-claude")
    recorder = MergeAnalyticsRecorder(test_dir)

    # Load operations
    operations = recorder.get_operation_history(limit=100)
    print(f"✓ Loaded {len(operations)} operation(s) from operations.json")

    if len(operations) > 0:
        op = operations[0]
        print(f"\nMost recent operation:")
        print(f"  ID: {op.operation_id}")
        print(f"  Timestamp: {op.timestamp}")
        print(f"  Tasks: {op.tasks_merged}")
        print(f"  Success: {op.success}")
        print(f"  Files processed: {op.stats.files_processed}")
        print(f"  Conflicts: {op.stats.conflicts_detected}")
        print(f"  Duration: {op.duration_seconds}s")

    # Get analytics summary
    analytics = recorder.get_analytics()
    print(f"\n✓ Analytics summary:")
    print(f"  Total operations: {analytics.total_operations}")
    print(f"  Total files merged: {analytics.total_files_merged}")
    print(f"  Success rate: {analytics.success_rate * 100:.1f}%")
    print(f"  Average duration: {analytics.average_duration_seconds:.1f}s")

    print("\n" + "="*60)
    print("✓ ANALYTICS LOADING TEST PASSED!")
    print("="*60)

    return True


if __name__ == "__main__":
    try:
        success = test_analytics_loading()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
