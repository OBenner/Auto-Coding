"""
Collaboration Models
====================

Data structures for real-time collaborative spec editing with comments,
suggestions, presence indicators, and version tracking.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class CommentStatus(str, Enum):
    """Status of a comment."""

    ACTIVE = "active"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class SuggestionStatus(str, Enum):
    """Status of a suggestion."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Comment(BaseModel):
    """A comment on a spec section for threaded discussions.

    Comments support hierarchical threading for organized discussions.
    """

    id: str = Field(description="Unique comment identifier")
    spec_id: str = Field(description="Spec this comment belongs to")
    section_id: str | None = Field(
        default=None, description="Spec section this comment references"
    )
    author: str = Field(description="Author identifier (username or ID)")
    author_name: str = Field(description="Display name of author")
    content: str = Field(description="Comment text content")
    parent_id: str | None = Field(
        default=None, description="Parent comment ID for threaded replies"
    )
    status: CommentStatus = Field(default=CommentStatus.ACTIVE, description="Comment status")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Comment creation timestamp"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    resolved_by: str | None = Field(
        default=None, description="User who resolved the comment"
    )
    resolved_at: datetime | None = Field(
        default=None, description="When the comment was resolved"
    )

    def to_dict(self) -> dict:
        """Convert comment to dictionary.

        Returns:
            Dictionary representation of the comment
        """
        return {
            "id": self.id,
            "spec_id": self.spec_id,
            "section_id": self.section_id,
            "author": self.author,
            "author_name": self.author_name,
            "content": self.content,
            "parent_id": self.parent_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Comment:
        """Create comment from dictionary.

        Args:
            data: Dictionary representation of a comment

        Returns:
            Comment instance
        """
        if isinstance(data.get("status"), str):
            data["status"] = CommentStatus(data["status"])

        # Parse datetime strings
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        if isinstance(data.get("resolved_at"), str):
            data["resolved_at"] = datetime.fromisoformat(data["resolved_at"])

        return cls(**data)


class Suggestion(BaseModel):
    """A suggested change to a spec without direct editing.

    Suggestions allow team members to propose changes for review
    before they are applied to the spec.
    """

    id: str = Field(description="Unique suggestion identifier")
    spec_id: str = Field(description="Spec this suggestion belongs to")
    section_id: str | None = Field(
        default=None, description="Spec section this suggestion references"
    )
    author: str = Field(description="Author identifier (username or ID)")
    author_name: str = Field(description="Display name of author")
    original_text: str = Field(description="Original text to be replaced")
    suggested_text: str = Field(description="Proposed replacement text")
    reason: str | None = Field(
        default=None, description="Explanation for the suggested change"
    )
    status: SuggestionStatus = Field(
        default=SuggestionStatus.PENDING, description="Suggestion status"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Suggestion creation timestamp"
    )
    reviewed_by: str | None = Field(
        default=None, description="User who reviewed the suggestion"
    )
    reviewed_at: datetime | None = Field(
        default=None, description="When the suggestion was reviewed"
    )
    review_comment: str | None = Field(
        default=None, description="Comment from the reviewer"
    )

    def to_dict(self) -> dict:
        """Convert suggestion to dictionary.

        Returns:
            Dictionary representation of the suggestion
        """
        return {
            "id": self.id,
            "spec_id": self.spec_id,
            "section_id": self.section_id,
            "author": self.author,
            "author_name": self.author_name,
            "original_text": self.original_text,
            "suggested_text": self.suggested_text,
            "reason": self.reason,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_comment": self.review_comment,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Suggestion:
        """Create suggestion from dictionary.

        Args:
            data: Dictionary representation of a suggestion

        Returns:
            Suggestion instance
        """
        if isinstance(data.get("status"), str):
            data["status"] = SuggestionStatus(data["status"])

        # Parse datetime strings
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("reviewed_at"), str):
            data["reviewed_at"] = datetime.fromisoformat(data["reviewed_at"])

        return cls(**data)


class PresenceType(str, Enum):
    """Type of user presence."""

    VIEWING = "viewing"
    EDITING = "editing"
    IDLE = "idle"


class Presence(BaseModel):
    """Real-time presence indicator for users viewing/editing a spec.

    Tracks which users are actively collaborating on a spec.
    """

    spec_id: str = Field(description="Spec this presence belongs to")
    user_id: str = Field(description="User identifier")
    user_name: str = Field(description="Display name of user")
    presence_type: PresenceType = Field(
        default=PresenceType.VIEWING, description="Type of presence"
    )
    section_id: str | None = Field(
        default=None, description="Section being viewed/edited"
    )
    cursor_position: int | None = Field(
        default=None, description="Cursor position in document"
    )
    last_seen: datetime = Field(
        default_factory=datetime.utcnow, description="Last activity timestamp"
    )

    def to_dict(self) -> dict:
        """Convert presence to dictionary.

        Returns:
            Dictionary representation of the presence
        """
        return {
            "spec_id": self.spec_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "presence_type": self.presence_type.value,
            "section_id": self.section_id,
            "cursor_position": self.cursor_position,
            "last_seen": self.last_seen.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Presence:
        """Create presence from dictionary.

        Args:
            data: Dictionary representation of presence

        Returns:
            Presence instance
        """
        if isinstance(data.get("presence_type"), str):
            data["presence_type"] = PresenceType(data["presence_type"])

        # Parse datetime strings
        if isinstance(data.get("last_seen"), str):
            data["last_seen"] = datetime.fromisoformat(data["last_seen"])

        return cls(**data)

    def is_stale(self, timeout_seconds: int = 60) -> bool:
        """Check if presence entry is stale (no recent activity).

        Args:
            timeout_seconds: Seconds before considering presence stale

        Returns:
            True if presence is stale
        """
        elapsed = (datetime.now(timezone.utc) - self.last_seen).total_seconds()
        return elapsed > timeout_seconds


class Version(BaseModel):
    """A version of a spec for change tracking and history.

    Maintains a complete history of all changes with diff support.
    """

    id: str = Field(description="Unique version identifier")
    spec_id: str = Field(description="Spec this version belongs to")
    version_number: int = Field(description="Sequential version number")
    author: str = Field(description="Author of this version")
    author_name: str = Field(description="Display name of author")
    content: str = Field(description="Full spec content at this version")
    commit_message: str | None = Field(
        default=None, description="Description of changes in this version"
    )
    previous_version_id: str | None = Field(
        default=None, description="Previous version ID for chaining"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Version creation timestamp"
    )
    is_approved: bool = Field(
        default=False, description="Whether this version is approved"
    )
    approved_by: str | None = Field(
        default=None, description="User who approved this version"
    )
    approved_at: datetime | None = Field(
        default=None, description="When this version was approved"
    )

    def to_dict(self) -> dict:
        """Convert version to dictionary.

        Returns:
            Dictionary representation of the version
        """
        return {
            "id": self.id,
            "spec_id": self.spec_id,
            "version_number": self.version_number,
            "author": self.author,
            "author_name": self.author_name,
            "content": self.content,
            "commit_message": self.commit_message,
            "previous_version_id": self.previous_version_id,
            "created_at": self.created_at.isoformat(),
            "is_approved": self.is_approved,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Version:
        """Create version from dictionary.

        Args:
            data: Dictionary representation of a version

        Returns:
            Version instance
        """
        # Parse datetime strings
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("approved_at"), str):
            data["approved_at"] = datetime.fromisoformat(data["approved_at"])

        return cls(**data)


def load_comments(spec_dir: Path) -> list[Comment]:
    """Load all comments for a spec.

    Args:
        spec_dir: Path to the spec directory

    Returns:
        List of comments
    """
    comments_file = spec_dir / "collaboration" / "comments.json"

    if not comments_file.exists():
        return []

    try:
        with open(comments_file, encoding="utf-8") as f:
            data = json.load(f)
        return [Comment.from_dict(item) for item in data]
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load comments from %s: %s", comments_file, e)
        return []


def save_comments(spec_dir: Path, comments: list[Comment]) -> None:
    """Save comments for a spec.

    Args:
        spec_dir: Path to the spec directory
        comments: List of comments to save
    """
    collaboration_dir = spec_dir / "collaboration"
    collaboration_dir.mkdir(parents=True, exist_ok=True)

    comments_file = collaboration_dir / "comments.json"

    try:
        with open(comments_file, "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in comments], f, indent=2)
    except OSError as e:
        logger.error("Failed to save comments to %s: %s", comments_file, e)


def load_suggestions(spec_dir: Path) -> list[Suggestion]:
    """Load all suggestions for a spec.

    Args:
        spec_dir: Path to the spec directory

    Returns:
        List of suggestions
    """
    suggestions_file = spec_dir / "collaboration" / "suggestions.json"

    if not suggestions_file.exists():
        return []

    try:
        with open(suggestions_file, encoding="utf-8") as f:
            data = json.load(f)
        return [Suggestion.from_dict(item) for item in data]
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load suggestions from %s: %s", suggestions_file, e)
        return []


def save_suggestions(spec_dir: Path, suggestions: list[Suggestion]) -> None:
    """Save suggestions for a spec.

    Args:
        spec_dir: Path to the spec directory
        suggestions: List of suggestions to save
    """
    collaboration_dir = spec_dir / "collaboration"
    collaboration_dir.mkdir(parents=True, exist_ok=True)

    suggestions_file = collaboration_dir / "suggestions.json"

    try:
        with open(suggestions_file, "w", encoding="utf-8") as f:
            json.dump([s.to_dict() for s in suggestions], f, indent=2)
    except OSError as e:
        logger.error("Failed to save suggestions to %s: %s", suggestions_file, e)


def load_versions(spec_dir: Path) -> list[Version]:
    """Load all versions for a spec.

    Args:
        spec_dir: Path to the spec directory

    Returns:
        List of versions
    """
    versions_file = spec_dir / "collaboration" / "versions.json"

    if not versions_file.exists():
        return []

    try:
        with open(versions_file, encoding="utf-8") as f:
            data = json.load(f)
        return [Version.from_dict(item) for item in data]
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load versions from %s: %s", versions_file, e)
        return []


def save_versions(spec_dir: Path, versions: list[Version]) -> None:
    """Save versions for a spec.

    Args:
        spec_dir: Path to the spec directory
        versions: List of versions to save
    """
    collaboration_dir = spec_dir / "collaboration"
    collaboration_dir.mkdir(parents=True, exist_ok=True)

    versions_file = collaboration_dir / "versions.json"

    try:
        with open(versions_file, "w", encoding="utf-8") as f:
            json.dump([v.to_dict() for v in versions], f, indent=2)
    except OSError as e:
        logger.error("Failed to save versions to %s: %s", versions_file, e)
