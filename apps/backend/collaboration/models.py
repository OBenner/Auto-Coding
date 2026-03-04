#!/usr/bin/env python3
"""
Collaboration Models
====================

Data classes and enums for multi-user spec collaboration.

Defines models for:
- Users (CollaborationUser)
- Permissions (SpecPermission with read/write/admin levels)
- Comments (Comment with threading and @mentions)
- Approvals (Approval workflow for spec review)
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission levels for spec collaboration."""

    READ = "read"  # Can view spec and comments
    WRITE = "write"  # Can comment and edit spec
    ADMIN = "admin"  # Can manage permissions and approve


class ApprovalStatus(Enum):
    """Approval workflow statuses."""

    PENDING = "pending"  # Awaiting review
    APPROVED = "approved"  # Spec approved, build can start
    REJECTED = "rejected"  # Spec rejected, needs revision


@dataclass
class CollaborationUser:
    """
    Represents a user in the collaboration system.

    Attributes:
        user_id: Unique identifier for the user
        username: Display name
        email: Optional email address
    """

    user_id: str
    username: str
    email: str | None = None

    def __post_init__(self):
        """Validate user fields."""
        if not self.user_id or not self.user_id.strip():
            raise ValueError("user_id cannot be empty")
        if not self.username or not self.username.strip():
            raise ValueError("username cannot be empty")


@dataclass
class SpecPermission:
    """
    Permission grant for a user on a specific spec.

    Attributes:
        spec_id: Spec identifier (e.g., "001-feature-name")
        user: User who has this permission
        level: Permission level (READ, WRITE, ADMIN)
        granted_by: Username of admin who granted permission
        granted_at: ISO timestamp when permission was granted
    """

    spec_id: str
    user: CollaborationUser
    level: PermissionLevel
    granted_by: str
    granted_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self):
        """Validate permission fields."""
        if not self.spec_id or not self.spec_id.strip():
            raise ValueError("spec_id cannot be empty")
        if not self.granted_by or not self.granted_by.strip():
            raise ValueError("granted_by cannot be empty")

    def has_write_access(self) -> bool:
        """Check if this permission includes write access."""
        return self.level in [PermissionLevel.WRITE, PermissionLevel.ADMIN]

    def has_admin_access(self) -> bool:
        """Check if this permission includes admin access."""
        return self.level == PermissionLevel.ADMIN


@dataclass
class Comment:
    """
    A comment in a spec discussion thread.

    Supports threaded replies and @mentions for notifications.

    Attributes:
        comment_id: Unique identifier for this comment
        spec_id: Spec this comment belongs to
        author: User who wrote the comment
        content: Comment text (supports markdown)
        created_at: ISO timestamp when comment was created
        parent_id: Optional parent comment ID for threaded replies
        mentions: List of usernames mentioned with @
        resolved: Whether this discussion thread is resolved
        updated_at: ISO timestamp of last edit (None if never edited)
    """

    comment_id: str
    spec_id: str
    author: CollaborationUser
    content: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    parent_id: str | None = None
    mentions: list[str] = field(default_factory=list)
    resolved: bool = False
    updated_at: str | None = None

    def __post_init__(self):
        """Validate comment fields and extract mentions."""
        if not self.comment_id or not self.comment_id.strip():
            raise ValueError("comment_id cannot be empty")
        if not self.spec_id or not self.spec_id.strip():
            raise ValueError("spec_id cannot be empty")
        if not self.content or not self.content.strip():
            raise ValueError("content cannot be empty")

        # Auto-extract @mentions if not provided
        if not self.mentions:
            self.mentions = self._extract_mentions(self.content)

    def _extract_mentions(self, text: str) -> list[str]:
        """
        Extract @username mentions from text.

        Args:
            text: Comment text to parse

        Returns:
            List of mentioned usernames (without @ prefix)
        """
        import re

        # Match @username pattern (letters, numbers, hyphens, underscores)
        pattern = r"@([a-zA-Z0-9_-]+)"
        matches = re.findall(pattern, text)
        return list(dict.fromkeys(matches))  # Remove duplicates, preserve order

    def is_reply(self) -> bool:
        """Check if this is a reply to another comment."""
        return self.parent_id is not None

    def mark_resolved(self) -> None:
        """Mark this comment thread as resolved."""
        self.resolved = True
        logger.info(f"Comment {self.comment_id} marked as resolved")

    def mark_edited(self) -> None:
        """Update the edited timestamp."""
        self.updated_at = datetime.now(UTC).isoformat()


@dataclass
class Approval:
    """
    Approval or rejection record for a spec.

    Used in approval workflows to track who approved/rejected
    and whether build can proceed.

    Attributes:
        approval_id: Unique identifier for this approval record
        spec_id: Spec being approved/rejected
        approver: User providing approval/rejection
        status: Approval status (PENDING, APPROVED, REJECTED)
        reason: Optional explanation for decision
        created_at: ISO timestamp when approval was created
        reviewed_at: ISO timestamp when approval decision was made
    """

    approval_id: str
    spec_id: str
    approver: CollaborationUser
    status: ApprovalStatus
    reason: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    reviewed_at: str | None = None

    def __post_init__(self):
        """Validate approval fields."""
        if not self.approval_id or not self.approval_id.strip():
            raise ValueError("approval_id cannot be empty")
        if not self.spec_id or not self.spec_id.strip():
            raise ValueError("spec_id cannot be empty")

    def approve(self, reason: str | None = None) -> None:
        """
        Mark this approval as approved.

        Args:
            reason: Optional reason for approval
        """
        self.status = ApprovalStatus.APPROVED
        self.reason = reason
        self.reviewed_at = datetime.now(UTC).isoformat()
        logger.info(f"Spec {self.spec_id} approved")
        logger.debug(
            f"Approval by {self.approver.username}: {reason or 'No reason provided'}"
        )

    def reject(self, reason: str | None = None) -> None:
        """
        Mark this approval as rejected.

        Args:
            reason: Optional reason for rejection
        """
        self.status = ApprovalStatus.REJECTED
        self.reason = reason
        self.reviewed_at = datetime.now(UTC).isoformat()
        logger.info(f"Spec {self.spec_id} rejected")
        logger.debug(
            f"Rejection by {self.approver.username}: {reason or 'No reason provided'}"
        )

    def is_pending(self) -> bool:
        """Check if this approval is still pending review."""
        return self.status == ApprovalStatus.PENDING

    def is_approved(self) -> bool:
        """Check if this approval is approved."""
        return self.status == ApprovalStatus.APPROVED

    def is_rejected(self) -> bool:
        """Check if this approval is rejected."""
        return self.status == ApprovalStatus.REJECTED
