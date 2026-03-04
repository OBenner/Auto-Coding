"""
Agent Preference Profile Data Models
======================================

Data structures for tracking and adapting agent behavior based on user preferences
and feedback patterns. Enables agents to learn from user interactions and adjust
their approach to match individual or team coding styles.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    rating: int | None = None  # Optional rating (1-5 for stars, 0/1 for thumbs)


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
    coding_style: CodingStylePreferences = field(default_factory=CodingStylePreferences)

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
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def add_feedback(
        self,
        feedback_type: FeedbackType | Literal["accepted", "rejected", "modified"],
        task_description: str,
        agent_type: str,
        context: dict[str, str] | None = None,
        rating: int | None = None,
    ) -> None:
        """
        Add a feedback record and update learned adjustments.

        Args:
            feedback_type: Type of feedback (accepted/rejected/modified)
            task_description: Description of the task that was evaluated
            agent_type: Agent that produced the output
            context: Optional additional context about the feedback
            rating: Optional rating (1-5 for stars, 0/1 for thumbs)
        """
        # Convert string to enum if needed
        if isinstance(feedback_type, str):
            feedback_type = FeedbackType(feedback_type)

        record = FeedbackRecord(
            timestamp=datetime.now(UTC).isoformat(),
            feedback_type=feedback_type,
            task_description=task_description,
            agent_type=agent_type,
            context=context or {},
            rating=rating,
        )
        self.feedback_history.append(record)
        self.updated_at = datetime.now(UTC).isoformat()

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
                    "rating": f.rating,
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
                rating=f.get("rating"),
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
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=data.get("updated_at", datetime.now(UTC).isoformat()),
        )


def modify_prompt_for_preferences(prompt: str, profile: PreferenceProfile) -> str:
    """
    Modify an agent prompt to include adaptive behavior instructions based on user preferences.

    This function injects preference-based instructions into the agent's system prompt to
    adapt its behavior according to learned patterns and explicit user settings. The modifications
    guide the agent's verbosity level, risk tolerance, coding style, and other behavioral aspects.

    Args:
        prompt: The original agent system prompt
        profile: User preference profile containing behavior settings and learned adjustments

    Returns:
        Modified prompt with adaptive behavior instructions injected

    Example:
        >>> from agents.preferences import PreferenceProfile, modify_prompt_for_preferences
        >>> profile = PreferenceProfile(verbosity_level=VerbosityLevel.CONCISE)
        >>> original_prompt = "You are a helpful coding assistant."
        >>> modified = modify_prompt_for_preferences(original_prompt, profile)
        >>> "concise" in modified.lower()
        True
    """
    # Build adaptive instructions based on preferences
    instructions = []

    # 1. Verbosity level adaptations
    effective_verbosity = profile.get_effective_verbosity()
    verbosity_guidance = {
        VerbosityLevel.MINIMAL: (
            "- Keep responses brief and code-focused. Minimize explanations unless explicitly requested.\n"
            "- Skip background context and reasoning unless critical to understanding.\n"
            "- Prefer showing over telling - let the code speak for itself."
        ),
        VerbosityLevel.CONCISE: (
            "- Provide concise explanations for simple tasks.\n"
            "- Focus on the 'what' and 'why' without excessive detail.\n"
            "- Use brief inline comments rather than long docstrings for obvious code."
        ),
        VerbosityLevel.NORMAL: (
            "- Provide clear explanations at a standard level of detail.\n"
            "- Balance brevity with thoroughness - explain key decisions without over-explaining."
        ),
        VerbosityLevel.DETAILED: (
            "- Provide thorough explanations for non-trivial changes.\n"
            "- Explain the reasoning behind architectural decisions.\n"
            "- Include helpful context about trade-offs and alternatives considered."
        ),
        VerbosityLevel.VERBOSE: (
            "- Provide extensive detail and comprehensive explanations.\n"
            "- Include background context, reasoning, and alternative approaches.\n"
            "- Document complex logic thoroughly with detailed comments and docstrings."
        ),
    }
    if effective_verbosity in verbosity_guidance:
        instructions.append(
            f"## Verbosity Guidance\n{verbosity_guidance[effective_verbosity]}"
        )

    # 2. Risk tolerance adaptations
    effective_risk = profile.get_effective_risk_tolerance()
    risk_guidance = {
        RiskTolerance.CAUTIOUS: (
            "- Prioritize safety and stability over speed.\n"
            "- Ask for confirmation before making significant changes to existing code.\n"
            "- Prefer conservative, well-tested approaches over experimental solutions.\n"
            "- Add extra validation and error handling to prevent regressions."
        ),
        RiskTolerance.BALANCED: (
            "- Balance safety with pragmatism.\n"
            "- Make reasonable assumptions for straightforward changes.\n"
            "- Ask for clarification when the approach has meaningful trade-offs."
        ),
        RiskTolerance.AGGRESSIVE: (
            "- Optimize for speed and iteration velocity.\n"
            "- Make reasonable assumptions to move quickly.\n"
            "- Refactor aggressively when it improves code quality.\n"
            "- Focus on getting working code first, then refine."
        ),
    }
    if effective_risk in risk_guidance:
        instructions.append(
            f"## Risk Tolerance Guidance\n{risk_guidance[effective_risk]}"
        )

    # 3. Project type context
    project_guidance = {
        ProjectType.GREENFIELD: (
            "- This is a new project with flexibility for experimentation.\n"
            "- Feel free to suggest modern patterns and best practices.\n"
            "- Prioritize clean architecture over backward compatibility."
        ),
        ProjectType.ESTABLISHED: (
            "- This is an established codebase with existing patterns.\n"
            "- Follow existing conventions and architectural patterns.\n"
            "- Balance innovation with consistency."
        ),
        ProjectType.LEGACY: (
            "- This is a legacy codebase requiring extra caution.\n"
            "- Preserve existing behavior unless explicitly asked to change it.\n"
            "- Make minimal, surgical changes to reduce risk of regressions.\n"
            "- Test thoroughly before and after changes."
        ),
    }
    if profile.project_type in project_guidance:
        instructions.append(
            f"## Project Context\n{project_guidance[profile.project_type]}"
        )

    # 4. Coding style preferences
    style_instructions = []
    style = profile.coding_style

    if style.indentation != "auto":
        style_instructions.append(
            f"- Use {style.indentation} for indentation (not auto-detected)"
        )
    if style.quote_style != "auto":
        style_instructions.append(
            f"- Use {style.quote_style} quotes for strings (not auto-detected)"
        )
    if style.line_length:
        style_instructions.append(f"- Limit lines to {style.line_length} characters")
    if style.naming_convention != "auto":
        style_instructions.append(
            f"- Follow {style.naming_convention} naming convention"
        )
    if style.comment_density == "minimal":
        style_instructions.append(
            "- Keep comments minimal - only for non-obvious logic"
        )
    elif style.comment_density == "verbose":
        style_instructions.append(
            "- Add comprehensive comments and docstrings for all non-trivial code"
        )
    if not style.type_hints:
        style_instructions.append("- Do not add type hints (user preference)")

    if style_instructions:
        instructions.append(
            "## Coding Style Preferences\n" + "\n".join(style_instructions)
        )

    # 5. Explicit user instructions
    if profile.user_instructions:
        user_prefs = "\n".join(f"- {instr}" for instr in profile.user_instructions)
        instructions.append(f"## User Preferences\n{user_prefs}")

    # 6. Inject instructions into prompt
    if not instructions:
        # No preferences to inject, return original prompt
        return prompt

    adaptive_section = (
        "\n\n# Adaptive Behavior Instructions\n\n"
        "The following instructions reflect learned user preferences and feedback patterns. "
        "Apply these guidelines to adapt your behavior to this user's coding style and expectations.\n\n"
        + "\n\n".join(instructions)
    )

    # Insert before the final section or at the end
    # Look for common final sections to insert before them
    final_markers = [
        "\n## Quality Checklist",
        "\n## Important",
        "\n# Important",
        "\n## Examples",
        "\n# Examples",
    ]

    for marker in final_markers:
        if marker in prompt:
            return prompt.replace(marker, adaptive_section + "\n" + marker)

    # No final section found, append at the end
    return prompt + adaptive_section


def _safe_enum(enum_cls: type[Enum], value: str, default: Enum) -> Enum:
    """Safely convert a string to an enum, returning default on invalid value."""
    try:
        return enum_cls(value)
    except (ValueError, TypeError):
        return default


def app_settings_to_profile(settings: dict) -> PreferenceProfile:
    """
    Convert frontend AppSettings dict to a backend PreferenceProfile.

    Field mapping:
    - agentVerbosity        -> verbosity_level
    - agentRiskTolerance    -> risk_tolerance
    - agentProjectType      -> project_type
    - agentCodingStyle.*    -> coding_style.*
    - agentUserInstructions -> user_instructions

    Invalid enum values are mapped to safe defaults.
    """
    coding_style_data = settings.get("agentCodingStyle", {})
    if not isinstance(coding_style_data, dict):
        coding_style_data = {}
    coding_style = CodingStylePreferences(
        indentation=coding_style_data.get("indentation", "auto"),
        quote_style=coding_style_data.get("quoteStyle", "auto"),
        line_length=coding_style_data.get("lineLength"),
        naming_convention=coding_style_data.get("namingConvention", "auto"),
        comment_density=coding_style_data.get("commentDensity", "normal"),
        type_hints=coding_style_data.get("typeHints", True),
    )

    raw_instructions = settings.get("agentUserInstructions", [])
    if not isinstance(raw_instructions, list):
        raw_instructions = []
    user_instructions = [str(s) for s in raw_instructions if isinstance(s, str)]

    return PreferenceProfile(
        verbosity_level=_safe_enum(
            VerbosityLevel,
            settings.get("agentVerbosity", "normal"),
            VerbosityLevel.NORMAL,
        ),
        risk_tolerance=_safe_enum(
            RiskTolerance,
            settings.get("agentRiskTolerance", "balanced"),
            RiskTolerance.BALANCED,
        ),
        project_type=_safe_enum(
            ProjectType,
            settings.get("agentProjectType", "established"),
            ProjectType.ESTABLISHED,
        ),
        coding_style=coding_style,
        user_instructions=user_instructions,
    )
