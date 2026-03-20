"""
Failure Pattern Extractor
==========================

Analyzes attempt history to extract recurring failure patterns.
Provides insights for intelligent recovery strategy selection.

Identifies patterns like:
- Recurring error types across attempts
- Escalating complexity (multiple failure types)
- Model-specific limitations
- Circular fix attempts
- Recovery strategy effectiveness
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Configuration for pattern extraction
MIN_ATTEMPTS_FOR_PATTERN = 2  # Minimum attempts to consider a pattern valid
PATTERN_WINDOW_SECONDS = 7200  # Time window for pattern analysis (2 hours)
SIMILARITY_THRESHOLD = 0.3  # Jaccard similarity threshold for approach comparison


class PatternType(Enum):
    """Types of failure patterns that can be detected."""

    RECURRING_ERROR = "recurring_error"  # Same error occurs multiple times
    ESCALATING_COMPLEXITY = "escalating_complexity"  # Multiple different failure types
    MODEL_LIMITATION = "model_limitation"  # Pattern suggests model capabilities issue
    CIRCULAR_FIX = "circular_fix"  # Same approach tried repeatedly
    CONTEXT_EXHAUSTION = "context_exhaustion"  # Running out of context repeatedly
    UNKNOWN = "unknown"


@dataclass
class FailurePattern:
    """Represents a detected failure pattern."""

    pattern_type: PatternType  # Type of pattern detected
    description: str  # Human-readable description
    frequency: int  # Number of times this pattern occurred
    confidence: float  # Confidence score 0.0-1.0
    first_seen: str  # ISO timestamp of first occurrence
    last_seen: str  # ISO timestamp of most recent occurrence
    affected_subtasks: list[str] = field(default_factory=list)  # Subtask IDs where pattern appears
    metadata: dict[str, Any] = field(default_factory=dict)  # Additional pattern-specific data


@dataclass
class SubtaskPatternAnalysis:
    """Pattern analysis for a specific subtask."""

    subtask_id: str
    total_attempts: int
    successful_attempts: int
    failed_attempts: int
    dominant_failure_type: str | None
    patterns: list[FailurePattern]
    recovery_recommendations: list[str]
    last_attempt: dict[str, Any] | None
    analysis_timestamp: str


class FailurePatternExtractor:
    """
    Extracts and analyzes failure patterns from attempt history.

    Responsibilities:
    - Load attempt history from memory directory
    - Identify recurring failure patterns
    - Calculate pattern statistics and confidence scores
    - Generate recovery recommendations based on patterns
    - Provide pattern-based insights for recovery strategy selection
    """

    def __init__(self, spec_dir: Path):
        """
        Initialize failure pattern extractor.

        Args:
            spec_dir: Spec directory containing memory/attempt_history.json
        """
        self.spec_dir = spec_dir
        self.memory_dir = spec_dir / "memory"
        self.attempt_history_file = self.memory_dir / "attempt_history.json"

    # ==========================================================================
    # Data Loading
    # ==========================================================================

    def _load_attempt_history(self) -> dict:
        """
        Load attempt history from JSON file.

        Returns:
            Attempt history dict with structure:
            {
                "subtasks": {
                    "subtask-id": {
                        "attempts": [
                            {
                                "session": int,
                                "timestamp": str (ISO),
                                "approach": str,
                                "success": bool,
                                "error": str | None
                            }
                        ],
                        "status": str
                    }
                },
                "stuck_subtasks": [...],
                "metadata": {...}
            }
        """
        try:
            with open(self.attempt_history_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to load attempt history: {e}")
            return {"subtasks": {}, "stuck_subtasks": [], "metadata": {}}

    def _get_subtask_attempts(self, subtask_id: str) -> list[dict[str, Any]]:
        """
        Get all attempts for a specific subtask.

        Args:
            subtask_id: Subtask identifier

        Returns:
            List of attempt dicts
        """
        history = self._load_attempt_history()
        subtask_data = history["subtasks"].get(subtask_id, {})
        return subtask_data.get("attempts", [])

    # ==========================================================================
    # Pattern Extraction - Core Methods
    # ==========================================================================

    def extract_patterns(self, subtask_id: str) -> SubtaskPatternAnalysis:
        """
        Extract failure patterns for a specific subtask.

        Analyzes the attempt history to identify patterns and generate
        recovery recommendations based on past failures.

        Args:
            subtask_id: Subtask identifier

        Returns:
            SubtaskPatternAnalysis with detected patterns and recommendations
        """
        attempts = self._get_subtask_attempts(subtask_id)

        if not attempts:
            return SubtaskPatternAnalysis(
                subtask_id=subtask_id,
                total_attempts=0,
                successful_attempts=0,
                failed_attempts=0,
                dominant_failure_type=None,
                patterns=[],
                recovery_recommendations=["No attempt history available for this subtask"],
                last_attempt=None,
                analysis_timestamp=datetime.now(UTC).isoformat(),
            )

        # Count successes and failures
        successful_count = sum(1 for a in attempts if a.get("success", False))
        failed_count = len(attempts) - successful_count

        # Extract all patterns
        patterns = self._extract_all_patterns(subtask_id, attempts)

        # Determine dominant failure type
        dominant_failure = self._get_dominant_failure_type(attempts)

        # Generate recovery recommendations
        recommendations = self._generate_recovery_recommendations(
            attempts, patterns, dominant_failure
        )

        return SubtaskPatternAnalysis(
            subtask_id=subtask_id,
            total_attempts=len(attempts),
            successful_attempts=successful_count,
            failed_attempts=failed_count,
            dominant_failure_type=dominant_failure,
            patterns=patterns,
            recovery_recommendations=recommendations,
            last_attempt=attempts[-1] if attempts else None,
            analysis_timestamp=datetime.now(UTC).isoformat(),
        )

    def _extract_all_patterns(
        self, subtask_id: str, attempts: list[dict[str, Any]]
    ) -> list[FailurePattern]:
        """
        Extract all detectable patterns from attempt history.

        Args:
            subtask_id: Subtask identifier
            attempts: List of attempt dicts

        Returns:
            List of detected FailurePattern objects
        """
        patterns = []

        if len(attempts) < MIN_ATTEMPTS_FOR_PATTERN:
            logger.debug(
                f"Not enough attempts for pattern detection in {subtask_id}: "
                f"{len(attempts)} < {MIN_ATTEMPTS_FOR_PATTERN}"
            )
            return patterns

        # Check for recurring errors
        recurring_pattern = self._detect_recurring_errors(subtask_id, attempts)
        if recurring_pattern:
            patterns.append(recurring_pattern)

        # Check for escalating complexity
        complexity_pattern = self._detect_escalating_complexity(subtask_id, attempts)
        if complexity_pattern:
            patterns.append(complexity_pattern)

        # Check for circular fixes
        circular_pattern = self._detect_circular_fixes(subtask_id, attempts)
        if circular_pattern:
            patterns.append(circular_pattern)

        # Check for model limitations
        model_pattern = self._detect_model_limitations(subtask_id, attempts)
        if model_pattern:
            patterns.append(model_pattern)

        # Check for context exhaustion
        context_pattern = self._detect_context_exhaustion(subtask_id, attempts)
        if context_pattern:
            patterns.append(context_pattern)

        return patterns

    # ==========================================================================
    # Pattern Detection Methods
    # ==========================================================================

    def _detect_recurring_errors(
        self, subtask_id: str, attempts: list[dict[str, Any]]
    ) -> FailurePattern | None:
        """
        Detect if the same error occurs multiple times.

        Args:
            subtask_id: Subtask identifier
            attempts: List of attempt dicts

        Returns:
            FailurePattern if recurring errors detected, None otherwise
        """
        # Extract all error messages
        errors = [a.get("error") for a in attempts if a.get("error")]

        if len(errors) < MIN_ATTEMPTS_FOR_PATTERN:
            return None

        # Categorize errors by type
        error_categories = [self._categorize_error(e) for e in errors]
        category_counts = Counter(error_categories)

        # Find most common error category
        most_common_category, count = category_counts.most_common(1)[0]

        # Only flag as pattern if it appears in 50%+ of failed attempts
        failed_attempts = len(errors)
        frequency_ratio = count / failed_attempts

        if frequency_ratio >= 0.5 and count >= MIN_ATTEMPTS_FOR_PATTERN:
            # Get timestamps
            failed_attempts_with_errors = [a for a in attempts if a.get("error")]
            first_seen = failed_attempts_with_errors[0].get("timestamp", "")
            last_seen = failed_attempts_with_errors[-1].get("timestamp", "")

            return FailurePattern(
                pattern_type=PatternType.RECURRING_ERROR,
                description=(
                    f"Recurring '{most_common_category}' error: occurred {count} times "
                    f"({frequency_ratio:.1%} of failed attempts)"
                ),
                frequency=count,
                confidence=frequency_ratio,
                first_seen=first_seen,
                last_seen=last_seen,
                affected_subtasks=[subtask_id],
                metadata={
                    "error_category": most_common_category,
                    "total_failed_attempts": failed_attempts,
                    "examples": errors[:3],  # Include first 3 examples
                },
            )

        return None

    def _detect_escalating_complexity(
        self, subtask_id: str, attempts: list[dict[str, Any]]
    ) -> FailurePattern | None:
        """
        Detect if multiple different failure types are occurring.

        This indicates the problem is complex and may require different approaches.

        Args:
            subtask_id: Subtask identifier
            attempts: List of attempt dicts

        Returns:
            FailurePattern if escalating complexity detected, None otherwise
        """
        # Extract all error categories
        errors = [a.get("error") for a in attempts if a.get("error")]

        if len(errors) < 3:
            return None  # Need at least 3 failures to detect complexity

        # Count unique error categories
        error_categories = [self._categorize_error(e) for e in errors]
        unique_categories = set(error_categories)

        # Escalating complexity: 3+ different error types
        if len(unique_categories) >= 3:
            failed_attempts_with_errors = [a for a in attempts if a.get("error")]
            first_seen = failed_attempts_with_errors[0].get("timestamp", "")
            last_seen = failed_attempts_with_errors[-1].get("timestamp", "")

            return FailurePattern(
                pattern_type=PatternType.ESCALATING_COMPLEXITY,
                description=(
                    f"Escalating complexity: {len(unique_categories)} different failure types "
                    f"encountered across {len(errors)} failed attempts"
                ),
                frequency=len(errors),
                confidence=0.8,
                first_seen=first_seen,
                last_seen=last_seen,
                affected_subtasks=[subtask_id],
                metadata={
                    "unique_error_categories": list(unique_categories),
                    "error_distribution": dict(Counter(error_categories)),
                    "total_failed_attempts": len(errors),
                },
            )

        return None

    def _detect_circular_fixes(
        self, subtask_id: str, attempts: list[dict[str, Any]]
    ) -> FailurePattern | None:
        """
        Detect if the same approach is being tried repeatedly.

        Uses Jaccard similarity to compare approach descriptions.

        Args:
            subtask_id: Subtask identifier
            attempts: List of attempt dicts

        Returns:
            FailurePattern if circular fixes detected, None otherwise
        """
        if len(attempts) < 3:
            return None

        # Extract approaches
        approaches = [a.get("approach", "") for a in attempts]

        # Calculate pairwise similarities
        similar_count = 0
        for i in range(len(approaches) - 1):
            similarity = self._calculate_similarity(approaches[i], approaches[i + 1])
            if similarity >= SIMILARITY_THRESHOLD:
                similar_count += 1

        # If 2+ consecutive attempts are similar, flag as circular
        if similar_count >= 2:
            first_seen = attempts[0].get("timestamp", "")
            last_seen = attempts[-1].get("timestamp", "")

            return FailurePattern(
                pattern_type=PatternType.CIRCULAR_FIX,
                description=(
                    f"Circular fix pattern: {similar_count} pairs of similar approaches "
                    f"detected across {len(attempts)} attempts"
                ),
                frequency=similar_count,
                confidence=0.85,
                first_seen=first_seen,
                last_seen=last_seen,
                affected_subtasks=[subtask_id],
                metadata={
                    "similar_pair_count": similar_count,
                    "total_attempts": len(attempts),
                    "approach_examples": approaches[:3],
                },
            )

        return None

    def _detect_model_limitations(
        self, subtask_id: str, attempts: list[dict[str, Any]]
    ) -> FailurePattern | None:
        """
        Detect patterns that suggest model limitations rather than code issues.

        Indicators:
        - Frequent timeout errors
        - Context exhaustion errors
        - Failures in complex logic/implementation tasks

        Args:
            subtask_id: Subtask identifier
            attempts: List of attempt dicts

        Returns:
            FailurePattern if model limitations suspected, None otherwise
        """
        errors = [a.get("error") for a in attempts if a.get("error")]

        if len(errors) < 2:
            return None

        # Check for model-limitation indicators
        timeout_count = sum(1 for e in errors if self._is_timeout_error(e))
        context_count = sum(1 for e in errors if self._is_context_error(e))

        # If timeouts or context issues appear frequently, flag as model limitation
        limitation_count = timeout_count + context_count
        if limitation_count >= 2:
            failed_attempts_with_errors = [a for a in attempts if a.get("error")]
            first_seen = failed_attempts_with_errors[0].get("timestamp", "")
            last_seen = failed_attempts_with_errors[-1].get("timestamp", "")

            limitation_types = []
            if timeout_count > 0:
                limitation_types.append(f"{timeout_count} timeout(s)")
            if context_count > 0:
                limitation_types.append(f"{context_count} context exhaustion")

            return FailurePattern(
                pattern_type=PatternType.MODEL_LIMITATION,
                description=(
                    f"Model limitation suspected: {', '.join(limitation_types)} "
                    f"across {len(errors)} failed attempts"
                ),
                frequency=limitation_count,
                confidence=0.75,
                first_seen=first_seen,
                last_seen=last_seen,
                affected_subtasks=[subtask_id],
                metadata={
                    "timeout_count": timeout_count,
                    "context_exhaustion_count": context_count,
                    "limitation_types": limitation_types,
                    "total_failed_attempts": len(errors),
                },
            )

        return None

    def _detect_context_exhaustion(
        self, subtask_id: str, attempts: list[dict[str, Any]]
    ) -> FailurePattern | None:
        """
        Detect repeated context exhaustion errors.

        Args:
            subtask_id: Subtask identifier
            attempts: List of attempt dicts

        Returns:
            FailurePattern if context exhaustion pattern detected, None otherwise
        """
        errors = [a.get("error") for a in attempts if a.get("error")]

        if len(errors) < 2:
            return None

        # Count context exhaustion errors
        context_errors = [e for e in errors if self._is_context_error(e)]

        if len(context_errors) >= 2:
            failed_attempts_with_errors = [a for a in attempts if a.get("error")]
            first_seen = failed_attempts_with_errors[0].get("timestamp", "")
            last_seen = failed_attempts_with_errors[-1].get("timestamp", "")

            return FailurePattern(
                pattern_type=PatternType.CONTEXT_EXHAUSTION,
                description=(
                    f"Repeated context exhaustion: {len(context_errors)} occurrences "
                    f"across {len(attempts)} attempts"
                ),
                frequency=len(context_errors),
                confidence=0.9,
                first_seen=first_seen,
                last_seen=last_seen,
                affected_subtasks=[subtask_id],
                metadata={
                    "context_exhaustion_count": len(context_errors),
                    "total_failed_attempts": len(errors),
                    "examples": context_errors[:2],
                },
            )

        return None

    # ==========================================================================
    # Helper Methods
    # ==========================================================================

    def _categorize_error(self, error: str) -> str:
        """
        Categorize an error message into a high-level category.

        Args:
            error: Error message string

        Returns:
            Error category string
        """
        error_lower = error.lower()

        # Check for various error patterns
        if any(
            pattern in error_lower
            for pattern in ["syntax", "indentation", "parse", "unexpected token"]
        ):
            return "syntax_error"

        if any(
            pattern in error_lower
            for pattern in ["module not found", "import", "cannot find module"]
        ):
            return "dependency_error"

        if any(
            pattern in error_lower
            for pattern in [
                "compilation error",
                "compile error",
                "type error:",
                "type mismatch",
                "build failed",
            ]
        ):
            return "build_error"

        if any(
            pattern in error_lower
            for pattern in ["test failed", "assertion", "expected", "timeout"]
        ):
            return "test_or_timeout_error"

        if any(
            pattern in error_lower
            for pattern in ["context", "token limit", "maximum length"]
        ):
            return "context_error"

        return "unknown_error"

    def _is_timeout_error(self, error: str) -> bool:
        """Check if error is a timeout error."""
        return any(keyword in error.lower() for keyword in ["timeout", "timed out"])

    def _is_context_error(self, error: str) -> bool:
        """Check if error is a context exhaustion error."""
        return any(
            keyword in error.lower()
            for keyword in ["context", "token limit", "maximum length", "context window"]
        )

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate Jaccard similarity between two texts.

        Jaccard similarity = |intersection| / |union|
        Returns 0.0 - 1.0 where 1.0 is identical.

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Similarity score 0.0 - 1.0
        """
        # Stop words to ignore
        stop_words = {
            "with",
            "using",
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "trying",
            "by",
            "from",
        }

        # Extract keywords
        words1 = set(word for word in text1.lower().split() if word not in stop_words)
        words2 = set(word for word in text2.lower().split() if word not in stop_words)

        # Calculate Jaccard similarity
        if not words1 and not words2:
            return 1.0  # Both empty
        if not words1 or not words2:
            return 0.0  # One empty

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _get_dominant_failure_type(self, attempts: list[dict[str, Any]]) -> str | None:
        """
        Determine the dominant failure type from attempts.

        Args:
            attempts: List of attempt dicts

        Returns:
            Dominant failure type string or None if no failures
        """
        errors = [a.get("error") for a in attempts if a.get("error")]

        if not errors:
            return None

        # Count error categories
        categories = [self._categorize_error(e) for e in errors]
        category_counts = Counter(categories)

        # Return most common category
        return category_counts.most_common(1)[0][0]

    def _generate_recovery_recommendations(
        self,
        attempts: list[dict[str, Any]],
        patterns: list[FailurePattern],
        dominant_failure: str | None,
    ) -> list[str]:
        """
        Generate recovery recommendations based on patterns and failure types.

        Args:
            attempts: List of attempt dicts
            patterns: Detected failure patterns
            dominant_failure: Dominant failure type

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if not attempts:
            return ["No attempt history available"]

        # Add pattern-specific recommendations
        for pattern in patterns:
            if pattern.pattern_type == PatternType.RECURRING_ERROR:
                error_category = pattern.metadata.get("error_category", "unknown")
                recommendations.append(
                    f"⚠️ Recurring '{error_category}' error: consider a different approach"
                )

            elif pattern.pattern_type == PatternType.ESCALATING_COMPLEXITY:
                recommendations.append(
                    "⚠️ Multiple failure types detected: task may be too complex, "
                    "consider breaking into smaller subtasks"
                )

            elif pattern.pattern_type == PatternType.CIRCULAR_FIX:
                recommendations.append(
                    "⚠️ Circular fix detected: similar approaches tried multiple times. "
                    "Try a fundamentally different approach."
                )

            elif pattern.pattern_type == PatternType.MODEL_LIMITATION:
                recommendations.append(
                    "⚠️ Model limitation suspected: try with fallback model or simpler implementation"
                )

            elif pattern.pattern_type == PatternType.CONTEXT_EXHAUSTION:
                recommendations.append(
                    "ℹ️ Context exhaustion pattern detected: consider splitting task or "
                    "continuing in next session"
                )

        # Add failure-type specific recommendations if no patterns found
        if not patterns and dominant_failure:
            if dominant_failure == "syntax_error":
                recommendations.append("Syntax errors recurring: review code structure carefully")
            elif dominant_failure == "dependency_error":
                recommendations.append("Dependency issues: verify all imports and packages")
            elif dominant_failure == "build_error":
                recommendations.append("Build errors: check type definitions and build config")
            elif dominant_failure == "test_or_timeout_error":
                recommendations.append("Test/timeout failures: verify implementation matches requirements")

        # Add general guidance based on attempt count
        failed_count = sum(1 for a in attempts if not a.get("success", False))
        if failed_count >= 3 and not recommendations:
            recommendations.append(
                f"Multiple failures ({failed_count}): consider alternative approach or escalation"
            )

        # Default recommendation if nothing else
        if not recommendations:
            recommendations.append("Proceed with implementation based on requirements")

        return recommendations

    # ==========================================================================
    # Cross-Subtask Analysis
    # ==========================================================================

    def extract_global_patterns(self) -> dict[str, Any]:
        """
        Extract patterns across all subtasks.

        Provides a global view of failure patterns in the current spec.

        Returns:
            Dict with global pattern statistics
        """
        history = self._load_attempt_history()
        subtask_ids = list(history["subtasks"].keys())

        all_patterns = []
        total_attempts = 0
        total_successful = 0
        total_failed = 0

        # Analyze each subtask
        for subtask_id in subtask_ids:
            analysis = self.extract_patterns(subtask_id)
            all_patterns.extend(analysis.patterns)
            total_attempts += analysis.total_attempts
            total_successful += analysis.successful_attempts
            total_failed += analysis.failed_attempts

        # Group patterns by type
        pattern_by_type: dict[PatternType, list[FailurePattern]] = {}
        for pattern in all_patterns:
            if pattern.pattern_type not in pattern_by_type:
                pattern_by_type[pattern.pattern_type] = []
            pattern_by_type[pattern.pattern_type].append(pattern)

        # Build summary
        return {
            "total_subtasks_analyzed": len(subtask_ids),
            "total_attempts": total_attempts,
            "total_successful": total_successful,
            "total_failed": total_failed,
            "total_patterns_detected": len(all_patterns),
            "patterns_by_type": {
                pattern_type.value: len(patterns)
                for pattern_type, patterns in pattern_by_type.items()
            },
            "most_common_pattern": (
                max(pattern_by_type.items(), key=lambda x: len(x[1]))[0].value
                if pattern_by_type
                else None
            ),
            "subtasks_with_circular_fixes": sum(
                1
                for p in all_patterns
                if p.pattern_type == PatternType.CIRCULAR_FIX
            ),
            "subtasks_with_escalating_complexity": sum(
                1
                for p in all_patterns
                if p.pattern_type == PatternType.ESCALATING_COMPLEXITY
            ),
            "analysis_timestamp": datetime.now(UTC).isoformat(),
        }

    # ==========================================================================
    # Utility Methods for Integration
    # ==========================================================================

    def get_subtask_summary(self, subtask_id: str) -> dict[str, Any]:
        """
        Get a quick summary of a subtask's attempt history.

        Args:
            subtask_id: Subtask identifier

        Returns:
            Dict with summary information
        """
        attempts = self._get_subtask_attempts(subtask_id)

        if not attempts:
            return {
                "subtask_id": subtask_id,
                "attempts": 0,
                "status": "no_history",
            }

        successful = sum(1 for a in attempts if a.get("success", False))
        failed = len(attempts) - successful

        return {
            "subtask_id": subtask_id,
            "attempts": len(attempts),
            "successful": successful,
            "failed": failed,
            "status": "completed" if successful > 0 else "failed",
            "last_attempt": attempts[-1].get("timestamp") if attempts else None,
        }
