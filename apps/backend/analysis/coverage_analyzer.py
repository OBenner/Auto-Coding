#!/usr/bin/env python3
"""
Coverage Analyzer Module
========================

Integrates with pytest-cov to run coverage analysis and parse coverage reports.
This module provides tools for running test coverage, parsing results, and
calculating coverage statistics.

The coverage analysis results are used by:
- QA Reviewer: To validate coverage meets minimum thresholds
- QA Fixer: To identify untested code paths
- Test Generator: To create tests for gaps in coverage

Usage:
    from coverage_analyzer import CoverageAnalyzer

    analyzer = CoverageAnalyzer(project_dir=".")
    result = analyzer.run_coverage(source_dir="apps/backend")

    print(f"Total coverage: {result.total_coverage}%")
    print(f"Files covered: {len(result.files)}")
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class FileCoverage:
    """
    Represents coverage data for a single file.

    Attributes:
        file_path: Relative path to the file
        lines_total: Total number of executable lines
        lines_covered: Number of lines covered by tests
        lines_missing: List of line numbers not covered
        branches_total: Total number of branches
        branches_covered: Number of branches covered
        coverage_percent: Percentage of lines covered (0-100)
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    file_path: str
    lines_total: int = 0
    lines_covered: int = 0
    lines_missing: list[int] = field(default_factory=list)
    branches_total: int = 0
    branches_covered: int = 0
    coverage_percent: float = 0.0


@dataclass
class CoverageResult:
    """
    Result of a coverage analysis run.

    Attributes:
        total_coverage: Overall coverage percentage (0-100)
        lines_total: Total executable lines across all files
        lines_covered: Total lines covered by tests
        branches_total: Total branches across all files
        branches_covered: Total branches covered by tests
        files: Coverage data per file
        report_path: Path to the coverage report file
        timestamp: When the coverage was run
        success: Whether coverage analysis succeeded
        error_message: Error message if failed
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    total_coverage: float = 0.0
    lines_total: int = 0
    lines_covered: int = 0
    branches_total: int = 0
    branches_covered: int = 0
    files: dict[str, FileCoverage] = field(default_factory=dict)
    report_path: str | None = None
    timestamp: str | None = None
    success: bool = False
    error_message: str | None = None


# =============================================================================
# COVERAGE ANALYZER
# =============================================================================


class CoverageAnalyzer:
    """
    Runs test coverage analysis using pytest-cov.

    This class integrates with pytest-cov to:
    - Execute tests with coverage measurement
    - Generate coverage reports in multiple formats (JSON, XML, HTML)
    - Parse coverage data for analysis
    - Calculate coverage statistics per file and overall

    Example:
        analyzer = CoverageAnalyzer(project_dir="/path/to/project")
        result = analyzer.run_coverage(
            source_dir="apps/backend",
            test_dir="tests",
            output_format="json"
        )

        if result.success:
            print(f"Coverage: {result.total_coverage}%")
        else:
            print(f"Error: {result.error_message}")
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    def __init__(self, project_dir: str | Path):
        """
        Initialize the coverage analyzer.

        Args:
            project_dir: Root directory of the project
        """
        self.project_dir = Path(project_dir).resolve()

    def run_coverage(
        self,
        source_dir: str | Path | None = None,
        test_dir: str | Path | None = None,
        output_format: str = "json",
        output_file: str | Path | None = None,
        min_coverage: float | None = None,
        additional_args: list[str] | None = None,
    ) -> CoverageResult:
        """
        Run pytest with coverage analysis.

        Args:
            source_dir: Directory to measure coverage for (e.g., "apps/backend")
            test_dir: Directory containing tests (defaults to "tests")
            output_format: Report format - "json", "xml", "html", or "term"
            output_file: Custom output file path (defaults to .coverage-{format})
            min_coverage: Minimum coverage threshold (will fail if below)
            additional_args: Additional pytest arguments

        Returns:
            CoverageResult with coverage data or error information

        Example:
            result = analyzer.run_coverage(
                source_dir="apps/backend",
                test_dir="tests",
                output_format="json",
                min_coverage=80.0
            )
        """
        # Build pytest command
        cmd = ["pytest"]

        # Add test directory
        if test_dir:
            cmd.append(str(test_dir))

        # Add coverage options
        if source_dir:
            cmd.append(f"--cov={source_dir}")
        else:
            cmd.append("--cov")

        # Add coverage report format
        if output_format == "json":
            output_path = output_file or self.project_dir / ".coverage.json"
            cmd.append(f"--cov-report=json:{output_path}")
        elif output_format == "xml":
            output_path = output_file or self.project_dir / "coverage.xml"
            cmd.append(f"--cov-report=xml:{output_path}")
        elif output_format == "html":
            output_path = output_file or self.project_dir / "htmlcov"
            cmd.append(f"--cov-report=html:{output_path}")
        elif output_format == "term":
            output_path = None
            cmd.append("--cov-report=term")
        else:
            return CoverageResult(
                success=False,
                error_message=f"Unsupported output format: {output_format}",
            )

        # Add minimum coverage threshold
        if min_coverage is not None:
            cmd.append(f"--cov-fail-under={min_coverage}")

        # Add any additional arguments
        if additional_args:
            cmd.extend(additional_args)

        # Execute pytest with coverage
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            # Create result object
            coverage_result = CoverageResult(
                success=result.returncode == 0,
                report_path=str(output_path) if output_path else None,
            )

            # If command failed, capture error
            if result.returncode != 0:
                coverage_result.error_message = (
                    f"pytest-cov failed with exit code {result.returncode}\n"
                    f"stdout: {result.stdout}\n"
                    f"stderr: {result.stderr}"
                )

            return coverage_result

        except subprocess.TimeoutExpired:
            return CoverageResult(
                success=False,
                error_message="Coverage analysis timed out after 5 minutes",
            )
        except FileNotFoundError:
            return CoverageResult(
                success=False,
                error_message="pytest not found. Please install pytest and pytest-cov.",
            )
        except Exception as e:
            return CoverageResult(
                success=False,
                error_message=f"Unexpected error running coverage: {str(e)}",
            )

    def check_pytest_cov_installed(self) -> tuple[bool, str]:
        """
        Check if pytest-cov is installed and available.

        Returns:
            Tuple of (is_installed, version_or_error_message)

        Example:
            installed, message = analyzer.check_pytest_cov_installed()
            if not installed:
                print(f"Please install pytest-cov: {message}")
        """
        try:
            result = subprocess.run(
                ["pytest", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                # Check if pytest-cov is available
                cov_result = subprocess.run(
                    ["pytest", "--co", "--cov=."],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if "unrecognized arguments: --cov" in cov_result.stderr:
                    return False, "pytest-cov plugin not installed"

                return True, result.stdout.strip()
            else:
                return False, "pytest not found"

        except FileNotFoundError:
            return False, "pytest not installed"
        except Exception as e:
            return False, f"Error checking pytest-cov: {str(e)}"


# =============================================================================
# MODULE-LEVEL UTILITIES
# =============================================================================


def validate_coverage_threshold(
    result: CoverageResult, min_threshold: float
) -> tuple[bool, str]:
    """
    Validate coverage result meets minimum threshold.

    Args:
        result: Coverage result to validate
        min_threshold: Minimum coverage percentage (0-100)

    Returns:
        Tuple of (passes_threshold, message)

    Example:
        passes, message = validate_coverage_threshold(result, 80.0)
        if not passes:
            print(f"Coverage too low: {message}")
    """
    if not result.success:
        return False, f"Coverage analysis failed: {result.error_message}"

    if result.total_coverage < min_threshold:
        return (
            False,
            f"Coverage {result.total_coverage:.1f}% is below minimum {min_threshold:.1f}%",
        )

    return True, f"Coverage {result.total_coverage:.1f}% meets minimum {min_threshold:.1f}%"
