"""
Agent Event Models

Pydantic models for real-time agent progress events sent via WebSocket.
These models match the event structure expected by the frontend agent-events.ts parser.
"""

from typing import Literal

from pydantic import BaseModel, Field

# Execution phases matching frontend expectations
ExecutionPhase = Literal[
    "idle", "planning", "coding", "qa_review", "qa_fixing", "complete", "failed"
]

# Ideation phases for spec creation
IdeationPhase = Literal[
    "idle", "analyzing", "discovering", "generating", "finalizing", "complete", "error"
]

# Roadmap phases for roadmap generation
RoadmapPhase = Literal[
    "idle", "analyzing", "discovering", "generating", "complete", "error"
]


class ProgressData(BaseModel):
    """Progress information for a phase"""

    completed: int = Field(default=0, description="Number of completed items")
    total: int = Field(default=0, description="Total number of items")
    percentage: float = Field(default=0.0, description="Completion percentage (0-100)")


class ExecutionProgressData(BaseModel):
    """Real-time execution progress data"""

    phase: ExecutionPhase = Field(..., description="Current execution phase")
    phase_progress: float = Field(
        default=0.0, description="Progress within current phase (0-100)"
    )
    overall_progress: float = Field(
        default=0.0, description="Overall build progress (0-100)"
    )
    message: str | None = Field(None, description="Human-readable status message")
    current_subtask: str | None = Field(
        None, description="Currently executing subtask ID"
    )


class IdeationProgressData(BaseModel):
    """Real-time ideation progress data"""

    phase: IdeationPhase = Field(..., description="Current ideation phase")
    progress: float = Field(default=0.0, description="Phase progress (0-100)")
    message: str | None = Field(None, description="Human-readable status message")
    completed_types: int = Field(
        default=0, description="Number of completed idea types"
    )
    total_types: int = Field(default=0, description="Total number of idea types")


class RoadmapProgressData(BaseModel):
    """Real-time roadmap generation progress data"""

    phase: RoadmapPhase = Field(..., description="Current roadmap phase")
    progress: float = Field(default=0.0, description="Phase progress (0-100)")
    message: str | None = Field(None, description="Human-readable status message")


class AgentEvent(BaseModel):
    """Base agent event for WebSocket communication"""

    event_type: Literal["execution", "ideation", "roadmap", "log", "error"] = Field(
        ..., description="Type of event"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    spec_id: str = Field(..., description="Spec/task ID this event relates to")
    data: dict | None = Field(None, description="Event-specific data payload")


class ExecutionEvent(AgentEvent):
    """Execution progress event"""

    event_type: Literal["execution"] = "execution"
    data: ExecutionProgressData = Field(..., description="Execution progress data")


class IdeationEvent(AgentEvent):
    """Ideation progress event"""

    event_type: Literal["ideation"] = "ideation"
    data: IdeationProgressData = Field(..., description="Ideation progress data")


class RoadmapEvent(AgentEvent):
    """Roadmap generation progress event"""

    event_type: Literal["roadmap"] = "roadmap"
    data: RoadmapProgressData = Field(..., description="Roadmap progress data")


class LogEvent(AgentEvent):
    """Raw log message event"""

    event_type: Literal["log"] = "log"
    log_line: str = Field(..., description="Raw log line")
    level: Literal["debug", "info", "warning", "error"] = Field(
        default="info", description="Log level"
    )


class ErrorEvent(AgentEvent):
    """Error event"""

    event_type: Literal["error"] = "error"
    error_message: str = Field(..., description="Error message")
    error_type: str | None = Field(None, description="Error type/category")
    traceback: str | None = Field(None, description="Error traceback if available")


class PhaseEvent(BaseModel):
    """Structured phase transition event (matching frontend phase-event-parser)"""

    phase: str = Field(..., description="New phase name")
    message: str | None = Field(None, description="Human-readable message")
    subtask: str | None = Field(None, description="Current subtask ID")
    progress: float | None = Field(None, description="Phase progress (0-100)")


class WebSocketMessage(BaseModel):
    """WebSocket message wrapper for client-server communication"""

    action: Literal["subscribe", "unsubscribe", "ping"] = Field(
        ..., description="Client action"
    )
    spec_id: str | None = Field(None, description="Spec ID to subscribe to")
