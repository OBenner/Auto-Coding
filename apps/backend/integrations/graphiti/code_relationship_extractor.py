#!/usr/bin/env python3
"""
Code Relationship Extractor Module
===================================

Uses AST parsing to extract semantic relationships between code entities.
This module provides deep analysis of code structure for building knowledge graphs.

The code relationship extractor identifies:
- Function call relationships (who calls whom)
- Import dependencies (what modules are used)
- Class inheritance hierarchies (parent-child relationships)
- Component usage patterns (how entities interact)

These relationships are used by:
- Graphiti Memory: To build semantic knowledge graphs of the codebase
- Impact Analyzer: To determine what breaks when code changes
- Dependency Visualizer: To show architectural layers and coupling

Usage:
    from code_relationship_extractor import CodeRelationshipExtractor

    extractor = CodeRelationshipExtractor()
    result = extractor.analyze_file('path/to/file.py')

    print(f"Function calls: {result['calls']}")
    print(f"Imports: {result['imports']}")
    print(f"Inheritance: {result['inheritance']}")
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
class FunctionCall:
    """
    Represents a function call relationship.

    Attributes:
        caller: Name of the calling function/method
        callee: Name of the called function/method
        lineno: Line number where call occurs
        call_type: Type of call (function, method, builtin)
        module: Module the callee belongs to (if imported)
    """

    caller: str
    callee: str
    lineno: int
    call_type: str = "function"
    module: str | None = None


@dataclass
class ImportRelationship:
    """
    Represents an import dependency.

    Attributes:
        module: Module being imported
        names: Specific names imported (empty if whole module)
        alias: Alias used for import (if any)
        lineno: Line number of import statement
        is_from_import: Whether this is 'from X import Y' style
    """

    module: str
    names: list[str] = field(default_factory=list)
    alias: str | None = None
    lineno: int = 0
    is_from_import: bool = False


@dataclass
class InheritanceRelationship:
    """
    Represents a class inheritance relationship.

    Attributes:
        child: Child class name
        parent: Parent class name
        lineno: Line number of class definition
        parent_module: Module the parent belongs to (if imported)
    """

    child: str
    parent: str
    lineno: int
    parent_module: str | None = None


@dataclass
class RelationshipResult:
    """
    Result of relationship extraction.

    Attributes:
        file_path: Path to analyzed file
        calls: List of function call relationships
        imports: List of import dependencies
        inheritance: List of class inheritance relationships
        total_relationships: Total number of relationships found
        entities: Set of all unique entity names (functions, classes)
    """

    file_path: str
    calls: list[FunctionCall] = field(default_factory=list)
    imports: list[ImportRelationship] = field(default_factory=list)
    inheritance: list[InheritanceRelationship] = field(default_factory=list)
    total_relationships: int = 0
    entities: set[str] = field(default_factory=set)


# =============================================================================
# CODE RELATIONSHIP EXTRACTOR
# =============================================================================


class CodeRelationshipExtractor:
    """
    Extracts semantic relationships from Python source code using AST parsing.

    Identifies:
    - Function calls and their context
    - Import dependencies and aliases
    - Class inheritance hierarchies
    - Module-level relationships

    This forms the foundation for building a semantic code graph in Graphiti.
    """

    def __init__(self):
        """Initialize the code relationship extractor."""
        self._current_function = None
        self._current_class = None
        self._import_map: dict[str, str] = {}

    def analyze_file(self, file_path: str | Path) -> dict[str, Any]:
        """
        Analyze a Python source file to extract relationships.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            Dictionary containing relationship data with keys:
            - calls: List of function call relationships
            - imports: List of import dependencies
            - inheritance: List of class inheritance relationships
            - total_relationships: Total count of all relationships
            - entities: Set of all unique entity names
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
        Analyze Python source code string to extract relationships.

        Args:
            source: Python source code as string

        Returns:
            Dictionary containing relationship data
        """
        result = self._analyze_source(source, "<string>")
        return self._result_to_dict(result)

    def _analyze_source(self, source: str, file_path: str) -> RelationshipResult:
        """
        Internal method to analyze source code and extract relationships.

        Args:
            source: Python source code
            file_path: Path for error reporting

        Returns:
            RelationshipResult object
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in {file_path}: {e}")

        # Reset state for new file
        self._current_function = None
        self._current_class = None
        self._import_map = {}

        result = RelationshipResult(file_path=file_path)

        # First pass: Extract imports to build import map
        result.imports = self._extract_imports(tree)
        self._build_import_map(result.imports)

        # Second pass: Extract inheritance relationships
        result.inheritance = self._extract_inheritance(tree)

        # Third pass: Extract function calls
        result.calls = self._extract_calls(tree)

        # Collect all unique entities
        result.entities = self._collect_entities(tree)

        # Calculate total relationships
        result.total_relationships = (
            len(result.calls) + len(result.imports) + len(result.inheritance)
        )

        return result

    def _extract_imports(self, tree: ast.AST) -> list[ImportRelationship]:
        """
        Extract all import statements and their relationships.

        Args:
            tree: AST tree to analyze

        Returns:
            List of ImportRelationship objects
        """
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # Handle: import module [as alias]
                for alias in node.names:
                    imports.append(
                        ImportRelationship(
                            module=alias.name,
                            names=[],
                            alias=alias.asname,
                            lineno=node.lineno,
                            is_from_import=False,
                        )
                    )

            elif isinstance(node, ast.ImportFrom):
                # Handle: from module import name1, name2 [as alias]
                if node.module:
                    # Handle multiple imports from same module
                    for alias in node.names:
                        imports.append(
                            ImportRelationship(
                                module=node.module,
                                names=[alias.name],
                                alias=alias.asname,
                                lineno=node.lineno,
                                is_from_import=True,
                            )
                        )

        return imports

    def _extract_inheritance(self, tree: ast.AST) -> list[InheritanceRelationship]:
        """
        Extract class inheritance relationships.

        Args:
            tree: AST tree to analyze

        Returns:
            List of InheritanceRelationship objects
        """
        inheritance = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Extract base classes
                for base in node.bases:
                    parent_name = None
                    parent_module = None

                    if isinstance(base, ast.Name):
                        parent_name = base.id
                        # Check if this is an imported class
                        parent_module = self._import_map.get(parent_name)

                    elif isinstance(base, ast.Attribute):
                        # Handle module.ClassName style
                        parent_name = ast.unparse(base)
                        if isinstance(base.value, ast.Name):
                            parent_module = base.value.id

                    if parent_name:
                        inheritance.append(
                            InheritanceRelationship(
                                child=node.name,
                                parent=parent_name,
                                lineno=node.lineno,
                                parent_module=parent_module,
                            )
                        )

        return inheritance

    def _extract_calls(self, tree: ast.AST) -> list[FunctionCall]:
        """
        Extract function call relationships using AST visitor pattern.

        Args:
            tree: AST tree to analyze

        Returns:
            List of FunctionCall objects
        """

        # Use custom visitor to track context
        class CallVisitor(ast.NodeVisitor):
            def __init__(self, extractor):
                self.extractor = extractor
                self.calls = []

            def visit_FunctionDef(self, node):
                # Track current function context
                old_function = self.extractor._current_function
                old_class = self.extractor._current_class

                if self.extractor._current_class:
                    # Method call: ClassName.method_name
                    self.extractor._current_function = (
                        f"{self.extractor._current_class}.{node.name}"
                    )
                else:
                    # Standalone function
                    self.extractor._current_function = node.name

                # Visit function body
                self.generic_visit(node)

                # Restore context
                self.extractor._current_function = old_function
                self.extractor._current_class = old_class

            def visit_AsyncFunctionDef(self, node):
                # Handle async functions same as regular functions
                self.visit_FunctionDef(node)

            def visit_ClassDef(self, node):
                # Track current class context
                old_class = self.extractor._current_class
                self.extractor._current_class = node.name

                # Visit class body
                self.generic_visit(node)

                # Restore context
                self.extractor._current_class = old_class

            def visit_Call(self, node):
                # Extract function call information
                callee_name = None
                call_type = "function"
                module = None

                if isinstance(node.func, ast.Name):
                    # Simple function call: func()
                    callee_name = node.func.id
                    module = self.extractor._import_map.get(callee_name)

                elif isinstance(node.func, ast.Attribute):
                    # Method call: obj.method()
                    callee_name = node.func.attr
                    call_type = "method"

                    # Try to determine module
                    if isinstance(node.func.value, ast.Name):
                        module = node.func.value.id

                if callee_name and self.extractor._current_function:
                    self.calls.append(
                        FunctionCall(
                            caller=self.extractor._current_function,
                            callee=callee_name,
                            lineno=node.lineno,
                            call_type=call_type,
                            module=module,
                        )
                    )

                # Continue visiting
                self.generic_visit(node)

        visitor = CallVisitor(self)
        visitor.visit(tree)
        return visitor.calls

    def _build_import_map(self, imports: list[ImportRelationship]) -> None:
        """
        Build a map of imported names to their source modules.

        Args:
            imports: List of import relationships
        """
        for imp in imports:
            if imp.alias:
                # Use alias as the key
                self._import_map[imp.alias] = imp.module
            elif imp.is_from_import and imp.names:
                # Map imported names to their module
                for name in imp.names:
                    self._import_map[name] = imp.module
            else:
                # Direct import
                self._import_map[imp.module] = imp.module

    def _collect_entities(self, tree: ast.AST) -> set[str]:
        """
        Collect all unique entity names (functions, classes, methods).

        Args:
            tree: AST tree to analyze

        Returns:
            Set of unique entity names
        """
        entities = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(
                node, ast.AsyncFunctionDef
            ):
                entities.add(node.name)

            elif isinstance(node, ast.ClassDef):
                entities.add(node.name)
                # Add methods as ClassName.method_name
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) or isinstance(
                        item, ast.AsyncFunctionDef
                    ):
                        entities.add(f"{node.name}.{item.name}")

        return entities

    def _result_to_dict(self, result: RelationshipResult) -> dict[str, Any]:
        """
        Convert RelationshipResult to dictionary.

        Args:
            result: RelationshipResult object to convert

        Returns:
            Dictionary representation of the result
        """
        return {
            "file_path": result.file_path,
            "calls": [
                {
                    "caller": call.caller,
                    "callee": call.callee,
                    "lineno": call.lineno,
                    "call_type": call.call_type,
                    "module": call.module,
                }
                for call in result.calls
            ],
            "imports": [
                {
                    "module": imp.module,
                    "names": imp.names,
                    "alias": imp.alias,
                    "lineno": imp.lineno,
                    "is_from_import": imp.is_from_import,
                }
                for imp in result.imports
            ],
            "inheritance": [
                {
                    "child": inh.child,
                    "parent": inh.parent,
                    "lineno": inh.lineno,
                    "parent_module": inh.parent_module,
                }
                for inh in result.inheritance
            ],
            "total_relationships": result.total_relationships,
            "entities": list(result.entities),
        }
