# Agent Audit Integration Guide

## Overview

The agent base module (`agents/base.py`) provides built-in audit logging utilities for enterprise security and compliance. All agent operations can now be automatically logged with correlation IDs, timing, metadata, and token usage.

## Quick Start

### Using the Context Manager (Recommended)

The easiest way to add audit logging is using the `audit_agent_session()` context manager:

```python
from agents.base import audit_agent_session

async def run_my_agent(spec_dir, project_dir, subtask_id):
    """Run an agent with automatic audit logging."""

    with audit_agent_session(
        agent_type="coder",  # or "planner", "qa_reviewer", "qa_fixer"
        spec_dir=spec_dir,
        project_dir=project_dir,
        subtask_id=subtask_id,
        session_id="session-123",
    ) as ctx:
        # Your agent work happens here
        # Audit start is automatically logged

        # Update metadata during execution
        ctx.metadata["files_modified"] = 5
        ctx.metadata["commits_created"] = 2

        # If an exception occurs, audit failure is automatically logged
        # If execution completes, audit success is automatically logged
```

**What this logs:**
- `AGENT_CODER_STARTED` - When entering the context
- `AGENT_CODER_COMPLETED` - On successful completion
- `AGENT_CODER_FAILED` - On exception
- Automatic timing (duration_ms)
- All metadata passed and updated during execution

### Manual Logging

For more granular control, you can log individual actions:

```python
from agents.base import create_agent_audit_context, log_agent_action
from enterprise.audit import AuditAction

# Create audit context
ctx = create_agent_audit_context(
    agent_type="coder",
    spec_dir=spec_dir,
    project_dir=project_dir,
    subtask_id=subtask_id,
)

# Log specific actions
log_agent_action(
    context=ctx,
    action=AuditAction.CODE_GENERATED,
    result="success",
    details={"files_created": 3},
    token_usage={"input_tokens": 1000, "output_tokens": 2000},
)

log_agent_action(
    context=ctx,
    action=AuditAction.CODE_REVIEWED,
    result="success",
    details={"issues_found": 0},
)
```

## Supported Agent Types

The integration supports all agent types with specific audit actions:

| Agent Type | Start Action | Complete Action | Failed Action |
|------------|-------------|----------------|---------------|
| `planner` | `AGENT_PLANNER_STARTED` | `AGENT_PLANNER_COMPLETED` | `AGENT_PLANNER_FAILED` |
| `coder` | `AGENT_CODER_STARTED` | `AGENT_CODER_COMPLETED` | `AGENT_CODER_FAILED` |
| `qa_reviewer` | `AGENT_QA_REVIEWER_STARTED` | `AGENT_QA_REVIEWER_COMPLETED` | `AGENT_QA_REVIEWER_FAILED` |
| `qa_fixer` | `AGENT_QA_FIXER_STARTED` | `AGENT_QA_FIXER_COMPLETED` | `AGENT_QA_FIXER_FAILED` |

Unknown agent types default to generic `AGENT_SESSION_*` actions.

## Audit Log Location

Audit logs are stored in:
```
.auto-claude/enterprise/audit/audit_YYYY-MM-DD.jsonl
```

Each entry is a JSON line with:
- `timestamp` - ISO 8601 timestamp
- `correlation_id` - Unique operation ID (e.g., `ent-6865ac36da23`)
- `action` - The action performed (e.g., `agent_coder_started`)
- `actor_type` - Always `bot` for agents
- `actor_id` - Agent identifier (e.g., `agent_coder`)
- `spec_id` - Spec directory name
- `project_id` - Project directory name
- `result` - `started`, `success`, `failure`, `denied`, `skipped`
- `duration_ms` - Operation duration in milliseconds
- `details` - Custom metadata dictionary
- `token_usage` - AI token usage (input_tokens, output_tokens)

## Compliance Features

- **90-day retention** - Logs retained for compliance requirements
- **Automatic rotation** - Files rotate at 100MB
- **Correlation IDs** - Track operations across multiple log entries
- **Immutable logs** - Append-only JSONL format
- **No PII by default** - Only technical metadata logged

## Integration with Session Management

The audit hooks are designed to integrate seamlessly with `agents/session.py`:

```python
from agents.base import audit_agent_session
from agents.session import run_agent_session

async def run_agent_with_audit(client, message, spec_dir, project_dir, subtask_id):
    """Run agent session with audit logging."""

    with audit_agent_session(
        agent_type="coder",
        spec_dir=spec_dir,
        project_dir=project_dir,
        subtask_id=subtask_id,
    ) as ctx:
        # Run the agent session
        status, response, usage = await run_agent_session(
            client=client,
            message=message,
            spec_dir=spec_dir,
        )

        # Track token usage in audit
        if usage:
            ctx.metadata["token_usage"] = usage

        # Track completion status
        ctx.metadata["status"] = status
        ctx.metadata["response_length"] = len(response)

        return status, response, usage
```

## API Reference

### `get_audit_logger() -> EnterpriseAuditLogger`

Get the singleton audit logger instance.

### `create_agent_audit_context(...) -> AuditContext`

Create an audit context for agent operations.

**Parameters:**
- `agent_type` (str): Agent type (planner, coder, qa_reviewer, qa_fixer)
- `spec_dir` (Path, optional): Spec directory path
- `project_dir` (Path, optional): Project directory path
- `subtask_id` (str, optional): Current subtask ID
- `session_id` (str, optional): Session identifier
- `user_email` (str, optional): User's email address
- `user_role` (str, optional): User's role
- `metadata` (dict, optional): Additional context metadata

**Returns:** `AuditContext` for use with `log_agent_action()`

### `audit_agent_session(...) -> ContextManager[AuditContext]`

Context manager for auditing an agent session. Automatically logs start, completion, and failure.

**Parameters:** Same as `create_agent_audit_context()`

**Yields:** `AuditContext` with mutable `metadata` dict

### `log_agent_action(context, action, ...)`

Log an agent action to the audit log.

**Parameters:**
- `context` (AuditContext): Audit context from `create_agent_audit_context()`
- `action` (AuditAction): The action being logged
- `result` (str): Result status (success, failure, denied, skipped)
- `error` (str, optional): Error message if failed
- `details` (dict, optional): Additional details
- `token_usage` (dict, optional): Token usage (input_tokens, output_tokens)

## Testing

To verify audit integration:

```python
from pathlib import Path
from agents.base import audit_agent_session

# Create a test session
spec_dir = Path('.auto-claude/specs/my-spec')
project_dir = Path('.')

with audit_agent_session(
    agent_type='coder',
    spec_dir=spec_dir,
    project_dir=project_dir,
    subtask_id='test-subtask',
) as ctx:
    ctx.metadata['test'] = 'verification'

# Check logs at .auto-claude/enterprise/audit/audit_YYYY-MM-DD.jsonl
```

## Related Files

- `apps/backend/agents/base.py` - Audit integration implementation
- `apps/backend/enterprise/audit.py` - Enterprise audit logger
- `apps/backend/agents/session.py` - Agent session management
