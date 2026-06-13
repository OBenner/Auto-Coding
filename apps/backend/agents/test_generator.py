"""
Test Generator Agent Module
============================

AI agent that generates tests based on code analysis results.
Supports multiple test frameworks:
- pytest for Python code
- Vitest for TypeScript/React code

Uses the Test Generator Agent prompt to create comprehensive test coverage.
"""

import ast
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

from analysis.coverage_analyzer import (
    CoverageAnalyzer,
    CoverageResult,
    parse_coverage_json,
    validate_coverage_threshold,
)
from core.client import create_client
from phase_config import get_phase_model, get_phase_thinking_budget
from phase_event import ExecutionPhase, emit_phase
from prompts_pkg.prompt_loader import get_agent_prompt
from spec.coverage_config import CoverageConfig, load_coverage_config
from task_logger import LogEntryType, LogPhase, get_task_logger
from ui import (
    Icons,
    bold,
    box,
    highlight,
    icon,
    muted,
    print_key_value,
    print_status,
)

# Import shared generator helpers
from ._generator_base import log_generator_result, run_generator_session
from ._validation import validate_python_tests

# Import fixture generator
from .fixture_generator import generate_fixtures

# Import framework-specific generators
from .vitest_generator import generate_vitest_tests, validate_vitest_tests

logger = logging.getLogger(__name__)

# Template for the integration test generator agent starting message.
# Formatted with analysis_json at runtime.
_INTEGRATION_TEST_STARTING_MESSAGE = """You are the Integration Test Generator Agent. Your task is to generate comprehensive integration tests for API endpoints and multi-component interactions.

## Code Analysis Results

{analysis_json}

## Your Task

1. Read the spec.md to understand what API endpoints and services were implemented
2. Review the implementation_plan.json to see what integrations were built
3. Study existing integration test patterns in tests/integration/test_*.py (if they exist)
4. Identify API endpoints, routes, and service integrations that need testing
5. Generate integration test files that validate:
   - API endpoint functionality (request/response validation)
   - Database interactions (CRUD operations)
   - Service layer integration
   - Authentication and authorization
   - Error handling and edge cases
6. Follow the project's testing conventions
7. Use appropriate mocking for external dependencies

## Integration Test Pattern (pytest)

Your tests should:
- Use pytest as the test framework
- Test multiple components working together (not isolated units)
- Validate API endpoints with different inputs
- Test database operations (create, read, update, delete)
- Verify service layer logic
- Handle authentication/authorization scenarios
- Test error conditions and edge cases
- Use fixtures for test data setup and teardown

Generate test files in the tests/integration/ directory following the naming convention test_integration_*.py.

Begin by loading context (Phase 0 in your prompt).
"""


def detect_test_framework(analysis_results: dict[str, Any]) -> str:
    """
    Detect which test framework to use based on analysis results.

    Args:
        analysis_results: Code analysis results from CodeAnalyzer or TypeScriptAnalyzer

    Returns:
        "pytest" for Python code, "vitest" for TypeScript/React code
    """
    # Check for TypeScript/React indicators
    has_components = "components" in analysis_results and analysis_results.get(
        "components"
    )
    has_hooks = "hooks" in analysis_results and analysis_results.get("hooks")
    has_tsx_files = any(
        str(f).endswith((".tsx", ".ts"))
        for f in analysis_results.get("analyzed_files", [])
    )

    # Check for Python indicators
    has_classes = "classes" in analysis_results and analysis_results.get("classes")
    has_py_files = any(
        str(f).endswith(".py") for f in analysis_results.get("analyzed_files", [])
    )

    # Decision logic
    if has_components or has_hooks or has_tsx_files:
        return "vitest"
    elif has_classes or has_py_files:
        return "pytest"
    else:
        # Default to pytest if unclear
        logger.warning(
            "Could not determine test framework from analysis results, defaulting to pytest"
        )
        return "pytest"


def analyze_coverage_gaps(
    project_dir: Path,
    source_dir: str | None = None,
    config: CoverageConfig | None = None,
    enforce_threshold: bool = True,
) -> tuple[CoverageResult | None, dict[str, Any]]:
    """
    Run coverage analysis and identify gaps in test coverage with threshold enforcement.

    This function performs comprehensive coverage analysis and enforces minimum coverage
    thresholds. It provides detailed gap reporting including:
    - Files below the coverage threshold
    - Critical gaps (significantly below threshold)
    - Missing line numbers per file
    - Coverage statistics and enforcement status
    - Prioritized list of files needing tests

    Args:
        project_dir: Root directory of the project
        source_dir: Directory to measure coverage for (e.g., "apps/backend")
        config: Coverage configuration with thresholds (optional)
        enforce_threshold: Whether to enforce the minimum coverage threshold (default: True)

    Returns:
        Tuple of (coverage_result, gaps_summary)
        - coverage_result: CoverageResult with analysis data or None if failed
        - gaps_summary: Dictionary with detailed gap statistics and enforcement status:
            * total_coverage: Overall coverage percentage
            * meets_threshold: Whether coverage meets the minimum threshold
            * threshold_message: Validation message from validate_coverage_threshold
            * files_with_gaps: List of files below threshold (sorted by priority)
            * critical_gaps: List of files with coverage < 50% of threshold
            * high_priority_gaps: List of files with coverage 50-80% of threshold
            * medium_priority_gaps: List of files with coverage 80-100% of threshold
            * missing_lines_by_file: Dict mapping file paths to missing line numbers
            * coverage_by_file: Dict mapping file paths to coverage percentages
            * total_lines_missing: Total number of missing lines across all files
            * total_files_analyzed: Total number of files in coverage report
            * threshold_percent: The minimum coverage threshold used
            * error: Error message if coverage analysis failed
    """
    analyzer = CoverageAnalyzer(project_dir)

    print_status("Running coverage analysis to identify gaps...", "progress")

    # Check if pytest-cov is available
    installed, message = analyzer.check_pytest_cov_installed()
    if not installed:
        logger.warning(f"pytest-cov not available: {message}")
        error_summary = {
            "error": message,
            "meets_threshold": False,
            "threshold_percent": config.minimum_coverage if config else 80.0,
        }
        return None, error_summary

    # Determine source directory if not specified
    if source_dir is None:
        # Default to apps/backend for backend projects
        if (project_dir / "apps" / "backend").exists():
            source_dir = "apps/backend"
        else:
            # Use current directory
            source_dir = "."

    # Get minimum coverage threshold
    min_coverage = config.minimum_coverage if config else 80.0

    # Run coverage with JSON output (optionally enforce threshold)
    coverage_output = project_dir / ".coverage.test_generator.json"
    result = analyzer.run_coverage(
        source_dir=source_dir,
        output_format="json",
        output_file=coverage_output,
        min_coverage=min_coverage if enforce_threshold else None,
    )

    if not result.success:
        logger.warning(f"Coverage analysis failed: {result.error_message}")
        error_summary = {
            "error": result.error_message,
            "meets_threshold": False,
            "threshold_percent": min_coverage,
        }
        return None, error_summary

    # Parse the JSON coverage report
    try:
        coverage_result = parse_coverage_json(coverage_output)
    except Exception as e:
        logger.error(f"Failed to parse coverage JSON: {e}")
        error_summary = {
            "error": str(e),
            "meets_threshold": False,
            "threshold_percent": min_coverage,
        }
        return None, error_summary

    # Validate coverage meets threshold using the coverage_analyzer function
    passes_threshold, threshold_message = validate_coverage_threshold(
        coverage_result, min_coverage
    )

    # Identify coverage gaps with detailed categorization
    gaps_summary = {
        "total_coverage": coverage_result.total_coverage,
        "meets_threshold": passes_threshold,
        "threshold_message": threshold_message,
        "threshold_percent": min_coverage,
        "files_with_gaps": [],
        "critical_gaps": [],  # < 50% of threshold
        "high_priority_gaps": [],  # 50-80% of threshold
        "medium_priority_gaps": [],  # 80-100% of threshold
        "missing_lines_by_file": {},
        "coverage_by_file": {},
        "total_lines_missing": 0,
        "total_files_analyzed": len(coverage_result.files),
    }

    # Analyze each file for gaps with priority categorization
    for file_path, file_coverage in coverage_result.files.items():
        coverage_percent = file_coverage.coverage_percent
        gaps_summary["coverage_by_file"][file_path] = coverage_percent

        # Check if file is below threshold
        if coverage_percent < min_coverage:
            # Calculate coverage deficit
            deficit = min_coverage - coverage_percent
            deficit_ratio = deficit / min_coverage

            # Add to appropriate priority category
            if deficit_ratio > 0.5:  # More than 50% below threshold
                gaps_summary["critical_gaps"].append(file_path)
            elif deficit_ratio > 0.2:  # 20-50% below threshold
                gaps_summary["high_priority_gaps"].append(file_path)
            else:  # Less than 20% below threshold
                gaps_summary["medium_priority_gaps"].append(file_path)

            gaps_summary["files_with_gaps"].append(file_path)
            gaps_summary["missing_lines_by_file"][file_path] = (
                file_coverage.lines_missing
            )
            gaps_summary["total_lines_missing"] += len(file_coverage.lines_missing)

    # Sort files within each priority category by coverage (lowest first)
    for category in ["critical_gaps", "high_priority_gaps", "medium_priority_gaps"]:
        gaps_summary[category].sort(key=lambda fp: gaps_summary["coverage_by_file"][fp])

    # Also sort the main files_with_gaps by priority (critical first, then coverage)
    priority_order = {}
    for idx, fp in enumerate(gaps_summary["critical_gaps"]):
        priority_order[fp] = idx
    for idx, fp in enumerate(gaps_summary["high_priority_gaps"]):
        priority_order[fp] = len(gaps_summary["critical_gaps"]) + idx
    for idx, fp in enumerate(gaps_summary["medium_priority_gaps"]):
        priority_order[fp] = (
            len(gaps_summary["critical_gaps"])
            + len(gaps_summary["high_priority_gaps"])
            + idx
        )

    gaps_summary["files_with_gaps"].sort(
        key=lambda fp: (
            priority_order.get(fp, 999),
            -gaps_summary["coverage_by_file"][fp],
        )
    )

    # Log results with detailed statistics
    files_with_gaps_count = len(gaps_summary["files_with_gaps"])
    total_files = gaps_summary["total_files_analyzed"]

    if files_with_gaps_count > 0:
        # Coverage below threshold
        status_level = "error" if not passes_threshold else "warning"
        print_status(
            f"Coverage threshold enforcement: {threshold_message}",
            status_level,
        )
        print_key_value("Total coverage", f"{coverage_result.total_coverage:.1f}%")
        print_key_value("Required threshold", f"{min_coverage:.1f}%")
        print_key_value("Files with gaps", f"{files_with_gaps_count}/{total_files}")
        print_key_value("Total missing lines", str(gaps_summary["total_lines_missing"]))

        if gaps_summary["critical_gaps"]:
            print_key_value(
                "Critical gaps (<50% of threshold)",
                str(len(gaps_summary["critical_gaps"])),
            )
        if gaps_summary["high_priority_gaps"]:
            print_key_value(
                "High priority gaps (50-80% of threshold)",
                str(len(gaps_summary["high_priority_gaps"])),
            )
        if gaps_summary["medium_priority_gaps"]:
            print_key_value(
                "Medium priority gaps (80-100% of threshold)",
                str(len(gaps_summary["medium_priority_gaps"])),
            )
    else:
        # Coverage meets or exceeds threshold
        print_status(
            f"✓ Coverage meets threshold: {coverage_result.total_coverage:.1f}% "
            f"(required: {min_coverage:.1f}%)",
            "success",
        )
        print_key_value("Files analyzed", str(total_files))
        print_key_value("Files meeting threshold", f"{total_files}/{total_files}")

    return coverage_result, gaps_summary


def format_coverage_gaps_prompt(gaps_summary: dict[str, Any]) -> str:
    """
    Format coverage gaps as a detailed prompt for the AI agent.

    This function creates a comprehensive, prioritized report of coverage gaps
    to guide test generation. It categorizes gaps by priority and provides
    specific line numbers needing coverage.

    Args:
        gaps_summary: Summary from analyze_coverage_gaps with detailed metrics

    Returns:
        Formatted string describing coverage gaps with prioritization
    """
    if "error" in gaps_summary:
        return f"## Coverage Analysis Failed\n\n{gaps_summary['error']}"

    # Get threshold information
    threshold = gaps_summary.get("threshold_percent", 80.0)
    total_coverage = gaps_summary["total_coverage"]

    lines = []
    lines.append("## Coverage Gap Analysis")
    lines.append("")

    # Coverage status header
    if gaps_summary.get("meets_threshold", False):
        lines.append("✓ **Status:** Coverage meets threshold")
        lines.append(
            f"**Total Coverage:** {total_coverage:.1f}% (required: {threshold:.1f}%)"
        )
    else:
        lines.append("⚠ **Status:** Coverage below threshold")
        lines.append(
            f"**Total Coverage:** {total_coverage:.1f}% (required: {threshold:.1f}%)"
        )
        lines.append(f"**Deficit:** {threshold - total_coverage:.1f}%")

    # Statistics
    lines.append("")
    lines.append("### Statistics")
    lines.append(f"- **Files Analyzed:** {gaps_summary.get('total_files_analyzed', 0)}")
    lines.append(
        f"- **Files with Gaps:** {len(gaps_summary.get('files_with_gaps', []))}"
    )
    lines.append(
        f"- **Total Missing Lines:** {gaps_summary.get('total_lines_missing', 0)}"
    )

    # Priority breakdown
    if gaps_summary.get("files_with_gaps"):
        lines.append("")
        lines.append("### Gap Prioritization")

        if gaps_summary.get("critical_gaps"):
            critical_count = len(gaps_summary["critical_gaps"])
            lines.append(
                f"- **🔴 Critical:** {critical_count} file(s) with coverage < {threshold * 0.5:.1f}%"
            )

        if gaps_summary.get("high_priority_gaps"):
            high_count = len(gaps_summary["high_priority_gaps"])
            lines.append(
                f"- **🟠 High Priority:** {high_count} file(s) with coverage {threshold * 0.5:.1f}%-{threshold * 0.8:.1f}%"
            )

        if gaps_summary.get("medium_priority_gaps"):
            medium_count = len(gaps_summary["medium_priority_gaps"])
            lines.append(
                f"- **🟡 Medium Priority:** {medium_count} file(s) with coverage {threshold * 0.8:.1f}%-{threshold:.1f}%"
            )

    # Detailed file listing by priority
    if gaps_summary.get("files_with_gaps"):
        lines.append("")
        lines.append("### Files Requiring Additional Tests")
        lines.append("")
        lines.append("*Files are listed by priority (critical → high → medium)*")
        lines.append("")

        # Show files with their coverage and missing lines
        max_files_to_show = 15
        shown_count = 0

        for file_path in gaps_summary["files_with_gaps"]:
            if shown_count >= max_files_to_show:
                break

            coverage = gaps_summary["coverage_by_file"].get(file_path, 0.0)
            missing_lines = gaps_summary["missing_lines_by_file"].get(file_path, [])

            # Determine priority indicator
            if file_path in gaps_summary.get("critical_gaps", []):
                priority = "🔴"
            elif file_path in gaps_summary.get("high_priority_gaps", []):
                priority = "🟠"
            else:
                priority = "🟡"

            lines.append(f"{priority} **{file_path}**")
            lines.append(
                f"   - Coverage: {coverage:.1f}% (threshold: {threshold:.1f}%)"
            )

            if missing_lines:
                # Show line ranges (limit to first 30 lines to keep prompt manageable)
                line_ranges = _format_line_ranges(missing_lines[:30])
                lines.append(f"   - Missing lines: {line_ranges}")

                if len(missing_lines) > 30:
                    lines.append(f"   - ... and {len(missing_lines) - 30} more lines")

            shown_count += 1

        # Show count of remaining files
        remaining_files = len(gaps_summary["files_with_gaps"]) - shown_count
        if remaining_files > 0:
            lines.append("")
            lines.append(f"... and {remaining_files} more file(s) with coverage gaps")

    # Action items
    lines.append("")
    lines.append("### Action Items")
    lines.append("")
    lines.append(
        "1. **Prioritize Critical Gaps:** Start with files marked 🔴 (lowest coverage)"
    )
    lines.append(
        "2. **Target Missing Lines:** Write tests specifically for the missing line numbers"
    )
    lines.append(
        "3. **Focus on High Impact:** Address high-priority gaps (🟠) before medium (🟡)"
    )
    lines.append(
        "4. **Verify Coverage:** Run tests and re-check coverage after each batch"
    )
    lines.append("")
    lines.append(
        "**Note:** Coverage is measured at the line level. Ensure tests execute all"
    )
    lines.append(
        "the missing lines listed above, including edge cases and error paths."
    )

    return "\n".join(lines)


def _format_line_ranges(line_numbers: list[int]) -> str:
    """
    Format a list of line numbers into compact ranges.

    Args:
        line_numbers: List of line numbers

    Returns:
        Formatted string like "1-5, 10, 15-20"
    """
    if not line_numbers:
        return ""

    sorted_lines = sorted(set(line_numbers))
    ranges = []
    start = sorted_lines[0]
    end = sorted_lines[0]

    for line in sorted_lines[1:]:
        if line == end + 1:
            end = line
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = line
            end = line

    # Add final range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")

    return ", ".join(ranges)


def validate_generated_tests(
    test_files: list[Path], project_dir: Path, framework: str = "pytest"
) -> bool:
    """
    Validate that generated tests are syntactically correct.

    Routes to framework-specific validation:
    - pytest: Uses pytest --collect-only to verify tests can be collected
    - vitest: Uses TypeScript compiler and Vitest to verify tests

    Args:
        test_files: List of generated test file paths
        project_dir: Project root directory
        framework: Test framework ("pytest" or "vitest")

    Returns:
        True if all tests are valid, False otherwise
    """
    if not test_files:
        logger.warning("No test files to validate")
        return False

    # Route to framework-specific validation
    if framework == "vitest":
        logger.info("Using Vitest validation for TypeScript/React tests")
        # validate_vitest_tests is async; use asyncio.run() from sync context.
        # In production, vitest validation is handled directly by
        # generate_vitest_tests() which awaits validate_vitest_tests().
        return asyncio.run(validate_vitest_tests(test_files, project_dir))

    # Default to pytest validation
    logger.info("Using pytest validation for Python tests")
    from ._validation import validate_python_tests

    return asyncio.run(validate_python_tests(test_files, project_dir))


def validate_test_quality(test_files: list[Path], project_dir: Path) -> dict[str, Any]:
    """
    Validate test quality beyond syntax checks.

    Performs comprehensive quality checks including:
    - Assertion presence and quality
    - Test naming conventions
    - Test structure (fixtures, setup/teardown)
    - Edge case coverage
    - Mocking quality
    - Test independence
    - Docstring presence

    Args:
        test_files: List of test file paths (relative to project_dir)
        project_dir: Project root directory

    Returns:
        Dictionary with:
        - passed: Whether quality checks passed
        - issues: List of quality issues found
        - score: Quality score (0-100)
        - metrics: Dictionary with detailed metrics
    """
    from dataclasses import dataclass

    @dataclass
    class QualityIssue:
        """Represents a test quality issue."""

        file: str
        line: int
        test_name: str
        severity: str  # "error", "warning", "info"
        category: str  # "assertions", "naming", "structure", "edge_cases", "mocking"
        message: str

    @dataclass
    class TestMetrics:
        """Metrics for test quality assessment."""

        total_tests: int = 0
        tests_with_assertions: int = 0
        tests_with_docstrings: int = 0
        tests_properly_named: int = 0
        tests_using_fixtures: int = 0
        tests_with_edge_cases: int = 0
        tests_with_mocks: int = 0
        assertions_per_test: float = 0.0
        avg_test_complexity: float = 0.0

    issues: list[QualityIssue] = []
    metrics = TestMetrics()

    if not test_files:
        return {
            "passed": False,
            "issues": [],
            "score": 0,
            "metrics": {},
            "error": "No test files to validate",
        }

    print()
    print_status("Analyzing test quality...", "progress")

    for test_file in test_files:
        file_path = project_dir / test_file
        if not file_path.exists():
            continue

        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)

            # Analyze test functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    metrics.total_tests += 1

                    # Check test naming
                    naming_score = _check_test_naming(node.name, test_file)
                    if naming_score["is_valid"]:
                        metrics.tests_properly_named += 1
                    else:
                        issues.append(
                            QualityIssue(
                                file=str(test_file),
                                line=node.lineno,
                                test_name=node.name,
                                severity="warning",
                                category="naming",
                                message=naming_score["message"],
                            )
                        )

                    # Check for docstring
                    has_docstring = ast.get_docstring(node) is not None
                    if has_docstring:
                        metrics.tests_with_docstrings += 1

                    # Check for assertions
                    assertion_info = _check_assertions(node)
                    if assertion_info["has_assertions"]:
                        metrics.tests_with_assertions += 1
                    else:
                        issues.append(
                            QualityIssue(
                                file=str(test_file),
                                line=node.lineno,
                                test_name=node.name,
                                severity="error",
                                category="assertions",
                                message="Test function has no assertions",
                            )
                        )

                    # Check for fixture usage
                    uses_fixtures = _check_fixture_usage(node)
                    if uses_fixtures:
                        metrics.tests_using_fixtures += 1

                    # Check for edge case coverage
                    edge_cases = _check_edge_case_coverage(node, source)
                    if edge_cases["has_edge_cases"]:
                        metrics.tests_with_edge_cases += 1
                    elif edge_cases["should_have_edge_cases"]:
                        issues.append(
                            QualityIssue(
                                file=str(test_file),
                                line=node.lineno,
                                test_name=node.name,
                                severity="info",
                                category="edge_cases",
                                message="Consider testing edge cases "
                                "(empty inputs, None, boundary values)",
                            )
                        )

                    # Check mocking quality
                    mock_info = _check_mocking_quality(node)
                    if mock_info["has_mocks"]:
                        metrics.tests_with_mocks += 1
                        if not mock_info["proper_usage"]:
                            issues.append(
                                QualityIssue(
                                    file=str(test_file),
                                    line=node.lineno,
                                    test_name=node.name,
                                    severity="warning",
                                    category="mocking",
                                    message=mock_info["message"],
                                )
                            )

        except (SyntaxError, OSError) as e:
            logger.warning(f"Failed to analyze {test_file}: {e}")
            continue

    # Calculate metrics
    if metrics.total_tests > 0:
        metrics.assertions_per_test = (
            metrics.tests_with_assertions / metrics.total_tests
        ) * 100

    # Calculate quality score
    score = _calculate_quality_score(metrics, len(issues))

    # Categorize issues by severity
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    info = [i for i in issues if i.severity == "info"]

    # Print summary
    print()
    print_key_value("Quality score", f"{score:.0f}/100")
    print_key_value("Tests analyzed", str(metrics.total_tests))
    print_key_value("Errors", str(len(errors)))
    print_key_value("Warnings", str(len(warnings)))
    print_key_value("Info", str(len(info)))
    print()

    # Print critical issues
    if errors:
        print_status("Quality Issues Detected", "error")
        for issue in errors[:5]:
            print(f"  {muted('•')} {issue.file}:{issue.line} - {issue.message}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")
        print()

    # Determine if quality is acceptable
    passed = len(errors) == 0 and score >= 50

    if passed:
        print_status("Test quality validation passed", "success")
    else:
        print_status("Test quality validation failed", "warning")

    return {
        "passed": passed,
        "issues": [
            {
                "file": i.file,
                "line": i.line,
                "test": i.test_name,
                "severity": i.severity,
                "category": i.category,
                "message": i.message,
            }
            for i in issues
        ],
        "score": score,
        "metrics": {
            "total_tests": metrics.total_tests,
            "tests_with_assertions": metrics.tests_with_assertions,
            "tests_with_docstrings": metrics.tests_with_docstrings,
            "tests_properly_named": metrics.tests_properly_named,
            "tests_using_fixtures": metrics.tests_using_fixtures,
            "tests_with_edge_cases": metrics.tests_with_edge_cases,
            "tests_with_mocks": metrics.tests_with_mocks,
            "assertions_coverage": metrics.assertions_per_test,
        },
    }


def _check_test_naming(test_name: str, test_file: Path) -> dict[str, Any]:
    """
    Check if test name follows conventions.

    Good: test_function_name_scenario()
    Bad: test1(), test_my_func(), t_e_s_t()

    Args:
        test_name: Name of the test function
        test_file: Path to test file

    Returns:
        Dictionary with is_valid and message
    """
    # Must start with test_
    if not test_name.startswith("test_"):
        return {
            "is_valid": False,
            "message": f"Test name '{test_name}' must start with 'test_'",
        }

    # Must be longer than just "test_"
    if len(test_name) <= 5:
        return {
            "is_valid": False,
            "message": f"Test name '{test_name}' is too short",
        }

    # Should use underscores, not camelCase
    if re.search(r"[A-Z]", test_name):
        return {
            "is_valid": False,
            "message": f"Test name '{test_name}' should use snake_case, not CamelCase",
        }

    # Should not have numbers as the only differentiation
    if re.match(r"test_\w+_\d+$", test_name):
        return {
            "is_valid": False,
            "message": f"Test name '{test_name}' should describe behavior, not use numbers",
        }

    return {"is_valid": True, "message": ""}


def _check_assertions(node: ast.FunctionDef) -> dict[str, Any]:
    """
    Check if test function has assertions.

    Args:
        node: AST function node

    Returns:
        Dictionary with has_assertions flag
    """
    has_assert = False

    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            has_assert = True
            break

    return {"has_assertions": has_assert}


def _check_fixture_usage(node: ast.FunctionDef) -> bool:
    """
    Check if test function uses pytest fixtures.

    Args:
        node: AST function node

    Returns:
        True if fixtures are used
    """
    # Check if function arguments suggest fixtures
    # Common fixture names: tmp_path, capsys, monkeypatch, fixture
    common_fixtures = {
        "tmp_path",
        "tmpdir",
        "capsys",
        "capfd",
        "monkeypatch",
        "fixture",
        "request",
    }

    for arg in node.args.args:
        if arg.arg in common_fixtures or arg.arg.startswith("mock_"):
            return True

    return False


def detect_edge_cases_from_analysis(
    analysis_results: dict[str, Any], project_dir: Path
) -> list[dict[str, Any]]:
    """
    Detect edge cases from code analysis results for test generation.

    This function extracts or detects edge case patterns from source code to guide
    the AI agent in generating comprehensive tests. It prioritizes edge_cases already
    present in analysis_results (from CodeAnalyzer or TypeScriptAnalyzer), and falls
    back to AST-based detection for Python source files.

    Detected edge cases include:
    - Error handling (try/except blocks)
    - Boundary conditions (None checks, numeric boundaries, empty checks)
    - Type validation (isinstance checks)
    - Error raising (raise statements)
    - Assertions

    Args:
        analysis_results: Code analysis results from CodeAnalyzer or TypeScriptAnalyzer
        project_dir: Root project directory for reading source files

    Returns:
        List of edge case dictionaries with keys:
        - type: Category of edge case (error_handling, boundary_condition, type_validation, etc.)
        - pattern: Specific pattern detected (try/except, none_check, isinstance_check, etc.)
        - lineno: Line number where pattern was found
        - description: Human-readable description of the edge case
        - file: Source file where edge case was found (if available)
    """
    # First, check if edge_cases are already in the analysis results
    if "edge_cases" in analysis_results and analysis_results["edge_cases"]:
        return analysis_results["edge_cases"]

    edge_cases = []

    # If we have analyzed_files in the results, detect edge cases from Python sources
    analyzed_files = list(analysis_results.get("analyzed_files", []))
    if not analyzed_files:
        # Try to extract file paths from functions/classes
        seen_files: set[str] = set()
        for func in analysis_results.get("functions", []):
            if "file" in func:
                file_path = func["file"]
                if file_path not in seen_files:
                    seen_files.add(file_path)
                    analyzed_files.append(file_path)
        for cls in analysis_results.get("classes", []):
            if "file" in cls:
                file_path = cls["file"]
                if file_path not in seen_files:
                    seen_files.add(file_path)
                    analyzed_files.append(file_path)

    # Detect edge cases from Python source files
    for file_path in analyzed_files:
        # Only process Python files
        if not str(file_path).endswith(".py"):
            continue

        full_path = project_dir / file_path
        if not full_path.exists():
            logger.debug(f"Source file not found: {full_path}")
            continue

        try:
            source = full_path.read_text(encoding="utf-8")
            tree = ast.parse(source)

            # Detect edge cases in this file
            file_edge_cases = _detect_edge_cases_from_ast(tree, str(file_path))
            edge_cases.extend(file_edge_cases)

        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Failed to detect edge cases in {file_path}: {e}")

    return edge_cases


def _detect_edge_cases_from_ast(tree: ast.AST, file_path: str) -> list[dict[str, Any]]:
    """
    Detect edge case patterns from Python AST.

    This is a simplified version of CodeAnalyzer._detect_edge_cases() that
    focuses on patterns most relevant for test generation.

    Args:
        tree: AST tree of the source code
        file_path: Path to the source file

    Returns:
        List of edge case dictionaries
    """
    edge_cases: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            edge_cases.extend(_detect_try_except_patterns(node, file_path))
        elif isinstance(node, ast.Compare):
            edge_cases.extend(_detect_comparison_patterns(node, file_path))
        elif isinstance(node, ast.Call):
            edge_cases.extend(_detect_isinstance_patterns(node, file_path))
        elif isinstance(node, ast.Raise):
            edge_cases.extend(_detect_raise_patterns(node, file_path))
        elif isinstance(node, ast.Assert):
            edge_cases.extend(_detect_assert_patterns(node, file_path))

    return edge_cases


def _detect_try_except_patterns(node: ast.Try, file_path: str) -> list[dict[str, Any]]:
    """Detect error handling patterns from try/except blocks."""
    results = []
    for handler in node.handlers:
        exc_type = "Exception"
        if handler.type:
            if isinstance(handler.type, ast.Name):
                exc_type = handler.type.id
            elif isinstance(handler.type, ast.Attribute):
                exc_type = ast.unparse(handler.type)
        results.append(
            {
                "type": "error_handling",
                "pattern": f"try/except {exc_type}",
                "lineno": node.lineno,
                "description": f"Handles {exc_type} exceptions",
                "file": file_path,
            }
        )
    return results


def _detect_comparison_patterns(
    node: ast.Compare, file_path: str
) -> list[dict[str, Any]]:
    """Detect boundary conditions from comparison nodes."""
    code = ast.unparse(node)

    if "None" in code:
        return [
            {
                "type": "boundary_condition",
                "pattern": "none_check",
                "lineno": node.lineno,
                "description": f"None check: {code}",
                "file": file_path,
            }
        ]

    if any(op in code for op in ["< 0", "> 0", "== 0", "<= 0", ">= 0"]):
        return [
            {
                "type": "boundary_condition",
                "pattern": "numeric_boundary",
                "lineno": node.lineno,
                "description": f"Numeric boundary: {code}",
                "file": file_path,
            }
        ]

    if "len(" in code and any(op in code for op in ["== 0", "> 0", "< 1"]):
        return [
            {
                "type": "boundary_condition",
                "pattern": "empty_check",
                "lineno": node.lineno,
                "description": f"Empty check: {code}",
                "file": file_path,
            }
        ]

    return []


def _detect_isinstance_patterns(node: ast.Call, file_path: str) -> list[dict[str, Any]]:
    """Detect isinstance type validation calls."""
    if not (isinstance(node.func, ast.Name) and node.func.id == "isinstance"):
        return []
    if len(node.args) < 2:
        return []

    type_check = ast.unparse(node.args[1])
    return [
        {
            "type": "type_validation",
            "pattern": "isinstance_check",
            "lineno": node.lineno,
            "description": f"Type check: isinstance(..., {type_check})",
            "file": file_path,
        }
    ]


def _detect_raise_patterns(node: ast.Raise, file_path: str) -> list[dict[str, Any]]:
    """Detect explicit error raising patterns."""
    exc_type = "Exception"
    if node.exc:
        if isinstance(node.exc, ast.Call) and isinstance(node.exc.func, ast.Name):
            exc_type = node.exc.func.id
        elif isinstance(node.exc, ast.Name):
            exc_type = node.exc.id

    return [
        {
            "type": "error_raising",
            "pattern": f"raise {exc_type}",
            "lineno": node.lineno,
            "description": f"Raises {exc_type}",
            "file": file_path,
        }
    ]


def _detect_assert_patterns(node: ast.Assert, file_path: str) -> list[dict[str, Any]]:
    """Detect assertion patterns."""
    test_code = ast.unparse(node.test)
    return [
        {
            "type": "assertion",
            "pattern": "assert",
            "lineno": node.lineno,
            "description": f"Assertion: {test_code}",
            "file": file_path,
        }
    ]


def _check_edge_case_coverage(node: ast.FunctionDef, source: str) -> dict[str, Any]:
    """
    Check if test covers edge cases.

    Looks for patterns like:
    - Testing with None/empty inputs
    - Testing exceptions
    - Boundary values
    - Multiple scenarios in one test

    Args:
        node: AST function node
        source: Source code of the file

    Returns:
        Dictionary with has_edge_cases and should_have_edge_cases flags
    """
    has_edge_cases = False

    # Check for exception testing
    for child in ast.walk(node):
        if isinstance(child, ast.With) or isinstance(child, ast.Try):
            # Check if using pytest.raises
            if isinstance(child, ast.With) or isinstance(child, ast.Try):
                has_edge_cases = True
                break

    # Check for edge case patterns in test name
    edge_case_keywords = [
        "none",
        "null",
        "empty",
        "zero",
        "negative",
        "invalid",
        "error",
        "exception",
        "boundary",
        "limit",
        "max",
        "min",
    ]

    test_name_lower = node.name.lower()
    for keyword in edge_case_keywords:
        if keyword in test_name_lower:
            has_edge_cases = True
            break

    # Tests should have edge cases if they're testing core logic
    # (heuristic: non-trivial tests should consider edge cases)
    should_have_edge_cases = len(node.body) > 3

    return {
        "has_edge_cases": has_edge_cases,
        "should_have_edge_cases": should_have_edge_cases,
    }


def _check_mocking_quality(node: ast.FunctionDef) -> dict[str, Any]:
    """
    Check if test uses mocking appropriately.

    Looks for:
    - Over-mocking (mocking everything)
    - Missing assertions on mocks
    - Proper use of patch decorators

    Args:
        node: AST function node

    Returns:
        Dictionary with has_mocks and proper_usage flags
    """
    has_mocks = False
    proper_usage = True
    issues = []

    # Check for mock-related decorators
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call):
            # Check for @patch, @mock.patch
            if hasattr(decorator.func, "id") and "patch" in decorator.func.id:
                has_mocks = True

    # Check for mock.patch usage in function body
    for child in ast.walk(node):
        if isinstance(child, ast.With):
            for item in child.items:
                if (
                    hasattr(item.context_expr, "func")
                    and hasattr(item.context_expr.func, "id")
                    and "patch" in item.context_expr.func.id
                ):
                    has_mocks = True

    # Check for mock variables
    mock_var_count = 0
    for arg in node.args.args:
        if "mock" in arg.arg.lower():
            mock_var_count += 1

    if mock_var_count > 3:
        proper_usage = False
        issues.append("Test uses too many mocks (may be over-mocked)")

    if has_mocks and mock_var_count == 0:
        # Has patches but no mock arguments - might be unused
        proper_usage = False
        issues.append("Mocking detected but mock objects not used in assertions")

    return {
        "has_mocks": has_mocks or mock_var_count > 0,
        "proper_usage": proper_usage,
        "message": "; ".join(issues) if issues else "",
    }


def _calculate_quality_score(metrics: Any, issue_count: int) -> float:
    """
    Calculate overall quality score from metrics.

    Args:
        metrics: TestMetrics object
        issue_count: Number of issues found

    Returns:
        Quality score (0-100)
    """
    if metrics.total_tests == 0:
        return 0.0

    score = 0.0

    # Assertion coverage (40 points)
    assertion_coverage = (metrics.tests_with_assertions / metrics.total_tests) * 40
    score += assertion_coverage

    # Naming conventions (15 points)
    naming_score = (metrics.tests_properly_named / metrics.total_tests) * 15
    score += naming_score

    # Docstring coverage (10 points)
    docstring_score = (metrics.tests_with_docstrings / metrics.total_tests) * 10
    score += docstring_score

    # Edge case coverage (15 points)
    edge_case_score = (metrics.tests_with_edge_cases / metrics.total_tests) * 15
    score += edge_case_score

    # Base score for having tests (20 points)
    score += 20

    # Deduct points for issues
    deduction = min(issue_count * 2, 30)
    score -= deduction

    return max(0.0, min(100.0, score))


async def generate_integration_tests(
    project_dir: Path,
    spec_dir: Path,
    analysis_results: dict[str, Any],
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run Integration Test Generator Agent session to generate integration tests for API endpoints.

    Integration tests validate that multiple components work together correctly,
    such as API endpoints interacting with databases, services, and external dependencies.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        analysis_results: Code analysis results (should include API endpoints, routes, etc.)
        model: Claude model to use (defaults to phase config)
        max_thinking_tokens: Extended thinking token budget (optional)
        verbose: Whether to show detailed output

    Returns:
        Dictionary with:
        - generated_files: List of generated test file paths (relative to project_dir)
        - success: Whether generation succeeded
        - error: Error message if failed
        - framework: Test framework used ("integration-pytest")
    """
    starting_message = _INTEGRATION_TEST_STARTING_MESSAGE.format(
        analysis_json=json.dumps(analysis_results, indent=2)
    )

    # Run the shared generator session boilerplate
    endpoints_count = len(analysis_results.get("endpoints", []))
    routes_count = len(analysis_results.get("routes", []))
    services_count = len(analysis_results.get("services", []))

    session_result = await run_generator_session(
        project_dir=project_dir,
        spec_dir=spec_dir,
        analysis_results=analysis_results,
        session_title="INTEGRATION TEST GENERATOR SESSION",
        session_description="Generating integration tests for API endpoints and services...",
        prompt_name="test_generator",  # Reuse test_generator prompt
        agent_type="test_generator",
        session_name="integration-test-generator-session",
        starting_message=starting_message,
        log_phase=LogPhase.VALIDATION,
        log_summary=(
            f"Analyzing {endpoints_count} endpoints, "
            f"{routes_count} routes, "
            f"{services_count} services for integration tests"
        ),
        model=model,
        max_thinking_tokens=max_thinking_tokens,
        verbose=verbose,
    )

    framework = "integration-pytest"

    if not session_result["success"]:
        return {
            "generated_files": [],
            "success": False,
            "error": session_result["error"],
            "framework": framework,
        }

    # Scan tests/integration/ directory for newly created test files
    print()
    print_status("Scanning for generated integration test files...", "progress")

    test_files: list[Path] = []
    tests_integration_dir = project_dir / "tests" / "integration"
    if tests_integration_dir.exists():
        for test_file in tests_integration_dir.glob("test_integration_*.py"):
            test_files.append(test_file.relative_to(project_dir))
    else:
        # Try to find integration tests in the main tests/ directory
        tests_dir = project_dir / "tests"
        if tests_dir.exists():
            for test_file in tests_dir.glob("test_integration_*.py"):
                test_files.append(test_file.relative_to(project_dir))
            if test_files:
                print_status(
                    f"Found {len(test_files)} integration tests in tests/", "success"
                )
        else:
            return {
                "generated_files": [],
                "success": False,
                "error": "tests/ directory not found",
                "framework": framework,
            }

    if not test_files:
        logger.warning("No integration test files were generated")
        print_status("No integration test files found", "warning")
        return {
            "generated_files": [],
            "success": False,
            "error": "No test files generated",
            "framework": framework,
        }

    print_key_value("Generated files", str(len(test_files)))
    for test_file in test_files:
        print(f"  {muted('•')} {test_file}")
    print()

    # Validate generated tests
    validation_success = await validate_python_tests(
        test_files, project_dir, label="Integration"
    )

    # Log results
    log_generator_result(
        spec_dir=spec_dir,
        test_files=test_files,
        validation_success=validation_success,
        framework="Integration",
    )

    return {
        "generated_files": [str(f) for f in test_files],
        "success": validation_success,
        "error": None if validation_success else "Test validation failed",
        "framework": framework,
    }


async def run_test_generator_session(
    project_dir: Path,
    spec_dir: Path,
    analysis_results: dict[str, Any],
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
    generate_fixtures_first: bool = True,
) -> dict[str, Any]:
    """
    Run Test Generator Agent session to generate tests for analyzed code.

    Automatically detects the appropriate test framework (pytest or vitest)
    based on the code analysis results and routes to the corresponding generator.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        analysis_results: Code analysis results from CodeAnalyzer or TypeScriptAnalyzer
        model: Claude model to use (defaults to phase config)
        max_thinking_tokens: Extended thinking token budget (optional)
        verbose: Whether to show detailed output
        generate_fixtures_first: Whether to generate fixtures before tests (default: True)

    Returns:
        Dictionary with:
        - generated_files: List of generated test file paths (relative to project_dir)
        - success: Whether generation succeeded
        - error: Error message if failed
        - framework: Test framework used ("pytest" or "vitest")
    """
    # Detect which test framework to use
    framework = detect_test_framework(analysis_results)
    logger.info(f"Detected test framework: {framework}")

    # Route to the appropriate generator
    if framework == "vitest":
        logger.info("Routing to Vitest generator for TypeScript/React tests")
        result = await generate_vitest_tests(
            project_dir=project_dir,
            spec_dir=spec_dir,
            analysis_results=analysis_results,
            model=model,
            max_thinking_tokens=max_thinking_tokens,
            verbose=verbose,
        )
        result["framework"] = "vitest"
        return result

    # Default to pytest for Python tests
    logger.info("Routing to pytest generator for Python tests")

    # Initialize task logger
    task_logger = get_task_logger(spec_dir)

    # Print session header
    content = [
        bold(f"{icon(Icons.SPARKLES)} TEST GENERATOR SESSION"),
        "",
        f"Spec: {highlight(spec_dir.name)}",
        muted("Generating pytest tests for analyzed code..."),
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print()

    # Emit TEST_GENERATION phase
    emit_phase(ExecutionPhase.TEST_GENERATION, "Generating pytest tests")

    # Determine model and thinking budget
    # Test generation is part of the QA phase
    if model is None:
        model = get_phase_model(spec_dir, "qa")
    if max_thinking_tokens is None:
        max_thinking_tokens = get_phase_thinking_budget(spec_dir, "qa")

    print_key_value("Model", model)
    print_key_value(
        "Thinking budget",
        str(max_thinking_tokens) if max_thinking_tokens else "Default",
    )
    print()

    # Log session start
    if task_logger:
        task_logger.start_phase(LogPhase.CODING, "Starting test generation...")
        task_logger.log_info(
            f"Analyzing {len(analysis_results.get('functions', []))} functions, "
            f"{len(analysis_results.get('classes', []))} classes",
        )

    # Load coverage configuration
    coverage_config: CoverageConfig | None = None
    try:
        coverage_config = load_coverage_config(project_dir, spec_dir)
        print_key_value("Min coverage", f"{coverage_config.minimum_coverage:.0f}%")
    except Exception as e:
        logger.warning(f"Failed to load coverage config: {e}")

    # Generate fixtures first if requested
    fixture_files = []
    if generate_fixtures_first:
        print()
        print_status("Generating test fixtures...", "progress")
        try:
            fixture_result = await generate_fixtures(
                project_dir=project_dir,
                spec_dir=spec_dir,
                analysis_results=analysis_results,
                model=model,
                max_thinking_tokens=max_thinking_tokens,
                verbose=verbose,
            )

            if fixture_result["success"] and fixture_result.get("generated_files"):
                fixture_files = fixture_result["generated_files"]
                print_key_value("Fixture files", str(len(fixture_files)))
                for fixture_file in fixture_files:
                    print(f"  {muted('•')} {fixture_file}")
            elif not fixture_result["success"]:
                logger.warning(
                    f"Fixture generation failed: {fixture_result.get('error')}"
                )
                print_status(
                    f"Fixture generation failed: {fixture_result.get('error')}",
                    "warning",
                )
            else:
                logger.info("No fixtures were generated")
                print_status("No fixtures were generated", "info")

        except Exception as e:
            error_msg = f"Fixture generation failed with exception: {e}"
            logger.warning(error_msg)
            print_status(error_msg, "warning")

    print()

    # Load the test generator prompt
    try:
        prompt = get_agent_prompt("test_generator")
    except Exception as e:
        error_msg = f"Failed to load test_generator prompt: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_error(error_msg)
        return {"generated_files": [], "success": False, "error": error_msg}

    # Create the starting message with analysis results
    starting_message = f"""You are the Test Generator Agent. Your task is to generate comprehensive pytest tests based on the code analysis results below.

## Code Analysis Results

{json.dumps(analysis_results, indent=2)}

## Your Task

1. Read the spec.md to understand what was implemented
2. Review the implementation_plan.json to see what features were built
3. Study existing test patterns in tests/conftest.py and tests/test_*.py
4. Generate pytest test files for the functions and classes above
5. Ensure tests cover edge cases detected in the analysis
6. Follow the project's testing conventions
7. Aim for {coverage_config.minimum_coverage if coverage_config else 80.0:.0f}%+ code coverage

Generate test files in the tests/ directory following the naming convention test_*.py.

Begin by loading context (Phase 0 in your prompt).
"""

    # Create SDK client with test_generator agent type
    try:
        client = create_client(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            agent_type="test_generator",
            max_thinking_tokens=max_thinking_tokens,
        )
    except Exception as e:
        error_msg = f"Failed to create Claude SDK client: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_error(error_msg)
        return {"generated_files": [], "success": False, "error": error_msg}

    # Run the agent session.
    #
    # ClaudeSDKClient has no `create_agent_session` method — agent turns are
    # driven by run_agent_session() (agents/session.py) inside `async with
    # client`. The agent role prompt leads the message since the SDK client
    # only carries the generic base system prompt.
    from .session import run_agent_session

    print_status("Running Test Generator Agent...", "progress")
    try:
        session_message = f"{prompt}\n\n{starting_message}"
        async with client:
            status, response, _usage, _decisions = await run_agent_session(
                client=client,
                message=session_message,
                spec_dir=spec_dir,
                verbose=verbose,
                phase=LogPhase.CODING,
            )

        if status == "error":
            error_msg = f"Test Generator Agent session failed: {response}"
            logger.error(error_msg)
            if task_logger:
                task_logger.log_error(error_msg)
            return {"generated_files": [], "success": False, "error": error_msg}

        if verbose:
            logger.info(f"Test Generator Agent response: {response}")

        # Log session completion
        if task_logger:
            task_logger.log_success("Test Generator Agent session completed")

    except Exception as e:
        error_msg = f"Test Generator Agent session failed: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_error(error_msg)
        return {"generated_files": [], "success": False, "error": error_msg}

    # Scan tests/ directory for newly created test files
    print()
    print_status("Scanning for generated test files...", "progress")

    tests_dir = project_dir / "tests"
    if not tests_dir.exists():
        logger.warning("tests/ directory not found")
        return {
            "generated_files": [],
            "success": False,
            "error": "tests/ directory not found",
        }

    # Find all test_*.py files (exclude conftest.py)
    test_files = []
    for test_file in tests_dir.glob("test_*.py"):
        relative_path = test_file.relative_to(project_dir)
        test_files.append(relative_path)

    if not test_files:
        logger.warning("No test files were generated")
        print_status("No test files found in tests/", "warning")
        return {
            "generated_files": [],
            "success": False,
            "error": "No test files generated",
        }

    print_key_value("Generated files", str(len(test_files)))
    for test_file in test_files:
        print(f"  {muted('•')} {test_file}")
    print()

    # Validate generated tests
    validation_success = validate_generated_tests(test_files, project_dir, "pytest")

    if not validation_success:
        if task_logger:
            task_logger.log_entry(
                LogEntryType.WARNING,
                f"Generated {len(test_files)} test files but validation failed",
            )
        return {
            "generated_files": [str(f) for f in test_files],
            "success": False,
            "error": "Test validation failed",
            "coverage_analyzed": False,
        }

    print()

    # Run coverage analysis to identify gaps
    print()
    print_status("Analyzing coverage gaps...", "progress")
    coverage_result, gaps_summary = analyze_coverage_gaps(
        project_dir=project_dir,
        config=coverage_config,
    )

    # Check if there are significant coverage gaps
    needs_improvement = False
    if coverage_result and coverage_result.success:
        # If coverage is below threshold or there are critical gaps, improve tests
        min_threshold = coverage_config.minimum_coverage if coverage_config else 80.0
        if (
            coverage_result.total_coverage < min_threshold
            or len(gaps_summary.get("critical_gaps", [])) > 0
        ):
            needs_improvement = True

            print()
            print_status(
                "Coverage gaps detected - running improvement iteration...", "warning"
            )
            print()

            # Format coverage gaps for AI agent
            gaps_prompt = format_coverage_gaps_prompt(gaps_summary)

            # Create improvement message
            improvement_message = f"""{gaps_prompt}

## Your Task

Review the coverage gaps above and generate additional test cases to cover the missing lines.

**Important:**
- Focus on the specific line numbers that are NOT covered
- Add tests that exercise the missing code paths
- Pay special attention to critical gaps (files significantly below threshold)
- Do NOT modify existing tests - only add new test cases
- Use the same test files you created earlier (append new test functions)

Generate additional test cases to improve coverage to at least {min_threshold:.0f}%.
"""

            # Run improvement iteration. A fresh connected session (the prior
            # `async with client` above already disconnected) — the
            # improvement_message is self-contained and the agent re-reads the
            # test files it wrote earlier from disk.
            try:
                print_status(
                    "Running Test Generator Agent improvement iteration...", "progress"
                )
                improvement_session_message = f"{prompt}\n\n{improvement_message}"
                async with client:
                    status, response, _usage, _decisions = await run_agent_session(
                        client=client,
                        message=improvement_session_message,
                        spec_dir=spec_dir,
                        verbose=verbose,
                        phase=LogPhase.CODING,
                    )

                if status == "error":
                    # Non-fatal: keep the tests already generated above.
                    logger.warning(f"Test improvement iteration failed: {response}")
                    print_status(f"Improvement iteration failed: {response}", "warning")

                if verbose:
                    logger.info(f"Test Generator improvement response: {response}")

                # Log improvement session
                if task_logger:
                    task_logger.log_entry(
                        LogEntryType.INFO,
                        "Test improvement iteration completed",
                    )

                # Re-scan for new/updated test files
                print()
                print_status("Re-scanning for updated test files...", "progress")
                updated_test_files = []
                existing_paths = {f for f in test_files}
                for test_file in tests_dir.glob("test_*.py"):
                    relative_path = test_file.relative_to(project_dir)
                    if relative_path not in existing_paths:
                        updated_test_files.append(relative_path)

                if updated_test_files:
                    print_key_value("New/updated files", str(len(updated_test_files)))
                    for test_file in updated_test_files:
                        print(f"  {muted('•')} {test_file}")
                    print()

                # Re-validate after improvement
                if updated_test_files:
                    print_status("Re-validating tests after improvement...", "progress")
                    validation_success = validate_generated_tests(
                        updated_test_files, project_dir
                    )

                    # Re-run coverage analysis
                    print()
                    print_status(
                        "Re-analyzing coverage after improvement...", "progress"
                    )
                    coverage_result, gaps_summary = analyze_coverage_gaps(
                        project_dir=project_dir,
                        config=coverage_config,
                    )

                    if coverage_result and coverage_result.success:
                        print_key_value(
                            "Updated coverage", f"{coverage_result.total_coverage:.1f}%"
                        )

            except Exception as e:
                error_msg = f"Test improvement iteration failed: {e}"
                logger.error(error_msg)
                if task_logger:
                    task_logger.log_entry(LogEntryType.ERROR, error_msg)
                # Don't fail completely - return original tests
                print_status(f"Improvement iteration failed: {e}", "warning")

    # Log results
    if task_logger:
        if validation_success:
            if coverage_result and coverage_result.success:
                task_logger.log_entry(
                    LogEntryType.SUCCESS,
                    f"Generated {len(test_files)} test files, "
                    f"coverage: {coverage_result.total_coverage:.1f}%, "
                    f"gaps improved: {needs_improvement}",
                )
            else:
                task_logger.log_entry(
                    LogEntryType.SUCCESS,
                    f"Generated and validated {len(test_files)} test files",
                )
        else:
            task_logger.log_entry(
                LogEntryType.WARNING,
                f"Generated {len(test_files)} test files but validation failed",
            )

    return {
        "generated_files": [str(f) for f in test_files],
        "fixture_files": fixture_files,
        "success": validation_success,
        "error": None if validation_success else "Test validation failed",
        "framework": "pytest",
        "coverage_analyzed": coverage_result is not None and coverage_result.success,
        "coverage_percent": coverage_result.total_coverage if coverage_result else None,
        "coverage_gaps": len(gaps_summary.get("files_with_gaps", []))
        if gaps_summary
        else 0,
    }
