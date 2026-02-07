"""
Pattern Extractor
=================

Extracts code patterns from files using AST-based code analysis.
Identifies patterns for API usage, error handling, state management, and more.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PatternExtractor:
    """Extracts code patterns from source files using AST analysis."""

    def __init__(self, project_dir: Path):
        """
        Initialize pattern extractor.

        Args:
            project_dir: Project root directory
        """
        self.project_dir = project_dir.resolve()

    def extract_patterns(
        self,
        file_path: Path,
        pattern_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract code patterns from a source file.

        Args:
            file_path: Path to source file to analyze
            pattern_types: Optional list of pattern types to extract
                          (e.g., ["api", "error", "state"])
                          If None, extracts all pattern types

        Returns:
            List of extracted patterns:
            [
                {
                    "type": "error-handling",
                    "pattern": "Try-catch with specific error types",
                    "code_snippet": "try:...",
                    "line_number": 42,
                    "context": "Function: handle_request"
                },
                ...
            ]
        """
        patterns = []

        # Determine which pattern types to extract
        all_types = ["api", "error", "state", "import", "class", "function"]
        types_to_extract = pattern_types if pattern_types else all_types

        try:
            # Resolve file path relative to project directory
            if not file_path.is_absolute():
                file_path = self.project_dir / file_path

            # Read source code
            source_code = file_path.read_text(encoding="utf-8", errors="ignore")

            # Determine language and extract patterns
            suffix = file_path.suffix.lower()
            if suffix == ".py":
                patterns.extend(
                    self._extract_python_patterns(
                        source_code, file_path, types_to_extract
                    )
                )
            elif suffix in [".js", ".jsx", ".ts", ".tsx"]:
                patterns.extend(
                    self._extract_javascript_patterns(
                        source_code, file_path, types_to_extract
                    )
                )
            else:
                # For other file types, use simple pattern matching
                patterns.extend(
                    self._extract_generic_patterns(
                        source_code, file_path, types_to_extract
                    )
                )

        except Exception as e:
            logger.warning(f"Failed to extract patterns from {file_path}: {e}")

        return patterns

    def _extract_python_patterns(
        self, source_code: str, file_path: Path, pattern_types: list[str]
    ) -> list[dict[str, Any]]:
        """Extract patterns from Python source using AST."""
        patterns = []

        try:
            tree = ast.parse(source_code)

            # Extract import patterns
            if "import" in pattern_types:
                patterns.extend(self._extract_python_imports(tree, source_code))

            # Extract error handling patterns
            if "error" in pattern_types:
                patterns.extend(self._extract_python_error_handling(tree, source_code))

            # Extract API usage patterns
            if "api" in pattern_types:
                patterns.extend(self._extract_python_api_patterns(tree, source_code))

            # Extract class patterns
            if "class" in pattern_types:
                patterns.extend(self._extract_python_class_patterns(tree, source_code))

            # Extract function patterns
            if "function" in pattern_types:
                patterns.extend(
                    self._extract_python_function_patterns(tree, source_code)
                )

        except SyntaxError as e:
            logger.debug(f"Failed to parse Python file {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Error extracting Python patterns from {file_path}: {e}")

        return patterns

    def _extract_python_imports(
        self, tree: ast.AST, source_code: str
    ) -> list[dict[str, Any]]:
        """Extract import patterns from Python AST."""
        patterns = []
        lines = source_code.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    snippet = self._get_code_snippet(lines, node.lineno, 1)
                    patterns.append(
                        {
                            "type": "import",
                            "pattern": f"Import module: {alias.name}",
                            "code_snippet": snippet,
                            "line_number": node.lineno,
                            "context": f"Module: {alias.name}",
                        }
                    )

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [alias.name for alias in node.names]
                snippet = self._get_code_snippet(lines, node.lineno, 1)
                patterns.append(
                    {
                        "type": "import",
                        "pattern": f"Import from {module}: {', '.join(names)}",
                        "code_snippet": snippet,
                        "line_number": node.lineno,
                        "context": f"Module: {module}",
                    }
                )

        return patterns

    def _extract_python_error_handling(
        self, tree: ast.AST, source_code: str
    ) -> list[dict[str, Any]]:
        """Extract error handling patterns from Python AST."""
        patterns = []
        lines = source_code.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                # Extract exception types
                exception_types = []
                for handler in node.handlers:
                    if handler.type:
                        if isinstance(handler.type, ast.Name):
                            exception_types.append(handler.type.id)
                        elif isinstance(handler.type, ast.Tuple):
                            for elt in handler.type.elts:
                                if isinstance(elt, ast.Name):
                                    exception_types.append(elt.id)

                # Get code snippet
                end_line = node.lineno + 5  # Get a few lines of context
                snippet = self._get_code_snippet(lines, node.lineno, end_line - node.lineno)

                pattern_desc = "Try-except"
                if exception_types:
                    pattern_desc += f" catching {', '.join(exception_types)}"
                if node.orelse:
                    pattern_desc += " with else clause"
                if node.finalbody:
                    pattern_desc += " with finally clause"

                patterns.append(
                    {
                        "type": "error-handling",
                        "pattern": pattern_desc,
                        "code_snippet": snippet,
                        "line_number": node.lineno,
                        "context": f"Exception types: {', '.join(exception_types) or 'generic'}",
                    }
                )

        return patterns

    def _extract_python_api_patterns(
        self, tree: ast.AST, source_code: str
    ) -> list[dict[str, Any]]:
        """Extract API usage patterns from Python AST."""
        patterns = []
        lines = source_code.split("\n")

        for node in ast.walk(tree):
            # Look for common API call patterns
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    # Method calls like client.get(), requests.post()
                    if isinstance(node.func.value, ast.Name):
                        obj_name = node.func.value.id
                        method_name = node.func.attr

                        # Identify common API patterns
                        api_keywords = ["client", "api", "request", "http", "fetch"]
                        if any(keyword in obj_name.lower() for keyword in api_keywords):
                            snippet = self._get_code_snippet(lines, node.lineno, 1)
                            patterns.append(
                                {
                                    "type": "api-design",
                                    "pattern": f"API call: {obj_name}.{method_name}()",
                                    "code_snippet": snippet,
                                    "line_number": node.lineno,
                                    "context": f"Object: {obj_name}, Method: {method_name}",
                                }
                            )

        return patterns

    def _extract_python_class_patterns(
        self, tree: ast.AST, source_code: str
    ) -> list[dict[str, Any]]:
        """Extract class definition patterns from Python AST."""
        patterns = []
        lines = source_code.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Extract base classes
                base_classes = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_classes.append(base.id)

                # Get decorators
                decorators = [
                    dec.id if isinstance(dec, ast.Name) else str(dec)
                    for dec in node.decorator_list
                ]

                snippet = self._get_code_snippet(lines, node.lineno, 3)

                pattern_desc = f"Class definition: {node.name}"
                if base_classes:
                    pattern_desc += f" (inherits from {', '.join(base_classes)})"
                if decorators:
                    pattern_desc += f" with decorators: {', '.join(decorators)}"

                patterns.append(
                    {
                        "type": "architecture",
                        "pattern": pattern_desc,
                        "code_snippet": snippet,
                        "line_number": node.lineno,
                        "context": f"Class: {node.name}",
                    }
                )

        return patterns

    def _extract_python_function_patterns(
        self, tree: ast.AST, source_code: str
    ) -> list[dict[str, Any]]:
        """Extract function definition patterns from Python AST."""
        patterns = []
        lines = source_code.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Get decorators
                decorators = []
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Name):
                        decorators.append(dec.id)
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                        decorators.append(dec.func.id)

                snippet = self._get_code_snippet(lines, node.lineno, 3)

                is_async = isinstance(node, ast.AsyncFunctionDef)
                pattern_desc = f"{'Async ' if is_async else ''}Function: {node.name}"
                if decorators:
                    pattern_desc += f" with decorators: {', '.join(decorators)}"

                patterns.append(
                    {
                        "type": "architecture",
                        "pattern": pattern_desc,
                        "code_snippet": snippet,
                        "line_number": node.lineno,
                        "context": f"Function: {node.name}, Async: {is_async}",
                    }
                )

        return patterns

    def _extract_javascript_patterns(
        self, source_code: str, file_path: Path, pattern_types: list[str]
    ) -> list[dict[str, Any]]:
        """
        Extract patterns from JavaScript/TypeScript source.

        Note: Full AST parsing for JS/TS would require additional dependencies.
        This implementation uses regex-based pattern matching for common patterns.
        """
        patterns = []
        lines = source_code.split("\n")

        # Extract import patterns
        if "import" in pattern_types:
            for i, line in enumerate(lines, start=1):
                if line.strip().startswith("import "):
                    patterns.append(
                        {
                            "type": "import",
                            "pattern": "ES6 import",
                            "code_snippet": line.strip(),
                            "line_number": i,
                            "context": "Import statement",
                        }
                    )

        # Extract error handling patterns
        if "error" in pattern_types:
            for i, line in enumerate(lines, start=1):
                if "try {" in line or "try{" in line:
                    snippet = self._get_code_snippet(lines, i, 5)
                    patterns.append(
                        {
                            "type": "error-handling",
                            "pattern": "Try-catch block",
                            "code_snippet": snippet,
                            "line_number": i,
                            "context": "JavaScript try-catch",
                        }
                    )

        # Extract state management patterns
        if "state" in pattern_types:
            for i, line in enumerate(lines, start=1):
                if "useState(" in line:
                    patterns.append(
                        {
                            "type": "state-management",
                            "pattern": "React useState hook",
                            "code_snippet": line.strip(),
                            "line_number": i,
                            "context": "React hooks",
                        }
                    )
                elif "useReducer(" in line:
                    patterns.append(
                        {
                            "type": "state-management",
                            "pattern": "React useReducer hook",
                            "code_snippet": line.strip(),
                            "line_number": i,
                            "context": "React hooks",
                        }
                    )

        return patterns

    def _extract_generic_patterns(
        self, source_code: str, file_path: Path, pattern_types: list[str]
    ) -> list[dict[str, Any]]:
        """Extract patterns from generic source files using simple pattern matching."""
        patterns = []
        lines = source_code.split("\n")

        # Look for common patterns across languages
        keywords = {
            "error": ["try", "catch", "except", "error", "exception"],
            "api": ["api", "endpoint", "route", "request", "response"],
            "state": ["state", "store", "redux", "context"],
        }

        for pattern_type in pattern_types:
            if pattern_type in keywords:
                for i, line in enumerate(lines, start=1):
                    line_lower = line.lower()
                    for keyword in keywords[pattern_type]:
                        if keyword in line_lower:
                            patterns.append(
                                {
                                    "type": pattern_type,
                                    "pattern": f"Contains keyword: {keyword}",
                                    "code_snippet": line.strip()[:100],
                                    "line_number": i,
                                    "context": f"Keyword: {keyword}",
                                }
                            )
                            break  # Only one pattern per line

        return patterns

    def _get_code_snippet(
        self, lines: list[str], start_line: int, num_lines: int = 1
    ) -> str:
        """
        Extract code snippet from source lines.

        Args:
            lines: Source code lines (1-indexed)
            start_line: Starting line number (1-indexed)
            num_lines: Number of lines to include

        Returns:
            Code snippet (max 300 characters)
        """
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), start_idx + num_lines)
        snippet = "\n".join(lines[start_idx:end_idx])
        return snippet[:300]  # Limit to 300 chars like pattern_discovery.py
