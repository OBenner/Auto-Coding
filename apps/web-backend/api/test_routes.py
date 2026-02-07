"""
Test API routes for WebSocket broadcasting testing

These endpoints are used for E2E testing of WebSocket functionality.
They allow test scripts to trigger broadcasts via HTTP, ensuring they
use the same ConnectionManager instance as the running server.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.websocket import broadcast_log_event, broadcast_execution_event

router = APIRouter(prefix="/test", tags=["test"])


class BroadcastLogRequest(BaseModel):
    """Request model for broadcast log event"""
    spec_id: str
    log_line: str
    level: str = "info"


class BroadcastExecutionRequest(BaseModel):
    """Request model for broadcast execution event"""
    spec_id: str
    phase: str
    phase_progress: float
    overall_progress: float
    message: Optional[str] = None
    current_subtask: Optional[str] = None


@router.post("/broadcast")
async def test_broadcast_log(request: BroadcastLogRequest):
    """
    Test endpoint to trigger a log event broadcast.

    Used for E2E testing to verify WebSocket clients receive events.
    """
    try:
        await broadcast_log_event(
            spec_id=request.spec_id,
            log_line=request.log_line,
            level=request.level
        )
        return {"status": "ok", "message": "Log event broadcasted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/broadcast-execution")
async def test_broadcast_execution(request: BroadcastExecutionRequest):
    """
    Test endpoint to trigger an execution event broadcast.

    Used for E2E testing to verify WebSocket clients receive execution progress events.
    """
    try:
        await broadcast_execution_event(
            spec_id=request.spec_id,
            phase=request.phase,
            phase_progress=request.phase_progress,
            overall_progress=request.overall_progress,
            message=request.message,
            current_subtask=request.current_subtask
        )
        return {"status": "ok", "message": "Execution event broadcasted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
