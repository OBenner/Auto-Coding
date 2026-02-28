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
import xml.etree.ElementTree as ET
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
            lines = []
            for raw in f:
                line = raw.strip()
                if line and not line.startswith("#"):
                    lines.append(line)
            return lines
    except (OSError, UnicodeDecodeError):
        return []


# =============================================================================
# TEST COVERAGE METRICS
# =============================================================================


def _count_test_files(project_dir: Path) -> int:
    """
    Count test files in the project.

    Args:
        project_dir: Project directory path

    Returns:
        Number of test files found
    """
    test_file_patterns = [
        "**/test_*.py",
        "**/*_test.py",
        "**/*.test.js",
        "**/*.test.ts",
        "**/*.test.tsx",
        "**/*.spec.js",
        "**/*.spec.ts",
        "**/*.spec.tsx",
        "**/test_*.go",
        "**/*_test.go",
        "**/*_test.rs",
        "**/*_spec.rb",
    ]

    test_files = set()
    for pattern in test_file_patterns:
        for file_path in project_dir.glob(pattern):
            if file_path.is_file():
                test_files.add(file_path)

    return len(test_files)


def _parse_jest_coverage(coverage_file: Path) -> dict[str, Any] | None:
    """
    Parse Jest/Vitest coverage JSON format.

    Args:
        coverage_file: Path to coverage.json or coverage-final.json

    Returns:
        Coverage metrics dict or None if parsing fails
    """
    try:
        with open(coverage_file, encoding="utf-8") as f:
            data = json.load(f)

        total_lines = 0
        covered_lines = 0

        # Jest coverage format has file-level coverage data
        for file_data in data.values():
            if isinstance(file_data, dict) and "lines" in file_data:
                lines = file_data["lines"]
                if "total" in lines and "covered" in lines:
                    total_lines += lines["total"]
                    covered_lines += lines["covered"]

        if total_lines == 0:
            return None

        percentage = (covered_lines / total_lines) * 100.0

        return {
            "percentage": round(percentage, 2),
            "covered_lines": covered_lines,
            "total_lines": total_lines,
        }

    except (OSError, json.JSONDecodeError, KeyError, ValueError, UnicodeDecodeError):
        return None


def _parse_cobertura_coverage(coverage_file: Path) -> dict[str, Any] | None:
    """
    Parse Cobertura XML coverage format.

    Args:
        coverage_file: Path to coverage.xml

    Returns:
        Coverage metrics dict or None if parsing fails
    """
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()

        # Cobertura format has line-rate attribute at root
        line_rate = root.get("line-rate")
        if line_rate:
            percentage = float(line_rate) * 100.0

            # Try to get line counts from metrics
            total_lines = 0
            covered_lines = 0

            for package in root.findall(".//package"):
                for class_elem in package.findall(".//class"):
                    lines = class_elem.findall(".//line")
                    for line in lines:
                        total_lines += 1
                        hits = int(line.get("hits", 0))
                        if hits > 0:
                            covered_lines += 1

            return {
                "percentage": round(percentage, 2),
                "covered_lines": covered_lines,
                "total_lines": total_lines,
            }

    except (OSError, ET.ParseError, ValueError, AttributeError):
        return None

    return None


def _parse_python_coverage_json(coverage_file: Path) -> dict[str, Any] | None:
    """
    Parse Python coverage.py JSON format.

    Args:
        coverage_file: Path to coverage.json

    Returns:
        Coverage metrics dict or None if parsing fails
    """
    try:
        with open(coverage_file, encoding="utf-8") as f:
            data = json.load(f)

        # Python coverage.json has totals section
        totals = data.get("totals", {})
        if totals:
            covered_lines = totals.get("covered_lines", 0)
            num_statements = totals.get("num_statements", 0)

            if num_statements == 0:
                return None

            percentage = totals.get("percent_covered", 0.0)

            return {
                "percentage": round(percentage, 2),
                "covered_lines": covered_lines,
                "total_lines": num_statements,
            }

    except (OSError, json.JSONDecodeError, KeyError, ValueError, UnicodeDecodeError):
        return None

    return None


def calculate_test_coverage(project_dir: Path) -> dict[str, Any]:
    """
    Calculate test coverage metrics from available coverage reports.

    Supports multiple coverage formats:
    - Jest/Vitest: coverage.json, coverage/coverage-final.json
    - Python: coverage.json (coverage.py JSON format)
    - Cobertura: coverage.xml

    Args:
        project_dir: Project directory path

    Returns:
        Dict with coverage metrics:
        {
            "percentage": float,
            "covered_lines": int,
            "total_lines": int,
            "test_count": int,
            "trend": str,  # "improving", "stable", "declining", "unknown"
        }
    """
    # Check for various coverage file formats
    coverage_files = [
        project_dir / "coverage.json",
        project_dir / "coverage" / "coverage-final.json",
        project_dir / "coverage.xml",
        project_dir / ".coverage",  # Python coverage.py SQLite (not parsed yet)
    ]

    coverage_data = None

    for coverage_file in coverage_files:
        if not coverage_file.exists():
            continue

        # Try different parsers based on file extension
        if coverage_file.name.endswith(".json"):
            # Try Jest/Vitest format first
            coverage_data = _parse_jest_coverage(coverage_file)
            if not coverage_data:
                # Try Python coverage.py JSON format
                coverage_data = _parse_python_coverage_json(coverage_file)
        elif coverage_file.name.endswith(".xml"):
            coverage_data = _parse_cobertura_coverage(coverage_file)

        if coverage_data:
            break

    # Count test files
    test_count = _count_test_files(project_dir)

    if not coverage_data:
        # No coverage data available
        return {
            "percentage": 0.0,
            "covered_lines": 0,
            "total_lines": 0,
            "test_count": test_count,
            "trend": "unknown",
        }

    # Add test count to coverage data
    coverage_data["test_count"] = test_count

    # Calculate trend (requires historical data - for now return "unknown")
    # This could be enhanced by storing previous coverage percentages
    # and comparing to determine if improving/declining
    coverage_data["trend"] = "unknown"

    return coverage_data


# Backwards compatibility - keep old function name as alias
_calculate_test_coverage = calculate_test_coverage


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

    # Merge user weights with defaults to prevent missing key errors
    merged_weights = {**DEFAULT_WEIGHTS, **(weights or {})}

    # Calculate weighted average
    overall = (
        test_score * merged_weights["test_coverage"]
        + quality_score * merged_weights["code_quality"]
        + security_score * merged_weights["security"]
        + dependency_score * merged_weights["dependencies"]
        + activity_score * merged_weights["agent_activity"]
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
    project_dir: Path | str,
    spec_dir: Path | str | None = None,
    weights: dict[str, float] | None = None,
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
        "agent_activity": _calculate_agent_activity(spec_path)
        if spec_path.exists()
        else {
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


def get_health_summary(
    project_dir: Path | str, spec_dir: Path | str | None = None
) -> dict[str, Any]:
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
        critical.append(
            f"{health['security']['critical_count']} critical security vulnerabilities"
        )
        recommendations.append("Run security scan and update vulnerable dependencies")

    if health["test_coverage"]["percentage"] < 50.0:
        critical.append(f"Low test coverage ({health['test_coverage']['percentage']}%)")
        recommendations.append("Increase test coverage to at least 70%")

    if health["dependencies"]["outdated_count"] > 10:
        critical.append(
            f"{health['dependencies']['outdated_count']} outdated dependencies"
        )
        recommendations.append("Update dependencies to latest stable versions")

    return {
        "overall_score": health["overall_score"],
        "status": health["status"],
        "critical_issues": critical,
        "recommendations": recommendations,
    }
