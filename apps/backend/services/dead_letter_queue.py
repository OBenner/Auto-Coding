"""
Dead-Letter Queue for Unrecoverable Failures
=============================================

Captures failures that cannot be automatically recovered for manual review.
Stores failure context, history, and recovery attempts to help humans debug.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Configuration
DLQ_FILE = "dead_letter_queue.json"


# =============================================================================
# DEAD-LETTER QUEUE CLASS
# =============================================================================


class DeadLetterQueue:
    """
    Manages dead-letter queue for unrecoverable failures.

    Stores failures in spec_dir/dead_letter_queue.json and provides
    methods for adding, retrieving, and resolving failures.
    """

    def __init__(self, spec_dir: Path | None = None):
        """
        Initialize dead-letter queue.

        Args:
            spec_dir: Spec directory (uses current directory if None)
        """
        self.spec_dir = spec_dir or Path.cwd()
        self._dlq_file = self.spec_dir / DLQ_FILE
        self._queue = self._load_queue()

    def _load_queue(self) -> dict[str, Any]:
        """
        Load queue from dead_letter_queue.json.

        Returns:
            Queue dict, initializes empty structure if file doesn't exist
        """
        if not self._dlq_file.exists():
            return self._create_empty_queue()

        try:
            with open(self._dlq_file, encoding="utf-8") as f:
                data = json.load(f)
                # Validate structure
                required_keys = ["failures", "resolved", "metadata"]
                if all(key in data for key in required_keys):
                    return data
                # If invalid, create new
                return self._create_empty_queue()
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return self._create_empty_queue()

    def _create_empty_queue(self) -> dict[str, Any]:
        """
        Create empty queue structure.

        Returns:
            Dict with initialized queue structure
        """
        return {
            "failures": [],
            "resolved": [],
            "metadata": {
                "created_at": datetime.now(UTC).isoformat(),
                "last_updated": datetime.now(UTC).isoformat(),
                "total_failures": 0,
                "total_resolved": 0,
            },
        }

    def _save_queue(self) -> bool:
        """
        Save queue to dead_letter_queue.json atomically.

        Uses a temp file + os.replace to prevent corruption on crash.

        Returns:
            True if saved successfully
        """
        try:
            self._queue["metadata"]["last_updated"] = datetime.now(UTC).isoformat()
            tmp_file = self._dlq_file.with_suffix(".json.tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._queue, f, indent=2, ensure_ascii=False)
            os.replace(tmp_file, self._dlq_file)
            return True
        except (OSError, TypeError, UnicodeDecodeError):
            return False

    # -------------------------------------------------------------------------
    # QUEUE MANAGEMENT METHODS
    # -------------------------------------------------------------------------

    def add_failure(
        self,
        subtask_id: str,
        failure_type: str,
        error_message: str,
        attempt_count: int,
        recovery_action: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Add a failure to the dead-letter queue.

        Args:
            subtask_id: ID of the subtask that failed
            failure_type: Type of failure (e.g., "circular_fix", "unknown")
            error_message: Error message or description
            attempt_count: Number of attempts made before giving up
            recovery_action: Last recovery action attempted (optional)
            context: Additional context for debugging (optional)

        Returns:
            True if added successfully
        """
        failure_record = {
            "id": f"dlq-{self._queue['metadata']['total_failures'] + 1}",
            "subtask_id": subtask_id,
            "failure_type": failure_type,
            "error_message": error_message,
            "attempt_count": attempt_count,
            "recovery_action": recovery_action,
            "context": context or {},
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "pending",
        }

        self._queue["failures"].append(failure_record)
        self._queue["metadata"]["total_failures"] += 1

        return self._save_queue()

    def get_pending_failures(self) -> list[dict[str, Any]]:
        """
        Get all pending failures (not yet resolved).

        Returns:
            List of failure records with status="pending"
        """
        return [f for f in self._queue["failures"] if f.get("status") == "pending"]

    def get_all_failures(self) -> list[dict[str, Any]]:
        """
        Get all failures in the queue.

        Returns:
            List of all failure records
        """
        return self._queue["failures"]

    def get_failure_by_id(self, failure_id: str) -> dict[str, Any] | None:
        """
        Get a specific failure by ID.

        Args:
            failure_id: Failure ID (e.g., "dlq-1")

        Returns:
            Failure record or None if not found
        """
        for failure in self._queue["failures"]:
            if failure.get("id") == failure_id:
                return failure
        return None

    def get_failures_by_subtask(self, subtask_id: str) -> list[dict[str, Any]]:
        """
        Get all failures for a specific subtask.

        Args:
            subtask_id: Subtask ID to filter by

        Returns:
            List of failure records for the subtask
        """
        return [f for f in self._queue["failures"] if f.get("subtask_id") == subtask_id]

    def mark_resolved(
        self,
        failure_id: str,
        resolution: str,
        resolved_by: str | None = None,
    ) -> bool:
        """
        Mark a failure as resolved.

        Args:
            failure_id: Failure ID to resolve
            resolution: Description of how it was resolved
            resolved_by: Who resolved it (optional, e.g., "human", "agent")

        Returns:
            True if resolved successfully
        """
        failure = self.get_failure_by_id(failure_id)
        if not failure:
            return False

        # Update failure status
        failure["status"] = "resolved"
        failure["resolved_at"] = datetime.now(UTC).isoformat()
        failure["resolution"] = resolution
        failure["resolved_by"] = resolved_by or "unknown"

        # Move to resolved list
        self._queue["resolved"].append(failure)
        self._queue["failures"] = [
            f for f in self._queue["failures"] if f.get("id") != failure_id
        ]
        self._queue["metadata"]["total_resolved"] += 1

        return self._save_queue()

    def clear_resolved(self) -> bool:
        """
        Clear all resolved failures from the queue.

        Returns:
            True if cleared successfully
        """
        self._queue["resolved"] = []
        return self._save_queue()

    # -------------------------------------------------------------------------
    # STATISTICS METHODS
    # -------------------------------------------------------------------------

    def get_queue_size(self) -> int:
        """
        Get the number of pending failures.

        Returns:
            Number of pending failures in the queue
        """
        return len(self.get_pending_failures())

    def get_total_failures(self) -> int:
        """
        Get total number of failures ever recorded.

        Returns:
            Total failures count
        """
        return self._queue["metadata"]["total_failures"]

    def get_total_resolved(self) -> int:
        """
        Get total number of resolved failures.

        Returns:
            Total resolved count
        """
        return self._queue["metadata"]["total_resolved"]

    def get_failure_rate_by_type(self) -> dict[str, int]:
        """
        Get failure counts grouped by failure type.

        Returns:
            Dict mapping failure_type to count
        """
        counts: dict[str, int] = {}
        for failure in self._queue["failures"]:
            failure_type = failure.get("failure_type", "unknown")
            counts[failure_type] = counts.get(failure_type, 0) + 1
        return counts

    def get_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive queue statistics.

        Returns:
            Dict with queue statistics
        """
        return {
            "pending_failures": self.get_queue_size(),
            "total_failures": self.get_total_failures(),
            "total_resolved": self.get_total_resolved(),
            "resolution_rate": (
                self.get_total_resolved() / self.get_total_failures() * 100
                if self.get_total_failures() > 0
                else 0.0
            ),
            "failure_by_type": self.get_failure_rate_by_type(),
            "created_at": self._queue["metadata"]["created_at"],
            "last_updated": self._queue["metadata"]["last_updated"],
        }

    # -------------------------------------------------------------------------
    # EXPORT METHODS
    # -------------------------------------------------------------------------

    def export_pending_failures(self, output_path: Path | str | None = None) -> str:
        """
        Export pending failures to a human-readable format.

        Args:
            output_path: Optional path to save the export (default: spec_dir/dlq_report.txt)

        Returns:
            Formatted report as a string
        """
        pending = self.get_pending_failures()
        if not pending:
            report = "No pending failures in the dead-letter queue.\n"
        else:
            lines = ["DEAD-LETTER QUEUE - PENDING FAILURES", "=" * 50, ""]
            for failure in pending:
                lines.append(f"ID: {failure['id']}")
                lines.append(f"Subtask: {failure['subtask_id']}")
                lines.append(f"Type: {failure['failure_type']}")
                lines.append(f"Attempts: {failure['attempt_count']}")
                lines.append(f"Timestamp: {failure['timestamp']}")
                lines.append(f"Error: {failure['error_message'][:200]}")
                if failure.get("recovery_action"):
                    lines.append(f"Last Action: {failure['recovery_action']}")
                lines.append("-" * 50)
            report = "\n".join(lines)

        # Save to file (use default spec_dir/dlq_report.txt if no path provided)
        if output_path is None:
            output_path = self.spec_dir / "dlq_report.txt"
        path = Path(output_path)
        path.write_text(report, encoding="utf-8")

        return report
