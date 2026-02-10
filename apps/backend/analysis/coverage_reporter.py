#!/usr/bin/env python3
"""
Coverage Reporter Module
========================

Collects and analyzes test coverage reports from various testing frameworks.
This module parses coverage data to provide structured insights about test
coverage across the codebase.

The coverage reporter is used by:
- QA Agent: To verify sufficient test coverage before approval
- Test Generator: To identify uncovered code paths
- Coverage Validation: To ensure coverage thresholds are met

Usage:
    from coverage_reporter import collect_coverage

    result = collect_coverage(project_dir, test_framework="pytest")
    print(f"Overall coverage: {result.overall_coverage}%")
    print(f"Uncovered files: {result.uncovered_files}")
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class FileCoverage:
    """
    Coverage information for a single file.

    Attributes:
        file_path: Relative path to the file
        lines_total: Total number of executable lines
        lines_covered: Number of lines covered by tests
        lines_missed: Number of lines not covered by tests
        coverage_percentage: Percentage of lines covered
        branches_total: Total number of branches (if available)
        branches_covered: Number of branches covered (if available)
        missing_lines: List of line numbers not covered
    """

    file_path: str
    lines_total: int
    lines_covered: int
    lines_missed: int
    coverage_percentage: float
    branches_total: int = 0
    branches_covered: int = 0
    missing_lines: list[int] = field(default_factory=list)


@dataclass
class CoverageReport:
    """
    Aggregated coverage report across all files.

    Attributes:
        overall_coverage: Overall coverage percentage
        lines_total: Total executable lines across all files
        lines_covered: Total lines covered by tests
        lines_missed: Total lines not covered
        branches_total: Total branches across all files
        branches_covered: Total branches covered
        files: List of per-file coverage details
        uncovered_files: List of files with 0% coverage
        report_path: Path to the raw coverage report
        framework: Test framework that generated the report
    """

    overall_coverage: float
    lines_total: int
    lines_covered: int
    lines_missed: int
    branches_total: int = 0
    branches_covered: int = 0
    files: list[FileCoverage] = field(default_factory=list)
    uncovered_files: list[str] = field(default_factory=list)
    report_path: str | None = None
    framework: str = ""


# =============================================================================
# COVERAGE PARSERS
# =============================================================================


class CoverageParser:
    """
    Base class for coverage report parsers.
    """

    def parse(self, report_path: Path) -> CoverageReport | None:
        """
        Parse a coverage report file.

        Args:
            report_path: Path to the coverage report

        Returns:
            CoverageReport if parsing succeeds, None otherwise
        """
        raise NotImplementedError


class PytestCoverageParser(CoverageParser):
    """
    Parser for pytest-cov coverage reports (JSON format).

    Pytest-cov can generate JSON reports with:
        pytest --cov --cov-report=json
    """

    def parse(self, report_path: Path) -> CoverageReport | None:
        """
        Parse pytest-cov JSON coverage report.

        Expected format:
        {
          "totals": {
            "covered_lines": 150,
            "num_statements": 200,
            "missing_lines": 50,
            "percent_covered": 75.0
          },
          "files": {
            "path/to/file.py": {
              "summary": {
                "covered_lines": 50,
                "num_statements": 60,
                "missing_lines": 10,
                "percent_covered": 83.33
              },
              "missing_lines": [10, 15, 20]
            }
          }
        }
        """
        try:
            with open(report_path) as f:
                data = json.load(f)

            totals = data.get("totals", {})
            files_data = data.get("files", {})

            # Parse per-file coverage
            file_coverages = []
            uncovered_files = []

            for file_path, file_data in files_data.items():
                summary = file_data.get("summary", {})
                missing_lines = file_data.get("missing_lines", [])

                lines_covered = summary.get("covered_lines", 0)
                lines_total = summary.get("num_statements", 0)
                lines_missed = summary.get("missing_lines", 0)
                coverage_pct = summary.get("percent_covered", 0.0)

                file_cov = FileCoverage(
                    file_path=file_path,
                    lines_total=lines_total,
                    lines_covered=lines_covered,
                    lines_missed=lines_missed,
                    coverage_percentage=coverage_pct,
                    missing_lines=missing_lines,
                )
                file_coverages.append(file_cov)

                if coverage_pct == 0:
                    uncovered_files.append(file_path)

            # Create overall report
            report = CoverageReport(
                overall_coverage=totals.get("percent_covered", 0.0),
                lines_total=totals.get("num_statements", 0),
                lines_covered=totals.get("covered_lines", 0),
                lines_missed=totals.get("missing_lines", 0),
                files=file_coverages,
                uncovered_files=uncovered_files,
                report_path=str(report_path),
                framework="pytest",
            )

            return report

        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f"Failed to parse pytest coverage report: {e}")
            return None


class VitestCoverageParser(CoverageParser):
    """
    Parser for Vitest coverage reports (JSON format).

    Vitest uses c8/v8 for coverage, generating JSON reports with:
        vitest run --coverage --coverage.reporter=json
    """

    def parse(self, report_path: Path) -> CoverageReport | None:
        """
        Parse Vitest JSON coverage report.

        Expected format (Istanbul/v8 JSON):
        {
          "total": {
            "lines": {"total": 200, "covered": 150, "pct": 75},
            "statements": {"total": 200, "covered": 150, "pct": 75},
            "branches": {"total": 50, "covered": 40, "pct": 80}
          },
          "path/to/file.ts": {
            "lines": {"total": 50, "covered": 40, "pct": 80},
            "statements": {...},
            "branches": {...}
          }
        }
        """
        try:
            with open(report_path) as f:
                data = json.load(f)

            # Extract totals
            total = data.get("total", {})
            lines = total.get("lines", {})
            branches = total.get("branches", {})

            lines_total = lines.get("total", 0)
            lines_covered = lines.get("covered", 0)
            lines_missed = lines_total - lines_covered
            overall_coverage = lines.get("pct", 0.0)

            branches_total = branches.get("total", 0)
            branches_covered = branches.get("covered", 0)

            # Parse per-file coverage
            file_coverages = []
            uncovered_files = []

            for file_path, file_data in data.items():
                if file_path == "total":
                    continue

                file_lines = file_data.get("lines", {})
                file_branches = file_data.get("branches", {})

                f_lines_total = file_lines.get("total", 0)
                f_lines_covered = file_lines.get("covered", 0)
                f_lines_missed = f_lines_total - f_lines_covered
                f_coverage_pct = file_lines.get("pct", 0.0)

                f_branches_total = file_branches.get("total", 0)
                f_branches_covered = file_branches.get("covered", 0)

                file_cov = FileCoverage(
                    file_path=file_path,
                    lines_total=f_lines_total,
                    lines_covered=f_lines_covered,
                    lines_missed=f_lines_missed,
                    coverage_percentage=f_coverage_pct,
                    branches_total=f_branches_total,
                    branches_covered=f_branches_covered,
                )
                file_coverages.append(file_cov)

                if f_coverage_pct == 0:
                    uncovered_files.append(file_path)

            # Create overall report
            report = CoverageReport(
                overall_coverage=overall_coverage,
                lines_total=lines_total,
                lines_covered=lines_covered,
                lines_missed=lines_missed,
                branches_total=branches_total,
                branches_covered=branches_covered,
                files=file_coverages,
                uncovered_files=uncovered_files,
                report_path=str(report_path),
                framework="vitest",
            )

            return report

        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            print(f"Failed to parse Vitest coverage report: {e}")
            return None


class CoberturaXMLParser(CoverageParser):
    """
    Parser for Cobertura XML coverage reports.

    Many tools can generate Cobertura XML format:
    - pytest-cov: pytest --cov --cov-report=xml
    - vitest: vitest run --coverage --coverage.reporter=cobertura
    """

    def parse(self, report_path: Path) -> CoverageReport | None:
        """
        Parse Cobertura XML coverage report.

        Expected format:
        <coverage line-rate="0.75" branch-rate="0.80">
          <packages>
            <package name="module">
              <classes>
                <class filename="path/to/file.py" line-rate="0.83">
                  <lines>
                    <line number="10" hits="1"/>
                    <line number="15" hits="0"/>
                  </lines>
                </class>
              </classes>
            </package>
          </packages>
        </coverage>
        """
        try:
            tree = ET.parse(report_path)
            root = tree.getroot()

            # Extract overall coverage
            line_rate = float(root.get("line-rate", 0))
            branch_rate = float(root.get("branch-rate", 0))
            overall_coverage = line_rate * 100

            # Parse per-file coverage
            file_coverages = []
            uncovered_files = []
            total_lines = 0
            total_covered = 0
            total_branches = 0
            total_branches_covered = 0

            for package in root.findall(".//package"):
                for cls in package.findall(".//class"):
                    file_path = cls.get("filename", "")
                    file_line_rate = float(cls.get("line-rate", 0))

                    lines = cls.findall(".//line")
                    lines_total = len(lines)
                    lines_covered = sum(1 for line in lines if int(line.get("hits", 0)) > 0)
                    lines_missed = lines_total - lines_covered
                    missing_lines = [
                        int(line.get("number", 0))
                        for line in lines
                        if int(line.get("hits", 0)) == 0
                    ]

                    file_cov = FileCoverage(
                        file_path=file_path,
                        lines_total=lines_total,
                        lines_covered=lines_covered,
                        lines_missed=lines_missed,
                        coverage_percentage=file_line_rate * 100,
                        missing_lines=missing_lines,
                    )
                    file_coverages.append(file_cov)

                    total_lines += lines_total
                    total_covered += lines_covered

                    if file_line_rate == 0:
                        uncovered_files.append(file_path)

            # Create overall report
            report = CoverageReport(
                overall_coverage=overall_coverage,
                lines_total=total_lines,
                lines_covered=total_covered,
                lines_missed=total_lines - total_covered,
                branches_total=total_branches,
                branches_covered=total_branches_covered,
                files=file_coverages,
                uncovered_files=uncovered_files,
                report_path=str(report_path),
                framework="unknown",
            )

            return report

        except (ET.ParseError, FileNotFoundError, ValueError) as e:
            print(f"Failed to parse Cobertura XML coverage report: {e}")
            return None


# =============================================================================
# COVERAGE COLLECTION
# =============================================================================


def find_coverage_report(
    project_dir: Path, framework: str | None = None
) -> Path | None:
    """
    Find coverage report files in the project directory.

    Args:
        project_dir: Root directory of the project
        framework: Test framework (pytest, vitest) or None for auto-detect

    Returns:
        Path to coverage report if found, None otherwise
    """
    # Common coverage report locations
    report_locations = {
        "pytest": [
            "coverage.json",
            ".coverage.json",
            "htmlcov/coverage.json",
            "coverage.xml",
        ],
        "vitest": [
            "coverage/coverage-final.json",
            "coverage/coverage-summary.json",
            "coverage/cobertura-coverage.xml",
        ],
    }

    # If framework specified, check its specific locations
    if framework:
        locations = report_locations.get(framework, [])
        for location in locations:
            report_path = project_dir / location
            if report_path.exists():
                return report_path

    # Otherwise, check all common locations
    all_locations = []
    for locs in report_locations.values():
        all_locations.extend(locs)

    for location in all_locations:
        report_path = project_dir / location
        if report_path.exists():
            return report_path

    return None


def collect_coverage(
    project_dir: str | Path, framework: str | None = None
) -> CoverageReport | None:
    """
    Collect test coverage information from the project.

    This is the main entry point for coverage collection. It:
    1. Searches for coverage report files
    2. Detects the report format
    3. Parses the coverage data
    4. Returns structured coverage information

    Args:
        project_dir: Root directory of the project
        framework: Test framework (pytest, vitest) or None for auto-detect

    Returns:
        CoverageReport if coverage data found and parsed, None otherwise

    Example:
        >>> result = collect_coverage("/path/to/project", framework="pytest")
        >>> if result:
        >>>     print(f"Coverage: {result.overall_coverage}%")
        >>>     for file in result.uncovered_files:
        >>>         print(f"Uncovered: {file}")
    """
    project_path = Path(project_dir)

    # Find coverage report
    report_path = find_coverage_report(project_path, framework)
    if not report_path:
        return None

    # Determine parser based on file extension
    parser: CoverageParser | None = None

    if report_path.suffix == ".json":
        # Try pytest format first, then vitest
        parser = PytestCoverageParser()
        result = parser.parse(report_path)
        if result:
            return result

        parser = VitestCoverageParser()
        result = parser.parse(report_path)
        if result:
            return result

    elif report_path.suffix == ".xml":
        parser = CoberturaXMLParser()
        result = parser.parse(report_path)
        if result:
            return result

    return None


def format_coverage_summary(report: CoverageReport) -> str:
    """
    Format coverage report as a human-readable summary.

    Args:
        report: Coverage report to format

    Returns:
        Formatted string summary
    """
    summary = []
    summary.append("=" * 60)
    summary.append("TEST COVERAGE REPORT")
    summary.append("=" * 60)
    summary.append(f"Framework: {report.framework}")
    summary.append(f"Overall Coverage: {report.overall_coverage:.2f}%")
    summary.append(f"Lines Covered: {report.lines_covered}/{report.lines_total}")
    summary.append(f"Lines Missed: {report.lines_missed}")

    if report.branches_total > 0:
        summary.append(
            f"Branches Covered: {report.branches_covered}/{report.branches_total}"
        )

    if report.uncovered_files:
        summary.append("\nUncovered Files:")
        for file_path in report.uncovered_files:
            summary.append(f"  - {file_path}")

    # Show files with lowest coverage
    sorted_files = sorted(report.files, key=lambda f: f.coverage_percentage)
    low_coverage_files = [f for f in sorted_files[:5] if f.coverage_percentage < 80]

    if low_coverage_files:
        summary.append("\nFiles with Low Coverage (<80%):")
        for file_cov in low_coverage_files:
            summary.append(
                f"  - {file_cov.file_path}: {file_cov.coverage_percentage:.2f}%"
            )
            if file_cov.missing_lines[:5]:  # Show first 5 missing lines
                lines_preview = ", ".join(map(str, file_cov.missing_lines[:5]))
                summary.append(f"    Missing lines: {lines_preview}...")

    summary.append("=" * 60)
    return "\n".join(summary)


# =============================================================================
# CLI INTERFACE (for testing)
# =============================================================================


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python coverage_reporter.py <project_dir> [framework]")
        sys.exit(1)

    project_dir = sys.argv[1]
    framework = sys.argv[2] if len(sys.argv) > 2 else None

    result = collect_coverage(project_dir, framework)
    if result:
        print(format_coverage_summary(result))
    else:
        print("No coverage report found.")
        sys.exit(1)
