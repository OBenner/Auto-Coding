"""
Security Audit Logger
=====================

Logs security-relevant events for compliance and monitoring.
Tracks command execution, filesystem access, API calls, and permission changes.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .constants import AUDIT_LOG_FILENAME

__all__ = [
    "log_security_event",
    "get_audit_logs",
    "clear_audit_logs",
    "export_audit_logs",
    "get_audit_log_path",
]


# =============================================================================
# CONSTANTS
# =============================================================================

# Maximum number of audit log entries to keep per project
MAX_AUDIT_LOG_ENTRIES = 1000

# Audit log entry categories
CATEGORY_COMMAND_EXECUTION = "command_execution"
CATEGORY_FILESYSTEM_ACCESS = "filesystem_access"
CATEGORY_API_CALL = "api_call"
CATEGORY_PERMISSION_CHANGE = "permission_change"
CATEGORY_SANDBOX_VIOLATION = "sandbox_violation"
CATEGORY_PROFILE_LOADED = "profile_loaded"
CATEGORY_PROFILE_EXPORTED = "profile_exported"
CATEGORY_RISK_DETECTED = "risk_detected"

# Severity levels
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"


# =============================================================================
# AUDIT LOG FUNCTIONS
# =============================================================================


def get_audit_log_path(project_dir: Path) -> Path:
    """
    Get the audit log file path for a project.

    Args:
        project_dir: Project root directory

    Returns:
        Path to the audit log file
    """
    return project_dir / AUDIT_LOG_FILENAME


def _load_audit_logs(project_dir: Path) -> list[dict[str, Any]]:
    """
    Load audit logs from disk.

    Args:
        project_dir: Project root directory

    Returns:
        List of audit log entries (empty list if file doesn't exist)
    """
    audit_log_path = get_audit_log_path(project_dir)

    if not audit_log_path.exists():
        return []

    try:
        with open(audit_log_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("logs", [])
    except (json.JSONDecodeError, OSError, KeyError):
        # If file is corrupted, return empty list
        return []


def _save_audit_logs(project_dir: Path, logs: list[dict[str, Any]]) -> None:
    """
    Save audit logs to disk.

    Args:
        project_dir: Project root directory
        logs: List of audit log entries to save
    """
    audit_log_path = get_audit_log_path(project_dir)

    # Ensure parent directory exists
    audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": 1,
        "logs": logs,
    }

    with open(audit_log_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def log_security_event(
    project_dir: Path,
    category: str,
    message: str,
    severity: str = SEVERITY_INFO,
    allowed: bool = True,
    command: str | None = None,
    file_path: str | None = None,
    api_endpoint: str | None = None,
    rule_id: str | None = None,
    context: dict[str, Any] | None = None,
    agent_type: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Log a security event to the audit log.

    Args:
        project_dir: Project root directory
        category: Event category (command_execution, filesystem_access, etc.)
        message: Human-readable event description
        severity: Event severity (info, warning, critical)
        allowed: Whether the operation was allowed or blocked
        command: Related command (if applicable)
        file_path: Related file path (if applicable)
        api_endpoint: Related API endpoint (if applicable)
        rule_id: Security rule that triggered this log
        context: Additional context metadata
        agent_type: Agent type that caused this event
        session_id: Session ID for correlation

    Returns:
        The created audit log entry
    """
    project_dir = Path(project_dir).resolve()

    # Create audit log entry
    entry: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "category": category,
        "severity": severity,
        "message": message,
        "allowed": allowed,
    }

    # Add optional fields if provided
    if command is not None:
        entry["command"] = command
    if file_path is not None:
        entry["filePath"] = file_path
    if api_endpoint is not None:
        entry["apiEndpoint"] = api_endpoint
    if rule_id is not None:
        entry["ruleId"] = rule_id
    if context is not None:
        entry["context"] = json.dumps(context)
    if agent_type is not None:
        entry["agentType"] = agent_type
    if session_id is not None:
        entry["sessionId"] = session_id

    # Load existing logs
    logs = _load_audit_logs(project_dir)

    # Add new log entry
    logs.append(entry)

    # Trim to max entries (keep most recent)
    if len(logs) > MAX_AUDIT_LOG_ENTRIES:
        logs = logs[-MAX_AUDIT_LOG_ENTRIES:]

    # Save to disk
    _save_audit_logs(project_dir, logs)

    return entry


def get_audit_logs(
    project_dir: Path,
    category: str | None = None,
    severity: str | None = None,
    allowed: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    Retrieve audit logs with optional filtering.

    Args:
        project_dir: Project root directory
        category: Filter by category (optional)
        severity: Filter by severity (optional)
        allowed: Filter by allowed/blocked status (optional)
        limit: Maximum number of entries to return (default: 100)
        offset: Number of entries to skip (for pagination)

    Returns:
        List of audit log entries (most recent first)
    """
    project_dir = Path(project_dir).resolve()

    # Load all logs
    logs = _load_audit_logs(project_dir)

    # Reverse to get most recent first
    logs = list(reversed(logs))

    # Apply filters
    if category is not None:
        logs = [log for log in logs if log.get("category") == category]

    if severity is not None:
        logs = [log for log in logs if log.get("severity") == severity]

    if allowed is not None:
        logs = [log for log in logs if log.get("allowed") == allowed]

    # Apply pagination
    start = offset
    end = start + limit
    return logs[start:end]


def clear_audit_logs(project_dir: Path) -> int:
    """
    Clear all audit logs for a project.

    Args:
        project_dir: Project root directory

    Returns:
        Number of log entries that were cleared
    """
    project_dir = Path(project_dir).resolve()

    # Load existing logs to count them
    logs = _load_audit_logs(project_dir)
    count = len(logs)

    # Save empty list
    _save_audit_logs(project_dir, [])

    return count


def export_audit_logs(
    project_dir: Path,
    include_entries: int = 1000,
) -> dict[str, Any]:
    """
    Export audit logs for compliance or backup.

    Args:
        project_dir: Project root directory
        include_entries: Number of most recent entries to include

    Returns:
        Dictionary containing audit log export data
    """
    project_dir = Path(project_dir).resolve()

    # Load logs
    logs = _load_audit_logs(project_dir)

    # Get most recent entries
    logs = list(reversed(logs))[:include_entries]

    return {
        "version": 1,
        "exportedAt": int(datetime.now(timezone.utc).timestamp()),
        "projectPath": str(project_dir),
        "entryCount": len(logs),
        "logs": logs,
    }
