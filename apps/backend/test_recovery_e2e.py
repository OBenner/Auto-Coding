#!/usr/bin/env python3
"""
End-to-End Recovery Loop Verification
======================================

Comprehensive test of the enhanced auto-recovery system.
Tests all components: failure detection, exponential backoff,
retry strategies, dead-letter queue, and notification thresholds.
"""

import json
import shutil
import time
from pathlib import Path
from typing import Any

from services.dead_letter_queue import DeadLetterQueue
from services.notification_manager import NotificationManager
from services.recovery import (
    FailureType,
    RecoveryAction,
    RecoveryManager,
    RetryStrategy,
)

# =============================================================================
# TEST SETUP
# =============================================================================


class TestResults:
    """Track test results for summary report."""

    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, test_name: str, message: str = ""):
        self.passed.append((test_name, message))
        print(f"✅ PASS: {test_name}")
        if message:
            print(f"   {message}")

    def add_fail(self, test_name: str, message: str):
        self.failed.append((test_name, message))
        print(f"❌ FAIL: {test_name}")
        print(f"   {message}")

    def add_warning(self, test_name: str, message: str):
        self.warnings.append((test_name, message))
        print(f"⚠️  WARN: {test_name}")
        print(f"   {message}")

    def print_summary(self):
        print("\n" + "=" * 70)
        print("END-TO-END VERIFICATION SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {len(self.passed)}")
        print(f"❌ Failed: {len(self.failed)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print("=" * 70)

        if self.failed:
            print("\nFailed Tests:")
            for test_name, message in self.failed:
                print(f"  • {test_name}: {message}")

        if self.warnings:
            print("\nWarnings:")
            for test_name, message in self.warnings:
                print(f"  • {test_name}: {message}")

        return len(self.failed) == 0


def setup_test_environment(base_dir: Path) -> tuple[Path, Path]:
    """
    Set up isolated test environment.

    Args:
        base_dir: Base directory for tests

    Returns:
        Tuple of (spec_dir, project_dir)
    """
    test_dir = base_dir / "test_recovery_e2e"
    spec_dir = test_dir / "spec"
    project_dir = test_dir / "project"

    # Clean up any existing test data
    if test_dir.exists():
        shutil.rmtree(test_dir)

    # Create fresh test directories
    spec_dir.mkdir(parents=True, exist_ok=True)
    project_dir.mkdir(parents=True, exist_ok=True)

    return spec_dir, project_dir


def cleanup_test_environment(base_dir: Path):
    """Clean up test environment."""
    test_dir = base_dir / "test_recovery_e2e"
    if test_dir.exists():
        shutil.rmtree(test_dir)


# =============================================================================
# TEST CASES
# =============================================================================


def test_failure_classification(manager: RecoveryManager, results: TestResults):
    """Test 1: Verify smart failure detection classifies errors correctly."""
    print("\n--- Test 1: Failure Classification ---")

    test_cases = [
        ("syntax error in main.py", FailureType.BROKEN_BUILD),
        ("verification failed: expected 200 got 404", FailureType.VERIFICATION_FAILED),
        ("context window exceeded", FailureType.CONTEXT_EXHAUSTED),
        ("random unknown error", FailureType.UNKNOWN),
    ]

    for error_msg, expected_type in test_cases:
        actual_type = manager.classify_failure(error_msg, "test-subtask")
        if actual_type == expected_type:
            results.add_pass(
                f"Classify '{error_msg[:30]}...'",
                f"Correctly identified as {expected_type.value}",
            )
        else:
            results.add_fail(
                f"Classify '{error_msg[:30]}...'",
                f"Expected {expected_type.value}, got {actual_type.value}",
            )


def test_exponential_backoff(manager: RecoveryManager, results: TestResults):
    """Test 2: Verify exponential backoff calculations."""
    print("\n--- Test 2: Exponential Backoff ---")

    expected_delays = [
        (0, 0.0),  # First attempt - no delay
        (1, 1.0),  # 1.0 * 2^1 = 2.0, but wait starts after first failure
        (2, 2.0),  # 1.0 * 2^2 = 4.0
        (3, 4.0),  # 1.0 * 2^3 = 8.0
        (4, 8.0),  # 1.0 * 2^4 = 16.0
        (5, 16.0),  # 1.0 * 2^5 = 32.0
        (6, 32.0),  # 1.0 * 2^6 = 64.0, capped at 60.0
        (10, 60.0),  # Capped at max
    ]

    for attempt, expected_delay in expected_delays:
        actual_delay = manager.calculate_backoff_delay(attempt)
        # Allow for small floating point differences
        if abs(actual_delay - expected_delay) < 0.01:
            results.add_pass(
                f"Backoff delay for attempt {attempt}",
                f"{actual_delay:.1f}s (expected {expected_delay:.1f}s)",
            )
        else:
            results.add_fail(
                f"Backoff delay for attempt {attempt}",
                f"Expected {expected_delay:.1f}s, got {actual_delay:.1f}s",
            )


def test_retry_strategies(manager: RecoveryManager, results: TestResults):
    """Test 3: Verify retry strategy selection."""
    print("\n--- Test 3: Retry Strategy Selection ---")

    subtask_id = "test-strategy-subtask"

    # Test VERIFICATION_FAILED progression
    strategies_vf = [
        (0, "direct_retry", False),
        (1, "model_fallback", True),
        (2, "alternative_approach", True),
        (3, None, None),  # Exhausted retries
    ]

    for attempt, expected_name, expected_fallback in strategies_vf:
        strategy = manager.select_retry_strategy(
            FailureType.VERIFICATION_FAILED, attempt, subtask_id
        )

        if expected_name is None:
            if strategy is None:
                results.add_pass(
                    f"VERIFICATION_FAILED attempt {attempt}",
                    "Correctly exhausted retries",
                )
            else:
                results.add_fail(
                    f"VERIFICATION_FAILED attempt {attempt}",
                    f"Expected None, got {strategy.name}",
                )
        elif strategy and strategy.name == expected_name:
            if strategy.use_model_fallback == expected_fallback:
                results.add_pass(
                    f"VERIFICATION_FAILED attempt {attempt}",
                    f"Strategy: {strategy.name}, Fallback: {strategy.use_model_fallback}",
                )
            else:
                results.add_fail(
                    f"VERIFICATION_FAILED attempt {attempt}",
                    f"Wrong fallback flag: expected {expected_fallback}, got {strategy.use_model_fallback}",
                )
        else:
            results.add_fail(
                f"VERIFICATION_FAILED attempt {attempt}",
                f"Expected {expected_name}, got {strategy.name if strategy else None}",
            )


def test_notification_thresholds(spec_dir: Path, results: TestResults):
    """Test 4: Verify notification thresholds work correctly."""
    print("\n--- Test 4: Notification Thresholds ---")

    notif_manager = NotificationManager(
        spec_dir, retry_threshold=3, escalation_threshold=5
    )
    subtask_id = "test-notif-subtask"

    # Test should_notify logic
    test_cases = [
        (0, False, "Below threshold - silent"),
        (1, False, "Below threshold - silent"),
        (2, False, "Below threshold - silent"),
        (3, True, "At threshold - notify"),
        (4, False, "Above threshold but not at interval"),
        (5, False, "At escalation threshold"),
        (6, True, "At notification interval (3, 6, 9...)"),
    ]

    for attempt, should_notify, reason in test_cases:
        actual = notif_manager.should_notify(subtask_id, attempt, "test_failure")
        if actual == should_notify:
            results.add_pass(f"Notify decision at attempt {attempt}", reason)
        else:
            results.add_fail(
                f"Notify decision at attempt {attempt}",
                f"Expected {should_notify}, got {actual} - {reason}",
            )

    # Test escalation
    if notif_manager.should_escalate(4):
        results.add_fail(
            "Escalation at attempt 4", "Should not escalate before threshold"
        )
    else:
        results.add_pass(
            "Escalation at attempt 4", "Correctly below escalation threshold"
        )

    if notif_manager.should_escalate(5):
        results.add_pass("Escalation at attempt 5", "Correctly at escalation threshold")
    else:
        results.add_fail("Escalation at attempt 5", "Should escalate at threshold")


def test_dead_letter_queue(spec_dir: Path, results: TestResults):
    """Test 5: Verify dead-letter queue captures unrecoverable failures."""
    print("\n--- Test 5: Dead-Letter Queue ---")

    dlq = DeadLetterQueue(spec_dir)

    # Add some failures
    failures_added = [
        dlq.add_failure(
            subtask_id="test-dlq-1",
            failure_type="circular_fix",
            error_message="Same approach tried 3 times",
            attempt_count=3,
            recovery_action="skip",
            context={"note": "Test failure 1"},
        ),
        dlq.add_failure(
            subtask_id="test-dlq-2",
            failure_type="unknown",
            error_message="Unknown error persists after 5 attempts",
            attempt_count=5,
            recovery_action="escalate",
            context={"note": "Test failure 2"},
        ),
    ]

    if all(failures_added):
        results.add_pass("Add failures to DLQ", "Both failures added successfully")
    else:
        results.add_fail("Add failures to DLQ", "Failed to add some failures")

    # Check pending failures
    pending = dlq.get_pending_failures()
    if len(pending) == 2:
        results.add_pass(
            "Retrieve pending failures", f"Found {len(pending)} pending failures"
        )
    else:
        results.add_fail("Retrieve pending failures", f"Expected 2, got {len(pending)}")

    # Check statistics
    stats = dlq.get_statistics()
    if stats["pending_failures"] == 2:
        results.add_pass("DLQ statistics", f"Pending: {stats['pending_failures']}")
    else:
        results.add_fail(
            "DLQ statistics", f"Expected 2 pending, got {stats['pending_failures']}"
        )

    # Test resolution
    if pending:
        resolved = dlq.mark_resolved(
            pending[0]["id"], resolution="Fixed manually", resolved_by="test"
        )
        if resolved:
            results.add_pass("Mark failure as resolved", "Successfully resolved")
            new_pending = dlq.get_pending_failures()
            if len(new_pending) == 1:
                results.add_pass("After resolution", "Pending count decreased to 1")
            else:
                results.add_fail(
                    "After resolution", f"Expected 1 pending, got {len(new_pending)}"
                )
        else:
            results.add_fail("Mark failure as resolved", "Failed to mark as resolved")


def test_recovery_action_integration(manager: RecoveryManager, results: TestResults):
    """Test 6: Verify full recovery action flow."""
    print("\n--- Test 6: Recovery Action Integration ---")

    # Test BROKEN_BUILD without good commit
    subtask_id = "test-broken-build"
    manager.record_attempt(
        subtask_id, 1, False, "Initial attempt", "syntax error in code"
    )

    action = manager.determine_recovery_action(FailureType.BROKEN_BUILD, subtask_id)

    if action.action == "escalate":
        results.add_pass(
            "BROKEN_BUILD without rollback", "Correctly escalates (no good commit)"
        )
        if action.should_notify:
            results.add_pass(
                "BROKEN_BUILD notification", "Always notifies on escalation"
            )
        else:
            results.add_fail("BROKEN_BUILD notification", "Should notify on escalation")
    else:
        results.add_fail(
            "BROKEN_BUILD without rollback",
            f"Expected 'escalate', got '{action.action}'",
        )

    # Test VERIFICATION_FAILED retry progression
    subtask_id_vf = "test-verification-failed"
    manager.record_attempt(
        subtask_id_vf, 1, False, "First attempt", "verification failed"
    )

    action = manager.determine_recovery_action(
        FailureType.VERIFICATION_FAILED, subtask_id_vf
    )

    if action.action == "retry":
        results.add_pass("VERIFICATION_FAILED first attempt", "Correctly retries")
        if action.wait_seconds > 0:
            results.add_pass(
                "Exponential backoff applied", f"Wait: {action.wait_seconds:.1f}s"
            )
        if action.strategy and action.strategy.name == "direct_retry":
            results.add_pass("First retry strategy", "Uses direct_retry")
        else:
            results.add_fail(
                "First retry strategy",
                f"Expected 'direct_retry', got '{action.strategy.name if action.strategy else None}'",
            )
    else:
        results.add_fail(
            "VERIFICATION_FAILED first attempt",
            f"Expected 'retry', got '{action.action}'",
        )


def test_notification_recording(manager: RecoveryManager, results: TestResults):
    """Test 7: Verify notification recording works correctly."""
    print("\n--- Test 7: Notification Recording ---")

    subtask_id = "test-notif-recording"

    # Record some attempts below threshold
    for i in range(3):
        manager.record_attempt(
            subtask_id, i + 1, False, f"Attempt {i + 1}", "test error"
        )

    # Get recovery action at threshold
    action = manager.determine_recovery_action(
        FailureType.VERIFICATION_FAILED, subtask_id
    )

    # Record the notification
    recorded = manager.record_recovery_notification(
        subtask_id, FailureType.VERIFICATION_FAILED, action
    )

    if recorded:
        results.add_pass("Record notification", "Notification recorded successfully")

        # Check statistics
        stats = manager.get_notification_statistics()
        if stats["total_notifications"] > 0 or stats["total_silent_failures"] > 0:
            results.add_pass(
                "Notification statistics",
                f"Notifications: {stats['total_notifications']}, Silent: {stats['total_silent_failures']}",
            )
        else:
            results.add_warning(
                "Notification statistics",
                "No notifications or silent failures recorded",
            )
    else:
        results.add_fail("Record notification", "Failed to record notification")


def test_circular_fix_detection(manager: RecoveryManager, results: TestResults):
    """Test 8: Verify circular fix detection."""
    print("\n--- Test 8: Circular Fix Detection ---")

    subtask_id = "test-circular"

    # Record attempts with similar approaches
    similar_approaches = [
        "Trying to fix authentication using async await pattern",
        "Attempting to fix auth with async await approach",
        "Fixing authentication issue using async await",
    ]

    for i, approach in enumerate(similar_approaches):
        manager.record_attempt(subtask_id, i + 1, False, approach, "still failing")

    # Check if circular fix is detected
    is_circular = manager.is_circular_fix(
        subtask_id, "Trying async await pattern for authentication"
    )

    if is_circular:
        results.add_pass(
            "Circular fix detection", "Detected repeated similar approaches"
        )

        # Test recovery action for circular fix
        action = manager.determine_recovery_action(FailureType.CIRCULAR_FIX, subtask_id)
        if action.action == "skip":
            results.add_pass("Circular fix recovery action", "Correctly skips subtask")
        else:
            results.add_fail(
                "Circular fix recovery action",
                f"Expected 'skip', got '{action.action}'",
            )
    else:
        results.add_fail(
            "Circular fix detection", "Failed to detect repeated similar approaches"
        )


def test_dlq_integration_with_recovery(manager: RecoveryManager, results: TestResults):
    """Test 9: Verify DLQ integration with recovery manager."""
    print("\n--- Test 9: DLQ Integration with Recovery ---")

    subtask_id = "test-dlq-integration"

    # Trigger an escalation which should add to DLQ
    for i in range(5):
        manager.record_attempt(
            subtask_id, i + 1, False, f"Attempt {i + 1}", "unknown error"
        )

    action = manager.determine_recovery_action(FailureType.UNKNOWN, subtask_id)

    if action.action == "escalate":
        results.add_pass("Escalation triggered", "Unknown error exhausted retries")

        # Check if added to DLQ
        dlq_failures = manager.get_dlq_pending_failures()
        matching = [f for f in dlq_failures if f["subtask_id"] == subtask_id]

        if matching:
            results.add_pass(
                "DLQ automatic capture", "Failure added to DLQ on escalation"
            )
            failure = matching[0]
            if failure["attempt_count"] > 0:
                results.add_pass(
                    "DLQ context capture",
                    f"Captured {failure['attempt_count']} attempts",
                )
            else:
                results.add_warning("DLQ context capture", "Attempt count not captured")
        else:
            results.add_fail(
                "DLQ automatic capture", "Failure not found in DLQ after escalation"
            )
    else:
        results.add_fail(
            "Escalation triggered", f"Expected 'escalate', got '{action.action}'"
        )


def test_context_exhausted_continuation(manager: RecoveryManager, results: TestResults):
    """Test 10: Verify CONTEXT_EXHAUSTED continues in next session."""
    print("\n--- Test 10: Context Exhausted Recovery ---")

    subtask_id = "test-context-exhausted"
    manager.record_attempt(
        subtask_id, 1, False, "Long implementation", "context window exceeded"
    )

    action = manager.determine_recovery_action(
        FailureType.CONTEXT_EXHAUSTED, subtask_id
    )

    if action.action == "continue":
        results.add_pass(
            "CONTEXT_EXHAUSTED action", "Correctly continues in next session"
        )
        if "commit progress" in action.reason.lower():
            results.add_pass(
                "CONTEXT_EXHAUSTED reason", "Reason mentions committing progress"
            )
        else:
            results.add_warning(
                "CONTEXT_EXHAUSTED reason", "Reason doesn't mention commit strategy"
            )
    else:
        results.add_fail(
            "CONTEXT_EXHAUSTED action", f"Expected 'continue', got '{action.action}'"
        )


def test_is_recoverable_flag(results: TestResults):
    """Test 11: Verify is_recoverable() method on FailureType."""
    print("\n--- Test 11: is_recoverable() Flag ---")

    recoverable_types = [
        FailureType.BROKEN_BUILD,
        FailureType.VERIFICATION_FAILED,
        FailureType.CONTEXT_EXHAUSTED,
        FailureType.UNKNOWN,
    ]

    non_recoverable_types = [FailureType.CIRCULAR_FIX]

    for ftype in recoverable_types:
        if ftype.is_recoverable():
            results.add_pass(
                f"{ftype.value} is_recoverable", "Correctly marked as recoverable"
            )
        else:
            results.add_fail(
                f"{ftype.value} is_recoverable", "Should be marked as recoverable"
            )

    for ftype in non_recoverable_types:
        if not ftype.is_recoverable():
            results.add_pass(
                f"{ftype.value} is_recoverable", "Correctly marked as non-recoverable"
            )
        else:
            results.add_fail(
                f"{ftype.value} is_recoverable", "Should be marked as non-recoverable"
            )


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================


def run_all_tests():
    """Run all end-to-end tests."""
    print("=" * 70)
    print("AUTO-RECOVERY LOOP - END-TO-END VERIFICATION")
    print("=" * 70)
    print("\nSetting up test environment...")

    # Setup
    base_dir = Path.cwd()
    spec_dir, project_dir = setup_test_environment(base_dir)
    results = TestResults()

    try:
        # Initialize recovery manager
        manager = RecoveryManager(spec_dir, project_dir)

        # Run all tests
        test_failure_classification(manager, results)
        test_exponential_backoff(manager, results)
        test_retry_strategies(manager, results)
        test_notification_thresholds(spec_dir, results)
        test_dead_letter_queue(spec_dir, results)
        test_recovery_action_integration(manager, results)
        test_notification_recording(manager, results)
        test_circular_fix_detection(manager, results)
        test_dlq_integration_with_recovery(manager, results)
        test_context_exhausted_continuation(manager, results)
        test_is_recoverable_flag(results)

        # Print summary
        all_passed = results.print_summary()

        # Cleanup
        print("\nCleaning up test environment...")
        cleanup_test_environment(base_dir)

        return 0 if all_passed else 1

    except Exception as e:
        results.add_fail("Test execution", f"Unexpected error: {e}")
        results.print_summary()
        # Don't cleanup on error so we can inspect state
        print(f"\nTest environment preserved at: {spec_dir.parent}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(run_all_tests())
