"""Codebase intelligence integration plugin."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

    def augment_prompt(self, context: Any) -> str | None:
        """Attach compact graph context to agent prompts when enabled."""
        project_dir = Path(context.project_dir)
        sidecar_path = self._sidecar_path(project_dir)
        status_before = self._index_status(project_dir, sidecar_path)
        rebuilt = not bool(status_before.get("fresh"))
        if status_before["fresh"]:
            index = CodebaseIndex.load(sidecar_path)
            status_after = status_before
        else:
            index = CodebaseIndexer(project_dir).write_index(sidecar_path)
            status_after = self._index_status(project_dir, sidecar_path)
        summary = index.summary()
        phase = self._phase_name(context)
        briefing_files = self._metadata_files(context)
        reason = "attached compact graph summary to agent prompt"
        try:
            self._write_runtime_trace(
                context=context,
                summary=summary,
                status=status_after,
                reason=reason,
                rebuilt=rebuilt,
                briefing_files=briefing_files,
            )
        except Exception as exc:
            logger.warning(
                "codebase-intelligence: failed to persist runtime trace: %s",
                exc,
            )

        tool_guidance = (
            "Use the codebase-intelligence MCP tools when planning, editing, "
            + "or reviewing changes that touch imports, shared symbols, modules, "
            + "or tests:"
        )
        lines = [
            "# Codebase Intelligence Runtime Context",
            f"index_path: {self._relative_sidecar_path(project_dir)}",
            f"index_status: {status_after['status']}",
            f"mcp_server: {self.name}-integration",
            f"phase: {phase}",
            "summary:",
            f"- total_files: {summary['total_files']}",
            f"- total_symbols: {summary['total_symbols']}",
            f"- total_dependencies: {summary['total_dependencies']}",
            f"- total_references: {summary['total_references']}",
            f"- total_package_dependencies: {summary['total_package_dependencies']}",
            f"- languages: {', '.join(summary['languages']) or 'none'}",
        ]
        briefing = self._task_briefing(context, index, briefing_files)
        if briefing:
            lines.extend(["", briefing])
        lines.extend(
            [
                "",
                tool_guidance,
                "- get_codebase_summary and get_module_graph for orientation.",
                "- find_file_dependencies and find_file_dependents before edits.",
                "- find_symbol_callers and trace_symbol_impact for shared APIs.",
                "- trace_file_impact to choose affected implementation and test files.",
                self._phase_guidance(phase),
            ]
        )
        return "\n".join(lines)

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

        def get_index_status() -> str:
            """
            Report whether the codebase sidecar is missing, fresh, or stale.

            Does not rewrite the sidecar.
            """
            return json.dumps(
                self._index_status(context.project_dir, sidecar_path),
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

        def find_symbol_callers(
            symbol_name: str,
            kind: str | None = None,
            limit: int = 50,
        ) -> str:
            """
            Find resolved callers for a symbol definition.

            Args:
                symbol_name: Symbol or method name to inspect.
                kind: Optional symbol kind filter.
                limit: Maximum number of caller records to return.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            safe_limit = self._safe_int(limit, default=50, minimum=1, maximum=500)
            callers = index.find_symbol_callers(
                symbol_name=symbol_name,
                kind=kind,
                limit=safe_limit,
            )
            return json.dumps(callers, indent=2, sort_keys=True)

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

        def trace_symbol_impact(
            symbol_name: str,
            depth: int = 2,
            kind: str | None = None,
        ) -> str:
            """
            Trace direct callers and impacted files for a symbol definition.

            Args:
                symbol_name: Symbol or method name to inspect.
                depth: Reverse dependency traversal depth.
                kind: Optional symbol kind filter.
            """
            index = self._load_or_build_index(context.project_dir, sidecar_path)
            safe_depth = self._safe_int(depth, default=2, minimum=1, maximum=10)
            impact = index.trace_symbol_impact(
                symbol_name=symbol_name,
                depth=safe_depth,
                kind=kind,
            )
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
            find_symbol_callers,
            find_symbol_references,
            get_dependency_inventory,
            get_graph_neighbors,
            get_index_status,
            get_module_graph,
            get_codebase_summary,
            search_symbols,
            trace_file_impact,
            trace_symbol_impact,
        ]

    def is_available(self) -> bool:
        return self.is_enabled

    def _load_or_build_index(
        self, project_dir: Path, sidecar_path: Path
    ) -> CodebaseIndex:
        status = self._index_status(project_dir, sidecar_path)
        if status["fresh"]:
            return CodebaseIndex.load(sidecar_path)
        return CodebaseIndexer(project_dir).write_index(sidecar_path)

    def _index_status(self, project_dir: Path, sidecar_path: Path) -> dict:
        current_fingerprints = CodebaseIndexer(project_dir).build_source_fingerprints()
        if not sidecar_path.exists():
            return {
                "status": "missing",
                "fresh": False,
                "index_path": self._relative_sidecar_path(project_dir),
                "changed_files": [],
                "added_files": sorted(current_fingerprints),
                "removed_files": [],
            }

        stored_index = CodebaseIndex.load(sidecar_path)
        stored_fingerprints = stored_index.current_source_fingerprints()
        current_paths = set(current_fingerprints)
        stored_paths = set(stored_fingerprints)
        changed_files = sorted(
            path
            for path in current_paths & stored_paths
            if current_fingerprints[path] != stored_fingerprints[path]
        )
        added_files = sorted(current_paths - stored_paths)
        removed_files = sorted(stored_paths - current_paths)
        fresh = not changed_files and not added_files and not removed_files
        return {
            "status": "fresh" if fresh else "stale",
            "fresh": fresh,
            "index_path": self._relative_sidecar_path(project_dir),
            "changed_files": changed_files,
            "added_files": added_files,
            "removed_files": removed_files,
        }

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

    def _phase_name(self, context: Any) -> str:
        metadata = getattr(context, "metadata", {}) or {}
        return str(
            getattr(context, "phase", "")
            or metadata.get("agent_type")
            or metadata.get("phase")
            or "agent"
        )

    def _phase_guidance(self, phase: str) -> str:
        normalized = phase.casefold()
        if "planner" in normalized:
            return (
                "Planner guidance: inspect module graph and impact paths before "
                "splitting implementation subtasks."
            )
        if "qa" in normalized:
            return (
                "QA guidance: use impact traces to justify validation scope and "
                "identify targeted test candidates."
            )
        if "coder" in normalized or "fixer" in normalized:
            return (
                "Coder guidance: check dependents and symbol callers before editing "
                "shared files or APIs."
            )
        return (
            "Agent guidance: use graph queries to ground assumptions before changing "
            "or validating code."
        )

    def _write_runtime_trace(
        self,
        context: Any,
        summary: dict[str, Any],
        status: dict[str, Any],
        reason: str,
        rebuilt: bool,
        briefing_files: list[str],
    ) -> None:
        project_dir = Path(context.project_dir)
        trace_dir = project_dir / ".auto-claude" / "plugin_traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "plugin": self.name,
            "phase": self._phase_name(context),
            "reason": reason,
            "index_path": self._relative_sidecar_path(project_dir),
            "index_status": status.get("status"),
            "rebuilt_index": rebuilt,
            "briefing_files": briefing_files,
            "summary": summary,
        }
        with (trace_dir / "codebase-intelligence.jsonl").open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _metadata_files(self, context: Any) -> list[str]:
        metadata = getattr(context, "metadata", {}) or {}
        seen: set[str] = set()
        files: list[str] = []
        for key in ("files", "changed_files", "target_files"):
            value = metadata.get(key)
            if isinstance(value, str):
                candidates = [value]
            elif isinstance(value, (list, tuple, set)):
                candidates = [str(item) for item in value]
            else:
                candidates = []
            for candidate in candidates:
                normalized = self._normalize_project_path(candidate)
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    files.append(normalized)
        return files[:5]

    def _task_briefing(
        self,
        context: Any,
        index: CodebaseIndex,
        files: list[str],
    ) -> str:
        if not files:
            return ""

        metadata = getattr(context, "metadata", {}) or {}
        lines = ["## Task Briefing"]
        task = str(metadata.get("task") or "").strip()
        if task:
            lines.append(f"task: {task[:240]}")

        for file_path in files:
            code_file = index.files.get(file_path)
            lines.append(f"### {file_path}")
            if code_file is None:
                lines.append("- status: not indexed")
                continue

            dependencies = [
                dep.resolved_path for dep in code_file.dependencies if dep.resolved_path
            ][:5]
            dependents = index.reverse_dependencies.get(file_path, [])[:5]
            impact = index.trace_file_impact(file_path=file_path, depth=2)
            impacted_files = [
                item["file_path"]
                for item in impact.get("impacted_files", [])
                if isinstance(item, dict) and item.get("file_path") != file_path
            ][:8]
            tests = [str(path) for path in impact.get("test_candidates", [])][:5]

            lines.append(f"- dependencies: {_join_or_none(dependencies)}")
            lines.append(f"- dependents: {_join_or_none(dependents)}")
            lines.append(f"- impacted_files: {_join_or_none(impacted_files)}")
            lines.append(f"- test_candidates: {_join_or_none(tests)}")
        return "\n".join(lines)


def _join_or_none(values: list[str]) -> str:
    return ", ".join(values) if values else "none"
