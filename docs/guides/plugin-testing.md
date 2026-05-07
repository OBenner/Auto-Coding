# Plugin Testing Guide

Complete guide to testing plugins for Auto Code, from unit tests to integration testing and manual validation.

## Table of Contents

- [Overview](#overview)
- [Testing Approach](#testing-approach)
- [Unit Testing](#unit-testing)
  - [Testing Agent Plugins](#testing-agent-plugins)
  - [Testing Integration Plugins](#testing-integration-plugins)
  - [Testing UI Plugins](#testing-ui-plugins)
  - [Testing MCP Tools](#testing-mcp-tools)
- [Integration Testing](#integration-testing)
- [Test Fixtures & Mocking](#test-fixtures--mocking)
- [Manual Testing](#manual-testing)
- [CI/CD Testing](#cicd-testing)
- [Performance Testing](#performance-testing)
- [Security Testing](#security-testing)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

Testing plugins ensures reliability, compatibility, and performance. Auto Code provides testing utilities and patterns for comprehensive plugin validation.

### Testing Layers

1. **Unit Tests** - Test individual plugin methods in isolation
2. **Integration Tests** - Test plugin interaction with Auto Code
3. **Manual Tests** - Verify end-to-end functionality with real agent sessions
4. **CI/CD Tests** - Automated testing in continuous integration

### Test Requirements

```bash
# Install test dependencies
cd apps/backend
uv pip install pytest pytest-asyncio pytest-cov pytest-mock

# For UI plugins, also install frontend test tools
cd apps/frontend
npm install --save-dev jest @testing-library/react @testing-library/jest-dom
```

---

## Testing Approach

### Test Structure

Organize tests alongside your plugin:

```
my-plugin/
├── plugin.json
├── agent.py                  # Plugin implementation
├── tests/                    # Test directory
│   ├── __init__.py
│   ├── test_lifecycle.py     # Test lifecycle hooks
│   ├── test_mcp_tools.py     # Test MCP tools
│   ├── test_integration.py   # Integration tests
│   └── fixtures/             # Test fixtures
│       ├── mock_context.py
│       └── sample_data.json
└── README.md
```

### Running Tests

```bash
# Run all plugin tests
pytest my-plugin/tests/ -v

# Run with coverage
pytest my-plugin/tests/ --cov=my-plugin --cov-report=html

# Run specific test file
pytest my-plugin/tests/test_lifecycle.py -v

# Run specific test
pytest my-plugin/tests/test_lifecycle.py::test_before_session -v
```

---

## Unit Testing

### Testing Agent Plugins

**Example**: Testing lifecycle hooks

```python
# tests/test_lifecycle.py
import pytest
from unittest.mock import MagicMock, patch
from agent import MyAgentPlugin
from plugins.sdk.agent import AgentContext

@pytest.fixture
def plugin():
    """Create plugin instance for testing."""
    return MyAgentPlugin(
        name="my-plugin",
        version="1.0.0",
        manifest_path="/path/to/plugin.json"
    )

@pytest.fixture
def mock_context():
    """Create mock AgentContext."""
    return AgentContext(
        spec_name="test-spec",
        spec_dir="/path/to/spec",
        project_dir="/path/to/project",
        agent_type="coder",
        model="claude-sonnet-4-5-20250929"
    )

def test_on_load(plugin):
    """Test plugin loads successfully."""
    plugin.on_load()
    # Assert plugin initialized correctly
    assert plugin.name == "my-plugin"

def test_on_enable(plugin):
    """Test plugin enables successfully."""
    plugin.on_enable()
    # Assert plugin is ready
    assert plugin._enabled is True

def test_before_session(plugin, mock_context):
    """Test before_session hook."""
    with patch('logging.info') as mock_log:
        plugin.before_session(mock_context)

        # Verify logging was called
        mock_log.assert_called_once()

        # Verify context was processed
        assert mock_context.spec_name == "test-spec"

def test_after_session_success(plugin, mock_context):
    """Test after_session hook with success."""
    result = plugin.after_session(mock_context, success=True)

    # Verify plugin handled success
    assert result is None  # or expected return value

def test_after_session_failure(plugin, mock_context):
    """Test after_session hook with failure."""
    result = plugin.after_session(mock_context, success=False)

    # Verify plugin handled failure
    assert result is None

def test_on_message(plugin, mock_context):
    """Test on_message hook."""
    message = {
        "role": "assistant",
        "content": "Test message"
    }

    plugin.on_message(mock_context, message)

    # Verify message was processed
    # Add assertions based on expected behavior

def test_on_disable(plugin):
    """Test plugin disables successfully."""
    plugin.on_enable()
    plugin.on_disable()

    assert plugin._enabled is False

def test_on_unload(plugin):
    """Test plugin unloads successfully."""
    plugin.on_load()
    plugin.on_unload()

    # Verify cleanup occurred
    # Add assertions based on expected cleanup
```

### Testing Integration Plugins

**Example**: Testing MCP tool creation and integration hooks

```python
# tests/test_integration.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from integration import MyIntegrationPlugin
from plugins.sdk.integration import IntegrationContext

@pytest.fixture
def plugin():
    """Create integration plugin instance."""
    return MyIntegrationPlugin(
        name="my-integration",
        version="1.0.0",
        manifest_path="/path/to/plugin.json"
    )

@pytest.fixture
def mock_context():
    """Create mock IntegrationContext."""
    return IntegrationContext(
        spec_name="test-spec",
        spec_dir="/path/to/spec",
        project_dir="/path/to/project"
    )

def test_is_available(plugin):
    """Test integration availability check."""
    # Mock external service connection
    with patch.object(plugin, '_check_service_connection', return_value=True):
        assert plugin.is_available() is True

    with patch.object(plugin, '_check_service_connection', return_value=False):
        assert plugin.is_available() is False

def test_create_mcp_tools(plugin, mock_context):
    """Test MCP tool creation."""
    tools = plugin.create_mcp_tools(mock_context)

    # Verify tools were created
    assert isinstance(tools, list)
    assert len(tools) > 0

    # Verify tool structure
    for tool in tools:
        assert callable(tool)
        assert hasattr(tool, '__name__')
        assert hasattr(tool, '__doc__')

@pytest.mark.asyncio
async def test_sync_data(plugin, mock_context):
    """Test data synchronization."""
    with patch.object(plugin, '_fetch_external_data', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = {"status": "success"}

        result = await plugin.sync_data(mock_context)

        assert result["status"] == "success"
        mock_fetch.assert_called_once()

def test_on_build_start(plugin, mock_context):
    """Test build start hook."""
    with patch.object(plugin, '_notify_external_service') as mock_notify:
        plugin.on_build_start(mock_context)

        mock_notify.assert_called_once_with(
            spec_name="test-spec",
            event="build_start"
        )

def test_on_build_complete_success(plugin, mock_context):
    """Test build complete hook with success."""
    with patch.object(plugin, '_update_external_status') as mock_update:
        plugin.on_build_complete(mock_context, success=True)

        mock_update.assert_called_once_with(status="completed")

def test_on_build_complete_failure(plugin, mock_context):
    """Test build complete hook with failure."""
    with patch.object(plugin, '_update_external_status') as mock_update:
        plugin.on_build_complete(mock_context, success=False)

        mock_update.assert_called_once_with(status="failed")

def test_on_subtask_update(plugin, mock_context):
    """Test subtask update hook."""
    plugin.on_subtask_update(mock_context, "subtask-1", "completed")

    # Verify subtask update was processed
    # Add assertions based on expected behavior
```

### Testing UI Plugins

**Example**: Testing React components and UI hooks

```javascript
// tests/ui.test.tsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MyUIPlugin } from '../ui';

describe('MyUIPlugin', () => {
  let plugin;

  beforeEach(() => {
    plugin = new MyUIPlugin({
      name: 'my-ui-plugin',
      version: '1.0.0',
      manifestPath: '/path/to/plugin.json'
    });
  });

  test('registers components', () => {
    const components = plugin.registerComponents();

    expect(components).toHaveLength(1);
    expect(components[0].name).toBe('MyCustomView');
  });

  test('registers menu items', () => {
    const menuItems = plugin.registerMenuItems();

    expect(menuItems).toHaveLength(1);
    expect(menuItems[0].label).toBe('My Plugin');
  });

  test('custom component renders', () => {
    const { MyCustomView } = plugin.registerComponents()[0].component;

    render(<MyCustomView />);

    expect(screen.getByText('My Custom View')).toBeInTheDocument();
  });

  test('button click handler', () => {
    const mockOnClick = jest.fn();
    const { MyCustomView } = plugin.registerComponents()[0].component;

    render(<MyCustomView onClick={mockOnClick} />);

    const button = screen.getByRole('button', { name: /click me/i });
    fireEvent.click(button);

    expect(mockOnClick).toHaveBeenCalledTimes(1);
  });

  test('keyboard shortcut registration', () => {
    const shortcuts = plugin.registerKeyboardShortcuts();

    expect(shortcuts).toHaveLength(1);
    expect(shortcuts[0].key).toBe('Ctrl+Shift+M');
  });
});
```

### Testing MCP Tools

**Example**: Testing custom MCP tools

```python
# tests/test_mcp_tools.py
import pytest
from unittest.mock import MagicMock, patch
from integration import MyIntegrationPlugin
from plugins.sdk.integration import IntegrationContext

@pytest.fixture
def plugin():
    return MyIntegrationPlugin(
        name="my-integration",
        version="1.0.0",
        manifest_path="/path/to/plugin.json"
    )

@pytest.fixture
def mock_context():
    return IntegrationContext(
        spec_name="test-spec",
        spec_dir="/path/to/spec",
        project_dir="/path/to/project"
    )

def test_mcp_tool_execution(plugin, mock_context):
    """Test MCP tool executes correctly."""
    tools = plugin.create_mcp_tools(mock_context)
    my_tool = next(t for t in tools if t.__name__ == 'my_custom_tool')

    # Execute tool
    result = my_tool(arg1="value1", arg2="value2")

    # Verify result
    assert result is not None
    assert "status" in result
    assert result["status"] == "success"

def test_mcp_tool_error_handling(plugin, mock_context):
    """Test MCP tool handles errors gracefully."""
    tools = plugin.create_mcp_tools(mock_context)
    my_tool = next(t for t in tools if t.__name__ == 'my_custom_tool')

    # Test with invalid input
    with pytest.raises(ValueError, match="Invalid argument"):
        my_tool(arg1=None)

def test_mcp_tool_validation(plugin, mock_context):
    """Test MCP tool validates inputs."""
    tools = plugin.create_mcp_tools(mock_context)
    my_tool = next(t for t in tools if t.__name__ == 'my_custom_tool')

    # Test input validation
    with pytest.raises(TypeError):
        my_tool(arg1=123)  # Expects string

@pytest.mark.asyncio
async def test_async_mcp_tool(plugin, mock_context):
    """Test async MCP tool execution."""
    tools = plugin.create_mcp_tools(mock_context)
    async_tool = next(t for t in tools if t.__name__ == 'my_async_tool')

    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_get.return_value.__aenter__.return_value.json.return_value = {
            "data": "test"
        }

        result = await async_tool(query="test")

        assert result["data"] == "test"
```

---

## Integration Testing

### Testing with Real Auto Code Environment

**Example**: Integration test with spec runner

```python
# tests/test_integration.py
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from plugins.registry import PluginRegistry
from plugins.loader import PluginLoader

@pytest.fixture
def temp_plugin_dir():
    """Create temporary plugin directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def install_plugin(temp_plugin_dir):
    """Install plugin for testing."""
    plugin_path = Path(temp_plugin_dir) / "my-plugin"
    plugin_path.mkdir()

    # Create plugin.json
    manifest = {
        "name": "my-plugin",
        "version": "1.0.0",
        "author": "Test Author",
        "description": "Test plugin",
        "plugin_type": "agent",
        "required_permissions": []
    }

    with open(plugin_path / "plugin.json", "w") as f:
        json.dump(manifest, f)

    # Create agent.py
    agent_code = """
from plugins.sdk.agent import AgentPlugin, AgentContext

class MyAgentPlugin(AgentPlugin):
    def on_load(self):
        pass

    def on_enable(self):
        pass

    def before_session(self, context: AgentContext):
        pass

    def after_session(self, context: AgentContext, success: bool):
        pass
"""

    with open(plugin_path / "agent.py", "w") as f:
        f.write(agent_code)

    return plugin_path

def test_plugin_discovery(install_plugin, temp_plugin_dir):
    """Test plugin is discovered by registry."""
    registry = PluginRegistry(plugin_dirs=[temp_plugin_dir])

    plugins = registry.discover_plugins()

    assert len(plugins) == 1
    assert plugins[0]["name"] == "my-plugin"

def test_plugin_loading(install_plugin, temp_plugin_dir):
    """Test plugin loads successfully."""
    loader = PluginLoader(plugin_dirs=[temp_plugin_dir])

    plugin = loader.load_plugin("my-plugin")

    assert plugin is not None
    assert plugin.name == "my-plugin"
    assert plugin.version == "1.0.0"

def test_plugin_lifecycle_integration(install_plugin, temp_plugin_dir):
    """Test plugin lifecycle with real registry."""
    from plugins.sdk.agent import AgentContext

    loader = PluginLoader(plugin_dirs=[temp_plugin_dir])
    plugin = loader.load_plugin("my-plugin")

    # Test lifecycle
    plugin.on_load()
    plugin.on_enable()

    context = AgentContext(
        spec_name="test-spec",
        spec_dir="/tmp/spec",
        project_dir="/tmp/project",
        agent_type="coder",
        model="claude-sonnet-4-5-20250929"
    )

    plugin.before_session(context)
    plugin.after_session(context, success=True)

    plugin.on_disable()
    plugin.on_unload()

@pytest.mark.slow
def test_plugin_with_real_spec(install_plugin, temp_plugin_dir):
    """Test plugin with actual spec execution."""
    # This requires Auto Code to be fully set up
    # Skip if not in integration test environment
    pytest.skip("Requires full Auto Code environment")
```

---

## Test Fixtures & Mocking

### Common Fixtures

```python
# tests/fixtures/mock_context.py
import pytest
from plugins.sdk.agent import AgentContext
from plugins.sdk.integration import IntegrationContext
from pathlib import Path

@pytest.fixture
def agent_context():
    """Standard agent context for testing."""
    return AgentContext(
        spec_name="test-spec-001",
        spec_dir="/tmp/specs/001",
        project_dir="/tmp/project",
        agent_type="coder",
        model="claude-sonnet-4-5-20250929"
    )

@pytest.fixture
def integration_context():
    """Standard integration context for testing."""
    return IntegrationContext(
        spec_name="test-spec-001",
        spec_dir="/tmp/specs/001",
        project_dir="/tmp/project"
    )

@pytest.fixture
def mock_spec_dir(tmp_path):
    """Create temporary spec directory with files."""
    spec_dir = tmp_path / "spec"
    spec_dir.mkdir()

    # Create spec.md
    (spec_dir / "spec.md").write_text("# Test Spec\n\nTest content")

    # Create implementation_plan.json
    plan = {
        "subtasks": [
            {"id": "subtask-1", "status": "pending"}
        ]
    }
    import json
    (spec_dir / "implementation_plan.json").write_text(json.dumps(plan))

    return spec_dir

@pytest.fixture
def mock_project_dir(tmp_path):
    """Create temporary project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create package.json
    (project_dir / "package.json").write_text('{"name": "test-project"}')

    # Create src directory
    (project_dir / "src").mkdir()
    (project_dir / "src" / "index.js").write_text("console.log('test');")

    return project_dir
```

### Mocking External Services

```python
# tests/fixtures/mock_services.py
import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_http_client():
    """Mock HTTP client for external API calls."""
    client = MagicMock()
    client.get = AsyncMock(return_value={
        "status": 200,
        "data": {"result": "success"}
    })
    client.post = AsyncMock(return_value={
        "status": 201,
        "data": {"id": "123"}
    })
    return client

@pytest.fixture
def mock_database():
    """Mock database for testing persistence."""
    db = MagicMock()
    db.store = {}

    def get(key):
        return db.store.get(key)

    def set(key, value):
        db.store[key] = value

    db.get = MagicMock(side_effect=get)
    db.set = MagicMock(side_effect=set)

    return db

@pytest.fixture
def mock_logger():
    """Mock logger for testing log output."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger
```

---

## Manual Testing

### Testing with Real Specs

**Step 1: Install your plugin**

```bash
cd apps/backend
python plugins/cli.py install --path /path/to/my-plugin
python plugins/cli.py enable my-plugin
```

**Step 2: Create test spec**

```bash
cd apps/backend
python spec_runner.py --task "Test my plugin functionality" --complexity simple
```

**Step 3: Run build with plugin**

```bash
cd apps/backend
python run.py --spec 001
```

**Step 4: Monitor plugin behavior**

```bash
# Watch logs for plugin output
tail -f .auto-claude/specs/001/build-progress.txt

# Check for errors
grep -i "error" .auto-claude/specs/001/build-progress.txt
```

### Testing MCP Tools

**Step 1: Enable verbose logging**

```python
# In your plugin, enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Step 2: Test tool creation**

```bash
# Run Python REPL
cd apps/backend
python

>>> from integration import MyIntegrationPlugin
>>> from plugins.sdk.integration import IntegrationContext
>>>
>>> plugin = MyIntegrationPlugin(name="my-plugin", version="1.0.0", manifest_path="plugin.json")
>>> context = IntegrationContext(spec_name="test", spec_dir="/tmp", project_dir="/tmp")
>>> tools = plugin.create_mcp_tools(context)
>>>
>>> # Test tool
>>> my_tool = tools[0]
>>> result = my_tool(arg1="test")
>>> print(result)
```

### Testing Lifecycle Hooks

**Create test script** (`test_hooks.py`):

```python
#!/usr/bin/env python3
import sys
from pathlib import Path
from plugins.loader import PluginLoader
from plugins.sdk.agent import AgentContext

# Load plugin
loader = PluginLoader(plugin_dirs=["./my-plugin"])
plugin = loader.load_plugin("my-plugin")

# Test lifecycle
print("Testing on_load...")
plugin.on_load()

print("Testing on_enable...")
plugin.on_enable()

print("Testing before_session...")
context = AgentContext(
    spec_name="test-spec",
    spec_dir="/tmp/spec",
    project_dir="/tmp/project",
    agent_type="coder",
    model="claude-sonnet-4-5-20250929"
)
plugin.before_session(context)

print("Testing after_session (success)...")
plugin.after_session(context, success=True)

print("Testing after_session (failure)...")
plugin.after_session(context, success=False)

print("Testing on_disable...")
plugin.on_disable()

print("Testing on_unload...")
plugin.on_unload()

print("\n✅ All lifecycle hooks tested successfully")
```

Run test:

```bash
cd apps/backend
python test_hooks.py
```

---

## CI/CD Testing

### GitHub Actions Workflow

```yaml
# .github/workflows/test-plugin.yml
name: Test Plugin

on:
  push:
    paths:
      - 'my-plugin/**'
  pull_request:
    paths:
      - 'my-plugin/**'

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          cd apps/backend
          pip install uv
          uv pip install pytest pytest-asyncio pytest-cov pytest-mock

      - name: Run tests
        run: |
          pytest my-plugin/tests/ -v --cov=my-plugin --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: plugin-tests

      - name: Test plugin installation
        run: |
          cd apps/backend
          python plugins/cli.py install --path ../../my-plugin
          python plugins/cli.py list | grep my-plugin

      - name: Test plugin enable/disable
        run: |
          cd apps/backend
          python plugins/cli.py enable my-plugin
          python plugins/cli.py list --enabled-only | grep my-plugin
          python plugins/cli.py disable my-plugin
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml (add to your plugin)
repos:
  - repo: local
    hooks:
      - id: plugin-tests
        name: Run plugin tests
        entry: pytest my-plugin/tests/ -v
        language: system
        pass_filenames: false
        always_run: true
```

---

## Performance Testing

### Measuring Hook Performance

```python
# tests/test_performance.py
import pytest
import time
from agent import MyAgentPlugin
from plugins.sdk.agent import AgentContext

@pytest.fixture
def plugin():
    return MyAgentPlugin(
        name="my-plugin",
        version="1.0.0",
        manifest_path="/path/to/plugin.json"
    )

@pytest.fixture
def context():
    return AgentContext(
        spec_name="perf-test",
        spec_dir="/tmp/spec",
        project_dir="/tmp/project",
        agent_type="coder",
        model="claude-sonnet-4-5-20250929"
    )

def test_before_session_performance(plugin, context, benchmark):
    """Test before_session hook performance."""
    plugin.on_load()
    plugin.on_enable()

    # Use pytest-benchmark
    result = benchmark(plugin.before_session, context)

    # Assert execution time is acceptable (< 100ms)
    assert benchmark.stats['mean'] < 0.1

def test_after_session_performance(plugin, context):
    """Test after_session doesn't block."""
    plugin.on_load()
    plugin.on_enable()

    start = time.time()
    plugin.after_session(context, success=True)
    duration = time.time() - start

    # Should complete in < 50ms
    assert duration < 0.05

@pytest.mark.parametrize("num_messages", [10, 100, 1000])
def test_message_processing_scalability(plugin, context, num_messages):
    """Test on_message scales linearly."""
    plugin.on_load()
    plugin.on_enable()

    messages = [
        {"role": "assistant", "content": f"Message {i}"}
        for i in range(num_messages)
    ]

    start = time.time()
    for msg in messages:
        plugin.on_message(context, msg)
    duration = time.time() - start

    # Should process 1000 messages in < 1 second
    if num_messages == 1000:
        assert duration < 1.0
```

### Load Testing

```python
# tests/test_load.py
import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor
from integration import MyIntegrationPlugin
from plugins.sdk.integration import IntegrationContext

@pytest.mark.asyncio
async def test_concurrent_tool_calls():
    """Test MCP tool handles concurrent requests."""
    plugin = MyIntegrationPlugin(
        name="my-integration",
        version="1.0.0",
        manifest_path="/path/to/plugin.json"
    )

    context = IntegrationContext(
        spec_name="load-test",
        spec_dir="/tmp/spec",
        project_dir="/tmp/project"
    )

    tools = plugin.create_mcp_tools(context)
    my_tool = tools[0]

    # Simulate 100 concurrent calls
    tasks = [
        asyncio.create_task(my_tool(arg=f"test-{i}"))
        for i in range(100)
    ]

    results = await asyncio.gather(*tasks)

    # All calls should succeed
    assert len(results) == 100
    assert all(r["status"] == "success" for r in results)

def test_memory_usage():
    """Test plugin doesn't leak memory."""
    import tracemalloc

    tracemalloc.start()

    plugin = MyAgentPlugin(
        name="my-plugin",
        version="1.0.0",
        manifest_path="/path/to/plugin.json"
    )

    plugin.on_load()
    plugin.on_enable()

    context = AgentContext(
        spec_name="mem-test",
        spec_dir="/tmp/spec",
        project_dir="/tmp/project",
        agent_type="coder",
        model="claude-sonnet-4-5-20250929"
    )

    # Run 1000 iterations
    for i in range(1000):
        plugin.before_session(context)
        plugin.after_session(context, success=True)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Peak memory should be < 10MB
    assert peak < 10 * 1024 * 1024
```

---

## Security Testing

### Testing Permission Validation

```python
# tests/test_security.py
import pytest
from plugins.loader import PluginLoader

def test_plugin_requires_permissions():
    """Test plugin declares required permissions."""
    loader = PluginLoader(plugin_dirs=["./my-plugin"])
    manifest = loader.load_manifest("my-plugin")

    # Plugin should declare permissions
    assert "required_permissions" in manifest

    # Sensitive permissions should be documented
    if "network" in manifest["required_permissions"]:
        assert "Network access for:" in manifest.get("description", "")

def test_plugin_isolation():
    """Test plugin runs in isolated environment."""
    from plugins.isolation import IsolatedPluginRunner

    runner = IsolatedPluginRunner("my-plugin")

    # Plugin should not access parent directory
    with pytest.raises(PermissionError):
        runner.run_code("import os; os.listdir('..')")

    # Plugin should not access sensitive files
    with pytest.raises(PermissionError):
        runner.run_code("open('/etc/passwd')")

def test_mcp_tool_input_validation():
    """Test MCP tools validate inputs."""
    plugin = MyIntegrationPlugin(
        name="my-integration",
        version="1.0.0",
        manifest_path="/path/to/plugin.json"
    )

    context = IntegrationContext(
        spec_name="security-test",
        spec_dir="/tmp/spec",
        project_dir="/tmp/project"
    )

    tools = plugin.create_mcp_tools(context)
    my_tool = tools[0]

    # Test SQL injection prevention
    with pytest.raises(ValueError, match="Invalid input"):
        my_tool(query="'; DROP TABLE users; --")

    # Test path traversal prevention
    with pytest.raises(ValueError, match="Invalid path"):
        my_tool(path="../../../etc/passwd")

    # Test command injection prevention
    with pytest.raises(ValueError, match="Invalid command"):
        my_tool(command="ls; rm -rf /")
```

---

## Best Practices

### 1. Test Coverage Goals

- **Aim for 80%+ code coverage** for all plugin code
- **100% coverage for critical paths** (security, data handling)
- **Test all lifecycle hooks** even if they're empty stubs

### 2. Use Fixtures

- **Create reusable fixtures** for common test data
- **Mock external dependencies** to avoid flaky tests
- **Use temporary directories** for file operations

### 3. Async Testing

```python
# Use pytest-asyncio for async code
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result is not None
```

### 4. Parameterized Tests

```python
# Test multiple scenarios efficiently
@pytest.mark.parametrize("input,expected", [
    ("test1", "result1"),
    ("test2", "result2"),
    ("test3", "result3"),
])
def test_multiple_inputs(input, expected):
    assert my_function(input) == expected
```

### 5. Test Organization

```python
# Group related tests in classes
class TestAgentLifecycle:
    def test_on_load(self):
        pass

    def test_on_enable(self):
        pass

    def test_on_disable(self):
        pass

class TestMCPTools:
    def test_tool_creation(self):
        pass

    def test_tool_execution(self):
        pass
```

### 6. Error Testing

```python
# Test error handling explicitly
def test_handles_missing_file():
    with pytest.raises(FileNotFoundError):
        plugin.load_config("nonexistent.json")

def test_handles_invalid_json():
    with pytest.raises(ValueError, match="Invalid JSON"):
        plugin.parse_config("{invalid json}")
```

### 7. Integration Test Markers

```python
# Mark slow/integration tests
@pytest.mark.slow
@pytest.mark.integration
def test_full_plugin_lifecycle():
    # Takes several seconds to run
    pass

# Run fast tests only
# pytest -m "not slow"
```

### 8. Continuous Testing

```bash
# Use pytest-watch for continuous testing during development
pip install pytest-watch
ptw my-plugin/tests/ -- -v
```

---

## Troubleshooting

### Tests Not Found

**Problem**: `pytest` doesn't discover tests

**Solutions**:

```bash
# Ensure test files start with test_
mv my_test.py test_my_feature.py

# Ensure __init__.py exists
touch tests/__init__.py

# Run with explicit path
pytest my-plugin/tests/ -v

# Check pytest configuration
pytest --collect-only
```

### Import Errors

**Problem**: `ModuleNotFoundError` when importing plugin code

**Solutions**:

```bash
# Install plugin in development mode
pip install -e ./my-plugin

# Add plugin directory to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:./my-plugin"

# Use relative imports in tests
from ..agent import MyAgentPlugin  # instead of absolute import
```

### Async Test Failures

**Problem**: `RuntimeWarning: coroutine was never awaited`

**Solutions**:

```python
# Add pytest.mark.asyncio decorator
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()

# Install pytest-asyncio
pip install pytest-asyncio

# Configure pytest.ini
# [pytest]
# asyncio_mode = auto
```

### Mock Not Working

**Problem**: Mock doesn't intercept calls

**Solutions**:

```python
# Use patch on the module where function is used, not defined
# ❌ Wrong
with patch('external_module.function'):
    plugin.my_method()  # Doesn't work

# ✅ Correct
with patch('my_plugin.function'):  # Patch where it's imported
    plugin.my_method()  # Works!

# Use patch.object for methods
with patch.object(plugin, 'internal_method'):
    plugin.my_method()
```

### Fixture Scope Issues

**Problem**: Fixture state persists between tests

**Solutions**:

```python
# Use function scope (default) for isolation
@pytest.fixture(scope="function")
def plugin():
    return MyPlugin()

# Use session scope carefully
@pytest.fixture(scope="session")
def expensive_resource():
    # Created once, shared by all tests
    return create_expensive_resource()

# Use autouse for teardown
@pytest.fixture(autouse=True)
def reset_state():
    yield
    # Cleanup after each test
    clear_global_state()
```

### Coverage Gaps

**Problem**: Coverage report shows untested code

**Solutions**:

```bash
# Generate HTML coverage report
pytest --cov=my-plugin --cov-report=html
# Open htmlcov/index.html to see gaps

# Show missing lines
pytest --cov=my-plugin --cov-report=term-missing

# Exclude test files from coverage
# setup.cfg or .coveragerc:
# [coverage:run]
# omit = tests/*
```

### Performance Test Instability

**Problem**: Performance tests fail intermittently

**Solutions**:

```python
# Use multiple iterations
def test_performance():
    durations = []
    for _ in range(10):
        start = time.time()
        my_function()
        durations.append(time.time() - start)

    # Check average, not single run
    avg = sum(durations) / len(durations)
    assert avg < 0.1

# Use pytest-benchmark for stable results
def test_benchmark(benchmark):
    result = benchmark(my_function)
    # Handles warmup, iterations automatically
```

### CI/CD Test Failures

**Problem**: Tests pass locally but fail in CI

**Solutions**:

```yaml
# Match CI environment locally with Docker
docker run -it python:3.12 bash
pip install pytest
pytest my-plugin/tests/

# Add debug output in CI
- name: Run tests
  run: pytest my-plugin/tests/ -v -s  # -s shows print output

# Check for timing issues
@pytest.mark.flaky(reruns=3)  # Retry flaky tests
def test_timing_sensitive():
    pass
```

---

## Related Documentation

- [Plugin Development Guide](plugin-development.md) - Creating plugins
- [Plugin Architecture](../architecture/plugin-architecture.md) - System design
- [Security Model](../architecture/security.md) - Plugin isolation and permissions
- [MCP Tools Guide](mcp-tools.md) - Creating custom tools

---

**Last Updated**: 2026-03-05
