"""
Dependency Resolver
===================

Resolves spec dependencies for scheduled builds, ensuring correct execution order
and detecting circular dependencies.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from .models import ScheduledBuild

logger = logging.getLogger(__name__)


class CircularDependencyError(Exception):
    """Raised when circular dependencies are detected."""

    def __init__(self, cycle: list[str]):
        """
        Initialize error with detected cycle.

        Args:
            cycle: List of spec IDs forming the circular dependency
        """
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Circular dependency detected: {cycle_str}")


class MissingDependencyError(Exception):
    """Raised when a required dependency is not found."""

    def __init__(self, spec_id: str, missing_deps: list[str]):
        """
        Initialize error with missing dependencies.

        Args:
            spec_id: Spec ID with missing dependencies
            missing_deps: List of missing dependency spec IDs
        """
        self.spec_id = spec_id
        self.missing_deps = missing_deps
        deps_str = ", ".join(missing_deps)
        super().__init__(f"Spec '{spec_id}' has missing dependencies: {deps_str}")


@dataclass
class DependencyGraph:
    """
    Represents the dependency graph structure.

    Attributes:
        nodes: Set of all spec IDs in the graph
        edges: Adjacency list representing dependencies (spec_id -> [dependencies])
        reverse_edges: Reverse adjacency list (spec_id -> [dependents])
    """

    nodes: set[str]
    edges: dict[str, list[str]]
    reverse_edges: dict[str, list[str]]

    @property
    def has_cycles(self) -> bool:
        """Check if graph contains cycles."""
        try:
            # Try to perform topological sort - if it fails, there's a cycle
            self._topological_sort()
            return False
        except CircularDependencyError:
            return True

    def _topological_sort(self) -> list[str]:
        """
        Perform topological sort using Kahn's algorithm.

        Returns:
            List of spec IDs in valid execution order

        Raises:
            CircularDependencyError: If cycles detected
        """
        # Calculate in-degrees for all nodes
        # edges[node] = [deps] means node depends on deps, so node has incoming edges
        in_degree = dict.fromkeys(self.nodes, 0)
        for node in self.nodes:
            for dep in self.edges.get(node, []):
                if dep in in_degree:
                    in_degree[node] += 1

        # Start with nodes that have no dependencies
        queue = deque([node for node in self.nodes if in_degree[node] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            # Process dependents
            for dependent in self.reverse_edges.get(node, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # If not all nodes processed, there's a cycle
        if len(result) != len(self.nodes):
            # Find nodes that form the cycle
            unvisited = set(self.nodes) - set(result)
            cycle = self._find_cycle(unvisited)
            raise CircularDependencyError(cycle)

        return result

    def _find_cycle(self, unvisited: set[str]) -> list[str]:
        """
        Find a cycle in the graph starting from unvisited nodes.

        Args:
            unvisited: Set of nodes not included in topological sort

        Returns:
            List of spec IDs forming a cycle
        """
        visited = set()
        rec_stack = set()
        cycle = []

        def dfs(node: str, path: list[str]) -> bool:
            """Depth-first search to find cycle."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.edges.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle - extract it from path
                    cycle_start = path.index(neighbor)
                    cycle.extend(path[cycle_start:] + [neighbor])
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        # Start DFS from any unvisited node
        for node in unvisited:
            if node not in visited and dfs(node, []):
                return cycle

        # Fallback: return first unvisited nodes
        return list(unvisited)[:3]

    def get_execution_levels(self) -> list[list[str]]:
        """
        Get execution levels for parallel processing.

        Specs at the same level can be executed in parallel as they have
        no dependencies on each other.

        Returns:
            List of levels, where each level is a list of spec IDs that
            can execute in parallel

        Example:
            If A depends on B and C, B depends on D, and C is independent:
            Level 0: [D, C]  # No dependencies
            Level 1: [B]     # Depends on D
            Level 2: [A]     # Depends on B and C
        """
        sorted_specs = self._topological_sort()

        # Calculate depth for each node
        depth = dict.fromkeys(self.nodes, 0)
        for node in sorted_specs:
            for dep in self.edges.get(node, []):
                if dep in depth:
                    depth[node] = max(depth[node], depth[dep] + 1)

        # Group by depth
        levels: dict[int, list[str]] = defaultdict(list)
        for node, d in depth.items():
            levels[d].append(node)

        # Return as sorted list of levels
        max_depth = max(depth.values()) if depth else 0
        return [levels[i] for i in range(max_depth + 1)]


class DependencyResolver:
    """
    Resolves dependencies for scheduled builds.

    Responsibilities:
    - Validate all dependencies exist
    - Detect circular dependencies
    - Resolve execution order using topological sort
    - Identify builds that can execute in parallel
    - Determine when a build's dependencies are satisfied
    """

    def __init__(self):
        """Initialize dependency resolver."""
        logger.debug("DependencyResolver initialized")

    def validate_dependencies(self, builds: list[ScheduledBuild]) -> None:
        """
        Validate that all build dependencies are satisfied.

        Args:
            builds: List of scheduled builds to validate

        Raises:
            MissingDependencyError: If any build references missing dependencies
            CircularDependencyError: If circular dependencies detected
        """
        build_ids = {build.spec_id for build in builds}

        # Check for missing dependencies
        for build in builds:
            missing = [dep for dep in build.dependencies if dep not in build_ids]
            if missing:
                raise MissingDependencyError(build.spec_id, missing)

        # Check for circular dependencies
        graph = self._build_dependency_graph(builds)
        if graph.has_cycles:
            # This will raise CircularDependencyError with cycle details
            graph._topological_sort()

        logger.info(f"Validated dependencies for {len(builds)} builds")

    def resolve_execution_order(
        self, builds: list[ScheduledBuild]
    ) -> list[ScheduledBuild]:
        """
        Resolve execution order for builds based on dependencies.

        Returns builds sorted such that dependencies are always executed
        before their dependents.

        Args:
            builds: List of scheduled builds

        Returns:
            List of builds in valid execution order

        Raises:
            CircularDependencyError: If circular dependencies detected
        """
        if not builds:
            return []

        graph = self._build_dependency_graph(builds)
        sorted_ids = graph._topological_sort()

        # Map spec_id to build
        build_map = {build.spec_id: build for build in builds}

        # Return builds in sorted order
        result = [build_map[spec_id] for spec_id in sorted_ids]

        logger.info(f"Resolved execution order for {len(result)} builds")
        return result

    def get_parallel_execution_groups(
        self, builds: list[ScheduledBuild]
    ) -> list[list[ScheduledBuild]]:
        """
        Get groups of builds that can execute in parallel.

        Builds in the same group have no dependencies on each other and
        all their dependencies are in earlier groups.

        Args:
            builds: List of scheduled builds

        Returns:
            List of groups, where each group contains builds that can run
            in parallel

        Example:
            If build A depends on B and C, B depends on D:
            Group 0: [D, C]  # Can run in parallel
            Group 1: [B]     # Must wait for D
            Group 2: [A]     # Must wait for B and C
        """
        if not builds:
            return []

        graph = self._build_dependency_graph(builds)
        levels = graph.get_execution_levels()

        # Map spec_id to build
        build_map = {build.spec_id: build for build in builds}

        # Convert levels to build groups
        groups = [[build_map[spec_id] for spec_id in level] for level in levels]

        logger.info(
            f"Created {len(groups)} parallel execution groups for {len(builds)} builds"
        )
        return groups

    def are_dependencies_satisfied(
        self,
        build: ScheduledBuild,
        completed_specs: set[str],
    ) -> bool:
        """
        Check if all dependencies for a build are satisfied.

        Args:
            build: ScheduledBuild to check
            completed_specs: Set of spec IDs that have completed successfully

        Returns:
            True if all dependencies are satisfied, False otherwise
        """
        return all(dep in completed_specs for dep in build.dependencies)

    def get_blocked_builds(
        self,
        builds: list[ScheduledBuild],
        completed_specs: set[str],
    ) -> list[ScheduledBuild]:
        """
        Get builds that are blocked by unsatisfied dependencies.

        Args:
            builds: List of scheduled builds
            completed_specs: Set of spec IDs that have completed

        Returns:
            List of builds waiting on dependencies
        """
        blocked = [
            build
            for build in builds
            if build.dependencies
            and not self.are_dependencies_satisfied(build, completed_specs)
        ]

        logger.debug(f"Found {len(blocked)} blocked builds")
        return blocked

    def get_ready_builds(
        self,
        builds: list[ScheduledBuild],
        completed_specs: set[str],
    ) -> list[ScheduledBuild]:
        """
        Get builds that are ready to execute (dependencies satisfied).

        Args:
            builds: List of scheduled builds
            completed_specs: Set of spec IDs that have completed

        Returns:
            List of builds ready to execute
        """
        ready = [
            build
            for build in builds
            if self.are_dependencies_satisfied(build, completed_specs)
        ]

        logger.debug(f"Found {len(ready)} ready builds")
        return ready

    def get_dependency_chain(
        self, build: ScheduledBuild, builds: list[ScheduledBuild]
    ) -> list[str]:
        """
        Get the full dependency chain for a build.

        Returns all specs that must complete before this build can execute,
        in execution order.

        Args:
            build: ScheduledBuild to analyze
            builds: All scheduled builds

        Returns:
            List of spec IDs in dependency chain (ordered)
        """
        graph = self._build_dependency_graph(builds)

        # BFS to find all dependencies
        visited = set()
        queue = deque(build.dependencies)
        chain = []

        while queue:
            spec_id = queue.popleft()
            if spec_id in visited:
                continue

            visited.add(spec_id)
            chain.append(spec_id)

            # Add dependencies of this spec
            for dep in graph.edges.get(spec_id, []):
                if dep not in visited:
                    queue.append(dep)

        # Sort chain by execution order
        sorted_chain = []
        for spec_id in graph._topological_sort():
            if spec_id in chain:
                sorted_chain.append(spec_id)

        logger.debug(f"Dependency chain for {build.spec_id}: {sorted_chain}")
        return sorted_chain

    def _build_dependency_graph(self, builds: list[ScheduledBuild]) -> DependencyGraph:
        """
        Build dependency graph from scheduled builds.

        Args:
            builds: List of scheduled builds

        Returns:
            DependencyGraph representing build dependencies
        """
        nodes = {build.spec_id for build in builds}
        edges: dict[str, list[str]] = {}
        reverse_edges: dict[str, list[str]] = defaultdict(list)

        for build in builds:
            edges[build.spec_id] = build.dependencies.copy()

            # Build reverse edges (which specs depend on this one)
            for dep in build.dependencies:
                reverse_edges[dep].append(build.spec_id)

        return DependencyGraph(
            nodes=nodes,
            edges=edges,
            reverse_edges=dict(reverse_edges),
        )

    def get_dependency_stats(self, builds: list[ScheduledBuild]) -> dict[str, Any]:
        """
        Get statistics about dependencies.

        Args:
            builds: List of scheduled builds

        Returns:
            Dictionary with dependency statistics:
            - total_builds: Total number of builds
            - builds_with_deps: Number of builds with dependencies
            - total_dependencies: Total dependency count
            - max_chain_length: Longest dependency chain
            - parallel_groups: Number of parallel execution groups
            - can_parallelize: Whether parallel execution is possible
        """
        if not builds:
            return {
                "total_builds": 0,
                "builds_with_deps": 0,
                "total_dependencies": 0,
                "max_chain_length": 0,
                "parallel_groups": 0,
                "can_parallelize": False,
            }

        graph = self._build_dependency_graph(builds)
        groups = graph.get_execution_levels()

        # Calculate max chain length
        max_chain = 0
        for build in builds:
            chain = self.get_dependency_chain(build, builds)
            max_chain = max(max_chain, len(chain))

        builds_with_deps = sum(1 for b in builds if b.dependencies)
        total_deps = sum(len(b.dependencies) for b in builds)

        return {
            "total_builds": len(builds),
            "builds_with_deps": builds_with_deps,
            "total_dependencies": total_deps,
            "max_chain_length": max_chain,
            "parallel_groups": len(groups),
            "can_parallelize": len(groups) > 1 and any(len(g) > 1 for g in groups),
        }
