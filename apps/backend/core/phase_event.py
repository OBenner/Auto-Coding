"""
Execution phase event protocol for frontend synchronization.

Protocol: __EXEC_PHASE__:{"phase":"coding","message":"Starting"}

This module also integrates with the webhook system to dispatch events
for key lifecycle transitions (build start, completion, QA results).
"""

import json
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Any

from core.resource_tracker import get_global_tracker

PHASE_MARKER_PREFIX = "__EXEC_PHASE__:"
_DEBUG = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")
_WEBHOOKS_ENABLED = os.environ.get("WEBHOOKS_ENABLED", "").lower() in (
    "1",
    "true",
    "yes",
)

# Lazy import webhook dispatcher to avoid import errors if not available
_webhook_dispatcher = None
_webhook_spec_dir: Path | None = None
_webhook_project_dir: Path | None = None
_last_phase: str | None = None


def _get_webhook_dispatcher():
    """Lazy import and caching of webhook dispatcher."""
    global _webhook_dispatcher, _webhook_spec_dir, _webhook_project_dir

    if not _WEBHOOKS_ENABLED:
        return None

    if _webhook_dispatcher is not None:
        return _webhook_dispatcher

    try:
        from integrations.webhooks.dispatcher import get_dispatcher

        if _webhook_spec_dir:
            _webhook_dispatcher = get_dispatcher(
                _webhook_spec_dir,
                _webhook_project_dir,
            )
            return _webhook_dispatcher
    except (ImportError, OSError):
        pass  # Webhook system not available

    return None


def init_webhooks(spec_dir: Path, project_dir: Path | None = None) -> None:
    """
    Initialize webhook integration for phase events.

    Call this once at the start of a build to enable webhook dispatching
    when phase events are emitted.

    Args:
        spec_dir: Spec directory containing webhook configuration
        project_dir: Optional project directory for additional context
    """
    global _webhook_spec_dir, _webhook_project_dir, _webhook_dispatcher

    if not _WEBHOOKS_ENABLED:
        return

    _webhook_spec_dir = spec_dir
    _webhook_project_dir = project_dir

    # Pre-initialize dispatcher to validate configuration
    _get_webhook_dispatcher()


class ExecutionPhase(str, Enum):
    """Maps to frontend's ExecutionPhase type for task card badges."""

    PLANNING = "planning"
    CODING = "coding"
    TEST_GENERATION = "test_generation"
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

    Also dispatches webhook events for key lifecycle transitions:
    - Planning → Coding: dispatches "build_started" event
    - Any → Complete: dispatches "build_completed" event
    - Any → Failed: dispatches "build_failed" event
    - QA Review → Complete: dispatches "qa_passed" event
    - QA Fixing → Failed: dispatches "qa_failed" event

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

    # Dispatch webhook events for key lifecycle transitions
    _dispatch_webhook_for_phase_transition(phase_value, message)


def _determine_webhook_event(
    phase: str,
    previous_phase: str | None,
    message: str,
) -> tuple[str | None, dict[str, Any]]:
    """
    Determine which webhook event to dispatch based on phase transition.

    Args:
        phase: Current execution phase
        previous_phase: Previous execution phase
        message: Phase message for webhook payload

    Returns:
        Tuple of (webhook_event name or None, webhook_data dict)
    """
    webhook_data: dict[str, Any] = {
        "phase": phase,
        "message": message,
    }

    # Build started: Planning -> Coding (first time)
    if phase == ExecutionPhase.CODING and previous_phase in (
        None,
        ExecutionPhase.PLANNING,
    ):
        webhook_data["build_started_at"] = message
        return "build_started", webhook_data

    # Build completed: Any phase -> Complete
    if phase == ExecutionPhase.COMPLETE:
        webhook_data["success"] = True
        if previous_phase == ExecutionPhase.QA_REVIEW:
            _dispatch_qa_event(passed=True, message=message)
        return "build_completed", webhook_data

    # Build failed: Any phase -> Failed
    if phase == ExecutionPhase.FAILED:
        webhook_data["success"] = False
        if previous_phase == ExecutionPhase.QA_FIXING:
            _dispatch_qa_event(passed=False, message=message)
        return "build_failed", webhook_data

    return None, webhook_data


def _enrich_and_send(
    dispatcher: Any,
    webhook_event: str,
    webhook_data: dict[str, Any],
    phase: str,
) -> None:
    """
    Enrich webhook data with spec/project info and dispatch.

    Args:
        dispatcher: Webhook dispatcher instance
        webhook_event: Event name to dispatch
        webhook_data: Event data dict
        phase: Current execution phase (for debug logging)
    """
    if _webhook_spec_dir:
        webhook_data["spec_id"] = _webhook_spec_dir.name
    if _webhook_project_dir:
        webhook_data["project_dir"] = str(_webhook_project_dir)

    dispatcher.dispatch_event(webhook_event, webhook_data, blocking=False)

    _debug_log(f"dispatched {webhook_event} for phase {phase}")


def _debug_log(message: str) -> None:
    """Write a debug message to stderr if debug mode is enabled."""
    if not _DEBUG:
        return
    try:
        sys.stderr.write(f"[phase_event] {message}\n")
        sys.stderr.flush()
    except (OSError, UnicodeEncodeError):
        # Intentionally ignored: debug logging is best-effort;
        # stderr may be unavailable or broken in some environments.
        pass


def _dispatch_webhook_for_phase_transition(
    phase: str,
    message: str,
) -> None:
    """
    Dispatch webhook events for key lifecycle phase transitions.

    Tracks phase transitions and dispatches appropriate webhook events:
    - Planning -> Coding: "build_started"
    - Any -> Complete: "build_completed"
    - Any -> Failed: "build_failed"
    - QA Review -> Complete: "qa_passed"
    - QA Fixing -> Failed: "qa_failed"

    Args:
        phase: Current execution phase
        message: Phase message for webhook payload
    """
    global _last_phase

    dispatcher = _get_webhook_dispatcher()
    if not dispatcher:
        return

    previous_phase = _last_phase
    _last_phase = phase

    webhook_event, webhook_data = _determine_webhook_event(
        phase, previous_phase, message
    )

    if not webhook_event:
        return

    try:
        _enrich_and_send(dispatcher, webhook_event, webhook_data, phase)
    except (OSError, ValueError, RuntimeError) as e:
        _debug_log(f"webhook dispatch failed: {e}")


def _dispatch_qa_event(passed: bool, message: str) -> None:
    """
    Dispatch QA-specific webhook event.

    Args:
        passed: Whether QA passed
        message: QA result message
    """
    dispatcher = _get_webhook_dispatcher()
    if not dispatcher:
        return

    try:
        webhook_event = "qa_passed" if passed else "qa_failed"
        webhook_data: dict[str, Any] = {
            "passed": passed,
            "message": message,
        }

        if _webhook_spec_dir:
            webhook_data["spec_id"] = _webhook_spec_dir.name
        if _webhook_project_dir:
            webhook_data["project_dir"] = str(_webhook_project_dir)

        dispatcher.dispatch_event(webhook_event, webhook_data, blocking=False)
        _debug_log(f"dispatched {webhook_event} (passed={passed})")
    except (OSError, ValueError, RuntimeError):
        pass  # Silently fail on webhook dispatch errors
