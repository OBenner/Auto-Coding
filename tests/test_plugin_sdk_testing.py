#!/usr/bin/env python3
"""
Tests for Plugin SDK Testing Utilities
=======================================

Tests the plugins.sdk.testing module functionality including:
- MockAgentContext initialization and cleanup
- MockIntegrationContext initialization and cleanup
- PluginTestCase helper methods
- Context manager behavior
- Temporary directory handling
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from apps.backend.plugins.base import PluginBase, PluginMetadata, PluginPermission, PluginType
from apps.backend.plugins.sdk.testing import (
    MockAgentContext,
    MockIntegrationContext,
    PluginTestCase,
)


# Test plugin implementations for testing
class SimpleAgentPlugin(PluginBase):
    """Simple agent plugin for testing."""

    def on_load(self) -> None:
        """Mark as loaded."""
        pass

    def on_unload(self) -> None:
        """Mark as unloaded."""
        pass

    def on_enable(self) -> None:
        """Mark as enabled."""
        pass

    def on_disable(self) -> None:
        """Mark as disabled."""
        pass

    def before_session(self, context) -> None:
        """Test lifecycle hook."""
        context.metadata["initialized"] = True


class TestMockAgentContext:
    """Tests for MockAgentContext."""

    def test_default_initialization(self):
        """Creates context with default values."""
        context = MockAgentContext()

        # Check default values
        assert context.session_id == "test-session-123"
        assert context.client is None
        assert context.phase == "testing"
        assert context.metadata == {}

        # Check that directories were created
        assert context.project_dir.exists()
        assert context.spec_dir.exists()

        # Cleanup
        context.cleanup()

    def test_custom_initialization(self):
        """Creates context with custom values."""
        with TemporaryDirectory() as project_dir, TemporaryDirectory() as spec_dir:
            custom_metadata = {"test": "value"}
            context = MockAgentContext(
                project_dir=Path(project_dir),
                spec_dir=Path(spec_dir),
                session_id="custom-session-456",
                client="mock-client",
                phase="implementation",
                metadata=custom_metadata,
            )

            # Check custom values
            assert context.session_id == "custom-session-456"
            assert context.client == "mock-client"
            assert context.phase == "implementation"
            assert context.metadata == custom_metadata
            assert str(context.project_dir) == project_dir
            assert str(context.spec_dir) == spec_dir

            # Cleanup (should not fail even though we didn't create temp dirs)
            context.cleanup()

    def test_spec_name_property(self):
        """Returns spec directory name."""
        context = MockAgentContext()
        assert context.spec_name == context.spec_dir.name
        context.cleanup()

    def test_project_name_property(self):
        """Returns project directory name."""
        context = MockAgentContext()
        assert context.project_name == context.project_dir.name
        context.cleanup()

    def test_cleanup(self):
        """Cleans up temporary directories."""
        context = MockAgentContext()

        # Store paths before cleanup
        project_path = context.project_dir
        spec_path = context.spec_dir

        # Both should exist
        assert project_path.exists()
        assert spec_path.exists()

        # Cleanup
        context.cleanup()

        # Directories should be removed
        assert not project_path.exists()
        assert not spec_path.exists()

    def test_context_manager(self):
        """Works as context manager with automatic cleanup."""
        project_path = None
        spec_path = None

        with MockAgentContext() as context:
            project_path = context.project_dir
            spec_path = context.spec_dir

            # Directories exist inside context
            assert project_path.exists()
            assert spec_path.exists()

        # Directories cleaned up after context exit
        assert not project_path.exists()
        assert not spec_path.exists()

    def test_metadata_modification(self):
        """Metadata dict can be modified."""
        with MockAgentContext() as context:
            context.metadata["key1"] = "value1"
            context.metadata["key2"] = 42

            assert context.metadata["key1"] == "value1"
            assert context.metadata["key2"] == 42


class TestMockIntegrationContext:
    """Tests for MockIntegrationContext."""

    def test_default_initialization(self):
        """Creates context with default values."""
        context = MockIntegrationContext()

        # Check default values
        assert context.config == {}
        assert context.state == {}
        assert context.metadata == {}

        # Check that directories were created
        assert context.project_dir.exists()
        assert context.spec_dir.exists()

        # Cleanup
        context.cleanup()

    def test_custom_initialization(self):
        """Creates context with custom values."""
        with TemporaryDirectory() as project_dir, TemporaryDirectory() as spec_dir:
            custom_config = {"api_key": "test-key"}
            custom_state = {"last_sync": "2024-01-01"}
            custom_metadata = {"test": "value"}

            context = MockIntegrationContext(
                project_dir=Path(project_dir),
                spec_dir=Path(spec_dir),
                config=custom_config,
                state=custom_state,
                metadata=custom_metadata,
            )

            # Check custom values
            assert context.config == custom_config
            assert context.state == custom_state
            assert context.metadata == custom_metadata
            assert str(context.project_dir) == project_dir
            assert str(context.spec_dir) == spec_dir

            # Cleanup
            context.cleanup()

    def test_spec_name_property(self):
        """Returns spec directory name."""
        context = MockIntegrationContext()
        assert context.spec_name == context.spec_dir.name
        context.cleanup()

    def test_project_name_property(self):
        """Returns project directory name."""
        context = MockIntegrationContext()
        assert context.project_name == context.project_dir.name
        context.cleanup()

    def test_get_config(self):
        """Gets configuration values."""
        config = {"key1": "value1", "key2": 42}
        context = MockIntegrationContext(config=config)

        assert context.get_config("key1") == "value1"
        assert context.get_config("key2") == 42
        assert context.get_config("missing") is None
        assert context.get_config("missing", "default") == "default"

        context.cleanup()

    def test_get_state(self):
        """Gets state values."""
        state = {"counter": 5, "enabled": True}
        context = MockIntegrationContext(state=state)

        assert context.get_state("counter") == 5
        assert context.get_state("enabled") is True
        assert context.get_state("missing") is None
        assert context.get_state("missing", "default") == "default"

        context.cleanup()

    def test_set_state(self):
        """Sets state values."""
        context = MockIntegrationContext()

        context.set_state("counter", 10)
        context.set_state("enabled", False)

        assert context.state["counter"] == 10
        assert context.state["enabled"] is False
        assert context.get_state("counter") == 10
        assert context.get_state("enabled") is False

        context.cleanup()

    def test_cleanup(self):
        """Cleans up temporary directories."""
        context = MockIntegrationContext()

        # Store paths before cleanup
        project_path = context.project_dir
        spec_path = context.spec_dir

        # Both should exist
        assert project_path.exists()
        assert spec_path.exists()

        # Cleanup
        context.cleanup()

        # Directories should be removed
        assert not project_path.exists()
        assert not spec_path.exists()

    def test_context_manager(self):
        """Works as context manager with automatic cleanup."""
        project_path = None
        spec_path = None

        with MockIntegrationContext() as context:
            project_path = context.project_dir
            spec_path = context.spec_dir

            # Directories exist inside context
            assert project_path.exists()
            assert spec_path.exists()

        # Directories cleaned up after context exit
        assert not project_path.exists()
        assert not spec_path.exists()


class TestPluginTestCase:
    """Tests for PluginTestCase helper methods."""

    def test_create_plugin_metadata_defaults(self):
        """Creates metadata with default values."""
        testcase = PluginTestCase()
        metadata = testcase.create_plugin_metadata("test-plugin")

        assert metadata.name == "test-plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "test-author"
        assert metadata.description == "Test plugin"
        assert metadata.plugin_type == PluginType.AGENT
        assert metadata.required_permissions == []
        assert metadata.dependencies == []
        assert metadata.license == "MIT"

    def test_create_plugin_metadata_custom(self):
        """Creates metadata with custom values."""
        testcase = PluginTestCase()
        metadata = testcase.create_plugin_metadata(
            name="custom-plugin",
            version="2.0.0",
            author="custom-author",
            description="Custom description",
            plugin_type=PluginType.INTEGRATION,
            required_permissions=[PluginPermission.READ_FILES, PluginPermission.NETWORK_ACCESS],
            dependencies=["dep1", "dep2"],
            homepage="https://example.com",
            license="Apache-2.0",
            auto_claude_version=">=2.8.0",
        )

        assert metadata.name == "custom-plugin"
        assert metadata.version == "2.0.0"
        assert metadata.author == "custom-author"
        assert metadata.description == "Custom description"
        assert metadata.plugin_type == PluginType.INTEGRATION
        assert metadata.required_permissions == [
            PluginPermission.READ_FILES,
            PluginPermission.NETWORK_ACCESS,
        ]
        assert metadata.dependencies == ["dep1", "dep2"]
        assert metadata.homepage == "https://example.com"
        assert metadata.license == "Apache-2.0"
        assert metadata.auto_claude_version == ">=2.8.0"

    def test_create_plugin(self):
        """Creates plugin instance."""
        testcase = PluginTestCase()
        plugin = testcase.create_plugin(
            SimpleAgentPlugin,
            name="test-plugin",
            version="1.0.0",
        )

        assert isinstance(plugin, SimpleAgentPlugin)
        assert plugin.name == "test-plugin"
        assert plugin.version == "1.0.0"
        assert plugin.plugin_type == PluginType.AGENT
        assert not plugin.is_loaded
        assert not plugin.is_enabled

    def test_create_plugin_with_permissions(self):
        """Creates plugin with permissions."""
        testcase = PluginTestCase()
        plugin = testcase.create_plugin(
            SimpleAgentPlugin,
            name="test-plugin",
            required_permissions=[PluginPermission.READ_FILES, PluginPermission.WRITE_FILES],
        )

        assert plugin.metadata.required_permissions == [
            PluginPermission.READ_FILES,
            PluginPermission.WRITE_FILES,
        ]

    def test_load_plugin(self):
        """Loads plugin and calls on_load."""
        testcase = PluginTestCase()
        plugin = testcase.load_plugin(SimpleAgentPlugin, "test-plugin")

        assert isinstance(plugin, SimpleAgentPlugin)
        assert plugin.is_loaded
        assert not plugin.is_enabled

    def test_enable_plugin(self):
        """Enables plugin and calls on_load and on_enable."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(SimpleAgentPlugin, "test-plugin")

        assert isinstance(plugin, SimpleAgentPlugin)
        assert plugin.is_loaded
        assert plugin.is_enabled

    def test_plugin_lifecycle(self):
        """Tests full plugin lifecycle."""
        testcase = PluginTestCase()

        # Create plugin
        plugin = testcase.create_plugin(
            SimpleAgentPlugin,
            name="lifecycle-plugin",
            version="1.0.0",
        )

        # Initial state
        assert not plugin.is_loaded
        assert not plugin.is_enabled

        # Load
        plugin.on_load()
        plugin._mark_loaded()
        assert plugin.is_loaded
        assert not plugin.is_enabled

        # Enable
        plugin.on_enable()
        plugin._mark_enabled()
        assert plugin.is_loaded
        assert plugin.is_enabled

        # Disable
        plugin.on_disable()
        plugin._mark_disabled()
        assert plugin.is_loaded
        assert not plugin.is_enabled

        # Unload
        plugin.on_unload()
        plugin._mark_unloaded()
        assert not plugin.is_loaded
        assert not plugin.is_enabled

    def test_plugin_with_mock_context(self):
        """Tests plugin with mock agent context."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(SimpleAgentPlugin, "test-plugin")

        with MockAgentContext() as context:
            # Test lifecycle hook
            plugin.before_session(context)

            # Verify hook behavior
            assert context.metadata.get("initialized") is True


class TestIntegrationPluginTestCase:
    """Integration tests combining multiple components."""

    def test_full_agent_plugin_test_flow(self):
        """Tests complete agent plugin testing flow."""
        testcase = PluginTestCase()

        # Create and enable plugin
        plugin = testcase.enable_plugin(
            SimpleAgentPlugin,
            name="integration-plugin",
            version="1.0.0",
            required_permissions=[PluginPermission.READ_FILES],
        )

        # Verify plugin state
        assert plugin.is_loaded
        assert plugin.is_enabled
        assert plugin.metadata.required_permissions == [PluginPermission.READ_FILES]

        # Test with mock context
        with MockAgentContext() as context:
            context.metadata["test_data"] = "value"

            # Call plugin hook
            plugin.before_session(context)

            # Verify modifications
            assert context.metadata.get("initialized") is True
            assert context.metadata.get("test_data") == "value"

    def test_multiple_contexts_cleanup(self):
        """Tests cleanup of multiple mock contexts."""
        paths = []

        # Create multiple contexts
        for i in range(3):
            with MockAgentContext() as context:
                paths.append((context.project_dir, context.spec_dir))

                # Verify directories exist during context
                assert context.project_dir.exists()
                assert context.spec_dir.exists()

        # Verify all directories were cleaned up
        for project_dir, spec_dir in paths:
            assert not project_dir.exists()
            assert not spec_dir.exists()

    def test_integration_context_state_persistence(self):
        """Tests state persistence in integration context."""
        with MockIntegrationContext() as context:
            # Set some state
            context.set_state("counter", 0)

            # Modify state over time
            for i in range(5):
                current = context.get_state("counter")
                context.set_state("counter", current + 1)

            # Verify final state
            assert context.get_state("counter") == 5
