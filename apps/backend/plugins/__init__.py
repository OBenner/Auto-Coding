"""
Plugin System Module
====================

Auto Claude plugin system for extensibility.

This module provides the core plugin infrastructure:
- PluginBase: Abstract base class for all plugins
- PluginMetadata: Metadata schema for plugin discovery
- PluginType: Enum of supported plugin types
- PluginPermission: Permission types for security

Example usage:
    from plugins.base import PluginBase, PluginMetadata, PluginType

    metadata = PluginMetadata(
        name="my-plugin",
        version="1.0.0",
        author="Me",
        description="My custom plugin",
        plugin_type=PluginType.AGENT
    )

    class MyPlugin(PluginBase):
        def on_load(self):
            # Initialize plugin
            pass

        def on_unload(self):
            # Clean up
            pass

        def on_enable(self):
            # Activate plugin
            pass

        def on_disable(self):
            # Deactivate plugin
            pass
"""

from .base import (
    PluginBase,
    PluginMetadata,
    PluginPermission,
    PluginType,
)

__all__ = [
    "PluginBase",
    "PluginMetadata",
    "PluginPermission",
    "PluginType",
]
