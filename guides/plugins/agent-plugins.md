# Agent Plugin Development Guide

Agent plugins extend Auto Claude's agent capabilities by hooking into the agent lifecycle and providing custom behaviors, tools, or monitoring. This guide covers everything you need to build powerful agent plugins.

## Table of Contents

- [Overview](#overview)
- [AgentPlugin API Reference](#agentplugin-api-reference)
- [Lifecycle Hooks](#lifecycle-hooks)
- [Agent Session Hooks](#agent-session-hooks)
- [AgentContext Access](#agentcontext-access)
- [Creating Custom Tools](#creating-custom-tools)
- [State Management](#state-management)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Complete Example](#complete-example)

## Overview

Agent plugins are Python classes that extend the `AgentPlugin` base class from the Auto Claude plugin SDK. They can:

- **Monitor agent sessions** - Track when agents start, complete, or fail
- **Access agent context** - Read project info, spec details, session metadata
- **Provide custom tools** - Add MCP tools for agents to use during sessions
- **Manage resources** - Set up/tear down resources around agent sessions
- **Analytics and logging** - Track agent behavior, performance, or usage

### When to Use Agent Plugins

Use agent plugins when you want to:
- Add monitoring or analytics to agent sessions
- Track agent performance metrics
- Log agent behavior for debugging
- Inject custom tools or behaviors into agent sessions
- Implement custom pre/post-processing logic
- Integrate with external monitoring services

### Quick Start

```bash
# Copy the example plugin
cp -r examples/plugins/hello-world-agent my-agent-plugin

# Update plugin.json
# Edit agent.py to implement your logic
# Install and test
```

## AgentPlugin API Reference

### Base Class

```python
from apps.backend.plugins.sdk.agent import AgentPlugin, AgentContext

class MyAgentPlugin(AgentPlugin):
    """Your custom agent plugin."""

    def __init__(self, metadata):
        super().__init__(metadata)
        # Initialize plugin state
```

### Required Methods

All plugins must implement these lifecycle methods from `PluginBase`:

| Method | Purpose | Required |
|--------|---------|----------|
| `on_load()` | Plugin initialization | Yes |
| `on_enable()` | Called when user enables plugin | Yes |
| `on_disable()` | Called when user disables plugin | Yes |
| `on_unload()` | Cleanup before unload | Yes |

### Agent-Specific Methods

Agent plugins can optionally implement these session hooks:

| Method | Purpose | When Called |
|--------|---------|-------------|
| `before_session(context)` | Pre-session setup | Before agent starts |
| `after_session(context, success)` | Post-session cleanup | After agent completes |
| `on_message(context, message)` | Monitor messages | During agent session |

## Lifecycle Hooks

### on_load()

Called when the plugin is first discovered and loaded by Auto Claude.

**Use this to:**
- Validate configuration
- Check dependencies
- Initialize resources
- Log plugin information

**Example:**

```python
def on_load(self) -> None:
    """Plugin loaded - validate configuration."""
    logger.info(f"{self.name}: Plugin loaded v{self.version}")

    # Validate required configuration
    if not self.get_config_value("API_KEY"):
        logger.warning(f"{self.name}: No API_KEY configured")

    # Check dependencies
    try:
        import requests
    except ImportError:
        raise RuntimeError("requests library required")
```

### on_enable()

Called when the user enables the plugin (either at startup or manually).

**Use this to:**
- Connect to external services
- Register tools/services
- Start background tasks
- Initialize session state

**Example:**

```python
def on_enable(self) -> None:
    """Plugin enabled - connect to services."""
    logger.info(f"{self.name}: Plugin enabled")

    # Connect to external service
    api_key = self.get_config_value("API_KEY")
    self.client = MyAPIClient(api_key)

    # Initialize session counter
    self.session_count = 0

    # Start background monitoring task
    self.start_monitoring()
```

### on_disable()

Called when the user disables the plugin.

**Use this to:**
- Disconnect from services
- Unregister tools/services
- Stop background tasks
- Save state

**Example:**

```python
def on_disable(self) -> None:
    """Plugin disabled - clean up resources."""
    logger.info(f"{self.name}: Plugin disabled")

    # Stop background tasks
    self.stop_monitoring()

    # Disconnect from service
    if self.client:
        self.client.disconnect()
        self.client = None

    # Save session stats
    logger.info(f"{self.name}: Handled {self.session_count} sessions")
```

### on_unload()

Called when the plugin is being unloaded (app shutdown or plugin update).

**Use this to:**
- Final cleanup
- Save persistent state
- Close file handles
- Log summary statistics

**Example:**

```python
def on_unload(self) -> None:
    """Plugin unloading - final cleanup."""
    logger.info(f"{self.name}: Plugin unloaded")

    # Save persistent state to file
    state_file = Path(__file__).parent / "state.json"
    with open(state_file, 'w') as f:
        json.dump({
            'total_sessions': self.session_count,
            'last_unload': datetime.now().isoformat()
        }, f)
```

## Agent Session Hooks

### before_session(context)

Called before an agent session starts. This is your opportunity to:
- Set up session-specific resources
- Validate context
- Log session start
- Initialize monitoring

**Signature:**

```python
def before_session(self, context: AgentContext) -> None:
    """Called before agent session starts."""
    pass
```

**Parameters:**
- `context`: AgentContext with project_dir, spec_dir, session_id, phase, etc.

**Raises:**
- If this method raises an exception, the agent session will be aborted

**Example:**

```python
def before_session(self, context: AgentContext) -> None:
    """Set up session monitoring."""
    self.session_count += 1

    logger.info(
        f"{self.name}: Starting session #{self.session_count} "
        f"for spec '{context.spec_name}' in project '{context.project_name}'"
    )

    # Log session details
    if context.phase:
        logger.debug(f"{self.name}: Session phase: {context.phase}")

    if context.session_id:
        logger.debug(f"{self.name}: Session ID: {context.session_id}")

    # Initialize session-specific state
    self.current_session = {
        'id': context.session_id,
        'start_time': datetime.now(),
        'spec': context.spec_name,
        'phase': context.phase
    }

    # Validate context
    if not context.project_dir.exists():
        raise ValueError(f"Project directory not found: {context.project_dir}")
```

### after_session(context, success)

Called after an agent session completes. Use this for:
- Clean up session resources
- Log results
- Save metrics/analytics
- Send notifications

**Signature:**

```python
def after_session(self, context: AgentContext, success: bool) -> None:
    """Called after agent session completes."""
    pass
```

**Parameters:**
- `context`: AgentContext (same as before_session)
- `success`: True if session completed successfully, False if error occurred

**Example:**

```python
def after_session(self, context: AgentContext, success: bool) -> None:
    """Clean up and log session results."""
    status = "succeeded" if success else "failed"
    logger.info(
        f"{self.name}: Session {status} for spec '{context.spec_name}'"
    )

    # Calculate session duration
    if hasattr(self, 'current_session'):
        start_time = self.current_session['start_time']
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"{self.name}: Session duration: {duration:.2f}s")

    # Log failures with more detail
    if not success:
        logger.warning(
            f"{self.name}: Session failed - you may want to investigate"
        )
        # Send notification (if configured)
        self.send_notification(context, success)

    # Save metrics
    self.save_session_metrics(context, success, duration)
```

### on_message(context, message)

Called when the agent receives a message during a session. This is a **monitoring hook only** - do not modify messages or block.

**Use this for:**
- Analytics and metrics
- Debug logging
- Real-time monitoring
- Message filtering/analysis

**Signature:**

```python
def on_message(self, context: AgentContext, message: Any) -> None:
    """Called when agent receives a message."""
    pass
```

**Parameters:**
- `context`: AgentContext for current session
- `message`: The message object from Claude SDK (AssistantMessage, etc.)

**Important:** This method should be lightweight and fast. Heavy processing should be done asynchronously.

**Example:**

```python
def on_message(self, context: AgentContext, message: Any) -> None:
    """Monitor agent messages."""
    # Log message type for debugging
    message_type = type(message).__name__
    logger.debug(f"{self.name}: Received message of type {message_type}")

    # Track message counts
    if not hasattr(self, 'message_counts'):
        self.message_counts = {}
    self.message_counts[message_type] = self.message_counts.get(message_type, 0) + 1

    # Analyze message content (lightweight only)
    if hasattr(message, 'text'):
        word_count = len(message.text.split())
        logger.debug(f"{self.name}: Message word count: {word_count}")

    # Queue for async processing if needed
    if self.needs_deep_analysis(message):
        self.analysis_queue.put((context, message))
```

## AgentContext Access

The `AgentContext` dataclass provides rich information about the current agent session.

### Available Properties

```python
@dataclass
class AgentContext:
    project_dir: Path          # Root directory of the project
    spec_dir: Path             # Directory containing the current spec
    session_id: Optional[str]  # Unique identifier for the session
    client: Optional[ClaudeSDKClient]  # Claude SDK client (during session)
    phase: Optional[str]       # Current phase (planning, coding, qa_review, etc.)
    metadata: dict[str, Any]   # Additional metadata
```

### Computed Properties

```python
context.spec_name    # Get spec directory name (e.g., "001-feature")
context.project_name # Get project directory name
```

### Usage Examples

**Accessing basic context:**

```python
def before_session(self, context: AgentContext) -> None:
    """Access context information."""
    # Basic properties
    logger.info(f"Project: {context.project_name}")
    logger.info(f"Spec: {context.spec_name}")
    logger.info(f"Session ID: {context.session_id}")

    # File paths
    logger.info(f"Project path: {context.project_dir}")
    logger.info(f"Spec path: {context.spec_dir}")

    # Phase information
    if context.phase:
        logger.info(f"Phase: {context.phase}")
        if context.phase == "qa_review":
            logger.info("This is a QA review session")
```

**Reading spec files:**

```python
def before_session(self, context: AgentContext) -> None:
    """Read spec information."""
    # Read spec.md
    spec_file = context.spec_dir / "spec.md"
    if spec_file.exists():
        with open(spec_file) as f:
            spec_content = f.read()
        logger.info(f"Spec has {len(spec_content)} characters")

    # Read implementation_plan.json
    plan_file = context.spec_dir / "implementation_plan.json"
    if plan_file.exists():
        with open(plan_file) as f:
            plan = json.load(f)
        total_subtasks = sum(
            len(phase['subtasks'])
            for phase in plan.get('phases', [])
        )
        logger.info(f"Plan has {total_subtasks} subtasks")
```

**Using metadata:**

```python
def before_session(self, context: AgentContext) -> None:
    """Access custom metadata."""
    # Check for custom metadata
    if 'priority' in context.metadata:
        priority = context.metadata['priority']
        logger.info(f"Session priority: {priority}")

    # Add custom metadata (if you control the caller)
    context.metadata['plugin_start_time'] = datetime.now().isoformat()
```

## Creating Custom Tools

Agent plugins can provide custom MCP tools that agents can use during sessions. Tools are created in the `on_enable()` hook.

### Tool Creation Pattern

```python
from apps.backend.plugins.sdk.agent import AgentPlugin, AgentContext

class MyToolPlugin(AgentPlugin):
    """Plugin that provides custom tools."""

    def on_enable(self) -> None:
        """Create and register custom tools."""
        # Tools will be registered when the plugin creates an MCP server
        # Note: Full MCP integration happens through IntegrationPlugin
        # AgentPlugins typically use tools indirectly through monitoring
        pass
```

### Important Note

**Agent plugins primarily monitor and hook into sessions**, while **Integration plugins provide MCP tools** to agents. If you want to create tools for agents to use:

1. **Use IntegrationPlugin instead** - See [integration-plugins.md](./integration-plugins.md)
2. **Or combine both** - Create an agent plugin for monitoring and an integration plugin for tools

### Monitoring Tool Usage

Agent plugins can monitor tool usage through the `on_message()` hook:

```python
def on_message(self, context: AgentContext, message: Any) -> None:
    """Monitor tool usage."""
    # Check if message contains tool results
    if hasattr(message, 'tool_name'):
        tool_name = message.tool_name
        logger.info(f"{self.name}: Agent used tool: {tool_name}")

        # Track tool usage statistics
        if not hasattr(self, 'tool_usage'):
            self.tool_usage = {}
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
```

## State Management

Agent plugins can maintain state across sessions using instance variables and file persistence.

### Session State (Temporary)

Use instance variables for state that only needs to exist during the plugin's lifetime:

```python
class MyAgentPlugin(AgentPlugin):
    def __init__(self, metadata):
        super().__init__(metadata)
        self.session_count = 0
        self.total_duration = 0.0

    def before_session(self, context: AgentContext) -> None:
        self.session_count += 1
        self.current_start = datetime.now()

    def after_session(self, context: AgentContext, success: bool) -> None:
        duration = (datetime.now() - self.current_start).total_seconds()
        self.total_duration += duration
```

### Persistent State (Saved)

Use file storage for state that should persist across plugin reloads:

```python
from pathlib import Path
import json

class MyAgentPlugin(AgentPlugin):
    def __init__(self, metadata):
        super().__init__(metadata)
        self.state_file = Path(__file__).parent / "state.json"
        self.state = self.load_state()

    def load_state(self) -> dict:
        """Load persistent state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load state: {e}")
        return {'total_sessions': 0, 'first_load': datetime.now().isoformat()}

    def save_state(self) -> None:
        """Save persistent state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save state: {e}")

    def on_enable(self) -> None:
        self.state = self.load_state()

    def after_session(self, context: AgentContext, success: bool) -> None:
        self.state['total_sessions'] += 1
        self.state['last_session'] = datetime.now().isoformat()
        self.save_state()

    def on_unload(self) -> None:
        self.save_state()
```

### Per-Spec State

Store state specific to each spec in the spec directory:

```python
def before_session(self, context: AgentContext) -> None:
    """Load per-spec state."""
    state_file = context.spec_dir / f"{self.name}-state.json"

    if state_file.exists():
        with open(state_file, 'r') as f:
            spec_state = json.load(f)
        logger.info(f"Previous sessions for this spec: {spec_state.get('count', 0)}")
    else:
        spec_state = {'count': 0}

    spec_state['count'] += 1
    spec_state['last_session'] = datetime.now().isoformat()

    with open(state_file, 'w') as f:
        json.dump(spec_state, f, indent=2)
```

## Error Handling

Proper error handling ensures your plugin doesn't crash agent sessions.

### Handle Exceptions Gracefully

```python
def before_session(self, context: AgentContext) -> None:
    """Safe session initialization."""
    try:
        # Attempt to connect to external service
        self.connect_monitoring_service()
    except ConnectionError as e:
        # Log but don't fail the session
        logger.warning(f"{self.name}: Could not connect to monitoring: {e}")
        # Gracefully degrade - session continues without monitoring
    except Exception as e:
        # Unexpected error - log with full traceback
        logger.exception(f"{self.name}: Unexpected error in before_session: {e}")
        # Optionally re-raise to abort session if critical
        # raise
```

### Validate Configuration

```python
def on_load(self) -> None:
    """Validate plugin configuration."""
    # Check required configuration
    api_key = self.get_config_value("API_KEY")
    if not api_key:
        logger.warning(
            f"{self.name}: No API_KEY configured. "
            f"Plugin will run with limited functionality."
        )

    # Validate API key format
    if api_key and not api_key.startswith("sk_"):
        raise ValueError(
            f"{self.name}: Invalid API_KEY format. "
            f"Expected format: sk_xxxxx"
        )
```

### Protect Against Missing Context

```python
def after_session(self, context: AgentContext, success: bool) -> None:
    """Handle potentially missing context."""
    try:
        spec_name = context.spec_name if context else "unknown"
        logger.info(f"{self.name}: Session completed for {spec_name}")
    except AttributeError:
        logger.warning(f"{self.name}: Context missing expected attributes")
```

### Timeout Long Operations

```python
import threading
import time

def before_session(self, context: AgentContext) -> None:
    """Connect with timeout."""
    def connect_with_timeout():
        self.client = ExternalService()
        self.client.connect()

    # Run connection in thread with timeout
    thread = threading.Thread(target=connect_with_timeout)
    thread.daemon = True
    thread.start()
    thread.join(timeout=5.0)  # 5 second timeout

    if thread.is_alive():
        logger.warning(f"{self.name}: Connection timed out")
        # Session continues without connection
```

## Best Practices

### 1. Keep Hooks Lightweight

Session hooks should execute quickly to avoid delaying agent sessions:

```python
# ❌ BAD - Slow operation blocks session start
def before_session(self, context: AgentContext) -> None:
    # This blocks the agent from starting!
    data = fetch_large_dataset_from_api()  # 10 seconds
    process_data(data)  # 5 seconds

# ✅ GOOD - Quick setup, defer heavy work
def before_session(self, context: AgentContext) -> None:
    # Log and move on
    logger.info(f"Session starting: {context.spec_name}")

    # Queue heavy work for background thread
    self.work_queue.put(('fetch_data', context.spec_name))
```

### 2. Use Appropriate Log Levels

```python
# INFO - Important lifecycle events
logger.info(f"{self.name}: Plugin enabled")
logger.info(f"{self.name}: Session started for spec '{context.spec_name}'")

# DEBUG - Detailed information for troubleshooting
logger.debug(f"{self.name}: Session ID: {context.session_id}")
logger.debug(f"{self.name}: Phase: {context.phase}")

# WARNING - Non-fatal issues
logger.warning(f"{self.name}: Could not connect to monitoring service")

# ERROR - Fatal issues
logger.error(f"{self.name}: Failed to load state: {e}")

# EXCEPTION - Include full traceback
logger.exception(f"{self.name}: Unexpected error")
```

### 3. Fail Gracefully

Don't crash the agent session unless absolutely necessary:

```python
def before_session(self, context: AgentContext) -> None:
    """Graceful degradation example."""
    try:
        # Try to enable optional feature
        self.enable_advanced_monitoring()
    except Exception as e:
        # Log warning but continue
        logger.warning(
            f"{self.name}: Advanced monitoring unavailable: {e}. "
            f"Continuing with basic monitoring."
        )
        # Session continues with reduced functionality
```

### 4. Document Required Permissions

Clearly document what permissions your plugin needs in `plugin.json` and README:

```json
{
  "required_permissions": [
    "network_access"
  ]
}
```

In your README:
```markdown
## Required Permissions

- **network_access** - Required to send metrics to external monitoring service
```

### 5. Provide Configuration Examples

Include `.env.example` or document configuration clearly:

```python
def on_load(self) -> None:
    """Document configuration requirements."""
    api_key = self.get_config_value("MY_PLUGIN_API_KEY")
    if not api_key:
        logger.warning(
            f"{self.name}: No API_KEY configured. "
            f"Set MY_PLUGIN_API_KEY environment variable. "
            f"Example: MY_PLUGIN_API_KEY=sk_xxxxx"
        )
```

### 6. Test Without External Dependencies

Make external services optional so plugin can be tested standalone:

```python
def on_enable(self) -> None:
    """Connect to service if available."""
    api_key = self.get_config_value("API_KEY")

    if api_key:
        try:
            self.client = ExternalService(api_key)
            logger.info(f"{self.name}: Connected to external service")
        except Exception as e:
            logger.warning(f"{self.name}: Service unavailable: {e}")
            self.client = None
    else:
        logger.info(f"{self.name}: Running in local mode (no API key)")
        self.client = None
```

### 7. Clean Up Resources

Always clean up in `on_disable()` and `on_unload()`:

```python
def on_disable(self) -> None:
    """Clean up all resources."""
    # Close connections
    if self.client:
        self.client.disconnect()
        self.client = None

    # Stop threads
    if hasattr(self, 'worker_thread'):
        self.worker_thread.stop()

    # Save state
    self.save_state()
```

## Complete Example

Here's a complete agent plugin that monitors session duration and sends notifications:

```python
"""
Session Duration Monitor Plugin
=================================

Monitors agent session duration and sends notifications when sessions
take longer than expected.
"""

import logging
from datetime import datetime
from pathlib import Path
import json

from apps.backend.plugins.sdk.agent import AgentPlugin, AgentContext

logger = logging.getLogger(__name__)


class SessionMonitorPlugin(AgentPlugin):
    """
    Agent plugin that monitors session duration and alerts on long sessions.

    Configuration (environment variables):
    - SESSION_MONITOR_THRESHOLD: Duration threshold in seconds (default: 300)
    - SESSION_MONITOR_NOTIFY: Enable notifications (default: false)
    """

    def __init__(self, metadata):
        """Initialize the session monitor plugin."""
        super().__init__(metadata)
        self.state_file = Path(__file__).parent / "state.json"
        self.sessions = {}
        self.state = {}

    def on_load(self) -> None:
        """Plugin loaded - load persistent state."""
        logger.info(f"{self.name}: Plugin loaded v{self.version}")

        # Load state from file
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
                logger.debug(
                    f"{self.name}: Loaded state with "
                    f"{self.state.get('total_sessions', 0)} total sessions"
                )
            except Exception as e:
                logger.warning(f"{self.name}: Could not load state: {e}")
                self.state = {}

    def on_enable(self) -> None:
        """Plugin enabled - initialize monitoring."""
        logger.info(f"{self.name}: Plugin enabled")

        # Load configuration
        self.threshold = int(
            self.get_config_value("SESSION_MONITOR_THRESHOLD", "300")
        )
        self.notify_enabled = (
            self.get_config_value("SESSION_MONITOR_NOTIFY", "false").lower() == "true"
        )

        logger.info(
            f"{self.name}: Monitoring threshold: {self.threshold}s, "
            f"notifications: {self.notify_enabled}"
        )

    def on_disable(self) -> None:
        """Plugin disabled - clean up."""
        logger.info(f"{self.name}: Plugin disabled")
        self.save_state()

    def on_unload(self) -> None:
        """Plugin unloading - save final state."""
        self.save_state()
        logger.info(
            f"{self.name}: Plugin unloaded after monitoring "
            f"{self.state.get('total_sessions', 0)} sessions"
        )

    def before_session(self, context: AgentContext) -> None:
        """Record session start time."""
        session_id = context.session_id or 'unknown'

        self.sessions[session_id] = {
            'start_time': datetime.now(),
            'spec': context.spec_name,
            'phase': context.phase,
            'project': context.project_name
        }

        logger.info(
            f"{self.name}: Monitoring session for spec '{context.spec_name}' "
            f"(phase: {context.phase})"
        )

    def after_session(self, context: AgentContext, success: bool) -> None:
        """Calculate duration and check threshold."""
        session_id = context.session_id or 'unknown'

        if session_id not in self.sessions:
            logger.warning(f"{self.name}: Session {session_id} not tracked")
            return

        # Calculate duration
        session_info = self.sessions[session_id]
        start_time = session_info['start_time']
        duration = (datetime.now() - start_time).total_seconds()

        status = "succeeded" if success else "failed"
        logger.info(
            f"{self.name}: Session {status} for '{context.spec_name}' "
            f"in {duration:.2f}s"
        )

        # Check threshold
        if duration > self.threshold:
            logger.warning(
                f"{self.name}: Session exceeded threshold "
                f"({duration:.2f}s > {self.threshold}s)"
            )
            if self.notify_enabled:
                self.send_notification(context, duration)

        # Update statistics
        self.update_stats(context, duration, success)

        # Clean up
        del self.sessions[session_id]

    def on_message(self, context: AgentContext, message: any) -> None:
        """Monitor message activity (lightweight)."""
        # Just count messages
        session_id = context.session_id or 'unknown'
        if session_id in self.sessions:
            message_count = self.sessions[session_id].get('messages', 0) + 1
            self.sessions[session_id]['messages'] = message_count

    def update_stats(self, context: AgentContext, duration: float, success: bool) -> None:
        """Update persistent statistics."""
        # Increment counters
        self.state['total_sessions'] = self.state.get('total_sessions', 0) + 1
        self.state['total_duration'] = self.state.get('total_duration', 0.0) + duration

        if success:
            self.state['successful_sessions'] = self.state.get('successful_sessions', 0) + 1

        # Track by phase
        if context.phase:
            phase_key = f"phase_{context.phase}"
            self.state[phase_key] = self.state.get(phase_key, 0) + 1

        # Update last session
        self.state['last_session'] = {
            'spec': context.spec_name,
            'duration': duration,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }

        self.save_state()

    def send_notification(self, context: AgentContext, duration: float) -> None:
        """Send notification about long session."""
        # In real implementation, this would use email, Slack, etc.
        logger.warning(
            f"{self.name}: NOTIFICATION - Long session detected:\n"
            f"  Spec: {context.spec_name}\n"
            f"  Duration: {duration:.2f}s\n"
            f"  Threshold: {self.threshold}s"
        )

    def save_state(self) -> None:
        """Save persistent state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"{self.name}: State saved")
        except Exception as e:
            logger.error(f"{self.name}: Failed to save state: {e}")
```

**Corresponding plugin.json:**

```json
{
  "name": "session-monitor",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Monitors agent session duration and alerts on long sessions",
  "plugin_type": "agent",
  "required_permissions": [],
  "dependencies": [],
  "homepage": "https://github.com/yourname/session-monitor",
  "license": "MIT"
}
```

## Next Steps

- **See it in action** - Install and test the [hello-world-agent](../../../examples/plugins/hello-world-agent/) example
- **Create tools** - Learn about [Integration Plugins](./integration-plugins.md) for MCP tool creation
- **Build UI** - Read the [UI Plugins Guide](./ui-plugins.md) to add frontend components
- **Review examples** - Explore all example plugins in `examples/plugins/`

## Learn More

- [Plugin Getting Started Guide](./getting-started.md)
- [Agent Plugin SDK Documentation](../../../apps/backend/plugins/sdk/agent.py)
- [Hello World Agent Example](../../../examples/plugins/hello-world-agent/README.md)
- [Plugin Security Model](./getting-started.md#security-and-sandboxing)
