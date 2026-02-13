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

    def __init__(self, message: str, role: Role | None = None, permission: Permission | None = None):
        """
        Initialize permission denied error.

        Args:
            message: Error message
            role: Role that was denied (optional)
            permission: Permission that was required (optional)
        """
        super().__init__(message)
        self.role = role
        self.permission = permission


def require_permission(permission: Permission | str, user_id_param: str = "user_id"):
    """
    Decorator that checks if user has required permission before executing function.

    This decorator works with both sync and async functions. It extracts the user's
    role from kwargs and checks if they have the required permission.

    Args:
        permission: Required permission (Permission enum or string)
        user_id_param: Name of parameter containing user_id (default: "user_id")

    Returns:
        Decorated function that checks permission before execution

    Raises:
        PermissionDeniedError: If user lacks required permission

    Example:
        @require_permission(Permission.SPEC_CREATE)
        def create_spec(user_id: str, role: Role, spec_data: dict):
            # Only executes if user has SPEC_CREATE permission
            pass

        @require_permission("build_run", user_id_param="current_user")
        async def run_build(current_user: str, role: Role, spec_id: str):
            # Async function example
            pass
    """
    import functools
    import inspect

    # Convert string to Permission enum if needed
    if isinstance(permission, str):
        try:
            permission_enum = Permission(permission)
        except ValueError:
            raise ValueError(f"Invalid permission string: {permission}")
    else:
        permission_enum = permission

    def decorator(func):
        # Determine if function is async
        is_async = inspect.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Extract user_id and role from kwargs
                user_id = kwargs.get(user_id_param)
                role = kwargs.get("role")

                # Validate required parameters
                if role is None:
                    error_msg = "Missing 'role' parameter for permission check"
                    logger.error(f"{error_msg} in function {func.__name__}")
                    raise PermissionDeniedError(error_msg)

                # Convert string role to enum if needed
                if isinstance(role, str):
                    try:
                        role = Role(role)
                    except ValueError:
                        error_msg = f"Invalid role: {role}"
                        logger.warning(f"Permission denied for user {user_id}: {error_msg}")
                        raise PermissionDeniedError(error_msg, role=None, permission=permission_enum)

                # Check permission
                is_allowed, reason = check_permission(role, permission_enum, user_id, func.__name__)

                if not is_allowed:
                    raise PermissionDeniedError(reason, role=role, permission=permission_enum)

                # Execute function
                return await func(*args, **kwargs)

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Extract user_id and role from kwargs
                user_id = kwargs.get(user_id_param)
                role = kwargs.get("role")

                # Validate required parameters
                if role is None:
                    error_msg = "Missing 'role' parameter for permission check"
                    logger.error(f"{error_msg} in function {func.__name__}")
                    raise PermissionDeniedError(error_msg)

                # Convert string role to enum if needed
                if isinstance(role, str):
                    try:
                        role = Role(role)
                    except ValueError:
                        error_msg = f"Invalid role: {role}"
                        logger.warning(f"Permission denied for user {user_id}: {error_msg}")
                        raise PermissionDeniedError(error_msg, role=None, permission=permission_enum)

                # Check permission
                is_allowed, reason = check_permission(role, permission_enum, user_id, func.__name__)

                if not is_allowed:
                    raise PermissionDeniedError(reason, role=role, permission=permission_enum)

                # Execute function
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


def require_role(required_role: Role | str, user_id_param: str = "user_id"):
    """
    Decorator that checks if user has required role before executing function.

    This decorator works with both sync and async functions. It checks if the
    user's role matches or exceeds the required role in the hierarchy.

    Args:
        required_role: Required role (Role enum or string)
        user_id_param: Name of parameter containing user_id (default: "user_id")

    Returns:
        Decorated function that checks role before execution

    Raises:
        PermissionDeniedError: If user lacks required role

    Example:
        @require_role(Role.DEVELOPER)
        def developer_only_operation(user_id: str, role: Role):
            # Only DEVELOPER, ADMIN can execute
            pass

        @require_role("admin")
        async def admin_only_operation(user_id: str, role: Role):
            # Only ADMIN can execute
            pass
    """
    import functools
    import inspect

    # Convert string to Role enum if needed
    if isinstance(required_role, str):
        try:
            required_role_enum = Role(required_role)
        except ValueError:
            raise ValueError(f"Invalid role string: {required_role}")
    else:
        required_role_enum = required_role

    def decorator(func):
        # Determine if function is async
        is_async = inspect.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Extract user_id and role from kwargs
                user_id = kwargs.get(user_id_param)
                role = kwargs.get("role")

                # Validate required parameters
                if role is None:
                    error_msg = "Missing 'role' parameter for role check"
                    logger.error(f"{error_msg} in function {func.__name__}")
                    raise PermissionDeniedError(error_msg)

                # Convert string role to enum if needed
                if isinstance(role, str):
                    try:
                        role = Role(role)
                    except ValueError:
                        error_msg = f"Invalid role: {role}"
                        logger.warning(f"Role check failed for user {user_id}: {error_msg}")
                        raise PermissionDeniedError(error_msg, role=None)

                # Check if role meets requirement (same or higher in hierarchy)
                hierarchy = get_role_hierarchy()
                user_level = hierarchy.get(role, 0)
                required_level = hierarchy.get(required_role_enum, 0)

                if user_level < required_level:
                    reason = (
                        f"Role {role.value} (level {user_level}) does not meet "
                        f"requirement {required_role_enum.value} (level {required_level})"
                    )
                    logger.warning(f"Role check failed: user={user_id}, {reason}")
                    raise PermissionDeniedError(reason, role=role)

                logger.info(
                    f"Role check passed: user={user_id}, role={role.value}, "
                    f"required={required_role_enum.value}, function={func.__name__}"
                )

                # Execute function
                return await func(*args, **kwargs)

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Extract user_id and role from kwargs
                user_id = kwargs.get(user_id_param)
                role = kwargs.get("role")

                # Validate required parameters
                if role is None:
                    error_msg = "Missing 'role' parameter for role check"
                    logger.error(f"{error_msg} in function {func.__name__}")
                    raise PermissionDeniedError(error_msg)

                # Convert string role to enum if needed
                if isinstance(role, str):
                    try:
                        role = Role(role)
                    except ValueError:
                        error_msg = f"Invalid role: {role}"
                        logger.warning(f"Role check failed for user {user_id}: {error_msg}")
                        raise PermissionDeniedError(error_msg, role=None)

                # Check if role meets requirement (same or higher in hierarchy)
                hierarchy = get_role_hierarchy()
                user_level = hierarchy.get(role, 0)
                required_level = hierarchy.get(required_role_enum, 0)

                if user_level < required_level:
                    reason = (
                        f"Role {role.value} (level {user_level}) does not meet "
                        f"requirement {required_role_enum.value} (level {required_level})"
                    )
                    logger.warning(f"Role check failed: user={user_id}, {reason}")
                    raise PermissionDeniedError(reason, role=role)

                logger.info(
                    f"Role check passed: user={user_id}, role={role.value}, "
                    f"required={required_role_enum.value}, function={func.__name__}"
                )

                # Execute function
                return func(*args, **kwargs)

            return sync_wrapper

    return decorator


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

    # Convert strings to enums if needed
    if isinstance(role, str):
        try:
            role = Role(role)
        except ValueError:
            reason = f"Invalid role: {role}"
            logger.warning(f"Permission hook blocked operation {operation}: {reason}")
            return {"decision": "block", "reason": reason}

    if isinstance(permission, str):
        try:
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

    Args:
        role: User role (Role enum or string)
        permission: Required permission (Permission enum or string)
        operation: Optional operation name for logging

    Returns:
        (is_allowed, reason) tuple
    """
    # Convert strings to enums
    if isinstance(role, str):
        try:
            role = Role(role)
        except ValueError:
            return False, f"Invalid role: {role}"

    if isinstance(permission, str):
        try:
            permission = Permission(permission)
        except ValueError:
            return False, f"Invalid permission: {permission}"

    # Check permission
    is_allowed, reason = check_permission(role, permission, resource=operation)

    return is_allowed, reason
