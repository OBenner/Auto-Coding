"""
Plugin Scaffolding Generator
=============================

Generates plugin scaffolding for new plugins.

This module provides utilities for creating new plugin projects with all
the necessary boilerplate code, configuration files, and documentation.

Example:
    ```python
    from plugins.sdk.scaffold import PluginScaffold

    # Create agent plugin
    scaffold = PluginScaffold()
    scaffold.generate(
        name="my-awesome-plugin",
        plugin_type="agent",
        author="Your Name",
        description="My awesome plugin",
        output_dir="./plugins/user/my-awesome-plugin"
    )

    # Create integration plugin with custom options
    scaffold.generate(
        name="slack-integration",
        plugin_type="integration",
        author="Your Name",
        description="Slack integration for Auto Code",
        output_dir="./plugins/user/slack-integration",
        permissions=["network_access", "access_secrets"],
        auto_claude_version=">=2.8.0",
        license="MIT"
    )
    ```
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..base import PluginType

logger = logging.getLogger(__name__)


class PluginScaffold:
    """
    Generates plugin scaffolding for new plugins.

    This class creates the directory structure and boilerplate files for
    a new plugin, including manifest, implementation, tests, and documentation.

    Generated structure:
        plugin-name/
            plugin.json      # Plugin manifest
            plugin.py        # Main implementation (or agent.py/integration.py/ui.py)
            README.md        # Documentation template
            test_plugin.py   # Optional test template
    """

    def __init__(self):
        """Initialize plugin scaffold generator."""
        logger.debug("PluginScaffold initialized")

    def generate(
        self,
        name: str,
        plugin_type: str | PluginType,
        author: str,
        description: str,
        output_dir: str | Path,
        version: str = "1.0.0",
        permissions: list[str] | None = None,
        dependencies: list[str] | None = None,
        homepage: str | None = None,
        license: str = "MIT",
        auto_claude_version: str | None = None,
        include_tests: bool = False,
    ) -> Path:
        """
        Generate plugin scaffolding.

        Args:
            name: Plugin name (e.g., "my-plugin")
            plugin_type: Plugin type ("agent", "integration", or "ui")
            author: Plugin author name
            description: Plugin description
            output_dir: Directory to create plugin in
            version: Plugin version (default: "1.0.0")
            permissions: List of required permissions (default: [])
            dependencies: List of plugin dependencies (default: [])
            homepage: Optional plugin homepage URL
            license: Plugin license (default: "MIT")
            auto_claude_version: Optional Auto Claude version requirement
            include_tests: Whether to generate test template (default: False)

        Returns:
            Path to generated plugin directory

        Raises:
            ValueError: If plugin_type is invalid or name contains invalid characters
            FileExistsError: If output directory already exists
        """
        # Validate inputs
        plugin_type = self._validate_plugin_type(plugin_type)
        self._validate_plugin_name(name)

        output_path = Path(output_dir)

        # Check if directory already exists
        if output_path.exists():
            raise FileExistsError(
                f"Plugin directory already exists: {output_path}. "
                f"Remove it or choose a different location."
            )

        logger.info(f"Generating {plugin_type.value} plugin '{name}' in {output_path}")

        # Create plugin directory
        output_path.mkdir(parents=True, exist_ok=False)

        # Generate manifest
        self._generate_manifest(
            output_path,
            name=name,
            version=version,
            author=author,
            description=description,
            plugin_type=plugin_type,
            permissions=permissions or [],
            dependencies=dependencies or [],
            homepage=homepage,
            license=license,
            auto_claude_version=auto_claude_version,
        )

        # Generate implementation
        self._generate_implementation(
            output_path,
            name=name,
            plugin_type=plugin_type,
            description=description,
        )

        # Generate README
        self._generate_readme(
            output_path,
            name=name,
            plugin_type=plugin_type,
            author=author,
            description=description,
            license=license,
        )

        # Generate tests if requested
        if include_tests:
            self._generate_tests(
                output_path,
                name=name,
                plugin_type=plugin_type,
            )

        logger.info(f"Plugin scaffolding generated successfully: {output_path}")
        return output_path

    def _validate_plugin_type(self, plugin_type: str | PluginType) -> PluginType:
        """
        Validate and convert plugin type.

        Args:
            plugin_type: Plugin type string or enum

        Returns:
            PluginType enum value

        Raises:
            ValueError: If plugin type is invalid
        """
        if isinstance(plugin_type, PluginType):
            return plugin_type

        try:
            return PluginType(plugin_type.lower())
        except ValueError:
            valid_types = [t.value for t in PluginType]
            raise ValueError(
                f"Invalid plugin type '{plugin_type}'. "
                f"Must be one of: {valid_types}"
            )

    def _validate_plugin_name(self, name: str) -> None:
        """
        Validate plugin name.

        Args:
            name: Plugin name to validate

        Raises:
            ValueError: If name is invalid
        """
        if not name:
            raise ValueError("Plugin name cannot be empty")

        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not all(c.isalnum() or c in ("-", "_") for c in name):
            raise ValueError(
                f"Invalid plugin name '{name}'. "
                f"Use only alphanumeric characters, hyphens, and underscores."
            )

        # Must start with alphanumeric
        if not name[0].isalnum():
            raise ValueError(
                f"Invalid plugin name '{name}'. "
                f"Must start with an alphanumeric character."
            )

    def _generate_manifest(
        self,
        output_path: Path,
        name: str,
        version: str,
        author: str,
        description: str,
        plugin_type: PluginType,
        permissions: list[str],
        dependencies: list[str],
        homepage: str | None,
        license: str,
        auto_claude_version: str | None,
    ) -> None:
        """Generate plugin.json manifest file."""
        manifest = {
            "name": name,
            "version": version,
            "author": author,
            "description": description,
            "plugin_type": plugin_type.value,
            "auto_claude_version": auto_claude_version or ">=1.0.0",
            "required_permissions": permissions,
            "dependencies": dependencies,
            "homepage": homepage,
            "license": license,
        }

        # Remove None values
        manifest = {k: v for k, v in manifest.items() if v is not None}

        manifest_path = output_path / "plugin.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        logger.debug(f"Generated manifest: {manifest_path}")

    def _generate_implementation(
        self,
        output_path: Path,
        name: str,
        plugin_type: PluginType,
        description: str,
    ) -> None:
        """Generate plugin implementation file."""
        if plugin_type == PluginType.AGENT:
            content = self._get_agent_template(name, description)
            filename = "agent.py"
        elif plugin_type == PluginType.INTEGRATION:
            content = self._get_integration_template(name, description)
            filename = "integration.py"
        else:  # UI
            content = self._get_ui_template(name, description)
            filename = "ui.py"

        impl_path = output_path / filename
        impl_path.write_text(content, encoding="utf-8")

        logger.debug(f"Generated implementation: {impl_path}")

    def _generate_readme(
        self,
        output_path: Path,
        name: str,
        plugin_type: PluginType,
        author: str,
        description: str,
        license: str,
    ) -> None:
        """Generate README.md documentation file."""
        content = self._get_readme_template(
            name=name,
            plugin_type=plugin_type,
            author=author,
            description=description,
            license=license,
        )

        readme_path = output_path / "README.md"
        readme_path.write_text(content, encoding="utf-8")

        logger.debug(f"Generated README: {readme_path}")

    def _generate_tests(
        self,
        output_path: Path,
        name: str,
        plugin_type: PluginType,
    ) -> None:
        """Generate test_plugin.py test template."""
        content = self._get_test_template(name, plugin_type)

        test_path = output_path / "test_plugin.py"
        test_path.write_text(content, encoding="utf-8")

        logger.debug(f"Generated tests: {test_path}")

    def _get_agent_template(self, name: str, description: str) -> str:
        """Get agent plugin implementation template."""
        class_name = self._to_class_name(name)
        return f'''"""
{description}

This is an agent plugin for Auto Code.
"""

import logging

from apps.backend.plugins.sdk.agent import AgentContext, AgentPlugin

logger = logging.getLogger(__name__)


class {class_name}(AgentPlugin):
    """
    {description}

    This plugin demonstrates:
    - Implementing lifecycle hooks (on_load, on_unload, on_enable, on_disable)
    - Using before_session and after_session hooks
    - Accessing context information (project_dir, spec_dir, etc.)
    """

    def __init__(self, metadata):
        """Initialize the {name} plugin."""
        super().__init__(metadata)
        logger.debug(f"{{self.name}}: Plugin instance created")

    def on_load(self) -> None:
        """
        Called when plugin is first loaded.

        Use this to validate configuration and initialize resources.
        """
        logger.info(f"{{self.name}}: Plugin loaded")

    def on_unload(self) -> None:
        """
        Called when plugin is being unloaded.

        Use this to clean up resources and save state.
        """
        logger.info(f"{{self.name}}: Plugin unloaded")

    def on_enable(self) -> None:
        """
        Called when plugin is enabled.

        Use this to register tools/services and start background tasks.
        """
        logger.info(f"{{self.name}}: Plugin enabled")

    def on_disable(self) -> None:
        """
        Called when plugin is disabled.

        Use this to unregister tools/services and stop background tasks.
        """
        logger.info(f"{{self.name}}: Plugin disabled")

    def before_session(self, context: AgentContext) -> None:
        """
        Called before an agent session starts.

        Args:
            context: Information about the current agent session
        """
        logger.info(
            f"{{self.name}}: Starting session for spec '{{context.spec_name}}' "
            f"in project '{{context.project_name}}'"
        )

    def after_session(self, context: AgentContext, success: bool) -> None:
        """
        Called after an agent session completes.

        Args:
            context: Information about the completed agent session
            success: True if session completed successfully
        """
        status = "succeeded" if success else "failed"
        logger.info(f"{{self.name}}: Session {{status}} for spec '{{context.spec_name}}'")

    def on_message(self, context: AgentContext, message: any) -> None:
        """
        Called when agent receives a message during a session.

        This is a monitoring/logging hook for analytics and debugging.

        Args:
            context: Information about the current agent session
            message: The message received from the Claude SDK
        """
        # Example: Log message type for debugging
        message_type = type(message).__name__
        logger.debug(f"{{self.name}}: Received message of type {{message_type}}")
'''

    def _get_integration_template(self, name: str, description: str) -> str:
        """Get integration plugin implementation template."""
        class_name = self._to_class_name(name)
        return f'''"""
{description}

This is an integration plugin for Auto Code.
"""

import logging

from apps.backend.plugins.sdk.integration import IntegrationPlugin

logger = logging.getLogger(__name__)


class {class_name}(IntegrationPlugin):
    """
    {description}

    This plugin demonstrates:
    - Implementing lifecycle hooks
    - Providing MCP tools to agents
    - Connecting to external services
    """

    def __init__(self, metadata):
        """Initialize the {name} plugin."""
        super().__init__(metadata)
        logger.debug(f"{{self.name}}: Plugin instance created")

    def on_load(self) -> None:
        """
        Called when plugin is first loaded.

        Use this to validate configuration and initialize resources.
        """
        logger.info(f"{{self.name}}: Plugin loaded")

    def on_unload(self) -> None:
        """
        Called when plugin is being unloaded.

        Use this to clean up resources and save state.
        """
        logger.info(f"{{self.name}}: Plugin unloaded")

    def on_enable(self) -> None:
        """
        Called when plugin is enabled.

        Use this to register MCP tools and connect to services.
        """
        logger.info(f"{{self.name}}: Plugin enabled")

        # TODO: Register MCP tools here
        # Example:
        # self.register_tool("my_tool", self.my_tool_handler)

    def on_disable(self) -> None:
        """
        Called when plugin is disabled.

        Use this to unregister tools and disconnect from services.
        """
        logger.info(f"{{self.name}}: Plugin disabled")

        # TODO: Unregister MCP tools here

    def get_mcp_tools(self) -> list[dict]:
        """
        Get MCP tools provided by this integration.

        Returns:
            List of MCP tool definitions
        """
        # TODO: Return your MCP tool definitions
        # Example:
        # return [
        #     {{
        #         "name": "my_tool",
        #         "description": "Does something useful",
        #         "parameters": {{
        #             "type": "object",
        #             "properties": {{
        #                 "param1": {{
        #                     "type": "string",
        #                     "description": "First parameter"
        #                 }}
        #             }},
        #             "required": ["param1"]
        #         }}
        #     }}
        # ]
        return []
'''

    def _get_ui_template(self, name: str, description: str) -> str:
        """Get UI plugin implementation template."""
        class_name = self._to_class_name(name)
        return f'''"""
{description}

This is a UI plugin for Auto Code.
"""

import logging

from apps.backend.plugins.sdk.ui import UIPlugin

logger = logging.getLogger(__name__)


class {class_name}(UIPlugin):
    """
    {description}

    This plugin demonstrates:
    - Implementing lifecycle hooks
    - Providing UI components/extensions
    - Communicating with frontend
    """

    def __init__(self, metadata):
        """Initialize the {name} plugin."""
        super().__init__(metadata)
        logger.debug(f"{{self.name}}: Plugin instance created")

    def on_load(self) -> None:
        """
        Called when plugin is first loaded.

        Use this to validate configuration and initialize resources.
        """
        logger.info(f"{{self.name}}: Plugin loaded")

    def on_unload(self) -> None:
        """
        Called when plugin is being unloaded.

        Use this to clean up resources and save state.
        """
        logger.info(f"{{self.name}}: Plugin unloaded")

    def on_enable(self) -> None:
        """
        Called when plugin is enabled.

        Use this to register UI components.
        """
        logger.info(f"{{self.name}}: Plugin enabled")

        # TODO: Register UI components here

    def on_disable(self) -> None:
        """
        Called when plugin is disabled.

        Use this to unregister UI components.
        """
        logger.info(f"{{self.name}}: Plugin disabled")

        # TODO: Unregister UI components here

    def get_ui_components(self) -> dict:
        """
        Get UI components provided by this plugin.

        Returns:
            Dictionary of UI component definitions
        """
        # TODO: Return your UI component definitions
        # Example:
        # return {{
        #     "toolbar_buttons": [
        #         {{
        #             "id": "my-button",
        #             "label": "My Button",
        #             "icon": "icon-name",
        #             "action": "my_action"
        #         }}
        #     ]
        # }}
        return {{}}
'''

    def _get_readme_template(
        self,
        name: str,
        plugin_type: PluginType,
        author: str,
        description: str,
        license: str,
    ) -> str:
        """Get README.md template."""
        return f'''# {name}

{description}

## Type

{plugin_type.value.capitalize()} Plugin

## Author

{author}

## Description

{description}

## Installation

1. Copy this plugin directory to your Auto Code plugins folder:
   ```
   .auto-claude/plugins/user/{name}/
   ```

2. Enable the plugin in Auto Code settings

## Configuration

<!-- Document any environment variables or configuration needed -->

## Usage

<!-- Provide examples of how to use this plugin -->

## Development

### Testing

```bash
pytest test_plugin.py -v
```

### Debugging

Enable debug logging to see plugin activity:

```python
import logging
logging.getLogger("{name}").setLevel(logging.DEBUG)
```

## License

{license}
'''

    def _get_test_template(self, name: str, plugin_type: PluginType) -> str:
        """Get test_plugin.py template."""
        class_name = self._to_class_name(name)

        if plugin_type == PluginType.AGENT:
            module_name = "agent"
            context_import = "from apps.backend.plugins.sdk.testing import MockAgentContext"
            context_usage = "context = MockAgentContext()"
        elif plugin_type == PluginType.INTEGRATION:
            module_name = "integration"
            context_import = "from apps.backend.plugins.sdk.testing import MockIntegrationContext"
            context_usage = "context = MockIntegrationContext()"
        else:  # UI
            module_name = "ui"
            context_import = ""
            context_usage = ""

        return f'''"""
Tests for {name} plugin.

This module tests the {name} plugin implementation.
"""

import pytest

from apps.backend.plugins.base import PluginMetadata, PluginType
{context_import}

from {module_name} import {class_name}


@pytest.fixture
def plugin():
    """Create plugin instance for testing."""
    metadata = PluginMetadata(
        name="{name}",
        version="1.0.0",
        author="Test Author",
        description="Test plugin",
        plugin_type=PluginType.{plugin_type.name},
        required_permissions=[],
    )
    return {class_name}(metadata)


def test_plugin_initialization(plugin):
    """Test that plugin initializes correctly."""
    assert plugin.name == "{name}"
    assert plugin.version == "1.0.0"
    assert plugin.plugin_type == PluginType.{plugin_type.name}
    assert not plugin.is_loaded
    assert not plugin.is_enabled


def test_plugin_load_unload(plugin):
    """Test plugin load/unload lifecycle."""
    plugin.on_load()
    plugin._mark_loaded()
    assert plugin.is_loaded

    plugin.on_unload()
    plugin._mark_unloaded()
    assert not plugin.is_loaded


def test_plugin_enable_disable(plugin):
    """Test plugin enable/disable lifecycle."""
    plugin.on_enable()
    plugin._mark_enabled()
    assert plugin.is_enabled

    plugin.on_disable()
    plugin._mark_disabled()
    assert not plugin.is_enabled


{self._get_test_type_specific(plugin_type, context_usage)}
'''

    def _get_test_type_specific(self, plugin_type: PluginType, context_usage: str) -> str:
        """Get type-specific test methods."""
        if plugin_type == PluginType.AGENT:
            return f'''
def test_plugin_session_hooks(plugin):
    """Test agent session lifecycle hooks."""
    {context_usage}

    # Test before_session
    plugin.before_session(context)

    # Test after_session
    plugin.after_session(context, success=True)
    plugin.after_session(context, success=False)

    # Test on_message
    plugin.on_message(context, {{"type": "test"}})
'''
        elif plugin_type == PluginType.INTEGRATION:
            return f'''
def test_plugin_mcp_tools(plugin):
    """Test MCP tools provided by integration."""
    tools = plugin.get_mcp_tools()
    assert isinstance(tools, list)
    # Add assertions for your specific tools
'''
        else:  # UI
            return f'''
def test_plugin_ui_components(plugin):
    """Test UI components provided by plugin."""
    components = plugin.get_ui_components()
    assert isinstance(components, dict)
    # Add assertions for your specific components
'''

    def _to_class_name(self, name: str) -> str:
        """
        Convert plugin name to Python class name.

        Examples:
            "my-plugin" -> "MyPlugin"
            "slack-integration" -> "SlackIntegration"
            "hello_world" -> "HelloWorld"

        Args:
            name: Plugin name

        Returns:
            Python class name
        """
        # Replace hyphens and underscores with spaces, then title case
        parts = name.replace("-", " ").replace("_", " ").split()
        class_name = "".join(word.capitalize() for word in parts)

        # Add "Plugin" suffix if not already there
        if not class_name.endswith("Plugin"):
            class_name += "Plugin"

        return class_name
