#!/usr/bin/env python3
"""
Collaboration Permission System
================================

Role-based access control for multi-user spec collaboration.

Key features:
- Role-based access (READ, WRITE, ADMIN)
- Permission verification for specs
- Spec owner detection and automatic admin rights
- Permission caching to reduce lookups
- Comprehensive permission denial logging

Permission levels:
- READ: Can view spec and comments
- WRITE: Can comment and edit spec
- ADMIN: Can manage permissions and approve

Usage:
    checker = PermissionChecker(spec_id="001-feature")

    # Grant permission
    checker.grant_permission(
        user_id="alice",
        username="Alice",
        level=PermissionLevel.WRITE,
        granted_by="bob"
    )

    # Check permission
    result = checker.check_permission("alice", PermissionLevel.WRITE)
    if result.allowed:
        # User can write to spec
        pass

    # Quick checks
    if checker.has_read_access("alice"):
        # User can read spec
        pass
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .models import CollaborationUser, PermissionLevel, SpecPermission

logger = logging.getLogger(__name__)


@dataclass
class PermissionCheckResult:
    """Result of a permission check."""

    allowed: bool
    user_id: str
    level: PermissionLevel | None
    reason: str | None = None


class PermissionError(Exception):
    """Raised when permission checks fail."""

    pass


class PermissionChecker:
    """
    Verifies permissions for spec collaboration actions.

    Manages role-based access control with three permission levels:
    - READ: View spec and comments
    - WRITE: Comment and edit spec
    - ADMIN: Manage permissions and approve

    The spec owner (creator) automatically gets ADMIN rights.

    Usage:
        checker = PermissionChecker(
            spec_id="001-feature",
            owner_user_id="alice"
        )

        # Grant permission to team member
        checker.grant_permission(
            user_id="bob",
            username="Bob",
            level=PermissionLevel.WRITE,
            granted_by="alice"
        )

        # Check if user can write
        result = checker.check_permission("bob", PermissionLevel.WRITE)
        if result.allowed:
            # Proceed with write operation
            pass
    """

    def __init__(
        self,
        spec_id: str,
        owner_user_id: str | None = None,
        permissions: dict[str, SpecPermission] | None = None,
    ):
        """
        Initialize permission checker for a spec.

        Args:
            spec_id: Spec identifier (e.g., "001-feature-name")
            owner_user_id: Optional spec owner user ID (gets automatic ADMIN)
            permissions: Optional pre-loaded permissions dict (user_id -> SpecPermission)
        """
        self.spec_id = spec_id
        self.owner_user_id = owner_user_id

        # Permission storage: user_id -> SpecPermission
        self._permissions: dict[str, SpecPermission] = permissions or {}

        # Cache for quick permission lookups
        self._permission_cache: dict[tuple[str, PermissionLevel], bool] = {}

        logger.info(
            f"Initialized permission checker for spec {spec_id} "
            f"(owner: {owner_user_id or 'not set'})"
        )

    def grant_permission(
        self,
        user_id: str,
        username: str,
        level: PermissionLevel,
        granted_by: str,
        email: str | None = None,
    ) -> SpecPermission:
        """
        Grant a permission to a user for this spec.

        Args:
            user_id: Unique user identifier
            username: Display name
            level: Permission level to grant
            granted_by: Username of admin granting permission
            email: Optional user email

        Returns:
            The created SpecPermission object

        Raises:
            ValueError: If inputs are invalid
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        user = CollaborationUser(user_id=user_id, username=username, email=email)

        permission = SpecPermission(
            spec_id=self.spec_id,
            user=user,
            level=level,
            granted_by=granted_by,
        )

        # Store permission
        self._permissions[user_id] = permission

        # Clear cache for this user
        self._clear_user_cache(user_id)

        logger.info(
            f"Granted {level.value} permission to {username} ({user_id}) "
            f"on spec {self.spec_id} by {granted_by}"
        )

        return permission

    def revoke_permission(self, user_id: str) -> bool:
        """
        Revoke all permissions for a user on this spec.

        Args:
            user_id: User whose permissions to revoke

        Returns:
            True if permission was revoked, False if user had no permissions

        Raises:
            PermissionError: If trying to revoke owner's permissions
        """
        # Cannot revoke owner's implicit admin rights
        if self.owner_user_id and user_id == self.owner_user_id:
            raise PermissionError(
                f"Cannot revoke permissions for spec owner {user_id}"
            )

        if user_id not in self._permissions:
            logger.warning(f"No permission to revoke for user {user_id}")
            return False

        permission = self._permissions[user_id]
        del self._permissions[user_id]

        # Clear cache for this user
        self._clear_user_cache(user_id)

        logger.info(
            f"Revoked {permission.level.value} permission from "
            f"{permission.user.username} ({user_id}) on spec {self.spec_id}"
        )

        return True

    def check_permission(
        self, user_id: str, required_level: PermissionLevel
    ) -> PermissionCheckResult:
        """
        Check if a user has the required permission level.

        Permission hierarchy:
        - ADMIN includes WRITE and READ
        - WRITE includes READ
        - READ is the base level

        Args:
            user_id: User to check
            required_level: Minimum required permission level

        Returns:
            PermissionCheckResult with allowed status and details
        """
        # Check cache first
        cache_key = (user_id, required_level)
        if cache_key in self._permission_cache:
            cached = self._permission_cache[cache_key]
            return PermissionCheckResult(
                allowed=cached,
                user_id=user_id,
                level=self._get_user_permission_level(user_id),
                reason="cached" if cached else "cached denial",
            )

        # Owner always has admin access
        if self.owner_user_id and user_id == self.owner_user_id:
            result = PermissionCheckResult(
                allowed=True,
                user_id=user_id,
                level=PermissionLevel.ADMIN,
                reason="spec owner",
            )
            self._permission_cache[cache_key] = True
            return result

        # Check explicit permissions
        if user_id not in self._permissions:
            result = PermissionCheckResult(
                allowed=False,
                user_id=user_id,
                level=None,
                reason=f"no permission granted for spec {self.spec_id}",
            )
            self._permission_cache[cache_key] = False
            logger.warning(
                f"Permission denied for {user_id}: no permission on spec {self.spec_id}"
            )
            return result

        permission = self._permissions[user_id]
        user_level = permission.level

        # Check permission hierarchy
        allowed = self._is_level_sufficient(user_level, required_level)

        result = PermissionCheckResult(
            allowed=allowed,
            user_id=user_id,
            level=user_level,
            reason=(
                f"has {user_level.value}"
                if allowed
                else f"has {user_level.value}, needs {required_level.value}"
            ),
        )

        # Cache result
        self._permission_cache[cache_key] = allowed

        if not allowed:
            logger.warning(
                f"Permission denied for {permission.user.username} ({user_id}): "
                f"has {user_level.value}, needs {required_level.value} "
                f"for spec {self.spec_id}"
            )

        return result

    def has_read_access(self, user_id: str) -> bool:
        """
        Check if user has read access to the spec.

        Args:
            user_id: User to check

        Returns:
            True if user can read the spec
        """
        result = self.check_permission(user_id, PermissionLevel.READ)
        return result.allowed

    def has_write_access(self, user_id: str) -> bool:
        """
        Check if user has write access to the spec.

        Args:
            user_id: User to check

        Returns:
            True if user can write to the spec
        """
        result = self.check_permission(user_id, PermissionLevel.WRITE)
        return result.allowed

    def has_admin_access(self, user_id: str) -> bool:
        """
        Check if user has admin access to the spec.

        Args:
            user_id: User to check

        Returns:
            True if user can manage the spec
        """
        result = self.check_permission(user_id, PermissionLevel.ADMIN)
        return result.allowed

    def get_user_permission(self, user_id: str) -> SpecPermission | None:
        """
        Get the explicit permission record for a user.

        Note: Does not return implicit owner permissions.

        Args:
            user_id: User to look up

        Returns:
            SpecPermission if user has explicit permission, None otherwise
        """
        return self._permissions.get(user_id)

    def get_all_permissions(self) -> list[SpecPermission]:
        """
        Get all explicit permissions for this spec.

        Returns:
            List of all SpecPermission objects
        """
        return list(self._permissions.values())

    def get_users_with_level(self, level: PermissionLevel) -> list[CollaborationUser]:
        """
        Get all users with a specific permission level.

        Args:
            level: Permission level to filter by

        Returns:
            List of users with exactly this permission level
        """
        return [
            perm.user for perm in self._permissions.values() if perm.level == level
        ]

    def clear_cache(self) -> None:
        """Clear the permission check cache."""
        self._permission_cache.clear()
        logger.debug(f"Cleared permission cache for spec {self.spec_id}")

    def _get_user_permission_level(self, user_id: str) -> PermissionLevel | None:
        """Get the permission level for a user (including owner)."""
        if self.owner_user_id and user_id == self.owner_user_id:
            return PermissionLevel.ADMIN

        if user_id in self._permissions:
            return self._permissions[user_id].level

        return None

    def _is_level_sufficient(
        self, user_level: PermissionLevel, required_level: PermissionLevel
    ) -> bool:
        """
        Check if user's permission level meets the required level.

        Permission hierarchy:
        ADMIN > WRITE > READ
        """
        level_hierarchy = {
            PermissionLevel.READ: 1,
            PermissionLevel.WRITE: 2,
            PermissionLevel.ADMIN: 3,
        }

        user_rank = level_hierarchy[user_level]
        required_rank = level_hierarchy[required_level]

        return user_rank >= required_rank

    def _clear_user_cache(self, user_id: str) -> None:
        """Clear cache entries for a specific user."""
        keys_to_remove = [
            key for key in self._permission_cache if key[0] == user_id
        ]
        for key in keys_to_remove:
            del self._permission_cache[key]


# Convenience function for quick permission checks
def check_permission(
    spec_id: str,
    user_id: str,
    required_level: PermissionLevel,
    owner_user_id: str | None = None,
    permissions: dict[str, SpecPermission] | None = None,
) -> PermissionCheckResult:
    """
    Quick permission check without creating a persistent checker.

    Args:
        spec_id: Spec to check permission for
        user_id: User to check
        required_level: Minimum required permission level
        owner_user_id: Optional spec owner (gets automatic ADMIN)
        permissions: Optional pre-loaded permissions dict

    Returns:
        PermissionCheckResult with allowed status and details

    Example:
        result = check_permission(
            spec_id="001-feature",
            user_id="alice",
            required_level=PermissionLevel.WRITE,
            owner_user_id="bob",
            permissions={...}
        )

        if result.allowed:
            # User can write
            pass
    """
    checker = PermissionChecker(
        spec_id=spec_id, owner_user_id=owner_user_id, permissions=permissions
    )
    return checker.check_permission(user_id, required_level)
