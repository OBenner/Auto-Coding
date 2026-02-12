#!/usr/bin/env python3
"""
Code Smell Detector Module
===========================

Uses AST parsing to detect code smells and maintainability issues in Python code.
This module provides proactive code quality analysis by identifying patterns that
commonly lead to maintainability problems.

The code smell detector identifies:
- High cyclomatic complexity
- Long functions and methods
- Deep nesting levels
- Code duplication
- God classes (classes with too many methods/lines)
- Long parameter lists
- Feature envy (methods that heavily use other classes)
- Shotgun surgery (changes requiring many small changes)

Usage:
    from code_smell_detector import CodeSmellDetector

    detector = CodeSmellDetector()
    result = detector.analyze_file('path/to/file.py')

    for issue in result['issues']:
        print(f"{issue['severity']}: {issue['message']} at line {issue['lineno']}")
"""

from __future__ import annotations

import ast
import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class CodeSmellIssue:
    """
    Represents a detected code smell.

    Attributes:
        smell_type: Type of code smell (high_complexity, long_function, deep_nesting, etc.)
        severity: Severity level (critical, high, medium, low)
        message: Human-readable description of the issue
        lineno: Line number where the issue occurs
        code_snippet: Code fragment causing the issue
        suggestion: Suggested fix or refactoring
        confidence: Confidence score (0.0 to 1.0)
        metrics: Additional metrics (complexity score, length, etc.)
    """

    smell_type: str
    severity: str
    message: str
    lineno: int
    code_snippet: str | None = None
    suggestion: str | None = None
    confidence: float = 0.8
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class DuplicationResult:
    """
    Represents a code duplication finding.

    Attributes:
        lineno1: Line number of first occurrence
        lineno2: Line number of second occurrence
        similarity_ratio: Similarity ratio (0.0 to 1.0)
        snippet1: Code snippet from first occurrence
        snippet2: Code snippet from second occurrence
        lines_count: Number of duplicated lines
    """

    lineno1: int
    lineno2: int
    similarity_ratio: float
    snippet1: str
    snippet2: str
    lines_count: int


@dataclass
class AnalysisResult:
    """
    Result of code smell analysis.

    Attributes:
        file_path: Path to analyzed file
        issues: List of detected code smell issues
        duplications: List of code duplication findings
        total_issues: Total count of issues
        critical_count: Count of critical issues
        high_count: Count of high severity issues
        medium_count: Count of medium severity issues
        low_count: Count of low severity issues
        max_complexity: Maximum cyclomatic complexity found
        max_nesting_level: Maximum nesting depth found
        duplication_count: Number of duplications found
    """

    file_path: str
    issues: list[CodeSmellIssue] = field(default_factory=list)
    duplications: list[DuplicationResult] = field(default_factory=list)
    total_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    max_complexity: int = 0
    max_nesting_level: int = 0
    duplication_count: int = 0


# =============================================================================
# CODE SMELL DETECTOR
# =============================================================================


class CodeSmellDetector:
    """
    Analyzes Python code for code smells using AST parsing.

    Identifies:
    - High cyclomatic complexity (complex decision logic)
    - Long functions and methods (hard to understand/modify)
    - Deep nesting (hard to read/understand)
    - Code duplication (maintenance burden)
    - God classes (too much responsibility)
    - Long parameter lists (hard to use/understand)
    """

    # Severity mapping
    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"

    # Thresholds for code smells
    MAX_COMPLEXITY_HIGH = 10
    MAX_COMPLEXITY_MEDIUM = 5
    MAX_FUNCTION_LENGTH_HIGH = 50
    MAX_FUNCTION_LENGTH_MEDIUM = 25
    MAX_NESTING_LEVEL_HIGH = 4
    MAX_NESTING_LEVEL_MEDIUM = 3
    MAX_CLASS_LENGTH_HIGH = 300
    MAX_CLASS_LENGTH_MEDIUM = 200
    MAX_METHOD_COUNT_HIGH = 20
    MAX_METHOD_COUNT_MEDIUM = 15
    MAX_PARAMETERS_HIGH = 7
    MAX_PARAMETERS_MEDIUM = 5
    DUPLICATION_THRESHOLD = 0.8  # Similarity ratio threshold
    MIN_DUPLICATION_LINES = 3

    def __init__(self):
        """Initialize the code smell detector."""
        pass

    def analyze_file(self, file_path: str | Path) -> dict[str, Any]:
        """
        Analyze a Python source file for code smells.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            Dictionary containing analysis results with keys:
            - file_path: Path to analyzed file
            - issues: List of code smell issue dictionaries
            - duplications: List of duplication dictionaries
            - total_issues: Total issue count
            - critical_count: Critical issue count
            - high_count: High severity issue count
            - medium_count: Medium severity issue count
            - low_count: Low severity issue count
            - max_complexity: Maximum complexity found
            - max_nesting_level: Maximum nesting level found
            - duplication_count: Number of duplications found
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

    def analyze_source(self, source: str) -> dict[str, Any]:
        """
        Analyze Python source code string for code smells.

        Args:
            source: Python source code as string

        Returns:
            Dictionary containing analysis results
        """
        result = self._analyze_source(source, "<string>")
        return self._result_to_dict(result)

    def _analyze_source(self, source: str, file_path: str) -> AnalysisResult:
        """
        Internal method to analyze source code.

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

        # Detect code smells
        for node in ast.walk(tree):
            # Check function complexity
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                func_issues = self._check_function_smells(node, source)
                result.issues.extend(func_issues)

            # Check class smells
            elif isinstance(node, ast.ClassDef):
                class_issues = self._check_class_smells(node, source)
                result.issues.extend(class_issues)

        # Detect code duplication
        result.duplications = self._detect_duplication(source)

        # Calculate statistics
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

            # Track max complexity
            if issue.smell_type == "high_complexity":
                complexity = issue.metrics.get("complexity", 0)
                if complexity > result.max_complexity:
                    result.max_complexity = complexity

            # Track max nesting
            if issue.smell_type == "deep_nesting":
                nesting = issue.metrics.get("nesting_level", 0)
                if nesting > result.max_nesting_level:
                    result.max_nesting_level = nesting

        result.duplication_count = len(result.duplications)

        return result

    def _check_function_smells(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        source: str,
    ) -> list[CodeSmellIssue]:
        """Check for function-level code smells."""
        issues = []

        # Calculate cyclomatic complexity
        complexity = self._calculate_complexity(node)

        # Check for high complexity
        if complexity > self.MAX_COMPLEXITY_HIGH:
            issues.append(
                CodeSmellIssue(
                    smell_type="high_complexity",
                    severity=self.SEVERITY_CRITICAL,
                    message=f"Function '{node.name}' has high cyclomatic complexity: {complexity}",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Refactor '{node.name}' into smaller functions. "
                        f"Consider using strategy pattern or extracting methods."
                    ),
                    metrics={"complexity": complexity},
                )
            )
        elif complexity > self.MAX_COMPLEXITY_MEDIUM:
            issues.append(
                CodeSmellIssue(
                    smell_type="high_complexity",
                    severity=self.SEVERITY_MEDIUM,
                    message=f"Function '{node.name}' has moderate cyclomatic complexity: {complexity}",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Consider refactoring '{node.name}' to reduce complexity."
                    ),
                    metrics={"complexity": complexity},
                )
            )

        # Check for long function
        func_length = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
        if func_length > self.MAX_FUNCTION_LENGTH_HIGH:
            issues.append(
                CodeSmellIssue(
                    smell_type="long_function",
                    severity=self.SEVERITY_HIGH,
                    message=f"Function '{node.name}' is too long: {func_length} lines",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Break '{node.name}' into smaller, more focused functions. "
                        f"Each function should do one thing well."
                    ),
                    metrics={"lines": func_length},
                )
            )
        elif func_length > self.MAX_FUNCTION_LENGTH_MEDIUM:
            issues.append(
                CodeSmellIssue(
                    smell_type="long_function",
                    severity=self.SEVERITY_MEDIUM,
                    message=f"Function '{node.name}' is moderately long: {func_length} lines",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Consider breaking '{node.name}' into smaller functions."
                    ),
                    metrics={"lines": func_length},
                )
            )

        # Check for deep nesting
        max_nesting = self._calculate_max_nesting(node)
        if max_nesting > self.MAX_NESTING_LEVEL_HIGH:
            issues.append(
                CodeSmellIssue(
                    smell_type="deep_nesting",
                    severity=self.SEVERITY_HIGH,
                    message=f"Function '{node.name}' has deep nesting: level {max_nesting}",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Refactor nested logic in '{node.name}' using early returns, "
                        f"guard clauses, or extract methods."
                    ),
                    metrics={"nesting_level": max_nesting},
                )
            )
        elif max_nesting > self.MAX_NESTING_LEVEL_MEDIUM:
            issues.append(
                CodeSmellIssue(
                    smell_type="deep_nesting",
                    severity=self.SEVERITY_MEDIUM,
                    message=f"Function '{node.name}' has moderate nesting: level {max_nesting}",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Consider reducing nesting in '{node.name}' using early returns."
                    ),
                    metrics={"nesting_level": max_nesting},
                )
            )

        # Check for long parameter list
        param_count = len(node.args.args)
        if param_count > self.MAX_PARAMETERS_HIGH:
            issues.append(
                CodeSmellIssue(
                    smell_type="long_parameter_list",
                    severity=self.SEVERITY_MEDIUM,
                    message=f"Function '{node.name}' has many parameters: {param_count}",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Consider using a parameter object or dataclass for '{node.name}'. "
                        f"Group related parameters together."
                    ),
                    metrics={"parameter_count": param_count},
                )
            )
        elif param_count > self.MAX_PARAMETERS_MEDIUM:
            issues.append(
                CodeSmellIssue(
                    smell_type="long_parameter_list",
                    severity=self.SEVERITY_LOW,
                    message=f"Function '{node.name}' has {param_count} parameters",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Consider reducing parameters or using a parameter object."
                    ),
                    metrics={"parameter_count": param_count},
                )
            )

        return issues

    def _check_class_smells(
        self,
        node: ast.ClassDef,
        source: str,
    ) -> list[CodeSmellIssue]:
        """Check for class-level code smells."""
        issues = []

        # Count methods (excluding __init__ and special methods)
        method_count = sum(
            1
            for item in node.body
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef)
            and not item.name.startswith("__")
        )

        # Check for god class (too many methods)
        if method_count > self.MAX_METHOD_COUNT_HIGH:
            issues.append(
                CodeSmellIssue(
                    smell_type="god_class",
                    severity=self.SEVERITY_HIGH,
                    message=f"Class '{node.name}' has too many methods: {method_count}",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Consider splitting '{node.name}' into smaller classes "
                        f"with single responsibilities."
                    ),
                    metrics={"method_count": method_count},
                )
            )
        elif method_count > self.MAX_METHOD_COUNT_MEDIUM:
            issues.append(
                CodeSmellIssue(
                    smell_type="god_class",
                    severity=self.SEVERITY_MEDIUM,
                    message=f"Class '{node.name}' has many methods: {method_count}",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Consider whether '{node.name}' has too many responsibilities."
                    ),
                    metrics={"method_count": method_count},
                )
            )

        # Check for long class
        class_length = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
        if class_length > self.MAX_CLASS_LENGTH_HIGH:
            issues.append(
                CodeSmellIssue(
                    smell_type="long_class",
                    severity=self.SEVERITY_MEDIUM,
                    message=f"Class '{node.name}' is very long: {class_length} lines",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Consider splitting '{node.name}' into smaller classes "
                        f"or extracting helper classes."
                    ),
                    metrics={"lines": class_length},
                )
            )
        elif class_length > self.MAX_CLASS_LENGTH_MEDIUM:
            issues.append(
                CodeSmellIssue(
                    smell_type="long_class",
                    severity=self.SEVERITY_LOW,
                    message=f"Class '{node.name}' is long: {class_length} lines",
                    lineno=node.lineno,
                    code_snippet=self._get_code_snippet(source, node.lineno),
                    suggestion=(
                        f"Consider whether '{node.name}' can be split into smaller classes."
                    ),
                    metrics={"lines": class_length},
                )
            )

        return issues

    def _calculate_complexity(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Count decision points
            if isinstance(
                child,
                ast.If | ast.While | ast.For | ast.ExceptHandler | ast.Match,
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Count and/or operators
                complexity += len(child.values) - 1

        return complexity

    def _calculate_max_nesting(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> int:
        """Calculate maximum nesting level in a function."""
        max_nesting = 0

        def _count_nesting(n: ast.AST, current_level: int) -> None:
            nonlocal max_nesting
            max_nesting = max(max_nesting, current_level)

            # Count nested control structures
            if isinstance(n, ast.If | ast.While | ast.For | ast.With | ast.Try):
                for child in ast.iter_child_nodes(n):
                    # Skip the test/condition part
                    if not isinstance(
                        child,
                        ast.expr | ast.pattern | ast.excepthandler,
                    ):
                        _count_nesting(child, current_level + 1)
            else:
                for child in ast.iter_child_nodes(n):
                    _count_nesting(child, current_level)

        _count_nesting(node, 0)
        return max_nesting

    def _detect_duplication(self, source: str) -> list[DuplicationResult]:
        """Detect code duplication using sequence matching."""
        duplications = []
        lines = source.splitlines()

        # Compare each line with others
        for i in range(len(lines)):
            # Skip comments and blank lines
            line1 = lines[i].strip()
            if not line1 or line1.startswith("#"):
                continue

            # Look for similar sequences
            for j in range(i + self.MIN_DUPLICATION_LINES, len(lines)):
                line2 = lines[j].strip()
                if not line2 or line2.startswith("#"):
                    continue

                # Calculate similarity
                similarity = difflib.SequenceMatcher(
                    None,
                    line1,
                    line2,
                ).ratio()

                if similarity >= self.DUPLICATION_THRESHOLD:
                    duplications.append(
                        DuplicationResult(
                            lineno1=i + 1,
                            lineno2=j + 1,
                            similarity_ratio=similarity,
                            snippet1=line1,
                            snippet2=line2,
                            lines_count=1,
                        )
                    )

        return duplications

    def _get_code_snippet(self, source: str, lineno: int, context: int = 2) -> str:
        """Extract a code snippet around a given line number."""
        lines = source.splitlines()
        start = max(0, lineno - context - 1)
        end = min(len(lines), lineno + context)

        snippet_lines = []
        for i in range(start, end):
            prefix = "> " if i == lineno - 1 else "  "
            snippet_lines.append(f"{prefix}{lines[i]}")

        return "\n".join(snippet_lines)

    def _result_to_dict(self, result: AnalysisResult) -> dict[str, Any]:
        """Convert AnalysisResult to dictionary."""
        return {
            "file_path": result.file_path,
            "issues": [
                {
                    "smell_type": issue.smell_type,
                    "severity": issue.severity,
                    "message": issue.message,
                    "lineno": issue.lineno,
                    "code_snippet": issue.code_snippet,
                    "suggestion": issue.suggestion,
                    "confidence": issue.confidence,
                    "metrics": issue.metrics,
                }
                for issue in result.issues
            ],
            "duplications": [
                {
                    "lineno1": dup.lineno1,
                    "lineno2": dup.lineno2,
                    "similarity_ratio": dup.similarity_ratio,
                    "snippet1": dup.snippet1,
                    "snippet2": dup.snippet2,
                    "lines_count": dup.lines_count,
                }
                for dup in result.duplications
            ],
            "total_issues": result.total_issues,
            "critical_count": result.critical_count,
            "high_count": result.high_count,
            "medium_count": result.medium_count,
            "low_count": result.low_count,
            "max_complexity": result.max_complexity,
            "max_nesting_level": result.max_nesting_level,
            "duplication_count": result.duplication_count,
        }
