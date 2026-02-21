"""
QA Coverage Validator
=====================

Validates test coverage meets minimum thresholds and enforces critical path requirements.
Used by QA Reviewer to ensure adequate test coverage before approving builds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from analysis.coverage_analyzer import CoverageResult
from spec.coverage_config import (
    CoverageConfig,
    CriticalPath,
    get_minimum_coverage_for_file,
    matches_pattern,
)

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class CoverageIssue:
    """
    Represents a coverage validation issue.

    Attributes:
        file_path: Path to the file with insufficient coverage
        actual_coverage: Actual coverage percentage for this file
        required_coverage: Required coverage percentage
        issue_type: Type of issue (overall, line, branch, critical_path)
        message: Human-readable description of the issue
        missing_lines: Line numbers not covered by tests (if applicable)
    """

    file_path: str
    actual_coverage: float
    required_coverage: float
    issue_type: str
    message: str
    missing_lines: list[int] = field(default_factory=list)


@dataclass
class ValidationResult:
    """
    Result of coverage validation.

    Attributes:
        passed: Whether validation passed all checks
        overall_coverage: Overall coverage percentage
        required_coverage: Required overall coverage percentage
        issues: List of coverage issues found
        critical_path_failures: Number of critical path failures
        files_checked: Number of files checked
        timestamp: When validation was performed
    """

    passed: bool
    overall_coverage: float
    required_coverage: float
    issues: list[CoverageIssue] = field(default_factory=list)
    critical_path_failures: int = 0
    files_checked: int = 0
    timestamp: str | None = None


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================


def validate_coverage(
    coverage_result: CoverageResult,
    config: CoverageConfig,
    project_dir: str | Path | None = None,
) -> ValidationResult:
    """
    Validate coverage result against configuration thresholds.

    This is the main entry point for coverage validation. It checks:
    1. Overall coverage meets minimum threshold
    2. Line coverage meets minimum (if specified)
    3. Branch coverage meets minimum (if specified)
    4. Critical path files meet their required coverage (typically 100%)

    Args:
        coverage_result: Coverage analysis result to validate
        config: Coverage configuration with thresholds
        project_dir: Project directory for path resolution (optional)

    Returns:
        ValidationResult with pass/fail status and list of issues

    Example:
        result = validate_coverage(coverage_result, config)
        if not result.passed:
            for issue in result.issues:
                print(f"{issue.file_path}: {issue.message}")
    """
    issues: list[CoverageIssue] = []

    # Check if coverage analysis succeeded
    if not coverage_result.success:
        issues.append(
            CoverageIssue(
                file_path="N/A",
                actual_coverage=0.0,
                required_coverage=config.minimum_coverage,
                issue_type="error",
                message=f"Coverage analysis failed: {coverage_result.error_message}",
            )
        )
        return ValidationResult(
            passed=False,
            overall_coverage=0.0,
            required_coverage=config.minimum_coverage,
            issues=issues,
        )

    # Validate overall coverage
    if coverage_result.total_coverage < config.minimum_coverage:
        issues.append(
            CoverageIssue(
                file_path="Overall",
                actual_coverage=coverage_result.total_coverage,
                required_coverage=config.minimum_coverage,
                issue_type="overall",
                message=f"Overall coverage {coverage_result.total_coverage:.1f}% is below minimum {config.minimum_coverage:.1f}%",
            )
        )

    # Validate line coverage if specified
    if config.minimum_line_coverage is not None:
        line_coverage_percent = (
            (coverage_result.lines_covered / coverage_result.lines_total * 100)
            if coverage_result.lines_total > 0
            else 0.0
        )
        if line_coverage_percent < config.minimum_line_coverage:
            issues.append(
                CoverageIssue(
                    file_path="Overall",
                    actual_coverage=line_coverage_percent,
                    required_coverage=config.minimum_line_coverage,
                    issue_type="line",
                    message=f"Line coverage {line_coverage_percent:.1f}% is below minimum {config.minimum_line_coverage:.1f}%",
                )
            )

    # Validate branch coverage if specified
    if (
        config.minimum_branch_coverage is not None
        and coverage_result.branches_total > 0
    ):
        branch_coverage_percent = (
            coverage_result.branches_covered / coverage_result.branches_total * 100
        )
        if branch_coverage_percent < config.minimum_branch_coverage:
            issues.append(
                CoverageIssue(
                    file_path="Overall",
                    actual_coverage=branch_coverage_percent,
                    required_coverage=config.minimum_branch_coverage,
                    issue_type="branch",
                    message=f"Branch coverage {branch_coverage_percent:.1f}% is below minimum {config.minimum_branch_coverage:.1f}%",
                )
            )

    # Validate critical path coverage
    critical_path_failures = _validate_critical_paths(coverage_result, config, issues)

    # Determine overall pass/fail
    # When fail_under_threshold is False, don't enforce thresholds (always pass)
    passed = len(issues) == 0 if config.fail_under_threshold else True

    return ValidationResult(
        passed=passed,
        overall_coverage=coverage_result.total_coverage,
        required_coverage=config.minimum_coverage,
        issues=issues,
        critical_path_failures=critical_path_failures,
        files_checked=len(coverage_result.files),
        timestamp=coverage_result.timestamp,
    )


def _validate_critical_paths(
    coverage_result: CoverageResult,
    config: CoverageConfig,
    issues: list[CoverageIssue],
) -> int:
    """
    Validate that critical path files meet their required coverage.

    Args:
        coverage_result: Coverage analysis result
        config: Coverage configuration with critical paths
        issues: List to append issues to

    Returns:
        Number of critical path failures
    """
    critical_path_failures = 0

    for raw_path, file_coverage in coverage_result.files.items():
        # Normalize to POSIX-style paths for cross-platform matching
        normalized = Path(raw_path).as_posix()

        # Get minimum coverage for this file (100% if critical path)
        required = get_minimum_coverage_for_file(normalized, config)

        # Skip if file doesn't require elevated coverage
        if required <= config.minimum_coverage:
            continue

        # Check if file meets required coverage
        if file_coverage.coverage_percent < required:
            critical_path_failures += 1

            # Find which critical path this matches
            matching_path = _find_matching_critical_path(normalized, config)
            path_name = matching_path.name if matching_path else "Critical path"

            issues.append(
                CoverageIssue(
                    file_path=normalized,
                    actual_coverage=file_coverage.coverage_percent,
                    required_coverage=required,
                    issue_type="critical_path",
                    message=f"{path_name} file '{normalized}' has {file_coverage.coverage_percent:.1f}% coverage, requires {required:.1f}%",
                    missing_lines=file_coverage.lines_missing,
                )
            )

    return critical_path_failures


def _find_matching_critical_path(
    file_path: str, config: CoverageConfig
) -> CriticalPath | None:
    """
    Find the critical path that matches a given file path.

    Args:
        file_path: File path to check
        config: Coverage configuration

    Returns:
        Matching CriticalPath or None
    """
    for critical_path in config.critical_paths:
        if matches_pattern(file_path, critical_path.pattern):
            return critical_path
    return None


# =============================================================================
# REPORTING
# =============================================================================


def format_validation_summary(result: ValidationResult) -> str:
    """
    Format validation result as a human-readable summary.

    Args:
        result: Validation result to format

    Returns:
        Formatted summary string

    Example:
        summary = format_validation_summary(result)
        print(summary)
    """
    lines = []

    # Header
    status = "✓ PASSED" if result.passed else "✗ FAILED"
    lines.append(f"Coverage Validation: {status}")
    lines.append(
        f"Overall Coverage: {result.overall_coverage:.1f}% (required: {result.required_coverage:.1f}%)"
    )
    lines.append(f"Files Checked: {result.files_checked}")
    lines.append("")

    # Issues summary
    if result.issues:
        lines.append(f"Issues Found: {len(result.issues)}")

        # Group by type
        overall_issues = [
            i for i in result.issues if i.issue_type in ("overall", "line", "branch")
        ]
        critical_issues = [i for i in result.issues if i.issue_type == "critical_path"]
        error_issues = [i for i in result.issues if i.issue_type == "error"]

        if error_issues:
            lines.append("\nErrors:")
            for issue in error_issues:
                lines.append(f"  - {issue.message}")

        if overall_issues:
            lines.append("\nOverall Coverage Issues:")
            for issue in overall_issues:
                lines.append(f"  - {issue.message}")

        if critical_issues:
            lines.append(f"\nCritical Path Failures: {len(critical_issues)}")
            for issue in critical_issues[:5]:  # Show first 5
                lines.append(f"  - {issue.message}")
                if issue.missing_lines:
                    lines.append(
                        f"    Missing lines: {_format_line_ranges(issue.missing_lines[:10])}"
                    )
            if len(critical_issues) > 5:
                lines.append(f"  ... and {len(critical_issues) - 5} more")
    else:
        lines.append("No issues found. All coverage thresholds met.")

    return "\n".join(lines)


def _format_line_ranges(line_numbers: list[int]) -> str:
    """
    Format a list of line numbers into compact ranges.

    Args:
        line_numbers: List of line numbers

    Returns:
        Formatted string like "1-5, 10, 15-20"

    Example:
        >>> _format_line_ranges([1, 2, 3, 5, 7, 8, 9])
        "1-3, 5, 7-9"
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


def get_coverage_issues_for_file(
    result: ValidationResult, file_path: str
) -> list[CoverageIssue]:
    """
    Get all coverage issues for a specific file.

    Args:
        result: Validation result
        file_path: Path to the file to check

    Returns:
        List of issues for this file

    Example:
        issues = get_coverage_issues_for_file(result, "apps/backend/auth/login.py")
        for issue in issues:
            print(f"{issue.issue_type}: {issue.message}")
    """
    return [issue for issue in result.issues if issue.file_path == file_path]


def has_critical_path_failures(result: ValidationResult) -> bool:
    """
    Check if validation result has any critical path failures.

    Args:
        result: Validation result

    Returns:
        True if any critical path failures found

    Example:
        if has_critical_path_failures(result):
            print("Critical paths require 100% coverage!")
    """
    return result.critical_path_failures > 0


def format_coverage_report(
    result: ValidationResult,
    coverage_result: CoverageResult,
    show_all_files: bool = False,
    max_missing_lines: int = 20,
) -> str:
    """
    Format a detailed coverage report with missing lines for each file.

    This provides a comprehensive, file-by-file breakdown of coverage issues,
    showing exactly which lines are not covered by tests. Useful for QA
    reporting and helping developers understand where tests are needed.

    Args:
        result: Validation result with issues
        coverage_result: Full coverage analysis result
        show_all_files: If True, show all files (not just those with issues)
        max_missing_lines: Maximum number of missing lines to show per file

    Returns:
        Formatted detailed coverage report

    Example:
        report = format_coverage_report(validation_result, coverage_result)
        with open("coverage_report.txt", "w") as f:
            f.write(report)
    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("DETAILED COVERAGE REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Overall statistics
    status = "✓ PASSED" if result.passed else "✗ FAILED"
    lines.append(f"Status: {status}")
    lines.append(
        f"Overall Coverage: {result.overall_coverage:.1f}% (required: {result.required_coverage:.1f}%)"
    )
    lines.append(f"Files Checked: {result.files_checked}")
    lines.append(f"Issues Found: {len(result.issues)}")
    if result.critical_path_failures > 0:
        lines.append(f"Critical Path Failures: {result.critical_path_failures}")
    lines.append("")

    # Overall coverage issues (not file-specific)
    overall_issues = [
        i
        for i in result.issues
        if i.issue_type in ("overall", "line", "branch", "error")
    ]
    if overall_issues:
        lines.append("-" * 80)
        lines.append("OVERALL ISSUES")
        lines.append("-" * 80)
        for issue in overall_issues:
            lines.append(f"  ✗ {issue.message}")
        lines.append("")

    # File-specific issues
    file_issues = [i for i in result.issues if i.file_path not in ("Overall", "N/A")]
    if file_issues:
        lines.append("-" * 80)
        lines.append("FILE-SPECIFIC COVERAGE ISSUES")
        lines.append("-" * 80)
        lines.append("")

        # Sort by file path for consistent output
        file_issues.sort(key=lambda x: x.file_path)

        for issue in file_issues:
            # File header
            issue_type_label = issue.issue_type.replace("_", " ").title()
            lines.append(f"File: {issue.file_path}")
            lines.append(f"  Type: {issue_type_label}")
            lines.append(
                f"  Coverage: {issue.actual_coverage:.1f}% (required: {issue.required_coverage:.1f}%)"
            )

            # Missing lines
            if issue.missing_lines:
                total_missing = len(issue.missing_lines)
                lines_to_show = issue.missing_lines[:max_missing_lines]
                formatted_lines = _format_line_ranges(lines_to_show)
                lines.append(
                    f"  Missing Lines ({total_missing} total): {formatted_lines}"
                )

                if total_missing > max_missing_lines:
                    lines.append(
                        f"    ... and {total_missing - max_missing_lines} more"
                    )
            else:
                lines.append("  Missing Lines: (line information not available)")

            lines.append("")

    # Show all files if requested
    if show_all_files and coverage_result.files:
        lines.append("-" * 80)
        lines.append("ALL FILES")
        lines.append("-" * 80)
        lines.append("")

        # Get files that don't have issues
        issue_file_paths = {i.file_path for i in file_issues}
        other_files = [
            (path, cov)
            for path, cov in coverage_result.files.items()
            if path not in issue_file_paths
        ]
        other_files.sort(key=lambda x: x[0])

        for file_path, file_cov in other_files:
            lines.append(f"File: {file_path}")
            lines.append(f"  Coverage: {file_cov.coverage_percent:.1f}%")
            lines.append(f"  Lines: {file_cov.lines_covered}/{file_cov.lines_total}")
            if file_cov.branches_total > 0:
                lines.append(
                    f"  Branches: {file_cov.branches_covered}/{file_cov.branches_total}"
                )
            if file_cov.lines_missing:
                missing_count = len(file_cov.lines_missing)
                lines_to_show = file_cov.lines_missing[:max_missing_lines]
                formatted_lines = _format_line_ranges(lines_to_show)
                lines.append(
                    f"  Missing Lines ({missing_count} total): {formatted_lines}"
                )
                if missing_count > max_missing_lines:
                    lines.append(
                        f"    ... and {missing_count - max_missing_lines} more"
                    )
            lines.append("")

    # Summary footer
    lines.append("-" * 80)
    if result.passed:
        lines.append("✓ All coverage thresholds met!")
    else:
        lines.append(
            "✗ Coverage validation failed. Please add tests to address the issues above."
        )
    lines.append("-" * 80)

    return "\n".join(lines)
