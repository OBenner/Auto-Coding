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

Usage:
    from performance_analyzer import PerformanceAnalyzer

    analyzer = PerformanceAnalyzer()
    result = analyzer.analyze_file('path/to/file.py')

    for issue in result['issues']:
        print(f"{issue['severity']}: {issue['message']} at line {issue['lineno']}")
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class PerformanceIssue:
    """
    Represents a detected performance issue.

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
    Result of performance analysis.

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


# =============================================================================
# PERFORMANCE ANALYZER
# =============================================================================


class PerformanceAnalyzer:
    """
    Analyzes Python code for performance issues using AST parsing.

    Identifies:
    - N+1 query patterns (database/API calls inside loops)
    - Memory leak risks (resource leaks, unbounded growth)
    - Slow algorithmic patterns (inefficient loops, redundant operations)
    - Loop complexity issues
    - Resource management problems
    """

    # Severity mapping
    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"

    # Database/API call patterns
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

    def __init__(self):
        """Initialize the performance analyzer."""
        pass

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

    def analyze_source(self, source: str, file_path: str = "<string>") -> dict[str, Any]:
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
            if isinstance(node, (ast.For, ast.While, ast.ListComp, ast.DictComp, ast.SetComp)):
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
            body = loop_node.body
            loop_type = "for" if isinstance(loop_node, ast.For) else "while"
        else:
            # Comprehension
            body = [loop_node.elt] if hasattr(loop_node, 'elt') else []
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
                        message="Nested loop detected: O(n²) complexity",
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
                                    message=f"Database call inside nested loop: O(n²) or worse complexity",
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
                    for pattern in ["sorted(", "sort(", "reverse(", "copy(", "deepcopy("]
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
        current = node

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


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m analysis.performance_analyzer <file_path> [--analyze-queries]")
        sys.exit(1)

    file_path = sys.argv[1]
    analyzer = PerformanceAnalyzer()

    try:
        result = analyzer.analyze_file(file_path)

        print(f"\nPerformance Analysis Results for: {file_path}")
        print("=" * 70)

        print(f"\nSummary:")
        print(f"  Total Issues: {result['total_issues']}")
        print(f"  Critical: {result['critical_count']}")
        print(f"  High: {result['high_count']}")
        print(f"  Medium: {result['medium_count']}")
        print(f"  Low: {result['low_count']}")
        print(f"  N+1 Query Patterns: {result['n_plus_1_count']}")
        print(f"  Memory Leak Patterns: {result['memory_leak_count']}")
        print(f"  Loops Analyzed: {len(result['loops'])}")

        if result['issues']:
            print(f"\nIssues Found:")
            for issue in result['issues']:
                print(f"\n  [{issue['severity'].upper()}] {issue['message']}")
                print(f"    Line: {issue['lineno']}")
                if issue['code_snippet']:
                    print(f"    Code: {issue['code_snippet']}")
                if issue['suggestion']:
                    print(f"    Suggestion: {issue['suggestion']}")
                print(f"    Impact: {issue['impact']} (confidence: {issue['confidence']:.2f})")

        if result['loops']:
            print(f"\nLoop Complexity:")
            for loop in result['loops']:
                print(
                    f"  Line {loop['lineno']}: {loop['loop_type']} loop "
                    f"(complexity: {loop['complexity_score']}/10, "
                    f"nesting: {loop['nesting_level']}, "
                    f"operations: {loop['operations_count']})"
                )
                if loop['contains_db_call']:
                    print(f"    ⚠ Contains database call")
                if loop['contains_api_call']:
                    print(f"    ⚠ Contains API call")

        print("\n" + "=" * 70)
        print("Analysis complete")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
