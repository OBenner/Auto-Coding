"""
Plugin Documentation Generator
===============================

Generates markdown documentation for plugins.

This module provides utilities for automatically generating README.md files
for plugins based on their metadata, implementation, and docstrings.

Example:
    ```python
    from plugins.sdk.docs_generator import PluginDocsGenerator

    # Generate documentation for a plugin
    generator = PluginDocsGenerator()
    docs = generator.generate_docs(Path("./plugins/user/my-plugin"))
    print(docs)

    # Save documentation to README.md
    generator.generate_and_save(
        plugin_dir=Path("./plugins/user/my-plugin"),
        output_file="README.md"
    )
    ```
"""

from __future__ import annotations

import ast
import json
import logging
from pathlib import Path
from typing import Any

from ..base import PluginType

logger = logging.getLogger(__name__)

# Import debug utilities - wrapped with source module name for CodeQL compliance
_SOURCE = "plugins.sdk.docs_generator"
try:
    from debug import (
        debug as _raw_debug,
    )
    from debug import (
        debug_error as _raw_debug_error,
    )
    from debug import (
        debug_success as _raw_debug_success,
    )
    from debug import (
        debug_verbose as _raw_debug_verbose,
    )
    from debug import (
        debug_warning as _raw_debug_warning,
    )
except ImportError:

    def _raw_debug(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_error(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_success(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_verbose(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""

    def _raw_debug_warning(*_args, **_kwargs):
        """No-op fallback when debug module is unavailable."""


def _debug(msg: str, **kwargs) -> None:
    """Debug log with source module."""
    _raw_debug(_SOURCE, msg, **kwargs)


def _debug_verbose(msg: str, **kwargs) -> None:
    """Verbose debug log with source module."""
    _raw_debug_verbose(_SOURCE, msg, **kwargs)


def _debug_success(msg: str, **kwargs) -> None:
    """Success debug log with source module."""
    _raw_debug_success(_SOURCE, msg, **kwargs)


def _debug_error(msg: str, **kwargs) -> None:
    """Error debug log with source module."""
    _raw_debug_error(_SOURCE, msg, **kwargs)


def _debug_warning(msg: str, **kwargs) -> None:
    """Warning debug log with source module."""
    _raw_debug_warning(_SOURCE, msg, **kwargs)


class PluginDocsGenerator:
    """
    Generates markdown documentation for plugins.

    This class analyzes plugin metadata and implementation to create
    comprehensive README.md files with installation instructions, usage
    examples, configuration details, and troubleshooting guides.

    Generated documentation includes:
    - Overview and description
    - Plugin type and metadata
    - Features and capabilities
    - Installation instructions
    - Configuration and permissions
    - Usage examples
    - Development guide
    - Troubleshooting section

    Example:
        >>> generator = PluginDocsGenerator()
        >>> docs = generator.generate_docs(Path("./plugins/user/my-plugin"))
        >>> print(docs)
    """

    def __init__(self):
        """Initialize documentation generator."""
        logger.debug("PluginDocsGenerator initialized")

    def generate_docs(self, plugin_dir: Path) -> str:
        """
        Generate markdown documentation for a plugin.

        Args:
            plugin_dir: Path to plugin directory

        Returns:
            Markdown documentation string

        Raises:
            FileNotFoundError: If plugin directory or manifest not found
            ValueError: If manifest is invalid
        """
        _debug(f"Generating documentation for plugin: {plugin_dir}")

        # Validate plugin directory
        if not plugin_dir.exists():
            raise FileNotFoundError(f"Plugin directory not found: {plugin_dir}")

        if not plugin_dir.is_dir():
            raise ValueError(f"Path is not a directory: {plugin_dir}")

        # Load and parse manifest
        manifest = self._load_manifest(plugin_dir)

        # Extract implementation details
        impl_info = self._extract_implementation_info(plugin_dir, manifest)

        # Generate documentation sections
        sections = [
            self._generate_header(manifest),
            self._generate_overview(manifest, impl_info),
            self._generate_features(manifest, impl_info),
            self._generate_installation(manifest),
            self._generate_usage(manifest, impl_info),
            self._generate_configuration(manifest),
            self._generate_permissions(manifest),
            self._generate_development(manifest, plugin_dir),
            self._generate_troubleshooting(manifest),
            self._generate_footer(manifest),
        ]

        # Combine sections
        docs = "\n\n".join(section for section in sections if section)

        _debug_success(f"Generated {len(docs)} characters of documentation")
        return docs

    def generate_and_save(
        self,
        plugin_dir: Path,
        output_file: str | Path = "README.md",
        overwrite: bool = False,
    ) -> Path:
        """
        Generate documentation and save to file.

        Args:
            plugin_dir: Path to plugin directory
            output_file: Output filename (default: README.md)
            overwrite: Overwrite existing file (default: False)

        Returns:
            Path to generated documentation file

        Raises:
            FileExistsError: If output file exists and overwrite is False
            FileNotFoundError: If plugin directory not found
            ValueError: If manifest is invalid
        """
        output_path = plugin_dir / output_file

        if output_path.exists() and not overwrite:
            raise FileExistsError(
                f"Documentation file already exists: {output_path}. "
                f"Use overwrite=True to replace it."
            )

        docs = self.generate_docs(plugin_dir)
        output_path.write_text(docs, encoding="utf-8")

        _debug_success(f"Documentation saved to: {output_path}")
        return output_path

    def _load_manifest(self, plugin_dir: Path) -> dict[str, Any]:
        """Load and parse plugin.json manifest."""
        manifest_path = plugin_dir / "plugin.json"

        if not manifest_path.exists():
            raise FileNotFoundError(
                f"Plugin manifest not found: {manifest_path}"
            )

        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            _debug_verbose(f"Loaded manifest: {manifest.get('name', 'unknown')}")
            return manifest
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in plugin.json: {e}")
        except Exception as e:
            raise ValueError(f"Failed to read plugin.json: {e}")

    def _extract_implementation_info(
        self,
        plugin_dir: Path,
        manifest: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract information from plugin implementation file."""
        info = {
            "class_name": None,
            "class_docstring": None,
            "methods": [],
            "has_hooks": False,
        }

        # Determine implementation file
        plugin_type = manifest.get("plugin_type", "agent")
        if plugin_type == "agent":
            impl_file = "agent.py"
        elif plugin_type == "integration":
            impl_file = "integration.py"
        elif plugin_type == "ui":
            impl_file = "ui.py"
        else:
            impl_file = "plugin.py"

        impl_path = plugin_dir / impl_file

        # Check fallback files
        if not impl_path.exists():
            for fallback in ["plugin.py", "__init__.py"]:
                fallback_path = plugin_dir / fallback
                if fallback_path.exists():
                    impl_path = fallback_path
                    break

        if not impl_path.exists():
            _debug_warning(f"Implementation file not found: {impl_file}")
            return info

        # Parse implementation file
        try:
            with open(impl_path, encoding="utf-8") as f:
                code = f.read()

            tree = ast.parse(code)

            # Find plugin class and extract info
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Look for plugin class (ends with Plugin or inherits from plugin base)
                    if node.name.endswith("Plugin") or self._is_plugin_class(node):
                        info["class_name"] = node.name
                        info["class_docstring"] = ast.get_docstring(node)

                        # Extract method names
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                info["methods"].append(item.name)

                        # Check for lifecycle hooks
                        hook_methods = {
                            "on_load",
                            "on_unload",
                            "on_enable",
                            "on_disable",
                        }
                        info["has_hooks"] = bool(hook_methods & set(info["methods"]))

                        break

            _debug_verbose(f"Extracted implementation info: class={info['class_name']}")

        except Exception as e:
            _debug_error(f"Failed to parse implementation file: {e}")

        return info

    def _is_plugin_class(self, node: ast.ClassDef) -> bool:
        """Check if AST node is a plugin class."""
        for base in node.bases:
            if isinstance(base, ast.Name):
                if "Plugin" in base.id:
                    return True
        return False

    def _generate_header(self, manifest: dict[str, Any]) -> str:
        """Generate document header."""
        name = manifest.get("name", "Unknown Plugin")
        description = manifest.get("description", "")

        header = f"# {name}\n\n{description}"
        return header

    def _generate_overview(
        self,
        manifest: dict[str, Any],
        impl_info: dict[str, Any],
    ) -> str:
        """Generate overview section."""
        plugin_type = manifest.get("plugin_type", "agent")
        version = manifest.get("version", "1.0.0")
        author = manifest.get("author", "Unknown")

        overview = "## Overview\n\n"
        overview += f"**Type:** {plugin_type.capitalize()} Plugin\n\n"
        overview += f"**Version:** {version}\n\n"
        overview += f"**Author:** {author}\n\n"

        if manifest.get("homepage"):
            overview += f"**Homepage:** {manifest['homepage']}\n\n"

        if manifest.get("license"):
            overview += f"**License:** {manifest['license']}\n\n"

        if impl_info.get("class_docstring"):
            overview += f"{impl_info['class_docstring']}\n"

        return overview

    def _generate_features(
        self,
        manifest: dict[str, Any],
        impl_info: dict[str, Any],
    ) -> str:
        """Generate features section."""
        features = "## Features\n\n"

        plugin_type = manifest.get("plugin_type", "agent")

        if plugin_type == "agent":
            if impl_info.get("has_hooks"):
                features += "### Lifecycle Hooks\n\n"
                features += "This plugin implements lifecycle hooks:\n\n"
                if "on_load" in impl_info.get("methods", []):
                    features += "- `on_load()` - Called when plugin is first loaded\n"
                if "on_enable" in impl_info.get("methods", []):
                    features += "- `on_enable()` - Called when plugin is enabled\n"
                if "on_disable" in impl_info.get("methods", []):
                    features += "- `on_disable()` - Called when plugin is disabled\n"
                if "on_unload" in impl_info.get("methods", []):
                    features += "- `on_unload()` - Called when plugin is unloaded\n"
                features += "\n"

            if "before_session" in impl_info.get("methods", []):
                features += "### Agent Hooks\n\n"
                features += "- `before_session()` - Called before an agent session starts\n"
                features += "- `after_session()` - Called after an agent session completes\n"
                if "on_message" in impl_info.get("methods", []):
                    features += "- `on_message()` - Called when agent receives messages\n"
                features += "\n"

        elif plugin_type == "integration":
            if "get_mcp_tools" in impl_info.get("methods", []):
                features += "### MCP Tools\n\n"
                features += "This plugin provides MCP tools for agent integration.\n\n"

        elif plugin_type == "ui":
            if "get_ui_components" in impl_info.get("methods", []):
                features += "### UI Components\n\n"
                features += "This plugin provides custom UI components.\n\n"

        return features if features != "## Features\n\n" else ""

    def _generate_installation(self, manifest: dict[str, Any]) -> str:
        """Generate installation section."""
        name = manifest.get("name", "plugin")

        installation = "## Installation\n\n"
        installation += "### Using Electron UI\n\n"
        installation += "1. Open Auto Code desktop app\n"
        installation += "2. Navigate to **Plugins** (shortcut: `U`)\n"
        installation += "3. Click **Install Plugin**\n"
        installation += "4. Select installation source (Directory, Git, or Package)\n"
        installation += "5. Follow the prompts to install\n\n"

        installation += "### Manual Installation\n\n"
        installation += "Copy the plugin directory to Auto Code's plugin location:\n\n"
        installation += "```bash\n"
        installation += f"cp -r {name}/ ~/.auto-claude/plugins/user/\n"
        installation += "```\n\n"

        installation += "### Verification\n\n"
        installation += "Verify the plugin loads correctly:\n\n"
        installation += "```bash\n"
        installation += (
            'python -c "from apps.backend.plugins.loader import PluginLoader; '
            f"loader = PluginLoader(); plugin = loader.load_plugin('{name}'); "
            'print(\'OK\')"'
        )
        installation += "\n```"

        return installation

    def _generate_usage(
        self,
        manifest: dict[str, Any],
        impl_info: dict[str, Any],
    ) -> str:
        """Generate usage section."""
        usage = "## Usage\n\n"
        usage += "Once installed and enabled, this plugin will automatically integrate with Auto Code.\n\n"

        plugin_type = manifest.get("plugin_type", "agent")

        if plugin_type == "agent":
            usage += "The plugin will be active during agent sessions and can:\n"
            usage += "- Monitor agent lifecycle events\n"
            usage += "- Access session context information\n"
            usage += "- Provide custom tools and behaviors\n"

        elif plugin_type == "integration":
            usage += "The plugin provides MCP tools that agents can use during sessions.\n"

        elif plugin_type == "ui":
            usage += "The plugin provides UI components visible in the Auto Code interface.\n"

        return usage

    def _generate_configuration(self, manifest: dict[str, Any]) -> str:
        """Generate configuration section."""
        config = "## Configuration\n\n"

        # Check if plugin has dependencies
        dependencies = manifest.get("dependencies", [])
        if dependencies:
            config += "### Dependencies\n\n"
            config += "This plugin requires the following plugins:\n\n"
            for dep in dependencies:
                config += f"- `{dep}`\n"
            config += "\n"
        else:
            config += "This plugin has no dependencies.\n\n"

        # Check Auto Claude version requirement
        ac_version = manifest.get("auto_claude_version")
        if ac_version and ac_version != ">=1.0.0":
            config += "### Version Requirements\n\n"
            config += f"**Auto Claude Version:** `{ac_version}`\n\n"

        return config

    def _generate_permissions(self, manifest: dict[str, Any]) -> str:
        """Generate permissions section."""
        permissions = manifest.get("required_permissions", [])

        if not permissions:
            section = "## Permissions\n\n"
            section += "This plugin requires **no special permissions**.\n"
            return section

        section = "## Permissions\n\n"
        section += "This plugin requires the following permissions:\n\n"

        permission_descriptions = {
            "read_files": "Read files from the project directory",
            "write_files": "Write files to the project directory",
            "network_access": "Make network requests to external services",
            "execute_commands": "Execute shell commands",
            "access_secrets": "Access environment variables and secrets",
            "create_mcp_tools": "Register MCP tools with the Claude SDK",
        }

        for perm in permissions:
            desc = permission_descriptions.get(perm, "Custom permission")
            section += f"- **{perm}**: {desc}\n"

        section += "\n"
        section += "These permissions are declared in `plugin.json` and enforced by the plugin system.\n"

        return section

    def _generate_development(
        self,
        manifest: dict[str, Any],
        plugin_dir: Path,
    ) -> str:
        """Generate development section."""
        dev = "## Development\n\n"

        dev += "### File Structure\n\n"
        dev += "```\n"
        dev += f"{manifest.get('name', 'plugin')}/\n"
        dev += "├── plugin.json      # Plugin metadata\n"

        plugin_type = manifest.get("plugin_type", "agent")
        if plugin_type == "agent":
            dev += "├── agent.py         # Plugin implementation\n"
        elif plugin_type == "integration":
            dev += "├── integration.py   # Plugin implementation\n"
        elif plugin_type == "ui":
            dev += "├── ui.py            # Plugin implementation\n"

        dev += "└── README.md        # Documentation\n"
        dev += "```\n\n"

        dev += "### Testing\n\n"
        dev += "Test the plugin using the Plugin SDK testing utilities:\n\n"
        dev += "```python\n"
        dev += "from apps.backend.plugins.sdk.testing import PluginTestCase\n\n"
        dev += "# Create test cases for your plugin\n"
        dev += "```\n\n"

        dev += "### Extending\n\n"
        dev += "To modify this plugin:\n\n"
        dev += "1. Update `plugin.json` if changing metadata or permissions\n"
        dev += "2. Modify the implementation file to add functionality\n"
        dev += "3. Test changes using the validation tools\n"
        dev += "4. Update this README with new features or changes\n"

        return dev

    def _generate_troubleshooting(self, manifest: dict[str, Any]) -> str:
        """Generate troubleshooting section."""
        troubleshooting = "## Troubleshooting\n\n"

        troubleshooting += "### Plugin not appearing in list\n\n"
        troubleshooting += "- Verify the plugin directory is in the correct location\n"
        troubleshooting += "- Check that `plugin.json` is valid JSON\n"
        troubleshooting += f"- Ensure `plugin_type` is set to `\"{manifest.get('plugin_type', 'agent')}\"`\n\n"

        troubleshooting += "### Plugin fails to load\n\n"
        troubleshooting += "- Check the logs for error messages\n"
        troubleshooting += "- Verify all required fields are present in `plugin.json`\n"
        troubleshooting += "- Ensure dependencies are installed and enabled\n"

        permissions = manifest.get("required_permissions", [])
        if permissions:
            troubleshooting += "- Confirm all required permissions are granted\n"

        troubleshooting += "\n"

        troubleshooting += "### Plugin not working as expected\n\n"
        troubleshooting += "- Make sure the plugin is **enabled**, not just installed\n"
        troubleshooting += "- Check logs for error messages or warnings\n"
        troubleshooting += "- Verify configuration is correct\n"

        return troubleshooting

    def _generate_footer(self, manifest: dict[str, Any]) -> str:
        """Generate document footer."""
        footer = "## Learn More\n\n"
        footer += "- [Plugin Development Guide](../../docs/guides/plugin-development.md)\n"
        footer += "- [Plugin SDK Documentation](../../apps/backend/plugins/sdk/)\n"
        footer += "- [Plugin Examples](../../examples/plugins/)\n\n"

        if manifest.get("license"):
            footer += "## License\n\n"
            footer += f"{manifest['license']}\n"

        return footer
