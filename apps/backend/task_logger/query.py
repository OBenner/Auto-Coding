"""
Query functionality for task logs.
"""

from datetime import datetime
from pathlib import Path

from .storage import load_task_logs


def query_sessions(
    spec_dir: Path,
    session_id: int | None = None,
    status: str | None = None,
    started_after: str | None = None,
    started_before: str | None = None,
    completed: bool | None = None,
    has_subtask: str | None = None,
) -> list[dict]:
    """
    Query sessions with optional filters.

    Args:
        spec_dir: Path to the spec directory
        session_id: Filter by specific session ID
        status: Filter by status (completed, active, failed)
        started_after: Filter sessions started after this ISO timestamp
        started_before: Filter sessions started before this ISO timestamp
        completed: Filter by completion status (True=completed, False=in progress)
        has_subtask: Filter sessions that include this subtask ID

    Returns:
        List of matching session dictionaries
    """
    logs = load_task_logs(spec_dir)
    if not logs or "sessions" not in logs:
        return []

    sessions = logs["sessions"]

    # Apply filters
    if session_id is not None:
        sessions = [s for s in sessions if s.get("session_id") == session_id]

    if completed is not None:
        if completed:
            sessions = [s for s in sessions if s.get("completed_at") is not None]
        else:
            sessions = [s for s in sessions if s.get("completed_at") is None]

    if started_after is not None:
        try:
            after_dt = datetime.fromisoformat(started_after)
            sessions = [
                s
                for s in sessions
                if s.get("started_at")
                and datetime.fromisoformat(s["started_at"]) > after_dt
            ]
        except (ValueError, TypeError):
            pass

    if started_before is not None:
        try:
            before_dt = datetime.fromisoformat(started_before)
            sessions = [
                s
                for s in sessions
                if s.get("started_at")
                and datetime.fromisoformat(s["started_at"]) < before_dt
            ]
        except (ValueError, TypeError):
            pass

    if has_subtask is not None:
        sessions = [s for s in sessions if has_subtask in s.get("subtasks", [])]

    return sessions


def query_entries(
    spec_dir: Path,
    phase: str | None = None,
    entry_type: str | None = None,
    session: int | None = None,
    subtask_id: str | None = None,
    tool_name: str | None = None,
    search_text: str | None = None,
    timestamp_after: str | None = None,
    timestamp_before: str | None = None,
    is_decision_point: bool | None = None,
    limit: int | None = None,
) -> list[dict]:
    """
    Query log entries with optional filters.

    Args:
        spec_dir: Path to the spec directory
        phase: Filter by phase (planning, coding, validation)
        entry_type: Filter by entry type (text, tool_start, tool_end, etc.)
        session: Filter by session number
        subtask_id: Filter by subtask ID
        tool_name: Filter by tool name
        search_text: Search in content field (case-insensitive)
        timestamp_after: Filter entries after this ISO timestamp
        timestamp_before: Filter entries before this ISO timestamp
        is_decision_point: Filter by decision point status
        limit: Maximum number of entries to return

    Returns:
        List of matching log entry dictionaries
    """
    logs = load_task_logs(spec_dir)
    if not logs or "phases" not in logs:
        return []

    entries = []

    # Collect all entries from all phases (shallow copy to avoid mutating stored data)
    for phase_name, phase_data in logs["phases"].items():
        for entry in phase_data.get("entries", []):
            entry_copy = dict(entry)
            # Add phase to entry if not present
            if "phase" not in entry_copy:
                entry_copy["phase"] = phase_name
            entries.append(entry_copy)

    # Apply filters
    if phase is not None:
        entries = [e for e in entries if e.get("phase") == phase]

    if entry_type is not None:
        entries = [e for e in entries if e.get("type") == entry_type]

    if session is not None:
        entries = [e for e in entries if e.get("session") == session]

    if subtask_id is not None:
        entries = [e for e in entries if e.get("subtask_id") == subtask_id]

    if tool_name is not None:
        entries = [e for e in entries if e.get("tool_name") == tool_name]

    if search_text is not None:
        search_lower = search_text.lower()
        entries = [
            e
            for e in entries
            if search_lower in e.get("content", "").lower()
            or search_lower in e.get("detail", "").lower()
            or search_lower in e.get("reasoning", "").lower()
            or search_lower in e.get("decision", "").lower()
            or search_lower in " ".join(e.get("alternatives", [])).lower()
        ]

    if timestamp_after is not None:
        try:
            after_dt = datetime.fromisoformat(timestamp_after)
            entries = [
                e
                for e in entries
                if e.get("timestamp")
                and datetime.fromisoformat(e["timestamp"]) > after_dt
            ]
        except (ValueError, TypeError):
            pass

    if timestamp_before is not None:
        try:
            before_dt = datetime.fromisoformat(timestamp_before)
            entries = [
                e
                for e in entries
                if e.get("timestamp")
                and datetime.fromisoformat(e["timestamp"]) < before_dt
            ]
        except (ValueError, TypeError):
            pass

    if is_decision_point is not None:
        entries = [
            e for e in entries if e.get("is_decision_point") == is_decision_point
        ]

    # Deterministic sort by timestamp before applying limit
    entries.sort(key=lambda e: e.get("timestamp", ""))

    # Apply limit
    if limit is not None and limit > 0:
        entries = entries[:limit]

    return entries


def query_decision_points(
    spec_dir: Path,
    phase: str | None = None,
    session: int | None = None,
    subtask_id: str | None = None,
) -> list[dict]:
    """
    Query decision points from log entries.

    Args:
        spec_dir: Path to the spec directory
        phase: Filter by phase
        session: Filter by session number
        subtask_id: Filter by subtask ID

    Returns:
        List of decision point entries
    """
    return query_entries(
        spec_dir=spec_dir,
        phase=phase,
        session=session,
        subtask_id=subtask_id,
        is_decision_point=True,
    )


def query_subtask_transitions(
    spec_dir: Path,
    session: int | None = None,
    from_subtask: str | None = None,
    to_subtask: str | None = None,
    timestamp_after: str | None = None,
    timestamp_before: str | None = None,
) -> list[dict]:
    """
    Query subtask transitions with optional filters.

    Args:
        spec_dir: Path to the spec directory
        session: Filter by session number
        from_subtask: Filter by source subtask ID
        to_subtask: Filter by target subtask ID
        timestamp_after: Filter transitions after this ISO timestamp
        timestamp_before: Filter transitions before this ISO timestamp

    Returns:
        List of matching subtask transition dictionaries
    """
    logs = load_task_logs(spec_dir)
    if not logs or "subtask_transitions" not in logs:
        return []

    transitions = logs["subtask_transitions"]

    # Apply filters
    if session is not None:
        transitions = [t for t in transitions if t.get("session") == session]

    if from_subtask is not None:
        transitions = [t for t in transitions if t.get("from_subtask") == from_subtask]

    if to_subtask is not None:
        transitions = [t for t in transitions if t.get("to_subtask") == to_subtask]

    if timestamp_after is not None:
        try:
            after_dt = datetime.fromisoformat(timestamp_after)
            transitions = [
                t
                for t in transitions
                if t.get("timestamp")
                and datetime.fromisoformat(t["timestamp"]) > after_dt
            ]
        except (ValueError, TypeError):
            pass

    if timestamp_before is not None:
        try:
            before_dt = datetime.fromisoformat(timestamp_before)
            transitions = [
                t
                for t in transitions
                if t.get("timestamp")
                and datetime.fromisoformat(t["timestamp"]) < before_dt
            ]
        except (ValueError, TypeError):
            pass

    return transitions


def search_all(
    spec_dir: Path,
    search_text: str,
    include_entries: bool = True,
    include_bookmarks: bool = True,
    case_sensitive: bool = False,
) -> dict:
    """
    Search across all log content.

    Args:
        spec_dir: Path to the spec directory
        search_text: Text to search for
        include_entries: Include log entries in search
        include_bookmarks: Include bookmarks in search
        case_sensitive: Perform case-sensitive search

    Returns:
        Dictionary with 'entries' and 'bookmarks' keys containing matching results
    """
    results = {"entries": [], "bookmarks": []}

    logs = load_task_logs(spec_dir)
    if not logs:
        return results

    search_term = search_text if case_sensitive else search_text.lower()

    # Search entries
    if include_entries:
        for phase_name, phase_data in logs.get("phases", {}).items():
            for entry in phase_data.get("entries", []):
                content = entry.get("content", "")
                detail = entry.get("detail", "")
                reasoning = entry.get("reasoning", "")

                if not case_sensitive:
                    content = content.lower()
                    detail = detail.lower()
                    reasoning = reasoning.lower()

                if (
                    search_term in content
                    or search_term in detail
                    or search_term in reasoning
                ):
                    # Add phase to entry if not present
                    if "phase" not in entry:
                        entry["phase"] = phase_name
                    results["entries"].append(entry)

    # Search bookmarks
    if include_bookmarks:
        for bookmark in logs.get("bookmarks", []):
            label = bookmark.get("label", "")
            note = bookmark.get("note", "")

            if not case_sensitive:
                label = label.lower()
                note = note.lower()

            if search_term in label or search_term in note:
                results["bookmarks"].append(bookmark)

    return results


def get_session_timeline(spec_dir: Path, session_id: int) -> dict:
    """
    Get a complete timeline for a specific session.

    Args:
        spec_dir: Path to the spec directory
        session_id: Session number

    Returns:
        Dictionary with session metadata, entries, transitions, and bookmarks
    """
    logs = load_task_logs(spec_dir)
    if not logs:
        return {
            "session": None,
            "entries": [],
            "transitions": [],
            "bookmarks": [],
        }

    # Get session metadata
    session = None
    for s in logs.get("sessions", []):
        if s.get("session_id") == session_id:
            session = s
            break

    # Get entries for this session
    entries = query_entries(spec_dir, session=session_id)

    # Get transitions for this session
    transitions = query_subtask_transitions(spec_dir, session=session_id)

    # Get bookmarks for this session
    bookmarks = []
    for bookmark in logs.get("bookmarks", []):
        if bookmark.get("session") == session_id:
            bookmarks.append(bookmark)

    return {
        "session": session,
        "entries": entries,
        "transitions": transitions,
        "bookmarks": bookmarks,
    }


def get_subtask_timeline(spec_dir: Path, subtask_id: str) -> dict:
    """
    Get a complete timeline for a specific subtask across all sessions.

    Args:
        spec_dir: Path to the spec directory
        subtask_id: Subtask ID

    Returns:
        Dictionary with entries, transitions, and bookmarks for this subtask
    """
    logs = load_task_logs(spec_dir)
    if not logs:
        return {
            "entries": [],
            "transitions": [],
            "bookmarks": [],
            "sessions": [],
        }

    # Get entries for this subtask
    entries = query_entries(spec_dir, subtask_id=subtask_id)

    # Get transitions involving this subtask
    transitions_from = query_subtask_transitions(spec_dir, from_subtask=subtask_id)
    transitions_to = query_subtask_transitions(spec_dir, to_subtask=subtask_id)

    # Combine and deduplicate transitions
    all_transitions = transitions_from + transitions_to
    seen = set()
    unique_transitions = []
    for t in all_transitions:
        key = f"{t.get('timestamp')}_{t.get('from_subtask')}_{t.get('to_subtask')}"
        if key not in seen:
            seen.add(key)
            unique_transitions.append(t)

    # Get bookmarks for this subtask
    bookmarks = []
    for bookmark in logs.get("bookmarks", []):
        if bookmark.get("subtask_id") == subtask_id:
            bookmarks.append(bookmark)

    # Get sessions that worked on this subtask
    sessions = []
    for session in logs.get("sessions", []):
        if subtask_id in session.get("subtasks", []):
            sessions.append(session)

    return {
        "entries": entries,
        "transitions": unique_transitions,
        "bookmarks": bookmarks,
        "sessions": sessions,
    }


def get_phase_summary(spec_dir: Path, phase: str) -> dict:
    """
    Get a summary of a specific phase.

    Args:
        spec_dir: Path to the spec directory
        phase: Phase name (planning, coding, validation)

    Returns:
        Dictionary with phase metadata and statistics
    """
    logs = load_task_logs(spec_dir)
    if not logs or "phases" not in logs:
        return {
            "phase": phase,
            "status": "unknown",
            "started_at": None,
            "completed_at": None,
            "entry_count": 0,
            "tool_usage": {},
            "decision_points": 0,
        }

    phase_data = logs["phases"].get(phase, {})
    entries = phase_data.get("entries", [])

    # Count tool usage
    tool_usage = {}
    decision_points = 0

    for entry in entries:
        if entry.get("tool_name"):
            tool_name = entry["tool_name"]
            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

        if entry.get("is_decision_point"):
            decision_points += 1

    return {
        "phase": phase,
        "status": phase_data.get("status", "unknown"),
        "started_at": phase_data.get("started_at"),
        "completed_at": phase_data.get("completed_at"),
        "entry_count": len(entries),
        "tool_usage": tool_usage,
        "decision_points": decision_points,
    }
