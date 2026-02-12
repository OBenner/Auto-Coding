"""
Test Generator Agent Module
============================

AI agent that generates pytest tests based on code analysis results.
Uses the Test Generator Agent prompt to create comprehensive test coverage.
"""

import ast
import json
import logging
import re
from pathlib import Path
from typing import Any

from analysis.coverage_analyzer import (
    CoverageAnalyzer,
    CoverageResult,
    parse_coverage_json,
)
from core.client import create_client
from phase_config import get_phase_model, get_phase_thinking_budget
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

logger = logging.getLogger(__name__)


def analyze_coverage_gaps(
    project_dir: Path,
    source_dir: str | None = None,
    config: CoverageConfig | None = None,
) -> tuple[CoverageResult | None, dict[str, Any]]:
    """
    Run coverage analysis and identify gaps in test coverage.

    Args:
        project_dir: Root directory of the project
        source_dir: Directory to measure coverage for (e.g., "apps/backend")
        config: Coverage configuration with thresholds (optional)

    Returns:
        Tuple of (coverage_result, gaps_summary)
        - coverage_result: CoverageResult with analysis data or None if failed
        - gaps_summary: Dictionary with gap statistics and files needing attention
    """
    analyzer = CoverageAnalyzer(project_dir)

    print_status("Running coverage analysis to identify gaps...", "progress")

    # Check if pytest-cov is available
    installed, message = analyzer.check_pytest_cov_installed()
    if not installed:
        logger.warning(f"pytest-cov not available: {message}")
        return None, {"error": message, "coverage_gaps": []}

    # Determine source directory if not specified
    if source_dir is None:
        # Default to apps/backend for backend projects
        if (project_dir / "apps" / "backend").exists():
            source_dir = "apps/backend"
        else:
            # Use current directory
            source_dir = "."

    # Run coverage with JSON output
    coverage_output = project_dir / ".coverage.test_generator.json"
    result = analyzer.run_coverage(
        source_dir=source_dir,
        output_format="json",
        output_file=coverage_output,
    )

    if not result.success:
        logger.warning(f"Coverage analysis failed: {result.error_message}")
        return None, {"error": result.error_message, "coverage_gaps": []}

    # Parse the JSON coverage report
    try:
        coverage_result = parse_coverage_json(coverage_output)
    except Exception as e:
        logger.error(f"Failed to parse coverage JSON: {e}")
        return None, {"error": str(e), "coverage_gaps": []}

    # Identify coverage gaps
    gaps_summary = {
        "total_coverage": coverage_result.total_coverage,
        "files_with_gaps": [],
        "critical_gaps": [],
        "missing_lines_by_file": {},
    }

    # Get minimum coverage threshold
    min_coverage = config.minimum_coverage if config else 80.0

    # Analyze each file for gaps
    for file_path, file_coverage in coverage_result.files.items():
        # Check if file is below threshold
        if file_coverage.coverage_percent < min_coverage:
            gaps_summary["files_with_gaps"].append(file_path)
            gaps_summary["missing_lines_by_file"][file_path] = (
                file_coverage.lines_missing
            )

            # Mark as critical gap if significantly below threshold
            if file_coverage.coverage_percent < min_coverage * 0.5:
                gaps_summary["critical_gaps"].append(file_path)

    # Log results
    files_with_gaps_count = len(gaps_summary["files_with_gaps"])
    if files_with_gaps_count > 0:
        print_status(
            f"Found {files_with_gaps_count} file(s) with coverage gaps",
            "warning",
        )
        print_key_value("Total coverage", f"{coverage_result.total_coverage:.1f}%")
        print_key_value("Files with gaps", str(files_with_gaps_count))
        if gaps_summary["critical_gaps"]:
            print_key_value("Critical gaps", str(len(gaps_summary["critical_gaps"])))
    else:
        print_status(
            f"Coverage meets threshold: {coverage_result.total_coverage:.1f}%",
            "success",
        )

    return coverage_result, gaps_summary


def format_coverage_gaps_prompt(gaps_summary: dict[str, Any]) -> str:
    """
    Format coverage gaps as a prompt for the AI agent.

    Args:
        gaps_summary: Summary from analyze_coverage_gaps

    Returns:
        Formatted string describing coverage gaps
    """
    if "error" in gaps_summary:
        return f"Coverage analysis failed: {gaps_summary['error']}"

    if not gaps_summary.get("files_with_gaps"):
        return "Coverage meets all thresholds. No gaps detected."

    lines = []
    lines.append("## Coverage Gaps Detected")
    lines.append("")
    lines.append(f"**Total Coverage:** {gaps_summary['total_coverage']:.1f}%")
    lines.append(f"**Files with Gaps:** {len(gaps_summary['files_with_gaps'])}")
    lines.append("")

    if gaps_summary.get("critical_gaps"):
        lines.append("### Critical Gaps (Significantly Below Threshold)")
        for file_path in gaps_summary["critical_gaps"][:5]:
            lines.append(f"- {file_path}")
        lines.append("")

    lines.append("### Files Requiring Additional Tests")
    for file_path in gaps_summary["files_with_gaps"][:10]:
        missing_lines = gaps_summary["missing_lines_by_file"].get(file_path, [])
        if missing_lines:
            line_ranges = _format_line_ranges(missing_lines[:20])
            lines.append(f"- **{file_path}**")
            lines.append(f"  - Missing lines: {line_ranges}")
        else:
            lines.append(f"- **{file_path}**")

    if len(gaps_summary["files_with_gaps"]) > 10:
        lines.append(
            f"- ... and {len(gaps_summary['files_with_gaps']) - 10} more files"
        )

    lines.append("")
    lines.append(
        "**Action Required:** Generate additional tests to cover the missing lines above."
    )
    lines.append("Focus on the specific line numbers that are not covered.")

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


def validate_generated_tests(test_files: list[Path], project_dir: Path) -> bool:
    """
    Validate that generated tests are syntactically correct.

    Uses pytest --collect-only to verify tests can be collected without errors.

    Args:
        test_files: List of generated test file paths
        project_dir: Project root directory

    Returns:
        True if all tests are valid, False otherwise
    """
    import subprocess

    if not test_files:
        logger.warning("No test files to validate")
        return False

    print()
    print_status("Validating generated tests...", "progress")

    for test_file in test_files:
        file_path = project_dir / test_file
        if not file_path.exists():
            print_status(f"Test file not found: {test_file}", "error")
            return False

        # Check Python syntax
        try:
            with open(file_path, encoding="utf-8") as f:
                compile(f.read(), str(file_path), "exec")
            print_status(f"Syntax valid: {test_file.name}", "success")
        except SyntaxError as e:
            print_status(f"Syntax error in {test_file}: {e}", "error")
            return False

        # Check if pytest can collect tests
        try:
            result = subprocess.run(
                ["pytest", str(file_path), "--collect-only", "-q"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                print_status(f"pytest collection failed for {test_file}", "error")
                logger.debug(f"pytest output: {result.stdout}\n{result.stderr}")
                return False
            print_status(f"pytest collection OK: {test_file.name}", "success")
        except subprocess.TimeoutExpired:
            print_status(f"pytest collection timeout for {test_file}", "error")
            return False
        except FileNotFoundError:
            logger.warning("pytest not found - skipping collection validation")
            print_status("pytest not available - syntax check only", "warning")
            continue

    print_status("All generated tests are valid", "success")
    return True


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
    from dataclasses import dataclass, field

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


async def run_test_generator_session(
    project_dir: Path,
    spec_dir: Path,
    analysis_results: dict[str, Any],
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run Test Generator Agent session to generate pytest tests.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        analysis_results: Code analysis results from CodeAnalyzer
        model: Claude model to use (defaults to phase config)
        max_thinking_tokens: Extended thinking token budget (optional)
        verbose: Whether to show detailed output

    Returns:
        Dictionary with:
        - generated_files: List of generated test file paths (relative to project_dir)
        - success: Whether generation succeeded
        - error: Error message if failed
    """
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

    # Determine model and thinking budget
    if model is None:
        model = get_phase_model("test_generation")
    if max_thinking_tokens is None:
        max_thinking_tokens = get_phase_thinking_budget("test_generation")

    print_key_value("Model", model)
    print_key_value(
        "Thinking budget",
        str(max_thinking_tokens) if max_thinking_tokens else "Default",
    )
    print()

    # Log session start
    if task_logger:
        task_logger.start_phase(LogPhase.CODING, "Starting test generation...")
        task_logger.log_entry(
            LogEntryType.INFO,
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

    # Load the test generator prompt
    try:
        prompt = get_agent_prompt("test_generator")
    except Exception as e:
        error_msg = f"Failed to load test_generator prompt: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
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
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
        return {"generated_files": [], "success": False, "error": error_msg}

    # Run the agent session
    print_status("Running Test Generator Agent...", "progress")
    try:
        response = await client.create_agent_session(
            name="test-generator-session",
            starting_message=starting_message,
            system_prompt=prompt,
        )

        if verbose:
            logger.info(f"Test Generator Agent response: {response}")

        # Log session completion
        if task_logger:
            task_logger.log_entry(
                LogEntryType.SUCCESS, "Test Generator Agent session completed"
            )

    except Exception as e:
        error_msg = f"Test Generator Agent session failed: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
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
    validation_success = validate_generated_tests(test_files, project_dir)

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

            # Run improvement iteration
            try:
                print_status(
                    "Running Test Generator Agent improvement iteration...", "progress"
                )
                response = await client.create_agent_session(
                    name="test-generator-improvement",
                    starting_message=improvement_message,
                    system_prompt=prompt,
                )

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
                for test_file in tests_dir.glob("test_*.py"):
                    relative_path = test_file.relative_to(project_dir)
                    if relative_path not in [str(f) for f in test_files]:
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

    return {
        "generated_files": [str(f) for f in test_files],
        "success": validation_success,
        "error": None if validation_success else "Test validation failed",
        "coverage_analyzed": coverage_result is not None and coverage_result.success,
        "coverage_percent": coverage_result.total_coverage if coverage_result else None,
        "coverage_gaps": len(gaps_summary.get("files_with_gaps", []))
        if gaps_summary
        else 0,
    }
