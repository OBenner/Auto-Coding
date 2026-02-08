#!/usr/bin/env python3
"""
Performance Analyzer Module
============================

Analyzes code for performance issues including N+1 queries and missing indexes.
This module helps prevent common performance bottlenecks before code is written.

The performance analyzer is used by:
- Planner Agent: To identify potential performance issues before implementation
- Prevention Scanner: As part of proactive issue detection

Usage:
    from analysis.performance_analyzer import PerformanceAnalyzer

    analyzer = PerformanceAnalyzer()
    results = analyzer.analyze(project_dir, spec_dir)

    if results.has_critical_issues:
        print("Performance issues found - review before proceeding")
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class PerformanceIssue:
    """
    Represents a performance issue found during analysis.

    Attributes:
        severity: Severity level (critical, high, medium, low, info)
        issue_type: Type of issue (n_plus_one, missing_index, slow_operation, etc.)
        title: Short title of the issue
        description: Detailed description
        file: File where issue was found
        line: Line number
        suggestion: Suggested fix or optimization
        impact: Estimated performance impact
    """

    severity: str  # critical, high, medium, low, info
    issue_type: str  # n_plus_one, missing_index, slow_operation, inefficient_loop
    title: str
    description: str
    file: str
    line: int
    suggestion: str
    impact: str  # Description of performance impact


@dataclass
class PerformanceAnalysisResult:
    """
    Result of a performance analysis.

    Attributes:
        issues: List of detected performance issues
        analysis_errors: List of errors during analysis
        has_critical_issues: Whether any critical issues were found
        should_warn: Whether these results should warn the user
        files_analyzed: Number of files analyzed
    """

    issues: list[PerformanceIssue] = field(default_factory=list)
    analysis_errors: list[str] = field(default_factory=list)
    has_critical_issues: bool = False
    should_warn: bool = False
    files_analyzed: int = 0


# =============================================================================
# PERFORMANCE ANALYZER
# =============================================================================


class PerformanceAnalyzer:
    """
    Analyzes code for performance issues.

    Detects:
    - N+1 query patterns in database operations
    - Missing indexes based on query patterns
    - Inefficient loops and operations
    - Slow operations in hot paths
    """

    # Patterns that indicate database queries
    DB_QUERY_PATTERNS = [
        r"\.query\(",  # SQLAlchemy, Django ORM
        r"\.filter\(",  # Django ORM, SQLAlchemy
        r"\.get\(",  # ORM get operations
        r"\.execute\(",  # Raw SQL execution
        r"\.fetchall\(",  # Database fetch operations
        r"\.fetchone\(",
        r"SELECT\s+.*\s+FROM",  # Raw SQL
        r"UPDATE\s+.*\s+SET",
        r"DELETE\s+FROM",
        r"INSERT\s+INTO",
    ]

    # Patterns that indicate loops
    LOOP_PATTERNS = [
        r"for\s+\w+\s+in\s+",  # Python for loops
        r"while\s+",  # Python while loops
        r"\.forEach\(",  # JavaScript forEach
        r"\.map\(",  # JavaScript map
        r"\.filter\(",  # JavaScript filter (can be confused with ORM)
    ]

    # ORM relationship access patterns
    ORM_RELATIONSHIP_PATTERNS = [
        r"\.\w+\.all\(\)",  # Accessing related objects
        r"\.\w+\.filter\(",  # Filtering related objects
        r"\.\w+_set\.all\(",  # Django reverse relationships
    ]

    # Index hint patterns in queries
    INDEX_PATTERNS = [
        r"WHERE\s+(\w+)\s*=",  # WHERE clauses on columns
        r"JOIN\s+\w+\s+ON\s+(\w+)",  # JOIN conditions
        r"ORDER\s+BY\s+(\w+)",  # ORDER BY clauses
        r"GROUP\s+BY\s+(\w+)",  # GROUP BY clauses
    ]

    def __init__(self) -> None:
        """Initialize the performance analyzer."""
        pass

    def analyze(
        self,
        project_dir: Path,
        spec_dir: Path | None = None,
        changed_files: list[str] | None = None,
        check_n_plus_one: bool = True,
        check_indexes: bool = True,
        check_loops: bool = True,
    ) -> PerformanceAnalysisResult:
        """
        Run all applicable performance analyses.

        Args:
            project_dir: Path to the project root
            spec_dir: Path to the spec directory (for storing results)
            changed_files: Optional list of files to analyze (if None, analyzes relevant files)
            check_n_plus_one: Whether to check for N+1 query patterns
            check_indexes: Whether to check for missing index patterns
            check_loops: Whether to check for inefficient loops

        Returns:
            PerformanceAnalysisResult with all findings
        """
        project_dir = Path(project_dir)
        result = PerformanceAnalysisResult()

        # Get files to analyze
        files_to_analyze = self._get_files_to_analyze(project_dir, changed_files)
        result.files_analyzed = len(files_to_analyze)

        # Run N+1 query detection
        if check_n_plus_one:
            self._detect_n_plus_one_queries(files_to_analyze, result)

        # Run missing index detection
        if check_indexes:
            self._detect_missing_indexes(files_to_analyze, result)

        # Run inefficient loop detection
        if check_loops:
            self._detect_inefficient_loops(files_to_analyze, result)

        # Determine if has critical issues
        result.has_critical_issues = any(
            issue.severity in ["critical", "high"] for issue in result.issues
        )

        # Should warn if any medium or higher issues found
        result.should_warn = any(
            issue.severity in ["critical", "high", "medium"] for issue in result.issues
        )

        # Save results if spec_dir provided
        if spec_dir:
            self._save_results(spec_dir, result)

        return result

    def _get_files_to_analyze(
        self, project_dir: Path, changed_files: list[str] | None
    ) -> list[Path]:
        """
        Get list of files to analyze.

        Args:
            project_dir: Project root directory
            changed_files: Optional list of specific files to analyze

        Returns:
            List of file paths to analyze
        """
        if changed_files:
            return [project_dir / f for f in changed_files if self._is_analyzable(f)]

        # Find all Python and JavaScript/TypeScript files
        files = []
        for ext in ["**/*.py", "**/*.js", "**/*.ts", "**/*.tsx"]:
            files.extend(project_dir.glob(ext))

        # Filter out common directories to skip
        skip_dirs = {
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            ".git",
            "dist",
            "build",
        }

        return [
            f
            for f in files
            if not any(skip_dir in f.parts for skip_dir in skip_dirs)
        ]

    def _is_analyzable(self, file_path: str) -> bool:
        """Check if file is analyzable (Python or JavaScript/TypeScript)."""
        return file_path.endswith((".py", ".js", ".ts", ".tsx"))

    def _detect_n_plus_one_queries(
        self, files: list[Path], result: PerformanceAnalysisResult
    ) -> None:
        """
        Detect N+1 query patterns.

        N+1 queries occur when:
        1. A loop iterates over a collection
        2. Inside the loop, a database query is executed for each item
        3. This could be avoided by eager loading or batch queries
        """
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                # Look for loops containing database queries
                in_loop = False
                loop_start = 0
                indent_level = 0

                for i, line in enumerate(lines, 1):
                    # Detect loop start
                    if any(re.search(pattern, line) for pattern in self.LOOP_PATTERNS):
                        in_loop = True
                        loop_start = i
                        indent_level = len(line) - len(line.lstrip())
                        continue

                    # Check if we exited the loop (dedented)
                    if in_loop:
                        current_indent = len(line) - len(line.lstrip())
                        if line.strip() and current_indent <= indent_level:
                            in_loop = False
                            continue

                        # Check for database queries inside loop
                        if any(
                            re.search(pattern, line, re.IGNORECASE)
                            for pattern in self.DB_QUERY_PATTERNS
                        ):
                            # Found potential N+1 query
                            result.issues.append(
                                PerformanceIssue(
                                    severity="high",
                                    issue_type="n_plus_one",
                                    title="Potential N+1 Query Pattern",
                                    description=f"Database query detected inside loop at line {i}. "
                                    f"Loop started at line {loop_start}. "
                                    "This may cause multiple queries when one would suffice.",
                                    file=str(file_path),
                                    line=i,
                                    suggestion="Consider using eager loading (select_related/prefetch_related in Django, "
                                    "joinedload/subqueryload in SQLAlchemy) or batch the queries outside the loop.",
                                    impact="Each loop iteration makes a separate database query, "
                                    "causing O(n) queries instead of O(1). This can severely impact "
                                    "performance with large datasets.",
                                )
                            )

                        # Check for ORM relationship access in loops
                        if any(
                            re.search(pattern, line)
                            for pattern in self.ORM_RELATIONSHIP_PATTERNS
                        ):
                            result.issues.append(
                                PerformanceIssue(
                                    severity="high",
                                    issue_type="n_plus_one",
                                    title="ORM Relationship Access in Loop",
                                    description=f"Accessing related objects inside loop at line {i}. "
                                    f"Loop started at line {loop_start}. "
                                    "This typically causes N+1 queries.",
                                    file=str(file_path),
                                    line=i,
                                    suggestion="Use select_related() for foreign keys or prefetch_related() "
                                    "for many-to-many and reverse foreign key relationships before the loop.",
                                    impact="Lazy loading of relationships causes one query per item in the loop.",
                                )
                            )

            except Exception as e:
                result.analysis_errors.append(f"Error analyzing {file_path}: {e}")

    def _detect_missing_indexes(
        self, files: list[Path], result: PerformanceAnalysisResult
    ) -> None:
        """
        Detect potential missing indexes based on query patterns.

        Looks for:
        - WHERE clauses on columns without obvious indexes
        - JOIN conditions on unindexed columns
        - ORDER BY on columns that might need indexes
        """
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                for i, line in enumerate(lines, 1):
                    # Look for SQL queries (raw or in strings)
                    if any(
                        re.search(pattern, line, re.IGNORECASE)
                        for pattern in self.DB_QUERY_PATTERNS
                    ):
                        # Check for WHERE clauses
                        where_match = re.search(
                            r"WHERE\s+(\w+)\s*[=<>]", line, re.IGNORECASE
                        )
                        if where_match:
                            column = where_match.group(1)
                            # Skip obvious indexed columns
                            if column.lower() not in ["id", "pk", "primary_key"]:
                                result.issues.append(
                                    PerformanceIssue(
                                        severity="medium",
                                        issue_type="missing_index",
                                        title=f"Potential Missing Index on Column '{column}'",
                                        description=f"Query at line {i} filters on column '{column}'. "
                                        "Ensure this column has an appropriate index.",
                                        file=str(file_path),
                                        line=i,
                                        suggestion=f"Add database index on column '{column}' if this query "
                                        "is frequently executed or operates on large datasets.",
                                        impact="Queries without indexes perform table scans, "
                                        "which become slow as data grows.",
                                    )
                                )

                        # Check for ORDER BY clauses
                        order_match = re.search(
                            r"ORDER\s+BY\s+(\w+)", line, re.IGNORECASE
                        )
                        if order_match:
                            column = order_match.group(1)
                            result.issues.append(
                                PerformanceIssue(
                                    severity="low",
                                    issue_type="missing_index",
                                    title=f"ORDER BY on Column '{column}' May Need Index",
                                    description=f"Query at line {i} orders by column '{column}'. "
                                    "Consider adding an index for better performance.",
                                    file=str(file_path),
                                    line=i,
                                    suggestion=f"If this ORDER BY is frequently used, add an index on '{column}'.",
                                    impact="Sorting without indexes can be slow on large result sets.",
                                )
                            )

            except Exception as e:
                result.analysis_errors.append(f"Error analyzing {file_path}: {e}")

    def _detect_inefficient_loops(
        self, files: list[Path], result: PerformanceAnalysisResult
    ) -> None:
        """
        Detect inefficient loop patterns.

        Looks for:
        - Nested loops that could be optimized
        - Repeated operations inside loops
        - Large data operations in loops
        """
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                loop_depth = 0
                loop_stack = []

                for i, line in enumerate(lines, 1):
                    indent = len(line) - len(line.lstrip())

                    # Check for loop start
                    if any(re.search(pattern, line) for pattern in self.LOOP_PATTERNS):
                        # Check for nested loops (O(n^2) or worse)
                        if loop_depth > 0:
                            result.issues.append(
                                PerformanceIssue(
                                    severity="medium",
                                    issue_type="inefficient_loop",
                                    title="Nested Loop Detected",
                                    description=f"Nested loop at line {i} (depth {loop_depth + 1}). "
                                    "This creates O(n^2) or worse time complexity.",
                                    file=str(file_path),
                                    line=i,
                                    suggestion="Consider if this can be optimized with better data structures "
                                    "(dictionaries/sets for lookups) or algorithms. "
                                    "Sometimes nested loops are necessary, but verify the approach.",
                                    impact="Nested loops can become very slow with large datasets. "
                                    "O(n^2) means doubling input size quadruples execution time.",
                                )
                            )

                        loop_depth += 1
                        loop_stack.append((i, indent))

                    # Check if we exited a loop
                    while loop_stack and indent <= loop_stack[-1][1]:
                        if line.strip():  # Only count non-empty lines
                            loop_stack.pop()
                            loop_depth -= 1

            except Exception as e:
                result.analysis_errors.append(f"Error analyzing {file_path}: {e}")

    def _save_results(
        self, spec_dir: Path, result: PerformanceAnalysisResult
    ) -> None:
        """
        Save performance analysis results to spec directory.

        Args:
            spec_dir: Spec directory path
            result: Analysis result to save
        """
        import json

        spec_dir = Path(spec_dir)
        spec_dir.mkdir(parents=True, exist_ok=True)

        output_file = spec_dir / "performance_analysis.json"

        data = {
            "files_analyzed": result.files_analyzed,
            "total_issues": len(result.issues),
            "critical_issues": len(
                [i for i in result.issues if i.severity == "critical"]
            ),
            "high_issues": len([i for i in result.issues if i.severity == "high"]),
            "medium_issues": len([i for i in result.issues if i.severity == "medium"]),
            "low_issues": len([i for i in result.issues if i.severity == "low"]),
            "has_critical_issues": result.has_critical_issues,
            "should_warn": result.should_warn,
            "issues": [
                {
                    "severity": issue.severity,
                    "issue_type": issue.issue_type,
                    "title": issue.title,
                    "description": issue.description,
                    "file": issue.file,
                    "line": issue.line,
                    "suggestion": issue.suggestion,
                    "impact": issue.impact,
                }
                for issue in result.issues
            ],
            "errors": result.analysis_errors,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def format_report(self, result: PerformanceAnalysisResult) -> str:
        """
        Format analysis results as a human-readable report.

        Args:
            result: Analysis result to format

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("PERFORMANCE ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"\nFiles Analyzed: {result.files_analyzed}")
        lines.append(f"Total Issues: {len(result.issues)}")

        if result.has_critical_issues:
            lines.append("\n⚠️  CRITICAL PERFORMANCE ISSUES FOUND")

        # Group by severity
        by_severity = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": [],
        }

        for issue in result.issues:
            by_severity[issue.severity].append(issue)

        # Report each severity level
        for severity in ["critical", "high", "medium", "low", "info"]:
            issues = by_severity[severity]
            if not issues:
                continue

            lines.append(f"\n{severity.upper()} Issues ({len(issues)}):")
            lines.append("-" * 80)

            for issue in issues:
                lines.append(f"\n📍 {issue.title}")
                lines.append(f"   File: {issue.file}:{issue.line}")
                lines.append(f"   Type: {issue.issue_type}")
                lines.append(f"   {issue.description}")
                lines.append(f"   💡 Suggestion: {issue.suggestion}")
                lines.append(f"   Impact: {issue.impact}")

        if result.analysis_errors:
            lines.append("\n" + "=" * 80)
            lines.append("ANALYSIS ERRORS:")
            for error in result.analysis_errors:
                lines.append(f"  ❌ {error}")

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)
