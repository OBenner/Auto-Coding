#!/usr/bin/env python3
"""
Bug Detector Module
===================

Uses AST parsing to detect potential runtime errors before code execution.
This module provides proactive bug detection by analyzing code patterns that
commonly lead to runtime errors.

The bug detector identifies:
- NoneType errors (attribute access on None, function calls on None)
- IndexError (list access without bounds checking)
- KeyError (dict access without .get() or key checking)
- Unhandled exceptions
- Division by zero risks
- Missing validation patterns

Usage:
    from bug_detector import BugDetector

    detector = BugDetector()
    result = detector.detect_issues('path/to/file.py')

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
class BugReport:
    """
    Represents a detected bug or potential runtime error.

    Attributes:
        bug_type: Type of bug (nonetype_error, index_error, key_error, etc.)
        severity: Severity level (critical, high, medium, low)
        message: Human-readable description of the issue
        lineno: Line number where the issue occurs
        code_snippet: Code fragment causing the issue
        suggestion: Suggested fix or mitigation
        confidence: Confidence score (0.0 to 1.0)
    """

    bug_type: str
    severity: str
    message: str
    lineno: int
    code_snippet: str | None = None
    suggestion: str | None = None
    confidence: float = 0.8


@dataclass
class DetectionResult:
    """
    Result of bug detection analysis.

    Attributes:
        file_path: Path to analyzed file
        issues: List of detected bug reports
        total_issues: Total count of issues
        critical_count: Count of critical issues
        high_count: Count of high severity issues
        medium_count: Count of medium severity issues
        low_count: Count of low severity issues
    """

    file_path: str
    issues: list[BugReport] = field(default_factory=list)
    total_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0


# =============================================================================
# BUG DETECTOR
# =============================================================================


class BugDetector:
    """
    Detects potential runtime errors using AST pattern matching.

    Identifies common bug patterns:
    - NoneType attribute access
    - Unchecked list indexing
    - Dict key access without safety checks
    - Division operations without zero checks
    - Unsafe type conversions
    - Missing error handlers
    """

    # Severity mapping
    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"

    def __init__(self):
        """Initialize the bug detector."""
        pass

    def detect_issues(self, file_path: str | Path) -> dict[str, Any]:
        """
        Detect potential bugs in a Python source file.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            Dictionary containing detection results with keys:
            - file_path: Path to analyzed file
            - issues: List of bug report dictionaries
            - total_issues: Total issue count
            - critical_count: Critical issue count
            - high_count: High severity issue count
            - medium_count: Medium severity issue count
            - low_count: Low severity issue count
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"Unable to read file as UTF-8: {file_path}")

        result = self._detect_from_source(source, str(path))
        return self._result_to_dict(result)

    def detect_from_source(self, source: str, file_path: str = "<string>") -> dict[str, Any]:
        """
        Detect bugs in Python source code string.

        Args:
            source: Python source code as string
            file_path: Optional file path for reporting

        Returns:
            Dictionary containing detection results
        """
        result = self._detect_from_source(source, file_path)
        return self._result_to_dict(result)

    def _detect_from_source(self, source: str, file_path: str) -> DetectionResult:
        """
        Internal method to detect bugs in source code.

        Args:
            source: Python source code
            file_path: Path for error reporting

        Returns:
            DetectionResult object
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in {file_path}: {e}")

        result = DetectionResult(file_path=file_path)

        # Track safe operations (within validation blocks)
        safe_operations = self._find_safe_operations(tree)

        # Detect various bug patterns
        for node in ast.walk(tree):
            # Detect NoneType errors
            none_issues = self._check_nonetype_errors(node, safe_operations)
            result.issues.extend(none_issues)

            # Detect IndexError risks
            index_issues = self._check_index_errors(node, safe_operations)
            result.issues.extend(index_issues)

            # Detect KeyError risks
            key_issues = self._check_key_errors(node, safe_operations)
            result.issues.extend(key_issues)

            # Detect division by zero risks
            div_issues = self._check_division_by_zero(node, safe_operations)
            result.issues.extend(div_issues)

            # Detect unsafe type operations
            type_issues = self._check_unsafe_type_operations(node, safe_operations)
            result.issues.extend(type_issues)

        # Count issues by severity
        result.total_issues = len(result.issues)
        result.critical_count = sum(1 for i in result.issues if i.severity == self.SEVERITY_CRITICAL)
        result.high_count = sum(1 for i in result.issues if i.severity == self.SEVERITY_HIGH)
        result.medium_count = sum(1 for i in result.issues if i.severity == self.SEVERITY_MEDIUM)
        result.low_count = sum(1 for i in result.issues if i.severity == self.SEVERITY_LOW)

        return result

    def _find_safe_operations(self, tree: ast.AST) -> set[int]:
        """
        Find line numbers of operations within safe validation blocks.

        Args:
            tree: AST tree

        Returns:
            Set of line numbers that are within safe blocks
        """
        safe_lines = set()

        for node in ast.walk(tree):
            # Operations within if statements checking for None/empty are safe
            if isinstance(node, ast.If):
                # Check if condition is a validation check
                if self._is_validation_condition(node.test):
                    # All lines in this if block are safe
                    for body_node in ast.walk(node):
                        if hasattr(body_node, 'lineno'):
                            safe_lines.add(body_node.lineno)

            # Operations within try blocks are considered safe
            if isinstance(node, ast.Try):
                for body_node in ast.walk(node):
                    if hasattr(body_node, 'lineno'):
                        safe_lines.add(body_node.lineno)

        return safe_lines

    def _is_validation_condition(self, node: ast.AST) -> bool:
        """
        Check if a node is a validation condition (None check, empty check, etc.).

        Args:
            node: AST node

        Returns:
            True if this is a validation condition
        """
        code = ast.unparse(node) if hasattr(node, 'lineno') else ""

        # Check for None checks
        if "is not None" in code or "is None" in code:
            return True

        # Check for empty checks
        if any(pattern in code for pattern in ["len(", "if not ", "if "]):
            if any(op in code for op in ["== 0", "> 0", "< 1"]):
                return True

        # Check for isinstance/type checks
        if "isinstance(" in code:
            return True

        return False

    def _check_nonetype_errors(
        self, node: ast.AST, safe_operations: set[int]
    ) -> list[BugReport]:
        """
        Detect potential NoneType errors.

        Args:
            node: AST node to check
            safe_operations: Set of safe line numbers

        Returns:
            List of BugReport objects
        """
        issues = []

        # Check for attribute access that could fail on None
        if isinstance(node, ast.Attribute):
            code = ast.unparse(node)
            if node.lineno not in safe_operations:
                issues.append(
                    BugReport(
                        bug_type="nonetype_error",
                        severity=self.SEVERITY_HIGH,
                        message=f"Potential NoneType error: attribute access without None check",
                        lineno=node.lineno,
                        code_snippet=code,
                        suggestion=f"Add None check before accessing: if {ast.unparse(node.value)} is not None",
                        confidence=0.7,
                    )
                )

        # Check for function/method calls that could fail on None
        if isinstance(node, ast.Call):
            code = ast.unparse(node)
            # Check if calling on potentially None object
            if isinstance(node.func, ast.Attribute):
                if node.lineno not in safe_operations:
                    issues.append(
                        BugReport(
                            bug_type="nonetype_error",
                            severity=self.SEVERITY_HIGH,
                            message=f"Potential NoneType error: method call without None check",
                            lineno=node.lineno,
                            code_snippet=code,
                            suggestion=f"Add None check before calling: if {ast.unparse(node.func.value)} is not None",
                            confidence=0.6,
                        )
                    )

        return issues

    def _check_index_errors(
        self, node: ast.AST, safe_operations: set[int]
    ) -> list[BugReport]:
        """
        Detect potential IndexError from list/dict subscript access.

        Args:
            node: AST node to check
            safe_operations: Set of safe line numbers

        Returns:
            List of BugReport objects
        """
        issues = []

        # Check for subscript operations (list[index], dict[key])
        if isinstance(node, ast.Subscript):
            if node.lineno not in safe_operations:
                code = ast.unparse(node)

                # Check if index is a literal (could be out of bounds)
                if isinstance(node.slice, ast.Constant):
                    if isinstance(node.slice.value, int):
                        if node.slice.value < 0 or node.slice.value > 1000:  # Heuristic
                            issues.append(
                                BugReport(
                                    bug_type="index_error",
                                    severity=self.SEVERITY_MEDIUM,
                                    message=f"Potential IndexError: hardcoded index {node.slice.value}",
                                    lineno=node.lineno,
                                    code_snippet=code,
                                    suggestion=f"Check bounds before accessing: if len({ast.unparse(node.value)}) > {node.slice.value}",
                                    confidence=0.5,
                                )
                            )

                # Check for unsafe indexing without validation
                elif not isinstance(node.slice, ast.Slice):  # Not a slice operation
                    issues.append(
                        BugReport(
                            bug_type="index_error",
                            severity=self.SEVERITY_LOW,
                            message=f"Potential IndexError: subscript access without bounds check",
                            lineno=node.lineno,
                            code_snippet=code,
                            suggestion=f"Add bounds check: if len({ast.unparse(node.value)}) > index",
                            confidence=0.4,
                        )
                    )

        return issues

    def _check_key_errors(
        self, node: ast.AST, safe_operations: set[int]
    ) -> list[BugReport]:
        """
        Detect potential KeyError from dictionary key access.

        Args:
            node: AST node to check
            safe_operations: Set of safe line numbers

        Returns:
            List of BugReport objects
        """
        issues = []

        # Check for dict[key] access (not dict.get())
        if isinstance(node, ast.Subscript):
            if node.lineno not in safe_operations:
                code = ast.unparse(node)

                # Check if this looks like dict access (not list slice)
                if isinstance(node.slice, (ast.Constant, ast.Name, ast.Attribute)):
                    issues.append(
                        BugReport(
                            bug_type="key_error",
                            severity=self.SEVERITY_MEDIUM,
                            message=f"Potential KeyError: dictionary key access without .get() or 'in' check",
                            lineno=node.lineno,
                            code_snippet=code,
                            suggestion=f"Use .get() method or check key existence: if key in dict",
                            confidence=0.5,
                        )
                    )

        return issues

    def _check_division_by_zero(
        self, node: ast.AST, safe_operations: set[int]
    ) -> list[BugReport]:
        """
        Detect potential division by zero errors.

        Args:
            node: AST node to check
            safe_operations: Set of safe line numbers

        Returns:
            List of BugReport objects
        """
        issues = []

        # Check for division operations
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                if node.lineno not in safe_operations:
                    code = ast.unparse(node)

                    # Check if dividing by a constant zero
                    if isinstance(node.right, ast.Constant):
                        if node.right.value == 0:
                            issues.append(
                                BugReport(
                                    bug_type="division_by_zero",
                                    severity=self.SEVERITY_CRITICAL,
                                    message=f"Division by zero: dividing by constant 0",
                                    lineno=node.lineno,
                                    code_snippet=code,
                                    suggestion="Remove division by zero or add validation",
                                    confidence=1.0,
                                )
                            )
                    else:
                        # Potential division by variable
                        issues.append(
                            BugReport(
                                bug_type="division_by_zero",
                                severity=self.SEVERITY_LOW,
                                message=f"Potential division by zero: no zero check on divisor",
                                lineno=node.lineno,
                                code_snippet=code,
                                suggestion=f"Add check: if {ast.unparse(node.right)} != 0",
                                confidence=0.3,
                            )
                        )

        return issues

    def _check_unsafe_type_operations(
        self, node: ast.AST, safe_operations: set[int]
    ) -> list[BugReport]:
        """
        Detect unsafe type operations that could cause runtime errors.

        Args:
            node: AST node to check
            safe_operations: Set of safe line numbers

        Returns:
            List of BugReport objects
        """
        issues = []

        # Check for int() conversion without validation
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "int":
                if node.lineno not in safe_operations:
                    code = ast.unparse(node)
                    if len(node.args) > 0:
                        issues.append(
                            BugReport(
                                bug_type="unsafe_conversion",
                                severity=self.SEVERITY_LOW,
                                message=f"Unsafe int() conversion without try/except",
                                lineno=node.lineno,
                                code_snippet=code,
                                suggestion="Wrap in try/except ValueError for safe conversion",
                                confidence=0.3,
                            )
                        )

        return issues

    def _result_to_dict(self, result: DetectionResult) -> dict[str, Any]:
        """
        Convert DetectionResult to dictionary.

        Args:
            result: DetectionResult object

        Returns:
            Dictionary representation
        """
        return {
            "file_path": result.file_path,
            "issues": [
                {
                    "bug_type": issue.bug_type,
                    "severity": issue.severity,
                    "message": issue.message,
                    "lineno": issue.lineno,
                    "code_snippet": issue.code_snippet,
                    "suggestion": issue.suggestion,
                    "confidence": issue.confidence,
                }
                for issue in result.issues
            ],
            "total_issues": result.total_issues,
            "critical_count": result.critical_count,
            "high_count": result.high_count,
            "medium_count": result.medium_count,
            "low_count": result.low_count,
        }
