"""
Recovery Metrics Tracking for Auto-Recovery
============================================

Tracks success rates, recovery attempts, and outcomes for the
intelligent auto-recovery loop in QA Fixer.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Configuration
METRICS_FILE = "recovery_metrics.json"


# =============================================================================
# RECOVERY METRICS CLASS
# =============================================================================


class RecoveryMetrics:
    """
    Tracks and manages auto-recovery metrics.

    Stores metrics in spec_dir/recovery_metrics.json and provides
    methods for recording attempts and calculating success rates.
    """

    def __init__(self, spec_dir: Path | None = None):
        """
        Initialize recovery metrics tracker.

        Args:
            spec_dir: Spec directory (uses current directory if None)
        """
        self.spec_dir = spec_dir or Path.cwd()
        self._metrics_file = self.spec_dir / METRICS_FILE
        self._metrics = self._load_metrics()

    def _load_metrics(self) -> dict[str, Any]:
        """
        Load metrics from recovery_metrics.json.

        Returns:
            Metrics dict, initializes empty structure if file doesn't exist
        """
        if not self._metrics_file.exists():
            return self._create_empty_metrics()

        try:
            with open(self._metrics_file, encoding="utf-8") as f:
                data = json.load(f)
                # Validate structure
                required_keys = [
                    "total_attempts",
                    "successful_recoveries",
                    "failed_recoveries",
                    "circular_fixes",
                    "recovery_history",
                ]
                if all(key in data for key in required_keys):
                    return data
                # If invalid, create new
                return self._create_empty_metrics()
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return self._create_empty_metrics()

    def _create_empty_metrics(self) -> dict[str, Any]:
        """
        Create empty metrics structure.

        Returns:
            Dict with initialized metric counters
        """
        return {
            "total_attempts": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "circular_fixes": 0,
            "recovery_history": [],
            "created_at": datetime.now(UTC).isoformat(),
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def _save_metrics(self) -> bool:
        """
        Save metrics to recovery_metrics.json atomically.

        Uses a temp file + os.replace to prevent corruption on crash.

        Returns:
            True if saved successfully
        """
        try:
            self._metrics["last_updated"] = datetime.now(UTC).isoformat()
            tmp_file = self._metrics_file.with_suffix(".json.tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self._metrics, f, indent=2, ensure_ascii=False)
            os.replace(tmp_file, self._metrics_file)
            return True
        except (OSError, TypeError, UnicodeDecodeError):
            return False

    # -------------------------------------------------------------------------
    # RECORDING METHODS
    # -------------------------------------------------------------------------

    def record_attempt(
        self,
        outcome: str,
        iterations: int,
        duration_seconds: float | None = None,
        issues_fixed: int = 0,
        strategy: str | None = None,
    ) -> bool:
        """
        Record a recovery attempt outcome.

        Args:
            outcome: Recovery outcome ("success", "failed", "circular")
            iterations: Number of iterations used
            duration_seconds: Optional duration of the recovery attempt
            issues_fixed: Number of issues fixed
            strategy: Strategy used for recovery (optional)

        Returns:
            True if recorded successfully
        """
        # Update counters
        self._metrics["total_attempts"] += 1

        if outcome == "success":
            self._metrics["successful_recoveries"] += 1
        elif outcome == "failed":
            self._metrics["failed_recoveries"] += 1
        elif outcome == "circular":
            self._metrics["circular_fixes"] += 1

        # Record history
        record = {
            "attempt_number": self._metrics["total_attempts"],
            "outcome": outcome,
            "iterations": iterations,
            "timestamp": datetime.now(UTC).isoformat(),
            "issues_fixed": issues_fixed,
        }

        if duration_seconds is not None:
            record["duration_seconds"] = round(duration_seconds, 2)

        if strategy:
            record["strategy"] = strategy

        self._metrics["recovery_history"].append(record)

        return self._save_metrics()

    def record_user_intervention(self, iteration: int) -> bool:
        """
        Record a user intervention during recovery.

        Args:
            iteration: Iteration number when intervention occurred

        Returns:
            True if recorded successfully
        """
        # Increment first, consistent with record_attempt
        self._metrics["total_attempts"] += 1

        record = {
            "attempt_number": self._metrics["total_attempts"],
            "outcome": "user_intervention",
            "iterations": iteration,
            "timestamp": datetime.now(UTC).isoformat(),
            "issues_fixed": 0,
        }

        self._metrics["recovery_history"].append(record)

        return self._save_metrics()

    # -------------------------------------------------------------------------
    # STATISTICS METHODS
    # -------------------------------------------------------------------------

    def get_success_rate(self) -> float:
        """
        Calculate overall recovery success rate.

        Returns:
            Success rate as percentage (0-100)
        """
        if self._metrics["total_attempts"] == 0:
            return 0.0

        successful = self._metrics["successful_recoveries"]
        total = self._metrics["total_attempts"]
        return round((successful / total) * 100, 2)

    def get_average_iterations(self) -> float:
        """
        Calculate average iterations per recovery attempt.

        Returns:
            Average iterations, or 0 if no attempts
        """
        if not self._metrics["recovery_history"]:
            return 0.0

        total_iterations = sum(
            record.get("iterations", 0) for record in self._metrics["recovery_history"]
        )
        return round(total_iterations / len(self._metrics["recovery_history"]), 2)

    def get_average_duration(self) -> float:
        """
        Calculate average duration of recovery attempts.

        Returns:
            Average duration in seconds, or 0 if no duration data
        """
        durations = [
            record.get("duration_seconds", 0)
            for record in self._metrics["recovery_history"]
            if "duration_seconds" in record
        ]

        if not durations:
            return 0.0

        return round(sum(durations) / len(durations), 2)

    def get_circular_fix_rate(self) -> float:
        """
        Calculate rate of circular fix detection.

        Returns:
            Circular fix rate as percentage (0-100)
        """
        if self._metrics["total_attempts"] == 0:
            return 0.0

        circular = self._metrics["circular_fixes"]
        total = self._metrics["total_attempts"]
        return round((circular / total) * 100, 2)

    # -------------------------------------------------------------------------
    # SUMMARY METHODS
    # -------------------------------------------------------------------------

    def get_summary(self) -> dict[str, Any]:
        """
        Get comprehensive recovery metrics summary.

        Returns:
            Dict with all metrics and calculated statistics
        """
        return {
            "total_attempts": self._metrics["total_attempts"],
            "successful_recoveries": self._metrics["successful_recoveries"],
            "failed_recoveries": self._metrics["failed_recoveries"],
            "circular_fixes": self._metrics["circular_fixes"],
            "success_rate_percent": self.get_success_rate(),
            "circular_fix_rate_percent": self.get_circular_fix_rate(),
            "average_iterations": self.get_average_iterations(),
            "average_duration_seconds": self.get_average_duration(),
            "last_updated": self._metrics.get("last_updated"),
        }

    def get_recent_history(self, limit: int = 5) -> list[dict[str, Any]]:
        """
        Get recent recovery attempts.

        Args:
            limit: Maximum number of recent attempts to return

        Returns:
            List of recent recovery records (most recent first)
        """
        return self._metrics["recovery_history"][-limit:][::-1]

    def format_summary(self) -> str:
        """
        Format recovery metrics summary as human-readable string.

        Returns:
            Formatted summary string
        """
        summary = self.get_summary()

        lines = [
            "📊 Recovery Metrics Summary",
            "",
            f"Total Attempts: {summary['total_attempts']}",
            f"Successful Recoveries: {summary['successful_recoveries']}",
            f"Failed Recoveries: {summary['failed_recoveries']}",
            f"Circular Fixes Detected: {summary['circular_fixes']}",
            "",
            f"Success Rate: {summary['success_rate_percent']:.1f}%",
            f"Circular Fix Rate: {summary['circular_fix_rate_percent']:.1f}%",
            f"Avg Iterations per Recovery: {summary['average_iterations']:.1f}",
        ]

        if summary["average_duration_seconds"] > 0:
            lines.append(
                f"Avg Duration: {summary['average_duration_seconds']:.1f} seconds"
            )

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # UTILITY METHODS
    # -------------------------------------------------------------------------

    def reset_metrics(self) -> bool:
        """
        Reset all metrics to zero.

        Returns:
            True if reset successfully
        """
        self._metrics = self._create_empty_metrics()
        return self._save_metrics()

    def get_metrics_file_path(self) -> Path:
        """
        Get the path to the metrics file.

        Returns:
            Path to recovery_metrics.json
        """
        return self._metrics_file


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def load_recovery_metrics(spec_dir: Path) -> RecoveryMetrics:
    """
    Load recovery metrics for a spec directory.

    Args:
        spec_dir: Spec directory path

    Returns:
        RecoveryMetrics instance
    """
    return RecoveryMetrics(spec_dir)


def record_recovery_outcome(
    spec_dir: Path,
    outcome: str,
    iterations: int,
    duration_seconds: float | None = None,
    issues_fixed: int = 0,
) -> bool:
    """
    Convenience function to record a recovery outcome.

    Args:
        spec_dir: Spec directory
        outcome: Recovery outcome ("success", "failed", "circular")
        iterations: Number of iterations used
        duration_seconds: Optional duration
        issues_fixed: Number of issues fixed

    Returns:
        True if recorded successfully
    """
    metrics = RecoveryMetrics(spec_dir)
    return metrics.record_attempt(outcome, iterations, duration_seconds, issues_fixed)


def get_recovery_summary(spec_dir: Path) -> dict[str, Any]:
    """
    Convenience function to get recovery summary.

    Args:
        spec_dir: Spec directory

    Returns:
        Recovery metrics summary dict
    """
    metrics = RecoveryMetrics(spec_dir)
    return metrics.get_summary()
