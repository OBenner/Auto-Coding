"""
Custom Integration Plugin Example
==================================

Example integration plugin that demonstrates:
- IntegrationPlugin interface implementation
- MCP tool creation for agent use
- Configuration management (API endpoint, settings)
- State persistence (task counter, sync timestamps)
- External service integration (file-based mock TaskManager)
- Build lifecycle hooks

This plugin connects to a simple file-based "TaskManager" service and provides
tools for agents to create, list, and update tasks. It demonstrates how to
build a real-world integration without requiring external dependencies.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from apps.backend.plugins.base import PluginMetadata
from apps.backend.plugins.sdk.integration import IntegrationContext, IntegrationPlugin

logger = logging.getLogger(__name__)


class MockTaskManagerClient:
    """
    Mock external service client (file-based task storage).

    In a real integration, this would be an HTTP API client, database client,
    or other external service connector.
    """

    def __init__(self, data_dir: Path):
        """Initialize the mock client with a data directory."""
        self.data_dir = data_dir
        self.tasks_file = data_dir / "tasks.json"
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Ensure the data directory and tasks file exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.tasks_file.exists():
            self._save_tasks([])

    def _load_tasks(self) -> list[dict]:
        """Load tasks from file."""
        try:
            with open(self.tasks_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to load tasks: {e}")
            return []

    def _save_tasks(self, tasks: list[dict]) -> None:
        """Save tasks to file."""
        try:
            with open(self.tasks_file, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2)
        except (OSError, UnicodeEncodeError) as e:
            logger.error(f"Failed to save tasks: {e}")

    def is_connected(self) -> bool:
        """Check if the client can access the service."""
        return self.tasks_file.exists()

    def create_task(
        self, title: str, description: str, status: str = "pending"
    ) -> dict:
        """Create a new task."""
        tasks = self._load_tasks()
        task_id = len(tasks) + 1
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        tasks.append(task)
        self._save_tasks(tasks)
        logger.info(f"Created task #{task_id}: {title}")
        return task

    def list_tasks(self, status: str | None = None) -> list[dict]:
        """List all tasks, optionally filtered by status."""
        tasks = self._load_tasks()
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        return tasks

    def update_task(self, task_id: int, status: str) -> dict | None:
        """Update a task's status."""
        tasks = self._load_tasks()
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = status
                task["updated_at"] = datetime.now().isoformat()
                self._save_tasks(tasks)
                logger.info(f"Updated task #{task_id} to {status}")
                return task
        return None

    def get_task(self, task_id: int) -> dict | None:
        """Get a task by ID."""
        tasks = self._load_tasks()
        for task in tasks:
            if task.get("id") == task_id:
                return task
        return None


class CustomIntegrationPlugin(IntegrationPlugin):
    """
    Example integration plugin demonstrating IntegrationPlugin capabilities.

    This plugin connects to a mock file-based TaskManager service and provides
    MCP tools for agents to interact with it. It demonstrates:
    - Config management (data directory location)
    - State persistence (task counter, last sync time)
    - MCP tool creation (create_task, list_tasks, update_task, get_task)
    - Lifecycle hooks (on_load, on_enable, on_disable, on_unload)
    - Build hooks (on_build_start, on_build_complete, on_subtask_update)
    - External service integration (MockTaskManagerClient)
    """

    def __init__(self, metadata: PluginMetadata):
        """Initialize the custom integration plugin."""
        super().__init__(metadata)
        self.client: MockTaskManagerClient | None = None
        logger.debug("CustomIntegrationPlugin initialized")

    def on_load(self) -> None:
        """
        Called when plugin is loaded.

        Validates configuration and ensures required settings are present.
        """
        logger.info("custom-integration: Plugin loaded")

        # Check for optional configuration
        data_dir = self.get_config_value("CUSTOM_INTEGRATION_DATA_DIR")
        if data_dir:
            logger.info(f"custom-integration: Using custom data directory: {data_dir}")
        else:
            logger.debug(
                "custom-integration: No data directory configured, will use default"
            )

    def on_enable(self) -> None:
        """
        Called when plugin is enabled.

        Initializes the connection to the external service.
        """
        logger.info("custom-integration: Plugin enabled")

        # Get data directory from config or use default
        data_dir_str = self.get_config_value(
            "CUSTOM_INTEGRATION_DATA_DIR", "~/.auto-claude/task-manager"
        )
        data_dir = Path(data_dir_str).expanduser()

        # Initialize the mock client
        self.client = MockTaskManagerClient(data_dir)
        logger.info(f"custom-integration: Connected to TaskManager at {data_dir}")

    def on_disable(self) -> None:
        """
        Called when plugin is disabled.

        Disconnects from the external service.
        """
        logger.info("custom-integration: Plugin disabled")
        if self.client:
            self.client = None
            logger.debug("custom-integration: Disconnected from TaskManager")

    def on_unload(self) -> None:
        """
        Called when plugin is unloaded.

        Cleanup resources and save any final state.
        """
        logger.info("custom-integration: Plugin unloaded")

    def create_mcp_tools(self, context: IntegrationContext) -> list:
        """
        Create MCP tools for this integration.

        These tools will be available to agents during sessions, allowing them
        to interact with the external TaskManager service.

        Args:
            context: Integration context with project/spec information

        Returns:
            List of tool functions for agent use
        """
        if not self.client:
            logger.warning("custom-integration: Client not initialized, no tools")
            return []

        # Load state to track usage
        self.load_state(context)
        task_count = context.get_state("task_count", 0)

        def create_task(title: str, description: str) -> str:
            """
            Create a new task in the external TaskManager.

            Args:
                title: Task title
                description: Task description

            Returns:
                JSON string with created task details
            """
            if not self.client:
                return json.dumps({"error": "TaskManager not connected"})

            task = self.client.create_task(title, description)
            context.set_state("task_count", context.get_state("task_count", 0) + 1)
            context.set_state("last_create", datetime.now().isoformat())
            self.save_state(context)
            return json.dumps(task, indent=2)

        def list_tasks(status: str | None = None) -> str:
            """
            List all tasks from the external TaskManager.

            Args:
                status: Optional status filter (pending, in_progress, completed)

            Returns:
                JSON string with list of tasks
            """
            if not self.client:
                return json.dumps({"error": "TaskManager not connected"})

            tasks = self.client.list_tasks(status)
            context.set_state("last_list", datetime.now().isoformat())
            self.save_state(context)
            return json.dumps(tasks, indent=2)

        def update_task_status(task_id: int, status: str) -> str:
            """
            Update a task's status in the external TaskManager.

            Args:
                task_id: ID of the task to update
                status: New status (pending, in_progress, completed)

            Returns:
                JSON string with updated task details or error
            """
            if not self.client:
                return json.dumps({"error": "TaskManager not connected"})

            task = self.client.update_task(task_id, status)
            if task:
                context.set_state("last_update", datetime.now().isoformat())
                self.save_state(context)
                return json.dumps(task, indent=2)
            return json.dumps({"error": f"Task {task_id} not found"})

        def get_task_details(task_id: int) -> str:
            """
            Get details of a specific task from the external TaskManager.

            Args:
                task_id: ID of the task to retrieve

            Returns:
                JSON string with task details or error
            """
            if not self.client:
                return json.dumps({"error": "TaskManager not connected"})

            task = self.client.get_task(task_id)
            if task:
                return json.dumps(task, indent=2)
            return json.dumps({"error": f"Task {task_id} not found"})

        logger.info(
            f"custom-integration: Created 4 MCP tools for spec '{context.spec_name}'"
        )
        logger.debug(f"custom-integration: Previous task count: {task_count}")

        return [create_task, list_tasks, update_task_status, get_task_details]

    def is_available(self) -> bool:
        """
        Check if the integration is available and ready to use.

        Returns:
            True if TaskManager is connected and available
        """
        return (
            self.is_enabled and self.client is not None and self.client.is_connected()
        )

    def sync_data(self, context: IntegrationContext) -> None:
        """
        Sync data between Auto Code and the external TaskManager.

        This demonstrates how to push subtasks to an external system.

        Args:
            context: Integration context with project/spec information
        """
        if not self.is_available():
            logger.debug("custom-integration: Sync skipped (not available)")
            return

        logger.info(f"custom-integration: Syncing data for spec '{context.spec_name}'")

        # Load implementation plan
        plan = self.load_implementation_plan(context)
        if not plan:
            logger.warning("custom-integration: No implementation plan found")
            return

        # Sync subtasks to external system
        phases = plan.get("phases", [])
        synced_count = 0

        for phase in phases:
            for subtask in phase.get("subtasks", []):
                subtask_id = subtask.get("id")
                description = subtask.get("description")
                status = subtask.get("status", "pending")

                # Check if task already exists in state
                task_mapping = context.get_state("task_mapping", {})
                if subtask_id not in task_mapping:
                    # Create new task in external system
                    task = self.client.create_task(
                        title=f"[{phase.get('name')}] {subtask_id}",
                        description=description,
                        status=status,
                    )
                    task_mapping[subtask_id] = task["id"]
                    context.set_state("task_mapping", task_mapping)
                    synced_count += 1
                else:
                    # Update existing task
                    task_id = task_mapping[subtask_id]
                    self.client.update_task(task_id, status)
                    synced_count += 1

        context.set_state("last_sync", datetime.now().isoformat())
        self.save_state(context)
        logger.info(f"custom-integration: Synced {synced_count} subtasks")

    def on_subtask_update(
        self, context: IntegrationContext, subtask_id: str, status: str
    ) -> None:
        """
        Called when a subtask status changes.

        Args:
            context: Integration context
            subtask_id: ID of the subtask that changed
            status: New status
        """
        if not self.is_available():
            return

        logger.info(f"custom-integration: Subtask {subtask_id} updated to {status}")

        # Update task in external system
        task_mapping = context.get_state("task_mapping", {})
        if subtask_id in task_mapping:
            task_id = task_mapping[subtask_id]
            self.client.update_task(task_id, status)
            logger.debug(f"custom-integration: Updated task #{task_id} to {status}")

    def on_build_start(self, context: IntegrationContext) -> None:
        """
        Called when a build starts.

        Args:
            context: Integration context
        """
        if not self.is_available():
            return

        logger.info(f"custom-integration: Build started for spec '{context.spec_name}'")

        # Create a "build started" task
        if self.client:
            self.client.create_task(
                title=f"Build Started: {context.spec_name}",
                description=f"Auto Code build started for {context.project_name}",
                status="in_progress",
            )

        context.set_state("build_start_time", datetime.now().isoformat())
        self.save_state(context)

    def on_build_complete(self, context: IntegrationContext, success: bool) -> None:
        """
        Called when a build completes.

        Args:
            context: Integration context
            success: True if build succeeded, False if failed
        """
        if not self.is_available():
            return

        status = "completed" if success else "failed"
        logger.info(
            f"custom-integration: Build {status} for spec '{context.spec_name}'"
        )

        # Create a "build complete" task
        if self.client:
            build_start = context.get_state("build_start_time", "unknown")
            self.client.create_task(
                title=f"Build {status.capitalize()}: {context.spec_name}",
                description=f"Auto Code build {status} for {context.project_name}\nStarted: {build_start}",
                status=status,
            )

        context.set_state("build_end_time", datetime.now().isoformat())
        context.set_state("build_success", success)
        self.save_state(context)
