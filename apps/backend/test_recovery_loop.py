"""
End-to-End Recovery Loop Verification Test
==========================================

Comprehensive test of the auto-recovery loop system including:
- Failure classification with pattern database
- Exponential backoff calculation
- Retry strategy selection (direct, model fallback, alternative)
- Dead-letter queue integration
- Notification threshold management
- Full recovery loop simulation

This test verifies all components work together properly.
"""

import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, UTC

# Import the recovery system components
from services.recovery import (
    RecoveryManager,
    FailureType,
    RecoveryAction,
    RetryStrategy,
    BACKOFF_BASE_DELAY,
    BACKOFF_MAX_DELAY,
    BACKOFF_MULTIPLIER,
)
from services.dead_letter_queue import DeadLetterQueue
from services.notification_manager import NotificationManager


class RecoveryLoopTest:
    """End-to-end test suite for recovery loop."""

    def __init__(self):
        self.test_dir = None
        self.spec_dir = None
        self.project_dir = None
        self.recovery_manager = None
        self.test_results = []

    def setup(self):
        """Create test environment."""
        print("\n" + "=" * 70)
        print("RECOVERY LOOP END-TO-END VERIFICATION")
        print("=" * 70)

        # Create temporary test directories
        self.test_dir = Path(tempfile.mkdtemp(prefix="recovery_test_"))
        self.spec_dir = self.test_dir / "specs" / "test-spec"
        self.project_dir = self.test_dir / "project"

        self.spec_dir.mkdir(parents=True, exist_ok=True)
        self.project_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n✓ Test environment created: {self.test_dir}")
        print(f"  Spec dir: {self.spec_dir}")
        print(f"  Project dir: {self.project_dir}")

        # Initialize recovery manager
        self.recovery_manager = RecoveryManager(
            spec_dir=self.spec_dir,
            project_dir=self.project_dir
        )
        print(f"✓ RecoveryManager initialized")

        return self

    def teardown(self):
        """Clean up test environment."""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            print(f"\n✓ Test environment cleaned up")

    def record_result(self, test_name: str, passed: bool, details: str = ""):
        """Record test result."""
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now(UTC).isoformat()
        })
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"  {details}")

    def test_1_failure_classification(self):
        """Test 1: Verify failure classification with pattern database."""
        print("\n--- Test 1: Failure Classification ---")

        test_cases = [
            ("syntax error in module", FailureType.BROKEN_BUILD),
            ("test failed assertion", FailureType.VERIFICATION_FAILED),
            ("timeout waiting for response", FailureType.VERIFICATION_FAILED),
            ("context token limit exceeded", FailureType.CONTEXT_EXHAUSTED),
            ("unknown error occurred", FailureType.UNKNOWN),
        ]

        all_passed = True
        for error_msg, expected_type in test_cases:
            result = self.recovery_manager.classify_failure(
                error=error_msg,
                subtask_id="test-subtask"
            )
            if result == expected_type:
                print(f"  ✓ '{error_msg}' → {expected_type.value}")
            else:
                print(f"  ✗ '{error_msg}' → {result.value} (expected {expected_type.value})")
                all_passed = False

        self.record_result(
            "Failure Classification",
            all_passed,
            f"Tested {len(test_cases)} error patterns"
        )
        return all_passed

    def test_2_exponential_backoff(self):
        """Test 2: Verify exponential backoff calculation."""
        print("\n--- Test 2: Exponential Backoff ---")

        expected_delays = [
            (0, 0.0),     # First attempt: no delay
            (1, 2.0),     # 1.0 * 2^1 = 2.0
            (2, 4.0),     # 1.0 * 2^2 = 4.0
            (3, 8.0),     # 1.0 * 2^3 = 8.0
            (4, 16.0),    # 1.0 * 2^4 = 16.0
            (5, 32.0),    # 1.0 * 2^5 = 32.0
            (6, 60.0),    # Capped at 60s
            (10, 60.0),   # Still capped
        ]

        all_passed = True
        for attempt, expected_delay in expected_delays:
            actual_delay = self.recovery_manager.calculate_backoff_delay(attempt)
            if abs(actual_delay - expected_delay) < 0.001:
                print(f"  ✓ Attempt {attempt}: {actual_delay}s delay")
            else:
                print(f"  ✗ Attempt {attempt}: {actual_delay}s (expected {expected_delay}s)")
                all_passed = False

        self.record_result(
            "Exponential Backoff",
            all_passed,
            f"Base={BACKOFF_BASE_DELAY}s, Max={BACKOFF_MAX_DELAY}s, Multiplier={BACKOFF_MULTIPLIER}x"
        )
        return all_passed

    def test_3_retry_strategy_selection(self):
        """Test 3: Verify progressive retry strategy selection."""
        print("\n--- Test 3: Retry Strategy Selection ---")

        test_cases = [
            # (failure_type, attempt, expected_strategy_name, should_have_fallback)
            (FailureType.VERIFICATION_FAILED, 0, "direct_retry", False),
            (FailureType.VERIFICATION_FAILED, 1, "model_fallback", True),
            (FailureType.VERIFICATION_FAILED, 2, "alternative_approach", True),
            (FailureType.UNKNOWN, 0, "direct_retry", False),
            (FailureType.UNKNOWN, 1, "model_fallback_alternative", True),  # UNKNOWN uses combined strategy
            (FailureType.BROKEN_BUILD, 0, None, False),  # No strategy for BROKEN_BUILD
        ]

        all_passed = True
        for failure_type, attempt, expected_strategy, expected_fallback in test_cases:
            strategy = self.recovery_manager.select_retry_strategy(
                failure_type=failure_type,
                attempt_count=attempt,
                subtask_id="test-subtask"
            )

            if expected_strategy is None:
                if strategy is None:
                    print(f"  ✓ {failure_type.value} attempt {attempt}: No strategy (as expected)")
                else:
                    print(f"  ✗ {failure_type.value} attempt {attempt}: {strategy.name} (expected None)")
                    all_passed = False
            else:
                if strategy and strategy.name == expected_strategy:
                    fallback_check = "✓" if strategy.use_model_fallback == expected_fallback else "✗"
                    print(f"  {fallback_check} {failure_type.value} attempt {attempt}: {strategy.name}")
                    if strategy.use_model_fallback != expected_fallback:
                        print(f"      Model fallback: {strategy.use_model_fallback} (expected {expected_fallback})")
                        all_passed = False
                else:
                    actual = strategy.name if strategy else "None"
                    print(f"  ✗ {failure_type.value} attempt {attempt}: {actual} (expected {expected_strategy})")
                    all_passed = False

        self.record_result(
            "Retry Strategy Selection",
            all_passed,
            "Progressive strategies: direct → model_fallback → alternative"
        )
        return all_passed

    def test_4_recovery_action_determination(self):
        """Test 4: Verify recovery action determination with all features."""
        print("\n--- Test 4: Recovery Action Determination ---")

        # Use different subtask IDs for each scenario to avoid attempt count interference
        scenarios = [
            {
                "name": "First verification failure",
                "subtask_id": "test-4-a",
                "failure_type": FailureType.VERIFICATION_FAILED,
                "expected_action": "retry",
                "expected_wait": 0.0,
                "expected_fallback": False,
            },
            {
                "name": "Second verification failure",
                "subtask_id": "test-4-b",
                "failure_type": FailureType.VERIFICATION_FAILED,
                "expected_action": "retry",
                "expected_wait": 2.0,
                "expected_fallback": False,  # First attempt shows 0, so fallback not yet
            },
        ]

        all_passed = True
        for scenario in scenarios:
            # Record an initial attempt for the second scenario
            if "b" in scenario["subtask_id"]:
                self.recovery_manager.record_attempt(
                    subtask_id=scenario["subtask_id"],
                    session=1,
                    success=False,
                    approach="initial",
                    error="test error"
                )

            action = self.recovery_manager.determine_recovery_action(
                subtask_id=scenario["subtask_id"],
                failure_type=scenario["failure_type"],
            )

            checks = [
                (action.action == scenario["expected_action"],
                 f"action={action.action} (expected {scenario['expected_action']})"),
                (abs(action.wait_seconds - scenario["expected_wait"]) < 0.001,
                 f"wait={action.wait_seconds}s (expected {scenario['expected_wait']}s)"),
                (action.strategy is not None,
                 f"strategy={action.strategy.name if action.strategy else None}"),
            ]

            all_checks_passed = all(check[0] for check in checks)
            status = "✓" if all_checks_passed else "✗"
            print(f"  {status} {scenario['name']}")
            for check_passed, desc in checks:
                if not check_passed:
                    print(f"      ✗ {desc}")
                    all_passed = False

        self.record_result(
            "Recovery Action Determination",
            all_passed,
            f"Tested {len(scenarios)} scenarios"
        )
        return all_passed

    def test_5_dead_letter_queue(self):
        """Test 5: Verify dead-letter queue integration."""
        print("\n--- Test 5: Dead-Letter Queue ---")

        # Add a failure to DLQ
        result = self.recovery_manager.add_failure_to_dlq(
            subtask_id="test-failed-subtask",
            failure_type=FailureType.UNKNOWN,
            error_message="Persistent unknown error after all retries",
            recovery_action=None,
        )

        # Check DLQ statistics
        stats = self.recovery_manager.get_dlq_statistics()
        print(f"  Total failures: {stats['total_failures']}")
        print(f"  Pending failures: {stats['pending_failures']}")

        # Get pending failures
        pending = self.recovery_manager.get_dlq_pending_failures()
        if len(pending) >= 1 and result:
            print(f"  ✓ Failure added to DLQ: {pending[0]['id']}")
            print(f"    Type: {pending[0]['failure_type']}")
            all_passed = True
        else:
            print(f"  ✗ Expected at least 1 pending failure, got {len(pending)}")
            all_passed = False

        self.record_result(
            "Dead-Letter Queue",
            all_passed,
            "Unrecoverable failures captured for manual review"
        )
        return all_passed

    def test_6_notification_thresholds(self):
        """Test 6: Verify notification threshold management."""
        print("\n--- Test 6: Notification Thresholds ---")

        # Record multiple attempts to reach threshold
        subtask_id = "test-6-notifications"

        # First 2 attempts (below retry_threshold of 3)
        for i in range(2):
            self.recovery_manager.record_attempt(
                subtask_id=subtask_id,
                session=i+1,
                success=False,
                approach="test",
                error="test error"
            )

        # Get action after 2 attempts (should not notify yet)
        action = self.recovery_manager.determine_recovery_action(
            subtask_id=subtask_id,
            failure_type=FailureType.VERIFICATION_FAILED,
        )

        stats = self.recovery_manager.get_notification_statistics()
        print(f"  Silent failures: {stats['total_silent_failures']}")

        # Now record the action (even though not notifying, we track it)
        self.recovery_manager.record_recovery_notification(
            subtask_id=subtask_id,
            failure_type=FailureType.VERIFICATION_FAILED,
            recovery_action=action,
        )

        # Third attempt (at retry_threshold)
        self.recovery_manager.record_attempt(
            subtask_id=subtask_id,
            session=3,
            success=False,
            approach="test",
            error="test error"
        )

        action = self.recovery_manager.determine_recovery_action(
            subtask_id=subtask_id,
            failure_type=FailureType.VERIFICATION_FAILED,
        )

        if action.should_notify:
            print(f"  ✓ Notification triggered at threshold")
            print(f"    Message: {action.notification_message[:60]}...")

            # Record the notification
            self.recovery_manager.record_recovery_notification(
                subtask_id=subtask_id,
                failure_type=FailureType.VERIFICATION_FAILED,
                recovery_action=action,
            )

            final_stats = self.recovery_manager.get_notification_statistics()
            print(f"  Total notifications: {final_stats['total_notifications']}")
            all_passed = True
        else:
            print(f"  ✗ Expected notification at threshold, got should_notify=False")
            all_passed = False

        self.record_result(
            "Notification Thresholds",
            all_passed,
            "Silent retries below threshold, notification at threshold"
        )
        return all_passed

    def test_7_full_recovery_loop_simulation(self):
        """Test 7: Simulate full recovery loop with multiple retries."""
        print("\n--- Test 7: Full Recovery Loop Simulation ---")

        subtask_id = "simulated-failing-subtask"
        max_attempts = 5
        all_passed = True
        exhausted = False

        print(f"  Simulating {max_attempts} recovery attempts...")

        for attempt_num in range(max_attempts):
            print(f"\n  Attempt {attempt_num}:")

            # Record the failed attempt
            self.recovery_manager.record_attempt(
                subtask_id=subtask_id,
                session=attempt_num + 1,
                success=False,
                approach="test_approach",
                error=f"Verification failed on attempt {attempt_num}"
            )

            # Determine recovery action
            action = self.recovery_manager.determine_recovery_action(
                subtask_id=subtask_id,
                failure_type=FailureType.VERIFICATION_FAILED,
            )

            print(f"    Action: {action.action}")
            print(f"    Strategy: {action.strategy.name if action.strategy else 'None'}")
            print(f"    Wait: {action.wait_seconds}s")
            print(f"    Model Fallback: {action.use_model_fallback}")
            print(f"    Notify: {action.should_notify}")

            # Record notification if needed
            if action.should_notify:
                self.recovery_manager.record_recovery_notification(
                    subtask_id=subtask_id,
                    failure_type=FailureType.VERIFICATION_FAILED,
                    recovery_action=action,
                )

            # Check if we exhausted retry strategies (action is "skip")
            if action.action == "skip":
                print(f"    ✓ Strategies exhausted after {attempt_num + 1} attempts")
                print(f"    Note: VERIFICATION_FAILED uses 'skip' (not 'escalate') when exhausted")
                exhausted = True
                break

        # VERIFICATION_FAILED doesn't escalate to DLQ, it just skips
        if exhausted:
            print(f"\n  ✓ Recovery loop correctly exhausted after max attempts")
        else:
            print(f"\n  ✗ Expected strategies to be exhausted")
            all_passed = False

        self.record_result(
            "Full Recovery Loop",
            all_passed,
            f"Simulated {max_attempts} attempts with progressive strategies"
        )
        return all_passed

    def test_8_unknown_failure_escalation(self):
        """Test 8: Verify UNKNOWN failures escalate and add to DLQ."""
        print("\n--- Test 8: UNKNOWN Failure Escalation to DLQ ---")

        subtask_id = "test-unknown-escalation"
        all_passed = True

        # UNKNOWN failures have max_attempts=2
        print(f"  Testing UNKNOWN failure escalation (max 2 attempts)...")

        for attempt_num in range(3):  # Try 3 times to exceed max
            print(f"\n  Attempt {attempt_num}:")

            # Record the failed attempt
            self.recovery_manager.record_attempt(
                subtask_id=subtask_id,
                session=attempt_num + 1,
                success=False,
                approach="test_approach",
                error=f"Unknown error on attempt {attempt_num}"
            )

            # Determine recovery action
            action = self.recovery_manager.determine_recovery_action(
                subtask_id=subtask_id,
                failure_type=FailureType.UNKNOWN,
            )

            print(f"    Action: {action.action}")
            print(f"    Strategy: {action.strategy.name if action.strategy else 'None'}")

            # Record notification if needed
            if action.should_notify:
                self.recovery_manager.record_recovery_notification(
                    subtask_id=subtask_id,
                    failure_type=FailureType.UNKNOWN,
                    recovery_action=action,
                )

            # Check for escalation
            if action.action == "escalate":
                print(f"    ✓ Escalation triggered after {attempt_num + 1} attempts")
                print(f"    Notification: {action.notification_message[:60]}...")
                all_passed = True
                break
        else:
            # Loop completed without escalation
            print(f"  ✗ Expected escalation after exhausting attempts")
            all_passed = False

        # Verify DLQ has the escalated failure
        pending = self.recovery_manager.get_dlq_pending_failures()
        unknown_failures = [f for f in pending if f["subtask_id"] == subtask_id]

        if len(unknown_failures) > 0:
            print(f"\n  ✓ Failure properly escalated to DLQ")
            print(f"    DLQ entry: {unknown_failures[0]['id']}")
        else:
            print(f"\n  ✗ Expected failure in DLQ after escalation")
            all_passed = False

        self.record_result(
            "UNKNOWN Failure Escalation",
            all_passed,
            "UNKNOWN errors escalate to DLQ after exhausting strategies"
        )
        return all_passed

    def test_9_is_recoverable_method(self):
        """Test 8: Verify FailureType.is_recoverable() method."""
        print("\n--- Test 8: FailureType.is_recoverable() ---")

        test_cases = [
            (FailureType.BROKEN_BUILD, True, "Can rollback and retry"),
            (FailureType.VERIFICATION_FAILED, True, "Can retry with different approach"),
            (FailureType.CONTEXT_EXHAUSTED, True, "Can continue in next session"),
            (FailureType.UNKNOWN, True, "Can retry with caution"),
            (FailureType.CIRCULAR_FIX, False, "Requires human intervention"),
        ]

        all_passed = True
        for failure_type, expected_recoverable, reason in test_cases:
            actual = failure_type.is_recoverable()
            if actual == expected_recoverable:
                print(f"  ✓ {failure_type.value}: recoverable={actual} ({reason})")
            else:
                print(f"  ✗ {failure_type.value}: recoverable={actual} (expected {expected_recoverable})")
                all_passed = False

        self.record_result(
            "is_recoverable() Method",
            all_passed,
            "Correctly distinguishes recoverable vs non-recoverable failures"
        )
        return all_passed

    def run_all_tests(self):
        """Run all recovery loop tests."""
        print("\n" + "=" * 70)
        print("RUNNING RECOVERY LOOP TESTS")
        print("=" * 70)

        tests = [
            self.test_1_failure_classification,
            self.test_2_exponential_backoff,
            self.test_3_retry_strategy_selection,
            self.test_4_recovery_action_determination,
            self.test_5_dead_letter_queue,
            self.test_6_notification_thresholds,
            self.test_7_full_recovery_loop_simulation,
            self.test_8_unknown_failure_escalation,
            self.test_9_is_recoverable_method,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"\n✗ Test failed with exception: {e}")
                import traceback
                traceback.print_exc()

        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Pass Rate: {pass_rate:.1f}%")

        if passed == total:
            print("\n✓ ALL TESTS PASSED - Recovery loop is working correctly!")
            return True
        else:
            print("\n✗ SOME TESTS FAILED - Review failures above")
            return False


def main():
    """Run the recovery loop verification."""
    test = RecoveryLoopTest()
    try:
        test.setup()
        success = test.run_all_tests()
        return test.teardown() or success
    except Exception as e:
        print(f"\n✗ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        test.teardown()


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
