"""
Durable agent-run records (Track C — C3).

Thin persistence layer over api/models/agent_execution.py. Request handlers use
``create_execution`` / ``list_executions`` / ``get_execution`` with the request's
DB session; the background agent task finishes runs through
``record_execution_result``, which opens its own short-lived session because the
request session is long gone by the time the run ends. Recording is best-effort:
a persistence failure must never break a running agent.
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from api.models.agent_execution import AgentExecution
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def create_execution(
    db: Session,
    workspace_id: int,
    user_id: int | None,
    spec_id: str,
    agent_type: str,
    model: str,
) -> AgentExecution:
    """Insert a new run record in status 'running' and return it."""
    execution = AgentExecution(
        workspace_id=workspace_id,
        user_id=user_id,
        spec_id=spec_id,
        agent_type=agent_type,
        model=model,
        status="running",
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def list_executions(
    db: Session, workspace_id: int, limit: int = 50
) -> tuple[list[AgentExecution], int]:
    """Return (newest-first page, total count) of a workspace's run records."""
    query = db.query(AgentExecution).filter(
        AgentExecution.workspace_id == workspace_id
    )
    total = query.count()
    executions = query.order_by(AgentExecution.id.desc()).limit(limit).all()
    return executions, total


def get_execution(db: Session, execution_id: int) -> AgentExecution | None:
    """Return one run record by id, or None."""
    return (
        db.query(AgentExecution).filter(AgentExecution.id == execution_id).first()
    )


def mark_execution_finished(
    db: Session, execution: AgentExecution, status: str, error: str | None = None
) -> AgentExecution:
    """Set a terminal status + finished_at on a run record (request-session path)."""
    execution.status = status
    execution.error = error
    execution.finished_at = datetime.now(UTC)
    db.commit()
    db.refresh(execution)
    return execution


def record_execution_result(
    execution_id: int | None,
    status: str,
    error: str | None = None,
    session_factory: "Callable[[], Session] | None" = None,
) -> None:
    """Finish a run record from the background agent task (own session).

    ``execution_id`` is None when the run was started without persistence (e.g.
    legacy tokens) — then this is a no-op. Failures are logged, never raised:
    the agent result must not depend on the audit write.
    """
    if execution_id is None:
        return
    try:
        if session_factory is None:
            from core.database import SessionLocal as session_factory
        db = session_factory()
        try:
            execution = (
                db.query(AgentExecution)
                .filter(AgentExecution.id == execution_id)
                .first()
            )
            if execution is None:
                logger.warning(
                    "Execution record %s not found for result update", execution_id
                )
                return
            execution.status = status
            execution.error = error
            execution.finished_at = datetime.now(UTC)
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.warning(
            "Failed to record result for execution %s", execution_id, exc_info=True
        )
