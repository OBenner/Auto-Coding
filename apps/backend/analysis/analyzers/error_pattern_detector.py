"""
Error Pattern Detector Module
==============================

Detects and analyzes error handling patterns in Python codebases.
Identifies try/except patterns, custom exceptions, error messages, and logging practices.

This module helps agents understand and replicate the error handling conventions
used in a codebase to maintain consistency.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from .base import BaseAnalyzer, collect_files


class ErrorPatternDetector(BaseAnalyzer):
    """Analyzes and detects error handling patterns in Python code."""

    def __init__(self, path: Path):
        super().__init__(path)
        self.error_patterns: dict[str, Any] = {
            "exception_types": {},
            "error_messages": [],
            "custom_exceptions": [],
            "try_except_patterns": [],
            "logging_patterns": [],
            "error_propagation": {"re_raises": 0, "handles": 0, "wraps": 0},
        }

    def detect_error_patterns(self) -> dict[str, Any]:
        """
        Detect error handling patterns across the codebase.

        Returns:
            Dictionary containing detected error patterns with keys:
            - exception_types: Most commonly caught exception types
            - error_messages: Common error message formats
            - custom_exceptions: Custom exception classes defined in project
            - try_except_patterns: Common try/except structures
            - logging_patterns: How errors are logged
            - error_propagation: Whether errors are re-raised, handled, or wrapped
        """
        # Find all Python files, excluding common directories
        py_files = collect_files(self.path, "*.py", limit=50)

        # Analyze error patterns in each file
        for file in py_files:
            try:
                self._analyze_file_error_patterns(file)
            except (OSError, UnicodeDecodeError, SyntaxError):
                continue

        # Summarize findings
        return self._summarize_patterns()

    def _analyze_file_error_patterns(self, file_path: Path) -> None:
        """Analyze error handling patterns in a single file."""
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (OSError, UnicodeDecodeError, SyntaxError):
            return

        # Detect custom exception classes
        self._detect_custom_exceptions(tree)

        # Analyze try/except blocks
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                self._analyze_try_block(node, source)

            # Detect error raising patterns
            elif isinstance(node, ast.Raise):
                self._analyze_raise_statement(node)

    def _detect_custom_exceptions(self, tree: ast.AST) -> None:
        """Detect custom exception classes defined in the codebase."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class inherits from Exception or a known exception
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = ast.unparse(base)

                    if "Exception" in base_name or "Error" in base_name:
                        if node.name not in [
                            exc["name"]
                            for exc in self.error_patterns["custom_exceptions"]
                        ]:
                            self.error_patterns["custom_exceptions"].append(
                                {
                                    "name": node.name,
                                    "base": base_name,
                                    "lineno": node.lineno,
                                    "docstring": ast.get_docstring(node),
                                }
                            )

    def _analyze_try_block(self, node: ast.Try, source: str) -> None:
        """Analyze a try/except block for patterns."""
        pattern = {
            "exception_types": [],
            "has_else": bool(node.orelse),
            "has_finally": bool(node.finalbody),
        }

        for handler in node.handlers:
            exc_type = "Exception"
            if handler.type:
                if isinstance(handler.type, ast.Name):
                    exc_type = handler.type.id
                elif isinstance(handler.type, ast.Attribute):
                    exc_type = ast.unparse(handler.type)
                elif isinstance(handler.type, ast.Tuple):
                    # Multiple exception types in one handler
                    exc_type = ast.unparse(handler.type)

            pattern["exception_types"].append(exc_type)

            # Track exception type frequency
            self.error_patterns["exception_types"][exc_type] = (
                self.error_patterns["exception_types"].get(exc_type, 0) + 1
            )

            # Analyze what happens in the handler
            self._analyze_exception_handler(handler)

            # Extract error messages from handler
            self._extract_error_messages(handler)

        # Store the try/except pattern
        if pattern not in self.error_patterns["try_except_patterns"]:
            self.error_patterns["try_except_patterns"].append(pattern)

    def _analyze_exception_handler(self, handler: ast.ExceptHandler) -> None:
        """Analyze what happens inside an exception handler."""
        for node in ast.walk(handler):
            # Check if exception is re-raised
            if isinstance(node, ast.Raise):
                if node.exc is None:
                    # Bare raise - re-raising
                    self.error_patterns["error_propagation"]["re_raises"] += 1
                else:
                    # Raising new exception - wrapping
                    self.error_patterns["error_propagation"]["wraps"] += 1

            # Check for logging calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                    if func_name in ["error", "exception", "warning", "critical"]:
                        # Logging pattern detected
                        obj = (
                            ast.unparse(node.func.value)
                            if hasattr(node.func, "value")
                            else ""
                        )
                        pattern = f"{obj}.{func_name}"
                        if pattern not in self.error_patterns["logging_patterns"]:
                            self.error_patterns["logging_patterns"].append(pattern)

        # If no re-raise or wrap, assume it's handled
        has_raise = any(isinstance(n, ast.Raise) for n in ast.walk(handler))
        if not has_raise:
            self.error_patterns["error_propagation"]["handles"] += 1

    def _analyze_raise_statement(self, node: ast.Raise) -> None:
        """Analyze error raising patterns."""
        if node.exc is None:
            # Bare raise (re-raising)
            return

        # Get the exception type being raised
        exc_type = "Exception"
        if isinstance(node.exc, ast.Call):
            if isinstance(node.exc.func, ast.Name):
                exc_type = node.exc.func.id
            elif isinstance(node.exc.func, ast.Attribute):
                exc_type = ast.unparse(node.exc.func)

            # Extract error message if present
            if node.exc.args:
                for arg in node.exc.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        self._add_error_message(arg.value, exc_type)
                    elif isinstance(arg, ast.JoinedStr):
                        # f-string error message
                        self._add_error_message("<f-string>", exc_type)

    def _extract_error_messages(self, handler: ast.ExceptHandler) -> None:
        """Extract error messages from logging calls in handler."""
        for node in ast.walk(handler):
            if isinstance(node, ast.Call):
                # Check for logging calls with message
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                    if func_name in ["error", "exception", "warning", "critical"]:
                        for arg in node.args:
                            if isinstance(arg, ast.Constant) and isinstance(
                                arg.value, str
                            ):
                                self._add_error_message(arg.value, "logged")

    def _add_error_message(self, message: str, context: str) -> None:
        """Add an error message to the patterns."""
        # Analyze message format
        message_format = self._analyze_message_format(message)

        message_info = {
            "message": message[:100],  # Truncate long messages
            "context": context,
            "format": message_format,
        }

        # Only add if not already present
        if message_info not in self.error_patterns["error_messages"][-20:]:
            self.error_patterns["error_messages"].append(message_info)

    def _analyze_message_format(self, message: str) -> dict[str, Any]:
        """Analyze the format of an error message."""
        format_info = {
            "has_interpolation": bool(
                re.search(r"\{.*\}|%s|%d|%r", message)
            ),  # Format strings
            "starts_with_capital": message[0].isupper() if message else False,
            "ends_with_period": message.endswith(".") if message else False,
            "has_quotes": '"' in message or "'" in message,
            "length": len(message),
        }

        return format_info

    def _summarize_patterns(self) -> dict[str, Any]:
        """Summarize detected error patterns into actionable insights."""
        # Sort exception types by frequency
        sorted_exceptions = sorted(
            self.error_patterns["exception_types"].items(),
            key=lambda x: x[1],
            reverse=True,
        )

        # Determine predominant error handling strategy
        propagation = self.error_patterns["error_propagation"]
        total = propagation["re_raises"] + propagation["handles"] + propagation["wraps"]

        strategy = "unknown"
        if total > 0:
            if propagation["handles"] / total > 0.6:
                strategy = "handle_locally"
            elif propagation["re_raises"] / total > 0.4:
                strategy = "propagate"
            elif propagation["wraps"] / total > 0.3:
                strategy = "wrap_and_raise"
            else:
                strategy = "mixed"

        # Determine common error message format
        message_format = self._determine_message_format()

        return {
            "common_exceptions": [
                {"type": exc, "count": count} for exc, count in sorted_exceptions[:10]
            ],
            "custom_exceptions": self.error_patterns["custom_exceptions"][:10],
            "error_handling_strategy": strategy,
            "logging_patterns": list(set(self.error_patterns["logging_patterns"][:10])),
            "message_format": message_format,
            "try_except_patterns": self.error_patterns["try_except_patterns"][:5],
            "error_propagation_stats": propagation,
        }

    def _determine_message_format(self) -> dict[str, Any]:
        """Determine the predominant error message format."""
        if not self.error_patterns["error_messages"]:
            return {
                "style": "unknown",
                "capitalization": "unknown",
                "punctuation": "unknown",
            }

        messages = self.error_patterns["error_messages"]
        total = len(messages)

        # Analyze capitalization
        capitalized = sum(
            1
            for msg in messages
            if msg.get("format", {}).get("starts_with_capital", False)
        )
        capitalization = "capital" if capitalized / total > 0.7 else "lowercase"

        # Analyze punctuation
        with_period = sum(
            1
            for msg in messages
            if msg.get("format", {}).get("ends_with_period", False)
        )
        punctuation = "period" if with_period / total > 0.5 else "no_period"

        # Analyze interpolation
        with_interpolation = sum(
            1
            for msg in messages
            if msg.get("format", {}).get("has_interpolation", False)
        )
        uses_interpolation = with_interpolation / total > 0.5

        return {
            "style": "descriptive" if uses_interpolation else "simple",
            "capitalization": capitalization,
            "punctuation": punctuation,
            "uses_interpolation": uses_interpolation,
        }


def detect_error_patterns(path: Path) -> dict[str, Any]:
    """
    Public API to detect error handling patterns in a codebase.

    Args:
        path: Path to project directory

    Returns:
        Dictionary containing detected error handling patterns
    """
    detector = ErrorPatternDetector(path)
    return detector.detect_error_patterns()
