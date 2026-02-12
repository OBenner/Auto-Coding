"""
Presence Tracking for Collaborative Spec Editing
==============================================

Manager for real-time presence indicators showing users viewing/editing specs.
Tracks user activity, cursor positions, and collaborative state.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING

from collaboration.models import Presence, PresenceType

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass


class PresenceManager:
    """Manager for real-time presence tracking.

    Tracks which users are actively viewing or editing a spec.
    Presence data is ephemeral and stored in memory (not persisted to disk).
    Automatically cleans up stale entries based on activity timeouts.
    """

    # Default timeout before marking presence as stale (seconds)
    DEFAULT_STALE_TIMEOUT = 60

    # Default timeout before removing presence entirely (seconds)
    DEFAULT_PRESENCE_TIMEOUT = 300  # 5 minutes

    def __init__(self, spec_dir: Path, stale_timeout: int = DEFAULT_STALE_TIMEOUT):
        """Initialize the presence manager.

        Args:
            spec_dir: Path to the spec directory
            stale_timeout: Seconds before considering presence stale
        """
        self.spec_dir = spec_dir
        self.spec_id = spec_dir.name
        self.stale_timeout = stale_timeout
        self._presence_store: dict[str, Presence] = {}  # user_id -> Presence
        self._lock = Lock()

    def update_presence(
        self,
        user_id: str,
        user_name: str,
        presence_type: PresenceType = PresenceType.VIEWING,
        section_id: str | None = None,
        cursor_position: int | None = None,
    ) -> Presence:
        """Update or create presence for a user.

        Args:
            user_id: User identifier
            user_name: Display name of user
            presence_type: Type of presence (viewing/editing/idle)
            section_id: Optional section being viewed/edited
            cursor_position: Optional cursor position in document

        Returns:
            Updated or created Presence object
        """
        with self._lock:
            # Update existing presence or create new
            if user_id in self._presence_store:
                presence = self._presence_store[user_id]
                presence.presence_type = presence_type
                presence.section_id = section_id
                presence.cursor_position = cursor_position
                presence.last_seen = datetime.utcnow()
                logger.debug(
                    "Updated presence for user %s in spec %s (type: %s)",
                    user_id,
                    self.spec_id,
                    presence_type.value,
                )
            else:
                presence = Presence(
                    spec_id=self.spec_id,
                    user_id=user_id,
                    user_name=user_name,
                    presence_type=presence_type,
                    section_id=section_id,
                    cursor_position=cursor_position,
                    last_seen=datetime.utcnow(),
                )
                self._presence_store[user_id] = presence
                logger.info(
                    "Added presence for user %s in spec %s (type: %s)",
                    user_id,
                    self.spec_id,
                    presence_type.value,
                )

            return presence

    def remove_presence(self, user_id: str) -> bool:
        """Remove presence for a user (e.g., on disconnect).

        Args:
            user_id: User identifier

        Returns:
            True if presence was removed
        """
        with self._lock:
            if user_id in self._presence_store:
                del self._presence_store[user_id]
                logger.info(
                    "Removed presence for user %s in spec %s",
                    user_id,
                    self.spec_id,
                )
                return True
            return False

    def get_presence(self, user_id: str) -> Presence | None:
        """Get presence for a specific user.

        Args:
            user_id: User identifier

        Returns:
            Presence object or None if user not present
        """
        with self._lock:
            presence = self._presence_store.get(user_id)
            if presence and presence.is_stale(self.stale_timeout):
                # Return stale presence but it will be cleaned up on next cleanup
                return presence
            return presence

    def get_all_presence(self, include_stale: bool = False) -> list[Presence]:
        """Get all presence for this spec.

        Args:
            include_stale: Whether to include stale presence entries

        Returns:
            List of Presence objects
        """
        with self._lock:
            presences = list(self._presence_store.values())

            if not include_stale:
                presences = [
                    p for p in presences if not p.is_stale(self.stale_timeout)
                ]

            return presences

    def get_active_users(self) -> list[dict]:
        """Get list of active users for UI display.

        Returns:
            List of user dictionaries with id, name, and presence_type
        """
        with self._lock:
            presences = [
                p
                for p in self._presence_store.values()
                if not p.is_stale(self.stale_timeout)
            ]

            return [
                {
                    "user_id": p.user_id,
                    "user_name": p.user_name,
                    "presence_type": p.presence_type.value,
                    "section_id": p.section_id,
                    "cursor_position": p.cursor_position,
                }
                for p in presences
            ]

    def cleanup_stale(self, timeout: int | None = None) -> int:
        """Remove stale presence entries.

        Args:
            timeout: Optional timeout override (uses default if None)

        Returns:
            Number of stale entries removed
        """
        cleanup_timeout = timeout or self.DEFAULT_PRESENCE_TIMEOUT

        with self._lock:
            stale_users = [
                user_id
                for user_id, presence in self._presence_store.items()
                if presence.is_stale(cleanup_timeout)
            ]

            for user_id in stale_users:
                del self._presence_store[user_id]

            if stale_users:
                logger.info(
                    "Cleaned up %d stale presence entries for spec %s",
                    len(stale_users),
                    self.spec_id,
                )

            return len(stale_users)

    def get_user_count(self, include_stale: bool = False) -> int:
        """Get count of users with presence.

        Args:
            include_stale: Whether to include stale entries

        Returns:
            Number of users
        """
        with self._lock:
            if include_stale:
                return len(self._presence_store)

            return len(
                [p for p in self._presence_store.values() if not p.is_stale(self.stale_timeout)]
            )

    def get_users_in_section(self, section_id: str | None) -> list[Presence]:
        """Get users viewing/editing a specific section.

        Args:
            section_id: Section identifier (None for spec-level)

        Returns:
            List of Presence objects for users in section
        """
        with self._lock:
            presences = [
                p
                for p in self._presence_store.values()
                if p.section_id == section_id and not p.is_stale(self.stale_timeout)
            ]

            return presences

    def is_user_present(self, user_id: str) -> bool:
        """Check if a user has presence (not stale).

        Args:
            user_id: User identifier

        Returns:
            True if user is present and active
        """
        with self._lock:
            presence = self._presence_store.get(user_id)
            return presence is not None and not presence.is_stale(self.stale_timeout)

    def mark_idle(self, user_id: str) -> bool:
        """Mark a user as idle (no recent activity).

        Args:
            user_id: User identifier

        Returns:
            True if user was marked idle
        """
        with self._lock:
            if user_id in self._presence_store:
                presence = self._presence_store[user_id]
                presence.presence_type = PresenceType.IDLE
                presence.last_seen = datetime.utcnow()
                logger.debug(
                    "Marked user %s as idle in spec %s",
                    user_id,
                    self.spec_id,
                )
                return True
            return False

    def mark_editing(self, user_id: str, section_id: str | None = None) -> bool:
        """Mark a user as actively editing.

        Args:
            user_id: User identifier
            section_id: Optional section being edited

        Returns:
            True if user was marked as editing
        """
        with self._lock:
            if user_id in self._presence_store:
                presence = self._presence_store[user_id]
                presence.presence_type = PresenceType.EDITING
                presence.section_id = section_id
                presence.last_seen = datetime.utcnow()
                logger.debug(
                    "Marked user %s as editing in spec %s (section: %s)",
                    user_id,
                    self.spec_id,
                    section_id,
                )
                return True
            return False

    def mark_viewing(self, user_id: str, section_id: str | None = None) -> bool:
        """Mark a user as viewing (not editing).

        Args:
            user_id: User identifier
            section_id: Optional section being viewed

        Returns:
            True if user was marked as viewing
        """
        with self._lock:
            if user_id in self._presence_store:
                presence = self._presence_store[user_id]
                presence.presence_type = PresenceType.VIEWING
                presence.section_id = section_id
                presence.last_seen = datetime.utcnow()
                logger.debug(
                    "Marked user %s as viewing in spec %s (section: %s)",
                    user_id,
                    self.spec_id,
                    section_id,
                )
                return True
            return False

    def get_presence_summary(self) -> dict:
        """Get summary of presence for this spec.

        Returns:
            Dictionary with presence statistics
        """
        with self._lock:
            active_presences = [
                p for p in self._presence_store.values() if not p.is_stale(self.stale_timeout)
            ]

            return {
                "spec_id": self.spec_id,
                "total_users": len(active_presences),
                "viewing": len([p for p in active_presences if p.presence_type == PresenceType.VIEWING]),
                "editing": len([p for p in active_presences if p.presence_type == PresenceType.EDITING]),
                "idle": len([p for p in active_presences if p.presence_type == PresenceType.IDLE]),
                "users": [
                    {
                        "user_id": p.user_id,
                        "user_name": p.user_name,
                        "presence_type": p.presence_type.value,
                    }
                    for p in active_presences
                ],
            }

    def clear_all(self) -> int:
        """Clear all presence (e.g., on server shutdown).

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._presence_store)
            self._presence_store.clear()
            logger.info(
                "Cleared all %d presence entries for spec %s",
                count,
                self.spec_id,
            )
            return count
