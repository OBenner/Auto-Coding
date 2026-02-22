"""
Smart Rollback and Recovery System
===================================

Automatic recovery from build failures, stuck loops, and broken builds.
Enables true "walk away" automation by detecting and recovering from common failure modes.

Key Features:
- Automatic rollback to last working state
- Circular fix detection (prevents infinite loops)
- Attempt history tracking across sessions
- Smart retry with different approaches
- Escalation to human when stuck
"""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from core.file_utils import write_json_atomic
from services.dead_letter_queue import DeadLetterQueue
from services.notification_manager import NotificationManager


class FailureType(Enum):
    """Types of failures that can occur during autonomous builds."""

    BROKEN_BUILD = "broken_build"  # Code doesn't compile/run
    VERIFICATION_FAILED = "verification_failed"  # Subtask verification failed
    CIRCULAR_FIX = "circular_fix"  # Same fix attempted multiple times
    CONTEXT_EXHAUSTED = "context_exhausted"  # Ran out of context mid-subtask
    UNKNOWN = "unknown"

    def is_recoverable(self) -> bool:
        """
        Determine if this failure type is automatically recoverable.

        Recoverable failures can be retried with alternative strategies
        (rollback, different approach, model fallback, etc.).

        Non-recoverable failures require human intervention or escalation.

        Returns:
            True if the failure can be automatically recovered from
        """
        # Recoverable: can rollback, retry, or continue with different approach
        recoverable_types = {
            FailureType.BROKEN_BUILD,  # Rollback to last good state and retry
            FailureType.VERIFICATION_FAILED,  # Retry with different approach
            FailureType.CONTEXT_EXHAUSTED,  # Continue in next session
            FailureType.UNKNOWN,  # Can retry with caution
        }

        return self in recoverable_types


@dataclass
class RetryStrategy:
    """Describes a retry strategy to use for recovery."""

    name: str  # Strategy identifier (e.g., "direct_retry", "model_fallback")
    description: str  # Human-readable description of what this strategy does
    use_model_fallback: bool = field(default=False)  # Try with fallback model
    guidance: str = field(default="")  # Specific guidance for the agent
    max_attempts: int = field(default=3)  # Maximum attempts for this strategy


@dataclass
class RecoveryAction:
    """Action to take in response to a failure."""

    action: str  # "rollback", "retry", "skip", "escalate"
    target: str  # commit hash, subtask id, or message
    reason: str
    wait_seconds: float = field(default=0.0)  # Exponential backoff delay before retry
    use_model_fallback: bool = field(
        default=False
    )  # Suggest trying with fallback model
    strategy: RetryStrategy | None = field(default=None)  # Selected retry strategy
    should_notify: bool = field(default=False)  # Whether to notify user
    notification_message: str = field(
        default=""
    )  # Notification message if should_notify=True


# Error Pattern Database
# ======================
# Maps failure types to their error message patterns for classification.
# Used by classify_failure() to determine the type of failure from error messages.

ERROR_PATTERNS: dict[FailureType, list[str]] = {
    FailureType.BROKEN_BUILD: [
        "syntax error",
        "compilation error",
        "module not found",
        "import error",
        "cannot find module",
        "unexpected token",
        "indentation error",
        "parse error",
        "type error",
        "reference error",
        "name error",
    ],
    FailureType.VERIFICATION_FAILED: [
        "verification failed",
        "expected",
        "assertion",
        "test failed",
        "status code",
        "timeout",
        "connection refused",
    ],
    FailureType.CONTEXT_EXHAUSTED: [
        "context",
        "token limit",
        "maximum length",
        "context window",
        "too many tokens",
    ],
}


# Exponential Backoff Configuration
# ==================================
# Prevents API rate limiting and thundering herd problems by increasing
# delay between retry attempts. Based on pattern from rate_limiter.py.

# Base delay for first retry (seconds)
BACKOFF_BASE_DELAY = 1.0

# Maximum delay cap to prevent excessively long waits (seconds)
BACKOFF_MAX_DELAY = 60.0

# Backoff multiplier (exponential growth: delay = base * multiplier^attempt)
BACKOFF_MULTIPLIER = 2.0


class RecoveryManager:
    """
    Manages recovery from build failures.

    Responsibilities:
    - Track attempt history across sessions
    - Classify failures and determine recovery actions
    - Rollback to working states
    - Detect circular fixes (same approach repeatedly)
    - Escalate stuck subtasks for human intervention
    """

    def __init__(self, spec_dir: Path, project_dir: Path):
        """
        Initialize recovery manager.

        Args:
            spec_dir: Spec directory containing memory/
            project_dir: Root project directory for git operations
        """
        self.spec_dir = spec_dir
        self.project_dir = project_dir
        self.memory_dir = spec_dir / "memory"
        self.attempt_history_file = self.memory_dir / "attempt_history.json"
        self.build_commits_file = self.memory_dir / "build_commits.json"

        # Ensure memory directory exists
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # Initialize files if they don't exist
        if not self.attempt_history_file.exists():
            self._init_attempt_history()

        if not self.build_commits_file.exists():
            self._init_build_commits()

        # Initialize dead-letter queue for unrecoverable failures
        self.dlq = DeadLetterQueue(spec_dir)

        # Initialize notification manager for user notifications
        self.notification_manager = NotificationManager(spec_dir)

    def _init_attempt_history(self) -> None:
        """Initialize the attempt history file."""
        initial_data = {
            "subtasks": {},
            "stuck_subtasks": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
            },
        }
        with open(self.attempt_history_file, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2)

    def _init_build_commits(self) -> None:
        """Initialize the build commits tracking file."""
        initial_data = {
            "commits": [],
            "last_good_commit": None,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
            },
        }
        with open(self.build_commits_file, "w", encoding="utf-8") as f:
            json.dump(initial_data, f, indent=2)

    def calculate_backoff_delay(self, attempt_count: int) -> float:
        """
        Calculate exponential backoff delay for retry attempts.

        Implements exponential backoff to prevent API rate limiting and
        thundering herd problems. Delay doubles with each attempt, capped
        at BACKOFF_MAX_DELAY.

        Formula: delay = min(base * multiplier^attempt, max_delay)
        Example progression (base=1.0, multiplier=2.0):
            - Attempt 0: 1.0s
            - Attempt 1: 2.0s
            - Attempt 2: 4.0s
            - Attempt 3: 8.0s
            - Attempt 4: 16.0s
            - Attempt 5: 32.0s
            - Attempt 6+: 60.0s (capped)

        Args:
            attempt_count: Number of previous attempts (0-indexed)

        Returns:
            Delay in seconds before next retry
        """
        if attempt_count <= 0:
            return 0.0

        # Calculate exponential delay: base * multiplier^attempt
        delay = BACKOFF_BASE_DELAY * (BACKOFF_MULTIPLIER**attempt_count)

        # Cap at maximum delay to prevent excessively long waits
        return min(delay, BACKOFF_MAX_DELAY)

    def select_retry_strategy(
        self, failure_type: FailureType, attempt_count: int, subtask_id: str
    ) -> RetryStrategy | None:
        """
        Select an appropriate retry strategy based on failure type and history.

        Strategies are selected progressively to increase chances of success:
        - Attempt 0: Direct retry (same approach)
        - Attempt 1: Model fallback (try different model)
        - Attempt 2+: Alternative approach with guidance

        For BROKEN_BUILD failures, no retry strategy is returned since
        these require rollback instead.

        Args:
            failure_type: Type of failure that occurred
            attempt_count: Number of previous attempts (0-indexed)
            subtask_id: ID of the subtask that failed

        Returns:
            RetryStrategy if retry should be attempted, None if should escalate/skip
        """
        # BROKEN_BUILD requires rollback, not retry
        if failure_type == FailureType.BROKEN_BUILD:
            return None

        # CIRCULAR_FIX should not retry (already detected repetition)
        if failure_type == FailureType.CIRCULAR_FIX:
            return None

        # CONTEXT_EXHAUSTED continues in next session (no retry strategy needed)
        if failure_type == FailureType.CONTEXT_EXHAUSTED:
            return None

        # For VERIFICATION_FAILED and UNKNOWN, select progressive strategies
        if failure_type == FailureType.VERIFICATION_FAILED:
            max_attempts = 3

            if attempt_count >= max_attempts:
                return None  # Exhausted retries

            if attempt_count == 0:
                # First attempt: direct retry
                return RetryStrategy(
                    name="direct_retry",
                    description="Retry with same approach",
                    use_model_fallback=False,
                    guidance="Review the verification error and fix the issue",
                    max_attempts=max_attempts,
                )
            elif attempt_count == 1:
                # Second attempt: try with model fallback
                return RetryStrategy(
                    name="model_fallback",
                    description="Retry with fallback model (opus→sonnet→haiku)",
                    use_model_fallback=True,
                    guidance="Use a different model which may handle this task better",
                    max_attempts=max_attempts,
                )
            else:
                # Third attempt: alternative approach with specific guidance
                return RetryStrategy(
                    name="alternative_approach",
                    description="Try a simpler or different approach",
                    use_model_fallback=True,
                    guidance=(
                        "IMPORTANT: Try a DIFFERENT approach:\n"
                        "- Use a simpler implementation\n"
                        "- Try a different library or pattern\n"
                        "- Break down into smaller steps\n"
                        "- Review previous attempt errors carefully"
                    ),
                    max_attempts=max_attempts,
                )

        elif failure_type == FailureType.UNKNOWN:
            max_attempts = 2

            if attempt_count >= max_attempts:
                return None  # Exhausted retries

            if attempt_count == 0:
                # First attempt: direct retry
                return RetryStrategy(
                    name="direct_retry",
                    description="Retry with same approach",
                    use_model_fallback=False,
                    guidance="Review the error message and fix the issue",
                    max_attempts=max_attempts,
                )
            else:
                # Second attempt: try with model fallback and alternative approach
                return RetryStrategy(
                    name="model_fallback_alternative",
                    description="Retry with fallback model and alternative approach",
                    use_model_fallback=True,
                    guidance=(
                        "Unknown error - try a different approach:\n"
                        "- Simplify the implementation\n"
                        "- Add error handling\n"
                        "- Check for edge cases\n"
                        "- Verify dependencies are available"
                    ),
                    max_attempts=max_attempts,
                )

        return None

    def _load_attempt_history(self) -> dict:
        """Load attempt history from JSON file."""
        try:
            with open(self.attempt_history_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            self._init_attempt_history()
            with open(self.attempt_history_file, encoding="utf-8") as f:
                return json.load(f)

    def _save_attempt_history(self, data: dict) -> None:
        """Save attempt history to JSON file."""
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        with open(self.attempt_history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_build_commits(self) -> dict:
        """Load build commits from JSON file."""
        try:
            with open(self.build_commits_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            self._init_build_commits()
            with open(self.build_commits_file, encoding="utf-8") as f:
                return json.load(f)

    def _save_build_commits(self, data: dict) -> None:
        """Save build commits to JSON file."""
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        with open(self.build_commits_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def classify_failure(self, error: str, subtask_id: str) -> FailureType:
        """
        Classify what type of failure occurred using the error pattern database.

        Args:
            error: Error message or description
            subtask_id: ID of the subtask that failed

        Returns:
            FailureType enum value
        """
        error_lower = error.lower()

        # Check against error pattern database
        # Iterate through known failure types and their patterns
        for failure_type, patterns in ERROR_PATTERNS.items():
            if any(pattern in error_lower for pattern in patterns):
                return failure_type

        # Check for circular fixes (determined by attempt history, not error patterns)
        if self.is_circular_fix(subtask_id, error):
            return FailureType.CIRCULAR_FIX

        # No pattern matched - return unknown
        return FailureType.UNKNOWN

    def should_escalate_early(
        self, subtask_id: str, failure_type: FailureType, error: str
    ) -> tuple[bool, str]:
        """
        Determine if a subtask should be escalated before normal retry limits.

        Proactively identifies high-risk situations that warrant early escalation:
        - Multiple different failure types (indicates complexity)
        - Repeated circular fix patterns
        - Context exhaustion with high attempt count
        - Error patterns indicating fundamental architectural issues

        Args:
            subtask_id: ID of the subtask to evaluate
            failure_type: Current failure type
            error: Current error message

        Returns:
            Tuple of (should_escalate: bool, reason: str)
        """
        history = self._load_attempt_history()
        subtask_data = history["subtasks"].get(subtask_id, {})
        attempts = subtask_data.get("attempts", [])

        # No history yet, don't escalate
        if not attempts:
            return False, ""

        attempt_count = len(attempts)

        # Check for multiple different failure types
        failure_types_seen = set()
        for attempt in attempts:
            if attempt.get("error"):
                attempt_failure = self.classify_failure(attempt["error"], subtask_id)
                failure_types_seen.add(attempt_failure)

        # Add current failure type
        failure_types_seen.add(failure_type)

        # If we've seen 3+ different failure types, escalate early
        # This indicates the problem is complex and not a simple retry scenario
        if len(failure_types_seen) >= 3:
            return (
                True,
                f"Multiple failure types encountered ({len(failure_types_seen)} unique types): "
                f"{', '.join(ft.value for ft in failure_types_seen)}. "
                f"This suggests a complex issue requiring human intervention.",
            )

        # Check for repeated circular fix patterns across attempts
        circular_count = 0
        for i, attempt in enumerate(attempts):
            if attempt.get("error") and self.is_circular_fix(
                subtask_id, attempt.get("approach", "")
            ):
                circular_count += 1

        # If 2+ attempts show circular patterns, escalate immediately
        if circular_count >= 2:
            return (
                True,
                f"Repeated circular fix patterns detected in {circular_count} attempts. "
                f"The agent is stuck in a loop and needs human guidance to break the cycle.",
            )

        # Context exhaustion with moderate attempt count warrants early escalation
        if failure_type == FailureType.CONTEXT_EXHAUSTED and attempt_count >= 2:
            return (
                True,
                f"Context exhausted after {attempt_count} attempts. "
                f"The task may be too complex for current context limits.",
            )

        # Broken build after 3+ attempts with different approaches
        if failure_type == FailureType.BROKEN_BUILD and attempt_count >= 3:
            # Check if approaches were actually different
            approaches = [a.get("approach", "") for a in attempts]
            unique_approaches = set(approaches)

            if len(unique_approaches) >= 2:
                return (
                    True,
                    f"Build remains broken after {attempt_count} attempts with {len(unique_approaches)} "
                    f"different approaches. This may indicate a fundamental architectural issue.",
                )

        # Check for error patterns indicating deeper issues
        deep_issue_keywords = [
            "permission denied",
            "access denied",
            "authentication",
            "authorization",
            "network",
            "timeout",
            "deadlock",
            "race condition",
            "corruption",
            "incompatible",
        ]

        error_lower = error.lower()
        if any(keyword in error_lower for keyword in deep_issue_keywords):
            if attempt_count >= 2:
                return (
                    True,
                    f"Error suggests infrastructure or configuration issue: '{error[:100]}'. "
                    f"Requires human investigation after {attempt_count} attempts.",
                )

        return False, ""

    def get_attempt_count(self, subtask_id: str) -> int:
        """
        Get how many times this subtask has been attempted.

        Args:
            subtask_id: ID of the subtask

        Returns:
            Number of attempts
        """
        history = self._load_attempt_history()
        subtask_data = history["subtasks"].get(subtask_id, {})
        return len(subtask_data.get("attempts", []))

    def record_attempt(
        self,
        subtask_id: str,
        session: int,
        success: bool,
        approach: str,
        error: str | None = None,
    ) -> None:
        """
        Record an attempt at a subtask.

        Args:
            subtask_id: ID of the subtask
            session: Session number
            success: Whether the attempt succeeded
            approach: Description of the approach taken
            error: Error message if failed
        """
        history = self._load_attempt_history()

        # Initialize subtask entry if it doesn't exist
        if subtask_id not in history["subtasks"]:
            history["subtasks"][subtask_id] = {"attempts": [], "status": "pending"}

        # Add the attempt
        attempt = {
            "session": session,
            "timestamp": datetime.now().isoformat(),
            "approach": approach,
            "success": success,
            "error": error,
        }
        history["subtasks"][subtask_id]["attempts"].append(attempt)

        # Update status
        if success:
            history["subtasks"][subtask_id]["status"] = "completed"
        else:
            history["subtasks"][subtask_id]["status"] = "failed"

        self._save_attempt_history(history)

    def is_circular_fix(self, subtask_id: str, current_approach: str) -> bool:
        """
        Detect if we're trying the same approach repeatedly.

        Args:
            subtask_id: ID of the subtask
            current_approach: Description of current approach

        Returns:
            True if this appears to be a circular fix attempt
        """
        history = self._load_attempt_history()
        subtask_data = history["subtasks"].get(subtask_id, {})
        attempts = subtask_data.get("attempts", [])

        if len(attempts) < 2:
            return False

        # Check if last 3 attempts used similar approaches
        # Simple similarity check: look for repeated keywords
        recent_attempts = attempts[-3:] if len(attempts) >= 3 else attempts

        # Extract key terms from current approach (ignore common words)
        stop_words = {
            "with",
            "using",
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "trying",
        }
        current_keywords = set(
            word for word in current_approach.lower().split() if word not in stop_words
        )

        similar_count = 0
        for attempt in recent_attempts:
            attempt_keywords = set(
                word
                for word in attempt["approach"].lower().split()
                if word not in stop_words
            )

            # Calculate Jaccard similarity (intersection over union)
            overlap = len(current_keywords & attempt_keywords)
            total = len(current_keywords | attempt_keywords)

            if total > 0:
                similarity = overlap / total
                # If >30% of meaningful words overlap, consider it similar
                # This catches key technical terms appearing repeatedly
                # (e.g., "async await" across multiple attempts)
                if similarity > 0.3:
                    similar_count += 1

        # If 2+ recent attempts were similar to current approach, it's circular
        return similar_count >= 2

    def determine_recovery_action(
        self, failure_type: FailureType, subtask_id: str
    ) -> RecoveryAction:
        """
        Decide what to do based on failure type and history.

        Uses select_retry_strategy() to choose appropriate retry strategies
        including model fallback, alternative approaches, and simpler implementations.
        Applies exponential backoff to prevent API rate limiting.

        Integrates with NotificationManager to determine when to notify users:
        - Silent retries below retry_threshold (default: 3 attempts)
        - Notify at threshold and every N attempts after
        - Escalate to human at escalation_threshold (default: 5 attempts)

        Strategy Progression:
        - Attempt 0: Direct retry with same approach
        - Attempt 1: Model fallback (opus -> sonnet -> haiku)
        - Attempt 2+: Alternative approach with guidance

        Args:
            failure_type: Type of failure that occurred
            subtask_id: ID of the subtask that failed

        Returns:
            RecoveryAction describing what to do (includes wait_seconds, strategy,
            use_model_fallback flag, and notification info)
        """
        attempt_count = self.get_attempt_count(subtask_id)

        # Check notification thresholds
        should_notify = self.notification_manager.should_notify(
            subtask_id=subtask_id,
            attempt_count=attempt_count,
            failure_type=failure_type.value,
        )
        should_escalate = self.notification_manager.should_escalate(attempt_count)

        # Special case: BROKEN_BUILD requires rollback
        if failure_type == FailureType.BROKEN_BUILD:
            last_good = self.get_last_good_commit()
            if last_good:
                notification_msg = (
                    f"Auto-recovery: Build broken in {subtask_id}, "
                    f"rolling back to working state (attempt {attempt_count + 1})"
                )
                return RecoveryAction(
                    action="rollback",
                    target=last_good,
                    reason=f"Build broken in subtask {subtask_id}, rolling back to working state",
                    should_notify=should_notify,
                    notification_message=notification_msg,
                )
            else:
                # Add to DLQ before escalating
                notification_msg = (
                    f"ESCALATION REQUIRED: Build broken in {subtask_id} "
                    f"and no good commit found to rollback to (attempt {attempt_count + 1})"
                )
                action = RecoveryAction(
                    action="escalate",
                    target=subtask_id,
                    reason="Build broken and no good commit found to rollback to",
                    should_notify=True,  # Always notify on escalation
                    notification_message=notification_msg,
                )
                self.add_failure_to_dlq(
                    subtask_id=subtask_id,
                    failure_type=failure_type,
                    error_message=action.reason,
                    recovery_action=action,
                )
                return action

        # Special case: CIRCULAR_FIX should skip (no retry)
        if failure_type == FailureType.CIRCULAR_FIX:
            notification_msg = (
                f"Auto-recovery: Circular fix detected in {subtask_id} - "
                f"same approach tried multiple times, skipping"
            )
            return RecoveryAction(
                action="skip",
                target=subtask_id,
                reason="Circular fix detected - same approach tried multiple times",
                should_notify=should_notify,
                notification_message=notification_msg,
            )

        # Special case: CONTEXT_EXHAUSTED continues in next session
        if failure_type == FailureType.CONTEXT_EXHAUSTED:
            notification_msg = (
                f"Auto-recovery: Context exhausted in {subtask_id}, "
                f"will commit progress and continue in next session"
            )
            return RecoveryAction(
                action="continue",
                target=subtask_id,
                reason="Context exhausted, will commit progress and continue in next session",
                should_notify=should_notify,
                notification_message=notification_msg,
            )

        # For other failure types, use strategy selection
        strategy = self.select_retry_strategy(failure_type, attempt_count, subtask_id)

        if strategy:
            # Retry with selected strategy
            backoff_delay = self.calculate_backoff_delay(attempt_count)
            notification_msg = (
                f"Auto-recovery: {failure_type.value} in {subtask_id}, "
                f"{strategy.description} (attempt {attempt_count + 1}/{strategy.max_attempts})"
            )
            if backoff_delay > 0:
                notification_msg += f" - waiting {backoff_delay:.1f}s before retry"

            return RecoveryAction(
                action="retry",
                target=subtask_id,
                reason=(
                    f"{failure_type.value}: {strategy.description} "
                    f"(attempt {attempt_count + 1}/{strategy.max_attempts})"
                ),
                wait_seconds=backoff_delay,
                use_model_fallback=strategy.use_model_fallback,
                strategy=strategy,
                should_notify=should_notify or should_escalate,
                notification_message=notification_msg,
            )
        else:
            # No more strategies available - escalate or skip
            if failure_type == FailureType.VERIFICATION_FAILED:
                notification_msg = (
                    f"Auto-recovery: Verification failed in {subtask_id} "
                    f"after {attempt_count} attempts, marking as stuck"
                )
                return RecoveryAction(
                    action="skip",
                    target=subtask_id,
                    reason=f"Verification failed after {attempt_count} attempts, marking as stuck",
                    should_notify=True,  # Always notify when giving up
                    notification_message=notification_msg,
                )
            else:  # UNKNOWN
                # Add to DLQ before escalating
                notification_msg = (
                    f"ESCALATION REQUIRED: Unknown error in {subtask_id} "
                    f"persists after {attempt_count} attempts"
                )
                action = RecoveryAction(
                    action="escalate",
                    target=subtask_id,
                    reason=f"Unknown error persists after {attempt_count} attempts",
                    should_notify=True,  # Always notify on escalation
                    notification_message=notification_msg,
                )
                self.add_failure_to_dlq(
                    subtask_id=subtask_id,
                    failure_type=failure_type,
                    error_message=action.reason,
                    recovery_action=action,
                )
                return action

    def get_last_good_commit(self) -> str | None:
        """
        Find the most recent commit where build was working.

        Returns:
            Commit hash or None
        """
        commits = self._load_build_commits()
        return commits.get("last_good_commit")

    def record_good_commit(self, commit_hash: str, subtask_id: str) -> None:
        """
        Record a commit where the build was working.

        Args:
            commit_hash: Git commit hash
            subtask_id: Subtask that was successfully completed
        """
        commits = self._load_build_commits()

        commit_record = {
            "hash": commit_hash,
            "subtask_id": subtask_id,
            "timestamp": datetime.now().isoformat(),
        }

        commits["commits"].append(commit_record)
        commits["last_good_commit"] = commit_hash

        self._save_build_commits(commits)

    def rollback_to_commit(self, commit_hash: str) -> bool:
        """
        Rollback to a specific commit.

        Args:
            commit_hash: Git commit hash to rollback to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use git reset --hard to rollback
            subprocess.run(
                ["git", "reset", "--hard", commit_hash],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error rolling back to {commit_hash}: {e.stderr}")
            return False

    def mark_subtask_stuck(self, subtask_id: str, reason: str) -> None:
        """
        Mark a subtask as needing human intervention.

        Args:
            subtask_id: ID of the subtask
            reason: Why it's stuck
        """
        history = self._load_attempt_history()

        stuck_entry = {
            "subtask_id": subtask_id,
            "reason": reason,
            "escalated_at": datetime.now().isoformat(),
            "attempt_count": self.get_attempt_count(subtask_id),
        }

        # Check if already in stuck list
        existing = [
            s for s in history["stuck_subtasks"] if s["subtask_id"] == subtask_id
        ]
        if not existing:
            history["stuck_subtasks"].append(stuck_entry)

        # Update subtask status
        if subtask_id in history["subtasks"]:
            history["subtasks"][subtask_id]["status"] = "stuck"

        self._save_attempt_history(history)

        # Also update the subtask status in implementation_plan.json
        # so that other callers (like is_build_ready_for_qa) see accurate status
        try:
            plan_file = self.spec_dir / "implementation_plan.json"
            if plan_file.exists():
                with open(plan_file, encoding="utf-8") as f:
                    plan = json.load(f)

                updated = False
                for phase in plan.get("phases", []):
                    for subtask in phase.get("subtasks", []):
                        if subtask.get("id") == subtask_id:
                            subtask["status"] = "failed"
                            stuck_note = f"Marked as stuck: {reason}"
                            existing = subtask.get("actual_output", "")
                            subtask["actual_output"] = (
                                f"{stuck_note}\n{existing}" if existing else stuck_note
                            )
                            updated = True
                            break
                    if updated:
                        break

                if updated:
                    write_json_atomic(plan_file, plan, indent=2)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            pass  # Non-fatal: plan update is best-effort

    def add_failure_to_dlq(
        self,
        subtask_id: str,
        failure_type: FailureType,
        error_message: str,
        recovery_action: RecoveryAction | None = None,
    ) -> bool:
        """
        Add a failure to the dead-letter queue for manual review.

        Called when recovery is escalated and no automatic recovery is possible.
        Captures full context including attempt history for debugging.

        Args:
            subtask_id: ID of the subtask that failed
            failure_type: Type of failure that occurred
            error_message: Error message or description
            recovery_action: Last recovery action attempted (optional)

        Returns:
            True if added to DLQ successfully
        """
        attempt_count = self.get_attempt_count(subtask_id)
        subtask_history = self.get_subtask_history(subtask_id)

        # Build context for debugging
        context = {
            "attempts": subtask_history.get("attempts", []),
            "status": subtask_history.get("status", "unknown"),
            "last_attempt": (
                subtask_history["attempts"][-1]
                if subtask_history.get("attempts")
                else None
            ),
        }

        # Add to DLQ
        return self.dlq.add_failure(
            subtask_id=subtask_id,
            failure_type=failure_type.value,
            error_message=error_message,
            attempt_count=attempt_count,
            recovery_action=recovery_action.action if recovery_action else None,
            context=context,
        )

    def get_stuck_subtasks(self) -> list[dict]:
        """
        Get all subtasks marked as stuck.

        Returns:
            List of stuck subtask entries
        """
        history = self._load_attempt_history()
        return history.get("stuck_subtasks", [])

    def get_subtask_history(self, subtask_id: str) -> dict:
        """
        Get the attempt history for a specific subtask.

        Args:
            subtask_id: ID of the subtask

        Returns:
            Subtask history dict with attempts
        """
        history = self._load_attempt_history()
        return history["subtasks"].get(
            subtask_id, {"attempts": [], "status": "pending"}
        )

    def get_recovery_hints(self, subtask_id: str) -> list[str]:
        """
        Get hints for recovery based on previous attempts.

        Args:
            subtask_id: ID of the subtask

        Returns:
            List of hint strings
        """
        subtask_history = self.get_subtask_history(subtask_id)
        attempts = subtask_history.get("attempts", [])

        if not attempts:
            return ["This is the first attempt at this subtask"]

        hints = [f"Previous attempts: {len(attempts)}"]

        # Add info about what was tried
        for i, attempt in enumerate(attempts[-3:], 1):
            hints.append(
                f"Attempt {i}: {attempt['approach']} - "
                f"{'SUCCESS' if attempt['success'] else 'FAILED'}"
            )
            if attempt.get("error"):
                hints.append(f"  Error: {attempt['error'][:100]}")

        # Add guidance
        if len(attempts) >= 2:
            hints.append(
                "\n⚠️  IMPORTANT: Try a DIFFERENT approach than previous attempts"
            )
            hints.append(
                "Consider: different library, different pattern, or simpler implementation"
            )

        return hints

    def record_outcome(
        self, subtask_id: str, success: bool, error: str | None = None
    ) -> None:
        """
        Record the outcome of the most recent attempt for a subtask.

        Updates the last recorded attempt with the success/failure result.

        Args:
            subtask_id: ID of the subtask
            success: Whether the attempt succeeded
            error: Error message if failed
        """
        history = self._load_attempt_history()
        subtask_data = history["subtasks"].get(subtask_id)

        if subtask_data and subtask_data["attempts"]:
            # Update the last attempt with the outcome
            subtask_data["attempts"][-1]["success"] = success
            if error:
                subtask_data["attempts"][-1]["error"] = error

            # Update subtask status
            subtask_data["status"] = "completed" if success else "failed"
            self._save_attempt_history(history)

    def clear_stuck_subtasks(self) -> None:
        """Clear all stuck subtasks (for manual resolution)."""
        history = self._load_attempt_history()
        history["stuck_subtasks"] = []
        self._save_attempt_history(history)

    def reset_subtask(self, subtask_id: str) -> None:
        """
        Reset a subtask's attempt history.

        Args:
            subtask_id: ID of the subtask to reset
        """
        history = self._load_attempt_history()

        # Clear attempt history
        if subtask_id in history["subtasks"]:
            history["subtasks"][subtask_id] = {"attempts": [], "status": "pending"}

        # Remove from stuck subtasks
        history["stuck_subtasks"] = [
            s for s in history["stuck_subtasks"] if s["subtask_id"] != subtask_id
        ]

        self._save_attempt_history(history)

    def get_dlq_pending_failures(self) -> list[dict]:
        """
        Get all pending failures from the dead-letter queue.

        Returns:
            List of pending failure records
        """
        return self.dlq.get_pending_failures()

    def get_dlq_statistics(self) -> dict:
        """
        Get dead-letter queue statistics.

        Returns:
            Dict with DLQ statistics including pending count,
            total failures, resolution rate, etc.
        """
        return self.dlq.get_statistics()

    def export_dlq_report(self, output_path: Path | str | None = None) -> str:
        """
        Export dead-letter queue failures to a human-readable report.

        Args:
            output_path: Optional path to save the report

        Returns:
            Formatted report as string
        """
        return self.dlq.export_pending_failures(output_path)

    def record_recovery_notification(
        self,
        subtask_id: str,
        failure_type: FailureType,
        recovery_action: RecoveryAction,
    ) -> bool:
        """
        Record a notification or silent failure based on recovery action.

        Should be called after determine_recovery_action() to track
        whether the user was notified or if this was a silent retry.

        Args:
            subtask_id: ID of the subtask that failed
            failure_type: Type of failure that occurred
            recovery_action: Recovery action that was taken

        Returns:
            True if recorded successfully
        """
        attempt_count = self.get_attempt_count(subtask_id)

        if recovery_action.should_notify:
            # Record that a notification was sent
            is_escalated = recovery_action.action == "escalate"
            return self.notification_manager.record_notification(
                subtask_id=subtask_id,
                attempt_count=attempt_count,
                failure_type=failure_type.value,
                message=recovery_action.notification_message,
                escalated=is_escalated,
            )
        else:
            # Record as silent failure (below notification threshold)
            return self.notification_manager.record_silent_failure(
                subtask_id=subtask_id,
                attempt_count=attempt_count,
                failure_type=failure_type.value,
            )

    def get_notification_statistics(self) -> dict:
        """
        Get notification statistics.

        Returns:
            Dict with notification statistics including notification rate,
            escalation rate, thresholds, etc.
        """
        return self.notification_manager.get_statistics()

    def get_notifications_for_subtask(self, subtask_id: str) -> list[dict]:
        """
        Get all notifications sent for a specific subtask.

        Args:
            subtask_id: Subtask ID to filter by

        Returns:
            List of notification records for the subtask
        """
        return self.notification_manager.get_notifications_for_subtask(subtask_id)

    def get_recent_notifications(self, limit: int = 10) -> list[dict]:
        """
        Get recent notifications.

        Args:
            limit: Maximum number of notifications to return

        Returns:
            List of recent notification records
        """
        return self.notification_manager.get_recent_notifications(limit)

    def update_notification_thresholds(
        self,
        retry_threshold: int | None = None,
        escalation_threshold: int | None = None,
    ) -> bool:
        """
        Update notification thresholds.

        Args:
            retry_threshold: New retry threshold (notify after N retries)
            escalation_threshold: New escalation threshold (escalate after N retries)

        Returns:
            True if updated successfully
        """
        return self.notification_manager.update_thresholds(
            retry_threshold=retry_threshold,
            escalation_threshold=escalation_threshold,
        )


# Utility functions for integration with agent.py


def check_and_recover(
    spec_dir: Path, project_dir: Path, subtask_id: str, error: str | None = None
) -> RecoveryAction | None:
    """
    Check if recovery is needed and return appropriate action.

    Args:
        spec_dir: Spec directory
        project_dir: Project directory
        subtask_id: Current subtask ID
        error: Error message if any

    Returns:
        RecoveryAction if recovery needed, None otherwise
    """
    if not error:
        return None

    manager = RecoveryManager(spec_dir, project_dir)
    failure_type = manager.classify_failure(error, subtask_id)

    return manager.determine_recovery_action(failure_type, subtask_id)


def get_recovery_context(spec_dir: Path, project_dir: Path, subtask_id: str) -> dict:
    """
    Get recovery context for a subtask (for prompt generation).

    Args:
        spec_dir: Spec directory
        project_dir: Project directory
        subtask_id: Subtask ID

    Returns:
        Dict with recovery hints and history
    """
    manager = RecoveryManager(spec_dir, project_dir)

    return {
        "attempt_count": manager.get_attempt_count(subtask_id),
        "hints": manager.get_recovery_hints(subtask_id),
        "subtask_history": manager.get_subtask_history(subtask_id),
        "stuck_subtasks": manager.get_stuck_subtasks(),
    }
