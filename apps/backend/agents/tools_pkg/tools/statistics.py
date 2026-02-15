"""
Spec Statistics Tools
=====================

Tools for calculating comprehensive build statistics including time tracking,
session counts, subtask completion rates, QA iterations, and phase durations.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None


def _parse_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO timestamp string to datetime object."""
    if not ts:
        return None
    try:
        # Handle both with and without timezone info
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except (ValueError, AttributeError):
        return None


def _format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def _calculate_phase_durations(
    phases: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """
    Calculate duration for each phase based on subtask timestamps.

    Args:
        phases: List of phase dicts from implementation_plan.json

    Returns:
        Dict mapping phase_id to duration stats
    """
    phase_stats = {}

    for phase in phases:
        phase_id = phase.get("id") or phase.get("phase", "unknown")
        subtasks = phase.get("subtasks", [])

        if not subtasks:
            phase_stats[phase_id] = {
                "duration_seconds": 0,
                "duration_formatted": "0s",
                "started_at": None,
                "completed_at": None,
                "status": "not_started",
            }
            continue

        # Find earliest start and latest completion across all subtasks
        start_times = []
        end_times = []
        completed_count = 0
        total_count = len(subtasks)

        for subtask in subtasks:
            status = subtask.get("status", "pending")

            # Track started times (use started_at or updated_at when status changed from pending)
            started_at = _parse_timestamp(subtask.get("started_at"))
            if started_at:
                start_times.append(started_at)
            elif status in ["in_progress", "completed", "failed"]:
                # Fallback to updated_at if no started_at
                updated_at = _parse_timestamp(subtask.get("updated_at"))
                if updated_at:
                    start_times.append(updated_at)

            # Track completion times
            if status == "completed":
                completed_count += 1
                completed_at = _parse_timestamp(subtask.get("completed_at"))
                if completed_at:
                    end_times.append(completed_at)
                else:
                    # Fallback to updated_at
                    updated_at = _parse_timestamp(subtask.get("updated_at"))
                    if updated_at:
                        end_times.append(updated_at)

        # Determine phase status
        if completed_count == total_count:
            phase_status = "completed"
        elif completed_count > 0 or any(
            s.get("status") == "in_progress" for s in subtasks
        ):
            phase_status = "in_progress"
        else:
            phase_status = "not_started"

        # Calculate duration
        phase_start = min(start_times) if start_times else None
        phase_end = max(end_times) if end_times else None

        duration_seconds = 0
        if phase_start:
            # If phase is completed, use latest completion time
            # Otherwise, use current time for in-progress phases
            end_time = phase_end if phase_end else datetime.now(timezone.utc)
            duration_seconds = (end_time - phase_start).total_seconds()

        phase_stats[phase_id] = {
            "duration_seconds": duration_seconds,
            "duration_formatted": _format_duration(duration_seconds),
            "started_at": phase_start.isoformat() if phase_start else None,
            "completed_at": phase_end.isoformat() if phase_end else None,
            "status": phase_status,
            "subtasks_completed": completed_count,
            "subtasks_total": total_count,
        }

    return phase_stats


def _calculate_completion_velocity(
    plan: dict[str, Any], phase_durations: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """
    Calculate subtask completion velocity.

    Args:
        plan: Implementation plan dict
        phase_durations: Phase duration stats

    Returns:
        Dict with velocity metrics
    """
    created_at = _parse_timestamp(plan.get("created_at"))
    if not created_at:
        return {
            "subtasks_per_hour": 0,
            "subtasks_per_day": 0,
            "average_subtask_duration": "N/A",
        }

    # Count completed subtasks
    completed = 0
    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            if subtask.get("status") == "completed":
                completed += 1

    # Calculate elapsed time
    now = datetime.now(timezone.utc)
    elapsed_seconds = (now - created_at).total_seconds()
    elapsed_hours = elapsed_seconds / 3600

    if elapsed_hours == 0:
        return {
            "subtasks_per_hour": 0,
            "subtasks_per_day": 0,
            "average_subtask_duration": "N/A",
        }

    subtasks_per_hour = completed / elapsed_hours if elapsed_hours > 0 else 0
    subtasks_per_day = subtasks_per_hour * 24

    # Calculate average subtask duration
    if completed > 0:
        avg_duration = elapsed_seconds / completed
        avg_duration_str = _format_duration(avg_duration)
    else:
        avg_duration_str = "N/A"

    return {
        "subtasks_per_hour": round(subtasks_per_hour, 2),
        "subtasks_per_day": round(subtasks_per_day, 2),
        "average_subtask_duration": avg_duration_str,
    }


def _count_unique_sessions(plan: dict[str, Any]) -> int:
    """
    Count unique session IDs across all subtasks.

    Args:
        plan: Implementation plan dict

    Returns:
        Number of unique sessions
    """
    session_ids = set()

    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            session_id = subtask.get("session_id")
            if session_id:
                session_ids.add(session_id)

    return len(session_ids)


def _calculate_quality_metrics(plan: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate quality metrics based on completion rates and QA performance.

    Args:
        plan: Implementation plan dict

    Returns:
        Dict with quality metrics
    """
    # Count subtasks by status
    total_subtasks = 0
    completed_subtasks = 0
    failed_subtasks = 0

    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            total_subtasks += 1
            status = subtask.get("status", "pending")
            if status == "completed":
                completed_subtasks += 1
            elif status == "failed":
                failed_subtasks += 1

    # Calculate completion rate (0.0 to 1.0)
    completion_rate = completed_subtasks / total_subtasks if total_subtasks > 0 else 0.0

    # QA metrics
    qa_signoff = plan.get("qa_signoff", {})
    raw_iterations = qa_signoff.get("qa_iterations", qa_signoff.get("qa_session", 0))
    try:
        qa_iterations = int(raw_iterations)
    except (TypeError, ValueError):
        qa_iterations = 0
    qa_status = qa_signoff.get("status", "pending")

    # Determine if spec is completed (aligned with productivity_analytics.py)
    status = plan.get("status", "")
    is_completed = status == "completed" or (
        total_subtasks > 0
        and completed_subtasks == total_subtasks
        and qa_status == "approved"
    )

    # Calculate first-attempt success (QA approved on first iteration)
    first_attempt_success = (
        is_completed and qa_status == "approved" and qa_iterations == 1
    )

    # Calculate quality score (0-100)
    # Based on:
    # - Completion rate (40%)
    # - QA success (40%)
    # - Low failure rate (20%)
    quality_score = 0.0

    # Completion component (0-40 points)
    quality_score += completion_rate * 40

    # QA component (0-40 points)
    if qa_status == "approved":
        qa_component = 40.0
        # Reduce points for multiple QA iterations
        if qa_iterations > 1:
            qa_component -= min((qa_iterations - 1) * 5, 20)
        quality_score += max(qa_component, 20)  # Minimum 20 points if approved
    elif qa_status == "in_progress":
        quality_score += 10

    # Failure rate component (0-20 points)
    if total_subtasks > 0:
        failure_rate = failed_subtasks / total_subtasks
        failure_component = (1 - failure_rate) * 20
        quality_score += failure_component

    return {
        "completion_rate": round(completion_rate, 3),
        "is_completed": is_completed,
        "first_attempt_success": first_attempt_success,
        "quality_score": round(quality_score, 1),
        "qa_iterations": qa_iterations,
        "qa_status": qa_status,
        "total_subtasks": total_subtasks,
        "completed_subtasks": completed_subtasks,
        "failed_subtasks": failed_subtasks,
        "failure_rate": round(
            failed_subtasks / total_subtasks if total_subtasks > 0 else 0.0, 3
        ),
    }


def _get_quality_assessment(quality_score: float) -> str:
    """
    Get qualitative assessment based on quality score.

    Args:
        quality_score: Quality score (0-100)

    Returns:
        Assessment string
    """
    if quality_score >= 90:
        return "Excellent - High quality build with minimal issues"
    elif quality_score >= 75:
        return "Good - Solid build with acceptable QA performance"
    elif quality_score >= 60:
        return "Fair - Build completed but with some quality concerns"
    elif quality_score >= 40:
        return "Poor - Significant quality issues or incomplete build"
    else:
        return "Critical - Major quality problems or build failure"


def create_statistics_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create spec statistics tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of statistics tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []

    # -------------------------------------------------------------------------
    # Tool: get_spec_statistics
    # -------------------------------------------------------------------------
    @tool(
        "get_spec_statistics",
        "Get comprehensive build statistics including time tracking, completion velocity, session counts, QA iterations, and phase durations.",
        {},
    )
    async def get_spec_statistics(args: dict[str, Any]) -> dict[str, Any]:
        """Get comprehensive spec statistics."""
        plan_file = spec_dir / "implementation_plan.json"

        if not plan_file.exists():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "No implementation plan found. Run the planner first.",
                    }
                ]
            }

        try:
            plan = json.loads(plan_file.read_text(encoding="utf-8"))

            # Calculate basic stats
            total_subtasks = 0
            completed_subtasks = 0
            failed_subtasks = 0
            in_progress_subtasks = 0

            for phase in plan.get("phases", []):
                for subtask in phase.get("subtasks", []):
                    total_subtasks += 1
                    status = subtask.get("status", "pending")
                    if status == "completed":
                        completed_subtasks += 1
                    elif status == "failed":
                        failed_subtasks += 1
                    elif status == "in_progress":
                        in_progress_subtasks += 1

            # Calculate time metrics
            created_at = _parse_timestamp(plan.get("created_at"))
            last_updated = _parse_timestamp(plan.get("last_updated"))
            now = datetime.now(timezone.utc)

            if created_at:
                # Total build time (from start to now)
                build_duration_seconds = (now - created_at).total_seconds()
                build_duration = _format_duration(build_duration_seconds)

                # Time since last update
                if last_updated:
                    idle_seconds = (now - last_updated).total_seconds()
                    idle_duration = _format_duration(idle_seconds)
                else:
                    idle_duration = "N/A"
            else:
                build_duration = "N/A"
                idle_duration = "N/A"

            # Phase durations
            phase_durations = _calculate_phase_durations(plan.get("phases", []))

            # Completion velocity
            velocity = _calculate_completion_velocity(plan, phase_durations)

            # Session count
            session_count = _count_unique_sessions(plan)

            # QA iterations
            qa_signoff = plan.get("qa_signoff", {})
            raw_iter = qa_signoff.get("qa_iterations", qa_signoff.get("qa_session", 0))
            try:
                qa_iterations = int(raw_iter)
            except (TypeError, ValueError):
                qa_iterations = 0
            qa_status = qa_signoff.get("status", "pending")

            # Completion rate
            completion_rate = (
                (completed_subtasks / total_subtasks * 100) if total_subtasks > 0 else 0
            )

            # Build output
            result = f"""Spec Statistics
================

Time Tracking:
  Total Build Time: {build_duration}
  Time Since Last Update: {idle_duration}
  Started: {created_at.strftime("%Y-%m-%d %H:%M UTC") if created_at else "N/A"}
  Last Updated: {last_updated.strftime("%Y-%m-%d %H:%M UTC") if last_updated else "N/A"}

Subtask Progress:
  Completion Rate: {completion_rate:.1f}% ({completed_subtasks}/{total_subtasks})
  In Progress: {in_progress_subtasks}
  Failed: {failed_subtasks}

Completion Velocity:
  Subtasks/Hour: {velocity["subtasks_per_hour"]}
  Subtasks/Day: {velocity["subtasks_per_day"]}
  Avg Subtask Duration: {velocity["average_subtask_duration"]}

QA Metrics:
  QA Iterations: {qa_iterations}
  QA Status: {qa_status}
  Session Count: {session_count}

Phase Durations:"""

            for phase_id, stats in phase_durations.items():
                phase_name = phase_id
                # Try to get readable phase name
                for phase in plan.get("phases", []):
                    if phase.get("id") == phase_id or phase.get("phase") == phase_id:
                        phase_name = phase.get("name", phase_id)
                        break

                result += f"""
  {phase_name}:
    Duration: {stats["duration_formatted"]}
    Status: {stats["status"]}
    Progress: {stats["subtasks_completed"]}/{stats["subtasks_total"]} subtasks"""

            return {"content": [{"type": "text", "text": result}]}

        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error calculating statistics: {e}"}
                ]
            }

    tools.append(get_spec_statistics)

    # -------------------------------------------------------------------------
    # Tool: get_quality_metrics
    # -------------------------------------------------------------------------
    @tool(
        "get_quality_metrics",
        "Get quality metrics including completion rates, QA success, quality score, and failure rates.",
        {},
    )
    async def get_quality_metrics(args: dict[str, Any]) -> dict[str, Any]:
        """Get quality metrics for the spec."""
        plan_file = spec_dir / "implementation_plan.json"

        if not plan_file.exists():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "No implementation plan found. Run the planner first.",
                    }
                ]
            }

        try:
            plan = json.loads(plan_file.read_text(encoding="utf-8"))

            # Calculate quality metrics
            quality = _calculate_quality_metrics(plan)

            # Build output
            result = f"""Quality Metrics
===============

Completion:
  Completion Rate: {quality["completion_rate"]:.1%} ({quality["completed_subtasks"]}/{quality["total_subtasks"]} subtasks)
  Spec Completed: {"Yes" if quality["is_completed"] else "No"}
  Failed Subtasks: {quality["failed_subtasks"]}
  Failure Rate: {quality["failure_rate"]:.1%}

QA Performance:
  QA Status: {quality["qa_status"]}
  QA Iterations: {quality["qa_iterations"]}
  First-Attempt Success: {"Yes" if quality["first_attempt_success"] else "No"}

Overall Quality Score: {quality["quality_score"]}/100

Quality Score Breakdown:
  - Completion Rate (40%): {quality["completion_rate"] * 40:.1f}/40
  - QA Success (40%): Based on QA status and iterations
  - Low Failure Rate (20%): {(1 - quality["failure_rate"]) * 20:.1f}/20

Quality Assessment:
  {_get_quality_assessment(quality["quality_score"])}
"""

            return {"content": [{"type": "text", "text": result}]}

        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error calculating quality metrics: {e}"}
                ]
            }

    tools.append(get_quality_metrics)

    return tools
