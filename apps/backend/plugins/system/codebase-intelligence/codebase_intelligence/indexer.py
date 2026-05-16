"""Project-level codebase intelligence indexer."""

from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from .extractors import (
    SUPPORTED_EXTENSIONS,
    detect_language,
    extract_python_file,
    extract_typescript_file,
)
from .models import CodebaseIndex, CodeDependency, CodeFile
from .packages import discover_package_dependencies, discover_package_manifests

SKIP_DIRS = {
    ".auto-claude",
    ".auto-Code",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".venv-*",
    ".worktrees",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "out",
    "venv",
}
TYPESCRIPT_RESOLUTION_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")


class CodebaseIndexer:
    """Builds a deterministic source graph for agent context and impact analysis."""

    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir).resolve()

    def build_index(self) -> CodebaseIndex:
        """Build a codebase index for supported files under the project."""
        files = self._discover_files()
        python_module_map = self._build_python_module_map(files)
        code_files: dict[str, CodeFile] = {}

        for path in files:
            rel_path = self._relative(path)
            language = detect_language(path)
            if language is None:
                continue

            if language == "python":
                symbols, dependencies, references = extract_python_file(path, rel_path)
            else:
                symbols, dependencies, references = extract_typescript_file(path, rel_path)

            resolved_dependencies = [
                self._resolve_dependency(dep, path, python_module_map)
                for dep in dependencies
            ]
            code_files[rel_path] = CodeFile(
                path=rel_path,
                language=language,
                sha256=self._sha256(path),
                symbols=symbols,
                dependencies=resolved_dependencies,
                references=references,
            )

        reverse_dependencies = self._build_reverse_dependencies(code_files)
        return CodebaseIndex(
            project_root=str(self.project_dir),
            generated_at=datetime.now(UTC).isoformat(),
            files=code_files,
            reverse_dependencies=reverse_dependencies,
            package_dependencies=discover_package_dependencies(self.project_dir),
            source_fingerprints=self.build_source_fingerprints(files),
        )

    def build_source_fingerprints(
        self,
        files: Iterable[Path] | None = None,
    ) -> dict[str, str]:
        """Build cheap file fingerprints for source and package manifests."""
        source_files = list(files) if files is not None else self._discover_files()
        manifest_files = discover_package_manifests(self.project_dir)
        fingerprints: dict[str, str] = {}
        for path in [*source_files, *manifest_files]:
            fingerprints[self._relative(path)] = self._sha256(path)
        return dict(sorted(fingerprints.items()))

    def write_index(self, output_file: str | Path) -> CodebaseIndex:
        """Build and write the index to a stable JSON artifact."""
        output_path = Path(output_file)
        if not output_path.is_absolute():
            output_path = self.project_dir / output_path

        index = self.build_index()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(index.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return index

    def _discover_files(self) -> list[Path]:
        discovered: list[Path] = []
        for root, dirs, files in os.walk(self.project_dir):
            dirs[:] = [name for name in dirs if not self._should_skip_dir(name)]
            root_path = Path(root)
            for file_name in files:
                path = root_path / file_name
                if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    discovered.append(path)
        return sorted(discovered, key=lambda path: self._relative(path))

    def _should_skip_dir(self, name: str) -> bool:
        if name in SKIP_DIRS:
            return True
        return any(
            pattern.endswith("*") and name.startswith(pattern[:-1])
            for pattern in SKIP_DIRS
        )

    def _build_python_module_map(self, files: Iterable[Path]) -> dict[str, str]:
        candidates: dict[str, set[str]] = defaultdict(set)
        for path in files:
            if path.suffix.lower() != ".py":
                continue
            rel_path = self._relative(path)
            module_parts = list(Path(rel_path).with_suffix("").parts)
            if module_parts[-1] == "__init__":
                module_parts = module_parts[:-1]
            if not module_parts:
                continue

            for start in range(len(module_parts)):
                alias = ".".join(module_parts[start:])
                if alias:
                    candidates[alias].add(rel_path)

        return {
            alias: next(iter(paths))
            for alias, paths in candidates.items()
            if len(paths) == 1
        }

    def _resolve_dependency(
        self,
        dependency: CodeDependency,
        source_file: Path,
        python_module_map: dict[str, str],
    ) -> CodeDependency:
        if dependency.kind == "python_import":
            resolved_path = self._resolve_python_dependency(
                dependency, source_file, python_module_map
            )
        elif dependency.kind == "typescript_import":
            resolved_path = self._resolve_typescript_dependency(
                dependency.target, source_file
            )
        else:
            resolved_path = None

        return CodeDependency(
            source_path=dependency.source_path,
            target=dependency.target,
            kind=dependency.kind,
            line=dependency.line,
            imported_names=dependency.imported_names,
            resolved_path=resolved_path,
            metadata=dependency.metadata,
        )

    def _resolve_python_dependency(
        self,
        dependency: CodeDependency,
        source_file: Path,
        python_module_map: dict[str, str],
    ) -> str | None:
        target = dependency.target
        metadata = dependency.metadata
        if metadata.get("is_relative"):
            target = self._resolve_relative_python_module(
                source_file=source_file,
                module=target,
                level=int(metadata.get("level", 0) or 0),
            )

        candidates = [target] if target else []
        candidates.extend(
            f"{target}.{name}" for name in dependency.imported_names if target
        )
        candidates.extend(name for name in dependency.imported_names if not target)

        for candidate in candidates:
            resolved = python_module_map.get(candidate)
            if resolved:
                return resolved
        return None

    def _resolve_relative_python_module(
        self,
        source_file: Path,
        module: str,
        level: int,
    ) -> str:
        rel_path = Path(self._relative(source_file))
        source_parts = list(rel_path.with_suffix("").parts)
        if source_parts and source_parts[-1] != "__init__":
            source_parts = source_parts[:-1]

        keep_count = max(len(source_parts) - max(level - 1, 0), 0)
        base_parts = source_parts[:keep_count]
        if module:
            base_parts.extend(part for part in module.split(".") if part)
        return ".".join(base_parts)

    def _resolve_typescript_dependency(
        self, target: str, source_file: Path
    ) -> str | None:
        if not target.startswith("."):
            return None

        base = (source_file.parent / target).resolve()
        candidates = [base]
        candidates.extend(
            base.with_suffix(ext) for ext in TYPESCRIPT_RESOLUTION_EXTENSIONS
        )
        candidates.extend(
            base / f"index{ext}" for ext in TYPESCRIPT_RESOLUTION_EXTENSIONS
        )

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return self._relative(candidate)
        return None

    def _build_reverse_dependencies(
        self, files: dict[str, CodeFile]
    ) -> dict[str, list[str]]:
        reverse: dict[str, set[str]] = defaultdict(set)
        for source_path, code_file in files.items():
            for dependency in code_file.dependencies:
                if dependency.resolved_path and dependency.resolved_path in files:
                    reverse[dependency.resolved_path].add(source_path)
        return {
            target: sorted(dependents) for target, dependents in sorted(reverse.items())
        }

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.project_dir).as_posix()

    def _sha256(self, path: Path) -> str:
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return ""
