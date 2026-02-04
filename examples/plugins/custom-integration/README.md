# Custom Integration Plugin

An example integration plugin that demonstrates how to connect Auto Claude to external services using the IntegrationPlugin SDK.

## Overview

This plugin connects to a mock file-based "TaskManager" service and provides MCP tools for agents to create, list, and update tasks. It demonstrates all key features of integration plugins without requiring external dependencies.

## What It Does

- **Provides MCP tools** for agents to interact with an external service
- **Manages configuration** (data directory, API settings)
- **Persists state** across sessions (task counter, sync timestamps, task mappings)
- **Syncs data** between Auto Claude and the external service
- **Tracks build lifecycle** (creates tasks when builds start/complete)
- **Updates tasks** in real-time when subtask statuses change

## Features Demonstrated

### MCP Tools for Agents

The plugin provides 4 tools that agents can use:

- `create_task(title, description)` - Create a new task in the external system
- `list_tasks(status?)` - List all tasks, optionally filtered by status
- `update_task_status(task_id, status)` - Update a task's status
- `get_task_details(task_id)` - Get details of a specific task

### Configuration Management

- Reads `CUSTOM_INTEGRATION_DATA_DIR` from environment or `.env`
- Falls back to default location `~/.auto-claude/task-manager`
- Demonstrates `get_config_value()` and `set_config_value()`

### State Persistence

The plugin tracks:
- `task_count` - Total number of tasks created
- `task_mapping` - Map of subtask IDs to external task IDs
- `last_sync`, `last_create`, `last_update`, `last_list` - Timestamps
- `build_start_time`, `build_end_time`, `build_success` - Build tracking

State is saved to `.custom-integration_state.json` in the spec directory.

### Data Synchronization

- **sync_data()** - Pushes all subtasks from implementation_plan.json to external system
- **on_subtask_update()** - Real-time updates when subtask status changes
- **Bidirectional sync** - Can pull updates from external system (demonstrated in code comments)

### Build Lifecycle Hooks

- **on_build_start()** - Creates a "Build Started" task when build begins
- **on_build_complete()** - Creates a "Build Complete/Failed" task when build ends
- Tracks build duration and success status

### External Service Integration

- **MockTaskManagerClient** - Demonstrates how to wrap an external API
- File-based storage (simulates REST API, database, etc.)
- Connection checking with `is_connected()`
- Error handling and logging

## Installation

### From Directory

1. **Copy the plugin directory** to Auto Claude's plugin location:
   ```bash
   cp -r examples/plugins/custom-integration ~/.auto-claude/plugins/user/
   ```

2. **Using the Electron UI**:
   - Open Auto Claude desktop app
   - Navigate to **Plugins** (shortcut: `U`)
   - Click **Install Plugin**
   - Select **Directory** as installation source
   - Browse to `examples/plugins/custom-integration`
   - Click **Install**

3. **Verify installation**:
   ```bash
   python -c "from apps.backend.plugins.loader import PluginLoader; loader = PluginLoader(); plugin = loader.load_plugin('examples/plugins/custom-integration'); print('OK')"
   ```

## Usage

### Basic Usage

Once installed and enabled:

1. **Agents automatically get access** to the 4 MCP tools
2. **Tasks are synced** to the external system when builds run
3. **Subtask updates** are pushed in real-time
4. **Build events** are tracked as tasks

### Configuration

Set the data directory (optional):

```bash
# In apps/backend/.env
CUSTOM_INTEGRATION_DATA_DIR=/path/to/task-manager-data
```

If not set, defaults to `~/.auto-claude/task-manager`.

### Viewing Tasks

Tasks are stored in JSON format:

```bash
cat ~/.auto-claude/task-manager/tasks.json
```

Example task:

```json
{
  "id": 1,
  "title": "[Backend Plugin SDK] subtask-1-1",
  "description": "Create plugin base interface and metadata schema",
  "status": "completed",
  "created_at": "2026-01-28T12:00:00",
  "updated_at": "2026-01-28T12:30:00"
}
```

### Agent Tool Usage

Agents can use the tools in their sessions:

```python
# Agent creates a task
result = create_task("Implement authentication", "Add JWT-based auth to API")
# Returns: {"id": 5, "title": "Implement authentication", ...}

# Agent lists pending tasks
tasks = list_tasks(status="pending")
# Returns: [{"id": 1, ...}, {"id": 3, ...}]

# Agent updates task status
update_task_status(5, "completed")
# Returns: {"id": 5, "status": "completed", ...}

# Agent gets task details
task = get_task_details(5)
# Returns: {"id": 5, "title": "Implement authentication", ...}
```

## Configuration Options

### Environment Variables

- `CUSTOM_INTEGRATION_DATA_DIR` - Directory for task storage (default: `~/.auto-claude/task-manager`)

### Plugin Permissions

Required permissions (declared in `plugin.json`):
- `read_files` - Read task data and implementation plans
- `write_files` - Write task data and state

## Development

### File Structure

```
custom-integration/
├── plugin.json        # Plugin metadata and manifest
├── integration.py     # Plugin implementation
└── README.md          # This documentation
```

### Extending This Plugin

To create your own integration based on this example:

1. **Copy the plugin directory**:
   ```bash
   cp -r examples/plugins/custom-integration examples/plugins/my-integration
   ```

2. **Update plugin.json**:
   - Change `name` to a unique identifier
   - Update `author`, `description`, `version`
   - Adjust `required_permissions` as needed

3. **Replace MockTaskManagerClient** with your actual service client:
   ```python
   class MyServiceClient:
       def __init__(self, api_key: str):
           self.api_key = api_key
           self.base_url = "https://api.myservice.com"

       def is_connected(self) -> bool:
           # Check API connectivity
           response = requests.get(f"{self.base_url}/health")
           return response.status_code == 200

       def create_task(self, title: str, description: str) -> dict:
           # Call REST API to create task
           response = requests.post(
               f"{self.base_url}/tasks",
               json={"title": title, "description": description},
               headers={"Authorization": f"Bearer {self.api_key}"}
           )
           return response.json()
   ```

4. **Update MCP tools** to match your service's API:
   - Add tools for your service's operations
   - Ensure clear docstrings (agents use these)
   - Handle errors gracefully

5. **Test your plugin**:
   ```bash
   python -c "from apps.backend.plugins.loader import PluginLoader; loader = PluginLoader(); plugin = loader.load_plugin('examples/plugins/my-integration'); print('OK')"
   ```

### Adding Authentication

For services requiring API keys:

```python
def on_load(self) -> None:
    # Validate API key is configured
    api_key = self.get_config_value("MY_SERVICE_API_KEY")
    if not api_key:
        raise ValueError("MY_SERVICE_API_KEY not configured in .env")

def on_enable(self) -> None:
    # Initialize client with API key
    api_key = self.get_config_value("MY_SERVICE_API_KEY")
    self.client = MyServiceClient(api_key)

    # Test connection
    if not self.client.is_connected():
        raise ConnectionError("Failed to connect to MyService")
```

### State Management Best Practices

```python
# Always load state before using it
self.load_state(context)

# Update state incrementally
context.set_state("counter", context.get_state("counter", 0) + 1)

# Save state after updates
self.save_state(context)

# Use timestamps for debugging
context.set_state("last_action", datetime.now().isoformat())
```

### Bi-directional Sync

To pull updates from the external service:

```python
def sync_data(self, context: IntegrationContext) -> None:
    # Push: Auto Claude → External Service
    plan = self.load_implementation_plan(context)
    for subtask in get_all_subtasks(plan):
        self.push_subtask_to_service(subtask)

    # Pull: External Service → Auto Claude
    external_tasks = self.client.list_tasks()
    for task in external_tasks:
        if task_needs_update(task):
            self.update_subtask_from_service(task)
```

## Real-World Integration Examples

### Issue Tracker (Jira, Linear, GitHub)

Replace MockTaskManagerClient with:
- REST API client (requests, httpx)
- GraphQL client (gql, sgqlc)
- SDK client (linear-sdk, PyGithub)

### Monitoring/Observability (Datadog, New Relic)

Add tools for:
- Creating custom metrics
- Logging build events
- Sending traces

### Project Management (Asana, Monday, ClickUp)

Add tools for:
- Creating projects from specs
- Syncing subtasks to tasks
- Updating progress

### Communication (Slack, Discord, Teams)

Add tools for:
- Sending build notifications
- Creating discussion threads
- Posting status updates

## Permissions

This plugin requires:
- `read_files` - Read implementation plans and task data
- `write_files` - Write task data and persistent state

For plugins that need additional permissions:

```json
{
  "required_permissions": [
    "read_files",
    "write_files",
    "network_access",
    "execute_commands"
  ]
}
```

## Troubleshooting

### Plugin not appearing in list

- Verify the plugin directory is in the correct location
- Check that `plugin.json` is valid JSON
- Ensure `plugin_type` is set to `"integration"`

### Plugin fails to load

- Check the logs for error messages
- Verify all required fields are present in `plugin.json`
- Ensure the plugin class extends `IntegrationPlugin`
- Check that `required_permissions` are granted

### Tools not available to agents

- Make sure the plugin is **enabled**, not just installed
- Verify `is_available()` returns `True`
- Check that `create_mcp_tools()` returns a non-empty list
- Look for errors in the logs during tool creation

### State not persisting

- Ensure you call `self.save_state(context)` after updates
- Check that the spec directory exists and is writable
- Look for `.custom-integration_state.json` in the spec directory
- Verify no exceptions during state save/load

### Tasks not syncing

- Verify the client is connected (`is_available()` returns `True`)
- Check the implementation_plan.json exists and is valid
- Look for sync errors in the logs
- Ensure `sync_data()` is being called (during build or manually)

## Learn More

- [Integration Plugin Development Guide](../../../guides/plugins/integration-plugins.md)
- [Plugin SDK Documentation](../../../apps/backend/plugins/sdk/integration.py)
- [Linear Integration Source](../../../apps/backend/integrations/linear/integration.py) - Real-world example
- [Plugin Getting Started](../../../guides/plugins/getting-started.md)

## License

MIT - See LICENSE file for details
