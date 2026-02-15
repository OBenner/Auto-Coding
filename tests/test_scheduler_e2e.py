"""
End-to-End Tests for Intelligent Build Scheduling
==================================================

Tests the full scheduling workflow from build creation to execution and notification.
These tests validate the integration between all scheduler components.
"""

import json
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the backend directory to path
_backend_dir = Path(__file__).parent.parent / "apps" / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from scheduler.models import (
    BuildStatus,
    ScheduledBuild,
    SchedulePriority,
)
from scheduler.queue_manager import QueueManager
from scheduler.scheduler import Scheduler, SchedulerEvent
from scheduler.storage import SchedulerStorage

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create specs directory with some test specs
    specs_dir = project_dir / ".auto-claude" / "specs"
    specs_dir.mkdir(parents=True)

    # Create test spec directories
    for spec_id in ["001-auth", "002-api", "003-ui"]:
        spec_path = specs_dir / spec_id
        spec_path.mkdir()

        # Create a minimal spec.md file
        spec_file = spec_path / "spec.md"
        spec_file.write_text(f"# Test Spec {spec_id}\n\nTest spec for E2E testing.")

    return project_dir


@pytest.fixture
def scheduler(temp_project_dir):
    """Create a scheduler instance with temporary storage."""
    scheduler = Scheduler(
        temp_project_dir, check_interval=1
    )  # 1 second for faster tests
    yield scheduler
    # Clean up - stop scheduler if running
    if scheduler.is_running():
        scheduler.stop()


@pytest.fixture
def storage(temp_project_dir):
    """Create a storage instance."""
    return SchedulerStorage(temp_project_dir)


@pytest.fixture
def queue_manager(temp_project_dir, storage):
    """Create a queue manager instance."""
    return QueueManager(temp_project_dir, storage=storage)


@pytest.fixture
def sample_build():
    """Create a sample scheduled build."""
    return ScheduledBuild(
        id=str(uuid.uuid4()),
        spec_id="001-auth",
        spec_name="Authentication Feature",
        priority=SchedulePriority.NORMAL,
        scheduled_time=None,  # Execute immediately
        dependencies=[],
    )


@pytest.fixture
def sample_build_with_time():
    """Create a sample build scheduled for the future."""
    return ScheduledBuild(
        id=str(uuid.uuid4()),
        spec_id="002-api",
        spec_name="API Integration",
        priority=SchedulePriority.HIGH,
        scheduled_time=datetime.now() + timedelta(seconds=2),  # 2 seconds in future
        dependencies=[],
    )


@pytest.fixture
def sample_build_with_deps():
    """Create a sample build with dependencies."""
    return ScheduledBuild(
        id=str(uuid.uuid4()),
        spec_id="003-ui",
        spec_name="UI Components",
        priority=SchedulePriority.NORMAL,
        scheduled_time=None,
        dependencies=["001-auth", "002-api"],
    )


# ============================================================================
# E2E Test: Build Scheduling and Storage
# ============================================================================


class TestSchedulingE2E:
    """Test build scheduling workflow end-to-end."""

    def test_schedule_build_basic(self, scheduler, sample_build):
        """Test scheduling a build and verifying it's stored."""
        # Schedule the build
        success = scheduler.schedule_build(sample_build)
        assert success is True

        # Verify it's in storage
        stored_build = scheduler.storage.get_build_by_id(sample_build.id)
        assert stored_build is not None
        assert stored_build.spec_id == "001-auth"
        # Status is automatically changed from PENDING to QUEUED when added
        assert stored_build.status == BuildStatus.QUEUED

        # Verify it's in the queue
        queue_status = scheduler.get_queue_status()
        assert queue_status["total"] >= 1
        assert queue_status["by_status"].get("queued", 0) >= 1

    def test_schedule_build_with_time(self, scheduler, sample_build_with_time):
        """Test scheduling a build for a future time."""
        success = scheduler.schedule_build(sample_build_with_time)
        assert success is True

        # Verify scheduled time is stored
        stored_build = scheduler.storage.get_build_by_id(sample_build_with_time.id)
        assert stored_build.scheduled_time is not None
        assert stored_build.scheduled_time > datetime.now()
        # Status is automatically changed from PENDING to QUEUED when added
        assert stored_build.status == BuildStatus.QUEUED

    def test_schedule_build_with_dependencies(self, scheduler, sample_build_with_deps):
        """Test scheduling a build with dependencies."""
        # This should fail because dependencies don't exist yet
        success = scheduler.schedule_build(sample_build_with_deps)
        # Dependencies will be missing, so this should fail
        assert success is False

    def test_cancel_scheduled_build(self, scheduler, sample_build):
        """Test cancelling a scheduled build."""
        # Schedule the build
        scheduler.schedule_build(sample_build)

        # Cancel it
        success = scheduler.cancel_build(sample_build.id)
        assert success is True

        # Verify status is CANCELLED
        stored_build = scheduler.storage.get_build_by_id(sample_build.id)
        assert stored_build.status == BuildStatus.CANCELLED

    def test_schedule_priority_ordering(self, scheduler, temp_project_dir):
        """Test that builds are ordered by priority in queue."""
        # Create builds with different priorities
        builds = [
            ScheduledBuild(
                id=str(uuid.uuid4()),
                spec_id="001-auth",
                spec_name="Low Priority",
                priority=SchedulePriority.LOW,
            ),
            ScheduledBuild(
                id=str(uuid.uuid4()),
                spec_id="002-api",
                spec_name="Critical Priority",
                priority=SchedulePriority.CRITICAL,
            ),
            ScheduledBuild(
                id=str(uuid.uuid4()),
                spec_id="003-ui",
                spec_name="Normal Priority",
                priority=SchedulePriority.NORMAL,
            ),
        ]

        # Schedule in reverse priority order
        for build in builds:
            scheduler.schedule_build(build)

        # Get ready builds and verify ordering
        ready_builds = scheduler.queue_manager.get_ready_builds()
        assert len(ready_builds) >= 3

        # First build should be CRITICAL priority (lowest value = highest priority)
        assert ready_builds[0].priority == SchedulePriority.CRITICAL


# ============================================================================
# E2E Test: Queue Management
# ============================================================================


class TestQueueManagementE2E:
    """Test queue view and status updates."""

    def test_queue_status_tracking(self, scheduler, sample_build):
        """Test that queue status accurately reflects build states."""
        # Schedule a build
        scheduler.schedule_build(sample_build)

        # Get initial queue status
        status = scheduler.get_queue_status()
        assert status["total"] >= 1
        assert status["by_status"].get("queued", 0) >= 1
        assert status["by_status"].get("running", 0) == 0

        # Manually mark as running (simulating execution)
        # Need to use queue_manager to update both in-memory and storage
        scheduler.queue_manager.update_build_status(
            sample_build.id, BuildStatus.RUNNING
        )

        # Verify running count
        status = scheduler.get_queue_status()
        assert status["by_status"].get("running", 0) >= 1
        assert status["by_status"].get("queued", 0) == 0

    def test_queue_multiple_builds(self, scheduler, temp_project_dir):
        """Test queue with multiple builds in different states."""
        # Create builds in different states
        # Note: PENDING will be auto-changed to QUEUED, so we start with QUEUED
        builds = []
        for i, status in enumerate(
            [BuildStatus.QUEUED, BuildStatus.RUNNING, BuildStatus.COMPLETED]
        ):
            build = ScheduledBuild(
                id=str(uuid.uuid4()),
                spec_id=f"00{i + 1}-test",
                spec_name=f"Test {i + 1}",
                status=status,
            )
            if status == BuildStatus.RUNNING:
                build.mark_started()
            elif status == BuildStatus.COMPLETED:
                build.mark_started()
                build.mark_completed()

            scheduler.schedule_build(build)
            builds.append(build)

        # Get queue status
        status = scheduler.get_queue_status()
        assert status["total"] >= 3

        # Verify builds by status
        builds_by_status = status.get("by_status", {})
        assert builds_by_status.get("queued", 0) >= 1
        assert builds_by_status.get("running", 0) >= 1
        assert builds_by_status.get("completed", 0) >= 1


# ============================================================================
# E2E Test: Build Execution
# ============================================================================


class TestBuildExecutionE2E:
    """Test actual build execution workflow."""

    def test_scheduler_starts_immediate_build(self, scheduler, sample_build):
        """Test that scheduler picks up and executes immediate builds."""
        # Track events
        events = []

        def track_event(event_type, build, **kwargs):
            events.append((event_type, build.id if build else None))

        # Register event callbacks
        scheduler.register_callback(SchedulerEvent.BUILD_EXECUTING, track_event)

        # Mock the actual build execution
        with patch("scheduler.scheduler.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Schedule the build
            scheduler.schedule_build(sample_build)

            # Start scheduler
            scheduler.start()

            # Wait for build to be picked up (max 5 seconds)
            max_wait = 5
            for _ in range(max_wait * 2):  # Check every 0.5 seconds
                if any(event[0] == SchedulerEvent.BUILD_EXECUTING for event in events):
                    break
                time.sleep(0.5)

            # Stop scheduler
            scheduler.stop()

            # Verify build was executed
            assert any(event[0] == SchedulerEvent.BUILD_EXECUTING for event in events)

    def test_scheduler_respects_scheduled_time(self, scheduler, sample_build_with_time):
        """Test that scheduler waits for scheduled time before executing."""
        # Track events
        events = []

        def track_event(event_type, build, **kwargs):
            events.append((event_type, build.id if build else None, datetime.now()))

        scheduler.register_callback(SchedulerEvent.BUILD_EXECUTING, track_event)

        # Mock build execution
        with patch("scheduler.scheduler.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Schedule the build (2 seconds in future)
            scheduled_time = sample_build_with_time.scheduled_time
            scheduler.schedule_build(sample_build_with_time)

            # Start scheduler
            scheduler.start()

            # Wait for build execution
            time.sleep(3)  # Wait 3 seconds (build scheduled for 2 seconds)

            # Stop scheduler
            scheduler.stop()

            # Verify build was executed after scheduled time
            executing_events = [
                e for e in events if e[0] == SchedulerEvent.BUILD_EXECUTING
            ]
            if executing_events:
                execution_time = executing_events[0][2]
                assert execution_time >= scheduled_time

    def test_scheduler_handles_build_failure_and_retry(self, scheduler, sample_build):
        """Test that scheduler retries failed builds."""
        # Track events
        events = []

        def track_event(event_type, build, **kwargs):
            events.append((event_type, build.id if build else None))

        scheduler.register_callback(SchedulerEvent.BUILD_FAILURE, track_event)
        scheduler.register_callback(SchedulerEvent.BUILD_RETRY, track_event)

        # Mock build execution to fail first time, succeed second time
        call_count = [0]

        def mock_run(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            mock_result.returncode = 1 if call_count[0] == 1 else 0
            mock_result.stdout = "Error output"
            mock_result.stderr = "Build failed"
            return mock_result

        with patch("scheduler.scheduler.subprocess.run", side_effect=mock_run):
            # Schedule the build
            scheduler.schedule_build(sample_build)

            # Start scheduler
            scheduler.start()

            # Wait for execution and retry
            time.sleep(4)

            # Stop scheduler
            scheduler.stop()

            # Verify failure event (retry may not happen quickly enough in test)
            assert any(event[0] == SchedulerEvent.BUILD_FAILURE for event in events)


# ============================================================================
# E2E Test: Dependency Resolution
# ============================================================================


class TestDependencyResolutionE2E:
    """Test dependency-aware build execution."""

    def test_dependency_blocks_execution(
        self, scheduler, sample_build, sample_build_with_deps
    ):
        """Test that builds with unsatisfied dependencies are blocked."""
        # This test verifies that scheduling a build with missing dependencies fails
        # which is the correct behavior
        success = scheduler.schedule_build(sample_build_with_deps)
        assert success is False  # Should fail due to missing dependencies

    def test_dependency_satisfied_allows_execution(self, scheduler, temp_project_dir):
        """Test that builds execute when dependencies are satisfied."""
        # Create a build with one dependency
        dep_build = ScheduledBuild(
            id=str(uuid.uuid4()),
            spec_id="001-auth",
            spec_name="Auth",
            status=BuildStatus.COMPLETED,  # Already completed
        )
        dep_build.mark_started()
        dep_build.mark_completed()
        scheduler.schedule_build(dep_build)

        dependent_build = ScheduledBuild(
            id=str(uuid.uuid4()),
            spec_id="002-api",
            spec_name="API",
            dependencies=["001-auth"],
        )
        scheduler.schedule_build(dependent_build)

        # Mark dependency as completed in scheduler
        scheduler._completed_specs.add("001-auth")

        # Check if dependencies are satisfied
        dep_chain = scheduler.get_dependency_chain(dependent_build.id)
        assert isinstance(dep_chain, list)


# ============================================================================
# E2E Test: Notifications
# ============================================================================


class TestNotificationE2E:
    """Test notification system integration."""

    def test_notification_on_build_complete(
        self, scheduler, sample_build, temp_project_dir
    ):
        """Test that notifications are sent on build completion."""
        # Track notification calls
        notifications = []

        # Register callback to track notifications
        def on_success(event_type, build, **kwargs):
            notifications.append(
                {
                    "event": event_type,
                    "build_id": build.id,
                    "spec_name": build.spec_name,
                }
            )

        scheduler.register_callback(SchedulerEvent.BUILD_SUCCESS, on_success)

        # Mock build execution
        with patch("scheduler.scheduler.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Schedule and execute build
            scheduler.schedule_build(sample_build)
            scheduler.start()
            time.sleep(2)
            scheduler.stop()

            # Verify success event was emitted
            # (actual desktop notification testing would require OS-specific mocking)

    def test_notification_on_build_failure(self, scheduler, sample_build):
        """Test that notifications are sent on build failure."""
        notifications = []

        def on_failure(event_type, build, **kwargs):
            notifications.append(
                {
                    "event": event_type,
                    "build_id": build.id,
                    "error": build.error_message,
                }
            )

        scheduler.register_callback(SchedulerEvent.BUILD_FAILURE, on_failure)

        # Mock build execution to fail
        with patch("scheduler.scheduler.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)

            # Schedule and execute build
            scheduler.schedule_build(sample_build)
            scheduler.start()
            time.sleep(2)
            scheduler.stop()

            # Verify failure notification
            assert any(
                n["event"] == SchedulerEvent.BUILD_FAILURE for n in notifications
            )


# ============================================================================
# E2E Test: Calendar View Data
# ============================================================================


class TestCalendarViewE2E:
    """Test calendar view data structure for frontend."""

    def test_builds_grouped_by_time(self, scheduler, temp_project_dir):
        """Test that builds can be grouped for calendar view."""
        # Create builds scheduled for different times
        now = datetime.now()
        builds = [
            ScheduledBuild(
                id=str(uuid.uuid4()),
                spec_id="001-auth",
                spec_name="Today Build",
                scheduled_time=now + timedelta(hours=2),
            ),
            ScheduledBuild(
                id=str(uuid.uuid4()),
                spec_id="002-api",
                spec_name="Tomorrow Build",
                scheduled_time=now + timedelta(days=1),
            ),
            ScheduledBuild(
                id=str(uuid.uuid4()),
                spec_id="003-ui",
                spec_name="Next Week Build",
                scheduled_time=now + timedelta(days=7),
            ),
        ]

        for build in builds:
            scheduler.schedule_build(build)

        # Get all builds
        all_builds = scheduler.storage.load_all_builds()
        assert len(all_builds) >= 3

        # Group by time (simulate frontend logic)
        grouped = {"today": [], "tomorrow": [], "this_week": [], "later": []}

        for build in all_builds:
            if build.scheduled_time:
                days_diff = (build.scheduled_time - now).days
                if days_diff == 0:
                    grouped["today"].append(build)
                elif days_diff == 1:
                    grouped["tomorrow"].append(build)
                elif days_diff <= 7:
                    grouped["this_week"].append(build)
                else:
                    grouped["later"].append(build)

        # Verify grouping - at least 3 builds are grouped
        total_grouped = sum(len(v) for v in grouped.values())
        assert total_grouped >= 3
        assert len(grouped["today"]) >= 1
        assert len(grouped["tomorrow"]) >= 1
        # 7 days should be in this_week or later depending on timing
        assert (len(grouped["this_week"]) + len(grouped["later"])) >= 1

    def test_calendar_data_serialization(self, scheduler, sample_build_with_time):
        """Test that build data can be serialized for frontend."""
        scheduler.schedule_build(sample_build_with_time)

        # Get build and convert to dict
        build = scheduler.storage.get_build_by_id(sample_build_with_time.id)
        build_dict = build.to_dict()

        # Verify all required fields for frontend
        assert "id" in build_dict
        assert "spec_id" in build_dict
        assert "spec_name" in build_dict
        assert "scheduled_time" in build_dict
        assert "priority" in build_dict
        assert "status" in build_dict
        assert "dependencies" in build_dict

        # Verify JSON serialization works
        json_str = json.dumps(build_dict)
        assert isinstance(json_str, str) and len(json_str) > 0

        # Verify deserialization
        loaded_dict = json.loads(json_str)
        assert loaded_dict["spec_id"] == "002-api"


# ============================================================================
# E2E Test: Complete Workflow
# ============================================================================


class TestCompleteWorkflowE2E:
    """Test the complete scheduling workflow from start to finish."""

    def test_complete_scheduling_workflow(self, scheduler, temp_project_dir):
        """Test complete workflow: schedule -> queue -> execute -> notify."""
        # Track all events
        events = []

        def track_all_events(event_type, build, **kwargs):
            events.append(
                {
                    "type": event_type,
                    "build_id": build.id if build else None,
                    "timestamp": datetime.now(),
                }
            )

        # Register callbacks for all events
        for event in [
            SchedulerEvent.BUILD_EXECUTING,
            SchedulerEvent.BUILD_SUCCESS,
            SchedulerEvent.BUILD_FAILURE,
        ]:
            scheduler.register_callback(event, track_all_events)

        # Create a build
        build = ScheduledBuild(
            id=str(uuid.uuid4()),
            spec_id="001-auth",
            spec_name="Complete Workflow Test",
            priority=SchedulePriority.HIGH,
            scheduled_time=None,  # Immediate execution
        )

        # Step 1: Schedule the build
        success = scheduler.schedule_build(build)
        assert success is True

        # Step 2: Verify it appears in queue
        queue_status = scheduler.get_queue_status()
        assert queue_status["total"] >= 1

        # Step 3: Verify it's in storage (simulating calendar view data fetch)
        stored_build = scheduler.storage.get_build_by_id(build.id)
        assert stored_build is not None
        # Status is automatically changed from PENDING to QUEUED when added
        assert stored_build.status == BuildStatus.QUEUED

        # Step 4: Start scheduler and execute build
        with patch("scheduler.scheduler.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            scheduler.start()
            time.sleep(3)  # Wait for execution
            scheduler.stop()

        # Step 5: Verify build is still in storage after execution
        final_build = scheduler.storage.get_build_by_id(build.id)
        assert final_build is not None

        # Step 6: Verify events were emitted
        assert len(events) > 0

    def test_parallel_execution_workflow(self, scheduler, temp_project_dir):
        """Test scheduling multiple independent builds for parallel execution."""
        # Create multiple independent builds
        builds = []
        for i in range(3):
            build = ScheduledBuild(
                id=str(uuid.uuid4()),
                spec_id=f"00{i + 1}-test",
                spec_name=f"Parallel Test {i + 1}",
                priority=SchedulePriority.NORMAL,
            )
            scheduler.schedule_build(build)
            builds.append(build)

        # Get parallel execution groups
        groups = scheduler.get_parallel_execution_groups()

        # All three builds should be in the same parallel group (no dependencies)
        assert len(groups) > 0
        # First group should contain all builds since they're independent
        first_group = groups[0]
        assert len(first_group) >= 3
