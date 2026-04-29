"""
Background Task Management Tools
=================================

Tools for managing long-running background commands with async execution,
progress tracking, and state persistence.
"""

import asyncio
import collections
import json
import logging
import os
import shlex
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.platform import is_windows

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manages long-running background tasks with async execution.

    Features:
    - Async command execution with asyncio subprocess
    - Real-time output streaming
    - Task state persistence
    - Cancellation with cleanup
    - Configurable timeout (4+ hour support)
    - Memory monitoring (optional)

    Usage:
        manager = BackgroundTaskManager(spec_dir, project_dir)
        task_id = await manager.start_task("npm run build", timeout=14400)
        status = manager.get_task_status(task_id)
        output = manager.get_task_output(task_id)
        await manager.cancel_task(task_id)
    """

    # Default timeout: 4 hours (14400 seconds)
    DEFAULT_TIMEOUT = 14400

    # Memory monitoring thresholds (percentage)
    MEMORY_WARNING_THRESHOLD = 80.0  # Warn at 80% memory usage
    MEMORY_CRITICAL_THRESHOLD = 90.0  # Critical at 90% memory usage
    MEMORY_CHECK_INTERVAL = 5  # Check memory every 5 lines of output
    MAX_OUTPUT_LINES = 10000  # Rolling buffer size for output lines

    # Task states
    STATE_PENDING = "pending"
    STATE_RUNNING = "running"
    STATE_COMPLETED = "completed"
    STATE_FAILED = "failed"
    STATE_CANCELLED = "cancelled"

    def __init__(self, spec_dir: Path, project_dir: Path) -> None:
        """
        Initialize the background task manager.

        Args:
            spec_dir: Path to the spec directory for state persistence
            project_dir: Path to the project root for command execution
        """
        self.spec_dir = spec_dir
        self.project_dir = project_dir
        self.tasks: dict[str, dict[str, Any]] = {}
        self.processes: dict[str, asyncio.subprocess.Process] = {}
        self._async_tasks: dict[
            str, asyncio.Task
        ] = {}  # prevent GC of background tasks

    def _generate_task_id(self) -> str:
        """
        Generate a unique task ID.

        Returns:
            Unique task ID string
        """
        # Add microsecond precision for uniqueness (fixes collision bug when multiple tasks start within same second)
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        return f"task_{timestamp}"

    def _get_task_state_file(self, task_id: str) -> Path:
        """
        Get the state file path for a task.

        Validates task_id to prevent path traversal attacks.

        Args:
            task_id: Task identifier

        Returns:
            Path to the task state file

        Raises:
            ValueError: If task_id contains unsafe characters
        """
        import re

        if not re.match(r"^[a-zA-Z0-9_\-]+$", task_id):
            raise ValueError(f"Invalid task_id: {task_id!r}")

        state_dir = self.spec_dir / ".background_tasks"
        state_dir.mkdir(parents=True, exist_ok=True)
        candidate = (state_dir / f"{task_id}.json").resolve()

        if not str(candidate).startswith(str(state_dir.resolve())):
            raise ValueError(f"Path traversal detected in task_id: {task_id!r}")

        return candidate

    def _save_task_state(self, task_id: str) -> bool:
        """
        Save task state to disk.

        Args:
            task_id: Task identifier

        Returns:
            True if saved successfully, False otherwise
        """
        if task_id not in self.tasks:
            return False

        try:
            state_file = self._get_task_state_file(task_id)
        except ValueError:
            return False

        # Atomic write: write to temp file, fsync, then replace
        tmp_fd = None
        tmp_path = None
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(
                dir=str(state_file.parent), suffix=".tmp"
            )
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                tmp_fd = None  # os.fdopen takes ownership
                json.dump(self.tasks[task_id], f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, str(state_file))
            tmp_path = None  # replaced successfully
            return True
        except Exception as e:
            logger.error(f"Failed to save task state for {task_id}: {e}")
            return False
        finally:
            # Clean up temp file on error
            if tmp_fd is not None:
                os.close(tmp_fd)
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _load_task_state(self, task_id: str) -> bool:
        """
        Load task state from disk.

        Args:
            task_id: Task identifier

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            state_file = self._get_task_state_file(task_id)
        except ValueError:
            # Invalid task_id (path traversal, bad chars)
            return False

        if not state_file.exists():
            return False

        try:
            with open(state_file, encoding="utf-8") as f:
                self.tasks[task_id] = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Failed to load task state for {task_id}: {e}")
            return False

    def _get_memory_stats(self) -> dict[str, Any] | None:
        """
        Get current memory statistics.

        Returns:
            Dict with memory stats or None if psutil not available
        """
        if not PSUTIL_AVAILABLE:
            return None

        try:
            mem = psutil.virtual_memory()
            return {
                "percent": round(mem.percent, 2),
                "available_mb": round(mem.available / (1024 * 1024), 2),
                "total_mb": round(mem.total / (1024 * 1024), 2),
                "used_mb": round(mem.used / (1024 * 1024), 2),
            }
        except Exception as e:
            logger.warning(f"Failed to get memory stats: {e}")
            return None

    def _check_memory_threshold(self, task_id: str) -> bool:
        """
        Check if memory usage exceeds thresholds and log warnings.

        Args:
            task_id: Task identifier

        Returns:
            True if memory is within safe limits, False if critical
        """
        if not PSUTIL_AVAILABLE:
            return True

        try:
            mem_stats = self._get_memory_stats()
            if not mem_stats:
                return True

            mem_percent = mem_stats["percent"]

            if mem_percent >= self.MEMORY_CRITICAL_THRESHOLD:
                logger.error(f"Task {task_id}: Critical memory usage at {mem_percent}%")
                return False
            elif mem_percent >= self.MEMORY_WARNING_THRESHOLD:
                logger.warning(f"Task {task_id}: High memory usage at {mem_percent}%")

            return True
        except Exception as e:
            logger.warning(f"Error checking memory threshold: {e}")
            return True

    async def _run_command(self, task_id: str) -> None:
        """
        Run a command asynchronously and stream output.

        Args:
            task_id: Task identifier
        """
        task = self.tasks[task_id]
        command = task["command"]
        work_dir = Path(task["working_dir"])
        timeout = task["timeout"]

        try:
            # SECURITY: Parse command safely to prevent shell injection (CWE-78)
            # Using shlex.split() + create_subprocess_exec() instead of create_subprocess_shell()
            # This prevents command injection attacks like: echo "test" && rm -rf /
            try:
                if is_windows():
                    # On Windows, shlex.split() in POSIX mode (default) treats
                    # backslashes as escape characters, mangling paths like
                    # C:\Python\python.exe → C:Pythonpython.exe.
                    # Use posix=False and strip outer quotes that it preserves.
                    raw_args = shlex.split(command, posix=False)
                    args = [
                        a[1:-1]
                        if len(a) >= 2 and a[0] == a[-1] and a[0] in ('"', "'")
                        else a
                        for a in raw_args
                    ]
                else:
                    args = shlex.split(command)
            except ValueError as e:
                raise ValueError(f"Invalid command syntax: {e}")

            # Create subprocess with argument list (not shell string)
            process = await asyncio.create_subprocess_exec(
                *args,  # Pass as argument list, not shell string
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout
                cwd=str(work_dir),
            )

            # Store process reference
            self.processes[task_id] = process
            task["status"] = self.STATE_RUNNING
            task["started_at"] = datetime.now(UTC).isoformat()
            task["pid"] = process.pid
            self._save_task_state(task_id)

            logger.debug(f"Task {task_id} started with PID {process.pid}")

            # Stream output with timeout
            async def read_and_wait():
                """Read output and wait for completion."""
                output_lines: collections.deque[str] = collections.deque(
                    maxlen=self.MAX_OUTPUT_LINES
                )
                if process.stdout:
                    async for line in process.stdout:
                        line_text = line.decode("utf-8", errors="replace")
                        output_lines.append(line_text)

                        # Update task output periodically (every 10 lines)
                        if len(output_lines) % 10 == 0:
                            task["output"] = "".join(output_lines)

                            # Check memory usage periodically
                            if (
                                len(output_lines) % (10 * self.MEMORY_CHECK_INTERVAL)
                                == 0
                            ):
                                mem_stats = self._get_memory_stats()
                                if mem_stats:
                                    task["memory_stats"] = mem_stats

                                    # Check if memory exceeds critical threshold
                                    if not self._check_memory_threshold(task_id):
                                        logger.warning(
                                            f"Task {task_id}: Memory usage critical, "
                                            f"consider throttling or cancellation"
                                        )

                            self._save_task_state(task_id)

                # Wait for process to complete
                await process.wait()
                return output_lines

            try:
                # Apply timeout to entire read+wait operation
                output_lines = await asyncio.wait_for(read_and_wait(), timeout=timeout)

                # Save final output
                task["output"] = "".join(output_lines)
                task["exit_code"] = process.returncode
                task["completed_at"] = datetime.now(UTC).isoformat()

                # Capture final memory stats
                final_mem = self._get_memory_stats()
                if final_mem:
                    task["memory_stats"] = final_mem

                # Don't overwrite status if task was already cancelled
                if task.get("status") == self.STATE_CANCELLED:
                    logger.debug(
                        f"Task {task_id} was cancelled, skipping status update"
                    )
                elif process.returncode == 0:
                    task["status"] = self.STATE_COMPLETED
                    logger.info(f"Task {task_id} completed successfully")
                else:
                    task["status"] = self.STATE_FAILED
                    task["error"] = f"Command exited with code {process.returncode}"
                    logger.warning(
                        f"Task {task_id} failed with exit code {process.returncode}"
                    )
                    # Capture error context for failed tasks
                    self._capture_error_context(task_id)

            except TimeoutError:
                # Timeout occurred - don't overwrite if already cancelled
                if task.get("status") != self.STATE_CANCELLED:
                    task["status"] = self.STATE_FAILED
                    task["error"] = f"Command timed out after {timeout} seconds"
                    task["completed_at"] = datetime.now(UTC).isoformat()
                logger.error(f"Task {task_id} timed out after {timeout} seconds")

                # Capture error context for timeout
                self._capture_error_context(task_id)

                # Try to terminate process gracefully
                try:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=2.0)
                    except TimeoutError:
                        process.kill()
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                except (TimeoutError, OSError) as e:
                    logger.error(f"Error terminating process for task {task_id}: {e}")

        except Exception as e:
            # Unexpected error - don't overwrite if already cancelled
            if task.get("status") != self.STATE_CANCELLED:
                task["status"] = self.STATE_FAILED
                task["error"] = f"Execution error: {str(e)}"
                task["completed_at"] = datetime.now(UTC).isoformat()
            logger.error(f"Task {task_id} failed with error: {e}", exc_info=True)
            # Capture error context for execution errors
            self._capture_error_context(task_id)

        finally:
            # Clean up process reference
            # Note: asyncio subprocess manages stream cleanup automatically
            if task_id in self.processes:
                self.processes.pop(task_id)

            # Save final task state
            self._save_task_state(task_id)

    async def start_task(
        self,
        command: str,
        timeout: int = DEFAULT_TIMEOUT,
        working_dir: str | None = None,
    ) -> str:
        """
        Start a background task.

        Args:
            command: Command to execute
            timeout: Timeout in seconds (default: 14400 = 4 hours)
            working_dir: Working directory for command (default: project_dir)

        Returns:
            Task ID

        Raises:
            ValueError: If command is empty
        """
        if not command or not command.strip():
            raise ValueError("Command cannot be empty")

        task_id = self._generate_task_id()
        work_dir = Path(working_dir) if working_dir else self.project_dir

        # Initialize task state
        self.tasks[task_id] = {
            "id": task_id,
            "command": command,
            "working_dir": str(work_dir),
            "status": self.STATE_PENDING,
            "created_at": datetime.now(UTC).isoformat(),
            "started_at": None,
            "completed_at": None,
            "timeout": timeout,
            "output": "",
            "error": None,
            "exit_code": None,
            "pid": None,
            "memory_stats": self._get_memory_stats(),
        }

        # Save initial state
        self._save_task_state(task_id)

        # Start command execution in background
        # Store task reference to prevent premature garbage collection
        bg_task = asyncio.create_task(self._run_command(task_id))
        bg_task.add_done_callback(
            lambda t: (
                self._async_tasks.pop(task_id, None)
                or (t.exception() if not t.cancelled() and t.exception() else None)
            )
        )
        self._async_tasks[task_id] = bg_task

        logger.info(f"Started background task {task_id}: {command}")
        return task_id

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """
        Get the status of a task.

        Args:
            task_id: Task identifier

        Returns:
            Task status dict or None if not found
        """
        # Try to load from disk if not in memory
        if task_id not in self.tasks:
            self._load_task_state(task_id)

        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id].copy()
        # Exclude sensitive/internal fields
        task.pop("output", None)

        return task

    def get_task_output(self, task_id: str) -> dict[str, Any] | None:
        """
        Get the output of a task.

        Args:
            task_id: Task identifier

        Returns:
            Dict with 'output' and 'error' keys, or None if not found
        """
        # Try to load from disk if not in memory
        if task_id not in self.tasks:
            self._load_task_state(task_id)

        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]
        return {
            "output": task.get("output", ""),
            "error": task.get("error"),
            "exit_code": task.get("exit_code"),
        }

    def get_error_context(self, task_id: str) -> dict[str, Any] | None:
        """
        Get error context from a failed task.

        Args:
            task_id: Task identifier

        Returns:
            Dict with error context or None if not found/not failed
        """
        # Try to load from disk if not in memory
        if task_id not in self.tasks:
            self._load_task_state(task_id)

        if task_id not in self.tasks:
            return None

        task = self.tasks[task_id]

        # If task failed but no error context captured yet, capture it now
        if task["status"] == self.STATE_FAILED and "error_context" not in task:
            return self._capture_error_context(task_id)

        return task.get("error_context")

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled successfully, False otherwise
        """
        # Try to load from disk if not in memory
        if task_id not in self.tasks:
            self._load_task_state(task_id)

        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]

        # Can only cancel running tasks
        if task["status"] != self.STATE_RUNNING:
            return False

        # Terminate process if running
        if task_id in self.processes:
            process = self.processes[task_id]
            try:
                process.terminate()
                # Wait for graceful shutdown with timeout
                try:
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except TimeoutError:
                    # Force kill if graceful shutdown failed
                    process.kill()
                    await asyncio.wait_for(process.wait(), timeout=5.0)
            except (TimeoutError, OSError) as e:
                logger.error(f"Error cancelling task {task_id}: {e}")
                return False
            finally:
                # Clean up process reference
                self.processes.pop(task_id, None)

        # Update task state
        task["status"] = self.STATE_CANCELLED
        task["completed_at"] = datetime.now(UTC).isoformat()
        self._save_task_state(task_id)

        logger.info(f"Cancelled background task {task_id}")
        return True

    def list_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        """
        List all tasks, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of task dicts
        """
        # Load all task states from disk
        state_dir = self.spec_dir / ".background_tasks"
        if state_dir.exists():
            for state_file in state_dir.glob("*.json"):
                task_id = state_file.stem
                if task_id not in self.tasks:
                    self._load_task_state(task_id)

        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t["status"] == status]

        # Sort by created_at descending
        tasks.sort(key=lambda t: t["created_at"], reverse=True)

        return tasks

    def _classify_error(self, error_msg: str, output: str) -> str:
        """
        Classify error type from error message and output.

        Args:
            error_msg: Error message
            output: Command output

        Returns:
            Error type classification
        """
        combined = f"{error_msg} {output}".lower()

        # Timeout errors (check first - most specific)
        if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            return "timeout"

        # Memory errors
        memory_indicators = ["out of memory", "oom", "memory error", "cannot allocate"]
        if any(indicator in combined for indicator in memory_indicators):
            return "memory"

        # Build/compilation errors (check before test failures to avoid false positives)
        build_indicators = [
            "syntax error",
            "syntaxerror",
            "compilation error",
            "parse error",
            "parseerror",
            "build failed",
            "unexpected token",
        ]
        if any(indicator in combined for indicator in build_indicators):
            return "build_error"

        # Command not found / missing dependencies
        missing_indicators = [
            "command not found",
            "not found",
            "no such file",
            "cannot find",
            "modulenotfounderror",
            "module not found",
        ]
        if any(indicator in combined for indicator in missing_indicators):
            return "command_not_found"

        # Permission errors
        permission_indicators = [
            "permission denied",
            "eacces",
            "access denied",
            "not permitted",
        ]
        if any(indicator in combined for indicator in permission_indicators):
            return "permission_denied"

        # Network errors
        network_indicators = [
            "network error",
            "connection refused",
            "connection timeout",
            "unreachable",
            "dns",
        ]
        if any(indicator in combined for indicator in network_indicators):
            return "network"

        # Test failures (check after build errors)
        test_indicators = ["test failed", "assertion", "assertion error"]
        if any(indicator in combined for indicator in test_indicators):
            return "test_failed"

        return "unknown"

    def _capture_error_context(self, task_id: str) -> dict[str, Any]:
        """
        Capture error context from a failed task.

        Args:
            task_id: Task identifier

        Returns:
            Dict with error context information
        """
        if task_id not in self.tasks:
            return {}

        task = self.tasks[task_id]
        error_msg = task.get("error", "")
        output = task.get("output", "")

        # Classify the error
        error_type = self._classify_error(error_msg, output)

        # Extract relevant output snippets (last 20 lines or less)
        output_lines = output.split("\n") if output else []
        relevant_output = "\n".join(output_lines[-20:]) if output_lines else ""

        # Build error context
        error_context = {
            "error_type": error_type,
            "error_message": error_msg,
            "exit_code": task.get("exit_code"),
            "relevant_output": relevant_output,
            "timeout_used": task.get("timeout"),
            "memory_stats": task.get("memory_stats"),
            "retry_suggestion": self.get_retry_suggestion(error_type),
            "captured_at": datetime.now(UTC).isoformat(),
        }

        # Store error context in task
        task["error_context"] = error_context
        self._save_task_state(task_id)

        return error_context

    @staticmethod
    def get_retry_suggestion(error_type: str) -> str:
        """
        Get a retry suggestion based on error type.

        Args:
            error_type: Type of error (timeout, memory, command_not_found, etc.)

        Returns:
            Suggestion string
        """
        suggestions = {
            "timeout": "increase_timeout",
            "memory": "reduce_memory_usage",
            "command_not_found": "install_dependencies",
            "permission_denied": "check_permissions",
            "network": "check_network",
            "build_error": "fix_syntax_or_compilation",
            "test_failed": "review_test_failures",
        }

        return suggestions.get(error_type, "retry")


def create_background_task_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create background task management tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of background task tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []

    # Create a shared manager instance
    manager = BackgroundTaskManager(spec_dir, project_dir)

    # -------------------------------------------------------------------------
    # Tool: start_background_command
    # -------------------------------------------------------------------------
    @tool(
        "start_background_command",
        "Start a long-running command in the background. Use this for commands that may take more than a few minutes (builds, tests, data processing).",
        {"command": str, "timeout": int, "working_dir": str},
    )
    async def start_background_command(args: dict[str, Any]) -> dict[str, Any]:
        """Start a background command."""
        command = args["command"]
        timeout = args.get("timeout", BackgroundTaskManager.DEFAULT_TIMEOUT)
        working_dir = args.get("working_dir")

        try:
            task_id = await manager.start_task(command, timeout, working_dir)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Started background task {task_id}",
                    }
                ]
            }
        except Exception:
            logger.error("Failed to start background task", exc_info=True)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error starting task. Check server logs for details.",
                    }
                ]
            }

    tools.append(start_background_command)

    # -------------------------------------------------------------------------
    # Tool: get_task_status
    # -------------------------------------------------------------------------
    @tool(
        "get_task_status",
        "Get the status of a background task. Returns task state, progress, and metadata.",
        {"task_id": str},
    )
    async def get_task_status(args: dict[str, Any]) -> dict[str, Any]:
        """Get background task status."""
        task_id = args["task_id"]

        status = manager.get_task_status(task_id)
        if not status:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Task '{task_id}' not found",
                    }
                ]
            }

        status_str = json.dumps(status, indent=2)
        return {"content": [{"type": "text", "text": f"Task Status:\n{status_str}"}]}

    tools.append(get_task_status)

    # -------------------------------------------------------------------------
    # Tool: get_task_output
    # -------------------------------------------------------------------------
    @tool(
        "get_task_output",
        "Get the output of a background task. Returns stdout, stderr, and exit code.",
        {"task_id": str},
    )
    async def get_task_output(args: dict[str, Any]) -> dict[str, Any]:
        """Get background task output."""
        task_id = args["task_id"]

        output = manager.get_task_output(task_id)
        if not output:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Task '{task_id}' not found",
                    }
                ]
            }

        output_str = json.dumps(output, indent=2)
        return {"content": [{"type": "text", "text": f"Task Output:\n{output_str}"}]}

    tools.append(get_task_output)

    # -------------------------------------------------------------------------
    # Tool: cancel_task
    # -------------------------------------------------------------------------
    @tool(
        "cancel_task",
        "Cancel a running background task. Attempts graceful shutdown, then force kills if needed.",
        {"task_id": str},
    )
    async def cancel_task(args: dict[str, Any]) -> dict[str, Any]:
        """Cancel a background task."""
        task_id = args["task_id"]

        success = await manager.cancel_task(task_id)
        if not success:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Failed to cancel task '{task_id}' (not found or not running)",
                    }
                ]
            }

        return {
            "content": [
                {"type": "text", "text": f"Successfully cancelled task {task_id}"}
            ]
        }

    tools.append(cancel_task)

    return tools
