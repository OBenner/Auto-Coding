"""
Scheduler Data Models
=====================

Core data structures for scheduled builds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class BuildStatus(str, Enum):
    """Status of a scheduled build."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class SchedulePriority(int, Enum):
    """Priority levels for scheduled builds."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


@dataclass
class ScheduledBuild:
    """
    Represents a scheduled build task.

    Attributes:
        id: Unique identifier for this scheduled build
        spec_id: ID of the spec to build (e.g., "001-feature-name")
        spec_name: Human-readable name of the spec
        scheduled_time: When to execute this build (None = execute immediately)
        priority: Priority level for queue ordering
        status: Current status of the build
        dependencies: List of spec IDs that must complete before this one
        created_at: When this schedule was created
        updated_at: Last status update time
        started_at: When build execution started
        completed_at: When build finished (success or failure)
        retry_count: Number of retry attempts made
        max_retries: Maximum retry attempts allowed
        error_message: Error details if build failed
        notification_config: Notification settings (email, webhook, etc.)
        metadata: Additional metadata (estimated_hours, tags, etc.)
    """

    id: str
    spec_id: str
    spec_name: str
    scheduled_time: datetime | None = None
    priority: SchedulePriority = SchedulePriority.NORMAL
    status: BuildStatus = BuildStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: str | None = None
    notification_config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "spec_id": self.spec_id,
            "spec_name": self.spec_name,
            "scheduled_time": self.scheduled_time.isoformat()
            if self.scheduled_time
            else None,
            "priority": self.priority.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "notification_config": self.notification_config,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledBuild:
        """Create ScheduledBuild from dictionary."""
        # Parse datetime fields
        scheduled_time = None
        if data.get("scheduled_time"):
            scheduled_time = datetime.fromisoformat(data["scheduled_time"])

        created_at = datetime.fromisoformat(data["created_at"])
        updated_at = datetime.fromisoformat(data["updated_at"])

        started_at = None
        if data.get("started_at"):
            started_at = datetime.fromisoformat(data["started_at"])

        completed_at = None
        if data.get("completed_at"):
            completed_at = datetime.fromisoformat(data["completed_at"])

        # Parse enum fields
        priority = SchedulePriority(data.get("priority", SchedulePriority.NORMAL.value))
        status = BuildStatus(data.get("status", BuildStatus.PENDING.value))

        return cls(
            id=data["id"],
            spec_id=data["spec_id"],
            spec_name=data["spec_name"],
            scheduled_time=scheduled_time,
            priority=priority,
            status=status,
            dependencies=data.get("dependencies", []),
            created_at=created_at,
            updated_at=updated_at,
            started_at=started_at,
            completed_at=completed_at,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            error_message=data.get("error_message"),
            notification_config=data.get("notification_config", {}),
            metadata=data.get("metadata", {}),
        )

    @property
    def is_ready_to_run(self) -> bool:
        """Check if build is ready to execute."""
        if self.status not in (BuildStatus.PENDING, BuildStatus.QUEUED):
            return False

        # Check if scheduled time has passed
        if self.scheduled_time and datetime.now() < self.scheduled_time:
            return False

        return True

    @property
    def can_retry(self) -> bool:
        """Check if build can be retried."""
        return (
            self.status == BuildStatus.FAILED and self.retry_count < self.max_retries
        )

    @property
    def duration_seconds(self) -> float | None:
        """Calculate build duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def mark_started(self) -> None:
        """Mark build as started."""
        self.status = BuildStatus.RUNNING
        self.started_at = datetime.now()
        self.updated_at = datetime.now()

    def mark_completed(self) -> None:
        """Mark build as completed successfully."""
        self.status = BuildStatus.COMPLETED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def mark_failed(self, error_message: str) -> None:
        """Mark build as failed with error message."""
        self.status = BuildStatus.FAILED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()
        self.error_message = error_message

    def mark_cancelled(self) -> None:
        """Mark build as cancelled."""
        self.status = BuildStatus.CANCELLED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def increment_retry(self) -> None:
        """Increment retry counter and mark for retry."""
        self.retry_count += 1
        self.status = BuildStatus.RETRYING
        self.updated_at = datetime.now()
        self.error_message = None
