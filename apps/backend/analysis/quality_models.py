"""
Quality Metrics Models
======================

Data models for tracking AI output quality across agent sessions.

Provides models for:
- Quality score per session (test pass rate, acceptance criteria, user approval)
- Trend analysis for detecting quality degradation
- Alert thresholds and baseline tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _parse_iso_datetime(raw: str) -> datetime:
    """Parse ISO datetime string, normalizing 'Z' suffix and naive timestamps to UTC."""
    if isinstance(raw, str) and raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class QualityScore:
    """
    Quality metrics for a single agent session.

    Captures key quality indicators based on test pass rate,
    acceptance criteria validation, and user approval.
    """

    session_id: str
    spec_id: str
    agent_type: str  # planner, coder, qa_reviewer, qa_fixer
    timestamp: datetime

    # Quality components (0.0 to 1.0)
    test_pass_rate: float = 0.0
    acceptance_criteria_met: float = 0.0
    user_approval_rate: float = 0.0

    # Session context
    subtask_id: str | None = None
    phase: str | None = None
    iteration: int = 1

    # Metadata
    total_tests: int = 0
    passed_tests: int = 0
    total_criteria: int = 0
    met_criteria: int = 0
    user_approved: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "spec_id": self.spec_id,
            "agent_type": self.agent_type,
            "timestamp": self.timestamp.isoformat(),
            "test_pass_rate": self.test_pass_rate,
            "acceptance_criteria_met": self.acceptance_criteria_met,
            "user_approval_rate": self.user_approval_rate,
            "subtask_id": self.subtask_id,
            "phase": self.phase,
            "iteration": self.iteration,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "total_criteria": self.total_criteria,
            "met_criteria": self.met_criteria,
            "user_approved": self.user_approved,
            "composite_score": self.composite_score,
            "is_high_quality": self.is_high_quality,
            "is_low_quality": self.is_low_quality,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityScore:
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            spec_id=data["spec_id"],
            agent_type=data["agent_type"],
            timestamp=_parse_iso_datetime(data["timestamp"]),
            test_pass_rate=data.get("test_pass_rate", 0.0),
            acceptance_criteria_met=data.get("acceptance_criteria_met", 0.0),
            user_approval_rate=data.get("user_approval_rate", 0.0),
            subtask_id=data.get("subtask_id"),
            phase=data.get("phase"),
            iteration=data.get("iteration", 1),
            total_tests=data.get("total_tests", 0),
            passed_tests=data.get("passed_tests", 0),
            total_criteria=data.get("total_criteria", 0),
            met_criteria=data.get("met_criteria", 0),
            user_approved=data.get("user_approved", False),
        )

    @staticmethod
    def _clamp01(v: float) -> float:
        """Clamp value to [0.0, 1.0]."""
        return max(0.0, min(1.0, v))

    @property
    def composite_score(self) -> float:
        """
        Calculate composite quality score (0.0 to 1.0).

        Weighted average of applicable components:
        - Test pass rate (40%) — only when total_tests > 0
        - Acceptance criteria (40%) — only when total_criteria > 0
        - User approval (20%) — always included

        When a component has no data, its weight is redistributed
        among the remaining components.
        """
        weighted = 0.0
        weight_sum = 0.0

        if self.total_tests > 0:
            weighted += self._clamp01(self.test_pass_rate) * 0.4
            weight_sum += 0.4
        if self.total_criteria > 0:
            weighted += self._clamp01(self.acceptance_criteria_met) * 0.4
            weight_sum += 0.4

        weighted += self._clamp01(self.user_approval_rate) * 0.2
        weight_sum += 0.2

        return weighted / weight_sum if weight_sum else 0.0

    @property
    def is_high_quality(self) -> bool:
        """Check if session meets high quality threshold (>= 0.8)."""
        return self.composite_score >= 0.8

    @property
    def is_low_quality(self) -> bool:
        """Check if session is below quality threshold (< 0.6)."""
        return self.composite_score < 0.6


@dataclass
class QualityTrend:
    """
    Quality trend analysis across multiple sessions.

    Tracks quality degradation patterns and alerts when
    quality drops below acceptable thresholds.
    """

    spec_id: str
    period_start: datetime
    period_end: datetime

    # Scores over time
    scores: list[QualityScore] = field(default_factory=list)

    # Baseline metrics
    baseline_score: float = 0.0
    baseline_calculated: bool = False

    # Trend analysis
    average_score: float = 0.0
    current_score: float = 0.0
    trend_direction: str = "stable"  # improving, stable, degrading
    degradation_detected: bool = False

    # Alert configuration
    alert_threshold_percent: float = 10.0  # Alert at 10% drop
    minimum_sessions_for_trend: int = 5

    def __post_init__(self):
        """Recalculate metrics after initialization."""
        if self.scores:
            self._recalculate_metrics()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "spec_id": self.spec_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "scores": [score.to_dict() for score in self.scores],
            "baseline_score": self.baseline_score,
            "baseline_calculated": self.baseline_calculated,
            "average_score": self.average_score,
            "current_score": self.current_score,
            "trend_direction": self.trend_direction,
            "degradation_detected": self.degradation_detected,
            "alert_threshold_percent": self.alert_threshold_percent,
            "minimum_sessions_for_trend": self.minimum_sessions_for_trend,
            "total_sessions": self.total_sessions,
            "quality_drop_percent": self.quality_drop_percent,
            "should_alert": self.should_alert,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityTrend:
        """Create from dictionary."""
        return cls(
            spec_id=data["spec_id"],
            period_start=_parse_iso_datetime(data["period_start"]),
            period_end=_parse_iso_datetime(data["period_end"]),
            scores=[QualityScore.from_dict(s) for s in data.get("scores", [])],
            baseline_score=data.get("baseline_score", 0.0),
            baseline_calculated=data.get("baseline_calculated", False),
            average_score=data.get("average_score", 0.0),
            current_score=data.get("current_score", 0.0),
            trend_direction=data.get("trend_direction", "stable"),
            degradation_detected=data.get("degradation_detected", False),
            alert_threshold_percent=data.get("alert_threshold_percent", 10.0),
            minimum_sessions_for_trend=data.get("minimum_sessions_for_trend", 5),
        )

    @property
    def total_sessions(self) -> int:
        """Get total number of sessions tracked."""
        return len(self.scores)

    @property
    def has_sufficient_data(self) -> bool:
        """Check if enough sessions exist for trend analysis."""
        return self.total_sessions >= self.minimum_sessions_for_trend

    @property
    def quality_drop_percent(self) -> float:
        """
        Calculate quality drop from baseline (as percentage).

        Returns:
            Positive value if quality dropped, negative if improved.
        """
        if not self.baseline_calculated or self.baseline_score == 0:
            return 0.0
        drop = (self.baseline_score - self.current_score) / self.baseline_score * 100
        return drop

    @property
    def should_alert(self) -> bool:
        """
        Check if quality drop exceeds alert threshold.

        Alerts when:
        - Sufficient data exists (5+ sessions)
        - Quality dropped by alert_threshold_percent or more from baseline
        """
        return (
            self.has_sufficient_data
            and self.baseline_calculated
            and self.quality_drop_percent >= self.alert_threshold_percent
        )

    def add_score(self, score: QualityScore) -> None:
        """Add a new quality score to the trend."""
        self.scores.append(score)
        self.period_end = score.timestamp
        self._recalculate_metrics()

    def _recalculate_metrics(self) -> None:
        """Recalculate trend metrics based on current scores."""
        if not self.scores:
            return

        # Calculate average score
        total = sum(s.composite_score for s in self.scores)
        self.average_score = total / len(self.scores)

        # Update current score (most recent)
        self.current_score = self.scores[-1].composite_score

        # Calculate baseline (average of first N sessions)
        if not self.baseline_calculated and self.has_sufficient_data:
            baseline_window = self.scores[: self.minimum_sessions_for_trend]
            self.baseline_score = sum(s.composite_score for s in baseline_window) / len(
                baseline_window
            )
            self.baseline_calculated = True

        # Determine trend direction
        if self.has_sufficient_data:
            recent_window = min(self.minimum_sessions_for_trend, len(self.scores))
            recent_scores = self.scores[-recent_window:]
            recent_avg = sum(s.composite_score for s in recent_scores) / len(
                recent_scores
            )

            if self.baseline_calculated:
                diff = recent_avg - self.baseline_score
                if diff > 0.05:
                    self.trend_direction = "improving"
                    self.degradation_detected = False
                elif diff < -0.05:
                    self.trend_direction = "degrading"
                    self.degradation_detected = True
                else:
                    self.trend_direction = "stable"
                    self.degradation_detected = False

    def get_scores_by_agent_type(self, agent_type: str) -> list[QualityScore]:
        """Filter scores by agent type."""
        return [s for s in self.scores if s.agent_type == agent_type]

    def get_recent_scores(self, n: int = 10) -> list[QualityScore]:
        """Get the N most recent quality scores."""
        return self.scores[-n:]
