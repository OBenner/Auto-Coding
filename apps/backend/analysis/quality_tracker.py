"""
Quality Tracker
===============

Calculates quality scores for AI agent sessions based on test pass rates,
acceptance criteria validation, and user approval.

Provides functionality for:
- Quality score calculation per session
- Trend analysis across sessions
- Baseline establishment and degradation detection
- Alert triggering on quality drops
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from analysis.quality_models import QualityScore, QualityTrend

# Configuration
DEFAULT_ALERT_THRESHOLD = 10.0  # Alert at 10% quality drop
MIN_SESSIONS_FOR_BASELINE = 5  # Minimum sessions to establish baseline
TREND_WINDOW_SIZE = 5  # Number of recent sessions to analyze


# =============================================================================
# DATA LOADING
# =============================================================================


def _load_implementation_plan(spec_dir: Path) -> dict[str, Any] | None:
    """
    Load implementation plan from spec directory.

    Args:
        spec_dir: Spec directory path

    Returns:
        Implementation plan dict or None if not found
    """
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return None

    try:
        with open(plan_file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _load_qa_iteration_history(spec_dir: Path) -> list[dict[str, Any]]:
    """
    Load QA iteration history from implementation plan.

    Args:
        spec_dir: Spec directory path

    Returns:
        List of QA iteration records
    """
    plan = _load_implementation_plan(spec_dir)
    if not plan:
        return []
    return plan.get("qa_iteration_history", [])


def _load_subtasks(spec_dir: Path) -> list[dict[str, Any]]:
    """
    Load subtasks from implementation plan.

    Args:
        spec_dir: Spec directory path

    Returns:
        List of all subtasks from all phases
    """
    plan = _load_implementation_plan(spec_dir)
    if not plan:
        return []

    subtasks = []
    for phase in plan.get("phases", []):
        subtasks.extend(phase.get("subtasks", []))
    return subtasks


def _load_quality_history(spec_dir: Path) -> list[dict[str, Any]]:
    """
    Load quality score history from spec directory.

    Args:
        spec_dir: Spec directory path

    Returns:
        List of quality score records
    """
    quality_file = spec_dir / "quality_history.json"
    if not quality_file.exists():
        return []

    try:
        with open(quality_file, encoding="utf-8") as f:
            data = json.load(f)
            return data.get("scores", [])
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []


def _save_quality_history(spec_dir: Path, scores: list[dict[str, Any]]) -> None:
    """
    Save quality score history to spec directory.

    Args:
        spec_dir: Spec directory path
        scores: List of quality score records to save
    """
    quality_file = spec_dir / "quality_history.json"
    spec_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(quality_file, "w", encoding="utf-8") as f:
            json.dump(
                {"scores": scores, "updated_at": datetime.now(UTC).isoformat()},
                f,
                indent=2,
            )
    except (OSError, UnicodeEncodeError):
        pass


# =============================================================================
# QUALITY SCORE CALCULATION
# =============================================================================


def calculate_quality_score(
    spec_dir: Path,
    session_id: str,
    agent_type: str,
    subtask_id: str | None = None,
    phase: str | None = None,
    iteration: int = 1,
) -> QualityScore:
    """
    Calculate quality score for an agent session.

    Quality is based on:
    - Test pass rate (40%): Percentage of tests passing
    - Acceptance criteria (40%): Percentage of criteria met
    - User approval (20%): Whether user approved the output

    Args:
        spec_dir: Spec directory path
        session_id: Unique session identifier
        agent_type: Type of agent (planner, coder, qa_reviewer, qa_fixer)
        subtask_id: Optional subtask ID being worked on
        phase: Optional phase name
        iteration: Iteration number (for QA cycles)

    Returns:
        QualityScore object with calculated metrics
    """
    spec_id = spec_dir.name

    # Calculate test pass rate
    test_pass_rate, total_tests, passed_tests = _calculate_test_pass_rate(
        spec_dir, subtask_id
    )

    # Calculate acceptance criteria
    criteria_met, total_criteria, met_criteria = _calculate_acceptance_criteria(
        spec_dir, iteration
    )

    # Determine user approval
    user_approval_rate, user_approved = _calculate_user_approval(spec_dir, iteration)

    # Create quality score
    score = QualityScore(
        session_id=session_id,
        spec_id=spec_id,
        agent_type=agent_type,
        timestamp=datetime.now(UTC),
        test_pass_rate=test_pass_rate,
        acceptance_criteria_met=criteria_met,
        user_approval_rate=user_approval_rate,
        subtask_id=subtask_id,
        phase=phase,
        iteration=iteration,
        total_tests=total_tests,
        passed_tests=passed_tests,
        total_criteria=total_criteria,
        met_criteria=met_criteria,
        user_approved=user_approved,
    )

    # Persist to history
    _persist_quality_score(spec_dir, score)

    return score


def _calculate_test_pass_rate(
    spec_dir: Path, subtask_id: str | None
) -> tuple[float, int, int]:
    """
    Calculate test pass rate from subtask verification.

    Args:
        spec_dir: Spec directory path
        subtask_id: Optional subtask ID to check

    Returns:
        Tuple of (pass_rate, total_tests, passed_tests)
    """
    if not subtask_id:
        return 0.0, 0, 0

    subtasks = _load_subtasks(spec_dir)
    subtask = next((s for s in subtasks if s.get("id") == subtask_id), None)

    if not subtask:
        return 0.0, 0, 0

    # Check verification status
    verification = subtask.get("verification", {})
    if not verification:
        return 0.0, 0, 0

    # For command-based verification, assume 1 test
    if verification.get("type") == "command":
        status = subtask.get("status", "pending")
        if status == "completed":
            return 1.0, 1, 1
        return 0.0, 1, 0

    # For test-based verification, parse test results
    # This would be enhanced with actual test result parsing
    return 0.0, 0, 0


def _calculate_acceptance_criteria(
    spec_dir: Path, iteration: int
) -> tuple[float, int, int]:
    """
    Calculate acceptance criteria met from QA iterations.

    Args:
        spec_dir: Spec directory path
        iteration: QA iteration number

    Returns:
        Tuple of (criteria_rate, total_criteria, met_criteria)
    """
    qa_history = _load_qa_iteration_history(spec_dir)
    if not qa_history:
        return 0.0, 0, 0

    # Find the QA iteration record
    qa_record = next(
        (r for r in qa_history if r.get("iteration") == iteration), None
    )

    if not qa_record:
        return 0.0, 0, 0

    # Extract criteria information
    total_criteria = qa_record.get("total_criteria", 0)
    met_criteria = qa_record.get("met_criteria", 0)

    if total_criteria == 0:
        return 0.0, 0, 0

    criteria_rate = met_criteria / total_criteria
    return criteria_rate, total_criteria, met_criteria


def _calculate_user_approval(spec_dir: Path, iteration: int) -> tuple[float, bool]:
    """
    Calculate user approval rate from QA status.

    Args:
        spec_dir: Spec directory path
        iteration: QA iteration number

    Returns:
        Tuple of (approval_rate, approved_bool)
    """
    qa_history = _load_qa_iteration_history(spec_dir)
    if not qa_history:
        return 0.0, False

    # Find the QA iteration record
    qa_record = next(
        (r for r in qa_history if r.get("iteration") == iteration), None
    )

    if not qa_record:
        return 0.0, False

    # Check approval status
    status = qa_record.get("status", "pending")
    approved = status == "approved"

    return 1.0 if approved else 0.0, approved


def _persist_quality_score(spec_dir: Path, score: QualityScore) -> None:
    """
    Persist quality score to history file.

    Args:
        spec_dir: Spec directory path
        score: QualityScore to persist
    """
    history = _load_quality_history(spec_dir)
    history.append(score.to_dict())
    _save_quality_history(spec_dir, history)


# =============================================================================
# TREND ANALYSIS
# =============================================================================


def analyze_quality_trend(
    spec_dir: Path,
    alert_threshold: float = DEFAULT_ALERT_THRESHOLD,
    min_sessions: int = MIN_SESSIONS_FOR_BASELINE,
) -> QualityTrend:
    """
    Analyze quality trend across sessions.

    Args:
        spec_dir: Spec directory path
        alert_threshold: Quality drop percentage to trigger alert
        min_sessions: Minimum sessions required for baseline

    Returns:
        QualityTrend object with analysis results
    """
    spec_id = spec_dir.name
    history = _load_quality_history(spec_dir)

    if not history:
        # Return empty trend
        return QualityTrend(
            spec_id=spec_id,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            alert_threshold_percent=alert_threshold,
            minimum_sessions_for_trend=min_sessions,
        )

    # Convert history to QualityScore objects
    scores = [QualityScore.from_dict(s) for s in history]

    # Create trend with scores
    period_start = scores[0].timestamp if scores else datetime.now(UTC)
    period_end = scores[-1].timestamp if scores else datetime.now(UTC)

    trend = QualityTrend(
        spec_id=spec_id,
        period_start=period_start,
        period_end=period_end,
        scores=scores,
        alert_threshold_percent=alert_threshold,
        minimum_sessions_for_trend=min_sessions,
    )

    return trend


def get_quality_summary(spec_dir: Path) -> dict[str, Any]:
    """
    Get quality summary metrics for a spec.

    Args:
        spec_dir: Spec directory path

    Returns:
        Dict with summary metrics:
        {
            "total_sessions": int,
            "average_quality": float,
            "current_quality": float,
            "baseline_quality": float,
            "trend_direction": str,
            "quality_drop_percent": float,
            "alert_active": bool,
            "high_quality_sessions": int,
            "low_quality_sessions": int,
        }
    """
    trend = analyze_quality_trend(spec_dir)

    high_quality_count = sum(1 for s in trend.scores if s.is_high_quality)
    low_quality_count = sum(1 for s in trend.scores if s.is_low_quality)

    return {
        "total_sessions": trend.total_sessions,
        "average_quality": round(trend.average_score, 3),
        "current_quality": round(trend.current_score, 3),
        "baseline_quality": round(trend.baseline_score, 3),
        "trend_direction": trend.trend_direction,
        "quality_drop_percent": round(trend.quality_drop_percent, 2),
        "alert_active": trend.should_alert,
        "high_quality_sessions": high_quality_count,
        "low_quality_sessions": low_quality_count,
    }


def get_quality_by_agent_type(spec_dir: Path) -> dict[str, dict[str, Any]]:
    """
    Get quality metrics grouped by agent type.

    Args:
        spec_dir: Spec directory path

    Returns:
        Dict mapping agent_type to quality metrics:
        {
            "coder": {
                "average_quality": float,
                "session_count": int,
                "trend": str,
            },
            ...
        }
    """
    history = _load_quality_history(spec_dir)
    if not history:
        return {}

    scores = [QualityScore.from_dict(s) for s in history]

    # Group by agent type
    by_agent_type: dict[str, list[QualityScore]] = {}
    for score in scores:
        if score.agent_type not in by_agent_type:
            by_agent_type[score.agent_type] = []
        by_agent_type[score.agent_type].append(score)

    # Calculate metrics per agent type
    results = {}
    for agent_type, agent_scores in by_agent_type.items():
        avg_quality = sum(s.composite_score for s in agent_scores) / len(agent_scores)

        # Simple trend: compare recent vs older
        if len(agent_scores) >= MIN_SESSIONS_FOR_BASELINE:
            recent = agent_scores[-TREND_WINDOW_SIZE:]
            recent_avg = sum(s.composite_score for s in recent) / len(recent)

            baseline = agent_scores[:MIN_SESSIONS_FOR_BASELINE]
            baseline_avg = sum(s.composite_score for s in baseline) / len(baseline)

            if recent_avg > baseline_avg + 0.05:
                trend = "improving"
            elif recent_avg < baseline_avg - 0.05:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        results[agent_type] = {
            "average_quality": round(avg_quality, 3),
            "session_count": len(agent_scores),
            "trend": trend,
        }

    return results
