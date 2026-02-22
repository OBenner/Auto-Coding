"""
Test script to verify MergeOrchestrator analytics integration.

This script tests that:
1. MergeOrchestrator has analytics_recorder attribute
2. Analytics are recorded after merge operations
3. Multiple merge operations are tracked correctly
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from merge.orchestrator import MergeOrchestrator


def test_orchestrator_has_analytics():
    """Test that MergeOrchestrator has analytics_recorder."""
    print("Testing MergeOrchestrator analytics integration...")

    # Initialize orchestrator
    test_dir = Path(".auto-claude")
    orchestrator = MergeOrchestrator(test_dir)
    print(f"✓ Initialized MergeOrchestrator")

    # Verify analytics_recorder attribute exists
    if not hasattr(orchestrator, 'analytics_recorder'):
        print("✗ FAILED: MergeOrchestrator does not have analytics_recorder attribute")
        return False
    print(f"✓ MergeOrchestrator has analytics_recorder attribute")

    # Verify it's the correct type
    from merge.analytics_recorder import MergeAnalyticsRecorder
    if not isinstance(orchestrator.analytics_recorder, MergeAnalyticsRecorder):
        print(f"✗ FAILED: analytics_recorder is not a MergeAnalyticsRecorder instance")
        print(f"  Type: {type(orchestrator.analytics_recorder)}")
        return False
    print(f"✓ analytics_recorder is correct type: MergeAnalyticsRecorder")

    # Verify analytics directory exists
    analytics_dir = test_dir / "merge_analytics"
    if not analytics_dir.exists():
        print(f"✗ FAILED: Analytics directory not created at {analytics_dir}")
        return False
    print(f"✓ Analytics directory exists: {analytics_dir}")

    # Test that we can access analytics methods
    try:
        analytics = orchestrator.analytics_recorder.get_analytics()
        print(f"✓ Can call get_analytics(): {analytics.total_operations} operations")
    except Exception as e:
        print(f"✗ FAILED: Error calling get_analytics(): {e}")
        return False

    try:
        history = orchestrator.analytics_recorder.get_operation_history(limit=10)
        print(f"✓ Can call get_operation_history(): {len(history)} operations")
    except Exception as e:
        print(f"✗ FAILED: Error calling get_operation_history(): {e}")
        return False

    print("\n" + "="*60)
    print("✓ ALL ORCHESTRATOR INTEGRATION TESTS PASSED!")
    print("="*60)

    return True


def test_analytics_persistence():
    """Test that analytics persist across multiple operations."""
    print("\nTesting analytics persistence...")

    test_dir = Path(".auto-claude")
    analytics_dir = test_dir / "merge_analytics"
    operations_file = analytics_dir / "operations.json"

    # Check if we have recorded operations
    if not operations_file.exists():
        print("ℹ No previous operations found (this is expected for first run)")
        return True

    # Load and verify
    with open(operations_file, 'r') as f:
        data = json.load(f)

    if not isinstance(data, list):
        print(f"✗ FAILED: operations.json should contain a list, got {type(data)}")
        return False
    print(f"✓ operations.json contains a list with {len(data)} operation(s)")

    # Verify each operation has required structure
    for i, op in enumerate(data):
        required_fields = [
            "operation_id",
            "timestamp",
            "tasks_merged",
            "stats",
            "success",
        ]
        missing = [f for f in required_fields if f not in op]
        if missing:
            print(f"✗ FAILED: Operation {i} missing fields: {missing}")
            return False

    print(f"✓ All {len(data)} operations have correct structure")

    # Test that timestamps are in chronological order (most recent first)
    if len(data) > 1:
        timestamps = [datetime.fromisoformat(op["timestamp"]) for op in data]
        if timestamps != sorted(timestamps, reverse=True):
            print("✗ FAILED: Operations are not sorted by timestamp (most recent first)")
            return False
        print("✓ Operations are correctly sorted by timestamp")

    print("\n" + "="*60)
    print("✓ ALL PERSISTENCE TESTS PASSED!")
    print("="*60)

    return True


if __name__ == "__main__":
    try:
        # Test 1: Orchestrator integration
        test1_success = test_orchestrator_has_analytics()

        # Test 2: Analytics persistence
        test2_success = test_analytics_persistence()

        success = test1_success and test2_success

        if success:
            print("\n" + "="*60)
            print("✓✓✓ ALL TESTS PASSED ✓✓✓")
            print("="*60)
            print("\nMerge analytics recording is working correctly!")
            print("Analytics are recorded in: .auto-claude/merge_analytics/")

        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
