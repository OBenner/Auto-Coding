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

            # Extract state management patterns
            if "state" in pattern_types:
                patterns.extend(self._extract_python_state_patterns(tree, source_code))

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
                has_logging = False
                has_reraise = False

                for handler in node.handlers:
                    if handler.type:
                        if isinstance(handler.type, ast.Name):
                            exception_types.append(handler.type.id)
                        elif isinstance(handler.type, ast.Tuple):
                            for elt in handler.type.elts:
                                if isinstance(elt, ast.Name):
                                    exception_types.append(elt.id)

                    # Check for logging in handler
                    for stmt in ast.walk(handler):
                        if isinstance(stmt, ast.Call) and isinstance(
                            stmt.func, ast.Attribute
                        ):
                            if isinstance(stmt.func.value, ast.Name):
                                if "log" in stmt.func.value.id.lower():
                                    has_logging = True

                    # Check for re-raising
                    for stmt in handler.body:
                        if isinstance(stmt, ast.Raise) and stmt.exc is None:
                            has_reraise = True

                # Get code snippet
                end_line = node.lineno + 5  # Get a few lines of context
                snippet = self._get_code_snippet(
                    lines, node.lineno, end_line - node.lineno
                )

                pattern_desc = "Try-except"
                if exception_types:
                    pattern_desc += f" catching {', '.join(exception_types)}"
                if has_logging:
                    pattern_desc += " with logging"
                if has_reraise:
                    pattern_desc += " with re-raise"
                if node.orelse:
                    pattern_desc += " with else clause"
                if node.finalbody:
                    pattern_desc += " with finally clause"

                context_parts = [
                    f"Exception types: {', '.join(exception_types) or 'generic'}"
                ]
                if has_logging:
                    context_parts.append("includes logging")
                if has_reraise:
                    context_parts.append("re-raises exception")

                patterns.append(
                    {
                        "type": "error-handling",
                        "pattern": pattern_desc,
                        "code_snippet": snippet,
                        "line_number": node.lineno,
                        "context": ", ".join(context_parts),
                    }
                )

            # Look for custom exception classes
            elif isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and "Exception" in base.id:
                        snippet = self._get_code_snippet(lines, node.lineno, 3)
                        patterns.append(
                            {
                                "type": "error-handling",
                                "pattern": f"Custom exception class: {node.name}",
                                "code_snippet": snippet,
                                "line_number": node.lineno,
                                "context": f"Inherits from {base.id}",
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
                    method_name = node.func.attr
                    obj_name = None

                    # Handle simple calls like client.get()
                    if isinstance(node.func.value, ast.Name):
                        obj_name = node.func.value.id

                    # Handle chained calls like self.client.get()
                    elif isinstance(node.func.value, ast.Attribute):
                        # Get the rightmost object name before the method
                        obj_name = node.func.value.attr

                    # Identify common API patterns
                    api_keywords = [
                        "client",
                        "api",
                        "request",
                        "http",
                        "fetch",
                        "session",
                    ]
                    http_methods = [
                        "get",
                        "post",
                        "put",
                        "delete",
                        "patch",
                        "head",
                        "options",
                    ]

                    if obj_name and any(
                        keyword in obj_name.lower() for keyword in api_keywords
                    ):
                        snippet = self._get_code_snippet(lines, node.lineno, 3)

                        # Identify HTTP method usage
                        if method_name.lower() in http_methods:
                            pattern_type = f"HTTP {method_name.upper()} request"
                        else:
                            pattern_type = f"API call: {obj_name}.{method_name}()"

                        patterns.append(
                            {
                                "type": "api-design",
                                "pattern": pattern_type,
                                "code_snippet": snippet,
                                "line_number": node.lineno,
                                "context": f"Object: {obj_name}, Method: {method_name}",
                            }
                        )

            # Look for API route decorators
            elif isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    decorator_name = None
                    if isinstance(decorator, ast.Name):
                        decorator_name = decorator.id
                    elif isinstance(decorator, ast.Call) and isinstance(
                        decorator.func, ast.Attribute
                    ):
                        # Decorators like @app.route(), @api.get()
                        if isinstance(decorator.func.value, ast.Name):
                            obj = decorator.func.value.id
                            method = decorator.func.attr
                            decorator_name = f"{obj}.{method}"

                    if decorator_name and any(
                        kw in decorator_name.lower()
                        for kw in ["route", "api", "endpoint"]
                    ):
                        snippet = self._get_code_snippet(lines, node.lineno, 3)
                        patterns.append(
                            {
                                "type": "api-design",
                                "pattern": f"API endpoint with @{decorator_name}",
                                "code_snippet": snippet,
                                "line_number": node.lineno,
                                "context": f"Function: {node.name}, Decorator: {decorator_name}",
                            }
                        )

        return patterns

    def _extract_python_state_patterns(
        self, tree: ast.AST, source_code: str
    ) -> list[dict[str, Any]]:
        """Extract state management patterns from Python AST."""
        patterns = []
        lines = source_code.split("\n")

        for node in ast.walk(tree):
            # Look for @property decorators (state getters)
            if isinstance(node, ast.FunctionDef):
                has_property = False
                has_setter = False

                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        if decorator.id == "property":
                            has_property = True
                        elif decorator.id.endswith(".setter"):
                            has_setter = True
                    elif isinstance(decorator, ast.Attribute):
                        if decorator.attr == "setter":
                            has_setter = True

                if has_property or has_setter:
                    snippet = self._get_code_snippet(lines, node.lineno, 3)
                    pattern_type = (
                        "Property getter" if has_property else "Property setter"
                    )
                    patterns.append(
                        {
                            "type": "state-management",
                            "pattern": f"{pattern_type}: @property {node.name}",
                            "code_snippet": snippet,
                            "line_number": node.lineno,
                            "context": f"Property: {node.name}",
                        }
                    )

            # Look for @dataclass decorator (state containers)
            elif isinstance(node, ast.ClassDef):
                has_dataclass = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                        has_dataclass = True
                    elif isinstance(decorator, ast.Call):
                        if (
                            isinstance(decorator.func, ast.Name)
                            and decorator.func.id == "dataclass"
                        ):
                            has_dataclass = True

                if has_dataclass:
                    snippet = self._get_code_snippet(lines, node.lineno, 5)
                    patterns.append(
                        {
                            "type": "state-management",
                            "pattern": f"Dataclass for state: {node.name}",
                            "code_snippet": snippet,
                            "line_number": node.lineno,
                            "context": f"Dataclass: {node.name}",
                        }
                    )

                # Look for __init__ with state attributes
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        # Count self.attribute assignments
                        state_attrs = []
                        for stmt in ast.walk(item):
                            if isinstance(stmt, ast.Assign):
                                for target in stmt.targets:
                                    if isinstance(target, ast.Attribute):
                                        if (
                                            isinstance(target.value, ast.Name)
                                            and target.value.id == "self"
                                        ):
                                            state_attrs.append(target.attr)

                        if state_attrs:
                            snippet = self._get_code_snippet(lines, item.lineno, 5)
                            patterns.append(
                                {
                                    "type": "state-management",
                                    "pattern": f"State initialization in __init__: {len(state_attrs)} attributes",
                                    "code_snippet": snippet,
                                    "line_number": item.lineno,
                                    "context": f"Class: {node.name}, Attributes: {', '.join(state_attrs[:3])}{'...' if len(state_attrs) > 3 else ''}",
                                }
                            )

            # Look for global state variables
            elif isinstance(node, ast.Assign):
                # Check if this is a module-level assignment (global state)
                # This is approximate - we'd need more context to be certain
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Check if the variable name suggests state (all caps, or specific naming)
                        var_name = target.id
                        if var_name.isupper() or any(
                            kw in var_name.lower()
                            for kw in ["state", "cache", "store", "config"]
                        ):
                            snippet = self._get_code_snippet(lines, node.lineno, 1)
                            patterns.append(
                                {
                                    "type": "state-management",
                                    "pattern": f"Global state variable: {var_name}",
                                    "code_snippet": snippet,
                                    "line_number": node.lineno,
                                    "context": f"Variable: {var_name}",
                                }
                            )

            # Look for context managers (state management via 'with' statement)
            elif isinstance(node, ast.With):
                for item in node.items:
                    if item.optional_vars:
                        snippet = self._get_code_snippet(lines, node.lineno, 3)
                        patterns.append(
                            {
                                "type": "state-management",
                                "pattern": "Context manager for state",
                                "code_snippet": snippet,
                                "line_number": node.lineno,
                                "context": "Using 'with' statement for state management",
                            }
                        )
                        break

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
            if isinstance(node, ast.FunctionDef) or isinstance(
                node, ast.AsyncFunctionDef
            ):
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


def extract_patterns(
    file_path: Path | str,
    project_dir: Path | str | None = None,
    pattern_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Standalone function to extract code patterns from a file.

    Args:
        file_path: Path to source file to analyze
        project_dir: Project root directory (defaults to current directory)
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

    Example:
        >>> patterns = extract_patterns("myfile.py", pattern_types=["api", "error"])
        >>> for p in patterns:
        ...     print(f"{p['type']}: {p['pattern']}")
    """
    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir)

    file_path = Path(file_path)

    extractor = PatternExtractor(project_dir)
    return extractor.extract_patterns(file_path, pattern_types)
