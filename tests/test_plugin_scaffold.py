#!/usr/bin/env python3
"""
Tests for Plugin Scaffolding Generator
======================================

Tests the plugins/sdk/scaffold.py module functionality including:
- Plugin generation for different types (agent, integration, ui)
- Input validation (plugin name, type)
- File generation (manifest, implementation, README, tests)
- Directory handling and error cases
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from apps.backend.plugins.base import PluginType
from apps.backend.plugins.sdk.scaffold import PluginScaffold


@pytest.fixture
def temp_dir():
    """Create temporary directory for test plugins."""
    tmpdir = Path(tempfile.mkdtemp())
    yield tmpdir
    # Cleanup
    if tmpdir.exists():
        shutil.rmtree(tmpdir)


@pytest.fixture
def scaffold():
    """Create PluginScaffold instance."""
    return PluginScaffold()


class TestPluginScaffoldInitialization:
    """Tests for PluginScaffold initialization."""

    def test_initialization(self):
        """PluginScaffold initializes correctly."""
        scaffold = PluginScaffold()
        assert scaffold is not None


class TestPluginNameValidation:
    """Tests for plugin name validation."""

    def test_valid_names(self, scaffold, temp_dir):
        """Accepts valid plugin names."""
        valid_names = [
            "my-plugin",
            "MyPlugin",
            "my_plugin",
            "plugin123",
            "123plugin",
            "a",
            "plugin-with-many-hyphens",
            "plugin_with_underscores",
        ]

        for i, name in enumerate(valid_names):
            output_dir = temp_dir / f"test_{i}"
            result = scaffold.generate(
                name=name,
                plugin_type="agent",
                author="Test",
                description="Test plugin",
                output_dir=output_dir,
            )
            assert result.exists()

    def test_empty_name(self, scaffold, temp_dir):
        """Rejects empty plugin name."""
        with pytest.raises(ValueError, match="Plugin name cannot be empty"):
            scaffold.generate(
                name="",
                plugin_type="agent",
                author="Test",
                description="Test",
                output_dir=temp_dir / "test",
            )

    def test_invalid_characters(self, scaffold, temp_dir):
        """Rejects names with invalid characters."""
        invalid_names = [
            "my plugin",  # space
            "my@plugin",  # special char
            "my.plugin",  # dot
            "my/plugin",  # slash
            "my\\plugin",  # backslash
            "my:plugin",  # colon
        ]

        for name in invalid_names:
            with pytest.raises(ValueError, match="Invalid plugin name"):
                scaffold.generate(
                    name=name,
                    plugin_type="agent",
                    author="Test",
                    description="Test",
                    output_dir=temp_dir / "test",
                )

    def test_name_starting_with_special_char(self, scaffold, temp_dir):
        """Rejects names starting with non-alphanumeric."""
        invalid_names = ["-plugin", "_plugin"]

        for name in invalid_names:
            with pytest.raises(ValueError, match="Must start with an alphanumeric"):
                scaffold.generate(
                    name=name,
                    plugin_type="agent",
                    author="Test",
                    description="Test",
                    output_dir=temp_dir / "test",
                )


class TestPluginTypeValidation:
    """Tests for plugin type validation."""

    def test_valid_types_as_string(self, scaffold, temp_dir):
        """Accepts valid plugin type strings."""
        types = ["agent", "integration", "ui"]

        for plugin_type in types:
            output_dir = temp_dir / plugin_type
            result = scaffold.generate(
                name=f"test-{plugin_type}",
                plugin_type=plugin_type,
                author="Test",
                description="Test plugin",
                output_dir=output_dir,
            )
            assert result.exists()

    def test_valid_types_as_enum(self, scaffold, temp_dir):
        """Accepts PluginType enum values."""
        types = [PluginType.AGENT, PluginType.INTEGRATION, PluginType.UI]

        for plugin_type in types:
            output_dir = temp_dir / plugin_type.value
            result = scaffold.generate(
                name=f"test-{plugin_type.value}",
                plugin_type=plugin_type,
                author="Test",
                description="Test plugin",
                output_dir=output_dir,
            )
            assert result.exists()

    def test_invalid_type(self, scaffold, temp_dir):
        """Rejects invalid plugin type."""
        with pytest.raises(ValueError, match="Invalid plugin type"):
            scaffold.generate(
                name="test",
                plugin_type="invalid",
                author="Test",
                description="Test",
                output_dir=temp_dir / "test",
            )

    def test_case_insensitive_type(self, scaffold, temp_dir):
        """Accepts case-insensitive plugin types."""
        types = ["AGENT", "Agent", "InTeGrAtIoN"]

        for i, plugin_type in enumerate(types):
            output_dir = temp_dir / f"test_{i}"
            result = scaffold.generate(
                name=f"test-{i}",
                plugin_type=plugin_type,
                author="Test",
                description="Test plugin",
                output_dir=output_dir,
            )
            assert result.exists()


class TestDirectoryHandling:
    """Tests for directory creation and error handling."""

    def test_creates_directory(self, scaffold, temp_dir):
        """Creates plugin directory."""
        output_dir = temp_dir / "my-plugin"
        assert not output_dir.exists()

        scaffold.generate(
            name="my-plugin",
            plugin_type="agent",
            author="Test",
            description="Test plugin",
            output_dir=output_dir,
        )

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_creates_parent_directories(self, scaffold, temp_dir):
        """Creates parent directories if needed."""
        output_dir = temp_dir / "nested" / "path" / "my-plugin"
        assert not output_dir.exists()

        scaffold.generate(
            name="my-plugin",
            plugin_type="agent",
            author="Test",
            description="Test plugin",
            output_dir=output_dir,
        )

        assert output_dir.exists()

    def test_fails_if_directory_exists(self, scaffold, temp_dir):
        """Raises FileExistsError if directory exists."""
        output_dir = temp_dir / "existing"
        output_dir.mkdir()

        with pytest.raises(FileExistsError, match="already exists"):
            scaffold.generate(
                name="test",
                plugin_type="agent",
                author="Test",
                description="Test",
                output_dir=output_dir,
            )


class TestManifestGeneration:
    """Tests for plugin.json manifest generation."""

    def test_manifest_created(self, scaffold, temp_dir):
        """Generates plugin.json file."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test-plugin",
            plugin_type="agent",
            author="Test Author",
            description="Test description",
            output_dir=output_dir,
        )

        manifest_path = output_dir / "plugin.json"
        assert manifest_path.exists()

    def test_manifest_required_fields(self, scaffold, temp_dir):
        """Manifest contains all required fields."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test-plugin",
            plugin_type="agent",
            author="Test Author",
            description="Test description",
            output_dir=output_dir,
        )

        with open(output_dir / "plugin.json") as f:
            manifest = json.load(f)

        assert manifest["name"] == "test-plugin"
        assert manifest["version"] == "1.0.0"
        assert manifest["author"] == "Test Author"
        assert manifest["description"] == "Test description"
        assert manifest["plugin_type"] == "agent"

    def test_manifest_custom_version(self, scaffold, temp_dir):
        """Manifest uses custom version."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test",
            plugin_type="agent",
            author="Test",
            description="Test",
            output_dir=output_dir,
            version="2.5.3",
        )

        with open(output_dir / "plugin.json") as f:
            manifest = json.load(f)

        assert manifest["version"] == "2.5.3"

    def test_manifest_with_permissions(self, scaffold, temp_dir):
        """Manifest includes permissions."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test",
            plugin_type="agent",
            author="Test",
            description="Test",
            output_dir=output_dir,
            permissions=["network_access", "access_secrets"],
        )

        with open(output_dir / "plugin.json") as f:
            manifest = json.load(f)

        assert manifest["required_permissions"] == ["network_access", "access_secrets"]

    def test_manifest_with_dependencies(self, scaffold, temp_dir):
        """Manifest includes dependencies."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test",
            plugin_type="agent",
            author="Test",
            description="Test",
            output_dir=output_dir,
            dependencies=["dep1", "dep2"],
        )

        with open(output_dir / "plugin.json") as f:
            manifest = json.load(f)

        assert manifest["dependencies"] == ["dep1", "dep2"]

    def test_manifest_with_all_optional_fields(self, scaffold, temp_dir):
        """Manifest includes all optional fields."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test",
            plugin_type="agent",
            author="Test",
            description="Test",
            output_dir=output_dir,
            homepage="https://example.com",
            license="Apache-2.0",
            auto_claude_version=">=2.8.0",
        )

        with open(output_dir / "plugin.json") as f:
            manifest = json.load(f)

        assert manifest["homepage"] == "https://example.com"
        assert manifest["license"] == "Apache-2.0"
        assert manifest["auto_claude_version"] == ">=2.8.0"


class TestImplementationGeneration:
    """Tests for implementation file generation."""

    def test_agent_implementation(self, scaffold, temp_dir):
        """Generates agent.py for agent plugin."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test-plugin",
            plugin_type="agent",
            author="Test",
            description="Test description",
            output_dir=output_dir,
        )

        impl_path = output_dir / "agent.py"
        assert impl_path.exists()

        content = impl_path.read_text()
        assert "AgentPlugin" in content
        assert "AgentContext" in content
        assert "before_session" in content
        assert "after_session" in content

    def test_integration_implementation(self, scaffold, temp_dir):
        """Generates integration.py for integration plugin."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test-plugin",
            plugin_type="integration",
            author="Test",
            description="Test description",
            output_dir=output_dir,
        )

        impl_path = output_dir / "integration.py"
        assert impl_path.exists()

        content = impl_path.read_text()
        assert "IntegrationPlugin" in content
        assert "get_mcp_tools" in content

    def test_ui_implementation(self, scaffold, temp_dir):
        """Generates ui.py for UI plugin."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test-plugin",
            plugin_type="ui",
            author="Test",
            description="Test description",
            output_dir=output_dir,
        )

        impl_path = output_dir / "ui.py"
        assert impl_path.exists()

        content = impl_path.read_text()
        assert "UIPlugin" in content
        assert "get_ui_components" in content

    def test_implementation_class_name(self, scaffold, temp_dir):
        """Implementation uses correct class name."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="my-awesome-plugin",
            plugin_type="agent",
            author="Test",
            description="Test",
            output_dir=output_dir,
        )

        content = (output_dir / "agent.py").read_text()
        assert "class MyAwesomePlugin(AgentPlugin):" in content


class TestReadmeGeneration:
    """Tests for README.md generation."""

    def test_readme_created(self, scaffold, temp_dir):
        """Generates README.md file."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test-plugin",
            plugin_type="agent",
            author="Test Author",
            description="Test description",
            output_dir=output_dir,
        )

        readme_path = output_dir / "README.md"
        assert readme_path.exists()

    def test_readme_contains_plugin_info(self, scaffold, temp_dir):
        """README contains plugin information."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="my-plugin",
            plugin_type="agent",
            author="John Doe",
            description="A great plugin",
            output_dir=output_dir,
            license="Apache-2.0",
        )

        content = (output_dir / "README.md").read_text()
        assert "my-plugin" in content
        assert "John Doe" in content
        assert "A great plugin" in content
        assert "Apache-2.0" in content


class TestTestGeneration:
    """Tests for test file generation."""

    def test_no_tests_by_default(self, scaffold, temp_dir):
        """Does not generate tests by default."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test",
            plugin_type="agent",
            author="Test",
            description="Test",
            output_dir=output_dir,
        )

        assert not (output_dir / "test_plugin.py").exists()

    def test_generates_tests_when_requested(self, scaffold, temp_dir):
        """Generates test_plugin.py when include_tests=True."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test",
            plugin_type="agent",
            author="Test",
            description="Test",
            output_dir=output_dir,
            include_tests=True,
        )

        test_path = output_dir / "test_plugin.py"
        assert test_path.exists()

    def test_agent_test_template(self, scaffold, temp_dir):
        """Agent test template includes session hooks."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test",
            plugin_type="agent",
            author="Test",
            description="Test",
            output_dir=output_dir,
            include_tests=True,
        )

        content = (output_dir / "test_plugin.py").read_text()
        assert "MockAgentContext" in content
        assert "before_session" in content
        assert "after_session" in content

    def test_integration_test_template(self, scaffold, temp_dir):
        """Integration test template includes MCP tools."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test",
            plugin_type="integration",
            author="Test",
            description="Test",
            output_dir=output_dir,
            include_tests=True,
        )

        content = (output_dir / "test_plugin.py").read_text()
        assert "get_mcp_tools" in content

    def test_ui_test_template(self, scaffold, temp_dir):
        """UI test template includes UI components."""
        output_dir = temp_dir / "test"
        scaffold.generate(
            name="test",
            plugin_type="ui",
            author="Test",
            description="Test",
            output_dir=output_dir,
            include_tests=True,
        )

        content = (output_dir / "test_plugin.py").read_text()
        assert "get_ui_components" in content


class TestClassNameConversion:
    """Tests for _to_class_name helper."""

    def test_hyphenated_name(self, scaffold):
        """Converts hyphenated names to PascalCase."""
        assert scaffold._to_class_name("my-plugin") == "MyPlugin"
        assert scaffold._to_class_name("slack-integration") == "SlackIntegrationPlugin"

    def test_underscored_name(self, scaffold):
        """Converts underscored names to PascalCase."""
        assert scaffold._to_class_name("my_plugin") == "MyPlugin"
        assert scaffold._to_class_name("hello_world") == "HelloWorldPlugin"

    def test_mixed_name(self, scaffold):
        """Converts mixed names to PascalCase."""
        assert scaffold._to_class_name("my-awesome_plugin") == "MyAwesomePlugin"

    def test_single_word(self, scaffold):
        """Handles single word names."""
        assert scaffold._to_class_name("test") == "TestPlugin"

    def test_already_has_plugin_suffix(self, scaffold):
        """Does not duplicate 'Plugin' suffix."""
        class_name = scaffold._to_class_name("my-plugin")
        assert class_name.count("Plugin") == 1


class TestFullGeneration:
    """Integration tests for full plugin generation."""

    def test_complete_agent_plugin(self, scaffold, temp_dir):
        """Generates complete agent plugin structure."""
        output_dir = temp_dir / "my-agent"
        result = scaffold.generate(
            name="my-agent",
            plugin_type="agent",
            author="Test Author",
            description="My test agent",
            output_dir=output_dir,
            version="1.2.3",
            permissions=["network_access"],
            homepage="https://example.com",
            license="MIT",
            include_tests=True,
        )

        # Check return value
        assert result == output_dir

        # Check all files created
        assert (output_dir / "plugin.json").exists()
        assert (output_dir / "agent.py").exists()
        assert (output_dir / "README.md").exists()
        assert (output_dir / "test_plugin.py").exists()

        # Verify manifest
        with open(output_dir / "plugin.json") as f:
            manifest = json.load(f)
        assert manifest["name"] == "my-agent"
        assert manifest["version"] == "1.2.3"
        assert manifest["plugin_type"] == "agent"

    def test_minimal_plugin(self, scaffold, temp_dir):
        """Generates plugin with minimal configuration."""
        output_dir = temp_dir / "minimal"
        scaffold.generate(
            name="minimal",
            plugin_type="agent",
            author="Test",
            description="Minimal plugin",
            output_dir=output_dir,
        )

        # Essential files should exist
        assert (output_dir / "plugin.json").exists()
        assert (output_dir / "agent.py").exists()
        assert (output_dir / "README.md").exists()

        # Optional test file should not exist
        assert not (output_dir / "test_plugin.py").exists()
