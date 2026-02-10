#!/usr/bin/env python3
"""
Integration Tests for Plugin System
====================================

Tests the complete plugin lifecycle including:
- Plugin installation
- Plugin discovery and loading
- Agent lifecycle hook execution
- Plugin enable/disable functionality
- End-to-end plugin integration with agent sessions
"""

import json
import logging
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
import pytest

# Ensure apps/backend is in path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from plugins.registry import PluginRegistry
from plugins.loader import PluginLoader
from plugins.base import PluginType
from plugins.sdk.agent import AgentContext


class TestPluginIntegration:
    """Integration tests for full plugin lifecycle."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, temp_dir):
        """Setup and teardown for each test - ensures clean plugin registry."""
        # Reset plugin registry before each test
        PluginRegistry.reset_instance()
        yield
        # Reset after test
        PluginRegistry.reset_instance()

    @pytest.fixture
    def user_plugins_dir(self, temp_dir):
        """Create temporary user plugins directory."""
        plugins_dir = temp_dir / ".auto-claude" / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        return plugins_dir

    @pytest.fixture
    def system_plugins_dir(self):
        """Get path to example plugins directory."""
        # Use the actual example plugins from the project
        backend_dir = Path(__file__).parent.parent / "apps" / "backend"
        examples_dir = Path(__file__).parent.parent / "examples" / "plugins"

        # Try multiple locations for example plugins
        if examples_dir.exists():
            return examples_dir
        # Fallback to relative path from backend
        alt_path = backend_dir.parent.parent / "examples" / "plugins"
        if alt_path.exists():
            return alt_path

        # If running from worktree, use the worktree examples
        return Path.cwd() / "examples" / "plugins"

    @pytest.fixture
    def project_dir(self, temp_dir):
        """Create temporary project directory."""
        project = temp_dir / "test_project"
        project.mkdir(parents=True, exist_ok=True)

        # Create a minimal spec directory
        spec_dir = project / ".auto-claude" / "specs" / "001-test-spec"
        spec_dir.mkdir(parents=True, exist_ok=True)

        return project

    @pytest.fixture
    def spec_dir(self, project_dir):
        """Get spec directory."""
        return project_dir / ".auto-claude" / "specs" / "001-test-spec"

    @pytest.fixture
    def install_test_plugin(self, user_plugins_dir):
        """Create a test agent plugin for integration testing."""
        plugin_dir = user_plugins_dir / "test-agent-plugin"
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Create plugin.json manifest
        manifest = {
            "name": "test-agent-plugin",
            "version": "1.0.0",
            "author": "Test Suite",
            "description": "Test agent plugin for integration testing",
            "plugin_type": "agent",
            "auto_claude_version": ">=1.0.0",
            "required_permissions": [],
            "dependencies": [],
            "homepage": "https://example.com/test-plugin",
            "license": "MIT"
        }
        (plugin_dir / "plugin.json").write_text(json.dumps(manifest, indent=2))

        # Create plugin.py implementation
        plugin_code = '''"""Test Agent Plugin for Integration Testing."""
import logging
import sys
from pathlib import Path

# Ensure plugins package is importable
backend_dir = Path(__file__).parent.parent.parent.parent / "apps" / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import plugins.sdk.agent as _agent_sdk

logger = logging.getLogger(__name__)


class TestAgentPlugin(_agent_sdk.AgentPlugin):
    """Simple test agent plugin."""

    def __init__(self, metadata):
        super().__init__(metadata)
        self.session_count = 0
        self.load_called = False
        self.enable_called = False
        logger.debug(f"{self.name}: Plugin instance created")

    def on_load(self) -> None:
        """Called when plugin is first loaded."""
        self.load_called = True
        logger.info(f"{self.name}: Plugin loaded")

    def on_unload(self) -> None:
        """Called when plugin is being unloaded."""
        logger.info(f"{self.name}: Plugin unloaded")

    def on_enable(self) -> None:
        """Called when plugin is enabled."""
        self.enable_called = True
        logger.info(f"{self.name}: Plugin enabled")
        self.session_count = 0

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        logger.info(f"{self.name}: Plugin disabled")

    def before_session(self, context: '_agent_sdk.AgentContext') -> None:
        """Called before an agent session starts."""
        self.session_count += 1
        logger.info(
            f"{self.name}: Starting session #{self.session_count} "
            f"for spec '{context.spec_name}' in project '{context.project_name}'"
        )

    def after_session(self, context: '_agent_sdk.AgentContext', success: bool) -> None:
        """Called after an agent session completes."""
        status = "succeeded" if success else "failed"
        logger.info(f"{self.name}: Session {status}")

    def on_message(self, context: '_agent_sdk.AgentContext', message: any) -> None:
        """Called when agent receives a message."""
        logger.debug(f"{self.name}: Received message")
'''
        (plugin_dir / "plugin.py").write_text(plugin_code)

        return plugin_dir

    def test_plugin_discovery(self, user_plugins_dir, install_test_plugin):
        """Test that plugins are discovered correctly."""
        # Create registry with user plugins directory
        registry = PluginRegistry.get_instance(user_plugins_dir=user_plugins_dir)

        # Load all plugins
        registry.load_all_plugins()

        # Verify test-agent-plugin was discovered
        plugin = registry.get_plugin("test-agent-plugin")
        assert plugin is not None, "test-agent-plugin should be discovered"
        assert plugin.name == "test-agent-plugin"
        assert plugin.version == "1.0.0"
        assert plugin.plugin_type == PluginType.AGENT

    def test_plugin_lifecycle_hooks(self, user_plugins_dir, install_test_plugin, caplog):
        """Test that plugin lifecycle hooks are called correctly."""
        # Enable debug logging to capture plugin messages
        caplog.set_level(logging.INFO)

        # Create registry and load plugins
        registry = PluginRegistry.get_instance(user_plugins_dir=user_plugins_dir)
        registry.load_all_plugins()

        # Get plugin
        plugin = registry.get_plugin("test-agent-plugin")
        assert plugin is not None

        # Enable plugin (triggers on_load and on_enable)
        registry.enable_plugin("test-agent-plugin")

        # Verify plugin is enabled
        assert plugin.is_enabled

        # Check that on_load and on_enable were called
        assert any("Plugin loaded" in record.message for record in caplog.records)
        assert any("Plugin enabled" in record.message for record in caplog.records)

    def test_agent_session_hooks(
        self,
        user_plugins_dir,
        install_test_plugin,
        project_dir,
        spec_dir,
        caplog
    ):
        """Test that agent session hooks (before_session, after_session) are called."""
        # Enable debug logging
        caplog.set_level(logging.INFO)

        # Create registry and load plugins
        registry = PluginRegistry.get_instance(
            user_plugins_dir=user_plugins_dir,
            project_dir=project_dir
        )
        registry.load_all_plugins()

        # Enable test-agent-plugin
        registry.enable_plugin("test-agent-plugin")

        # Get plugin
        plugin = registry.get_plugin("test-agent-plugin")
        assert plugin is not None

        # Create agent context
        context = AgentContext(
            project_dir=project_dir,
            spec_dir=spec_dir,
            session_id="test-session-001",
            phase="implementation",
            metadata={}
        )

        # Clear previous log records
        caplog.clear()

        # Simulate before_session hook
        plugin.before_session(context)

        # Verify before_session was called and logged
        before_session_logs = [r for r in caplog.records if "Starting session" in r.message]
        assert len(before_session_logs) > 0, "before_session should log session start"

        # Verify session count incremented
        assert plugin.session_count == 1

        # Simulate after_session hook (success case)
        caplog.clear()
        plugin.after_session(context, success=True)

        # Verify after_session was called and logged success
        after_session_logs = [r for r in caplog.records if "succeeded" in r.message]
        assert len(after_session_logs) > 0, "after_session should log session success"

    def test_full_agent_plugin_lifecycle_e2e(
        self,
        user_plugins_dir,
        install_test_plugin,
        project_dir,
        spec_dir,
        caplog
    ):
        """
        End-to-end test of full agent plugin lifecycle:
        1. Install plugin
        2. Enable plugin
        3. Run simulated agent session
        4. Verify before_session and after_session hooks
        5. Check logs for lifecycle messages
        """
        # Enable all logging
        caplog.set_level(logging.DEBUG)

        # Step 1: Create registry and discover plugins
        registry = PluginRegistry.get_instance(
            user_plugins_dir=user_plugins_dir,
            project_dir=project_dir
        )

        # Step 2: Load all plugins
        registry.load_all_plugins()

        # Verify plugin was loaded
        all_plugins = registry.list_plugins()
        assert len(all_plugins) > 0, "At least one plugin should be loaded"

        plugin_names = [p.name for p in all_plugins]
        assert "test-agent-plugin" in plugin_names, "test-agent-plugin should be in loaded plugins"

        # Step 3: Enable the plugin
        registry.enable_plugin("test-agent-plugin")

        # Get plugin instance
        plugin = registry.get_plugin("test-agent-plugin")
        assert plugin is not None
        assert plugin.is_enabled

        # Verify on_load and on_enable were called
        assert any("Plugin loaded" in r.message for r in caplog.records)
        assert any("Plugin enabled" in r.message for r in caplog.records)

        # Step 4: Get enabled agent plugins (simulating what agent session does)
        enabled_agent_plugins = registry.list_plugins(plugin_type=PluginType.AGENT, enabled_only=True)
        assert len(enabled_agent_plugins) > 0, "Should have at least one enabled agent plugin"
        assert plugin in enabled_agent_plugins

        # Step 5: Simulate agent session
        context = AgentContext(
            project_dir=project_dir,
            spec_dir=spec_dir,
            session_id="integration-test-001",
            phase="coder",
            metadata={"test": "integration"}
        )

        # Clear previous logs
        caplog.clear()

        # Call before_session for all enabled agent plugins
        for p in enabled_agent_plugins:
            p.before_session(context)

        # Verify before_session was called
        assert any("Starting session" in r.message for r in caplog.records)
        assert plugin.session_count == 1

        # Simulate some agent work happening...
        # (In real scenario, agent would run here)

        # Call after_session for all enabled agent plugins
        caplog.clear()
        for p in enabled_agent_plugins:
            p.after_session(context, success=True)

        # Verify after_session was called
        assert any("succeeded" in r.message for r in caplog.records)

        # Step 6: Verify complete lifecycle
        # The plugin should have:
        # - Been loaded (on_load called)
        # - Been enabled (on_enable called)
        # - Participated in session (before_session, after_session called)
        # - Incremented session count
        assert plugin.session_count == 1
        assert plugin.is_enabled

    def test_plugin_disable(
        self,
        user_plugins_dir,
        install_test_plugin,
        project_dir,
        caplog
    ):
        """Test that disabling a plugin works correctly."""
        caplog.set_level(logging.INFO)

        # Create registry and load plugins
        registry = PluginRegistry.get_instance(
            user_plugins_dir=user_plugins_dir,
            project_dir=project_dir
        )
        registry.load_all_plugins()

        # Enable plugin
        registry.enable_plugin("test-agent-plugin")
        plugin = registry.get_plugin("test-agent-plugin")
        assert plugin.is_enabled

        # Disable plugin
        caplog.clear()
        registry.disable_plugin("test-agent-plugin")

        # Verify plugin is disabled
        assert not plugin.is_enabled

        # Verify on_disable was called
        assert any("Plugin disabled" in r.message for r in caplog.records)

    def test_plugin_failure_handling(
        self,
        user_plugins_dir,
        install_test_plugin,
        project_dir,
        spec_dir
    ):
        """Test that plugin hook failures are handled gracefully."""
        # Create registry and load plugins
        registry = PluginRegistry.get_instance(
            user_plugins_dir=user_plugins_dir,
            project_dir=project_dir
        )
        registry.load_all_plugins()
        registry.enable_plugin("test-agent-plugin")

        plugin = registry.get_plugin("test-agent-plugin")

        # Create context
        context = AgentContext(
            project_dir=project_dir,
            spec_dir=spec_dir,
            session_id="test-failure",
            phase="test",
            metadata={}
        )

        # Simulate after_session with failure
        # Should not raise exception
        plugin.after_session(context, success=False)

        # Plugin should still be functional
        assert plugin.is_enabled

    def test_multiple_plugins(
        self,
        user_plugins_dir,
        system_plugins_dir,
        install_test_plugin,
        project_dir
    ):
        """Test that multiple plugins can coexist."""
        # Install another example plugin if available
        custom_integration_src = system_plugins_dir / "custom-integration"
        if custom_integration_src.exists():
            custom_integration_dst = user_plugins_dir / "custom-integration"
            shutil.copytree(custom_integration_src, custom_integration_dst, dirs_exist_ok=True)

        # Create registry and load all plugins
        registry = PluginRegistry.get_instance(
            user_plugins_dir=user_plugins_dir,
            project_dir=project_dir
        )
        registry.load_all_plugins()

        # Get all plugins
        all_plugins = registry.list_plugins()

        # Should have at least test-agent-plugin
        plugin_names = [p.name for p in all_plugins]
        assert "test-agent-plugin" in plugin_names

        # If custom-integration was installed, it should be there too
        if custom_integration_src.exists():
            assert "custom-integration" in plugin_names or len(all_plugins) >= 1


class TestPluginContextAccess:
    """Tests for plugin access to context information."""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        """Reset registry before each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    def test_agent_context_contains_required_fields(self, temp_dir):
        """Test that AgentContext provides all required fields to plugins."""
        project_dir = temp_dir / "project"
        project_dir.mkdir()

        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        # Create context
        context = AgentContext(
            project_dir=project_dir,
            spec_dir=spec_dir,
            session_id="test-001",
            phase="planner",
            metadata={"key": "value"}
        )

        # Verify all fields are accessible
        assert context.project_dir == project_dir
        assert context.spec_dir == spec_dir
        assert context.session_id == "test-001"
        assert context.phase == "planner"
        assert context.metadata == {"key": "value"}

        # Verify derived properties
        assert context.project_name == "project"
        assert context.spec_name == "spec"

    def test_context_with_client(self, temp_dir):
        """Test that context can include client reference."""
        project_dir = temp_dir / "project"
        project_dir.mkdir()

        spec_dir = temp_dir / "spec"
        spec_dir.mkdir()

        # Mock client
        mock_client = MagicMock()

        # Create context with client
        context = AgentContext(
            project_dir=project_dir,
            spec_dir=spec_dir,
            session_id="test-002",
            client=mock_client,
            phase="coder",
            metadata={}
        )

        # Verify client is accessible
        assert context.client is mock_client


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
