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
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
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


def parse_coverage_json(json_path: str | Path) -> CoverageResult:
    """
    Parse a JSON coverage report generated by pytest-cov.

    The JSON format from pytest-cov looks like:
    {
        "meta": {"version": "...", "timestamp": "..."},
        "files": {
            "path/to/file.py": {
                "executed_lines": [1, 2, 3, ...],
                "missing_lines": [10, 11, ...],
                "excluded_lines": [],
                "summary": {
                    "covered_lines": 100,
                    "num_statements": 120,
                    "percent_covered": 83.33,
                    "missing_lines": 20,
                    "excluded_lines": 0
                }
            }
        },
        "totals": {
            "covered_lines": 1000,
            "num_statements": 1200,
            "percent_covered": 83.33,
            "missing_lines": 200,
            "excluded_lines": 0
        }
    }

    Args:
        json_path: Path to the JSON coverage report file

    Returns:
        CoverageResult with parsed coverage data

    Raises:
        FileNotFoundError: If the JSON file doesn't exist
        ValueError: If the JSON is malformed or invalid

    Example:
        result = parse_coverage_json(".coverage.json")
        print(f"Total coverage: {result.total_coverage}%")
        for file_path, file_cov in result.files.items():
            print(f"{file_path}: {file_cov.coverage_percent}%")
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Coverage JSON file not found: {json_path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in coverage report: {e}")
    except Exception as e:
        raise ValueError(f"Error reading coverage JSON: {e}")

    # Extract metadata
    meta = data.get("meta", {})
    timestamp = meta.get("timestamp")

    # Parse totals
    totals = data.get("totals", {})
    total_coverage = totals.get("percent_covered", 0.0)
    lines_total = totals.get("num_statements", 0)
    lines_covered = totals.get("covered_lines", 0)

    # Parse file-level coverage
    files_data = data.get("files", {})
    files: dict[str, FileCoverage] = {}

    for file_path, file_info in files_data.items():
        summary = file_info.get("summary", {})
        missing_lines = file_info.get("missing_lines", [])

        file_coverage = FileCoverage(
            file_path=file_path,
            lines_total=summary.get("num_statements", 0),
            lines_covered=summary.get("covered_lines", 0),
            lines_missing=missing_lines,
            branches_total=0,  # JSON format doesn't include branch info by default
            branches_covered=0,
            coverage_percent=summary.get("percent_covered", 0.0),
        )
        files[file_path] = file_coverage

    return CoverageResult(
        total_coverage=total_coverage,
        lines_total=lines_total,
        lines_covered=lines_covered,
        branches_total=0,
        branches_covered=0,
        files=files,
        report_path=str(path),
        timestamp=timestamp,
        success=True,
    )


def parse_coverage_xml(xml_path: str | Path) -> CoverageResult:
    """
    Parse an XML coverage report generated by pytest-cov (Cobertura format).

    The XML format from pytest-cov follows the Cobertura schema:
    <coverage line-rate="0.83" branch-rate="0.75" timestamp="...">
        <packages>
            <package name="package_name" line-rate="0.83" branch-rate="0.75">
                <classes>
                    <class name="ClassName" filename="path/to/file.py"
                           line-rate="0.83" branch-rate="0.75">
                        <lines>
                            <line number="1" hits="1"/>
                            <line number="2" hits="0"/>
                        </lines>
                    </class>
                </classes>
            </package>
        </packages>
    </coverage>

    Args:
        xml_path: Path to the XML coverage report file

    Returns:
        CoverageResult with parsed coverage data

    Raises:
        FileNotFoundError: If the XML file doesn't exist
        ValueError: If the XML is malformed or invalid

    Example:
        result = parse_coverage_xml("coverage.xml")
        print(f"Total coverage: {result.total_coverage}%")
        print(f"Branch coverage: {result.branches_covered}/{result.branches_total}")
    """
    path = Path(xml_path)
    if not path.exists():
        raise FileNotFoundError(f"Coverage XML file not found: {xml_path}")

    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML in coverage report: {e}")
    except Exception as e:
        raise ValueError(f"Error reading coverage XML: {e}")

    # Extract root-level coverage metrics
    line_rate = float(root.get("line-rate", "0.0"))
    branch_rate = float(root.get("branch-rate", "0.0"))
    timestamp_str = root.get("timestamp")

    # Convert timestamp if available
    timestamp = None
    if timestamp_str:
        try:
            # Cobertura timestamp is Unix epoch in milliseconds
            timestamp_int = int(timestamp_str)
            if timestamp_int > 10**12:  # Milliseconds
                timestamp_int = timestamp_int // 1000
            timestamp = datetime.fromtimestamp(timestamp_int).isoformat()
        except (ValueError, OSError):
            timestamp = timestamp_str

    # Initialize counters
    total_lines = 0
    total_covered = 0
    total_branches = 0
    total_branches_covered = 0
    files: dict[str, FileCoverage] = {}

    # Parse packages and classes
    packages = root.find("packages")
    if packages is not None:
        for package in packages.findall("package"):
            classes = package.find("classes")
            if classes is not None:
                for cls in classes.findall("class"):
                    filename = cls.get("filename", "")
                    class_line_rate = float(cls.get("line-rate", "0.0"))
                    class_branch_rate = float(cls.get("branch-rate", "0.0"))

                    # Parse lines for this class
                    lines_elem = cls.find("lines")
                    if lines_elem is not None:
                        lines = lines_elem.findall("line")
                        file_lines_total = len(lines)
                        file_lines_covered = sum(
                            1 for line in lines if int(line.get("hits", "0")) > 0
                        )
                        missing_lines = [
                            int(line.get("number", "0"))
                            for line in lines
                            if int(line.get("hits", "0")) == 0
                        ]

                        # Count branches (if present)
                        file_branches_total = 0
                        file_branches_covered = 0
                        for line in lines:
                            if line.get("branch") == "true":
                                file_branches_total += 1
                                # Branch coverage is stored in conditions-covered/conditions
                                # Format: "50% (1/2)" or just the fraction
                                branch_cond = line.get("condition-coverage", "")
                                if branch_cond:
                                    # Parse "50% (1/2)" format
                                    if "(" in branch_cond:
                                        fraction = branch_cond.split("(")[1].split(")")[0]
                                        covered, _ = fraction.split("/")
                                        if int(covered) > 0:
                                            file_branches_covered += 1

                        # Calculate percentage
                        file_coverage_percent = (
                            (file_lines_covered / file_lines_total * 100)
                            if file_lines_total > 0
                            else 0.0
                        )

                        # Update totals
                        total_lines += file_lines_total
                        total_covered += file_lines_covered
                        total_branches += file_branches_total
                        total_branches_covered += file_branches_covered

                        # Create or update file coverage entry
                        if filename in files:
                            # Merge multiple classes in same file
                            existing = files[filename]
                            existing.lines_total += file_lines_total
                            existing.lines_covered += file_lines_covered
                            existing.lines_missing.extend(missing_lines)
                            existing.branches_total += file_branches_total
                            existing.branches_covered += file_branches_covered
                            # Recalculate percentage
                            existing.coverage_percent = (
                                (
                                    existing.lines_covered
                                    / existing.lines_total
                                    * 100
                                )
                                if existing.lines_total > 0
                                else 0.0
                            )
                        else:
                            files[filename] = FileCoverage(
                                file_path=filename,
                                lines_total=file_lines_total,
                                lines_covered=file_lines_covered,
                                lines_missing=missing_lines,
                                branches_total=file_branches_total,
                                branches_covered=file_branches_covered,
                                coverage_percent=file_coverage_percent,
                            )

    # Calculate total coverage percentage
    total_coverage = (total_covered / total_lines * 100) if total_lines > 0 else 0.0

    return CoverageResult(
        total_coverage=total_coverage,
        lines_total=total_lines,
        lines_covered=total_covered,
        branches_total=total_branches,
        branches_covered=total_branches_covered,
        files=files,
        report_path=str(path),
        timestamp=timestamp,
        success=True,
    )


def calculate_coverage_stats(
    lines_covered: int,
    lines_total: int,
    branches_covered: int = 0,
    branches_total: int = 0,
) -> dict[str, float]:
    """
    Calculate coverage statistics from raw line and branch data.

    This is a utility function for calculating coverage percentages when you
    have raw coverage counts but not a full CoverageResult object. It handles
    edge cases like zero lines or zero branches.

    Args:
        lines_covered: Number of lines covered by tests
        lines_total: Total number of executable lines
        branches_covered: Number of branches covered by tests (optional)
        branches_total: Total number of branches (optional)

    Returns:
        Dictionary with coverage statistics:
        - line_coverage: Line coverage percentage (0-100)
        - branch_coverage: Branch coverage percentage (0-100)
        - total_coverage: Combined coverage percentage (0-100)

    Example:
        stats = calculate_coverage_stats(
            lines_covered=80,
            lines_total=100,
            branches_covered=15,
            branches_total=20
        )
        print(f"Line coverage: {stats['line_coverage']:.1f}%")
        print(f"Branch coverage: {stats['branch_coverage']:.1f}%")
        print(f"Total coverage: {stats['total_coverage']:.1f}%")
    """
    # Calculate line coverage
    line_coverage = (lines_covered / lines_total * 100) if lines_total > 0 else 0.0

    # Calculate branch coverage
    branch_coverage = (
        (branches_covered / branches_total * 100) if branches_total > 0 else 0.0
    )

    # Calculate combined coverage
    # If we have both lines and branches, weight them equally
    # If we only have lines, use line coverage as total
    if branches_total > 0:
        total_coverage = (line_coverage + branch_coverage) / 2
    else:
        total_coverage = line_coverage

    return {
        "line_coverage": round(line_coverage, 2),
        "branch_coverage": round(branch_coverage, 2),
        "total_coverage": round(total_coverage, 2),
    }


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
