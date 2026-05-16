"""Data models for the deterministic codebase intelligence graph."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CodeSymbol:
    """A code entity discovered in a source file."""

    name: str
    kind: str
    file_path: str
    line: int
    language: str
    end_line: int | None = None
    container: str | None = None
    signature: str = ""
    docstring: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodeSymbol:
        return cls(
            name=data["name"],
            kind=data["kind"],
            file_path=data["file_path"],
            line=int(data["line"]),
            language=data["language"],
            end_line=data.get("end_line"),
            container=data.get("container"),
            signature=data.get("signature", ""),
            docstring=data.get("docstring"),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind,
            "file_path": self.file_path,
            "line": self.line,
            "language": self.language,
        }
        if self.end_line is not None:
            data["end_line"] = self.end_line
        if self.container:
            data["container"] = self.container
        if self.signature:
            data["signature"] = self.signature
        if self.docstring:
            data["docstring"] = self.docstring
        return data


@dataclass
class CodeDependency:
    """A dependency edge from one source file to another target."""

    source_path: str
    target: str
    kind: str
    line: int
    imported_names: list[str] = field(default_factory=list)
    resolved_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodeDependency:
        return cls(
            source_path=data["source_path"],
            target=data["target"],
            kind=data["kind"],
            line=int(data["line"]),
            imported_names=list(data.get("imported_names", [])),
            resolved_path=data.get("resolved_path"),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "source_path": self.source_path,
            "target": self.target,
            "kind": self.kind,
            "line": self.line,
            "imported_names": sorted(self.imported_names),
        }
        if self.resolved_path:
            data["resolved_path"] = self.resolved_path
        if self.metadata:
            data["metadata"] = self.metadata
        return data


@dataclass
class CodeReference:
    """A lightweight reference discovered inside executable code."""

    name: str
    kind: str
    file_path: str
    line: int
    container: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodeReference:
        return cls(
            name=data["name"],
            kind=data["kind"],
            file_path=data["file_path"],
            line=int(data["line"]),
            container=data.get("container"),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "file_path": self.file_path,
            "line": self.line,
            "kind": self.kind,
            "name": self.name,
        }
        if self.container:
            data["container"] = self.container
        return data


@dataclass
class PackageDependency:
    """A package-manager dependency declared by the project."""

    name: str
    ecosystem: str
    source_path: str
    dependency_type: str
    specifier: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PackageDependency:
        return cls(
            name=data["name"],
            ecosystem=data["ecosystem"],
            source_path=data["source_path"],
            dependency_type=data["dependency_type"],
            specifier=data.get("specifier", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "ecosystem": self.ecosystem,
            "source_path": self.source_path,
            "dependency_type": self.dependency_type,
        }
        if self.specifier:
            data["specifier"] = self.specifier
        return data


@dataclass
class CodeFile:
    """A source file and the graph facts extracted from it."""

    path: str
    language: str
    sha256: str
    symbols: list[CodeSymbol] = field(default_factory=list)
    dependencies: list[CodeDependency] = field(default_factory=list)
    references: list[CodeReference] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodeFile:
        return cls(
            path=data["path"],
            language=data["language"],
            sha256=data["sha256"],
            symbols=[
                CodeSymbol.from_dict(symbol) for symbol in data.get("symbols", [])
            ],
            dependencies=[
                CodeDependency.from_dict(dep)
                for dep in data.get("dependencies", [])
            ],
            references=[
                CodeReference.from_dict(ref)
                for ref in data.get("references", [])
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "language": self.language,
            "sha256": self.sha256,
            "symbols": [symbol.to_dict() for symbol in self.symbols],
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "references": [ref.to_dict() for ref in self.references],
        }


@dataclass
class CodebaseIndex:
    """A deterministic graph snapshot for a project."""

    project_root: str
    generated_at: str
    files: dict[str, CodeFile] = field(default_factory=dict)
    reverse_dependencies: dict[str, list[str]] = field(default_factory=dict)
    package_dependencies: list[PackageDependency] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CodebaseIndex:
        return cls(
            project_root=data["project_root"],
            generated_at=data["generated_at"],
            files={
                path: CodeFile.from_dict(file_data)
                for path, file_data in data.get("files", {}).items()
            },
            reverse_dependencies={
                path: list(dependents)
                for path, dependents in data.get("reverse_dependencies", {}).items()
            },
            package_dependencies=[
                PackageDependency.from_dict(dep)
                for dep in data.get("package_dependencies", [])
            ],
        )

    @classmethod
    def load(cls, path: str | Path) -> CodebaseIndex:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def summary(self) -> dict[str, Any]:
        languages = sorted({code_file.language for code_file in self.files.values()})
        total_symbols = sum(len(code_file.symbols) for code_file in self.files.values())
        total_dependencies = sum(
            1
            for code_file in self.files.values()
            for dep in code_file.dependencies
            if dep.resolved_path
        )
        total_references = sum(
            len(code_file.references) for code_file in self.files.values()
        )
        return {
            "available": True,
            "total_files": len(self.files),
            "total_symbols": total_symbols,
            "total_dependencies": total_dependencies,
            "total_references": total_references,
            "total_package_dependencies": len(self.package_dependencies),
            "languages": languages,
        }

    def search_symbols(
        self,
        query: str,
        kind: str | None = None,
        limit: int = 20,
    ) -> list[CodeSymbol]:
        needle = query.casefold()
        matches: list[CodeSymbol] = []
        for code_file in self.files.values():
            for symbol in code_file.symbols:
                if kind and symbol.kind != kind:
                    continue
                haystack = " ".join(
                    [
                        symbol.name,
                        symbol.file_path,
                        symbol.signature,
                        symbol.docstring or "",
                    ]
                ).casefold()
                if needle in haystack:
                    matches.append(symbol)
        return sorted(matches, key=lambda s: (s.file_path, s.line, s.name))[:limit]

    def find_symbol_references(
        self,
        symbol_name: str,
        kind: str | None = None,
        limit: int = 50,
    ) -> list[CodeReference]:
        needle = symbol_name.casefold()
        matches: list[CodeReference] = []
        for code_file in self.files.values():
            for reference in code_file.references:
                if kind and reference.kind != kind:
                    continue
                names = {reference.name.casefold()}
                names.add(reference.name.rsplit(".", 1)[-1].casefold())
                if needle in names:
                    matches.append(reference)
        return sorted(matches, key=lambda ref: (ref.file_path, ref.line, ref.name))[
            :limit
        ]

    def trace_file_impact(self, file_path: str, depth: int = 2) -> dict[str, Any]:
        normalized = file_path.replace("\\", "/").lstrip("./")
        visited = {normalized}
        frontier = [(normalized, 0)]
        impacted: list[dict[str, Any]] = []

        while frontier:
            current, distance = frontier.pop(0)
            if distance >= depth:
                continue
            for dependent in self.reverse_dependencies.get(current, []):
                if dependent in visited:
                    continue
                visited.add(dependent)
                next_distance = distance + 1
                impacted.append(
                    {
                        "file_path": dependent,
                        "distance": next_distance,
                        "is_test": self._is_test_file(dependent),
                    }
                )
                frontier.append((dependent, next_distance))

        impacted = sorted(
            impacted,
            key=lambda item: (item["distance"], item["file_path"]),
        )
        return {
            "file_path": normalized,
            "depth": depth,
            "impacted_files": impacted,
            "test_candidates": [
                item["file_path"] for item in impacted if item["is_test"]
            ],
        }

    def get_dependency_inventory(
        self,
        ecosystem: str | None = None,
    ) -> list[PackageDependency]:
        dependencies = self.package_dependencies
        if ecosystem:
            dependencies = [
                dep for dep in dependencies if dep.ecosystem == ecosystem
            ]
        return sorted(
            dependencies,
            key=lambda dep: (
                dep.ecosystem,
                dep.source_path,
                dep.dependency_type,
                dep.name,
            ),
        )

    def get_module_graph(self, depth: int = 2) -> dict[str, Any]:
        modules: dict[str, dict[str, Any]] = {}
        edges: dict[tuple[str, str], int] = {}

        for code_file in self.files.values():
            module_path = self._module_for_file(code_file.path, depth)
            module = modules.setdefault(
                module_path,
                {
                    "path": module_path,
                    "total_files": 0,
                    "total_symbols": 0,
                    "languages": set(),
                },
            )
            module["total_files"] += 1
            module["total_symbols"] += len(code_file.symbols)
            module["languages"].add(code_file.language)

            for dependency in code_file.dependencies:
                if not dependency.resolved_path:
                    continue
                target_module = self._module_for_file(dependency.resolved_path, depth)
                if module_path == target_module:
                    continue
                edge_key = (module_path, target_module)
                edges[edge_key] = edges.get(edge_key, 0) + 1

        return {
            "depth": depth,
            "modules": [
                {
                    **module,
                    "languages": sorted(module["languages"]),
                }
                for module in sorted(modules.values(), key=lambda item: item["path"])
            ],
            "edges": [
                {"source": source, "target": target, "weight": weight}
                for (source, target), weight in sorted(edges.items())
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_root": self.project_root,
            "generated_at": self.generated_at,
            "summary": self.summary(),
            "files": {
                path: self.files[path].to_dict() for path in sorted(self.files.keys())
            },
            "reverse_dependencies": {
                path: sorted(dependents)
                for path, dependents in sorted(self.reverse_dependencies.items())
            },
            "package_dependencies": [
                dep.to_dict() for dep in self.get_dependency_inventory()
            ],
        }

    def _module_for_file(self, file_path: str, depth: int) -> str:
        parent_parts = Path(file_path).parent.parts
        if not parent_parts:
            return "."
        return "/".join(parent_parts[: max(depth, 1)])

    def _is_test_file(self, file_path: str) -> bool:
        path = file_path.replace("\\", "/").casefold()
        file_name = Path(path).name
        return (
            path.startswith("tests/")
            or "/tests/" in path
            or file_name.startswith("test_")
            or file_name.endswith("_test.py")
            or ".test." in file_name
            or ".spec." in file_name
        )
