# Integration Plugin Development Guide

Integration plugins connect Auto Claude to external services by creating MCP (Model Context Protocol) tools that agents can use during builds. This guide covers everything you need to build robust integration plugins.

## Table of Contents

- [Overview](#overview)
- [IntegrationPlugin API Reference](#integrationplugin-api-reference)
- [Creating MCP Tools](#creating-mcp-tools)
- [External Service Integration](#external-service-integration)
- [Configuration Management](#configuration-management)
- [State Persistence](#state-persistence)
- [Data Synchronization](#data-synchronization)
- [Build Lifecycle Hooks](#build-lifecycle-hooks)
- [Real-time Updates](#real-time-updates)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Complete Example](#complete-example)

## Overview

Integration plugins are Python classes that extend the `IntegrationPlugin` base class from the Auto Claude plugin SDK. They enable:

- **MCP Tool Creation** - Provide tools that agents can invoke during sessions
- **External Service Integration** - Connect to REST APIs, GraphQL, databases, or SDKs
- **Data Synchronization** - Bidirectional sync between Auto Claude and external services
- **Build Tracking** - Monitor build lifecycle and push updates to external systems
- **Real-time Updates** - React to subtask status changes and sync immediately
- **Configuration Management** - Manage API keys, endpoints, and settings

### When to Use Integration Plugins

Use integration plugins when you want to:
- Connect Auto Claude to issue trackers (Jira, Linear, GitHub Issues)
- Integrate with communication platforms (Slack, Discord, Microsoft Teams)
- Sync with project management tools (Asana, Monday, ClickUp)
- Push metrics to monitoring services (Datadog, New Relic)
- Connect to cloud storage (Google Drive, Dropbox, S3)
- Query databases or internal APIs
- Provide custom tools for agents to use

### Quick Start

```bash
# Copy the example plugin
cp -r examples/plugins/custom-integration my-integration-plugin

# Update plugin.json
# Edit integration.py to implement your service integration
# Install and test
```

## IntegrationPlugin API Reference

### Base Class

```python
from apps.backend.plugins.sdk.integration import IntegrationPlugin, IntegrationContext

class MyIntegrationPlugin(IntegrationPlugin):
    """Your custom integration plugin."""

    def __init__(self, metadata):
        super().__init__(metadata)
        self.client = None  # Your external service client
```

### Required Methods

All integration plugins must implement these core methods:

| Method | Purpose | Required |
|--------|---------|----------|
| `create_mcp_tools(context)` | Create MCP tools for agents | Yes |
| `is_available()` | Check service connectivity | Yes |

### Optional Integration Methods

Additional methods you can implement:

| Method | Purpose | When Called |
|--------|---------|-------------|
| `create_mcp_server(context)` | Build MCP server from tools | When loading plugin |
| `sync_data(context)` | Sync data with external service | On-demand or periodic |
| `on_subtask_update(context, subtask_id, status, notes)` | Handle subtask updates | When subtask status changes |
| `on_build_start(context)` | Track build start | When build begins |
| `on_build_complete(context, success)` | Track build completion | When build ends |

### Lifecycle Hooks (from PluginBase)

| Method | Purpose | Required |
|--------|---------|----------|
| `on_load()` | Plugin initialization | Yes |
| `on_enable()` | Called when user enables plugin | Yes |
| `on_disable()` | Called when user disables plugin | Yes |
| `on_unload()` | Cleanup before unload | Yes |

## Creating MCP Tools

MCP tools are the primary way agents interact with external services. Each tool is a Python function with clear documentation.

### Tool Creation Pattern

```python
from typing import Any

def create_mcp_tools(self, context: IntegrationContext) -> list[tuple[str, callable]]:
    """Create MCP tools for agents to use."""

    def create_task(title: str, description: str) -> dict[str, Any]:
        """
        Create a new task in the external system.

        Args:
            title: Task title
            description: Task description

        Returns:
            dict: Created task with id, title, description, status
        """
        try:
            # Call your external service
            result = self.client.create_task(title, description)

            # Log for debugging
            self.logger.info(f"Created task: {result['id']}")

            return {"success": True, "data": result}
        except Exception as e:
            self.logger.error(f"Failed to create task: {e}")
            return {"success": False, "error": str(e)}

    def list_tasks(status: str = None) -> dict[str, Any]:
        """
        List all tasks, optionally filtered by status.

        Args:
            status: Optional status filter (pending, in_progress, completed)

        Returns:
            dict: List of tasks
        """
        try:
            tasks = self.client.list_tasks(status=status)
            return {"success": True, "data": tasks}
        except Exception as e:
            self.logger.error(f"Failed to list tasks: {e}")
            return {"success": False, "error": str(e)}

    # Return list of (tool_name, tool_function) tuples
    return [
        ("create_task", create_task),
        ("list_tasks", list_tasks),
    ]
```

### Tool Best Practices

**1. Clear Docstrings**

Agents use docstrings to understand what tools do:

```python
def update_task_status(task_id: int, status: str) -> dict[str, Any]:
    """
    Update the status of an existing task.

    Args:
        task_id: The ID of the task to update
        status: New status (pending, in_progress, completed, failed)

    Returns:
        dict: Updated task object with new status and updated_at timestamp

    Raises:
        ValueError: If task_id is invalid or status is not recognized
    """
```

**2. Type Hints**

Always include type hints for parameters and return values:

```python
def get_task_details(task_id: int) -> dict[str, Any]:
    """Get details of a specific task."""
```

**3. Error Handling**

Return structured responses with success/error information:

```python
try:
    result = self.client.delete_task(task_id)
    return {"success": True, "data": result}
except Exception as e:
    self.logger.error(f"Delete failed: {e}", exc_info=True)
    return {"success": False, "error": str(e)}
```

**4. Logging**

Log tool usage for debugging:

```python
def create_task(title: str, description: str):
    self.logger.info(f"Creating task: {title}")
    result = self.client.create_task(title, description)
    self.logger.debug(f"Task created: {result}")
    return result
```

## External Service Integration

### Client Initialization

Initialize your external service client in `on_enable()`:

```python
def on_enable(self) -> None:
    """Initialize the external service client when plugin is enabled."""
    # Get API key from config
    api_key = self.get_config_value("MY_SERVICE_API_KEY")
    if not api_key:
        raise ValueError("MY_SERVICE_API_KEY not configured in .env")

    # Initialize client
    self.client = MyServiceClient(api_key=api_key)

    # Test connection
    if not self.is_available():
        raise ConnectionError("Failed to connect to MyService")

    self.logger.info("MyService client initialized")
```

### Connection Checking

Implement `is_available()` to check service connectivity:

```python
def is_available(self) -> bool:
    """Check if the external service is available."""
    if not self.client:
        return False

    try:
        # Ping the service or check health endpoint
        response = self.client.health_check()
        return response.get("status") == "ok"
    except Exception as e:
        self.logger.warning(f"Service unavailable: {e}")
        return False
```

### REST API Integration

Example REST API client wrapper:

```python
import requests

class MyServiceClient:
    def __init__(self, api_key: str, base_url: str = "https://api.myservice.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def health_check(self) -> dict:
        """Check service health."""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def create_task(self, title: str, description: str) -> dict:
        """Create a task."""
        response = self.session.post(
            f"{self.base_url}/tasks",
            json={"title": title, "description": description}
        )
        response.raise_for_status()
        return response.json()

    def list_tasks(self, status: str = None) -> list[dict]:
        """List tasks."""
        params = {"status": status} if status else {}
        response = self.session.get(f"{self.base_url}/tasks", params=params)
        response.raise_for_status()
        return response.json()
```

### GraphQL Integration

Example GraphQL client wrapper:

```python
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

class GraphQLServiceClient:
    def __init__(self, api_key: str, endpoint: str):
        transport = RequestsHTTPTransport(
            url=endpoint,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        self.client = Client(transport=transport)

    def create_issue(self, title: str, description: str) -> dict:
        """Create an issue using GraphQL."""
        mutation = gql("""
            mutation CreateIssue($title: String!, $description: String!) {
                createIssue(input: {title: $title, description: $description}) {
                    issue {
                        id
                        title
                        description
                    }
                }
            }
        """)
        result = self.client.execute(mutation, variable_values={
            "title": title,
            "description": description
        })
        return result["createIssue"]["issue"]
```

### SDK Integration

Example using an official SDK:

```python
from linear_sdk import LinearClient

class LinearIntegrationClient:
    def __init__(self, api_key: str):
        self.client = LinearClient(api_key)

    def create_issue(self, team_id: str, title: str, description: str) -> dict:
        """Create a Linear issue using the official SDK."""
        issue = self.client.issue_create({
            "teamId": team_id,
            "title": title,
            "description": description
        })
        return {
            "id": issue.id,
            "title": issue.title,
            "url": issue.url
        }
```

## Configuration Management

### Reading Configuration

Use `get_config_value()` to read environment variables and .env files:

```python
def on_load(self) -> None:
    """Load configuration when plugin is loaded."""
    # Read required config
    self.api_key = self.get_config_value("MY_SERVICE_API_KEY")
    if not self.api_key:
        raise ValueError("MY_SERVICE_API_KEY is required")

    # Read optional config with default
    self.base_url = self.get_config_value(
        "MY_SERVICE_BASE_URL",
        default="https://api.myservice.com"
    )
    self.timeout = int(self.get_config_value("MY_SERVICE_TIMEOUT", default="30"))
```

### Setting Configuration

Use `set_config_value()` to update configuration:

```python
def configure(self, api_key: str, base_url: str = None) -> None:
    """Update plugin configuration."""
    self.set_config_value("MY_SERVICE_API_KEY", api_key)
    if base_url:
        self.set_config_value("MY_SERVICE_BASE_URL", base_url)
```

### Environment Variables

Document required environment variables in your plugin's README:

```markdown
## Configuration

Add these environment variables to `apps/backend/.env`:

```bash
# Required
MY_SERVICE_API_KEY=your_api_key_here

# Optional
MY_SERVICE_BASE_URL=https://api.myservice.com
MY_SERVICE_TIMEOUT=30
```
```

## State Persistence

Integration plugins often need to persist state between sessions (e.g., task mappings, sync timestamps, counters).

### Saving State

```python
def on_build_start(self, context: IntegrationContext) -> None:
    """Track build start and save to state."""
    # Load existing state
    self.load_state(context)

    # Update state
    context.set_state("build_count", context.get_state("build_count", 0) + 1)
    context.set_state("last_build_start", datetime.now().isoformat())

    # Save state
    self.save_state(context)
```

### Loading State

```python
def sync_data(self, context: IntegrationContext) -> None:
    """Sync data using persisted state."""
    # Load state at start
    self.load_state(context)

    # Get previous sync timestamp
    last_sync = context.get_state("last_sync")
    if last_sync:
        self.logger.info(f"Last sync: {last_sync}")

    # Perform sync
    # ...

    # Update sync timestamp
    context.set_state("last_sync", datetime.now().isoformat())
    self.save_state(context)
```

### State File Location

State is saved as `.{plugin-name}_state.json` in the spec directory:

```
.auto-claude/specs/001-feature/
├── spec.md
├── implementation_plan.json
└── .my-integration_state.json  ← Your plugin state
```

### State Schema Example

```json
{
  "task_mapping": {
    "subtask-1-1": 42,
    "subtask-1-2": 43
  },
  "task_count": 2,
  "last_sync": "2026-01-28T12:00:00",
  "last_create": "2026-01-28T12:05:00",
  "build_count": 5
}
```

## Data Synchronization

### One-way Sync (Push)

Push Auto Claude subtasks to external service:

```python
def sync_data(self, context: IntegrationContext) -> None:
    """Push subtasks from implementation plan to external service."""
    # Load implementation plan
    plan = self.load_implementation_plan(context)

    # Get all subtasks
    subtasks = self.get_all_subtasks(plan)

    # Load state for task mapping
    self.load_state(context)
    task_mapping = context.get_state("task_mapping", {})

    # Push each subtask
    for subtask in subtasks:
        subtask_id = subtask["id"]

        # Skip if already synced
        if subtask_id in task_mapping:
            continue

        # Create task in external service
        task = self.client.create_task(
            title=f"[{plan['feature']}] {subtask['description']}",
            description=subtask.get("notes", ""),
            status=self.map_status(subtask.get("status", "pending"))
        )

        # Store mapping
        task_mapping[subtask_id] = task["id"]
        self.logger.info(f"Synced {subtask_id} → {task['id']}")

    # Save updated mapping
    context.set_state("task_mapping", task_mapping)
    context.set_state("last_sync", datetime.now().isoformat())
    self.save_state(context)
```

### Two-way Sync (Bidirectional)

Sync in both directions:

```python
def sync_data(self, context: IntegrationContext) -> None:
    """Bidirectional sync between Auto Claude and external service."""
    plan = self.load_implementation_plan(context)
    self.load_state(context)

    # 1. PUSH: Auto Claude → External Service
    subtasks = self.get_all_subtasks(plan)
    task_mapping = context.get_state("task_mapping", {})

    for subtask in subtasks:
        subtask_id = subtask["id"]
        external_task_id = task_mapping.get(subtask_id)

        if external_task_id:
            # Update existing task
            self.client.update_task(
                external_task_id,
                status=self.map_status(subtask["status"])
            )
        else:
            # Create new task
            task = self.client.create_task(
                title=subtask["description"],
                description=subtask.get("notes", "")
            )
            task_mapping[subtask_id] = task["id"]

    # 2. PULL: External Service → Auto Claude
    external_tasks = self.client.list_tasks()

    for task in external_tasks:
        # Find corresponding subtask
        subtask_id = self.find_subtask_by_external_id(task["id"], task_mapping)
        if not subtask_id:
            continue

        # Check if external task was updated
        if self.task_needs_update(task, subtask_id, plan):
            # Update subtask in implementation plan
            self.update_subtask_status(
                context,
                subtask_id,
                self.map_external_status(task["status"]),
                f"Updated from external service: {task['updated_at']}"
            )

    # Save state
    context.set_state("task_mapping", task_mapping)
    context.set_state("last_sync", datetime.now().isoformat())
    self.save_state(context)
```

### Helper Methods for Sync

```python
def map_status(self, auto_claude_status: str) -> str:
    """Map Auto Claude status to external service status."""
    mapping = {
        "pending": "todo",
        "in_progress": "in_progress",
        "completed": "done",
        "failed": "failed"
    }
    return mapping.get(auto_claude_status, "todo")

def map_external_status(self, external_status: str) -> str:
    """Map external service status to Auto Claude status."""
    mapping = {
        "todo": "pending",
        "in_progress": "in_progress",
        "done": "completed",
        "failed": "failed"
    }
    return mapping.get(external_status, "pending")

def get_all_subtasks(self, plan: dict) -> list[dict]:
    """Extract all subtasks from implementation plan."""
    subtasks = []
    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            subtasks.append(subtask)
    return subtasks

def find_subtask_by_external_id(
    self,
    external_id: str,
    task_mapping: dict[str, str]
) -> str | None:
    """Find subtask ID by external task ID."""
    for subtask_id, ext_id in task_mapping.items():
        if ext_id == external_id:
            return subtask_id
    return None
```

## Build Lifecycle Hooks

### on_build_start()

Called when a build begins:

```python
def on_build_start(self, context: IntegrationContext) -> None:
    """Track build start in external service."""
    try:
        # Load state
        self.load_state(context)

        # Create a "Build Started" task
        spec_name = context.spec_dir.name
        task = self.client.create_task(
            title=f"[Build] {spec_name} - Started",
            description=f"Build started at {datetime.now().isoformat()}",
            status="in_progress"
        )

        # Save build task ID
        context.set_state("build_task_id", task["id"])
        context.set_state("build_start_time", datetime.now().isoformat())
        self.save_state(context)

        self.logger.info(f"Build start tracked: {task['id']}")
    except Exception as e:
        self.logger.error(f"Failed to track build start: {e}", exc_info=True)
```

### on_build_complete()

Called when a build finishes:

```python
def on_build_complete(self, context: IntegrationContext, success: bool) -> None:
    """Track build completion in external service."""
    try:
        # Load state
        self.load_state(context)

        # Calculate duration
        start_time = context.get_state("build_start_time")
        if start_time:
            start = datetime.fromisoformat(start_time)
            duration = (datetime.now() - start).total_seconds()
        else:
            duration = 0

        # Update build task
        build_task_id = context.get_state("build_task_id")
        if build_task_id:
            self.client.update_task(
                build_task_id,
                status="done" if success else "failed",
                description=f"Build {'succeeded' if success else 'failed'} after {duration:.1f}s"
            )

        # Create completion task
        spec_name = context.spec_dir.name
        task = self.client.create_task(
            title=f"[Build] {spec_name} - {'Success' if success else 'Failed'}",
            description=f"Duration: {duration:.1f}s",
            status="done" if success else "failed"
        )

        # Save state
        context.set_state("build_end_time", datetime.now().isoformat())
        context.set_state("build_success", success)
        self.save_state(context)

        self.logger.info(f"Build completion tracked: {task['id']}")
    except Exception as e:
        self.logger.error(f"Failed to track build completion: {e}", exc_info=True)
```

## Real-time Updates

### on_subtask_update()

Called whenever a subtask status changes:

```python
def on_subtask_update(
    self,
    context: IntegrationContext,
    subtask_id: str,
    status: str,
    notes: str
) -> None:
    """Push subtask updates to external service in real-time."""
    try:
        # Load state
        self.load_state(context)
        task_mapping = context.get_state("task_mapping", {})

        # Get external task ID
        external_task_id = task_mapping.get(subtask_id)
        if not external_task_id:
            self.logger.warning(f"No external task for {subtask_id}, creating...")
            # Create task if it doesn't exist
            plan = self.load_implementation_plan(context)
            subtask = self.find_subtask_by_id(plan, subtask_id)
            if subtask:
                task = self.client.create_task(
                    title=subtask["description"],
                    description=notes,
                    status=self.map_status(status)
                )
                task_mapping[subtask_id] = task["id"]
                external_task_id = task["id"]
            else:
                self.logger.error(f"Subtask {subtask_id} not found in plan")
                return

        # Update external task
        self.client.update_task(
            external_task_id,
            status=self.map_status(status),
            notes=notes
        )

        # Update state
        context.set_state("task_mapping", task_mapping)
        context.set_state("last_update", datetime.now().isoformat())
        self.save_state(context)

        self.logger.info(f"Updated {subtask_id} → {external_task_id}: {status}")
    except Exception as e:
        self.logger.error(f"Failed to update subtask: {e}", exc_info=True)
```

### Helper Methods

```python
def find_subtask_by_id(self, plan: dict, subtask_id: str) -> dict | None:
    """Find a subtask by ID in the implementation plan."""
    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            if subtask["id"] == subtask_id:
                return subtask
    return None
```

## Error Handling

### Graceful Degradation

Never crash the build due to integration failures:

```python
def on_subtask_update(self, context, subtask_id, status, notes) -> None:
    """Update subtask with graceful error handling."""
    try:
        # Try to update external service
        self.client.update_task(task_id, status)
    except requests.exceptions.Timeout:
        self.logger.warning("External service timeout, skipping update")
        # Don't propagate error - build continues
    except requests.exceptions.ConnectionError:
        self.logger.error("Cannot connect to external service")
        # Don't propagate error - build continues
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}", exc_info=True)
        # Don't propagate error - build continues
```

### Retry Logic

Implement retries for transient failures:

```python
import time

def create_task_with_retry(self, title: str, description: str, max_retries: int = 3):
    """Create task with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return self.client.create_task(title, description)
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff
            self.logger.warning(f"Timeout, retrying in {wait_time}s...")
            time.sleep(wait_time)
        except Exception as e:
            self.logger.error(f"Failed to create task: {e}")
            raise
```

### Validation

Validate inputs before calling external services:

```python
def create_task(self, title: str, description: str) -> dict:
    """Create task with input validation."""
    # Validate inputs
    if not title or not title.strip():
        raise ValueError("Title cannot be empty")
    if len(title) > 255:
        raise ValueError("Title too long (max 255 characters)")

    # Call external service
    try:
        return self.client.create_task(title.strip(), description.strip())
    except Exception as e:
        self.logger.error(f"Failed to create task: {e}")
        raise
```

## Best Practices

### 1. Implement is_available()

Always check service availability before operations:

```python
def create_mcp_tools(self, context):
    """Only create tools if service is available."""
    if not self.is_available():
        self.logger.warning("Service unavailable, tools disabled")
        return []

    # Return tools
    return [("create_task", create_task)]
```

### 2. Use Structured Logging

Log at appropriate levels:

```python
self.logger.debug("Detailed debugging info")        # Development
self.logger.info("Normal operations")               # Production
self.logger.warning("Recoverable issues")           # Attention needed
self.logger.error("Errors", exc_info=True)          # Failures
```

### 3. Handle Rate Limits

Respect API rate limits:

```python
import time

class RateLimitedClient:
    def __init__(self, api_key: str, requests_per_second: int = 10):
        self.api_key = api_key
        self.min_interval = 1.0 / requests_per_second
        self.last_request = 0

    def _wait_for_rate_limit(self):
        """Enforce rate limit."""
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()

    def create_task(self, title: str, description: str):
        """Create task with rate limiting."""
        self._wait_for_rate_limit()
        # Make request
```

### 4. Cache Responses

Cache frequently accessed data:

```python
from functools import lru_cache
import time

class CachedClient:
    def __init__(self):
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes

    @lru_cache(maxsize=100)
    def get_task(self, task_id: int):
        """Get task with caching."""
        return self.client.get_task(task_id)

    def invalidate_cache(self):
        """Clear cache."""
        self.get_task.cache_clear()
```

### 5. Document Configuration

Document all environment variables in your README:

```markdown
## Configuration

Required environment variables:

- `MY_SERVICE_API_KEY` - Your API key from MyService
- `MY_SERVICE_TEAM_ID` - Your team ID

Optional environment variables:

- `MY_SERVICE_BASE_URL` - API endpoint (default: https://api.myservice.com)
- `MY_SERVICE_TIMEOUT` - Request timeout in seconds (default: 30)
```

### 6. Test Thoroughly

Test with mock external services:

```python
# tests/test_my_integration.py
import pytest
from unittest.mock import Mock, patch

def test_create_task():
    # Mock the external service
    with patch('my_integration.MyServiceClient') as MockClient:
        mock_client = MockClient.return_value
        mock_client.create_task.return_value = {"id": 123, "title": "Test"}

        # Test plugin
        plugin = MyIntegrationPlugin(metadata)
        plugin.client = mock_client

        result = plugin.create_task("Test", "Description")
        assert result["success"] is True
        assert result["data"]["id"] == 123
```

### 7. Minimize State

Only persist essential state:

```python
# ✅ GOOD - Minimal state
context.set_state("task_mapping", {"subtask-1": 42})
context.set_state("last_sync", "2026-01-28T12:00:00")

# ❌ BAD - Excessive state
context.set_state("all_tasks", [...])  # Don't cache entire API responses
context.set_state("request_history", [...])  # Don't log everything
```

### 8. Handle Credentials Securely

Never hardcode or log credentials:

```python
# ✅ GOOD - Read from environment
api_key = self.get_config_value("MY_SERVICE_API_KEY")

# ❌ BAD - Hardcoded
api_key = "sk_live_12345"

# ❌ BAD - Logged
self.logger.info(f"Using API key: {api_key}")

# ✅ GOOD - Redacted logging
self.logger.info(f"Using API key: {api_key[:8]}...")
```

## Complete Example

Here's a complete integration plugin that connects to a mock task management service:

```python
"""Custom integration plugin for task management service."""
from pathlib import Path
from datetime import datetime
from typing import Any
import json

from apps.backend.plugins.sdk.integration import IntegrationPlugin, IntegrationContext


class MockTaskManagerClient:
    """Mock client for demonstration purposes."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.data_dir / "tasks.json"
        self.task_counter = self._load_counter()

    def _load_counter(self) -> int:
        """Load task counter."""
        counter_file = self.data_dir / "counter.json"
        if counter_file.exists():
            with open(counter_file) as f:
                return json.load(f).get("counter", 0)
        return 0

    def _save_counter(self):
        """Save task counter."""
        counter_file = self.data_dir / "counter.json"
        with open(counter_file, 'w') as f:
            json.dump({"counter": self.task_counter}, f)

    def _load_tasks(self) -> list[dict]:
        """Load tasks from file."""
        if self.tasks_file.exists():
            with open(self.tasks_file) as f:
                return json.load(f)
        return []

    def _save_tasks(self, tasks: list[dict]):
        """Save tasks to file."""
        with open(self.tasks_file, 'w') as f:
            json.dump(tasks, f, indent=2)

    def is_connected(self) -> bool:
        """Check if connected (always true for file-based storage)."""
        return self.data_dir.exists()

    def create_task(self, title: str, description: str, status: str = "pending") -> dict:
        """Create a new task."""
        tasks = self._load_tasks()
        self.task_counter += 1

        task = {
            "id": self.task_counter,
            "title": title,
            "description": description,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        tasks.append(task)
        self._save_tasks(tasks)
        self._save_counter()

        return task

    def list_tasks(self, status: str = None) -> list[dict]:
        """List all tasks, optionally filtered by status."""
        tasks = self._load_tasks()
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return tasks

    def update_task_status(self, task_id: int, status: str, notes: str = None) -> dict:
        """Update task status."""
        tasks = self._load_tasks()

        for task in tasks:
            if task["id"] == task_id:
                task["status"] = status
                task["updated_at"] = datetime.now().isoformat()
                if notes:
                    task["notes"] = notes
                self._save_tasks(tasks)
                return task

        raise ValueError(f"Task {task_id} not found")

    def get_task_details(self, task_id: int) -> dict:
        """Get details of a specific task."""
        tasks = self._load_tasks()
        for task in tasks:
            if task["id"] == task_id:
                return task
        raise ValueError(f"Task {task_id} not found")


class CustomIntegrationPlugin(IntegrationPlugin):
    """
    Custom integration plugin that demonstrates external service integration.

    This plugin connects to a mock task management service and provides MCP tools
    for agents to create, list, and update tasks.
    """

    def on_load(self) -> None:
        """Initialize plugin when loaded."""
        self.logger.info("Custom Integration Plugin loaded")
        self.client = None

    def on_enable(self) -> None:
        """Initialize client when plugin is enabled."""
        # Get data directory from config
        data_dir = self.get_config_value(
            "CUSTOM_INTEGRATION_DATA_DIR",
            default=str(Path.home() / ".auto-claude" / "task-manager")
        )

        # Initialize client
        self.client = MockTaskManagerClient(data_dir)
        self.logger.info(f"Task manager client initialized: {data_dir}")

    def on_disable(self) -> None:
        """Cleanup when plugin is disabled."""
        self.client = None
        self.logger.info("Custom Integration Plugin disabled")

    def on_unload(self) -> None:
        """Cleanup when plugin is unloaded."""
        self.logger.info("Custom Integration Plugin unloaded")

    def is_available(self) -> bool:
        """Check if the task manager is available."""
        if not self.client:
            return False
        return self.client.is_connected()

    def create_mcp_tools(self, context: IntegrationContext) -> list[tuple[str, callable]]:
        """Create MCP tools for agents to use."""

        def create_task(title: str, description: str) -> dict[str, Any]:
            """
            Create a new task in the task manager.

            Args:
                title: Task title
                description: Task description

            Returns:
                dict: Created task with id, title, description, status
            """
            try:
                task = self.client.create_task(title, description)
                self.logger.info(f"Created task: {task['id']}")
                return {"success": True, "data": task}
            except Exception as e:
                self.logger.error(f"Failed to create task: {e}")
                return {"success": False, "error": str(e)}

        def list_tasks(status: str = None) -> dict[str, Any]:
            """
            List all tasks, optionally filtered by status.

            Args:
                status: Optional status filter (pending, in_progress, completed, failed)

            Returns:
                dict: List of tasks
            """
            try:
                tasks = self.client.list_tasks(status=status)
                return {"success": True, "data": tasks}
            except Exception as e:
                self.logger.error(f"Failed to list tasks: {e}")
                return {"success": False, "error": str(e)}

        def update_task_status(task_id: int, status: str) -> dict[str, Any]:
            """
            Update the status of an existing task.

            Args:
                task_id: The ID of the task to update
                status: New status (pending, in_progress, completed, failed)

            Returns:
                dict: Updated task
            """
            try:
                task = self.client.update_task_status(task_id, status)
                self.logger.info(f"Updated task {task_id} to {status}")
                return {"success": True, "data": task}
            except Exception as e:
                self.logger.error(f"Failed to update task: {e}")
                return {"success": False, "error": str(e)}

        def get_task_details(task_id: int) -> dict[str, Any]:
            """
            Get details of a specific task.

            Args:
                task_id: The ID of the task

            Returns:
                dict: Task details
            """
            try:
                task = self.client.get_task_details(task_id)
                return {"success": True, "data": task}
            except Exception as e:
                self.logger.error(f"Failed to get task details: {e}")
                return {"success": False, "error": str(e)}

        return [
            ("create_task", create_task),
            ("list_tasks", list_tasks),
            ("update_task_status", update_task_status),
            ("get_task_details", get_task_details),
        ]

    def sync_data(self, context: IntegrationContext) -> None:
        """Sync implementation plan subtasks to external task manager."""
        try:
            # Load implementation plan
            plan = self.load_implementation_plan(context)

            # Load state
            self.load_state(context)
            task_mapping = context.get_state("task_mapping", {})

            # Get all subtasks
            subtasks = self.get_all_subtasks(plan)

            # Sync each subtask
            for subtask in subtasks:
                subtask_id = subtask["id"]

                # Skip if already synced
                if subtask_id in task_mapping:
                    continue

                # Create task in external system
                task = self.client.create_task(
                    title=f"[{plan['feature']}] {subtask['description']}",
                    description=subtask.get("notes", ""),
                    status=subtask.get("status", "pending")
                )

                # Store mapping
                task_mapping[subtask_id] = task["id"]
                self.logger.info(f"Synced {subtask_id} → task {task['id']}")

            # Save state
            context.set_state("task_mapping", task_mapping)
            context.set_state("last_sync", datetime.now().isoformat())
            self.save_state(context)

            self.logger.info(f"Synced {len(task_mapping)} subtasks")
        except Exception as e:
            self.logger.error(f"Sync failed: {e}", exc_info=True)

    def on_subtask_update(
        self,
        context: IntegrationContext,
        subtask_id: str,
        status: str,
        notes: str
    ) -> None:
        """Push subtask updates to external task manager."""
        try:
            # Load state
            self.load_state(context)
            task_mapping = context.get_state("task_mapping", {})

            # Get external task ID
            external_task_id = task_mapping.get(subtask_id)
            if not external_task_id:
                self.logger.warning(f"No external task for {subtask_id}")
                return

            # Update external task
            self.client.update_task_status(external_task_id, status, notes)

            # Update timestamp
            context.set_state("last_update", datetime.now().isoformat())
            self.save_state(context)

            self.logger.info(f"Updated task {external_task_id}: {status}")
        except Exception as e:
            self.logger.error(f"Failed to update subtask: {e}", exc_info=True)

    def on_build_start(self, context: IntegrationContext) -> None:
        """Track build start in task manager."""
        try:
            spec_name = context.spec_dir.name
            task = self.client.create_task(
                title=f"[Build] {spec_name} - Started",
                description=f"Build started at {datetime.now().isoformat()}",
                status="in_progress"
            )

            self.load_state(context)
            context.set_state("build_task_id", task["id"])
            context.set_state("build_start_time", datetime.now().isoformat())
            self.save_state(context)

            self.logger.info(f"Build start tracked: task {task['id']}")
        except Exception as e:
            self.logger.error(f"Failed to track build start: {e}", exc_info=True)

    def on_build_complete(self, context: IntegrationContext, success: bool) -> None:
        """Track build completion in task manager."""
        try:
            # Calculate duration
            self.load_state(context)
            start_time = context.get_state("build_start_time")
            if start_time:
                start = datetime.fromisoformat(start_time)
                duration = (datetime.now() - start).total_seconds()
            else:
                duration = 0

            # Create completion task
            spec_name = context.spec_dir.name
            task = self.client.create_task(
                title=f"[Build] {spec_name} - {'Success' if success else 'Failed'}",
                description=f"Duration: {duration:.1f}s",
                status="completed" if success else "failed"
            )

            # Update build task
            build_task_id = context.get_state("build_task_id")
            if build_task_id:
                self.client.update_task_status(
                    build_task_id,
                    "completed" if success else "failed",
                    f"Build {'succeeded' if success else 'failed'} after {duration:.1f}s"
                )

            # Save state
            context.set_state("build_end_time", datetime.now().isoformat())
            context.set_state("build_success", success)
            self.save_state(context)

            self.logger.info(f"Build completion tracked: task {task['id']}")
        except Exception as e:
            self.logger.error(f"Failed to track build completion: {e}", exc_info=True)

    def get_all_subtasks(self, plan: dict) -> list[dict]:
        """Extract all subtasks from implementation plan."""
        subtasks = []
        for phase in plan.get("phases", []):
            for subtask in phase.get("subtasks", []):
                subtasks.append(subtask)
        return subtasks
```

## Learn More

- [Plugin Getting Started Guide](getting-started.md) - Basic plugin concepts
- [Agent Plugin Guide](agent-plugins.md) - Building agent plugins
- [UI Plugin Guide](ui-plugins.md) - Building UI plugins
- [Custom Integration Example](../../examples/plugins/custom-integration/README.md) - Working example
- [Linear Integration Source](../../apps/backend/integrations/linear/integration.py) - Real-world example

## Real-World Integration Examples

### Issue Trackers
- **Jira** - Create issues, update status, sync comments
- **Linear** - Create issues, link to specs, update progress
- **GitHub Issues** - Create issues, link to PRs, track milestones

### Communication Platforms
- **Slack** - Send notifications, create threads, update channels
- **Discord** - Post updates, create threads, send embeds
- **Microsoft Teams** - Send adaptive cards, create channels

### Project Management
- **Asana** - Create projects, sync tasks, update progress
- **Monday.com** - Create boards, update items, track timelines
- **ClickUp** - Create tasks, set priorities, update statuses

### Monitoring & Observability
- **Datadog** - Send custom metrics, create events, track builds
- **New Relic** - Log events, send traces, track performance
- **Sentry** - Track errors, link to commits, monitor releases

## Troubleshooting

### Plugin Tools Not Available

**Problem:** Tools don't appear in agent sessions

**Solutions:**
- Verify plugin is **enabled**, not just installed
- Check `is_available()` returns `True`
- Ensure `create_mcp_tools()` returns non-empty list
- Look for errors in plugin logs during tool creation

### External Service Connection Failed

**Problem:** `is_available()` returns `False`

**Solutions:**
- Verify API credentials are configured correctly
- Check network connectivity to external service
- Test API endpoint directly (curl, Postman)
- Review service health status page
- Check for rate limiting or IP blocking

### State Not Persisting

**Problem:** State resets between sessions

**Solutions:**
- Ensure you call `self.save_state(context)` after updates
- Verify spec directory exists and is writable
- Check for `.{plugin-name}_state.json` in spec directory
- Look for exceptions during state save/load

### Tasks Not Syncing

**Problem:** Subtasks don't appear in external service

**Solutions:**
- Verify `sync_data()` is being called
- Check implementation_plan.json exists and is valid
- Look for sync errors in logs
- Test external API directly to rule out service issues
- Verify task mapping is being saved to state

## Contributing

We welcome contributions to improve this guide or add more integration examples!

- [GitHub Issues](https://github.com/AndyMik90/Auto-Claude/issues)
- [GitHub Discussions](https://github.com/AndyMik90/Auto-Claude/discussions)

Happy integrating! 🔌
