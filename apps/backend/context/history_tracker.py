"""
Context History Tracker for Session Coherence
==============================================

Tracks what context has been provided to agents across multiple turns and sessions
to maintain coherence, prevent redundant information, and optimize context usage.

Components:
- HistoryTracker: Main class for tracking context history
- ContextEntry: Represents a single context item sent to the agent
- Persistence layer for cross-session history

Usage:
    # Create tracker
    tracker = HistoryTracker()

    # Track sent context
    tracker.add_context(
        file_path="apps/backend/core/client.py",
        content_hash="abc123",
        token_count=1500,
        turn_number=1
    )

    # Check if content was recently sent
    if tracker.was_sent_recently("apps/backend/core/client.py"):
        # Skip or summarize
        pass

    # Get context summary for new turn
    summary = tracker.get_session_summary()
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContextEntry:
    """
    Represents a single context item sent to the agent.

    Tracks metadata about each piece of context to enable intelligent
    decisions about what to send, resend, or summarize.

    Attributes:
        file_path: Path to the file or context identifier
        content_hash: Hash of the content for change detection
        token_count: Number of tokens in the content
        turn_number: Turn number when this was sent
        timestamp: When this was sent (ISO format)
        sent_count: How many times this has been sent
        last_modified: Last modification time of the file (if applicable)
        summary: Optional summary of the content
    """

    file_path: str
    content_hash: str
    token_count: int
    turn_number: int
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    sent_count: int = 1
    last_modified: str | None = None
    summary: str | None = None


class HistoryTracker:
    """
    Tracks context history to maintain session coherence.

    Maintains a record of what context has been sent to the agent,
    enabling intelligent decisions about:
    - When to skip redundant context
    - When to resend updated content
    - When to summarize instead of resending full content
    - How to maintain coherence across long sessions

    Args:
        spec_dir: Directory for spec-specific history persistence
        max_turns_cache: How many turns to keep in memory (default: 10)
        resend_threshold: Turns before considering resending (default: 5)
    """

    def __init__(
        self,
        spec_dir: Path | None = None,
        max_turns_cache: int = 10,
        resend_threshold: int = 5,
    ):
        """Initialize the history tracker."""
        self.spec_dir = spec_dir
        self.max_turns_cache = max_turns_cache
        self.resend_threshold = resend_threshold

        # In-memory tracking
        self.current_turn = 0
        self.history: dict[str, ContextEntry] = {}  # file_path -> latest entry
        self.turn_history: list[list[str]] = []  # turn_number -> list of file_paths

        # Load persisted history if available
        if spec_dir:
            self._load_history()

    def _load_history(self) -> None:
        """Load history from persisted file if available."""
        if not self.spec_dir:
            return

        history_file = self.spec_dir / "context_history.json"
        if not history_file.exists():
            return

        try:
            with open(history_file, encoding="utf-8") as f:
                data = json.load(f)

            # Restore current turn
            self.current_turn = data.get("current_turn", 0)

            # Restore history entries
            history_data = data.get("history", {})
            for file_path, entry_dict in history_data.items():
                self.history[file_path] = ContextEntry(**entry_dict)

            # Restore turn history
            self.turn_history = data.get("turn_history", [])

            logger.debug(
                f"Loaded context history: {len(self.history)} entries, "
                f"turn {self.current_turn}"
            )
        except Exception as e:
            logger.warning(f"Failed to load context history: {e}")
            # Start fresh on error
            self.history = {}
            self.turn_history = []
            self.current_turn = 0

    def _save_history(self) -> None:
        """Persist history to file."""
        if not self.spec_dir:
            return

        try:
            # Ensure directory exists
            self.spec_dir.mkdir(parents=True, exist_ok=True)

            # Prepare data for serialization
            data = {
                "current_turn": self.current_turn,
                "history": {
                    file_path: asdict(entry)
                    for file_path, entry in self.history.items()
                },
                "turn_history": self.turn_history,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            history_file = self.spec_dir / "context_history.json"
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved context history to {history_file}")
        except Exception as e:
            logger.warning(f"Failed to save context history: {e}")

    def start_new_turn(self) -> int:
        """
        Start a new turn in the session.

        Returns:
            The new turn number
        """
        self.current_turn += 1
        self.turn_history.append([])

        # Trim old turns if needed
        if len(self.turn_history) > self.max_turns_cache:
            self.turn_history = self.turn_history[-self.max_turns_cache :]

        logger.debug(f"Started turn {self.current_turn}")
        return self.current_turn

    def add_context(
        self,
        file_path: str,
        content: str | None = None,
        content_hash: str | None = None,
        token_count: int | None = None,
        last_modified: str | None = None,
        summary: str | None = None,
    ) -> ContextEntry:
        """
        Track a context item that was sent to the agent.

        Args:
            file_path: Path to the file or context identifier
            content: The actual content (used to compute hash if not provided)
            content_hash: Pre-computed hash of the content
            token_count: Number of tokens (estimated if not provided)
            last_modified: Last modification timestamp
            summary: Optional summary of the content

        Returns:
            The ContextEntry that was created or updated
        """
        # Compute content hash if not provided
        if content_hash is None and content is not None:
            content_hash = self._compute_hash(content)
        elif content_hash is None:
            content_hash = "unknown"

        # Estimate token count if not provided
        if token_count is None and content is not None:
            token_count = self._estimate_tokens(content)
        elif token_count is None:
            token_count = 0

        # Check if we've sent this before
        if file_path in self.history:
            existing = self.history[file_path]

            # Check if content changed
            if existing.content_hash != content_hash:
                # Content changed - create new entry
                logger.debug(
                    f"Content changed for {file_path} "
                    f"(old hash: {existing.content_hash[:8]}, "
                    f"new hash: {content_hash[:8]})"
                )
                entry = ContextEntry(
                    file_path=file_path,
                    content_hash=content_hash,
                    token_count=token_count,
                    turn_number=self.current_turn,
                    sent_count=existing.sent_count + 1,
                    last_modified=last_modified,
                    summary=summary,
                )
            else:
                # Same content - update existing entry
                existing.turn_number = self.current_turn
                existing.sent_count += 1
                existing.timestamp = datetime.now(timezone.utc).isoformat()
                if summary:
                    existing.summary = summary
                entry = existing
        else:
            # New context item
            entry = ContextEntry(
                file_path=file_path,
                content_hash=content_hash,
                token_count=token_count,
                turn_number=self.current_turn,
                last_modified=last_modified,
                summary=summary,
            )

        # Update tracking
        self.history[file_path] = entry
        if self.turn_history:
            self.turn_history[-1].append(file_path)

        # Persist
        self._save_history()

        return entry

    def was_sent_recently(
        self,
        file_path: str,
        turns_ago: int | None = None,
    ) -> bool:
        """
        Check if a file was sent recently.

        Args:
            file_path: Path to check
            turns_ago: Number of turns to look back (defaults to resend_threshold)

        Returns:
            True if the file was sent within the threshold
        """
        if file_path not in self.history:
            return False

        turns_ago = turns_ago or self.resend_threshold
        entry = self.history[file_path]

        return (self.current_turn - entry.turn_number) <= turns_ago

    def has_content_changed(
        self,
        file_path: str,
        current_content: str | None = None,
        current_hash: str | None = None,
    ) -> bool:
        """
        Check if content has changed since last sent.

        Args:
            file_path: Path to check
            current_content: Current content (to compute hash)
            current_hash: Pre-computed hash of current content

        Returns:
            True if content has changed or was never sent
        """
        if file_path not in self.history:
            return True  # Never sent = changed

        # Compute current hash if needed
        if current_hash is None and current_content is not None:
            current_hash = self._compute_hash(current_content)
        elif current_hash is None:
            # Can't determine - assume changed
            return True

        return self.history[file_path].content_hash != current_hash

    def should_resend(
        self,
        file_path: str,
        current_content: str | None = None,
        current_hash: str | None = None,
    ) -> bool:
        """
        Determine if content should be resent to the agent.

        Content should be resent if:
        - It's never been sent
        - It's been too many turns since it was sent
        - The content has changed

        Args:
            file_path: Path to check
            current_content: Current content
            current_hash: Pre-computed hash of current content

        Returns:
            True if content should be resent
        """
        # Never sent - should send
        if file_path not in self.history:
            return True

        # Content changed - should resend
        if self.has_content_changed(file_path, current_content, current_hash):
            return True

        # Too old - should resend
        if not self.was_sent_recently(file_path):
            return True

        return False

    def get_session_summary(self) -> dict[str, Any]:
        """
        Get a summary of the current session context.

        Returns:
            Dictionary with session statistics and recent context
        """
        total_tokens = sum(entry.token_count for entry in self.history.values())
        unique_files = len(self.history)

        # Get recent files (last 3 turns)
        recent_files = set()
        for turn_files in self.turn_history[-3:]:
            recent_files.update(turn_files)

        # Get most frequently sent
        frequent = sorted(
            self.history.values(),
            key=lambda e: e.sent_count,
            reverse=True,
        )[:10]

        return {
            "current_turn": self.current_turn,
            "total_tokens_sent": total_tokens,
            "unique_files_sent": unique_files,
            "recent_files": list(recent_files),
            "most_frequent": [
                {
                    "path": entry.file_path,
                    "sent_count": entry.sent_count,
                    "last_turn": entry.turn_number,
                }
                for entry in frequent
            ],
        }

    def get_context_for_file(self, file_path: str) -> ContextEntry | None:
        """
        Get the history entry for a specific file.

        Args:
            file_path: Path to look up

        Returns:
            ContextEntry if found, None otherwise
        """
        return self.history.get(file_path)

    def clear_history(self) -> None:
        """Clear all history (use with caution)."""
        self.history = {}
        self.turn_history = []
        self.current_turn = 0
        self._save_history()
        logger.info("Context history cleared")

    @staticmethod
    def _compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _estimate_tokens(content: str) -> int:
        """Estimate token count from content (rough approximation)."""
        # Rough estimate: ~4 characters per token
        return len(content) // 4


def get_history_tracker(
    spec_dir: Path | None = None,
    max_turns_cache: int = 10,
    resend_threshold: int = 5,
) -> HistoryTracker:
    """
    Factory function to create a HistoryTracker instance.

    Args:
        spec_dir: Directory for spec-specific history persistence
        max_turns_cache: How many turns to keep in memory
        resend_threshold: Turns before considering resending

    Returns:
        Configured HistoryTracker instance

    Example:
        >>> tracker = get_history_tracker(
        ...     spec_dir=Path(".auto-claude/specs/120"),
        ...     max_turns_cache=15,
        ...     resend_threshold=3
        ... )
    """
    return HistoryTracker(
        spec_dir=spec_dir,
        max_turns_cache=max_turns_cache,
        resend_threshold=resend_threshold,
    )
