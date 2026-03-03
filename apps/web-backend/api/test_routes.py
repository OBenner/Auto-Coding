"""
Test API routes for WebSocket broadcasting testing.

WARNING: These endpoints are only registered when DEBUG=true (see main.py).
They must NEVER be exposed in production.
"""

from enum import Enum

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.websocket import broadcast_execution_event, broadcast_log_event

router = APIRouter(prefix="/test", tags=["test"])


class LogLevel(str, Enum):
    """Allowed log levels."""

    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class BroadcastLogRequest(BaseModel):
    """Request model for broadcast log event."""

    spec_id: str = Field(..., min_length=1, max_length=200)
    log_line: str = Field(..., min_length=1, max_length=10000)
    level: LogLevel = LogLevel.info


class BroadcastExecutionRequest(BaseModel):
    """Request model for broadcast execution event."""

    spec_id: str = Field(..., min_length=1, max_length=200)
    phase: str = Field(..., min_length=1, max_length=100)
    phase_progress: float = Field(..., ge=0.0, le=100.0)
    overall_progress: float = Field(..., ge=0.0, le=100.0)
    message: str | None = Field(None, max_length=1000)
    current_subtask: str | None = Field(None, max_length=200)


@router.post("/broadcast")
async def test_broadcast_log(request: BroadcastLogRequest):
    """
    Trigger a log event broadcast (debug/test only).
    """
    await broadcast_log_event(
        spec_id=request.spec_id,
        log_line=request.log_line,
        level=request.level.value,
    )
    return {"status": "ok", "message": "Log event broadcasted"}


@router.post("/broadcast-execution")
async def test_broadcast_execution(request: BroadcastExecutionRequest):
    """
    Trigger an execution event broadcast (debug/test only).
    """
    await broadcast_execution_event(
        spec_id=request.spec_id,
        phase=request.phase,
        phase_progress=request.phase_progress,
        overall_progress=request.overall_progress,
        message=request.message,
        current_subtask=request.current_subtask,
    )
    return {"status": "ok", "message": "Execution event broadcasted"}
