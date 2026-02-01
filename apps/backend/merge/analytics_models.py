"""
Merge Analytics Models
======================

Data models for tracking and analyzing merge operations.

This module contains data classes for merge analytics:
- MergeAnalyticsEntry: Record of a single merge operation
- MergeAnalyticsSummary: Aggregated statistics across multiple merges
- ConflictPattern: Recurring conflict pattern analysis
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import MergeStats


@dataclass
class MergeAnalyticsEntry:
    """
    Record of a single merge operation.

    Captures all relevant information about a merge for historical tracking
    and pattern analysis.
    """

    # Unique identification
    merge_id: str  # Format: "merge_{timestamp}_{task_ids_hash}"
    timestamp: datetime

    # Tasks involved
    task_ids: list[str] = field(default_factory=list)

    # Merge outcome
    success: bool = True
    error: str | None = None

    # Statistics
    stats: MergeStats = field(default_factory=MergeStats)
    duration_seconds: float = 0.0

    # Files affected
    files_processed: list[str] = field(default_factory=list)
    files_auto_merged: list[str] = field(default_factory=list)
    files_ai_merged: list[str] = field(default_factory=list)
    files_failed: list[str] = field(default_factory=list)

    # Conflict details
    conflicts_detected: int = 0
    conflicts_auto_resolved: int = 0
    conflicts_ai_resolved: int = 0
    conflicts_remaining: int = 0

    # Additional context
    merge_intent: str = ""  # Why this merge was performed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "merge_id": self.merge_id,
            "timestamp": self.timestamp.isoformat(),
            "task_ids": self.task_ids,
            "success": self.success,
            "error": self.error,
            "stats": self.stats.to_dict(),
            "duration_seconds": self.duration_seconds,
            "files_processed": self.files_processed,
            "files_auto_merged": self.files_auto_merged,
            "files_ai_merged": self.files_ai_merged,
            "files_failed": self.files_failed,
            "conflicts_detected": self.conflicts_detected,
            "conflicts_auto_resolved": self.conflicts_auto_resolved,
            "conflicts_ai_resolved": self.conflicts_ai_resolved,
            "conflicts_remaining": self.conflicts_remaining,
            "merge_intent": self.merge_intent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MergeAnalyticsEntry:
        """Create entry from dictionary."""
        # Reconstruct MergeStats from dict
        stats_data = data.get("stats", {})
        stats = MergeStats(**stats_data) if stats_data else MergeStats()

        return cls(
            merge_id=data["merge_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            task_ids=data.get("task_ids", []),
            success=data.get("success", True),
            error=data.get("error"),
            stats=stats,
            duration_seconds=data.get("duration_seconds", 0.0),
            files_processed=data.get("files_processed", []),
            files_auto_merged=data.get("files_auto_merged", []),
            files_ai_merged=data.get("files_ai_merged", []),
            files_failed=data.get("files_failed", []),
            conflicts_detected=data.get("conflicts_detected", 0),
            conflicts_auto_resolved=data.get("conflicts_auto_resolved", 0),
            conflicts_ai_resolved=data.get("conflicts_ai_resolved", 0),
            conflicts_remaining=data.get("conflicts_remaining", 0),
            merge_intent=data.get("merge_intent", ""),
        )

    @property
    def success_rate(self) -> float:
        """Calculate success rate for this merge (0.0 to 1.0)."""
        if not self.files_processed:
            return 1.0
        successful = len(self.files_auto_merged) + len(self.files_ai_merged)
        return successful / len(self.files_processed)

    @property
    def auto_merge_rate(self) -> float:
        """Calculate auto-merge rate (conflicts resolved without AI)."""
        if self.conflicts_detected == 0:
            return 1.0
        return self.conflicts_auto_resolved / self.conflicts_detected


@dataclass
class MergeAnalyticsSummary:
    """
    Aggregated statistics across multiple merge operations.

    Provides high-level insights into merge performance over time.
    """

    # Time period
    period_start: datetime
    period_end: datetime

    # Overall metrics
    total_merges: int = 0
    successful_merges: int = 0
    failed_merges: int = 0

    # File statistics
    total_files_processed: int = 0
    total_files_auto_merged: int = 0
    total_files_ai_merged: int = 0
    total_files_failed: int = 0

    # Conflict statistics
    total_conflicts_detected: int = 0
    total_conflicts_auto_resolved: int = 0
    total_conflicts_ai_resolved: int = 0
    total_conflicts_remaining: int = 0

    # Performance metrics
    average_duration_seconds: float = 0.0
    median_duration_seconds: float = 0.0
    total_ai_calls: int = 0
    total_tokens_used: int = 0

    # Tasks
    unique_tasks_merged: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_merges": self.total_merges,
            "successful_merges": self.successful_merges,
            "failed_merges": self.failed_merges,
            "total_files_processed": self.total_files_processed,
            "total_files_auto_merged": self.total_files_auto_merged,
            "total_files_ai_merged": self.total_files_ai_merged,
            "total_files_failed": self.total_files_failed,
            "total_conflicts_detected": self.total_conflicts_detected,
            "total_conflicts_auto_resolved": self.total_conflicts_auto_resolved,
            "total_conflicts_ai_resolved": self.total_conflicts_ai_resolved,
            "total_conflicts_remaining": self.total_conflicts_remaining,
            "average_duration_seconds": self.average_duration_seconds,
            "median_duration_seconds": self.median_duration_seconds,
            "total_ai_calls": self.total_ai_calls,
            "total_tokens_used": self.total_tokens_used,
            "unique_tasks_merged": self.unique_tasks_merged,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MergeAnalyticsSummary:
        """Create summary from dictionary."""
        return cls(
            period_start=datetime.fromisoformat(data["period_start"]),
            period_end=datetime.fromisoformat(data["period_end"]),
            total_merges=data.get("total_merges", 0),
            successful_merges=data.get("successful_merges", 0),
            failed_merges=data.get("failed_merges", 0),
            total_files_processed=data.get("total_files_processed", 0),
            total_files_auto_merged=data.get("total_files_auto_merged", 0),
            total_files_ai_merged=data.get("total_files_ai_merged", 0),
            total_files_failed=data.get("total_files_failed", 0),
            total_conflicts_detected=data.get("total_conflicts_detected", 0),
            total_conflicts_auto_resolved=data.get("total_conflicts_auto_resolved", 0),
            total_conflicts_ai_resolved=data.get("total_conflicts_ai_resolved", 0),
            total_conflicts_remaining=data.get("total_conflicts_remaining", 0),
            average_duration_seconds=data.get("average_duration_seconds", 0.0),
            median_duration_seconds=data.get("median_duration_seconds", 0.0),
            total_ai_calls=data.get("total_ai_calls", 0),
            total_tokens_used=data.get("total_tokens_used", 0),
            unique_tasks_merged=data.get("unique_tasks_merged", []),
        )

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate (0.0 to 1.0)."""
        if self.total_merges == 0:
            return 1.0
        return self.successful_merges / self.total_merges

    @property
    def auto_merge_rate(self) -> float:
        """Calculate percentage of conflicts resolved without AI."""
        if self.total_conflicts_detected == 0:
            return 1.0
        return self.total_conflicts_auto_resolved / self.total_conflicts_detected

    @property
    def ai_resolution_rate(self) -> float:
        """Calculate percentage of conflicts resolved by AI."""
        if self.total_conflicts_detected == 0:
            return 0.0
        return self.total_conflicts_ai_resolved / self.total_conflicts_detected

    @property
    def conflict_resolution_rate(self) -> float:
        """Calculate overall conflict resolution rate."""
        if self.total_conflicts_detected == 0:
            return 1.0
        resolved = self.total_conflicts_auto_resolved + self.total_conflicts_ai_resolved
        return resolved / self.total_conflicts_detected


@dataclass
class ConflictPattern:
    """
    A recurring conflict pattern detected across multiple merges.

    Used to identify problematic areas and improve merge strategies.
    """

    # Pattern identification
    pattern_id: str  # Unique identifier for this pattern
    file_path: str
    location: str  # Function/class/location in file

    # Conflict details
    conflict_type: str  # ChangeType value as string
    severity: str  # ConflictSeverity value as string

    # Occurrence tracking
    frequency: int = 1  # Number of times this pattern was seen
    tasks_involved: list[str] = field(default_factory=list)

    # Time tracking
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    # Resolution tracking
    auto_resolved_count: int = 0
    ai_resolved_count: int = 0
    manual_required_count: int = 0

    # Additional context
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pattern_id": self.pattern_id,
            "file_path": self.file_path,
            "location": self.location,
            "conflict_type": self.conflict_type,
            "severity": self.severity,
            "frequency": self.frequency,
            "tasks_involved": self.tasks_involved,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "auto_resolved_count": self.auto_resolved_count,
            "ai_resolved_count": self.ai_resolved_count,
            "manual_required_count": self.manual_required_count,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ConflictPattern:
        """Create pattern from dictionary."""
        return cls(
            pattern_id=data["pattern_id"],
            file_path=data["file_path"],
            location=data["location"],
            conflict_type=data["conflict_type"],
            severity=data["severity"],
            frequency=data.get("frequency", 1),
            tasks_involved=data.get("tasks_involved", []),
            first_seen=datetime.fromisoformat(data["first_seen"]),
            last_seen=datetime.fromisoformat(data["last_seen"]),
            auto_resolved_count=data.get("auto_resolved_count", 0),
            ai_resolved_count=data.get("ai_resolved_count", 0),
            manual_required_count=data.get("manual_required_count", 0),
            description=data.get("description", ""),
        )

    @property
    def resolution_success_rate(self) -> float:
        """Calculate how often this pattern is successfully resolved."""
        total = self.auto_resolved_count + self.ai_resolved_count + self.manual_required_count
        if total == 0:
            return 0.0
        resolved = self.auto_resolved_count + self.ai_resolved_count
        return resolved / total

    @property
    def requires_attention(self) -> bool:
        """Check if this pattern occurs frequently and needs attention."""
        # Pattern is problematic if seen 3+ times and often needs manual intervention
        return self.frequency >= 3 and self.manual_required_count > self.frequency * 0.3
