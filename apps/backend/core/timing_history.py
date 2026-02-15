"""
Timing History Storage
======================

Stores historical timing data for completion time estimates.
Tracks phase, subtask, and agent execution times to predict future completion.
"""

import json
import time
from pathlib import Path
from typing import TypedDict


class TimingRecord(TypedDict, total=False):
    """Single timing record for a completed operation."""

    operation_type: str  # "phase", "subtask", "agent_session"
    operation_id: str  # Phase ID, subtask ID, or agent type
    started_at: float  # Unix timestamp
    completed_at: float  # Unix timestamp
    duration_seconds: float  # Total duration
    status: str  # "completed", "failed", etc.


class TimingEstimate(TypedDict):
    """Estimated completion time based on historical data."""

    estimated_seconds: float
    confidence: str  # "high", "medium", "low"
    sample_size: int  # Number of historical samples used


class TimingHistory:
    """
    Manages historical timing data for completion estimates.

    Stores timing records in timing_history.json and provides
    methods to calculate estimates based on past performance.

    Example:
        history = TimingHistory(spec_dir)
        history.record_completion("subtask", "subtask-1-1", started, completed)
        estimate = history.estimate_completion("subtask", "subtask-1-2")
        print(f"Estimated: {estimate['estimated_seconds']}s")
    """

    def __init__(self, spec_dir: Path) -> None:
        """
        Initialize timing history.

        Args:
            spec_dir: Directory containing timing_history.json
        """
        self.spec_dir = Path(spec_dir)
        self.history_file = self.spec_dir / "timing_history.json"
        self._records: list[TimingRecord] = []
        self._load()

    def _load(self) -> None:
        """Load timing history from disk."""
        if not self.history_file.exists():
            self._records = []
            return

        try:
            with open(self.history_file, encoding="utf-8") as f:
                data = json.load(f)
                self._records = data.get("records", [])
        except (OSError, ValueError):
            # Corrupted or missing file - start fresh
            self._records = []

    def _save(self) -> None:
        """Save timing history to disk."""
        try:
            self.spec_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "version": "1.0",
                "updated_at": time.time(),
                "records": self._records,
            }
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except (OSError, ValueError):
            pass  # Silent failure - timing history is non-critical

    def record_completion(
        self,
        operation_type: str,
        operation_id: str,
        started_at: float,
        completed_at: float | None = None,
        status: str = "completed",
    ) -> None:
        """
        Record a completed operation for future estimates.

        Args:
            operation_type: Type of operation ("phase", "subtask", "agent_session")
            operation_id: Unique identifier (phase ID, subtask ID, agent type)
            started_at: Unix timestamp when operation started
            completed_at: Unix timestamp when completed (defaults to now)
            status: Completion status (default: "completed")
        """
        if completed_at is None:
            completed_at = time.time()

        duration = completed_at - started_at
        if duration < 0:
            duration = 0.0

        record: TimingRecord = {
            "operation_type": operation_type,
            "operation_id": operation_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_seconds": round(duration, 2),
            "status": status,
        }

        self._records.append(record)
        self._save()

    def estimate_completion(
        self,
        operation_type: str,
        operation_id: str | None = None,
    ) -> TimingEstimate:
        """
        Estimate completion time based on historical data.

        Args:
            operation_type: Type of operation to estimate
            operation_id: Optional specific operation ID (for exact matches)

        Returns:
            TimingEstimate with estimated_seconds, confidence, and sample_size
        """
        # Filter relevant records
        relevant = [
            r
            for r in self._records
            if r.get("operation_type") == operation_type
            and r.get("status") == "completed"
            and r.get("duration_seconds", 0) > 0
        ]

        # Try exact match first if operation_id provided
        if operation_id:
            exact_match = [r for r in relevant if r.get("operation_id") == operation_id]
            if exact_match:
                relevant = exact_match

        if not relevant:
            # No historical data - return conservative estimate
            return {
                "estimated_seconds": 300.0,  # 5 minutes default
                "confidence": "low",
                "sample_size": 0,
            }

        # Calculate average duration
        durations = [r["duration_seconds"] for r in relevant]
        avg_duration = sum(durations) / len(durations)

        # Determine confidence based on sample size and variance
        sample_size = len(durations)
        if sample_size >= 5:
            confidence = "high"
        elif sample_size >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        # Add buffer for low confidence estimates
        if confidence == "low":
            avg_duration *= 1.5  # 50% buffer
        elif confidence == "medium":
            avg_duration *= 1.2  # 20% buffer

        return {
            "estimated_seconds": round(avg_duration, 2),
            "confidence": confidence,
            "sample_size": sample_size,
        }

    def get_records(
        self,
        operation_type: str | None = None,
        operation_id: str | None = None,
    ) -> list[TimingRecord]:
        """
        Get timing records matching criteria.

        Args:
            operation_type: Optional filter by operation type
            operation_id: Optional filter by operation ID

        Returns:
            List of matching timing records
        """
        records = self._records

        if operation_type:
            records = [r for r in records if r.get("operation_type") == operation_type]

        if operation_id:
            records = [r for r in records if r.get("operation_id") == operation_id]

        return records

    def clear_history(self) -> None:
        """Clear all timing history (for testing/reset)."""
        self._records = []
        self._save()

    def get_average_duration(
        self,
        operation_type: str,
        min_samples: int = 1,
    ) -> float | None:
        """
        Get average duration for an operation type.

        Args:
            operation_type: Type of operation
            min_samples: Minimum samples required (default: 1)

        Returns:
            Average duration in seconds, or None if insufficient data
        """
        relevant = [
            r
            for r in self._records
            if r.get("operation_type") == operation_type
            and r.get("status") == "completed"
            and r.get("duration_seconds", 0) > 0
        ]

        if len(relevant) < min_samples:
            return None

        durations = [r["duration_seconds"] for r in relevant]
        return sum(durations) / len(durations)


# Convenience functions for global access

# Cache dict for singleton pattern (avoids separate global variable alerts)
_timing_cache: dict = {"history": None, "spec_dir": None}


def get_timing_history(spec_dir: Path) -> TimingHistory:
    """
    Get or create timing history for a spec directory.

    Args:
        spec_dir: Directory containing timing_history.json

    Returns:
        TimingHistory instance
    """
    spec_path = Path(spec_dir).resolve()

    # Reuse cached instance if same spec_dir
    if _timing_cache["history"] is not None and _timing_cache["spec_dir"] == spec_path:
        return _timing_cache["history"]

    _timing_cache["history"] = TimingHistory(spec_path)
    _timing_cache["spec_dir"] = spec_path
    return _timing_cache["history"]


def reset_timing_history() -> None:
    """Reset global timing history instance."""
    _timing_cache["history"] = None
    _timing_cache["spec_dir"] = None
