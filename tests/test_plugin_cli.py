#!/usr/bin/env python3
"""
Plugin CLI Command Tests
=========================

Tests for plugin CLI commands including:
- list command with filtering
- enable/disable commands
- install command from path and URL
- info and uninstall commands
- Error handling and edge cases
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest

# Ensure apps/backend is in path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from plugins.cli import (
    create_parser,
    cmd_list,
    cmd_enable,
    cmd_disable,
    cmd_install,
    cmd_info,
    cmd_uninstall,
    main,
)
from plugins.base import PluginType
from plugins.registry import PluginRegistry
from plugins.loader import PluginLoadError, PluginValidationError


class TestPluginCLIParser:
    """Tests for CLI argument parser."""

    def test_parser_creates_all_commands(self):
        """Test that parser creates all expected commands."""
        parser = create_parser()

        # Get subparsers from parser - look for _SubParsersAction
        subparsers_actions = [
            action for action in parser._actions
            if hasattr(action, 'choices') and action.choices is not None
        ]
        assert len(subparsers_actions) > 0, "Parser should have subparsers"

        # Get choices (command names)
        subparsers_action = subparsers_actions[0]
        choices = list(subparsers_action.choices.keys())

        # Verify all expected commands exist
        expected_commands = ["list", "enable", "disable", "install", "info", "uninstall"]
        for cmd in expected_commands:
            assert cmd in choices, f"Command '{cmd}' should be in parser"

    def test_list_command_parses_type_filter(self):
        """Test that list command parses --type argument."""
        parser = create_parser()

        # Test default (all)
        args = parser.parse_args(["list"])
        assert args.command == "list"
        assert args.type == "all"
        assert args.enabled_only is False

        # Test type filters
        for plugin_type in ["agent", "integration", "ui"]:
            args = parser.parse_args(["list", "--type", plugin_type])
            assert args.type == plugin_type

    def test_list_command_parses_enabled_only_flag(self):
        """Test that list command parses --enabled-only flag."""
        parser = create_parser()

        args = parser.parse_args(["list", "--enabled-only"])
        assert args.enabled_only is True

    def test_enable_command_parses_plugin_name(self):
        """Test that enable command parses plugin name."""
        parser = create_parser()

        args = parser.parse_args(["enable", "my-plugin"])
        assert args.command == "enable"
        assert args.plugin_name == "my-plugin"

    def test_disable_command_parses_plugin_name(self):
        """Test that disable command parses plugin name."""
        parser = create_parser()

        args = parser.parse_args(["disable", "my-plugin"])
        assert args.command == "disable"
        assert args.plugin_name == "my-plugin"

    def test_install_command_parses_path(self):
        """Test that install command parses --path argument."""
        parser = create_parser()

        args = parser.parse_args(["install", "--path", "/some/path"])
        assert args.command == "install"
        assert args.path == "/some/path"
        assert args.url is None
        assert args.force is False

    def test_install_command_parses_url(self):
        """Test that install command parses --url argument."""
        parser = create_parser()

        args = parser.parse_args(["install", "--url", "https://github.com/user/plugin.git"])
        assert args.command == "install"
        assert args.url == "https://github.com/user/plugin.git"
        assert args.path is None

    def test_install_command_parses_force_flag(self):
        """Test that install command parses --force flag."""
        parser = create_parser()

        args = parser.parse_args(["install", "--path", "/path", "--force"])
        assert args.force is True

    def test_install_command_parses_dry_run_flag(self):
        """Test that install command parses --dry-run flag."""
        parser = create_parser()

        args = parser.parse_args(["install", "--path", "/path", "--dry-run"])
        assert args.dry_run is True

    def test_info_command_parses_plugin_name(self):
        """Test that info command parses plugin name."""
        parser = create_parser()

        args = parser.parse_args(["info", "my-plugin"])
        assert args.command == "info"
        assert args.plugin_name == "my-plugin"

    def test_uninstall_command_parses_plugin_name(self):
        """Test that uninstall command parses plugin name."""
        parser = create_parser()

        args = parser.parse_args(["uninstall", "my-plugin"])
        assert args.command == "uninstall"
        assert args.plugin_name == "my-plugin"

    def test_uninstall_command_parses_force_flag(self):
        """Test that uninstall command parses --force flag."""
        parser = create_parser()

        args = parser.parse_args(["uninstall", "my-plugin", "--force"])
        assert args.force is True


class TestListCommand:
    """Tests for the list command."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Reset plugin registry before each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    @pytest.fixture
    def mock_plugins(self):
        """Create mock plugin instances for testing."""
        mock_agent = MagicMock()
        mock_agent.name = "test-agent"
        mock_agent.version = "1.0.0"
        mock_agent.plugin_type = PluginType.AGENT
        mock_agent.is_enabled = True
        mock_agent.metadata.description = "Test agent plugin"

        mock_integration = MagicMock()
        mock_integration.name = "test-integration"
        mock_integration.version = "2.0.0"
        mock_integration.plugin_type = PluginType.INTEGRATION
        mock_integration.is_enabled = False
        mock_integration.metadata.description = "Test integration plugin"

        return [mock_agent, mock_integration]

    def test_list_all_plugins(self, mock_plugins, capsys):
        """Test listing all plugins without filters."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_registry = MagicMock()
            mock_registry.list_plugins.return_value = mock_plugins
            mock_get_instance.return_value = mock_registry

            args = MagicMock(type="all", enabled_only=False)
            result = cmd_list(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "test-agent" in captured.out
            assert "test-integration" in captured.out
            assert "Total: 2 plugin(s)" in captured.out

    def test_list_filters_by_type(self, mock_plugins, capsys):
        """Test listing plugins filtered by type."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_registry = MagicMock()
            # Return only agent plugins when filter is applied
            mock_registry.list_plugins.return_value = [mock_plugins[0]]
            mock_get_instance.return_value = mock_registry

            args = MagicMock(type="agent", enabled_only=False)
            result = cmd_list(args)

            assert result == 0

            # Verify registry was called with correct filter (may be called twice)
            calls = mock_registry.list_plugins.call_args_list
            # The final call should have the correct filter
            assert any(
                call[1] == {"plugin_type": PluginType.AGENT, "enabled_only": False}
                for call in calls
            ), f"Expected correct filter call, got: {calls}"

            captured = capsys.readouterr()
            assert "test-agent" in captured.out
            assert "Showing agent plugins only" in captured.out

    def test_list_filters_enabled_only(self, mock_plugins, capsys):
        """Test listing only enabled plugins."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_registry = MagicMock()
            # Return only enabled plugins
            mock_registry.list_plugins.return_value = [mock_plugins[0]]
            mock_get_instance.return_value = mock_registry

            args = MagicMock(type="all", enabled_only=True)
            result = cmd_list(args)

            assert result == 0

            # Verify registry was called with enabled_only=True (may be called twice)
            calls = mock_registry.list_plugins.call_args_list
            assert any(
                call[1] == {"plugin_type": None, "enabled_only": True}
                for call in calls
            ), f"Expected correct filter call, got: {calls}"

            captured = capsys.readouterr()
            assert "Showing enabled plugins only" in captured.out

    def test_list_no_plugins_found(self, capsys):
        """Test list command when no plugins are found."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_registry = MagicMock()
            mock_registry.list_plugins.return_value = []
            mock_get_instance.return_value = mock_registry

            args = MagicMock(type="all", enabled_only=False)
            result = cmd_list(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "No plugins found." in captured.out

    def test_list_loads_plugins_if_empty(self, mock_plugins):
        """Test that list command loads plugins if registry is empty."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_registry = MagicMock()
            # First call returns empty, second call returns plugins
            mock_registry.list_plugins.side_effect = [[], mock_plugins]
            mock_get_instance.return_value = mock_registry

            args = MagicMock(type="all", enabled_only=False)
            result = cmd_list(args)

            assert result == 0
            # Verify load_all_plugins was called
            mock_registry.load_all_plugins.assert_called_once()

    def test_list_handles_exception(self, caplog):
        """Test that list command handles exceptions gracefully."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_get_instance.side_effect = Exception("Registry error")

            args = MagicMock(type="all", enabled_only=False)
            result = cmd_list(args)

            assert result == 1
            # Check caplog for error message
            assert any("Failed to list plugins" in record.message for record in caplog.records)


class TestEnableCommand:
    """Tests for the enable command."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Reset plugin registry before each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    def test_enable_existing_plugin(self, capsys):
        """Test enabling an existing plugin."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_plugin = MagicMock()
            mock_plugin.name = "test-plugin"

            mock_registry = MagicMock()
            mock_registry.list_plugins.return_value = [mock_plugin]
            mock_registry.get_plugin.return_value = mock_plugin
            mock_get_instance.return_value = mock_registry

            args = MagicMock(plugin_name="test-plugin")
            result = cmd_enable(args)

            assert result == 0
            mock_registry.enable_plugin.assert_called_once_with("test-plugin")

            captured = capsys.readouterr()
            assert "Plugin 'test-plugin' enabled successfully" in captured.out

    def test_enable_nonexistent_plugin(self, caplog):
        """Test enabling a plugin that doesn't exist."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_registry = MagicMock()
            mock_registry.list_plugins.return_value = []
            mock_registry.get_plugin.return_value = None
            mock_get_instance.return_value = mock_registry

            args = MagicMock(plugin_name="nonexistent")
            result = cmd_enable(args)

            assert result == 1
            # Check caplog for error message
            assert any("Plugin not found: nonexistent" in record.message for record in caplog.records)

    def test_enable_loads_plugins_if_empty(self):
        """Test that enable command loads plugins if registry is empty."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_plugin = MagicMock()
            mock_registry = MagicMock()
            # First call returns empty, second call returns plugin
            mock_registry.list_plugins.side_effect = [[], [mock_plugin]]
            mock_registry.get_plugin.return_value = mock_plugin
            mock_get_instance.return_value = mock_registry

            args = MagicMock(plugin_name="test-plugin")
            result = cmd_enable(args)

            assert result == 0
            mock_registry.load_all_plugins.assert_called_once()

    def test_enable_handles_exception(self, caplog):
        """Test that enable command handles exceptions gracefully."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_registry = MagicMock()
            mock_registry.list_plugins.return_value = [MagicMock()]
            mock_registry.get_plugin.return_value = MagicMock()
            mock_registry.enable_plugin.side_effect = Exception("Enable error")
            mock_get_instance.return_value = mock_registry

            args = MagicMock(plugin_name="test-plugin")
            result = cmd_enable(args)

            assert result == 1
            # Check caplog for error message
            assert any("Failed to enable plugin" in record.message for record in caplog.records)


class TestDisableCommand:
    """Tests for the disable command."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Reset plugin registry before each test."""
        PluginRegistry.reset_instance()
        yield
        PluginRegistry.reset_instance()

    def test_disable_existing_plugin(self, capsys):
        """Test disabling an existing plugin."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_plugin = MagicMock()
            mock_plugin.name = "test-plugin"

            mock_registry = MagicMock()
            mock_registry.list_plugins.return_value = [mock_plugin]
            mock_registry.get_plugin.return_value = mock_plugin
            mock_get_instance.return_value = mock_registry

            args = MagicMock(plugin_name="test-plugin")
            result = cmd_disable(args)

            assert result == 0
            mock_registry.disable_plugin.assert_called_once_with("test-plugin")

            captured = capsys.readouterr()
            assert "Plugin 'test-plugin' disabled successfully" in captured.out

    def test_disable_nonexistent_plugin(self, caplog):
        """Test disabling a plugin that doesn't exist."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_registry = MagicMock()
            mock_registry.list_plugins.return_value = []
            mock_registry.get_plugin.return_value = None
            mock_get_instance.return_value = mock_registry

            args = MagicMock(plugin_name="nonexistent")
            result = cmd_disable(args)

            assert result == 1
            # Check caplog for error message
            assert any("Plugin not found: nonexistent" in record.message for record in caplog.records)

    def test_disable_handles_exception(self, caplog):
        """Test that disable command handles exceptions gracefully."""
        with patch("plugins.cli.PluginRegistry.get_instance") as mock_get_instance:
            mock_registry = MagicMock()
            mock_registry.list_plugins.return_value = [MagicMock()]
            mock_registry.get_plugin.return_value = MagicMock()
            mock_registry.disable_plugin.side_effect = Exception("Disable error")
            mock_get_instance.return_value = mock_registry

            args = MagicMock(plugin_name="test-plugin")
            result = cmd_disable(args)

            assert result == 1
            # Check caplog for error message
            assert any("Failed to disable plugin" in record.message for record in caplog.records)


class TestInstallCommand:
    """Tests for the install command."""

    @pytest.fixture
    def mock_plugin_dir(self, temp_dir):
        """Create a mock plugin directory for testing."""
        plugin_dir = temp_dir / "test-plugin"
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Create plugin.json manifest
        manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "author": "Test Author",
            "description": "Test plugin for CLI testing",
            "plugin_type": "agent",
            "auto_claude_version": ">=1.0.0",
            "required_permissions": [],
            "dependencies": [],
        }
        (plugin_dir / "plugin.json").write_text(json.dumps(manifest, indent=2))

        # Create plugin.py
        (plugin_dir / "plugin.py").write_text("# Test plugin code\n")

        return plugin_dir

    def test_install_from_path_success(self, mock_plugin_dir, temp_dir, capsys):
        """Test successful installation from local path."""
        user_plugins_dir = temp_dir / "user_plugins"
        user_plugins_dir.mkdir()

        with patch("plugins.cli.PluginLoader") as mock_loader_class:
            mock_loader = MagicMock()
            mock_metadata = MagicMock()
            mock_metadata.name = "test-plugin"
            mock_metadata.version = "1.0.0"
            mock_metadata.description = "Test plugin for CLI testing"

            mock_loader._load_metadata.return_value = mock_metadata
            mock_loader.validate_plugin_security.return_value = (True, [])
            mock_loader.user_plugins_dir = user_plugins_dir
            mock_loader_class.return_value = mock_loader

            args = MagicMock(
                path=str(mock_plugin_dir),
                url=None,
                force=False,
                dry_run=False,
            )
            result = cmd_install(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "installed successfully" in captured.out
            assert "test-plugin" in captured.out

    def test_install_from_path_dry_run(self, mock_plugin_dir, temp_dir, capsys):
        """Test dry-run mode for install command."""
        user_plugins_dir = temp_dir / "user_plugins"
        user_plugins_dir.mkdir()

        with patch("plugins.cli.PluginLoader") as mock_loader_class:
            mock_loader = MagicMock()
            mock_metadata = MagicMock()
            mock_metadata.name = "test-plugin"
            mock_metadata.version = "1.0.0"
            mock_metadata.description = "Test plugin"

            mock_loader._load_metadata.return_value = mock_metadata
            mock_loader.validate_plugin_security.return_value = (True, [])
            mock_loader.user_plugins_dir = user_plugins_dir
            mock_loader_class.return_value = mock_loader

            args = MagicMock(
                path=str(mock_plugin_dir),
                url=None,
                force=False,
                dry_run=True,
            )
            result = cmd_install(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "[DRY RUN]" in captured.out
            assert "Would install plugin" in captured.out

            # Verify plugin was NOT actually installed
            target_dir = user_plugins_dir / "test-plugin"
            assert not target_dir.exists()

    def test_install_from_path_with_security_warnings(self, mock_plugin_dir, temp_dir, capsys):
        """Test installation with security warnings (but not blocked)."""
        user_plugins_dir = temp_dir / "user_plugins"
        user_plugins_dir.mkdir()

        with patch("plugins.cli.PluginLoader") as mock_loader_class:
            mock_loader = MagicMock()
            mock_metadata = MagicMock()
            mock_metadata.name = "test-plugin"
            mock_metadata.version = "1.0.0"
            mock_metadata.description = "Test plugin"

            mock_loader._load_metadata.return_value = mock_metadata
            # Plugin is safe but has warnings
            mock_loader.validate_plugin_security.return_value = (
                True,
                ["Suspicious import detected: subprocess"]
            )
            mock_loader.user_plugins_dir = user_plugins_dir
            mock_loader_class.return_value = mock_loader

            args = MagicMock(
                path=str(mock_plugin_dir),
                url=None,
                force=False,
                dry_run=False,
            )
            result = cmd_install(args)

            assert result == 0
            captured = capsys.readouterr()
            assert "Security warnings detected" in captured.out
            assert "Suspicious import" in captured.out
            assert "installed successfully" in captured.out

    def test_install_from_path_security_blocked(self, mock_plugin_dir, temp_dir, caplog):
        """Test that installation is blocked when security validation fails."""
        user_plugins_dir = temp_dir / "user_plugins"
        user_plugins_dir.mkdir()

        with patch("plugins.cli.PluginLoader") as mock_loader_class:
            mock_loader = MagicMock()
            mock_metadata = MagicMock()
            mock_metadata.name = "test-plugin"
            mock_metadata.version = "1.0.0"

            mock_loader._load_metadata.return_value = mock_metadata
            # Plugin fails security validation
            mock_loader.validate_plugin_security.return_value = (
                False,
                ["Critical security issue: malicious code detected"]
            )
            mock_loader.user_plugins_dir = user_plugins_dir
            mock_loader_class.return_value = mock_loader

            args = MagicMock(
                path=str(mock_plugin_dir),
                url=None,
                force=False,
                dry_run=False,
            )
            result = cmd_install(args)

            assert result == 1
            # Check caplog for error message
            assert any("failed security validation" in record.message for record in caplog.records)

    def test_install_from_path_nonexistent(self, temp_dir, caplog):
        """Test installation from nonexistent path."""
        nonexistent_path = temp_dir / "nonexistent"

        args = MagicMock(
            path=str(nonexistent_path),
            url=None,
            force=False,
            dry_run=False,
        )
        result = cmd_install(args)

        assert result == 1
        # Check caplog for error message
        assert any("Source path not found" in record.message for record in caplog.records)

    def test_install_from_path_not_directory(self, temp_dir, caplog):
        """Test installation from a file instead of directory."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("not a plugin")

        args = MagicMock(
            path=str(file_path),
            url=None,
            force=False,
            dry_run=False,
        )
        result = cmd_install(args)

        assert result == 1
        # Check caplog for error message
        assert any("not a directory" in record.message for record in caplog.records)

    def test_install_from_path_force_overwrite(self, mock_plugin_dir, temp_dir, caplog, capsys):
        """Test force overwrite of existing plugin."""
        user_plugins_dir = temp_dir / "user_plugins"
        user_plugins_dir.mkdir()

        # Create existing plugin directory
        existing_plugin = user_plugins_dir / "test-plugin"
        existing_plugin.mkdir()
        (existing_plugin / "old_file.txt").write_text("old content")

        with patch("plugins.cli.PluginLoader") as mock_loader_class:
            mock_loader = MagicMock()
            mock_metadata = MagicMock()
            mock_metadata.name = "test-plugin"
            mock_metadata.version = "1.0.0"
            mock_metadata.description = "Test plugin"

            mock_loader._load_metadata.return_value = mock_metadata
            mock_loader.validate_plugin_security.return_value = (True, [])
            mock_loader.user_plugins_dir = user_plugins_dir
            mock_loader_class.return_value = mock_loader

            args = MagicMock(
                path=str(mock_plugin_dir),
                url=None,
                force=True,
                dry_run=False,
            )
            result = cmd_install(args)

            assert result == 0
            # Check caplog for warning message
            assert any("Removing existing plugin" in record.message for record in caplog.records)
            captured = capsys.readouterr()
            assert "installed successfully" in captured.out

    def test_install_from_path_without_force_fails(self, mock_plugin_dir, temp_dir, caplog):
        """Test that installation fails if plugin exists and --force is not used."""
        user_plugins_dir = temp_dir / "user_plugins"
        user_plugins_dir.mkdir()

        # Create existing plugin directory
        existing_plugin = user_plugins_dir / "test-plugin"
        existing_plugin.mkdir()

        with patch("plugins.cli.PluginLoader") as mock_loader_class:
            mock_loader = MagicMock()
            mock_metadata = MagicMock()
            mock_metadata.name = "test-plugin"
            mock_metadata.version = "1.0.0"

            mock_loader._load_metadata.return_value = mock_metadata
            mock_loader.validate_plugin_security.return_value = (True, [])
            mock_loader.user_plugins_dir = user_plugins_dir
            mock_loader_class.return_value = mock_loader

            args = MagicMock(
                path=str(mock_plugin_dir),
                url=None,
                force=False,
                dry_run=False,
            )
            result = cmd_install(args)

            assert result == 1
            # Check caplog for error message
            assert any("already installed" in record.message for record in caplog.records)
            assert any("--force" in record.message for record in caplog.records)

    def test_install_from_url_success(self, mock_plugin_dir, temp_dir, capsys):
        """Test successful installation from remote URL."""
        with patch("plugins.cli.run_git") as mock_run_git, \
             patch("plugins.cli._install_from_path") as mock_install_from_path:

            # Mock successful git clone
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run_git.return_value = mock_result

            # Mock successful installation
            mock_install_from_path.return_value = 0

            args = MagicMock(
                path=None,
                url="https://github.com/user/test-plugin.git",
                force=False,
                dry_run=False,
            )
            result = cmd_install(args)

            assert result == 0
            # Verify git clone was called
            mock_run_git.assert_called_once()
            # Verify _install_from_path was called with temp directory
            mock_install_from_path.assert_called_once()

    def test_install_from_url_clone_failure(self, caplog):
        """Test installation failure when git clone fails."""
        with patch("plugins.cli.run_git") as mock_run_git:
            # Mock failed git clone
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "fatal: repository not found"
            mock_run_git.return_value = mock_result

            args = MagicMock(
                path=None,
                url="https://github.com/user/nonexistent.git",
                force=False,
                dry_run=False,
            )
            result = cmd_install(args)

            assert result == 1
            # Check caplog for error message
            assert any("Failed to clone repository" in record.message for record in caplog.records)

    def test_install_from_path_invalid_manifest(self, temp_dir, caplog):
        """Test installation with invalid plugin.json manifest."""
        plugin_dir = temp_dir / "invalid-plugin"
        plugin_dir.mkdir()

        # Create invalid manifest (missing required fields)
        invalid_manifest = {"name": "test-plugin"}  # Missing required fields
        (plugin_dir / "plugin.json").write_text(json.dumps(invalid_manifest))

        with patch("plugins.cli.PluginLoader") as mock_loader_class:
            mock_loader = MagicMock()
            mock_loader._load_metadata.side_effect = PluginValidationError("Invalid manifest")
            mock_loader_class.return_value = mock_loader

            args = MagicMock(
                path=str(plugin_dir),
                url=None,
                force=False,
                dry_run=False,
            )
            result = cmd_install(args)

            assert result == 1
            # Check caplog for error message
            assert any("Invalid plugin" in record.message for record in caplog.records)


class TestInfoCommand:
    """Tests for the info command (placeholder)."""

    def test_info_command_placeholder(self, capsys):
        """Test that info command returns placeholder message."""
        args = MagicMock(plugin_name="test-plugin")
        result = cmd_info(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Info command" in captured.out
        assert "test-plugin" in captured.out


class TestUninstallCommand:
    """Tests for the uninstall command (placeholder)."""

    def test_uninstall_command_placeholder(self, capsys):
        """Test that uninstall command returns placeholder message."""
        args = MagicMock(plugin_name="test-plugin")
        result = cmd_uninstall(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Uninstall command" in captured.out
        assert "test-plugin" in captured.out


class TestMainFunction:
    """Tests for the main entry point."""

    def test_main_dispatches_list_command(self):
        """Test that main function dispatches to list command."""
        with patch("plugins.cli.cmd_list") as mock_cmd_list, \
             patch("sys.argv", ["cli.py", "list"]):
            mock_cmd_list.return_value = 0

            result = main()

            assert result == 0
            mock_cmd_list.assert_called_once()

    def test_main_dispatches_enable_command(self):
        """Test that main function dispatches to enable command."""
        with patch("plugins.cli.cmd_enable") as mock_cmd_enable, \
             patch("sys.argv", ["cli.py", "enable", "test-plugin"]):
            mock_cmd_enable.return_value = 0

            result = main()

            assert result == 0
            mock_cmd_enable.assert_called_once()

    def test_main_dispatches_disable_command(self):
        """Test that main function dispatches to disable command."""
        with patch("plugins.cli.cmd_disable") as mock_cmd_disable, \
             patch("sys.argv", ["cli.py", "disable", "test-plugin"]):
            mock_cmd_disable.return_value = 0

            result = main()

            assert result == 0
            mock_cmd_disable.assert_called_once()

    def test_main_dispatches_install_command(self):
        """Test that main function dispatches to install command."""
        with patch("plugins.cli.cmd_install") as mock_cmd_install, \
             patch("sys.argv", ["cli.py", "install", "--path", "/some/path"]):
            mock_cmd_install.return_value = 0

            result = main()

            assert result == 0
            mock_cmd_install.assert_called_once()

    def test_main_dispatches_info_command(self):
        """Test that main function dispatches to info command."""
        with patch("plugins.cli.cmd_info") as mock_cmd_info, \
             patch("sys.argv", ["cli.py", "info", "test-plugin"]):
            mock_cmd_info.return_value = 0

            result = main()

            assert result == 0
            mock_cmd_info.assert_called_once()

    def test_main_dispatches_uninstall_command(self):
        """Test that main function dispatches to uninstall command."""
        with patch("plugins.cli.cmd_uninstall") as mock_cmd_uninstall, \
             patch("sys.argv", ["cli.py", "uninstall", "test-plugin"]):
            mock_cmd_uninstall.return_value = 0

            result = main()

            assert result == 0
            mock_cmd_uninstall.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
