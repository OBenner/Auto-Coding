"""
Enterprise Audit Logger
=======================

Structured audit logging for enterprise security and compliance.
Extends the GitHub audit pattern with enterprise-specific features.

Features:
- JSON-formatted structured logs
- Correlation ID generation per operation
- Actor tracking (user/bot/automation/admin)
- SSO/SAML authentication tracking
- Data residency compliance monitoring
- RBAC permission auditing
- Compliance reporting (SOC2, GDPR, HIPAA)
- Duration and token usage tracking
- Log rotation with configurable retention
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Configure module logger
logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Types of auditable actions in enterprise context."""

    # Authentication & SSO actions
    SSO_LOGIN_STARTED = "sso_login_started"
    SSO_LOGIN_COMPLETED = "sso_login_completed"
    SSO_LOGIN_FAILED = "sso_login_failed"
    SAML_ASSERTION_VERIFIED = "saml_assertion_verified"
    SAML_ASSERTION_REJECTED = "saml_assertion_rejected"
    TOKEN_ISSUED = "token_issued"
    TOKEN_REFRESHED = "token_refreshed"
    TOKEN_REVOKED = "token_revoked"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    LOGOUT = "logout"

    # Data Residency & Compliance actions
    DATA_RESIDENCY_VALIDATED = "data_residency_validated"
    DATA_RESIDENCY_VIOLATION = "data_residency_violation"
    DATA_TRANSFER_REQUESTED = "data_transfer_requested"
    DATA_TRANSFER_APPROVED = "data_transfer_approved"
    DATA_TRANSFER_DENIED = "data_transfer_denied"
    DATA_DELETION_REQUESTED = "data_deletion_requested"
    DATA_DELETION_COMPLETED = "data_deletion_completed"
    DATA_EXPORT_REQUESTED = "data_export_requested"
    DATA_EXPORT_COMPLETED = "data_export_completed"

    # RBAC & Permission actions
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    PERMISSION_CHECKED = "permission_checked"
    POLICY_EVALUATED = "policy_evaluated"
    ACCESS_APPROVED = "access_approved"
    ACCESS_DENIED = "access_denied"

    # Agent & Build actions
    AGENT_SESSION_STARTED = "agent_session_started"
    AGENT_SESSION_COMPLETED = "agent_session_completed"
    AGENT_SESSION_FAILED = "agent_session_failed"
    BUILD_STARTED = "build_started"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"
    CODE_GENERATED = "code_generated"
    CODE_REVIEWED = "code_reviewed"
    CODE_DEPLOYED = "code_deployed"

    # API & External Service actions
    API_CALL_MADE = "api_call_made"
    API_CALL_FAILED = "api_call_failed"
    API_RATE_LIMIT_WARNING = "api_rate_limit_warning"
    API_RATE_LIMIT_EXCEEDED = "api_rate_limit_exceeded"
    EXTERNAL_SERVICE_CALL = "external_service_call"
    EXTERNAL_SERVICE_ERROR = "external_service_error"

    # Security & Monitoring actions
    SECURITY_SCAN_STARTED = "security_scan_started"
    SECURITY_SCAN_COMPLETED = "security_scan_completed"
    VULNERABILITY_DETECTED = "vulnerability_detected"
    SECURITY_POLICY_VIOLATED = "security_policy_violated"
    ANOMALY_DETECTED = "anomaly_detected"
    THREAT_BLOCKED = "threat_blocked"

    # Compliance Reporting actions
    COMPLIANCE_REPORT_GENERATED = "compliance_report_generated"
    COMPLIANCE_REPORT_EXPORTED = "compliance_report_exported"
    AUDIT_LOG_ACCESSED = "audit_log_accessed"
    AUDIT_LOG_EXPORTED = "audit_log_exported"
    RETENTION_POLICY_APPLIED = "retention_policy_applied"

    # Configuration & Admin actions
    CONFIG_UPDATED = "config_updated"
    FEATURE_FLAG_TOGGLED = "feature_flag_toggled"
    ADMIN_ACTION = "admin_action"
    SYSTEM_MAINTENANCE = "system_maintenance"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"


class ActorType(str, Enum):
    """Types of actors that can trigger actions."""

    USER = "user"
    ADMIN = "admin"
    BOT = "bot"
    AUTOMATION = "automation"
    SYSTEM = "system"
    WEBHOOK = "webhook"
    SERVICE_ACCOUNT = "service_account"


@dataclass
class AuditContext:
    """Context for an auditable operation."""

    correlation_id: str
    actor_type: ActorType
    actor_id: str | None = None
    user_email: str | None = None
    user_role: str | None = None
    organization_id: str | None = None
    project_id: str | None = None
    spec_id: str | None = None
    session_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    data_region: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "actor_type": self.actor_type.value,
            "actor_id": self.actor_id,
            "user_email": self.user_email,
            "user_role": self.user_role,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "spec_id": self.spec_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "data_region": self.data_region,
            "started_at": self.started_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class AuditEntry:
    """A single audit log entry."""

    timestamp: datetime
    correlation_id: str
    action: AuditAction
    actor_type: ActorType
    actor_id: str | None
    user_email: str | None
    user_role: str | None
    organization_id: str | None
    project_id: str | None
    spec_id: str | None
    session_id: str | None
    ip_address: str | None
    data_region: str | None
    result: str  # success, failure, denied, skipped
    duration_ms: int | None
    error: str | None
    details: dict[str, Any]
    token_usage: dict[str, int] | None  # input_tokens, output_tokens
    security_context: dict[str, Any] | None  # Additional security metadata

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "action": self.action.value,
            "actor_type": self.actor_type.value,
            "actor_id": self.actor_id,
            "user_email": self.user_email,
            "user_role": self.user_role,
            "organization_id": self.organization_id,
            "project_id": self.project_id,
            "spec_id": self.spec_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "data_region": self.data_region,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "details": self.details,
            "token_usage": self.token_usage,
            "security_context": self.security_context,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class EnterpriseAuditLogger:
    """
    Structured audit logger for enterprise security and compliance.

    Usage:
        audit = EnterpriseAuditLogger(log_dir=Path(".auto-claude/enterprise/audit"))

        # Start an operation with context
        ctx = audit.start_operation(
            actor_type=ActorType.USER,
            actor_id="user123",
            user_email="user@example.com",
            user_role="developer",
            organization_id="org-456",
            project_id="proj-789",
        )

        # Log events during the operation
        audit.log(ctx, AuditAction.AGENT_SESSION_STARTED)

        # ... do work ...

        # Log completion with details
        audit.log(
            ctx,
            AuditAction.AGENT_SESSION_COMPLETED,
            result="success",
            details={"subtasks_completed": 5},
        )
    """

    _instance: EnterpriseAuditLogger | None = None

    def __init__(
        self,
        log_dir: Path | None = None,
        retention_days: int = 90,  # Longer retention for compliance
        max_file_size_mb: int = 100,
        enabled: bool = True,
    ):
        """
        Initialize enterprise audit logger.

        Args:
            log_dir: Directory for audit logs (default: .auto-claude/enterprise/audit)
            retention_days: Days to retain logs (default: 90 for compliance)
            max_file_size_mb: Max size per log file before rotation (default: 100MB)
            enabled: Whether audit logging is enabled (default: True)
        """
        self.log_dir = log_dir or Path(".auto-claude/enterprise/audit")
        self.retention_days = retention_days
        self.max_file_size_mb = max_file_size_mb
        self.enabled = enabled

        if enabled:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._current_log_file: Path | None = None
            self._rotate_if_needed()

    @classmethod
    def get_instance(
        cls,
        log_dir: Path | None = None,
        **kwargs,
    ) -> EnterpriseAuditLogger:
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(log_dir=log_dir, **kwargs)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def _get_log_file_path(self) -> Path:
        """Get path for current day's log file."""
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        return self.log_dir / f"audit_{date_str}.jsonl"

    def _rotate_if_needed(self) -> None:
        """Rotate log file if it exceeds max size."""
        if not self.enabled:
            return

        log_file = self._get_log_file_path()

        if log_file.exists():
            size_mb = log_file.stat().st_size / (1024 * 1024)
            if size_mb >= self.max_file_size_mb:
                # Rotate: add timestamp suffix
                timestamp = datetime.now(UTC).strftime("%H%M%S")
                rotated = log_file.with_suffix(f".{timestamp}.jsonl")
                log_file.rename(rotated)
                logger.info(f"Rotated audit log to {rotated}")

        self._current_log_file = log_file

    def _cleanup_old_logs(self) -> None:
        """Remove logs older than retention period."""
        if not self.enabled or not self.log_dir.exists():
            return

        cutoff = datetime.now(UTC).timestamp() - (self.retention_days * 24 * 60 * 60)

        for log_file in self.log_dir.glob("audit_*.jsonl"):
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
                logger.info(f"Deleted old audit log: {log_file}")

    def generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for an operation."""
        return f"ent-{uuid.uuid4().hex[:12]}"

    def start_operation(
        self,
        actor_type: ActorType,
        actor_id: str | None = None,
        user_email: str | None = None,
        user_role: str | None = None,
        organization_id: str | None = None,
        project_id: str | None = None,
        spec_id: str | None = None,
        session_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        data_region: str | None = None,
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditContext:
        """
        Start a new auditable operation.

        Args:
            actor_type: Type of actor (USER, ADMIN, BOT, AUTOMATION, SYSTEM)
            actor_id: Identifier for the actor
            user_email: User's email address
            user_role: User's role (admin, developer, viewer, etc.)
            organization_id: Organization identifier
            project_id: Project identifier
            spec_id: Spec identifier
            session_id: Session identifier
            ip_address: IP address of the actor
            user_agent: User agent string
            data_region: Data region (EU, US, etc.)
            correlation_id: Optional existing correlation ID
            metadata: Additional context metadata

        Returns:
            AuditContext for use with log() calls
        """
        return AuditContext(
            correlation_id=correlation_id or self.generate_correlation_id(),
            actor_type=actor_type,
            actor_id=actor_id,
            user_email=user_email,
            user_role=user_role,
            organization_id=organization_id,
            project_id=project_id,
            spec_id=spec_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            data_region=data_region,
            metadata=metadata or {},
        )

    def log(
        self,
        context: AuditContext,
        action: AuditAction,
        result: str = "success",
        error: str | None = None,
        details: dict[str, Any] | None = None,
        token_usage: dict[str, int] | None = None,
        security_context: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> AuditEntry:
        """
        Log an audit event.

        Args:
            context: Audit context from start_operation()
            action: The action being logged
            result: Result status (success, failure, denied, skipped)
            error: Error message if failed
            details: Additional details about the action
            token_usage: Token usage if AI-related (input_tokens, output_tokens)
            security_context: Additional security metadata
            duration_ms: Duration in milliseconds if timed

        Returns:
            The created AuditEntry
        """
        # Calculate duration from context start if not provided
        if duration_ms is None and context.started_at:
            elapsed = datetime.now(UTC) - context.started_at
            duration_ms = int(elapsed.total_seconds() * 1000)

        entry = AuditEntry(
            timestamp=datetime.now(UTC),
            correlation_id=context.correlation_id,
            action=action,
            actor_type=context.actor_type,
            actor_id=context.actor_id,
            user_email=context.user_email,
            user_role=context.user_role,
            organization_id=context.organization_id,
            project_id=context.project_id,
            spec_id=context.spec_id,
            session_id=context.session_id,
            ip_address=context.ip_address,
            data_region=context.data_region,
            result=result,
            duration_ms=duration_ms,
            error=error,
            details=details or {},
            token_usage=token_usage,
            security_context=security_context,
        )

        self._write_entry(entry)
        return entry

    def _write_entry(self, entry: AuditEntry) -> None:
        """Write an entry to the log file."""
        if not self.enabled:
            return

        self._rotate_if_needed()

        try:
            log_file = self._get_log_file_path()
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    @contextmanager
    def operation(
        self,
        action_start: AuditAction,
        action_complete: AuditAction,
        action_failed: AuditAction,
        actor_type: ActorType,
        actor_id: str | None = None,
        user_email: str | None = None,
        user_role: str | None = None,
        organization_id: str | None = None,
        project_id: str | None = None,
        spec_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Context manager for auditing an operation.

        Usage:
            with audit.operation(
                action_start=AuditAction.AGENT_SESSION_STARTED,
                action_complete=AuditAction.AGENT_SESSION_COMPLETED,
                action_failed=AuditAction.AGENT_SESSION_FAILED,
                actor_type=ActorType.USER,
                user_email="user@example.com",
                project_id="proj-123",
                spec_id="spec-456",
            ) as ctx:
                # Do work
                ctx.metadata["subtasks_completed"] = 5

        Automatically logs start, completion, and failure with timing.
        """
        ctx = self.start_operation(
            actor_type=actor_type,
            actor_id=actor_id,
            user_email=user_email,
            user_role=user_role,
            organization_id=organization_id,
            project_id=project_id,
            spec_id=spec_id,
            metadata=metadata,
        )

        self.log(ctx, action_start, result="started")
        start_time = time.monotonic()

        try:
            yield ctx
            duration_ms = int((time.monotonic() - start_time) * 1000)
            self.log(
                ctx,
                action_complete,
                result="success",
                details=ctx.metadata,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            self.log(
                ctx,
                action_failed,
                result="failure",
                error=str(e),
                details=ctx.metadata,
                duration_ms=duration_ms,
            )
            raise

    def log_sso_login(
        self,
        context: AuditContext,
        success: bool,
        sso_provider: str,
        error: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Log an SSO login attempt."""
        action = (
            AuditAction.SSO_LOGIN_COMPLETED if success else AuditAction.SSO_LOGIN_FAILED
        )
        self.log(
            context,
            action,
            result="success" if success else "failure",
            error=error,
            details={"sso_provider": sso_provider},
            duration_ms=duration_ms,
        )

    def log_data_residency_check(
        self,
        context: AuditContext,
        compliant: bool,
        required_region: str,
        actual_region: str,
        resource_type: str,
        resource_id: str,
    ) -> None:
        """Log a data residency compliance check."""
        action = (
            AuditAction.DATA_RESIDENCY_VALIDATED
            if compliant
            else AuditAction.DATA_RESIDENCY_VIOLATION
        )
        self.log(
            context,
            action,
            result="compliant" if compliant else "violation",
            details={
                "required_region": required_region,
                "actual_region": actual_region,
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
        )

    def log_permission_check(
        self,
        context: AuditContext,
        allowed: bool,
        permission: str,
        resource_type: str,
        resource_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Log a permission check result."""
        action = AuditAction.PERMISSION_GRANTED if allowed else AuditAction.PERMISSION_DENIED
        self.log(
            context,
            action,
            result="granted" if allowed else "denied",
            details={
                "permission": permission,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "reason": reason,
            },
        )

    def log_agent_session(
        self,
        context: AuditContext,
        agent_type: str,
        model: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        """Log an AI agent session."""
        action = (
            AuditAction.AGENT_SESSION_COMPLETED
            if not error
            else AuditAction.AGENT_SESSION_FAILED
        )
        self.log(
            context,
            action,
            result="success" if not error else "failure",
            error=error,
            details={
                "agent_type": agent_type,
                "model": model,
            },
            token_usage={
                "input_tokens": input_tokens or 0,
                "output_tokens": output_tokens or 0,
            },
            duration_ms=duration_ms,
        )

    def log_api_call(
        self,
        context: AuditContext,
        service: str,
        endpoint: str,
        method: str = "GET",
        status_code: int | None = None,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        """Log an external API call."""
        action = AuditAction.API_CALL_MADE if not error else AuditAction.API_CALL_FAILED
        self.log(
            context,
            action,
            result="success" if not error else "failure",
            error=error,
            details={
                "service": service,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
            },
            duration_ms=duration_ms,
        )

    def log_security_event(
        self,
        context: AuditContext,
        event_type: str,
        severity: str,
        description: str,
        affected_resource: str | None = None,
    ) -> None:
        """Log a security event."""
        self.log(
            context,
            AuditAction.ANOMALY_DETECTED,
            result="detected",
            details={
                "event_type": event_type,
                "severity": severity,
                "description": description,
                "affected_resource": affected_resource,
            },
        )

    def log_compliance_report(
        self,
        context: AuditContext,
        report_type: str,
        period_start: datetime,
        period_end: datetime,
        entry_count: int,
    ) -> None:
        """Log compliance report generation."""
        self.log(
            context,
            AuditAction.COMPLIANCE_REPORT_GENERATED,
            result="success",
            details={
                "report_type": report_type,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "entry_count": entry_count,
            },
        )

    def query_logs(
        self,
        correlation_id: str | None = None,
        action: AuditAction | None = None,
        actor_id: str | None = None,
        user_email: str | None = None,
        organization_id: str | None = None,
        project_id: str | None = None,
        spec_id: str | None = None,
        data_region: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """
        Query audit logs with filters.

        Args:
            correlation_id: Filter by correlation ID
            action: Filter by action type
            actor_id: Filter by actor ID
            user_email: Filter by user email
            organization_id: Filter by organization
            project_id: Filter by project
            spec_id: Filter by spec
            data_region: Filter by data region
            since: Only entries after this time
            limit: Maximum entries to return

        Returns:
            List of matching AuditEntry objects
        """
        if not self.enabled or not self.log_dir.exists():
            return []

        results = []

        for log_file in sorted(self.log_dir.glob("audit_*.jsonl"), reverse=True):
            try:
                with open(log_file, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue

                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        # Apply filters
                        if correlation_id and data.get("correlation_id") != correlation_id:
                            continue
                        if action and data.get("action") != action.value:
                            continue
                        if actor_id and data.get("actor_id") != actor_id:
                            continue
                        if user_email and data.get("user_email") != user_email:
                            continue
                        if organization_id and data.get("organization_id") != organization_id:
                            continue
                        if project_id and data.get("project_id") != project_id:
                            continue
                        if spec_id and data.get("spec_id") != spec_id:
                            continue
                        if data_region and data.get("data_region") != data_region:
                            continue
                        if since:
                            entry_time = datetime.fromisoformat(data["timestamp"])
                            if entry_time < since:
                                continue

                        # Reconstruct entry
                        entry = AuditEntry(
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                            correlation_id=data["correlation_id"],
                            action=AuditAction(data["action"]),
                            actor_type=ActorType(data["actor_type"]),
                            actor_id=data.get("actor_id"),
                            user_email=data.get("user_email"),
                            user_role=data.get("user_role"),
                            organization_id=data.get("organization_id"),
                            project_id=data.get("project_id"),
                            spec_id=data.get("spec_id"),
                            session_id=data.get("session_id"),
                            ip_address=data.get("ip_address"),
                            data_region=data.get("data_region"),
                            result=data["result"],
                            duration_ms=data.get("duration_ms"),
                            error=data.get("error"),
                            details=data.get("details", {}),
                            token_usage=data.get("token_usage"),
                            security_context=data.get("security_context"),
                        )
                        results.append(entry)

                        if len(results) >= limit:
                            return results

            except Exception as e:
                logger.error(f"Error reading audit log {log_file}: {e}")

        return results

    def get_operation_history(self, correlation_id: str) -> list[AuditEntry]:
        """Get all entries for a specific operation by correlation ID."""
        return self.query_logs(correlation_id=correlation_id, limit=1000)

    def get_statistics(
        self,
        organization_id: str | None = None,
        project_id: str | None = None,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Get aggregate statistics from audit logs.

        Returns:
            Dictionary with counts by action, result, actor type, and data region
        """
        entries = self.query_logs(
            organization_id=organization_id,
            project_id=project_id,
            since=since,
            limit=10000,
        )

        stats = {
            "total_entries": len(entries),
            "by_action": {},
            "by_result": {},
            "by_actor_type": {},
            "by_data_region": {},
            "total_duration_ms": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
        }

        for entry in entries:
            # Count by action
            action = entry.action.value
            stats["by_action"][action] = stats["by_action"].get(action, 0) + 1

            # Count by result
            result = entry.result
            stats["by_result"][result] = stats["by_result"].get(result, 0) + 1

            # Count by actor type
            actor = entry.actor_type.value
            stats["by_actor_type"][actor] = stats["by_actor_type"].get(actor, 0) + 1

            # Count by data region
            if entry.data_region:
                region = entry.data_region
                stats["by_data_region"][region] = stats["by_data_region"].get(region, 0) + 1

            # Sum durations
            if entry.duration_ms:
                stats["total_duration_ms"] += entry.duration_ms

            # Sum token usage
            if entry.token_usage:
                stats["total_input_tokens"] += entry.token_usage.get("input_tokens", 0)
                stats["total_output_tokens"] += entry.token_usage.get("output_tokens", 0)

        return stats


# Convenience functions for quick logging
def get_audit_logger() -> EnterpriseAuditLogger:
    """Get the global enterprise audit logger instance."""
    return EnterpriseAuditLogger.get_instance()


def audit_operation(
    action_start: AuditAction,
    action_complete: AuditAction,
    action_failed: AuditAction,
    **kwargs,
):
    """Decorator for auditing function calls."""

    def decorator(func):
        async def async_wrapper(*args, **func_kwargs):
            audit = get_audit_logger()
            with audit.operation(
                action_start=action_start,
                action_complete=action_complete,
                action_failed=action_failed,
                **kwargs,
            ) as ctx:
                return await func(*args, audit_context=ctx, **func_kwargs)

        def sync_wrapper(*args, **func_kwargs):
            audit = get_audit_logger()
            with audit.operation(
                action_start=action_start,
                action_complete=action_complete,
                action_failed=action_failed,
                **kwargs,
            ) as ctx:
                return func(*args, audit_context=ctx, **func_kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
