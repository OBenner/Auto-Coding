"""
Execution phase event protocol for frontend synchronization.

Protocol: __EXEC_PHASE__:{"phase":"coding","message":"Starting"}
"""

import json
import os
import sys
from enum import Enum
from typing import Any

from core.resource_tracker import get_global_tracker

PHASE_MARKER_PREFIX = "__EXEC_PHASE__:"
_DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")


class ExecutionPhase(str, Enum):
    """Maps to frontend's ExecutionPhase type for task card badges."""

    PLANNING = "planning"
    CODING = "coding"
    QA_REVIEW = "qa_review"
    QA_FIXING = "qa_fixing"
    COMPLETE = "complete"
    FAILED = "failed"


def emit_phase(
    phase: ExecutionPhase | str,
    message: str = "",
    *,
    progress: int | None = None,
    subtask: str | None = None,
    include_resources: bool = True,
) -> None:
    """
    Emit structured phase event to stdout for frontend parsing.

    Args:
        phase: Execution phase (planning, coding, etc.)
        message: Human-readable status message
        progress: Optional progress percentage (0-100)
        subtask: Optional subtask identifier
        include_resources: Whether to include resource usage metrics (default: True)
    """
    phase_value = phase.value if isinstance(phase, ExecutionPhase) else phase

    payload: dict[str, Any] = {
        "phase": phase_value,
        "message": message,
    }

    if progress is not None:
        if not (0 <= progress <= 100):
            progress = max(0, min(100, progress))
        payload["progress"] = progress

    if subtask is not None:
        payload["subtask"] = subtask

    # Include resource usage metrics
    if include_resources:
        try:
            tracker = get_global_tracker()
            metrics = tracker.get_metrics()
            if metrics:
                payload["resources"] = metrics
        except (ImportError, OSError, ValueError, AttributeError):
            pass  # Silently skip resource metrics on error

    try:
        print(f"{PHASE_MARKER_PREFIX}{json.dumps(payload, default=str)}", flush=True)
    except (OSError, UnicodeEncodeError) as e:
        if _DEBUG:
            try:
                sys.stderr.write(f"[phase_event] emit failed: {e}\n")
                sys.stderr.flush()
            except (OSError, UnicodeEncodeError):
                pass  # Truly silent on complete I/O failure
