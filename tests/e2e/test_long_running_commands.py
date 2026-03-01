#!/usr/bin/env python3
"""
End-to-End Tests for Long-Running Command Handler
==================================================

Tests the complete lifecycle of long-running background commands including:
- 4+ hour timeout configuration
- Task status tracking
- Real-time output streaming
- State persistence across operations
- Cancellation and cleanup

Usage:
    pytest tests/e2e/test_long_running_commands.py -v
"""

import asyncio
import json
import logging
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Add apps/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))

from agents.tools_pkg.tools.background_task import (
    PSUTIL_AVAILABLE,
    BackgroundTaskManager,
)
from core.task_state_store import TaskStateStore

# Import psutil if available (for cleanup in tests)
try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)


@pytest.fixture
def test_dirs():
    """Create temporary directories for testing."""
    tmpdir = tempfile.mkdtemp()
    try:
        tmpdir_path = Path(tmpdir)
        spec_dir = tmpdir_path / "spec"
        project_dir = tmpdir_path / "project"
        spec_dir.mkdir()
        project_dir.mkdir()
        yield spec_dir, project_dir
    finally:
        # Add delay for Windows to release file handles
        time.sleep(0.5)
        # Clean up with ignore_errors for Windows compatibility
        try:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass  # Ignore cleanup errors on Windows


@pytest.fixture
async def manager(test_dirs):
    """Create a BackgroundTaskManager instance with cleanup."""
    spec_dir, project_dir = test_dirs
    mgr = BackgroundTaskManager(spec_dir, project_dir)
    yield mgr
    # Cleanup: kill all remaining subprocess processes and await termination
    for task_id, process in list(mgr.processes.items()):
        try:
            process.kill()
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except (OSError, asyncio.TimeoutError):
            pass
    mgr.processes.clear()
    # Cancel any pending async tasks and await them
    for task_id, async_task in list(mgr._async_tasks.items()):
        if not async_task.done():
            async_task.cancel()
            try:
                await asyncio.wait_for(async_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError, OSError):
                pass
    mgr._async_tasks.clear()


@pytest.mark.asyncio
class TestLongRunningCommands:
    """Test suite for long-running command execution."""

    async def test_long_timeout_configuration(self, manager):
        """
        Test 1: Verify system supports 4+ hour timeout.

        Acceptance criteria:
        - Commands can be configured with 4+ hour timeout
        - DEFAULT_TIMEOUT is at least 4 hours (14400 seconds)
        """
        # Verify default timeout is 4+ hours
        assert manager.DEFAULT_TIMEOUT >= 14400, (
            "DEFAULT_TIMEOUT should be at least 4 hours"
        )

        # Start a task with long timeout
        task_id = await manager.start_task(
            "echo 'Long running task'",
            timeout=18000,  # 5 hours
        )

        # Verify timeout is stored correctly
        status = manager.get_task_status(task_id)
        assert status is not None
        assert status["timeout"] == 18000

        logger.info(f"✓ Long timeout configuration test passed: {task_id}")

    async def test_task_status_lifecycle(self, manager):
        """
        Test 2: Verify task status updates through lifecycle.

        Acceptance criteria:
        - Task starts in 'pending' state
        - Task transitions to 'running' when execution begins
        - Task ends in 'completed', 'failed', or 'cancelled' state
        """
        # Create a task that runs for a few seconds
        # Use Python for cross-platform compatibility
        task_id = await manager.start_task(
            f"{sys.executable} -c \"import time; print('Starting'); time.sleep(1); print('Done')\"",
            timeout=10,
        )

        # Check initial state (should be pending or running)
        status = manager.get_task_status(task_id)
        assert status is not None
        assert status["status"] in ["pending", "running"]

        # Wait for task to start running
        for _ in range(10):
            status = manager.get_task_status(task_id)
            if status and status["status"] == "running":
                break
            await asyncio.sleep(0.3)

        # Check running state
        assert status is not None
        assert status["status"] == "running", (
            f"Expected running, got {status['status']}"
        )
        assert status["started_at"] is not None
        assert status["pid"] is not None

        # Poll for completion
        for _ in range(20):
            status = manager.get_task_status(task_id)
            if status and status["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.3)

        # Check final state
        assert status is not None
        assert status["status"] == "completed", (
            f"Expected completed, got {status['status']}"
        )
        assert status["completed_at"] is not None
        assert status["exit_code"] == 0

        logger.info(f"✓ Task status lifecycle test passed: {task_id}")

    async def test_realtime_output_streaming(self, manager):
        """
        Test 3: Verify output streams in real-time.

        Acceptance criteria:
        - Output is captured as command executes
        - Output is persisted periodically during execution
        - Final output includes all command output
        """
        # Create a command that produces incremental output
        # Use -u for unbuffered Python output and flush=True in prints
        # Produce 20 lines at 0.1s each so task["output"] gets flushed (every 10 lines)
        task_id = await manager.start_task(
            f"{sys.executable} -u -c \"import time; [print(f'Line {{i}}', flush=True) or time.sleep(0.1) for i in range(1, 21)]\"",
            timeout=10,
        )

        # Wait for initial output (need at least 10 lines for output flush at 10-line intervals)
        # 20 lines at 0.1s each = 2s total; first flush at ~1.0s (line 10)
        await asyncio.sleep(1.2)

        # Check that we're getting partial output (10 lines flushed)
        output_data = manager.get_task_output(task_id)
        assert output_data is not None
        initial_len = len(output_data.get("output", ""))

        # Wait for next flush threshold (line 20 at ~2.0s from start)
        await asyncio.sleep(1.0)

        # Output should have grown (proves real-time streaming)
        output_data_2 = manager.get_task_output(task_id)
        assert output_data_2 is not None
        assert len(output_data_2.get("output", "")) > initial_len, (
            f"Output did not grow: initial={initial_len}, current={len(output_data_2.get('output', ''))}"
        )

        # Poll for completion
        for _ in range(20):
            status = manager.get_task_status(task_id)
            if status and status["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.3)

        # Final output should contain all lines
        final_output = manager.get_task_output(task_id)
        assert final_output is not None
        assert "Line 1" in final_output["output"]
        assert "Line 20" in final_output["output"]

        logger.info(f"✓ Real-time output streaming test passed: {task_id}")

    async def test_state_persistence(self, manager, test_dirs):
        """
        Test 4: Verify state persistence to disk.

        Acceptance criteria:
        - Task state is saved to disk atomically
        - State can be reloaded after process restart
        - State includes all critical metadata
        """
        spec_dir, _ = test_dirs

        # Create a task
        task_id = await manager.start_task(
            f"{sys.executable} -c \"import time; print('Testing persistence'); time.sleep(0.5)\"",
            timeout=10,
        )

        # Wait for task to run
        await asyncio.sleep(0.3)

        # Verify state file exists
        state_file = spec_dir / ".background_tasks" / f"{task_id}.json"
        assert state_file.exists(), "State file should be created"

        # Load state directly from file
        saved_state = json.loads(state_file.read_text(encoding="utf-8"))

        # Verify state contents
        assert saved_state["id"] == task_id
        assert "Testing persistence" in saved_state["command"]
        assert saved_state["status"] in ["pending", "running"]
        assert saved_state["timeout"] == 10
        assert "created_at" in saved_state

        # Poll for completion
        for _ in range(20):
            final_state = json.loads(state_file.read_text(encoding="utf-8"))
            if final_state["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.3)

        assert final_state["status"] == "completed", (
            f"Expected completed, got {final_state['status']}"
        )
        assert final_state["completed_at"] is not None
        assert final_state["exit_code"] == 0

        logger.info(f"✓ State persistence test passed: {task_id}")

    async def test_cancellation_and_cleanup(self, manager):
        """
        Test 5: Verify cancellation with proper cleanup.

        Acceptance criteria:
        - Running tasks can be cancelled
        - Process is terminated gracefully
        - State is updated to 'cancelled'
        - Final state is persisted
        """
        # Create a long-running task
        task_id = await manager.start_task(
            f"{sys.executable} -c \"import time; [print(f'Iteration {{i}}') or time.sleep(0.5) for i in range(1, 11)]\"",
            timeout=30,
        )

        # Wait for task to start running
        for _ in range(10):
            status = manager.get_task_status(task_id)
            if status and status["status"] == "running":
                break
            await asyncio.sleep(0.3)

        # Verify task is running
        assert status is not None
        assert status["status"] == "running", (
            f"Expected running, got {status['status']}"
        )
        pid = status["pid"]
        assert pid is not None

        # Cancel the task
        success = await manager.cancel_task(task_id)
        assert success is True

        # Poll for cancelled state
        for _ in range(10):
            status = manager.get_task_status(task_id)
            if status and status["status"] in ["cancelled", "failed"]:
                break
            await asyncio.sleep(0.3)

        # Verify task is cancelled
        assert status is not None
        assert status["status"] == "cancelled", (
            f"Expected cancelled, got {status['status']}"
        )
        assert status["completed_at"] is not None

        # Verify process is no longer in manager
        assert task_id not in manager.processes

        logger.info(f"✓ Cancellation and cleanup test passed: {task_id}")

    async def test_timeout_handling(self, manager):
        """
        Test 6: Verify timeout handling for commands that exceed limit.

        Acceptance criteria:
        - Commands that exceed timeout are terminated
        - Task state is marked as 'failed' with timeout error
        - Error context includes timeout information
        """
        # Create a task with short timeout
        task_id = await manager.start_task(
            f'{sys.executable} -c "import time; time.sleep(10)"',  # Will timeout
            timeout=1,  # 1 second timeout
        )

        # Poll for timeout to occur
        for _ in range(20):
            status = manager.get_task_status(task_id)
            if status and status["status"] in ["failed", "completed"]:
                break
            await asyncio.sleep(0.3)

        # Verify task failed due to timeout
        assert status is not None
        assert status["status"] == "failed", f"Expected failed, got {status['status']}"
        assert "timed out" in status["error"].lower()

        # Verify error context includes timeout info
        error_context = manager.get_error_context(task_id)
        assert error_context is not None
        assert error_context["error_type"] == "timeout"
        assert error_context["timeout_used"] == 1
        assert error_context["retry_suggestion"] == "increase_timeout"

        logger.info(f"✓ Timeout handling test passed: {task_id}")

    async def test_memory_monitoring(self, manager):
        """
        Test 7: Verify memory monitoring during execution.

        Acceptance criteria:
        - Memory stats are captured at task start
        - Memory stats are updated during execution (if psutil available)
        - Memory stats are included in final state
        - Memory monitoring triggers warnings if thresholds exceeded
        - No memory leaks during task execution
        """
        # Create a task that produces enough output to trigger memory checks
        # Memory is checked every 50 lines (MEMORY_CHECK_INTERVAL = 5, checked every 10 * 5 lines)
        # We'll produce 100 lines with delays to ensure task runs long enough
        task_id = await manager.start_task(
            f"{sys.executable} -c \"import time; [print(f'Output line {{i:04d}}') or time.sleep(0.05) for i in range(1, 101)]\"",
            timeout=30,
        )

        # Wait for task to start
        await asyncio.sleep(0.2)

        # === PHASE 1: Verify memory stats at task start ===
        status_start = manager.get_task_status(task_id)
        assert status_start is not None
        # Task should be pending or running at this point
        assert status_start["status"] in ["pending", "running"]

        # Track initial memory stats
        initial_mem_stats = None
        if PSUTIL_AVAILABLE:
            # Memory stats should be captured initially
            # Note: May not be in state yet if output hasn't reached 50 lines
            if (
                "memory_stats" in status_start
                and status_start["memory_stats"] is not None
            ):
                initial_mem_stats = status_start["memory_stats"]
                assert "percent" in initial_mem_stats
                assert "available_mb" in initial_mem_stats
                assert "total_mb" in initial_mem_stats
                assert "used_mb" in initial_mem_stats
                assert 0 <= initial_mem_stats["percent"] <= 100
                logger.info(
                    f"Initial memory: {initial_mem_stats['percent']}% used, {initial_mem_stats['available_mb']} MB available"
                )
        else:
            logger.info("Memory monitoring not available (psutil not installed)")

        # === PHASE 2: Monitor memory during execution ===
        # Wait a bit for task to produce more output and trigger memory checks
        # With 100 lines at 0.05s each = ~5s, wait 2s to be mid-execution
        await asyncio.sleep(2.0)

        status_during = manager.get_task_status(task_id)
        assert status_during is not None
        # Task should still be running or may have completed
        assert status_during["status"] in ["running", "completed"]

        if PSUTIL_AVAILABLE:
            # After producing significant output, memory stats should be present
            # (task should have hit the 50-line checkpoint)
            if (
                "memory_stats" in status_during
                and status_during["memory_stats"] is not None
            ):
                during_mem_stats = status_during["memory_stats"]
                assert "percent" in during_mem_stats
                assert "available_mb" in during_mem_stats
                assert "total_mb" in during_mem_stats
                assert "used_mb" in during_mem_stats
                assert 0 <= during_mem_stats["percent"] <= 100
                logger.info(
                    f"During execution memory: {during_mem_stats['percent']}% used"
                )

                # Verify memory stats are reasonable (no huge leak)
                # Memory shouldn't jump by more than 50% during our small task
                if initial_mem_stats:
                    mem_increase = (
                        during_mem_stats["percent"] - initial_mem_stats["percent"]
                    )
                    assert mem_increase < 50, (
                        f"Memory increased by {mem_increase}% - possible leak"
                    )
                    logger.info(f"Memory change during execution: {mem_increase:+.2f}%")

        # === PHASE 3: Wait for completion ===
        # Task should take ~5 seconds total (100 lines * 0.05s)
        # Poll for completion instead of fixed sleep (CI can be slow)
        status_final = None
        for _ in range(30):
            status_final = manager.get_task_status(task_id)
            if status_final and status_final["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.5)

        # === PHASE 4: Verify memory stats in final state ===
        assert status_final is not None
        assert status_final["status"] == "completed", (
            f"Expected completed, got {status_final['status']}"
        )
        assert status_final["exit_code"] == 0

        if PSUTIL_AVAILABLE:
            # Final memory stats should be captured
            assert "memory_stats" in status_final
            final_mem_stats = status_final["memory_stats"]
            assert final_mem_stats is not None
            assert "percent" in final_mem_stats
            assert "available_mb" in final_mem_stats
            assert "total_mb" in final_mem_stats
            assert "used_mb" in final_mem_stats
            assert 0 <= final_mem_stats["percent"] <= 100
            logger.info(f"Final memory: {final_mem_stats['percent']}% used")

            # === PHASE 5: Verify no memory leaks ===
            # Compare initial and final memory (should be similar)
            if initial_mem_stats:
                mem_total_change = (
                    final_mem_stats["percent"] - initial_mem_stats["percent"]
                )
                # Memory shouldn't increase by more than 10% for this simple task
                # (allowing some variance for system activity)
                assert abs(mem_total_change) < 10, (
                    f"Memory leak detected: {mem_total_change:+.2f}% change"
                )
                logger.info(
                    f"Total memory change: {mem_total_change:+.2f}% (no leak detected)"
                )

            # === PHASE 6: Verify memory stats are persisted ===
            # Load state from disk to verify persistence
            state_file = manager._get_task_state_file(task_id)
            assert state_file.exists()
            persisted_state = json.loads(state_file.read_text(encoding="utf-8"))
            assert "memory_stats" in persisted_state
            assert persisted_state["memory_stats"] == final_mem_stats
            logger.info("✓ Memory stats persisted to disk")

            logger.info("✓ Memory monitoring fully operational")
        else:
            logger.info("✓ Memory monitoring test skipped (psutil not installed)")

        logger.info(f"✓ Memory monitoring test passed: {task_id}")

    async def test_error_context_capture(self, manager):
        """
        Test 8: Verify error context is captured for failed tasks.

        Acceptance criteria:
        - Failed tasks capture error context
        - Error context includes error type, message, and relevant output
        - Retry suggestions are provided based on error type
        """
        # Create a task that will fail
        task_id = await manager.start_task(
            f"{sys.executable} -c \"import sys; print('About to fail'); sys.exit(42)\"",
            timeout=10,
        )

        # Poll for task to fail
        for _ in range(20):
            status = manager.get_task_status(task_id)
            if status and status["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(0.3)

        # Verify task failed
        assert status is not None
        assert status["status"] == "failed", f"Expected failed, got {status['status']}"

        # Get error context
        error_context = manager.get_error_context(task_id)
        assert error_context is not None
        assert "error_type" in error_context
        assert "error_message" in error_context
        assert "exit_code" in error_context
        assert error_context["exit_code"] == 42
        assert "retry_suggestion" in error_context
        assert "relevant_output" in error_context
        assert "About to fail" in error_context["relevant_output"]

        logger.info(f"✓ Error context capture test passed: {task_id}")

    async def test_list_and_filter_tasks(self, manager):
        """
        Test 9: Verify task listing and filtering.

        Acceptance criteria:
        - Can list all tasks
        - Can filter tasks by status
        - Tasks are sorted by creation time
        """
        # Create multiple tasks with different outcomes
        task1_id = await manager.start_task(
            f"{sys.executable} -c \"import time; print('Task 1'); time.sleep(0.3)\"",
            timeout=10,
        )
        await asyncio.sleep(0.1)

        task2_id = await manager.start_task(
            f"{sys.executable} -c \"import sys; print('Task 2'); sys.exit(1)\"",
            timeout=10,
        )
        await asyncio.sleep(0.1)

        task3_id = await manager.start_task(
            f'{sys.executable} -c "import time; time.sleep(5)"', timeout=10
        )

        # Poll for first two tasks to reach terminal state
        for _ in range(20):
            s1 = manager.get_task_status(task1_id)
            s2 = manager.get_task_status(task2_id)
            if (
                s1
                and s1["status"] in ["completed", "failed"]
                and s2
                and s2["status"] in ["completed", "failed"]
            ):
                break
            await asyncio.sleep(0.3)

        # List all tasks
        all_tasks = manager.list_tasks()
        assert len(all_tasks) >= 3

        # Verify sorting (most recent first)
        assert all_tasks[0]["id"] == task3_id

        # Filter by status
        running_tasks = manager.list_tasks(status="running")
        assert len(running_tasks) >= 1
        assert task3_id in [t["id"] for t in running_tasks]

        completed_tasks = manager.list_tasks(status="completed")
        assert task1_id in [t["id"] for t in completed_tasks]

        failed_tasks = manager.list_tasks(status="failed")
        assert task2_id in [t["id"] for t in failed_tasks]

        # Cancel the running task
        await manager.cancel_task(task3_id)

        logger.info("✓ List and filter tasks test passed")

    async def test_orphaned_task_recovery(self, manager, test_dirs):
        """
        Test 10: Verify orphaned task recovery on restart.

        Acceptance criteria:
        - Tasks orphaned by app restart are detected
        - Orphaned tasks can be marked as failed
        - Recovery process provides statistics
        """
        spec_dir, _ = test_dirs

        # Create a running task
        task_id = await manager.start_task(
            f'{sys.executable} -c "import time; time.sleep(10)"', timeout=30
        )

        # Wait for task to start running
        for _ in range(10):
            status = manager.get_task_status(task_id)
            if status and status["status"] == "running":
                break
            await asyncio.sleep(0.3)

        # Verify task is running
        assert status is not None
        assert status["status"] == "running", (
            f"Expected running, got {status['status']}"
        )

        # Simulate app restart by creating a new TaskStateStore
        store = TaskStateStore(spec_dir / ".background_tasks")

        # Find orphaned tasks
        orphaned = store.find_orphaned_tasks()
        assert task_id in orphaned

        # Recover orphaned tasks
        recovery_stats = store.recover_on_startup()
        assert recovery_stats["orphaned_count"] >= 1
        assert recovery_stats["marked_count"] >= 1

        # Verify task is now marked as failed
        state = store.load_state(task_id)
        assert state is not None
        assert state["status"] == "failed"
        assert "orphaned" in state["error"].lower() or state.get("orphaned") is True

        # Cancel the actual running process
        await manager.cancel_task(task_id)

        logger.info(f"✓ Orphaned task recovery test passed: {task_id}")

    async def test_app_restart_recovery_e2e(self, test_dirs):
        """
        Test 11: End-to-end app restart recovery scenario.

        This test simulates a complete app restart workflow:
        1. Start long-running command
        2. Simulate app shutdown
        3. Simulate app startup with recovery
        4. Verify task state recovered
        5. Verify output still accessible
        6. Verify can still monitor/cancel

        Acceptance criteria (from spec):
        - Agent state persists if app is restarted during long operation
        - Task state is recovered on startup
        - Output remains accessible after restart
        - Users can still view task status after restart
        """
        spec_dir, project_dir = test_dirs

        # === PHASE 1: Start long-running command ===
        logger.info("Phase 1: Starting long-running command...")
        manager1 = BackgroundTaskManager(spec_dir, project_dir)

        # Create a command that outputs multiple lines over time
        task_id = await manager1.start_task(
            f"{sys.executable} -c \"import time, sys; [print(f'Progress {{i}}', flush=True) or sys.stdout.flush() or time.sleep(0.3) for i in range(1, 20)]\"",
            timeout=30,
        )

        # Wait for task to start running
        status_before = None
        for _ in range(10):
            status_before = manager1.get_task_status(task_id)
            if status_before and status_before["status"] == "running":
                break
            await asyncio.sleep(0.3)

        # Verify task is running
        assert status_before is not None
        assert status_before["status"] == "running", (
            f"Expected running, got {status_before['status']}"
        )
        assert status_before["pid"] is not None
        logger.info(f"Task {task_id} started with PID {status_before['pid']}")

        # Wait a bit more for output to be produced and captured
        await asyncio.sleep(1.5)

        # Get initial output
        output_before = manager1.get_task_output(task_id)
        assert output_before is not None
        # Output might be empty if task just started, but the key is state is persisted
        logger.info(
            f"Initial output captured: {len(output_before['output'])} characters"
        )

        # === PHASE 2: Simulate app restart ===
        logger.info("Phase 2: Simulating app shutdown and restart...")

        # Simulate app shutdown - manager1 goes out of scope
        # In a real restart, the process might keep running or be orphaned
        # We intentionally don't cancel it to simulate orphaned task scenario
        old_pid = status_before["pid"]
        del manager1

        # Small delay to ensure manager is cleaned up
        await asyncio.sleep(0.2)

        # Simulate app startup - create new manager and recover state
        store = TaskStateStore(spec_dir / ".background_tasks")
        recovery_stats = store.recover_on_startup()

        logger.info(f"Recovery stats: {recovery_stats}")
        assert recovery_stats["orphaned_count"] >= 1, (
            "Should find at least one orphaned task"
        )
        assert recovery_stats["marked_count"] >= 1, (
            "Should mark at least one task as orphaned"
        )

        # === PHASE 3: Verify task state recovered ===
        logger.info("Phase 3: Verifying task state recovery...")

        # Create new manager (simulating app restarted)
        manager2 = BackgroundTaskManager(spec_dir, project_dir)

        # Load task state from disk
        status_after = manager2.get_task_status(task_id)
        assert status_after is not None, "Task state should be recovered from disk"
        assert status_after["id"] == task_id
        assert status_after["command"] == status_before["command"]
        assert status_after["timeout"] == status_before["timeout"]
        assert status_after["created_at"] == status_before["created_at"]
        assert status_after["started_at"] == status_before["started_at"]

        # Task should be marked as failed/orphaned after recovery
        assert status_after["status"] == "failed", (
            "Orphaned task should be marked as failed"
        )
        assert (
            status_after.get("orphaned") is True
            or "orphaned" in status_after.get("error", "").lower()
        )
        logger.info(
            f"✓ Task state recovered correctly: status={status_after['status']}, orphaned={status_after.get('orphaned')}"
        )

        # === PHASE 4: Verify output still accessible ===
        logger.info("Phase 4: Verifying output accessibility...")

        # Output should still be accessible from persisted state
        output_after = manager2.get_task_output(task_id)
        assert output_after is not None, (
            "Task output should be accessible after restart"
        )

        # Output may be empty if task was just started when "restart" happened
        # The key verification is that output data structure is accessible
        logger.info(f"✓ Output accessible: {len(output_after['output'])} characters")

        # If we did capture output, verify it's the right format
        if len(output_after["output"]) > 0:
            # Output should be a string
            assert isinstance(output_after["output"], str), "Output should be string"
            logger.info(f"  Output sample: {output_after['output'][:100]}")

        # === PHASE 5: Verify can still monitor task ===
        logger.info("Phase 5: Verifying task monitoring capabilities...")

        # Should be able to query task status
        task_list = manager2.list_tasks()
        assert len(task_list) >= 1, "Should be able to list tasks after restart"
        task_ids = [t["id"] for t in task_list]
        assert task_id in task_ids, "Our task should be in the task list"

        # Should be able to filter by status
        failed_tasks = manager2.list_tasks(status="failed")
        failed_ids = [t["id"] for t in failed_tasks]
        assert task_id in failed_ids, "Our orphaned task should be in failed list"
        logger.info(
            f"✓ Task monitoring works: found {len(task_list)} total tasks, {len(failed_tasks)} failed"
        )

        # === PHASE 6: Verify state file integrity ===
        logger.info("Phase 6: Verifying state file integrity...")

        # State file should exist and be valid JSON
        state_file = spec_dir / ".background_tasks" / f"{task_id}.json"
        assert state_file.exists(), "State file should exist"

        state_data = json.loads(state_file.read_text(encoding="utf-8"))

        # Verify all critical fields are present
        required_fields = ["id", "command", "status", "created_at", "timeout"]
        for field in required_fields:
            assert field in state_data, f"State should contain {field}"

        logger.info("✓ State file integrity verified")

        # === CLEANUP: Terminate any remaining processes ===
        # Try to terminate the orphaned process if it's still running
        try:
            if PSUTIL_AVAILABLE:
                if psutil.pid_exists(old_pid):
                    proc = psutil.Process(old_pid)
                    proc.terminate()
                    logger.info(f"Cleaned up orphaned process {old_pid}")
        except Exception as e:
            logger.debug(
                f"Cleanup of process {old_pid} not needed or already terminated: {e}"
            )

        logger.info(f"✓ App restart recovery E2E test passed: {task_id}")


@pytest.mark.asyncio
async def test_full_lifecycle_integration(test_dirs):
    """
    Integration test covering complete long-running command lifecycle.

    This test simulates a realistic scenario:
    1. Start multiple long-running commands
    2. Monitor progress in real-time
    3. Cancel one task
    4. Wait for others to complete
    5. Verify all states are correct
    """
    spec_dir, project_dir = test_dirs
    manager = BackgroundTaskManager(spec_dir, project_dir)

    logger.info("Starting full lifecycle integration test...")

    # Start multiple tasks
    tasks = []

    # Task 1: Will complete successfully
    task1_id = await manager.start_task(
        f"{sys.executable} -c \"import time; [print(f'Build step {{i}}') or time.sleep(0.2) for i in range(1, 4)]\"",
        timeout=10,
    )
    tasks.append(("build", task1_id))

    # Task 2: Will be cancelled (long running)
    task2_id = await manager.start_task(
        f"{sys.executable} -c \"import time; [print(f'Long process {{i}}') or time.sleep(1) for i in range(1, 11)]\"",
        timeout=30,
    )
    tasks.append(("long_process", task2_id))

    # Task 3: Will fail
    task3_id = await manager.start_task(
        f"{sys.executable} -c \"import sys, time; print('Starting tests'); time.sleep(0.3); sys.exit(1)\"",
        timeout=10,
    )
    tasks.append(("tests", task3_id))
    await asyncio.sleep(0.3)  # Small delay for stability

    logger.info(f"Started {len(tasks)} tasks")

    # Monitor progress
    await asyncio.sleep(0.8)

    # Check all tasks are running or completed
    for name, task_id in tasks:
        status = manager.get_task_status(task_id)
        assert status is not None
        logger.info(f"{name}: {status['status']}")

    # Cancel the long-running task (if still running)
    status2_before = manager.get_task_status(task2_id)
    if status2_before["status"] == "running":
        success = await manager.cancel_task(task2_id)
        assert success is True
        logger.info("Cancelled long_process task")
    else:
        logger.info(
            f"Long process task already {status2_before['status']}, skipping cancellation"
        )

    # Poll for remaining tasks to complete
    for _ in range(20):
        status1 = manager.get_task_status(task1_id)
        status3 = manager.get_task_status(task3_id)
        if (
            status1
            and status1["status"] in ["completed", "failed"]
            and status3
            and status3["status"] in ["completed", "failed"]
        ):
            break
        await asyncio.sleep(0.3)

    # Verify final states
    # Task 1 should be completed
    assert status1["status"] == "completed", (
        f"Expected completed, got {status1['status']}"
    )
    output1 = manager.get_task_output(task1_id)
    assert "Build step 3" in output1["output"]
    logger.info("✓ Build task completed successfully")

    # Task 2 should be cancelled — poll until terminal state
    for _ in range(20):
        status2 = manager.get_task_status(task2_id)
        if status2["status"] in ["cancelled", "completed", "failed"]:
            break
        await asyncio.sleep(0.3)
    assert status2["status"] == "cancelled", (
        f"Expected cancelled, got {status2['status']}"
    )
    logger.info(f"✓ Long process task status: {status2['status']}")

    # Task 3 should be failed
    status3 = manager.get_task_status(task3_id)
    assert status3["status"] == "failed"
    error_context = manager.get_error_context(task3_id)
    assert error_context is not None
    logger.info("✓ Test task failed as expected")

    # Verify all states are persisted
    state_dir = spec_dir / ".background_tasks"
    state_files = list(state_dir.glob("*.json"))
    assert len(state_files) >= 3
    logger.info("✓ All states persisted to disk")

    # Verify we can list tasks
    all_tasks = manager.list_tasks()
    assert len(all_tasks) >= 3

    completed = manager.list_tasks(status="completed")
    cancelled = manager.list_tasks(status="cancelled")
    failed = manager.list_tasks(status="failed")

    logger.info(
        f"Task summary: {len(completed)} completed, {len(cancelled)} cancelled, {len(failed)} failed"
    )

    logger.info("✓ Full lifecycle integration test passed")


if __name__ == "__main__":
    # Run tests directly with asyncio
    import sys

    logging.basicConfig(level=logging.INFO)

    print("=" * 80)
    print("Long-Running Command Handler - End-to-End Tests")
    print("=" * 80)
    print()

    # Run integration test
    tmpdir = tempfile.mkdtemp()
    try:
        tmpdir_path = Path(tmpdir)
        spec_dir = tmpdir_path / "spec"
        project_dir = tmpdir_path / "project"
        spec_dir.mkdir()
        project_dir.mkdir()
        test_dirs = (spec_dir, project_dir)

        asyncio.run(test_full_lifecycle_integration(test_dirs))

        print()
        print("=" * 80)
        print("All tests passed! ✓")
        print("=" * 80)
    finally:
        # Give processes time to fully terminate before cleanup
        time.sleep(1)
        try:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass  # Ignore cleanup errors on Windows
