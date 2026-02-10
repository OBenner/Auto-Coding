"""
Background Task Management Tools
=================================

Tools for managing long-running background commands with async execution,
progress tracking, and state persistence.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None


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

    def _generate_task_id(self) -> str:
        """
        Generate a unique task ID.

        Returns:
            Unique task ID string
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return f"task_{timestamp}"

    def _get_task_state_file(self, task_id: str) -> Path:
        """
        Get the state file path for a task.

        Args:
            task_id: Task identifier

        Returns:
            Path to the task state file
        """
        state_dir = self.spec_dir / ".background_tasks"
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir / f"{task_id}.json"

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
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(self.tasks[task_id], f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save task state for {task_id}: {e}")
            return False

    def _load_task_state(self, task_id: str) -> bool:
        """
        Load task state from disk.

        Args:
            task_id: Task identifier

        Returns:
            True if loaded successfully, False otherwise
        """
        state_file = self._get_task_state_file(task_id)
        if not state_file.exists():
            return False

        try:
            with open(state_file, encoding="utf-8") as f:
                self.tasks[task_id] = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Failed to load task state for {task_id}: {e}")
            return False

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
            # Update task state to running
            task["status"] = self.STATE_RUNNING
            task["started_at"] = datetime.now(UTC).isoformat()
            self._save_task_state(task_id)

            # Create subprocess with pipes for output streaming
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout
                cwd=str(work_dir),
            )

            # Store process reference
            self.processes[task_id] = process
            task["pid"] = process.pid
            self._save_task_state(task_id)

            logger.debug(f"Task {task_id} started with PID {process.pid}")

            # Stream output with timeout
            async def read_and_wait():
                """Read output and wait for completion."""
                output_lines = []
                if process.stdout:
                    async for line in process.stdout:
                        line_text = line.decode("utf-8", errors="replace")
                        output_lines.append(line_text)

                        # Update task output periodically (every 10 lines)
                        if len(output_lines) % 10 == 0:
                            task["output"] = "".join(output_lines)
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

                # Determine final status based on exit code
                if process.returncode == 0:
                    task["status"] = self.STATE_COMPLETED
                    logger.info(f"Task {task_id} completed successfully")
                else:
                    task["status"] = self.STATE_FAILED
                    task["error"] = f"Command exited with code {process.returncode}"
                    logger.warning(
                        f"Task {task_id} failed with exit code {process.returncode}"
                    )

            except asyncio.TimeoutError:
                # Timeout occurred
                task["status"] = self.STATE_FAILED
                task["error"] = f"Command timed out after {timeout} seconds"
                task["completed_at"] = datetime.now(UTC).isoformat()
                logger.error(f"Task {task_id} timed out after {timeout} seconds")

                # Try to terminate process gracefully
                try:
                    process.terminate()
                    await asyncio.sleep(0.5)
                    if process.returncode is None:
                        process.kill()
                        await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error terminating process for task {task_id}: {e}")

        except Exception as e:
            # Unexpected error during command execution
            task["status"] = self.STATE_FAILED
            task["error"] = f"Execution error: {str(e)}"
            task["completed_at"] = datetime.now(UTC).isoformat()
            logger.error(f"Task {task_id} failed with error: {e}", exc_info=True)

        finally:
            # Clean up process reference
            if task_id in self.processes:
                del self.processes[task_id]

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
        }

        # Save initial state
        self._save_task_state(task_id)

        # Start command execution in background
        asyncio.create_task(self._run_command(task_id))

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

        # Terminate process if running (will be implemented in subtask-1-3)
        if task_id in self.processes:
            process = self.processes[task_id]
            try:
                process.terminate()
                await asyncio.sleep(0.5)  # Give it time to graceful shutdown
                if process.returncode is None:
                    process.kill()
            except Exception as e:
                logger.error(f"Error cancelling task {task_id}: {e}")
                return False

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
        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error starting task: {e}"}
                ]
            }

    tools.append(start_background_command)

    # -------------------------------------------------------------------------
    # Tool: get_task_status (will be fully implemented in subtask-2-2)
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
        return {
            "content": [
                {"type": "text", "text": f"Task Status:\n{status_str}"}
            ]
        }

    tools.append(get_task_status)

    # -------------------------------------------------------------------------
    # Tool: get_task_output (will be fully implemented in subtask-2-2)
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
        return {
            "content": [
                {"type": "text", "text": f"Task Output:\n{output_str}"}
            ]
        }

    tools.append(get_task_output)

    # -------------------------------------------------------------------------
    # Tool: cancel_task (will be fully implemented in subtask-2-3)
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
