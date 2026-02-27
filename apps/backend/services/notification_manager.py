"""
Notification Manager with Retry Thresholds
===========================================

Manages user notification thresholds to reduce noise during auto-recovery.
Only notifies users after N retries, not on every failure.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Configuration
NOTIFICATIONS_FILE = "notifications.json"
DEFAULT_RETRY_THRESHOLD = 3  # Notify after 3 failed retries
DEFAULT_ESCALATION_THRESHOLD = 5  # Escalate after 5 failed retries


# =============================================================================
# NOTIFICATION MANAGER CLASS
# =============================================================================


class NotificationManager:
    """
    Manages notification thresholds and tracking.

    Stores notification settings and history in spec_dir/notifications.json
    and provides methods for determining when to notify users.
    """

    def __init__(
        self,
        spec_dir: Path | None = None,
        retry_threshold: int = DEFAULT_RETRY_THRESHOLD,
        escalation_threshold: int = DEFAULT_ESCALATION_THRESHOLD,
    ):
        """
        Initialize notification manager.

        Args:
            spec_dir: Spec directory (uses current directory if None)
            retry_threshold: Number of retries before notifying user
            escalation_threshold: Number of retries before escalating to human
        """
        self.spec_dir = spec_dir or Path.cwd()
        self._notifications_file = self.spec_dir / NOTIFICATIONS_FILE
        self.retry_threshold = retry_threshold
        self.escalation_threshold = escalation_threshold
        self._data = self._load_data()

    def _load_data(self) -> dict[str, Any]:
        """
        Load notification data from notifications.json.

        Returns:
            Data dict, initializes empty structure if file doesn't exist
        """
        if not self._notifications_file.exists():
            return self._create_empty_data()

        try:
            with open(self._notifications_file, encoding="utf-8") as f:
                data = json.load(f)
                # Validate structure
                required_keys = [
                    "settings",
                    "notifications",
                    "silent_failures",
                    "metadata",
                ]
                if all(key in data for key in required_keys):
                    # Update thresholds from loaded settings
                    self.retry_threshold = data["settings"].get(
                        "retry_threshold", DEFAULT_RETRY_THRESHOLD
                    )
                    self.escalation_threshold = data["settings"].get(
                        "escalation_threshold", DEFAULT_ESCALATION_THRESHOLD
                    )
                    return data
                # If invalid, create new
                return self._create_empty_data()
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return self._create_empty_data()

    def _create_empty_data(self) -> dict[str, Any]:
        """
        Create empty notification data structure.

        Returns:
            Dict with initialized notification tracking
        """
        return {
            "settings": {
                "retry_threshold": self.retry_threshold,
                "escalation_threshold": self.escalation_threshold,
            },
            "notifications": [],  # Notifications sent to user
            "silent_failures": [],  # Failures below threshold (no notification)
            "metadata": {
                "created_at": datetime.now(UTC).isoformat(),
                "last_updated": datetime.now(UTC).isoformat(),
                "total_notifications": 0,
                "total_silent_failures": 0,
            },
        }

    def _save_data(self) -> bool:
        """
        Save notification data to notifications.json atomically.

        Uses a temp file + os.replace to prevent corruption on crash.

        Returns:
            True if saved successfully
        """
        try:
            self._data["metadata"]["last_updated"] = datetime.now(UTC).isoformat()
            # Update settings in case thresholds changed
            self._data["settings"]["retry_threshold"] = self.retry_threshold
            self._data["settings"]["escalation_threshold"] = self.escalation_threshold

            tmp_file = self._notifications_file.with_suffix(".json.tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_file, self._notifications_file)
            return True
        except (OSError, TypeError, UnicodeDecodeError):
            return False

    # -------------------------------------------------------------------------
    # THRESHOLD CHECKING METHODS
    # -------------------------------------------------------------------------

    def should_notify(
        self,
        subtask_id: str,
        attempt_count: int,
        failure_type: str,
    ) -> bool:
        """
        Check if user should be notified for this failure.

        Notifications are sent when:
        - Attempt count reaches retry_threshold
        - Every N attempts after threshold (to provide progress updates)

        Args:
            subtask_id: Subtask that failed
            attempt_count: Number of retry attempts so far
            failure_type: Type of failure

        Returns:
            True if user should be notified
        """
        # Always notify on first threshold breach
        if attempt_count == self.retry_threshold:
            return True

        # After threshold, notify every N attempts for progress
        if attempt_count > self.retry_threshold:
            # Notify every retry_threshold attempts
            # (e.g., if threshold=3, notify at 3, 6, 9, 12...)
            return (attempt_count % self.retry_threshold) == 0

        # Below threshold - silent
        return False

    def should_escalate(self, attempt_count: int) -> bool:
        """
        Check if failure should be escalated to human intervention.

        Args:
            attempt_count: Number of retry attempts so far

        Returns:
            True if should escalate to human
        """
        return attempt_count >= self.escalation_threshold

    # -------------------------------------------------------------------------
    # RECORDING METHODS
    # -------------------------------------------------------------------------

    def record_notification(
        self,
        subtask_id: str,
        attempt_count: int,
        failure_type: str,
        message: str,
        escalated: bool = False,
    ) -> bool:
        """
        Record that a notification was sent to the user.

        Args:
            subtask_id: Subtask that failed
            attempt_count: Number of retry attempts
            failure_type: Type of failure
            message: Notification message sent
            escalated: Whether this was an escalation notification

        Returns:
            True if recorded successfully
        """
        notification_record = {
            "id": f"notif-{self._data['metadata']['total_notifications'] + 1}",
            "subtask_id": subtask_id,
            "attempt_count": attempt_count,
            "failure_type": failure_type,
            "message": message,
            "escalated": escalated,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self._data["notifications"].append(notification_record)
        self._data["metadata"]["total_notifications"] += 1

        return self._save_data()

    def record_silent_failure(
        self,
        subtask_id: str,
        attempt_count: int,
        failure_type: str,
    ) -> bool:
        """
        Record a failure that did not trigger a notification.

        Args:
            subtask_id: Subtask that failed
            attempt_count: Number of retry attempts
            failure_type: Type of failure

        Returns:
            True if recorded successfully
        """
        silent_record = {
            "subtask_id": subtask_id,
            "attempt_count": attempt_count,
            "failure_type": failure_type,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        self._data["silent_failures"].append(silent_record)
        self._data["metadata"]["total_silent_failures"] += 1

        return self._save_data()

    # -------------------------------------------------------------------------
    # RETRIEVAL METHODS
    # -------------------------------------------------------------------------

    def get_notifications_for_subtask(self, subtask_id: str) -> list[dict[str, Any]]:
        """
        Get all notifications for a specific subtask.

        Args:
            subtask_id: Subtask ID to filter by

        Returns:
            List of notification records for the subtask
        """
        return [
            n for n in self._data["notifications"] if n.get("subtask_id") == subtask_id
        ]

    def get_recent_notifications(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent notifications.

        Args:
            limit: Maximum number of notifications to return

        Returns:
            List of recent notification records
        """
        return self._data["notifications"][-limit:]

    def get_escalated_notifications(self) -> list[dict[str, Any]]:
        """
        Get all escalated notifications.

        Returns:
            List of notification records where escalated=True
        """
        return [n for n in self._data["notifications"] if n.get("escalated", False)]

    # -------------------------------------------------------------------------
    # STATISTICS METHODS
    # -------------------------------------------------------------------------

    def get_notification_rate(self) -> float:
        """
        Calculate notification rate (notifications / total failures).

        Returns:
            Notification rate as percentage (0-100)
        """
        total_failures = (
            self._data["metadata"]["total_notifications"]
            + self._data["metadata"]["total_silent_failures"]
        )

        if total_failures == 0:
            return 0.0

        return self._data["metadata"]["total_notifications"] / total_failures * 100

    def get_escalation_rate(self) -> float:
        """
        Calculate escalation rate (escalations / total notifications).

        Returns:
            Escalation rate as percentage (0-100)
        """
        total_notifications = self._data["metadata"]["total_notifications"]

        if total_notifications == 0:
            return 0.0

        escalated = len(self.get_escalated_notifications())
        return escalated / total_notifications * 100

    def get_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive notification statistics.

        Returns:
            Dict with notification statistics
        """
        return {
            "total_notifications": self._data["metadata"]["total_notifications"],
            "total_silent_failures": self._data["metadata"]["total_silent_failures"],
            "notification_rate": round(self.get_notification_rate(), 2),
            "escalation_rate": round(self.get_escalation_rate(), 2),
            "retry_threshold": self.retry_threshold,
            "escalation_threshold": self.escalation_threshold,
            "recent_notifications": len(self.get_recent_notifications(limit=5)),
            "created_at": self._data["metadata"]["created_at"],
            "last_updated": self._data["metadata"]["last_updated"],
        }

    # -------------------------------------------------------------------------
    # CONFIGURATION METHODS
    # -------------------------------------------------------------------------

    def update_thresholds(
        self,
        retry_threshold: int | None = None,
        escalation_threshold: int | None = None,
    ) -> bool:
        """
        Update notification thresholds.

        Args:
            retry_threshold: New retry threshold (optional)
            escalation_threshold: New escalation threshold (optional)

        Returns:
            True if updated successfully
        """
        if retry_threshold is not None:
            self.retry_threshold = retry_threshold

        if escalation_threshold is not None:
            self.escalation_threshold = escalation_threshold

        return self._save_data()
