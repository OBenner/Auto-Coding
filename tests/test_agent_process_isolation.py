#!/usr/bin/env python3
"""
Tests for Agent Process Isolation
===================================

Tests for crash-resistant agent execution including:
- Process isolation functionality
- Crash scenarios and recovery
- Resource limit enforcement
- Agent subprocess execution
- RecoveryManager integration
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from agents.process_isolator import (
    AgentCrashError,
    AgentIsolationResult,
    AgentProcessError,
    AgentProcessIsolator,
    ResourceLimitExceeded,
    ResourceLimits,
)
from services.recovery import (
    FailureType,
    RecoveryAction,
    RecoveryManager,
)

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_spec_dir(temp_project_dir):
    """Create a temporary spec directory."""
    spec_dir = temp_project_dir / ".auto-claude" / "specs" / "test-spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    return spec_dir


@pytest.fixture
def dummy_agent_script(tmp_path):
    """Create a dummy agent script for testing."""
    script = tmp_path / "dummy_agent.py"
    script.write_text(
        """#!/usr/bin/env python3
import sys
import json

# Simple agent that outputs JSON
result = {
    "success": True,
    "output": {"response": "Test completed"},
    "error": None
}
print(json.dumps(result))
sys.exit(0)
"""
    )
    return script


@pytest.fixture
def crashing_agent_script(tmp_path):
    """Create an agent script that crashes."""
    script = tmp_path / "crashing_agent.py"
    script.write_text(
        """#!/usr/bin/env python3
import sys

# Simulate crash
sys.exit(1)
"""
    )
    return script


@pytest.fixture
def hanging_agent_script(tmp_path):
    """Create an agent script that hangs indefinitely."""
    script = tmp_path / "hanging_agent.py"
    script.write_text(
        """#!/usr/bin/env python3
import time

# Hang indefinitely
while True:
    time.sleep(1)
"""
    )
    return script


@pytest.fixture
def memory_hog_agent_script(tmp_path):
    """Create an agent script that consumes excessive memory."""
    script = tmp_path / "memory_hog.py"
    script.write_text(
        """#!/usr/bin/env python3
import sys
import json

# Simulate memory allocation (intentionally inefficient)
data = []
try:
    # Keep adding data until we hit a limit or crash
    for i in range(1000000):
        data.append("x" * 1000)
except MemoryError:
    pass

result = {
    "success": True,
    "output": {"items": len(data)},
    "error": None
}
print(json.dumps(result))
"""
    )
    return script


# =============================================================================
# RESOURCE LIMITS TESTS
# =============================================================================


class TestResourceLimits:
    """Tests for ResourceLimits dataclass."""

    def test_default_limits(self):
        """Default resource limits are reasonable."""
        limits = ResourceLimits()
        assert limits.max_memory_mb == 2048
        assert limits.max_cpu_percent == 80
        assert limits.max_execution_seconds == 3600
        assert limits.max_file_descriptors == 200
        assert limits.max_threads == 20

    def test_custom_limits(self):
        """Custom resource limits are accepted."""
        limits = ResourceLimits(
            max_memory_mb=1024,
            max_cpu_percent=60,
            max_execution_seconds=1800,
        )
        assert limits.max_memory_mb == 1024
        assert limits.max_cpu_percent == 60
        assert limits.max_execution_seconds == 1800

    def test_validation_rejects_invalid_memory(self):
        """Rejects non-positive memory limit."""
        with pytest.raises(ValueError, match="max_memory_mb must be positive"):
            ResourceLimits(max_memory_mb=0)

        with pytest.raises(ValueError, match="max_memory_mb must be positive"):
            ResourceLimits(max_memory_mb=-100)

    def test_validation_rejects_invalid_cpu(self):
        """Rejects invalid CPU percentage limits."""
        with pytest.raises(
            ValueError, match="max_cpu_percent must be between 1 and 100"
        ):
            ResourceLimits(max_cpu_percent=0)

        with pytest.raises(
            ValueError, match="max_cpu_percent must be between 1 and 100"
        ):
            ResourceLimits(max_cpu_percent=101)

        with pytest.raises(
            ValueError, match="max_cpu_percent must be between 1 and 100"
        ):
            ResourceLimits(max_cpu_percent=-50)

    def test_validation_rejects_invalid_execution_time(self):
        """Rejects non-positive execution time limit."""
        with pytest.raises(ValueError, match="max_execution_seconds must be positive"):
            ResourceLimits(max_execution_seconds=0)

        with pytest.raises(ValueError, match="max_execution_seconds must be positive"):
            ResourceLimits(max_execution_seconds=-10)

    def test_validation_rejects_invalid_file_descriptors(self):
        """Rejects non-positive file descriptor limit."""
        with pytest.raises(ValueError, match="max_file_descriptors must be positive"):
            ResourceLimits(max_file_descriptors=0)

    def test_validation_rejects_invalid_threads(self):
        """Rejects non-positive thread limit."""
        with pytest.raises(ValueError, match="max_threads must be positive"):
            ResourceLimits(max_threads=0)

    def test_to_dict(self):
        """Serializes to dictionary correctly."""
        limits = ResourceLimits(
            max_memory_mb=512, max_cpu_percent=50, max_execution_seconds=600
        )
        data = limits.to_dict()

        assert data["max_memory_mb"] == 512
        assert data["max_cpu_percent"] == 50
        assert data["max_execution_seconds"] == 600
        assert data["max_file_descriptors"] == 200
        assert data["max_threads"] == 20

    def test_from_dict(self):
        """Deserializes from dictionary correctly."""
        data = {
            "max_memory_mb": 1024,
            "max_cpu_percent": 70,
            "max_execution_seconds": 1200,
            "max_file_descriptors": 150,
            "max_threads": 15,
        }
        limits = ResourceLimits.from_dict(data)

        assert limits.max_memory_mb == 1024
        assert limits.max_cpu_percent == 70
        assert limits.max_execution_seconds == 1200
        assert limits.max_file_descriptors == 150
        assert limits.max_threads == 15

    def test_from_dict_uses_defaults(self):
        """Uses default values for missing keys."""
        data = {"max_memory_mb": 512}
        limits = ResourceLimits.from_dict(data)

        assert limits.max_memory_mb == 512
        assert limits.max_cpu_percent == 80  # default
        assert limits.max_execution_seconds == 3600  # default


# =============================================================================
# AGENT ISOLATION RESULT TESTS
# =============================================================================


class TestAgentIsolationResult:
    """Tests for AgentIsolationResult dataclass."""

    def test_default_values(self):
        """Default result indicates failure."""
        result = AgentIsolationResult(success=False)
        assert result.success is False
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.return_code == 0
        assert result.execution_time == 0.0
        assert result.error is None
        assert result.violated_limits == []
        assert result.crashed is False
        assert result.agent_output is None

    def test_success_result(self):
        """Success result with output."""
        result = AgentIsolationResult(
            success=True,
            stdout="test output",
            return_code=0,
            execution_time=1.5,
            agent_output={"response": "done"},
        )
        assert result.success is True
        assert result.stdout == "test output"
        assert result.execution_time == 1.5
        assert result.agent_output["response"] == "done"

    def test_failure_result_with_error(self):
        """Failure result includes error details."""
        result = AgentIsolationResult(
            success=False,
            stderr="error message",
            return_code=1,
            error="Agent failed",
        )
        assert result.success is False
        assert result.stderr == "error message"
        assert result.error == "Agent failed"

    def test_crash_result(self):
        """Crash result marked appropriately."""
        result = AgentIsolationResult(
            success=False,
            return_code=139,  # SIGSEGV
            crashed=True,
            error="Segmentation fault",
        )
        assert result.success is False
        assert result.crashed is True
        assert result.return_code == 139

    def test_resource_limit_violation(self):
        """Result tracks which limits were violated."""
        result = AgentIsolationResult(
            success=False,
            violated_limits=["max_memory_mb", "max_execution_seconds"],
            error="Resource limits exceeded",
        )
        assert "max_memory_mb" in result.violated_limits
        assert "max_execution_seconds" in result.violated_limits

    def test_to_dict(self):
        """Serializes to dictionary correctly."""
        result = AgentIsolationResult(
            success=True,
            stdout="output",
            stderr="errors",
            return_code=0,
            execution_time=2.5,
            error=None,
            violated_limits=[],
            crashed=False,
            agent_output={"data": "value"},
        )
        data = result.to_dict()

        assert data["success"] is True
        assert data["stdout"] == "output"
        assert data["execution_time"] == 2.5
        assert data["agent_output"]["data"] == "value"


# =============================================================================
# PROCESS ISOLATOR TESTS
# =============================================================================


class TestAgentProcessIsolator:
    """Tests for AgentProcessIsolator class."""

    def test_initialization(self, temp_project_dir):
        """Initializes with project directory and limits."""
        limits = ResourceLimits(max_memory_mb=512)
        isolator = AgentProcessIsolator(project_dir=temp_project_dir, limits=limits)

        assert isolator.project_dir == temp_project_dir.resolve()
        assert isolator.limits.max_memory_mb == 512
        assert isolator._process is None

    def test_initialization_with_default_limits(self, temp_project_dir):
        """Uses default resource limits when not provided."""
        isolator = AgentProcessIsolator(project_dir=temp_project_dir)

        assert isolator.limits.max_memory_mb == 2048
        assert isolator.limits.max_cpu_percent == 80

    def test_execute_agent_success(self, temp_project_dir, dummy_agent_script):
        """Executes agent successfully in isolated subprocess."""
        isolator = AgentProcessIsolator(project_dir=temp_project_dir)
        result = isolator.execute_agent(
            agent_script=str(dummy_agent_script),
        )

        assert result.success is True
        assert result.return_code == 0
        assert result.agent_output is not None
        assert result.agent_output["success"] is True
        assert result.execution_time > 0

    def test_execute_agent_crash(self, temp_project_dir, crashing_agent_script):
        """Handles agent crash gracefully."""
        isolator = AgentProcessIsolator(project_dir=temp_project_dir)
        result = isolator.execute_agent(
            agent_script=str(crashing_agent_script),
        )

        assert result.success is False
        assert result.return_code == 1
        assert result.crashed is False  # Exit code 1 is intentional, not crash

    def test_execute_agent_timeout(self, temp_project_dir, hanging_agent_script):
        """Terminates agent that exceeds execution time limit."""
        limits = ResourceLimits(max_execution_seconds=2)
        isolator = AgentProcessIsolator(project_dir=temp_project_dir, limits=limits)
        result = isolator.execute_agent(
            agent_script=str(hanging_agent_script),
        )

        assert result.success is False
        assert "max_execution_seconds" in result.violated_limits
        assert "timeout" in result.error.lower()

    def test_execute_agent_nonexistent_script(self, temp_project_dir):
        """Returns error for non-existent script."""
        isolator = AgentProcessIsolator(project_dir=temp_project_dir)
        result = isolator.execute_agent(agent_script="nonexistent.py")

        assert result.success is False
        assert "not found" in result.error
        assert result.return_code == -1

    def test_context_manager_cleanup(self, temp_project_dir):
        """Cleans up resources when used as context manager."""
        limits = ResourceLimits(max_memory_mb=256)

        with AgentProcessIsolator(
            project_dir=temp_project_dir, limits=limits
        ) as isolator:
            # Process should be None after execution
            assert isolator._process is None

        # After context exit, cleanup is complete
        assert True  # If we get here, cleanup didn't crash

    def test_terminate_graceful(self, temp_project_dir, hanging_agent_script):
        """Terminates running agent gracefully."""
        isolator = AgentProcessIsolator(
            project_dir=temp_project_dir,
            limits=ResourceLimits(max_execution_seconds=60),
        )

        # Start process in background
        import threading

        def run_agent():
            isolator.execute_agent(agent_script=str(hanging_agent_script))

        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

        # Give it time to start
        import time

        time.sleep(0.5)

        # Terminate should work
        isolator.terminate()
        assert True  # If we get here, terminate didn't hang

    def test_kill_forceful(self, temp_project_dir, hanging_agent_script):
        """Forcefully kills running agent."""
        isolator = AgentProcessIsolator(
            project_dir=temp_project_dir,
            limits=ResourceLimits(max_execution_seconds=60),
        )

        # Start process in background
        import threading

        def run_agent():
            isolator.execute_agent(agent_script=str(hanging_agent_script))

        thread = threading.Thread(target=run_agent, daemon=True)
        thread.start()

        # Give it time to start
        import time

        time.sleep(0.5)

        # Kill should work
        isolator.kill()
        assert True  # If we get here, kill didn't hang


# =============================================================================
# CRASH ISOLATION TESTS
# =============================================================================


class TestCrashIsolation:
    """Tests for crash isolation functionality."""

    def test_agent_crash_doesnt_affect_main(self, temp_project_dir):
        """Agent crash doesn't crash the main process."""
        # This test verifies the main process continues after agent crash
        crashing_script = temp_project_dir / "crash.py"
        crashing_script.write_text(
            """
import sys
import os
# Simulate crash
sys.exit(1)
"""
        )

        isolator = AgentProcessIsolator(project_dir=temp_project_dir)
        result = isolator.execute_agent(agent_script=str(crashing_script))

        # Main process should still be running
        assert result.success is False
        assert True  # If we reach here, main process survived

    def test_multiple_agents_can_fail_independently(self, temp_project_dir):
        """Multiple agents can fail without affecting each other."""
        crashing_script = temp_project_dir / "crash.py"
        crashing_script.write_text("import sys; sys.exit(1)")

        isolator = AgentProcessIsolator(project_dir=temp_project_dir)

        # Run multiple failing agents
        results = []
        for _ in range(3):
            result = isolator.execute_agent(agent_script=str(crashing_script))
            results.append(result)

        # All should fail independently
        assert all(r.success is False for r in results)
        assert len(results) == 3

    def test_exception_during_execution_is_caught(self, temp_project_dir):
        """Exceptions during execution are caught and reported."""
        isolator = AgentProcessIsolator(project_dir=temp_project_dir)

        # This should not raise an exception
        result = isolator.execute_agent(agent_script="nonexistent.py")

        assert result.success is False
        assert result.error is not None


# =============================================================================
# RECOVERY MANAGER TESTS
# =============================================================================


class TestRecoveryManager:
    """Tests for RecoveryManager class."""

    def test_initialization(self, temp_spec_dir, temp_project_dir):
        """Initializes with spec and project directories."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        assert manager.spec_dir == temp_spec_dir
        assert manager.project_dir == temp_project_dir
        assert manager.memory_dir.exists()

    def test_classify_broken_build(self, temp_spec_dir, temp_project_dir):
        """Classifies broken build errors correctly."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        error = "syntax error: invalid syntax"
        failure_type = manager.classify_failure(error, "subtask-1")

        assert failure_type == FailureType.BROKEN_BUILD

    def test_classify_verification_failure(self, temp_spec_dir, temp_project_dir):
        """Classifies verification failures correctly."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        error = "AssertionError: Expected 'OK' but got 'FAIL'"
        failure_type = manager.classify_failure(error, "subtask-1")

        assert failure_type == FailureType.VERIFICATION_FAILED

    def test_classify_context_exhausted(self, temp_spec_dir, temp_project_dir):
        """Classifies context exhaustion correctly."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        error = "Context length exceeded: maximum tokens reached"
        failure_type = manager.classify_failure(error, "subtask-1")

        assert failure_type == FailureType.CONTEXT_EXHAUSTED

    def test_classify_unknown_error(self, temp_spec_dir, temp_project_dir):
        """Classifies unknown errors correctly."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        error = "Unknown error occurred"
        failure_type = manager.classify_failure(error, "subtask-1")

        assert failure_type == FailureType.UNKNOWN

    def test_get_attempt_count_starts_at_zero(self, temp_spec_dir, temp_project_dir):
        """New subtask has zero attempts."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        count = manager.get_attempt_count("new-subtask")
        assert count == 0

    def test_record_attempt_increments_count(self, temp_spec_dir, temp_project_dir):
        """Recording attempts increments count."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        manager.record_attempt(
            subtask_id="subtask-1",
            session=1,
            success=False,
            approach="First attempt",
        )

        count = manager.get_attempt_count("subtask-1")
        assert count == 1

        # Record another attempt
        manager.record_attempt(
            subtask_id="subtask-1",
            session=1,
            success=False,
            approach="Second attempt",
        )

        count = manager.get_attempt_count("subtask-1")
        assert count == 2

    def test_is_circular_fix_detects_repetition(self, temp_spec_dir, temp_project_dir):
        """Detects circular fix attempts."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)
        subtask_id = "subtask-1"

        # Record similar attempts
        for i in range(3):
            manager.record_attempt(
                subtask_id=subtask_id,
                session=i + 1,
                success=False,
                approach="Try using async await pattern",
            )

        # Fourth attempt with similar approach should be detected as circular
        is_circular = manager.is_circular_fix(
            subtask_id, "Try using async await pattern again"
        )

        assert is_circular is True

    def test_is_circular_fix_allows_different_approaches(
        self, temp_spec_dir, temp_project_dir
    ):
        """Allows different approaches without circular detection."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)
        subtask_id = "subtask-1"

        # Record attempts with different approaches
        manager.record_attempt(
            subtask_id=subtask_id,
            session=1,
            success=False,
            approach="Use callbacks",
        )
        manager.record_attempt(
            subtask_id=subtask_id,
            session=2,
            success=False,
            approach="Use promises",
        )

        # Different approach should not be circular
        is_circular = manager.is_circular_fix(
            subtask_id, "Try using async await pattern"
        )

        assert is_circular is False

    def test_determine_recovery_action_for_broken_build(
        self, temp_spec_dir, temp_project_dir
    ):
        """Determines rollback action for broken build."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        # Record a good commit first
        manager.record_good_commit("abc123", "subtask-0")

        action = manager.determine_recovery_action(
            FailureType.BROKEN_BUILD, "subtask-1"
        )

        assert action.action == "rollback"
        assert action.target == "abc123"
        assert "broken" in action.reason.lower()

    def test_determine_recovery_action_for_verification_failure(
        self, temp_spec_dir, temp_project_dir
    ):
        """Determines retry action for verification failure."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        action = manager.determine_recovery_action(
            FailureType.VERIFICATION_FAILED, "subtask-1"
        )

        assert action.action == "retry"
        assert "retry with different approach" in action.reason.lower()

    def test_determine_recovery_action_for_circular_fix(
        self, temp_spec_dir, temp_project_dir
    ):
        """Determines skip action for circular fix."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        action = manager.determine_recovery_action(
            FailureType.CIRCULAR_FIX, "subtask-1"
        )

        assert action.action == "skip"
        assert "circular" in action.reason.lower()

    def test_record_good_commit(self, temp_spec_dir, temp_project_dir):
        """Records successful commits."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        manager.record_good_commit("abc123", "subtask-1")

        last_good = manager.get_last_good_commit()
        assert last_good == "abc123"

    def test_mark_subtask_stuck(self, temp_spec_dir, temp_project_dir):
        """Marks subtask as stuck."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        manager.mark_subtask_stuck("subtask-1", "Cannot fix this issue")

        stuck = manager.get_stuck_subtasks()
        assert len(stuck) == 1
        assert stuck[0]["subtask_id"] == "subtask-1"
        assert "Cannot fix this issue" in stuck[0]["reason"]

    def test_get_recovery_hints(self, temp_spec_dir, temp_project_dir):
        """Provides recovery hints based on history."""
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        # Record some attempts
        manager.record_attempt(
            subtask_id="subtask-1",
            session=1,
            success=False,
            approach="First attempt",
            error="Syntax error",
        )

        hints = manager.get_recovery_hints("subtask-1")

        assert len(hints) > 0
        assert any("Previous attempts" in h for h in hints)
        assert any("First attempt" in h for h in hints)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestProcessIsolationIntegration:
    """Integration tests for process isolation system."""

    def test_full_crash_and_recovery_cycle(self, temp_spec_dir, temp_project_dir):
        """Tests complete crash detection and recovery cycle."""
        # Create a manager
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        # Simulate a failure
        error = "AssertionError: Test failed"
        failure_type = manager.classify_failure(error, "subtask-1")

        # Get recovery action
        action = manager.determine_recovery_action(failure_type, "subtask-1")

        # Record the attempt
        manager.record_attempt(
            subtask_id="subtask-1",
            session=1,
            success=False,
            approach="Initial implementation",
            error=error,
        )

        # Verify recovery state
        assert action.action == "retry"
        assert manager.get_attempt_count("subtask-1") == 1

    def test_successful_execution_with_recovery_tracking(
        self, temp_spec_dir, temp_project_dir, dummy_agent_script
    ):
        """Tests successful execution with recovery tracking."""
        isolator = AgentProcessIsolator(project_dir=temp_project_dir)
        manager = RecoveryManager(spec_dir=temp_spec_dir, project_dir=temp_project_dir)

        # Execute agent successfully
        result = isolator.execute_agent(agent_script=str(dummy_agent_script))

        # Record success
        if result.success:
            manager.record_attempt(
                subtask_id="subtask-1",
                session=1,
                success=True,
                approach="Working approach",
            )
            # Record good commit
            manager.record_good_commit("abc123", "subtask-1")

        # Verify
        assert result.success is True
        assert manager.get_last_good_commit() == "abc123"
        assert manager.get_subtask_history("subtask-1")["status"] == "completed"


class TestAgentProcessExceptions:
    """Tests for custom exceptions."""

    def test_agent_process_error(self):
        """AgentProcessError can be raised and caught."""
        with pytest.raises(AgentProcessError, match="Test error"):
            raise AgentProcessError("Test error")

    def test_resource_limit_exceeded(self):
        """ResourceLimitExceeded can be raised and caught."""
        with pytest.raises(ResourceLimitExceeded, match="Memory limit"):
            raise ResourceLimitExceeded("Memory limit exceeded")

    def test_agent_crash_error(self):
        """AgentCrashError can be raised and caught."""
        with pytest.raises(AgentCrashError, match="Agent crashed"):
            raise AgentCrashError("Agent crashed unexpectedly")
