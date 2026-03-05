# Agents API Reference

Complete reference for Auto Code's agent system, including core implementation agents, QA validation agents, and specialized agent modules.

## Overview

Auto Code uses a multi-agent architecture to implement features through coordinated AI sessions. Each agent has a specific role in the build pipeline, from planning to implementation to quality assurance.

**Agent Pipeline:**
1. **Planner Agent** - Creates implementation plan with subtasks
2. **Coder Agent** - Implements individual subtasks (can spawn subagents)
3. **QA Reviewer Agent** - Validates acceptance criteria
4. **QA Fixer Agent** - Fixes QA-reported issues

**Key Features:**
- Agent-specific tool permissions and security controls
- Session management with recovery and retry logic
- Memory integration with Graphiti for cross-session context
- Plugin system for lifecycle hooks
- Enterprise audit logging for compliance

---

## Core Agent Infrastructure

### Base Module

Shared imports, types, and constants used across all agent modules.

::: apps.backend.agents.base
    options:
      show_root_heading: true
      show_source: false
      members:
        - get_audit_logger
        - create_agent_audit_context
        - audit_agent_session

---

## Core Implementation Agents

### Planner Agent

Creates implementation plans with subtasks and phases. Also handles follow-up planning for adding new work to completed specs.

::: apps.backend.agents.planner
    options:
      show_root_heading: true
      show_source: false
      members:
        - create_planner_session
        - run_followup_planner

**Usage Example:**
```python
from pathlib import Path
from agents.planner import create_planner_session

# Create planner session
session = create_planner_session(
    project_dir=Path("/path/to/project"),
    spec_dir=Path(".auto-claude/specs/001-feature"),
    model="claude-sonnet-4-5-20250929",
    max_thinking_tokens=10000
)

# Run planning
response = await session.run("Create implementation plan")
```

---

### Coder Agent

Main autonomous agent loop that implements individual subtasks. Handles file validation, pattern detection, and can spawn subagents for parallel work.

#### Key Features

- **Subtask Implementation**: Executes individual subtasks from the implementation plan
- **Recovery Management**: Automatic retry logic with exponential backoff
- **Subagent Spawning**: Can create isolated subagents for parallel work
- **Memory Integration**: Uses Graphiti for pattern suggestions and context
- **Model Fallback**: Falls back through model chain on failures
- **Token Tracking**: Monitors context window usage

::: apps.backend.agents.coder
    options:
      show_root_heading: true
      show_source: false
      members:
        - run_autonomous_agent
        - create_coder_session

**Usage Example:**
```python
from pathlib import Path
from agents.coder import run_autonomous_agent

# Run coder agent
success = await run_autonomous_agent(
    project_dir=Path("/path/to/project"),
    spec_dir=Path(".auto-claude/specs/001-feature"),
    model="claude-sonnet-4-5-20250929",
    max_iterations=10,
    verbose=True,
    auto_continue=False,
    skip_qa=False
)
```

---

## QA Validation Agents

### QA System Overview

The QA validation system uses two specialized agents in a review-fix loop:

1. **QA Reviewer Agent** - Validates implementation against acceptance criteria
2. **QA Fixer Agent** - Fixes issues reported by the reviewer

**Modules:**
- `qa/loop.py` - Main QA orchestration loop
- `qa/reviewer.py` - QA reviewer agent session
- `qa/fixer.py` - QA fixer agent session
- `qa/report.py` - Issue tracking, reporting, escalation
- `qa/criteria.py` - Acceptance criteria and status management

::: apps.backend.qa
    options:
      show_root_heading: true
      show_source: false
      members:
        - run_qa_validation_loop
        - is_qa_approved
        - is_qa_rejected
        - get_qa_iteration_count
        - should_run_qa
        - has_recurring_issues
        - get_recurring_issue_summary
        - escalate_to_human
        - is_no_test_project
        - check_test_discovery
        - create_manual_test_plan

**Usage Example:**
```python
from pathlib import Path
from qa import run_qa_validation_loop, is_qa_approved

# Run QA validation
success = await run_qa_validation_loop(
    project_dir=Path("/path/to/project"),
    spec_dir=Path(".auto-claude/specs/001-feature"),
    model="claude-sonnet-4-5-20250929",
    verbose=True
)

# Check if approved
if is_qa_approved(Path(".auto-claude/specs/001-feature")):
    print("QA approved!")
```

---

## Specialized Agent Modules

### Memory Manager

Manages session memory and context using Graphiti integration.

::: apps.backend.agents.memory_manager
    options:
      show_root_heading: true
      show_source: false
      members:
        - get_graphiti_context
        - get_pattern_suggestions
        - debug_memory_system_status

---

### Test Generator

Generates unit and integration tests for implementations.

::: apps.backend.agents.test_generator
    options:
      show_root_heading: true
      show_source: false

---

### Documentation Generator

Generates API documentation and code comments.

::: apps.backend.agents.documentation_generator
    options:
      show_root_heading: true
      show_source: false

---

### Security Auditor

Scans code for security vulnerabilities and compliance issues.

::: apps.backend.agents.security_auditor
    options:
      show_root_heading: true
      show_source: false

---

### Migration Assistant

Assists with code migrations and refactoring.

::: apps.backend.agents.migration_assistant
    options:
      show_root_heading: true
      show_source: false

---

### Performance Profiler

Analyzes code performance and suggests optimizations.

::: apps.backend.agents.performance_profiler
    options:
      show_root_heading: true
      show_source: false

---

## Session Management

### Agent Session

Core session management for all agents.

::: apps.backend.agents.session
    options:
      show_root_heading: true
      show_source: false
      members:
        - run_agent_session
        - run_agent_session_isolated
        - save_token_stats
        - post_session_processing

---

## Agent Utilities

### Decision Tracking

Tracks architectural and implementation decisions.

::: apps.backend.agents.decision_tracker
    options:
      show_root_heading: true
      show_source: false
      members:
        - track_decision
        - get_decision_history

---

### Agent Subprocess

Manages subagent execution in isolated processes.

::: apps.backend.agents.agent_subprocess
    options:
      show_root_heading: true
      show_source: false
      members:
        - spawn_subagent

---

### Agent Utils

General utility functions for agents.

::: apps.backend.agents.utils
    options:
      show_root_heading: true
      show_source: false

---

## Plugin System Integration

Agents support plugin lifecycle hooks for extensibility.

**Available Hooks:**
- `before_agent_session` - Called before agent session starts
- `after_agent_session` - Called after agent session completes
- `on_agent_error` - Called when agent encounters error
- `on_subtask_complete` - Called when subtask is completed
- `on_build_complete` - Called when build completes

**Usage Example:**
```python
from plugins.registry import PluginRegistry
from plugins.sdk.agent import AgentContext

registry = PluginRegistry.get_instance()

# Before agent session
context = AgentContext(
    agent_type="coder",
    spec_dir=spec_dir,
    project_dir=project_dir,
    subtask_id="subtask-1-1"
)
registry.trigger_before_agent_session(context)

# Run agent session
# ...

# After agent session
registry.trigger_after_agent_session(context, success=True)
```

---

## Environment Variables

### Agent Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `AUTO_BUILD_MODEL` | Override default model | `claude-sonnet-4-5-20250929` |
| `MAX_THINKING_TOKENS` | Extended thinking budget | None (provider default) |
| `AUTO_CONTINUE` | Non-interactive mode | `false` |
| `DEBUG` | Enable debug output | `false` |
| `USER_ROLE` | User role for permissions | `developer` |

### Memory Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `GRAPHITI_ENABLED` | Enable Graphiti memory | `true` |
| `ANTHROPIC_API_KEY` | API key for Graphiti LLM | Required if enabled |

### QA Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `MAX_QA_ITERATIONS` | Maximum QA cycles | `5` |
| `RECURRING_ISSUE_THRESHOLD` | Escalation threshold | `3` |
| `SKIP_QA` | Skip automatic QA | `false` |

---

## Error Handling

### Common Agent Errors

**Rate Limit Exceeded:**
```
Error: API rate limit exceeded
```
**Solution:** Agent automatically creates `RATE_LIMIT_PAUSE` file and waits for reset time.

**Authentication Failed:**
```
Error: Authentication failed
```
**Solution:** Agent creates `AUTH_PAUSE` file. Frontend should prompt for re-authentication and create `RESUME` file.

**Subtask Stuck:**
```
Error: Subtask exceeded maximum retries
```
**Solution:** Agent marks subtask as stuck and notifies via Linear/notifications. Recovery manager suggests recovery actions.

**Context Window Exceeded:**
```
Error: Context window limit exceeded
```
**Solution:** Agent falls back through model chain (Sonnet 4.5 → Opus 4 → Sonnet 4) to find model with larger context.

---

## Best Practices

### Agent Development

1. **Always use audit logging** for enterprise compliance:
   ```python
   with audit_agent_session(agent_type="coder", spec_dir=spec_dir) as ctx:
       # Agent work
       ctx.metadata["files_modified"] = 5
   ```

2. **Check permissions** before sensitive operations:
   ```python
   check_agent_permission(Permission.SPEC_DELETE, user_role="viewer")
   ```

3. **Use memory system** for cross-session context:
   ```python
   context = get_graphiti_context(spec_dir, project_dir, task)
   ```

4. **Handle retries gracefully** with exponential backoff:
   ```python
   for attempt in range(MAX_SUBTASK_RETRIES):
       try:
           result = await run_subtask()
           break
       except RetryableError:
           await asyncio.sleep(2 ** attempt)
   ```

5. **Track decisions** for transparency:
   ```python
   track_decision(
       spec_dir,
       decision_type="technical",
       decision="Use React hooks instead of class components",
       rationale="Hooks provide better state management and are modern standard"
   )
   ```

### Session Management

1. **Always save token stats** for cost tracking:
   ```python
   save_token_stats(spec_dir, "coder", session_result["token_usage"])
   ```

2. **Run post-session processing** to update memory:
   ```python
   await post_session_processing(spec_dir, project_dir, "coder", result)
   ```

3. **Use isolated sessions** for subagents:
   ```python
   result = await run_agent_session_isolated(session, message, timeout=3600)
   ```

---

## See Also

- [Backend API Reference](./backend-api.md) - Core module documentation
- [Web Backend API](./web-backend-api.md) - FastAPI endpoints reference
- [Memory System Diagram](../diagrams/memory-system.mermaid) - Graphiti architecture
- [Agent Pipeline Diagram](../diagrams/agent-pipeline.mermaid) - Build workflow
- [Security Model Diagram](../diagrams/security-model.mermaid) - Security architecture

---

**Version:** 2.8.0
**Last Updated:** 2026-03-05
**Maintained By:** Auto Code Team
