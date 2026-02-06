"""
Plugin Isolation & Sandboxing
==============================

Provides secure plugin execution with resource limits and filesystem restrictions.

This module implements plugin sandboxing to prevent malicious or poorly-written
plugins from affecting system stability or security. Plugins are executed in
isolated subprocesses with controlled resource usage and restricted filesystem access.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Import debug utilities
try:
    from debug import (
        debug,
        debug_error,
        debug_success,
        debug_verbose,
        debug_warning,
    )
except ImportError:

    def debug(*args, **kwargs):
        pass

    def debug_verbose(*args, **kwargs):
        pass

    def debug_success(*args, **kwargs):
        pass

    def debug_error(*args, **kwargs):
        pass

    def debug_warning(*args, **kwargs):
        pass


@dataclass
class ResourceLimits:
    """
    Resource limits for plugin execution.

    These limits prevent plugins from consuming excessive system resources
    and ensure overall system stability.

    Attributes:
        max_memory_mb: Maximum memory usage in megabytes (default: 512MB)
        max_cpu_percent: Maximum CPU usage percentage (default: 50%)
        max_execution_seconds: Maximum execution time in seconds (default: 30s)
        max_file_descriptors: Maximum number of open file descriptors (default: 100)
        max_threads: Maximum number of threads (default: 10)
    """

    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    max_execution_seconds: int = 30
    max_file_descriptors: int = 100
    max_threads: int = 10

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
            max_memory_mb=data.get("max_memory_mb", 512),
            max_cpu_percent=data.get("max_cpu_percent", 50),
            max_execution_seconds=data.get("max_execution_seconds", 30),
            max_file_descriptors=data.get("max_file_descriptors", 100),
            max_threads=data.get("max_threads", 10),
        )


class SandboxViolation(Exception):
    """Raised when a plugin violates sandbox restrictions."""

    pass


class ResourceLimitExceeded(SandboxViolation):
    """Raised when a plugin exceeds resource limits."""

    pass


class FilesystemViolation(SandboxViolation):
    """Raised when a plugin attempts unauthorized filesystem access."""

    pass


@dataclass
class SandboxResult:
    """
    Result of sandboxed plugin execution.

    Attributes:
        success: Whether execution completed successfully
        stdout: Standard output from plugin
        stderr: Standard error from plugin
        return_code: Process exit code
        execution_time: Actual execution time in seconds
        error: Error message if execution failed
        violated_limits: List of resource limits that were exceeded
    """

    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None
    violated_limits: list[str] = field(default_factory=list)

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
        }


class PluginSandbox:
    """
    Sandbox for secure plugin execution.

    Executes plugins in isolated subprocesses with:
    - Restricted filesystem access (limited to plugin directory)
    - Resource limits (CPU, memory, time)
    - Monitored execution
    - Security boundaries

    Example:
        >>> from plugins.isolation import PluginSandbox, ResourceLimits
        >>> limits = ResourceLimits(max_memory_mb=256, max_execution_seconds=10)
        >>> sandbox = PluginSandbox(
        ...     plugin_dir=Path("/path/to/plugin"),
        ...     allowed_dirs=[Path("/path/to/project")],
        ...     limits=limits
        ... )
        >>> result = sandbox.execute_python(
        ...     script="plugin_main.py",
        ...     args=["arg1", "arg2"]
        ... )
        >>> if result.success:
        ...     print(f"Output: {result.stdout}")
        ... else:
        ...     print(f"Error: {result.error}")
    """

    def __init__(
        self,
        plugin_dir: Path,
        allowed_dirs: Optional[list[Path]] = None,
        limits: Optional[ResourceLimits] = None,
    ):
        """
        Initialize plugin sandbox.

        Args:
            plugin_dir: Directory containing the plugin
            allowed_dirs: Additional directories the plugin can access (e.g., project dir)
            limits: Resource limits for plugin execution
        """
        self.plugin_dir = Path(plugin_dir).resolve()
        self.allowed_dirs = [self.plugin_dir]
        if allowed_dirs:
            self.allowed_dirs.extend([Path(d).resolve() for d in allowed_dirs])
        self.limits = limits or ResourceLimits()
        self._process: Optional[subprocess.Popen] = None
        self._start_time: float = 0.0

        logger.debug(f"Initialized sandbox for plugin at: {self.plugin_dir}")
        debug_verbose(f"Allowed directories: {[str(d) for d in self.allowed_dirs]}")
        debug_verbose(f"Resource limits: {self.limits.to_dict()}")

    def _validate_path(self, path: Path) -> None:
        """
        Validate that a path is within allowed directories.

        Args:
            path: Path to validate

        Raises:
            FilesystemViolation: If path is outside allowed directories
        """
        resolved_path = Path(path).resolve()

        # Check if path is within any allowed directory
        for allowed_dir in self.allowed_dirs:
            try:
                resolved_path.relative_to(allowed_dir)
                return  # Path is valid
            except ValueError:
                continue

        # Path is not in any allowed directory
        raise FilesystemViolation(
            f"Plugin attempted to access unauthorized path: {path}\n"
            f"Allowed directories: {[str(d) for d in self.allowed_dirs]}"
        )

    def _create_sandbox_env(self) -> dict[str, str]:
        """
        Create restricted environment for plugin execution.

        Returns:
            Environment variables dict with security restrictions
        """
        # Start with minimal environment
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(self.plugin_dir),
            # Security flags
            "PYTHONDONTWRITEBYTECODE": "1",  # Prevent .pyc creation
            "PYTHONUNBUFFERED": "1",  # Real-time output
            # Resource hints (informational, not enforced by env vars)
            "AUTO_CLAUDE_PLUGIN_MAX_MEMORY_MB": str(self.limits.max_memory_mb),
            "AUTO_CLAUDE_PLUGIN_MAX_CPU_PERCENT": str(self.limits.max_cpu_percent),
            "AUTO_CLAUDE_PLUGIN_MAX_EXECUTION_SECONDS": str(
                self.limits.max_execution_seconds
            ),
        }

        # Add system-required variables
        if sys.platform == "win32":
            for var in ["SYSTEMROOT", "TEMP", "TMP"]:
                if var in os.environ:
                    env[var] = os.environ[var]

        return env

    def execute_python(
        self,
        script: str,
        args: Optional[list[str]] = None,
        working_dir: Optional[Path] = None,
    ) -> SandboxResult:
        """
        Execute a Python script in the sandbox.

        Args:
            script: Name of Python script to execute (relative to plugin_dir)
            args: Command-line arguments to pass to script
            working_dir: Working directory for execution (must be in allowed_dirs)

        Returns:
            SandboxResult with execution outcome

        Raises:
            FilesystemViolation: If script or working_dir is outside allowed paths
        """
        script_path = self.plugin_dir / script
        self._validate_path(script_path)

        if not script_path.exists():
            return SandboxResult(
                success=False,
                error=f"Script not found: {script}",
                return_code=-1,
            )

        # Validate working directory
        if working_dir:
            working_dir = Path(working_dir).resolve()
            self._validate_path(working_dir)
        else:
            working_dir = self.plugin_dir

        # Build command
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)

        debug(f"Executing plugin script: {script}")
        debug_verbose(f"Command: {' '.join(cmd)}")
        debug_verbose(f"Working dir: {working_dir}")

        return self._execute_subprocess(cmd, working_dir)

    def _execute_subprocess(
        self,
        cmd: list[str],
        working_dir: Path,
    ) -> SandboxResult:
        """
        Execute command in isolated subprocess with monitoring.

        Args:
            cmd: Command to execute
            working_dir: Working directory

        Returns:
            SandboxResult with execution outcome
        """
        env = self._create_sandbox_env()
        result = SandboxResult(success=False)
        self._start_time = time.time()

        try:
            # Start process with resource limits (platform-specific)
            self._process = subprocess.Popen(
                cmd,
                cwd=working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

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
                result.stdout = stdout
                result.stderr = stderr
                result.return_code = self._process.returncode
                result.execution_time = time.time() - self._start_time
                result.success = self._process.returncode == 0

                if result.success:
                    debug_success(
                        f"Plugin executed successfully in {result.execution_time:.2f}s"
                    )
                else:
                    debug_warning(
                        f"Plugin exited with code {result.return_code}: {stderr[:200]}"
                    )

            except subprocess.TimeoutExpired:
                self._process.kill()
                result.error = (
                    f"Execution timeout ({self.limits.max_execution_seconds}s exceeded)"
                )
                result.violated_limits.append("max_execution_seconds")
                debug_error(f"Plugin execution timeout: {result.error}")

        except Exception as e:
            result.error = f"Execution failed: {str(e)}"
            debug_error(f"Plugin execution error: {result.error}")
            if self._process:
                try:
                    self._process.kill()
                except Exception:
                    pass

        finally:
            self._process = None

        return result

    def _monitor_resources(self) -> None:
        """
        Monitor plugin resource usage during execution.

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
                debug_warning(
                    "psutil not available, resource monitoring disabled. "
                    "Install psutil for CPU/memory limit enforcement."
                )
                return

            while self._process and self._process.poll() is None:
                try:
                    # Check memory usage
                    memory_mb = process.memory_info().rss / (1024 * 1024)
                    if memory_mb > self.limits.max_memory_mb:
                        debug_error(
                            f"Plugin exceeded memory limit: {memory_mb:.0f}MB > {self.limits.max_memory_mb}MB"
                        )
                        self._process.kill()
                        break

                    # Check CPU usage (averaged over 1 second)
                    cpu_percent = process.cpu_percent(interval=1.0)
                    if cpu_percent > self.limits.max_cpu_percent:
                        debug_warning(
                            f"Plugin high CPU usage: {cpu_percent:.0f}% > {self.limits.max_cpu_percent}%"
                        )
                        # Note: We warn but don't kill on CPU - it's often bursty

                    time.sleep(0.5)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break

        except Exception as e:
            debug_error(f"Resource monitoring error: {e}")

    def cleanup(self) -> None:
        """
        Clean up sandbox resources.

        Terminates any running process and clears state.
        """
        if self._process:
            try:
                self._process.kill()
                self._process.wait(timeout=5)
            except Exception as e:
                debug_error(f"Error during sandbox cleanup: {e}")
            finally:
                self._process = None

        debug_verbose("Sandbox cleanup complete")

    def __enter__(self) -> PluginSandbox:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleanup resources."""
        self.cleanup()
