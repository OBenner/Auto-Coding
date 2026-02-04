"""
UI Plugin SDK
==============

SDK for creating custom UI extension plugins.

UI plugins can:
- Add custom components to the Electron frontend
- Extend sidebar navigation with new items
- Add settings panels
- Create dashboard widgets
- Provide IPC handlers for frontend-backend communication
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

from ..base import PluginBase, PluginMetadata, PluginType

if TYPE_CHECKING:
    from electron import ipcMain  # type: ignore

logger = logging.getLogger(__name__)


class UIExtensionPoint(str, Enum):
    """
    Extension points where UI plugins can inject components.

    These define where in the Electron frontend a plugin can add UI elements.
    """

    SIDEBAR = "sidebar"  # Add items to sidebar navigation
    SETTINGS = "settings"  # Add panels to settings page
    DASHBOARD = "dashboard"  # Add widgets to dashboard
    TOOLBAR = "toolbar"  # Add buttons to main toolbar
    CONTEXT_MENU = "context_menu"  # Add items to context menus
    STATUS_BAR = "status_bar"  # Add items to status bar


@dataclass
class UIComponentDefinition:
    """
    Definition of a UI component provided by a plugin.

    This describes a React component that should be loaded and rendered
    in the Electron frontend at a specific extension point.

    Attributes:
        id: Unique identifier for this component
        extension_point: Where to render this component
        title: Display title for the component
        icon: Optional icon name (from icon library)
        component_path: Path to the React component file (relative to plugin directory)
        route: Optional route path for navigation (e.g., "/my-plugin")
        order: Optional display order (lower numbers appear first)
        props: Optional default props to pass to the component
    """

    id: str
    extension_point: UIExtensionPoint
    title: str
    icon: Optional[str] = None
    component_path: Optional[str] = None
    route: Optional[str] = None
    order: int = 100
    props: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "extension_point": self.extension_point.value if isinstance(self.extension_point, UIExtensionPoint) else self.extension_point,
            "title": self.title,
            "icon": self.icon,
            "component_path": self.component_path,
            "route": self.route,
            "order": self.order,
            "props": self.props,
        }


@dataclass
class UIContext:
    """
    Context information provided to UI plugins.

    This context is passed to plugin hooks to provide information about
    the current frontend state, project, and plugin configuration.

    Attributes:
        project_dir: Root directory of the project being worked on
        plugin_dir: Directory containing the plugin files
        config: Optional plugin-specific configuration
        state: Optional persistent state data for this plugin
        metadata: Optional additional metadata as key-value pairs
    """

    project_dir: Path
    plugin_dir: Path
    config: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def project_name(self) -> str:
        """Get the project directory name."""
        return self.project_dir.name

    @property
    def plugin_name(self) -> str:
        """Get the plugin directory name."""
        return self.plugin_dir.name

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key to look up
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def get_state(self, key: str, default: Any = None) -> Any:
        """
        Get a state value by key.

        Args:
            key: State key to look up
            default: Default value if key not found

        Returns:
            State value or default
        """
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """
        Set a state value.

        Args:
            key: State key to set
            value: Value to store
        """
        self.state[key] = value


class UIPlugin(PluginBase):
    """
    Base class for UI extension plugins.

    UI plugins extend the Electron frontend by providing React components,
    IPC handlers, and frontend-backend communication channels.

    Key capabilities:
    - Register UI components at extension points
    - Provide IPC handlers for frontend communication
    - Manage plugin-specific state and configuration
    - Access project and plugin directories

    Example:
        ```python
        class MyUIPlugin(UIPlugin):
            def __init__(self, metadata: PluginMetadata):
                super().__init__(metadata)
                self.data_cache = {}

            def on_load(self):
                # Validate plugin structure
                if not (self.plugin_dir / "components").exists():
                    raise ValueError("Plugin missing components directory")
                logger.info("MyUIPlugin loaded")

            def on_enable(self):
                # Register UI components and IPC handlers
                logger.info("MyUIPlugin enabled")

            def on_disable(self):
                # Unregister components and handlers
                logger.info("MyUIPlugin disabled")

            def on_unload(self):
                # Cleanup
                self.data_cache.clear()

            def get_ui_components(self, context: UIContext) -> list[UIComponentDefinition]:
                # Define UI components to inject
                return [
                    UIComponentDefinition(
                        id="my-dashboard-widget",
                        extension_point=UIExtensionPoint.DASHBOARD,
                        title="My Widget",
                        icon="chart-bar",
                        component_path="components/DashboardWidget.tsx",
                        order=10,
                    ),
                    UIComponentDefinition(
                        id="my-settings-panel",
                        extension_point=UIExtensionPoint.SETTINGS,
                        title="My Plugin Settings",
                        icon="cog",
                        component_path="components/SettingsPanel.tsx",
                        route="/settings/my-plugin",
                        order=20,
                    ),
                ]

            def register_ipc_handlers(self, context: UIContext) -> dict[str, Callable]:
                # Register IPC handlers for frontend communication
                def get_data(event, request_id: str):
                    # Handle frontend request
                    return {"status": "success", "data": self.data_cache}

                def update_data(event, key: str, value: Any):
                    # Update plugin data
                    self.data_cache[key] = value
                    return {"status": "success"}

                # Return mapping of IPC channel names to handler functions
                return {
                    f"{self.name}:get-data": get_data,
                    f"{self.name}:update-data": update_data,
                }

            def get_frontend_assets(self, context: UIContext) -> list[str]:
                # Return paths to frontend assets (CSS, JS bundles)
                return [
                    str(self.plugin_dir / "assets" / "styles.css"),
                    str(self.plugin_dir / "dist" / "bundle.js"),
                ]
        ```
    """

    def __init__(self, metadata: PluginMetadata):
        """
        Initialize UI plugin.

        Args:
            metadata: Plugin metadata from plugin.json

        Raises:
            ValueError: If plugin_type is not UI
        """
        if metadata.plugin_type != PluginType.UI:
            raise ValueError(
                f"UIPlugin requires plugin_type=UI, got {metadata.plugin_type}"
            )
        super().__init__(metadata)
        self.plugin_dir: Optional[Path] = None
        self._ipc_handlers: dict[str, Callable] = {}
        logger.debug(f"UIPlugin initialized: {metadata.name}")

    def set_plugin_dir(self, plugin_dir: Path) -> None:
        """
        Set the plugin directory.

        This is called by the plugin loader after instantiation to provide
        the plugin with its installation directory.

        Args:
            plugin_dir: Path to the plugin directory
        """
        self.plugin_dir = plugin_dir

    def get_ui_components(self, context: UIContext) -> list[UIComponentDefinition]:
        """
        Get UI components provided by this plugin.

        Override this method to declare which UI components your plugin provides
        and where they should be rendered in the Electron frontend.

        Args:
            context: UI context with project and plugin information

        Returns:
            List of UI component definitions

        Example:
            ```python
            def get_ui_components(self, context: UIContext) -> list[UIComponentDefinition]:
                return [
                    UIComponentDefinition(
                        id="my-sidebar-item",
                        extension_point=UIExtensionPoint.SIDEBAR,
                        title="My Tool",
                        icon="puzzle",
                        route="/my-tool",
                        order=50,
                    ),
                ]
            ```
        """
        return []

    def register_ipc_handlers(self, context: UIContext) -> dict[str, Callable]:
        """
        Register IPC handlers for frontend-backend communication.

        Override this method to provide IPC handlers that the frontend can call.
        Each handler receives the IPC event and any arguments passed from the frontend.

        Handler functions should:
        - Accept (event, *args, **kwargs) parameters
        - Return JSON-serializable data or None
        - Handle errors gracefully
        - Be lightweight (offload heavy work to background threads)

        Args:
            context: UI context with project and plugin information

        Returns:
            Dictionary mapping IPC channel names to handler functions

        Example:
            ```python
            def register_ipc_handlers(self, context: UIContext) -> dict[str, Callable]:
                def handle_action(event, action_name: str, params: dict):
                    # Process action
                    result = self.perform_action(action_name, params)
                    return {"success": True, "result": result}

                return {
                    f"{self.name}:perform-action": handle_action,
                }
            ```

        Note:
            IPC channel names should be prefixed with your plugin name to avoid
            conflicts with other plugins (e.g., "my-plugin:do-something").
        """
        return {}

    def get_frontend_assets(self, context: UIContext) -> list[str]:
        """
        Get paths to frontend assets (CSS, JS, images) for this plugin.

        Override this method to provide paths to static assets that should be
        loaded in the frontend. Paths should be absolute or relative to the
        plugin directory.

        Args:
            context: UI context with project and plugin information

        Returns:
            List of asset file paths

        Example:
            ```python
            def get_frontend_assets(self, context: UIContext) -> list[str]:
                return [
                    str(self.plugin_dir / "assets" / "styles.css"),
                    str(self.plugin_dir / "dist" / "main.js"),
                ]
            ```
        """
        return []

    def on_frontend_ready(self, context: UIContext) -> None:
        """
        Called when the Electron frontend has loaded and is ready.

        Override this to:
        - Initialize frontend state
        - Send initial data to frontend
        - Start background tasks that update UI

        Args:
            context: UI context with project and plugin information
        """
        pass

    def on_window_focus(self, context: UIContext, focused: bool) -> None:
        """
        Called when the Electron window gains or loses focus.

        Override this to:
        - Pause/resume background updates
        - Sync state when window regains focus
        - Update UI based on focus state

        Args:
            context: UI context with project and plugin information
            focused: True if window gained focus, False if lost focus
        """
        pass

    def save_state(self, context: UIContext) -> None:
        """
        Save plugin state to disk.

        This is a helper method for persisting UI state across sessions.
        State is saved to the plugin directory.

        Args:
            context: UI context with state to save
        """
        import json

        if not self.plugin_dir:
            logger.warning(f"Cannot save state for {self.name}: plugin_dir not set")
            return

        state_file = self.plugin_dir / ".state.json"
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(context.state, f, indent=2)
        except (OSError, UnicodeEncodeError) as e:
            logger.error(f"Failed to save UI plugin state: {e}")

    def load_state(self, context: UIContext) -> None:
        """
        Load plugin state from disk.

        This is a helper method for loading persisted UI state.

        Args:
            context: UI context to populate with loaded state
        """
        import json

        if not self.plugin_dir:
            logger.warning(f"Cannot load state for {self.name}: plugin_dir not set")
            return

        state_file = self.plugin_dir / ".state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file, encoding="utf-8") as f:
                loaded_state = json.load(f)
                context.state.update(loaded_state)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to load UI plugin state: {e}")
