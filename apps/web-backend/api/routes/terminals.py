"""
Terminal session management API (Track C — C5).

Lets a caller list and close *their own* live PTY sessions (created by the
/ws/terminal endpoint, namespaced per identity). Ownership is keyed on the
token ``sub`` exactly as the WebSocket endpoint keys it, so a caller can only
ever see or close sessions they own.
"""

import logging

from core.security import require_auth
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from services.terminal_manager import terminal_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/terminals", tags=["terminals"])


class TerminalSessionResponse(BaseModel):
    """Response model for one of the caller's terminal sessions."""

    session_id: str = Field(..., description="Client-facing session id")
    alive: bool = Field(..., description="Whether the PTY is still running")
    working_dir: str = Field(..., description="Session working directory")
    rows: int = Field(..., description="Terminal rows")
    cols: int = Field(..., description="Terminal columns")


class TerminalSessionListResponse(BaseModel):
    """Response model for the caller's active terminal sessions."""

    sessions: list[TerminalSessionResponse] = Field(
        default_factory=list, description="The caller's own sessions"
    )


def _require_owner(auth: dict) -> str:
    """Owner identity for terminal sessions: the raw token ``sub`` as a string.

    Mirrors /ws/terminal's ownership derivation (which accepts any non-empty
    ``sub``, numeric or legacy) rather than ``current_user_id`` (numeric-only),
    so REST management targets exactly the sessions the WebSocket created.
    """
    sub = auth.get("sub")
    if sub is None or str(sub) == "":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No authenticated user in token",
        )
    return str(sub)


@router.get("", response_model=TerminalSessionListResponse)
def list_my_terminals(auth: dict = Depends(require_auth)):
    """List the caller's own active terminal sessions."""
    owner = _require_owner(auth)
    sessions = [
        TerminalSessionResponse(**info)
        for info in terminal_manager.list_sessions_for_owner(owner)
    ]
    return TerminalSessionListResponse(sessions=sessions)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def close_my_terminal(session_id: str, auth: dict = Depends(require_auth)):
    """Close one of the caller's own terminal sessions (404 if not theirs)."""
    owner = _require_owner(auth)
    if not terminal_manager.close_session_for_owner(owner, session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminal session not found",
        )
