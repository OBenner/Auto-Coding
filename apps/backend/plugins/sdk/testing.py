"""
Plugin SDK Testing Utilities
=============================

Testing utilities for plugin developers.

This module provides mock contexts and base test cases for testing plugins
without requiring a full Auto Code setup or running actual agent sessions.

Example:
    ```python
    from plugins.sdk.testing import MockAgentContext, PluginTestCase
    from my_plugin import MyAgentPlugin

    class TestMyPlugin(PluginTestCase):
        def test_before_session(self):
            # Create mock context
            context = MockAgentContext()

            # Load and enable plugin
            plugin = self.load_plugin(MyAgentPlugin, "my-plugin")

            # Test lifecycle hook
            plugin.before_session(context)

            # Assert expected behavior
            assert context.metadata.get("initialized") is True
    ```
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..base import PluginMetadata, PluginPermission, PluginType

if TYPE_CHECKING:
    from ..base import PluginBase

logger = logging.getLogger(__name__)


class MockAgentContext:
    """
    Mock AgentContext for testing agent plugins.

    Provides a lightweight context object with sensible defaults for testing
    plugin lifecycle hooks without requiring a real agent session.

    All paths use temporary directories that are automatically cleaned up.

    Attributes:
        project_dir: Temporary project directory path
        spec_dir: Temporary spec directory path
        session_id: Mock session ID (default: "test-session-123")
        client: Mock Claude SDK client (default: None)
        phase: Mock phase name (default: "testing")
        metadata: Metadata dictionary for storing test data
    """

    def __init__(
        self,
        project_dir: Path | None = None,
        spec_dir: Path | None = None,
        session_id: str | None = "test-session-123",
        client: Any = None,
        phase: str | None = "testing",
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize mock agent context.

        Args:
            project_dir: Optional project directory (creates temp dir if None)
            spec_dir: Optional spec directory (creates temp dir if None)
            session_id: Optional session ID (default: "test-session-123")
            client: Optional mock Claude SDK client (default: None)
            phase: Optional phase name (default: "testing")
            metadata: Optional metadata dict (default: empty dict)
        """
        self._temp_dirs: list[tempfile.TemporaryDirectory] = []

        if project_dir is None:
            temp_project = tempfile.TemporaryDirectory(prefix="test_project_")
            self._temp_dirs.append(temp_project)
            project_dir = Path(temp_project.name)

        if spec_dir is None:
            temp_spec = tempfile.TemporaryDirectory(prefix="test_spec_")
            self._temp_dirs.append(temp_spec)
            spec_dir = Path(temp_spec.name)

        self.project_dir = Path(project_dir)
        self.spec_dir = Path(spec_dir)
        self.session_id = session_id
        self.client = client
        self.phase = phase
        self.metadata = metadata if metadata is not None else {}

    @property
    def spec_name(self) -> str:
        """Get the spec directory name."""
        return self.spec_dir.name

    @property
    def project_name(self) -> str:
        """Get the project directory name."""
        return self.project_dir.name

    def cleanup(self) -> None:
        """
        Clean up temporary directories.

        Call this in test teardown to remove temp directories.
        """
        for temp_dir in self._temp_dirs:
            try:
                temp_dir.cleanup()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")
        self._temp_dirs.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp dirs."""
        self.cleanup()


class MockIntegrationContext:
    """
    Mock IntegrationContext for testing integration plugins.

    Provides a lightweight context object with sensible defaults for testing
    integration plugin hooks without requiring a real integration setup.

    All paths use temporary directories that are automatically cleaned up.

    Attributes:
        project_dir: Temporary project directory path
        spec_dir: Temporary spec directory path
        config: Configuration dictionary
        state: State dictionary for persistent data
        metadata: Metadata dictionary for storing test data
    """

    def __init__(
        self,
        project_dir: Path | None = None,
        spec_dir: Path | None = None,
        config: dict[str, Any] | None = None,
        state: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize mock integration context.

        Args:
            project_dir: Optional project directory (creates temp dir if None)
            spec_dir: Optional spec directory (creates temp dir if None)
            config: Optional configuration dict (default: empty dict)
            state: Optional state dict (default: empty dict)
            metadata: Optional metadata dict (default: empty dict)
        """
        self._temp_dirs: list[tempfile.TemporaryDirectory] = []

        if project_dir is None:
            temp_project = tempfile.TemporaryDirectory(prefix="test_project_")
            self._temp_dirs.append(temp_project)
            project_dir = Path(temp_project.name)

        if spec_dir is None:
            temp_spec = tempfile.TemporaryDirectory(prefix="test_spec_")
            self._temp_dirs.append(temp_spec)
            spec_dir = Path(temp_spec.name)

        self.project_dir = Path(project_dir)
        self.spec_dir = Path(spec_dir)
        self.config = config if config is not None else {}
        self.state = state if state is not None else {}
        self.metadata = metadata if metadata is not None else {}

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

    def cleanup(self) -> None:
        """
        Clean up temporary directories.

        Call this in test teardown to remove temp directories.
        """
        for temp_dir in self._temp_dirs:
            try:
                temp_dir.cleanup()
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")
        self._temp_dirs.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp dirs."""
        self.cleanup()


class PluginTestCase:
    """
    Base test case class for plugin testing.

    Provides common utilities for loading plugins, creating mock contexts,
    and testing plugin lifecycle hooks.

    This is not a unittest.TestCase subclass - it's designed to work with
    pytest or as a mixin for unittest.

    Example:
        ```python
        import pytest
        from plugins.sdk.testing import PluginTestCase, MockAgentContext
        from my_plugin import MyAgentPlugin

        class TestMyPlugin(PluginTestCase):
            def test_plugin_lifecycle(self):
                # Create plugin with metadata
                plugin = self.create_plugin(
                    MyAgentPlugin,
                    name="my-plugin",
                    version="1.0.0",
                    plugin_type=PluginType.AGENT,
                    required_permissions=[PluginPermission.READ_FILES]
                )

                # Test lifecycle
                plugin.on_load()
                plugin.on_enable()
                assert plugin.is_enabled

                plugin.on_disable()
                assert not plugin.is_enabled

                plugin.on_unload()

            def test_before_session(self):
                plugin = self.load_plugin(MyAgentPlugin, "my-plugin")
                context = MockAgentContext()

                # Test hook
                plugin.before_session(context)
                assert context.metadata.get("initialized") is True

                context.cleanup()
        ```
    """

    def create_plugin_metadata(
        self,
        name: str,
        version: str = "1.0.0",
        author: str = "test-author",
        description: str = "Test plugin",
        plugin_type: PluginType = PluginType.AGENT,
        required_permissions: list[PluginPermission] | None = None,
        dependencies: list[str] | None = None,
        homepage: str | None = None,
        license: str | None = "MIT",
        auto_claude_version: str | None = None,
    ) -> PluginMetadata:
        """
        Create plugin metadata for testing.

        Args:
            name: Plugin name
            version: Plugin version (default: "1.0.0")
            author: Plugin author (default: "test-author")
            description: Plugin description (default: "Test plugin")
            plugin_type: Plugin type (default: AGENT)
            required_permissions: List of required permissions (default: empty)
            dependencies: List of plugin dependencies (default: empty)
            homepage: Optional homepage URL
            license: License identifier (default: "MIT")
            auto_claude_version: Optional Auto Claude version requirement

        Returns:
            PluginMetadata instance
        """
        return PluginMetadata(
            name=name,
            version=version,
            author=author,
            description=description,
            plugin_type=plugin_type,
            required_permissions=required_permissions or [],
            dependencies=dependencies or [],
            homepage=homepage,
            license=license,
            auto_claude_version=auto_claude_version,
        )

    def create_plugin(
        self,
        plugin_class: type[PluginBase],
        name: str,
        version: str = "1.0.0",
        author: str = "test-author",
        description: str = "Test plugin",
        plugin_type: PluginType = PluginType.AGENT,
        required_permissions: list[PluginPermission] | None = None,
        dependencies: list[str] | None = None,
        **kwargs,
    ) -> PluginBase:
        """
        Create a plugin instance for testing.

        Args:
            plugin_class: Plugin class to instantiate
            name: Plugin name
            version: Plugin version (default: "1.0.0")
            author: Plugin author (default: "test-author")
            description: Plugin description (default: "Test plugin")
            plugin_type: Plugin type (default: AGENT)
            required_permissions: List of required permissions (default: empty)
            dependencies: List of plugin dependencies (default: empty)
            **kwargs: Additional metadata fields

        Returns:
            Plugin instance
        """
        metadata = self.create_plugin_metadata(
            name=name,
            version=version,
            author=author,
            description=description,
            plugin_type=plugin_type,
            required_permissions=required_permissions,
            dependencies=dependencies,
            **kwargs,
        )
        return plugin_class(metadata)

    def load_plugin(
        self,
        plugin_class: type[PluginBase],
        name: str,
        **kwargs,
    ) -> PluginBase:
        """
        Create and load a plugin instance for testing.

        This is a convenience method that creates the plugin and calls on_load().

        Args:
            plugin_class: Plugin class to instantiate
            name: Plugin name
            **kwargs: Additional metadata fields (passed to create_plugin)

        Returns:
            Loaded plugin instance
        """
        plugin = self.create_plugin(plugin_class, name, **kwargs)
        plugin.on_load()
        plugin._mark_loaded()
        return plugin

    def enable_plugin(
        self,
        plugin_class: type[PluginBase],
        name: str,
        **kwargs,
    ) -> PluginBase:
        """
        Create, load, and enable a plugin instance for testing.

        This is a convenience method that creates the plugin, calls on_load(),
        and then calls on_enable().

        Args:
            plugin_class: Plugin class to instantiate
            name: Plugin name
            **kwargs: Additional metadata fields (passed to create_plugin)

        Returns:
            Enabled plugin instance
        """
        plugin = self.load_plugin(plugin_class, name, **kwargs)
        plugin.on_enable()
        plugin._mark_enabled()
        return plugin
