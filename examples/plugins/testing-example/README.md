# Testing Example Plugin

A comprehensive example demonstrating how to write tests for Auto Code plugins. This plugin includes a complete test suite showing testing patterns, best practices, and the use of Auto Code's testing utilities.

## Overview

This plugin demonstrates:
- **Unit testing** individual plugin methods
- **Lifecycle testing** for plugin hooks
- **Mock contexts** for isolated testing
- **State management** testing
- **Error handling** and edge cases
- **Integration testing** combining multiple features
- **Best practices** for maintainable tests

## What It Does

The plugin itself:
- Tracks session statistics (total, successful, failed)
- Records unique specs processed
- Supports feature toggles for behavior control
- Validates spec directory and counts files
- Provides debug information on demand
- Demonstrates testable plugin architecture

## Test Coverage

The test suite (`test_plugin.py`) includes:

### 1. Metadata Tests
- Plugin type validation
- Required permissions checking
- Initialization state verification

### 2. Lifecycle Tests
- `on_load()` feature initialization
- `on_enable()` statistics reset
- `on_disable()` cleanup
- `on_unload()` final state
- Complete lifecycle flow

### 3. Session Tracking Tests
- Session counter incrementation
- Unique spec name tracking
- Success/failure counting
- Success rate calculation
- Statistics in context metadata

### 4. Context Metadata Tests
- Debug mode activation
- Debug info injection
- Spec directory validation
- File counting operations

### 5. Feature Toggle Tests
- Enabling/disabling features
- Feature impact on behavior
- Dynamic behavior changes

### 6. Statistics API Tests
- `get_stats()` accuracy
- `reset_stats()` clearing
- Edge cases (zero sessions)

### 7. Error Handling Tests
- Missing directory handling
- Division by zero prevention
- Graceful degradation

### 8. Integration Tests
- Complete session workflows
- Multiple feature combinations
- Real-world usage scenarios

## Installation

### Prerequisites

Install test dependencies:
```bash
cd apps/backend
uv pip install -r ../../tests/requirements-test.txt
```

### From Directory

1. **Copy the plugin directory**:
   ```bash
   cp -r examples/plugins/testing-example ~/.auto-claude/plugins/user/
   ```

2. **Verify installation**:
   ```bash
   python -c "from apps.backend.plugins.loader import PluginLoader; loader = PluginLoader(); plugin = loader.load_plugin('examples/plugins/testing-example'); print('OK')"
   ```

## Running Tests

### Run All Tests

```bash
# From project root
pytest examples/plugins/testing-example/test_plugin.py -v

# Or with coverage
pytest examples/plugins/testing-example/test_plugin.py -v --cov=examples.plugins.testing-example
```

### Run Specific Test Classes

```bash
# Test only lifecycle hooks
pytest examples/plugins/testing-example/test_plugin.py::TestPluginLifecycle -v

# Test only session tracking
pytest examples/plugins/testing-example/test_plugin.py::TestSessionTracking -v

# Test only error handling
pytest examples/plugins/testing-example/test_plugin.py::TestErrorHandling -v
```

### Run Specific Tests

```bash
# Test a single test method
pytest examples/plugins/testing-example/test_plugin.py::TestSessionTracking::test_before_session_increments_counter -v
```

## Testing Patterns Demonstrated

### 1. Using PluginTestCase

```python
from apps.backend.plugins.sdk.testing import PluginTestCase

testcase = PluginTestCase()

# Create plugin instance
plugin = testcase.create_plugin(TestingExamplePlugin, "test-plugin")

# Create and load plugin
plugin = testcase.load_plugin(TestingExamplePlugin, "test-plugin")

# Create, load, and enable plugin
plugin = testcase.enable_plugin(TestingExamplePlugin, "test-plugin")
```

### 2. Using MockAgentContext

```python
from apps.backend.plugins.sdk.testing import MockAgentContext

# As context manager (automatic cleanup)
with MockAgentContext() as context:
    plugin.before_session(context)
    assert context.metadata.get("initialized") is True

# With custom values
with MockAgentContext(
    session_id="custom-session",
    phase="implementation",
    metadata={"test": "value"}
) as context:
    plugin.before_session(context)
```

### 3. Testing Lifecycle Hooks

```python
def test_full_lifecycle(self):
    """Test complete plugin lifecycle."""
    testcase = PluginTestCase()
    plugin = testcase.create_plugin(TestingExamplePlugin, "test")

    # Load
    plugin.on_load()
    plugin._mark_loaded()
    assert plugin.is_loaded

    # Enable
    plugin.on_enable()
    plugin._mark_enabled()
    assert plugin.is_enabled

    # Disable
    plugin.on_disable()
    plugin._mark_disabled()
    assert not plugin.is_enabled

    # Unload
    plugin.on_unload()
    plugin._mark_unloaded()
    assert not plugin.is_loaded
```

### 4. Testing State Management

```python
def test_session_tracking(self):
    """Test session statistics tracking."""
    testcase = PluginTestCase()
    plugin = testcase.enable_plugin(TestingExamplePlugin, "test")

    # Run sessions
    for success in [True, True, False]:
        with MockAgentContext() as context:
            plugin.before_session(context)
            plugin.after_session(context, success=success)

    # Verify state
    assert plugin.total_sessions == 3
    assert plugin.successful_sessions == 2
    assert plugin.failed_sessions == 1
```

### 5. Testing Error Handling

```python
def test_handles_missing_directory(self):
    """Plugin should handle missing directories gracefully."""
    testcase = PluginTestCase()
    plugin = testcase.enable_plugin(TestingExamplePlugin, "test")

    with MockAgentContext() as context:
        # Delete directory
        import shutil
        shutil.rmtree(context.spec_dir)

        # Should not raise exception
        plugin.before_session(context)

        # Should handle gracefully
        assert context.metadata.get("spec_dir_exists") is False
```

### 6. Testing Context Metadata

```python
def test_context_metadata_modification(self):
    """Test plugin modifying context metadata."""
    testcase = PluginTestCase()
    plugin = testcase.enable_plugin(TestingExamplePlugin, "test")

    with MockAgentContext() as context:
        # Set flag in metadata
        context.metadata["enable_debug_mode"] = True

        plugin.before_session(context)

        # Verify plugin added debug info
        assert "debug_info" in context.metadata
        assert context.metadata["debug_info"]["spec_name"] == context.spec_name
```

## Best Practices

### 1. Organize Tests by Feature

Group related tests in classes:
- `TestPluginMetadata` - Metadata and initialization
- `TestPluginLifecycle` - Lifecycle hooks
- `TestSessionTracking` - Session functionality
- `TestErrorHandling` - Error cases
- `TestIntegration` - End-to-end workflows

### 2. Use Descriptive Test Names

```python
# Good - clearly states what is being tested
def test_before_session_increments_counter(self):
    """before_session should increment session counter."""
    ...

# Bad - vague, unclear purpose
def test_session(self):
    """Test session."""
    ...
```

### 3. Test One Thing Per Test

```python
# Good - focused on one aspect
def test_successful_sessions_counted(self):
    """after_session should increment successful_sessions when success=True."""
    ...

def test_failed_sessions_counted(self):
    """after_session should increment failed_sessions when success=False."""
    ...

# Bad - testing multiple things
def test_session_counting(self):
    """Test all session counting."""
    # Tests both success and failure
    ...
```

### 4. Use Context Managers for Cleanup

```python
# Good - automatic cleanup
with MockAgentContext() as context:
    plugin.before_session(context)
    # Context automatically cleaned up

# Acceptable - manual cleanup
context = MockAgentContext()
try:
    plugin.before_session(context)
finally:
    context.cleanup()
```

### 5. Test Edge Cases

```python
def test_handles_zero_sessions(self):
    """Statistics should handle zero sessions correctly."""
    plugin = testcase.enable_plugin(TestingExamplePlugin, "test")
    stats = plugin.get_stats()
    assert stats["success_rate"] == 0  # No division by zero
```

### 6. Use pytest Features

```python
# Approximate float comparisons
assert stats["success_rate"] == pytest.approx(66.67, rel=0.01)

# Exception testing
with pytest.raises(ValueError):
    plugin.invalid_operation()

# Parametrized tests
@pytest.mark.parametrize("success,expected", [
    (True, 1),
    (False, 0),
])
def test_success_tracking(self, success, expected):
    ...
```

## Writing Your Own Tests

### 1. Create Test File

Create `test_plugin.py` next to your plugin:

```
my-plugin/
├── plugin.json
├── agent.py          # or integration.py, ui.py
└── test_plugin.py    # Your tests
```

### 2. Import Testing Utilities

```python
from apps.backend.plugins.sdk.testing import (
    MockAgentContext,        # For agent plugins
    MockIntegrationContext,  # For integration plugins
    PluginTestCase,          # Helper methods
)
```

### 3. Write Tests

```python
class TestMyPlugin:
    """Tests for MyPlugin."""

    def test_plugin_loads(self):
        """Plugin should load successfully."""
        testcase = PluginTestCase()
        plugin = testcase.load_plugin(MyPlugin, "my-plugin")
        assert plugin.is_loaded

    def test_lifecycle_hook(self):
        """Plugin should handle lifecycle hooks."""
        testcase = PluginTestCase()
        plugin = testcase.enable_plugin(MyPlugin, "my-plugin")

        with MockAgentContext() as context:
            plugin.before_session(context)
            # Assert expected behavior
```

### 4. Run Tests

```bash
pytest path/to/my-plugin/test_plugin.py -v
```

## Troubleshooting

### Import Errors

If you get import errors:

```bash
# Run tests from project root
cd /path/to/Auto-Claude
pytest examples/plugins/testing-example/test_plugin.py -v

# Or add project to PYTHONPATH
export PYTHONPATH=/path/to/Auto-Claude:$PYTHONPATH
pytest examples/plugins/testing-example/test_plugin.py -v
```

### Test Discovery Issues

If pytest doesn't find your tests:
- Ensure test file is named `test_*.py` or `*_test.py`
- Ensure test classes are named `Test*`
- Ensure test methods are named `test_*`

### Cleanup Errors

If you get cleanup errors:
- Always use context managers (`with MockAgentContext()`)
- Or manually call `.cleanup()` in `finally` blocks
- Don't use deleted directories after cleanup

## Learn More

- [Plugin Testing Guide](../../../guides/plugins/testing-plugins.md)
- [Plugin SDK Documentation](../../../apps/backend/plugins/sdk/testing.py)
- [Agent Plugin Development](../../../guides/plugins/agent-plugins.md)
- [Plugin Getting Started](../../../guides/plugins/getting-started.md)

## License

MIT - See LICENSE file for details
