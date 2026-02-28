#!/usr/bin/env python3
"""
Code Analyzer Module
====================

Uses AST parsing to extract testable functions, classes, and methods from Python source files.
This module provides analysis of code structure for automated test generation.

The code analyzer results are used by:
- Test Generator: To identify functions/classes that need tests
- QA Agent: To determine what code needs test coverage
- Planner: To understand code complexity for test planning

Usage:
    from code_analyzer import CodeAnalyzer

    analyzer = CodeAnalyzer()
    result = analyzer.analyze_file('path/to/file.py')

    print(f"Functions: {result['functions']}")
    print(f"Classes: {result['classes']}")
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
class FunctionInfo:
    """
    Represents an extracted function or method.

    Attributes:
        name: Function name
        lineno: Line number in source file
        args: List of argument names
        returns: Return type annotation if available
        docstring: Function docstring if available
        is_async: Whether function is async
        decorators: List of decorator names
        complexity: Cyclomatic complexity estimate
    """

    name: str
    lineno: int
    args: list[str] = field(default_factory=list)
    returns: str | None = None
    docstring: str | None = None
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)
    complexity: int = 1


@dataclass
class ClassInfo:
    """
    Represents an extracted class.

    Attributes:
        name: Class name
        lineno: Line number in source file
        bases: List of base class names
        methods: List of method information
        docstring: Class docstring if available
        decorators: List of decorator names
    """

    name: str
    lineno: int
    bases: list[str] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)
    docstring: str | None = None
    decorators: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """
    Result of code analysis.

    Attributes:
        file_path: Path to analyzed file
        functions: List of standalone functions
        classes: List of classes with their methods
        imports: List of import statements
        has_main: Whether file has if __name__ == '__main__'
        total_lines: Total lines in file
        edge_cases: List of detected edge case patterns
        naming_conventions: Detected naming conventions (variable, function, class styles)
        error_patterns: Detected error handling patterns (exception types, logging, etc.)
    """

    file_path: str
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    has_main: bool = False
    total_lines: int = 0
    edge_cases: list[dict[str, Any]] = field(default_factory=list)
    naming_conventions: dict[str, Any] = field(default_factory=dict)
    error_patterns: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# CODE ANALYZER
# =============================================================================


class CodeAnalyzer:
    """
    Analyzes Python source code using AST parsing.

    Extracts:
    - Standalone functions with signatures and docstrings
    - Classes with methods
    - Type hints and return types
    - Complexity metrics
    """

    def __init__(self):
        """Initialize the code analyzer."""
        pass

    def analyze_file(self, file_path: str | Path) -> dict[str, Any]:
        """
        Analyze a Python source file.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            Dictionary containing analysis results with keys:
            - functions: List of FunctionInfo objects
            - classes: List of ClassInfo objects
            - imports: List of import statements
            - has_main: Whether file has main block
            - total_lines: Total lines in file
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
        Analyze Python source code string.

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

        result = AnalysisResult(
            file_path=file_path, total_lines=len(source.splitlines())
        )

        # Extract imports
        result.imports = self._extract_imports(tree)

        # Check for __main__ block
        result.has_main = self._has_main_block(tree)

        # Extract functions and classes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(
                node, ast.AsyncFunctionDef
            ):
                # Only add top-level functions (not methods)
                if self._is_top_level(node, tree):
                    func_info = self._extract_function(node)
                    result.functions.append(func_info)

            elif isinstance(node, ast.ClassDef):
                class_info = self._extract_class(node)
                result.classes.append(class_info)

        # Detect edge cases for test generation
        result.edge_cases = self._detect_edge_cases(tree)

        # Detect naming conventions in this file
        result.naming_conventions = self._detect_naming_conventions(result)

        # Detect error handling patterns in this file
        result.error_patterns = self._detect_error_patterns(tree)

        return result

    def _extract_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> FunctionInfo:
        """Extract information from a function definition."""
        # Extract argument names
        args = [arg.arg for arg in node.args.args]

        # Extract return type annotation
        returns = None
        if node.returns:
            returns = ast.unparse(node.returns)

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Extract decorators
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)

        # Estimate complexity (count branches)
        complexity = self._estimate_complexity(node)

        return FunctionInfo(
            name=node.name,
            lineno=node.lineno,
            args=args,
            returns=returns,
            docstring=docstring,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            decorators=decorators,
            complexity=complexity,
        )

    def _extract_class(self, node: ast.ClassDef) -> ClassInfo:
        """Extract information from a class definition."""
        # Extract base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(ast.unparse(base))

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Extract decorators
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                decorators.append(dec.func.id)

        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef) or isinstance(
                item, ast.AsyncFunctionDef
            ):
                method_info = self._extract_function(item)
                methods.append(method_info)

        return ClassInfo(
            name=node.name,
            lineno=node.lineno,
            bases=bases,
            methods=methods,
            docstring=docstring,
            decorators=decorators,
        )

    def _extract_imports(self, tree: ast.AST) -> list[str]:
        """Extract import statements."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        return imports

    def _has_main_block(self, tree: ast.AST) -> bool:
        """Check if file has if __name__ == '__main__' block."""
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if condition is __name__ == '__main__'
                if isinstance(node.test, ast.Compare):
                    if (
                        isinstance(node.test.left, ast.Name)
                        and node.test.left.id == "__name__"
                    ):
                        return True
        return False

    def _is_top_level(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, tree: ast.AST
    ) -> bool:
        """Check if a function is at module level (not a method)."""
        # Check if parent is Module (not ClassDef)
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for item in parent.body:
                    if item is node:
                        return False
        return True

    def _estimate_complexity(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Estimate cyclomatic complexity by counting decision points."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Count decision points
            if isinstance(child, ast.If | ast.While | ast.For | ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Count and/or operators
                complexity += len(child.values) - 1

        return complexity

    def _detect_edge_cases(self, tree: ast.AST) -> list[dict[str, Any]]:
        """
        Detect edge case patterns for test scenario generation.

        Identifies:
        - Error handling (try/except blocks)
        - Boundary conditions (comparisons with limits, None checks)
        - Empty checks (len checks, truthiness checks)
        - Type validation (isinstance checks)
        - Explicit error raising (raise statements)
        - Assertions

        Returns:
            List of edge case dictionaries with type, description, and location
        """
        edge_cases = []

        for node in ast.walk(tree):
            # Detect try/except blocks (error handling)
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    exc_type = "Exception"
                    if handler.type:
                        if isinstance(handler.type, ast.Name):
                            exc_type = handler.type.id
                        elif isinstance(handler.type, ast.Attribute):
                            exc_type = ast.unparse(handler.type)

                    edge_cases.append(
                        {
                            "type": "error_handling",
                            "pattern": f"try/except {exc_type}",
                            "lineno": node.lineno,
                            "description": f"Handles {exc_type} exceptions",
                        }
                    )

            # Detect boundary checks and None checks
            elif isinstance(node, ast.Compare):
                code = ast.unparse(node)

                # Check for None comparisons
                if "None" in code:
                    edge_cases.append(
                        {
                            "type": "boundary_condition",
                            "pattern": "none_check",
                            "lineno": node.lineno,
                            "description": f"None check: {code}",
                        }
                    )

                # Check for numeric boundary conditions
                elif any(op in code for op in ["< 0", "> 0", "== 0", "<= 0", ">= 0"]):
                    edge_cases.append(
                        {
                            "type": "boundary_condition",
                            "pattern": "numeric_boundary",
                            "lineno": node.lineno,
                            "description": f"Numeric boundary: {code}",
                        }
                    )

                # Check for empty/length checks
                elif "len(" in code and any(
                    op in code for op in ["== 0", "> 0", "< 1"]
                ):
                    edge_cases.append(
                        {
                            "type": "boundary_condition",
                            "pattern": "empty_check",
                            "lineno": node.lineno,
                            "description": f"Empty check: {code}",
                        }
                    )

            # Detect isinstance type checks
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                    if len(node.args) >= 2:
                        type_check = (
                            ast.unparse(node.args[1])
                            if len(node.args) > 1
                            else "unknown"
                        )
                        edge_cases.append(
                            {
                                "type": "type_validation",
                                "pattern": "isinstance_check",
                                "lineno": node.lineno,
                                "description": f"Type check: isinstance(..., {type_check})",
                            }
                        )

            # Detect raise statements (explicit errors)
            elif isinstance(node, ast.Raise):
                exc_type = "Exception"
                if node.exc:
                    if isinstance(node.exc, ast.Call) and isinstance(
                        node.exc.func, ast.Name
                    ):
                        exc_type = node.exc.func.id
                    elif isinstance(node.exc, ast.Name):
                        exc_type = node.exc.id

                edge_cases.append(
                    {
                        "type": "error_raising",
                        "pattern": f"raise {exc_type}",
                        "lineno": node.lineno,
                        "description": f"Raises {exc_type}",
                    }
                )

            # Detect assertions
            elif isinstance(node, ast.Assert):
                test_code = ast.unparse(node.test)
                edge_cases.append(
                    {
                        "type": "assertion",
                        "pattern": "assert",
                        "lineno": node.lineno,
                        "description": f"Assertion: {test_code}",
                    }
                )

        return edge_cases

    def _detect_naming_conventions(self, result: AnalysisResult) -> dict[str, Any]:
        """
        Detect naming conventions used in the analyzed file.

        Analyzes function, class, and variable names to determine the
        predominant naming style (snake_case, camelCase, PascalCase, etc.).

        Args:
            result: AnalysisResult containing extracted functions and classes

        Returns:
            Dictionary with detected naming conventions:
            - function_style: Detected function naming style
            - class_style: Detected class naming style
            - variable_style: Detected variable naming style
            - constant_style: Detected constant naming style
            - private_prefix: How private members are indicated
            - examples: Sample identifiers
        """
        conventions = {
            "function_style": None,
            "class_style": None,
            "variable_style": None,
            "constant_style": None,
            "private_prefix": "_",  # Python convention
            "examples": {},
        }

        # Collect function names
        function_names = [
            f.name for f in result.functions if not f.name.startswith("_")
        ]
        if function_names:
            conventions["function_style"] = self._detect_case_style(function_names)
            conventions["examples"]["functions"] = function_names[:5]

        # Collect class names
        class_names = [c.name for c in result.classes if not c.name.startswith("_")]
        if class_names:
            conventions["class_style"] = self._detect_case_style(class_names)
            conventions["examples"]["classes"] = class_names[:5]

        # Analyze variable naming from imports and assignments
        # This is a simplified approach - full AST traversal would be more complete
        if result.functions or result.classes:
            # Default to Python PEP 8 conventions if we have code
            if not conventions["function_style"]:
                conventions["function_style"] = "snake_case"
            if not conventions["class_style"]:
                conventions["class_style"] = "PascalCase"
            conventions["variable_style"] = "snake_case"
            conventions["constant_style"] = "UPPER_SNAKE_CASE"

        return conventions

    def _detect_case_style(self, identifiers: list[str]) -> str | None:
        """
        Detect the predominant case style from a list of identifiers.

        Delegates to NamingDetector.detect_case_style for consistency.
        Strips leading underscores before analysis to handle private members.

        Args:
            identifiers: List of identifier names to analyze

        Returns:
            One of: snake_case, camelCase, PascalCase, UPPER_SNAKE_CASE, or None
        """
        from analysis.analyzers.naming_detector import NamingDetector

        # Strip leading underscores (private member convention)
        stripped = [name.lstrip("_") for name in identifiers if name]
        stripped = [name for name in stripped if name]
        return NamingDetector.detect_case_style(stripped)

    def _detect_error_patterns(self, tree: ast.AST) -> dict[str, Any]:
        """
        Detect error handling patterns in the analyzed file.

        Analyzes try/except blocks, exception types, logging patterns,
        and error propagation strategies.

        Args:
            tree: AST tree of the source code

        Returns:
            Dictionary with detected error patterns:
            - exception_types: List of exception types caught/raised
            - custom_exceptions: Custom exception classes defined
            - has_logging: Whether error logging is used
            - error_strategy: Whether errors are handled or propagated
        """
        patterns = {
            "exception_types": [],
            "custom_exceptions": [],
            "has_logging": False,
            "error_strategy": "unknown",
            "try_except_count": 0,
            "raise_count": 0,
        }

        try_blocks = 0
        re_raises = 0
        handles = 0

        for node in ast.walk(tree):
            # Detect custom exception classes
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = ast.unparse(base)

                    if "Exception" in base_name or "Error" in base_name:
                        patterns["custom_exceptions"].append(node.name)

            # Analyze try/except blocks
            elif isinstance(node, ast.Try):
                try_blocks += 1
                for handler in node.handlers:
                    # Extract exception type
                    if handler.type:
                        exc_type = None
                        if isinstance(handler.type, ast.Name):
                            exc_type = handler.type.id
                        elif isinstance(handler.type, ast.Attribute):
                            exc_type = ast.unparse(handler.type)

                        if exc_type and exc_type not in patterns["exception_types"]:
                            patterns["exception_types"].append(exc_type)

                    # Check for logging in handler
                    for child in ast.walk(handler):
                        if isinstance(child, ast.Call) and isinstance(
                            child.func, ast.Attribute
                        ):
                            attr = child.func.attr
                            if attr in ["error", "exception", "warning", "critical"]:
                                patterns["has_logging"] = True

                    # Check if exception is re-raised
                    has_reraise = any(
                        isinstance(n, ast.Raise) and n.exc is None
                        for n in ast.walk(handler)
                    )
                    if has_reraise:
                        re_raises += 1
                    else:
                        handles += 1

            # Count raise statements
            elif isinstance(node, ast.Raise):
                patterns["raise_count"] += 1
                # Extract raised exception type
                if node.exc:
                    exc_type = None
                    if isinstance(node.exc, ast.Call):
                        if isinstance(node.exc.func, ast.Name):
                            exc_type = node.exc.func.id
                        elif isinstance(node.exc.func, ast.Attribute):
                            exc_type = ast.unparse(node.exc.func)

                    if exc_type and exc_type not in patterns["exception_types"]:
                        patterns["exception_types"].append(exc_type)

        patterns["try_except_count"] = try_blocks

        # Determine error strategy
        if try_blocks > 0:
            if re_raises > handles:
                patterns["error_strategy"] = "propagate"
            elif handles > 0:
                patterns["error_strategy"] = "handle"
            else:
                patterns["error_strategy"] = "mixed"
        elif patterns["raise_count"] > 0:
            patterns["error_strategy"] = "raise_only"

        return patterns

    def _result_to_dict(self, result: AnalysisResult) -> dict[str, Any]:
        """Convert AnalysisResult to dictionary."""
        return {
            "file_path": result.file_path,
            "functions": [
                {
                    "name": f.name,
                    "lineno": f.lineno,
                    "args": f.args,
                    "returns": f.returns,
                    "docstring": f.docstring,
                    "is_async": f.is_async,
                    "decorators": f.decorators,
                    "complexity": f.complexity,
                }
                for f in result.functions
            ],
            "classes": [
                {
                    "name": c.name,
                    "lineno": c.lineno,
                    "bases": c.bases,
                    "docstring": c.docstring,
                    "decorators": c.decorators,
                    "methods": [
                        {
                            "name": m.name,
                            "lineno": m.lineno,
                            "args": m.args,
                            "returns": m.returns,
                            "docstring": m.docstring,
                            "is_async": m.is_async,
                            "decorators": m.decorators,
                            "complexity": m.complexity,
                        }
                        for m in c.methods
                    ],
                }
                for c in result.classes
            ],
            "imports": result.imports,
            "has_main": result.has_main,
            "total_lines": result.total_lines,
            "edge_cases": result.edge_cases,
            "naming_conventions": result.naming_conventions,
            "error_patterns": result.error_patterns,
        }
