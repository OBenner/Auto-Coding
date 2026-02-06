"""
Plugin Registry & Manager
==========================

Central registry for managing plugin lifecycle and providing plugin lookup.

This module provides a singleton registry that:
- Discovers and loads plugins
- Manages plugin enable/disable state
- Provides lookup by name or type
- Handles plugin lifecycle (load, unload, enable, disable)
"""

from __future__ import annotations

import logging
from pathlib import Path

from .base import PluginBase, PluginType
from .loader import PluginLoader

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


class PluginRegistry:
    """
    Singleton registry for managing loaded plugins.

    The registry maintains the collection of loaded plugins, their state
    (enabled/disabled), and provides lookup and lifecycle management.

    Example:
        >>> from plugins.registry import PluginRegistry
        >>> registry = PluginRegistry.get_instance()
        >>>
        >>> # Load all plugins
        >>> registry.load_all_plugins()
        >>>
        >>> # Get specific plugin
        >>> plugin = registry.get_plugin("hello-world-agent")
        >>> if plugin:
        ...     registry.enable_plugin(plugin.name)
        >>>
        >>> # List plugins by type
        >>> agent_plugins = registry.list_plugins(plugin_type=PluginType.AGENT)
        >>> for plugin in agent_plugins:
        ...     print(f"{plugin.name}: {'enabled' if plugin.is_enabled else 'disabled'}")
    """

    _instance: PluginRegistry | None = None

    def __init__(
        self,
        user_plugins_dir: Path | None = None,
        system_plugins_dir: Path | None = None,
        project_dir: Path | None = None,
    ):
        """
        Initialize plugin registry.

        Note: Use get_instance() instead of direct instantiation for singleton pattern.

        Args:
            user_plugins_dir: Directory containing user-installed plugins
            system_plugins_dir: Directory containing system/built-in plugins
            project_dir: Project directory to grant plugins access to
        """
        self.loader = PluginLoader(
            user_plugins_dir=user_plugins_dir,
            system_plugins_dir=system_plugins_dir,
        )
        self.project_dir = project_dir
        self._plugins: dict[str, PluginBase] = {}
        logger.debug("PluginRegistry initialized")

    @classmethod
    def get_instance(
        cls,
        user_plugins_dir: Path | None = None,
        system_plugins_dir: Path | None = None,
        project_dir: Path | None = None,
    ) -> PluginRegistry:
        """
        Get singleton instance of PluginRegistry.

        Creates the instance on first call, returns existing instance on subsequent calls.
        If instance exists, directory parameters are ignored.

        Args:
            user_plugins_dir: Directory containing user-installed plugins
            system_plugins_dir: Directory containing system/built-in plugins
            project_dir: Project directory to grant plugins access to

        Returns:
            Singleton PluginRegistry instance
        """
        if cls._instance is None:
            cls._instance = cls(
                user_plugins_dir=user_plugins_dir,
                system_plugins_dir=system_plugins_dir,
                project_dir=project_dir,
            )
            debug("Created new PluginRegistry instance")
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset singleton instance (useful for testing).

        Unloads all plugins and clears the singleton instance.
        """
        if cls._instance is not None:
            cls._instance.unload_all_plugins()
            cls._instance = None
            debug("Reset PluginRegistry instance")

    def load_all_plugins(self) -> None:
        """
        Discover and load all plugins from configured directories.

        This scans both user and system plugin directories, loads valid plugins,
        and automatically enables them if they were previously enabled.

        Raises:
            Exception: If critical plugin loading fails
        """
        debug("Loading all plugins...")

        # Discover available plugins
        discovered = self.loader.discover_plugins()
        debug_verbose(f"Discovered {len(discovered)} plugin(s)")

        # Load each plugin
        for metadata in discovered:
            try:
                # Determine plugin directory
                user_plugin_dir = self.loader.user_plugins_dir / metadata.name
                system_plugin_dir = self.loader.system_plugins_dir / metadata.name

                plugin_dir = (
                    user_plugin_dir
                    if user_plugin_dir.exists()
                    else system_plugin_dir
                )

                # Load plugin
                plugin = self.loader.load_plugin(
                    plugin_dir=plugin_dir,
                    project_dir=self.project_dir,
                )

                # Call on_load lifecycle hook
                plugin.on_load()
                plugin._mark_loaded()

                # Register plugin
                self._plugins[plugin.name] = plugin
                debug_success(f"Loaded plugin: {plugin.name} v{plugin.version}")

                # Auto-enable plugin (can be made configurable later)
                try:
                    self.enable_plugin(plugin.name)
                except Exception as e:
                    debug_warning(
                        f"Failed to auto-enable plugin {plugin.name}: {e}"
                    )
                    logger.warning(f"Failed to auto-enable plugin {plugin.name}: {e}")

            except Exception as e:
                debug_error(f"Failed to load plugin {metadata.name}: {e}")
                logger.error(f"Failed to load plugin {metadata.name}: {e}")
                continue

        debug_success(f"Loaded {len(self._plugins)} plugin(s) successfully")

    def unload_all_plugins(self) -> None:
        """
        Unload all plugins and clean up resources.

        Disables and unloads all plugins, calling their lifecycle hooks.
        """
        debug("Unloading all plugins...")

        for plugin_name in list(self._plugins.keys()):
            try:
                self.unload_plugin(plugin_name)
            except Exception as e:
                debug_error(f"Failed to unload plugin {plugin_name}: {e}")
                logger.error(f"Failed to unload plugin {plugin_name}: {e}")

        self._plugins.clear()
        debug_success("Unloaded all plugins")

    def get_plugin(self, name: str) -> PluginBase | None:
        """
        Get a plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None if not found
        """
        plugin = self._plugins.get(name)
        if plugin:
            debug_verbose(f"Found plugin: {name}")
        else:
            debug_verbose(f"Plugin not found: {name}")
        return plugin

    def list_plugins(
        self,
        plugin_type: PluginType | None = None,
        enabled_only: bool = False,
    ) -> list[PluginBase]:
        """
        List plugins, optionally filtered by type or enabled state.

        Args:
            plugin_type: Filter by plugin type (None = all types)
            enabled_only: If True, only return enabled plugins

        Returns:
            List of plugin instances matching the filter
        """
        plugins = list(self._plugins.values())

        if plugin_type is not None:
            plugins = [p for p in plugins if p.plugin_type == plugin_type]

        if enabled_only:
            plugins = [p for p in plugins if p.is_enabled]

        debug_verbose(
            f"Listed {len(plugins)} plugin(s) "
            f"(type={plugin_type}, enabled_only={enabled_only})"
        )
        return plugins

    def enable_plugin(self, name: str) -> None:
        """
        Enable a plugin.

        Calls the plugin's on_enable() lifecycle hook and marks it as enabled.

        Args:
            name: Plugin name

        Raises:
            KeyError: If plugin not found
            Exception: If plugin cannot be enabled
        """
        plugin = self._plugins.get(name)
        if plugin is None:
            raise KeyError(f"Plugin not found: {name}")

        if plugin.is_enabled:
            debug_verbose(f"Plugin already enabled: {name}")
            return

        debug(f"Enabling plugin: {name}")
        plugin.on_enable()
        plugin._mark_enabled()
        debug_success(f"Enabled plugin: {name}")

    def disable_plugin(self, name: str) -> None:
        """
        Disable a plugin.

        Calls the plugin's on_disable() lifecycle hook and marks it as disabled.

        Args:
            name: Plugin name

        Raises:
            KeyError: If plugin not found
            Exception: If plugin cannot be disabled
        """
        plugin = self._plugins.get(name)
        if plugin is None:
            raise KeyError(f"Plugin not found: {name}")

        if not plugin.is_enabled:
            debug_verbose(f"Plugin already disabled: {name}")
            return

        debug(f"Disabling plugin: {name}")
        plugin.on_disable()
        plugin._mark_disabled()
        debug_success(f"Disabled plugin: {name}")

    def unload_plugin(self, name: str) -> None:
        """
        Unload a plugin.

        Disables the plugin (if enabled), calls on_unload(), and removes it from registry.

        Args:
            name: Plugin name

        Raises:
            KeyError: If plugin not found
        """
        plugin = self._plugins.get(name)
        if plugin is None:
            raise KeyError(f"Plugin not found: {name}")

        debug(f"Unloading plugin: {name}")

        # Disable first if enabled
        if plugin.is_enabled:
            try:
                self.disable_plugin(name)
            except Exception as e:
                debug_warning(f"Error disabling plugin {name} before unload: {e}")
                logger.warning(f"Error disabling plugin {name} before unload: {e}")

        # Call unload hook
        try:
            plugin.on_unload()
            plugin._mark_unloaded()
        except Exception as e:
            debug_warning(f"Error in on_unload for plugin {name}: {e}")
            logger.warning(f"Error in on_unload for plugin {name}: {e}")

        # Remove from registry
        del self._plugins[name]
        debug_success(f"Unloaded plugin: {name}")

    def is_plugin_loaded(self, name: str) -> bool:
        """
        Check if a plugin is loaded.

        Args:
            name: Plugin name

        Returns:
            True if plugin is loaded, False otherwise
        """
        return name in self._plugins

    def is_plugin_enabled(self, name: str) -> bool:
        """
        Check if a plugin is enabled.

        Args:
            name: Plugin name

        Returns:
            True if plugin is loaded and enabled, False otherwise
        """
        plugin = self._plugins.get(name)
        return plugin.is_enabled if plugin else False


# Convenience functions for common operations


def get_plugin(name: str) -> PluginBase | None:
    """
    Get a plugin by name from the singleton registry.

    Convenience function that uses the singleton registry instance.

    Args:
        name: Plugin name

    Returns:
        Plugin instance or None if not found

    Example:
        >>> from plugins.registry import get_plugin
        >>> plugin = get_plugin("hello-world-agent")
        >>> if plugin:
        ...     print(f"Found: {plugin.name} v{plugin.version}")
    """
    registry = PluginRegistry.get_instance()
    return registry.get_plugin(name)


def list_plugins(
    plugin_type: PluginType | None = None,
    enabled_only: bool = False,
) -> list[PluginBase]:
    """
    List plugins from the singleton registry.

    Convenience function that uses the singleton registry instance.

    Args:
        plugin_type: Filter by plugin type (None = all types)
        enabled_only: If True, only return enabled plugins

    Returns:
        List of plugin instances matching the filter

    Example:
        >>> from plugins.registry import list_plugins, PluginType
        >>> # List all plugins
        >>> all_plugins = list_plugins()
        >>>
        >>> # List only agent plugins
        >>> agent_plugins = list_plugins(plugin_type=PluginType.AGENT)
        >>>
        >>> # List only enabled plugins
        >>> enabled_plugins = list_plugins(enabled_only=True)
    """
    registry = PluginRegistry.get_instance()
    return registry.list_plugins(plugin_type=plugin_type, enabled_only=enabled_only)
