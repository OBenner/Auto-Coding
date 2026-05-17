"""Graph dataset export helpers for codebase intelligence."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import CodebaseIndex


@dataclass(frozen=True)
class GraphNode:
    """A graph node suitable for JSON export or graph database import."""

    id: str
    kind: str
    label: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "properties": self.properties,
        }

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
        }


@dataclass(frozen=True)
class GraphEdge:
    """A directed graph edge between graph nodes."""

    source: str
    target: str
    kind: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "properties": self.properties,
        }

    def to_summary_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
        }


@dataclass
class GraphDataset:
    """A deterministic nodes/edges projection of a codebase index."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]

    @classmethod
    def from_index(cls, index: CodebaseIndex) -> GraphDataset:
        nodes: dict[str, GraphNode] = {}
        edges: dict[tuple[str, str, str], GraphEdge] = {}
        symbol_lookup = index.build_symbol_lookup()

        def add_node(node: GraphNode) -> None:
            nodes.setdefault(node.id, node)

        def add_edge(edge: GraphEdge) -> None:
            edges.setdefault((edge.source, edge.target, edge.kind), edge)

        root_id = "project:root"
        add_node(
            GraphNode(
                id=root_id,
                kind="project",
                label=Path(index.project_root).name,
                properties={"project_root": index.project_root},
            )
        )

        for package in index.get_dependency_inventory():
            package_id = _package_id(package.ecosystem, package.name)
            add_node(
                GraphNode(
                    id=package_id,
                    kind="package",
                    label=package.name,
                    properties=package.to_dict(),
                )
            )
            manifest_id = _file_id(package.source_path)
            add_node(
                GraphNode(
                    id=manifest_id,
                    kind="file",
                    label=Path(package.source_path).name,
                    properties={
                        "path": package.source_path,
                        "language": "manifest",
                    },
                )
            )
            add_edge(
                GraphEdge(
                    source=manifest_id,
                    target=package_id,
                    kind="declares_dependency",
                    properties={
                        "ecosystem": package.ecosystem,
                        "dependency_type": package.dependency_type,
                    },
                )
            )

        for code_file in index.files.values():
            file_id = _file_id(code_file.path)
            add_node(
                GraphNode(
                    id=file_id,
                    kind="file",
                    label=Path(code_file.path).name,
                    properties={
                        "path": code_file.path,
                        "language": code_file.language,
                        "sha256": code_file.sha256,
                    },
                )
            )
            add_edge(GraphEdge(source=root_id, target=file_id, kind="contains"))

            module_id = _module_id(_module_for_file(code_file.path, depth=3))
            add_node(
                GraphNode(
                    id=module_id,
                    kind="module",
                    label=module_id.removeprefix("module:"),
                    properties={
                        "path": module_id.removeprefix("module:"),
                    },
                )
            )
            add_edge(GraphEdge(source=module_id, target=file_id, kind="contains"))

            for symbol in code_file.symbols:
                add_node(
                    GraphNode(
                        id=symbol.id,
                        kind="symbol",
                        label=symbol.name,
                        properties=symbol.to_dict(),
                    )
                )
                add_edge(GraphEdge(source=file_id, target=symbol.id, kind="defines"))

            for dependency in code_file.dependencies:
                if not dependency.resolved_path:
                    continue
                add_edge(
                    GraphEdge(
                        source=file_id,
                        target=_file_id(dependency.resolved_path),
                        kind="imports",
                        properties={
                            "line": dependency.line,
                            "target": dependency.target,
                        },
                    )
                )

            for reference in code_file.references:
                target_symbol = index.resolve_reference_target_symbol(
                    reference,
                    symbol_lookup=symbol_lookup,
                )
                if target_symbol:
                    add_edge(
                        GraphEdge(
                            source=file_id,
                            target=target_symbol.id,
                            kind="references",
                            properties=reference.to_dict(),
                        )
                    )
                    caller_symbol = index.find_reference_caller_symbol(reference)
                    if caller_symbol:
                        add_edge(
                            GraphEdge(
                                source=caller_symbol.id,
                                target=target_symbol.id,
                                kind="calls",
                                properties=reference.to_dict(),
                            )
                        )

        return cls(
            nodes=sorted(nodes.values(), key=lambda node: node.id),
            edges=sorted(
                edges.values(),
                key=lambda edge: (edge.source, edge.target, edge.kind),
            ),
        )

    def summary(self) -> dict[str, Any]:
        node_kinds: dict[str, int] = {}
        edge_kinds: dict[str, int] = {}
        for node in self.nodes:
            node_kinds[node.kind] = node_kinds.get(node.kind, 0) + 1
        for edge in self.edges:
            edge_kinds[edge.kind] = edge_kinds.get(edge.kind, 0) + 1
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "node_kinds": dict(sorted(node_kinds.items())),
            "edge_kinds": dict(sorted(edge_kinds.items())),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def write_json(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def write_kuzu_csv(self, output_dir: Path) -> dict[str, str]:
        output_dir.mkdir(parents=True, exist_ok=True)
        nodes_csv = output_dir / "nodes.csv"
        edges_csv = output_dir / "edges.csv"
        schema_cypher = output_dir / "schema.cypher"

        with nodes_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["id", "kind", "label", "properties_json"],
            )
            writer.writeheader()
            for node in self.nodes:
                writer.writerow(
                    {
                        "id": node.id,
                        "kind": node.kind,
                        "label": node.label,
                        "properties_json": json.dumps(
                            node.properties,
                            sort_keys=True,
                        ),
                    }
                )

        with edges_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["source", "target", "kind", "properties_json"],
            )
            writer.writeheader()
            for edge in self.edges:
                writer.writerow(
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "kind": edge.kind,
                        "properties_json": json.dumps(
                            edge.properties,
                            sort_keys=True,
                        ),
                    }
                )

        schema_cypher.write_text(
            "\n".join(
                [
                    "CREATE NODE TABLE IF NOT EXISTS CodeNode(",
                    "  id STRING,",
                    "  kind STRING,",
                    "  label STRING,",
                    "  properties_json STRING,",
                    "  PRIMARY KEY (id)",
                    ");",
                    "CREATE REL TABLE IF NOT EXISTS CodeEdge(",
                    "  FROM CodeNode TO CodeNode,",
                    "  kind STRING,",
                    "  properties_json STRING",
                    ");",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "nodes_csv": nodes_csv.name,
            "edges_csv": edges_csv.name,
            "schema_cypher": schema_cypher.name,
        }

    def neighbors(
        self,
        node_id: str,
        direction: str = "both",
        edge_kind: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        node_lookup = {node.id: node for node in self.nodes}
        normalized_direction = (
            direction if direction in {"in", "out", "both"} else "both"
        )
        matches: list[dict[str, Any]] = []

        for edge in self.edges:
            if edge_kind and edge.kind != edge_kind:
                continue
            neighbor_id = ""
            if normalized_direction in {"out", "both"} and edge.source == node_id:
                neighbor_id = edge.target
            elif normalized_direction in {"in", "both"} and edge.target == node_id:
                neighbor_id = edge.source
            if not neighbor_id or neighbor_id not in node_lookup:
                continue
            matches.append(
                {
                    "edge": edge.to_summary_dict(),
                    "node": node_lookup[neighbor_id].to_summary_dict(),
                }
            )
        return sorted(
            matches,
            key=lambda item: (
                item["edge"]["kind"],
                item["node"]["id"],
                item["edge"]["source"],
                item["edge"]["target"],
            ),
        )[:limit]


def _file_id(path: str) -> str:
    return f"file:{path}"


def _module_id(path: str) -> str:
    return f"module:{path}"


def _package_id(ecosystem: str, name: str) -> str:
    return f"package:{ecosystem}:{name}"


def _module_for_file(file_path: str, depth: int) -> str:
    parent_parts = Path(file_path).parent.parts
    if not parent_parts:
        return "."
    return "/".join(parent_parts[: max(depth, 1)])
