"""
Enterprise Permission Controls
===============================

Role-based access control (RBAC) for enterprise users.

Features:
- Role definitions with hierarchical permissions
- Permission checking for agent operations
- Integration with SSO/SAML for role assignment
- Audit logging for permission checks
- Policy-based access control

Supported Roles:
- ADMIN: Full access to all operations
- DEVELOPER: Can create and modify specs, run builds
- VIEWER: Read-only access to specs and audit logs
- AUDITOR: Access to audit logs and compliance reports
- OPERATOR: Can run builds but not modify specs
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Configure module logger
logger = logging.getLogger(__name__)


class Role(str, Enum):
    """Enterprise user roles with hierarchical permissions."""

    ADMIN = "admin"
    DEVELOPER = "developer"
    OPERATOR = "operator"
    AUDITOR = "auditor"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Granular permissions for different operations."""

    # Spec management permissions
    SPEC_CREATE = "spec_create"
    SPEC_READ = "spec_read"
    SPEC_UPDATE = "spec_update"
    SPEC_DELETE = "spec_delete"

    # Build execution permissions
    BUILD_RUN = "build_run"
    BUILD_STOP = "build_stop"
    BUILD_REVIEW = "build_review"
    BUILD_MERGE = "build_merge"
    BUILD_DISCARD = "build_discard"

    # Agent permissions
    AGENT_PLANNER_RUN = "agent_planner_run"
    AGENT_CODER_RUN = "agent_coder_run"
    AGENT_QA_RUN = "agent_qa_run"

    # Code permissions
    CODE_READ = "code_read"
    CODE_WRITE = "code_write"
    CODE_EXECUTE = "code_execute"
    CODE_REVIEW = "code_review"

    # Audit and compliance permissions
    AUDIT_READ = "audit_read"
    AUDIT_EXPORT = "audit_export"
    COMPLIANCE_READ = "compliance_read"
    COMPLIANCE_EXPORT = "compliance_export"

    # Configuration permissions
    CONFIG_READ = "config_read"
    CONFIG_UPDATE = "config_update"
    SSO_CONFIGURE = "sso_configure"
    DATA_RESIDENCY_CONFIGURE = "data_residency_configure"

    # User management permissions
    USER_CREATE = "user_create"
    USER_READ = "user_read"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    ROLE_ASSIGN = "role_assign"


@dataclass
class PermissionPolicy:
    """Permission policy for a role."""

    role: Role
    permissions: set[Permission] = field(default_factory=set)
    description: str = ""

    def has_permission(self, permission: Permission) -> bool:
        """Check if this role has a specific permission."""
        return permission in self.permissions

    def grant_permission(self, permission: Permission) -> None:
        """Grant a permission to this role."""
        self.permissions.add(permission)

    def revoke_permission(self, permission: Permission) -> None:
        """Revoke a permission from this role."""
        self.permissions.discard(permission)


# Default permission policies for each role
DEFAULT_POLICIES: dict[Role, PermissionPolicy] = {
    Role.ADMIN: PermissionPolicy(
        role=Role.ADMIN,
        permissions={
            # Full access to everything
            Permission.SPEC_CREATE,
            Permission.SPEC_READ,
            Permission.SPEC_UPDATE,
            Permission.SPEC_DELETE,
            Permission.BUILD_RUN,
            Permission.BUILD_STOP,
            Permission.BUILD_REVIEW,
            Permission.BUILD_MERGE,
            Permission.BUILD_DISCARD,
            Permission.AGENT_PLANNER_RUN,
            Permission.AGENT_CODER_RUN,
            Permission.AGENT_QA_RUN,
            Permission.CODE_READ,
            Permission.CODE_WRITE,
            Permission.CODE_EXECUTE,
            Permission.CODE_REVIEW,
            Permission.AUDIT_READ,
            Permission.AUDIT_EXPORT,
            Permission.COMPLIANCE_READ,
            Permission.COMPLIANCE_EXPORT,
            Permission.CONFIG_READ,
            Permission.CONFIG_UPDATE,
            Permission.SSO_CONFIGURE,
            Permission.DATA_RESIDENCY_CONFIGURE,
            Permission.USER_CREATE,
            Permission.USER_READ,
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
            Permission.ROLE_ASSIGN,
        },
        description="Full administrative access to all operations",
    ),
    Role.DEVELOPER: PermissionPolicy(
        role=Role.DEVELOPER,
        permissions={
            # Spec and build operations
            Permission.SPEC_CREATE,
            Permission.SPEC_READ,
            Permission.SPEC_UPDATE,
            Permission.SPEC_DELETE,
            Permission.BUILD_RUN,
            Permission.BUILD_STOP,
            Permission.BUILD_REVIEW,
            Permission.BUILD_MERGE,
            Permission.BUILD_DISCARD,
            # Agent operations
            Permission.AGENT_PLANNER_RUN,
            Permission.AGENT_CODER_RUN,
            Permission.AGENT_QA_RUN,
            # Code operations
            Permission.CODE_READ,
            Permission.CODE_WRITE,
            Permission.CODE_EXECUTE,
            Permission.CODE_REVIEW,
            # Limited audit access
            Permission.AUDIT_READ,
            # Limited config access
            Permission.CONFIG_READ,
        },
        description="Can create and modify specs, run builds, and write code",
    ),
    Role.OPERATOR: PermissionPolicy(
        role=Role.OPERATOR,
        permissions={
            # Read-only spec access
            Permission.SPEC_READ,
            # Build operations (but not merge/discard)
            Permission.BUILD_RUN,
            Permission.BUILD_STOP,
            Permission.BUILD_REVIEW,
            # Agent operations
            Permission.AGENT_PLANNER_RUN,
            Permission.AGENT_CODER_RUN,
            Permission.AGENT_QA_RUN,
            # Limited code access
            Permission.CODE_READ,
            Permission.CODE_EXECUTE,
            Permission.CODE_REVIEW,
            # Audit read
            Permission.AUDIT_READ,
            # Config read
            Permission.CONFIG_READ,
        },
        description="Can run builds but not modify specs or merge changes",
    ),
    Role.AUDITOR: PermissionPolicy(
        role=Role.AUDITOR,
        permissions={
            # Read-only access
            Permission.SPEC_READ,
            Permission.BUILD_REVIEW,
            Permission.CODE_READ,
            Permission.CODE_REVIEW,
            # Full audit and compliance access
            Permission.AUDIT_READ,
            Permission.AUDIT_EXPORT,
            Permission.COMPLIANCE_READ,
            Permission.COMPLIANCE_EXPORT,
            # Config read
            Permission.CONFIG_READ,
            # User read
            Permission.USER_READ,
        },
        description="Access to audit logs and compliance reports",
    ),
    Role.VIEWER: PermissionPolicy(
        role=Role.VIEWER,
        permissions={
            # Read-only access
            Permission.SPEC_READ,
            Permission.BUILD_REVIEW,
            Permission.CODE_READ,
            Permission.AUDIT_READ,
            Permission.CONFIG_READ,
        },
        description="Read-only access to specs and audit logs",
    ),
}


def get_role_permissions(role: Role) -> set[Permission]:
    """
    Get all permissions for a role.

    Args:
        role: The role to get permissions for

    Returns:
        Set of permissions granted to this role
    """
    policy = DEFAULT_POLICIES.get(role)
    if not policy:
        logger.warning(f"Unknown role: {role}, returning empty permissions")
        return set()
    return policy.permissions.copy()


def has_permission(role: Role, permission: Permission) -> bool:
    """
    Check if a role has a specific permission.

    Args:
        role: The role to check
        permission: The permission to check for

    Returns:
        True if role has permission, False otherwise
    """
    policy = DEFAULT_POLICIES.get(role)
    if not policy:
        logger.warning(f"Unknown role: {role}, denying permission {permission}")
        return False
    return policy.has_permission(permission)


def check_permission(
    role: Role | str,
    permission: Permission | str,
    user_id: str | None = None,
    resource: str | None = None,
) -> tuple[bool, str]:
    """
    Check if a role has permission and return detailed result.

    This function validates permissions and returns both a boolean result
    and a human-readable reason for the decision.

    Args:
        role: User role (Role enum or string)
        permission: Required permission (Permission enum or string)
        user_id: Optional user ID for audit logging
        resource: Optional resource identifier

    Returns:
        (is_allowed, reason) tuple
    """
    # Convert strings to enums if needed
    if isinstance(role, str):
        try:
            role = Role(role)
        except ValueError:
            reason = f"Invalid role: {role}"
            logger.warning(f"Permission denied for user {user_id}: {reason}")
            return False, reason

    if isinstance(permission, str):
        try:
            permission = Permission(permission)
        except ValueError:
            reason = f"Invalid permission: {permission}"
            logger.warning(f"Permission denied for user {user_id}: {reason}")
            return False, reason

    # Check permission
    is_allowed = has_permission(role, permission)

    if is_allowed:
        reason = f"Role {role.value} has permission {permission.value}"
        logger.info(
            f"Permission granted: user={user_id}, role={role.value}, "
            f"permission={permission.value}, resource={resource}"
        )
    else:
        reason = f"Role {role.value} does not have permission {permission.value}"
        logger.warning(
            f"Permission denied: user={user_id}, role={role.value}, "
            f"permission={permission.value}, resource={resource}"
        )

    return is_allowed, reason


def get_role_hierarchy() -> dict[Role, int]:
    """
    Get role hierarchy levels (higher = more permissions).

    Returns:
        Dict mapping roles to their hierarchy level
    """
    return {
        Role.ADMIN: 100,
        Role.DEVELOPER: 75,
        Role.OPERATOR: 50,
        Role.AUDITOR: 40,
        Role.VIEWER: 25,
    }


def is_higher_role(role1: Role, role2: Role) -> bool:
    """
    Check if role1 has higher privilege level than role2.

    Args:
        role1: First role to compare
        role2: Second role to compare

    Returns:
        True if role1 has higher privilege than role2
    """
    hierarchy = get_role_hierarchy()
    return hierarchy.get(role1, 0) > hierarchy.get(role2, 0)


# ============================================================================
# Permission Checking Decorators and Middleware
# ============================================================================


class PermissionDeniedError(Exception):
    """Exception raised when permission check fails."""

    def __init__(
        self,
        message: str,
        role: Role | None = None,
        permission: Permission | None = None,
    ):
        super().__init__(message)
        self.role = role
        self.permission = permission


def _resolve_role(role: str | Role | None, user_id: str | None, context: str) -> Role:
    """
    Convert role string to Role enum, raising PermissionDeniedError on failure.

    Args:
        role: Role string or enum (None raises error)
        user_id: User identifier for logging
        context: Context description (e.g. "permission check", "role check")

    Returns:
        Validated Role enum

    Raises:
        PermissionDeniedError: If role is None or invalid
    """
    if role is None:
        error_msg = f"Missing 'role' parameter for {context}"
        logger.error(error_msg)
        raise PermissionDeniedError(error_msg)

    if isinstance(role, str):
        try:
            return Role(role)
        except ValueError:
            error_msg = f"Invalid role: {role}"
            logger.warning(
                f"{context.capitalize()} failed for user {user_id}: {error_msg}"
            )
            raise PermissionDeniedError(error_msg, role=None)

    return role


def _enforce_permission(
    role: str | Role | None,
    permission_enum: Permission,
    user_id: str | None,
    func_name: str,
) -> None:
    """
    Validate role and check permission, raising on denial.

    Args:
        role: User role (string or enum)
        permission_enum: Required permission
        user_id: User identifier for logging
        func_name: Function name for logging
    """
    resolved = _resolve_role(role, user_id, "permission check")
    is_allowed, reason = check_permission(resolved, permission_enum, user_id, func_name)
    if not is_allowed:
        raise PermissionDeniedError(reason, role=resolved, permission=permission_enum)


def _enforce_role(
    role: str | Role | None,
    required_role_enum: Role,
    user_id: str | None,
    func_name: str,
) -> None:
    """
    Validate role and check hierarchy level, raising on denial.

    Args:
        role: User role (string or enum)
        required_role_enum: Minimum required role
        user_id: User identifier for logging
        func_name: Function name for logging
    """
    resolved = _resolve_role(role, user_id, "role check")
    hierarchy = get_role_hierarchy()
    user_level = hierarchy.get(resolved, 0)
    required_level = hierarchy.get(required_role_enum, 0)

    if user_level < required_level:
        reason = (
            f"Role {resolved.value} (level {user_level}) does not meet "
            f"requirement {required_role_enum.value} (level {required_level})"
        )
        logger.warning(f"Role check failed: user={user_id}, {reason}")
        raise PermissionDeniedError(reason, role=resolved)

    logger.info(
        f"Role check passed: user={user_id}, role={resolved.value}, "
        f"required={required_role_enum.value}, function={func_name}"
    )


def _access_check_decorator(check_fn, user_id_param: str = "user_id"):
    """
    Generic decorator factory for access control checks.

    Creates a decorator that extracts role/user_id from kwargs and calls
    check_fn(role, user_id, func_name) before executing the wrapped function.
    Works with both sync and async functions.
    """
    import functools
    import inspect

    def decorator(func):
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                check_fn(kwargs.get("role"), kwargs.get(user_id_param), func.__name__)
                return await func(*args, **kwargs)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            check_fn(kwargs.get("role"), kwargs.get(user_id_param), func.__name__)
            return func(*args, **kwargs)

        return sync_wrapper

    return decorator


def require_permission(permission: Permission | str, user_id_param: str = "user_id"):
    """
    Decorator that checks if user has required permission before executing function.

    Works with both sync and async functions. Extracts user's role from kwargs.

    Raises:
        PermissionDeniedError: If user lacks required permission
    """
    if isinstance(permission, str):
        try:
            permission_enum = Permission(permission)
        except ValueError:
            raise ValueError(f"Invalid permission string: {permission}")
    else:
        permission_enum = permission

    def check(role, user_id, func_name):
        _enforce_permission(role, permission_enum, user_id, func_name)

    return _access_check_decorator(check, user_id_param)


def require_role(required_role: Role | str, user_id_param: str = "user_id"):
    """
    Decorator that checks if user has required role before executing function.

    Works with both sync and async functions. Checks role hierarchy.

    Raises:
        PermissionDeniedError: If user lacks required role
    """
    if isinstance(required_role, str):
        try:
            required_role_enum = Role(required_role)
        except ValueError:
            raise ValueError(f"Invalid role string: {required_role}")
    else:
        required_role_enum = required_role

    def check(role, user_id, func_name):
        _enforce_role(role, required_role_enum, user_id, func_name)

    return _access_check_decorator(check, user_id_param)


async def permission_check_hook(
    input_data: dict[str, Any],
    context: Any | None = None,
) -> dict[str, Any]:
    """
    Pre-operation hook that validates user permissions.

    This hook is similar to bash_security_hook but for general operations.
    It checks if the user has the required permission before allowing the
    operation to proceed.

    Args:
        input_data: Dict containing operation, user_id, role, and permission
        context: Optional context object

    Returns:
        Empty dict to allow, or {"decision": "block", "reason": "..."} to block

    Example input_data:
        {
            "operation": "spec_create",
            "user_id": "user@example.com",
            "role": "developer",
            "permission": "spec_create",
            "resource": "spec-001"
        }
    """
    # Validate input_data structure
    if not isinstance(input_data, dict):
        return {
            "decision": "block",
            "reason": f"Invalid input_data type: expected dict, got {type(input_data).__name__}",
        }

    # Extract required fields
    operation = input_data.get("operation")
    user_id = input_data.get("user_id")
    role = input_data.get("role")
    permission = input_data.get("permission")
    resource = input_data.get("resource")

    # Validate required fields
    if not operation:
        return {
            "decision": "block",
            "reason": "Missing required field: operation",
        }

    if not role:
        return {
            "decision": "block",
            "reason": "Missing required field: role",
        }

    if not permission:
        return {
            "decision": "block",
            "reason": "Missing required field: permission",
        }

    # Convert strings to enums
    try:
        if isinstance(role, str):
            role = Role(role)
    except ValueError:
        reason = f"Invalid role: {role}"
        logger.warning(f"Permission hook blocked operation {operation}: {reason}")
        return {"decision": "block", "reason": reason}

    try:
        if isinstance(permission, str):
            permission = Permission(permission)
    except ValueError:
        reason = f"Invalid permission: {permission}"
        logger.warning(f"Permission hook blocked operation {operation}: {reason}")
        return {"decision": "block", "reason": reason}

    # Check permission
    is_allowed, reason = check_permission(role, permission, user_id, resource)

    if not is_allowed:
        logger.warning(
            f"Permission hook blocked operation: operation={operation}, "
            f"user={user_id}, role={role.value}, permission={permission.value}, "
            f"resource={resource}"
        )
        return {"decision": "block", "reason": reason}

    # Permission granted
    logger.info(
        f"Permission hook allowed operation: operation={operation}, "
        f"user={user_id}, role={role.value}, permission={permission.value}, "
        f"resource={resource}"
    )
    return {}


def validate_permission_input(
    role: Role | str,
    permission: Permission | str,
    operation: str | None = None,
) -> tuple[bool, str]:
    """
    Validate permission input for testing/debugging.

    Delegates to check_permission which handles string-to-enum conversion.

    Args:
        role: User role (Role enum or string)
        permission: Required permission (Permission enum or string)
        operation: Optional operation name for logging

    Returns:
        (is_allowed, reason) tuple
    """
    return check_permission(role, permission, resource=operation)
