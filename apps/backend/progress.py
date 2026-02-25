"""
Progress tracking module facade.

Provides progress tracking utilities for build execution.
Re-exports from core.progress for clean imports.
"""

from core.progress import (
    count_subtasks,
    count_subtasks_detailed,
    format_duration,
    get_current_phase,
    get_next_subtask,
    get_plan_summary,
    get_progress_percentage,
    get_recovery_metrics_summary,
    is_build_complete,
    is_build_ready_for_qa,
    print_build_complete_banner,
    print_paused_banner,
    print_progress_summary,
    print_session_header,
    reset_subtask_to_pending,
)


def get_recovery_metrics():
    """
    Lazy import of RecoveryMetrics to avoid circular dependencies.

    Returns:
        RecoveryMetrics class
    """
    from qa.recovery_metrics import RecoveryMetrics

    return RecoveryMetrics


__all__ = [
    "count_subtasks",
    "count_subtasks_detailed",
    "format_duration",
    "get_current_phase",
    "get_next_subtask",
    "get_plan_summary",
    "get_progress_percentage",
    "get_recovery_metrics_summary",
    "get_recovery_metrics",
    "is_build_complete",
    "is_build_ready_for_qa",
    "print_build_complete_banner",
    "print_paused_banner",
    "print_progress_summary",
    "print_session_header",
    "reset_subtask_to_pending",
]

# Make RecoveryMetrics available for imports (lazy loaded)
# Usage: from progress import get_recovery_metrics
# RecoveryMetrics = get_recovery_metrics()
RecoveryMetrics = None  # Lazy-loaded via get_recovery_metrics()
