#!/usr/bin/env python3
"""
Comment Thread Management
=========================

Manages comment threads for multi-user spec collaboration.

Key features:
- Create top-level comments on specs
- Reply to existing comments (threading)
- Resolve comment threads
- @mention extraction and handling
- Permission-based access control
- Graphiti storage integration

Usage:
    manager = CommentManager(
        spec_id="001-feature",
        spec_dir=Path(".auto-claude/specs/001-feature"),
        project_dir=Path("."),
        permission_checker=checker
    )

    # Create a comment
    comment = await manager.create_comment(
        user_id="alice",
        username="Alice",
        content="This approach looks good! @bob what do you think?"
    )

    # Reply to a comment
    reply = await manager.reply_to_comment(
        parent_comment_id=comment.comment_id,
        user_id="bob",
        username="Bob",
        content="Agreed! Let's proceed."
    )

    # Resolve thread
    await manager.resolve_thread(comment.comment_id, user_id="alice")
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from integrations.graphiti.queries_pkg.schema import EPISODE_TYPE_COMMENT

from .base import CollaborationManagerBase
from .models import CollaborationUser, Comment, PermissionLevel
from .permissions import PermissionChecker

logger = logging.getLogger(__name__)


class CommentError(Exception):
    """Raised when comment operations fail."""

    pass


class CommentManager(CollaborationManagerBase):
    """
    Manages comment threads for spec collaboration.

    Provides thread-safe comment operations with permission checks
    and Graphiti storage integration.

    Features:
    - Create top-level comments
    - Reply to comments (threading)
    - Resolve comment threads
    - Automatic @mention extraction
    - Permission-based access control
    - Persistent storage via Graphiti

    Usage:
        manager = CommentManager(
            spec_id="001-feature",
            spec_dir=Path(".auto-claude/specs/001-feature"),
            project_dir=Path("."),
            permission_checker=checker
        )

        # Create comment (requires WRITE permission)
        comment = await manager.create_comment(
            user_id="alice",
            username="Alice",
            content="Great work!"
        )

        # Reply to comment
        reply = await manager.reply_to_comment(
            parent_comment_id=comment.comment_id,
            user_id="bob",
            username="Bob",
            content="Thanks!"
        )

        # Resolve thread (requires WRITE permission)
        await manager.resolve_thread(comment.comment_id, user_id="alice")
    """

    _manager_name = "comment"

    def __init__(
        self,
        spec_id: str,
        spec_dir: Path,
        project_dir: Path,
        permission_checker: PermissionChecker | None = None,
    ):
        """
        Initialize comment manager for a spec.

        Args:
            spec_id: Spec identifier (e.g., "001-feature-name")
            spec_dir: Path to spec directory (for Graphiti storage)
            project_dir: Project root directory
            permission_checker: Optional permission checker (for access control)
        """
        super().__init__(spec_id, spec_dir, project_dir, permission_checker)

        # In-memory comment cache: comment_id -> Comment
        self._comments: dict[str, Comment] = {}

        # Thread index: parent_id -> [child_comment_ids]
        self._thread_index: dict[str, list[str]] = {}

        logger.info(f"Initialized comment manager for spec {spec_id}")

    async def create_comment(
        self,
        user_id: str,
        username: str,
        content: str,
        email: str | None = None,
    ) -> Comment:
        """
        Create a new top-level comment on the spec.

        Args:
            user_id: User creating the comment
            username: Display name
            content: Comment text (supports markdown and @mentions)
            email: Optional user email

        Returns:
            Created Comment object

        Raises:
            CommentError: If permission denied or creation fails
        """
        # Check write permission
        self._require_permission(user_id, PermissionLevel.WRITE, CommentError)

        # Create comment
        comment = Comment(
            comment_id=str(uuid.uuid4()),
            spec_id=self.spec_id,
            author=CollaborationUser(user_id=user_id, username=username, email=email),
            content=content,
        )

        # Store in cache
        self._comments[comment.comment_id] = comment

        # Add to thread index (top-level comment has no parent)
        self._thread_index.setdefault(comment.comment_id, [])

        logger.info(
            f"Created comment {comment.comment_id} by {username} on spec {self.spec_id}"
        )

        # Persist to Graphiti
        if self._memory_available:
            await self._store_comment_in_graphiti(comment)

        return comment

    async def reply_to_comment(
        self,
        parent_comment_id: str,
        user_id: str,
        username: str,
        content: str,
        email: str | None = None,
    ) -> Comment:
        """
        Reply to an existing comment (creates threaded reply).

        Args:
            parent_comment_id: ID of comment being replied to
            user_id: User creating the reply
            username: Display name
            content: Reply text (supports markdown and @mentions)
            email: Optional user email

        Returns:
            Created reply Comment object

        Raises:
            CommentError: If parent not found, permission denied, or creation fails
        """
        # Check write permission
        self._require_permission(user_id, PermissionLevel.WRITE, CommentError)

        # Verify parent exists
        if parent_comment_id not in self._comments:
            raise CommentError(f"Parent comment {parent_comment_id} not found")

        # Create reply
        reply = Comment(
            comment_id=str(uuid.uuid4()),
            spec_id=self.spec_id,
            author=CollaborationUser(user_id=user_id, username=username, email=email),
            content=content,
            parent_id=parent_comment_id,
        )

        # Store in cache
        self._comments[reply.comment_id] = reply

        # Add to thread index
        self._thread_index.setdefault(parent_comment_id, []).append(reply.comment_id)

        logger.info(
            f"Created reply {reply.comment_id} by {username} "
            f"to comment {parent_comment_id} on spec {self.spec_id}"
        )

        # Persist to Graphiti
        if self._memory_available:
            await self._store_comment_in_graphiti(reply)

        return reply

    async def resolve_thread(self, comment_id: str, user_id: str) -> bool:
        """
        Mark a comment thread as resolved.

        Resolves the specified comment and all its replies.

        Args:
            comment_id: ID of comment to resolve
            user_id: User resolving the thread

        Returns:
            True if resolved successfully

        Raises:
            CommentError: If comment not found or permission denied
        """
        # Check write permission
        self._require_permission(user_id, PermissionLevel.WRITE, CommentError)

        # Verify comment exists
        if comment_id not in self._comments:
            raise CommentError(f"Comment {comment_id} not found")

        comment = self._comments[comment_id]

        # Mark as resolved
        comment.mark_resolved()

        logger.info(
            f"Resolved comment thread {comment_id} on spec {self.spec_id} "
            f"by user {user_id}"
        )

        # Update in Graphiti if available
        if self._memory_available:
            await self._update_comment_in_graphiti(comment, action="resolved")

        return True

    async def get_comment(self, comment_id: str) -> Comment | None:
        """
        Get a specific comment by ID.

        Args:
            comment_id: Comment to retrieve

        Returns:
            Comment object if found, None otherwise
        """
        return self._comments.get(comment_id)

    def get_thread(self, comment_id: str) -> list[Comment]:
        """
        Get all replies to a comment (immediate children only).

        Args:
            comment_id: Parent comment ID

        Returns:
            List of reply Comment objects (may be empty)
        """
        reply_ids = self._thread_index.get(comment_id, [])
        return [self._comments[rid] for rid in reply_ids if rid in self._comments]

    def get_all_comments(self) -> list[Comment]:
        """
        Get all comments for this spec.

        Returns:
            List of all Comment objects
        """
        return list(self._comments.values())

    def get_top_level_comments(self) -> list[Comment]:
        """
        Get all top-level comments (not replies).

        Returns:
            List of top-level Comment objects
        """
        return [c for c in self._comments.values() if c.parent_id is None]

    def get_comments_by_author(self, user_id: str) -> list[Comment]:
        """
        Get all comments by a specific author.

        Args:
            user_id: User to filter by

        Returns:
            List of Comment objects by this author
        """
        return [c for c in self._comments.values() if c.author.user_id == user_id]

    def get_unresolved_comments(self) -> list[Comment]:
        """
        Get all unresolved top-level comments.

        Returns:
            List of unresolved Comment objects
        """
        return [
            c for c in self._comments.values() if c.parent_id is None and not c.resolved
        ]

    def get_mentions_for_user(self, username: str) -> list[Comment]:
        """
        Get all comments that mention a specific user.

        Args:
            username: Username to search for (without @ prefix)

        Returns:
            List of Comment objects mentioning this user
        """
        return [c for c in self._comments.values() if username in c.mentions]

    async def _store_comment_in_graphiti(self, comment: Comment) -> bool:
        """Store a comment in Graphiti as an episode."""
        return await self._store_episode_in_graphiti(
            episode_name=f"comment_{comment.comment_id}_{self.spec_id}",
            episode_content={
                "type": EPISODE_TYPE_COMMENT,
                "spec_id": self.spec_id,
                "comment_id": comment.comment_id,
                "author_id": comment.author.user_id,
                "author_username": comment.author.username,
                "content": comment.content,
                "parent_id": comment.parent_id,
                "mentions": comment.mentions,
                "resolved": comment.resolved,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
            },
            source_description=(
                f"Comment on spec {self.spec_id} by {comment.author.username}"
            ),
            operation_name="store_comment_in_graphiti",
            comment_id=comment.comment_id,
        )

    async def _update_comment_in_graphiti(self, comment: Comment, action: str) -> bool:
        """Update a comment in Graphiti (for resolved status changes)."""
        return await self._store_episode_in_graphiti(
            episode_name=f"comment_update_{comment.comment_id}_{action}",
            episode_content={
                "type": EPISODE_TYPE_COMMENT,
                "spec_id": self.spec_id,
                "comment_id": comment.comment_id,
                "action": action,
                "resolved": comment.resolved,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            source_description=f"Comment {action}: {comment.comment_id}",
            operation_name="update_comment_in_graphiti",
            comment_id=comment.comment_id,
            action=action,
        )
