"""
Data models for task logging.
"""

from dataclasses import asdict, dataclass
from enum import Enum


class LogPhase(str, Enum):
    """Log phases matching the execution flow."""

    PLANNING = "planning"
    CODING = "coding"
    VALIDATION = "validation"


class LogEntryType(str, Enum):
    """Types of log entries."""

    TEXT = "text"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    PHASE_START = "phase_start"
    PHASE_END = "phase_end"
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"


@dataclass
class LogEntry:
    """A single log entry."""

    timestamp: str
    type: str
    content: str
    phase: str
    tool_name: str | None = None
    tool_input: str | None = None
    subtask_id: str | None = None
    session: int | None = None
    # New fields for expandable detail view
    detail: str | None = (
        None  # Full content that can be expanded (e.g., file contents, command output)
    )
    subphase: str | None = (
        None  # Subphase grouping (e.g., "PROJECT DISCOVERY", "CONTEXT GATHERING")
    )
    collapsed: bool | None = None  # Whether to show collapsed by default in UI
    # Decision point tracking fields
    is_decision_point: bool | None = (
        None  # Whether this entry represents an important decision point
    )
    reasoning: str | None = (
        None  # Agent's reasoning/thinking at this decision point
    )
    alternatives: list[str] | None = (
        None  # Alternative options that were considered
    )
    decision: str | None = None  # The final decision or choice made

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PhaseLog:
    """Logs for a single phase."""

    phase: str
    status: str  # "pending", "active", "completed", "failed"
    started_at: str | None = None
    completed_at: str | None = None
    entries: list = None

    def __post_init__(self):
        if self.entries is None:
            self.entries = []

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "entries": self.entries,
        }


@dataclass
class SessionMetadata:
    """Metadata for a session."""

    session_id: int
    started_at: str
    completed_at: str | None = None
    duration_seconds: float | None = None
    subtasks: list[str] | None = None

    def __post_init__(self):
        if self.subtasks is None:
            self.subtasks = []

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values for optional fields."""
        result = {
            "session_id": self.session_id,
            "started_at": self.started_at,
        }
        if self.completed_at is not None:
            result["completed_at"] = self.completed_at
        if self.duration_seconds is not None:
            result["duration_seconds"] = self.duration_seconds
        if self.subtasks:
            result["subtasks"] = self.subtasks
        return result


@dataclass
class SubtaskTransition:
    """A transition between subtasks."""

    timestamp: str
    from_subtask: str | None
    to_subtask: str | None
    session: int | None = None

    def to_dict(self) -> dict:
        """
        Convert to dictionary.

        Always includes from_subtask and to_subtask (even if None) since None
        is meaningful (indicates start/end of subtask work).
        """
        result = {
            "timestamp": self.timestamp,
            "from_subtask": self.from_subtask,
            "to_subtask": self.to_subtask,
        }
        if self.session is not None:
            result["session"] = self.session
        return result
