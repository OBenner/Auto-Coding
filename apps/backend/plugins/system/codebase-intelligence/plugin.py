"""Codebase intelligence integration plugin."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import plugins.sdk.integration as integration_sdk
from codebase_intelligence import CodebaseIndex, CodebaseIndexer, GraphDataset

logger = logging.getLogger(__name__)


class CodebaseIntelligencePlugin(integration_sdk.IntegrationPlugin):
    """Integration plugin that exposes deterministic codebase graph tools."""

    def on_load(self) -> None:
        logger.info("codebase-intelligence: Plugin loaded")

    def on_enable(self) -> None:
        logger.info("codebase-intelligence: Plugin enabled")

    def on_disable(self) -> None:
        logger.info("codebase-intelligence: Plugin disabled")

    def on_unload(self) -> None:
        logger.info("codebase-intelligence: Plugin unloaded")

    def create_mcp_tools(self, context: integration_sdk.IntegrationContext) -> list:
        """Create codebase graph tools for agent sessions."""
        sidecar_path = self._sidecar_path(context.project_dir)

        def build_codebase_index() -> str:
            """
            Build or refresh the deterministic codebase graph for this project.

            Returns:
                JSON with the sidecar path and compact graph summary.
            """
            index = CodebaseIndexer(context.project_dir).write_index(sidecar_path)
            return json.dumps(
                {
                    "index_path": self._relative_sidecar_path(context.project_dir),
                    "summary": index.summary(),
                },
                indent=2,
                sort_keys=True,
            )

        def export_graph_dataset(format: str = "json") -> str:
            """
            Export the codebase graph as JSON or Kuzu-ready CSV artifacts.

            Args:
                format: Either json or kuzu_csv.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            dataset = GraphDataset.from_index(index)
            artifacts_dir = self._graph_artifacts_dir(context.project_dir)
            graph_json_path = artifacts_dir / "graph.json"
            dataset.write_json(graph_json_path)

            artifacts = {
                "graph_json": self._relative_path(
                    context.project_dir,
                    graph_json_path,
                )
            }
            normalized_format = format.casefold()
            if normalized_format == "kuzu_csv":
                csv_artifacts = dataset.write_kuzu_csv(artifacts_dir / "kuzu")
                artifacts.update(
                    {
                        key: self._relative_path(
                            context.project_dir,
                            artifacts_dir / "kuzu" / file_name,
                        )
                        for key, file_name in csv_artifacts.items()
                    }
                )

            return json.dumps(
                {
                    "format": normalized_format,
                    "artifacts": artifacts,
                    "summary": dataset.summary(),
                },
                indent=2,
                sort_keys=True,
            )

        def get_codebase_summary() -> str:
            """
            Return a compact summary of the current codebase graph.

            Builds the sidecar first when no index has been written yet.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            return json.dumps(
                {
                    "index_path": self._relative_sidecar_path(context.project_dir),
                    "summary": index.summary(),
                },
                indent=2,
                sort_keys=True,
            )

        def find_file_dependents(file_path: str) -> str:
            """
            Find files that depend on a project file.

            Args:
                file_path: Project-relative file path to inspect.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            normalized = self._normalize_project_path(file_path)
            return json.dumps(
                {
                    "file_path": normalized,
                    "dependents": index.reverse_dependencies.get(normalized, []),
                },
                indent=2,
                sort_keys=True,
            )

        def find_file_dependencies(
            file_path: str,
            include_external: bool = False,
        ) -> str:
            """
            Find files or modules imported by a project file.

            Args:
                file_path: Project-relative file path to inspect.
                include_external: Include unresolved external imports when true.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            normalized = self._normalize_project_path(file_path)
            code_file = index.files.get(normalized)
            dependencies = []
            if code_file:
                dependencies = [
                    dep.to_dict()
                    for dep in code_file.dependencies
                    if include_external or dep.resolved_path
                ]
            return json.dumps(
                {
                    "file_path": normalized,
                    "dependencies": dependencies,
                },
                indent=2,
                sort_keys=True,
            )

        def search_symbols(
            query: str,
            kind: str | None = None,
            limit: int = 20,
        ) -> str:
            """
            Search code symbols by name, path, signature, or docstring.

            Args:
                query: Case-insensitive search term.
                kind: Optional symbol kind filter.
                limit: Maximum number of matches to return.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            safe_limit = self._safe_int(limit, default=20, minimum=1, maximum=200)
            matches = index.search_symbols(query=query, kind=kind, limit=safe_limit)
            return json.dumps(
                {
                    "query": query,
                    "kind": kind,
                    "matches": [symbol.to_dict() for symbol in matches],
                },
                indent=2,
                sort_keys=True,
            )

        def find_symbol_references(
            symbol_name: str,
            kind: str | None = None,
            limit: int = 50,
        ) -> str:
            """
            Find lightweight references to a symbol or call target.

            Args:
                symbol_name: Symbol or call name to find.
                kind: Optional reference kind filter.
                limit: Maximum number of matches to return.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            safe_limit = self._safe_int(limit, default=50, minimum=1, maximum=500)
            references = index.find_symbol_references(
                symbol_name=symbol_name,
                kind=kind,
                limit=safe_limit,
            )
            return json.dumps(
                {
                    "symbol_name": symbol_name,
                    "kind": kind,
                    "references": [reference.to_dict() for reference in references],
                },
                indent=2,
                sort_keys=True,
            )

        def trace_file_impact(file_path: str, depth: int = 2) -> str:
            """
            Trace files impacted by changes to a project file.

            Args:
                file_path: Project-relative file path to inspect.
                depth: Reverse dependency traversal depth.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            safe_depth = self._safe_int(depth, default=2, minimum=1, maximum=10)
            impact = index.trace_file_impact(file_path=file_path, depth=safe_depth)
            return json.dumps(impact, indent=2, sort_keys=True)

        def get_dependency_inventory(ecosystem: str | None = None) -> str:
            """
            Return package dependencies discovered from project manifests.

            Args:
                ecosystem: Optional package ecosystem filter, such as npm or python.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            dependencies = index.get_dependency_inventory(ecosystem=ecosystem)
            return json.dumps(
                {
                    "ecosystem": ecosystem,
                    "total_dependencies": len(dependencies),
                    "dependencies": [
                        dependency.to_dict() for dependency in dependencies
                    ],
                },
                indent=2,
                sort_keys=True,
            )

        def get_module_graph(depth: int = 2) -> str:
            """
            Return a directory-level module dependency graph.

            Args:
                depth: Directory depth used to group files into modules.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            safe_depth = self._safe_int(depth, default=2, minimum=1, maximum=6)
            return json.dumps(
                index.get_module_graph(depth=safe_depth),
                indent=2,
                sort_keys=True,
            )

        def get_graph_neighbors(
            node_id: str,
            direction: str = "both",
            edge_kind: str | None = None,
            limit: int = 50,
        ) -> str:
            """
            Return neighboring graph nodes for a node id.

            Args:
                node_id: Graph node id, such as file:path/to/file.py.
                direction: in, out, or both.
                edge_kind: Optional edge kind filter.
                limit: Maximum number of neighbors to return.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            dataset = GraphDataset.from_index(index)
            safe_limit = self._safe_int(limit, default=50, minimum=1, maximum=500)
            return json.dumps(
                {
                    "node_id": node_id,
                    "direction": direction,
                    "edge_kind": edge_kind,
                    "neighbors": dataset.neighbors(
                        node_id=node_id,
                        direction=direction,
                        edge_kind=edge_kind,
                        limit=safe_limit,
                    ),
                },
                indent=2,
                sort_keys=True,
            )

        return [
            build_codebase_index,
            export_graph_dataset,
            find_file_dependencies,
            find_file_dependents,
            find_symbol_references,
            get_dependency_inventory,
            get_graph_neighbors,
            get_module_graph,
            get_codebase_summary,
            search_symbols,
            trace_file_impact,
        ]

    def is_available(self) -> bool:
        return self.is_enabled

    def _load_or_build_index(self, project_dir: Path, sidecar_path: Path) -> CodebaseIndex:
        if sidecar_path.exists():
            return CodebaseIndex.load(sidecar_path)
        return CodebaseIndexer(project_dir).write_index(sidecar_path)

    def _sidecar_path(self, project_dir: Path) -> Path:
        return project_dir / ".auto-claude" / "codebase_intelligence" / "index.json"

    def _relative_sidecar_path(self, project_dir: Path) -> str:
        return self._sidecar_path(project_dir).relative_to(project_dir).as_posix()

    def _graph_artifacts_dir(self, project_dir: Path) -> Path:
        return project_dir / ".auto-claude" / "codebase_intelligence" / "graph"

    def _relative_path(self, project_dir: Path, path: Path) -> str:
        return path.relative_to(project_dir).as_posix()

    def _normalize_project_path(self, file_path: str) -> str:
        return file_path.replace("\\", "/").lstrip("./")

    def _safe_int(
        self,
        value: int,
        default: int,
        minimum: int,
        maximum: int,
    ) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return max(minimum, min(parsed, maximum))
