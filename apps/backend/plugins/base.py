"""
Plugin Base Module
==================

Base classes and types for the Auto Code plugin system.

This module defines the core plugin interface that all plugins must implement,
as well as metadata schemas for plugin discovery and registration.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)


class PluginType(str, Enum):
    """Types of plugins supported by Auto Code."""

    AGENT = "agent"  # Custom agent plugins with tools/behaviors
    INTEGRATION = "integration"  # External service integrations (MCP tools)
    UI = "ui"  # Frontend UI extensions


class PluginPermission(str, Enum):
    """
    Permission types for plugin security model.

    Plugins must declare required permissions in their metadata.
    The permission system validates plugin actions against declared permissions.
    """

    READ_FILES = "read_files"  # Read files from project directory
    WRITE_FILES = "write_files"  # Write files to project directory
    NETWORK_ACCESS = "network_access"  # Make network requests
    EXECUTE_COMMANDS = "execute_commands"  # Execute shell commands
    ACCESS_SECRETS = "access_secrets"  # Access environment variables/secrets
    CREATE_MCP_TOOLS = "create_mcp_tools"  # Register MCP tools with Claude SDK


class PermissionDeniedError(Exception):
    """
    Raised when a plugin attempts an action without required permission.

    This exception includes detailed information about the permission denial
    to help with debugging and security auditing.
    """

    def __init__(
        self,
        plugin_name: str,
        required_permission: PluginPermission,
        action: str,
    ):
        """
        Initialize permission denied error.

        Args:
            plugin_name: Name of the plugin that was denied
            required_permission: The permission that was required but not granted
            action: Description of the action that was attempted
        """
        self.plugin_name = plugin_name
        self.required_permission = required_permission
        self.action = action
        message = (
            f"Permission denied: Plugin '{plugin_name}' attempted to {action} "
            f"but lacks required permission '{required_permission.value}'. "
            f"Add this permission to the plugin's metadata to allow this action."
        )
        super().__init__(message)


class PermissionValidator:
    """
    Validates plugin actions against declared permissions.

    This class enforces the plugin security model by checking if plugins
    have the required permissions before allowing sensitive operations.

    Example usage:
        validator = PermissionValidator(plugin.metadata)
        validator.require(PluginPermission.READ_FILES, "read config file")

    Or with explicit permissions:
        validator = PermissionValidator.from_permissions([
            PluginPermission.READ_FILES,
            PluginPermission.NETWORK_ACCESS
        ], plugin_name="my-plugin")
        validator.check(PluginPermission.WRITE_FILES)  # Returns False
    """

    def __init__(self, metadata: PluginMetadata):
        """
        Initialize validator with plugin metadata.

        Args:
            metadata: Plugin metadata containing required_permissions
        """
        self.plugin_name = metadata.name
        self.granted_permissions = set(metadata.required_permissions)
        logger.debug(
            f"PermissionValidator initialized for '{self.plugin_name}' "
            f"with permissions: {[p.value for p in self.granted_permissions]}"
        )

    @classmethod
    def from_permissions(
        cls,
        permissions: list[PluginPermission],
        plugin_name: str = "unknown",
    ) -> PermissionValidator:
        """
        Create validator from explicit permission list.

        Useful for testing or when working with permissions outside of
        full plugin metadata context.

        Args:
            permissions: List of granted permissions
            plugin_name: Name to use in error messages

        Returns:
            PermissionValidator instance
        """
        # Create minimal metadata for the validator
        metadata = PluginMetadata(
            name=plugin_name,
            version="0.0.0",
            author="unknown",
            description="Validator-only metadata",
            plugin_type=PluginType.AGENT,
            required_permissions=permissions,
        )
        return cls(metadata)

    def check(self, permission: PluginPermission) -> bool:
        """
        Check if a permission is granted without raising an error.

        Use this for optional features where you want to gracefully
        degrade functionality if permission is missing.

        Args:
            permission: The permission to check

        Returns:
            True if permission is granted, False otherwise
        """
        has_permission = permission in self.granted_permissions
        logger.debug(
            f"Permission check for '{self.plugin_name}': "
            f"{permission.value} = {has_permission}"
        )
        return has_permission

    def require(
        self,
        permission: PluginPermission,
        action: str,
    ) -> None:
        """
        Require a permission for an action, raising exception if denied.

        Use this for critical operations that cannot proceed without
        the permission. The exception includes detailed information
        for debugging and security auditing.

        Args:
            permission: The permission required for the action
            action: Human-readable description of what is being attempted

        Raises:
            PermissionDeniedError: If the permission is not granted
        """
        if not self.check(permission):
            logger.warning(
                f"Permission denied for '{self.plugin_name}': "
                f"attempted to {action} without {permission.value}"
            )
            raise PermissionDeniedError(
                plugin_name=self.plugin_name,
                required_permission=permission,
                action=action,
            )

    def check_any(self, permissions: list[PluginPermission]) -> bool:
        """
        Check if at least one of the given permissions is granted.

        Useful for operations that can be performed with any of
        several alternative permissions.

        Args:
            permissions: List of permissions to check

        Returns:
            True if any permission is granted, False otherwise
        """
        return any(self.check(p) for p in permissions)

    def check_all(self, permissions: list[PluginPermission]) -> bool:
        """
        Check if all given permissions are granted.

        Useful for operations that require multiple permissions
        simultaneously.

        Args:
            permissions: List of permissions to check

        Returns:
            True if all permissions are granted, False otherwise
        """
        return all(self.check(p) for p in permissions)

    def get_granted_permissions(self) -> list[PluginPermission]:
        """
        Get the list of all granted permissions.

        Returns:
            Sorted list of granted permissions
        """
        return sorted(self.granted_permissions, key=lambda p: p.value)

    def get_missing_permissions(
        self,
        required: list[PluginPermission],
    ) -> list[PluginPermission]:
        """
        Get the list of permissions that are required but not granted.

        Useful for providing helpful error messages or UI prompts.

        Args:
            required: List of permissions needed for an operation

        Returns:
            List of permissions that are required but not granted
        """
        return [p for p in required if not self.check(p)]


@dataclass
class PluginMetadata:
    """
    Plugin metadata schema.

    This information is loaded from the plugin's plugin.json manifest file
    during discovery and used for validation, display, and permission checks.

    Attributes:
        name: Unique plugin identifier (e.g., "hello-world-agent")
        version: Semantic version string (e.g., "1.0.0")
        author: Plugin author name or organization
        description: Human-readable description of plugin functionality
        plugin_type: Type of plugin (agent, integration, or ui)
        required_permissions: List of permissions the plugin needs
        dependencies: List of other plugin names this plugin depends on
        homepage: Optional URL to plugin documentation/repository
        license: Optional license identifier (e.g., "MIT", "Apache-2.0")
    """

    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    required_permissions: list[PluginPermission] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    homepage: str | None = None
    license: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "plugin_type": self.plugin_type.value if isinstance(self.plugin_type, PluginType) else self.plugin_type,
            "required_permissions": [
                p.value if isinstance(p, PluginPermission) else p
                for p in self.required_permissions
            ],
            "dependencies": self.dependencies,
            "homepage": self.homepage,
            "license": self.license,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginMetadata:
        """Create metadata from dictionary (loaded from plugin.json)."""
        return cls(
            name=data["name"],
            version=data["version"],
            author=data["author"],
            description=data["description"],
            plugin_type=PluginType(data["plugin_type"]),
            required_permissions=[
                PluginPermission(p) for p in data.get("required_permissions", [])
            ],
            dependencies=data.get("dependencies", []),
            homepage=data.get("homepage"),
            license=data.get("license"),
        )


class PluginBase(ABC):
    """
    Abstract base class for all plugins.

    All plugins (agent, integration, UI) must extend this class and implement
    the lifecycle hooks. The plugin system calls these hooks at appropriate times:

    - on_load: Called when plugin is first discovered and loaded
    - on_unload: Called when plugin is being unloaded (app shutdown)
    - on_enable: Called when user enables the plugin (or on startup if enabled)
    - on_disable: Called when user disables the plugin

    Plugins should use these hooks to:
    - Register/unregister tools or services
    - Initialize/cleanup resources
    - Connect/disconnect from external services
    - Set up/tear down UI extensions
    """

    def __init__(self, metadata: PluginMetadata):
        """
        Initialize plugin with metadata.

        Args:
            metadata: Plugin metadata loaded from plugin.json
        """
        self.metadata = metadata
        self._enabled = False
        self._loaded = False
        logger.debug(f"Initializing plugin: {metadata.name}")

    @property
    def name(self) -> str:
        """Get plugin name."""
        return self.metadata.name

    @property
    def version(self) -> str:
        """Get plugin version."""
        return self.metadata.version

    @property
    def plugin_type(self) -> PluginType:
        """Get plugin type."""
        return self.metadata.plugin_type

    @property
    def is_enabled(self) -> bool:
        """Check if plugin is currently enabled."""
        return self._enabled

    @property
    def is_loaded(self) -> bool:
        """Check if plugin is currently loaded."""
        return self._loaded

    @abstractmethod
    def on_load(self) -> None:
        """
        Called when plugin is first loaded.

        Use this to:
        - Validate configuration
        - Initialize resources
        - Check dependencies

        Raises:
            Exception: If plugin cannot be loaded (missing deps, invalid config, etc.)
        """
        pass

    @abstractmethod
    def on_unload(self) -> None:
        """
        Called when plugin is being unloaded.

        Use this to:
        - Clean up resources
        - Close connections
        - Save state

        This is called during app shutdown or when plugin is removed.
        """
        pass

    @abstractmethod
    def on_enable(self) -> None:
        """
        Called when plugin is enabled.

        Use this to:
        - Register tools/services
        - Start background tasks
        - Connect to external services
        - Register UI extensions

        Raises:
            Exception: If plugin cannot be enabled (service unavailable, etc.)
        """
        pass

    @abstractmethod
    def on_disable(self) -> None:
        """
        Called when plugin is disabled.

        Use this to:
        - Unregister tools/services
        - Stop background tasks
        - Disconnect from services
        - Remove UI extensions

        Plugin should be in a state where it has no active effects.
        """
        pass

    def _mark_loaded(self) -> None:
        """Internal: Mark plugin as loaded."""
        self._loaded = True
        logger.info(f"Plugin loaded: {self.name} v{self.version}")

    def _mark_unloaded(self) -> None:
        """Internal: Mark plugin as unloaded."""
        self._loaded = False
        logger.info(f"Plugin unloaded: {self.name}")

    def _mark_enabled(self) -> None:
        """Internal: Mark plugin as enabled."""
        self._enabled = True
        logger.info(f"Plugin enabled: {self.name}")

    def _mark_disabled(self) -> None:
        """Internal: Mark plugin as disabled."""
        self._enabled = False
        logger.info(f"Plugin disabled: {self.name}")
