#!/usr/bin/env python3
"""
Tests for the MultiRepoDependencyGraph module.

Tests cover:
- Adding and removing repos (nodes)
- Adding edges between repos
- Querying dependencies and dependents
- Topological sort (build order) via Kahn's algorithm
- Cycle detection
- Affected repo traversal (BFS)
- Impact score calculation
- Serialization (to_dict / from_dict)
- Error handling (unknown repos, duplicate registration, cycles)
"""

import sys
from pathlib import Path

import pytest

# Add apps/backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analysis.dependency_graph import (
    DependencyEdge,
    EdgeType,
    MultiRepoDependencyGraph,
    RepoNode,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def empty_graph() -> MultiRepoDependencyGraph:
    """Return a fresh, empty MultiRepoDependencyGraph."""
    return MultiRepoDependencyGraph()


@pytest.fixture
def simple_graph(tmp_path: Path) -> MultiRepoDependencyGraph:
    """
    Three-repo graph: frontend → backend → shared

        shared  (no deps)
        backend → shared
        frontend → backend
    """
    graph = MultiRepoDependencyGraph()
    graph.add_repo("shared", tmp_path / "shared")
    graph.add_repo("backend", tmp_path / "backend")
    graph.add_repo("frontend", tmp_path / "frontend")
    graph.add_edge("backend", "shared")
    graph.add_edge("frontend", "backend")
    return graph


@pytest.fixture
def diamond_graph(tmp_path: Path) -> MultiRepoDependencyGraph:
    """
    Diamond dependency graph:

        a → b → d
        a → c → d
    """
    graph = MultiRepoDependencyGraph()
    for name in ("a", "b", "c", "d"):
        graph.add_repo(name, tmp_path / name)
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    graph.add_edge("b", "d")
    graph.add_edge("c", "d")
    return graph


# =============================================================================
# TESTS – ADDING REPOS
# =============================================================================


class TestAddRepo:
    """Tests for MultiRepoDependencyGraph.add_repo."""

    def test_add_single_repo_returns_node(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """add_repo should return the created RepoNode."""
        node = empty_graph.add_repo("my-repo", tmp_path / "my-repo")

        assert isinstance(node, RepoNode)
        assert node.name == "my-repo"

    def test_added_repo_appears_in_nodes(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """Registered repo should be accessible via .nodes."""
        empty_graph.add_repo("repo-a", tmp_path / "a")

        assert "repo-a" in empty_graph.nodes

    def test_add_repo_stores_resolved_path(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """RepoNode.path should be the resolved absolute string path."""
        raw_path = tmp_path / "sub"
        node = empty_graph.add_repo("sub", raw_path)

        assert node.path == str(raw_path.resolve())

    def test_add_repo_stores_metadata(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """Metadata dict should be attached to the node."""
        meta = {"language": "python", "tags": ["api"]}
        node = empty_graph.add_repo("api", tmp_path / "api", metadata=meta)

        assert node.metadata["language"] == "python"
        assert node.metadata["tags"] == ["api"]

    def test_add_repo_empty_metadata_by_default(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """When no metadata is provided the node should have an empty dict."""
        node = empty_graph.add_repo("no-meta", tmp_path / "no-meta")

        assert node.metadata == {}

    def test_add_duplicate_repo_raises_value_error(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """Registering the same name twice must raise ValueError."""
        empty_graph.add_repo("dup", tmp_path / "dup1")

        with pytest.raises(ValueError, match="already registered"):
            empty_graph.add_repo("dup", tmp_path / "dup2")

    def test_add_repo_resets_analyzed_flag(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """Adding a new repo should mark the graph as not yet analyzed."""
        empty_graph.analyzed = True
        empty_graph.add_repo("new", tmp_path / "new")

        assert empty_graph.analyzed is False


# =============================================================================
# TESTS – REMOVING REPOS
# =============================================================================


class TestRemoveRepo:
    """Tests for MultiRepoDependencyGraph.remove_repo."""

    def test_remove_existing_repo_returns_true(self, simple_graph: MultiRepoDependencyGraph):
        """remove_repo should return True when the repo is found and removed."""
        result = simple_graph.remove_repo("shared")

        assert result is True

    def test_remove_nonexistent_repo_returns_false(self, empty_graph: MultiRepoDependencyGraph):
        """remove_repo should return False when name is not registered."""
        assert empty_graph.remove_repo("ghost") is False

    def test_removed_repo_absent_from_nodes(self, simple_graph: MultiRepoDependencyGraph):
        """After removal the repo name should no longer be in .nodes."""
        simple_graph.remove_repo("shared")

        assert "shared" not in simple_graph.nodes

    def test_remove_repo_cleans_up_edges(self, simple_graph: MultiRepoDependencyGraph):
        """Edges referencing the removed repo should be purged."""
        simple_graph.remove_repo("backend")

        for edge in simple_graph.edges:
            assert edge.source != "backend"
            assert edge.target != "backend"

    def test_remove_repo_cleans_up_dependent_references(self, simple_graph: MultiRepoDependencyGraph):
        """Other nodes' .dependencies / .dependents sets must not reference removed name."""
        simple_graph.remove_repo("backend")

        for node in simple_graph.nodes.values():
            assert "backend" not in node.dependencies
            assert "backend" not in node.dependents


# =============================================================================
# TESTS – ADDING EDGES
# =============================================================================


class TestAddEdge:
    """Tests for MultiRepoDependencyGraph.add_edge."""

    def test_add_edge_returns_dependency_edge(self, simple_graph: MultiRepoDependencyGraph):
        """add_edge should return a DependencyEdge instance."""
        # Re-use simple_graph but add a fresh edge
        edge = simple_graph.add_edge("frontend", "shared")

        assert isinstance(edge, DependencyEdge)
        assert edge.source == "frontend"
        assert edge.target == "shared"

    def test_add_edge_default_type_is_imports(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """Default edge_type should be EdgeType.IMPORTS."""
        empty_graph.add_repo("a", tmp_path / "a")
        empty_graph.add_repo("b", tmp_path / "b")
        edge = empty_graph.add_edge("a", "b")

        assert edge.edge_type == EdgeType.IMPORTS

    def test_add_edge_custom_type(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """Edge type should be stored correctly."""
        empty_graph.add_repo("x", tmp_path / "x")
        empty_graph.add_repo("y", tmp_path / "y")
        edge = empty_graph.add_edge("x", "y", edge_type=EdgeType.DECLARES)

        assert edge.edge_type == EdgeType.DECLARES

    def test_add_edge_updates_source_dependencies(self, simple_graph: MultiRepoDependencyGraph):
        """Source node's .dependencies should include target name after add_edge."""
        assert "shared" in simple_graph.nodes["backend"].dependencies

    def test_add_edge_updates_target_dependents(self, simple_graph: MultiRepoDependencyGraph):
        """Target node's .dependents should include source name after add_edge."""
        assert "backend" in simple_graph.nodes["shared"].dependents

    def test_add_edge_unknown_source_raises_value_error(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """Specifying an unregistered source should raise ValueError."""
        empty_graph.add_repo("target", tmp_path / "t")

        with pytest.raises(ValueError, match="Source repo"):
            empty_graph.add_edge("ghost-source", "target")

    def test_add_edge_unknown_target_raises_value_error(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """Specifying an unregistered target should raise ValueError."""
        empty_graph.add_repo("source", tmp_path / "s")

        with pytest.raises(ValueError, match="Target repo"):
            empty_graph.add_edge("source", "ghost-target")

    def test_add_edge_stores_weight(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """Custom weight should be stored on the edge."""
        empty_graph.add_repo("p", tmp_path / "p")
        empty_graph.add_repo("q", tmp_path / "q")
        edge = empty_graph.add_edge("p", "q", weight=42)

        assert edge.weight == 42

    def test_add_edge_stores_details(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """Custom details should be stored on the edge."""
        empty_graph.add_repo("m", tmp_path / "m")
        empty_graph.add_repo("n", tmp_path / "n")
        details = {"shared_packages": ["requests"]}
        edge = empty_graph.add_edge("m", "n", details=details)

        assert edge.details["shared_packages"] == ["requests"]


# =============================================================================
# TESTS – QUERYING
# =============================================================================


class TestGetRepo:
    """Tests for MultiRepoDependencyGraph.get_repo."""

    def test_get_existing_repo(self, simple_graph: MultiRepoDependencyGraph):
        """get_repo should return the RepoNode for a registered name."""
        node = simple_graph.get_repo("backend")

        assert node is not None
        assert node.name == "backend"

    def test_get_nonexistent_repo_returns_none(self, simple_graph: MultiRepoDependencyGraph):
        """get_repo should return None for an unknown name."""
        assert simple_graph.get_repo("nope") is None


class TestGetDependencies:
    """Tests for MultiRepoDependencyGraph.get_dependencies."""

    def test_get_dependencies_returns_correct_nodes(self, simple_graph: MultiRepoDependencyGraph):
        """backend depends on shared; get_dependencies should return [shared_node]."""
        deps = simple_graph.get_dependencies("backend")

        assert len(deps) == 1
        assert deps[0].name == "shared"

    def test_get_dependencies_for_root_node_is_empty(self, simple_graph: MultiRepoDependencyGraph):
        """shared has no dependencies; result should be empty list."""
        assert simple_graph.get_dependencies("shared") == []

    def test_get_dependencies_unknown_repo_returns_empty(self, simple_graph: MultiRepoDependencyGraph):
        """Querying an unknown repo should return an empty list (no exception)."""
        assert simple_graph.get_dependencies("unknown") == []


class TestGetDependents:
    """Tests for MultiRepoDependencyGraph.get_dependents."""

    def test_get_dependents_returns_correct_nodes(self, simple_graph: MultiRepoDependencyGraph):
        """shared is depended on by backend; get_dependents should return [backend_node]."""
        dependents = simple_graph.get_dependents("shared")

        assert len(dependents) == 1
        assert dependents[0].name == "backend"

    def test_get_dependents_for_leaf_node_is_empty(self, simple_graph: MultiRepoDependencyGraph):
        """frontend has no dependents; result should be empty list."""
        assert simple_graph.get_dependents("frontend") == []

    def test_get_dependents_unknown_repo_returns_empty(self, simple_graph: MultiRepoDependencyGraph):
        """Querying an unknown repo should return an empty list (no exception)."""
        assert simple_graph.get_dependents("unknown") == []


# =============================================================================
# TESTS – AFFECTED REPOS (BFS TRAVERSAL)
# =============================================================================


class TestGetAffectedRepos:
    """Tests for MultiRepoDependencyGraph.get_affected_repos."""

    def test_changing_shared_affects_backend_and_frontend(self, simple_graph: MultiRepoDependencyGraph):
        """shared ← backend ← frontend, so changing shared affects both."""
        affected = simple_graph.get_affected_repos("shared")

        assert "backend" in affected
        assert "frontend" in affected
        assert "shared" not in affected

    def test_changing_leaf_affects_nobody(self, simple_graph: MultiRepoDependencyGraph):
        """frontend has no dependents; changing it affects nobody."""
        affected = simple_graph.get_affected_repos("frontend")

        assert affected == []

    def test_get_affected_repos_unknown_raises_key_error(self, simple_graph: MultiRepoDependencyGraph):
        """Passing an unknown repo name should raise KeyError."""
        with pytest.raises(KeyError):
            simple_graph.get_affected_repos("does-not-exist")

    def test_diamond_graph_all_upstream_affected(self, diamond_graph: MultiRepoDependencyGraph):
        """
        Diamond: d ← b ← a, d ← c ← a
        Changing d should affect b, c, and a (all of them).
        """
        affected = diamond_graph.get_affected_repos("d")

        assert set(affected) == {"b", "c", "a"}

    def test_no_duplicate_repos_in_affected(self, diamond_graph: MultiRepoDependencyGraph):
        """Each repo should appear at most once in the affected list."""
        affected = diamond_graph.get_affected_repos("d")

        assert len(affected) == len(set(affected))


# =============================================================================
# TESTS – BUILD ORDER (TOPOLOGICAL SORT)
# =============================================================================


class TestGetBuildOrder:
    """Tests for MultiRepoDependencyGraph.get_build_order."""

    def test_simple_graph_build_order_respects_deps(self, simple_graph: MultiRepoDependencyGraph):
        """
        For shared → backend → frontend the build order must satisfy:
        shared before backend, backend before frontend.
        """
        order = simple_graph.get_build_order()

        assert order.index("shared") < order.index("backend")
        assert order.index("backend") < order.index("frontend")

    def test_build_order_includes_all_repos(self, simple_graph: MultiRepoDependencyGraph):
        """Every registered repo should appear exactly once in the build order."""
        order = simple_graph.get_build_order()

        assert set(order) == set(simple_graph.nodes.keys())
        assert len(order) == len(simple_graph.nodes)

    def test_diamond_graph_build_order_valid(self, diamond_graph: MultiRepoDependencyGraph):
        """
        Diamond: a→b→d, a→c→d
        d must appear before b and c; b and c before a.
        """
        order = diamond_graph.get_build_order()

        assert order.index("d") < order.index("b")
        assert order.index("d") < order.index("c")
        assert order.index("b") < order.index("a")
        assert order.index("c") < order.index("a")

    def test_no_deps_graph_build_order_is_all_nodes(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """When there are no edges, all nodes appear in the build order."""
        empty_graph.add_repo("x", tmp_path / "x")
        empty_graph.add_repo("y", tmp_path / "y")
        order = empty_graph.get_build_order()

        assert set(order) == {"x", "y"}

    def test_cyclic_graph_raises_value_error(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """A circular dependency should raise ValueError."""
        empty_graph.add_repo("a", tmp_path / "a")
        empty_graph.add_repo("b", tmp_path / "b")
        empty_graph.add_edge("a", "b")
        empty_graph.add_edge("b", "a")

        with pytest.raises(ValueError, match="[Cc]ircular"):
            empty_graph.get_build_order()


# =============================================================================
# TESTS – CYCLE DETECTION
# =============================================================================


class TestHasCycle:
    """Tests for MultiRepoDependencyGraph.has_cycle."""

    def test_acyclic_graph_has_no_cycle(self, simple_graph: MultiRepoDependencyGraph):
        """Simple linear graph should have no cycle."""
        assert simple_graph.has_cycle() is False

    def test_empty_graph_has_no_cycle(self, empty_graph: MultiRepoDependencyGraph):
        """An empty graph cannot have a cycle."""
        assert empty_graph.has_cycle() is False

    def test_cyclic_graph_has_cycle(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """A → B → A should be detected as cyclic."""
        empty_graph.add_repo("a", tmp_path / "a")
        empty_graph.add_repo("b", tmp_path / "b")
        empty_graph.add_edge("a", "b")
        empty_graph.add_edge("b", "a")

        assert empty_graph.has_cycle() is True

    def test_self_loop_is_cycle(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """A node pointing to itself creates a cycle."""
        empty_graph.add_repo("self", tmp_path / "self")
        # Manually create self-loop by manipulating the node's sets to avoid
        # add_edge validation which disallows undefined targets (self IS defined).
        empty_graph.add_edge("self", "self")

        assert empty_graph.has_cycle() is True

    def test_three_node_cycle(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """A → B → C → A is a three-node cycle."""
        for name in ("a", "b", "c"):
            empty_graph.add_repo(name, tmp_path / name)
        empty_graph.add_edge("a", "b")
        empty_graph.add_edge("b", "c")
        empty_graph.add_edge("c", "a")

        assert empty_graph.has_cycle() is True

    def test_diamond_graph_has_no_cycle(self, diamond_graph: MultiRepoDependencyGraph):
        """Diamond (DAG) should have no cycle."""
        assert diamond_graph.has_cycle() is False


# =============================================================================
# TESTS – EDGES FOR REPO
# =============================================================================


class TestGetEdgesForRepo:
    """Tests for MultiRepoDependencyGraph.get_edges_for_repo."""

    def test_returns_source_and_target_edges(self, simple_graph: MultiRepoDependencyGraph):
        """backend appears as both source (→shared) and target (←frontend)."""
        edges = simple_graph.get_edges_for_repo("backend")
        sources = {e.source for e in edges}
        targets = {e.target for e in edges}

        assert "backend" in sources or "backend" in targets
        # Specifically: one edge where backend is source, one where it's target
        assert any(e.source == "backend" for e in edges)
        assert any(e.target == "backend" for e in edges)

    def test_returns_empty_for_isolated_repo(self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path):
        """Repo with no edges should return empty list."""
        empty_graph.add_repo("solo", tmp_path / "solo")

        assert empty_graph.get_edges_for_repo("solo") == []

    def test_returns_empty_for_unknown_repo(self, simple_graph: MultiRepoDependencyGraph):
        """Unknown repo name should return empty list without raising."""
        assert simple_graph.get_edges_for_repo("mystery") == []


# =============================================================================
# TESTS – IMPACT SCORE
# =============================================================================


class TestCalculateImpactScore:
    """Tests for MultiRepoDependencyGraph.calculate_impact_score."""

    def test_no_dependents_score_is_zero(self, simple_graph: MultiRepoDependencyGraph):
        """frontend has no dependents; impact score should be 0.0."""
        assert simple_graph.calculate_impact_score("frontend") == 0.0

    def test_one_dependent_score_is_three(self, simple_graph: MultiRepoDependencyGraph):
        """backend has one dependent (frontend); score should be 3.0."""
        assert simple_graph.calculate_impact_score("backend") == 3.0

    def test_unknown_repo_score_is_zero(self, simple_graph: MultiRepoDependencyGraph):
        """Score for an unknown repo should be 0.0 (no exception)."""
        assert simple_graph.calculate_impact_score("does-not-exist") == 0.0

    @pytest.mark.parametrize(
        "num_dependents, expected_score",
        [
            (0, 0.0),
            (1, 3.0),
            (2, 5.0),
            (3, 5.0),
            (5, 7.0),
            (10, 7.0),
            (11, 9.0),
            (30, 9.0),
            (31, 10.0),
        ],
    )
    def test_impact_score_scale(
        self,
        empty_graph: MultiRepoDependencyGraph,
        tmp_path: Path,
        num_dependents: int,
        expected_score: float,
    ):
        """Impact score should follow the documented logarithmic scale."""
        # Add a central repo and N dependents
        empty_graph.add_repo("center", tmp_path / "center")
        for i in range(num_dependents):
            name = f"dep-{i}"
            empty_graph.add_repo(name, tmp_path / name)
            empty_graph.add_edge(name, "center")

        assert empty_graph.calculate_impact_score("center") == expected_score


# =============================================================================
# TESTS – SERIALIZATION
# =============================================================================


class TestToDict:
    """Tests for MultiRepoDependencyGraph.to_dict."""

    def test_to_dict_contains_required_keys(self, simple_graph: MultiRepoDependencyGraph):
        """Serialized dict should have nodes, edges, analyzed, repo_count, edge_count."""
        data = simple_graph.to_dict()

        assert "nodes" in data
        assert "edges" in data
        assert "analyzed" in data
        assert "repo_count" in data
        assert "edge_count" in data

    def test_to_dict_repo_count_matches(self, simple_graph: MultiRepoDependencyGraph):
        """repo_count should equal the number of registered nodes."""
        data = simple_graph.to_dict()

        assert data["repo_count"] == len(simple_graph.nodes)

    def test_to_dict_edge_count_matches(self, simple_graph: MultiRepoDependencyGraph):
        """edge_count should equal the number of edges."""
        data = simple_graph.to_dict()

        assert data["edge_count"] == len(simple_graph.edges)

    def test_node_to_dict_fields(self, simple_graph: MultiRepoDependencyGraph):
        """Each node dict should include expected fields."""
        data = simple_graph.to_dict()
        node_data = data["nodes"]["backend"]

        assert "name" in node_data
        assert "path" in node_data
        assert "dependencies" in node_data
        assert "dependents" in node_data
        assert "file_count" in node_data
        assert "external_modules" in node_data
        assert "metadata" in node_data

    def test_edge_to_dict_fields(self, simple_graph: MultiRepoDependencyGraph):
        """Each edge dict should include expected fields."""
        data = simple_graph.to_dict()
        edge_data = data["edges"][0]

        assert "source" in edge_data
        assert "target" in edge_data
        assert "edge_type" in edge_data
        assert "weight" in edge_data
        assert "details" in edge_data


class TestFromDict:
    """Tests for MultiRepoDependencyGraph.from_dict."""

    def test_round_trip_preserves_nodes(self, simple_graph: MultiRepoDependencyGraph):
        """Serializing and deserializing should restore the same node names."""
        data = simple_graph.to_dict()
        restored = MultiRepoDependencyGraph.from_dict(data)

        assert set(restored.nodes.keys()) == set(simple_graph.nodes.keys())

    def test_round_trip_preserves_edge_count(self, simple_graph: MultiRepoDependencyGraph):
        """Serializing and deserializing should restore all edges."""
        data = simple_graph.to_dict()
        restored = MultiRepoDependencyGraph.from_dict(data)

        assert len(restored.edges) == len(simple_graph.edges)

    def test_round_trip_preserves_dependencies(self, simple_graph: MultiRepoDependencyGraph):
        """Dependency sets should survive round-trip serialization."""
        data = simple_graph.to_dict()
        restored = MultiRepoDependencyGraph.from_dict(data)

        assert restored.nodes["backend"].dependencies == simple_graph.nodes["backend"].dependencies

    def test_round_trip_preserves_dependents(self, simple_graph: MultiRepoDependencyGraph):
        """Dependent sets should survive round-trip serialization."""
        data = simple_graph.to_dict()
        restored = MultiRepoDependencyGraph.from_dict(data)

        assert restored.nodes["shared"].dependents == simple_graph.nodes["shared"].dependents

    def test_round_trip_preserves_analyzed_flag(self, simple_graph: MultiRepoDependencyGraph):
        """analyzed flag should be preserved through serialization."""
        simple_graph.analyzed = True
        data = simple_graph.to_dict()
        restored = MultiRepoDependencyGraph.from_dict(data)

        assert restored.analyzed is True

    def test_from_dict_empty_data_creates_empty_graph(self):
        """from_dict with empty dict should produce an empty graph."""
        restored = MultiRepoDependencyGraph.from_dict({})

        assert restored.nodes == {}
        assert restored.edges == []


# =============================================================================
# TESTS – REPO NODE DATA CLASS
# =============================================================================


class TestRepoNode:
    """Tests for the RepoNode dataclass."""

    def test_repo_node_defaults(self, tmp_path: Path):
        """RepoNode should have sensible defaults for all optional fields."""
        node = RepoNode(name="test", path=str(tmp_path))

        assert node.dependencies == set()
        assert node.dependents == set()
        assert node.file_count == 0
        assert node.external_modules == set()
        assert node.metadata == {}

    def test_repo_node_to_dict_sorted_sets(self, tmp_path: Path):
        """to_dict should produce sorted lists for set fields."""
        node = RepoNode(name="test", path=str(tmp_path))
        node.dependencies = {"z-dep", "a-dep"}
        node.dependents = {"z-dep2", "a-dep2"}

        data = node.to_dict()

        assert data["dependencies"] == sorted(["z-dep", "a-dep"])
        assert data["dependents"] == sorted(["z-dep2", "a-dep2"])


# =============================================================================
# TESTS – DEPENDENCY EDGE DATA CLASS
# =============================================================================


class TestDependencyEdge:
    """Tests for the DependencyEdge dataclass."""

    def test_dependency_edge_defaults(self):
        """DependencyEdge should have correct default values."""
        edge = DependencyEdge(source="a", target="b")

        assert edge.edge_type == EdgeType.IMPORTS
        assert edge.weight == 1
        assert edge.details == {}

    def test_dependency_edge_to_dict(self):
        """to_dict should produce a dictionary with expected keys."""
        edge = DependencyEdge(
            source="a",
            target="b",
            edge_type=EdgeType.DECLARES,
            weight=5,
            details={"note": "test"},
        )
        data = edge.to_dict()

        assert data["source"] == "a"
        assert data["target"] == "b"
        assert data["edge_type"] == EdgeType.DECLARES.value
        assert data["weight"] == 5
        assert data["details"] == {"note": "test"}


# =============================================================================
# TESTS – EDGE TYPE ENUM
# =============================================================================


class TestEdgeType:
    """Tests for the EdgeType enum."""

    def test_edge_type_values(self):
        """Each EdgeType should have the expected string value."""
        assert EdgeType.IMPORTS.value == "imports"
        assert EdgeType.DECLARES.value == "declares"
        assert EdgeType.REFERENCES.value == "references"
        assert EdgeType.UNKNOWN.value == "unknown"

    def test_edge_type_is_str_subclass(self):
        """EdgeType members should be instances of str (str enum)."""
        assert isinstance(EdgeType.IMPORTS, str)
        assert isinstance(EdgeType.DECLARES, str)


# =============================================================================
# TESTS – INTEGRATION / COMBINED SCENARIOS
# =============================================================================


class TestIntegrationScenarios:
    """End-to-end integration tests covering combined operations."""

    def test_add_then_remove_repo_updates_edge_and_dependency_sets(
        self, simple_graph: MultiRepoDependencyGraph
    ):
        """Removing a middle node should leave the remaining graph consistent."""
        simple_graph.remove_repo("backend")

        # shared is still in graph, frontend is still in graph
        assert "shared" in simple_graph.nodes
        assert "frontend" in simple_graph.nodes
        # No edges should reference the removed repo
        remaining_edges = simple_graph.get_edges_for_repo("backend")
        assert remaining_edges == []

    def test_build_order_then_add_node_invalidates_analyzed(
        self, simple_graph: MultiRepoDependencyGraph, tmp_path: Path
    ):
        """After computing build order, adding a new repo resets analyzed to False."""
        # Manually set analyzed to True (simulating a previous analyze() call)
        simple_graph.analyzed = True
        simple_graph.add_repo("new-service", tmp_path / "new-service")

        assert simple_graph.analyzed is False

    def test_large_linear_chain_build_order(
        self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path
    ):
        """
        Build a linear chain: r0 → r1 → r2 → ... → r9
        The build order should go from r9 down to r0.
        """
        n = 10
        for i in range(n):
            empty_graph.add_repo(f"r{i}", tmp_path / f"r{i}")
        for i in range(n - 1):
            empty_graph.add_edge(f"r{i}", f"r{i + 1}")

        order = empty_graph.get_build_order()

        # r9 (leaf) should come first, r0 (root of chain) last
        assert order.index(f"r{n - 1}") < order.index("r0")

    def test_multiple_roots_no_cycle(
        self, empty_graph: MultiRepoDependencyGraph, tmp_path: Path
    ):
        """Multiple independent roots should all appear in build order without error."""
        for name in ("root1", "root2", "child"):
            empty_graph.add_repo(name, tmp_path / name)
        empty_graph.add_edge("root1", "child")
        empty_graph.add_edge("root2", "child")

        order = empty_graph.get_build_order()

        assert "child" in order
        assert order.index("child") < order.index("root1")
        assert order.index("child") < order.index("root2")
        assert empty_graph.has_cycle() is False

    def test_get_affected_repos_after_remove(
        self, simple_graph: MultiRepoDependencyGraph
    ):
        """After removing a dependent, it should no longer appear in affected repos."""
        simple_graph.remove_repo("frontend")
        affected = simple_graph.get_affected_repos("shared")

        assert "frontend" not in affected
        assert "backend" in affected
