"""
Dependency Analyzer Module
===========================

Analyzes import graphs and file dependencies in Python projects.
This module provides dependency analysis for intelligent file prioritization.

The dependency analyzer results are used by:
- File Prioritizer: To boost priority of files with many dependents
- Context Builder: To include related files based on import relationships
- QA Agent: To identify affected files when changes are made

Usage:
    from dependency_analyzer import DependencyAnalyzer

    analyzer = DependencyAnalyzer(project_dir='.')
    graph = analyzer.build_dependency_graph()
    dependents = analyzer.get_dependents('apps/backend/core/client.py')
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
class ImportInfo:
    """
    Represents an import statement in a file.

    Attributes:
        module: The module being imported (e.g., 'os', 'pathlib')
        names: List of names imported (e.g., ['Path'] for 'from pathlib import Path')
        alias: Alias if used (e.g., 'pd' for 'import pandas as pd')
        lineno: Line number in source file
        is_relative: Whether this is a relative import (e.g., 'from . import foo')
        level: Level of relative import (1 for '.', 2 for '..', etc.)
    """

    module: str
    names: list[str] = field(default_factory=list)
    alias: str | None = None
    lineno: int = 0
    is_relative: bool = False
    level: int = 0


@dataclass
class DependencyNode:
    """
    Represents a file in the dependency graph.

    Attributes:
        file_path: Relative path to the file
        imports: List of ImportInfo objects for this file
        dependencies: Set of file paths this file depends on
        dependents: Set of file paths that depend on this file
        is_external: Whether this is an external dependency (not in project)
    """

    file_path: str
    imports: list[ImportInfo] = field(default_factory=list)
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)
    is_external: bool = False


@dataclass
class DependencyGraph:
    """
    Complete dependency graph for a project.

    Attributes:
        nodes: Dictionary mapping file paths to DependencyNode objects
        external_modules: Set of external module names used in the project
        entry_points: Files with no dependents (potential entry points)
        leaf_nodes: Files with no dependencies (pure utilities)
    """

    nodes: dict[str, DependencyNode] = field(default_factory=dict)
    external_modules: set[str] = field(default_factory=set)
    entry_points: set[str] = field(default_factory=set)
    leaf_nodes: set[str] = field(default_factory=set)


# =============================================================================
# DEPENDENCY ANALYZER
# =============================================================================


class DependencyAnalyzer:
    """
    Analyzes Python import dependencies using AST parsing.

    Extracts:
    - Import statements (import and from...import)
    - Relative imports and their resolution
    - Dependency relationships between files
    - External vs internal dependencies
    """

    def __init__(self, project_dir: str | Path | None = None):
        """
        Initialize the dependency analyzer.

        Args:
            project_dir: Path to project root directory (None for cwd)
        """
        self.project_dir = Path(project_dir or ".").resolve()
        self._module_cache: dict[str, str] = {}

    def analyze_file(self, file_path: str | Path) -> dict[str, Any]:
        """
        Analyze imports in a single Python file.

        Args:
            file_path: Path to Python file to analyze

        Returns:
            Dictionary containing:
            - file_path: Relative path to file
            - imports: List of ImportInfo dictionaries
            - dependencies: List of resolved file paths
            - external_modules: List of external module names
        """
        path = Path(file_path)
        if not path.is_absolute():
            path = self.project_dir / path

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"Unable to read file as UTF-8: {file_path}")

        imports = self._extract_imports(source, str(path))
        dependencies = []
        external_modules = []

        # Resolve imports to file paths
        relative_path = str(path.relative_to(self.project_dir))
        for import_info in imports:
            resolved = self._resolve_import(import_info, relative_path)
            if resolved:
                if resolved.startswith("external:"):
                    external_modules.append(resolved.replace("external:", ""))
                else:
                    dependencies.append(resolved)

        return {
            "file_path": relative_path,
            "imports": [self._import_info_to_dict(imp) for imp in imports],
            "dependencies": dependencies,
            "external_modules": external_modules,
        }

    def build_dependency_graph(
        self, file_paths: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Build a complete dependency graph for multiple files.

        Args:
            file_paths: List of files to analyze (None to scan project)

        Returns:
            Dictionary containing:
            - nodes: Dictionary mapping file paths to node info
            - external_modules: List of all external modules used
            - entry_points: Files with no dependents
            - leaf_nodes: Files with no dependencies
        """
        if file_paths is None:
            # Scan project for Python files
            file_paths = self._discover_python_files()

        graph = DependencyGraph()

        # First pass: analyze all files
        for file_path in file_paths:
            try:
                analysis = self.analyze_file(file_path)
                node = DependencyNode(
                    file_path=analysis["file_path"],
                    imports=[
                        self._dict_to_import_info(imp) for imp in analysis["imports"]
                    ],
                    dependencies=set(analysis["dependencies"]),
                )
                graph.nodes[analysis["file_path"]] = node
                graph.external_modules.update(analysis["external_modules"])
            except (FileNotFoundError, ValueError, SyntaxError):
                # Skip files we can't analyze
                continue

        # Second pass: build reverse dependencies
        for file_path, node in graph.nodes.items():
            for dep in node.dependencies:
                if dep in graph.nodes:
                    graph.nodes[dep].dependents.add(file_path)

        # Identify entry points and leaf nodes
        for file_path, node in graph.nodes.items():
            if not node.dependents:
                graph.entry_points.add(file_path)
            if not node.dependencies:
                graph.leaf_nodes.add(file_path)

        return self._graph_to_dict(graph)

    def get_dependents(self, file_path: str) -> list[str]:
        """
        Get all files that depend on the given file.

        Args:
            file_path: Path to file to check

        Returns:
            List of file paths that import/depend on this file
        """
        graph = self.build_dependency_graph()
        nodes = {
            path: self._dict_to_node(data) for path, data in graph["nodes"].items()
        }

        if file_path not in nodes:
            return []

        return list(nodes[file_path].dependents)

    def get_dependencies(self, file_path: str) -> list[str]:
        """
        Get all files that the given file depends on.

        Args:
            file_path: Path to file to check

        Returns:
            List of file paths that this file imports
        """
        try:
            analysis = self.analyze_file(file_path)
            return analysis["dependencies"]
        except (FileNotFoundError, ValueError):
            return []

    def calculate_impact_score(self, file_path: str) -> float:
        """
        Calculate the impact score for a file based on dependents.

        Files with many dependents have higher impact scores.
        This is useful for prioritization.

        Args:
            file_path: Path to file to score

        Returns:
            Impact score (0-10 scale)
        """
        dependents = self.get_dependents(file_path)
        count = len(dependents)

        # Logarithmic scaling: many dependents = high impact
        if count == 0:
            return 0.0
        elif count == 1:
            return 3.0
        elif count <= 3:
            return 5.0
        elif count <= 10:
            return 7.0
        elif count <= 30:
            return 9.0
        else:
            return 10.0

    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================

    def _extract_imports(self, source: str, file_path: str) -> list[ImportInfo]:
        """
        Extract import statements from source code.

        Args:
            source: Python source code
            file_path: Path for error reporting

        Returns:
            List of ImportInfo objects
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # import foo, bar as baz
                for alias in node.names:
                    imports.append(
                        ImportInfo(
                            module=alias.name,
                            alias=alias.asname,
                            lineno=node.lineno,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                # from foo import bar, baz
                module = node.module or ""
                names = [alias.name for alias in node.names] if node.names else []
                imports.append(
                    ImportInfo(
                        module=module,
                        names=names,
                        lineno=node.lineno,
                        is_relative=node.level > 0,
                        level=node.level,
                    )
                )

        return imports

    def _resolve_import(
        self, import_info: ImportInfo, current_file: str
    ) -> str | None:
        """
        Resolve an import to a file path.

        Args:
            import_info: Import information
            current_file: Path to file containing the import

        Returns:
            Resolved file path or None if external/unresolvable
        """
        # Handle relative imports
        if import_info.is_relative:
            return self._resolve_relative_import(import_info, current_file)

        # Check if it's a project module
        module_parts = import_info.module.split(".")

        # Try to resolve as project file
        for i in range(len(module_parts), 0, -1):
            module_path = Path(*module_parts[:i])

            # Try as package
            candidate = self.project_dir / module_path / "__init__.py"
            if candidate.exists():
                rel_path = str(candidate.relative_to(self.project_dir))
                return rel_path

            # Try as module file
            candidate = self.project_dir / f"{module_path}.py"
            if candidate.exists():
                rel_path = str(candidate.relative_to(self.project_dir))
                return rel_path

        # External module
        return f"external:{import_info.module}"

    def _resolve_relative_import(
        self, import_info: ImportInfo, current_file: str
    ) -> str | None:
        """
        Resolve a relative import to a file path.

        Args:
            import_info: Import information with is_relative=True
            current_file: Path to file containing the import

        Returns:
            Resolved file path or None
        """
        current_path = Path(current_file)
        parent = current_path.parent

        # Go up 'level' directories
        for _ in range(import_info.level - 1):
            parent = parent.parent

        # Resolve module name
        if import_info.module:
            module_parts = import_info.module.split(".")
            target = parent / Path(*module_parts)
        else:
            target = parent

        # Try as package
        candidate = self.project_dir / target / "__init__.py"
        if candidate.exists():
            return str(candidate.relative_to(self.project_dir))

        # Try as module file
        candidate = self.project_dir / f"{target}.py"
        if candidate.exists():
            return str(candidate.relative_to(self.project_dir))

        return None

    def _discover_python_files(self) -> list[str]:
        """
        Discover all Python files in the project.

        Returns:
            List of relative file paths
        """
        python_files = []
        for path in self.project_dir.rglob("*.py"):
            # Skip virtual environments and hidden directories
            if any(
                part.startswith(".")
                or part in ["venv", "env", ".venv", "__pycache__", "node_modules"]
                for part in path.parts
            ):
                continue

            try:
                rel_path = str(path.relative_to(self.project_dir))
                python_files.append(rel_path)
            except ValueError:
                continue

        return python_files

    def _import_info_to_dict(self, import_info: ImportInfo) -> dict[str, Any]:
        """Convert ImportInfo to dictionary."""
        return {
            "module": import_info.module,
            "names": import_info.names,
            "alias": import_info.alias,
            "lineno": import_info.lineno,
            "is_relative": import_info.is_relative,
            "level": import_info.level,
        }

    def _dict_to_import_info(self, data: dict[str, Any]) -> ImportInfo:
        """Convert dictionary to ImportInfo."""
        return ImportInfo(
            module=data["module"],
            names=data.get("names", []),
            alias=data.get("alias"),
            lineno=data.get("lineno", 0),
            is_relative=data.get("is_relative", False),
            level=data.get("level", 0),
        )

    def _graph_to_dict(self, graph: DependencyGraph) -> dict[str, Any]:
        """Convert DependencyGraph to dictionary."""
        return {
            "nodes": {
                path: {
                    "file_path": node.file_path,
                    "imports": [self._import_info_to_dict(imp) for imp in node.imports],
                    "dependencies": list(node.dependencies),
                    "dependents": list(node.dependents),
                    "is_external": node.is_external,
                }
                for path, node in graph.nodes.items()
            },
            "external_modules": list(graph.external_modules),
            "entry_points": list(graph.entry_points),
            "leaf_nodes": list(graph.leaf_nodes),
        }

    def _dict_to_node(self, data: dict[str, Any]) -> DependencyNode:
        """Convert dictionary to DependencyNode."""
        return DependencyNode(
            file_path=data["file_path"],
            imports=[self._dict_to_import_info(imp) for imp in data.get("imports", [])],
            dependencies=set(data.get("dependencies", [])),
            dependents=set(data.get("dependents", [])),
            is_external=data.get("is_external", False),
        )
