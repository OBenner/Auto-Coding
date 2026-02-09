"""
Health Analyzer Module
======================

Aggregates project health metrics from multiple analysis sources
to provide a comprehensive dashboard of project status.

Provides metrics on:
- Test coverage percentage and trends
- Technical debt score and breakdown
- Dependency freshness and update availability
- Security vulnerability summary
- Code quality metrics (complexity, duplication)
- Recent agent activity summary
- Customizable health score weighting

Usage:
    from health_analyzer import get_project_health

    health = get_project_health(project_dir, spec_dir)
    print(f"Overall Health Score: {health['overall_score']}")
    print(f"Test Coverage: {health['test_coverage']['percentage']}%")
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Configuration
DEFAULT_WEIGHTS = {
    "test_coverage": 0.25,
    "code_quality": 0.20,
    "security": 0.25,
    "dependencies": 0.15,
    "agent_activity": 0.15,
}

HEALTH_THRESHOLDS = {
    "excellent": 90,
    "good": 75,
    "fair": 60,
    "poor": 0,
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


def _load_package_json(project_dir: Path) -> dict[str, Any] | None:
    """
    Load package.json from project directory.

    Args:
        project_dir: Project directory path

    Returns:
        Package.json dict or None if not found
    """
    package_file = project_dir / "package.json"
    if not package_file.exists():
        return None

    try:
        with open(package_file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _load_requirements_txt(project_dir: Path) -> list[str]:
    """
    Load requirements.txt dependencies.

    Args:
        project_dir: Project directory path

    Returns:
        List of dependency lines
    """
    req_file = project_dir / "requirements.txt"
    if not req_file.exists():
        return []

    try:
        with open(req_file, encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except (OSError, UnicodeDecodeError):
        return []


# =============================================================================
# TEST COVERAGE METRICS
# =============================================================================


def _calculate_test_coverage(project_dir: Path) -> dict[str, Any]:
    """
    Calculate test coverage metrics.

    Args:
        project_dir: Project directory path

    Returns:
        Dict with coverage metrics:
        {
            "percentage": float,
            "covered_lines": int,
            "total_lines": int,
            "test_count": int,
            "trend": str,  # "improving", "stable", "declining"
        }
    """
    # Check for coverage reports
    coverage_file = project_dir / "coverage.json"
    if not coverage_file.exists():
        coverage_file = project_dir / ".coverage"

    if not coverage_file.exists():
        # No coverage data available
        return {
            "percentage": 0.0,
            "covered_lines": 0,
            "total_lines": 0,
            "test_count": 0,
            "trend": "unknown",
        }

    # For now, return placeholder data
    # This will be implemented in subtask-1-2
    return {
        "percentage": 0.0,
        "covered_lines": 0,
        "total_lines": 0,
        "test_count": 0,
        "trend": "unknown",
    }


# =============================================================================
# CODE QUALITY METRICS
# =============================================================================


def _calculate_code_quality(project_dir: Path) -> dict[str, Any]:
    """
    Calculate code quality metrics.

    Args:
        project_dir: Project directory path

    Returns:
        Dict with quality metrics:
        {
            "complexity_score": float,
            "duplication_percentage": float,
            "maintainability_index": float,
            "issues_count": int,
        }
    """
    # This will use code_analyzer.py to analyze code
    # For now, return placeholder data
    return {
        "complexity_score": 0.0,
        "duplication_percentage": 0.0,
        "maintainability_index": 100.0,
        "issues_count": 0,
    }


# =============================================================================
# SECURITY METRICS
# =============================================================================


def _calculate_security_score(project_dir: Path) -> dict[str, Any]:
    """
    Calculate security vulnerability metrics.

    Args:
        project_dir: Project directory path

    Returns:
        Dict with security metrics:
        {
            "vulnerability_count": int,
            "critical_count": int,
            "high_count": int,
            "medium_count": int,
            "low_count": int,
            "scan_date": str,
        }
    """
    # This will use security_scanner.py
    # For now, return placeholder data
    return {
        "vulnerability_count": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "scan_date": datetime.now(UTC).isoformat(),
    }


# =============================================================================
# DEPENDENCY METRICS
# =============================================================================


def _calculate_dependency_health(project_dir: Path) -> dict[str, Any]:
    """
    Calculate dependency freshness and update availability.

    Args:
        project_dir: Project directory path

    Returns:
        Dict with dependency metrics:
        {
            "total_dependencies": int,
            "outdated_count": int,
            "major_updates_available": int,
            "minor_updates_available": int,
            "patch_updates_available": int,
            "freshness_score": float,
        }
    """
    # Count dependencies from package.json and requirements.txt
    package_json = _load_package_json(project_dir)
    requirements = _load_requirements_txt(project_dir)

    npm_deps = 0
    if package_json:
        npm_deps = len(package_json.get("dependencies", {}))
        npm_deps += len(package_json.get("devDependencies", {}))

    python_deps = len(requirements)
    total_deps = npm_deps + python_deps

    # For now, return basic data
    # Update checking will be implemented later
    return {
        "total_dependencies": total_deps,
        "outdated_count": 0,
        "major_updates_available": 0,
        "minor_updates_available": 0,
        "patch_updates_available": 0,
        "freshness_score": 100.0,
    }


# =============================================================================
# AGENT ACTIVITY METRICS
# =============================================================================


def _calculate_agent_activity(spec_dir: Path) -> dict[str, Any]:
    """
    Calculate recent agent activity metrics.

    Args:
        spec_dir: Spec directory path

    Returns:
        Dict with activity metrics:
        {
            "total_iterations": int,
            "success_rate": float,
            "average_fix_time": float,
            "recent_activity": list[dict],
        }
    """
    plan = _load_implementation_plan(spec_dir)
    if not plan:
        return {
            "total_iterations": 0,
            "success_rate": 0.0,
            "average_fix_time": 0.0,
            "recent_activity": [],
        }

    # Get QA iteration history
    history = plan.get("qa_iteration_history", [])
    total = len(history)
    approved = sum(1 for r in history if r.get("status") == "approved")
    success_rate = (approved / total * 100.0) if total > 0 else 0.0

    # Get recent activity (last 5 iterations)
    recent = history[-5:] if len(history) > 5 else history

    return {
        "total_iterations": total,
        "success_rate": round(success_rate, 1),
        "average_fix_time": 0.0,  # Will be calculated from timestamps later
        "recent_activity": recent,
    }


# =============================================================================
# HEALTH SCORE CALCULATION
# =============================================================================


def _calculate_overall_score(
    metrics: dict[str, Any], weights: dict[str, float] | None = None
) -> float:
    """
    Calculate overall health score from component metrics.

    Args:
        metrics: Dict with all component metrics
        weights: Optional custom weights (defaults to DEFAULT_WEIGHTS)

    Returns:
        Overall health score (0-100)
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # Normalize each component to 0-100 scale
    test_score = metrics["test_coverage"]["percentage"]
    quality_score = metrics["code_quality"]["maintainability_index"]
    security_score = 100.0 - (
        metrics["security"]["vulnerability_count"] * 10
    )  # Deduct 10 points per vulnerability
    security_score = max(0.0, min(100.0, security_score))
    dependency_score = metrics["dependencies"]["freshness_score"]
    activity_score = metrics["agent_activity"]["success_rate"]

    # Calculate weighted average
    overall = (
        test_score * weights["test_coverage"]
        + quality_score * weights["code_quality"]
        + security_score * weights["security"]
        + dependency_score * weights["dependencies"]
        + activity_score * weights["agent_activity"]
    )

    return round(overall, 1)


def _get_health_status(score: float) -> str:
    """
    Get health status label from score.

    Args:
        score: Health score (0-100)

    Returns:
        Status label: "excellent", "good", "fair", or "poor"
    """
    if score >= HEALTH_THRESHOLDS["excellent"]:
        return "excellent"
    elif score >= HEALTH_THRESHOLDS["good"]:
        return "good"
    elif score >= HEALTH_THRESHOLDS["fair"]:
        return "fair"
    else:
        return "poor"


# =============================================================================
# PUBLIC API
# =============================================================================


def get_project_health(
    project_dir: Path | str, spec_dir: Path | str | None = None, weights: dict[str, float] | None = None
) -> dict[str, Any]:
    """
    Get comprehensive project health metrics.

    Args:
        project_dir: Project directory path
        spec_dir: Optional spec directory path (for agent activity metrics)
        weights: Optional custom weights for health score calculation

    Returns:
        Dict with complete health data:
        {
            "overall_score": float,
            "status": str,
            "test_coverage": dict,
            "code_quality": dict,
            "security": dict,
            "dependencies": dict,
            "agent_activity": dict,
            "generated_at": str,
        }
    """
    project_path = Path(project_dir)
    spec_path = Path(spec_dir) if spec_dir else project_path / ".auto-claude" / "specs"

    # Gather all component metrics
    metrics = {
        "test_coverage": _calculate_test_coverage(project_path),
        "code_quality": _calculate_code_quality(project_path),
        "security": _calculate_security_score(project_path),
        "dependencies": _calculate_dependency_health(project_path),
        "agent_activity": _calculate_agent_activity(spec_path) if spec_path.exists() else {
            "total_iterations": 0,
            "success_rate": 0.0,
            "average_fix_time": 0.0,
            "recent_activity": [],
        },
    }

    # Calculate overall score
    overall_score = _calculate_overall_score(metrics, weights)
    status = _get_health_status(overall_score)

    return {
        "overall_score": overall_score,
        "status": status,
        "test_coverage": metrics["test_coverage"],
        "code_quality": metrics["code_quality"],
        "security": metrics["security"],
        "dependencies": metrics["dependencies"],
        "agent_activity": metrics["agent_activity"],
        "generated_at": datetime.now(UTC).isoformat(),
    }


def get_health_summary(project_dir: Path | str, spec_dir: Path | str | None = None) -> dict[str, Any]:
    """
    Get condensed health summary for quick display.

    Args:
        project_dir: Project directory path
        spec_dir: Optional spec directory path

    Returns:
        Dict with summary data:
        {
            "overall_score": float,
            "status": str,
            "critical_issues": list[str],
            "recommendations": list[str],
        }
    """
    health = get_project_health(project_dir, spec_dir)

    # Identify critical issues
    critical = []
    recommendations = []

    if health["security"]["critical_count"] > 0:
        critical.append(f"{health['security']['critical_count']} critical security vulnerabilities")
        recommendations.append("Run security scan and update vulnerable dependencies")

    if health["test_coverage"]["percentage"] < 50.0:
        critical.append(f"Low test coverage ({health['test_coverage']['percentage']}%)")
        recommendations.append("Increase test coverage to at least 70%")

    if health["dependencies"]["outdated_count"] > 10:
        critical.append(f"{health['dependencies']['outdated_count']} outdated dependencies")
        recommendations.append("Update dependencies to latest stable versions")

    return {
        "overall_score": health["overall_score"],
        "status": health["status"],
        "critical_issues": critical,
        "recommendations": recommendations,
    }
