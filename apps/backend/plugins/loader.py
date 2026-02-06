"""
Plugin Discovery & Loading
===========================

Discovers, validates, and loads plugins from plugin directories.

This module handles plugin discovery by scanning configured directories,
validating plugin.json manifest files, dynamically loading plugin modules,
and initializing plugin instances with proper sandboxing.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from pathlib import Path

from .base import PluginBase, PluginMetadata, PluginType
from .isolation import PluginSandbox, ResourceLimits

# Configure logging
logger = logging.getLogger(__name__)

# Import debug utilities
try:
    from debug import debug, debug_error, debug_success, debug_verbose, debug_warning
except ImportError:

    def debug(*args, **kwargs):
        pass

    def debug_verbose(*args, **kwargs):
        pass

    def debug_success(*args, **kwargs):
        pass

    def debug_error(*args, **kwargs):
        pass

    def debug_warning(*args, **kwargs):
        pass


class PluginLoadError(Exception):
    """Raised when a plugin fails to load."""

    pass


class PluginValidationError(Exception):
    """Raised when plugin manifest validation fails."""

    pass


class PluginLoader:
    """
    Discovers and loads plugins from configured directories.

    The loader scans plugin directories, validates manifests, loads modules,
    and initializes plugin instances. It supports both user-installed and
    system plugins.

    Plugin directory structure:
        plugin_name/
            plugin.json      # Required: Plugin manifest
            plugin.py        # Required: Plugin implementation (or __init__.py)
            README.md        # Optional: Documentation
            ...              # Optional: Additional files

    Example:
        >>> from plugins.loader import PluginLoader
        >>> loader = PluginLoader()
        >>> plugins = loader.discover_plugins()
        >>> for plugin in plugins:
        ...     print(f"Found: {plugin.name} v{plugin.version}")
        >>>
        >>> # Load specific plugin
        >>> plugin = loader.load_plugin(Path("path/to/plugin"))
        >>> plugin.on_load()
        >>> plugin.on_enable()
    """

    def __init__(
        self,
        user_plugins_dir: Path | None = None,
        system_plugins_dir: Path | None = None,
        default_limits: ResourceLimits | None = None,
    ):
        """
        Initialize plugin loader.

        Args:
            user_plugins_dir: Directory containing user-installed plugins
            system_plugins_dir: Directory containing system/built-in plugins
            default_limits: Default resource limits for plugin sandboxing
        """
        # Default plugin directories relative to backend root
        if user_plugins_dir is None:
            user_plugins_dir = Path.cwd() / ".auto-claude" / "plugins" / "user"
        if system_plugins_dir is None:
            system_plugins_dir = Path(__file__).parent.parent / "plugins" / "system"

        self.user_plugins_dir = Path(user_plugins_dir)
        self.system_plugins_dir = Path(system_plugins_dir)
        self.default_limits = default_limits or ResourceLimits()

        # Ensure directories exist
        self.user_plugins_dir.mkdir(parents=True, exist_ok=True)
        self.system_plugins_dir.mkdir(parents=True, exist_ok=True)

        logger.debug("PluginLoader initialized:")
        debug_verbose(f"  User plugins: {self.user_plugins_dir}")
        debug_verbose(f"  System plugins: {self.system_plugins_dir}")
        debug_verbose(f"  Default limits: {self.default_limits.to_dict()}")

    def discover_plugins(self) -> list[PluginMetadata]:
        """
        Discover all plugins in configured directories.

        Scans both user and system plugin directories, validates manifests,
        and returns metadata for all valid plugins found.

        Returns:
            List of PluginMetadata for all discovered plugins

        Raises:
            PluginValidationError: If manifest validation fails
        """
        discovered = []

        debug("Discovering plugins...")

        # Scan system plugins first (can be overridden by user plugins)
        if self.system_plugins_dir.exists():
            debug_verbose(f"Scanning system plugins: {self.system_plugins_dir}")
            for plugin_dir in self.system_plugins_dir.iterdir():
                if plugin_dir.is_dir():
                    try:
                        metadata = self._load_metadata(plugin_dir)
                        discovered.append(metadata)
                        debug_verbose(f"  Found: {metadata.name} v{metadata.version}")
                    except Exception as e:
                        debug_warning(
                            f"  Skipping invalid system plugin {plugin_dir.name}: {e}"
                        )
                        logger.warning(
                            f"Failed to load system plugin {plugin_dir.name}: {e}"
                        )

        # Scan user plugins (can override system plugins)
        if self.user_plugins_dir.exists():
            debug_verbose(f"Scanning user plugins: {self.user_plugins_dir}")
            for plugin_dir in self.user_plugins_dir.iterdir():
                if plugin_dir.is_dir():
                    try:
                        metadata = self._load_metadata(plugin_dir)
                        # Check for duplicates (user plugin overrides system)
                        existing = next(
                            (p for p in discovered if p.name == metadata.name), None
                        )
                        if existing:
                            debug_warning(
                                f"  User plugin '{metadata.name}' overrides system plugin"
                            )
                            discovered.remove(existing)
                        discovered.append(metadata)
                        debug_verbose(f"  Found: {metadata.name} v{metadata.version}")
                    except Exception as e:
                        debug_warning(
                            f"  Skipping invalid user plugin {plugin_dir.name}: {e}"
                        )
                        logger.warning(
                            f"Failed to load user plugin {plugin_dir.name}: {e}"
                        )

        debug_success(f"Discovered {len(discovered)} plugins")
        return discovered

    def load_plugin(
        self,
        plugin_dir: Path,
        project_dir: Path | None = None,
        limits: ResourceLimits | None = None,
    ) -> PluginBase:
        """
        Load a plugin from a directory.

        Validates the manifest, imports the plugin module, instantiates
        the plugin class, and prepares it for use with sandboxing.

        Args:
            plugin_dir: Directory containing the plugin
            project_dir: Project directory to grant plugin access to
            limits: Resource limits for plugin execution (uses default if None)

        Returns:
            Initialized plugin instance

        Raises:
            PluginLoadError: If plugin loading fails
            PluginValidationError: If manifest validation fails
        """
        plugin_dir = Path(plugin_dir).resolve()

        if not plugin_dir.exists():
            raise PluginLoadError(f"Plugin directory not found: {plugin_dir}")

        debug(f"Loading plugin from: {plugin_dir}")

        # Load and validate manifest
        try:
            metadata = self._load_metadata(plugin_dir)
            debug_verbose(f"  Loaded metadata: {metadata.name} v{metadata.version}")
        except Exception as e:
            raise PluginValidationError(f"Invalid plugin manifest: {e}") from e

        # Find plugin module (plugin.py or __init__.py)
        module_path = self._find_plugin_module(plugin_dir)
        if not module_path:
            raise PluginLoadError(
                f"Plugin module not found: Expected {plugin_dir}/plugin.py or {plugin_dir}/__init__.py"
            )

        debug_verbose(f"  Loading module: {module_path}")

        # Dynamically import plugin module
        try:
            plugin_class = self._import_plugin_module(
                module_path, metadata.name, plugin_dir
            )
        except Exception as e:
            raise PluginLoadError(f"Failed to import plugin module: {e}") from e

        # Instantiate plugin
        try:
            plugin = plugin_class(metadata)
            debug_verbose(f"  Instantiated plugin class: {plugin_class.__name__}")
        except Exception as e:
            raise PluginLoadError(f"Failed to instantiate plugin: {e}") from e

        # Set up sandbox for plugin execution
        allowed_dirs = [plugin_dir]
        if project_dir:
            allowed_dirs.append(Path(project_dir).resolve())

        plugin._sandbox = PluginSandbox(
            plugin_dir=plugin_dir,
            allowed_dirs=allowed_dirs,
            limits=limits or self.default_limits,
        )
        debug_verbose(f"  Configured sandbox with {len(allowed_dirs)} allowed dirs")

        debug_success(f"Loaded plugin: {metadata.name} v{metadata.version}")
        return plugin

    def _load_metadata(self, plugin_dir: Path) -> PluginMetadata:
        """
        Load and validate plugin metadata from plugin.json.

        Args:
            plugin_dir: Directory containing plugin.json

        Returns:
            Validated PluginMetadata instance

        Raises:
            PluginValidationError: If manifest is missing or invalid
        """
        manifest_path = plugin_dir / "plugin.json"

        if not manifest_path.exists():
            raise PluginValidationError(
                f"Missing plugin.json in {plugin_dir.name}"
            )

        try:
            with open(manifest_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise PluginValidationError(
                f"Invalid JSON in plugin.json: {e}"
            ) from e
        except Exception as e:
            raise PluginValidationError(
                f"Failed to read plugin.json: {e}"
            ) from e

        # Validate required fields
        required_fields = ["name", "version", "author", "description", "plugin_type"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise PluginValidationError(
                f"Missing required fields in plugin.json: {', '.join(missing)}"
            )

        # Validate plugin_type
        try:
            PluginType(data["plugin_type"])
        except ValueError as e:
            raise PluginValidationError(
                f"Invalid plugin_type '{data['plugin_type']}'. "
                f"Must be one of: {', '.join([t.value for t in PluginType])}"
            ) from e

        # Create metadata
        try:
            metadata = PluginMetadata.from_dict(data)
        except Exception as e:
            raise PluginValidationError(
                f"Invalid plugin metadata: {e}"
            ) from e

        return metadata

    def _find_plugin_module(self, plugin_dir: Path) -> Path | None:
        """
        Find plugin module file (plugin.py or __init__.py).

        Args:
            plugin_dir: Directory containing the plugin

        Returns:
            Path to plugin module or None if not found
        """
        # Try plugin.py first
        plugin_py = plugin_dir / "plugin.py"
        if plugin_py.exists():
            return plugin_py

        # Try __init__.py (package-style plugin)
        init_py = plugin_dir / "__init__.py"
        if init_py.exists():
            return init_py

        return None

    def _import_plugin_module(
        self,
        module_path: Path,
        plugin_name: str,
        plugin_dir: Path,
    ) -> type[PluginBase]:
        """
        Dynamically import plugin module and extract plugin class.

        Args:
            module_path: Path to plugin module file
            plugin_name: Name of the plugin (for module naming)
            plugin_dir: Plugin directory path

        Returns:
            Plugin class (subclass of PluginBase)

        Raises:
            PluginLoadError: If module import fails or plugin class not found
        """
        # Create unique module name to avoid conflicts
        module_name = f"auto_claude_plugin_{plugin_name.replace('-', '_')}"

        # Add plugin directory to Python path temporarily
        plugin_dir_str = str(plugin_dir)
        if plugin_dir_str not in sys.path:
            sys.path.insert(0, plugin_dir_str)

        try:
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise PluginLoadError(f"Failed to create module spec for {module_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find plugin class (must be PluginBase subclass)
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, PluginBase)
                    and attr is not PluginBase
                ):
                    plugin_class = attr
                    break

            if plugin_class is None:
                raise PluginLoadError(
                    f"No PluginBase subclass found in {module_path.name}"
                )

            return plugin_class

        except Exception as e:
            raise PluginLoadError(f"Failed to import plugin module: {e}") from e
        finally:
            # Clean up sys.path
            if plugin_dir_str in sys.path:
                sys.path.remove(plugin_dir_str)


def discover_plugins(
    user_plugins_dir: Path | None = None,
    system_plugins_dir: Path | None = None,
) -> list[PluginMetadata]:
    """
    Convenience function to discover all plugins.

    Creates a PluginLoader instance and discovers plugins in both
    user and system directories.

    Args:
        user_plugins_dir: Directory containing user-installed plugins (optional)
        system_plugins_dir: Directory containing system/built-in plugins (optional)

    Returns:
        List of PluginMetadata for all discovered plugins

    Example:
        >>> from plugins.loader import discover_plugins
        >>> plugins = discover_plugins()
        >>> for plugin in plugins:
        ...     print(f"{plugin.name}: {plugin.description}")
    """
    loader = PluginLoader(
        user_plugins_dir=user_plugins_dir,
        system_plugins_dir=system_plugins_dir,
    )
    return loader.discover_plugins()
