#!/usr/bin/env python3
"""
Notification and Change History System
====================================

Manages notifications and change tracking for multi-user spec collaboration.

Key features:
- @mention notifications when users are tagged in comments
- Permission change notifications
- Approval workflow notifications
- Comprehensive change history tracking
- Graphiti storage integration

Usage:
    manager = NotificationManager(
        spec_id="001-feature",
        spec_dir=Path(".auto-claude/specs/001-feature"),
        project_dir=Path(".")
    )

    # Track comment with @mentions
    await manager.track_comment_mention(
        comment_id="abc-123",
        mentioned_usernames=["alice", "bob"],
        author_username="charlie"
    )

    # Track permission change
    await manager.track_permission_granted(
        username="alice",
        level="write",
        granted_by="admin"
    )

    # Get notifications for user
    notifications = await manager.get_notifications_for_user("alice")
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from integrations.graphiti.queries_pkg.schema import (
    EPISODE_TYPE_CHANGE_HISTORY,
    EPISODE_TYPE_NOTIFICATION,
)

from .base import CollaborationManagerBase

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications in the collaboration system."""

    MENTION = "mention"  # @mentioned in a comment
    PERMISSION_GRANTED = "permission_granted"  # Permission was granted
    PERMISSION_REVOKED = "permission_revoked"  # Permission was revoked
    APPROVAL_REQUESTED = "approval_requested"  # Approval requested
    APPROVAL_APPROVED = "approval_approved"  # Spec approved
    APPROVAL_REJECTED = "approval_rejected"  # Spec rejected
    SPEC_MODIFIED = "spec_modified"  # Spec was modified


class ChangeType(Enum):
    """Types of changes tracked in history."""

    COMMENT_ADDED = "comment_added"
    COMMENT_EDITED = "comment_edited"
    COMMENT_RESOLVED = "comment_resolved"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    SPEC_EDITED = "spec_edited"


@dataclass
class Notification:
    """
    A notification for a user about collaboration events.

    Attributes:
        notification_id: Unique identifier for this notification
        spec_id: Spec this notification relates to
        notification_type: Type of notification
        target_user: User who should receive this notification
        actor_user: User who triggered this notification
        created_at: ISO timestamp when notification was created
        read: Whether notification has been read
        metadata: Additional context (comment_id, permission_level, etc.)
    """

    notification_id: str
    spec_id: str
    notification_type: NotificationType
    target_user: str  # username
    actor_user: str  # username
    created_at: str
    read: bool = False
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "notification_id": self.notification_id,
            "spec_id": self.spec_id,
            "notification_type": self.notification_type.value,
            "target_user": self.target_user,
            "actor_user": self.actor_user,
            "created_at": self.created_at,
            "read": self.read,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Notification:
        """Create from dictionary."""
        return cls(
            notification_id=data["notification_id"],
            spec_id=data["spec_id"],
            notification_type=NotificationType(data["notification_type"]),
            target_user=data["target_user"],
            actor_user=data["actor_user"],
            created_at=data["created_at"],
            read=data.get("read", False),
            metadata=data.get("metadata"),
        )


@dataclass
class ChangeRecord:
    """
    A record of a change made to a spec.

    Tracks who changed what and when for full audit trail.

    Attributes:
        change_id: Unique identifier for this change
        spec_id: Spec that was changed
        change_type: Type of change
        actor_user: User who made the change
        created_at: ISO timestamp when change occurred
        details: Additional context about the change
    """

    change_id: str
    spec_id: str
    change_type: ChangeType
    actor_user: str
    created_at: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "change_id": self.change_id,
            "spec_id": self.spec_id,
            "change_type": self.change_type.value,
            "actor_user": self.actor_user,
            "created_at": self.created_at,
            "details": self.details or {},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChangeRecord:
        """Create from dictionary."""
        return cls(
            change_id=data["change_id"],
            spec_id=data["spec_id"],
            change_type=ChangeType(data["change_type"]),
            actor_user=data["actor_user"],
            created_at=data["created_at"],
            details=data.get("details"),
        )


class NotificationManager(CollaborationManagerBase):
    """
    Manages notifications and change history for spec collaboration.

    Provides:
    - Notification creation for various events
    - Change history tracking
    - Notification querying by user
    - Graphiti storage integration

    Usage:
        manager = NotificationManager(
            spec_id="001-feature",
            spec_dir=Path(".auto-claude/specs/001-feature"),
            project_dir=Path(".")
        )

        await manager.initialize()

        # Track @mentions
        await manager.track_comment_mention(
            comment_id="abc-123",
            mentioned_usernames=["alice", "bob"],
            author_username="charlie"
        )

        # Get notifications for user
        notifications = await manager.get_notifications_for_user("alice")
    """

    _manager_name = "notification"

    def __init__(
        self,
        spec_id: str,
        spec_dir: Path,
        project_dir: Path,
    ):
        """
        Initialize notification manager for a spec.

        Args:
            spec_id: Spec identifier (e.g., "001-feature-name")
            spec_dir: Path to spec directory (for Graphiti storage)
            project_dir: Project root directory
        """
        super().__init__(spec_id, spec_dir, project_dir)

        # In-memory notification cache: notification_id -> Notification
        self._notifications: dict[str, Notification] = {}

        # In-memory change history cache: change_id -> ChangeRecord
        self._change_history: dict[str, ChangeRecord] = {}

        # User notification index: username -> [notification_ids]
        self._user_notifications: dict[str, list[str]] = {}

        logger.info(f"Initialized notification manager for spec {spec_id}")

    async def track_comment_mention(
        self,
        comment_id: str,
        mentioned_usernames: list[str],
        author_username: str,
    ) -> list[Notification]:
        """
        Track @mentions in a comment and create notifications.

        Args:
            comment_id: ID of the comment with mentions
            mentioned_usernames: List of usernames who were @mentioned
            author_username: User who wrote the comment

        Returns:
            List of created Notification objects
        """
        notifications = []

        for username in mentioned_usernames:
            notification = Notification(
                notification_id=str(uuid.uuid4()),
                spec_id=self.spec_id,
                notification_type=NotificationType.MENTION,
                target_user=username,
                actor_user=author_username,
                created_at=datetime.now(UTC).isoformat(),
                metadata={"comment_id": comment_id},
            )

            # Store in cache
            self._notifications[notification.notification_id] = notification
            self._user_notifications.setdefault(username, []).append(
                notification.notification_id
            )

            notifications.append(notification)

            logger.info(
                f"Created mention notification for {username} "
                f"in comment {comment_id} by {author_username}"
            )

        # Persist to Graphiti
        if self._memory_available and notifications:
            for notification in notifications:
                await self._store_notification_in_graphiti(notification)

        return notifications

    async def track_permission_granted(
        self,
        username: str,
        level: str,
        granted_by: str,
    ) -> Notification:
        """
        Track when a permission is granted to a user.

        Args:
            username: User who received permission
            level: Permission level granted
            granted_by: Username of admin who granted permission

        Returns:
            Created Notification object
        """
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            spec_id=self.spec_id,
            notification_type=NotificationType.PERMISSION_GRANTED,
            target_user=username,
            actor_user=granted_by,
            created_at=datetime.now(UTC).isoformat(),
            metadata={"permission_level": level},
        )

        # Store in cache
        self._notifications[notification.notification_id] = notification
        self._user_notifications.setdefault(username, []).append(
            notification.notification_id
        )

        logger.info(
            f"Created permission notification for {username}: "
            f"{level} granted by {granted_by}"
        )

        # Add change record for audit trail
        await self._add_change_record(
            change_type=ChangeType.PERMISSION_GRANTED,
            actor_user=granted_by,
            details={"target_user": username, "permission_level": level},
        )

        # Persist to Graphiti
        if self._memory_available:
            await self._store_notification_in_graphiti(notification)

        return notification

    async def track_approval_requested(
        self,
        requested_by: str,
        admin_usernames: list[str] | None = None,
    ) -> list[Notification]:
        """
        Track when approval is requested for a spec.

        Creates notifications for all admins.

        Args:
            requested_by: User who requested approval
            admin_usernames: List of admin usernames to notify (if known)

        Returns:
            List of created Notification objects
        """
        await self._add_change_record(
            change_type=ChangeType.APPROVAL_REQUESTED,
            actor_user=requested_by,
            details={},
        )

        notifications: list[Notification] = []
        for admin_user in admin_usernames or []:
            notification = Notification(
                notification_id=str(uuid.uuid4()),
                spec_id=self.spec_id,
                notification_type=NotificationType.APPROVAL_REQUESTED,
                target_user=admin_user,
                actor_user=requested_by,
                created_at=datetime.now(UTC).isoformat(),
                metadata={},
            )

            self._notifications[notification.notification_id] = notification
            self._user_notifications.setdefault(admin_user, []).append(
                notification.notification_id
            )
            notifications.append(notification)

        if self._memory_available:
            for notification in notifications:
                await self._store_notification_in_graphiti(notification)

        logger.info(f"Tracked approval request by {requested_by}")
        return notifications

    async def track_approval_approved(
        self,
        approver: str,
    ) -> Notification:
        """
        Track when a spec is approved.

        Args:
            approver: Admin who approved the spec

        Returns:
            Created Notification object
        """
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            spec_id=self.spec_id,
            notification_type=NotificationType.APPROVAL_APPROVED,
            target_user=approver,  # Self-notification for history
            actor_user=approver,
            created_at=datetime.now(UTC).isoformat(),
            metadata={},
        )

        # Store in cache and user index
        self._notifications[notification.notification_id] = notification
        self._user_notifications.setdefault(approver, []).append(
            notification.notification_id
        )

        # Add to change history
        await self._add_change_record(
            change_type=ChangeType.APPROVAL_APPROVED,
            actor_user=approver,
            details={},
        )

        logger.info(f"Tracked approval by {approver}")

        # Persist to Graphiti
        if self._memory_available:
            await self._store_notification_in_graphiti(notification)

        return notification

    async def track_approval_rejected(
        self,
        approver: str,
        reason: str | None = None,
    ) -> Notification:
        """
        Track when a spec is rejected.

        Args:
            approver: Admin who rejected the spec
            reason: Optional rejection reason

        Returns:
            Created Notification object
        """
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            spec_id=self.spec_id,
            notification_type=NotificationType.APPROVAL_REJECTED,
            target_user=approver,  # Self-notification for history
            actor_user=approver,
            created_at=datetime.now(UTC).isoformat(),
            metadata={"reason": reason},
        )

        # Store in cache and user index
        self._notifications[notification.notification_id] = notification
        self._user_notifications.setdefault(approver, []).append(
            notification.notification_id
        )

        # Add to change history
        await self._add_change_record(
            change_type=ChangeType.APPROVAL_REJECTED,
            actor_user=approver,
            details={"reason": reason},
        )

        logger.info(f"Tracked rejection by {approver}: {reason}")

        # Persist to Graphiti
        if self._memory_available:
            await self._store_notification_in_graphiti(notification)

        return notification

    async def track_comment_added(
        self,
        comment_id: str,
        author_username: str,
    ) -> None:
        """
        Track when a comment is added to change history.

        Args:
            comment_id: ID of the comment
            author_username: User who added the comment
        """
        await self._add_change_record(
            change_type=ChangeType.COMMENT_ADDED,
            actor_user=author_username,
            details={"comment_id": comment_id},
        )

    async def track_spec_modified(
        self,
        modified_by: str,
        modification_type: str,
    ) -> None:
        """
        Track when a spec is modified.

        Args:
            modified_by: User who modified the spec
            modification_type: Type of modification (e.g., "title_edited", "description_edited")
        """
        await self._add_change_record(
            change_type=ChangeType.SPEC_EDITED,
            actor_user=modified_by,
            details={"modification_type": modification_type},
        )

    async def get_notifications_for_user(
        self,
        username: str,
        unread_only: bool = False,
    ) -> list[Notification]:
        """
        Get all notifications for a specific user.

        Args:
            username: User to get notifications for
            unread_only: If True, only return unread notifications

        Returns:
            List of Notification objects for this user
        """
        notification_ids = self._user_notifications.get(username, [])
        notifications = [
            self._notifications[nid]
            for nid in notification_ids
            if nid in self._notifications
        ]

        if unread_only:
            notifications = [n for n in notifications if not n.read]

        # Sort by created_at descending (newest first)
        notifications.sort(key=lambda n: n.created_at, reverse=True)

        return notifications

    async def mark_notification_read(self, notification_id: str) -> bool:
        """
        Mark a notification as read and persist to Graphiti.

        Args:
            notification_id: Notification to mark as read

        Returns:
            True if marked successfully
        """
        if notification_id not in self._notifications:
            logger.warning(f"Notification {notification_id} not found")
            return False

        notification = self._notifications[notification_id]
        notification.read = True

        # Persist updated read status to Graphiti
        if self._memory_available:
            try:
                await self._store_notification_in_graphiti(notification)
            except Exception as e:
                logger.error(f"Failed to persist notification read status: {e}")
                return False

        logger.debug(f"Marked notification {notification_id} as read")
        return True

    async def mark_all_notifications_read(self, username: str) -> int:
        """
        Mark all notifications for a user as read and persist to Graphiti.

        Args:
            username: User whose notifications to mark read

        Returns:
            Number of notifications marked as read
        """
        notification_ids = self._user_notifications.get(username, [])
        count = 0

        for nid in notification_ids:
            if nid in self._notifications:
                notification = self._notifications[nid]
                if not notification.read:
                    notification.read = True
                    count += 1

                    # Persist each updated notification
                    if self._memory_available:
                        try:
                            await self._store_notification_in_graphiti(notification)
                        except Exception as e:
                            logger.error(
                                f"Failed to persist notification {nid} read status: {e}"
                            )

        logger.info(f"Marked {count} notifications as read for {username}")
        return count

    async def get_change_history(
        self,
        limit: int = 50,
    ) -> list[ChangeRecord]:
        """
        Get change history for this spec.

        Args:
            limit: Maximum number of changes to return

        Returns:
            List of ChangeRecord objects (newest first)
        """
        changes = list(self._change_history.values())

        # Sort by created_at descending
        changes.sort(key=lambda c: c.created_at, reverse=True)

        return changes[:limit]

    async def _add_change_record(
        self,
        change_type: ChangeType,
        actor_user: str,
        details: dict[str, Any] | None = None,
    ) -> ChangeRecord:
        """
        Add a change record to history.

        Args:
            change_type: Type of change
            actor_user: User who made the change
            details: Optional additional context

        Returns:
            Created ChangeRecord object
        """
        change = ChangeRecord(
            change_id=str(uuid.uuid4()),
            spec_id=self.spec_id,
            change_type=change_type,
            actor_user=actor_user,
            created_at=datetime.now(UTC).isoformat(),
            details=details,
        )

        # Store in cache
        self._change_history[change.change_id] = change

        logger.info(
            f"Recorded change {change.change_id}: {change_type.value} by {actor_user}"
        )

        # Persist to Graphiti
        if self._memory_available:
            await self._store_change_in_graphiti(change)

        return change

    async def _store_notification_in_graphiti(
        self,
        notification: Notification,
    ) -> bool:
        """Store a notification in Graphiti as an episode."""
        return await self._store_episode_in_graphiti(
            episode_name=f"notification_{notification.notification_id}",
            episode_content={
                "type": EPISODE_TYPE_NOTIFICATION,
                "spec_id": self.spec_id,
                "notification_id": notification.notification_id,
                "notification_type": notification.notification_type.value,
                "target_user": notification.target_user,
                "actor_user": notification.actor_user,
                "read": notification.read,
                "created_at": notification.created_at,
                "metadata": notification.metadata,
            },
            source_description=(
                f"Notification for {notification.target_user} on spec {self.spec_id}"
            ),
            operation_name="store_notification_in_graphiti",
            notification_id=notification.notification_id,
        )

    async def _store_change_in_graphiti(
        self,
        change: ChangeRecord,
    ) -> bool:
        """Store a change record in Graphiti as an episode."""
        return await self._store_episode_in_graphiti(
            episode_name=f"change_{change.change_id}",
            episode_content={
                "type": EPISODE_TYPE_CHANGE_HISTORY,
                "spec_id": self.spec_id,
                "change_id": change.change_id,
                "change_type": change.change_type.value,
                "actor_user": change.actor_user,
                "created_at": change.created_at,
                "details": change.details,
            },
            source_description=(
                f"Change to spec {self.spec_id} by {change.actor_user}"
            ),
            operation_name="store_change_in_graphiti",
            change_id=change.change_id,
        )
