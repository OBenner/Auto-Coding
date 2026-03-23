# Agent Thought Process Inspector

The Agent Inspector provides real-time visibility into AI agent reasoning, tool calls, and decision-making processes during task execution.

## Overview

Access the Agent Inspector from the sidebar navigation. It displays:

- **Thinking blocks** — The agent's internal reasoning and chain-of-thought
- **Tool calls** — Every tool invocation with inputs, outputs, duration, and success/failure status
- **Performance metrics** — Timing data, token usage, and efficiency statistics
- **Pattern detection** — Automatic identification of suspicious behaviors

## Features

### Three View Modes

| View | Description |
|------|-------------|
| **Timeline** | Chronological stream of all agent events (thinking + tools) |
| **Thoughts** | Filtered view showing only thinking/reasoning blocks |
| **Tool Calls** | Filtered view showing only tool invocations |

### Search & Filter

- **Full-text search** with keyboard shortcut (Cmd+Shift+K / Ctrl+Shift+K)
- **Tool type filters** — filter by specific tool names (Bash, Read, Write, Grep, etc.)
- **Select/deselect all** tool types

### Pattern Detection

The inspector automatically analyzes agent behavior for suspicious patterns:

| Pattern | Trigger | Description |
|---------|---------|-------------|
| **Infinite Loop** | Same tool called N+ times consecutively | Agent may be stuck repeating the same action |
| **Repeated Failures** | Multiple consecutive tool failures | Agent may be unable to recover from errors |
| **Rapid Execution** | Tools executed faster than expected | May indicate no-op or trivial tool calls |
| **Same Error** | Identical errors appearing repeatedly | Underlying issue not being addressed |
| **No Progress** | High tool call count with low completion | Agent may be spinning without making progress |

Each detected pattern shows:
- Severity level (warning, error, info)
- Affected tool calls with timestamps
- Actionable suggestions for resolution

### Performance Metrics

Real-time statistics including:

- **Total duration** — End-to-end session time
- **Tool call count** — Total invocations
- **Success rate** — Percentage of successful tool calls
- **Average duration** — Mean tool execution time
- **Fastest/slowest** — Extremes with tool identification
- **Thinking time** — Total time spent in reasoning blocks
- **Token usage** — Input/output token counts

### Export

Export session data for offline analysis:

- **JSON format** — Complete structured data for programmatic consumption
- **Markdown format** — Human-readable report suitable for sharing

## Architecture

### Component Structure

```text
agent-inspector/
├── ThoughtInspector.tsx      # Main container with view switching
├── ThoughtBlock.tsx          # Individual thinking block display
├── ToolCallBlock.tsx         # Tool call with input/output/timing
├── PatternDetector.tsx       # Suspicious pattern analysis
├── PerformanceMetrics.tsx    # Performance statistics dashboard
├── SearchBar.tsx             # Search with keyboard shortcut
├── FilterPanel.tsx           # Tool type filter checkboxes
└── ExportDialog.tsx          # JSON/Markdown export modal
```

### Data Flow

1. `ThoughtInspector` loads data via IPC from the backend task logger
2. Backend reads `.ndjson` session log files from spec directories
3. Log entries are parsed into thinking blocks and tool calls
4. Pattern detection runs client-side against the loaded tool calls
5. Performance metrics are computed from timing data in tool calls

### IPC Channels

| Channel | Purpose |
|---------|---------|
| `AGENT_INSPECTOR_GET_THOUGHTS` | Load thinking/reasoning blocks |
| `AGENT_INSPECTOR_GET_TOOL_CALLS` | Load tool call entries |
| `AGENT_INSPECTOR_GET_INSPECTOR_DATA` | Load combined data (thoughts + tools + metrics) |
| `AGENT_INSPECTOR_EXPORT_SESSION` | Export session as JSON or Markdown |

### Backend Integration

The inspector reads from the task logger system:

- **Session logs**: `apps/backend/task_logger/logger.py` — writes `.ndjson` log files
- **Log models**: `apps/backend/task_logger/models.py` — defines `LogEntry` structure
- **Session tracking**: `apps/backend/agents/session.py` — manages session lifecycle

Each log entry contains:
- Timestamp and session ID
- Entry type (thinking, tool_use, tool_result, text, error)
- Content, tool name, inputs/outputs
- Duration and success/failure status

## Usage

### Viewing Agent Activity

1. Start a task (or select a completed task)
2. Click **Agent Inspector** in the sidebar
3. Select the session to inspect
4. Switch between Timeline, Thoughts, and Tool Calls views

### Debugging Issues

1. Open the **Pattern Detection** panel to see flagged behaviors
2. Click on affected items to jump to the relevant log entries
3. Expand tool calls to see full input/output
4. Use search to find specific tool names or content

### Exporting for Review

1. Click the **Export** button in the inspector toolbar
2. Choose JSON (for data analysis) or Markdown (for sharing)
3. Select the session and download

## Internationalization

All UI text uses `react-i18next` with the `agent-inspector` namespace:
- English: `locales/en/agent-inspector.json`
- French: `locales/fr/agent-inspector.json`
