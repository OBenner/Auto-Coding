"""
Test script to verify conflict pattern detection.

This script tests that:
1. Multiple merges with similar conflicts are recorded
2. Conflict patterns are detected and grouped by (file_path, location)
3. Occurrence counts increment correctly
4. Severity levels are updated appropriately
5. Tasks involved are tracked properly
6. Dashboard data structure is correct
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "backend"))

from merge.analytics_recorder import (
    MergeAnalyticsRecorder,
    ConflictPattern,
)
from merge.models import MergeReport, MergeStats
from merge.types import ConflictRegion, ConflictSeverity, ChangeType


def create_test_merge_report(
    task_ids: list[str],
    conflicts: list[ConflictRegion],
    success: bool = True,
    timestamp: datetime | None = None,
) -> MergeReport:
    """Create a test merge report with specified conflicts."""
    stats = MergeStats(
        files_processed=len({c.file_path for c in conflicts}),
        files_auto_merged=0,
        files_ai_merged=len({c.file_path for c in conflicts}),
        files_need_review=0,
        files_failed=0,
        conflicts_detected=len(conflicts),
        conflicts_auto_resolved=0,
        conflicts_ai_resolved=len(conflicts),
        ai_calls_made=len(conflicts),
        estimated_tokens_used=1500 * len(conflicts),
        duration_seconds=30.0 + len(conflicts) * 5.0,
    )

    # Create file results with conflicts
    from merge.types import MergeResult, MergeDecision

    file_results = {}
    for conflict in conflicts:
        if conflict.file_path not in file_results:
            file_results[conflict.file_path] = MergeResult(
                file_path=conflict.file_path,
                decision=MergeDecision.AI_MERGED,
                conflicts_resolved=[],
                conflicts_remaining=[],
                explanation="AI merged the conflicts",
            )
        file_results[conflict.file_path].conflicts_resolved.append(conflict)

    return MergeReport(
        tasks_merged=task_ids,
        started_at=timestamp or datetime.now(),
        stats=stats,
        success=success,
        error=None,
        file_results=file_results,
    )


def test_conflict_pattern_detection():
    """Test end-to-end conflict pattern detection."""
    print("Testing conflict pattern detection...")
    print("=" * 60)

    # Setup test directory
    test_dir = Path(".auto-claude")
    analytics_dir = test_dir / "merge_analytics"
    patterns_file = analytics_dir / "conflict_patterns.json"
    operations_file = analytics_dir / "operations.json"

    # Clear existing data for clean test
    if patterns_file.exists():
        patterns_file.unlink()
        print("✓ Cleared existing pattern data for clean test")
    if operations_file.exists():
        operations_file.unlink()
        print("✓ Cleared existing operations data for clean test")

    # Initialize recorder
    recorder = MergeAnalyticsRecorder(test_dir)
    print(f"✓ Initialized analytics recorder at {analytics_dir}\n")

    # Test Case 1: First occurrence of conflict pattern
    print("Test Case 1: First occurrence of conflict pattern")
    print("-" * 60)

    conflict1 = ConflictRegion(
        file_path="apps/frontend/src/components/App.tsx",
        location="function:App",
        tasks_involved=["task-001", "task-002"],
        change_types=[ChangeType.ADD_HOOK_CALL, ChangeType.MODIFY_FUNCTION],
        severity=ConflictSeverity.MEDIUM,
        can_auto_merge=False,
        reason="Both tasks modified the same function",
    )

    report1 = create_test_merge_report(
        task_ids=["task-001", "task-002"],
        conflicts=[conflict1],
        timestamp=datetime.now() - timedelta(hours=3),
    )

    recorder.record_merge_operation("merge-001", report1)
    print("✓ Recorded first merge with conflict in App.tsx:function:App")

    # Verify pattern created
    patterns = recorder._load_conflict_patterns()
    if len(patterns) != 1:
        print(f"✗ FAILED: Expected 1 pattern, got {len(patterns)}")
        return False

    pattern1 = patterns[0]
    if pattern1.file_path != "apps/frontend/src/components/App.tsx":
        print(f"✗ FAILED: Wrong file_path: {pattern1.file_path}")
        return False
    if pattern1.location != "function:App":
        print(f"✗ FAILED: Wrong location: {pattern1.location}")
        return False
    if pattern1.occurrence_count != 1:
        print(f"✗ FAILED: Expected occurrence_count=1, got {pattern1.occurrence_count}")
        return False
    if pattern1.severity != ConflictSeverity.MEDIUM:
        print(f"✗ FAILED: Wrong severity: {pattern1.severity}")
        return False

    print(f"✓ Pattern created: {pattern1.file_path} @ {pattern1.location}")
    print(f"  - Occurrence count: {pattern1.occurrence_count}")
    print(f"  - Severity: {pattern1.severity.value}")
    print(f"  - Tasks: {pattern1.tasks_involved}\n")

    # Test Case 2: Same pattern occurs again (should increment count)
    print("Test Case 2: Same pattern occurs again")
    print("-" * 60)

    conflict2 = ConflictRegion(
        file_path="apps/frontend/src/components/App.tsx",
        location="function:App",
        tasks_involved=["task-003", "task-004"],
        change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
        severity=ConflictSeverity.MEDIUM,
        can_auto_merge=False,
        reason="Different tasks, same conflict location",
    )

    report2 = create_test_merge_report(
        task_ids=["task-003", "task-004"],
        conflicts=[conflict2],
        timestamp=datetime.now() - timedelta(hours=2),
    )

    recorder.record_merge_operation("merge-002", report2)
    print("✓ Recorded second merge with conflict in same location")

    # Verify pattern updated
    patterns = recorder._load_conflict_patterns()
    if len(patterns) != 1:
        print(f"✗ FAILED: Expected 1 pattern (should merge), got {len(patterns)}")
        return False

    pattern2 = patterns[0]
    if pattern2.occurrence_count != 2:
        print(f"✗ FAILED: Expected occurrence_count=2, got {pattern2.occurrence_count}")
        return False

    # Should have all 4 tasks tracked
    expected_tasks = {"task-001", "task-002", "task-003", "task-004"}
    actual_tasks = set(pattern2.tasks_involved)
    if actual_tasks != expected_tasks:
        print(f"✗ FAILED: Expected tasks {expected_tasks}, got {actual_tasks}")
        return False

    print(f"✓ Pattern occurrence count incremented: {pattern2.occurrence_count}")
    print(f"✓ All tasks tracked: {pattern2.tasks_involved}\n")

    # Test Case 3: Same location, higher severity (should update severity)
    print("Test Case 3: Same location, higher severity")
    print("-" * 60)

    conflict3 = ConflictRegion(
        file_path="apps/frontend/src/components/App.tsx",
        location="function:App",
        tasks_involved=["task-005", "task-006"],
        change_types=[ChangeType.REMOVE_FUNCTION, ChangeType.MODIFY_FUNCTION],
        severity=ConflictSeverity.HIGH,  # Higher than previous MEDIUM
        can_auto_merge=False,
        reason="Conflicting function removal and modification",
    )

    report3 = create_test_merge_report(
        task_ids=["task-005", "task-006"],
        conflicts=[conflict3],
        timestamp=datetime.now() - timedelta(hours=1),
    )

    recorder.record_merge_operation("merge-003", report3)
    print("✓ Recorded third merge with higher severity")

    # Verify severity updated
    patterns = recorder._load_conflict_patterns()
    pattern3 = patterns[0]

    if pattern3.severity != ConflictSeverity.HIGH:
        print(f"✗ FAILED: Expected severity=HIGH, got {pattern3.severity}")
        return False
    if pattern3.occurrence_count != 3:
        print(f"✗ FAILED: Expected occurrence_count=3, got {pattern3.occurrence_count}")
        return False

    print(f"✓ Severity updated to: {pattern3.severity.value}")
    print(f"✓ Occurrence count: {pattern3.occurrence_count}\n")

    # Test Case 4: Different location in same file (should create new pattern)
    print("Test Case 4: Different location in same file")
    print("-" * 60)

    conflict4 = ConflictRegion(
        file_path="apps/frontend/src/components/App.tsx",
        location="function:handleSubmit",  # Different location
        tasks_involved=["task-007", "task-008"],
        change_types=[ChangeType.MODIFY_FUNCTION, ChangeType.MODIFY_FUNCTION],
        severity=ConflictSeverity.LOW,
        can_auto_merge=False,
        reason="Different function in same file",
    )

    report4 = create_test_merge_report(
        task_ids=["task-007", "task-008"],
        conflicts=[conflict4],
        timestamp=datetime.now() - timedelta(minutes=30),
    )

    recorder.record_merge_operation("merge-004", report4)
    print("✓ Recorded merge with conflict in different location")

    # Should now have 2 patterns
    patterns = recorder._load_conflict_patterns()
    if len(patterns) != 2:
        print(f"✗ FAILED: Expected 2 patterns, got {len(patterns)}")
        return False

    # Find the new pattern
    new_pattern = next((p for p in patterns if p.location == "function:handleSubmit"), None)
    if not new_pattern:
        print("✗ FAILED: New pattern not found")
        return False

    if new_pattern.occurrence_count != 1:
        print(f"✗ FAILED: New pattern should have occurrence_count=1, got {new_pattern.occurrence_count}")
        return False

    print(f"✓ New pattern created: {new_pattern.location}")
    print(f"  - Occurrence count: {new_pattern.occurrence_count}")
    print(f"  - Total patterns: {len(patterns)}\n")

    # Test Case 5: Different file (should create another pattern)
    print("Test Case 5: Different file")
    print("-" * 60)

    conflict5 = ConflictRegion(
        file_path="apps/backend/core/client.py",
        location="function:create_client",
        tasks_involved=["task-009", "task-010"],
        change_types=[ChangeType.ADD_IMPORT, ChangeType.MODIFY_FUNCTION],
        severity=ConflictSeverity.CRITICAL,
        can_auto_merge=False,
        reason="Critical conflict in backend client",
    )

    report5 = create_test_merge_report(
        task_ids=["task-009", "task-010"],
        conflicts=[conflict5],
        timestamp=datetime.now(),
    )

    recorder.record_merge_operation("merge-005", report5)
    print("✓ Recorded merge with conflict in different file")

    # Should now have 3 patterns
    patterns = recorder._load_conflict_patterns()
    if len(patterns) != 3:
        print(f"✗ FAILED: Expected 3 patterns, got {len(patterns)}")
        return False

    # Verify sorting (by occurrence_count, descending)
    if patterns[0].occurrence_count < patterns[1].occurrence_count:
        print("✗ FAILED: Patterns not sorted by occurrence_count")
        return False

    print(f"✓ Total patterns: {len(patterns)}")
    print(f"✓ Patterns sorted by occurrence count\n")

    # Test Case 6: Verify analytics aggregation
    print("Test Case 6: Analytics aggregation")
    print("-" * 60)

    analytics = recorder.get_analytics()

    if analytics.total_operations != 5:
        print(f"✗ FAILED: Expected 5 operations, got {analytics.total_operations}")
        return False

    if len(analytics.conflict_patterns) != 3:
        print(f"✗ FAILED: Expected 3 conflict patterns, got {len(analytics.conflict_patterns)}")
        return False

    # Top pattern should be the one with 3 occurrences
    top_pattern = analytics.conflict_patterns[0]
    if top_pattern.occurrence_count != 3:
        print(f"✗ FAILED: Top pattern should have 3 occurrences, got {top_pattern.occurrence_count}")
        return False

    print(f"✓ Total operations: {analytics.total_operations}")
    print(f"✓ Total conflicts detected: {analytics.total_conflicts}")
    print(f"✓ Conflict patterns identified: {len(analytics.conflict_patterns)}")
    print(f"✓ Top pattern: {top_pattern.file_path} @ {top_pattern.location} ({top_pattern.occurrence_count} times)\n")

    # Test Case 7: Verify dashboard data structure
    print("Test Case 7: Dashboard data structure")
    print("-" * 60)

    # Load patterns file directly (what dashboard would read)
    if not patterns_file.exists():
        print(f"✗ FAILED: Patterns file not found: {patterns_file}")
        return False

    with open(patterns_file, 'r') as f:
        dashboard_data = json.load(f)

    if len(dashboard_data) != 3:
        print(f"✗ FAILED: Dashboard should have 3 patterns, got {len(dashboard_data)}")
        return False

    # Verify all required fields present
    required_fields = ["file_path", "location", "occurrence_count", "severity", "tasks_involved", "last_seen"]
    for i, pattern_data in enumerate(dashboard_data):
        missing = [f for f in required_fields if f not in pattern_data]
        if missing:
            print(f"✗ FAILED: Pattern {i} missing fields: {missing}")
            return False

    # Verify top pattern data
    top_pattern_data = dashboard_data[0]
    if top_pattern_data["occurrence_count"] != 3:
        print(f"✗ FAILED: Top pattern occurrence_count mismatch in dashboard data")
        return False
    if top_pattern_data["severity"] != "high":
        print(f"✗ FAILED: Top pattern severity should be 'high', got {top_pattern_data['severity']}")
        return False
    if len(top_pattern_data["tasks_involved"]) != 6:
        print(f"✗ FAILED: Top pattern should track 6 tasks, got {len(top_pattern_data['tasks_involved'])}")
        return False

    print(f"✓ Dashboard data structure correct")
    print(f"✓ All required fields present")
    print(f"✓ Data matches expected format\n")

    # Summary
    print("=" * 60)
    print("✓ ALL CONFLICT PATTERN TESTS PASSED!")
    print("=" * 60)
    print(f"\nPattern Detection Summary:")
    print(f"  Total operations recorded: {analytics.total_operations}")
    print(f"  Total conflicts detected: {analytics.total_conflicts}")
    print(f"  Unique conflict patterns: {len(analytics.conflict_patterns)}")
    print(f"\nTop 3 Conflict Patterns:")
    for i, pattern in enumerate(analytics.conflict_patterns[:3], 1):
        print(f"  {i}. {pattern.file_path}")
        print(f"     Location: {pattern.location}")
        print(f"     Occurrences: {pattern.occurrence_count}")
        print(f"     Severity: {pattern.severity.value}")
        print(f"     Tasks: {len(pattern.tasks_involved)} tasks involved")
        print()

    return True


if __name__ == "__main__":
    try:
        success = test_conflict_pattern_detection()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
