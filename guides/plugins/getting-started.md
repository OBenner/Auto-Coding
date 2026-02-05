# Plugin Development - Getting Started

Welcome to Auto Claude's plugin system! This guide will help you create your first plugin and understand the core concepts of Auto Claude's extensibility framework.

## Overview

Auto Claude's plugin system allows you to extend the platform with:

- **Agent Plugins** - Custom agents with specialized tools and behaviors
- **Integration Plugins** - External service integrations using MCP tools
- **UI Plugins** - Frontend extensions with React components and IPC handlers

All plugins run in a secure sandbox with explicit permission controls to protect your projects.

## Quick Start

### 1. Choose a Plugin Type

Start with an example plugin based on what you want to build:

```bash
# Agent plugin - Add custom agent behaviors
cp -r examples/plugins/hello-world-agent my-plugin

# Integration plugin - Connect external services
cp -r examples/plugins/custom-integration my-plugin

# UI plugin - Add frontend components
cp -r examples/plugins/ui-extension my-plugin
```

### 2. Update Plugin Metadata

Edit `my-plugin/plugin.json`:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "What your plugin does",
  "plugin_type": "agent",
  "required_permissions": [],
  "dependencies": [],
  "homepage": "https://github.com/yourname/my-plugin",
  "license": "MIT"
}
```

### 3. Install and Test

**Using the UI:**
1. Open Auto Claude desktop app
2. Navigate to **Plugins** (shortcut: `U`)
3. Click **Install Plugin**
4. Select **Directory** and browse to `my-plugin`
5. Click **Install**

**Using CLI:**
```bash
# Copy to user plugins directory
cp -r my-plugin ~/.auto-claude/plugins/user/

# Verify it loads
python -c "from apps.backend.plugins.loader import PluginLoader; \
loader = PluginLoader(); \
plugin = loader.load_plugin('my-plugin'); \
print('Plugin loaded:', plugin.metadata.name)"
```

## Plugin Structure

### Directory Layout

Every plugin must follow this structure:

```
my-plugin/
├── plugin.json          # Required: Plugin metadata and manifest
├── agent.py             # For agent plugins
├── integration.py       # For integration plugins
├── ui-component.tsx     # For UI plugins
└── README.md            # Recommended: Documentation
```

### The plugin.json Manifest

The manifest defines your plugin's identity, type, and requirements:

```json
{
  "name": "unique-plugin-name",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Clear description of what your plugin does",
  "plugin_type": "agent",
  "required_permissions": [
    "read_files",
    "write_files"
  ],
  "dependencies": [],
  "homepage": "https://github.com/yourname/plugin",
  "license": "MIT"
}
```

**Required Fields:**
- `name` - Unique identifier (lowercase, hyphens only)
- `version` - Semantic version (e.g., "1.0.0")
- `author` - Your name or organization
- `description` - What your plugin does
- `plugin_type` - One of: `agent`, `integration`, `ui`
- `license` - License identifier (e.g., "MIT", "Apache-2.0")

**Optional Fields:**
- `required_permissions` - Array of permission strings (see Permissions section)
- `dependencies` - Array of Python package names
- `homepage` - URL to plugin's homepage/repository

## Plugin Types

### Agent Plugins

Agent plugins extend agent behavior by providing custom tools and lifecycle hooks.

**Use cases:**
- Add specialized tools for agents to use
- Monitor agent sessions and log activities
- Inject custom prompts or context
- Track metrics across builds

**Lifecycle hooks:**
- `on_load()` - Plugin discovered and loaded
- `on_enable()` - User enables plugin
- `on_disable()` - User disables plugin
- `on_unload()` - Plugin being unloaded (shutdown)
- `before_session(context)` - Before agent session starts
- `after_session(context, success)` - After agent session completes
- `on_message(context, message)` - When agent receives messages

**Example:** See [examples/plugins/hello-world-agent](../../examples/plugins/hello-world-agent)

**Learn more:** [Agent Plugin Development Guide](agent-plugins.md)

### Integration Plugins

Integration plugins connect Auto Claude to external services by creating MCP tools that agents can use.

**Use cases:**
- Integrate with issue trackers (Jira, Linear, GitHub)
- Connect to communication platforms (Slack, Discord)
- Sync with cloud storage (Google Drive, Dropbox)
- Query databases or APIs

**Lifecycle hooks:**
- `create_mcp_tools()` - Create MCP tools for agents
- `create_mcp_server()` - Build MCP server from tools
- `is_available()` - Check if service is accessible
- `sync_data(project_dir, spec_dir)` - Sync with external service
- `on_subtask_update(subtask_id, status, notes)` - Real-time subtask updates
- `on_build_start(spec_dir)` - Build lifecycle hook
- `on_build_complete(spec_dir, success)` - Build lifecycle hook

**Example:** See [examples/plugins/custom-integration](../../examples/plugins/custom-integration)

**Learn more:** [Integration Plugin Development Guide](integration-plugins.md)

### UI Plugins

UI plugins extend the Electron frontend with custom React components and IPC handlers.

**Use cases:**
- Add dashboard widgets
- Create custom settings panels
- Add sidebar navigation items
- Extend context menus
- Add status bar indicators

**Extension points:**
- `sidebar` - Add sidebar navigation items
- `settings` - Add settings panels
- `dashboard` - Add dashboard widgets
- `toolbar` - Add toolbar buttons
- `context_menu` - Extend context menus
- `status_bar` - Add status bar items

**Lifecycle hooks:**
- `get_ui_components()` - Register UI components
- `register_ipc_handlers()` - Backend-frontend communication
- `get_frontend_assets()` - Provide static assets
- `on_frontend_ready()` - Frontend loaded and ready
- `on_window_focus()` - Window gains focus

**Example:** See [examples/plugins/ui-extension](../../examples/plugins/ui-extension)

**Learn more:** [UI Plugin Development Guide](ui-plugins.md)

## Permission System

Plugins must explicitly declare required permissions in `plugin.json`. This security model prevents plugins from accessing sensitive resources without user awareness.

### Available Permissions

| Permission | Description | Use Case |
|------------|-------------|----------|
| `read_files` | Read files from project directory | Access config files, read source code |
| `write_files` | Write files to project directory | Generate reports, save state |
| `network_access` | Make network requests | Connect to external APIs |
| `execute_commands` | Execute shell commands | Run build tools, call CLIs |
| `access_secrets` | Access environment variables/secrets | Use API keys from `.env` |
| `create_mcp_tools` | Register MCP tools with Claude SDK | Provide tools for agents |

### Requesting Permissions

Add permissions to your `plugin.json`:

```json
{
  "required_permissions": [
    "read_files",
    "network_access"
  ]
}
```

### Permission Validation

The plugin system automatically validates permissions before sensitive operations:

```python
from apps.backend.plugins.base import PermissionValidator, PluginPermission

class MyPlugin(AgentPlugin):
    def before_session(self, context):
        # Automatically checks if plugin has required permission
        validator = PermissionValidator(self.metadata)
        validator.require(PluginPermission.READ_FILES, "read config")

        # Now safe to read files
        with open(context.project_dir / "config.json") as f:
            config = json.load(f)
```

## Installation Methods

### From Directory (Available Now)

Install a plugin from a local directory using the UI or CLI:

**UI Method:**
1. Navigate to **Plugins** page
2. Click **Install Plugin**
3. Select **Directory**
4. Browse to plugin folder
5. Click **Install**

**CLI Method:**
```bash
# Copy to user plugins directory
cp -r /path/to/my-plugin ~/.auto-claude/plugins/user/

# Or use symlink for development
ln -s /path/to/my-plugin ~/.auto-claude/plugins/user/my-plugin
```

### From Zip File (Coming Soon)

Package your plugin as a zip file for easy distribution:

```bash
# Create plugin zip
cd my-plugin
zip -r ../my-plugin-v1.0.0.zip .
```

Users will be able to install from zip through the UI.

### From Marketplace (Coming Soon)

The Auto Claude plugin marketplace will allow users to:
- Browse and search plugins
- Install with one click
- Receive automatic updates
- Rate and review plugins

## Development Workflow

### 1. Set Up Development Environment

```bash
# Clone plugin template
cp -r examples/plugins/hello-world-agent my-plugin
cd my-plugin

# Install as symlink for live development
ln -s $(pwd) ~/.auto-claude/plugins/user/my-plugin
```

### 2. Implement Plugin Logic

Edit your plugin's main file (`agent.py`, `integration.py`, or `plugin.py`):

```python
from apps.backend.plugins.sdk.agent import AgentPlugin, AgentContext

class MyAgentPlugin(AgentPlugin):
    def on_load(self):
        """Called when plugin is loaded."""
        self.logger.info("My plugin loaded!")

    def before_session(self, context: AgentContext):
        """Called before agent session starts."""
        self.logger.info(f"Starting session for {context.spec_name}")
        # Add custom logic here
```

### 3. Test Your Plugin

**Verify plugin loads:**
```bash
python -c "from apps.backend.plugins.loader import PluginLoader; \
loader = PluginLoader(); \
plugin = loader.load_plugin('my-plugin'); \
print('OK')"
```

**Test in a real build:**
1. Create a test spec
2. Enable your plugin in the UI
3. Run the build and monitor logs
4. Verify your plugin's hooks are called

### 4. Handle Errors Gracefully

Always implement error handling:

```python
def before_session(self, context: AgentContext):
    try:
        # Your plugin logic
        data = self.load_config()
        self.process_data(data)
    except Exception as e:
        self.logger.error(f"Plugin error: {e}", exc_info=True)
        # Don't crash the entire system
        return
```

### 5. Add Logging

Use the built-in logger for debugging:

```python
def on_enable(self):
    self.logger.debug("Debug info")
    self.logger.info("Informational message")
    self.logger.warning("Warning message")
    self.logger.error("Error message")
```

## Testing

### Unit Testing

Create tests for your plugin logic:

```python
# tests/test_my_plugin.py
import pytest
from my_plugin.agent import MyAgentPlugin

def test_plugin_loads():
    plugin = MyAgentPlugin()
    assert plugin is not None

def test_session_handling():
    plugin = MyAgentPlugin()
    context = create_test_context()

    plugin.before_session(context)
    # Assert expected behavior
```

Run tests:
```bash
pytest tests/
```

### Integration Testing

Test your plugin with the full plugin loader:

```python
from apps.backend.plugins.loader import PluginLoader

def test_plugin_loads_with_loader():
    loader = PluginLoader()
    plugin = loader.load_plugin('examples/plugins/my-plugin')

    assert plugin.metadata.name == 'my-plugin'
    assert plugin.metadata.plugin_type == 'agent'
```

### Manual Testing

1. Install plugin in Auto Claude
2. Enable plugin
3. Create a test spec
4. Run build and observe logs
5. Verify plugin behavior

## Debugging

### Enable Debug Logging

Set logging level in your plugin:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

**Plugin not appearing in list:**
- Verify `plugin.json` is valid JSON
- Check plugin is in correct directory (`~/.auto-claude/plugins/user/`)
- Ensure `plugin_type` matches your plugin class

**Plugin fails to load:**
- Check logs for error messages
- Verify all required fields in `plugin.json`
- Ensure plugin class extends correct base class
- Check for Python syntax errors

**Permission denied errors:**
- Add required permission to `plugin.json`
- Reinstall plugin after updating manifest
- Check PermissionValidator logs for details

**Hooks not being called:**
- Verify plugin is **enabled**, not just installed
- Check agent type matches (agent plugins only work with agent sessions)
- Look for errors in `on_load()` or `on_enable()` that prevent initialization

### Inspecting Plugin State

```python
# In your plugin code
def before_session(self, context):
    self.logger.debug(f"Context: {context}")
    self.logger.debug(f"Metadata: {self.metadata}")
    self.logger.debug(f"Permissions: {self.metadata.required_permissions}")
```

### Using the Python Debugger

```python
def before_session(self, context):
    import pdb; pdb.set_trace()  # Breakpoint
    # Your code here
```

## Best Practices

### 1. Fail Gracefully

Never crash the entire system:

```python
def before_session(self, context):
    try:
        # Your logic
        pass
    except Exception as e:
        self.logger.error(f"Error: {e}", exc_info=True)
        return  # Don't propagate error
```

### 2. Minimize Permissions

Only request permissions you actually need:

```json
{
  "required_permissions": ["read_files"]  // Not ["read_files", "write_files"]
}
```

### 3. Document Your Plugin

Include a comprehensive README.md:
- What your plugin does
- Installation instructions
- Configuration options
- Usage examples
- Troubleshooting

### 4. Version Your Plugin

Use semantic versioning:
- `1.0.0` - Initial release
- `1.1.0` - New feature (backward compatible)
- `1.0.1` - Bug fix
- `2.0.0` - Breaking change

### 5. Handle State Carefully

Persist state between sessions if needed:

```python
def on_load(self):
    self.state_file = Path(__file__).parent / "state.json"
    if self.state_file.exists():
        with open(self.state_file) as f:
            self.state = json.load(f)

def on_unload(self):
    with open(self.state_file, 'w') as f:
        json.dump(self.state, f)
```

### 6. Use Meaningful Names

Choose descriptive, unique plugin names:
- ✅ `jira-integration`
- ✅ `code-quality-checker`
- ❌ `plugin1`
- ❌ `my-plugin`

## Plugin Discovery Paths

Auto Claude looks for plugins in these locations (in order):

1. **User plugins:** `~/.auto-claude/plugins/user/`
   - User-installed plugins
   - Overrides system plugins with same name
   - Persistent across Auto Claude updates

2. **System plugins:** `~/.auto-claude/plugins/system/`
   - Auto Claude bundled plugins
   - Updated with Auto Claude releases
   - Can be overridden by user plugins

**Note:** User plugins take precedence if a plugin with the same name exists in both locations.

## Security and Sandboxing

All plugins run in a secure sandbox with:

- **Filesystem restrictions** - Access limited to plugin directory and project directory
- **Resource limits** - CPU, memory, and execution time caps
- **Permission validation** - Actions checked against declared permissions
- **Process isolation** - Plugins run in separate processes

This ensures:
- Plugins cannot access files outside permitted directories
- Runaway plugins are automatically terminated
- Malicious plugins cannot harm your system
- System stability even if plugins crash

## Next Steps

- **Agent Plugins:** Read [Agent Plugin Development Guide](agent-plugins.md)
- **Integration Plugins:** Read [Integration Plugin Development Guide](integration-plugins.md)
- **UI Plugins:** Read [UI Plugin Development Guide](ui-plugins.md)
- **Examples:** Study plugins in `examples/plugins/`
- **SDK Reference:** Explore `apps/backend/plugins/sdk/`

## Getting Help

- **Issues:** [GitHub Issues](https://github.com/OBenner/Auto-Coding/issues)
- **Discussions:** [GitHub Discussions](https://github.com/OBenner/Auto-Coding/discussions)
- **Documentation:** [guides/plugins/](.)

## Contributing Your Plugin

Once your plugin is ready, consider sharing it:

1. Publish to GitHub
2. Add to Auto Claude plugin list (coming soon)
3. Submit to plugin marketplace (coming soon)
4. Share in GitHub Discussions

Happy plugin development! 🚀
