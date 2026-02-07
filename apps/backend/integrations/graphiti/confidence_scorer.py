"""
Confidence Scorer
=================

Tracks pattern usage frequency and calculates confidence scores.
Provides methods to update pattern confidence based on usage patterns,
recency, and team approval status.
"""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

from core.sentry import capture_exception
from debug import debug, debug_detailed, debug_error, debug_success, is_debug_enabled

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Manages pattern confidence scoring based on usage frequency and recency.

    This class provides methods for:
    - Recording pattern usage events
    - Calculating confidence scores based on usage frequency
    - Adjusting confidence based on recency and team approval
    - Providing confidence statistics for patterns
    """

    # Confidence thresholds
    MIN_CONFIDENCE = 0.0
    MAX_CONFIDENCE = 1.0
    INITIAL_CONFIDENCE = 0.7
    TEAM_STANDARD_CONFIDENCE = 1.0
    DEPRECATED_CONFIDENCE = 0.0

    # Scoring parameters
    HIGH_USAGE_THRESHOLD = 10  # Uses needed for high confidence
    MEDIUM_USAGE_THRESHOLD = 5  # Uses needed for medium confidence
    RECENCY_DECAY_DAYS = 30  # Days after which recency starts to decay
    MAX_RECENCY_BOOST = 0.1  # Maximum boost from recent usage

    def __init__(self):
        """Initialize confidence scorer."""
        self._usage_history: dict[str, list[datetime]] = {}
        self._team_standards: set[str] = set()
        self._deprecated_patterns: set[str] = set()

        if is_debug_enabled():
            debug("patterns", "ConfidenceScorer initialized")

    def record_usage(
        self,
        pattern_key: str,
        timestamp: datetime | None = None,
    ) -> None:
        """
        Record a pattern usage event.

        Args:
            pattern_key: Unique identifier for the pattern (e.g., "category:pattern_hash")
            timestamp: When the pattern was used (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now(UTC)

        if pattern_key not in self._usage_history:
            self._usage_history[pattern_key] = []

        self._usage_history[pattern_key].append(timestamp)

        if is_debug_enabled():
            debug_detailed(
                "patterns",
                "Pattern usage recorded",
                pattern_key=pattern_key,
                total_uses=len(self._usage_history[pattern_key]),
            )

    def calculate_confidence(
        self,
        pattern_key: str,
        base_confidence: float | None = None,
        current_time: datetime | None = None,
    ) -> float:
        """
        Calculate confidence score for a pattern based on usage history.

        Confidence is calculated using:
        1. Base confidence (initial or provided value)
        2. Usage frequency multiplier
        3. Recency boost (recent usage increases confidence)
        4. Team standard override (sets to 1.0)
        5. Deprecated override (sets to 0.0)

        Args:
            pattern_key: Unique identifier for the pattern
            base_confidence: Optional base confidence score (defaults to INITIAL_CONFIDENCE)
            current_time: Current time for recency calculations (defaults to now)

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if current_time is None:
            current_time = datetime.now(UTC)

        # Check for overrides
        if pattern_key in self._deprecated_patterns:
            return self.DEPRECATED_CONFIDENCE

        if pattern_key in self._team_standards:
            return self.TEAM_STANDARD_CONFIDENCE

        # Start with base confidence
        if base_confidence is None:
            base_confidence = self.INITIAL_CONFIDENCE
        confidence = max(self.MIN_CONFIDENCE, min(self.MAX_CONFIDENCE, base_confidence))

        # Get usage history
        usage_times = self._usage_history.get(pattern_key, [])
        if not usage_times:
            return confidence

        # Calculate usage frequency multiplier
        usage_count = len(usage_times)
        frequency_multiplier = self._calculate_frequency_multiplier(usage_count)

        # Calculate recency boost
        recency_boost = self._calculate_recency_boost(usage_times, current_time)

        # Apply multipliers and boosts
        confidence = confidence * frequency_multiplier + recency_boost

        # Ensure within bounds
        confidence = max(self.MIN_CONFIDENCE, min(self.MAX_CONFIDENCE, confidence))

        if is_debug_enabled():
            debug_detailed(
                "patterns",
                "Confidence calculated",
                pattern_key=pattern_key,
                base_confidence=round(base_confidence, 3),
                usage_count=usage_count,
                frequency_multiplier=round(frequency_multiplier, 3),
                recency_boost=round(recency_boost, 3),
                final_confidence=round(confidence, 3),
            )

        return confidence

    def mark_as_team_standard(self, pattern_key: str) -> None:
        """
        Mark a pattern as a team standard (sets confidence to 1.0).

        Args:
            pattern_key: Unique identifier for the pattern
        """
        self._team_standards.add(pattern_key)
        # Remove from deprecated if it was there
        self._deprecated_patterns.discard(pattern_key)

        if is_debug_enabled():
            debug_success(
                "patterns",
                "Pattern marked as team standard",
                pattern_key=pattern_key,
            )

    def mark_as_deprecated(self, pattern_key: str) -> None:
        """
        Mark a pattern as deprecated (sets confidence to 0.0).

        Args:
            pattern_key: Unique identifier for the pattern
        """
        self._deprecated_patterns.add(pattern_key)
        # Remove from team standards if it was there
        self._team_standards.discard(pattern_key)

        if is_debug_enabled():
            debug_detailed(
                "patterns",
                "Pattern marked as deprecated",
                pattern_key=pattern_key,
            )

    def get_usage_count(self, pattern_key: str) -> int:
        """
        Get the total usage count for a pattern.

        Args:
            pattern_key: Unique identifier for the pattern

        Returns:
            Number of times the pattern has been used
        """
        return len(self._usage_history.get(pattern_key, []))

    def get_recent_usage_count(
        self,
        pattern_key: str,
        days: int = 30,
        current_time: datetime | None = None,
    ) -> int:
        """
        Get the usage count for a pattern within a time window.

        Args:
            pattern_key: Unique identifier for the pattern
            days: Number of days to look back
            current_time: Current time for calculations (defaults to now)

        Returns:
            Number of uses within the time window
        """
        if current_time is None:
            current_time = datetime.now(UTC)

        cutoff_time = current_time - timedelta(days=days)
        usage_times = self._usage_history.get(pattern_key, [])

        recent_count = sum(1 for t in usage_times if t >= cutoff_time)
        return recent_count

    def get_confidence_statistics(
        self,
        pattern_key: str,
        base_confidence: float | None = None,
    ) -> dict[str, Any]:
        """
        Get detailed confidence statistics for a pattern.

        Args:
            pattern_key: Unique identifier for the pattern
            base_confidence: Optional base confidence score

        Returns:
            Dictionary with confidence statistics:
            {
                "confidence": 0.85,
                "usage_count": 12,
                "recent_usage_30d": 8,
                "first_used": "2026-01-15T10:30:00Z",
                "last_used": "2026-02-07T14:45:00Z",
                "is_team_standard": False,
                "is_deprecated": False,
                "confidence_level": "high"  # "low", "medium", "high"
            }
        """
        usage_times = self._usage_history.get(pattern_key, [])
        confidence = self.calculate_confidence(pattern_key, base_confidence)

        stats = {
            "confidence": round(confidence, 3),
            "usage_count": len(usage_times),
            "recent_usage_30d": self.get_recent_usage_count(pattern_key, days=30),
            "first_used": usage_times[0].isoformat() if usage_times else None,
            "last_used": usage_times[-1].isoformat() if usage_times else None,
            "is_team_standard": pattern_key in self._team_standards,
            "is_deprecated": pattern_key in self._deprecated_patterns,
            "confidence_level": self._get_confidence_level(confidence),
        }

        return stats

    def _calculate_frequency_multiplier(self, usage_count: int) -> float:
        """
        Calculate a multiplier based on usage frequency.

        Uses a logarithmic scale to reward frequent usage while preventing
        runaway confidence scores.

        Args:
            usage_count: Number of times the pattern has been used

        Returns:
            Multiplier between 1.0 and ~1.4
        """
        if usage_count < 1:
            return 1.0

        # Use logarithmic scale for diminishing returns
        # 1 use: 1.0x, 5 uses: 1.16x, 10 uses: 1.26x, 20 uses: 1.35x
        multiplier = 1.0 + (math.log10(usage_count + 1) * 0.3)

        # Cap at reasonable maximum
        return min(multiplier, 1.4)

    def _calculate_recency_boost(
        self,
        usage_times: list[datetime],
        current_time: datetime,
    ) -> float:
        """
        Calculate a boost based on recent usage patterns.

        Recent usage indicates the pattern is currently relevant and active.

        Args:
            usage_times: List of usage timestamps
            current_time: Current time for calculations

        Returns:
            Boost value between 0.0 and MAX_RECENCY_BOOST
        """
        if not usage_times:
            return 0.0

        # Get most recent usage
        last_used = max(usage_times)
        days_since_use = (current_time - last_used).days

        # No boost if not used recently
        if days_since_use > self.RECENCY_DECAY_DAYS:
            return 0.0

        # Linear decay from MAX_RECENCY_BOOST to 0
        # 0 days: full boost, 30 days: no boost
        decay_factor = 1.0 - (days_since_use / self.RECENCY_DECAY_DAYS)
        boost = self.MAX_RECENCY_BOOST * decay_factor

        return max(0.0, boost)

    def _get_confidence_level(self, confidence: float) -> str:
        """
        Convert numeric confidence to a level string.

        Args:
            confidence: Confidence score (0.0 to 1.0)

        Returns:
            "low", "medium", or "high"
        """
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.6:
            return "medium"
        else:
            return "low"

    def clear_history(self) -> None:
        """Clear all usage history and pattern status (for testing)."""
        self._usage_history.clear()
        self._team_standards.clear()
        self._deprecated_patterns.clear()

        if is_debug_enabled():
            debug("patterns", "Confidence scorer history cleared")


def create_pattern_key(pattern: str, category: str) -> str:
    """
    Create a unique key for a pattern.

    Args:
        pattern: Pattern description
        category: Pattern category

    Returns:
        Unique pattern key in format "category:pattern_hash"
    """
    import hashlib

    pattern_hash = hashlib.md5(
        f"{pattern}:{category}".encode(), usedforsecurity=False
    ).hexdigest()[:8]

    return f"{category}:{pattern_hash}"
