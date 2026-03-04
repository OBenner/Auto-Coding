"""
Enterprise Security & Compliance Module
========================================

Provides enterprise-grade security and compliance features including:
- Comprehensive audit logging for all operations
- SSO/SAML authentication tracking
- Data residency compliance monitoring
- Role-based access control (RBAC) logging
- Compliance reporting (SOC2, GDPR, HIPAA)
"""

from enterprise.audit import (
    ActorType,
    AuditAction,
    AuditContext,
    AuditEntry,
    EnterpriseAuditLogger,
    audit_operation,
    get_audit_logger,
)

__all__ = [
    "EnterpriseAuditLogger",
    "AuditAction",
    "AuditContext",
    "AuditEntry",
    "ActorType",
    "get_audit_logger",
    "audit_operation",
]
