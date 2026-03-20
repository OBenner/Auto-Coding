"""
Multi-Repo Dependency Graph
============================

Provides cross-repository dependency analysis and graph visualization for
multi-codebase orchestration. Builds on the single-project DependencyAnalyzer
to track, visualize, and reason about dependencies that span multiple repos.

The MultiRepoDependencyGraph is used by:
- Multi-repo CLI: To show dependency relationships across projects
- Orchestrator: To compute build/test order when changes propagate
- QA Agent: To identify affected repos when shared libraries change

Usage:
    from analysis.dependency_graph import MultiRepoDependencyGraph

    graph = MultiRepoDependencyGraph()
    graph.add_repo("frontend", "/path/to/frontend")
    graph.add_repo("backend", "/path/to/backend")
    graph.add_repo("shared", "/path/to/shared")

    graph.analyze()

    # Get repos affected when 'shared' changes
    affected = graph.get_affected_repos("shared")

    # Get build order (dependencies first)
    order = graph.get_build_order()

    # Export as dict for visualization
    data = graph.to_dict()
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# =============================================================================
# ENUMS
# =============================================================================


class EdgeType(str, Enum):
    """Type of dependency edge between repos."""

    IMPORTS = "imports"  # Direct import relationship
    DECLARES = "declares"  # Package declares another as dependency
    REFERENCES = "references"  # Loose reference (config, env, etc.)
    UNKNOWN = "unknown"  # Unclassified dependency


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class RepoNode:
    """
    Represents a single repository in the multi-repo dependency graph.

    Attributes:
        name: Unique identifier for this repo
        path: Absolute path to the repo root directory
        dependencies: Names of repos this repo depends on
        dependents: Names of repos that depend on this repo
        file_count: Number of analyzable files discovered
        external_modules: External package names used by this repo
        metadata: Arbitrary extra info (language, tags, etc.)
    """

    name: str
    path: str
    dependencies: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)
    file_count: int = 0
    external_modules: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "path": self.path,
            "dependencies": sorted(self.dependencies),
            "dependents": sorted(self.dependents),
            "file_count": self.file_count,
            "external_modules": sorted(self.external_modules),
            "metadata": self.metadata,
        }


@dataclass
class DependencyEdge:
    """
    Represents a directed dependency edge between two repos.

    Attributes:
        source: Name of the dependent repo (the one that imports)
        target: Name of the dependency repo (the one being imported)
        edge_type: Nature of the dependency relationship
        weight: Strength of the dependency (e.g. number of cross-imports)
        details: Additional metadata about the edge
    """

    source: str
    target: str
    edge_type: EdgeType = EdgeType.IMPORTS
    weight: int = 1
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "details": self.details,
        }


# =============================================================================
# MULTI-REPO DEPENDENCY GRAPH
# =============================================================================


class MultiRepoDependencyGraph:
    """
    Builds and queries a dependency graph spanning multiple repositories.

    Analyzes cross-repo import relationships (Python), declared package
    dependencies (requirements.txt / package.json), and produces a directed
    acyclic graph suitable for build-order computation and impact analysis.

    Attributes:
        nodes: Mapping of repo name → RepoNode
        edges: List of directed DependencyEdge objects
        analyzed: Whether analyze() has been called
    """

    def __init__(self) -> None:
        """Initialize an empty multi-repo dependency graph."""
        self.nodes: dict[str, RepoNode] = {}
        self.edges: list[DependencyEdge] = []
        self.analyzed: bool = False

    # -------------------------------------------------------------------------
    # PUBLIC API – BUILDING THE GRAPH
    # -------------------------------------------------------------------------

    def add_repo(
        self,
        name: str,
        path: str | Path,
        metadata: dict[str, Any] | None = None,
    ) -> RepoNode:
        """
        Register a repository with the graph.

        Args:
            name: Unique name for the repo
            path: Path to the repo root directory
            metadata: Optional extra information (language, tags, etc.)

        Returns:
            The created RepoNode

        Raises:
            ValueError: If a repo with this name is already registered
        """
        if name in self.nodes:
            raise ValueError(f"Repo '{name}' is already registered in the graph")

        resolved = str(Path(path).resolve())
        node = RepoNode(name=name, path=resolved, metadata=metadata or {})
        self.nodes[name] = node
        self.analyzed = False
        return node

    def remove_repo(self, name: str) -> bool:
        """
        Remove a repository and all its edges from the graph.

        Args:
            name: Name of the repo to remove

        Returns:
            True if removed, False if not found
        """
        if name not in self.nodes:
            return False

        del self.nodes[name]
        self.edges = [
            e for e in self.edges if e.source != name and e.target != name
        ]

        # Clean up references in remaining nodes
        for node in self.nodes.values():
            node.dependencies.discard(name)
            node.dependents.discard(name)

        self.analyzed = False
        return True

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: EdgeType = EdgeType.IMPORTS,
        weight: int = 1,
        details: dict[str, Any] | None = None,
    ) -> DependencyEdge:
        """
        Manually declare a dependency between two repos.

        Args:
            source: Repo that depends on target
            target: Repo being depended upon
            edge_type: Nature of the dependency
            weight: Strength / frequency of the dependency
            details: Additional metadata for the edge

        Returns:
            The created DependencyEdge

        Raises:
            ValueError: If source or target is not registered
        """
        if source not in self.nodes:
            raise ValueError(f"Source repo '{source}' is not registered")
        if target not in self.nodes:
            raise ValueError(f"Target repo '{target}' is not registered")

        edge = DependencyEdge(
            source=source,
            target=target,
            edge_type=edge_type,
            weight=weight,
            details=details or {},
        )
        self.edges.append(edge)
        self.nodes[source].dependencies.add(target)
        self.nodes[target].dependents.add(source)
        self.analyzed = False
        return edge

    def analyze(self) -> None:
        """
        Analyze all registered repos to discover cross-repo dependencies.

        Scans Python files and declared package dependencies in each repo,
        then infers edges between repos that share package names or import
        paths.  Existing manually declared edges are preserved.
        """
        # Reset auto-discovered state (keep manual edges)
        manual_edges = [e for e in self.edges if e.edge_type != EdgeType.IMPORTS]
        self.edges = list(manual_edges)
        for node in self.nodes.values():
            node.dependencies.clear()
            node.dependents.clear()
            node.external_modules.clear()
            node.file_count = 0

        # Re-apply manual edges
        for edge in manual_edges:
            self.nodes[edge.source].dependencies.add(edge.target)
            self.nodes[edge.target].dependents.add(edge.source)

        # Gather per-repo information
        repo_info: dict[str, dict[str, Any]] = {}
        for name, node in self.nodes.items():
            info = self._analyze_repo(node)
            repo_info[name] = info
            node.file_count = info["file_count"]
            node.external_modules.update(info["external_modules"])

        # Infer cross-repo edges from shared package names
        self._infer_cross_repo_edges(repo_info)
        self.analyzed = True

    # -------------------------------------------------------------------------
    # PUBLIC API – QUERYING THE GRAPH
    # -------------------------------------------------------------------------

    def get_repo(self, name: str) -> RepoNode | None:
        """
        Retrieve a repo node by name.

        Args:
            name: Repo name

        Returns:
            RepoNode or None if not found
        """
        return self.nodes.get(name)

    def get_dependencies(self, name: str) -> list[RepoNode]:
        """
        Get repos that the named repo depends on.

        Args:
            name: Name of the repo

        Returns:
            List of RepoNode dependencies (empty list if not found)
        """
        node = self.nodes.get(name)
        if node is None:
            return []
        return [self.nodes[dep] for dep in node.dependencies if dep in self.nodes]

    def get_dependents(self, name: str) -> list[RepoNode]:
        """
        Get repos that depend on the named repo.

        Args:
            name: Name of the repo

        Returns:
            List of RepoNode dependents (empty list if not found)
        """
        node = self.nodes.get(name)
        if node is None:
            return []
        return [self.nodes[dep] for dep in node.dependents if dep in self.nodes]

    def get_affected_repos(self, name: str) -> list[str]:
        """
        Get all repos transitively affected when the named repo changes.

        Performs a breadth-first traversal of the dependents graph starting
        from the given repo.

        Args:
            name: Name of the changed repo

        Returns:
            Ordered list of affected repo names (excluding the changed repo)

        Raises:
            KeyError: If the named repo is not registered
        """
        if name not in self.nodes:
            raise KeyError(f"Repo '{name}' is not registered")

        visited: set[str] = set()
        queue: deque[str] = deque([name])
        affected: list[str] = []

        while queue:
            current = queue.popleft()
            for dependent in self.nodes[current].dependents:
                if dependent not in visited:
                    visited.add(dependent)
                    affected.append(dependent)
                    queue.append(dependent)

        return affected

    def get_build_order(self) -> list[str]:
        """
        Compute a topological build order (dependencies before dependents).

        Uses Kahn's algorithm to produce a valid build sequence.

        Returns:
            List of repo names in build order

        Raises:
            ValueError: If a circular dependency is detected
        """
        in_degree: dict[str, int] = {name: 0 for name in self.nodes}

        for node in self.nodes.values():
            for dep in node.dependencies:
                if dep in in_degree:
                    in_degree[node.name] += 1

        queue: deque[str] = deque(
            name for name, degree in in_degree.items() if degree == 0
        )
        order: list[str] = []

        while queue:
            current = queue.popleft()
            order.append(current)

            for dependent in self.nodes[current].dependents:
                if dependent in in_degree:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if len(order) != len(self.nodes):
            raise ValueError(
                "Circular dependency detected in multi-repo graph; "
                "cannot compute a valid build order"
            )

        return order

    def get_edges_for_repo(self, name: str) -> list[DependencyEdge]:
        """
        Get all edges involving a specific repo (as source or target).

        Args:
            name: Repo name

        Returns:
            List of DependencyEdge objects involving this repo
        """
        return [e for e in self.edges if e.source == name or e.target == name]

    def calculate_impact_score(self, name: str) -> float:
        """
        Calculate an impact score for a repo based on its dependent count.

        Repos with many dependents have higher impact scores.
        Uses a logarithmic scale consistent with DependencyAnalyzer.

        Args:
            name: Repo name

        Returns:
            Impact score on a 0–10 scale (0.0 if repo not found)
        """
        node = self.nodes.get(name)
        if node is None:
            return 0.0

        count = len(node.dependents)
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
        return 10.0

    def has_cycle(self) -> bool:
        """
        Check whether the dependency graph contains a cycle.

        Returns:
            True if a cycle exists, False otherwise
        """
        try:
            self.get_build_order()
            return False
        except ValueError:
            return True

    # -------------------------------------------------------------------------
    # SERIALIZATION
    # -------------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the full graph to a dictionary.

        Returns:
            Dictionary containing:
            - nodes: Mapping of repo name → node data
            - edges: List of edge data dictionaries
            - analyzed: Whether analyze() has been called
            - repo_count: Total number of registered repos
            - edge_count: Total number of edges
        """
        return {
            "nodes": {name: node.to_dict() for name, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges],
            "analyzed": self.analyzed,
            "repo_count": len(self.nodes),
            "edge_count": len(self.edges),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MultiRepoDependencyGraph:
        """
        Reconstruct a MultiRepoDependencyGraph from a serialized dictionary.

        Args:
            data: Dictionary as produced by to_dict()

        Returns:
            Populated MultiRepoDependencyGraph instance
        """
        graph = cls()

        for name, node_data in data.get("nodes", {}).items():
            node = RepoNode(
                name=name,
                path=node_data["path"],
                file_count=node_data.get("file_count", 0),
                external_modules=set(node_data.get("external_modules", [])),
                metadata=node_data.get("metadata", {}),
            )
            # Restore dependency/dependent sets directly (skip add_repo validation)
            node.dependencies = set(node_data.get("dependencies", []))
            node.dependents = set(node_data.get("dependents", []))
            graph.nodes[name] = node

        for edge_data in data.get("edges", []):
            edge = DependencyEdge(
                source=edge_data["source"],
                target=edge_data["target"],
                edge_type=EdgeType(edge_data.get("edge_type", EdgeType.IMPORTS.value)),
                weight=edge_data.get("weight", 1),
                details=edge_data.get("details", {}),
            )
            graph.edges.append(edge)

        graph.analyzed = data.get("analyzed", False)
        return graph

    # -------------------------------------------------------------------------
    # INTERNAL HELPERS
    # -------------------------------------------------------------------------

    def _analyze_repo(self, node: RepoNode) -> dict[str, Any]:
        """
        Scan a single repository and collect dependency metadata.

        Attempts Python AST-based analysis via DependencyAnalyzer, and falls
        back to package-manifest scanning when unavailable.

        Args:
            node: RepoNode to analyze

        Returns:
            Dictionary with keys:
            - file_count: Number of files analyzed
            - external_modules: Set of external package names
            - package_names: Set of package names declared by this repo
        """
        repo_path = Path(node.path)
        if not repo_path.exists():
            return {"file_count": 0, "external_modules": set(), "package_names": set()}

        external_modules: set[str] = set()
        file_count = 0

        # --- Python AST analysis ---
        try:
            from context.dependency_analyzer import DependencyAnalyzer

            analyzer = DependencyAnalyzer(project_dir=repo_path)
            graph_data = analyzer.build_dependency_graph()
            file_count = len(graph_data.get("nodes", {}))
            external_modules.update(graph_data.get("external_modules", []))
        except Exception:
            # Fall back to simple file counting
            try:
                py_files = list(repo_path.rglob("*.py"))
                file_count = len(py_files)
            except OSError:
                file_count = 0

        # --- Declared package names ---
        package_names: set[str] = self._extract_package_names(repo_path)

        # --- requirements.txt / setup.py declared dependencies ---
        declared_deps = self._extract_declared_deps(repo_path)
        external_modules.update(declared_deps)

        return {
            "file_count": file_count,
            "external_modules": external_modules,
            "package_names": package_names,
        }

    def _extract_package_names(self, repo_path: Path) -> set[str]:
        """
        Determine the importable package names provided by a repo.

        Checks for setup.py, pyproject.toml, package.json name fields, and
        top-level __init__.py directories.

        Args:
            repo_path: Path to the repo root

        Returns:
            Set of package name strings
        """
        names: set[str] = set()

        # Top-level Python packages (directories with __init__.py)
        try:
            for item in repo_path.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    names.add(item.name)
        except OSError:
            pass

        # pyproject.toml name field
        pyproject = repo_path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(encoding="utf-8")
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("name") and "=" in stripped:
                        value = stripped.split("=", 1)[1].strip().strip('"\'')
                        if value:
                            names.add(value)
                            names.add(value.replace("-", "_"))
            except OSError:
                pass

        # package.json name field (JS/TS repos)
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                import json

                data = json.loads(package_json.read_text(encoding="utf-8"))
                pkg_name = data.get("name", "")
                if pkg_name:
                    names.add(pkg_name)
                    names.add(pkg_name.lstrip("@").replace("/", "_").replace("-", "_"))
            except (OSError, ValueError):
                pass

        return names

    def _extract_declared_deps(self, repo_path: Path) -> set[str]:
        """
        Extract declared dependency names from package manifests.

        Reads requirements.txt and package.json dependencies sections.

        Args:
            repo_path: Path to the repo root

        Returns:
            Set of dependency names
        """
        deps: set[str] = set()

        # requirements.txt
        requirements = repo_path / "requirements.txt"
        if requirements.exists():
            try:
                for line in requirements.read_text(encoding="utf-8").splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        # Strip version specifiers: foo>=1.0 → foo
                        name = stripped.split("=")[0].split(">")[0].split("<")[0]
                        name = name.split("!")[0].split("[")[0].strip()
                        if name:
                            deps.add(name.lower().replace("-", "_"))
            except OSError:
                pass

        # package.json dependencies / devDependencies
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                import json

                data = json.loads(package_json.read_text(encoding="utf-8"))
                for section in ("dependencies", "devDependencies", "peerDependencies"):
                    for pkg in data.get(section, {}):
                        deps.add(pkg.lstrip("@").replace("/", "_").replace("-", "_"))
            except (OSError, ValueError):
                pass

        return deps

    def _infer_cross_repo_edges(
        self, repo_info: dict[str, dict[str, Any]]
    ) -> None:
        """
        Infer dependency edges between repos by matching external module names
        against package names provided by other repos.

        Args:
            repo_info: Per-repo analysis results from _analyze_repo()
        """
        for source_name, info in repo_info.items():
            ext_modules: set[str] = info.get("external_modules", set())
            for target_name, target_info in repo_info.items():
                if target_name == source_name:
                    continue
                target_packages: set[str] = target_info.get("package_names", set())
                # Normalize to lowercase for comparison
                normalized_ext = {m.lower().replace("-", "_") for m in ext_modules}
                normalized_pkg = {p.lower().replace("-", "_") for p in target_packages}
                shared = normalized_ext & normalized_pkg
                if shared:
                    # Check if edge already exists
                    existing = any(
                        e.source == source_name and e.target == target_name
                        for e in self.edges
                    )
                    if not existing:
                        self.add_edge(
                            source=source_name,
                            target=target_name,
                            edge_type=EdgeType.IMPORTS,
                            weight=len(shared),
                            details={"shared_packages": sorted(shared)},
                        )
