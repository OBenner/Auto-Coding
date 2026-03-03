#!/usr/bin/env python3
"""
Integration Plugin MCP Tool Tests
==================================

Tests the creation and invocation of MCP tools from integration plugins.

This test suite verifies that:
- Integration plugins can create MCP tools
- MCP tools are callable and return expected results
- Tool functions have proper signatures and docstrings
- IntegrationContext is properly passed to tool creation
- State persistence works across tool invocations
- MCP server creation works with plugin tools
"""

import json
import logging
import sys
from pathlib import Path

import pytest

# Ensure apps/backend is in path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from plugins.base import PluginType
from plugins.registry import PluginRegistry
from plugins.sdk.integration import IntegrationContext

# Get logger for tests
logger = logging.getLogger(__name__)


class TestIntegrationPluginMCPTools:
    """Tests for MCP tool creation from integration plugins."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, temp_dir):
        """Setup and teardown for each test - ensures clean plugin registry."""
        # Reset plugin registry before each test
        PluginRegistry.reset_instance()
        yield
        # Reset after test
        PluginRegistry.reset_instance()

    @pytest.fixture
    def user_plugins_dir(self, temp_dir):
        """Create temporary user plugins directory."""
        plugins_dir = temp_dir / ".auto-claude" / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        return plugins_dir

    @pytest.fixture
    def system_plugins_dir(self):
        """Get path to example plugins directory."""
        # Try multiple locations for example plugins
        backend_dir = Path(__file__).parent.parent / "apps" / "backend"
        examples_dir = Path(__file__).parent.parent / "examples" / "plugins"

        if examples_dir.exists():
            return examples_dir

        # Fallback to relative path from backend
        alt_path = backend_dir.parent.parent / "examples" / "plugins"
        if alt_path.exists():
            return alt_path

        # If running from worktree, use the worktree examples
        return Path.cwd() / "examples" / "plugins"

    @pytest.fixture
    def project_dir(self, temp_dir):
        """Create temporary project directory."""
        project = temp_dir / "test_project"
        project.mkdir(parents=True, exist_ok=True)

        # Create a minimal spec directory
        spec_dir = project / ".auto-claude" / "specs" / "001-test-spec"
        spec_dir.mkdir(parents=True, exist_ok=True)

        # Create a minimal implementation plan for sync testing
        plan = {
            "feature": "Test Feature",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Implementation",
                    "subtasks": [
                        {
                            "id": "subtask-1-1",
                            "description": "Test subtask 1",
                            "status": "pending",
                        },
                        {
                            "id": "subtask-1-2",
                            "description": "Test subtask 2",
                            "status": "in_progress",
                        },
                    ],
                }
            ],
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        return project

    @pytest.fixture
    def spec_dir(self, project_dir):
        """Get spec directory."""
        return project_dir / ".auto-claude" / "specs" / "001-test-spec"

    @pytest.fixture
    def install_test_integration_plugin(self, user_plugins_dir):
        """Create a test integration plugin for MCP tool testing."""
        plugin_dir = user_plugins_dir / "test-integration-plugin"
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Create plugin.json manifest
        manifest = {
            "name": "test-integration-plugin",
            "version": "1.0.0",
            "author": "Test Suite",
            "description": "Test integration plugin for MCP tool testing",
            "plugin_type": "integration",
            "auto_claude_version": ">=1.0.0",
            "required_permissions": ["read_files", "write_files"],
            "dependencies": [],
            "homepage": "https://example.com/test-plugin",
            "license": "MIT",
        }
        (plugin_dir / "plugin.json").write_text(json.dumps(manifest, indent=2))

        # Create plugin.py implementation
        # NOTE: We use _BaseIntegrationPlugin naming to avoid the loader picking up
        # IntegrationPlugin when scanning for PluginBase subclasses
        plugin_code = '''"""Test Integration Plugin for MCP Tool Testing."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import sys

# Ensure plugins package is importable
backend_dir = Path(__file__).parent.parent.parent.parent / "apps" / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from plugins.base import PluginMetadata
# Import module to avoid top-level import of IntegrationPlugin class
import plugins.sdk.integration as integration_sdk

logger = logging.getLogger(__name__)


class MockDataStore:
    """Mock data store for testing MCP tools."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.items_file = data_dir / "items.json"
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.items_file.exists():
            self._save_items([])

    def _load_items(self) -> list[dict]:
        try:
            with open(self.items_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return []

    def _save_items(self, items: list[dict]) -> None:
        try:
            with open(self.items_file, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2)
        except (OSError, UnicodeEncodeError):
            pass

    def create_item(self, name: str, value: str) -> dict:
        items = self._load_items()
        item_id = len(items) + 1
        item = {
            "id": item_id,
            "name": name,
            "value": value,
            "created_at": datetime.now().isoformat()
        }
        items.append(item)
        self._save_items(items)
        return item

    def list_items(self) -> list[dict]:
        return self._load_items()

    def get_item(self, item_id: int) -> Optional[dict]:
        items = self._load_items()
        for item in items:
            if item.get("id") == item_id:
                return item
        return None

    def update_item(self, item_id: int, value: str) -> Optional[dict]:
        items = self._load_items()
        for item in items:
            if item.get("id") == item_id:
                item["value"] = value
                item["updated_at"] = datetime.now().isoformat()
                self._save_items(items)
                return item
        return None

    def is_connected(self) -> bool:
        return self.items_file.exists()


class TestIntegrationPlugin(integration_sdk.IntegrationPlugin):
    """Test integration plugin with MCP tools."""

    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.data_store: Optional[MockDataStore] = None

    def on_load(self) -> None:
        logger.info("test-integration-plugin: Plugin loaded")

    def on_enable(self) -> None:
        logger.info("test-integration-plugin: Plugin enabled")
        data_dir_str = self.get_config_value(
            "TEST_INTEGRATION_DATA_DIR",
            "~/.auto-claude/test-integration"
        )
        data_dir = Path(data_dir_str).expanduser()
        self.data_store = MockDataStore(data_dir)
        logger.info(f"test-integration-plugin: Connected to data store at {data_dir}")

    def on_disable(self) -> None:
        logger.info("test-integration-plugin: Plugin disabled")
        self.data_store = None

    def on_unload(self) -> None:
        logger.info("test-integration-plugin: Plugin unloaded")

    def create_mcp_tools(self, context: integration_sdk.IntegrationContext) -> list:
        """Create MCP tools for testing."""
        if not self.data_store:
            logger.warning("test-integration-plugin: Data store not initialized")
            return []

        # Load state
        self.load_state(context)

        def create_item(name: str, value: str) -> str:
            """Create a new item in the data store."""
            if not self.data_store:
                return json.dumps({"error": "Data store not connected"})

            item = self.data_store.create_item(name, value)
            context.set_state("item_count", context.get_state("item_count", 0) + 1)
            context.set_state("last_create", datetime.now().isoformat())
            self.save_state(context)
            return json.dumps(item, indent=2)

        def list_items() -> str:
            """List all items from the data store."""
            if not self.data_store:
                return json.dumps({"error": "Data store not connected"})

            items = self.data_store.list_items()
            context.set_state("last_list", datetime.now().isoformat())
            self.save_state(context)
            return json.dumps(items, indent=2)

        def get_item(item_id: int) -> str:
            """Get an item by ID."""
            if not self.data_store:
                return json.dumps({"error": "Data store not connected"})

            item = self.data_store.get_item(item_id)
            if item:
                return json.dumps(item, indent=2)
            return json.dumps({"error": f"Item {item_id} not found"})

        def update_item(item_id: int, value: str) -> str:
            """Update an item's value."""
            if not self.data_store:
                return json.dumps({"error": "Data store not connected"})

            item = self.data_store.update_item(item_id, value)
            if item:
                context.set_state("last_update", datetime.now().isoformat())
                self.save_state(context)
                return json.dumps(item, indent=2)
            return json.dumps({"error": f"Item {item_id} not found"})

        logger.info(f"test-integration-plugin: Created 4 MCP tools for spec '{context.spec_name}'")
        return [create_item, list_items, get_item, update_item]

    def is_available(self) -> bool:
        """Check if integration is available."""
        return (
            self.is_enabled
            and self.data_store is not None
            and self.data_store.is_connected()
        )
'''
        (plugin_dir / "plugin.py").write_text(plugin_code)

        return plugin_dir

    @pytest.fixture
    def integration_context(self, project_dir, spec_dir, temp_dir):
        """Create an IntegrationContext for testing."""
        # Create a data directory for the mock data store
        data_dir = temp_dir / "test_integration_data"
        data_dir.mkdir(parents=True, exist_ok=True)

        context = IntegrationContext(
            project_dir=project_dir,
            spec_dir=spec_dir,
            config={"TEST_INTEGRATION_DATA_DIR": str(data_dir)},
            state={},
            metadata={},
        )

        return context

    def test_plugin_mcp_tool_discovery(
        self,
        user_plugins_dir,
        install_test_integration_plugin,
        integration_context,
        caplog,
    ):
        """Test that integration plugins create MCP tools correctly."""
        caplog.set_level(logging.INFO)

        # Create registry and load plugins
        registry = PluginRegistry.get_instance(
            user_plugins_dir=user_plugins_dir,
            project_dir=integration_context.project_dir,
        )
        registry.load_all_plugins()

        # Get test-integration-plugin
        plugin = registry.get_plugin("test-integration-plugin")
        assert plugin is not None, "test-integration-plugin should be loaded"
        assert plugin.plugin_type == PluginType.INTEGRATION

        # Enable plugin
        registry.enable_plugin("test-integration-plugin")
        assert plugin.is_enabled

        # Set config on plugin instance
        plugin.set_config_value(
            "TEST_INTEGRATION_DATA_DIR",
            integration_context.config.get(
                "TEST_INTEGRATION_DATA_DIR",
                integration_context.config.get("TEST_INTEGRATION_DATA_DIR"),
            ),
        )

        # Trigger on_enable to initialize the data store
        plugin.on_enable()

        # Create MCP tools
        tools = plugin.create_mcp_tools(integration_context)

        # Verify tools were created
        assert isinstance(tools, list), "create_mcp_tools should return a list"
        assert len(tools) > 0, "Should create at least one MCP tool"

        # Verify all tools are callable
        for tool in tools:
            assert callable(tool), f"Tool {tool} should be callable"
            assert hasattr(tool, "__name__"), f"Tool {tool} should have a name"
            assert hasattr(tool, "__doc__"), f"Tool {tool} should have a docstring"

        # Log the discovered tools
        tool_names = [tool.__name__ for tool in tools]
        logger.info(f"Discovered MCP tools: {tool_names}")

    def test_mcp_tool_invocation(
        self, user_plugins_dir, install_test_integration_plugin, integration_context
    ):
        """Test that MCP tools can be invoked and return expected results."""
        # Create registry and load plugins
        registry = PluginRegistry.get_instance(
            user_plugins_dir=user_plugins_dir,
            project_dir=integration_context.project_dir,
        )
        registry.load_all_plugins()

        # Get and enable plugin
        plugin = registry.get_plugin("test-integration-plugin")
        plugin.set_config_value(
            "TEST_INTEGRATION_DATA_DIR",
            integration_context.config["TEST_INTEGRATION_DATA_DIR"],
        )
        registry.enable_plugin("test-integration-plugin")
        plugin.on_enable()

        # Create MCP tools
        tools = plugin.create_mcp_tools(integration_context)
        tool_dict = {tool.__name__: tool for tool in tools}

        # Test 1: Create an item
        create_item = tool_dict.get("create_item")
        assert create_item is not None, "create_item tool should exist"

        result = create_item("Test Item", "This is a test item")
        result_data = json.loads(result)

        assert "id" in result_data, "Created item should have an ID"
        assert result_data["name"] == "Test Item"
        assert result_data["value"] == "This is a test item"
        assert "created_at" in result_data
        item_id = result_data["id"]

        # Test 2: List items
        list_items = tool_dict.get("list_items")
        assert list_items is not None, "list_items tool should exist"

        result = list_items()
        result_data = json.loads(result)

        assert isinstance(result_data, list), "list_items should return a list"
        assert len(result_data) >= 1, "Should have at least one item"
        assert any(t["id"] == item_id for t in result_data), (
            "Created item should be in list"
        )

        # Test 3: Update item value
        update_item = tool_dict.get("update_item")
        assert update_item is not None, "update_item tool should exist"

        result = update_item(item_id, "Updated value")
        result_data = json.loads(result)

        assert result_data["id"] == item_id
        assert result_data["value"] == "Updated value"

        # Test 4: Get item details
        get_item = tool_dict.get("get_item")
        assert get_item is not None, "get_item tool should exist"

        result = get_item(item_id)
        result_data = json.loads(result)

        assert result_data["id"] == item_id
        assert result_data["value"] == "Updated value"
        assert result_data["name"] == "Test Item"

    def test_mcp_tool_state_persistence(
        self, user_plugins_dir, install_test_integration_plugin, integration_context
    ):
        """Test that MCP tools can persist state across invocations."""
        # Create registry and load plugins
        registry = PluginRegistry.get_instance(
            user_plugins_dir=user_plugins_dir,
            project_dir=integration_context.project_dir,
        )
        registry.load_all_plugins()

        # Get and enable plugin
        plugin = registry.get_plugin("test-integration-plugin")
        plugin.set_config_value(
            "TEST_INTEGRATION_DATA_DIR",
            integration_context.config["TEST_INTEGRATION_DATA_DIR"],
        )
        registry.enable_plugin("test-integration-plugin")
        plugin.on_enable()

        # Create MCP tools (this loads state)
        tools = plugin.create_mcp_tools(integration_context)
        tool_dict = {tool.__name__: tool for tool in tools}

        # Create multiple items
        create_item = tool_dict["create_item"]
        create_item("Item 1", "First item")
        create_item("Item 2", "Second item")

        # Verify state was updated
        item_count = integration_context.get_state("item_count", 0)
        assert item_count == 2, "item_count state should be updated"

        # Verify last_create timestamp was set
        last_create = integration_context.get_state("last_create")
        assert last_create is not None, "last_create timestamp should be set"

        # Verify state file was created
        state_file = (
            integration_context.spec_dir / ".test-integration-plugin_state.json"
        )
        assert state_file.exists(), "State file should be created"

        # Load state file and verify contents
        with open(state_file) as f:
            saved_state = json.load(f)

        assert saved_state["item_count"] == 2
        assert "last_create" in saved_state

    def test_mcp_tool_error_handling(
        self, user_plugins_dir, install_test_integration_plugin, integration_context
    ):
        """Test that MCP tools handle errors gracefully."""
        # Create registry and load plugins
        registry = PluginRegistry.get_instance(
            user_plugins_dir=user_plugins_dir,
            project_dir=integration_context.project_dir,
        )
        registry.load_all_plugins()

        # Get and enable plugin
        plugin = registry.get_plugin("test-integration-plugin")
        plugin.set_config_value(
            "TEST_INTEGRATION_DATA_DIR",
            integration_context.config["TEST_INTEGRATION_DATA_DIR"],
        )
        registry.enable_plugin("test-integration-plugin")
        plugin.on_enable()

        # Create MCP tools
        tools = plugin.create_mcp_tools(integration_context)
        tool_dict = {tool.__name__: tool for tool in tools}

        # Test 1: Get non-existent item
        get_item = tool_dict["get_item"]
        result = get_item(99999)
        result_data = json.loads(result)

        assert "error" in result_data, "Should return error for non-existent item"
        assert "not found" in result_data["error"].lower()

        # Test 2: Update non-existent item
        update_item = tool_dict["update_item"]
        result = update_item(99999, "new value")
        result_data = json.loads(result)

        assert "error" in result_data, "Should return error for non-existent item"

    def test_mcp_server_creation(
        self, user_plugins_dir, install_test_integration_plugin, integration_context
    ):
        """Test that plugins can create MCP servers from their tools."""
        # Create registry and load plugins
        registry = PluginRegistry.get_instance(
            user_plugins_dir=user_plugins_dir,
            project_dir=integration_context.project_dir,
        )
        registry.load_all_plugins()

        # Get and enable plugin
        plugin = registry.get_plugin("test-integration-plugin")
        plugin.set_config_value(
            "TEST_INTEGRATION_DATA_DIR",
            integration_context.config["TEST_INTEGRATION_DATA_DIR"],
        )
        registry.enable_plugin("test-integration-plugin")
        plugin.on_enable()

        # Try to create MCP server
        try:
            mcp_server = plugin.create_mcp_server(integration_context)

            # If SDK is available, server should be created
            if mcp_server is not None:
                assert hasattr(mcp_server, "name"), "MCP server should have a name"
                # The server name should include the plugin name
                # (actual attribute name depends on SDK implementation)
        except ImportError:
            # If Claude SDK is not available, this is expected
            pytest.skip("Claude SDK not available for MCP server creation")

    def test_multiple_mcp_tool_contexts(
        self, user_plugins_dir, install_test_integration_plugin, temp_dir
    ):
        """Test that plugins can create tools for different contexts independently."""
        # Create registry
        registry = PluginRegistry.get_instance(user_plugins_dir=user_plugins_dir)
        registry.load_all_plugins()

        # Get and enable plugin
        plugin = registry.get_plugin("test-integration-plugin")
        registry.enable_plugin("test-integration-plugin")

        # Create two different contexts with different data directories
        context1_dir = temp_dir / "context1"
        context1_dir.mkdir()
        context1_spec = context1_dir / "spec1"
        context1_spec.mkdir()
        data_dir1 = temp_dir / "data1"
        data_dir1.mkdir()

        context1 = IntegrationContext(
            project_dir=context1_dir,
            spec_dir=context1_spec,
            config={"TEST_INTEGRATION_DATA_DIR": str(data_dir1)},
            state={},
            metadata={},
        )

        context2_dir = temp_dir / "context2"
        context2_dir.mkdir()
        context2_spec = context2_dir / "spec2"
        context2_spec.mkdir()
        data_dir2 = temp_dir / "data2"
        data_dir2.mkdir()

        context2 = IntegrationContext(
            project_dir=context2_dir,
            spec_dir=context2_spec,
            config={"TEST_INTEGRATION_DATA_DIR": str(data_dir2)},
            state={},
            metadata={},
        )

        # Set config and enable for context 1
        plugin.set_config_value("TEST_INTEGRATION_DATA_DIR", str(data_dir1))
        plugin.on_enable()

        # Create tools for context 1
        tools1 = plugin.create_mcp_tools(context1)
        tool_dict1 = {tool.__name__: tool for tool in tools1}

        # Create item in context 1
        create_item1 = tool_dict1["create_item"]
        result1 = create_item1("Context1 Item", "Item in context 1")
        _item1_data = json.loads(result1)  # noqa: F841

        # Re-enable with context 2 config
        plugin.on_disable()
        plugin.set_config_value("TEST_INTEGRATION_DATA_DIR", str(data_dir2))
        plugin.on_enable()

        # Create tools for context 2
        tools2 = plugin.create_mcp_tools(context2)
        tool_dict2 = {tool.__name__: tool for tool in tools2}

        # Create item in context 2
        create_item2 = tool_dict2["create_item"]
        result2 = create_item2("Context2 Item", "Item in context 2")
        _item2_data = json.loads(result2)  # noqa: F841

        # List items in context 2 (should only have context 2 item)
        list_items2 = tool_dict2["list_items"]
        result2_list = list_items2()
        items2 = json.loads(result2_list)

        # Context 2 should only have its own item
        assert len(items2) == 1
        assert items2[0]["name"] == "Context2 Item"

        # Verify items are in different data directories
        items1_file = data_dir1 / "items.json"
        items2_file = data_dir2 / "items.json"

        assert items1_file.exists()
        assert items2_file.exists()

        with open(items1_file) as f:
            items1_data = json.load(f)
        with open(items2_file) as f:
            items2_data = json.load(f)

        assert len(items1_data) == 1
        assert len(items2_data) == 1
        assert items1_data[0]["name"] == "Context1 Item"
        assert items2_data[0]["name"] == "Context2 Item"

    def test_integration_plugin_availability(
        self,
        user_plugins_dir,
        install_test_integration_plugin,
        integration_context,
        temp_dir,
    ):
        """Test that is_available() correctly reports plugin availability."""
        # Use a fresh data directory for this test
        fresh_data_dir = temp_dir / "fresh_test_data"
        fresh_data_dir.mkdir(parents=True, exist_ok=True)

        # Create registry and load plugins
        registry = PluginRegistry.get_instance(
            user_plugins_dir=user_plugins_dir,
            project_dir=integration_context.project_dir,
        )
        registry.load_all_plugins()

        # Get plugin (not enabled yet)
        plugin = registry.get_plugin("test-integration-plugin")

        # Ensure plugin starts in clean state
        plugin.data_store = None
        plugin._enabled = False

        # Before enable, should not be available
        assert not plugin.is_available(), "Plugin should not be available before enable"

        # Enable plugin
        plugin.set_config_value("TEST_INTEGRATION_DATA_DIR", str(fresh_data_dir))
        registry.enable_plugin("test-integration-plugin")
        plugin.on_enable()

        # After enable, should be available
        assert plugin.is_available(), "Plugin should be available after enable"

        # Disable plugin
        plugin.on_disable()
        registry.disable_plugin("test-integration-plugin")

        # After disable, should not be available
        assert not plugin.is_available(), "Plugin should not be available after disable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
