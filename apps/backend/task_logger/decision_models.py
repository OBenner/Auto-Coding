"""
Data models for AI decision tracking and explainability.
"""

from dataclasses import asdict, dataclass
from enum import Enum


class DecisionType(str, Enum):
    """Types of decisions made by AI agents."""

    APPROACH = "approach"  # Overall approach to solving a problem
    IMPLEMENTATION = "implementation"  # Specific implementation choice
    TOOL_SELECTION = "tool_selection"  # Which tool to use
    FILE_MODIFICATION = "file_modification"  # How to modify files
    ERROR_RECOVERY = "error_recovery"  # How to recover from errors
    ARCHITECTURE = "architecture"  # Architectural decisions
    OPTIMIZATION = "optimization"  # Performance/quality optimizations
    OTHER = "other"  # Other decision types


class ConfidenceLevel(str, Enum):
    """Confidence levels for decisions."""

    VERY_LOW = "very_low"  # < 40%
    LOW = "low"  # 40-60%
    MEDIUM = "medium"  # 60-80%
    HIGH = "high"  # 80-95%
    VERY_HIGH = "very_high"  # > 95%


@dataclass
class Alternative:
    """An alternative approach that was considered but not chosen."""

    description: str  # Description of the alternative
    reasoning: str  # Why this alternative was considered
    rejected_reason: str  # Why it was not chosen
    confidence_impact: str | None = None  # How this would affect confidence
    tradeoffs: list[str] | None = None  # Known tradeoffs of this approach

    def __post_init__(self):
        if self.tradeoffs is None:
            self.tradeoffs = []

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class DecisionPoint:
    """A decision point made by the AI agent."""

    timestamp: str  # When the decision was made
    decision_type: str  # Type of decision (from DecisionType enum)
    context: str  # What problem/situation led to this decision
    chosen_approach: str  # The approach that was chosen
    reasoning: str  # Why this approach was chosen
    confidence: float  # Confidence score (0.0 - 1.0)
    confidence_level: str  # Human-readable confidence level
    phase: str  # Which phase this decision was made in
    subtask_id: str | None = None  # Associated subtask if applicable
    session: int | None = None  # Session number
    alternatives: list[Alternative] | None = None  # Alternatives considered
    requires_review: bool = False  # Flag for uncertain decisions
    reasoning_chain: list[str] | None = None  # Step-by-step reasoning
    impact: str | None = None  # Expected impact of this decision
    reversible: bool = True  # Whether this decision can be easily reversed
    dependencies: list[str] | None = None  # What this decision depends on
    metadata: dict | None = None  # Additional metadata

    def __post_init__(self):
        if self.alternatives is None:
            self.alternatives = []
        if self.reasoning_chain is None:
            self.reasoning_chain = []
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}

        # Clamp confidence to valid range
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

        # Auto-flag low confidence decisions for review
        if self.confidence < 0.6 and not self.requires_review:
            self.requires_review = True

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        data = {}
        for k, v in asdict(self).items():
            if v is not None:
                data[k] = v
        return data

    def add_alternative(self, alternative: Alternative) -> None:
        """Add an alternative to this decision point."""
        if self.alternatives is None:
            self.alternatives = []
        self.alternatives.append(alternative)

    def add_reasoning_step(self, step: str) -> None:
        """Add a step to the reasoning chain."""
        if self.reasoning_chain is None:
            self.reasoning_chain = []
        self.reasoning_chain.append(step)

    @staticmethod
    def calculate_confidence_level(confidence: float) -> str:
        """Calculate human-readable confidence level from score."""
        if confidence < 0.4:
            return ConfidenceLevel.VERY_LOW.value
        elif confidence < 0.6:
            return ConfidenceLevel.LOW.value
        elif confidence < 0.8:
            return ConfidenceLevel.MEDIUM.value
        elif confidence < 0.95:
            return ConfidenceLevel.HIGH.value
        else:
            return ConfidenceLevel.VERY_HIGH.value
