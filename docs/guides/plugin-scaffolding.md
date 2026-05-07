# Plugin Scaffolding Guide

Quick-start templates and boilerplate code for creating Auto Code plugins.

## Table of Contents

- [Overview](#overview)
- [Scaffolding Scripts](#scaffolding-scripts)
- [Agent Plugin Templates](#agent-plugin-templates)
- [Integration Plugin Templates](#integration-plugin-templates)
- [UI Plugin Templates](#ui-plugin-templates)
- [Testing Templates](#testing-templates)
- [Common Patterns](#common-patterns)
- [Configuration Templates](#configuration-templates)
- [Directory Structures](#directory-structures)

---

## Overview

This guide provides ready-to-use templates for scaffolding new Auto Code plugins. Use these templates as starting points for your plugin development.

### Quick Scaffolding Workflow

1. **Choose plugin type** - Agent, Integration, or UI
2. **Copy template** - Use scaffolding script or copy manually
3. **Customize manifest** - Update `plugin.json` with your details
4. **Implement hooks** - Fill in lifecycle methods
5. **Add tests** - Use testing templates
6. **Install and test** - Verify functionality

---

## Scaffolding Scripts

### Automated Plugin Generator

Create a new plugin with a single command:

```bash
cd apps/backend
python plugins/scaffold.py --name my-plugin --type agent --author "Your Name"
```

**Options:**
- `--name` - Plugin name (required)
- `--type` - Plugin type: `agent`, `integration`, or `ui` (required)
- `--author` - Author name (optional)
- `--description` - Plugin description (optional)
- `--output` - Output directory (default: `~/.auto-claude/plugins/user/`)
- `--with-tests` - Include test templates (optional)
- `--with-mcp-tools` - Include MCP tool templates (integration plugins only)

**Example:**

```bash
# Create agent plugin with tests
python plugins/scaffold.py \
  --name session-logger \
  --type agent \
  --author "Jane Dev" \
  --description "Logs all agent sessions" \
  --with-tests

# Create integration plugin with MCP tools
python plugins/scaffold.py \
  --name slack-notifier \
  --type integration \
  --author "John Dev" \
  --with-mcp-tools \
  --with-tests
```

### Manual Scaffolding

If you prefer manual setup:

```bash
# Create plugin directory
mkdir -p my-plugin
cd my-plugin

# Create basic structure
touch plugin.json
touch agent.py  # or integration.py or ui.py
touch README.md
mkdir tests
touch tests/__init__.py
touch tests/test_plugin.py
```

---

## Agent Plugin Templates

### Minimal Agent Plugin

**File: `plugin.json`**

```json
{
  "name": "my-agent-plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Basic agent plugin",
  "plugin_type": "agent",
  "required_permissions": [],
  "auto_claude_version": ">=2.8.0"
}
```

**File: `agent.py`**

```python
from plugins.sdk.agent import AgentPlugin, AgentContext
import logging

logger = logging.getLogger(__name__)

class MyAgentPlugin(AgentPlugin):
    """Minimal agent plugin template."""

    def on_load(self):
        """Called when plugin is loaded."""
        logger.info(f"{self.name} v{self.version} loaded")

    def on_enable(self):
        """Called when plugin is enabled."""
        logger.info(f"{self.name} enabled")

    def before_session(self, context: AgentContext):
        """Called before agent session starts."""
        logger.info(f"Session starting: {context.spec_name}")

    def after_session(self, context: AgentContext, success: bool):
        """Called after agent session completes."""
        status = "succeeded" if success else "failed"
        logger.info(f"Session {status}: {context.spec_name}")

    def on_disable(self):
        """Called when plugin is disabled."""
        logger.info(f"{self.name} disabled")

    def on_unload(self):
        """Called when plugin is unloaded."""
        logger.info(f"{self.name} unloaded")
```

---

### Session Analytics Plugin

**Use case**: Track session metrics, timing, and outcomes

**File: `plugin.json`**

```json
{
  "name": "session-analytics",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Track agent session analytics",
  "plugin_type": "agent",
  "required_permissions": ["filesystem:write"],
  "auto_claude_version": ">=2.8.0",
  "config": {
    "output_file": ".auto-claude/analytics/sessions.json",
    "track_tools_usage": true,
    "track_message_count": true
  }
}
```

**File: `agent.py`**

```python
from plugins.sdk.agent import AgentPlugin, AgentContext
from datetime import datetime
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SessionAnalyticsPlugin(AgentPlugin):
    """Track agent session analytics."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_start = None
        self.tool_calls = []
        self.message_count = 0

    def on_enable(self):
        """Initialize analytics storage."""
        output_file = Path(self.config.get("output_file", ".auto-claude/analytics/sessions.json"))
        output_file.parent.mkdir(parents=True, exist_ok=True)
        if not output_file.exists():
            output_file.write_text("[]")
        logger.info(f"Analytics enabled, output: {output_file}")

    def before_session(self, context: AgentContext):
        """Record session start time."""
        self.session_start = datetime.now()
        self.tool_calls = []
        self.message_count = 0
        logger.info(f"Session started: {context.spec_name}")

    def on_message(self, context: AgentContext, message: dict):
        """Track messages and tool usage."""
        self.message_count += 1

        # Track tool calls if enabled
        if self.config.get("track_tools_usage") and "tool_use" in message:
            tool_name = message["tool_use"].get("name")
            if tool_name:
                self.tool_calls.append(tool_name)

    def after_session(self, context: AgentContext, success: bool):
        """Save session analytics."""
        if not self.session_start:
            return

        duration = (datetime.now() - self.session_start).total_seconds()

        analytics = {
            "spec_name": context.spec_name,
            "agent_type": context.agent_type,
            "success": success,
            "duration_seconds": duration,
            "message_count": self.message_count,
            "tool_calls": self.tool_calls if self.config.get("track_tools_usage") else None,
            "timestamp": datetime.now().isoformat()
        }

        # Append to analytics file
        output_file = Path(self.config.get("output_file"))
        try:
            data = json.loads(output_file.read_text())
            data.append(analytics)
            output_file.write_text(json.dumps(data, indent=2))
            logger.info(f"Analytics saved: {duration:.1f}s, {self.message_count} messages")
        except Exception as e:
            logger.error(f"Failed to save analytics: {e}")
```

---

### Session Notification Plugin

**Use case**: Send notifications when sessions complete

**File: `plugin.json`**

```json
{
  "name": "session-notifier",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Send notifications on session events",
  "plugin_type": "agent",
  "required_permissions": ["network:http"],
  "auto_claude_version": ">=2.8.0",
  "config": {
    "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    "notify_on_success": true,
    "notify_on_failure": true,
    "include_spec_details": true
  }
}
```

**File: `agent.py`**

```python
from plugins.sdk.agent import AgentPlugin, AgentContext
import logging
import requests

logger = logging.getLogger(__name__)

class SessionNotifierPlugin(AgentPlugin):
    """Send webhook notifications on session events."""

    def after_session(self, context: AgentContext, success: bool):
        """Send notification when session completes."""
        # Check if we should notify
        if success and not self.config.get("notify_on_success"):
            return
        if not success and not self.config.get("notify_on_failure"):
            return

        webhook_url = self.config.get("webhook_url")
        if not webhook_url:
            logger.warning("No webhook_url configured")
            return

        # Build notification payload
        status = "✅ Succeeded" if success else "❌ Failed"
        message = f"Agent session {status}\n\n"
        message += f"**Spec:** {context.spec_name}\n"
        message += f"**Agent:** {context.agent_type}\n"

        if self.config.get("include_spec_details"):
            message += f"**Project:** {context.project_dir}\n"

        payload = {
            "text": message,
            "username": "Auto Code",
            "icon_emoji": ":robot_face:"
        }

        # Send webhook
        try:
            response = requests.post(webhook_url, json=payload, timeout=5)
            response.raise_for_status()
            logger.info(f"Notification sent: {status}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
```

---

## Integration Plugin Templates

### Minimal Integration Plugin

**File: `plugin.json`**

```json
{
  "name": "my-integration",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Basic integration plugin",
  "plugin_type": "integration",
  "required_permissions": ["network:http"],
  "auto_claude_version": ">=2.8.0"
}
```

**File: `integration.py`**

```python
from plugins.sdk.integration import IntegrationPlugin, IntegrationContext
import logging

logger = logging.getLogger(__name__)

class MyIntegrationPlugin(IntegrationPlugin):
    """Minimal integration plugin template."""

    def on_load(self):
        """Called when plugin is loaded."""
        logger.info(f"{self.name} v{self.version} loaded")

    def on_enable(self):
        """Called when plugin is enabled."""
        logger.info(f"{self.name} enabled")

    def is_available(self) -> bool:
        """Check if integration is ready to use."""
        # Check API keys, connection, etc.
        return True

    def on_build_start(self, context: IntegrationContext):
        """Called when a spec build starts."""
        logger.info(f"Build started: {context.spec_name}")

    def on_build_complete(self, context: IntegrationContext, success: bool):
        """Called when a spec build completes."""
        status = "succeeded" if success else "failed"
        logger.info(f"Build {status}: {context.spec_name}")

    def on_disable(self):
        """Called when plugin is disabled."""
        logger.info(f"{self.name} disabled")

    def on_unload(self):
        """Called when plugin is unloaded."""
        logger.info(f"{self.name} unloaded")
```

---

### Issue Tracker Integration

**Use case**: Sync builds with external issue trackers (Jira, GitHub, Linear)

**File: `plugin.json`**

```json
{
  "name": "issue-tracker",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Sync builds with issue tracker",
  "plugin_type": "integration",
  "required_permissions": ["network:http"],
  "auto_claude_version": ">=2.8.0",
  "config": {
    "api_url": "https://api.github.com",
    "api_token": "${GITHUB_TOKEN}",
    "auto_create_issues": true,
    "auto_update_status": true,
    "labels": ["auto-code", "ai-generated"]
  }
}
```

**File: `integration.py`**

```python
from plugins.sdk.integration import IntegrationPlugin, IntegrationContext
import logging
import requests
import os

logger = logging.getLogger(__name__)

class IssueTrackerPlugin(IntegrationPlugin):
    """Sync builds with external issue tracker."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_url = None
        self.api_token = None
        self.issue_map = {}  # spec_name -> issue_id

    def on_enable(self):
        """Initialize API connection."""
        self.api_url = self.config.get("api_url")
        api_token = self.config.get("api_token", "")

        # Support environment variable substitution
        if api_token.startswith("${") and api_token.endswith("}"):
            env_var = api_token[2:-1]
            self.api_token = os.environ.get(env_var)
        else:
            self.api_token = api_token

        if not self.api_token:
            logger.warning(f"{self.name}: No API token configured")

    def is_available(self) -> bool:
        """Check if integration is ready."""
        return bool(self.api_url and self.api_token)

    def on_build_start(self, context: IntegrationContext):
        """Create or update issue when build starts."""
        if not self.config.get("auto_create_issues"):
            return

        if not self.is_available():
            logger.warning("Issue tracker not available")
            return

        # Create issue
        issue = self._create_issue(context)
        if issue:
            self.issue_map[context.spec_name] = issue["id"]
            logger.info(f"Created issue: {issue['url']}")

    def on_build_complete(self, context: IntegrationContext, success: bool):
        """Update issue status when build completes."""
        if not self.config.get("auto_update_status"):
            return

        issue_id = self.issue_map.get(context.spec_name)
        if not issue_id:
            return

        status = "completed" if success else "failed"
        self._update_issue_status(issue_id, status)
        logger.info(f"Updated issue {issue_id}: {status}")

    def on_subtask_update(self, context: IntegrationContext, subtask_id: str, status: str):
        """Update issue when subtask status changes."""
        if not self.config.get("auto_update_status"):
            return

        issue_id = self.issue_map.get(context.spec_name)
        if not issue_id:
            return

        # Add comment with subtask update
        comment = f"Subtask `{subtask_id}` → {status}"
        self._add_issue_comment(issue_id, comment)

    def _create_issue(self, context: IntegrationContext) -> dict:
        """Create issue in tracker."""
        try:
            payload = {
                "title": f"Auto Code: {context.spec_name}",
                "description": f"Automated build for spec {context.spec_name}",
                "labels": self.config.get("labels", [])
            }
            response = requests.post(
                f"{self.api_url}/issues",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to create issue: {e}")
            return None

    def _update_issue_status(self, issue_id: str, status: str):
        """Update issue status."""
        try:
            payload = {"status": status}
            response = requests.patch(
                f"{self.api_url}/issues/{issue_id}",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=10
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to update issue: {e}")

    def _add_issue_comment(self, issue_id: str, comment: str):
        """Add comment to issue."""
        try:
            payload = {"body": comment}
            response = requests.post(
                f"{self.api_url}/issues/{issue_id}/comments",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=10
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
```

---

### MCP Tool Integration

**Use case**: Add custom MCP tools for agents

**File: `plugin.json`**

```json
{
  "name": "custom-tools",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Custom MCP tools for agents",
  "plugin_type": "integration",
  "required_permissions": ["filesystem:read", "network:http"],
  "auto_claude_version": ">=2.8.0"
}
```

**File: `integration.py`**

```python
from plugins.sdk.integration import IntegrationPlugin, IntegrationContext
from typing import List, Callable
import logging

logger = logging.getLogger(__name__)

class CustomToolsPlugin(IntegrationPlugin):
    """Provide custom MCP tools for agents."""

    def create_mcp_tools(self, context: IntegrationContext) -> List[Callable]:
        """Return list of MCP tool functions."""
        return [
            self.fetch_api_docs,
            self.validate_config,
            self.run_custom_check
        ]

    def fetch_api_docs(self, library_name: str) -> dict:
        """
        Fetch API documentation for a library.

        Args:
            library_name: Name of the library to fetch docs for

        Returns:
            Dictionary with documentation content
        """
        # Implement API docs fetching logic
        logger.info(f"Fetching docs for: {library_name}")
        return {
            "library": library_name,
            "docs": "Documentation content here..."
        }

    def validate_config(self, config_path: str) -> dict:
        """
        Validate configuration file.

        Args:
            config_path: Path to config file

        Returns:
            Validation results
        """
        # Implement config validation logic
        logger.info(f"Validating config: {config_path}")
        return {
            "valid": True,
            "errors": [],
            "warnings": []
        }

    def run_custom_check(self, check_type: str) -> dict:
        """
        Run custom project check.

        Args:
            check_type: Type of check to run

        Returns:
            Check results
        """
        # Implement custom check logic
        logger.info(f"Running check: {check_type}")
        return {
            "check_type": check_type,
            "passed": True,
            "details": "Check completed successfully"
        }
```

---

## UI Plugin Templates

### Minimal UI Plugin

**File: `plugin.json`**

```json
{
  "name": "my-ui-plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Basic UI plugin",
  "plugin_type": "ui",
  "required_permissions": [],
  "auto_claude_version": ">=2.8.0",
  "ui": {
    "entry_point": "ui/index.tsx",
    "routes": [
      {
        "path": "/plugins/my-plugin",
        "component": "MyPluginView"
      }
    ]
  }
}
```

**File: `ui/index.tsx`**

```typescript
import React from 'react';

interface MyPluginViewProps {
  // Define props
}

export const MyPluginView: React.FC<MyPluginViewProps> = () => {
  return (
    <div className="plugin-container">
      <h1>My Plugin</h1>
      <p>Plugin UI content here</p>
    </div>
  );
};

export default MyPluginView;
```

---

### Dashboard Plugin

**Use case**: Add custom dashboard view

**File: `plugin.json`**

```json
{
  "name": "build-dashboard",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Custom build metrics dashboard",
  "plugin_type": "ui",
  "required_permissions": ["filesystem:read"],
  "auto_claude_version": ">=2.8.0",
  "ui": {
    "entry_point": "ui/Dashboard.tsx",
    "routes": [
      {
        "path": "/plugins/dashboard",
        "component": "BuildDashboard",
        "menu_item": {
          "label": "Build Dashboard",
          "icon": "dashboard"
        }
      }
    ]
  }
}
```

**File: `ui/Dashboard.tsx`**

```typescript
import React, { useState, useEffect } from 'react';
import { Card, Chart, Metric } from '@auto-claude/ui-components';

interface BuildMetrics {
  totalBuilds: number;
  successRate: number;
  avgDuration: number;
  recentBuilds: Array<{
    specName: string;
    success: boolean;
    duration: number;
    timestamp: string;
  }>;
}

export const BuildDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<BuildMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch metrics from backend
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      const response = await fetch('/api/plugins/build-dashboard/metrics');
      const data = await response.json();
      setMetrics(data);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading metrics...</div>;
  }

  if (!metrics) {
    return <div>Failed to load metrics</div>;
  }

  return (
    <div className="dashboard-container">
      <h1>Build Dashboard</h1>

      <div className="metrics-grid">
        <Card>
          <Metric
            label="Total Builds"
            value={metrics.totalBuilds}
            icon="build"
          />
        </Card>

        <Card>
          <Metric
            label="Success Rate"
            value={`${metrics.successRate.toFixed(1)}%`}
            icon="check"
          />
        </Card>

        <Card>
          <Metric
            label="Avg Duration"
            value={`${metrics.avgDuration.toFixed(1)}s`}
            icon="timer"
          />
        </Card>
      </div>

      <Card>
        <h2>Recent Builds</h2>
        <Chart
          type="line"
          data={metrics.recentBuilds}
          xAxis="timestamp"
          yAxis="duration"
        />
      </Card>

      <Card>
        <h2>Build History</h2>
        <table className="build-table">
          <thead>
            <tr>
              <th>Spec</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {metrics.recentBuilds.map((build, idx) => (
              <tr key={idx}>
                <td>{build.specName}</td>
                <td>
                  {build.success ? '✅ Success' : '❌ Failed'}
                </td>
                <td>{build.duration.toFixed(1)}s</td>
                <td>{new Date(build.timestamp).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
};

export default BuildDashboard;
```

---

## Testing Templates

### Agent Plugin Tests

**File: `tests/test_agent_plugin.py`**

```python
import pytest
from unittest.mock import Mock, patch
from plugins.sdk.agent import AgentContext
from agent import MyAgentPlugin  # Import your plugin

@pytest.fixture
def plugin():
    """Create plugin instance for testing."""
    manifest = {
        "name": "test-plugin",
        "version": "1.0.0",
        "plugin_type": "agent",
        "config": {}
    }
    return MyAgentPlugin(manifest, "/fake/path")

@pytest.fixture
def context():
    """Create mock AgentContext."""
    return AgentContext(
        spec_name="test-spec",
        spec_dir="/fake/spec",
        project_dir="/fake/project",
        agent_type="coder"
    )

def test_on_load(plugin):
    """Test plugin loads successfully."""
    plugin.on_load()
    # Add assertions based on your plugin behavior

def test_on_enable(plugin):
    """Test plugin enables successfully."""
    plugin.on_enable()
    # Add assertions

def test_before_session(plugin, context):
    """Test before_session hook."""
    plugin.before_session(context)
    # Add assertions

def test_after_session(plugin, context):
    """Test after_session hook."""
    plugin.after_session(context, success=True)
    # Add assertions for success case

    plugin.after_session(context, success=False)
    # Add assertions for failure case

def test_on_message(plugin, context):
    """Test on_message hook."""
    message = {
        "role": "assistant",
        "content": "Test message"
    }
    plugin.on_message(context, message)
    # Add assertions

def test_on_disable(plugin):
    """Test plugin disables cleanly."""
    plugin.on_disable()
    # Add assertions

def test_on_unload(plugin):
    """Test plugin unloads cleanly."""
    plugin.on_unload()
    # Add assertions
```

---

### Integration Plugin Tests

**File: `tests/test_integration_plugin.py`**

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from plugins.sdk.integration import IntegrationContext
from integration import MyIntegrationPlugin  # Import your plugin

@pytest.fixture
def plugin():
    """Create plugin instance for testing."""
    manifest = {
        "name": "test-integration",
        "version": "1.0.0",
        "plugin_type": "integration",
        "config": {
            "api_url": "https://api.example.com",
            "api_token": "test-token"
        }
    }
    return MyIntegrationPlugin(manifest, "/fake/path")

@pytest.fixture
def context():
    """Create mock IntegrationContext."""
    return IntegrationContext(
        spec_name="test-spec",
        spec_dir="/fake/spec",
        project_dir="/fake/project"
    )

def test_is_available(plugin):
    """Test availability check."""
    assert plugin.is_available() is True

def test_on_build_start(plugin, context):
    """Test build start hook."""
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": "123"}

        plugin.on_build_start(context)

        # Verify API call was made
        assert mock_post.called

def test_on_build_complete(plugin, context):
    """Test build complete hook."""
    with patch('requests.patch') as mock_patch:
        mock_patch.return_value.status_code = 200

        plugin.on_build_complete(context, success=True)

        # Verify API call was made
        assert mock_patch.called

def test_create_mcp_tools(plugin, context):
    """Test MCP tool creation."""
    tools = plugin.create_mcp_tools(context)

    # Verify tools were created
    assert isinstance(tools, list)
    assert len(tools) > 0

    # Test each tool is callable
    for tool in tools:
        assert callable(tool)
```

---

### UI Plugin Tests

**File: `tests/Dashboard.test.tsx`**

```typescript
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BuildDashboard } from '../ui/Dashboard';

// Mock fetch
global.fetch = jest.fn();

describe('BuildDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    (global.fetch as jest.Mock).mockImplementation(() =>
      new Promise(() => {}) // Never resolves
    );

    render(<BuildDashboard />);
    expect(screen.getByText('Loading metrics...')).toBeInTheDocument();
  });

  it('renders metrics when loaded', async () => {
    const mockMetrics = {
      totalBuilds: 42,
      successRate: 85.5,
      avgDuration: 123.4,
      recentBuilds: [
        {
          specName: 'test-spec',
          success: true,
          duration: 120,
          timestamp: '2024-01-01T00:00:00Z'
        }
      ]
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      json: async () => mockMetrics
    });

    render(<BuildDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Total Builds')).toBeInTheDocument();
      expect(screen.getByText('42')).toBeInTheDocument();
      expect(screen.getByText('85.5%')).toBeInTheDocument();
      expect(screen.getByText('123.4s')).toBeInTheDocument();
    });
  });

  it('renders error state on fetch failure', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error('Failed to fetch'));

    render(<BuildDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load metrics')).toBeInTheDocument();
    });
  });
});
```

---

## Common Patterns

### Configuration with Environment Variables

```python
import os

class MyPlugin(AgentPlugin):
    def on_enable(self):
        """Support ${ENV_VAR} syntax in config."""
        api_key = self.config.get("api_key", "")

        # Expand environment variables
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.environ.get(env_var)

        if not api_key:
            self.logger.warning("No API key configured")
            return

        self.api_key = api_key
```

---

### Error Handling

```python
class MyPlugin(AgentPlugin):
    def before_session(self, context: AgentContext):
        """Always wrap external calls in try/except."""
        try:
            result = self._do_something_risky()
            self.logger.info(f"Success: {result}")
        except Exception as e:
            # Log error but don't crash the agent session
            self.logger.error(f"Failed to do something: {e}")
            # Optionally re-raise if critical
            # raise
```

---

### Async Operations

```python
import asyncio
from typing import Optional

class MyPlugin(AgentPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._background_task: Optional[asyncio.Task] = None

    def on_enable(self):
        """Start background task."""
        loop = asyncio.get_event_loop()
        self._background_task = loop.create_task(self._monitor())

    async def _monitor(self):
        """Background monitoring task."""
        while True:
            try:
                await self._check_something()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")

    def on_disable(self):
        """Stop background task."""
        if self._background_task:
            self._background_task.cancel()
```

---

### Caching

```python
from functools import lru_cache
import time

class MyPlugin(IntegrationPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    def _get_cached(self, key: str):
        """Get value from cache if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return value
        return None

    def _set_cached(self, key: str, value):
        """Store value in cache with timestamp."""
        self._cache[key] = (value, time.time())

    def fetch_data(self, resource_id: str):
        """Fetch data with caching."""
        # Check cache first
        cached = self._get_cached(resource_id)
        if cached is not None:
            return cached

        # Fetch from API
        data = self._fetch_from_api(resource_id)

        # Cache result
        self._set_cached(resource_id, data)

        return data
```

---

### Rate Limiting

```python
import time
from collections import deque

class MyPlugin(IntegrationPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rate_limit = 10  # requests per minute
        self._requests = deque()

    def _check_rate_limit(self):
        """Enforce rate limit."""
        now = time.time()

        # Remove requests older than 1 minute
        while self._requests and self._requests[0] < now - 60:
            self._requests.popleft()

        # Check if we've hit the limit
        if len(self._requests) >= self._rate_limit:
            wait_time = 60 - (now - self._requests[0])
            raise Exception(f"Rate limit exceeded. Try again in {wait_time:.1f}s")

        # Record this request
        self._requests.append(now)

    def make_api_call(self, endpoint: str):
        """Make API call with rate limiting."""
        self._check_rate_limit()
        # Make the actual API call
        return self._call_api(endpoint)
```

---

## Configuration Templates

### Plugin Manifest (plugin.json)

```json
{
  "name": "plugin-name",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "Plugin description",
  "plugin_type": "agent | integration | ui",
  "required_permissions": [
    "filesystem:read",
    "filesystem:write",
    "network:http",
    "network:ws",
    "subprocess:run"
  ],
  "auto_claude_version": ">=2.8.0",
  "config": {
    "setting1": "value1",
    "setting2": "${ENV_VAR}",
    "setting3": true
  },
  "dependencies": {
    "requests": ">=2.31.0",
    "asyncio": ">=3.4.3"
  },
  "ui": {
    "entry_point": "ui/index.tsx",
    "routes": [
      {
        "path": "/plugins/my-plugin",
        "component": "MyComponent",
        "menu_item": {
          "label": "My Plugin",
          "icon": "extension"
        }
      }
    ]
  }
}
```

---

### README Template

```markdown
# Plugin Name

Short description of what the plugin does.

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

\`\`\`bash
cd apps/backend
python plugins/cli.py install --path /path/to/plugin-name
python plugins/cli.py enable plugin-name
\`\`\`

## Configuration

Required environment variables:
- `API_KEY` - Your API key
- `API_URL` - API endpoint URL (optional)

Configuration in `plugin.json`:
\`\`\`json
{
  "config": {
    "setting1": "value1",
    "api_key": "${API_KEY}"
  }
}
\`\`\`

## Usage

How to use the plugin...

## Development

\`\`\`bash
# Run tests
pytest tests/

# Run linting
ruff check .
\`\`\`

## License

MIT
```

---

## Directory Structures

### Agent Plugin Structure

```
my-agent-plugin/
├── plugin.json          # Plugin manifest
├── agent.py             # Plugin implementation
├── README.md            # Documentation
├── requirements.txt     # Python dependencies (optional)
├── tests/
│   ├── __init__.py
│   └── test_plugin.py   # Unit tests
└── examples/
    └── usage.md         # Usage examples
```

---

### Integration Plugin Structure

```
my-integration/
├── plugin.json          # Plugin manifest
├── integration.py       # Plugin implementation
├── README.md            # Documentation
├── requirements.txt     # Python dependencies (optional)
├── lib/
│   ├── __init__.py
│   ├── api_client.py    # API client
│   └── utils.py         # Utilities
├── tests/
│   ├── __init__.py
│   ├── test_plugin.py
│   └── test_api_client.py
└── examples/
    └── usage.md
```

---

### UI Plugin Structure

```
my-ui-plugin/
├── plugin.json          # Plugin manifest
├── ui.py                # Backend component (optional)
├── README.md            # Documentation
├── package.json         # Node dependencies
├── ui/
│   ├── index.tsx        # Entry point
│   ├── components/
│   │   ├── Dashboard.tsx
│   │   └── Settings.tsx
│   ├── hooks/
│   │   └── useMetrics.ts
│   └── styles/
│       └── plugin.css
├── tests/
│   ├── Dashboard.test.tsx
│   └── Settings.test.tsx
└── examples/
    └── usage.md
```

---

### Full-Featured Plugin Structure

```
my-plugin/
├── plugin.json          # Plugin manifest
├── agent.py             # Agent hooks
├── integration.py       # Integration hooks
├── ui.py                # UI backend
├── README.md            # Documentation
├── requirements.txt     # Python dependencies
├── package.json         # Node dependencies
├── lib/
│   ├── __init__.py
│   ├── api_client.py
│   ├── models.py
│   └── utils.py
├── ui/
│   ├── index.tsx
│   ├── components/
│   ├── hooks/
│   └── styles/
├── tests/
│   ├── test_agent.py
│   ├── test_integration.py
│   └── ui/
│       └── Dashboard.test.tsx
├── examples/
│   ├── basic-usage.md
│   └── advanced-usage.md
└── docs/
    ├── api.md
    └── configuration.md
```

---

## Next Steps

- **Study examples**: Review `examples/plugins/` for working implementations
- **Read full guide**: See [Plugin Development Guide](plugin-development.md) for detailed documentation
- **Test thoroughly**: Use provided test templates to ensure quality
- **Follow best practices**: Refer to security and performance guidelines
- **Distribute**: Package and share your plugin with the community

---

## See Also

- [Plugin Development Guide](plugin-development.md) - Complete development guide
- [Plugin API Reference](../api/plugins.md) - Full API documentation
- [Plugin Examples](../../examples/plugins/) - Working plugin examples
- [Security Guidelines](../security/plugin-security.md) - Security best practices
