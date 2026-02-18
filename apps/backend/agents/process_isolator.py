"""
Agent Process Isolation
========================

Provides crash-resistant agent execution with resource limits and process isolation.

This module implements agent sandboxing to prevent agent crashes from affecting
the main application. Agents are executed in isolated subprocesses with controlled
resource usage and automatic crash recovery.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)

# Import debug utilities via shared helper
from agents.debug_helpers import create_debug_helpers

_debug, _debug_error, _debug_success, _debug_verbose, _debug_warning = (
    create_debug_helpers("agents.process_isolator")
)


@dataclass
class ResourceLimits:
    """
    Resource limits for agent execution.

    These limits prevent agents from consuming excessive system resources
    and ensure overall system stability.

    Attributes:
        max_memory_mb: Maximum memory usage in megabytes (default: 2048MB for agents)
        max_cpu_percent: Maximum CPU usage percentage (default: 80%)
        max_execution_seconds: Maximum execution time in seconds (default: 3600s = 1 hour)
        max_file_descriptors: Maximum number of open file descriptors (default: 200)
        max_threads: Maximum number of threads (default: 20)
    """

    max_memory_mb: int = 2048
    max_cpu_percent: int = 80
    max_execution_seconds: int = 3600
    max_file_descriptors: int = 200
    max_threads: int = 20

    def __post_init__(self):
        """Validate resource limits."""
        if self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        if not 0 < self.max_cpu_percent <= 100:
            raise ValueError("max_cpu_percent must be between 1 and 100")
        if self.max_execution_seconds <= 0:
            raise ValueError("max_execution_seconds must be positive")
        if self.max_file_descriptors <= 0:
            raise ValueError("max_file_descriptors must be positive")
        if self.max_threads <= 0:
            raise ValueError("max_threads must be positive")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_percent": self.max_cpu_percent,
            "max_execution_seconds": self.max_execution_seconds,
            "max_file_descriptors": self.max_file_descriptors,
            "max_threads": self.max_threads,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ResourceLimits:
        """Create from dictionary."""
        return cls(
            max_memory_mb=data.get("max_memory_mb", 2048),
            max_cpu_percent=data.get("max_cpu_percent", 80),
            max_execution_seconds=data.get("max_execution_seconds", 3600),
            max_file_descriptors=data.get("max_file_descriptors", 200),
            max_threads=data.get("max_threads", 20),
        )


class AgentProcessError(Exception):
    """Raised when agent process encounters an error."""

    pass


class ResourceLimitExceeded(AgentProcessError):
    """Raised when agent exceeds resource limits."""

    pass


class AgentCrashError(AgentProcessError):
    """Raised when agent process crashes unexpectedly."""

    pass


@dataclass
class AgentIsolationResult:
    """
    Result of isolated agent execution.

    Attributes:
        success: Whether execution completed successfully
        stdout: Standard output from agent
        stderr: Standard error from agent
        return_code: Process exit code
        execution_time: Actual execution time in seconds
        error: Error message if execution failed
        violated_limits: List of resource limits that were exceeded
        crashed: Whether the agent process crashed
        agent_output: Parsed JSON output from agent (if available)
    """

    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    execution_time: float = 0.0
    error: str | None = None
    violated_limits: list[str] = field(default_factory=list)
    crashed: bool = False
    agent_output: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "execution_time": self.execution_time,
            "error": self.error,
            "violated_limits": self.violated_limits,
            "crashed": self.crashed,
            "agent_output": self.agent_output,
        }


class AgentProcessIsolator:
    """
    Isolator for crash-resistant agent execution.

    Executes agents in isolated subprocesses with:
    - Resource limits (CPU, memory, time)
    - Crash isolation (agent crash doesn't affect main app)
    - Monitored execution
    - Automatic recovery support

    Example:
        >>> from agents.process_isolator import AgentProcessIsolator, ResourceLimits
        >>> limits = ResourceLimits(max_memory_mb=1024, max_execution_seconds=600)
        >>> isolator = AgentProcessIsolator(
        ...     project_dir=Path("/path/to/project"),
        ...     limits=limits
        ... )
        >>> result = isolator.execute_agent(
        ...     agent_type="coder",
        ...     agent_args={"spec_dir": "/path/to/spec"}
        ... )
        >>> if result.success:
        ...     print(f"Agent completed: {result.agent_output}")
        ... else:
        ...     print(f"Agent failed: {result.error}")
    """

    def __init__(
        self,
        project_dir: Path,
        limits: ResourceLimits | None = None,
    ):
        """
        Initialize agent process isolator.

        Args:
            project_dir: Root directory of the project
            limits: Resource limits for agent execution
        """
        self.project_dir = Path(project_dir).resolve()
        self.limits = limits or ResourceLimits()
        self._process: subprocess.Popen | None = None
        self._start_time: float = 0.0
        self._peak_memory_mb: float = 0.0
        self._violated_limits: list[str] = []

        logger.debug(f"Initialized agent isolator for project: {self.project_dir}")
        _debug_verbose(f"Resource limits: {self.limits.to_dict()}")

    def _create_agent_env(self) -> dict[str, str]:
        """
        Create environment for agent execution.

        Returns:
            Environment variables dict with inherited environment
        """
        # Inherit full environment for agent execution
        env = os.environ.copy()

        # Add agent-specific environment variables
        env.update(
            {
                "PYTHONUNBUFFERED": "1",  # Real-time output
                # Resource hints (informational)
                "AUTO_CLAUDE_AGENT_MAX_MEMORY_MB": str(self.limits.max_memory_mb),
                "AUTO_CLAUDE_AGENT_MAX_CPU_PERCENT": str(self.limits.max_cpu_percent),
                "AUTO_CLAUDE_AGENT_MAX_EXECUTION_SECONDS": str(
                    self.limits.max_execution_seconds
                ),
                # Signal that we're in isolated mode
                "AUTO_CLAUDE_AGENT_ISOLATED": "1",
            }
        )

        return env

    def execute_agent(
        self,
        agent_script: str,
        agent_args: list[str] | None = None,
        working_dir: Path | None = None,
    ) -> AgentIsolationResult:
        """
        Execute an agent in isolated subprocess.

        Args:
            agent_script: Path to agent subprocess script (e.g., "agents/agent_subprocess.py")
            agent_args: Command-line arguments to pass to agent
            working_dir: Working directory for execution (defaults to project_dir)

        Returns:
            AgentIsolationResult with execution outcome
        """
        script_path = Path(agent_script).resolve()

        if not script_path.exists():
            return AgentIsolationResult(
                success=False,
                error=f"Agent script not found: {agent_script}",
                return_code=-1,
            )

        # Default to project directory
        if working_dir:
            working_dir = Path(working_dir).resolve()
        else:
            working_dir = self.project_dir

        # Build command
        cmd = [sys.executable, str(script_path)]
        if agent_args:
            cmd.extend(agent_args)

        _debug(f"Executing agent in isolated process: {script_path.name}")
        _debug_verbose(f"Command: {' '.join(cmd)}")
        _debug_verbose(f"Working dir: {working_dir}")

        return self._execute_subprocess(cmd, working_dir)

    def _handle_completed_process(
        self,
        result: AgentIsolationResult,
        stdout: str,
        stderr: str,
    ) -> None:
        """Populate result from a completed (non-timed-out) process."""
        result.stdout = stdout
        result.stderr = stderr
        result.return_code = self._process.returncode
        result.execution_time = time.time() - self._start_time
        result.success = self._process.returncode == 0

        # Try to parse JSON output from stdout
        if result.success and stdout.strip():
            try:
                result.agent_output = json.loads(stdout.strip())
            except json.JSONDecodeError:
                _debug_verbose("Agent output is not JSON, treating as plain text")

        # Check for crash indicators
        if result.return_code != 0 and result.return_code not in [-1, 1]:
            result.crashed = True
            _debug_error(f"Agent process crashed with code {result.return_code}")

        if result.success:
            _debug_success(
                f"Agent executed successfully in {result.execution_time:.2f}s "
                f"(peak memory: {self._peak_memory_mb:.0f}MB)"
            )
        else:
            _debug_warning(
                f"Agent exited with code {result.return_code}: {stderr[:200]}"
            )

    def _handle_timeout(self, result: AgentIsolationResult) -> None:
        """Handle a timed-out subprocess."""
        self._process.kill()
        stdout, stderr = self._process.communicate(timeout=5)
        result.stdout = stdout or ""
        result.stderr = stderr or ""
        result.return_code = self._process.returncode or -1
        result.error = (
            f"Execution timeout ({self.limits.max_execution_seconds}s exceeded)"
        )
        result.violated_limits.append("max_execution_seconds")
        result.crashed = True
        result.execution_time = time.time() - self._start_time
        _debug_error(f"Agent execution timeout: {result.error}")

    def _execute_subprocess(
        self,
        cmd: list[str],
        working_dir: Path,
    ) -> AgentIsolationResult:
        """
        Execute command in isolated subprocess with monitoring.

        Args:
            cmd: Command to execute
            working_dir: Working directory

        Returns:
            AgentIsolationResult with execution outcome
        """
        env = self._create_agent_env()
        result = AgentIsolationResult(success=False)
        self._start_time = time.time()
        self._peak_memory_mb = 0.0
        self._violated_limits = []

        try:
            # Start process
            self._process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            _debug(f"Agent process started with PID: {self._process.pid}")

            # Monitor execution with timeout
            monitor_thread = threading.Thread(
                target=self._monitor_resources, daemon=True
            )
            monitor_thread.start()

            # Wait for completion with timeout
            try:
                stdout, stderr = self._process.communicate(
                    timeout=self.limits.max_execution_seconds
                )
                self._handle_completed_process(result, stdout, stderr)
            except subprocess.TimeoutExpired:
                self._handle_timeout(result)

            # Collect violated limits recorded by the monitor thread
            result.violated_limits.extend(self._violated_limits)

        except Exception as e:
            result.error = f"Agent execution failed: {str(e)}"
            result.crashed = True
            _debug_error(f"Agent execution error: {result.error}")
            if self._process:
                try:
                    self._process.kill()
                except OSError:
                    pass  # Process already exited

        finally:
            self._process = None

        return result

    def _monitor_resources(self) -> None:
        """
        Monitor agent resource usage during execution.

        This runs in a separate thread and checks CPU/memory usage.
        If limits are exceeded, the process is terminated.

        Note: Resource monitoring is best-effort. Precise enforcement
        would require platform-specific APIs (cgroups on Linux, job objects
        on Windows). This implementation provides basic protection.
        """
        if not self._process:
            return

        try:
            # Try to import psutil for resource monitoring
            try:
                import psutil

                process = psutil.Process(self._process.pid)
            except ImportError:
                _debug_warning(
                    "psutil not available, resource monitoring disabled. "
                    "Install psutil for CPU/memory limit enforcement."
                )
                return

            while self._process and self._process.poll() is None:
                try:
                    # Check memory usage
                    memory_mb = process.memory_info().rss / (1024 * 1024)
                    self._peak_memory_mb = max(self._peak_memory_mb, memory_mb)

                    if memory_mb > self.limits.max_memory_mb:
                        _debug_error(
                            f"Agent exceeded memory limit: {memory_mb:.0f}MB > {self.limits.max_memory_mb}MB"
                        )
                        self._violated_limits.append("max_memory_mb")
                        self._process.kill()
                        break

                    # Check CPU usage (non-blocking, returns since last call)
                    cpu_percent = process.cpu_percent(interval=None)
                    if cpu_percent > self.limits.max_cpu_percent:
                        _debug_warning(
                            f"Agent high CPU usage: {cpu_percent:.0f}% > {self.limits.max_cpu_percent}%"
                        )
                        # Note: We warn but don't kill on CPU - it's often bursty

                    time.sleep(1.0)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break

        except Exception as e:
            _debug_error(f"Resource monitoring error: {e}")

    def terminate(self) -> None:
        """
        Terminate the running agent process.

        This is a graceful termination that allows the process to clean up.
        """
        if self._process:
            try:
                _debug("Terminating agent process...")
                self._process.terminate()
                self._process.wait(timeout=5)
                _debug_success("Agent process terminated gracefully")
            except subprocess.TimeoutExpired:
                _debug_warning("Agent did not terminate gracefully, killing...")
                self.kill()
            except Exception as e:
                _debug_error(f"Error during agent termination: {e}")

    def kill(self) -> None:
        """
        Forcefully kill the running agent process.

        This is an immediate termination without cleanup.
        """
        if self._process:
            try:
                self._process.kill()
                self._process.wait(timeout=5)
                _debug_warning("Agent process killed")
            except Exception as e:
                _debug_error(f"Error during agent kill: {e}")
            finally:
                self._process = None

    def cleanup(self) -> None:
        """
        Clean up isolator resources.

        Terminates any running process and clears state.
        """
        if self._process:
            try:
                self._process.kill()
                self._process.wait(timeout=5)
            except Exception as e:
                _debug_error(f"Error during isolator cleanup: {e}")
            finally:
                self._process = None

        _debug_verbose("Isolator cleanup complete")

    def __enter__(self) -> AgentProcessIsolator:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleanup resources."""
        self.cleanup()
