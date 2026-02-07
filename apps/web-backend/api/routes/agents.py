"""
Agent Execution API routes

Provides endpoints for starting and managing agent execution.
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Literal, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from core.config import settings
from services.agent_runner import (
    cancel_task,
    cleanup_completed_tasks,
    get_task_status,
    start_agent_task,
)

logger = logging.getLogger(__name__)

# Track active pair programming sessions
_pair_sessions: Dict[str, asyncio.Task] = {}
_pair_session_agents: Dict[str, any] = {}

# Create router for agent endpoints
router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentRunRequest(BaseModel):
    """Request to run an agent"""

    spec_id: str = Field(..., description="Spec ID (e.g., '001' or '001-feature-name')")
    agent_type: Literal["planner", "coder", "qa_reviewer", "qa_fixer"] = Field(
        ..., description="Type of agent to run"
    )
    model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude model to use"
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output"
    )


class AgentRunResponse(BaseModel):
    """Response from starting an agent"""

    task_id: str = Field(..., description="Task ID for tracking execution")
    spec_id: str = Field(..., description="Spec ID")
    agent_type: str = Field(..., description="Agent type")
    status: Literal["started", "error"] = Field(..., description="Initial status")
    message: str = Field(..., description="Human-readable message")


class AgentStatusResponse(BaseModel):
    """Response with agent task status"""

    task_id: str = Field(..., description="Task ID")
    status: Literal["running", "completed", "failed", "not_found"] = Field(
        ..., description="Current task status"
    )
    result: Optional[dict] = Field(None, description="Task result (if completed)")
    error: Optional[str] = Field(None, description="Error message (if failed)")


class AgentCancelResponse(BaseModel):
    """Response from cancelling an agent"""

    task_id: str = Field(..., description="Task ID")
    cancelled: bool = Field(..., description="Whether task was cancelled")
    message: str = Field(..., description="Human-readable message")


# Pair Programming Models

class PairStartRequest(BaseModel):
    """Request to start a pair programming session"""

    spec_id: Optional[str] = Field(None, description="Optional spec ID for context")
    initial_message: Optional[str] = Field(None, description="Initial message or task")
    model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude model to use"
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output"
    )


class PairStartResponse(BaseModel):
    """Response from starting a pair programming session"""

    session_id: str = Field(..., description="Session ID for tracking")
    spec_id: Optional[str] = Field(None, description="Spec ID (if provided)")
    status: Literal["started", "error"] = Field(..., description="Initial status")
    message: str = Field(..., description="Human-readable message")


class PairStatusResponse(BaseModel):
    """Response with pair programming session status"""

    session_id: str = Field(..., description="Session ID")
    status: Literal["active", "idle", "paused", "stopped", "error"] = Field(
        ..., description="Current session status"
    )
    mode: Optional[str] = Field(None, description="Current mode (pair or autonomous)")
    session_num: Optional[int] = Field(None, description="Session number")
    error: Optional[str] = Field(None, description="Error message (if error)")


class PairStopResponse(BaseModel):
    """Response from stopping a pair programming session"""

    session_id: str = Field(..., description="Session ID")
    stopped: bool = Field(..., description="Whether session was stopped")
    message: str = Field(..., description="Human-readable message")


def _get_project_dir() -> Path:
    """Get the project directory from settings."""
    # Use configured project directory or fall back to parent of backend
    if hasattr(settings, "PROJECT_DIR") and settings.PROJECT_DIR:
        return Path(settings.PROJECT_DIR)

    # Default: parent of web-backend directory (../../ from api/routes/)
    return Path(__file__).parent.parent.parent.parent.parent


def _ensure_backend_in_path():
    """Ensure backend directory is at the front of sys.path for imports"""
    backend_dir = Path(__file__).parent.parent.parent.parent / "backend"
    backend_path = str(backend_dir)
    # Remove if present to avoid duplicates
    if backend_path in sys.path:
        sys.path.remove(backend_path)
    # Always insert at front to ensure backend.core takes precedence
    sys.path.insert(0, backend_path)


async def _run_pair_session_task(
    session_id: str,
    spec_id: Optional[str],
    initial_message: Optional[str],
    project_dir: Path,
    model: str,
    verbose: bool,
):
    """
    Background task to run a pair programming session.

    Args:
        session_id: Unique session identifier
        spec_id: Optional spec ID for context
        initial_message: Optional initial message
        project_dir: Project directory
        model: Claude model to use
        verbose: Enable verbose output
    """
    try:
        # Ensure backend is importable
        _ensure_backend_in_path()

        # Import pair programming agent
        from agents.pair_programming import PairProgrammingAgent

        # Determine spec directory
        spec_dir = None
        if spec_id:
            specs_dir = project_dir / ".auto-claude" / "specs"
            if specs_dir.exists():
                for candidate in specs_dir.iterdir():
                    if candidate.is_dir():
                        folder_name = candidate.name
                        if folder_name.startswith(f"{spec_id}-") or folder_name == spec_id:
                            spec_dir = candidate
                            break

        logger.info(f"Starting pair programming session: {session_id}")

        # Create agent
        agent = PairProgrammingAgent(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            verbose=verbose,
        )

        # Store agent reference
        _pair_session_agents[session_id] = agent

        # Start session
        result = await agent.start_session(initial_message=initial_message)

        logger.info(f"Pair programming session completed: {session_id}, result={result}")

    except Exception as e:
        logger.error(f"Error in pair programming session {session_id}: {e}", exc_info=True)
        # Store error in agent dict for status retrieval
        if session_id in _pair_session_agents:
            _pair_session_agents[session_id] = {"error": str(e)}
    finally:
        # Clean up task reference
        if session_id in _pair_sessions:
            del _pair_sessions[session_id]


@router.post("/run", response_model=AgentRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_agent(request: AgentRunRequest):
    """
    Start an agent execution task.

    This endpoint starts an agent task in the background and returns immediately.
    Use the returned task_id to check status via GET /api/agents/status/{task_id}.

    The agent will run asynchronously and emit progress events via WebSocket.

    Args:
        request: Agent run request with spec_id, agent_type, model, and verbose

    Returns:
        AgentRunResponse with task_id for tracking

    Raises:
        HTTPException: 400 if spec not found or task already running, 500 for other errors

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/agents/run \\
             -H "Content-Type: application/json" \\
             -d '{"spec_id": "001", "agent_type": "planner"}'
        # Returns: {"task_id": "001:planner", "status": "started", ...}
        ```
    """
    try:
        logger.info(
            f"Agent run request: spec_id={request.spec_id}, "
            f"agent_type={request.agent_type}, model={request.model}"
        )

        # Start the agent task
        project_dir = _get_project_dir()

        task_id = start_agent_task(
            spec_id=request.spec_id,
            agent_type=request.agent_type,
            project_dir=project_dir,
            model=request.model,
            verbose=request.verbose,
        )

        # Clean up completed tasks
        cleanup_completed_tasks()

        return AgentRunResponse(
            task_id=task_id,
            spec_id=request.spec_id,
            agent_type=request.agent_type,
            status="started",
            message=f"Agent task started: {request.agent_type} for spec {request.spec_id}"
        )

    except FileNotFoundError as e:
        logger.warning(f"Spec not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.warning(f"Task already running: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error starting agent: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start agent: {str(e)}",
        )


@router.get("/status/{task_id}", response_model=AgentStatusResponse, status_code=status.HTTP_200_OK)
async def get_agent_status(task_id: str):
    """
    Get the status of a running agent task.

    Args:
        task_id: Task ID returned by POST /api/agents/run

    Returns:
        AgentStatusResponse with current status and result (if completed)

    Raises:
        HTTPException: 404 if task not found

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/agents/status/001:planner \\
             -H "Content-Type: application/json"
        # Returns: {"task_id": "001:planner", "status": "running", ...}
        ```
    """
    try:
        task_status = get_task_status(task_id)

        if task_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found: {task_id}",
            )

        return AgentStatusResponse(
            task_id=task_id,
            status=task_status["status"],
            result=task_status.get("result"),
            error=task_status.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        )


@router.post("/cancel/{task_id}", response_model=AgentCancelResponse, status_code=status.HTTP_200_OK)
async def cancel_agent(task_id: str):
    """
    Cancel a running agent task.

    Args:
        task_id: Task ID to cancel

    Returns:
        AgentCancelResponse with cancellation status

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/agents/cancel/001:planner \\
             -H "Content-Type: application/json"
        # Returns: {"task_id": "001:planner", "cancelled": true, ...}
        ```
    """
    try:
        cancelled = cancel_task(task_id)

        if cancelled:
            return AgentCancelResponse(
                task_id=task_id,
                cancelled=True,
                message=f"Task cancelled: {task_id}"
            )
        else:
            return AgentCancelResponse(
                task_id=task_id,
                cancelled=False,
                message=f"Task not found or already completed: {task_id}"
            )

    except Exception as e:
        logger.error(f"Error cancelling task: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def agents_health():
    """
    Health check for agents API.

    Returns basic status information about the agents API endpoint.

    Returns:
        Dictionary with status and configuration info
    """
    project_dir = _get_project_dir()

    return {
        "status": "ok",
        "endpoint": "agents",
        "project_dir": str(project_dir),
    }


# Pair Programming Routes

@router.post("/pair/start", response_model=PairStartResponse, status_code=status.HTTP_200_OK)
async def start_pair_session(request: PairStartRequest):
    """
    Start a pair programming session.

    This endpoint starts an interactive pair programming session with the AI.
    The session runs in the background and emits suggestions via WebSocket.

    Args:
        request: Pair programming start request with optional spec_id and initial_message

    Returns:
        PairStartResponse with session_id for tracking

    Raises:
        HTTPException: 409 if session already active, 500 for other errors

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/agents/pair/start \\
             -H "Content-Type: application/json" \\
             -d '{"spec_id": "001", "initial_message": "Help me implement authentication"}'
        # Returns: {"session_id": "pair_001_...", "status": "started", ...}
        ```
    """
    try:
        logger.info(
            f"Pair session start request: spec_id={request.spec_id}, "
            f"initial_message={request.initial_message[:50] if request.initial_message else 'None'}"
        )

        # Generate unique session ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"pair_{request.spec_id or 'general'}_{timestamp}"

        # Check if session already exists
        if session_id in _pair_sessions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Session already active: {session_id}",
            )

        # Get project directory
        project_dir = _get_project_dir()

        # Start background task
        task = asyncio.create_task(
            _run_pair_session_task(
                session_id=session_id,
                spec_id=request.spec_id,
                initial_message=request.initial_message,
                project_dir=project_dir,
                model=request.model,
                verbose=request.verbose,
            )
        )

        _pair_sessions[session_id] = task

        return PairStartResponse(
            session_id=session_id,
            spec_id=request.spec_id,
            status="started",
            message=f"Pair programming session started: {session_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting pair session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start pair programming session: {str(e)}",
        )


@router.get("/pair/status/{session_id}", response_model=PairStatusResponse, status_code=status.HTTP_200_OK)
async def get_pair_status(session_id: str):
    """
    Get the status of a pair programming session.

    Args:
        session_id: Session ID returned by POST /api/agents/pair/start

    Returns:
        PairStatusResponse with current session status

    Raises:
        HTTPException: 404 if session not found

    Example:
        ```bash
        curl -X GET http://localhost:8000/api/agents/pair/status/pair_001_20260203_120000 \\
             -H "Content-Type: application/json"
        # Returns: {"session_id": "pair_001_...", "status": "active", ...}
        ```
    """
    try:
        # Check if session is running
        if session_id in _pair_sessions:
            task = _pair_sessions[session_id]
            if task.done():
                status_str = "stopped"
            else:
                status_str = "active"

            # Get agent info if available
            mode = None
            session_num = None
            if session_id in _pair_session_agents:
                agent = _pair_session_agents[session_id]
                if hasattr(agent, "get_mode"):
                    mode = agent.get_mode()
                if hasattr(agent, "session_state"):
                    session_num = agent.session_state.session_num

            return PairStatusResponse(
                session_id=session_id,
                status=status_str,
                mode=mode,
                session_num=session_num,
                error=None,
            )

        # Check if agent info exists (session completed)
        if session_id in _pair_session_agents:
            agent_info = _pair_session_agents[session_id]
            if isinstance(agent_info, dict) and "error" in agent_info:
                return PairStatusResponse(
                    session_id=session_id,
                    status="error",
                    mode=None,
                    session_num=None,
                    error=agent_info["error"],
                )
            else:
                return PairStatusResponse(
                    session_id=session_id,
                    status="stopped",
                    mode=None,
                    session_num=None,
                    error=None,
                )

        # Session not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pair session status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session status: {str(e)}",
        )


@router.post("/pair/stop/{session_id}", response_model=PairStopResponse, status_code=status.HTTP_200_OK)
async def stop_pair_session(session_id: str):
    """
    Stop a pair programming session.

    Args:
        session_id: Session ID to stop

    Returns:
        PairStopResponse with stop status

    Example:
        ```bash
        curl -X POST http://localhost:8000/api/agents/pair/stop/pair_001_20260203_120000 \\
             -H "Content-Type: application/json"
        # Returns: {"session_id": "pair_001_...", "stopped": true, ...}
        ```
    """
    try:
        if session_id in _pair_sessions:
            task = _pair_sessions[session_id]
            task.cancel()

            # Wait for cancellation (with timeout)
            try:
                await asyncio.wait_for(task, timeout=5.0)
            except asyncio.CancelledError:
                pass
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for session {session_id} to stop")

            # Clean up
            del _pair_sessions[session_id]
            if session_id in _pair_session_agents:
                del _pair_session_agents[session_id]

            return PairStopResponse(
                session_id=session_id,
                stopped=True,
                message=f"Session stopped: {session_id}"
            )

        return PairStopResponse(
            session_id=session_id,
            stopped=False,
            message=f"Session not found or already stopped: {session_id}"
        )

    except Exception as e:
        logger.error(f"Error stopping pair session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop session: {str(e)}",
        )
