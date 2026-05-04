# Long-Running Command Handler

**Status:** Stable
**Version:** 2.9.0
**Last Updated:** 2026-02-10

---

## Overview

The Long-Running Command Handler is a robust async execution system that enables AI agents to run commands that take minutes or hours to complete without timing out or failing. This feature solves a critical limitation in autonomous coding workflows where build processes, comprehensive test suites, or data processing operations need to run without constant supervision.

**Key Problem Solved:** Traditional command execution in AI agents fails on long-running tasks due to timeout constraints and lack of state persistence. This feature enables autonomous workflows that were previously impossible, giving Auto Code a significant advantage over systems like GitHub Copilot Agent.

---

## Key Benefits

| Benefit | Description |
|---------|-------------|
| **4+ Hour Execution** | Commands can run for up to 4 hours (configurable) without timing out, enabling complex build and test workflows |
| **Real-Time Progress** | Live output streaming shows exactly what's happening, so users know the agent hasn't crashed |
| **State Persistence** | Task state survives app restarts, network interruptions, and crashes - work never gets lost |
| **Graceful Cancellation** | Cancel long operations safely with automatic cleanup and process termination |
| **Memory Monitoring** | Automatic memory usage tracking prevents system overload on resource-intensive tasks |
| **Error Recovery** | Failed commands capture context and suggest retry strategies for faster debugging |

---

## How It Works

The Long-Running Command Handler uses asyncio for non-blocking command execution with comprehensive state management.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Electron)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  TaskProgress Component (Real-time UI)              │   │
│  │  - Live output display (xterm.js)                   │   │
│  │  - Status badge (running/completed/failed)          │   │
│  │  - Cancel button with confirmation                  │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ IPC Events
                       │ (start, cancel, status, progress)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Backend (Python + MCP Tools)                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  BackgroundTaskManager                              │   │
│  │  - Async command execution (asyncio)                │   │
│  │  - Output streaming & buffering                     │   │
│  │  - Process lifecycle management                     │   │
│  │  - Memory monitoring (psutil)                       │   │
│  │  - Error classification & suggestions               │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  TaskStateStore                                     │   │
│  │  - Atomic state persistence (JSON)                  │   │
│  │  - Orphaned task recovery                           │   │
│  │  - Task history tracking                            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                       │
                       │ Subprocess
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         Long-Running Command (npm, pytest, etc.)            │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **BackgroundTaskManager** | `apps/backend/agents/tools_pkg/tools/background_task.py` | Core task execution engine with async subprocess management |
| **TaskStateStore** | `apps/backend/core/task_state_store.py` | Atomic state persistence layer with crash recovery |
| **BackgroundTaskState** | `apps/frontend/src/main/agent/task-state.ts` | Frontend state management for task tracking |
| **TaskProgress Component** | `apps/frontend/src/renderer/components/TaskProgress.tsx` | Real-time UI for output display and control |
| **MCP Tools** | `apps/backend/agents/tools_pkg/tools/background_task.py` | Agent-accessible tools (start, cancel, status, output) |

---

## Getting Started

### Prerequisites

- Auto Code 2.9.0 or later
- Python 3.12+ with asyncio support
- Optional: `psutil` for memory monitoring (auto-installed)

### Basic Usage

**For AI Agents (via MCP Tools):**

```python
# Start a long-running command
result = start_background_command(
    command="npm run build:all",
    timeout=7200  # 2 hours
)
task_id = result["task_id"]

# Check status
status = get_task_status(task_id)
print(f"Status: {status['status']}")  # running/completed/failed/cancelled

# Get output
output = get_task_output(task_id)
print(output["output"])  # Live output stream

# Cancel if needed
cancel_task(task_id)
```

**For Python Backend:**

```python
from pathlib import Path
from agents.tools_pkg.tools.background_task import BackgroundTaskManager

# Initialize manager
manager = BackgroundTaskManager(
    spec_dir=Path(".auto-claude/specs/001"),
    project_dir=Path(".")
)

# Start task
task_id = await manager.start_task(
    command="pytest tests/ -v",
    timeout=3600,  # 1 hour
    working_dir=Path(".")
)

# Monitor progress
status = manager.get_task_status(task_id)
output = manager.get_task_output(task_id)

# Cancel if needed
await manager.cancel_task(task_id)
```

**Expected Result:**
```json
{
  "task_id": "task_20260210_120000",
  "status": "running",
  "command": "pytest tests/ -v",
  "started_at": "2026-02-10T12:00:00Z",
  "output": "===== test session starts =====\n...",
  "pid": 12345,
  "memory_stats": {
    "percent": 45.2,
    "available_mb": 8192,
    "total_mb": 16384
  }
}
```

### Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `timeout` | integer | `14400` (4 hours) | Maximum execution time in seconds |
| `working_dir` | Path | Project root | Directory where command executes |
| `MEMORY_WARNING_THRESHOLD` | float | `80.0` | Memory usage % to trigger warnings |
| `MEMORY_CRITICAL_THRESHOLD` | float | `90.0` | Memory usage % for critical alerts |
| `MEMORY_CHECK_INTERVAL` | integer | `5` | Check memory every N lines of output |

---

## Use Cases

### Use Case 1: Large test suite execution

**Scenario:** Running comprehensive test suite that takes 30+ minutes

**Steps:**
1. Agent starts background command: `pytest tests/ --full-coverage -v`
2. Task executes with real-time output streaming
3. Agent continues other work while tests run
4. Agent checks status periodically
5. On completion, agent reviews results and makes decisions

**Outcome:** Agent can run full test suites without blocking or timing out

### Use Case 2: Multi-stage build process

**Scenario:** Building Docker images or compiling large projects

**Steps:**
1. Agent starts build: `docker build -t myapp:latest . && docker-compose up -d`
2. Build runs in background with progress tracking
3. Memory monitoring ensures system doesn't run out of resources
4. State persists if user restarts app during build
5. Agent captures build logs for debugging if failures occur

**Outcome:** Complex builds complete reliably with full observability

### Use Case 3: Data processing pipelines

**Scenario:** Running data migration or ETL jobs

**Steps:**
1. Agent starts processing: `python scripts/migrate_data.py --all`
2. Task streams output showing progress through records
3. User can cancel safely if wrong data set selected
4. Error context captured if migration fails
5. Agent suggests retry strategies based on error type

**Outcome:** Data operations run safely with recovery options

---

## Advanced Features

### Configurable timeout with 4+ hour support

The system supports timeouts up to 4 hours by default, configurable to any duration:

```python
# 8-hour timeout for extremely long builds
task_id = await manager.start_task(
    command="npm run build:production",
    timeout=28800  # 8 hours
)
```

**Implementation:** Uses `asyncio.wait_for()` to enforce timeout at both output reading and process completion levels.

### Memory monitoring and throttling

Automatic memory tracking prevents system overload:

```python
# Memory stats captured at start, during execution, and completion
status = manager.get_task_status(task_id)
print(status["memory_stats"])
# {
#   "percent": 78.5,
#   "available_mb": 4096,
#   "total_mb": 16384,
#   "used_mb": 12288
# }
```

**Behavior:**
- Warning logged at 80% memory usage
- Critical alert at 90% memory usage
- Stats persisted every 5 lines of output
- Available when `psutil` installed (automatic)

### State recovery on app restart

Orphaned tasks are automatically recovered on startup:

```python
from core.task_state_store import TaskStateStore

store = TaskStateStore(state_dir)

# Auto-recovery on app startup
recovery_stats = store.recover_on_startup()
print(f"Recovered {recovery_stats['orphaned_count']} orphaned tasks")

# Find manually
orphaned = store.find_orphaned_tasks()
for task in orphaned:
    print(f"Task {task['task_id']} was running when app crashed")
```

**Recovery process:**
1. On startup, scan all task state files
2. Find tasks with status "running"
3. Mark as "failed" with reason "orphaned"
4. User can review and restart if needed

### Error context capture and retry suggestions

Failed commands provide actionable debugging information:

```python
# Get error details
error_context = manager.get_error_context(task_id)
print(error_context)
# {
#   "error_type": "timeout",
#   "error_message": "Command timed out after 3600 seconds",
#   "exit_code": null,
#   "relevant_output": ["last 20 lines of output"],
#   "timeout_used": 3600,
#   "memory_stats": {...},
#   "retry_suggestion": "increase_timeout"
# }

# Get suggested action
suggestion = manager.get_retry_suggestion(error_context["error_type"])
# Returns: "increase_timeout" | "add_memory" | "fix_syntax_or_compilation" |
#          "review_test_failures" | "check_network" | "fix_permissions" | "retry"
```

**Error classification:**
- `timeout` - Command exceeded timeout limit
- `memory` - Out of memory error detected
- `command_not_found` - Command or executable not found
- `permission_denied` - Permission or access error
- `network` - Network connectivity issue
- `build_error` - Compilation or syntax errors
- `test_failed` - Test failures detected
- `unknown` - Unclassified error

---

## Limitations & Constraints

- **Maximum timeout:** While configurable, extremely long timeouts (>8 hours) may encounter system limitations
- **Output buffering:** Very large output (>100MB) may cause memory pressure - use log files for extensive output
- **Platform differences:** Process termination behavior varies slightly between Windows and Unix systems
- **Concurrent tasks:** No hard limit, but system resources constrain practical concurrency (recommend <10 simultaneous tasks)
- **State storage:** Task state stored as JSON files - very high task counts (1000+) may impact disk I/O

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Command times out quickly | Default timeout too short for task | Increase `timeout` parameter (e.g., 7200 for 2 hours) |
| High memory usage | Memory-intensive command without monitoring | Install `psutil` for monitoring: `pip install psutil>=5.9.0` |
| Task stuck in "running" state | App crashed during execution | Restart app - auto-recovery marks orphaned tasks |
| Cannot cancel task | Process termination failed | Check task output for errors; force kill may be needed |
| Output not updating | Command produces no stdout | Check stderr or task logs; some commands are silent |
| State file corruption | App crash during write | Atomic writes prevent corruption - file won't exist if write failed |
| "Command not found" error | Command not in PATH or misspelled | Verify command exists: `which <command>` or `where <command>` |

---

## Related Features

- **Agent Session Management** - Tasks integrate with agent sessions for lifecycle tracking
- **Memory System (Graphiti)** - Task outcomes can be stored in memory for future reference
- **MCP Tool Registry** - Background task tools registered automatically for agent access
- **Security Sandbox** - Commands execute within security constraints for safety

---

## Technical Details

### Dependencies

- **asyncio** (Python stdlib) - Async subprocess execution and event loop management
- **psutil** (optional, ≥5.9.0) - Memory monitoring and process management
- **pathlib** (Python stdlib) - Cross-platform path handling
- **json** (Python stdlib) - State serialization
- **xterm.js** (Frontend) - Terminal-like output rendering in UI

### Integration Points

- **MCP Tool System** - Four tools registered: `start_background_command`, `get_task_status`, `get_task_output`, `cancel_task`
- **Frontend IPC** - Event-driven communication via Electron IPC channels
- **File System** - State persisted to `.auto-claude/specs/{spec-id}/.background_tasks/`
- **Process Management** - Uses asyncio subprocess with graceful termination (SIGTERM → SIGKILL)

### Security Considerations

**Command execution safety:**
- All commands execute within Auto Code's security sandbox
- Working directory restricted to project directory
- No shell injection vulnerabilities (uses `asyncio.create_subprocess_exec` with argument list, not shell)
- Process isolation prevents interference with other tasks

**State file security:**
- State files written atomically to prevent corruption
- Files stored in spec-specific directories (isolated per task/spec)
- No sensitive data in state files (commands/output only)

**Process cleanup:**
- Graceful termination (SIGTERM) attempted first
- Force kill (SIGKILL) after 5 seconds if needed
- Zombie process prevention with `wait()` calls
- Process handles closed properly on cleanup

### Performance

**Execution overhead:**
- Task startup: <100ms
- State persistence: <50ms per write (atomic)
- Memory monitoring: <10ms per check (every 5 lines)
- Output streaming: Real-time with <1s latency

**Scalability:**
- Tested with 10+ concurrent tasks
- Output buffering handles up to 100MB per task
- State files scale to 1000+ tasks per spec
- Memory footprint: ~5-10MB per active task

**Benchmarks:**
- 4-hour build task: No memory leaks detected
- 1000-line output: ~2s total streaming time
- State recovery: <100ms for 100 tasks
- Cancellation: <5s graceful termination

---

## Testing

### Unit Tests

```bash
# Run background task unit tests
cd apps/backend
pytest tests/ -v -k 'background_task'
```

### Integration Tests

```bash
# Run long-running command integration tests
cd apps/backend
pytest tests/integration/ -v -k 'long_running'
```

### E2E Tests

```bash
# Run comprehensive E2E test suite
pytest tests/e2e/test_long_running_commands.py -v

# Run specific test
pytest tests/e2e/test_long_running_commands.py::TestLongRunningCommands::test_long_timeout_configuration -v
```

**Test coverage:**
- 4+ hour timeout configuration ✅
- Task status lifecycle (pending → running → completed/failed/cancelled) ✅
- Real-time output streaming ✅
- State persistence and recovery ✅
- Cancellation and cleanup ✅
- Timeout handling ✅
- Memory monitoring ✅
- Error context capture ✅
- Orphaned task recovery ✅

### Manual Testing Checklist

- [ ] Start long-running command (e.g., `sleep 60`)
- [ ] Verify output streams in real-time
- [ ] Check status updates correctly
- [ ] Cancel task and verify cleanup
- [ ] Restart app during task and verify recovery
- [ ] Test timeout with short-timeout task
- [ ] Verify memory monitoring (if psutil installed)
- [ ] Test error scenarios (command not found, syntax error)
- [ ] Cross-platform verification (Windows, macOS, Linux)

---

## Roadmap

### Planned Enhancements

- [ ] Task prioritization and queue management
- [ ] Resource limits (CPU, memory caps) per task
- [ ] Task dependencies (wait for task X before starting Y)
- [ ] Output filtering and search
- [ ] Task templates for common operations
- [ ] Scheduled task execution
- [ ] Task history export (CSV, JSON)

### Known Issues

None at this time. See [GitHub Issues](https://github.com/your-org/auto-code/issues?q=is%3Aissue+is%3Aopen+label%3Along-running) for latest.

---

## References

- [Background Task Manager API](../api/backend-api.md#background-task-manager)
- [MCP Tools Documentation](../modules/backend-architecture.md#mcp-tools)
- [State Persistence Guide](../modules/backend-architecture.md#task-state-store)
- [Frontend Integration](../modules/frontend-architecture.md#task-progress-component)
- [E2E Testing Guide](../integration/e2e-testing.md)

---

## Changelog

### Version 2.9.0 - 2026-02-10
- Initial release of Long-Running Command Handler
- Support for 4+ hour command execution
- Real-time output streaming with xterm.js
- State persistence and crash recovery
- Memory monitoring with psutil integration
- Error classification and retry suggestions
- Graceful cancellation with cleanup
- Comprehensive E2E test suite

---

## Support

For questions or issues related to this feature:

- [GitHub Issues](https://github.com/your-org/auto-code/issues/new?template=feature-request.md)
- [Documentation](https://docs.auto-code.dev)
