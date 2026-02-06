"""
Merge Analytics Recorder
=========================

Records and aggregates merge analytics data for tracking and reporting.

This module handles:
- Recording merge operations with timestamps and outcomes
- Storing historical merge data to disk
- Aggregating statistics across merge operations
- Identifying patterns and trends in merge operations
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import MergeReport, MergeStats
from .types import ConflictSeverity

logger = logging.getLogger(__name__)

# Severity ranking for comparison (higher number = more severe)
SEVERITY_RANK = {
    ConflictSeverity.NONE: 0,
    ConflictSeverity.LOW: 1,
    ConflictSeverity.MEDIUM: 2,
    ConflictSeverity.HIGH: 3,
    ConflictSeverity.CRITICAL: 4,
}


@dataclass
class MergeOperationRecord:
    """
    Single merge operation record.

    Captures essential information about a merge operation
    for historical tracking and analysis.
    """

    operation_id: str
    timestamp: datetime
    tasks_merged: list[str]
    stats: MergeStats
    success: bool
    error: str | None = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation_id": self.operation_id,
            "timestamp": self.timestamp.isoformat(),
            "tasks_merged": self.tasks_merged,
            "stats": self.stats.to_dict(),
            "success": self.success,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MergeOperationRecord:
        """Create from dictionary."""
        stats_data = data.get("stats", {})
        stats = MergeStats(
            files_processed=stats_data.get("files_processed", 0),
            files_auto_merged=stats_data.get("files_auto_merged", 0),
            files_ai_merged=stats_data.get("files_ai_merged", 0),
            files_need_review=stats_data.get("files_need_review", 0),
            files_failed=stats_data.get("files_failed", 0),
            conflicts_detected=stats_data.get("conflicts_detected", 0),
            conflicts_auto_resolved=stats_data.get("conflicts_auto_resolved", 0),
            conflicts_ai_resolved=stats_data.get("conflicts_ai_resolved", 0),
            ai_calls_made=stats_data.get("ai_calls_made", 0),
            estimated_tokens_used=stats_data.get("estimated_tokens_used", 0),
            duration_seconds=stats_data.get("duration_seconds", 0.0),
        )

        return cls(
            operation_id=data["operation_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tasks_merged=data.get("tasks_merged", []),
            stats=stats,
            success=data.get("success", True),
            error=data.get("error"),
            duration_seconds=data.get("duration_seconds", 0.0),
        )


@dataclass
class ConflictPattern:
    """
    Pattern identified in conflict occurrences.

    Tracks recurring conflicts across merge operations
    to help identify systematic issues.
    """

    file_path: str
    location: str
    occurrence_count: int = 0
    severity: ConflictSeverity = ConflictSeverity.NONE
    tasks_involved: list[str] = field(default_factory=list)
    last_seen: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file_path": self.file_path,
            "location": self.location,
            "occurrence_count": self.occurrence_count,
            "severity": self.severity.value,
            "tasks_involved": self.tasks_involved,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConflictPattern:
        """Create from dictionary."""
        return cls(
            file_path=data["file_path"],
            location=data["location"],
            occurrence_count=data.get("occurrence_count", 0),
            severity=ConflictSeverity(data.get("severity", "none")),
            tasks_involved=data.get("tasks_involved", []),
            last_seen=datetime.fromisoformat(data["last_seen"])
            if data.get("last_seen")
            else None,
        )


@dataclass
class MergeAnalytics:
    """
    Aggregated analytics across multiple merge operations.

    Provides insights into merge performance and patterns.
    """

    total_operations: int = 0
    total_files_merged: int = 0
    total_conflicts: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_ai_calls: int = 0
    total_tokens_used: int = 0
    average_duration_seconds: float = 0.0
    success_rate: float = 0.0
    auto_merge_rate: float = 0.0
    conflict_patterns: list[ConflictPattern] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_operations": self.total_operations,
            "total_files_merged": self.total_files_merged,
            "total_conflicts": self.total_conflicts,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "total_ai_calls": self.total_ai_calls,
            "total_tokens_used": self.total_tokens_used,
            "average_duration_seconds": self.average_duration_seconds,
            "success_rate": self.success_rate,
            "auto_merge_rate": self.auto_merge_rate,
            "conflict_patterns": [p.to_dict() for p in self.conflict_patterns],
        }


class MergeAnalyticsRecorder:
    """
    Records and aggregates merge analytics data.

    Responsibilities:
    - Record each merge operation to disk
    - Load and aggregate historical data
    - Identify conflict patterns
    - Generate analytics reports
    """

    def __init__(self, storage_dir: Path | str):
        """
        Initialize the analytics recorder.

        Args:
            storage_dir: Directory for analytics data (.auto-claude/)
        """
        self.storage_dir = Path(storage_dir).resolve()
        self.analytics_dir = self.storage_dir / "merge_analytics"
        self.operations_file = self.analytics_dir / "operations.json"
        self.patterns_file = self.analytics_dir / "conflict_patterns.json"

        # Ensure directories exist
        self.analytics_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Analytics recorder initialized at {self.analytics_dir}")

    def record_merge_operation(
        self,
        operation_id: str,
        merge_report: MergeReport,
    ) -> None:
        """
        Record a merge operation to disk.

        Args:
            operation_id: Unique identifier for this operation
            merge_report: The merge report to record
        """
        try:
            # Load existing operations
            operations = self._load_operations()

            # Create new record
            record = MergeOperationRecord(
                operation_id=operation_id,
                timestamp=merge_report.started_at,
                tasks_merged=merge_report.tasks_merged,
                stats=merge_report.stats,
                success=merge_report.success,
                error=merge_report.error,
                duration_seconds=merge_report.stats.duration_seconds,
            )

            # Add to operations (replace if exists with same ID)
            operations = [op for op in operations if op.operation_id != operation_id]
            operations.append(record)

            # Sort by timestamp (most recent first)
            operations.sort(key=lambda op: op.timestamp, reverse=True)

            # Save to disk
            self._save_operations(operations)

            # Update conflict patterns
            self._update_conflict_patterns(merge_report)

            logger.info(f"Recorded merge operation: {operation_id}")

        except Exception as e:
            logger.error(f"Failed to record merge operation {operation_id}: {e}")

    def get_analytics(
        self,
        since: datetime | None = None,
        task_id: str | None = None,
    ) -> MergeAnalytics:
        """
        Get aggregated analytics for merge operations.

        Args:
            since: Only include operations after this timestamp
            task_id: Only include operations involving this task

        Returns:
            Aggregated analytics data
        """
        operations = self._load_operations()

        # Filter operations
        if since:
            operations = [op for op in operations if op.timestamp >= since]
        if task_id:
            operations = [op for op in operations if task_id in op.tasks_merged]

        if not operations:
            return MergeAnalytics()

        # Aggregate statistics
        analytics = MergeAnalytics()
        analytics.total_operations = len(operations)

        total_duration = 0.0
        total_conflicts = 0
        total_conflicts_auto_resolved = 0

        for op in operations:
            analytics.total_files_merged += op.stats.files_processed
            analytics.total_ai_calls += op.stats.ai_calls_made
            analytics.total_tokens_used += op.stats.estimated_tokens_used
            total_duration += op.duration_seconds

            if op.success:
                analytics.successful_operations += 1
            else:
                analytics.failed_operations += 1

            total_conflicts += op.stats.conflicts_detected
            total_conflicts_auto_resolved += op.stats.conflicts_auto_resolved

        # Calculate rates
        if analytics.total_operations > 0:
            analytics.success_rate = (
                analytics.successful_operations / analytics.total_operations
            )
            analytics.average_duration_seconds = (
                total_duration / analytics.total_operations
            )

        analytics.total_conflicts = total_conflicts
        if total_conflicts > 0:
            analytics.auto_merge_rate = total_conflicts_auto_resolved / total_conflicts

        # Load conflict patterns
        analytics.conflict_patterns = self._load_conflict_patterns()

        return analytics

    def get_operation_history(
        self,
        limit: int = 100,
        task_id: str | None = None,
    ) -> list[MergeOperationRecord]:
        """
        Get recent merge operation history.

        Args:
            limit: Maximum number of operations to return
            task_id: Filter by task ID

        Returns:
            List of merge operation records (most recent first)
        """
        operations = self._load_operations()

        # Filter by task if specified
        if task_id:
            operations = [op for op in operations if task_id in op.tasks_merged]

        # Return limited results
        return operations[:limit]

    def export_analytics(self, output_path: Path | str) -> None:
        """
        Export analytics to JSON file for reporting.

        Args:
            output_path: Path to save the analytics export
        """
        analytics = self.get_analytics()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analytics.to_dict(), f, indent=2)

        logger.info(f"Exported analytics to {output_path}")

    def _load_operations(self) -> list[MergeOperationRecord]:
        """Load merge operations from disk."""
        if not self.operations_file.exists():
            return []

        try:
            with open(self.operations_file, encoding="utf-8") as f:
                data = json.load(f)

            operations = [MergeOperationRecord.from_dict(op) for op in data]
            logger.debug(f"Loaded {len(operations)} merge operations")
            return operations

        except Exception as e:
            logger.error(f"Failed to load operations: {e}")
            return []

    def _save_operations(self, operations: list[MergeOperationRecord]) -> None:
        """Save merge operations to disk."""
        try:
            data = [op.to_dict() for op in operations]

            with open(self.operations_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(operations)} merge operations")

        except Exception as e:
            logger.error(f"Failed to save operations: {e}")

    def _load_conflict_patterns(self) -> list[ConflictPattern]:
        """Load conflict patterns from disk."""
        if not self.patterns_file.exists():
            return []

        try:
            with open(self.patterns_file, encoding="utf-8") as f:
                data = json.load(f)

            patterns = [ConflictPattern.from_dict(p) for p in data]
            logger.debug(f"Loaded {len(patterns)} conflict patterns")
            return patterns

        except Exception as e:
            logger.error(f"Failed to load conflict patterns: {e}")
            return []

    def _save_conflict_patterns(self, patterns: list[ConflictPattern]) -> None:
        """Save conflict patterns to disk."""
        try:
            data = [p.to_dict() for p in patterns]

            with open(self.patterns_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(patterns)} conflict patterns")

        except Exception as e:
            logger.error(f"Failed to save conflict patterns: {e}")

    def _update_conflict_patterns(self, merge_report: MergeReport) -> None:
        """
        Update conflict patterns based on merge report.

        Args:
            merge_report: The merge report to analyze
        """
        try:
            patterns = self._load_conflict_patterns()
            pattern_map = {
                (p.file_path, p.location): p for p in patterns
            }

            # Extract conflicts from file results
            for file_path, result in merge_report.file_results.items():
                for conflict in result.conflicts_resolved + result.conflicts_remaining:
                    key = (conflict.file_path, conflict.location)

                    if key in pattern_map:
                        # Update existing pattern
                        pattern = pattern_map[key]
                        pattern.occurrence_count += 1
                        pattern.last_seen = merge_report.started_at
                        # Add new tasks if not already tracked
                        for task in conflict.tasks_involved:
                            if task not in pattern.tasks_involved:
                                pattern.tasks_involved.append(task)
                        # Update severity if higher
                        if SEVERITY_RANK[conflict.severity] > SEVERITY_RANK[pattern.severity]:
                            pattern.severity = conflict.severity
                    else:
                        # Create new pattern
                        pattern = ConflictPattern(
                            file_path=conflict.file_path,
                            location=conflict.location,
                            occurrence_count=1,
                            severity=conflict.severity,
                            tasks_involved=conflict.tasks_involved.copy(),
                            last_seen=merge_report.started_at,
                        )
                        pattern_map[key] = pattern

            # Save updated patterns
            updated_patterns = list(pattern_map.values())
            # Sort by occurrence count (most frequent first)
            updated_patterns.sort(key=lambda p: p.occurrence_count, reverse=True)
            self._save_conflict_patterns(updated_patterns)

        except Exception as e:
            logger.error(f"Failed to update conflict patterns: {e}")
