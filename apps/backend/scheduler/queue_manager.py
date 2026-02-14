"""
Queue Manager Module
====================

Manages the build queue with priority ordering and thread-safe operations.

This module provides:
- Priority-based queue management
- Thread-safe queue operations
- Event callbacks for queue state changes
- Integration with SchedulerStorage
- Queue statistics and monitoring
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import BuildStatus, ScheduledBuild, SchedulePriority
from .storage import SchedulerStorage

logger = logging.getLogger(__name__)


class QueueEvent:
    """
    Queue event types for callbacks.

    Events emitted during queue operations:
    - BUILD_ADDED: New build added to queue
    - BUILD_REMOVED: Build removed from queue
    - BUILD_STATUS_CHANGED: Build status updated
    - BUILD_STARTED: Build execution started
    - BUILD_COMPLETED: Build finished successfully
    - BUILD_FAILED: Build failed
    - QUEUE_EMPTY: Queue became empty
    """

    BUILD_ADDED = "build_added"
    BUILD_REMOVED = "build_removed"
    BUILD_STATUS_CHANGED = "build_status_changed"
    BUILD_STARTED = "build_started"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"
    QUEUE_EMPTY = "queue_empty"


class QueueManager:
    """
    Manages the build queue with priority ordering.

    Responsibilities:
    - Maintain in-memory queue with priority ordering
    - Provide thread-safe queue operations
    - Persist queue state via SchedulerStorage
    - Emit events for queue state changes
    - Track queue statistics

    The queue maintains builds sorted by:
    1. Priority (CRITICAL -> BACKGROUND)
    2. Scheduled time (earlier times first)
    3. Creation time (older builds first)
    """

    def __init__(
        self, project_dir: Path | str, storage: SchedulerStorage | None = None
    ):
        """
        Initialize queue manager.

        Args:
            project_dir: Root directory of the project
            storage: Optional SchedulerStorage instance (creates new if None)
        """
        self.project_dir = Path(project_dir).resolve()
        self.storage = storage or SchedulerStorage(project_dir)

        # Thread safety
        self._lock = threading.RLock()

        # Event callbacks: {event_type: [callback_functions]}
        self._event_callbacks: dict[str, list[Callable]] = {}

        # Load initial queue state from storage
        self._builds: dict[str, ScheduledBuild] = {}
        self._load_from_storage()

        logger.info(f"QueueManager initialized with {len(self._builds)} builds")

    def _load_from_storage(self) -> None:
        """Load builds from storage into memory."""
        builds = self.storage.load_all_builds()
        for build in builds:
            self._builds[build.id] = build

    def _save_to_storage(self) -> bool:
        """Persist current queue state to storage."""
        builds = list(self._builds.values())
        return self.storage.save_builds(builds)

    def _emit_event(
        self, event_type: str, build: ScheduledBuild | None = None, **kwargs: Any
    ) -> None:
        """
        Emit event to registered callbacks.

        Args:
            event_type: Type of event (from QueueEvent)
            build: Related ScheduledBuild (if applicable)
            **kwargs: Additional event data
        """
        callbacks = self._event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                callback(event_type=event_type, build=build, **kwargs)
            except Exception as e:
                logger.error(f"Error in event callback for {event_type}: {e}")

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register callback for queue events.

        Args:
            event_type: Event type to listen for (from QueueEvent)
            callback: Function to call (receives event_type, build, **kwargs)
        """
        with self._lock:
            if event_type not in self._event_callbacks:
                self._event_callbacks[event_type] = []
            self._event_callbacks[event_type].append(callback)
            logger.debug(f"Registered callback for event: {event_type}")

    def unregister_callback(self, event_type: str, callback: Callable) -> None:
        """
        Unregister event callback.

        Args:
            event_type: Event type
            callback: Callback function to remove
        """
        with self._lock:
            if event_type in self._event_callbacks:
                try:
                    self._event_callbacks[event_type].remove(callback)
                    logger.debug(f"Unregistered callback for event: {event_type}")
                except ValueError:
                    logger.warning(f"Callback not found for event: {event_type}")

    def add_build(self, build: ScheduledBuild) -> bool:
        """
        Add build to queue.

        Args:
            build: ScheduledBuild to add

        Returns:
            True if successful, False if build already exists
        """
        with self._lock:
            if build.id in self._builds:
                logger.error(f"Build {build.id} already exists in queue")
                return False

            # Set initial status
            if build.status == BuildStatus.PENDING:
                build.status = BuildStatus.QUEUED
                build.updated_at = datetime.now()

            self._builds[build.id] = build

            # Persist to storage
            if not self.storage.add_build(build):
                # Rollback on storage failure
                del self._builds[build.id]
                return False

            logger.info(
                f"Added build to queue: {build.id} (priority: {build.priority.name})"
            )
            self._emit_event(QueueEvent.BUILD_ADDED, build)

            return True

    def remove_build(self, build_id: str) -> bool:
        """
        Remove build from queue.

        Args:
            build_id: ID of build to remove

        Returns:
            True if successful, False if build not found
        """
        with self._lock:
            if build_id not in self._builds:
                logger.warning(f"Build {build_id} not found in queue")
                return False

            build = self._builds[build_id]
            del self._builds[build_id]

            # Persist to storage
            self.storage.remove_build(build_id)

            logger.info(f"Removed build from queue: {build_id}")
            self._emit_event(QueueEvent.BUILD_REMOVED, build)

            # Check if queue is now empty
            if not self._builds:
                self._emit_event(QueueEvent.QUEUE_EMPTY)

            return True

    def get_build(self, build_id: str) -> ScheduledBuild | None:
        """
        Get build by ID.

        Args:
            build_id: Build ID

        Returns:
            ScheduledBuild or None if not found
        """
        with self._lock:
            return self._builds.get(build_id)

    def update_build_status(
        self, build_id: str, status: BuildStatus, error_message: str | None = None
    ) -> bool:
        """
        Update build status.

        Args:
            build_id: Build ID
            status: New status
            error_message: Optional error message (for failed builds)

        Returns:
            True if successful, False if build not found
        """
        with self._lock:
            build = self._builds.get(build_id)
            if not build:
                logger.error(f"Build {build_id} not found")
                return False

            old_status = build.status
            build.status = status
            build.updated_at = datetime.now()

            if error_message:
                build.error_message = error_message

            # Update timestamps based on status
            if status == BuildStatus.RUNNING:
                build.mark_started()
            elif status == BuildStatus.COMPLETED:
                build.mark_completed()
            elif status == BuildStatus.FAILED:
                build.mark_failed(error_message or "Unknown error")
            elif status == BuildStatus.CANCELLED:
                build.mark_cancelled()

            # Persist to storage
            self.storage.update_build(build)

            logger.info(
                f"Build {build_id} status: {old_status.value} -> {status.value}"
            )
            self._emit_event(
                QueueEvent.BUILD_STATUS_CHANGED,
                build,
                old_status=old_status,
                new_status=status,
            )

            # Emit specific events for important status changes
            if status == BuildStatus.RUNNING:
                self._emit_event(QueueEvent.BUILD_STARTED, build)
            elif status == BuildStatus.COMPLETED:
                self._emit_event(QueueEvent.BUILD_COMPLETED, build)
            elif status == BuildStatus.FAILED:
                self._emit_event(QueueEvent.BUILD_FAILED, build, error=error_message)

            return True

    def get_all_builds(self) -> list[ScheduledBuild]:
        """
        Get all builds in queue.

        Returns:
            List of all ScheduledBuild objects
        """
        with self._lock:
            return list(self._builds.values())

    def get_builds_by_status(
        self, status: BuildStatus | list[BuildStatus]
    ) -> list[ScheduledBuild]:
        """
        Get builds filtered by status.

        Args:
            status: Single status or list of statuses

        Returns:
            List of matching builds
        """
        with self._lock:
            if isinstance(status, BuildStatus):
                status = [status]

            return [b for b in self._builds.values() if b.status in status]

    def get_ready_builds(self) -> list[ScheduledBuild]:
        """
        Get builds ready to execute, sorted by priority.

        Returns builds that:
        - Are in PENDING or QUEUED status
        - Have passed their scheduled time (or have no scheduled time)
        - Sorted by: priority (asc) -> scheduled_time (asc) -> created_at (asc)

        Returns:
            List of ready builds in priority order
        """
        with self._lock:
            ready = [b for b in self._builds.values() if b.is_ready_to_run]

            # Sort by priority, scheduled time, then creation time
            ready.sort(
                key=lambda b: (
                    b.priority.value,  # Lower number = higher priority
                    b.scheduled_time or datetime.min,  # Earlier time first
                    b.created_at,  # Older builds first
                )
            )

            return ready

    def get_next_build(self) -> ScheduledBuild | None:
        """
        Get next build to execute without removing it from queue.

        Returns highest priority ready build based on:
        1. Priority level (CRITICAL first)
        2. Scheduled time (earlier first)
        3. Creation time (older first)

        Returns:
            Next ScheduledBuild to execute, or None if queue is empty
        """
        ready_builds = self.get_ready_builds()
        return ready_builds[0] if ready_builds else None

    def pop_next_build(self) -> ScheduledBuild | None:
        """
        Get and remove next build from queue.

        Returns:
            Next ScheduledBuild to execute, or None if queue is empty
        """
        with self._lock:
            next_build = self.get_next_build()
            if next_build:
                # Don't remove from queue, just mark as running
                # Build will be removed when completed/failed
                self.update_build_status(next_build.id, BuildStatus.RUNNING)
            return next_build

    def get_builds_by_priority(
        self, priority: SchedulePriority
    ) -> list[ScheduledBuild]:
        """
        Get builds with specific priority level.

        Args:
            priority: Priority level to filter by

        Returns:
            List of matching builds
        """
        with self._lock:
            return [b for b in self._builds.values() if b.priority == priority]

    def get_builds_due_before(self, time: datetime) -> list[ScheduledBuild]:
        """
        Get builds scheduled before a specific time.

        Args:
            time: Cutoff time

        Returns:
            List of builds due before the specified time
        """
        with self._lock:
            return [
                b
                for b in self._builds.values()
                if b.scheduled_time and b.scheduled_time <= time and b.is_ready_to_run
            ]

    def get_running_builds(self) -> list[ScheduledBuild]:
        """
        Get all currently running builds.

        Returns:
            List of builds with RUNNING status
        """
        return self.get_builds_by_status(BuildStatus.RUNNING)

    def get_pending_builds(self) -> list[ScheduledBuild]:
        """
        Get all pending builds (not yet queued).

        Returns:
            List of builds with PENDING status
        """
        return self.get_builds_by_status(BuildStatus.PENDING)

    def get_queued_builds(self) -> list[ScheduledBuild]:
        """
        Get all queued builds (waiting to execute).

        Returns:
            List of builds with QUEUED status
        """
        return self.get_builds_by_status(BuildStatus.QUEUED)

    def get_stats(self) -> dict[str, Any]:
        """
        Get queue statistics.

        Returns:
            Dictionary with queue statistics including:
            - total: Total builds in queue
            - by_status: Count by status
            - by_priority: Count by priority
            - ready_to_run: Number of ready builds
            - next_build: Next build to execute (if any)
        """
        with self._lock:
            builds = list(self._builds.values())
            ready = self.get_ready_builds()
            next_build = ready[0] if ready else None

            stats = {
                "total": len(builds),
                "by_status": {},
                "by_priority": {},
                "ready_to_run": len(ready),
                "next_build": next_build.to_dict() if next_build else None,
            }

            # Count by status
            for status in list(BuildStatus):
                count = sum(1 for b in builds if b.status == status)
                if count > 0:
                    stats["by_status"][status.value] = count

            # Count by priority
            for priority in list(SchedulePriority):
                count = sum(1 for b in builds if b.priority == priority)
                if count > 0:
                    stats["by_priority"][priority.value] = count

            return stats

    def clear_completed_builds(self) -> int:
        """
        Remove all completed, failed, and cancelled builds from queue.

        Returns:
            Number of builds removed
        """
        with self._lock:
            terminal_states = {
                BuildStatus.COMPLETED,
                BuildStatus.FAILED,
                BuildStatus.CANCELLED,
            }
            to_remove = [
                build_id
                for build_id, build in self._builds.items()
                if build.status in terminal_states
            ]

            for build_id in to_remove:
                self.remove_build(build_id)

            logger.info(f"Cleared {len(to_remove)} completed builds from queue")
            return len(to_remove)

    def is_empty(self) -> bool:
        """
        Check if queue is empty.

        Returns:
            True if no builds in queue
        """
        with self._lock:
            return len(self._builds) == 0

    def has_ready_builds(self) -> bool:
        """
        Check if any builds are ready to execute.

        Returns:
            True if at least one build is ready
        """
        return len(self.get_ready_builds()) > 0

    def refresh_from_storage(self) -> None:
        """
        Reload queue state from storage.

        Useful for synchronizing with external changes.
        """
        with self._lock:
            logger.info("Refreshing queue from storage")
            self._builds.clear()
            self._load_from_storage()
            logger.info(f"Reloaded {len(self._builds)} builds from storage")
