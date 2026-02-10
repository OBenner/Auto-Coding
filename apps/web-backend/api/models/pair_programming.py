"""
Pair Programming Event Models

Pydantic models for real-time pair programming events sent via WebSocket.
These models support the AI pair programming mode with code suggestions,
voice interaction, and session management.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


# Pair programming session phases
PairProgrammingPhase = Literal[
    "idle",
    "active",
    "paused",
    "analyzing",
    "suggesting",
    "complete",
    "error"
]

# Suggestion types matching suggestion_engine.py
SuggestionType = Literal[
    "completion",
    "refactor",
    "fix",
    "explanation"
]

# Voice interaction states
VoiceState = Literal[
    "idle",
    "listening",
    "processing",
    "speaking",
    "error"
]


class CodeRange(BaseModel):
    """Code range specification for suggestions"""

    start_line: int = Field(..., description="Starting line number (0-indexed)")
    start_column: int = Field(..., description="Starting column number (0-indexed)")
    end_line: int = Field(..., description="Ending line number (0-indexed)")
    end_column: int = Field(..., description="Ending column number (0-indexed)")


class SuggestionData(BaseModel):
    """
    Code suggestion data matching suggestion_engine.Suggestion structure.
    Sent from AI to developer during pair programming.
    """

    suggestion_id: str = Field(..., description="Unique identifier for this suggestion")
    type: SuggestionType = Field(..., description="Type of suggestion")
    content: str = Field(..., description="Suggested code or explanation text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    range: Optional[CodeRange] = Field(None, description="Code range where suggestion applies")
    description: str = Field(..., description="Human-readable description of suggestion")
    reasoning: Optional[str] = Field(None, description="Why this suggestion was made")
    file_path: Optional[str] = Field(None, description="File path this suggestion applies to")


class PairSessionData(BaseModel):
    """Pair programming session state data"""

    session_id: str = Field(..., description="Unique session identifier")
    phase: PairProgrammingPhase = Field(..., description="Current session phase")
    message: Optional[str] = Field(None, description="Human-readable status message")
    file_path: Optional[str] = Field(None, description="Currently active file")
    voice_enabled: bool = Field(default=False, description="Whether voice mode is active")


class VoiceInteractionData(BaseModel):
    """Voice interaction state data"""

    state: VoiceState = Field(..., description="Current voice interaction state")
    transcript: Optional[str] = Field(None, description="Transcribed text from speech")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if state is 'error'")


class SuggestionEvent(BaseModel):
    """
    Real-time suggestion event sent during pair programming.
    WebSocket event type: 'pair_suggestion'
    """

    event_type: Literal["pair_suggestion"] = "pair_suggestion"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    spec_id: Optional[str] = Field(None, description="Related spec/task ID if applicable")
    data: SuggestionData = Field(..., description="Suggestion data payload")


class PairSessionEvent(BaseModel):
    """
    Pair programming session lifecycle event.
    WebSocket event type: 'pair_session'
    """

    event_type: Literal["pair_session"] = "pair_session"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    spec_id: Optional[str] = Field(None, description="Related spec/task ID if applicable")
    data: PairSessionData = Field(..., description="Session state data")


class VoiceInteractionEvent(BaseModel):
    """
    Voice interaction state event.
    WebSocket event type: 'pair_voice'
    """

    event_type: Literal["pair_voice"] = "pair_voice"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    spec_id: Optional[str] = Field(None, description="Related spec/task ID if applicable")
    data: VoiceInteractionData = Field(..., description="Voice interaction data")


class SuggestionActionData(BaseModel):
    """Data for suggestion acceptance/rejection actions"""

    suggestion_id: str = Field(..., description="ID of the suggestion being acted upon")
    action: Literal["accept", "reject", "modify"] = Field(..., description="Action taken")
    modified_content: Optional[str] = Field(None, description="Modified content if action is 'modify'")


class SuggestionActionEvent(BaseModel):
    """
    Event sent when developer accepts/rejects a suggestion.
    WebSocket event type: 'pair_action'
    """

    event_type: Literal["pair_action"] = "pair_action"
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    spec_id: Optional[str] = Field(None, description="Related spec/task ID if applicable")
    data: SuggestionActionData = Field(..., description="Action data")
