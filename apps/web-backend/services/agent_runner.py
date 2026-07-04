"""
Agent Runner Service

Service layer for executing Auto Code agents (planner, coder, qa_reviewer, qa_fixer).
This service wraps the backend agent execution logic and provides async task management.
Integrates with WebSocket event broadcasting for real-time progress updates.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# WebSocket broadcast functions (imported lazily to avoid circular imports)
_broadcast_execution_event = None
_broadcast_log_event = None
_broadcast_error_event = None


def _init_websocket_broadcast():
    """
    Initialize WebSocket broadcast functions from the websocket module.

    This function is called lazily to avoid circular import issues and
    to ensure WebSocket broadcasting is only initialized when needed.
    """
    global _broadcast_execution_event, _broadcast_log_event, _broadcast_error_event

    if _broadcast_execution_event is not None:
        return  # Already initialized

    try:
        from api.websocket import (
            broadcast_error_event,
            broadcast_execution_event,
            broadcast_log_event,
        )

        _broadcast_execution_event = broadcast_execution_event
        _broadcast_log_event = broadcast_log_event
        _broadcast_error_event = broadcast_error_event
        logger.debug("WebSocket broadcast functions initialized")
    except ImportError as e:
        logger.warning(f"WebSocket broadcast functions not available: {e}")
        _broadcast_execution_event = _noop_broadcast
        _broadcast_log_event = _noop_broadcast
        _broadcast_error_event = _noop_broadcast


async def _noop_broadcast(*args, **kwargs):
    """No-op broadcast function when WebSocket module is unavailable."""


from core import sanitize_log as _sanitize_log

from services.execution_log import record_execution_result

# Shared failure message (broadcast, run record, and API result must agree).
_PLANNER_FAILED = "Planner execution failed"

# Keep track of running agent tasks
_running_tasks: dict[str, asyncio.Task] = {}


def _get_backend_path() -> Path:
    """
    Get the path to the Auto Code backend.

    Returns:
        Path to the backend directory
    """
    web_backend_dir = Path(__file__).parent.parent
    backend_dir = web_backend_dir.parent / "backend"

    if not backend_dir.exists():
        raise FileNotFoundError(
            f"Backend directory not found: {backend_dir}. "
            "Ensure Auto Code backend is installed."
        )

    return backend_dir


def _ensure_backend_in_path():
    """Ensure backend directory is in sys.path for imports"""
    backend_path = str(_get_backend_path())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


async def run_agent_async(
    spec_id: str,
    agent_type: str,
    project_dir: Path | None = None,
    model: str = "claude-sonnet-4-5-20250929",
    verbose: bool = False,
    execution_id: int | None = None,
) -> dict[str, Any]:
    """
    Run an agent asynchronously.

    Args:
        spec_id: Spec ID (e.g., "001" or "001-feature-name")
        agent_type: Type of agent ("planner", "coder", "qa_reviewer", "qa_fixer")
        project_dir: Project directory (defaults to parent of web-backend)
        model: Claude model to use
        verbose: Enable verbose output
        execution_id: Optional AgentExecution record id; when set, the run's
            terminal status is persisted to it (best-effort, own DB session)

    Returns:
        Dict with execution result

    Raises:
        ValueError: If agent_type is invalid
        FileNotFoundError: If spec not found
    """
    # Initialize WebSocket broadcast functions
    _init_websocket_broadcast()

    # Ensure backend is importable
    _ensure_backend_in_path()

    # Lazy imports from backend
    from agents import run_autonomous_agent, run_followup_planner

    # Validate agent type
    valid_agents = ["planner", "coder", "qa_reviewer", "qa_fixer"]
    if agent_type not in valid_agents:
        raise ValueError(
            f"Invalid agent_type: {agent_type}. Must be one of: {valid_agents}"
        )

    # Determine project directory
    if project_dir is None:
        project_dir = Path(__file__).parent.parent.parent.parent

    # Find spec directory
    specs_dir = project_dir / ".auto-claude" / "specs"

    if not specs_dir.exists():
        raise FileNotFoundError(f"Specs directory not found: {specs_dir}")

    # Find matching spec directory
    spec_dir = None
    for candidate in specs_dir.iterdir():
        if candidate.is_dir():
            folder_name = candidate.name
            if folder_name.startswith(f"{spec_id}-") or folder_name == spec_id:
                spec_dir = candidate
                break

    if spec_dir is None:
        raise FileNotFoundError(f"Spec not found: {spec_id}")

    # Use spec_dir.name as the canonical spec_id for broadcasting
    canonical_spec_id = spec_dir.name

    logger.info(
        f"Starting agent execution: type={_sanitize_log(agent_type)}, spec={_sanitize_log(canonical_spec_id)}, "
        f"model={_sanitize_log(model)}"
    )

    # Broadcast agent start event
    phase_map = {
        "planner": "planning",
        "coder": "coding",
        "qa_reviewer": "qa_review",
        "qa_fixer": "qa_fixing",
    }
    if _broadcast_execution_event is not None:
        await _broadcast_execution_event(
            spec_id=canonical_spec_id,
            phase=phase_map.get(agent_type, "idle"),
            phase_progress=0.0,
            overall_progress=0.0,
            message=f"Starting {agent_type} agent",
            current_subtask=None,
        )

    try:
        if agent_type == "planner":
            if _broadcast_log_event:
                await _broadcast_log_event(
                    spec_id=canonical_spec_id,
                    log_line=f"Running planner agent with model {model}",
                    level="info",
                )

            success = await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model=model,
                verbose=verbose,
            )

            if success:
                if _broadcast_execution_event:
                    await _broadcast_execution_event(
                        spec_id=canonical_spec_id,
                        phase="complete",
                        phase_progress=100.0,
                        overall_progress=100.0,
                        message="Planner execution completed successfully",
                        current_subtask=None,
                    )
            else:
                if _broadcast_execution_event:
                    await _broadcast_execution_event(
                        spec_id=canonical_spec_id,
                        phase="failed",
                        phase_progress=0.0,
                        overall_progress=0.0,
                        message=_PLANNER_FAILED,
                        current_subtask=None,
                    )

            # Offload the blocking DB write so it doesn't stall the event loop.
            await asyncio.to_thread(
                record_execution_result,
                execution_id,
                "completed" if success else "failed",
                None if success else _PLANNER_FAILED,
            )
            return {
                "success": success,
                "agent_type": agent_type,
                "spec_id": canonical_spec_id,
                "message": "Planner execution completed"
                if success
                else _PLANNER_FAILED,
            }

        elif agent_type in ["coder", "qa_reviewer", "qa_fixer"]:
            if _broadcast_log_event:
                await _broadcast_log_event(
                    spec_id=canonical_spec_id,
                    log_line=f"Running {agent_type} agent with model {model}",
                    level="info",
                )

            await run_autonomous_agent(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model=model,
                max_iterations=None,
                verbose=verbose,
                source_spec_dir=None,
            )

            if _broadcast_execution_event:
                await _broadcast_execution_event(
                    spec_id=canonical_spec_id,
                    phase="complete",
                    phase_progress=100.0,
                    overall_progress=100.0,
                    message=f"{agent_type} execution completed successfully",
                    current_subtask=None,
                )

            await asyncio.to_thread(record_execution_result, execution_id, "completed")
            return {
                "success": True,
                "agent_type": agent_type,
                "spec_id": canonical_spec_id,
                "message": f"{agent_type} execution completed",
            }

        else:
            raise ValueError(f"Unsupported agent type: {agent_type}")

    except asyncio.CancelledError:
        # Task cancelled via cancel_task(): persist the terminal state, then
        # re-raise so asyncio cancellation semantics are preserved. Kept
        # synchronous on purpose — awaiting here could be interrupted by a
        # second cancellation and lose the write; the brief block is acceptable.
        record_execution_result(execution_id, "cancelled")
        raise
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)

        # Use canonical_spec_id (always defined) instead of spec_dir.name
        # to avoid UnboundLocalError if spec_dir lookup failed
        error_spec_id = canonical_spec_id if "canonical_spec_id" in dir() else spec_id

        if _broadcast_error_event is not None:
            await _broadcast_error_event(
                spec_id=error_spec_id,
                error_message=str(e),
                error_type=type(e).__name__,
                traceback=None,
            )

        await asyncio.to_thread(record_execution_result, execution_id, "failed", str(e))
        return {
            "success": False,
            "agent_type": agent_type,
            "spec_id": error_spec_id,
            "error": str(e),
            "message": f"Agent execution failed: {e}",
        }


def start_agent_task(
    spec_id: str,
    agent_type: str,
    project_dir: Path | None = None,
    model: str = "claude-sonnet-4-5-20250929",
    verbose: bool = False,
    execution_id: int | None = None,
) -> str:
    """
    Start an agent task in the background.

    Args:
        spec_id: Spec ID
        agent_type: Type of agent
        project_dir: Project directory
        model: Claude model to use
        verbose: Enable verbose output
        execution_id: Optional AgentExecution record id to finish when the run ends

    Returns:
        Task ID for tracking

    Raises:
        RuntimeError: If task already running for this spec
    """
    _init_websocket_broadcast()

    task_id = f"{spec_id}:{agent_type}"

    if task_id in _running_tasks and not _running_tasks[task_id].done():
        raise RuntimeError(
            f"Agent task already running for spec {spec_id} (type: {agent_type})"
        )

    task = asyncio.create_task(
        run_agent_async(
            spec_id=spec_id,
            agent_type=agent_type,
            project_dir=project_dir,
            model=model,
            verbose=verbose,
            execution_id=execution_id,
        )
    )

    _running_tasks[task_id] = task

    logger.info(f"Started agent task: {_sanitize_log(task_id)}")

    return task_id


def get_task_status(task_id: str) -> dict[str, Any] | None:
    """
    Get the status of a running task.

    Args:
        task_id: Task ID returned by start_agent_task

    Returns:
        Dict with task status, or None if not found
    """
    if task_id not in _running_tasks:
        return None

    task = _running_tasks[task_id]

    if task.done():
        try:
            result = task.result()
            return {
                "status": "completed",
                "result": result,
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
            }
    else:
        return {
            "status": "running",
        }


def cancel_task(task_id: str) -> bool:
    """
    Cancel a running task.

    Args:
        task_id: Task ID

    Returns:
        True if task was cancelled, False if not found or already done
    """
    if task_id not in _running_tasks:
        return False

    task = _running_tasks[task_id]

    if task.done():
        return False

    task.cancel()
    logger.info(f"Cancelled agent task: {_sanitize_log(task_id)}")

    return True


def cleanup_completed_tasks():
    """Remove completed tasks from tracking"""
    completed = [task_id for task_id, task in _running_tasks.items() if task.done()]

    for task_id in completed:
        del _running_tasks[task_id]

    if completed:
        logger.debug(f"Cleaned up {len(completed)} completed tasks")
