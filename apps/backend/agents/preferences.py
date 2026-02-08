"""
Agent Preference Profile Data Models
======================================

Data structures for tracking and adapting agent behavior based on user preferences
and feedback patterns. Enables agents to learn from user interactions and adjust
their approach to match individual or team coding styles.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


class VerbosityLevel(str, Enum):
    """Agent verbosity level for explanations and responses."""

    MINIMAL = "minimal"  # Brief, code-focused output
    CONCISE = "concise"  # Short explanations for simple tasks
    NORMAL = "normal"  # Standard detail level
    DETAILED = "detailed"  # Thorough explanations
    VERBOSE = "verbose"  # Extensive detail for complex tasks


class RiskTolerance(str, Enum):
    """Risk tolerance for agent decision-making."""

    CAUTIOUS = "cautious"  # Prefer safety, ask before changes
    BALANCED = "balanced"  # Standard approach
    AGGRESSIVE = "aggressive"  # Move fast, optimize for speed


class ProjectType(str, Enum):
    """Project maturity level affecting risk decisions."""

    GREENFIELD = "greenfield"  # New project, higher risk tolerance
    ESTABLISHED = "established"  # Mature project
    LEGACY = "legacy"  # Legacy codebase, be more cautious


class FeedbackType(str, Enum):
    """Type of user feedback on agent output."""

    ACCEPTED = "accepted"  # User accepted output as-is
    REJECTED = "rejected"  # User rejected and requested redo
    MODIFIED = "modified"  # User accepted but made changes


@dataclass
class FeedbackRecord:
    """A single user feedback event."""

    timestamp: str  # ISO format datetime
    feedback_type: FeedbackType
    task_description: str
    agent_type: str  # planner, coder, qa_reviewer, etc.
    context: dict[str, str] = field(
        default_factory=dict
    )  # Additional context (e.g., what was modified)


@dataclass
class CodingStylePreferences:
    """Coding style preferences learned from project conventions."""

    indentation: str = "auto"  # "spaces", "tabs", "auto"
    quote_style: str = "auto"  # "single", "double", "auto"
    line_length: int | None = None  # Max line length or None
    naming_convention: str = "auto"  # "snake_case", "camelCase", "auto"
    comment_density: str = "normal"  # "minimal", "normal", "verbose"
    type_hints: bool = True  # Whether to use type hints


@dataclass
class PreferenceProfile:
    """
    Complete preference profile for an agent.

    Tracks user preferences, feedback history, and learned patterns to adapt
    agent behavior over time.
    """

    # Explicit user preferences
    verbosity_level: VerbosityLevel = VerbosityLevel.NORMAL
    risk_tolerance: RiskTolerance = RiskTolerance.BALANCED
    project_type: ProjectType = ProjectType.ESTABLISHED

    # Coding style preferences
    coding_style: CodingStylePreferences = field(
        default_factory=CodingStylePreferences
    )

    # Feedback history
    feedback_history: list[FeedbackRecord] = field(default_factory=list)

    # Learned patterns from feedback
    learned_verbosity_adjustment: int = 0  # -2 to +2 (more concise to more verbose)
    learned_risk_adjustment: int = 0  # -1 to +1 (more cautious to more aggressive)

    # Explicit user instructions (e.g., "be more cautious", "more concise")
    user_instructions: list[str] = field(default_factory=list)

    # Team-wide preferences (if set)
    team_profile_id: str | None = None

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def add_feedback(
        self,
        feedback_type: FeedbackType | Literal["accepted", "rejected", "modified"],
        task_description: str,
        agent_type: str,
        context: dict[str, str] | None = None,
    ) -> None:
        """
        Add a feedback record and update learned adjustments.

        Args:
            feedback_type: Type of feedback (accepted/rejected/modified)
            task_description: Description of the task that was evaluated
            agent_type: Agent that produced the output
            context: Optional additional context about the feedback
        """
        # Convert string to enum if needed
        if isinstance(feedback_type, str):
            feedback_type = FeedbackType(feedback_type)

        record = FeedbackRecord(
            timestamp=datetime.utcnow().isoformat(),
            feedback_type=feedback_type,
            task_description=task_description,
            agent_type=agent_type,
            context=context or {},
        )
        self.feedback_history.append(record)
        self.updated_at = datetime.utcnow().isoformat()

        # Update learned adjustments based on feedback patterns
        self._update_learned_preferences()

    def _update_learned_preferences(self) -> None:
        """
        Update learned preference adjustments based on recent feedback patterns.

        Analyzes the last 10 feedback records to detect patterns and adjust
        verbosity and risk tolerance accordingly.
        """
        if len(self.feedback_history) < 3:
            return  # Not enough data to learn patterns

        # Analyze recent feedback (last 10 records)
        recent = self.feedback_history[-10:]
        rejection_rate = sum(
            1 for f in recent if f.feedback_type == FeedbackType.REJECTED
        ) / len(recent)

        # If high rejection rate, adjust toward more caution
        if rejection_rate > 0.3:
            self.learned_risk_adjustment = max(-1, self.learned_risk_adjustment - 1)

        # Analyze modification patterns for verbosity hints
        modifications = [f for f in recent if f.feedback_type == FeedbackType.MODIFIED]
        if len(modifications) >= 3:
            # Look for verbosity-related context hints
            too_verbose_count = sum(
                1
                for m in modifications
                if "too verbose" in m.context.get("reason", "").lower()
                or "too detailed" in m.context.get("reason", "").lower()
            )
            too_concise_count = sum(
                1
                for m in modifications
                if "too concise" in m.context.get("reason", "").lower()
                or "need more detail" in m.context.get("reason", "").lower()
            )

            if too_verbose_count >= 2:
                self.learned_verbosity_adjustment = max(
                    -2, self.learned_verbosity_adjustment - 1
                )
            elif too_concise_count >= 2:
                self.learned_verbosity_adjustment = min(
                    2, self.learned_verbosity_adjustment + 1
                )

    def get_effective_verbosity(self) -> VerbosityLevel:
        """
        Get effective verbosity level including learned adjustments.

        Returns:
            Adjusted verbosity level based on user preferences and feedback
        """
        levels = list(VerbosityLevel)
        current_index = levels.index(self.verbosity_level)
        adjusted_index = max(
            0, min(len(levels) - 1, current_index + self.learned_verbosity_adjustment)
        )
        return levels[adjusted_index]

    def get_effective_risk_tolerance(self) -> RiskTolerance:
        """
        Get effective risk tolerance including learned adjustments.

        Returns:
            Adjusted risk tolerance based on project type and feedback
        """
        tolerances = list(RiskTolerance)
        current_index = tolerances.index(self.risk_tolerance)

        # Apply project type adjustment
        project_adjustment = 0
        if self.project_type == ProjectType.GREENFIELD:
            project_adjustment = 1  # More aggressive for new projects
        elif self.project_type == ProjectType.LEGACY:
            project_adjustment = -1  # More cautious for legacy

        adjusted_index = max(
            0,
            min(
                len(tolerances) - 1,
                current_index + self.learned_risk_adjustment + project_adjustment,
            ),
        )
        return tolerances[adjusted_index]

    def get_feedback_acceptance_rate(self) -> float:
        """
        Calculate acceptance rate from feedback history.

        Returns:
            Acceptance rate (0.0-1.0) or 0.0 if no feedback
        """
        if not self.feedback_history:
            return 0.0

        accepted = sum(
            1 for f in self.feedback_history if f.feedback_type == FeedbackType.ACCEPTED
        )
        return accepted / len(self.feedback_history)

    def to_dict(self) -> dict:
        """
        Convert preference profile to dictionary for storage.

        Returns:
            Dictionary representation of the profile
        """
        return {
            "verbosity_level": self.verbosity_level.value,
            "risk_tolerance": self.risk_tolerance.value,
            "project_type": self.project_type.value,
            "coding_style": {
                "indentation": self.coding_style.indentation,
                "quote_style": self.coding_style.quote_style,
                "line_length": self.coding_style.line_length,
                "naming_convention": self.coding_style.naming_convention,
                "comment_density": self.coding_style.comment_density,
                "type_hints": self.coding_style.type_hints,
            },
            "feedback_history": [
                {
                    "timestamp": f.timestamp,
                    "feedback_type": f.feedback_type.value,
                    "task_description": f.task_description,
                    "agent_type": f.agent_type,
                    "context": f.context,
                }
                for f in self.feedback_history
            ],
            "learned_verbosity_adjustment": self.learned_verbosity_adjustment,
            "learned_risk_adjustment": self.learned_risk_adjustment,
            "user_instructions": self.user_instructions,
            "team_profile_id": self.team_profile_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PreferenceProfile":
        """
        Create preference profile from dictionary.

        Args:
            data: Dictionary representation of the profile

        Returns:
            PreferenceProfile instance
        """
        coding_style_data = data.get("coding_style", {})
        coding_style = CodingStylePreferences(
            indentation=coding_style_data.get("indentation", "auto"),
            quote_style=coding_style_data.get("quote_style", "auto"),
            line_length=coding_style_data.get("line_length"),
            naming_convention=coding_style_data.get("naming_convention", "auto"),
            comment_density=coding_style_data.get("comment_density", "normal"),
            type_hints=coding_style_data.get("type_hints", True),
        )

        feedback_history = [
            FeedbackRecord(
                timestamp=f["timestamp"],
                feedback_type=FeedbackType(f["feedback_type"]),
                task_description=f["task_description"],
                agent_type=f["agent_type"],
                context=f.get("context", {}),
            )
            for f in data.get("feedback_history", [])
        ]

        return cls(
            verbosity_level=VerbosityLevel(data.get("verbosity_level", "normal")),
            risk_tolerance=RiskTolerance(data.get("risk_tolerance", "balanced")),
            project_type=ProjectType(data.get("project_type", "established")),
            coding_style=coding_style,
            feedback_history=feedback_history,
            learned_verbosity_adjustment=data.get("learned_verbosity_adjustment", 0),
            learned_risk_adjustment=data.get("learned_risk_adjustment", 0),
            user_instructions=data.get("user_instructions", []),
            team_profile_id=data.get("team_profile_id"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
        )
