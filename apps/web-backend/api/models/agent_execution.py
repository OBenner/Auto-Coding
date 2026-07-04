"""
Agent execution history for cloud-hosted Auto Code (Track C — C3).

Persists every agent run (planner/coder/qa_reviewer/qa_fixer) so history and
audit survive restarts (UC-S2/S3): who ran what, in which workspace, with which
model, and how it ended. The in-memory task registry in services/agent_runner.py
remains the live-status source; this table is the durable record.
"""

from datetime import UTC, datetime

from core.database import Base
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

# Closed sets, mirrored as DB CHECK constraints below.
AGENT_TYPES = ("planner", "coder", "qa_reviewer", "qa_fixer")
EXECUTION_STATUSES = ("running", "completed", "failed", "cancelled")


class AgentExecution(Base):
    """One agent run: workspace-scoped, user-attributed, with lifecycle status."""

    __tablename__ = "agent_executions"
    __table_args__ = (
        CheckConstraint(
            "agent_type IN ('planner', 'coder', 'qa_reviewer', 'qa_fixer')",
            name="ck_agent_execution_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'cancelled')",
            name="ck_agent_execution_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # SET NULL: the audit record must survive user deletion.
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    spec_id = Column(String(255), nullable=False, index=True)
    agent_type = Column(String(20), nullable=False)
    model = Column(String(100), nullable=False)

    status = Column(String(20), nullable=False, default="running")
    error = Column(Text, nullable=True)

    # timezone=True: values are written as aware-UTC; naive columns would drop
    # the offset on round-trip (matters on Postgres).
    started_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    finished_at = Column(DateTime(timezone=True), nullable=True)

    workspace = relationship("Workspace")
    user = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<AgentExecution(id={self.id}, workspace_id={self.workspace_id}, "
            f"spec_id={self.spec_id!r}, agent_type={self.agent_type!r}, "
            f"status={self.status!r})>"
        )


# Pydantic models for API responses


class ExecutionResponse(BaseModel):
    """Response model for a single agent execution record."""

    id: int = Field(..., description="Execution ID")
    workspace_id: int = Field(..., description="Workspace the run belongs to")
    user_id: int | None = Field(None, description="User who started the run")
    spec_id: str = Field(..., description="Spec the agent ran against")
    agent_type: str = Field(..., description="planner/coder/qa_reviewer/qa_fixer")
    model: str = Field(..., description="Model used for the run")
    status: str = Field(..., description="running/completed/failed/cancelled")
    error: str | None = Field(None, description="Error message when failed")
    started_at: datetime = Field(..., description="Run start timestamp")
    finished_at: datetime | None = Field(None, description="Run end timestamp")

    model_config = ConfigDict(from_attributes=True)


class ExecutionListResponse(BaseModel):
    """Response model for a workspace's execution history (newest first)."""

    executions: list[ExecutionResponse] = Field(
        default_factory=list, description="Execution records, newest first"
    )
    total: int = Field(..., description="Total records in this workspace")
