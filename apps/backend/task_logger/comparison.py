"""
Session comparison utilities for analyzing and learning from agent behavior.
"""

import logging
from datetime import datetime
from pathlib import Path

from .storage import load_task_logs

logger = logging.getLogger(__name__)


def _normalize_subtasks(subtasks: list) -> set[str]:
    """Extract string IDs from a list of subtasks.

    Handles both plain string IDs and dict objects with an "id" key.

    Args:
        subtasks: List of subtask identifiers (strings or dicts with "id").

    Returns:
        Set of string subtask IDs.
    """
    result: set[str] = set()
    for item in subtasks:
        if isinstance(item, str):
            result.add(item)
        elif isinstance(item, dict) and "id" in item:
            result.add(str(item["id"]))
    return result


def compare_sessions(
    spec_dir: Path,
    session_ids: list[int],
) -> dict:
    """
    Compare multiple sessions side-by-side.

    Args:
        spec_dir: Path to the spec directory
        session_ids: List of session IDs to compare

    Returns:
        Dictionary with comparison data including:
        - sessions: List of session metadata
        - metrics: Compared metrics (duration, subtask counts, tool usage)
        - common_subtasks: Subtasks worked on by multiple sessions
        - unique_subtasks: Subtasks unique to each session
    """
    logs = load_task_logs(spec_dir)
    if not logs or "sessions" not in logs:
        return {
            "sessions": [],
            "metrics": {},
            "common_subtasks": [],
            "unique_subtasks": {},
        }

    # Find requested sessions
    sessions = []
    for session_id in session_ids:
        session_data = next(
            (s for s in logs["sessions"] if s.get("session_id") == session_id),
            None,
        )
        if session_data:
            sessions.append(session_data)

    if not sessions:
        return {
            "sessions": [],
            "metrics": {},
            "common_subtasks": [],
            "unique_subtasks": {},
        }

    # Compare metrics
    metrics = {
        "durations": {},
        "subtask_counts": {},
        "completion_status": {},
    }

    for session in sessions:
        session_id = session["session_id"]
        metrics["durations"][session_id] = session.get("duration_seconds")
        metrics["subtask_counts"][session_id] = len(session.get("subtasks", []))
        metrics["completion_status"][session_id] = (
            "completed" if session.get("completed_at") else "in_progress"
        )

    # Find common and unique subtasks
    subtask_sets = {
        s["session_id"]: _normalize_subtasks(s.get("subtasks", [])) for s in sessions
    }

    common_subtasks = []
    if len(subtask_sets) > 1:
        # Find intersection of all session subtasks
        common_subtasks = list(set.intersection(*subtask_sets.values()))

    unique_subtasks = {}
    for session_id, subtasks in subtask_sets.items():
        other_sessions = [sid for sid in subtask_sets if sid != session_id]
        if other_sessions:
            other_subtasks = set.union(*[subtask_sets[sid] for sid in other_sessions])
            unique = subtasks - other_subtasks
            unique_subtasks[session_id] = list(unique)
        else:
            unique_subtasks[session_id] = list(subtasks)

    return {
        "sessions": sessions,
        "metrics": metrics,
        "common_subtasks": sorted(common_subtasks),
        "unique_subtasks": unique_subtasks,
    }


def compare_session_approaches(
    spec_dir: Path,
    session_ids: list[int],
    subtask_id: str | None = None,
) -> dict:
    """
    Compare how different sessions approached the same subtask or overall work.

    Args:
        spec_dir: Path to the spec directory
        session_ids: List of session IDs to compare
        subtask_id: Optional specific subtask to compare (None for overall comparison)

    Returns:
        Dictionary with approach comparison data including:
        - subtask_id: The subtask being compared (or None)
        - sessions: List of session approaches with tool usage, entry counts, etc.
        - tool_usage_comparison: Tool usage patterns across sessions
        - decision_points: Decision points from each session
    """
    logs = load_task_logs(spec_dir)
    if not logs:
        return {
            "subtask_id": subtask_id,
            "sessions": [],
            "tool_usage_comparison": {},
            "decision_points": {},
        }

    # Collect entries for each session
    session_approaches = []

    for session_id in session_ids:
        # Find entries for this session
        entries = []
        for phase_data in logs.get("phases", {}).values():
            for entry in phase_data.get("entries", []):
                if entry.get("session") == session_id:
                    # Filter by subtask if specified
                    if subtask_id is None or entry.get("subtask_id") == subtask_id:
                        entries.append(entry)

        if entries:
            # Analyze tool usage
            tool_usage = {}
            decision_points = []

            for entry in entries:
                # Count tool usage
                if entry.get("type") == "tool_start":
                    tool_name = entry.get("tool_name", "unknown")
                    tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

                # Collect decision points
                if entry.get("is_decision_point"):
                    decision_points.append(
                        {
                            "timestamp": entry.get("timestamp"),
                            "content": entry.get("content"),
                            "reasoning": entry.get("reasoning"),
                            "decision": entry.get("decision"),
                            "alternatives": entry.get("alternatives", []),
                        }
                    )

            session_approaches.append(
                {
                    "session_id": session_id,
                    "entry_count": len(entries),
                    "tool_usage": tool_usage,
                    "decision_points": decision_points,
                    "start_time": entries[0].get("timestamp") if entries else None,
                    "end_time": entries[-1].get("timestamp") if entries else None,
                }
            )

    # Compare tool usage across sessions
    tool_usage_comparison = {}
    for approach in session_approaches:
        session_id = approach["session_id"]
        for tool, count in approach["tool_usage"].items():
            if tool not in tool_usage_comparison:
                tool_usage_comparison[tool] = {}
            tool_usage_comparison[tool][session_id] = count

    # Collect all decision points by session
    decision_points_by_session = {
        approach["session_id"]: approach["decision_points"]
        for approach in session_approaches
    }

    return {
        "subtask_id": subtask_id,
        "sessions": session_approaches,
        "tool_usage_comparison": tool_usage_comparison,
        "decision_points": decision_points_by_session,
    }


def get_session_summary(
    spec_dir: Path,
    session_id: int,
) -> dict | None:
    """
    Get a detailed summary of a single session.

    Args:
        spec_dir: Path to the spec directory
        session_id: Session ID to summarize

    Returns:
        Dictionary with session summary or None if session not found
    """
    logs = load_task_logs(spec_dir)
    if not logs or "sessions" not in logs:
        return None

    # Find the session
    session = next(
        (s for s in logs["sessions"] if s.get("session_id") == session_id),
        None,
    )
    if not session:
        return None

    # Collect all entries for this session
    entries = []
    for phase_name, phase_data in logs.get("phases", {}).items():
        for entry in phase_data.get("entries", []):
            if entry.get("session") == session_id:
                entries.append({**entry, "phase": phase_name})

    # Analyze tool usage
    tool_usage = {}
    decision_count = 0
    error_count = 0

    for entry in entries:
        if entry.get("type") == "tool_start":
            tool_name = entry.get("tool_name", "unknown")
            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
        if entry.get("is_decision_point"):
            decision_count += 1
        if entry.get("type") == "error":
            error_count += 1

    # Calculate time spent per subtask
    subtask_times: dict[str, float] = {}
    transitions = logs.get("subtask_transitions", [])
    session_transitions = [t for t in transitions if t.get("session") == session_id]

    # Sort transitions by timestamp for correct duration calculation
    session_transitions.sort(key=lambda t: t.get("timestamp", ""))

    for i, transition in enumerate(session_transitions):
        to_subtask = transition.get("to_subtask")
        if to_subtask and i + 1 < len(session_transitions):
            # Calculate time until next transition
            try:
                start = datetime.fromisoformat(transition["timestamp"])
                end = datetime.fromisoformat(session_transitions[i + 1]["timestamp"])
                duration = (end - start).total_seconds()
                # Accumulate durations for subtasks visited multiple times
                subtask_times[to_subtask] = subtask_times.get(to_subtask, 0) + duration
            except (ValueError, KeyError) as exc:
                logger.warning(
                    "Skipping transition with invalid timestamp "
                    "(session=%s, to_subtask=%s): %s",
                    session_id,
                    to_subtask,
                    exc,
                )

    return {
        "session": session,
        "entry_count": len(entries),
        "tool_usage": tool_usage,
        "decision_point_count": decision_count,
        "error_count": error_count,
        "subtask_times": subtask_times,
        "subtasks": session.get("subtasks", []),
    }


def compare_session_metrics(
    spec_dir: Path,
    session_ids: list[int],
) -> dict:
    """
    Compare quantitative metrics across sessions.

    Args:
        spec_dir: Path to the spec directory
        session_ids: List of session IDs to compare

    Returns:
        Dictionary with metrics comparison including:
        - duration: Duration in seconds for each session
        - tool_usage: Total tool calls per session
        - subtask_count: Number of subtasks per session
        - decision_count: Number of decision points per session
        - error_count: Number of errors per session
        - efficiency: Subtasks per hour (if completed)
    """
    logs = load_task_logs(spec_dir)
    if not logs:
        return {
            "duration": {},
            "tool_usage": {},
            "subtask_count": {},
            "decision_count": {},
            "error_count": {},
            "efficiency": {},
        }

    metrics = {
        "duration": {},
        "tool_usage": {},
        "subtask_count": {},
        "decision_count": {},
        "error_count": {},
        "efficiency": {},
    }

    for session_id in session_ids:
        summary = get_session_summary(spec_dir, session_id)
        if not summary:
            continue

        session = summary["session"]
        metrics["duration"][session_id] = session.get("duration_seconds")
        metrics["subtask_count"][session_id] = len(summary["subtasks"])

        # Count total tool usage
        total_tools = sum(summary["tool_usage"].values())
        metrics["tool_usage"][session_id] = total_tools

        metrics["decision_count"][session_id] = summary["decision_point_count"]
        metrics["error_count"][session_id] = summary["error_count"]

        # Calculate efficiency (subtasks per hour)
        duration = session.get("duration_seconds")
        subtask_count = len(summary["subtasks"])
        if duration and duration > 0 and subtask_count > 0:
            hours = duration / 3600
            efficiency = subtask_count / hours
            metrics["efficiency"][session_id] = round(efficiency, 2)
        else:
            metrics["efficiency"][session_id] = None

    return metrics


def find_similar_sessions(
    spec_dir: Path,
    session_id: int,
    similarity_threshold: float = 0.5,
) -> list[dict]:
    """
    Find sessions similar to the given session based on subtask overlap.

    Args:
        spec_dir: Path to the spec directory
        session_id: Reference session ID
        similarity_threshold: Minimum similarity score (0.0 to 1.0) to include

    Returns:
        List of similar sessions with similarity scores, sorted by score descending
    """
    logs = load_task_logs(spec_dir)
    if not logs or "sessions" not in logs:
        return []

    # Find the reference session
    ref_session = next(
        (s for s in logs["sessions"] if s.get("session_id") == session_id),
        None,
    )
    if not ref_session:
        return []

    ref_subtasks = _normalize_subtasks(ref_session.get("subtasks", []))
    if not ref_subtasks:
        return []

    similar_sessions = []

    for session in logs["sessions"]:
        if session["session_id"] == session_id:
            continue

        session_subtasks = _normalize_subtasks(session.get("subtasks", []))
        if not session_subtasks:
            continue

        # Calculate Jaccard similarity (intersection over union)
        intersection = len(ref_subtasks & session_subtasks)
        union = len(ref_subtasks | session_subtasks)

        if union > 0:
            similarity = intersection / union

            if similarity >= similarity_threshold:
                similar_sessions.append(
                    {
                        "session": session,
                        "similarity_score": round(similarity, 3),
                        "common_subtasks": list(ref_subtasks & session_subtasks),
                        "unique_subtasks": list(session_subtasks - ref_subtasks),
                    }
                )

    # Sort by similarity score descending
    similar_sessions.sort(key=lambda x: x["similarity_score"], reverse=True)

    return similar_sessions
