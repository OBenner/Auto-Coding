# Audit Logging Guide

This guide covers audit logging in Auto Code enterprise deployments, including event types, querying, compliance reporting, and log management.

## Table of Contents

- [Overview](#overview)
- [Audit Architecture](#audit-architecture)
- [Event Types](#event-types)
  - [Authentication & SSO Events](#authentication--sso-events)
  - [Data Residency Events](#data-residency-events)
  - [RBAC & Permission Events](#rbac--permission-events)
  - [Agent & Build Events](#agent--build-events)
  - [API & External Service Events](#api--external-service-events)
  - [Security & Monitoring Events](#security--monitoring-events)
  - [Compliance Reporting Events](#compliance-reporting-events)
  - [Configuration & Admin Events](#configuration--admin-events)
- [Audit Log Format](#audit-log-format)
- [Configuration](#configuration)
- [Query and Filtering](#query-and-filtering)
- [Compliance Reporting](#compliance-reporting)
- [Log Management](#log-management)
- [Integration](#integration)
- [Troubleshooting](#troubleshooting)

---

## Overview

Auto Code provides comprehensive, tamper-evident audit logging for enterprise security and compliance.

**Key Features:**
- **Structured Logging** - JSON-formatted logs for machine parsing
- **Correlation IDs** - Track operations across multiple events
- **Actor Tracking** - User, bot, automation, and system actions
- **Token Usage** - Track AI model consumption
- **Duration Tracking** - Performance monitoring
- **Security Context** - Additional metadata for security events
- **Log Rotation** - Automatic file rotation by size
- **Retention Policies** - Configurable log retention (default: 90 days)

**Compliance Support:**
- SOC2 Type II - Complete audit trail of all system access
- GDPR - Data processing and transfer logging
- HIPAA - PHI access and modification tracking
- CCPA - Data subject rights fulfillment logging
- UK DPA - Post-Brexit GDPR compliance

---

## Audit Architecture

### Log Storage

```
.auto-claude/enterprise/audit/
├── audit_2024-02-13.jsonl        # Current day's log
├── audit_2024-02-12.jsonl        # Previous day
├── audit_2024-02-13.153022.jsonl  # Rotated log (1.5GB)
└── audit_2024-02-13.145918.jsonl  # Rotated log (1.4GB)
```

**Format:** JSONL (one JSON object per line)

**Naming:** `audit_YYYY-MM-DD[.HHMMSS].jsonl`

**Rotation:** Automatic when file exceeds 100 MB

**Retention:** 90 days (configurable)

### Audit Flow

```
┌─────────────┐    Start Operation    ┌────────────────┐
│   User/Bot │ ────────────────────> │ Audit Logger   │
└─────────────┘                      └───────┬────────┘
                                             │
                                              │ Generate Correlation ID
                                              │
                                              ▼
                                       ┌───────────────┐
                                       │ AuditContext   │
                                       │ - actor_type   │
                                       │ - actor_id     │
                                       │ - project_id   │
                                       │ - spec_id      │
                                       │ - data_region  │
                                       │ - started_at   │
                                       └───────┬───────┘
                                               │
              ┌────────────────────────────────┴────────────────┐
              │                                         │
              ▼                                         ▼
     ┌─────────────────┐                     ┌──────────────────┐
     │ Log Events     │                     │ Read/Export Logs │
     └─────────────────┘                     └──────────────────┘
              │                                         │
              ▼                                         ▼
     ┌─────────────────┐                     ┌──────────────────┐
     │ Write to JSONL │                     │ Query Filters    │
     └─────────────────┘                     └──────────────────┘
```

### Singleton Pattern

```python
from enterprise.audit import get_audit_logger

# Get singleton instance
audit = get_audit_logger()

# All subsequent calls use same instance
audit2 = get_audit_logger()
assert audit is audit2  # True
```

---

## Event Types

Auto Code captures 70+ distinct event types across 8 categories.

### Authentication & SSO Events

| Event | Description | Logged Fields |
|-------|-------------|----------------|
| `sso_login_started` | SSO authentication initiated | user_email, sso_provider |
| `sso_login_completed` | SSO authentication succeeded | user_email, sso_provider, duration_ms |
| `sso_login_failed` | SSO authentication failed | user_email, sso_provider, error |
| `saml_assertion_verified` | SAML assertion validated | user_email, sso_provider, assertion_issuer |
| `saml_assertion_rejected` | SAML assertion rejected | user_email, sso_provider, error |
| `token_issued` | Session token issued | user_email, session_id |
| `token_refreshed` | Session token refreshed | user_email, session_id |
| `token_revoked` | Session token revoked | user_email, session_id, reason |
| `session_created` | User session created | user_email, session_id, ip_address |
| `session_expired` | User session expired | user_email, session_id |
| `logout` | User logout | user_email, session_id |

**Example Entry:**

```json
{
  "timestamp": "2024-02-13T14:30:15.123456Z",
  "relation_id": "ent-a1b2c3d4e5f6",
  "action": "sso_login_completed",
  "actor_type": "user",
  "actor_id": "user_123",
  "user_email": "user@example.com",
  "user_role": "developer",
  "organization_id": "org_456",
  "result": "success",
  "duration_ms": 1250,
  "details": {
    "sso_provider": "okta"
  }
}
```

### Data Residency Events

| Event | Description | Logged Fields |
|-------|-------------|----------------|
| `data_residency_validated` | Data transfer validated | required_region, actual_region, resource_type |
| `data_residency_violation` | Data transfer violation detected | required_region, actual_region, resource_type, violation_details |
| `data_transfer_requested` | Data transfer requested | source_region, destination_region, data_type |
| `data_transfer_approved` | Data transfer approved | source_region, destination_region, approval_reason |
| `data_transfer_denied` | Data transfer denied | source_region, destination_region, denial_reason |
| `data_deletion_requested` | Data deletion requested | data_subject_id, data_type |
| `data_deletion_completed` | Data deletion completed | data_subject_id, records_deleted |
| `data_export_requested` | Data export requested | data_subject_id, data_type |
| `data_export_completed` | Data export completed | data_subject_id, records_exported |

**Example Entry:**

```json
{
  "timestamp": "2024-02-13T14:30:20.123456Z",
  "relation_id": "ent-a1b2c3d4e5f6",
  "action": "data_residency_validated",
  "actor_type": "system",
  "actor_id": "data_residency_check",
  "user_email": "system@autoclaude",
  "result": "compliant",
  "details": {
    "required_region": "EU",
    "actual_region": "EU",
    "resource_type": "user_data",
    "resource_id": "user_123"
  },
  "data_region": "EU"
}
```

### RBAC & Permission Events

| Event | Description | Logged Fields |
|-------|-------------|----------------|
| `role_assigned` | Role assigned to user | user_email, role, assigned_by |
| `role_revoked` | Role revoked from user | user_email, role, revoked_by |
| `permission_granted` | Permission granted | user_email, permission, resource_type, resource_id |
| `permission_denied` | Permission denied | user_email, permission, resource_type, resource_id, reason |
| `permission_checked` | Permission checked | user_email, permission, allowed |
| `policy_evaluated` | Policy evaluated | user_email, policy_name, result |
| `access_approved` | Access approved | user_email, resource_type, resource_id |
| `access_denied` | Access denied | user_email, resource_type, resource_id, reason |

**Example Entry:**

```json
{
  "timestamp": "2024-02-13T14:30:25.123456Z",
  "relation_id": "ent-a1b2c3d4e5f6",
  "action": "permission_denied",
  "actor_type": "user",
  "actor_id": "user_123",
  "user_email": "user@example.com",
  "user_role": "viewer",
  "result": "denied",
  "details": {
    "permission": "build_run",
    "resource_type": "build",
    "resource_id": "build_789",
    "reason": "Insufficient permissions: viewer role cannot run builds"
  }
}
```

### Agent & Build Events

**Generic Agent Events:**

| Event | Description |
|-------|-------------|
| `agent_session_started` | Agent session started |
| `agent_session_completed` | Agent session completed |
| `agent_session_failed` | Agent session failed |

**Planner Agent Events:**

| Event | Description |
|-------|-------------|
| `agent_planner_started` | Planner agent started |
| `agent_planner_completed` | Planner agent completed |
| `agent_planner_failed` | Planner agent failed |

**Coder Agent Events:**

| Event | Description |
|-------|-------------|
| `agent_coder_started` | Coder agent started |
| `agent_coder_completed` | Coder agent completed |
| `agent_coder_failed` | Coder agent failed |

**QA Agent Events:**

| Event | Description |
|-------|-------------|
| `agent_qa_reviewer_started` | QA Reviewer agent started |
| `agent_qa_reviewer_completed` | QA Reviewer agent completed |
| `agent_qa_reviewer_failed` | QA Reviewer agent failed |
| `agent_qa_fixer_started` | QA Fixer agent started |
| `agent_qa_fixer_completed` | QA Fixer agent completed |
| `agent_qa_fixer_failed` | QA Fixer agent failed |

**Build Events:**

| Event | Description |
|-------|-------------|
| `build_started` | Build started |
| `build_completed` | Build completed |
| `build_failed` | Build failed |
| `code_generated` | Code generated |
| `code_reviewed` | Code reviewed |
| `code_deployed` | Code deployed |

**Example Entry:**

```json
{
  "timestamp": "2024-02-13T14:30:30.123456Z",
  "relation_id": "ent-a1b2c3d4e5f6",
  "action": "agent_coder_completed",
  "actor_type": "automation",
  "actor_id": "coder_agent",
  "user_email": null,
  "user_role": null,
  "organization_id": "org_456",
  "project_id": "proj_789",
  "spec_id": "spec_001",
  "session_id": "sess_abc123",
  "result": "success",
  "duration_ms": 45000,
  "details": {
    "agent_type": "coder",
    "model": "claude-sonnet-4"
  },
  "token_usage": {
    "input_tokens": 15234,
    "output_tokens": 8932
  }
}
```

### API & External Service Events

| Event | Description | Logged Fields |
|-------|-------------|----------------|
| `api_call_made` | External API call made | service, endpoint, method, status_code |
| `api_call_failed` | External API call failed | service, endpoint, method, error |
| `api_rate_limit_warning` | API rate limit warning | service, requests_remaining |
| `api_rate_limit_exceeded` | API rate limit exceeded | service, limit |
| `external_service_call` | External service called | service_name, operation |
| `external_service_error` | External service error | service_name, error |

**Example Entry:**

```json
{
  "timestamp": "2024-02-13T14:30:35.123456Z",
  "relation_id": "ent-a1b2c3d4e5f6",
  "action": "api_call_made",
  "actor_type": "automation",
  "actor_id": "http_client",
  "result": "success",
  "duration_ms": 250,
  "details": {
    "service": "anthropic",
    "endpoint": "/v1/messages",
    "method": "POST",
    "status_code": 200
  }
}
```

### Security & Monitoring Events

| Event | Description | Logged Fields |
|-------|-------------|----------------|
| `security_scan_started` | Security scan started | scan_type, target |
| `security_scan_completed` | Security scan completed | scan_type, findings_count |
| `vulnerability_detected` | Vulnerability detected | severity, cve_id, affected_component |
| `security_policy_violated` | Security policy violated | policy_name, violation_details |
| `anomaly_detected` | Anomaly detected | anomaly_type, severity, description |
| `threat_blocked` | Threat blocked | threat_type, blocked_by |

**Example Entry:**

```json
{
  "timestamp": "2024-02-13T14:30:40.123456Z",
  "relation_id": "ent-a1b2c3d4e5f6",
  "action": "vulnerability_detected",
  "actor_type": "system",
  "actor_id": "security_scanner",
  "result": "detected",
  "details": {
    "severity": "high",
    "cve_id": "CVE-2024-12345",
    "affected_component": "dependency/package@2.1.0",
    "description": "Remote code execution vulnerability"
  },
  "security_context": {
    "scan_type": "dependency_scan",
    "scan_id": "scan_789"
  }
}
```

### Compliance Reporting Events

| Event | Description | Logged Fields |
|-------|-------------|----------------|
| `compliance_report_generated` | Compliance report generated | report_type, period_start, period_end |
| `compliance_report_exported` | Compliance report exported | report_type, format, destination |
| `audit_log_accessed` | Audit log accessed | access_type, query_filters |
| `audit_log_exported` | Audit log exported | export_format, record_count |
| `retention_policy_applied` | Retention policy applied | policy_name, records_deleted |

**Example Entry:**

```json
{
  "timestamp": "2024-02-13T14:30:45.123456Z",
  "relation_id": "ent-compliance-123",
  "action": "compliance_report_generated",
  "actor_type": "system",
  "actor_id": "compliance_reporter",
  "user_email": null,
  "result": "success",
  "details": {
    "report_type": "weekly",
    "period_start": "2024-02-06T00:00:00Z",
    "period_end": "2024-02-13T00:00:00Z",
    "entry_count": 15234
  }
}
```

### Configuration & Admin Events

| Event | Description | Logged Fields |
|-------|-------------|----------------|
| `config_updated` | Configuration updated | config_key, old_value, new_value, updated_by |
| `feature_flag_toggled` | Feature flag toggled | feature_name, new_state, toggled_by |
| `admin_action` | Admin action performed | action_type, target, admin_email |
| `system_maintenance` | System maintenance performed | maintenance_type, duration_seconds |
| `backup_created` | Backup created | backup_type, backup_path |
| `backup_restored` | Backup restored | backup_type, backup_path, restored_by |

**Example Entry:**

```json
{
  "timestamp": "2024-02-13T14:30:50.123456Z",
  "relation_id": "ent-admin-456",
  "action": "config_updated",
  "actor_type": "admin",
  "actor_id": "admin_789",
  "user_email": "admin@example.com",
  "user_role": "admin",
  "result": "success",
  "details": {
    "config_key": "data_region",
    "old_value": "GLOBAL",
    "new_value": "EU",
    "updated_by": "admin@example.com"
  }
}
```

---

## Audit Log Format

### Entry Structure

Every audit entry contains:

**Required Fields:**

```json
{
  "timestamp": "2024-02-13T14:30:00.123456Z",
  "relation_id": "ent-a1b2c3d4e5f6",
  "action": "agent_coder_started",
  "actor_type": "automation",
  "actor_id": "coder_agent",
  "result": "success",
  "details": {}
}
```

**Optional Fields:**

```json
{
  "actor_id": "user_123",
  "user_email": "user@example.com",
  "user_role": "developer",
  "organization_id": "org_456",
  "project_id": "proj_789",
  "spec_id": "spec_001",
  "session_id": "sess_abc123",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "data_region": "EU",
  "duration_ms": 1500,
  "error": "Connection timeout",
  "token_usage": {
    "input_tokens": 1000,
    "output_tokens": 500
  },
  "security_context": {
    "scan_type": "vulnerability_scan"
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timestamp` | ISO 8601 | Yes | Event timestamp (UTC) |
| `relation_id` | string | Yes | Correlation ID for operation |
| `action` | enum | Yes | Action type (see Event Types) |
| `actor_type` | enum | Yes | Actor type (user, admin, bot, automation, system) |
| `actor_id` | string | No | Actor identifier |
| `user_email` | string | No | User email (for actor_type=user/admin) |
| `user_role` | string | No | User role (admin, developer, viewer, etc.) |
| `organization_id` | string | No | Organization identifier |
| `project_id` | string | No | Project identifier |
| `spec_id` | string | No | Spec identifier |
| `session_id` | string | No | Session identifier |
| `ip_address` | string | No | Client IP address |
| `user_agent` | string | No | Client user agent |
| `data_region` | string | No | Data region (EU, US, UK, AP, GLOBAL) |
| `result` | string | Yes | Result status (success, failure, denied, started) |
| `duration_ms` | int | No | Duration in milliseconds |
| `error` | string | No | Error message (if failed) |
| `details` | object | Yes | Additional event details |
| `token_usage` | object | No | Token usage (input_tokens, output_tokens) |
| `security_context` | object | No | Security metadata |

### Example: Complete Entry

```json
{
  "timestamp": "2024-02-13T14:30:00.123456Z",
  "relation_id": "ent-a1b2c3d4e5f6",
  "action": "agent_coder_completed",
  "actor_type": "automation",
  "actor_id": "coder_agent",
  "user_email": null,
  "user_role": null,
  "organization_id": "org_456",
  "project_id": "proj_789",
  "spec_id": "spec_001",
  "session_id": "sess_abc123",
  "ip_address": null,
  "user_agent": null,
  "data_region": "EU",
  "result": "success",
  "duration_ms": 45000,
  "error": null,
  "details": {
    "agent_type": "coder",
    "model": "claude-sonnet-4",
    "subtasks_completed": 5,
    "files_modified": 12
  },
  "token_usage": {
    "input_tokens": 15234,
    "output_tokens": 8932
  },
  "security_context": null
}
```

---

## Configuration

### Enable Audit Logging

**Via Environment Variables:**

```bash
# Enable audit logging (default: true in enterprise mode)
export ENTERPRISE_AUDIT_ENABLED=true

# Configure log directory (default: .auto-claude/enterprise/audit)
export ENTERPRISE_AUDIT_LOG_PATH=/var/log/autoclaude/audit

# Set retention period (default: 90 days)
export ENTERPRISE_AUDIT_RETENTION_DAYS=365

# Set max file size before rotation (default: 100 MB)
export ENTERPRISE_AUDIT_MAX_FILE_SIZE_MB=500
```

**Programmatic Configuration:**

```python
from enterprise.audit import EnterpriseAuditLogger
from pathlib import Path

# Initialize with custom settings
audit = EnterpriseAuditLogger(
    log_dir=Path("/var/log/autoclaude/audit"),
    retention_days=365,
    max_file_size_mb=500,
    enabled=True
)
```

### Directory Setup

```bash
# Create audit directory
sudo mkdir -p /var/log/autoclaude/audit

# Set ownership
sudo chown autoclaude:autoclaude /var/log/autoclaude/audit

# Set permissions
sudo chmod 755 /var/log/autoclaude/audit

# Verify
ls -la /var/log/autoclaude/audit
```

**SELinux Configuration (if enabled):**

```bash
# Set SELinux context
sudo semanage fcontext -a -t httpd_log_t "/var/log/autoclaude/audit(/.*)?"
sudo restorecon -Rv /var/log/autoclaude/audit
```

### Singleton Instance

```python
from enterprise.audit import get_audit_logger

# Get singleton (uses environment config)
audit = get_audit_logger()

# Force reload configuration
audit2 = get_audit_logger(reload=True)
```

---

## Query and Filtering

### Query Methods

**Basic Query:**

```python
from enterprise.audit import get_audit_logger

audit = get_audit_logger()

# Get recent entries (last 100)
entries = audit.query_logs(limit=100)

for entry in entries:
    print(f"{entry.timestamp}: {entry.action.value}")
```

**Filter by Action:**

```python
from enterprise.audit import get_audit_logger, AuditAction

audit = get_audit_logger()

# Get only coder agent events
entries = audit.query_logs(
    action=audit.AuditAction.AGENT_CODER_COMPLETED,
    limit=50
)

for entry in entries:
    print(f"{entry.timestamp}: {entry.details.get('subtasks_completed', 0)} subtasks")
```

**Filter by User:**

```python
# Get events for specific user
entries = audit.query_logs(
    user_email="user@example.com",
    limit=100
)

for entry in entries:
    print(f"{entry.action.value}: {entry.result}")
```

**Filter by Organization:**

```python
# Get events for organization
entries = audit.query_logs(
    organization_id="org_456",
    limit=1000
)

print(f"Total events: {len(entries)}")
```

**Filter by Project:**

```python
# Get events for specific project
entries = audit.query_logs(
    project_id="proj_789",
    limit=1000
)

# Analyze build success rate
builds = [e for e in entries if e.action in [
    audit.AuditAction.BUILD_COMPLETED,
    audit.AuditAction.BUILD_FAILED
]]

success_rate = len([e for e in builds if e.result == "success"]) / len(builds) * 100
print(f"Build success rate: {success_rate:.1f}%")
```

**Filter by Spec:**

```python
# Get events for specific spec
entries = audit.query_logs(
    spec_id="spec_001",
    limit=1000
)

# Get operation history
history = audit.get_operation_history("ent-a1b2c3d4e5f6")
for entry in history:
    print(f"{entry.action.value}: {entry.result}")
```

**Filter by Data Region:**

```python
# Get EU-specific events
entries = audit.query_logs(
    data_region="EU",
    limit=1000
)

# Check for data residency violations
violations = [e for e in entries if e.action == audit.AuditAction.DATA_RESIDENCY_VIOLATION]
if violations:
    print(f"WARNING: {len(violations)} data residency violations detected")
```

**Filter by Time:**

```python
from datetime import datetime, timedelta, UTC

# Get last 24 hours
since = datetime.now(UTC) - timedelta(hours=24)

entries = audit.query_logs(
    since=since,
    limit=10000
)

print(f"Events in last 24 hours: {len(entries)}")
```

**Combine Filters:**

```python
# Get failed builds for project in last week
since = datetime.now(UTC) - timedelta(days=7)

entries = audit.query_logs(
    action=audit.AuditAction.BUILD_FAILED,
    project_id="proj_789",
    since=since,
    limit=100
)

for entry in entries:
    print(f"{entry.timestamp}: {entry.error}")
```

### Get Statistics

**Overall Statistics:**

```python
from datetime import datetime, timedelta, UTC

audit = get_audit_logger()

# Last 30 days
since = datetime.now(UTC) - timedelta(days=30)

stats = audit.get_statistics(since=since)

print(f"Total entries: {stats['total_entries']}")
print(f"Total duration: {stats['total_duration_ms'] / 1000 / 60:.1f} minutes")
print(f"Total tokens: {stats['total_input_tokens'] + stats['total_output_tokens']}")

# By action
print("\nBy Action:")
for action, count in stats['by_action'].items():
    print(f"  {action}: {count}")

# By result
print("\nBy Result:")
for result, count in stats['by_result'].items():
    print(f"  {result}: {count}")

# By actor type
print("\nBy Actor Type:")
for actor, count in stats['by_actor_type'].items():
    print(f"  {actor}: {count}")

# By data region
print("\nBy Data Region:")
for region, count in stats['by_data_region'].items():
    print(f"  {region}: {count}")
```

**Organization Statistics:**

```python
# Get org-specific stats
stats = audit.get_statistics(
    organization_id="org_456",
    since=datetime.now(UTC) - timedelta(days=30)
)

print(f"Org {org_456} last 30 days:")
print(f"  Total events: {stats['total_entries']}")
print(f"  Token usage: {stats['total_input_tokens'] + stats['total_output_tokens']}")
```

**Project Statistics:**

```python
# Get project-specific stats
stats = audit.get_statistics(
    project_id="proj_789",
    since=datetime.now(UTC) - timedelta(days=7)
)

print(f"Project proj_789 last 7 days:")
print(f"  Builds: {stats['by_action'].get('build_started', 0)}")
print(f"  Success rate: {stats['by_result'].get('success', 0) / stats['total_entries'] * 100:.1f}%")
```

---

## Compliance Reporting

### Generate Reports

**Weekly Compliance Report:**

```python
from enterprise.audit import get_audit_logger
from datetime import datetime, timedelta, UTC
import json

audit = get_audit_logger()

# Date range
end_date = datetime.now(UTC)
start_date = end_date - timedelta(days=7)

# Get statistics
stats = audit.get_statistics(since=start_date)

# Build report
report = {
    "report_type": "weekly_compliance",
    "period_start": start_date.isoformat(),
    "period_end": end_date.isoformat(),
    "entry_count": stats["total_entries"],

    # Summary
    "summary": {
        "total_duration_seconds": stats["total_duration_ms"] / 1000,
        "total_tokens": stats["total_input_tokens"] + stats["total_output_tokens"],
        "unique_users": len(set(e.user_email for e in audit.query_logs(since=start_date))),
        "unique_projects": len(set(e.project_id for e in audit.query_logs(since=start_date))),
    },

    # Breakdown by category
    "by_action": stats["by_action"],
    "by_result": stats["by_result"],
    "by_actor_type": stats["by_actor_type"],
    "by_data_region": stats["by_data_region"],

    # Token usage
    "token_usage": {
        "total_input_tokens": stats["total_input_tokens"],
        "total_output_tokens": stats["total_output_tokens"],
    },
}

# Save report
with open('weekly-compliance-report.json', 'w') as f:
    json.dump(report, f, indent=2)

# Log report generation
ctx = audit.start_operation(
    actor_type=audit.ActorType.SYSTEM,
    actor_id="compliance_reporter"
)
audit.log_compliance_report(
    context=ctx,
    report_type="weekly",
    period_start=start_date,
    period_end=end_date,
    entry_count=stats["total_entries"]
)

print(f"Report saved: weekly-compliance-report.json")
```

**SOC2 Compliance Report:**

```python
# SOC2 requires specific evidence
def generate_soc2_report(since, until):
    """Generate SOC2 compliance report."""

    audit = get_audit_logger()

    # Get all events
    entries = audit.query_logs(since=since, limit=100000)

    # SOC2 evidence categories
    evidence = {
        "access_control": {
            "authentication_events": [],
            "permission_checks": [],
            "role_assignments": [],
        },
        "change_management": {
            "config_changes": [],
            "admin_actions": [],
        },
        "data_protection": {
            "data_residency_checks": [],
            "data_transfers": [],
        },
        "system_monitoring": {
            "security_events": [],
            "anomalies": [],
        },
    }

    # Categorize events
    for entry in entries:
        if entry.action == audit.AuditAction.SSO_LOGIN_COMPLETED:
            evidence["access_control"]["authentication_events"].append(entry.to_dict())

        elif entry.action == audit.AuditAction.PERMISSION_GRANTED:
            evidence["access_control"]["permission_checks"].append(entry.to_dict())

        elif entry.action == audit.AuditAction.ROLE_ASSIGNED:
            evidence["access_control"]["role_assignments"].append(entry.to_dict())

        elif entry.action == audit.AuditAction.CONFIG_UPDATED:
            evidence["change_management"]["config_changes"].append(entry.to_dict())

        elif entry.action == audit.AuditAction.ADMIN_ACTION:
            evidence["change_management"]["admin_actions"].append(entry.to_dict())

        elif entry.action == audit.AuditAction.DATA_RESIDENCY_VALIDATED:
            evidence["data_protection"]["data_residency_checks"].append(entry.to_dict())

        elif entry.action == audit.AuditAction.DATA_TRANSFER_APPROVED:
            evidence["data_protection"]["data_transfers"].append(entry.to_dict())

        elif entry.action == audit.AuditAction.ANOMALY_DETECTED:
            evidence["system_monitoring"]["anomalies"].append(entry.to_dict())

        elif entry.action == audit.AuditAction.VULNERABILITY_DETECTED:
            evidence["system_monitoring"]["security_events"].append(entry.to_dict())

    return evidence

# Generate for last 90 days (SOC2 retention)
since = datetime.now(UTC) - timedelta(days=90)
evidence = generate_soc2_report(since=since, until=datetime.now(UTC))

with open('soc2-evidence.json', 'w') as f:
    json.dump(evidence, f, indent=2)

print("SOC2 evidence saved: soc2-evidence.json")
```

**GDPR Data Subject Access Report:**

```python
def generate_dsar_report(user_email: str, since: datetime):
    """Generate GDPR Data Subject Access Report."""

    audit = get_audit_logger()

    # Get all user events
    entries = audit.query_logs(user_email=user_email, since=since, limit=10000)

    # GDPR categories
    report = {
        "data_subject_email": user_email,
        "report_period": {
            "start": since.isoformat(),
            "end": datetime.now(UTC).isoformat(),
        },

        # Processing activities
        "processing_activities": [],

        # Authentication events
        "authentication_events": [],

        # Data accesses
        "data_accesses": [],

        # Data transfers
        "data_transfers": [],

        # Rights exercised
        "rights_exercised": [],
    }

    for entry in entries:
        if entry.action == audit.AuditAction.SSO_LOGIN_COMPLETED:
            report["authentication_events"].append(entry.to_dict())

        elif entry.action == audit.AuditAction.PERMISSION_GRANTED:
            report["data_accesses"].append(entry.to_dict())

        elif entry.action == audit.AuditAction.DATA_TRANSFER_APPROVED:
            report["data_transfers"].append(entry.to_dict())

        elif entry.action in [
            audit.AuditAction.DATA_DELETION_REQUESTED,
            audit.AuditAction.DATA_EXPORT_REQUESTED,
        ]:
            report["rights_exercised"].append(entry.to_dict())

        # All events are processing activities
        report["processing_activities"].append({
            "timestamp": entry.timestamp.isoformat(),
            "action": entry.action.value,
            "purpose": "Software development automation",
        })

    return report

# Generate DSAR
user_email = "user@example.com"
since = datetime.now(UTC) - timedelta(days=365)  # GDPR retention

report = generate_dsar_report(user_email, since)

with open(f'dsar-{user_email}.json', 'w') as f:
    json.dump(report, f, indent=2)

print(f"DSAR saved: dsar-{user_email}.json")
```

---

## Log Management

### Retention Policy

**Automatic Cleanup:**

```python
from enterprise.audit import get_audit_logger

audit = get_audit_logger()

# Manually trigger cleanup
audit._cleanup_old_logs()

# This removes logs older than retention_days
# (default: 90 days)
```

**Configure Retention:**

```bash
# Environment variable
export ENTERPRISE_AUDIT_RETENTION_DAYS=365  # 1 year
```

**Programmatic Configuration:**

```python
audit = EnterpriseAuditLogger(
    log_dir=Path("/var/log/autoclaude/audit"),
    retention_days=365,  # 1 year
)
```

### Log Rotation

**Automatic Rotation:**

Logs automatically rotate when file size exceeds `max_file_size_mb` (default: 100 MB).

**Rotated File Naming:**

```
audit_2024-02-13.jsonl              # Current
audit_2024-02-13.153022.jsonl        # Rotated at 15:30:22
audit_2024-02-13.145918.jsonl        # Rotated at 14:59:18
```

**Configure Rotation:**

```bash
# Environment variable
export ENTERPRISE_AUDIT_MAX_FILE_SIZE_MB=500  # 500 MB
```

**Programmatic Configuration:**

```python
audit = EnterpriseAuditLogger(
    log_dir=Path("/var/log/autoclaude/audit"),
    max_file_size_mb=500,  # 500 MB
)
```

### Export and Backup

**Export to JSON:**

```python
from datetime import datetime, timedelta, UTC

audit = get_audit_logger()

# Export last 30 days
since = datetime.now(UTC) - timedelta(days=30)
entries = audit.query_logs(since=since, limit=100000)

# Export
with open('audit-export.json', 'w') as f:
    json.dump([e.to_dict() for e in entries], f, indent=2)

# Log export
ctx = audit.start_operation(
    actor_type=audit.ActorType.USER,
    actor_id="admin_123",
    user_email="admin@example.com"
)

audit.log(
    context=ctx,
    action=audit.AuditAction.AUDIT_LOG_EXPORTED,
    result="success",
    details={
        "export_format": "json",
        "record_count": len(entries),
        "period_start": since.isoformat(),
        "period_end": datetime.now(UTC).isoformat(),
    }
)
```

**Export to CSV:**

```python
import csv
from datetime import datetime, timedelta, UTC

audit = get_audit_logger()

# Get entries
since = datetime.now(UTC) - timedelta(days=7)
entries = audit.query_logs(since=since, limit=10000)

# Export to CSV
with open('audit-export.csv', 'w', newline='') as f:
    writer = csv.writer(f)

    # Header
    writer.writerow([
        'timestamp', 'relation_id', 'action', 'actor_type',
        'user_email', 'result', 'duration_ms'
    ])

    # Rows
    for entry in entries:
        writer.writerow([
            entry.timestamp.isoformat(),
            entry.relation_id,
            entry.action.value,
            entry.actor_type.value,
            entry.user_email or '',
            entry.result,
            entry.duration_ms or '',
        ])

print(f"Exported {len(entries)} entries to audit-export.csv")
```

**Archive Old Logs:**

```bash
#!/bin/bash
# Archive audit logs older than 30 days

AUDIT_DIR="/var/log/autoclaude/audit"
ARCHIVE_DIR="/var/log/autoclaude/archive"

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

# Find and archive old logs
find "$AUDIT_DIR" -name "audit_*.jsonl" -mtime +30 -print0 | \
    while IFS= read -r -d '' file; do
        # Get date from filename
        date=$(basename "$file" | sed 's/audit_\([0-9]*-[0-9]*-[0-9]*\).*/\1/')

        # Compress
        gzip -c "$file" > "$ARCHIVE_DIR/audit-$date.jsonl.gz"

        # Verify
        if [ $? -eq 0 ]; then
            echo "Archived: $file"
            rm "$file"
        else
            echo "ERROR: Failed to archive $file"
        fi
    done
```

---

## Integration

### SIEM Integration

**Send to Elasticsearch:**

```python
from datetime import datetime, timedelta, UTC
import requests

audit = get_audit_logger()

# Get recent entries
since = datetime.now(UTC) - timedelta(minutes=5)
entries = audit.query_logs(since=since, limit=1000)

# Bulk insert to Elasticsearch
bulk_data = []
for entry in entries:
    bulk_data.append({
        "index": {"_index": "autoclaude-audit"}
    })
    bulk_data.append(entry.to_dict())

# Send
response = requests.post(
    'http://elasticsearch:9200/_bulk',
    headers={'Content-Type': 'application/x-ndjson'},
    data='\n'.join([json.dumps(line) for line in bulk_data]) + '\n'
)

if response.status_code == 200:
    print(f"Sent {len(entries)} entries to Elasticsearch")
else:
    print(f"ERROR: {response.status_code} - {response.text}")
```

**Send to Splunk:**

```python
import requests

# Send to Splunk HEC
splunk_url = "https://splunk.example.com:8088/services/collector/event"
splunk_token = "Splunk..."

entries = audit.query_logs(limit=100)

for entry in entries:
    # Format for Splunk
    event = {
        "event": entry.to_dict(),
        "sourcetype": "autoclaude:audit",
        "source": "autoclaude",
        "index": "audit"
    }

    # Send
    response = requests.post(
        splunk_url,
        headers={
            'Authorization': f'Splunk {splunk_token}',
            'Content-Type': 'application/json'
        },
        json=event
    )

    if response.status_code != 200:
        print(f"ERROR: {response.status_code}")
```

**Send to Sumo Logic:**

```python
import requests

# Sumo Logic HTTP endpoint
sumo_url = "https://sumologic.example.com/receiver/v1/http/..."

entries = audit.query_logs(limit=1000)

# Send in bulk
bulk_data = '\n'.join([json.dumps(e.to_dict()) for e in entries])

response = requests.post(
    sumo_url,
    headers={'Content-Type': 'application/json'},
    data=bulk_data
)

if response.status_code == 200:
    print(f"Sent {len(entries)} entries to Sumo Logic")
```

### Real-Time Streaming

**Log Tailing:**

```python
import time
from pathlib import Path

def tail_audit_logs(log_dir: Path):
    """Tail audit logs in real-time."""
    current_log = log_dir / f"audit_{datetime.now().strftime('%Y-%m-%d')}.jsonl"

    with open(current_log, 'r') as f:
        # Skip to end
        f.seek(0, 2)

        while True:
            line = f.readline()
            if line:
                # Parse JSON
                entry = json.loads(line)
                yield entry
            else:
                time.sleep(0.1)

# Use generator
for entry in tail_audit_logs(Path(".auto-claude/enterprise/audit")):
    print(f"{entry.timestamp}: {entry.action.value}")
```

### Alert Integration

**Alert on Failed Login:**

```python
from datetime import datetime, timedelta, UTC

audit = get_audit_logger()

# Check for failed logins in last 15 minutes
since = datetime.now(UTC) - timedelta(minutes=15)

failed_logins = audit.query_logs(
    action=audit.AuditAction.SSO_LOGIN_FAILED,
    since=since
)

if len(failed_logins) > 5:
    # Alert
    for entry in failed_logins:
        print(f"ALERT: Failed login for {entry.user_email} from {entry.ip_address}")
```

**Alert on Permission Denied:**

```python
# Check for permission denied
denied = audit.query_logs(
    action=audit.AuditAction.PERMISSION_DENIED,
    since=datetime.now(UTC) - timedelta(minutes=60)
)

if denied:
    print(f"WARNING: {len(denied)} permission denials in last hour")
```

**Alert on Data Residency Violation:**

```python
# Check for violations
violations = audit.query_logs(
    action=audit.AuditAction.DATA_RESIDENCY_VIOLATION,
    since=datetime.now(UTC) - timedelta(hours=24)
)

if violations:
    print(f"CRITICAL: {len(violations)} data residency violations detected")
    for v in violations:
        print(f"  {v.details['required_region']} -> {v.details['actual_region']}")
```

---

## Troubleshooting

### Common Issues

**Issue: Audit logs not written**

```bash
# Check directory exists
ls -la .auto-claude/enterprise/audit/

# Check permissions
stat .auto-claude/enterprise/audit/

# Fix permissions
chmod 755 .auto-claude/enterprise/audit/
chown autoclaude:autoclaude .auto-claude/enterprise/audit/
```

**Issue: Logs not rotating**

```bash
# Check current log size
ls -lh .auto-claude/enterprise/audit/

# Verify rotation configuration
python -c "
from enterprise.audit import get_audit_logger

audit = get_audit_logger()
print(f'Max file size: {audit.max_file_size_mb} MB')
print(f'Retention: {audit.retention_days} days')
"
```

**Issue: Query returns no results**

```bash
# Check log files exist
ls -la .auto-claude/enterprise/audit/*.jsonl

# Verify query filters
python -c "
from enterprise.audit import get_audit_logger
from datetime import datetime, timedelta, UTC

audit = get_audit_logger()
entries = audit.query_logs(limit=10)
print(f'Total entries: {len(entries)}')

if entries:
    print(f'Sample: {entries[0].timestamp}')
"
```

### Debug Mode

**Enable verbose logging:**

```python
import logging

# Enable audit module debug logging
logging.basicConfig(level=logging.DEBUG)
audit_logger = logging.getLogger('enterprise.audit')
audit_logger.setLevel(logging.DEBUG)

# Run queries
from enterprise.audit import get_audit_logger

audit = get_audit_logger()
entries = audit.query_logs(limit=1)
```

**Inspect raw logs:**

```bash
# View current log file
today=$(date +%Y-%m-%d)
cat .auto-claude/enterprise/audit/audit_${today}.jsonl | jq .

# Filter by action
cat .auto-claude/enterprise/audit/audit_*.jsonl | \
  jq 'select(.action == "agent_coder_completed")'

# Filter by user
cat .auto-claude/enterprise/audit/audit_*.jsonl | \
  jq 'select(.user_email == "user@example.com")'
```

---

## Appendix

### AuditAction Reference

All 70+ audit actions organized by category:

**Authentication & SSO (11 actions):**
- `sso_login_started`
- `sso_login_completed`
- `sso_login_failed`
- `saml_assertion_verified`
- `saml_assertion_rejected`
- `token_issued`
- `token_refreshed`
- `token_revoked`
- `session_created`
- `session_expired`
- `logout`

**Data Residency & Compliance (10 actions):**
- `data_residency_validated`
- `data_residency_violation`
- `data_transfer_requested`
- `data_transfer_approved`
- `data_transfer_denied`
- `data_deletion_requested`
- `data_deletion_completed`
- `data_export_requested`
- `data_export_completed`

**RBAC & Permissions (8 actions):**
- `role_assigned`
- `role_revoked`
- `permission_granted`
- `permission_denied`
- `permission_checked`
- `policy_evaluated`
- `access_approved`
- `access_denied`

**Agent & Build (12 actions):**
- `agent_session_started`
- `agent_session_completed`
- `agent_session_failed`
- `agent_planner_started`
- `agent_planner_completed`
- `agent_planner_failed`
- `agent_coder_started`
- `agent_coder_completed`
- `agent_coder_failed`
- `agent_qa_reviewer_started`
- `agent_qa_reviewer_completed`
- `agent_qa_reviewer_failed`
- `agent_qa_fixer_started`
- `agent_qa_fixer_completed`
- `agent_qa_fixer_failed`
- `build_started`
- `build_completed`
- `build_failed`
- `code_generated`
- `code_reviewed`
- `code_deployed`

**API & External Services (6 actions):**
- `api_call_made`
- `api_call_failed`
- `api_rate_limit_warning`
- `api_rate_limit_exceeded`
- `external_service_call`
- `external_service_error`

**Security & Monitoring (6 actions):**
- `security_scan_started`
- `security_scan_completed`
- `vulnerability_detected`
- `security_policy_violated`
- `anomaly_detected`
- `threat_blocked`

**Compliance Reporting (5 actions):**
- `compliance_report_generated`
- `compliance_report_exported`
- `audit_log_accessed`
- `audit_log_exported`
- `retention_policy_applied`

**Configuration & Admin (6 actions):**
- `config_updated`
- `feature_flag_toggled`
- `admin_action`
- `system_maintenance`
- `backup_created`
- `backup_restored`

### ActorType Reference

| Type | Description | Example Usage |
|-------|-------------|----------------|
| `USER` | Human user | User actions via UI/CLI |
| `ADMIN` | Admin user | Administrative actions |
| `BOT` | Automated bot | Service account actions |
| `AUTOMATION` | AI agent | Agent execution |
| `SYSTEM` | System process | Background tasks |
| `WEBHOOK` | Webhook trigger | External callbacks |
| `SERVICE_ACCOUNT` | Service account | Non-human authentication |

### Environment Variable Reference

| Variable | Type | Default | Description |
|-----------|------|---------|-------------|
| `ENTERPRISE_AUDIT_ENABLED` | bool | true (enterprise) | Enable audit logging |
| `ENTERPRISE_AUDIT_LOG_PATH` | path | .auto-claude/enterprise/audit | Audit log directory |
| `ENTERPRISE_AUDIT_RETENTION_DAYS` | int | 90 | Log retention period |
| `ENTERPRISE_AUDIT_MAX_FILE_SIZE_MB` | int | 100 | Max file size before rotation |

### Compliance Mapping

**SOC2 Controls:**

| SOC2 Control | Audit Events | Evidence |
|-------------|---------------|----------|
| Access Control | `sso_login_*`, `permission_*`, `role_*` | Authentication, authorization logs |
| Change Management | `config_updated`, `admin_action` | Configuration changes |
| Data Protection | `data_residency_*`, `data_transfer_*` | Data residency checks |
| Monitoring | `anomaly_detected`, `vulnerability_detected` | Security monitoring |

**GDPR Controls:**

| GDPR Article | Audit Events | Evidence |
|--------------|---------------|----------|
| Article 30 (Records) | All events | Complete processing record |
| Article 32 (Security) | `security_scan_*`, `anomaly_detected` | Security measures |
| Article 33 (Breach) | `data_residency_violation` | Breach detection |
| Articles 12-23 (Rights) | `data_deletion_*`, `data_export_*` | Rights fulfillment |

---

<div align="center">

**Audit Logging Guide**

[← Back to Deployment Guide](DEPLOYMENT_GUIDE.md)

</div>
