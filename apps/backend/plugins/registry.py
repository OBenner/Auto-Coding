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

import json
import logging
from pathlib import Path

from .base import PluginBase, PluginType
from .loader import PluginLoader

# Configure logging
logger = logging.getLogger(__name__)

# Import debug utilities - wrapped with source module name for CodeQL compliance
_SOURCE = "plugins.registry"
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
        self.project_dir = Path(project_dir) if project_dir is not None else Path.cwd()
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
            _debug("Created new PluginRegistry instance")
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
            _debug("Reset PluginRegistry instance")

    def load_all_plugins(self) -> None:
        """
        Discover and load all plugins from configured directories.

        This scans both user and system plugin directories, loads valid plugins,
        and automatically enables them if they were previously enabled.

        Raises:
            Exception: If critical plugin loading fails
        """
        _debug("Loading all plugins...")

        # Discover available plugins
        discovered = self.loader.discover_plugins()
        _debug_verbose(f"Discovered {len(discovered)} plugin(s)")

        # Load each plugin
        for metadata in discovered:
            try:
                # Determine plugin directory
                user_plugin_dir = self.loader.user_plugins_dir / metadata.name
                system_plugin_dir = self.loader.system_plugins_dir / metadata.name

                plugin_dir = (
                    user_plugin_dir if user_plugin_dir.exists() else system_plugin_dir
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
                _debug_success(f"Loaded plugin: {plugin.name} v{plugin.version}")

                # Auto-enable unless project state explicitly disables it.
                if self._is_enabled_by_state(plugin.name):
                    try:
                        self.enable_plugin(plugin.name, persist=False)
                    except Exception as e:
                        _debug_warning(
                            f"Failed to auto-enable plugin {plugin.name}: {e}"
                        )
                        logger.warning(
                            f"Failed to auto-enable plugin {plugin.name}: {e}"
                        )

            except Exception as e:
                _debug_error(f"Failed to load plugin {metadata.name}: {e}")
                logger.error(f"Failed to load plugin {metadata.name}: {e}")
                continue

        _debug_success(f"Loaded {len(self._plugins)} plugin(s) successfully")

    def unload_all_plugins(self) -> None:
        """
        Unload all plugins and clean up resources.

        Disables and unloads all plugins, calling their lifecycle hooks.
        """
        _debug("Unloading all plugins...")

        for plugin_name in list(self._plugins.keys()):
            try:
                self.unload_plugin(plugin_name)
            except Exception as e:
                _debug_error(f"Failed to unload plugin {plugin_name}: {e}")
                logger.error(f"Failed to unload plugin {plugin_name}: {e}")

        self._plugins.clear()
        _debug_success("Unloaded all plugins")

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
            _debug_verbose(f"Found plugin: {name}")
        else:
            _debug_verbose(f"Plugin not found: {name}")
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

        _debug_verbose(
            f"Listed {len(plugins)} plugin(s) "
            f"(type={plugin_type}, enabled_only={enabled_only})"
        )
        return plugins

    @property
    def state_path(self) -> Path:
        """Project-scoped plugin runtime state file path."""
        return self.project_dir / ".auto-claude" / "plugins" / "state.json"

    def _load_state(self) -> dict:
        """Load project plugin state, tolerating missing or malformed files."""
        if not self.state_path.exists():
            return {"plugins": {}}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Failed to read plugin state at %s", self.state_path)
            return {"plugins": {}}
        if not isinstance(data, dict):
            return {"plugins": {}}
        plugins = data.get("plugins")
        if not isinstance(plugins, dict):
            data["plugins"] = {}
        return data

    def _write_state(self, state: dict) -> None:
        """Persist project plugin state."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _is_enabled_by_state(self, name: str) -> bool:
        """Return enabled state, defaulting to enabled for discovered plugins."""
        plugin_state = self._load_state().get("plugins", {}).get(name, {})
        if isinstance(plugin_state, dict) and plugin_state.get("enabled") is False:
            return False
        return True

    def _set_enabled_state(self, name: str, enabled: bool) -> None:
        """Persist explicit enabled state for a plugin."""
        state = self._load_state()
        plugins = state.setdefault("plugins", {})
        plugins[name] = {"enabled": enabled}
        self._write_state(state)

    def enable_plugin(self, name: str, persist: bool = True) -> None:
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
            _debug_verbose(f"Plugin already enabled: {name}")
            if persist:
                self._set_enabled_state(name, True)
            return

        _debug(f"Enabling plugin: {name}")
        plugin.on_enable()
        plugin._mark_enabled()
        if persist:
            self._set_enabled_state(name, True)
        _debug_success(f"Enabled plugin: {name}")

    def disable_plugin(self, name: str, persist: bool = True) -> None:
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
            _debug_verbose(f"Plugin already disabled: {name}")
            if persist:
                self._set_enabled_state(name, False)
            return

        _debug(f"Disabling plugin: {name}")
        plugin.on_disable()
        plugin._mark_disabled()
        if persist:
            self._set_enabled_state(name, False)
        _debug_success(f"Disabled plugin: {name}")

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

        _debug(f"Unloading plugin: {name}")

        # Disable first if enabled
        if plugin.is_enabled:
            try:
                self.disable_plugin(name, persist=False)
            except Exception as e:
                _debug_warning(f"Error disabling plugin {name} before unload: {e}")
                logger.warning(f"Error disabling plugin {name} before unload: {e}")

        # Call unload hook
        try:
            plugin.on_unload()
            plugin._mark_unloaded()
        except Exception as e:
            _debug_warning(f"Error in on_unload for plugin {name}: {e}")
            logger.warning(f"Error in on_unload for plugin {name}: {e}")

        # Remove from registry
        del self._plugins[name]
        _debug_success(f"Unloaded plugin: {name}")

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
