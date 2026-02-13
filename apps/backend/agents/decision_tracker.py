"""
Decision Tracker for AI Agent Sessions
========================================

Tracks decision points made by AI agents during task execution,
including chosen approaches, alternatives considered, and confidence levels.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from task_logger.decision_models import (
    Alternative,
    DecisionPoint,
    DecisionType,
)
from task_logger.logger import TaskLogger
from task_logger.models import LogPhase

logger = logging.getLogger(__name__)


class DecisionTracker:
    """
    Tracks AI agent decisions during task execution.

    This class manages decision points, including:
    - The chosen approach for a problem
    - Alternative approaches that were considered
    - Reasoning and confidence levels
    - Decision metadata for audit and analysis

    Decisions are logged to the TaskLogger and stored for later review,
    enabling transparency and trust in AI behavior.

    Usage:
        tracker = DecisionTracker(spec_dir, task_logger)

        # Track a decision
        decision = tracker.track_decision(
            decision_type=DecisionType.IMPLEMENTATION,
            context="Need to validate user input",
            chosen_approach="Use Pydantic models for validation",
            reasoning="Type-safe, self-documenting, widely adopted",
            confidence=0.85
        )

        # Add alternatives
        tracker.add_alternative(
            decision,
            Alternative(
                description="Manual validation with if/else",
                reasoning="Simple, no dependencies",
                rejected_reason="Harder to maintain, error-prone"
            )
        )

        # Finalize and log
        tracker.log_decision(decision)
    """

    DECISIONS_FILE = "decisions.json"

    def __init__(
        self,
        spec_dir: Path,
        task_logger: TaskLogger | None = None,
        current_phase: LogPhase = LogPhase.CODING,
    ):
        """
        Initialize the decision tracker.

        Args:
            spec_dir: Path to the spec directory
            task_logger: TaskLogger instance for logging decisions
            current_phase: Current execution phase (default: CODING)
        """
        self.spec_dir = Path(spec_dir)
        self.decisions_file = self.spec_dir / self.DECISIONS_FILE
        self.task_logger = task_logger
        self.current_phase = current_phase
        self.current_subtask: str | None = None
        self.current_session: int | None = None
        self.decisions: list[DecisionPoint] = []

        # Load existing decisions
        self._load_decisions()

    def _load_decisions(self) -> None:
        """Load existing decisions from file."""
        if self.decisions_file.exists():
            try:
                with open(self.decisions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Reconstruct DecisionPoint objects from stored data
                    self.decisions = [
                        self._decision_from_dict(d) for d in data.get("decisions", [])
                    ]
                    logger.debug(f"Loaded {len(self.decisions)} existing decisions")
            except Exception as e:
                logger.error(f"Failed to load decisions: {e}")
                self.decisions = []

    def _save_decisions(self) -> None:
        """Save decisions to file."""
        try:
            # Ensure spec directory exists
            self.spec_dir.mkdir(parents=True, exist_ok=True)

            # Convert decisions to dict format
            data = {
                "decisions": [d.to_dict() for d in self.decisions],
                "last_updated": datetime.now(UTC).isoformat(),
            }

            with open(self.decisions_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self.decisions)} decisions to {self.decisions_file}")
        except Exception as e:
            logger.error(f"Failed to save decisions: {e}")

    def _decision_from_dict(self, data: dict[str, Any]) -> DecisionPoint:
        """Reconstruct a DecisionPoint from dictionary data."""
        # Convert Alternative dicts back to Alternative objects
        alternatives = []
        if "alternatives" in data and data["alternatives"]:
            for alt_data in data["alternatives"]:
                alternatives.append(
                    Alternative(
                        description=alt_data["description"],
                        reasoning=alt_data["reasoning"],
                        rejected_reason=alt_data["rejected_reason"],
                        confidence_impact=alt_data.get("confidence_impact"),
                        tradeoffs=alt_data.get("tradeoffs", []),
                    )
                )

        return DecisionPoint(
            timestamp=data["timestamp"],
            decision_type=data["decision_type"],
            context=data["context"],
            chosen_approach=data["chosen_approach"],
            reasoning=data["reasoning"],
            confidence=data["confidence"],
            confidence_level=data["confidence_level"],
            phase=data["phase"],
            subtask_id=data.get("subtask_id"),
            session=data.get("session"),
            alternatives=alternatives,
            requires_review=data.get("requires_review", False),
            reasoning_chain=data.get("reasoning_chain", []),
            impact=data.get("impact"),
            reversible=data.get("reversible", True),
            dependencies=data.get("dependencies", []),
            metadata=data.get("metadata", {}),
        )

    def set_phase(self, phase: LogPhase) -> None:
        """Set the current execution phase."""
        self.current_phase = phase

    def set_subtask(self, subtask_id: str | None) -> None:
        """Set the current subtask being processed."""
        self.current_subtask = subtask_id

    def set_session(self, session: int) -> None:
        """Set the current session number."""
        self.current_session = session

    def track_decision(
        self,
        decision_type: DecisionType | str,
        context: str,
        chosen_approach: str,
        reasoning: str,
        confidence: float,
        alternatives: list[Alternative] | None = None,
        reasoning_chain: list[str] | None = None,
        impact: str | None = None,
        reversible: bool = True,
        dependencies: list[str] | None = None,
        metadata: dict | None = None,
    ) -> DecisionPoint:
        """
        Track a decision made during task execution.

        Args:
            decision_type: Type of decision (from DecisionType enum)
            context: What problem/situation led to this decision
            chosen_approach: The approach that was chosen
            reasoning: Why this approach was chosen
            confidence: Confidence score (0.0 - 1.0)
            alternatives: Alternative approaches considered (optional)
            reasoning_chain: Step-by-step reasoning (optional)
            impact: Expected impact of this decision (optional)
            reversible: Whether this decision can be easily reversed (default: True)
            dependencies: What this decision depends on (optional)
            metadata: Additional metadata (optional)

        Returns:
            The created DecisionPoint object
        """
        # Convert DecisionType enum to string if needed
        if isinstance(decision_type, DecisionType):
            decision_type = decision_type.value

        # Calculate confidence level
        confidence_level = DecisionPoint.calculate_confidence_level(confidence)

        # Create decision point
        decision = DecisionPoint(
            timestamp=datetime.now(UTC).isoformat(),
            decision_type=decision_type,
            context=context,
            chosen_approach=chosen_approach,
            reasoning=reasoning,
            confidence=confidence,
            confidence_level=confidence_level,
            phase=self.current_phase.value,
            subtask_id=self.current_subtask,
            session=self.current_session,
            alternatives=alternatives or [],
            reasoning_chain=reasoning_chain or [],
            impact=impact,
            reversible=reversible,
            dependencies=dependencies or [],
            metadata=metadata or {},
        )

        # Store decision
        self.decisions.append(decision)

        logger.info(
            f"Tracked {decision_type} decision: {chosen_approach} "
            f"(confidence: {confidence_level})"
        )

        return decision

    def add_alternative(
        self,
        decision: DecisionPoint,
        alternative: Alternative,
    ) -> None:
        """
        Add an alternative approach to a decision.

        Args:
            decision: The decision to add an alternative to
            alternative: The alternative approach
        """
        decision.add_alternative(alternative)
        logger.debug(f"Added alternative to decision: {alternative.description}")

    def add_reasoning_step(
        self,
        decision: DecisionPoint,
        step: str,
    ) -> None:
        """
        Add a reasoning step to a decision's reasoning chain.

        Args:
            decision: The decision to add reasoning to
            step: The reasoning step to add
        """
        decision.add_reasoning_step(step)
        logger.debug(f"Added reasoning step: {step}")

    def log_decision(
        self,
        decision: DecisionPoint,
        print_to_console: bool = True,
    ) -> None:
        """
        Log a decision to the TaskLogger.

        This creates a log entry that includes the decision details
        and can be viewed in the UI.

        Args:
            decision: The decision to log
            print_to_console: Whether to print to console (default: True)
        """
        if not self.task_logger:
            logger.warning("No TaskLogger configured, skipping decision log")
            return

        # Format decision summary for log
        summary = (
            f"Decision: {decision.chosen_approach} "
            f"(confidence: {decision.confidence_level})"
        )

        # Format decision detail for expandable view
        detail_parts = [
            f"Type: {decision.decision_type}",
            f"Context: {decision.context}",
            f"Chosen: {decision.chosen_approach}",
            f"Reasoning: {decision.reasoning}",
            f"Confidence: {decision.confidence:.2f} ({decision.confidence_level})",
        ]

        if decision.alternatives:
            detail_parts.append(
                f"\nAlternatives Considered ({len(decision.alternatives)}):"
            )
            for i, alt in enumerate(decision.alternatives, 1):
                detail_parts.append(
                    f"  {i}. {alt.description}\n"
                    f"     Rejected: {alt.rejected_reason}"
                )

        if decision.reasoning_chain:
            detail_parts.append("\nReasoning Chain:")
            for i, step in enumerate(decision.reasoning_chain, 1):
                detail_parts.append(f"  {i}. {step}")

        if decision.impact:
            detail_parts.append(f"\nImpact: {decision.impact}")

        if decision.dependencies:
            detail_parts.append(f"Dependencies: {', '.join(decision.dependencies)}")

        detail = "\n".join(detail_parts)

        # Log with expandable detail
        self.task_logger.log_with_detail(
            content=summary,
            detail=detail,
            phase=LogPhase(decision.phase),
            collapsed=True,
            print_to_console=print_to_console,
        )

        # Save all decisions to file
        self._save_decisions()

    def get_decisions(
        self,
        phase: LogPhase | None = None,
        subtask_id: str | None = None,
        decision_type: DecisionType | None = None,
        min_confidence: float | None = None,
        requires_review: bool | None = None,
    ) -> list[DecisionPoint]:
        """
        Retrieve decisions with optional filtering.

        Args:
            phase: Filter by execution phase (optional)
            subtask_id: Filter by subtask ID (optional)
            decision_type: Filter by decision type (optional)
            min_confidence: Filter by minimum confidence (optional)
            requires_review: Filter by review requirement (optional)

        Returns:
            List of matching DecisionPoint objects
        """
        results = self.decisions.copy()

        if phase is not None:
            results = [d for d in results if d.phase == phase.value]

        if subtask_id is not None:
            results = [d for d in results if d.subtask_id == subtask_id]

        if decision_type is not None:
            dtype = decision_type.value if isinstance(decision_type, DecisionType) else decision_type
            results = [d for d in results if d.decision_type == dtype]

        if min_confidence is not None:
            results = [d for d in results if d.confidence >= min_confidence]

        if requires_review is not None:
            results = [d for d in results if d.requires_review == requires_review]

        return results

    def get_decisions_requiring_review(self) -> list[DecisionPoint]:
        """
        Get all decisions that require human review.

        Returns:
            List of DecisionPoint objects requiring review
        """
        return [d for d in self.decisions if d.requires_review]

    def get_decision_stats(self) -> dict[str, Any]:
        """
        Get statistics about tracked decisions.

        Returns:
            Dictionary with decision statistics
        """
        if not self.decisions:
            return {
                "total": 0,
                "by_type": {},
                "by_phase": {},
                "by_confidence_level": {},
                "avg_confidence": 0.0,
                "requiring_review": 0,
            }

        # Calculate statistics
        by_type: dict[str, int] = {}
        by_phase: dict[str, int] = {}
        by_confidence_level: dict[str, int] = {}
        total_confidence = 0.0

        for decision in self.decisions:
            # Count by type
            by_type[decision.decision_type] = by_type.get(decision.decision_type, 0) + 1

            # Count by phase
            by_phase[decision.phase] = by_phase.get(decision.phase, 0) + 1

            # Count by confidence level
            by_confidence_level[decision.confidence_level] = (
                by_confidence_level.get(decision.confidence_level, 0) + 1
            )

            # Sum confidence
            total_confidence += decision.confidence

        return {
            "total": len(self.decisions),
            "by_type": by_type,
            "by_phase": by_phase,
            "by_confidence_level": by_confidence_level,
            "avg_confidence": total_confidence / len(self.decisions),
            "requiring_review": len(self.get_decisions_requiring_review()),
        }

    def clear(self) -> None:
        """Clear all tracked decisions (useful for testing)."""
        self.decisions = []
        if self.decisions_file.exists():
            self.decisions_file.unlink()
        logger.info("Cleared all decisions")
