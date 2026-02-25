"""
Integration Plugin SDK
======================

SDK for creating custom integration plugins.

Integration plugins can:
- Connect to external services (issue trackers, monitoring, etc.)
- Create MCP tools for agent use
- Sync data between Auto Claude and external systems
- Manage integration configuration and state
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..base import PluginBase, PluginMetadata, PluginType

if TYPE_CHECKING:
    try:
        from claude_agent_sdk import create_sdk_mcp_server
    except ImportError:
        create_sdk_mcp_server = None

logger = logging.getLogger(__name__)


@dataclass
class IntegrationContext:
    """
    Context information provided to integration plugins.

    This context is passed to plugin hooks to provide information about
    the current project, spec, and integration configuration.

    Attributes:
        project_dir: Root directory of the project being worked on
        spec_dir: Directory containing the current spec
        config: Optional integration-specific configuration (from .env or settings)
        state: Optional persistent state data for this integration
        metadata: Optional additional metadata as key-value pairs
    """

    project_dir: Path
    spec_dir: Path
    config: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def spec_name(self) -> str:
        """Get the spec directory name."""
        return self.spec_dir.name

    @property
    def project_name(self) -> str:
        """Get the project directory name."""
        return self.project_dir.name

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key to look up
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Get a state value by key.

        Args:
            key: State key to look up
            default: Default value if key not found

        Returns:
            State value or default
        """
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """
        Set a state value.

        Args:
            key: State key to set
            value: Value to store
        """
        self.state[key] = value


class IntegrationPlugin(PluginBase):
    """
    Base class for integration plugins.

    Integration plugins connect Auto Claude to external services by providing
    MCP tools, syncing data, and managing external service state.

    Key capabilities:
    - Create MCP tools for agent use
    - Connect to external services (REST APIs, databases, etc.)
    - Sync data between Auto Claude and external systems
    - Manage configuration and persistent state

    Example:
        ```python
        class MyIntegrationPlugin(IntegrationPlugin):
            def __init__(self, metadata: PluginMetadata):
                super().__init__(metadata)
                self.api_client = None

            def on_load(self):
                # Validate configuration
                api_key = self.get_config_value("MY_SERVICE_API_KEY")
                if not api_key:
                    raise ValueError("MY_SERVICE_API_KEY not configured")

            def on_enable(self):
                # Connect to external service
                api_key = self.get_config_value("MY_SERVICE_API_KEY")
                self.api_client = MyServiceClient(api_key)
                logger.info("Connected to MyService")

            def on_disable(self):
                # Disconnect from service
                if self.api_client:
                    self.api_client.close()
                    self.api_client = None

            def on_unload(self):
                # Cleanup
                pass

            def create_mcp_tools(self, context: IntegrationContext) -> list:
                # Create tools for agent use
                def get_issues():
                    return self.api_client.list_issues()

                def create_issue(title: str, description: str):
                    return self.api_client.create_issue(title, description)

                return [get_issues, create_issue]

            def is_available(self) -> bool:
                # Check if service is available
                return self.api_client is not None and self.api_client.is_connected()

            def sync_data(self, context: IntegrationContext) -> None:
                # Sync implementation plan with external service
                plan = self.load_implementation_plan(context)
                if plan:
                    self.sync_subtasks_to_service(plan)
        ```
    """

    def __init__(self, metadata: PluginMetadata):
        """
        Initialize integration plugin.

        Args:
            metadata: Plugin metadata from plugin.json

        Raises:
            ValueError: If plugin_type is not INTEGRATION
        """
        if metadata.plugin_type != PluginType.INTEGRATION:
            raise ValueError(
                f"IntegrationPlugin requires plugin_type=INTEGRATION, got {metadata.plugin_type}"
            )
        super().__init__(metadata)
        self._config: dict[str, Any] = {}
        logger.debug(f"IntegrationPlugin initialized: {metadata.name}")

    def create_mcp_tools(self, context: IntegrationContext) -> list:
        """
        Create MCP tools for this integration.

        Override this method to provide tools that agents can use to interact
        with your external service. Tools should be simple functions with
        clear docstrings that explain their purpose and parameters.

        Args:
            context: Integration context with project/spec information

        Returns:
            List of tool functions (each function becomes an MCP tool)

        Example:
            ```python
            def create_mcp_tools(self, context: IntegrationContext) -> list:
                def search_docs(query: str) -> str:
                    '''Search the external documentation system.'''
                    return self.api_client.search(query)

                def create_ticket(title: str, priority: str) -> str:
                    '''Create a ticket in the external system.'''
                    return self.api_client.create_ticket(title, priority)

                return [search_docs, create_ticket]
            ```
        """
        return []

    def create_mcp_server(self, context: IntegrationContext):
        """
        Create an MCP server for this integration.

        This is a convenience method that creates an MCP server from the tools
        returned by create_mcp_tools(). Override create_mcp_tools() instead of
        this method in most cases.

        Args:
            context: Integration context with project/spec information

        Returns:
            MCP server instance, or None if no tools or SDK unavailable
        """
        try:
            from claude_agent_sdk import create_sdk_mcp_server
        except ImportError:
            logger.warning(f"Claude SDK not available for {self.name}")
            return None

        tools = self.create_mcp_tools(context)
        if not tools:
            return None

        return create_sdk_mcp_server(
            name=f"{self.name}-integration",
            version=self.version,
            tools=tools,
        )

    def is_available(self) -> bool:
        """
        Check if the integration is available and ready to use.

        Override this to check:
        - External service connectivity
        - API key validity
        - Required configuration presence
        - Feature flags

        Returns:
            True if integration can be used, False otherwise
        """
        return self.is_enabled

    def sync_data(self, context: IntegrationContext) -> None:
        """
        Sync data between Auto Claude and the external service.

        Override this to implement bidirectional sync:
        - Push subtasks/progress to external service
        - Pull updates from external service
        - Update implementation plan with external data

        This is called periodically during builds and can be used to keep
        external systems in sync with Auto Claude's state.

        Args:
            context: Integration context with project/spec information
        """
        pass

    def on_subtask_update(
        self, context: IntegrationContext, subtask_id: str, status: str
    ) -> None:
        """
        Called when a subtask status changes.

        Override this to push updates to external services in real-time.

        Args:
            context: Integration context
            subtask_id: ID of the subtask that changed
            status: New status (pending, in_progress, completed, failed)
        """
        pass

    def on_build_start(self, context: IntegrationContext) -> None:
        """
        Called when a build starts for a spec.

        Override this to:
        - Initialize external tracking (create project, epic, etc.)
        - Set up webhooks or listeners
        - Log build start

        Args:
            context: Integration context
        """
        pass

    def on_build_complete(self, context: IntegrationContext, success: bool) -> None:
        """
        Called when a build completes.

        Override this to:
        - Finalize external tracking
        - Send notifications
        - Clean up resources
        - Log results

        Args:
            context: Integration context
            success: True if build succeeded, False if failed
        """
        pass

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value from environment or plugin config.

        Args:
            key: Configuration key (usually env var name)
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        import os

        # Check environment first
        env_value = os.environ.get(key)
        if env_value is not None:
            return env_value

        # Fall back to plugin config
        return self._config.get(key, default)

    def set_config_value(self, key: str, value: Any) -> None:
        """
        Set a configuration value in plugin config.

        Args:
            key: Configuration key
            value: Value to store
        """
        self._config[key] = value

    def load_implementation_plan(self, context: IntegrationContext) -> dict | None:
        """
        Load the implementation plan from the spec directory.

        This is a helper method for integration plugins that need to sync
        subtasks with external services.

        Args:
            context: Integration context

        Returns:
            Implementation plan dictionary, or None if not found
        """
        import json

        plan_file = context.spec_dir / "implementation_plan.json"
        if not plan_file.exists():
            return None

        try:
            with open(plan_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to load implementation plan: {e}")
            return None

    def save_state(self, context: IntegrationContext) -> None:
        """
        Save integration state to spec directory.

        This is a helper method for persisting integration state across sessions.

        Args:
            context: Integration context with state to save
        """
        import json

        state_file = context.spec_dir / f".{self.name}_state.json"
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(context.state, f, indent=2)
        except (OSError, UnicodeEncodeError) as e:
            logger.error(f"Failed to save integration state: {e}")

    def load_state(self, context: IntegrationContext) -> None:
        """
        Load integration state from spec directory.

        This is a helper method for loading persisted integration state.

        Args:
            context: Integration context to populate with loaded state
        """
        import json

        state_file = context.spec_dir / f".{self.name}_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file, encoding="utf-8") as f:
                loaded_state = json.load(f)
                context.state.update(loaded_state)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to load integration state: {e}")
