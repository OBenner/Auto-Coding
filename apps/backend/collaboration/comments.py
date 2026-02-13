"""
Comment System for Collaborative Spec Editing
=========================================

Manager for threaded comments on spec sections.
Provides CRUD operations, threading support, and status management.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from collaboration.models import Comment, CommentStatus, load_comments, save_comments

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class CommentManager:
    """Manager for spec comments with threading and status tracking.

    Provides a high-level interface for managing comments on specifications.
    Comments can be organized by section, threaded for replies, and
    resolved/archived for workflow management.
    """

    def __init__(self, spec_dir: Path):
        """Initialize the comment manager.

        Args:
            spec_dir: Path to the spec directory
        """
        self.spec_dir = spec_dir
        self._comments_cache: list[Comment] | None = None

    def load_comments(self) -> list[Comment]:
        """Load comments from disk.

        Returns:
            List of all comments for this spec
        """
        if self._comments_cache is None:
            self._comments_cache = load_comments(self.spec_dir)
            logger.debug(
                "Loaded %d comments from %s",
                len(self._comments_cache),
                self.spec_dir,
            )
        return self._comments_cache

    def save_comments(self, comments: list[Comment] | None = None) -> bool:
        """Save comments to disk.

        Args:
            comments: Optional list of comments (uses cache if None)

        Returns:
            True if save was successful
        """
        comments_to_save = comments if comments is not None else self._comments_cache
        if comments_to_save is None:
            logger.warning("No comments to save")
            return False

        try:
            save_comments(self.spec_dir, comments_to_save)
            self._comments_cache = comments_to_save
            logger.debug(
                "Saved %d comments to %s",
                len(comments_to_save),
                self.spec_dir,
            )
            return True
        except Exception as e:
            logger.error("Failed to save comments: %s", e)
            return False

    def add_comment(
        self,
        author: str,
        author_name: str,
        content: str,
        section_id: str | None = None,
        parent_id: str | None = None,
    ) -> Comment | None:
        """Add a new comment.

        Args:
            author: Author identifier
            author_name: Display name of author
            content: Comment text content
            section_id: Optional section this comment references
            parent_id: Optional parent comment ID for threading

        Returns:
            Created comment or None if creation failed
        """
        if not content or not content.strip():
            logger.warning("Cannot add comment with empty content")
            return None

        comments = self.load_comments()

        # Create new comment
        comment = Comment(
            id=str(uuid.uuid4()),
            spec_id=self.spec_dir.name,
            section_id=section_id,
            author=author,
            author_name=author_name,
            content=content.strip(),
            parent_id=parent_id,
            status=CommentStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
        )

        comments.append(comment)

        if self.save_comments(comments):
            logger.info(
                "Added comment %s by %s to spec %s",
                comment.id,
                author,
                self.spec_dir.name,
            )
            return comment

        return None

    def get_comment(self, comment_id: str) -> Comment | None:
        """Get a specific comment by ID.

        Args:
            comment_id: Comment identifier

        Returns:
            Comment or None if not found
        """
        comments = self.load_comments()
        for comment in comments:
            if comment.id == comment_id:
                return comment
        return None

    def get_comments_for_spec(
        self,
        status: CommentStatus | None = None,
        include_resolved: bool = True,
    ) -> list[Comment]:
        """Get all comments for this spec.

        Args:
            status: Optional status filter
            include_resolved: Whether to include resolved comments

        Returns:
            List of comments matching criteria
        """
        comments = self.load_comments()

        if status:
            return [c for c in comments if c.status == status]

        if not include_resolved:
            return [c for c in comments if c.status != CommentStatus.RESOLVED]

        return comments

    def get_comments_for_section(
        self,
        section_id: str | None,
        include_resolved: bool = True,
    ) -> list[Comment]:
        """Get comments for a specific section.

        Args:
            section_id: Section identifier (None for spec-level comments)
            include_resolved: Whether to include resolved comments

        Returns:
            List of comments for the section
        """
        comments = self.load_comments()

        filtered = [
            c
            for c in comments
            if c.section_id == section_id
            and (include_resolved or c.status != CommentStatus.RESOLVED)
        ]

        return filtered

    def get_comment_thread(self, comment_id: str) -> list[Comment]:
        """Get a thread of comments (parent + all replies).

        Args:
            comment_id: Root comment ID

        Returns:
            List of comments in the thread (root first, then replies)
        """
        comments = self.load_comments()
        thread = []

        # Find root comment
        root = self.get_comment(comment_id)
        if root:
            thread.append(root)

        # Find all replies (recursive)
        replies = self._get_replies(comment_id, comments)
        thread.extend(replies)

        return thread

    def _get_replies(self, parent_id: str, comments: list[Comment]) -> list[Comment]:
        """Recursively get all replies to a comment.

        Args:
            parent_id: Parent comment ID
            comments: List of all comments

        Returns:
            List of reply comments
        """
        replies = []
        for comment in comments:
            if comment.parent_id == parent_id:
                replies.append(comment)
                # Get nested replies
                replies.extend(self._get_replies(comment.id, comments))
        return replies

    def resolve_comment(
        self,
        comment_id: str,
        resolved_by: str,
    ) -> bool:
        """Mark a comment as resolved.

        Args:
            comment_id: Comment to resolve
            resolved_by: User resolving the comment

        Returns:
            True if resolution was successful
        """
        comments = self.load_comments()

        for comment in comments:
            if comment.id == comment_id:
                comment.status = CommentStatus.RESOLVED
                comment.resolved_by = resolved_by
                comment.resolved_at = datetime.now(timezone.utc)

                if self.save_comments(comments):
                    logger.info(
                        "Resolved comment %s by %s",
                        comment_id,
                        resolved_by,
                    )
                    return True
                return False

        logger.warning("Comment not found for resolution: %s", comment_id)
        return False

    def unresolve_comment(self, comment_id: str) -> bool:
        """Mark a resolved comment as active again.

        Args:
            comment_id: Comment to unresolve

        Returns:
            True if successful
        """
        comments = self.load_comments()

        for comment in comments:
            if comment.id == comment_id:
                comment.status = CommentStatus.ACTIVE
                comment.resolved_by = None
                comment.resolved_at = None

                if self.save_comments(comments):
                    logger.info("Unresolved comment %s", comment_id)
                    return True
                return False

        logger.warning("Comment not found for unresolve: %s", comment_id)
        return False

    def archive_comment(self, comment_id: str) -> bool:
        """Archive a comment (removes from active view).

        Args:
            comment_id: Comment to archive

        Returns:
            True if successful
        """
        comments = self.load_comments()

        for comment in comments:
            if comment.id == comment_id:
                comment.status = CommentStatus.ARCHIVED

                if self.save_comments(comments):
                    logger.info("Archived comment %s", comment_id)
                    return True
                return False

        logger.warning("Comment not found for archive: %s", comment_id)
        return False

    def update_comment(
        self,
        comment_id: str,
        content: str,
    ) -> bool:
        """Update comment content.

        Args:
            comment_id: Comment to update
            content: New content

        Returns:
            True if update was successful
        """
        if not content or not content.strip():
            logger.warning("Cannot update comment with empty content")
            return False

        comments = self.load_comments()

        for comment in comments:
            if comment.id == comment_id:
                comment.content = content.strip()
                comment.updated_at = datetime.now(timezone.utc)

                if self.save_comments(comments):
                    logger.info("Updated comment %s", comment_id)
                    return True
                return False

        logger.warning("Comment not found for update: %s", comment_id)
        return False

    def delete_comment(self, comment_id: str) -> bool:
        """Delete a comment permanently.

        Args:
            comment_id: Comment to delete

        Returns:
            True if deletion was successful
        """
        comments = self.load_comments()

        # Find and remove comment
        original_length = len(comments)
        comments = [c for c in comments if c.id != comment_id]

        if len(comments) < original_length:
            if self.save_comments(comments):
                logger.info("Deleted comment %s", comment_id)
                return True
            return False

        logger.warning("Comment not found for deletion: %s", comment_id)
        return False

    def get_comment_count(
        self,
        section_id: str | None = None,
        include_resolved: bool = False,
    ) -> int:
        """Get count of comments.

        Args:
            section_id: Optional section to count for
            include_resolved: Whether to include resolved comments

        Returns:
            Number of comments matching criteria
        """
        if section_id:
            return len(
                self.get_comments_for_section(section_id, include_resolved)
            )
        return len(self.get_comments_for_spec(include_resolved=include_resolved))

    def get_active_comment_count(self, section_id: str | None = None) -> int:
        """Get count of active (unresolved) comments.

        Args:
            section_id: Optional section to count for

        Returns:
            Number of active comments
        """
        return self.get_comment_count(section_id, include_resolved=False)

    def get_comments_by_author(
        self,
        author: str,
        include_resolved: bool = True,
    ) -> list[Comment]:
        """Get all comments by a specific author.

        Args:
            author: Author identifier
            include_resolved: Whether to include resolved comments

        Returns:
            List of comments by the author
        """
        comments = self.load_comments()

        filtered = [
            c
            for c in comments
            if c.author == author
            and (include_resolved or c.status != CommentStatus.RESOLVED)
        ]

        return filtered
