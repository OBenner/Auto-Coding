"""
Scheduler Storage Module
========================

Handles persistence of scheduled builds to disk.

This module provides:
- Loading/saving scheduled builds from JSON
- Querying builds by status, priority, time
- Updating build status
- Cleaning up completed builds
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import BuildStatus, ScheduledBuild, SchedulePriority

logger = logging.getLogger(__name__)


class SchedulerStorage:
    """
    Manages persistence of scheduled build data.

    Responsibilities:
    - Load/save scheduled builds to JSON
    - Query builds by various criteria
    - Update build status atomically
    - Maintain schedule integrity
    """

    def __init__(self, project_dir: Path | str):
        """
        Initialize scheduler storage.

        Args:
            project_dir: Root directory of the project
        """
        self.project_dir = Path(project_dir).resolve()
        self.storage_dir = self.project_dir / ".auto-claude" / "scheduler"
        self.schedule_file = self.storage_dir / "schedule.json"

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def load_all_builds(self) -> list[ScheduledBuild]:
        """
        Load all scheduled builds from disk.

        Returns:
            List of ScheduledBuild objects
        """
        if not self.schedule_file.exists():
            return []

        try:
            with open(self.schedule_file, encoding="utf-8") as f:
                data = json.load(f)

            builds = []
            for build_data in data.get("builds", []):
                try:
                    builds.append(ScheduledBuild.from_dict(build_data))
                except Exception as e:
                    logger.error(f"Failed to parse build {build_data.get('id')}: {e}")

            logger.debug(f"Loaded {len(builds)} scheduled builds")
            return builds

        except Exception as e:
            logger.error(f"Failed to load schedule data: {e}")
            return []

    def save_builds(self, builds: list[ScheduledBuild]) -> bool:
        """
        Persist scheduled builds to disk.

        Args:
            builds: List of ScheduledBuild objects

        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                "builds": [build.to_dict() for build in builds],
                "last_updated": datetime.now().isoformat(),
            }

            with open(self.schedule_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(builds)} scheduled builds")
            return True

        except Exception as e:
            logger.error(f"Failed to save schedule data: {e}")
            return False

    def add_build(self, build: ScheduledBuild) -> bool:
        """
        Add a new scheduled build.

        Args:
            build: ScheduledBuild object to add

        Returns:
            True if successful, False otherwise
        """
        builds = self.load_all_builds()

        # Check for duplicate ID
        if any(b.id == build.id for b in builds):
            logger.error(f"Build with ID {build.id} already exists")
            return False

        builds.append(build)
        return self.save_builds(builds)

    def update_build(self, build: ScheduledBuild) -> bool:
        """
        Update an existing scheduled build.

        Args:
            build: ScheduledBuild object with updates

        Returns:
            True if successful, False otherwise
        """
        builds = self.load_all_builds()

        # Find and update the build
        updated = False
        for i, existing_build in enumerate(builds):
            if existing_build.id == build.id:
                builds[i] = build
                updated = True
                break

        if not updated:
            logger.error(f"Build with ID {build.id} not found")
            return False

        return self.save_builds(builds)

    def remove_build(self, build_id: str) -> bool:
        """
        Remove a scheduled build.

        Args:
            build_id: ID of build to remove

        Returns:
            True if successful, False otherwise
        """
        builds = self.load_all_builds()
        initial_count = len(builds)

        builds = [b for b in builds if b.id != build_id]

        if len(builds) == initial_count:
            logger.warning(f"Build with ID {build_id} not found")
            return False

        return self.save_builds(builds)

    def get_build_by_id(self, build_id: str) -> ScheduledBuild | None:
        """
        Get a scheduled build by ID.

        Args:
            build_id: ID of build to retrieve

        Returns:
            ScheduledBuild object or None if not found
        """
        builds = self.load_all_builds()
        for build in builds:
            if build.id == build_id:
                return build
        return None

    def get_builds_by_status(
        self, status: BuildStatus | list[BuildStatus]
    ) -> list[ScheduledBuild]:
        """
        Get builds filtered by status.

        Args:
            status: Single status or list of statuses to filter by

        Returns:
            List of matching ScheduledBuild objects
        """
        builds = self.load_all_builds()

        if isinstance(status, BuildStatus):
            status = [status]

        return [b for b in builds if b.status in status]

    def get_builds_by_spec(self, spec_id: str) -> list[ScheduledBuild]:
        """
        Get all builds for a specific spec.

        Args:
            spec_id: Spec ID to filter by

        Returns:
            List of matching ScheduledBuild objects
        """
        builds = self.load_all_builds()
        return [b for b in builds if b.spec_id == spec_id]

    def get_ready_builds(self) -> list[ScheduledBuild]:
        """
        Get builds that are ready to execute.

        Returns builds that are:
        - In PENDING or QUEUED status
        - Past their scheduled time (or have no scheduled time)
        - Sorted by priority and then scheduled time

        Returns:
            List of ready ScheduledBuild objects sorted by priority
        """
        builds = self.load_all_builds()

        # Filter to ready builds
        ready_builds = [b for b in builds if b.is_ready_to_run]

        # Sort by priority (lower number = higher priority) and then by scheduled time
        ready_builds.sort(
            key=lambda b: (
                b.priority.value,
                b.scheduled_time or datetime.min,
            )
        )

        return ready_builds

    def get_builds_due_before(self, time: datetime) -> list[ScheduledBuild]:
        """
        Get builds scheduled before a specific time.

        Args:
            time: Cutoff time

        Returns:
            List of ScheduledBuild objects
        """
        builds = self.load_all_builds()
        return [
            b
            for b in builds
            if b.scheduled_time and b.scheduled_time <= time and b.is_ready_to_run
        ]

    def cleanup_completed_builds(self, days_old: int = 7) -> int:
        """
        Remove completed/failed builds older than specified days.

        Args:
            days_old: Remove builds completed more than this many days ago

        Returns:
            Number of builds removed
        """
        builds = self.load_all_builds()
        cutoff_time = datetime.now().timestamp() - (days_old * 86400)

        # Keep builds that are not terminal states or are recent
        terminal_states = (BuildStatus.COMPLETED, BuildStatus.FAILED, BuildStatus.CANCELLED)

        initial_count = len(builds)
        builds = [
            b
            for b in builds
            if b.status not in terminal_states
            or (b.completed_at and b.completed_at.timestamp() > cutoff_time)
        ]

        removed = initial_count - len(builds)
        if removed > 0:
            self.save_builds(builds)
            logger.info(f"Cleaned up {removed} old builds")

        return removed

    def get_stats(self) -> dict[str, Any]:
        """
        Get statistics about scheduled builds.

        Returns:
            Dictionary with build statistics
        """
        builds = self.load_all_builds()

        stats = {
            "total": len(builds),
            "by_status": {},
            "by_priority": {},
            "ready_to_run": 0,
            "with_dependencies": 0,
            "average_duration_seconds": None,
        }

        # Count by status
        for status in BuildStatus:
            count = sum(1 for b in builds if b.status == status)
            if count > 0:
                stats["by_status"][status.value] = count

        # Count by priority
        for priority in SchedulePriority:
            count = sum(1 for b in builds if b.priority == priority)
            if count > 0:
                stats["by_priority"][priority.value] = count

        # Count ready builds
        stats["ready_to_run"] = sum(1 for b in builds if b.is_ready_to_run)

        # Count builds with dependencies
        stats["with_dependencies"] = sum(1 for b in builds if b.dependencies)

        # Calculate average duration for completed builds
        durations = [b.duration_seconds for b in builds if b.duration_seconds]
        if durations:
            stats["average_duration_seconds"] = sum(durations) / len(durations)

        return stats
