"""
Progress Tracking Utilities
===========================

Functions for tracking and displaying progress of the autonomous coding agent.
Uses subtask-based implementation plans (implementation_plan.json).

Enhanced with colored output, icons, and better visual formatting.
"""

import json
import logging
from pathlib import Path

from core.plan_normalization import normalize_subtask_aliases
from core.timing_history import get_timing_history
from ui import (
    Icons,
    bold,
    box,
    highlight,
    icon,
    muted,
    print_phase_status,
    print_status,
    progress_bar,
    success,
    warning,
)


def count_subtasks(spec_dir: Path) -> tuple[int, int]:
    """
    Count completed and total subtasks in implementation_plan.json.

    Args:
        spec_dir: Directory containing implementation_plan.json

    Returns:
        (completed_count, total_count)
    """
    plan_file = spec_dir / "implementation_plan.json"

    if not plan_file.exists():
        return 0, 0

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        total = 0
        completed = 0

        for phase in plan.get("phases", []):
            for subtask in phase.get("subtasks", []):
                total += 1
                if subtask.get("status") == "completed":
                    completed += 1

        return completed, total
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return 0, 0


def count_subtasks_detailed(spec_dir: Path) -> dict:
    """
    Count subtasks by status.

    Returns:
        Dict with completed, in_progress, pending, failed counts
    """
    plan_file = spec_dir / "implementation_plan.json"

    result = {
        "completed": 0,
        "in_progress": 0,
        "pending": 0,
        "failed": 0,
        "total": 0,
    }

    if not plan_file.exists():
        return result

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        for phase in plan.get("phases", []):
            for subtask in phase.get("subtasks", []):
                result["total"] += 1
                status = subtask.get("status", "pending")
                if status in result:
                    result[status] += 1
                else:
                    result["pending"] += 1

        return result
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return result


def is_build_complete(spec_dir: Path) -> bool:
    """
    Check if all subtasks are completed.

    Args:
        spec_dir: Directory containing implementation_plan.json

    Returns:
        True if all subtasks complete, False otherwise
    """
    completed, total = count_subtasks(spec_dir)
    return total > 0 and completed == total


def get_progress_percentage(spec_dir: Path) -> float:
    """
    Get the progress as a percentage.

    Args:
        spec_dir: Directory containing implementation_plan.json

    Returns:
        Percentage of subtasks completed (0-100)
    """
    completed, total = count_subtasks(spec_dir)
    if total == 0:
        return 0.0
    return (completed / total) * 100


def print_session_header(
    session_num: int,
    is_planner: bool,
    subtask_id: str = None,
    subtask_desc: str = None,
    phase_name: str = None,
    attempt: int = 1,
) -> None:
    """Print a formatted header for the session."""
    session_type = "PLANNER AGENT" if is_planner else "CODING AGENT"
    session_icon = Icons.GEAR if is_planner else Icons.LIGHTNING

    content = [
        bold(f"{icon(session_icon)} SESSION {session_num}: {session_type}"),
    ]

    if subtask_id:
        content.append("")
        subtask_line = f"{icon(Icons.SUBTASK)} Subtask: {highlight(subtask_id)}"
        if subtask_desc:
            # Truncate long descriptions
            desc = subtask_desc[:50] + "..." if len(subtask_desc) > 50 else subtask_desc
            subtask_line += f" - {desc}"
        content.append(subtask_line)

    if phase_name:
        content.append(f"{icon(Icons.PHASE)} Phase: {phase_name}")

    if attempt > 1:
        content.append(warning(f"{icon(Icons.WARNING)} Attempt: {attempt}"))

    print()
    print(box(content, width=70, style="heavy"))
    print()


def print_progress_summary(spec_dir: Path, show_next: bool = True) -> None:
    """Print a summary of current progress with enhanced formatting."""
    completed, total = count_subtasks(spec_dir)

    if total > 0:
        print()
        # Progress bar
        print(f"Progress: {progress_bar(completed, total, width=40)}")

        # Status message
        if completed == total:
            print_status("BUILD COMPLETE - All subtasks completed!", "success")
        else:
            remaining = total - completed
            print_status(f"{remaining} subtasks remaining", "info")

        # Phase summary
        try:
            with open(spec_dir / "implementation_plan.json", encoding="utf-8") as f:
                plan = json.load(f)

            print("\nPhases:")
            for phase in plan.get("phases", []):
                phase_subtasks = phase.get("subtasks", [])
                phase_completed = sum(
                    1 for s in phase_subtasks if s.get("status") == "completed"
                )
                phase_total = len(phase_subtasks)
                phase_name = phase.get("name", phase.get("id", "Unknown"))

                if phase_completed == phase_total:
                    status = "complete"
                elif phase_completed > 0 or any(
                    s.get("status") == "in_progress" for s in phase_subtasks
                ):
                    status = "in_progress"
                else:
                    # Check if blocked by dependencies
                    deps = phase.get("depends_on", [])
                    all_deps_complete = True
                    for dep_id in deps:
                        for p in plan.get("phases", []):
                            if p.get("id") == dep_id or p.get("phase") == dep_id:
                                p_subtasks = p.get("subtasks", [])
                                if not all(
                                    s.get("status") == "completed" for s in p_subtasks
                                ):
                                    all_deps_complete = False
                                break
                    status = "pending" if all_deps_complete else "blocked"

                print_phase_status(phase_name, phase_completed, phase_total, status)

            # Show next subtask if requested
            if show_next and completed < total:
                next_subtask = get_next_subtask(spec_dir)
                if next_subtask:
                    print()
                    next_id = next_subtask.get("id", "unknown")
                    next_desc = next_subtask.get("description", "")
                    if len(next_desc) > 60:
                        next_desc = next_desc[:57] + "..."
                    print(
                        f"  {icon(Icons.ARROW_RIGHT)} Next: {highlight(next_id)} - {next_desc}"
                    )

            # Show recovery metrics if available
            recovery_stats = get_recovery_metrics_summary(spec_dir)
            if recovery_stats:
                print()
                print("Recovery Metrics:")
                success_rate = recovery_stats["success_rate"]
                total_attempts = recovery_stats["total_attempts"]
                successful = recovery_stats["successful_recoveries"]

                if success_rate >= 70:
                    rate_display = success(f"{success_rate:.0f}%")
                elif success_rate >= 40:
                    rate_display = warning(f"{success_rate:.0f}%")
                else:
                    rate_display = f"{success_rate:.0f}%"

                print(
                    f"  {icon(Icons.SUCCESS)} Success Rate: {rate_display} ({successful}/{total_attempts} attempts)"
                )

                if recovery_stats["circular_fixes"] > 0:
                    print(
                        f"  {icon(Icons.WARNING)} Circular Fixes: {recovery_stats['circular_fixes']}"
                    )

        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            pass  # Ignore corrupted/unreadable progress files
    else:
        print()
        print_status("No implementation subtasks yet - planner needs to run", "pending")


def print_build_complete_banner(spec_dir: Path) -> None:
    """Print a completion banner."""
    content = [
        success(f"{icon(Icons.SUCCESS)} BUILD COMPLETE!"),
        "",
        "All subtasks have been implemented successfully.",
        "",
        muted("Next steps:"),
        f"  1. Review the {highlight('auto-claude/*')} branch",
        "  2. Run manual tests",
        "  3. Create a PR and merge to main",
    ]

    print()
    print(box(content, width=70, style="heavy"))
    print()


def print_paused_banner(
    spec_dir: Path,
    spec_name: str,
    has_worktree: bool = False,
) -> None:
    """Print a paused banner with resume instructions."""
    completed, total = count_subtasks(spec_dir)

    content = [
        warning(f"{icon(Icons.PAUSE)} BUILD PAUSED"),
        "",
        f"Progress saved: {completed}/{total} subtasks complete",
    ]

    if has_worktree:
        content.append("")
        content.append(muted("Your build is in a separate workspace and is safe."))

    print()
    print(box(content, width=70, style="heavy"))


def get_plan_summary(spec_dir: Path) -> dict:
    """
    Get a detailed summary of implementation plan status.

    Args:
        spec_dir: Directory containing implementation_plan.json

    Returns:
        Dictionary with plan statistics
    """
    plan_file = spec_dir / "implementation_plan.json"

    if not plan_file.exists():
        return {
            "workflow_type": None,
            "total_phases": 0,
            "total_subtasks": 0,
            "completed_subtasks": 0,
            "pending_subtasks": 0,
            "in_progress_subtasks": 0,
            "failed_subtasks": 0,
            "phases": [],
        }

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        summary = {
            "workflow_type": plan.get("workflow_type"),
            "total_phases": len(plan.get("phases", [])),
            "total_subtasks": 0,
            "completed_subtasks": 0,
            "pending_subtasks": 0,
            "in_progress_subtasks": 0,
            "failed_subtasks": 0,
            "phases": [],
        }

        for phase in plan.get("phases", []):
            phase_info = {
                "id": phase.get("id"),
                "phase": phase.get("phase"),
                "name": phase.get("name"),
                "depends_on": phase.get("depends_on", []),
                "subtasks": [],
                "completed": 0,
                "total": 0,
            }

            for subtask in phase.get("subtasks", []):
                status = subtask.get("status", "pending")
                summary["total_subtasks"] += 1
                phase_info["total"] += 1

                if status == "completed":
                    summary["completed_subtasks"] += 1
                    phase_info["completed"] += 1
                elif status == "in_progress":
                    summary["in_progress_subtasks"] += 1
                elif status == "failed":
                    summary["failed_subtasks"] += 1
                else:
                    summary["pending_subtasks"] += 1

                phase_info["subtasks"].append(
                    {
                        "id": subtask.get("id"),
                        "description": subtask.get("description"),
                        "status": status,
                        "service": subtask.get("service"),
                    }
                )

            summary["phases"].append(phase_info)

        return summary

    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {
            "workflow_type": None,
            "total_phases": 0,
            "total_subtasks": 0,
            "completed_subtasks": 0,
            "pending_subtasks": 0,
            "in_progress_subtasks": 0,
            "failed_subtasks": 0,
            "phases": [],
        }


def get_current_phase(spec_dir: Path) -> dict | None:
    """Get the current phase being worked on."""
    plan_file = spec_dir / "implementation_plan.json"

    if not plan_file.exists():
        return None

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        for phase in plan.get("phases", []):
            subtasks = phase.get("subtasks", phase.get("chunks", []))
            # Phase is current if it has incomplete subtasks and dependencies are met
            has_incomplete = any(s.get("status") != "completed" for s in subtasks)
            if has_incomplete:
                return {
                    "id": phase.get("id"),
                    "phase": phase.get("phase"),
                    "name": phase.get("name"),
                    "completed": sum(
                        1 for s in subtasks if s.get("status") == "completed"
                    ),
                    "total": len(subtasks),
                }

        return None

    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def get_next_subtask(spec_dir: Path, restart_from: str | None = None) -> dict | None:
    """
    Find the next subtask to work on, respecting phase dependencies.

    Args:
        spec_dir: Directory containing implementation_plan.json
        restart_from: Optional subtask ID to restart from (skips completed subtasks)

    Returns:
        The next subtask dict to work on, or None if all complete
    """
    plan_file = spec_dir / "implementation_plan.json"

    if not plan_file.exists():
        return None

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        phases = plan.get("phases", [])

        # If restart_from is specified, find that specific subtask
        # and skip to the next pending subtask if it's already completed
        if restart_from:
            restart_phase_index = None
            restart_subtask_index = None
            restart_phase_id = None
            restart_phase_name = None
            restart_phase_num = None

            # Find the restart point
            for phase_idx, phase in enumerate(phases):
                phase_id_value = phase.get("id")
                phase_id = (
                    phase_id_value if phase_id_value is not None else phase.get("phase")
                )
                for subtask_idx, subtask in enumerate(
                    phase.get("subtasks", phase.get("chunks", []))
                ):
                    if subtask.get("id") == restart_from:
                        restart_phase_index = phase_idx
                        restart_subtask_index = subtask_idx
                        restart_phase_id = phase_id
                        restart_phase_name = phase.get("name")
                        restart_phase_num = phase.get("phase")
                        break
                if restart_phase_index is not None:
                    break

            # If restart point found, skip to next pending subtask
            if restart_phase_index is not None:
                # First, check if the restart subtask itself is completed
                # If so, we need to find the next pending subtask
                current_phase = phases[restart_phase_index]
                subtasks = current_phase.get(
                    "subtasks", current_phase.get("chunks", [])
                )

                # Start from the restart subtask and look for the next pending one
                for i in range(restart_subtask_index, len(subtasks)):
                    subtask = subtasks[i]
                    status = subtask.get("status", "pending")
                    if status != "completed":
                        # Found next non-completed subtask
                        subtask_out, _changed = normalize_subtask_aliases(subtask)
                        return {
                            **subtask_out,
                            "phase_id": restart_phase_id,
                            "phase_name": restart_phase_name,
                            "phase_num": restart_phase_num,
                        }

                # If all subtasks in this phase are complete, check subsequent phases
                # Build phase completion map first
                phase_complete: dict[str, bool] = {}
                for i, phase in enumerate(phases):
                    phase_id_value = phase.get("id")
                    phase_id_raw = (
                        phase_id_value
                        if phase_id_value is not None
                        else phase.get("phase")
                    )
                    phase_id_key = (
                        str(phase_id_raw)
                        if phase_id_raw is not None
                        else f"unknown:{i}"
                    )
                    subtasks_list = phase.get("subtasks", phase.get("chunks", []))
                    phase_complete[phase_id_key] = all(
                        s.get("status") == "completed" for s in subtasks_list
                    )

                # Look for next phase with pending subtasks
                for phase_idx in range(restart_phase_index + 1, len(phases)):
                    phase = phases[phase_idx]
                    phase_id_value = phase.get("id")
                    phase_id = (
                        phase_id_value
                        if phase_id_value is not None
                        else phase.get("phase")
                    )
                    depends_on_raw = phase.get("depends_on", [])
                    if isinstance(depends_on_raw, list):
                        depends_on = [str(d) for d in depends_on_raw if d is not None]
                    elif depends_on_raw is None:
                        depends_on = []
                    else:
                        depends_on = [str(depends_on_raw)]

                    # Check if dependencies are satisfied
                    deps_satisfied = all(
                        phase_complete.get(dep, False) for dep in depends_on
                    )
                    if not deps_satisfied:
                        continue

                    # Find first pending subtask in this phase
                    for subtask in phase.get("subtasks", phase.get("chunks", [])):
                        status = subtask.get("status", "pending")
                        if status != "completed":
                            subtask_out, _changed = normalize_subtask_aliases(subtask)
                            return {
                                **subtask_out,
                                "phase_id": phase_id,
                                "phase_name": phase.get("name"),
                                "phase_num": phase.get("phase"),
                            }

                # All subsequent subtasks are complete
                return None
            # If restart_from subtask not found, log warning and fall through to normal flow
            logging.getLogger(__name__).warning(
                f"restart_from subtask '{restart_from}' not found in plan, "
                "falling through to normal flow"
            )

        # Build a map of phase completion
        phase_complete: dict[str, bool] = {}
        for i, phase in enumerate(phases):
            phase_id_value = phase.get("id")
            phase_id_raw = (
                phase_id_value if phase_id_value is not None else phase.get("phase")
            )
            phase_id_key = (
                str(phase_id_raw) if phase_id_raw is not None else f"unknown:{i}"
            )
            subtasks = phase.get("subtasks", phase.get("chunks", []))
            phase_complete[phase_id_key] = all(
                s.get("status") == "completed" for s in subtasks
            )

        # Find next available subtask
        for phase in phases:
            phase_id_value = phase.get("id")
            phase_id = (
                phase_id_value if phase_id_value is not None else phase.get("phase")
            )
            depends_on_raw = phase.get("depends_on", [])
            if isinstance(depends_on_raw, list):
                depends_on = [str(d) for d in depends_on_raw if d is not None]
            elif depends_on_raw is None:
                depends_on = []
            else:
                depends_on = [str(depends_on_raw)]

            # Check if dependencies are satisfied
            deps_satisfied = all(phase_complete.get(dep, False) for dep in depends_on)
            if not deps_satisfied:
                continue

            # Find first pending subtask in this phase
            for subtask in phase.get("subtasks", phase.get("chunks", [])):
                status = subtask.get("status", "pending")
                if status in {"pending", "not_started", "not started"}:
                    subtask_out, _changed = normalize_subtask_aliases(subtask)
                    subtask_out["status"] = "pending"
                    return {
                        **subtask_out,
                        "phase_id": phase_id,
                        "phase_name": phase.get("name"),
                        "phase_num": phase.get("phase"),
                    }

        return None

    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def format_duration(seconds: float) -> str:
    """Format a duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


# Timing History Integration Functions


def record_subtask_completion(
    spec_dir: Path,
    subtask_id: str,
    started_at: float,
    completed_at: float | None = None,
    status: str = "completed",
) -> None:
    """
    Record completion of a subtask for future time estimates.

    Args:
        spec_dir: Directory containing timing_history.json
        subtask_id: Subtask identifier (e.g., "subtask-1-1")
        started_at: Unix timestamp when subtask started
        completed_at: Unix timestamp when completed (defaults to now)
        status: Completion status (default: "completed")
    """
    try:
        history = get_timing_history(spec_dir)
        history.record_completion(
            operation_type="subtask",
            operation_id=subtask_id,
            started_at=started_at,
            completed_at=completed_at,
            status=status,
        )
    except (OSError, ValueError, AttributeError):
        pass  # Silent failure - timing history is non-critical


def record_phase_completion(
    spec_dir: Path,
    phase_id: str,
    started_at: float,
    completed_at: float | None = None,
    status: str = "completed",
) -> None:
    """
    Record completion of a phase for future time estimates.

    Args:
        spec_dir: Directory containing timing_history.json
        phase_id: Phase identifier (e.g., "phase-1-backend-metrics")
        started_at: Unix timestamp when phase started
        completed_at: Unix timestamp when completed (defaults to now)
        status: Completion status (default: "completed")
    """
    try:
        history = get_timing_history(spec_dir)
        history.record_completion(
            operation_type="phase",
            operation_id=phase_id,
            started_at=started_at,
            completed_at=completed_at,
            status=status,
        )
    except (OSError, ValueError, AttributeError):
        pass  # Silent failure - timing history is non-critical


def get_estimated_completion_time(
    spec_dir: Path,
    operation_type: str = "subtask",
    operation_id: str | None = None,
) -> dict:
    """
    Get estimated completion time based on historical data.

    Args:
        spec_dir: Directory containing timing_history.json
        operation_type: Type of operation ("subtask", "phase", "agent_session")
        operation_id: Optional specific operation ID for exact matches

    Returns:
        Dict with 'estimated_seconds', 'confidence', 'sample_size', and
        'formatted' (human-readable time string)
    """
    try:
        history = get_timing_history(spec_dir)
        estimate = history.estimate_completion(operation_type, operation_id)

        # Add formatted duration
        formatted = format_duration(estimate["estimated_seconds"])
        return {
            **estimate,
            "formatted": formatted,
        }
    except (OSError, ValueError, AttributeError):
        # Return conservative default on error
        return {
            "estimated_seconds": 300.0,
            "confidence": "low",
            "sample_size": 0,
            "formatted": "5m",
        }


def get_remaining_time_estimate(spec_dir: Path) -> dict:
    """
    Estimate total remaining time for all pending subtasks.

    Args:
        spec_dir: Directory containing implementation_plan.json and timing_history.json

    Returns:
        Dict with 'total_seconds', 'formatted', 'confidence', and 'pending_count'
    """
    try:
        counts = count_subtasks_detailed(spec_dir)
        pending_count = counts["pending"] + counts["in_progress"]

        if pending_count == 0:
            return {
                "total_seconds": 0.0,
                "formatted": "0s",
                "confidence": "high",
                "pending_count": 0,
            }

        # Get average subtask duration from history
        history = get_timing_history(spec_dir)
        avg_duration = history.get_average_duration("subtask", min_samples=2)

        if avg_duration is None:
            # No historical data - use conservative estimate
            total_seconds = pending_count * 300.0  # 5 minutes per subtask
            confidence = "low"
        else:
            total_seconds = pending_count * avg_duration
            # Confidence based on sample size
            sample_size = len(history.get_records("subtask"))
            if sample_size >= 5:
                confidence = "high"
            elif sample_size >= 2:
                confidence = "medium"
            else:
                confidence = "low"

        return {
            "total_seconds": round(total_seconds, 2),
            "formatted": format_duration(total_seconds),
            "confidence": confidence,
            "pending_count": pending_count,
        }
    except (OSError, ValueError, AttributeError):
        return {
            "total_seconds": 0.0,
            "formatted": "unknown",
            "confidence": "low",
            "pending_count": 0,
        }


def get_recovery_metrics_summary(spec_dir: Path) -> dict | None:
    """
    Get recovery metrics summary for the current build.

    Args:
        spec_dir: Directory containing recovery_metrics.json

    Returns:
        Dict with recovery stats, or None if no metrics available
    """
    try:
        # Import here to avoid circular dependency
        from qa.recovery_metrics import RecoveryMetrics

        metrics = RecoveryMetrics(spec_dir)
        stats = metrics.get_stats()

        if stats["total_attempts"] == 0:
            return None

        return {
            "total_attempts": stats["total_attempts"],
            "successful_recoveries": stats["successful_recoveries"],
            "failed_recoveries": stats["failed_recoveries"],
            "circular_fixes": stats["circular_fixes"],
            "success_rate": stats["success_rate"],
            "avg_iterations": stats.get("avg_iterations", 0.0),
        }
    except (OSError, ValueError, AttributeError, ImportError):
        return None
