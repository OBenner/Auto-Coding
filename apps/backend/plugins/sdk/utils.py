"""
Plugin SDK Utilities
====================

Utility classes for common plugin operations.

This module provides helper classes for:
- File I/O operations with permission checking
- Configuration management from environment variables
- Persistent state management

Example:
    ```python
    from plugins.sdk.utils import PluginFileManager, PluginConfigManager, PluginStateManager
    from plugins.base import PluginPermission

    # File operations
    file_mgr = PluginFileManager(
        project_dir=context.project_dir,
        permissions=[PluginPermission.READ_FILES],
        plugin_name="my-plugin"
    )
    content = file_mgr.read_file("README.md")

    # Configuration
    config_mgr = PluginConfigManager(
        plugin_name="my-plugin",
        required_keys=["API_KEY", "API_URL"]
    )
    api_key = config_mgr.get("MY_PLUGIN_API_KEY")

    # State management
    state_mgr = PluginStateManager(
        plugin_name="my-plugin",
        state_dir=context.spec_dir / "plugin_state"
    )
    state_mgr.set("last_sync", "2024-01-01")
    last_sync = state_mgr.get("last_sync")
    ```
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from ..base import PermissionDeniedError, PluginPermission

logger = logging.getLogger(__name__)


class PluginFileManager:
    """
    Manages file I/O operations for plugins with permission checking.

    This class provides safe file operations that respect the plugin's
    declared permissions. All operations are scoped to the project directory
    to prevent plugins from accessing files outside the project.

    Attributes:
        project_dir: Root directory for file operations (scoped to this dir)
        plugin_name: Name of the plugin for permission checks and logging
        permissions: Set of granted permissions for this plugin
    """

    def __init__(
        self,
        project_dir: Path,
        permissions: list[PluginPermission],
        plugin_name: str = "unknown",
    ):
        """
        Initialize file manager.

        Args:
            project_dir: Root directory for file operations
            permissions: List of granted permissions
            plugin_name: Name of the plugin (for error messages)
        """
        self.project_dir = Path(project_dir).resolve()
        self.plugin_name = plugin_name
        self.permissions = set(permissions)
        logger.debug(
            f"PluginFileManager initialized for '{plugin_name}' "
            f"in {project_dir}"
        )

    def _check_permission(
        self,
        permission: PluginPermission,
        action: str,
    ) -> None:
        """
        Check if plugin has required permission.

        Args:
            permission: Required permission
            action: Description of action being attempted

        Raises:
            PermissionDeniedError: If permission not granted
        """
        if permission not in self.permissions:
            raise PermissionDeniedError(
                plugin_name=self.plugin_name,
                required_permission=permission,
                action=action,
            )

    def _resolve_path(self, path: str | Path) -> Path:
        """
        Resolve path relative to project directory.

        Args:
            path: File path (relative or absolute)

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path is outside project directory
        """
        resolved = (self.project_dir / path).resolve()
        try:
            resolved.relative_to(self.project_dir)
        except ValueError:
            raise ValueError(
                f"Path '{path}' is outside project directory '{self.project_dir}'"
            )
        return resolved

    def read_file(self, path: str | Path, encoding: str = "utf-8") -> str:
        """
        Read file contents.

        Args:
            path: File path relative to project directory
            encoding: File encoding (default: utf-8)

        Returns:
            File contents as string

        Raises:
            PermissionDeniedError: If READ_FILES permission not granted
            ValueError: If path is outside project directory
            FileNotFoundError: If file does not exist
        """
        self._check_permission(
            PluginPermission.READ_FILES,
            f"read file '{path}'",
        )
        resolved = self._resolve_path(path)
        logger.debug(f"{self.plugin_name}: Reading file {resolved}")
        return resolved.read_text(encoding=encoding)

    def write_file(
        self,
        path: str | Path,
        content: str,
        encoding: str = "utf-8",
        create_dirs: bool = True,
    ) -> None:
        """
        Write content to file.

        Args:
            path: File path relative to project directory
            content: Content to write
            encoding: File encoding (default: utf-8)
            create_dirs: Create parent directories if they don't exist

        Raises:
            PermissionDeniedError: If WRITE_FILES permission not granted
            ValueError: If path is outside project directory
        """
        self._check_permission(
            PluginPermission.WRITE_FILES,
            f"write file '{path}'",
        )
        resolved = self._resolve_path(path)

        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)

        logger.debug(f"{self.plugin_name}: Writing file {resolved}")
        resolved.write_text(content, encoding=encoding)

    def read_json(self, path: str | Path) -> dict[str, Any] | list[Any]:
        """
        Read and parse JSON file.

        Args:
            path: JSON file path relative to project directory

        Returns:
            Parsed JSON data (dict or list)

        Raises:
            PermissionDeniedError: If READ_FILES permission not granted
            ValueError: If path is outside project directory or JSON is invalid
            FileNotFoundError: If file does not exist
        """
        content = self.read_file(path)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file '{path}': {e}")

    def write_json(
        self,
        path: str | Path,
        data: dict[str, Any] | list[Any],
        indent: int = 2,
        create_dirs: bool = True,
    ) -> None:
        """
        Write data as JSON file.

        Args:
            path: JSON file path relative to project directory
            data: Data to serialize as JSON
            indent: JSON indentation (default: 2 spaces)
            create_dirs: Create parent directories if they don't exist

        Raises:
            PermissionDeniedError: If WRITE_FILES permission not granted
            ValueError: If path is outside project directory or data not serializable
        """
        try:
            content = json.dumps(data, indent=indent, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot serialize data to JSON: {e}")

        self.write_file(path, content, create_dirs=create_dirs)

    def file_exists(self, path: str | Path) -> bool:
        """
        Check if file exists.

        Args:
            path: File path relative to project directory

        Returns:
            True if file exists, False otherwise

        Raises:
            ValueError: If path is outside project directory
        """
        resolved = self._resolve_path(path)
        return resolved.exists() and resolved.is_file()

    def dir_exists(self, path: str | Path) -> bool:
        """
        Check if directory exists.

        Args:
            path: Directory path relative to project directory

        Returns:
            True if directory exists, False otherwise

        Raises:
            ValueError: If path is outside project directory
        """
        resolved = self._resolve_path(path)
        return resolved.exists() and resolved.is_dir()

    def list_files(
        self,
        path: str | Path = ".",
        pattern: str = "*",
        recursive: bool = False,
    ) -> list[Path]:
        """
        List files in directory.

        Args:
            path: Directory path relative to project directory (default: project root)
            pattern: Glob pattern to match (default: "*")
            recursive: Search recursively (default: False)

        Returns:
            List of file paths relative to project directory

        Raises:
            PermissionDeniedError: If READ_FILES permission not granted
            ValueError: If path is outside project directory
        """
        self._check_permission(
            PluginPermission.READ_FILES,
            f"list files in '{path}'",
        )
        resolved = self._resolve_path(path)

        if recursive:
            files = resolved.rglob(pattern)
        else:
            files = resolved.glob(pattern)

        # Return paths relative to project directory
        return [
            f.relative_to(self.project_dir)
            for f in files
            if f.is_file()
        ]


class PluginConfigManager:
    """
    Manages plugin configuration from environment variables.

    This class provides utilities for loading plugin configuration from
    environment variables with validation and defaults.

    Configuration keys are automatically prefixed with the plugin name
    to avoid conflicts (e.g., "API_KEY" becomes "MY_PLUGIN_API_KEY").

    Attributes:
        plugin_name: Name of the plugin
        prefix: Environment variable prefix (default: uppercase plugin name)
        required_keys: List of required configuration keys
    """

    def __init__(
        self,
        plugin_name: str,
        prefix: str | None = None,
        required_keys: list[str] | None = None,
    ):
        """
        Initialize config manager.

        Args:
            plugin_name: Name of the plugin
            prefix: Optional custom prefix for env vars (default: uppercase plugin name)
            required_keys: Optional list of required config keys (without prefix)

        Raises:
            ValueError: If required keys are missing
        """
        self.plugin_name = plugin_name
        self.prefix = prefix or plugin_name.upper().replace("-", "_")
        self.required_keys = required_keys or []

        logger.debug(
            f"PluginConfigManager initialized for '{plugin_name}' "
            f"with prefix '{self.prefix}'"
        )

        # Validate required keys
        missing = self.get_missing_keys()
        if missing:
            raise ValueError(
                f"Missing required configuration keys: {missing}. "
                f"Set environment variables: {[self._make_key(k) for k in missing]}"
            )

    def _make_key(self, key: str) -> str:
        """
        Create full environment variable key with prefix.

        Args:
            key: Base key name

        Returns:
            Full environment variable key
        """
        return f"{self.prefix}_{key}"

    def get(self, key: str, default: str | None = None) -> str | None:
        """
        Get configuration value.

        Args:
            key: Configuration key (without prefix)
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        env_key = self._make_key(key)
        value = os.getenv(env_key, default)
        logger.debug(
            f"{self.plugin_name}: Config get '{key}' = "
            f"{'<set>' if value is not None else '<not set>'}"
        )
        return value

    def get_required(self, key: str) -> str:
        """
        Get required configuration value.

        Args:
            key: Configuration key (without prefix)

        Returns:
            Configuration value

        Raises:
            ValueError: If key is not set
        """
        value = self.get(key)
        if value is None:
            raise ValueError(
                f"Required configuration key '{key}' not set. "
                f"Set environment variable '{self._make_key(key)}'"
            )
        return value

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get boolean configuration value.

        Args:
            key: Configuration key (without prefix)
            default: Default value if not found

        Returns:
            Boolean value
        """
        value = self.get(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def get_int(self, key: str, default: int | None = None) -> int | None:
        """
        Get integer configuration value.

        Args:
            key: Configuration key (without prefix)
            default: Default value if not found

        Returns:
            Integer value or default

        Raises:
            ValueError: If value is not a valid integer
        """
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            raise ValueError(
                f"Configuration key '{key}' must be an integer, got '{value}'"
            )

    def get_all(self) -> dict[str, str]:
        """
        Get all configuration values for this plugin.

        Returns:
            Dictionary of all config values (keys without prefix)
        """
        config = {}
        prefix_len = len(self.prefix) + 1  # +1 for underscore

        for env_key, value in os.environ.items():
            if env_key.startswith(self.prefix + "_"):
                key = env_key[prefix_len:]
                config[key] = value

        return config

    def get_missing_keys(self) -> list[str]:
        """
        Get list of required keys that are not set.

        Returns:
            List of missing required keys (without prefix)
        """
        return [
            key
            for key in self.required_keys
            if self.get(key) is None
        ]

    def has_all_required(self) -> bool:
        """
        Check if all required keys are set.

        Returns:
            True if all required keys are set, False otherwise
        """
        return len(self.get_missing_keys()) == 0


class PluginStateManager:
    """
    Manages persistent state for plugins.

    This class provides utilities for storing and retrieving plugin state
    that persists across sessions. State is stored as JSON files in the
    plugin's state directory.

    Attributes:
        plugin_name: Name of the plugin
        state_dir: Directory for storing state files
        state_file: Path to the main state JSON file
    """

    def __init__(
        self,
        plugin_name: str,
        state_dir: Path | None = None,
    ):
        """
        Initialize state manager.

        Args:
            plugin_name: Name of the plugin
            state_dir: Optional custom state directory (default: .auto-claude/plugin_state/<plugin_name>)
        """
        self.plugin_name = plugin_name

        if state_dir is None:
            # Default to .auto-claude/plugin_state/<plugin_name>
            state_dir = Path.cwd() / ".auto-claude" / "plugin_state" / plugin_name

        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "state.json"
        self._state: dict[str, Any] = {}
        self._loaded = False

        logger.debug(
            f"PluginStateManager initialized for '{plugin_name}' "
            f"in {self.state_dir}"
        )

    def _ensure_loaded(self) -> None:
        """Load state from disk if not already loaded."""
        if not self._loaded:
            self.load()

    def load(self) -> None:
        """
        Load state from disk.

        If state file doesn't exist, initializes with empty state.
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
                logger.debug(f"{self.plugin_name}: Loaded state from {self.state_file}")
            except json.JSONDecodeError as e:
                logger.warning(
                    f"{self.plugin_name}: Failed to load state from {self.state_file}: {e}. "
                    f"Using empty state."
                )
                self._state = {}
        else:
            self._state = {}
            logger.debug(f"{self.plugin_name}: No state file found, using empty state")

        self._loaded = True

    def save(self) -> None:
        """
        Save state to disk.

        Creates state directory if it doesn't exist.
        """
        self.state_dir.mkdir(parents=True, exist_ok=True)

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, ensure_ascii=False)

        logger.debug(f"{self.plugin_name}: Saved state to {self.state_file}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get state value by key.

        Args:
            key: State key
            default: Default value if key not found

        Returns:
            State value or default
        """
        self._ensure_loaded()
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set state value.

        Args:
            key: State key
            value: Value to store (must be JSON-serializable)

        Raises:
            ValueError: If value is not JSON-serializable
        """
        self._ensure_loaded()

        # Validate that value is JSON-serializable
        try:
            json.dumps(value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"State value for '{key}' must be JSON-serializable: {e}")

        self._state[key] = value
        logger.debug(f"{self.plugin_name}: Set state '{key}' = {value}")

    def delete(self, key: str) -> None:
        """
        Delete state value.

        Args:
            key: State key to delete
        """
        self._ensure_loaded()
        if key in self._state:
            del self._state[key]
            logger.debug(f"{self.plugin_name}: Deleted state key '{key}'")

    def clear(self) -> None:
        """
        Clear all state.

        This removes all state data but does not delete the state file.
        Call save() to persist the cleared state.
        """
        self._state = {}
        self._loaded = True
        logger.debug(f"{self.plugin_name}: Cleared all state")

    def get_all(self) -> dict[str, Any]:
        """
        Get all state data.

        Returns:
            Dictionary containing all state data
        """
        self._ensure_loaded()
        return self._state.copy()

    def update(self, data: dict[str, Any]) -> None:
        """
        Update state with multiple values.

        Args:
            data: Dictionary of key-value pairs to update

        Raises:
            ValueError: If any value is not JSON-serializable
        """
        self._ensure_loaded()

        # Validate all values are JSON-serializable
        try:
            json.dumps(data)
        except (TypeError, ValueError) as e:
            raise ValueError(f"State data must be JSON-serializable: {e}")

        self._state.update(data)
        logger.debug(f"{self.plugin_name}: Updated state with {len(data)} keys")

    def has_key(self, key: str) -> bool:
        """
        Check if state has a key.

        Args:
            key: State key to check

        Returns:
            True if key exists, False otherwise
        """
        self._ensure_loaded()
        return key in self._state
