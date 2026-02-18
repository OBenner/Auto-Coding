"""
Export functionality for task logs.
"""

import json
from pathlib import Path

from .query import get_session_timeline
from .storage import load_task_logs


def export_session(
    spec_dir: Path,
    session_id: int,
    format: str = "json",
    include_entries: bool = True,
    include_transitions: bool = True,
    include_bookmarks: bool = True,
) -> str:
    """
    Export a single session to JSON or markdown format.

    Args:
        spec_dir: Path to the spec directory
        session_id: Session ID to export
        format: Export format ("json" or "markdown")
        include_entries: Include log entries in export
        include_transitions: Include subtask transitions in export
        include_bookmarks: Include bookmarks in export

    Returns:
        Exported data as a string

    Raises:
        ValueError: If format is not "json" or "markdown"
        FileNotFoundError: If session not found
    """
    if format not in ("json", "markdown"):
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'markdown'.")

    timeline = get_session_timeline(spec_dir, session_id)
    if not timeline or not isinstance(timeline, dict) or not timeline.get("session"):
        raise FileNotFoundError(f"Session {session_id} not found")

    # Build export data
    export_data = {
        "session": timeline["session"],
    }

    if include_entries:
        export_data["entries"] = timeline["entries"]
    if include_transitions:
        export_data["transitions"] = timeline["transitions"]
    if include_bookmarks:
        export_data["bookmarks"] = timeline["bookmarks"]

    if format == "json":
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    else:
        return _format_session_markdown(export_data)


def export_all_sessions(
    spec_dir: Path,
    format: str = "json",
    include_entries: bool = True,
    include_transitions: bool = True,
    include_bookmarks: bool = True,
) -> str:
    """
    Export all sessions to JSON or markdown format.

    Args:
        spec_dir: Path to the spec directory
        format: Export format ("json" or "markdown")
        include_entries: Include log entries in export
        include_transitions: Include subtask transitions in export
        include_bookmarks: Include bookmarks in export

    Returns:
        Exported data as a string

    Raises:
        ValueError: If format is not "json" or "markdown"
    """
    if format not in ("json", "markdown"):
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'markdown'.")

    logs = load_task_logs(spec_dir)
    if not logs:
        return json.dumps({}) if format == "json" else ""

    export_data = {
        "spec_id": logs.get("spec_id"),
        "created_at": logs.get("created_at"),
        "updated_at": logs.get("updated_at"),
        "sessions": logs.get("sessions", []),
    }

    if include_entries:
        export_data["phases"] = logs.get("phases", {})
    if include_transitions:
        export_data["subtask_transitions"] = logs.get("subtask_transitions", [])
    if include_bookmarks:
        export_data["bookmarks"] = logs.get("bookmarks", [])

    if format == "json":
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    else:
        return _format_all_sessions_markdown(export_data)


def export_phase(
    spec_dir: Path,
    phase: str,
    format: str = "json",
) -> str:
    """
    Export a specific phase to JSON or markdown format.

    Args:
        spec_dir: Path to the spec directory
        phase: Phase name (planning, coding, validation)
        format: Export format ("json" or "markdown")

    Returns:
        Exported data as a string

    Raises:
        ValueError: If format is not "json" or "markdown"
        FileNotFoundError: If phase not found
    """
    if format not in ("json", "markdown"):
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'markdown'.")

    logs = load_task_logs(spec_dir)
    if not logs or "phases" not in logs:
        raise FileNotFoundError("No log data found")

    if phase not in logs["phases"]:
        raise FileNotFoundError(f"Phase {phase} not found")

    phase_data = logs["phases"][phase]

    if format == "json":
        return json.dumps(phase_data, indent=2, ensure_ascii=False)
    else:
        return _format_phase_markdown(phase_data)


def _matches_decision_point_filters(
    entry: dict,
    session_id: int | None,
) -> bool:
    """Check if a decision point entry matches the session filter."""
    if not entry.get("is_decision_point"):
        return False
    if session_id is not None and entry.get("session") != session_id:
        return False
    return True


def _collect_decision_points_from_phase(
    phase_name: str,
    phase_data: dict,
    session_id: int | None,
) -> list[dict]:
    """Collect matching decision points from a single phase."""
    points = []
    for entry in phase_data.get("entries", []):
        if not _matches_decision_point_filters(entry, session_id):
            continue
        if "phase" not in entry:
            entry = {**entry, "phase": phase_name}
        points.append(entry)
    return points


def export_decision_points(
    spec_dir: Path,
    format: str = "json",
    session_id: int | None = None,
    phase: str | None = None,
) -> str:
    """
    Export decision points to JSON or markdown format.

    Args:
        spec_dir: Path to the spec directory
        format: Export format ("json" or "markdown")
        session_id: Optional session ID filter
        phase: Optional phase filter

    Returns:
        Exported data as a string

    Raises:
        ValueError: If format is not "json" or "markdown"
    """
    if format not in ("json", "markdown"):
        raise ValueError(f"Unsupported format: {format}. Use 'json' or 'markdown'.")

    logs = load_task_logs(spec_dir)
    if not logs or "phases" not in logs:
        return json.dumps([]) if format == "json" else ""

    decision_points = []

    for phase_name, phase_data in logs["phases"].items():
        if phase and phase_name != phase:
            continue
        decision_points.extend(
            _collect_decision_points_from_phase(phase_name, phase_data, session_id)
        )

    if format == "json":
        return json.dumps(decision_points, indent=2, ensure_ascii=False)
    return _format_decision_points_markdown(decision_points)


def _format_session_metadata(session: dict, lines: list[str]) -> None:
    """Append session metadata lines."""
    lines.append(f"# Session {session['session_id']}")
    lines.append("")
    lines.append("## Session Metadata")
    lines.append("")
    lines.append(f"- **Started At:** {session.get('started_at', 'N/A')}")
    lines.append(f"- **Completed At:** {session.get('completed_at', 'N/A')}")

    duration = session.get("duration_seconds")
    if duration is not None:
        lines.append(f"- **Duration:** {duration:.2f} seconds")

    subtasks = session.get("subtasks", [])
    if subtasks:
        lines.append(f"- **Subtasks:** {', '.join(subtasks)}")

    lines.append("")


def _format_bookmarks_section(bookmarks: list[dict], lines: list[str]) -> None:
    """Append bookmarks section lines."""
    if not bookmarks:
        return
    lines.append("## Bookmarks")
    lines.append("")
    for bookmark in bookmarks:
        lines.append(f"### {bookmark['label']}")
        lines.append(f"- **Timestamp:** {bookmark['entry_timestamp']}")
        lines.append(f"- **Phase:** {bookmark['phase']}")
        if bookmark.get("note"):
            lines.append(f"- **Note:** {bookmark['note']}")
        lines.append("")


def _format_transitions_section(transitions: list[dict], lines: list[str]) -> None:
    """Append transitions section lines."""
    if not transitions:
        return
    lines.append("## Subtask Transitions")
    lines.append("")
    for transition in transitions:
        from_subtask = transition.get("from_subtask") or "None"
        to_subtask = transition.get("to_subtask") or "None"
        timestamp = transition.get("timestamp", "N/A")
        lines.append(f"- **{timestamp}**: {from_subtask} \u2192 {to_subtask}")
    lines.append("")


def _format_entry_details(entry: dict, lines: list[str]) -> None:
    """Append detail lines for a single log entry."""
    timestamp = entry.get("timestamp", "N/A")
    entry_type = entry.get("type", "unknown")
    content = entry.get("content", "")

    lines.append(f"#### [{timestamp}] {entry_type}")
    if content:
        lines.append(f"{content}")

    if entry.get("is_decision_point"):
        _format_entry_decision_point(entry, lines)

    if entry.get("tool_name"):
        lines.append(f"- **Tool:** {entry['tool_name']}")
    if entry.get("subtask_id"):
        lines.append(f"- **Subtask:** {entry['subtask_id']}")

    lines.append("")


def _format_entry_decision_point(entry: dict, lines: list[str]) -> None:
    """Append decision point details for an entry."""
    lines.append("")
    lines.append("**Decision Point:**")
    if entry.get("reasoning"):
        lines.append(f"- **Reasoning:** {entry['reasoning']}")
    if entry.get("decision"):
        lines.append(f"- **Decision:** {entry['decision']}")
    if entry.get("alternatives"):
        lines.append(f"- **Alternatives:** {', '.join(entry['alternatives'])}")


def _format_entries_section(entries: list[dict], lines: list[str]) -> None:
    """Append log entries section grouped by phase."""
    if not entries:
        return
    lines.append("## Log Entries")
    lines.append("")

    by_phase: dict[str, list[dict]] = {}
    for entry in entries:
        phase = entry.get("phase", "unknown")
        if phase not in by_phase:
            by_phase[phase] = []
        by_phase[phase].append(entry)

    for phase, phase_entries in by_phase.items():
        lines.append(f"### Phase: {phase.title()}")
        lines.append("")
        for entry in phase_entries:
            _format_entry_details(entry, lines)


def _format_session_markdown(data: dict) -> str:
    """Format session data as markdown."""
    lines: list[str] = []

    _format_session_metadata(data["session"], lines)
    _format_bookmarks_section(data.get("bookmarks", []), lines)
    _format_transitions_section(data.get("transitions", []), lines)
    _format_entries_section(data.get("entries", []), lines)

    return "\n".join(lines)


def _format_all_sessions_header(data: dict, lines: list[str]) -> None:
    """Append the header section for all-sessions export."""
    spec_id = data.get("spec_id", "Unknown")
    lines.append(f"# Task Log Export: {spec_id}")
    lines.append("")
    lines.append(f"**Created At:** {data.get('created_at', 'N/A')}")
    lines.append(f"**Updated At:** {data.get('updated_at', 'N/A')}")
    lines.append("")


def _format_sessions_list(sessions: list[dict], lines: list[str]) -> None:
    """Append individual session summaries."""
    lines.append(f"## Sessions ({len(sessions)})")
    lines.append("")

    for session in sessions:
        lines.append(f"### Session {session['session_id']}")
        lines.append(f"- **Started:** {session.get('started_at', 'N/A')}")
        lines.append(f"- **Completed:** {session.get('completed_at', 'N/A')}")
        duration = session.get("duration_seconds")
        if duration is not None:
            lines.append(f"- **Duration:** {duration:.2f} seconds")
        subtasks = session.get("subtasks", [])
        if subtasks:
            lines.append(f"- **Subtasks:** {', '.join(subtasks)}")
        lines.append("")


def _format_phases_summary(phases: dict, lines: list[str]) -> None:
    """Append phases summary section."""
    if not phases:
        return
    lines.append("## Phases")
    lines.append("")
    for phase_name, phase_data in phases.items():
        status = phase_data.get("status", "unknown")
        entry_count = len(phase_data.get("entries", []))
        lines.append(f"### {phase_name.title()}")
        lines.append(f"- **Status:** {status}")
        lines.append(f"- **Entries:** {entry_count}")
        lines.append("")


def _format_all_bookmarks_section(bookmarks: list[dict], lines: list[str]) -> None:
    """Append bookmarks section for all-sessions export."""
    if not bookmarks:
        return
    lines.append(f"## Bookmarks ({len(bookmarks)})")
    lines.append("")
    for bookmark in bookmarks:
        lines.append(f"### {bookmark['label']}")
        lines.append(f"- **Phase:** {bookmark['phase']}")
        lines.append(f"- **Timestamp:** {bookmark['entry_timestamp']}")
        if bookmark.get("session"):
            lines.append(f"- **Session:** {bookmark['session']}")
        if bookmark.get("note"):
            lines.append(f"- **Note:** {bookmark['note']}")
        lines.append("")


def _format_all_sessions_markdown(data: dict) -> str:
    """Format all sessions data as markdown."""
    lines: list[str] = []

    _format_all_sessions_header(data, lines)
    _format_sessions_list(data.get("sessions", []), lines)
    _format_phases_summary(data.get("phases", {}), lines)
    _format_all_bookmarks_section(data.get("bookmarks", []), lines)

    return "\n".join(lines)


def _format_phase_markdown(phase_data: dict) -> str:
    """Format phase data as markdown."""
    lines = []

    phase_name = phase_data.get("phase", "Unknown")
    lines.append(f"# Phase: {phase_name.title()}")
    lines.append("")

    # Metadata
    lines.append("## Phase Status")
    lines.append("")
    lines.append(f"- **Status:** {phase_data.get('status', 'unknown')}")
    lines.append(f"- **Started At:** {phase_data.get('started_at', 'N/A')}")
    lines.append(f"- **Completed At:** {phase_data.get('completed_at', 'N/A')}")
    lines.append("")

    # Entries
    entries = phase_data.get("entries", [])
    if entries:
        lines.append(f"## Log Entries ({len(entries)})")
        lines.append("")

        for entry in entries:
            timestamp = entry.get("timestamp", "N/A")
            entry_type = entry.get("type", "unknown")
            content = entry.get("content", "")

            lines.append(f"### [{timestamp}] {entry_type}")
            if content:
                lines.append(f"{content}")

            if entry.get("tool_name"):
                lines.append(f"- **Tool:** {entry['tool_name']}")
            if entry.get("subtask_id"):
                lines.append(f"- **Subtask:** {entry['subtask_id']}")

            lines.append("")

    return "\n".join(lines)


def _format_single_decision_point(dp: dict, lines: list[str]) -> None:
    """Format a single decision point as markdown."""
    timestamp = dp.get("timestamp", "N/A")
    phase = dp.get("phase", "unknown")
    content = dp.get("content", "")

    lines.append(f"## [{timestamp}] Phase: {phase.title()}")
    lines.append("")

    if content:
        lines.append(f"**Summary:** {content}")
        lines.append("")

    if dp.get("reasoning"):
        lines.append("### Reasoning")
        lines.append(dp["reasoning"])
        lines.append("")

    if dp.get("decision"):
        lines.append("### Decision")
        lines.append(dp["decision"])
        lines.append("")

    if dp.get("alternatives"):
        lines.append("### Alternatives Considered")
        for alt in dp["alternatives"]:
            lines.append(f"- {alt}")
        lines.append("")

    if dp.get("session"):
        lines.append(f"**Session:** {dp['session']}")
    if dp.get("subtask_id"):
        lines.append(f"**Subtask:** {dp['subtask_id']}")

    lines.append("")
    lines.append("---")
    lines.append("")


def _format_decision_points_markdown(decision_points: list[dict]) -> str:
    """Format decision points as markdown."""
    lines: list[str] = []

    lines.append(f"# Decision Points ({len(decision_points)})")
    lines.append("")

    for dp in decision_points:
        _format_single_decision_point(dp, lines)

    return "\n".join(lines)
