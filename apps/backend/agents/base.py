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
from enterprise.permissions import (
    Permission,
    PermissionDeniedError,
    Role,
    check_permission,
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


# ============================================================================
# Permission Controls Integration
# ============================================================================


def get_agent_permission(agent_type: str) -> Permission:
    """
    Map agent type to required permission.

    Args:
        agent_type: Type of agent (planner, coder, qa_reviewer, qa_fixer)

    Returns:
        Permission enum value for the agent type

    Raises:
        ValueError: If agent type is unknown
    """
    permission_map = {
        "planner": Permission.AGENT_PLANNER_RUN,
        "coder": Permission.AGENT_CODER_RUN,
        "qa_reviewer": Permission.AGENT_QA_RUN,
        "qa_fixer": Permission.AGENT_QA_RUN,
    }

    if agent_type not in permission_map:
        raise ValueError(f"Unknown agent type: {agent_type}")

    return permission_map[agent_type]


def check_agent_permission(
    agent_type: str,
    user_role: str | Role | None,
    context: AuditContext,
    user_id: str | None = None,
    raise_on_deny: bool = True,
) -> bool:
    """
    Check if user has permission to run an agent and log the result.

    Args:
        agent_type: Type of agent (planner, coder, qa_reviewer, qa_fixer)
        user_role: User's role (Role enum or string like "admin", "developer")
        context: Audit context for logging
        user_id: User identifier for audit logging
        raise_on_deny: If True, raise PermissionDeniedError on denial

    Returns:
        True if permission granted, False otherwise

    Raises:
        PermissionDeniedError: If permission denied and raise_on_deny=True
    """
    # If no role provided, assume ADMIN for backward compatibility
    if user_role is None:
        logger.info("No user role provided, assuming ADMIN for backward compatibility")
        user_role = Role.ADMIN

    # Convert string to Role enum if needed
    if isinstance(user_role, str):
        try:
            user_role = Role(user_role)
        except ValueError:
            logger.error(f"Invalid role: {user_role}")
            # Log the permission denial
            audit = get_audit_logger()
            audit.log_permission_check(
                context=context,
                allowed=False,
                permission=f"agent_{agent_type}_run",
                resource_type="agent",
                resource_id=agent_type,
                reason=f"Invalid role: {user_role}",
            )
            if raise_on_deny:
                raise PermissionDeniedError(
                    f"Invalid role: {user_role}",
                    role=None,
                    permission=None,
                )
            return False

    # Get required permission for agent type
    try:
        required_permission = get_agent_permission(agent_type)
    except ValueError as e:
        logger.error(f"Failed to get permission for agent type {agent_type}: {e}")
        audit = get_audit_logger()
        audit.log_permission_check(
            context=context,
            allowed=False,
            permission="unknown",
            resource_type="agent",
            resource_id=agent_type,
            reason=str(e),
        )
        if raise_on_deny:
            raise PermissionDeniedError(
                f"Unknown agent type: {agent_type}",
                role=user_role,
                permission=None,
            )
        return False

    # Check permission
    is_allowed, reason = check_permission(
        role=user_role,
        permission=required_permission,
        user_id=user_id or context.user_email,
        resource=f"agent:{agent_type}",
    )

    # Log permission check to audit trail
    audit = get_audit_logger()
    audit.log_permission_check(
        context=context,
        allowed=is_allowed,
        permission=required_permission.value,
        resource_type="agent",
        resource_id=agent_type,
        reason=reason,
    )

    # Raise exception if denied and raise_on_deny=True
    if not is_allowed and raise_on_deny:
        raise PermissionDeniedError(
            f"Permission denied: {reason}",
            role=user_role,
            permission=required_permission,
        )

    return is_allowed


@contextmanager
def audit_agent_session_with_permissions(
    agent_type: str,
    user_role: str | Role | None = None,
    spec_dir: Path | None = None,
    project_dir: Path | None = None,
    subtask_id: str | None = None,
    session_id: str | None = None,
    user_email: str | None = None,
    user_id: str | None = None,
    metadata: dict[str, Any] | None = None,
):
    """
    Context manager for auditing an agent session with permission checking.

    This combines permission checking with audit logging for agent operations.
    Permission is checked before the session starts, and the check is logged
    to the audit trail.

    Usage:
        with audit_agent_session_with_permissions(
            agent_type="coder",
            user_role="developer",
            spec_dir=spec_dir,
            project_dir=project_dir,
            subtask_id="subtask-1-1",
            session_id="session-123",
            user_email="user@example.com",
        ) as ctx:
            # Agent work happens here
            # Permission was already checked and logged
            ctx.metadata["commits_created"] = 2
            ctx.metadata["files_modified"] = 5

    Args:
        agent_type: Type of agent (planner, coder, qa_reviewer, qa_fixer)
        user_role: User's role (admin, developer, viewer, etc.)
        spec_dir: Spec directory path
        project_dir: Project directory path
        subtask_id: Current subtask ID
        session_id: Session identifier
        user_email: User's email address
        user_id: User identifier (defaults to user_email)
        metadata: Additional context metadata

    Yields:
        AuditContext with metadata that can be updated during execution

    Raises:
        PermissionDeniedError: If user doesn't have permission to run the agent
    """
    # If user_role is provided as string in metadata, use it
    if user_role is None and metadata and "user_role" in metadata:
        user_role = metadata["user_role"]

    # Create audit context first (needed for permission check logging)
    audit = get_audit_logger()
    context = create_agent_audit_context(
        agent_type=agent_type,
        spec_dir=spec_dir,
        project_dir=project_dir,
        subtask_id=subtask_id,
        session_id=session_id,
        user_email=user_email,
        user_role=user_role.value if isinstance(user_role, Role) else user_role,
        metadata=metadata,
    )

    # Check permission before starting agent session (raises on deny)
    check_agent_permission(
        agent_type=agent_type,
        user_role=user_role,
        context=context,
        user_id=user_id or user_email,
        raise_on_deny=True,
    )

    # Permission granted, proceed with agent session
    with audit_agent_session(
        agent_type=agent_type,
        spec_dir=spec_dir,
        project_dir=project_dir,
        subtask_id=subtask_id,
        session_id=session_id,
        user_email=user_email,
        user_role=user_role.value if isinstance(user_role, Role) else user_role,
        metadata=metadata,
    ) as ctx:
        yield ctx
