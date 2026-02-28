"""
Metrics Tracker
===============

Tracks success rates, improvement trends, and learning effectiveness
for the failure analysis and correction system.

Provides analytics on:
- QA iteration success rates
- Root cause identification effectiveness
- User correction tracking
- Improvement trends over time
- Failure pattern tracking and analysis
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Configuration
TREND_WINDOW_SIZE = 10  # Number of recent iterations to analyze for trends
MIN_SAMPLES_FOR_TREND = 3  # Minimum iterations needed to calculate trends

_EMPTY_FAILURE_METRICS: dict[str, Any] = {
    "total_failures": 0,
    "failure_types": {},
    "failure_categories": {},
    "root_causes_identified": 0,
    "root_cause_rate": 0.0,
    "recurring_failures": 0,
    "recurrence_rate": 0.0,
    "top_failure_files": [],
    "top_failure_categories": [],
    "pattern_detection_rate": 0.0,
    "avg_occurrences_per_failure": 0.0,
}


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


def _load_learning_metrics(spec_dir: Path) -> dict[str, Any]:
    """
    Load learning metrics from implementation plan.

    Args:
        spec_dir: Spec directory path

    Returns:
        Learning metrics dict (may be empty)
    """
    plan = _load_implementation_plan(spec_dir)
    if not plan:
        return {}
    return plan.get("learning_metrics", {})


# =============================================================================
# SUCCESS RATE CALCULATION
# =============================================================================


def get_success_rate(spec_dir: Path, window_size: int | None = None) -> dict[str, Any]:
    """
    Calculate success rate metrics for QA iterations.

    Args:
        spec_dir: Spec directory path
        window_size: Optional window size for recent success rate (defaults to all)

    Returns:
        Dict with success rate metrics:
        {
            "overall_success_rate": float,  # 0.0 - 1.0
            "recent_success_rate": float,   # Success rate in recent window
            "first_attempt_success_rate": float,  # Success on first try
            "total_iterations": int,
            "approved_iterations": int,
            "rejected_iterations": int,
            "error_iterations": int,
            "average_iterations_to_success": float,
        }
    """
    history = _load_qa_iteration_history(spec_dir)

    if not history:
        return {
            "overall_success_rate": 0.0,
            "recent_success_rate": 0.0,
            "first_attempt_success_rate": 0.0,
            "total_iterations": 0,
            "approved_iterations": 0,
            "rejected_iterations": 0,
            "error_iterations": 0,
            "average_iterations_to_success": 0.0,
        }

    # Count iteration outcomes
    approved = sum(1 for r in history if r.get("status") == "approved")
    rejected = sum(1 for r in history if r.get("status") == "rejected")
    errors = sum(1 for r in history if r.get("status") == "error")
    total = len(history)

    # Overall success rate
    overall_rate = approved / total if total > 0 else 0.0

    # Recent success rate (window_size most recent iterations)
    if window_size is None:
        window_size = total
    recent_history = history[-window_size:] if len(history) > window_size else history
    recent_approved = sum(1 for r in recent_history if r.get("status") == "approved")
    recent_rate = recent_approved / len(recent_history) if recent_history else 0.0

    # First attempt success (iteration 1 approved)
    first_attempt_success = any(
        r.get("iteration") == 1 and r.get("status") == "approved" for r in history
    )
    first_attempt_rate = 1.0 if first_attempt_success else 0.0

    # Average iterations to success
    # Find the iteration number where approval happened
    approval_iteration = None
    for record in history:
        if record.get("status") == "approved":
            approval_iteration = record.get("iteration", 1)
            break

    avg_iterations = float(approval_iteration) if approval_iteration else float(total)

    return {
        "overall_success_rate": round(overall_rate, 3),
        "recent_success_rate": round(recent_rate, 3),
        "first_attempt_success_rate": round(first_attempt_rate, 3),
        "total_iterations": total,
        "approved_iterations": approved,
        "rejected_iterations": rejected,
        "error_iterations": errors,
        "average_iterations_to_success": round(avg_iterations, 1),
    }


# =============================================================================
# FAILURE PATTERN TRACKING
# =============================================================================


def get_failure_metrics(spec_dir: Path) -> dict[str, Any]:
    """
    Track failure patterns and analysis effectiveness.

    Analyzes:
    - Failure types and categories
    - Root cause identification rate
    - Failure recurrence patterns
    - Most problematic files/areas
    - Pattern detection effectiveness

    Args:
        spec_dir: Spec directory path

    Returns:
        Dict with failure metrics:
        {
            "total_failures": int,
            "failure_types": dict[str, int],  # Count by type (qa_rejection, build_error, etc.)
            "failure_categories": dict[str, int],  # Count by category
            "root_causes_identified": int,
            "root_cause_rate": float,  # 0.0 - 1.0
            "recurring_failures": int,
            "recurrence_rate": float,  # 0.0 - 1.0
            "top_failure_files": list[dict[str, Any]],  # Top 5 files with most issues
            "top_failure_categories": list[dict[str, Any]],  # Top 5 categories
            "pattern_detection_rate": float,  # Issues with detected patterns / total
            "avg_occurrences_per_failure": float,
        }
    """
    history = _load_qa_iteration_history(spec_dir)
    metrics = _load_learning_metrics(spec_dir) or {}

    if not history:
        return dict(_EMPTY_FAILURE_METRICS)

    # Collect all issues across all iterations
    all_issues: list[dict[str, Any]] = []
    for record in history:
        all_issues.extend(record.get("issues", []))

    total_failures = len(all_issues)
    if total_failures == 0:
        return dict(_EMPTY_FAILURE_METRICS)

    # Count failure types
    failure_types: Counter[str] = Counter()
    for record in history:
        failure_type = record.get("failure_type", "unknown")
        issue_count = len(record.get("issues", []))
        if issue_count > 0:
            failure_types[failure_type] += issue_count

    # Count failure categories
    failure_categories: Counter[str] = Counter()
    for issue in all_issues:
        category = issue.get("category", "unknown")
        failure_categories[category] += 1

    # Count root causes identified
    root_causes_count = metrics.get("root_causes_identified", 0)
    root_cause_rate = root_causes_count / total_failures if total_failures > 0 else 0.0

    # Count recurring failures (occurrence_count > 1)
    recurring_failures = sum(
        1 for issue in all_issues if issue.get("occurrence_count", 1) > 1
    )
    recurrence_rate = recurring_failures / total_failures if total_failures > 0 else 0.0

    # Count issues by file
    file_counts: Counter[str] = Counter()
    for issue in all_issues:
        if file := issue.get("file"):
            file_counts[file] += 1

    # Get top 5 files with most issues
    top_failure_files = [
        {"file": file, "count": count} for file, count in file_counts.most_common(5)
    ]

    # Get top 5 categories
    top_failure_categories = [
        {"category": category, "count": count}
        for category, count in failure_categories.most_common(5)
    ]

    # Calculate pattern detection rate
    # (issues with root_cause or suggested_fix / total)
    issues_with_patterns = sum(
        1
        for issue in all_issues
        if issue.get("root_cause") or issue.get("suggested_fix")
    )
    pattern_detection_rate = (
        issues_with_patterns / total_failures if total_failures > 0 else 0.0
    )

    # Calculate average occurrences per failure
    total_occurrences = sum(issue.get("occurrence_count", 1) for issue in all_issues)
    avg_occurrences = total_occurrences / total_failures if total_failures > 0 else 0.0

    return {
        "total_failures": total_failures,
        "failure_types": dict(failure_types),
        "failure_categories": dict(failure_categories),
        "root_causes_identified": root_causes_count,
        "root_cause_rate": round(root_cause_rate, 3),
        "recurring_failures": recurring_failures,
        "recurrence_rate": round(recurrence_rate, 3),
        "top_failure_files": top_failure_files,
        "top_failure_categories": top_failure_categories,
        "pattern_detection_rate": round(pattern_detection_rate, 3),
        "avg_occurrences_per_failure": round(avg_occurrences, 2),
    }


# =============================================================================
# IMPROVEMENT TRENDS
# =============================================================================


def get_improvement_trends(spec_dir: Path) -> dict[str, Any]:
    """
    Analyze improvement trends over time.

    Tracks:
    - Success rate trend (improving/stable/declining)
    - Recurring issue reduction
    - Fix effectiveness improvement
    - Root cause identification rate

    Args:
        spec_dir: Spec directory path

    Returns:
        Dict with trend analysis:
        {
            "trend": str,  # "improving", "stable", "declining", "insufficient_data"
            "success_rate_trend": float,  # Positive = improving
            "recurring_issues_trend": str,  # "reducing", "stable", "increasing"
            "root_causes_identified": int,
            "user_corrections_applied": int,
            "pattern_effectiveness": float,
            "recommendations": list[str],
        }
    """
    history = _load_qa_iteration_history(spec_dir)
    metrics = _load_learning_metrics(spec_dir)

    if len(history) < MIN_SAMPLES_FOR_TREND:
        return {
            "trend": "insufficient_data",
            "success_rate_trend": 0.0,
            "recurring_issues_trend": "unknown",
            "root_causes_identified": 0,
            "user_corrections_applied": 0,
            "pattern_effectiveness": 0.0,
            "recommendations": [
                "Need at least 3 QA iterations to calculate trends",
                "Continue building to collect more data",
            ],
        }

    # Calculate success rate trend (compare first half vs second half)
    midpoint = len(history) // 2
    first_half = history[:midpoint]
    second_half = history[midpoint:]

    first_half_success = (
        sum(1 for r in first_half if r.get("status") == "approved") / len(first_half)
        if first_half
        else 0.0
    )
    second_half_success = (
        sum(1 for r in second_half if r.get("status") == "approved") / len(second_half)
        if second_half
        else 0.0
    )

    success_trend = second_half_success - first_half_success

    # Determine overall trend
    if success_trend > 0.1:
        trend = "improving"
    elif success_trend < -0.1:
        trend = "declining"
    else:
        trend = "stable"

    # Analyze recurring issues trend
    recurring_trend = _analyze_recurring_issues_trend(history)

    # Get learning metrics
    root_causes_count = metrics.get("root_causes_identified", 0)
    user_corrections_count = metrics.get("user_corrections_applied", 0)

    # Calculate pattern effectiveness
    # (percentage of issues resolved without becoming recurring)
    total_issues = sum(len(r.get("issues", [])) for r in history)
    recurring_issues = _count_recurring_issues(history)
    pattern_effectiveness = (
        (total_issues - recurring_issues) / total_issues if total_issues > 0 else 1.0
    )

    # Generate recommendations
    recommendations = _generate_recommendations(
        trend, success_trend, recurring_trend, root_causes_count, user_corrections_count
    )

    return {
        "trend": trend,
        "success_rate_trend": round(success_trend, 3),
        "recurring_issues_trend": recurring_trend,
        "root_causes_identified": root_causes_count,
        "user_corrections_applied": user_corrections_count,
        "pattern_effectiveness": round(pattern_effectiveness, 3),
        "recommendations": recommendations,
    }


def _analyze_recurring_issues_trend(history: list[dict[str, Any]]) -> str:
    """
    Analyze trend in recurring issues.

    Args:
        history: QA iteration history

    Returns:
        "reducing", "stable", or "increasing"
    """
    if len(history) < 2:
        return "stable"

    # Count issues with occurrence_count > 1 in each half
    midpoint = len(history) // 2
    first_half = history[:midpoint]
    second_half = history[midpoint:]

    def count_recurring(records: list[dict[str, Any]]) -> int:
        count = 0
        for record in records:
            for issue in record.get("issues", []):
                if issue.get("occurrence_count", 1) > 1:
                    count += 1
        return count

    first_half_recurring = count_recurring(first_half)
    second_half_recurring = count_recurring(second_half)

    # Normalize by number of records
    first_rate = first_half_recurring / len(first_half) if first_half else 0.0
    second_rate = second_half_recurring / len(second_half) if second_half else 0.0

    if second_rate < first_rate - 0.5:
        return "reducing"
    elif second_rate > first_rate + 0.5:
        return "increasing"
    else:
        return "stable"


def _count_recurring_issues(history: list[dict[str, Any]]) -> int:
    """
    Count total recurring issues across all iterations.

    Args:
        history: QA iteration history

    Returns:
        Count of recurring issues
    """
    recurring_count = 0
    for record in history:
        for issue in record.get("issues", []):
            if issue.get("occurrence_count", 1) > 1:
                recurring_count += 1
    return recurring_count


def _generate_recommendations(
    trend: str,
    success_trend: float,
    recurring_trend: str,
    root_causes_count: int,
    user_corrections_count: int,
) -> list[str]:
    """
    Generate actionable recommendations based on metrics.

    Args:
        trend: Overall trend direction
        success_trend: Success rate change
        recurring_trend: Recurring issues trend
        root_causes_count: Number of root causes identified
        user_corrections_count: Number of user corrections

    Returns:
        List of recommendation strings
    """
    recommendations = []

    # Overall trend recommendations
    if trend == "declining":
        recommendations.append(
            "⚠️ Success rate is declining - review recent failures for patterns"
        )
        recommendations.append("Consider reviewing specification clarity")
    elif trend == "improving":
        recommendations.append("✅ Success rate is improving - keep up the good work!")
    else:
        recommendations.append("Success rate is stable")

    # Recurring issues recommendations
    if recurring_trend == "increasing":
        recommendations.append(
            "⚠️ Recurring issues are increasing - investigate root causes"
        )
        recommendations.append(
            "Review failure patterns and update learned patterns in Graphiti"
        )
    elif recurring_trend == "reducing":
        recommendations.append(
            "✅ Recurring issues are reducing - learning is working!"
        )

    # Root cause tracking recommendations
    if root_causes_count == 0:
        recommendations.append(
            "No root causes identified yet - failure analysis will help with this"
        )
    else:
        recommendations.append(
            f"Root causes identified: {root_causes_count} - review for patterns"
        )

    # User correction recommendations
    if user_corrections_count > 0:
        recommendations.append(
            f"User corrections applied: {user_corrections_count} - valuable training data"
        )
    else:
        recommendations.append(
            "No user corrections yet - manual edits will improve future sessions"
        )

    return recommendations


# =============================================================================
# DETAILED METRICS
# =============================================================================


def get_detailed_metrics(spec_dir: Path) -> dict[str, Any]:
    """
    Get comprehensive metrics for the spec.

    Combines success rates, trends, failure patterns, and learning metrics
    into a single report.

    Args:
        spec_dir: Spec directory path

    Returns:
        Dict with complete metrics overview
    """
    success_metrics = get_success_rate(spec_dir)
    trend_metrics = get_improvement_trends(spec_dir)
    failure_metrics = get_failure_metrics(spec_dir)
    learning_metrics = _load_learning_metrics(spec_dir)

    # Get issue breakdown
    history = _load_qa_iteration_history(spec_dir)
    issue_breakdown = _get_issue_breakdown(history)

    return {
        "success_metrics": success_metrics,
        "trend_metrics": trend_metrics,
        "failure_metrics": failure_metrics,
        "learning_metrics": learning_metrics,
        "issue_breakdown": issue_breakdown,
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _get_issue_breakdown(history: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Get breakdown of issues by type and severity.

    Args:
        history: QA iteration history

    Returns:
        Dict with issue statistics
    """
    issue_types: Counter[str] = Counter()
    issue_files: Counter[str] = Counter()

    for record in history:
        for issue in record.get("issues", []):
            issue_type = issue.get("type", "unknown")
            issue_types[issue_type] += 1

            if file := issue.get("file"):
                issue_files[file] += 1

    return {
        "by_type": dict(issue_types),
        "by_file": dict(issue_files.most_common(10)),  # Top 10 files
        "total_issues": sum(issue_types.values()),
        "unique_types": len(issue_types),
    }


# =============================================================================
# METRICS STORAGE
# =============================================================================


def update_learning_metrics(
    spec_dir: Path,
    root_causes_identified: int | None = None,
    user_corrections_applied: int | None = None,
    patterns_applied: int | None = None,
) -> bool:
    """
    Update learning metrics in implementation plan.

    Args:
        spec_dir: Spec directory path
        root_causes_identified: Number of root causes identified
        user_corrections_applied: Number of user corrections applied
        patterns_applied: Number of patterns successfully applied

    Returns:
        True if updated successfully
    """
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return False

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        if "learning_metrics" not in plan:
            plan["learning_metrics"] = {}

        metrics = plan["learning_metrics"]

        if root_causes_identified is not None:
            metrics["root_causes_identified"] = root_causes_identified

        if user_corrections_applied is not None:
            metrics["user_corrections_applied"] = user_corrections_applied

        if patterns_applied is not None:
            metrics["patterns_applied"] = patterns_applied

        metrics["last_updated"] = datetime.now(UTC).isoformat()

        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)

        return True

    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False


def increment_learning_metric(spec_dir: Path, metric_name: str) -> bool:
    """
    Increment a learning metric by 1.

    Args:
        spec_dir: Spec directory path
        metric_name: Name of metric to increment (e.g., "root_causes_identified")

    Returns:
        True if incremented successfully
    """
    metrics = _load_learning_metrics(spec_dir)
    current_value = metrics.get(metric_name, 0)

    return update_learning_metrics(spec_dir, **{metric_name: current_value + 1})
