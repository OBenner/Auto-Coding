"""
Storage functionality for task logs.
"""

import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .models import Bookmark, LogEntry, LogPhase, SessionMetadata, SubtaskTransition

# Regex to strip ANSI escape codes (full CSI sequences including colors, cursor moves)
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class LogStorage:
    """Handles persistent storage of task logs."""

    LOG_FILE = "task_logs.json"

    def __init__(self, spec_dir: Path):
        """
        Initialize log storage.

        Args:
            spec_dir: Path to the spec directory
        """
        self.spec_dir = Path(spec_dir)
        self.log_file = self.spec_dir / self.LOG_FILE
        self._data: dict = self._load_or_create()

    def _load_or_create(self) -> dict:
        """Load existing logs or create new structure."""
        if self.log_file.exists():
            try:
                with open(self.log_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # Ensure required keys exist (for backward compatibility)
                    if "sessions" not in data:
                        data["sessions"] = []
                    if "subtask_transitions" not in data:
                        data["subtask_transitions"] = []
                    if "bookmarks" not in data:
                        data["bookmarks"] = []
                    return data
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                pass

        return {
            "spec_id": self.spec_dir.name,
            "created_at": self._timestamp(),
            "updated_at": self._timestamp(),
            "phases": {
                LogPhase.PLANNING.value: {
                    "phase": LogPhase.PLANNING.value,
                    "status": "pending",
                    "started_at": None,
                    "completed_at": None,
                    "entries": [],
                },
                LogPhase.CODING.value: {
                    "phase": LogPhase.CODING.value,
                    "status": "pending",
                    "started_at": None,
                    "completed_at": None,
                    "entries": [],
                },
                LogPhase.VALIDATION.value: {
                    "phase": LogPhase.VALIDATION.value,
                    "status": "pending",
                    "started_at": None,
                    "completed_at": None,
                    "entries": [],
                },
            },
            "sessions": [],
            "subtask_transitions": [],
            "bookmarks": [],
        }

    def save(self) -> None:
        """Save logs to file atomically to prevent corruption from concurrent reads."""
        self._data["updated_at"] = self._timestamp()
        try:
            self.spec_dir.mkdir(parents=True, exist_ok=True)
            # Write to temp file first, then atomic rename to prevent corruption
            # when the UI reads mid-write
            fd, tmp_path = tempfile.mkstemp(
                dir=self.spec_dir, prefix=".task_logs_", suffix=".tmp"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2, ensure_ascii=False)
                # Atomic rename (on POSIX systems, rename is atomic)
                os.replace(tmp_path, self.log_file)
            except Exception:
                # Clean up temp file on failure
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
        except OSError as e:
            print(f"Warning: Failed to save task logs: {e}", file=sys.stderr)

    def _timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Strip ANSI escape codes from text for clean storage and UI display."""
        return _ANSI_ESCAPE_RE.sub("", text)

    def add_entry(self, entry: LogEntry) -> None:
        """
        Add an entry to the specified phase.
        ANSI escape codes are stripped from content, detail, and tool_input fields before storage.

        Args:
            entry: The log entry to add
        """
        phase_key = entry.phase
        if phase_key not in self._data["phases"]:
            # Create phase if it doesn't exist
            self._data["phases"][phase_key] = {
                "phase": phase_key,
                "status": "active",
                "started_at": self._timestamp(),
                "completed_at": None,
                "entries": [],
            }

        entry_dict = entry.to_dict()
        # Strip ANSI escape codes from text fields before persisting
        if "content" in entry_dict and isinstance(entry_dict["content"], str):
            entry_dict["content"] = self._strip_ansi(entry_dict["content"])
        if "detail" in entry_dict and isinstance(entry_dict["detail"], str):
            entry_dict["detail"] = self._strip_ansi(entry_dict["detail"])
        if "tool_input" in entry_dict and isinstance(entry_dict["tool_input"], str):
            entry_dict["tool_input"] = self._strip_ansi(entry_dict["tool_input"])

        self._data["phases"][phase_key]["entries"].append(entry_dict)
        self.save()

    def update_phase_status(
        self, phase: str, status: str, completed_at: str | None = None
    ) -> None:
        """
        Update phase status.

        Args:
            phase: Phase name
            status: New status (pending, active, completed, failed)
            completed_at: Optional completion timestamp
        """
        if phase in self._data["phases"]:
            self._data["phases"][phase]["status"] = status
            if completed_at:
                self._data["phases"][phase]["completed_at"] = completed_at

    def set_phase_started(self, phase: str, started_at: str) -> None:
        """
        Set phase start time.

        Args:
            phase: Phase name
            started_at: Start timestamp
        """
        if phase in self._data["phases"]:
            self._data["phases"][phase]["started_at"] = started_at

    def get_data(self) -> dict:
        """Get all log data."""
        return self._data

    def get_phase_data(self, phase: str) -> dict:
        """Get data for a specific phase."""
        return self._data["phases"].get(phase, {})

    def update_spec_id(self, new_spec_id: str) -> None:
        """
        Update the spec ID in the data.

        Args:
            new_spec_id: New spec ID
        """
        self._data["spec_id"] = new_spec_id

    def start_session(self, session_id: int) -> None:
        """
        Start a new session.

        If a session with the given ID already exists, this is a no-op.

        Args:
            session_id: Session number
        """
        # Initialize sessions list if it doesn't exist (for backward compatibility)
        if "sessions" not in self._data:
            self._data["sessions"] = []

        # Check for existing session with the same ID to prevent duplicates
        for existing in self._data["sessions"]:
            if existing.get("session_id") == session_id:
                return

        session = SessionMetadata(
            session_id=session_id,
            started_at=self._timestamp(),
        )
        self._data["sessions"].append(session.to_dict())
        self.save()

    def end_session(self, session_id: int) -> None:
        """
        End a session and calculate duration.

        Args:
            session_id: Session number to end
        """
        if "sessions" not in self._data:
            return

        # Find the session
        for session in self._data["sessions"]:
            if session["session_id"] == session_id:
                completed_at = self._timestamp()
                session["completed_at"] = completed_at

                # Calculate duration in seconds
                try:
                    started = datetime.fromisoformat(session["started_at"])
                    completed = datetime.fromisoformat(completed_at)
                    duration = (completed - started).total_seconds()
                    session["duration_seconds"] = duration
                except (ValueError, KeyError):
                    # Gracefully handle missing or malformed timestamps in session data
                    pass

                self.save()
                break

    def add_subtask_to_session(self, session_id: int, subtask_id: str) -> None:
        """
        Add a subtask to a session's list of subtasks.

        Args:
            session_id: Session number
            subtask_id: Subtask ID
        """
        if "sessions" not in self._data:
            return

        # Find the session
        for session in self._data["sessions"]:
            if session["session_id"] == session_id:
                if "subtasks" not in session:
                    session["subtasks"] = []
                if subtask_id not in session["subtasks"]:
                    session["subtasks"].append(subtask_id)
                    self.save()
                break

    def add_subtask_transition(
        self,
        from_subtask: str | None,
        to_subtask: str | None,
        session: int | None = None,
    ) -> None:
        """
        Record a subtask transition.

        Args:
            from_subtask: Previous subtask ID (None if starting first subtask)
            to_subtask: New subtask ID (None if ending subtask)
            session: Session number
        """
        # Initialize subtask_transitions list if it doesn't exist (for backward compatibility)
        if "subtask_transitions" not in self._data:
            self._data["subtask_transitions"] = []

        transition = SubtaskTransition(
            timestamp=self._timestamp(),
            from_subtask=from_subtask,
            to_subtask=to_subtask,
            session=session,
        )
        self._data["subtask_transitions"].append(transition.to_dict())
        self.save()

    def get_session_data(self, session_id: int) -> dict | None:
        """
        Get data for a specific session.

        Args:
            session_id: Session number

        Returns:
            Session data or None if not found
        """
        if "sessions" not in self._data:
            return None

        for session in self._data["sessions"]:
            if session["session_id"] == session_id:
                return session
        return None

    def add_bookmark(self, bookmark: Bookmark) -> None:
        """
        Add a bookmark to the logs.

        Args:
            bookmark: The bookmark to add
        """
        # Initialize bookmarks list if it doesn't exist (for backward compatibility)
        if "bookmarks" not in self._data:
            self._data["bookmarks"] = []

        # Prevent duplicate bookmarks with the same ID
        bookmark_dict = bookmark.to_dict()
        bookmark_id = bookmark_dict.get("id")
        if bookmark_id:
            for existing in self._data["bookmarks"]:
                if existing.get("id") == bookmark_id:
                    return

        self._data["bookmarks"].append(bookmark_dict)
        self.save()

    def get_bookmarks(
        self,
        phase: str | None = None,
        session: int | None = None,
        subtask_id: str | None = None,
    ) -> list[dict]:
        """
        Get bookmarks, optionally filtered by phase, session, or subtask.

        Args:
            phase: Optional phase filter
            session: Optional session filter
            subtask_id: Optional subtask filter

        Returns:
            List of bookmark dictionaries
        """
        if "bookmarks" not in self._data:
            return []

        bookmarks = self._data["bookmarks"]

        # Apply filters
        if phase is not None:
            bookmarks = [b for b in bookmarks if b.get("phase") == phase]
        if session is not None:
            bookmarks = [b for b in bookmarks if b.get("session") == session]
        if subtask_id is not None:
            bookmarks = [b for b in bookmarks if b.get("subtask_id") == subtask_id]

        return bookmarks

    def remove_bookmark(self, bookmark_id: str) -> bool:
        """
        Remove a bookmark by its ID.

        Args:
            bookmark_id: The bookmark ID to remove

        Returns:
            True if bookmark was found and removed, False otherwise
        """
        if "bookmarks" not in self._data:
            return False

        initial_length = len(self._data["bookmarks"])
        self._data["bookmarks"] = [
            b for b in self._data["bookmarks"] if b.get("id") != bookmark_id
        ]

        if len(self._data["bookmarks"]) < initial_length:
            self.save()
            return True
        return False


def load_task_logs(spec_dir: Path) -> dict | None:
    """
    Load task logs from a spec directory.

    Args:
        spec_dir: Path to the spec directory

    Returns:
        Logs dictionary or None if not found
    """
    log_file = spec_dir / LogStorage.LOG_FILE
    if not log_file.exists():
        return None

    try:
        with open(log_file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def get_active_phase(spec_dir: Path) -> str | None:
    """
    Get the currently active phase for a spec.

    Args:
        spec_dir: Path to the spec directory

    Returns:
        Phase name or None if no active phase
    """
    logs = load_task_logs(spec_dir)
    if not logs:
        return None

    for phase_name, phase_data in logs.get("phases", {}).items():
        if phase_data.get("status") == "active":
            return phase_name

    return None
