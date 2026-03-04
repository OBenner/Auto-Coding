#!/usr/bin/env python3
"""
Performance Analyzer Module
===========================

Uses AST parsing to detect performance issues and anti-patterns in Python code.
This module provides proactive performance analysis by identifying code patterns
that commonly lead to performance problems.

The performance analyzer identifies:
- N+1 query patterns (database/API calls inside loops)
- Memory leak risks (unclosed resources, unbounded accumulation)
- Slow algorithmic patterns (nested loops, inefficient operations)
- Loop complexity issues
- Resource management problems
- Missing indexes based on query patterns

The performance analyzer is used by:
- Planner Agent: To identify potential performance issues before implementation
- Prevention Scanner: As part of proactive issue detection
- Predictive Scanner: For AST-based file-level analysis

Usage:
    from analysis.performance_analyzer import PerformanceAnalyzer

    analyzer = PerformanceAnalyzer()

    # AST-based single file analysis
    result = analyzer.analyze_file('path/to/file.py')
    for issue in result['issues']:
        print(f"{issue['severity']}: {issue['message']} at line {issue['lineno']}")

    # Project-level regex-based analysis
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
    Represents a detected performance issue (AST-based analysis).

    Attributes:
        issue_type: Type of performance issue (n_plus_1_query, memory_leak, slow_algorithm, etc.)
        severity: Severity level (critical, high, medium, low)
        message: Human-readable description of the issue
        lineno: Line number where the issue occurs
        code_snippet: Code fragment causing the issue
        suggestion: Suggested fix or optimization
        confidence: Confidence score (0.0 to 1.0)
        impact: Estimated performance impact (high, medium, low)
    """

    issue_type: str
    severity: str
    message: str
    lineno: int
    code_snippet: str | None = None
    suggestion: str | None = None
    confidence: float = 0.8
    impact: str = "medium"


@dataclass
class LoopComplexity:
    """
    Represents complexity analysis of a loop.

    Attributes:
        lineno: Line number of the loop
        loop_type: Type of loop (for, while, list comprehension)
        nesting_level: Depth of nesting (0 = top-level)
        complexity_score: Estimated complexity (1-10)
        contains_db_call: Whether loop contains database operations
        contains_api_call: Whether loop contains API calls
        operations_count: Number of operations inside loop
    """

    lineno: int
    loop_type: str
    nesting_level: int = 0
    complexity_score: int = 1
    contains_db_call: bool = False
    contains_api_call: bool = False
    operations_count: int = 0


@dataclass
class AnalysisResult:
    """
    Result of AST-based performance analysis.

    Attributes:
        file_path: Path to analyzed file
        issues: List of detected performance issues
        total_issues: Total count of issues
        critical_count: Count of critical issues
        high_count: Count of high severity issues
        medium_count: Count of medium severity issues
        low_count: Count of low severity issues
        loops: List of loop complexity information
        n_plus_1_count: Count of detected N+1 query patterns
        memory_leak_count: Count of potential memory leaks
    """

    file_path: str
    issues: list[PerformanceIssue] = field(default_factory=list)
    total_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    loops: list[LoopComplexity] = field(default_factory=list)
    n_plus_1_count: int = 0
    memory_leak_count: int = 0


@dataclass
class ProjectPerformanceIssue:
    """
    Represents a performance issue found during project-level analysis.

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
    Result of a project-level performance analysis.

    Attributes:
        issues: List of detected performance issues
        analysis_errors: List of errors during analysis
        has_critical_issues: Whether any critical issues were found
        should_warn: Whether these results should warn the user
        files_analyzed: Number of files analyzed
    """

    issues: list[ProjectPerformanceIssue] = field(default_factory=list)
    analysis_errors: list[str] = field(default_factory=list)
    has_critical_issues: bool = False
    should_warn: bool = False
    files_analyzed: int = 0


# =============================================================================
# PERFORMANCE ANALYZER
# =============================================================================


class PerformanceAnalyzer:
    """
    Analyzes Python code for performance issues.

    Provides two analysis modes:
    1. AST-based single-file analysis (analyze_file / analyze_source)
       - N+1 query patterns (database/API calls inside loops)
       - Memory leak risks (resource leaks, unbounded growth)
       - Slow algorithmic patterns (inefficient loops, redundant operations)
       - Loop complexity issues
       - Resource management problems

    2. Project-level regex-based analysis (analyze)
       - N+1 query patterns in database operations
       - Missing indexes based on query patterns
       - Inefficient loops and operations
       - Slow operations in hot paths
    """

    # Severity mapping (AST-based analysis)
    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"

    # Database/API call patterns (AST-based analysis)
    DB_PATTERNS = [
        "execute",
        "fetchall",
        "fetchone",
        "commit",
        "query",
        "select",
        "insert",
        "update",
        "delete",
        "find",
        "save",
        "create",
    ]

    API_PATTERNS = ["requests.", "httpx.", "urllib.", "fetch(", "get(", "post("]

    # Patterns that indicate database queries (project-level analysis)
    DB_QUERY_PATTERNS = [
        r"\.query\(",  # SQLAlchemy query
        r"\.objects\.filter\(",  # Django ORM filter
        r"\.objects\.get\(",  # Django ORM get
        r"\.objects\.all\(",  # Django ORM all
        r"\.objects\.exclude\(",  # Django ORM exclude
        r"session\.query\(",  # SQLAlchemy session query
        r"\.execute\(",  # Raw SQL execution
        r"\.fetchall\(",  # Database fetch operations
        r"\.fetchone\(",
        r"SELECT\s+.*\s+FROM",  # Raw SQL
        r"UPDATE\s+.*\s+SET",
        r"DELETE\s+FROM",
        r"INSERT\s+INTO",
    ]

    # Patterns that indicate loops (project-level analysis)
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

    # =========================================================================
    # AST-BASED SINGLE FILE ANALYSIS
    # =========================================================================

    def analyze_file(self, file_path: str | Path) -> dict[str, Any]:
        """
        Analyze a Python source file for performance issues.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            Dictionary containing analysis results with keys:
            - file_path: Path to analyzed file
            - issues: List of performance issue dictionaries
            - total_issues: Total issue count
            - critical_count: Critical issue count
            - high_count: High severity issue count
            - medium_count: Medium severity issue count
            - low_count: Low severity issue count
            - loops: List of loop complexity information
            - n_plus_1_count: N+1 query pattern count
            - memory_leak_count: Memory leak pattern count
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"Unable to read file as UTF-8: {file_path}")

        result = self._analyze_source(source, str(path))
        return self._result_to_dict(result)

    def analyze_source(
        self, source: str, file_path: str = "<string>"
    ) -> dict[str, Any]:
        """
        Analyze Python source code string for performance issues.

        Args:
            source: Python source code as string
            file_path: Path for error reporting

        Returns:
            Dictionary containing analysis results
        """
        result = self._analyze_source(source, file_path)
        return self._result_to_dict(result)

    def _analyze_source(self, source: str, file_path: str) -> AnalysisResult:
        """
        Internal method to analyze source code for performance issues.

        Args:
            source: Python source code
            file_path: Path for error reporting

        Returns:
            AnalysisResult object
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in {file_path}: {e}")

        result = AnalysisResult(file_path=file_path)

        # Detect performance issues
        result.issues = self._detect_performance_issues(tree)
        result.loops = self._analyze_loop_complexity(tree)

        # Count specific issue types
        result.n_plus_1_count = sum(
            1 for issue in result.issues if issue.issue_type == "n_plus_1_query"
        )
        result.memory_leak_count = sum(
            1 for issue in result.issues if issue.issue_type == "memory_leak"
        )

        # Count by severity
        for issue in result.issues:
            result.total_issues += 1
            if issue.severity == self.SEVERITY_CRITICAL:
                result.critical_count += 1
            elif issue.severity == self.SEVERITY_HIGH:
                result.high_count += 1
            elif issue.severity == self.SEVERITY_MEDIUM:
                result.medium_count += 1
            elif issue.severity == self.SEVERITY_LOW:
                result.low_count += 1

        return result

    def _detect_performance_issues(self, tree: ast.AST) -> list[PerformanceIssue]:
        """
        Detect performance issues in AST.

        Identifies:
        - N+1 query patterns
        - Memory leak risks
        - Slow algorithmic patterns
        - Resource management issues

        Returns:
            List of PerformanceIssue objects
        """
        issues = []

        for node in ast.walk(tree):
            # Detect N+1 query patterns
            if isinstance(
                node, (ast.For, ast.While, ast.ListComp, ast.DictComp, ast.SetComp)
            ):
                n_plus_1_issues = self._detect_n_plus_1_patterns(node)
                issues.extend(n_plus_1_issues)

            # Detect memory leak patterns
            elif isinstance(node, ast.With):
                memory_issues = self._detect_memory_leaks(node)
                issues.extend(memory_issues)

            # Detect slow algorithmic patterns
            elif isinstance(node, ast.For):
                slow_issues = self._detect_slow_algorithms(node)
                issues.extend(slow_issues)

            # Detect resource management issues
            elif isinstance(node, ast.Call):
                resource_issues = self._detect_resource_issues(node)
                issues.extend(resource_issues)

        return issues

    def _detect_n_plus_1_patterns(
        self, loop_node: ast.For | ast.While | ast.comprehension
    ) -> list[PerformanceIssue]:
        """
        Detect N+1 query patterns (database/API calls inside loops).

        Args:
            loop_node: Loop or comprehension AST node

        Returns:
            List of PerformanceIssue objects
        """
        issues = []

        # Get loop body
        if isinstance(loop_node, (ast.For, ast.While)):
            _body = loop_node.body
            loop_type = "for" if isinstance(loop_node, ast.For) else "while"
        else:
            # Comprehension
            _body = [loop_node.elt] if hasattr(loop_node, "elt") else []
            loop_type = "comprehension"

        # Check for DB/API calls in loop body
        for node in ast.walk(loop_node):
            # Skip the loop definition itself
            if node is loop_node:
                continue

            # Check for function calls that might be DB operations
            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node)

                # Check if it's a database operation
                if any(pattern in func_name.lower() for pattern in self.DB_PATTERNS):
                    issues.append(
                        PerformanceIssue(
                            issue_type="n_plus_1_query",
                            severity=self.SEVERITY_HIGH,
                            message=f"N+1 query pattern detected: Database call '{func_name}' inside {loop_type} loop",
                            lineno=node.lineno,
                            code_snippet=ast.unparse(node),
                            suggestion="Move the database call outside the loop or use bulk operations",
                            confidence=0.85,
                            impact="high",
                        )
                    )

                # Check if it's an API call
                elif any(pattern in func_name for pattern in self.API_PATTERNS):
                    issues.append(
                        PerformanceIssue(
                            issue_type="n_plus_1_query",
                            severity=self.SEVERITY_HIGH,
                            message=f"N+1 query pattern detected: API call '{func_name}' inside {loop_type} loop",
                            lineno=node.lineno,
                            code_snippet=ast.unparse(node),
                            suggestion="Move the API call outside the loop or batch requests",
                            confidence=0.85,
                            impact="high",
                        )
                    )

        return issues

    def _detect_memory_leaks(self, node: ast.With) -> list[PerformanceIssue]:
        """
        Detect memory leak patterns.

        Args:
            node: With statement AST node

        Returns:
            List of PerformanceIssue objects
        """
        issues = []

        # Check for unbounded list growth patterns
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = self._get_call_name(child)

                # Check for append in loops without bounds
                if func_name.endswith(".append") or func_name.endswith(".extend"):
                    # Check if inside a loop
                    for parent in ast.walk(node):
                        if isinstance(parent, (ast.For, ast.While)):
                            issues.append(
                                PerformanceIssue(
                                    issue_type="memory_leak",
                                    severity=self.SEVERITY_MEDIUM,
                                    message=f"Potential unbounded memory growth: {func_name} inside loop",
                                    lineno=child.lineno,
                                    code_snippet=ast.unparse(child),
                                    suggestion="Consider pre-allocating or adding bounds checking",
                                    confidence=0.7,
                                    impact="medium",
                                )
                            )
                            break

        return issues

    def _detect_slow_algorithms(self, node: ast.For) -> list[PerformanceIssue]:
        """
        Detect slow algorithmic patterns.

        Args:
            node: For loop AST node

        Returns:
            List of PerformanceIssue objects
        """
        issues = []

        # Check for nested loops
        for child in ast.walk(node):
            if isinstance(child, ast.For) and child is not node:
                # Nested loop detected
                issues.append(
                    PerformanceIssue(
                        issue_type="slow_algorithm",
                        severity=self.SEVERITY_MEDIUM,
                        message="Nested loop detected: O(n\u00b2) complexity",
                        lineno=child.lineno,
                        code_snippet=ast.unparse(child),
                        suggestion="Consider using dictionaries, sets, or more efficient algorithms",
                        confidence=0.9,
                        impact="high",
                    )
                )

                # Check for operations inside nested loop
                for nested_child in ast.walk(child):
                    if isinstance(nested_child, ast.Call):
                        func_name = self._get_call_name(nested_child)
                        if any(pattern in func_name for pattern in self.DB_PATTERNS):
                            issues.append(
                                PerformanceIssue(
                                    issue_type="n_plus_1_query",
                                    severity=self.SEVERITY_CRITICAL,
                                    message="Database call inside nested loop: O(n\u00b2) or worse complexity",
                                    lineno=nested_child.lineno,
                                    code_snippet=ast.unparse(nested_child),
                                    suggestion="Refactor to use bulk operations or joins",
                                    confidence=0.95,
                                    impact="high",
                                )
                            )

        # Check for expensive operations in loop
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = self._get_call_name(child)

                # Check for expensive operations
                if any(
                    pattern in func_name
                    for pattern in [
                        "sorted(",
                        "sort(",
                        "reverse(",
                        "copy(",
                        "deepcopy(",
                    ]
                ):
                    issues.append(
                        PerformanceIssue(
                            issue_type="slow_algorithm",
                            severity=self.SEVERITY_LOW,
                            message=f"Expensive operation inside loop: {func_name}",
                            lineno=child.lineno,
                            code_snippet=ast.unparse(child),
                            suggestion="Move operation outside loop or use in-place modification",
                            confidence=0.75,
                            impact="medium",
                        )
                    )

        return issues

    def _detect_resource_issues(self, node: ast.Call) -> list[PerformanceIssue]:
        """
        Detect resource management issues.

        Args:
            node: Call AST node

        Returns:
            List of PerformanceIssue objects
        """
        issues = []
        func_name = self._get_call_name(node)

        # Check for file operations without context manager
        if func_name == "open" and not self._is_inside_with(node):
            # This is handled by linters typically, but we can note it
            pass

        return issues

    def _analyze_loop_complexity(self, tree: ast.AST) -> list[LoopComplexity]:
        """
        Analyze loop complexity across the codebase.

        Args:
            tree: AST tree

        Returns:
            List of LoopComplexity objects
        """
        loops = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                loop_type = "for"
                nesting_level = self._get_nesting_level(node, tree)
                complexity_score = self._calculate_loop_complexity(node)
                contains_db_call = self._contains_db_call(node)
                contains_api_call = self._contains_api_call(node)
                operations_count = self._count_operations(node)

                loops.append(
                    LoopComplexity(
                        lineno=node.lineno,
                        loop_type=loop_type,
                        nesting_level=nesting_level,
                        complexity_score=complexity_score,
                        contains_db_call=contains_db_call,
                        contains_api_call=contains_api_call,
                        operations_count=operations_count,
                    )
                )

            elif isinstance(node, ast.While):
                loop_type = "while"
                nesting_level = self._get_nesting_level(node, tree)
                complexity_score = self._calculate_loop_complexity(node)
                contains_db_call = self._contains_db_call(node)
                contains_api_call = self._contains_api_call(node)
                operations_count = self._count_operations(node)

                loops.append(
                    LoopComplexity(
                        lineno=node.lineno,
                        loop_type=loop_type,
                        nesting_level=nesting_level,
                        complexity_score=complexity_score,
                        contains_db_call=contains_db_call,
                        contains_api_call=contains_api_call,
                        operations_count=operations_count,
                    )
                )

        return loops

    def _get_call_name(self, node: ast.Call) -> str:
        """Extract the function name from a Call node."""
        try:
            return ast.unparse(node.func)
        except Exception:
            return "<unknown>"

    def _is_inside_with(self, node: ast.Call) -> bool:
        """Check if a call is inside a with statement."""
        for parent in ast.walk(node):
            if isinstance(parent, ast.With):
                # Check if this call is in the with clause
                for item in parent.items:
                    if item.context_expr == node:
                        return True
        return False

    def _get_nesting_level(self, node: ast.For | ast.While, tree: ast.AST) -> int:
        """Calculate the nesting level of a loop."""
        level = 0
        _current = node

        # Walk up from the node to find containing loops
        for parent in ast.walk(tree):
            if isinstance(parent, (ast.For, ast.While)):
                # Check if our node is inside this parent
                for child in ast.walk(parent):
                    if child is node and parent is not node:
                        level += 1
                        break

        return level

    def _calculate_loop_complexity(self, node: ast.For | ast.While) -> int:
        """Calculate complexity score for a loop (1-10)."""
        complexity = 1  # Base complexity

        # Count nested loops
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While)) and child is not node:
                complexity += 2

            # Count conditionals
            elif isinstance(child, ast.If):
                complexity += 1

            # Count function calls
            elif isinstance(child, ast.Call):
                complexity += 0.5

        return min(int(complexity), 10)

    def _contains_db_call(self, node: ast.For | ast.While) -> bool:
        """Check if loop contains database calls."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = self._get_call_name(child)
                if any(pattern in func_name.lower() for pattern in self.DB_PATTERNS):
                    return True
        return False

    def _contains_api_call(self, node: ast.For | ast.While) -> bool:
        """Check if loop contains API calls."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func_name = self._get_call_name(child)
                if any(pattern in func_name for pattern in self.API_PATTERNS):
                    return True
        return False

    def _count_operations(self, node: ast.For | ast.While) -> int:
        """Count operations inside a loop."""
        count = 0

        for child in ast.walk(node):
            # Skip the loop definition itself
            if child is node:
                continue

            if isinstance(child, ast.Call):
                count += 1
            elif isinstance(child, ast.If):
                count += 1
            elif isinstance(child, ast.Assign):
                count += 1

        return count

    def _result_to_dict(self, result: AnalysisResult) -> dict[str, Any]:
        """Convert AnalysisResult to dictionary."""
        return {
            "file_path": result.file_path,
            "issues": [
                {
                    "issue_type": issue.issue_type,
                    "severity": issue.severity,
                    "message": issue.message,
                    "lineno": issue.lineno,
                    "code_snippet": issue.code_snippet,
                    "suggestion": issue.suggestion,
                    "confidence": issue.confidence,
                    "impact": issue.impact,
                }
                for issue in result.issues
            ],
            "total_issues": result.total_issues,
            "critical_count": result.critical_count,
            "high_count": result.high_count,
            "medium_count": result.medium_count,
            "low_count": result.low_count,
            "loops": [
                {
                    "lineno": loop.lineno,
                    "loop_type": loop.loop_type,
                    "nesting_level": loop.nesting_level,
                    "complexity_score": loop.complexity_score,
                    "contains_db_call": loop.contains_db_call,
                    "contains_api_call": loop.contains_api_call,
                    "operations_count": loop.operations_count,
                }
                for loop in result.loops
            ],
            "n_plus_1_count": result.n_plus_1_count,
            "memory_leak_count": result.memory_leak_count,
        }

    # =========================================================================
    # PROJECT-LEVEL REGEX-BASED ANALYSIS
    # =========================================================================

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

        from analysis.io_utils import should_skip_path

        return [f for f in files if not should_skip_path(f)]

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
                                ProjectPerformanceIssue(
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
                                ProjectPerformanceIssue(
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
                                    ProjectPerformanceIssue(
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
                                ProjectPerformanceIssue(
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
                                ProjectPerformanceIssue(
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

    def _save_results(self, spec_dir: Path, result: PerformanceAnalysisResult) -> None:
        """
        Save performance analysis results to spec directory.

        Args:
            spec_dir: Spec directory path
            result: Analysis result to save
        """

        from analysis.io_utils import (
            atomic_json_write,
            build_issue_summary,
            prepare_save_dir,
        )

        spec_dir, output_file = prepare_save_dir(spec_dir, "performance_analysis.json")

        data = build_issue_summary(result)
        data["issues"] = [
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
        ]

        atomic_json_write(
            data, output_file, dir=spec_dir, prefix="performance_analysis_"
        )

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

        from analysis.io_utils import SEVERITY_ORDER, group_by_severity

        by_severity = group_by_severity(result.issues)

        for severity in SEVERITY_ORDER:
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


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python -m analysis.performance_analyzer <file_path> [--analyze-queries]"
        )
        sys.exit(1)

    file_path = sys.argv[1]
    analyzer = PerformanceAnalyzer()

    try:
        result = analyzer.analyze_file(file_path)

        print(f"\nPerformance Analysis Results for: {file_path}")
        print("=" * 70)

        print("\nSummary:")
        print(f"  Total Issues: {result['total_issues']}")
        print(f"  Critical: {result['critical_count']}")
        print(f"  High: {result['high_count']}")
        print(f"  Medium: {result['medium_count']}")
        print(f"  Low: {result['low_count']}")
        print(f"  N+1 Query Patterns: {result['n_plus_1_count']}")
        print(f"  Memory Leak Patterns: {result['memory_leak_count']}")
        print(f"  Loops Analyzed: {len(result['loops'])}")

        if result["issues"]:
            print("\nIssues Found:")
            for issue in result["issues"]:
                print(f"\n  [{issue['severity'].upper()}] {issue['message']}")
                print(f"    Line: {issue['lineno']}")
                if issue["code_snippet"]:
                    print(f"    Code: {issue['code_snippet']}")
                if issue["suggestion"]:
                    print(f"    Suggestion: {issue['suggestion']}")
                print(
                    f"    Impact: {issue['impact']} (confidence: {issue['confidence']:.2f})"
                )

        if result["loops"]:
            print("\nLoop Complexity:")
            for loop in result["loops"]:
                print(
                    f"  Line {loop['lineno']}: {loop['loop_type']} loop "
                    f"(complexity: {loop['complexity_score']}/10, "
                    f"nesting: {loop['nesting_level']}, "
                    f"operations: {loop['operations_count']})"
                )
                if loop["contains_db_call"]:
                    print("    ⚠ Contains database call")
                if loop["contains_api_call"]:
                    print("    ⚠ Contains API call")

        print("\n" + "=" * 70)
        print("Analysis complete")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
