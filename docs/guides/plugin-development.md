# Plugin Development Guide

Complete guide to creating, installing, and distributing plugins for Auto Code.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Plugin Types](#plugin-types)
- [Plugin Manifest](#plugin-manifest)
- [Plugin Lifecycle](#plugin-lifecycle)
- [Creating Agent Plugins](#creating-agent-plugins)
- [Creating Integration Plugins](#creating-integration-plugins)
- [Creating UI Plugins](#creating-ui-plugins)
- [Security & Permissions](#security--permissions)
- [MCP Tool Creation](#mcp-tool-creation)
- [CLI Usage](#cli-usage)
- [Best Practices](#best-practices)
- [Distribution](#distribution)
- [Troubleshooting](#troubleshooting)

---

## Overview

Auto Code's plugin system enables third-party developers to extend functionality without modifying core code. Plugins can:

- **Hook into agent lifecycle** - Run code before/after agent sessions
- **Create MCP tools** - Add custom tools for agents to use
- **Integrate external services** - Connect to issue trackers, notification systems, etc.
- **Extend the UI** - Add custom views and components to the Electron app
- **Monitor agent behavior** - Track messages, tools usage, and session outcomes

### Architecture

The plugin system consists of:

- **Plugin SDK** (`apps/backend/plugins/sdk/`) - Base classes for agent, integration, and UI plugins
- **Plugin Registry** (`apps/backend/plugins/registry.py`) - Discovers and manages installed plugins
- **Plugin Loader** (`apps/backend/plugins/loader.py`) - Loads plugins with security validation
- **Plugin CLI** (`apps/backend/plugins/cli.py`) - Command-line interface for plugin management
- **Isolation Layer** (`apps/backend/plugins/isolation.py`) - Sandboxed execution environment

### Plugin Discovery

Plugins are discovered from these locations (in order):

1. **Built-in plugins** - `apps/backend/plugins/builtin/`
2. **User plugins** - `~/.auto-claude/plugins/user/`
3. **Project plugins** - `.auto-claude/plugins/` (gitignored)

---

## Quick Start

### 1. Create Plugin Directory

```bash
mkdir -p my-plugin
cd my-plugin
```

### 2. Create Plugin Manifest (`plugin.json`)

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "My custom Auto Code plugin",
  "plugin_type": "agent",
  "required_permissions": [],
  "auto_claude_version": ">=2.8.0"
}
```

### 3. Create Plugin Implementation

**Agent plugin** (`agent.py`):

```python
from plugins.sdk.agent import AgentPlugin, AgentContext
import logging

logger = logging.getLogger(__name__)

class MyAgentPlugin(AgentPlugin):
    def on_load(self):
        logger.info(f"{self.name} loaded")

    def on_enable(self):
        logger.info(f"{self.name} enabled")

    def before_session(self, context: AgentContext):
        logger.info(f"Session starting for {context.spec_name}")

    def after_session(self, context: AgentContext, success: bool):
        status = "succeeded" if success else "failed"
        logger.info(f"Session {status}")

    def on_disable(self):
        logger.info(f"{self.name} disabled")

    def on_unload(self):
        logger.info(f"{self.name} unloaded")
```

### 4. Install and Enable

```bash
# Install from local path
cd apps/backend
python plugins/cli.py install --path ../../my-plugin

# Enable the plugin
python plugins/cli.py enable my-plugin

# Verify it's enabled
python plugins/cli.py list --enabled-only
```

### 5. Test Your Plugin

Run a spec to see your plugin's lifecycle hooks in action:

```bash
cd apps/backend
python run.py --spec 001
```

Check logs for your plugin's output.

---

## Plugin Types

### Agent Plugins

**Purpose**: Hook into agent lifecycle, monitor sessions, add custom behaviors

**Base Class**: `AgentPlugin` (`plugins.sdk.agent`)

**Key Hooks**:
- `before_session(context)` - Called before agent session starts
- `after_session(context, success)` - Called after agent session completes
- `on_message(context, message)` - Called when agent receives messages

**Use Cases**:
- Session analytics and metrics
- Custom logging and monitoring
- Agent behavior modification
- Session notifications

**Example**: `examples/plugins/hello-world-agent/`

---

### Integration Plugins

**Purpose**: Connect to external services, create MCP tools, sync data

**Base Class**: `IntegrationPlugin` (`plugins.sdk.integration`)

**Key Methods**:
- `create_mcp_tools(context)` - Return list of MCP tool functions
- `is_available()` - Check if integration is ready
- `sync_data(context)` - Sync with external service
- `on_build_start(context)` - Called when build starts
- `on_build_complete(context, success)` - Called when build completes
- `on_subtask_update(context, subtask_id, status)` - Called on subtask changes

**Use Cases**:
- Issue tracker integrations (Linear, Jira, GitHub Issues)
- Notification systems (Slack, Discord, Teams)
- Custom LLM providers
- File template systems
- External data sources

**Example**: `examples/plugins/custom-integration/`

---

### UI Plugins

**Purpose**: Add custom views, components, and functionality to Electron UI

**Base Class**: `UIPlugin` (`plugins.sdk.ui`)

**Key Capabilities**:
- Register custom React components
- Add menu items and keyboard shortcuts
- Extend existing views
- Create custom pages

**Use Cases**:
- Custom dashboards
- Spec visualization tools
- Settings panels
- Custom editors

**Example**: `examples/plugins/ui-extension/`

---

## Tool Hooks and Backend Coverage

Beyond the lifecycle hooks above, a plugin declaring the `generic_edit` or
`full_agent_runtime` capability can intercept individual tool calls:

- `augment_prompt(context)` - contribute scoped instructions to the agent prompt
- `pre_tool(context, tool_name, tool_input)` - inspect a tool call before it
  runs; return `ToolHookDecision.block(reason)` to prevent execution
- `post_tool(context, tool_name, tool_input, tool_result)` - observe a tool
  call after it ran

### Which hooks run on which backend

Auto Code runs agents on more than one execution backend. Coverage differs, so
write hooks defensively:

| Hook | Claude SDK (`full_autonomous`) | Direct-API in-process (`generic_edit`) | Codex / generic CLI |
|------|:---:|:---:|:---:|
| `before_session` / `after_session` / `on_message` | ✅ | ✅ | ✅ |
| `pre_tool` (block) | ✅ | ✅ | ❌ (opaque CLI loop) |
| `post_tool` (observe) | ✅ | ✅ (observational) | ❌ |
| `augment_prompt` | ✅ | see note | ❌ |

Codex and other CLI backends run their own tool loop inside a separate process,
so per-tool interception is not possible there — only prompt-level and lifecycle
hooks can reach them.

### Direct-API tool-name normalization

The Direct-API runtime speaks its own local-action vocabulary (`run_command`,
`write_file`, `replace_text`, ...). Before your hook is called, each action is
normalized to the **canonical Claude SDK tool vocabulary** so a hook written
against SDK names matches on both backends. Match against the SDK name, not the
native one — e.g. a shell command is `Bash` with `{"command": ...}`, a full-file
write is `Write` with `{"file_path", "content"}`, an in-place edit is `Edit` with
`{"file_path", "old_string", "new_string"}`. Actions without an SDK equivalent
use a stable extension name: `Delete`, `Move`, `ApplyPatch`. The mapping lives in
`apps/backend/agents/runtime/plugin_tool_bridge.py`.

### Direct-API limitations (design decisions, not bugs)

1. **`pre_tool` is block-only.** On the SDK path a hook may return a *modified*
   `tool_input`; on Direct-API the normalization is one-directional
   (native → inspection view), so only `block`/allow is honored — input rewrite
   is ignored.
2. **`post_tool` is observational.** The action has already executed, so a
   `post_tool` block cannot un-run it. The block is logged and annotated onto
   the result (`plugin_post_tool_block`) rather than rolled back.
3. **Read-only actions are gated off by default.** Reads/searches/listings
   (`Read`, `Grep`, `LS`, git status/diff) do not trigger hooks on Direct-API
   unless read-only hooking is explicitly enabled, so plugins don't run on every
   file read.

> **Note (`augment_prompt`)**: prompt augmentation currently reaches the Claude
> SDK backend only. Cross-backend prompt augmentation is tracked as separate
> work; do not rely on `augment_prompt` for Direct-API/Codex runs yet.

---

## Plugin Manifest

Every plugin requires a `plugin.json` manifest file:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Brief description of what the plugin does",
  "plugin_type": "agent",
  "required_permissions": [
    "read_files",
    "network_access"
  ],
  "dependencies": [],
  "homepage": "https://github.com/yourname/my-plugin",
  "license": "MIT",
  "auto_claude_version": ">=2.8.0"
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique plugin identifier (lowercase, hyphens) |
| `version` | string | Semantic version (e.g., "1.0.0") |
| `author` | string | Author name or organization |
| `description` | string | Human-readable description |
| `plugin_type` | string | One of: `"agent"`, `"integration"`, `"ui"` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `required_permissions` | array | Permissions needed (see [Security](#security--permissions)) |
| `dependencies` | array | Names of other plugins this plugin requires |
| `homepage` | string | URL to plugin documentation or repository |
| `license` | string | License identifier (e.g., "MIT", "Apache-2.0") |
| `auto_claude_version` | string | Auto Code version requirement (e.g., ">=2.8.0") |

### Version Compatibility

The `auto_claude_version` field supports these formats:

- **Exact**: `"2.8.0"` - Requires exactly this version
- **Comparison**: `">=2.8.0"`, `">2.8.0"`, `"<=3.0.0"`, `"<3.0.0"`
- **Range**: `">=2.8.0,<4.0.0"` - Comma-separated for ranges
- **Caret**: `"^3.0.0"` - Compatible with 3.x.x (not 4.0.0)
- **Tilde**: `"~3.0.0"` - Compatible with 3.0.x (not 3.1.0)

---

## Plugin Lifecycle

All plugins follow this lifecycle:

```
[Discovery] → [Load] → [Enable] → [Active] → [Disable] → [Unload]
```

### Lifecycle Hooks

Implement these methods in your plugin class:

#### 1. `on_load()`

**When**: Plugin is first discovered and loaded (app startup or install)

**Use for**:
- Validate configuration
- Check dependencies
- Initialize resources
- Verify required files exist

**Example**:
```python
def on_load(self):
    # Check if required config is present
    api_key = os.getenv("MY_SERVICE_API_KEY")
    if not api_key:
        raise ValueError("MY_SERVICE_API_KEY not configured")

    logger.info(f"{self.name} v{self.version} loaded successfully")
```

---

#### 2. `on_enable()`

**When**: User enables the plugin (or on startup if already enabled)

**Use for**:
- Register tools/services
- Connect to external services
- Start background tasks
- Register UI extensions

**Example**:
```python
def on_enable(self):
    # Connect to external API
    self.api_client = MyServiceClient(
        api_key=os.getenv("MY_SERVICE_API_KEY")
    )

    # Start background sync task
    self.sync_thread = threading.Thread(target=self._background_sync)
    self.sync_thread.start()

    logger.info(f"{self.name} enabled and connected")
```

---

#### 3. `on_disable()`

**When**: User disables the plugin

**Use for**:
- Unregister tools/services
- Disconnect from services
- Stop background tasks
- Remove UI extensions

**Example**:
```python
def on_disable(self):
    # Stop background tasks
    if hasattr(self, 'sync_thread'):
        self.sync_thread.join(timeout=5)

    # Disconnect from API
    if hasattr(self, 'api_client'):
        self.api_client.close()
        self.api_client = None

    logger.info(f"{self.name} disabled")
```

---

#### 4. `on_unload()`

**When**: Plugin is being removed or app is shutting down

**Use for**:
- Final cleanup
- Save persistent state
- Close file handles
- Release resources

**Example**:
```python
def on_unload(self):
    # Save state for next session
    state_file = Path(__file__).parent / "state.json"
    with open(state_file, 'w') as f:
        json.dump(self.state, f, indent=2)

    logger.info(f"{self.name} unloaded")
```

---

## Creating Agent Plugins

Agent plugins hook into the agent lifecycle to add custom behaviors, monitoring, and tools.

### Minimal Agent Plugin

```python
from plugins.sdk.agent import AgentPlugin, AgentContext
import logging

logger = logging.getLogger(__name__)

class MyAgentPlugin(AgentPlugin):
    def on_load(self):
        # Called when plugin is loaded
        logger.info(f"{self.name} loaded")

    def on_enable(self):
        # Called when plugin is enabled
        self.session_count = 0
        logger.info(f"{self.name} enabled")

    def before_session(self, context: AgentContext):
        # Called before each agent session
        self.session_count += 1
        logger.info(
            f"Starting session #{self.session_count} "
            f"for spec '{context.spec_name}' "
            f"in project '{context.project_name}'"
        )

    def after_session(self, context: AgentContext, success: bool):
        # Called after each agent session
        status = "succeeded" if success else "failed"
        logger.info(f"Session {status} for spec '{context.spec_name}'")

    def on_message(self, context: AgentContext, message):
        # Called when agent receives messages (for monitoring)
        # Keep this lightweight - no heavy processing
        pass

    def on_disable(self):
        # Called when plugin is disabled
        logger.info(f"{self.name} disabled after {self.session_count} sessions")

    def on_unload(self):
        # Called when plugin is unloaded
        logger.info(f"{self.name} unloaded")
```

### AgentContext Properties

The `AgentContext` object provides:

```python
context.project_dir: Path        # Root directory of project
context.spec_dir: Path            # Current spec directory
context.spec_name: str            # Spec directory name
context.project_name: str         # Project directory name
context.session_id: str | None    # Unique session identifier
context.client: ClaudeSDKClient | None  # Claude SDK client (during session)
context.phase: str | None         # Current phase (planning, coding, qa_review, qa_fix)
context.metadata: dict            # Additional metadata
```

### Advanced Example: Session Analytics Plugin

```python
from plugins.sdk.agent import AgentPlugin, AgentContext
from pathlib import Path
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SessionAnalyticsPlugin(AgentPlugin):
    def on_load(self):
        self.analytics_file = Path(__file__).parent / "analytics.json"
        self.load_analytics()

    def on_enable(self):
        logger.info(f"{self.name} enabled")

    def before_session(self, context: AgentContext):
        # Record session start time
        session_data = {
            "session_id": context.session_id,
            "spec_name": context.spec_name,
            "phase": context.phase,
            "start_time": datetime.now().isoformat(),
            "project": context.project_name
        }
        self.current_session = session_data
        logger.info(f"Session started: {context.session_id}")

    def after_session(self, context: AgentContext, success: bool):
        # Record session end and save analytics
        if hasattr(self, 'current_session'):
            self.current_session.update({
                "end_time": datetime.now().isoformat(),
                "success": success,
                "phase": context.phase
            })

            # Calculate duration
            start = datetime.fromisoformat(self.current_session["start_time"])
            end = datetime.fromisoformat(self.current_session["end_time"])
            duration = (end - start).total_seconds()
            self.current_session["duration_seconds"] = duration

            # Save to analytics file
            self.analytics.setdefault("sessions", []).append(self.current_session)
            self.save_analytics()

            logger.info(
                f"Session {context.session_id} completed in {duration:.1f}s "
                f"(success={success})"
            )

    def on_message(self, context: AgentContext, message):
        # Count messages (lightweight)
        if hasattr(self, 'current_session'):
            self.current_session.setdefault("message_count", 0)
            self.current_session["message_count"] += 1

    def on_disable(self):
        self.save_analytics()
        logger.info(f"{self.name} disabled")

    def on_unload(self):
        self.save_analytics()
        logger.info(f"{self.name} unloaded")

    def load_analytics(self):
        if self.analytics_file.exists():
            with open(self.analytics_file) as f:
                self.analytics = json.load(f)
        else:
            self.analytics = {"sessions": []}

    def save_analytics(self):
        with open(self.analytics_file, 'w') as f:
            json.dump(self.analytics, f, indent=2)
```

---

## Creating Integration Plugins

Integration plugins connect Auto Code to external services and create MCP tools for agents.

### Minimal Integration Plugin

```python
from plugins.sdk.integration import IntegrationPlugin, IntegrationContext
import logging

logger = logging.getLogger(__name__)

class MyIntegrationPlugin(IntegrationPlugin):
    def on_load(self):
        # Validate configuration
        api_key = self.get_config_value("MY_SERVICE_API_KEY")
        if not api_key:
            raise ValueError("MY_SERVICE_API_KEY not configured")
        logger.info(f"{self.name} loaded")

    def on_enable(self):
        # Connect to external service
        api_key = self.get_config_value("MY_SERVICE_API_KEY")
        from my_service import Client
        self.client = Client(api_key=api_key)
        logger.info(f"{self.name} connected to service")

    def create_mcp_tools(self, context: IntegrationContext):
        # Return list of tool functions
        def search_docs(query: str) -> str:
            """Search the external documentation."""
            results = self.client.search(query)
            return json.dumps(results, indent=2)

        def create_ticket(title: str, description: str) -> str:
            """Create a ticket in the external system."""
            ticket = self.client.create_ticket(title, description)
            return f"Created ticket: {ticket['url']}"

        return [search_docs, create_ticket]

    def is_available(self) -> bool:
        # Check if service is available
        return (
            self.is_enabled and
            hasattr(self, 'client') and
            self.client.is_connected()
        )

    def on_disable(self):
        # Disconnect from service
        if hasattr(self, 'client'):
            self.client.close()
        logger.info(f"{self.name} disconnected")

    def on_unload(self):
        logger.info(f"{self.name} unloaded")
```

### IntegrationContext Properties

The `IntegrationContext` object provides:

```python
context.project_dir: Path         # Root directory of project
context.spec_dir: Path             # Current spec directory
context.spec_name: str             # Spec directory name
context.project_name: str          # Project directory name
context.config: dict               # Integration configuration
context.state: dict                # Persistent state data
context.metadata: dict             # Additional metadata

# Helper methods
context.get_config(key, default)   # Get config value
context.get_state(key, default)    # Get state value
context.set_state(key, value)      # Set state value
```

### Advanced Example: Issue Tracker Integration

```python
from plugins.sdk.integration import IntegrationPlugin, IntegrationContext
import logging
import json

logger = logging.getLogger(__name__)

class IssueTrackerPlugin(IntegrationPlugin):
    def on_load(self):
        # Validate config
        self.api_url = self.get_config_value("TRACKER_API_URL")
        self.api_key = self.get_config_value("TRACKER_API_KEY")

        if not self.api_url or not self.api_key:
            raise ValueError("TRACKER_API_URL and TRACKER_API_KEY required")

        logger.info(f"{self.name} loaded")

    def on_enable(self):
        # Initialize API client
        from tracker_sdk import TrackerClient
        self.client = TrackerClient(
            api_url=self.api_url,
            api_key=self.api_key
        )
        logger.info(f"{self.name} connected to {self.api_url}")

    def create_mcp_tools(self, context: IntegrationContext):
        # Create MCP tools for agents

        def create_issue(title: str, description: str, labels: str = "") -> str:
            """Create an issue in the tracker.

            Args:
                title: Issue title
                description: Issue description
                labels: Comma-separated labels (optional)
            """
            issue = self.client.create_issue(
                title=title,
                description=description,
                labels=labels.split(",") if labels else []
            )
            return f"Created issue #{issue['number']}: {issue['url']}"

        def list_issues(state: str = "open", limit: int = 10) -> str:
            """List issues from the tracker.

            Args:
                state: Issue state (open, closed, all)
                limit: Maximum number of issues to return
            """
            issues = self.client.list_issues(state=state, limit=limit)
            return json.dumps(
                [{"number": i["number"], "title": i["title"]} for i in issues],
                indent=2
            )

        def update_issue(number: int, state: str) -> str:
            """Update an issue state.

            Args:
                number: Issue number
                state: New state (open, in_progress, closed)
            """
            issue = self.client.update_issue(number, state=state)
            return f"Updated issue #{number} to {state}"

        return [create_issue, list_issues, update_issue]

    def is_available(self) -> bool:
        # Check if service is reachable
        if not self.is_enabled or not hasattr(self, 'client'):
            return False

        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Service unavailable: {e}")
            return False

    def sync_data(self, context: IntegrationContext):
        # Sync implementation plan with tracker
        plan = self.load_implementation_plan(context)
        if not plan:
            return

        # Check if we've created an epic for this spec
        epic_id = context.get_state("epic_id")

        if not epic_id:
            # Create epic for this spec
            epic = self.client.create_epic(
                title=f"Spec: {context.spec_name}",
                description=plan.get("feature", "Auto Code spec implementation")
            )
            epic_id = epic["id"]
            context.set_state("epic_id", epic_id)
            self.save_state(context)
            logger.info(f"Created epic #{epic_id} for {context.spec_name}")

        # Sync subtasks to issues
        for phase in plan.get("phases", []):
            for subtask in phase.get("subtasks", []):
                self._sync_subtask(context, epic_id, subtask)

    def on_build_start(self, context: IntegrationContext):
        # Called when build starts
        logger.info(f"Build started for {context.spec_name}")

        # Create epic if needed
        self.sync_data(context)

    def on_build_complete(self, context: IntegrationContext, success: bool):
        # Called when build completes
        status = "completed" if success else "failed"
        logger.info(f"Build {status} for {context.spec_name}")

        # Update epic status
        epic_id = context.get_state("epic_id")
        if epic_id:
            self.client.update_epic(
                epic_id,
                state="completed" if success else "failed"
            )

    def on_subtask_update(
        self, context: IntegrationContext, subtask_id: str, status: str
    ):
        # Called when subtask status changes
        issue_number = context.get_state(f"subtask_{subtask_id}_issue")
        if issue_number:
            # Map subtask status to issue state
            issue_state = {
                "pending": "open",
                "in_progress": "in_progress",
                "completed": "closed",
                "failed": "open"
            }.get(status, "open")

            self.client.update_issue(issue_number, state=issue_state)
            logger.info(f"Updated issue #{issue_number} to {issue_state}")

    def on_disable(self):
        if hasattr(self, 'client'):
            self.client.close()
        logger.info(f"{self.name} disabled")

    def on_unload(self):
        logger.info(f"{self.name} unloaded")

    def _sync_subtask(self, context, epic_id, subtask):
        # Helper to sync a single subtask
        subtask_id = subtask["id"]
        issue_number = context.get_state(f"subtask_{subtask_id}_issue")

        if not issue_number:
            # Create new issue for this subtask
            issue = self.client.create_issue(
                title=f"[{subtask_id}] {subtask['description']}",
                description=f"Subtask from spec: {context.spec_name}",
                labels=["auto-code", subtask.get("service", "unknown")],
                epic_id=epic_id
            )
            issue_number = issue["number"]
            context.set_state(f"subtask_{subtask_id}_issue", issue_number)
            self.save_state(context)
            logger.info(f"Created issue #{issue_number} for {subtask_id}")
```

---

## Creating UI Plugins

UI plugins extend the Electron desktop app with custom views and components.

### Minimal UI Plugin

```python
from plugins.sdk.ui import UIPlugin
import logging

logger = logging.getLogger(__name__)

class MyUIPlugin(UIPlugin):
    def on_load(self):
        logger.info(f"{self.name} loaded")

    def on_enable(self):
        # Register UI components
        self.register_view(
            id="my-custom-view",
            title="My Custom View",
            icon="star",
            component_path="./views/CustomView.tsx"
        )

        # Add menu item
        self.register_menu_item(
            menu="View",
            label="My Custom View",
            accelerator="Ctrl+Shift+V",
            action=lambda: self.navigate_to("my-custom-view")
        )

        logger.info(f"{self.name} UI registered")

    def on_disable(self):
        # Unregister UI components
        self.unregister_view("my-custom-view")
        logger.info(f"{self.name} UI unregistered")

    def on_unload(self):
        logger.info(f"{self.name} unloaded")
```

### UI Component Example

**React component** (`views/CustomView.tsx`):

```typescript
import React from 'react';

interface CustomViewProps {
  plugin: any;
}

export const CustomView: React.FC<CustomViewProps> = ({ plugin }) => {
  return (
    <div className="custom-view">
      <h1>My Custom View</h1>
      <p>Plugin: {plugin.name}</p>
      <p>Version: {plugin.version}</p>
    </div>
  );
};
```

**IMPORTANT**: See `examples/plugins/ui-extension/` for complete UI plugin examples with React components, hooks, and styling.

---

## Security & Permissions

Plugins must declare required permissions in their `plugin.json` manifest. The plugin system enforces permissions at runtime.

### Available Permissions

| Permission | Description | Risk Level |
|------------|-------------|------------|
| `read_files` | Read files from project directory | Low |
| `write_files` | Write/modify files in project | Medium |
| `network_access` | Make network requests | Medium |
| `execute_commands` | Execute shell commands | High |
| `access_secrets` | Access environment variables/secrets | High |
| `create_mcp_tools` | Register MCP tools with Claude SDK | Low |

### Declaring Permissions

```json
{
  "name": "my-plugin",
  "required_permissions": [
    "read_files",
    "network_access"
  ]
}
```

### Using Permission Validator

```python
from plugins.base import PermissionValidator, PluginPermission

class MyPlugin(AgentPlugin):
    def on_load(self):
        # Create permission validator
        self.permissions = PermissionValidator(self.metadata)

    def some_method(self):
        # Check permission before action
        if self.permissions.check(PluginPermission.READ_FILES):
            # Safe to read files
            with open("config.json") as f:
                config = json.load(f)

        # Require permission (raises exception if denied)
        self.permissions.require(
            PluginPermission.WRITE_FILES,
            "write configuration file"
        )
        with open("config.json", "w") as f:
            json.dump(config, f)
```

### Security Validation

When plugins are installed, the loader performs security validation:

1. **Python syntax check** - Ensures valid Python code
2. **Suspicious imports** - Detects dangerous imports (subprocess, socket, etc.)
3. **Dangerous function calls** - Blocks eval, exec, compile, os.system
4. **Secret scanning** - Detects hardcoded API keys, tokens, credentials

**Installation is blocked** if critical security issues are found.

### Best Practices

✅ **DO**:
- Declare all permissions needed
- Use permission validator before sensitive operations
- Handle permission denied gracefully
- Minimize required permissions

❌ **DON'T**:
- Request permissions you don't need
- Bypass permission checks
- Hardcode secrets in plugin code
- Execute untrusted code

---

## MCP Tool Creation

Integration plugins can create MCP tools that agents can use during sessions.

### Creating Tools

```python
from plugins.sdk.integration import IntegrationPlugin, IntegrationContext

class MyIntegrationPlugin(IntegrationPlugin):
    def create_mcp_tools(self, context: IntegrationContext) -> list:
        # Define tool functions

        def search_database(query: str, limit: int = 10) -> str:
            """Search the database for records.

            Args:
                query: Search query string
                limit: Maximum number of results (default: 10)

            Returns:
                JSON string with search results
            """
            results = self.db.search(query, limit=limit)
            return json.dumps(results, indent=2)

        def create_record(name: str, data: str) -> str:
            """Create a new record in the database.

            Args:
                name: Record name
                data: Record data (JSON string)

            Returns:
                Success message with record ID
            """
            record = self.db.create(name, json.loads(data))
            return f"Created record: {record['id']}"

        # Return list of tool functions
        return [search_database, create_record]
```

### Tool Function Requirements

1. **Clear docstring** - Agents use this to understand the tool
2. **Type hints** - Required for parameter validation
3. **String return type** - MCP tools must return strings (use JSON for complex data)
4. **Error handling** - Handle errors gracefully and return helpful messages

### Good Tool Example

```python
def get_weather(location: str, units: str = "metric") -> str:
    """Get current weather for a location.

    Fetches current weather conditions including temperature, humidity,
    and conditions for the specified location.

    Args:
        location: City name or coordinates (e.g., "London" or "51.5,-0.1")
        units: Temperature units - "metric" (Celsius) or "imperial" (Fahrenheit)

    Returns:
        JSON string with weather data including temperature, humidity,
        conditions, and forecast.

    Examples:
        get_weather("London")
        get_weather("New York", units="imperial")
        get_weather("51.5074,-0.1278")  # London coordinates
    """
    try:
        # Validate units
        if units not in ["metric", "imperial"]:
            return json.dumps({
                "error": "Invalid units. Use 'metric' or 'imperial'."
            })

        # Fetch weather data
        data = self.weather_api.get_current(location, units=units)

        # Return formatted result
        return json.dumps({
            "location": data["name"],
            "temperature": data["temp"],
            "units": "°C" if units == "metric" else "°F",
            "humidity": data["humidity"],
            "conditions": data["weather"]["description"],
            "forecast": data.get("forecast", [])
        }, indent=2)

    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return json.dumps({
            "error": f"Failed to fetch weather: {str(e)}"
        })
```

### Tool Availability

Tools are only available when:
1. Plugin is **enabled**
2. Plugin's `is_available()` returns `True`
3. Required permissions are granted

---

## CLI Usage

The plugin CLI (`apps/backend/plugins/cli.py`) manages plugin installation, configuration, and lifecycle.

### List Plugins

```bash
# List all plugins
python plugins/cli.py list

# List only agent plugins
python plugins/cli.py list --type agent

# List only enabled plugins
python plugins/cli.py list --enabled-only

# List integration plugins
python plugins/cli.py list --type integration
```

### Install Plugins

```bash
# Install from local directory
python plugins/cli.py install --path /path/to/plugin

# Install from remote git repository
python plugins/cli.py install --url https://github.com/user/plugin.git

# Install with security validation bypass (not recommended)
python plugins/cli.py install --path /path/to/plugin --force

# Dry run (validate without installing)
python plugins/cli.py install --url https://github.com/user/plugin.git --dry-run
```

### Enable/Disable Plugins

```bash
# Enable a plugin
python plugins/cli.py enable my-plugin

# Disable a plugin
python plugins/cli.py disable my-plugin
```

### Plugin Info

```bash
# Show detailed plugin information
python plugins/cli.py info my-plugin
```

### Uninstall Plugins

```bash
# Uninstall a plugin
python plugins/cli.py uninstall my-plugin
```

---

## Best Practices

### Plugin Structure

```
my-plugin/
├── plugin.json           # Plugin manifest (required)
├── agent.py              # Agent plugin implementation
├── README.md             # Documentation
├── requirements.txt      # Python dependencies (optional)
├── .env.example          # Example configuration (optional)
└── tests/                # Plugin tests (recommended)
    ├── test_plugin.py
    └── fixtures/
```

### Configuration Management

**Use environment variables**:

```python
# In plugin code
api_key = self.get_config_value("MY_PLUGIN_API_KEY")
webhook_url = self.get_config_value("MY_PLUGIN_WEBHOOK_URL")
```

**Provide `.env.example`**:

```bash
# .env.example
MY_PLUGIN_API_KEY=your_api_key_here
MY_PLUGIN_WEBHOOK_URL=https://hooks.example.com/webhook
MY_PLUGIN_ENABLED=true
```

**Document in README**:

```markdown
## Configuration

This plugin requires the following environment variables:

- `MY_PLUGIN_API_KEY` - API key for MyService (required)
- `MY_PLUGIN_WEBHOOK_URL` - Webhook URL for notifications (optional)
- `MY_PLUGIN_ENABLED` - Enable/disable plugin (default: true)
```

### Error Handling

```python
def before_session(self, context: AgentContext):
    try:
        # Plugin logic
        self.prepare_session(context)
    except Exception as e:
        # Log error but don't crash the session
        logger.error(f"Failed to prepare session: {e}")
        # Optionally re-raise for critical errors
        # raise
```

### Logging

```python
import logging

# Use plugin name as logger name
logger = logging.getLogger(__name__)

class MyPlugin(AgentPlugin):
    def on_load(self):
        # Use appropriate log levels
        logger.debug("Loading configuration")
        logger.info(f"{self.name} loaded successfully")
        logger.warning("API key not found, using defaults")
        logger.error("Failed to connect to service")
```

### State Management

```python
from pathlib import Path
import json

class MyPlugin(AgentPlugin):
    def on_load(self):
        # Load persisted state
        self.state_file = Path(__file__).parent / "state.json"
        self.load_state()

    def load_state(self):
        if self.state_file.exists():
            with open(self.state_file) as f:
                self.state = json.load(f)
        else:
            self.state = {"session_count": 0}

    def save_state(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def on_unload(self):
        # Save state on unload
        self.save_state()
```

### Testing

Create tests for your plugin:

```python
# tests/test_plugin.py
import pytest
from plugins.loader import PluginLoader
from pathlib import Path

@pytest.fixture
def plugin():
    loader = PluginLoader()
    plugin_path = Path(__file__).parent.parent
    return loader.load_plugin(str(plugin_path))

def test_plugin_loads(plugin):
    assert plugin is not None
    assert plugin.name == "my-plugin"

def test_plugin_enable_disable(plugin):
    plugin.on_load()
    plugin.on_enable()
    assert plugin.is_enabled

    plugin.on_disable()
    assert not plugin.is_enabled
```

### Documentation

**Comprehensive README**:

- Overview and features
- Installation instructions
- Configuration requirements
- Usage examples
- Troubleshooting guide
- License information

**Example**: See `examples/plugins/hello-world-agent/README.md`

---

## Distribution

### Publishing to GitHub

1. **Create repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/user/my-plugin.git
   git push -u origin main
   ```

2. **Tag release**:
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

3. **Users install with**:
   ```bash
   python plugins/cli.py install --url https://github.com/user/my-plugin.git
   ```

### Plugin Registry (Future)

A centralized plugin registry is planned for Auto Code. This will enable:

- Plugin discovery and search
- Version management
- Dependency resolution
- Security ratings
- User reviews

**Stay tuned for updates!**

---

## Troubleshooting

### Plugin Not Appearing in List

**Check**:
- Plugin directory is in correct location (`~/.auto-claude/plugins/user/`)
- `plugin.json` exists and is valid JSON
- `plugin_type` matches plugin class (`agent`, `integration`, or `ui`)

**Debug**:
```bash
# Check for syntax errors
python -c "import json; json.load(open('plugin.json'))"

# Check loader output
python -c "from plugins.loader import PluginLoader; loader = PluginLoader(); loader.discover_plugins()"
```

---

### Plugin Fails to Load

**Check**:
- All required fields are in `plugin.json`
- Plugin file name matches type (`agent.py`, `integration.py`, or `ui.py`)
- Plugin class extends correct base class
- No Python syntax errors
- All dependencies are installed

**Debug**:
```bash
# Test plugin import
python -c "from plugins.loader import PluginLoader; loader = PluginLoader(); plugin = loader.load_plugin('/path/to/plugin')"

# Check logs
tail -f ~/.auto-claude/logs/plugin.log
```

---

### Plugin Hooks Not Called

**Check**:
- Plugin is **enabled**, not just installed
- Hooks are named correctly (`before_session`, not `on_before_session`)
- Plugin type matches hook (agent hooks only work on AgentPlugin)
- No exceptions in hook implementation

**Debug**:
```python
# Add logging to hooks
def before_session(self, context: AgentContext):
    logger.info(f"HOOK CALLED: before_session for {context.spec_name}")
    # Your code here
```

---

### MCP Tools Not Available

**Check**:
- Plugin is enabled
- `is_available()` returns `True`
- `create_mcp_tools()` returns non-empty list
- Tool functions have docstrings and type hints
- Required permissions are granted (`create_mcp_tools`)

**Debug**:
```python
# Test tool creation
from plugins.sdk.integration import IntegrationContext
from pathlib import Path

context = IntegrationContext(
    project_dir=Path.cwd(),
    spec_dir=Path.cwd() / ".auto-claude/specs/001"
)

tools = plugin.create_mcp_tools(context)
print(f"Tools created: {len(tools)}")
for tool in tools:
    print(f"- {tool.__name__}: {tool.__doc__[:50]}...")
```

---

### Permission Denied Errors

**Check**:
- Required permissions are declared in `plugin.json`
- Permission names match exactly (use `PluginPermission` enum values)
- User has approved the permissions

**Fix**:
Add missing permissions to `plugin.json`:
```json
{
  "required_permissions": [
    "read_files",
    "network_access"
  ]
}
```

Then reinstall the plugin:
```bash
python plugins/cli.py uninstall my-plugin
python plugins/cli.py install --path /path/to/my-plugin
python plugins/cli.py enable my-plugin
```

---

### Version Compatibility Errors

**Check**:
- `auto_claude_version` in `plugin.json` is correct
- Version format is valid (see [Version Compatibility](#version-compatibility))
- Auto Code version meets requirement

**Debug**:
```bash
# Check Auto Code version
python -c "import json; print(json.load(open('package.json'))['version'])"

# Check plugin requirement
python -c "import json; print(json.load(open('plugin.json'))['auto_claude_version'])"
```

**Fix**:
Update `auto_claude_version` in `plugin.json`:
```json
{
  "auto_claude_version": ">=2.8.0"
}
```

---

## Additional Resources

- **Example Plugins**: `examples/plugins/`
  - `hello-world-agent/` - Minimal agent plugin
  - `custom-integration/` - Integration plugin with MCP tools
  - `custom-llm-provider/` - LLM integration example
  - `team-webhook/` - Webhook notifications plugin
  - `file-templates/` - File template system plugin
  - `ui-extension/` - UI plugin example

- **Plugin SDK Documentation**:
  - `apps/backend/plugins/sdk/agent.py` - Agent plugin SDK
  - `apps/backend/plugins/sdk/integration.py` - Integration plugin SDK
  - `apps/backend/plugins/sdk/ui.py` - UI plugin SDK
  - `apps/backend/plugins/base.py` - Base classes and permissions

- **Core Implementation**:
  - `apps/backend/plugins/registry.py` - Plugin registry
  - `apps/backend/plugins/loader.py` - Plugin loader with security
  - `apps/backend/plugins/cli.py` - CLI interface

---

## Questions or Issues?

- **GitHub Issues**: Report bugs or request features
- **Discussions**: Ask questions and share plugins
- **Contributing**: PRs welcome for plugin system improvements

---

**Happy plugin development! 🚀**
