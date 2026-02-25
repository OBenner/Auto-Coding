# Hello World Agent Plugin

A simple example agent plugin that demonstrates the Auto Claude plugin system's basic capabilities and lifecycle hooks.

## Overview

This plugin logs messages at each stage of the agent lifecycle, helping developers understand how agent plugins work in Auto Claude. It's a minimal but complete implementation that can serve as a template for building more complex agent plugins.

## What It Does

- **Logs lifecycle events**: Tracks when the plugin is loaded, enabled, disabled, and unloaded
- **Monitors agent sessions**: Records before and after each agent session
- **Tracks session count**: Maintains a counter of sessions handled
- **Demonstrates context access**: Shows how to access project, spec, and session information
- **Implements all hooks**: Complete implementation of the AgentPlugin interface

## Features Demonstrated

### Lifecycle Hooks

- `on_load()` - Called when plugin is first discovered and loaded
- `on_enable()` - Called when user enables the plugin
- `on_disable()` - Called when user disables the plugin
- `on_unload()` - Called when plugin is being unloaded (app shutdown)

### Agent Hooks

- `before_session()` - Called before an agent session starts
- `after_session()` - Called after an agent session completes
- `on_message()` - Called when agent receives messages (monitoring)

### Context Access

The plugin demonstrates how to access:
- `context.project_dir` - Root directory of the project
- `context.spec_dir` - Directory containing the current spec
- `context.spec_name` - Name of the current spec
- `context.project_name` - Name of the project
- `context.phase` - Current phase (planning, coding, qa_review, etc.)
- `context.session_id` - Unique identifier for the session

## Installation

### From Directory

1. **Copy the plugin directory** to Auto Claude's plugin location:
   ```bash
   cp -r examples/plugins/hello-world-agent ~/.auto-claude/plugins/user/
   ```

2. **Using the Electron UI**:
   - Open Auto Claude desktop app
   - Navigate to **Plugins** (shortcut: `U`)
   - Click **Install Plugin**
   - Select **Directory** as installation source
   - Browse to `examples/plugins/hello-world-agent`
   - Click **Install**

3. **Verify installation**:
   ```bash
   python -c "from apps.backend.plugins.loader import PluginLoader; loader = PluginLoader(); plugin = loader.load_plugin('examples/plugins/hello-world-agent'); print('OK')"
   ```

## Usage

Once installed and enabled, the plugin will automatically:
1. Log when it's loaded and enabled
2. Log before each agent session starts
3. Log after each agent session completes
4. Track the total number of sessions

You'll see log output like:

```
INFO: hello-world-agent: Plugin loaded
INFO: hello-world-agent: Plugin enabled
INFO: hello-world-agent: Starting session #1 for spec '001-feature' in project 'my-project'
DEBUG: hello-world-agent: Session phase: coding
INFO: hello-world-agent: Session succeeded for spec '001-feature'
```

## Configuration

This plugin requires no configuration. It has:
- **No required permissions** - Safe to install and enable
- **No dependencies** - Works standalone
- **No external services** - All functionality is local

## Development

### File Structure

```
hello-world-agent/
├── plugin.json    # Plugin metadata and manifest
├── agent.py       # Plugin implementation
└── README.md      # This documentation
```

### Extending This Plugin

To create your own agent plugin based on this example:

1. **Copy the plugin directory**:
   ```bash
   cp -r examples/plugins/hello-world-agent examples/plugins/my-plugin
   ```

2. **Update plugin.json**:
   - Change `name` to a unique identifier
   - Update `author`, `description`, `version`
   - Add `required_permissions` if needed

3. **Modify agent.py**:
   - Rename the class (e.g., `MyAgentPlugin`)
   - Implement your custom logic in lifecycle hooks
   - Add custom tools or behaviors

4. **Test your plugin**:
   ```bash
   python -c "from apps.backend.plugins.loader import PluginLoader; loader = PluginLoader(); plugin = loader.load_plugin('examples/plugins/my-plugin'); print('OK')"
   ```

### Adding Custom Tools

Agent plugins can provide custom tools to agents by implementing tool creation in the `on_enable()` hook. See the `custom-integration` example plugin for how to create MCP tools.

### State Management

To persist state across sessions:

```python
def on_load(self):
    # Load state from file
    state_file = Path(__file__).parent / "state.json"
    if state_file.exists():
        with open(state_file, 'r') as f:
            self.state = json.load(f)

def on_unload(self):
    # Save state to file
    state_file = Path(__file__).parent / "state.json"
    with open(state_file, 'w') as f:
        json.dump(self.state, f)
```

## Permissions

This plugin requires **no permissions** because it only logs messages and doesn't:
- Read or write files
- Make network requests
- Execute commands
- Access secrets

For plugins that need permissions, add them to `plugin.json`:

```json
{
  "required_permissions": [
    "read_files",
    "write_files"
  ]
}
```

## Troubleshooting

### Plugin not appearing in list

- Verify the plugin directory is in the correct location
- Check that `plugin.json` is valid JSON
- Ensure `plugin_type` is set to `"agent"`

### Plugin fails to load

- Check the logs for error messages
- Verify all required fields are present in `plugin.json`
- Ensure the plugin class extends `AgentPlugin`

### Logs not appearing

- Make sure the plugin is **enabled**, not just installed
- Check your logging configuration level
- Verify logger is configured to output to console or file

## Learn More

- [Agent Plugin Development Guide](../../../guides/plugins/agent-plugins.md)
- [Plugin SDK Documentation](../../../apps/backend/plugins/sdk/agent.py)
- [Plugin Getting Started](../../../guides/plugins/getting-started.md)

## License

MIT - See LICENSE file for details
