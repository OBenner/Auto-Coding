"""
Scheduler Service
=================

Main scheduler service with time-based execution and dependency resolution.

This module provides:
- Time-based build scheduling
- Dependency-aware execution
- Parallel build execution support
- Automatic retry on failures
- Event-driven notifications
- Thread-safe scheduler control

Usage:
    from scheduler.scheduler import Scheduler

    scheduler = Scheduler(project_dir)
    scheduler.start()
    # Scheduler runs in background, checking for ready builds
    # ...
    scheduler.stop()
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .dependency_resolver import (
    CircularDependencyError,
    DependencyResolver,
    MissingDependencyError,
)
from .models import BuildStatus, ScheduledBuild
from .queue_manager import QueueEvent, QueueManager
from .storage import SchedulerStorage

logger = logging.getLogger(__name__)


class SchedulerEvent:
    """
    Scheduler event types for callbacks.

    Events emitted during scheduler operations:
    - SCHEDULER_STARTED: Scheduler started running
    - SCHEDULER_STOPPED: Scheduler stopped
    - BUILD_EXECUTING: Build execution started
    - BUILD_SUCCESS: Build completed successfully
    - BUILD_FAILURE: Build failed
    - BUILD_RETRY: Build being retried after failure
    - DEPENDENCY_BLOCKED: Build blocked by unsatisfied dependencies
    - CYCLE_DETECTED: Circular dependency detected
    """

    SCHEDULER_STARTED = "scheduler_started"
    SCHEDULER_STOPPED = "scheduler_stopped"
    BUILD_EXECUTING = "build_executing"
    BUILD_SUCCESS = "build_success"
    BUILD_FAILURE = "build_failure"
    BUILD_RETRY = "build_retry"
    DEPENDENCY_BLOCKED = "dependency_blocked"
    CYCLE_DETECTED = "cycle_detected"


class Scheduler:
    """
    Main scheduler service for automated build execution.

    Responsibilities:
    - Monitor queue for ready builds
    - Resolve dependencies and determine execution order
    - Execute builds at scheduled times
    - Handle build failures and retries
    - Coordinate parallel execution (when dependencies allow)
    - Emit events for notifications
    - Maintain scheduler state

    The scheduler runs in a background thread, periodically checking
    for builds that are ready to execute based on:
    1. Scheduled time has passed (or no scheduled time)
    2. All dependencies are satisfied
    3. Priority ordering

    Thread Safety:
    - All public methods are thread-safe
    - Uses internal locks for state management
    - Background scheduler thread handles build execution
    """

    def __init__(
        self,
        project_dir: Path | str,
        check_interval: int = 30,
        max_parallel_builds: int = 1,
    ):
        """
        Initialize scheduler service.

        Args:
            project_dir: Root directory of the project
            check_interval: Seconds between queue checks (default: 30)
            max_parallel_builds: Maximum concurrent builds (default: 1)
        """
        self.project_dir = Path(project_dir).resolve()
        self.check_interval = check_interval
        self.max_parallel_builds = max_parallel_builds

        # Components
        self.storage = SchedulerStorage(project_dir)
        self.queue_manager = QueueManager(project_dir, storage=self.storage)
        self.dependency_resolver = DependencyResolver()

        # Thread control
        self._running = False
        self._lock = threading.RLock()
        self._scheduler_thread: threading.Thread | None = None

        # Track completed builds for dependency resolution
        self._completed_specs: set[str] = set()

        # Event callbacks
        self._event_callbacks: dict[str, list[Callable]] = {}

        # Register for queue events
        self.queue_manager.register_callback(
            QueueEvent.BUILD_COMPLETED, self._on_build_completed
        )
        self.queue_manager.register_callback(
            QueueEvent.BUILD_FAILED, self._on_build_failed
        )

        logger.info(
            f"Scheduler initialized (interval: {check_interval}s, "
            f"max_parallel: {max_parallel_builds})"
        )

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register callback for scheduler events.

        Args:
            event_type: Event type to listen for (from SchedulerEvent)
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

    def _emit_event(
        self, event_type: str, build: ScheduledBuild | None = None, **kwargs: Any
    ) -> None:
        """
        Emit event to registered callbacks.

        Args:
            event_type: Type of event (from SchedulerEvent)
            build: Related ScheduledBuild (if applicable)
            **kwargs: Additional event data
        """
        callbacks = self._event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                callback(event_type=event_type, build=build, **kwargs)
            except Exception as e:
                logger.error(f"Error in event callback for {event_type}: {e}")

    def start(self) -> bool:
        """
        Start the scheduler service.

        Launches background thread that monitors the queue and executes
        ready builds.

        Returns:
            True if started successfully, False if already running
        """
        with self._lock:
            if self._running:
                logger.warning("Scheduler already running")
                return False

            self._running = True
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop, daemon=True, name="SchedulerThread"
            )
            self._scheduler_thread.start()

            logger.info("Scheduler started")
            self._emit_event(SchedulerEvent.SCHEDULER_STARTED)
            return True

    def stop(self) -> bool:
        """
        Stop the scheduler service.

        Gracefully stops the background scheduler thread. Running builds
        will continue to completion.

        Returns:
            True if stopped successfully, False if not running
        """
        with self._lock:
            if not self._running:
                logger.warning("Scheduler not running")
                return False

            self._running = False

        # Wait for scheduler thread to finish
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=10.0)
            if self._scheduler_thread.is_alive():
                logger.warning("Scheduler thread did not stop gracefully")

        logger.info("Scheduler stopped")
        self._emit_event(SchedulerEvent.SCHEDULER_STOPPED)
        return True

    def is_running(self) -> bool:
        """
        Check if scheduler is running.

        Returns:
            True if scheduler is active
        """
        with self._lock:
            return self._running

    def schedule_build(self, build: ScheduledBuild) -> bool:
        """
        Schedule a new build.

        Validates dependencies and adds build to queue.

        Args:
            build: ScheduledBuild to schedule

        Returns:
            True if scheduled successfully, False otherwise
        """
        try:
            # Validate dependencies if build has any
            if build.dependencies:
                all_builds = self.queue_manager.get_all_builds() + [build]
                try:
                    self.dependency_resolver.validate_dependencies(all_builds)
                except CircularDependencyError as e:
                    logger.error(f"Circular dependency detected: {e}")
                    self._emit_event(
                        SchedulerEvent.CYCLE_DETECTED, build, cycle=e.cycle
                    )
                    return False
                except MissingDependencyError as e:
                    logger.error(f"Missing dependencies: {e}")
                    return False

            # Add to queue
            success = self.queue_manager.add_build(build)
            if success:
                logger.info(
                    f"Scheduled build: {build.spec_id} "
                    f"(time: {build.scheduled_time or 'immediate'}, "
                    f"priority: {build.priority.name})"
                )
            return success

        except Exception as e:
            logger.error(f"Failed to schedule build {build.spec_id}: {e}")
            return False

    def cancel_build(self, build_id: str) -> bool:
        """
        Cancel a scheduled build.

        Args:
            build_id: ID of build to cancel

        Returns:
            True if cancelled successfully, False otherwise
        """
        build = self.queue_manager.get_build(build_id)
        if not build:
            logger.error(f"Build {build_id} not found")
            return False

        # Can only cancel pending/queued builds
        if build.status not in (BuildStatus.PENDING, BuildStatus.QUEUED):
            logger.error(
                f"Cannot cancel build {build_id} with status {build.status.value}"
            )
            return False

        return self.queue_manager.update_build_status(build_id, BuildStatus.CANCELLED)

    def get_queue_status(self) -> dict[str, Any]:
        """
        Get current queue status.

        Returns:
            Dictionary with queue statistics and status
        """
        stats = self.queue_manager.get_stats()
        stats["scheduler_running"] = self._running
        stats["completed_specs"] = list(self._completed_specs)
        stats["dependency_stats"] = self.dependency_resolver.get_dependency_stats(
            self.queue_manager.get_all_builds()
        )
        return stats

    def _scheduler_loop(self) -> None:
        """
        Main scheduler loop that runs in background thread.

        Periodically checks for ready builds and executes them.
        """
        logger.info("Scheduler loop started")

        while self._running:
            try:
                self._process_ready_builds()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)

            # Sleep for check interval
            time.sleep(self.check_interval)

        logger.info("Scheduler loop stopped")

    def _process_ready_builds(self) -> None:
        """
        Process builds that are ready to execute.

        Checks queue for ready builds, resolves dependencies, and executes
        builds that can run.
        """
        # Get all ready builds from queue
        ready_builds = self.queue_manager.get_ready_builds()

        if not ready_builds:
            return

        logger.debug(f"Found {len(ready_builds)} ready builds")

        # Filter by dependency satisfaction
        executable_builds = self.dependency_resolver.get_ready_builds(
            ready_builds, self._completed_specs
        )

        if not executable_builds:
            # Log blocked builds
            blocked = self.dependency_resolver.get_blocked_builds(
                ready_builds, self._completed_specs
            )
            if blocked:
                for build in blocked:
                    unsatisfied = [
                        dep
                        for dep in build.dependencies
                        if dep not in self._completed_specs
                    ]
                    logger.debug(
                        f"Build {build.spec_id} blocked by dependencies: {unsatisfied}"
                    )
                    self._emit_event(
                        SchedulerEvent.DEPENDENCY_BLOCKED,
                        build,
                        unsatisfied_deps=unsatisfied,
                    )
            return

        # Limit to max parallel builds
        running_count = len(self.queue_manager.get_running_builds())
        available_slots = self.max_parallel_builds - running_count

        if available_slots <= 0:
            logger.debug(
                f"Max parallel builds ({self.max_parallel_builds}) reached, waiting"
            )
            return

        # Execute builds up to available slots
        builds_to_execute = executable_builds[:available_slots]

        for build in builds_to_execute:
            self._execute_build(build)

    def _execute_build(self, build: ScheduledBuild) -> None:
        """
        Execute a single build.

        Args:
            build: ScheduledBuild to execute
        """
        logger.info(f"Executing build: {build.spec_id}")

        # Update status to running
        self.queue_manager.update_build_status(build.id, BuildStatus.RUNNING)
        self._emit_event(SchedulerEvent.BUILD_EXECUTING, build)

        # Execute build in separate thread to avoid blocking scheduler
        thread = threading.Thread(
            target=self._run_build_process,
            args=(build,),
            daemon=True,
            name=f"Build-{build.spec_id}",
        )
        thread.start()

    def _run_build_process(self, build: ScheduledBuild) -> None:
        """
        Run the build process (executes in separate thread).

        Args:
            build: ScheduledBuild to execute
        """
        try:
            # Execute run.py for the spec
            cmd = ["python", "run.py", "--spec", build.spec_id]

            logger.info(f"Running command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                cwd=self.project_dir / "apps" / "backend",
                capture_output=True,
                text=True,
                timeout=7200,  # 2 hour timeout
            )

            if result.returncode == 0:
                # Build succeeded
                logger.info(f"Build {build.spec_id} completed successfully")
                self.queue_manager.update_build_status(build.id, BuildStatus.COMPLETED)
                self._completed_specs.add(build.spec_id)
                self._emit_event(SchedulerEvent.BUILD_SUCCESS, build)

            else:
                # Build failed
                error_message = result.stderr or result.stdout or "Unknown error"
                logger.error(f"Build {build.spec_id} failed: {error_message}")

                # Check if we can retry
                build = self.queue_manager.get_build(build.id)
                if build and build.can_retry:
                    logger.info(
                        f"Retrying build {build.spec_id} "
                        f"(attempt {build.retry_count + 1}/{build.max_retries})"
                    )
                    build.increment_retry()
                    self.queue_manager.update_build_status(
                        build.id, BuildStatus.QUEUED
                    )
                    self.queue_manager.storage.update_build(build)
                    self._emit_event(
                        SchedulerEvent.BUILD_RETRY,
                        build,
                        retry_count=build.retry_count,
                    )
                else:
                    # No more retries
                    self.queue_manager.update_build_status(
                        build.id, BuildStatus.FAILED, error_message=error_message
                    )
                    self._emit_event(
                        SchedulerEvent.BUILD_FAILURE, build, error=error_message
                    )

        except subprocess.TimeoutExpired:
            logger.error(f"Build {build.spec_id} timed out")
            self.queue_manager.update_build_status(
                build.id, BuildStatus.FAILED, error_message="Build timed out"
            )
            self._emit_event(
                SchedulerEvent.BUILD_FAILURE, build, error="Build timed out"
            )

        except Exception as e:
            logger.error(f"Error executing build {build.spec_id}: {e}", exc_info=True)
            self.queue_manager.update_build_status(
                build.id, BuildStatus.FAILED, error_message=str(e)
            )
            self._emit_event(SchedulerEvent.BUILD_FAILURE, build, error=str(e))

    def _on_build_completed(self, event_type: str, build: ScheduledBuild, **kwargs: Any) -> None:
        """
        Callback when build completes.

        Args:
            event_type: Event type
            build: Completed build
            **kwargs: Additional event data
        """
        logger.info(f"Build completed: {build.spec_id}")
        self._completed_specs.add(build.spec_id)

    def _on_build_failed(self, event_type: str, build: ScheduledBuild, **kwargs: Any) -> None:
        """
        Callback when build fails.

        Args:
            event_type: Event type
            build: Failed build
            **kwargs: Additional event data
        """
        logger.warning(f"Build failed: {build.spec_id}")
        # Note: We don't add to completed_specs so dependent builds won't run

    def get_next_scheduled_build(self) -> ScheduledBuild | None:
        """
        Get next build that will execute.

        Considers dependencies and scheduled times.

        Returns:
            Next ScheduledBuild to execute, or None if queue is empty
        """
        ready_builds = self.queue_manager.get_ready_builds()
        if not ready_builds:
            return None

        # Filter by dependency satisfaction
        executable_builds = self.dependency_resolver.get_ready_builds(
            ready_builds, self._completed_specs
        )

        return executable_builds[0] if executable_builds else None

    def get_dependency_chain(self, build_id: str) -> list[str]:
        """
        Get dependency chain for a build.

        Args:
            build_id: Build ID

        Returns:
            List of spec IDs in dependency chain (ordered)
        """
        build = self.queue_manager.get_build(build_id)
        if not build:
            return []

        all_builds = self.queue_manager.get_all_builds()
        return self.dependency_resolver.get_dependency_chain(build, all_builds)

    def get_parallel_execution_groups(self) -> list[list[ScheduledBuild]]:
        """
        Get groups of builds that can execute in parallel.

        Returns:
            List of groups, where each group contains builds that can run
            in parallel
        """
        all_builds = self.queue_manager.get_all_builds()
        return self.dependency_resolver.get_parallel_execution_groups(all_builds)

    def cleanup_completed_builds(self, days_old: int = 7) -> int:
        """
        Remove old completed/failed builds from queue.

        Args:
            days_old: Remove builds completed more than this many days ago

        Returns:
            Number of builds removed
        """
        removed = self.storage.cleanup_completed_builds(days_old)
        if removed > 0:
            # Refresh queue from storage
            self.queue_manager.refresh_from_storage()
        return removed
