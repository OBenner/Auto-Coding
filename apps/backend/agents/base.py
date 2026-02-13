"""
Base Module for Agent System
=============================

Shared imports, types, and constants used across agent modules.
Includes audit logging integration for enterprise security and compliance.
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from enterprise.audit import (
    ActorType,
    AuditAction,
    AuditContext,
    EnterpriseAuditLogger,
)

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
AUTO_CONTINUE_DELAY_SECONDS = 3
HUMAN_INTERVENTION_FILE = "PAUSE"


# ============================================================================
# Enterprise Audit Integration
# ============================================================================


def get_audit_logger() -> EnterpriseAuditLogger:
    """
    Get the singleton audit logger instance.

    Returns:
        EnterpriseAuditLogger instance
    """
    return EnterpriseAuditLogger.get_instance()


def create_agent_audit_context(
    agent_type: str,
    spec_dir: Path | None = None,
    project_dir: Path | None = None,
    subtask_id: str | None = None,
    session_id: str | None = None,
    user_email: str | None = None,
    user_role: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditContext:
    """
    Create an audit context for agent operations.

    Args:
        agent_type: Type of agent (planner, coder, qa_reviewer, qa_fixer)
        spec_dir: Spec directory path
        project_dir: Project directory path
        subtask_id: Current subtask ID
        session_id: Session identifier
        user_email: User's email address
        user_role: User's role (admin, developer, viewer, etc.)
        metadata: Additional context metadata

    Returns:
        AuditContext for logging agent actions
    """
    audit = get_audit_logger()

    # Extract spec_id from spec_dir if provided
    spec_id = spec_dir.name if spec_dir else None

    # Extract project_id from project_dir if provided
    project_id = project_dir.name if project_dir else None

    return audit.start_operation(
        actor_type=ActorType.BOT,
        actor_id=f"agent_{agent_type}",
        user_email=user_email,
        user_role=user_role,
        project_id=project_id,
        spec_id=spec_id,
        session_id=session_id,
        metadata=metadata or {"agent_type": agent_type, "subtask_id": subtask_id},
    )


@contextmanager
def audit_agent_session(
    agent_type: str,
    spec_dir: Path | None = None,
    project_dir: Path | None = None,
    subtask_id: str | None = None,
    session_id: str | None = None,
    user_email: str | None = None,
    user_role: str | None = None,
    metadata: dict[str, Any] | None = None,
):
    """
    Context manager for auditing an agent session.

    Automatically logs agent start, completion, and failure with timing.

    Usage:
        with audit_agent_session(
            agent_type="coder",
            spec_dir=spec_dir,
            project_dir=project_dir,
            subtask_id="subtask-1-1",
            session_id="session-123",
        ) as ctx:
            # Agent work happens here
            ctx.metadata["commits_created"] = 2
            ctx.metadata["files_modified"] = 5

    Args:
        agent_type: Type of agent (planner, coder, qa_reviewer, qa_fixer)
        spec_dir: Spec directory path
        project_dir: Project directory path
        subtask_id: Current subtask ID
        session_id: Session identifier
        user_email: User's email address
        user_role: User's role
        metadata: Additional context metadata

    Yields:
        AuditContext with metadata that can be updated during execution
    """
    # Map agent type to audit actions
    action_map = {
        "planner": (
            AuditAction.AGENT_PLANNER_STARTED,
            AuditAction.AGENT_PLANNER_COMPLETED,
            AuditAction.AGENT_PLANNER_FAILED,
        ),
        "coder": (
            AuditAction.AGENT_CODER_STARTED,
            AuditAction.AGENT_CODER_COMPLETED,
            AuditAction.AGENT_CODER_FAILED,
        ),
        "qa_reviewer": (
            AuditAction.AGENT_QA_REVIEWER_STARTED,
            AuditAction.AGENT_QA_REVIEWER_COMPLETED,
            AuditAction.AGENT_QA_REVIEWER_FAILED,
        ),
        "qa_fixer": (
            AuditAction.AGENT_QA_FIXER_STARTED,
            AuditAction.AGENT_QA_FIXER_COMPLETED,
            AuditAction.AGENT_QA_FIXER_FAILED,
        ),
    }

    # Default to generic agent session actions if agent type not mapped
    action_start, action_complete, action_failed = action_map.get(
        agent_type,
        (
            AuditAction.AGENT_SESSION_STARTED,
            AuditAction.AGENT_SESSION_COMPLETED,
            AuditAction.AGENT_SESSION_FAILED,
        ),
    )

    audit = get_audit_logger()

    with audit.operation(
        action_start=action_start,
        action_complete=action_complete,
        action_failed=action_failed,
        actor_type=ActorType.BOT,
        actor_id=f"agent_{agent_type}",
        user_email=user_email,
        user_role=user_role,
        project_id=project_dir.name if project_dir else None,
        spec_id=spec_dir.name if spec_dir else None,
        metadata=metadata or {"agent_type": agent_type, "subtask_id": subtask_id},
    ) as ctx:
        yield ctx


def log_agent_action(
    context: AuditContext,
    action: AuditAction,
    result: str = "success",
    error: str | None = None,
    details: dict[str, Any] | None = None,
    token_usage: dict[str, int] | None = None,
) -> None:
    """
    Log an agent action to the audit log.

    Args:
        context: Audit context from create_agent_audit_context()
        action: The action being logged
        result: Result status (success, failure, denied, skipped)
        error: Error message if failed
        details: Additional details about the action
        token_usage: Token usage if AI-related (input_tokens, output_tokens)
    """
    audit = get_audit_logger()
    audit.log(
        context=context,
        action=action,
        result=result,
        error=error,
        details=details,
        token_usage=token_usage,
    )
