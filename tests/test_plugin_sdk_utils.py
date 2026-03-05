#!/usr/bin/env python3
"""
Tests for Plugin SDK Utilities
===============================

Tests the plugins/sdk/utils.py module functionality including:
- PluginFileManager: File I/O operations with permission checking
- PluginConfigManager: Configuration management from environment variables
- PluginStateManager: Persistent state management
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from plugins.base import PermissionDeniedError, PluginPermission
from plugins.sdk.utils import (
    PluginConfigManager,
    PluginFileManager,
    PluginStateManager,
)


class TestPluginFileManager:
    """Tests for PluginFileManager file operations."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def file_manager_with_read(self, temp_project_dir):
        """Create file manager with READ_FILES permission."""
        return PluginFileManager(
            project_dir=temp_project_dir,
            permissions=[PluginPermission.READ_FILES],
            plugin_name="test-plugin",
        )

    @pytest.fixture
    def file_manager_with_write(self, temp_project_dir):
        """Create file manager with WRITE_FILES permission."""
        return PluginFileManager(
            project_dir=temp_project_dir,
            permissions=[PluginPermission.WRITE_FILES],
            plugin_name="test-plugin",
        )

    @pytest.fixture
    def file_manager_with_both(self, temp_project_dir):
        """Create file manager with both READ and WRITE permissions."""
        return PluginFileManager(
            project_dir=temp_project_dir,
            permissions=[PluginPermission.READ_FILES, PluginPermission.WRITE_FILES],
            plugin_name="test-plugin",
        )

    def test_init_creates_manager(self, temp_project_dir):
        """Initializes file manager with correct attributes."""
        manager = PluginFileManager(
            project_dir=temp_project_dir,
            permissions=[PluginPermission.READ_FILES],
            plugin_name="my-plugin",
        )
        assert manager.project_dir == temp_project_dir.resolve()
        assert manager.plugin_name == "my-plugin"
        assert PluginPermission.READ_FILES in manager.permissions

    def test_read_file_with_permission(self, file_manager_with_read, temp_project_dir):
        """Reads file content with READ_FILES permission."""
        test_file = temp_project_dir / "test.txt"
        test_file.write_text("Hello, World!")

        content = file_manager_with_read.read_file("test.txt")
        assert content == "Hello, World!"

    def test_read_file_without_permission(self, file_manager_with_write, temp_project_dir):
        """Raises PermissionDeniedError when reading without READ_FILES permission."""
        test_file = temp_project_dir / "test.txt"
        test_file.write_text("Hello")

        with pytest.raises(PermissionDeniedError) as exc_info:
            file_manager_with_write.read_file("test.txt")
        assert "read_files" in str(exc_info.value).lower()

    def test_write_file_with_permission(self, file_manager_with_write, temp_project_dir):
        """Writes file content with WRITE_FILES permission."""
        file_manager_with_write.write_file("test.txt", "Hello, World!")

        test_file = temp_project_dir / "test.txt"
        assert test_file.exists()
        assert test_file.read_text() == "Hello, World!"

    def test_write_file_without_permission(self, file_manager_with_read):
        """Raises PermissionDeniedError when writing without WRITE_FILES permission."""
        with pytest.raises(PermissionDeniedError) as exc_info:
            file_manager_with_read.write_file("test.txt", "Hello")
        assert "write_files" in str(exc_info.value).lower()

    def test_write_file_creates_dirs(self, file_manager_with_write, temp_project_dir):
        """Creates parent directories when writing file."""
        file_manager_with_write.write_file("subdir/nested/test.txt", "Hello")

        test_file = temp_project_dir / "subdir" / "nested" / "test.txt"
        assert test_file.exists()
        assert test_file.read_text() == "Hello"

    def test_read_json_valid_dict(self, file_manager_with_both, temp_project_dir):
        """Reads and parses JSON file containing dict."""
        test_file = temp_project_dir / "data.json"
        test_file.write_text('{"key": "value", "number": 42}')

        data = file_manager_with_both.read_json("data.json")
        assert data == {"key": "value", "number": 42}

    def test_read_json_valid_list(self, file_manager_with_both, temp_project_dir):
        """Reads and parses JSON file containing list."""
        test_file = temp_project_dir / "data.json"
        test_file.write_text('[1, 2, 3, "four"]')

        data = file_manager_with_both.read_json("data.json")
        assert data == [1, 2, 3, "four"]

    def test_read_json_invalid(self, file_manager_with_both, temp_project_dir):
        """Raises ValueError for invalid JSON."""
        test_file = temp_project_dir / "invalid.json"
        test_file.write_text("not valid json {")

        with pytest.raises(ValueError) as exc_info:
            file_manager_with_both.read_json("invalid.json")
        assert "Invalid JSON" in str(exc_info.value)

    def test_write_json_dict(self, file_manager_with_both, temp_project_dir):
        """Writes dict as formatted JSON file."""
        data = {"key": "value", "nested": {"x": 1, "y": 2}}
        file_manager_with_both.write_json("output.json", data)

        test_file = temp_project_dir / "output.json"
        assert test_file.exists()
        loaded = json.loads(test_file.read_text())
        assert loaded == data

    def test_write_json_list(self, file_manager_with_both, temp_project_dir):
        """Writes list as formatted JSON file."""
        data = [1, 2, {"key": "value"}]
        file_manager_with_both.write_json("output.json", data)

        test_file = temp_project_dir / "output.json"
        assert test_file.exists()
        loaded = json.loads(test_file.read_text())
        assert loaded == data

    def test_write_json_custom_indent(self, file_manager_with_both, temp_project_dir):
        """Writes JSON with custom indentation."""
        data = {"key": "value"}
        file_manager_with_both.write_json("output.json", data, indent=4)

        test_file = temp_project_dir / "output.json"
        content = test_file.read_text()
        assert "    " in content  # 4-space indent

    def test_write_json_unserializable(self, file_manager_with_both):
        """Raises ValueError for non-serializable data."""
        # Functions are not JSON-serializable
        data = {"func": lambda x: x}

        with pytest.raises(ValueError) as exc_info:
            file_manager_with_both.write_json("output.json", data)
        assert "Cannot serialize" in str(exc_info.value)

    def test_file_exists_true(self, file_manager_with_both, temp_project_dir):
        """Returns True for existing file."""
        test_file = temp_project_dir / "exists.txt"
        test_file.write_text("content")

        assert file_manager_with_both.file_exists("exists.txt") is True

    def test_file_exists_false(self, file_manager_with_both):
        """Returns False for non-existent file."""
        assert file_manager_with_both.file_exists("nonexistent.txt") is False

    def test_file_exists_for_directory(self, file_manager_with_both, temp_project_dir):
        """Returns False for directory path."""
        subdir = temp_project_dir / "subdir"
        subdir.mkdir()

        assert file_manager_with_both.file_exists("subdir") is False

    def test_dir_exists_true(self, file_manager_with_both, temp_project_dir):
        """Returns True for existing directory."""
        subdir = temp_project_dir / "subdir"
        subdir.mkdir()

        assert file_manager_with_both.dir_exists("subdir") is True

    def test_dir_exists_false(self, file_manager_with_both):
        """Returns False for non-existent directory."""
        assert file_manager_with_both.dir_exists("nonexistent") is False

    def test_dir_exists_for_file(self, file_manager_with_both, temp_project_dir):
        """Returns False for file path."""
        test_file = temp_project_dir / "file.txt"
        test_file.write_text("content")

        assert file_manager_with_both.dir_exists("file.txt") is False

    def test_list_files_simple(self, file_manager_with_read, temp_project_dir):
        """Lists files in directory with default pattern."""
        (temp_project_dir / "file1.txt").write_text("a")
        (temp_project_dir / "file2.txt").write_text("b")
        (temp_project_dir / "file3.md").write_text("c")

        files = file_manager_with_read.list_files()
        file_names = [f.name for f in files]

        assert len(files) == 3
        assert "file1.txt" in file_names
        assert "file2.txt" in file_names
        assert "file3.md" in file_names

    def test_list_files_with_pattern(self, file_manager_with_read, temp_project_dir):
        """Lists files matching glob pattern."""
        (temp_project_dir / "file1.txt").write_text("a")
        (temp_project_dir / "file2.txt").write_text("b")
        (temp_project_dir / "file3.md").write_text("c")

        files = file_manager_with_read.list_files(pattern="*.txt")
        file_names = [f.name for f in files]

        assert len(files) == 2
        assert "file1.txt" in file_names
        assert "file2.txt" in file_names
        assert "file3.md" not in file_names

    def test_list_files_recursive(self, file_manager_with_read, temp_project_dir):
        """Lists files recursively in subdirectories."""
        (temp_project_dir / "file1.txt").write_text("a")
        subdir = temp_project_dir / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("b")
        nested = subdir / "nested"
        nested.mkdir()
        (nested / "file3.txt").write_text("c")

        files = file_manager_with_read.list_files(recursive=True)
        file_names = [f.name for f in files]

        assert len(files) == 3
        assert "file1.txt" in file_names
        assert "file2.txt" in file_names
        assert "file3.txt" in file_names

    def test_list_files_in_subdir(self, file_manager_with_read, temp_project_dir):
        """Lists files in specific subdirectory."""
        (temp_project_dir / "root.txt").write_text("a")
        subdir = temp_project_dir / "subdir"
        subdir.mkdir()
        (subdir / "sub1.txt").write_text("b")
        (subdir / "sub2.txt").write_text("c")

        files = file_manager_with_read.list_files(path="subdir")
        file_names = [f.name for f in files]

        assert len(files) == 2
        assert "sub1.txt" in file_names
        assert "sub2.txt" in file_names
        assert "root.txt" not in file_names

    def test_list_files_without_permission(self, file_manager_with_write):
        """Raises PermissionDeniedError when listing without READ_FILES permission."""
        with pytest.raises(PermissionDeniedError) as exc_info:
            file_manager_with_write.list_files()
        assert "read_files" in str(exc_info.value).lower()

    def test_resolve_path_relative(self, file_manager_with_both, temp_project_dir):
        """Resolves relative path correctly."""
        resolved = file_manager_with_both._resolve_path("subdir/file.txt")
        expected = (temp_project_dir / "subdir" / "file.txt").resolve()
        assert resolved == expected

    def test_resolve_path_absolute(self, file_manager_with_both, temp_project_dir):
        """Resolves absolute path within project directory."""
        abs_path = temp_project_dir / "file.txt"
        resolved = file_manager_with_both._resolve_path(abs_path)
        assert resolved == abs_path.resolve()

    def test_resolve_path_outside_project_raises(self, file_manager_with_both, temp_project_dir):
        """Raises ValueError for path outside project directory."""
        outside_path = temp_project_dir.parent / "outside.txt"

        with pytest.raises(ValueError) as exc_info:
            file_manager_with_both._resolve_path(outside_path)
        assert "outside project directory" in str(exc_info.value)

    def test_resolve_path_traversal_blocked(self, file_manager_with_both):
        """Blocks path traversal attempts."""
        with pytest.raises(ValueError) as exc_info:
            file_manager_with_both._resolve_path("../../etc/passwd")
        assert "outside project directory" in str(exc_info.value)


class TestPluginConfigManager:
    """Tests for PluginConfigManager configuration management."""

    @pytest.fixture
    def clean_env(self):
        """Clean environment for each test."""
        # Store original env
        original_env = dict(os.environ)

        # Clear test-related vars
        for key in list(os.environ.keys()):
            if key.startswith("TEST_PLUGIN_"):
                del os.environ[key]

        yield

        # Restore original env
        os.environ.clear()
        os.environ.update(original_env)

    def test_init_with_default_prefix(self, clean_env):
        """Initializes with uppercase plugin name as prefix."""
        manager = PluginConfigManager(plugin_name="my-plugin")
        assert manager.plugin_name == "my-plugin"
        assert manager.prefix == "MY_PLUGIN"

    def test_init_with_custom_prefix(self, clean_env):
        """Initializes with custom prefix."""
        manager = PluginConfigManager(plugin_name="my-plugin", prefix="CUSTOM")
        assert manager.prefix == "CUSTOM"

    def test_init_with_required_keys_present(self, clean_env):
        """Initializes successfully when required keys are set."""
        os.environ["TEST_PLUGIN_API_KEY"] = "secret"
        os.environ["TEST_PLUGIN_API_URL"] = "https://api.example.com"

        manager = PluginConfigManager(
            plugin_name="test-plugin",
            required_keys=["API_KEY", "API_URL"],
        )
        assert manager.has_all_required() is True

    def test_init_with_required_keys_missing(self, clean_env):
        """Raises ValueError when required keys are missing."""
        os.environ["TEST_PLUGIN_API_KEY"] = "secret"
        # API_URL is missing

        with pytest.raises(ValueError) as exc_info:
            PluginConfigManager(
                plugin_name="test-plugin",
                required_keys=["API_KEY", "API_URL"],
            )
        assert "Missing required configuration keys" in str(exc_info.value)
        assert "API_URL" in str(exc_info.value)

    def test_get_existing_key(self, clean_env):
        """Gets value for existing key."""
        os.environ["TEST_PLUGIN_MY_KEY"] = "my_value"

        manager = PluginConfigManager(plugin_name="test-plugin")
        value = manager.get("MY_KEY")

        assert value == "my_value"

    def test_get_missing_key_with_default(self, clean_env):
        """Returns default for missing key."""
        manager = PluginConfigManager(plugin_name="test-plugin")
        value = manager.get("MISSING_KEY", default="default_value")

        assert value == "default_value"

    def test_get_missing_key_without_default(self, clean_env):
        """Returns None for missing key without default."""
        manager = PluginConfigManager(plugin_name="test-plugin")
        value = manager.get("MISSING_KEY")

        assert value is None

    def test_get_required_existing_key(self, clean_env):
        """Gets required key that exists."""
        os.environ["TEST_PLUGIN_REQUIRED_KEY"] = "required_value"

        manager = PluginConfigManager(plugin_name="test-plugin")
        value = manager.get_required("REQUIRED_KEY")

        assert value == "required_value"

    def test_get_required_missing_key(self, clean_env):
        """Raises ValueError for missing required key."""
        manager = PluginConfigManager(plugin_name="test-plugin")

        with pytest.raises(ValueError) as exc_info:
            manager.get_required("REQUIRED_KEY")
        assert "Required configuration key" in str(exc_info.value)
        assert "REQUIRED_KEY" in str(exc_info.value)

    def test_get_bool_true_values(self, clean_env):
        """Parses various true values as boolean."""
        manager = PluginConfigManager(plugin_name="test-plugin")

        for value in ["true", "TRUE", "True", "1", "yes", "YES", "on", "ON"]:
            os.environ["TEST_PLUGIN_BOOL_KEY"] = value
            assert manager.get_bool("BOOL_KEY") is True

    def test_get_bool_false_values(self, clean_env):
        """Parses various false values as boolean."""
        manager = PluginConfigManager(plugin_name="test-plugin")

        for value in ["false", "FALSE", "False", "0", "no", "NO", "off", "OFF"]:
            os.environ["TEST_PLUGIN_BOOL_KEY"] = value
            assert manager.get_bool("BOOL_KEY") is False

    def test_get_bool_with_default(self, clean_env):
        """Returns default for missing boolean key."""
        manager = PluginConfigManager(plugin_name="test-plugin")

        assert manager.get_bool("MISSING_BOOL", default=True) is True
        assert manager.get_bool("MISSING_BOOL", default=False) is False

    def test_get_int_valid(self, clean_env):
        """Parses valid integer value."""
        os.environ["TEST_PLUGIN_INT_KEY"] = "42"

        manager = PluginConfigManager(plugin_name="test-plugin")
        value = manager.get_int("INT_KEY")

        assert value == 42

    def test_get_int_negative(self, clean_env):
        """Parses negative integer value."""
        os.environ["TEST_PLUGIN_INT_KEY"] = "-10"

        manager = PluginConfigManager(plugin_name="test-plugin")
        value = manager.get_int("INT_KEY")

        assert value == -10

    def test_get_int_invalid(self, clean_env):
        """Raises ValueError for invalid integer."""
        os.environ["TEST_PLUGIN_INT_KEY"] = "not_a_number"

        manager = PluginConfigManager(plugin_name="test-plugin")

        with pytest.raises(ValueError) as exc_info:
            manager.get_int("INT_KEY")
        assert "must be an integer" in str(exc_info.value)

    def test_get_int_with_default(self, clean_env):
        """Returns default for missing integer key."""
        manager = PluginConfigManager(plugin_name="test-plugin")
        value = manager.get_int("MISSING_INT", default=100)

        assert value == 100

    def test_get_all(self, clean_env):
        """Gets all configuration values for plugin."""
        os.environ["TEST_PLUGIN_KEY1"] = "value1"
        os.environ["TEST_PLUGIN_KEY2"] = "value2"
        os.environ["OTHER_PLUGIN_KEY"] = "other"

        manager = PluginConfigManager(plugin_name="test-plugin")
        config = manager.get_all()

        assert config == {"KEY1": "value1", "KEY2": "value2"}
        assert "KEY" not in config  # OTHER_PLUGIN_KEY should not be included

    def test_get_missing_keys(self, clean_env):
        """Gets list of missing required keys."""
        os.environ["TEST_PLUGIN_KEY1"] = "value1"

        # Create manager without required keys first
        manager = PluginConfigManager(plugin_name="test-plugin")

        # Manually set required keys for testing
        manager.required_keys = ["KEY1", "KEY2", "KEY3"]
        missing = manager.get_missing_keys()

        assert len(missing) == 2
        assert "KEY2" in missing
        assert "KEY3" in missing
        assert "KEY1" not in missing

    def test_has_all_required_true(self, clean_env):
        """Returns True when all required keys are set."""
        os.environ["TEST_PLUGIN_KEY1"] = "value1"
        os.environ["TEST_PLUGIN_KEY2"] = "value2"

        manager = PluginConfigManager(
            plugin_name="test-plugin",
            required_keys=["KEY1", "KEY2"],
        )

        assert manager.has_all_required() is True

    def test_has_all_required_false(self, clean_env):
        """Returns False when required keys are missing."""
        os.environ["TEST_PLUGIN_KEY1"] = "value1"

        # Create manager without validation
        manager = PluginConfigManager(plugin_name="test-plugin")
        manager.required_keys = ["KEY1", "KEY2"]

        assert manager.has_all_required() is False


class TestPluginStateManager:
    """Tests for PluginStateManager persistent state management."""

    @pytest.fixture
    def temp_state_dir(self):
        """Create temporary state directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def state_manager(self, temp_state_dir):
        """Create state manager with temporary directory."""
        return PluginStateManager(
            plugin_name="test-plugin",
            state_dir=temp_state_dir,
        )

    def test_init_creates_manager(self, temp_state_dir):
        """Initializes state manager with correct attributes."""
        manager = PluginStateManager(
            plugin_name="my-plugin",
            state_dir=temp_state_dir,
        )

        assert manager.plugin_name == "my-plugin"
        assert manager.state_dir == temp_state_dir
        assert manager.state_file == temp_state_dir / "state.json"

    def test_init_with_default_dir(self):
        """Uses default state directory when not specified."""
        manager = PluginStateManager(plugin_name="my-plugin")
        expected_dir = Path.cwd() / ".auto-claude" / "plugin_state" / "my-plugin"

        assert manager.state_dir == expected_dir

    def test_get_with_existing_key(self, state_manager):
        """Gets value for existing state key."""
        state_manager.set("my_key", "my_value")
        value = state_manager.get("my_key")

        assert value == "my_value"

    def test_get_with_missing_key(self, state_manager):
        """Returns None for missing state key."""
        value = state_manager.get("missing_key")

        assert value is None

    def test_get_with_default(self, state_manager):
        """Returns default for missing state key."""
        value = state_manager.get("missing_key", default="default_value")

        assert value == "default_value"

    def test_set_string_value(self, state_manager):
        """Sets string state value."""
        state_manager.set("string_key", "string_value")
        assert state_manager.get("string_key") == "string_value"

    def test_set_number_value(self, state_manager):
        """Sets number state value."""
        state_manager.set("number_key", 42)
        assert state_manager.get("number_key") == 42

    def test_set_dict_value(self, state_manager):
        """Sets dict state value."""
        data = {"nested": {"key": "value"}}
        state_manager.set("dict_key", data)
        assert state_manager.get("dict_key") == data

    def test_set_list_value(self, state_manager):
        """Sets list state value."""
        data = [1, 2, {"key": "value"}]
        state_manager.set("list_key", data)
        assert state_manager.get("list_key") == data

    def test_set_unserializable_value(self, state_manager):
        """Raises ValueError for non-serializable value."""
        # Functions are not JSON-serializable
        with pytest.raises(ValueError) as exc_info:
            state_manager.set("func_key", lambda x: x)
        assert "JSON-serializable" in str(exc_info.value)

    def test_delete_existing_key(self, state_manager):
        """Deletes existing state key."""
        state_manager.set("key_to_delete", "value")
        assert state_manager.has_key("key_to_delete") is True

        state_manager.delete("key_to_delete")
        assert state_manager.has_key("key_to_delete") is False

    def test_delete_missing_key(self, state_manager):
        """Deleting missing key does nothing."""
        state_manager.delete("missing_key")  # Should not raise

    def test_clear_all_state(self, state_manager):
        """Clears all state data."""
        state_manager.set("key1", "value1")
        state_manager.set("key2", "value2")
        assert len(state_manager.get_all()) == 2

        state_manager.clear()
        assert len(state_manager.get_all()) == 0

    def test_get_all_returns_copy(self, state_manager):
        """get_all returns copy of state, not reference."""
        state_manager.set("key", "value")
        all_state = state_manager.get_all()

        # Modify returned dict
        all_state["new_key"] = "new_value"

        # Original state should be unchanged
        assert state_manager.has_key("new_key") is False

    def test_update_multiple_values(self, state_manager):
        """Updates state with multiple values."""
        data = {"key1": "value1", "key2": 42, "key3": ["a", "b"]}
        state_manager.update(data)

        assert state_manager.get("key1") == "value1"
        assert state_manager.get("key2") == 42
        assert state_manager.get("key3") == ["a", "b"]

    def test_update_with_unserializable_value(self, state_manager):
        """Raises ValueError for non-serializable update data."""
        data = {"func": lambda x: x}

        with pytest.raises(ValueError) as exc_info:
            state_manager.update(data)
        assert "JSON-serializable" in str(exc_info.value)

    def test_has_key_true(self, state_manager):
        """Returns True for existing key."""
        state_manager.set("existing_key", "value")
        assert state_manager.has_key("existing_key") is True

    def test_has_key_false(self, state_manager):
        """Returns False for missing key."""
        assert state_manager.has_key("missing_key") is False

    def test_save_creates_file(self, state_manager, temp_state_dir):
        """Saves state to JSON file."""
        state_manager.set("key", "value")
        state_manager.save()

        state_file = temp_state_dir / "state.json"
        assert state_file.exists()

        with open(state_file, "r") as f:
            data = json.load(f)
        assert data == {"key": "value"}

    def test_save_creates_directory(self, temp_state_dir):
        """Creates state directory if it doesn't exist."""
        state_dir = temp_state_dir / "nested" / "dir"
        manager = PluginStateManager(plugin_name="test-plugin", state_dir=state_dir)

        manager.set("key", "value")
        manager.save()

        assert state_dir.exists()
        assert (state_dir / "state.json").exists()

    def test_load_existing_file(self, state_manager, temp_state_dir):
        """Loads state from existing file."""
        # Create state file manually
        state_file = temp_state_dir / "state.json"
        state_data = {"key1": "value1", "key2": 42}
        with open(state_file, "w") as f:
            json.dump(state_data, f)

        # Create new manager and load
        manager = PluginStateManager(plugin_name="test-plugin", state_dir=temp_state_dir)
        manager.load()

        assert manager.get("key1") == "value1"
        assert manager.get("key2") == 42

    def test_load_missing_file(self, state_manager):
        """Loads empty state when file doesn't exist."""
        state_manager.load()
        assert state_manager.get_all() == {}

    def test_load_invalid_json(self, state_manager, temp_state_dir):
        """Loads empty state when JSON is invalid."""
        # Create invalid JSON file
        state_file = temp_state_dir / "state.json"
        state_file.write_text("not valid json {")

        state_manager.load()
        assert state_manager.get_all() == {}

    def test_auto_load_on_first_access(self, temp_state_dir):
        """Auto-loads state on first access."""
        # Create state file
        state_file = temp_state_dir / "state.json"
        with open(state_file, "w") as f:
            json.dump({"auto_key": "auto_value"}, f)

        # Create manager (doesn't load immediately)
        manager = PluginStateManager(plugin_name="test-plugin", state_dir=temp_state_dir)

        # First access should auto-load
        value = manager.get("auto_key")
        assert value == "auto_value"

    def test_persistence_across_instances(self, temp_state_dir):
        """State persists across manager instances."""
        # First manager sets state
        manager1 = PluginStateManager(plugin_name="test-plugin", state_dir=temp_state_dir)
        manager1.set("persistent_key", "persistent_value")
        manager1.save()

        # Second manager loads state
        manager2 = PluginStateManager(plugin_name="test-plugin", state_dir=temp_state_dir)
        value = manager2.get("persistent_key")

        assert value == "persistent_value"
