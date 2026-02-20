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
import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from analysis.metrics_tracker import _load_implementation_plan
from analysis.quality_models import QualityScore, QualityTrend

_logger = logging.getLogger(__name__)

# Configuration
DEFAULT_ALERT_THRESHOLD = 10.0  # Alert at 10% quality drop
MIN_SESSIONS_FOR_BASELINE = 5  # Minimum sessions to establish baseline
TREND_WINDOW_SIZE = 5  # Number of recent sessions to analyze
VALID_AGENT_TYPES = {"planner", "coder", "qa_reviewer", "qa_fixer"}

_quality_history_lock = threading.Lock()


def _extract_subtasks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract subtasks from an already-loaded implementation plan.

    Args:
        plan: Implementation plan dict

    Returns:
        List of all subtasks from all phases
    """
    subtasks = []
    for phase in plan.get("phases", []):
        subtasks.extend(phase.get("subtasks", []))
    return subtasks


def _extract_qa_history(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Extract QA iteration history from an already-loaded plan.

    Args:
        plan: Implementation plan dict

    Returns:
        List of QA iteration records
    """
    return plan.get("qa_iteration_history", [])


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
            if not isinstance(data, dict):
                _logger.warning("Invalid %s format (expected object)", quality_file)
                return []
            scores = data.get("scores", [])
            if not isinstance(scores, list):
                _logger.warning(
                    "Invalid %s format (scores is not a list)", quality_file
                )
                return []
            return scores
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        _logger.warning("Failed to read %s: %s", quality_file, exc)
        return []


def _save_quality_history(spec_dir: Path, scores: list[dict[str, Any]]) -> None:
    """
    Save quality score history atomically to spec directory.

    Uses write-to-temp + os.replace to prevent corruption on crash.

    Args:
        spec_dir: Spec directory path
        scores: List of quality score records to save
    """
    quality_file = spec_dir / "quality_history.json"
    tmp_file = quality_file.with_name(f"{quality_file.name}.tmp")
    spec_dir.mkdir(parents=True, exist_ok=True)

    try:
        payload = {
            "scores": scores,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, quality_file)
    except (OSError, UnicodeEncodeError) as exc:
        _logger.warning("Failed to write %s: %s", quality_file, exc)
        try:
            tmp_file.unlink(missing_ok=True)
        except OSError:
            pass  # Best-effort cleanup of temp file


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

    # Validate agent_type
    if agent_type not in VALID_AGENT_TYPES:
        _logger.warning("Unknown agent_type %r, normalizing", agent_type)
        agent_type = agent_type.lower().strip()
        if agent_type not in VALID_AGENT_TYPES:
            _logger.warning(
                "agent_type %r still invalid after normalization, using 'unknown'",
                agent_type,
            )
            agent_type = "unknown"

    # Load plan once to avoid repeated IO
    plan = _load_implementation_plan(spec_dir)
    subtasks = _extract_subtasks(plan) if plan else []
    qa_history = _extract_qa_history(plan) if plan else []

    # Calculate test pass rate
    test_pass_rate, total_tests, passed_tests = _calculate_test_pass_rate(
        subtasks, subtask_id
    )

    # Calculate acceptance criteria
    criteria_met, total_criteria, met_criteria = _calculate_acceptance_criteria(
        qa_history, iteration
    )

    # Determine user approval
    user_approval_rate, user_approved = _calculate_user_approval(qa_history, iteration)

    # Skip persistence when no meaningful data is available
    has_qa_record = any(r.get("iteration") == iteration for r in qa_history)
    has_meaningful_data = total_tests > 0 or total_criteria > 0 or has_qa_record

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

    # Only persist scores with meaningful data to avoid polluting trends
    if has_meaningful_data:
        _persist_quality_score(spec_dir, score)
    else:
        _logger.debug(
            "Skipping persistence: no test/criteria data for session %s", session_id
        )

    return score


def _calculate_test_pass_rate(
    subtasks: list[dict[str, Any]], subtask_id: str | None
) -> tuple[float, int, int]:
    """
    Calculate test pass rate from subtask verification.

    Args:
        subtasks: List of subtask dicts from the plan
        subtask_id: Optional subtask ID to check

    Returns:
        Tuple of (pass_rate, total_tests, passed_tests)
    """
    if not subtask_id:
        return 0.0, 0, 0

    subtask = next((s for s in subtasks if s.get("id") == subtask_id), None)

    if not subtask:
        return 0.0, 0, 0

    # Check verification status
    verification = subtask.get("verification", {})
    if not verification:
        return 0.0, 0, 0

    # Normalize verification type
    v_type = str(verification.get("type", "")).lower().strip()

    # For command-based verification, assume 1 test
    if v_type == "command":
        status = str(subtask.get("status", "pending")).lower().strip()
        if status == "completed":
            return 1.0, 1, 1
        return 0.0, 1, 0

    # For test-based verification, parse stored test results if available
    if "test" in v_type:
        results = verification.get("results", {})
        total = results.get("total", results.get("total_tests", 0))
        passed = results.get(
            "passed", results.get("passed_tests", results.get("passed_count", 0))
        )
        try:
            total = int(total)
            passed = int(passed)
        except (TypeError, ValueError):
            return 0.0, 0, 0
        if total > 0:
            passed = max(0, min(passed, total))
            return passed / total, total, passed

    # Unknown verification type — treat as "no data"
    return 0.0, 0, 0


def _calculate_acceptance_criteria(
    qa_history: list[dict[str, Any]], iteration: int
) -> tuple[float, int, int]:
    """
    Calculate acceptance criteria met from QA iterations.

    Args:
        qa_history: List of QA iteration records
        iteration: QA iteration number

    Returns:
        Tuple of (criteria_rate, total_criteria, met_criteria)
    """
    if not qa_history:
        return 0.0, 0, 0

    # Find the QA iteration record
    qa_record = next((r for r in qa_history if r.get("iteration") == iteration), None)

    if not qa_record:
        return 0.0, 0, 0

    # Extract and validate criteria information
    try:
        total_criteria = int(qa_record.get("total_criteria", 0))
        met_criteria = int(qa_record.get("met_criteria", 0))
    except (TypeError, ValueError):
        return 0.0, 0, 0

    if total_criteria <= 0:
        return 0.0, 0, 0

    # Clamp met_criteria within valid range
    met_criteria = max(0, min(met_criteria, total_criteria))
    criteria_rate = met_criteria / total_criteria
    return criteria_rate, total_criteria, met_criteria


def _calculate_user_approval(
    qa_history: list[dict[str, Any]], iteration: int
) -> tuple[float, bool]:
    """
    Calculate user approval rate from QA status.

    Args:
        qa_history: List of QA iteration records
        iteration: QA iteration number

    Returns:
        Tuple of (approval_rate, approved_bool)
    """
    if not qa_history:
        return 0.0, False

    # Find the QA iteration record
    qa_record = next((r for r in qa_history if r.get("iteration") == iteration), None)

    if not qa_record:
        return 0.0, False

    # Check approval status (normalize to handle case differences)
    status = str(qa_record.get("status", "pending")).lower().strip()
    approved = status == "approved"

    return 1.0 if approved else 0.0, approved


def _persist_quality_score(spec_dir: Path, score: QualityScore) -> None:
    """
    Persist quality score to history file.

    Uses an in-process lock to guard the read-modify-write cycle.

    Args:
        spec_dir: Spec directory path
        score: QualityScore to persist
    """
    with _quality_history_lock:
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

    # Convert history to QualityScore objects, skipping malformed entries
    scores: list[QualityScore] = []
    for entry in history:
        try:
            scores.append(QualityScore.from_dict(entry))
        except (KeyError, ValueError, TypeError) as exc:
            _logger.warning("Skipping malformed quality score entry: %s", exc)

    if not scores:
        return QualityTrend(
            spec_id=spec_id,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            alert_threshold_percent=alert_threshold,
            minimum_sessions_for_trend=min_sessions,
        )

    # Sort by timestamp to ensure chronological order
    scores.sort(key=lambda s: s.timestamp)

    # Create trend with scores
    period_start = scores[0].timestamp
    period_end = scores[-1].timestamp

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

    scores: list[QualityScore] = []
    for entry in history:
        try:
            scores.append(QualityScore.from_dict(entry))
        except (KeyError, ValueError, TypeError):
            continue

    # Sort by timestamp for consistent trend analysis
    scores.sort(key=lambda s: s.timestamp)

    # Group by agent type
    by_agent_type: dict[str, list[QualityScore]] = {}
    for score in scores:
        if score.agent_type not in by_agent_type:
            by_agent_type[score.agent_type] = []
        by_agent_type[score.agent_type].append(score)

    # Calculate metrics per agent type using QualityTrend
    results = {}
    for agent_type, agent_scores in by_agent_type.items():
        agent_trend = QualityTrend(
            spec_id=spec_dir.name,
            period_start=agent_scores[0].timestamp,
            period_end=agent_scores[-1].timestamp,
            scores=agent_scores,
            minimum_sessions_for_trend=MIN_SESSIONS_FOR_BASELINE,
        )

        if not agent_trend.has_sufficient_data:
            trend = "insufficient_data"
        else:
            trend = agent_trend.trend_direction

        results[agent_type] = {
            "average_quality": round(agent_trend.average_score, 3),
            "session_count": len(agent_scores),
            "trend": trend,
        }

    return results
