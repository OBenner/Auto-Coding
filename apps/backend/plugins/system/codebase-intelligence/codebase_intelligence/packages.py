"""Package manifest scanners for codebase intelligence."""

from __future__ import annotations

import json
import os
import re
import tomllib
from pathlib import Path
from typing import Any

from .models import PackageDependency

PACKAGE_MANIFEST_NAMES = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
}
SKIP_DIRS = {
    ".auto-claude",
    ".auto-Code",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    ".worktrees",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "out",
    "venv",
}

_REQUIREMENT_NAME_RE = re.compile(
    r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(.*)$"
)


def discover_package_dependencies(project_dir: Path) -> list[PackageDependency]:
    """Read supported package manifests under a project."""
    dependencies: list[PackageDependency] = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [name for name in dirs if not _should_skip_dir(name)]
        for file_name in sorted(files):
            path = Path(root) / file_name
            if not _is_supported_manifest(path):
                continue
            rel_path = path.relative_to(project_dir).as_posix()
            dependencies.extend(_read_manifest(path, rel_path))
    return sorted(
        dependencies,
        key=lambda dep: (
            dep.ecosystem,
            dep.source_path,
            dep.dependency_type,
            dep.name,
        ),
    )


def _is_supported_manifest(path: Path) -> bool:
    name = path.name
    return name in PACKAGE_MANIFEST_NAMES or (
        name.startswith("requirements") and name.endswith(".txt")
    )


def _should_skip_dir(name: str) -> bool:
    if name in SKIP_DIRS:
        return True
    return any(
        pattern.endswith("*") and name.startswith(pattern[:-1])
        for pattern in SKIP_DIRS
    )


def _read_manifest(path: Path, rel_path: str) -> list[PackageDependency]:
    if path.name == "package.json":
        return _read_package_json(path, rel_path)
    if path.name == "pyproject.toml":
        return _read_pyproject(path, rel_path)
    if path.name.startswith("requirements") and path.name.endswith(".txt"):
        return _read_requirements(path, rel_path)
    return []


def _read_package_json(path: Path, rel_path: str) -> list[PackageDependency]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []

    dependencies: list[PackageDependency] = []
    for section in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        values = data.get(section)
        if not isinstance(values, dict):
            continue
        for name, specifier in sorted(values.items()):
            dependencies.append(
                PackageDependency(
                    name=str(name),
                    ecosystem="npm",
                    source_path=rel_path,
                    dependency_type=section,
                    specifier=str(specifier),
                )
            )
    return dependencies


def _read_pyproject(path: Path, rel_path: str) -> list[PackageDependency]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):
        return []

    dependencies: list[PackageDependency] = []
    project = data.get("project", {})
    dependencies.extend(
        _python_dependencies_from_values(
            project.get("dependencies", []),
            rel_path,
            "project.dependencies",
        )
    )

    optional_dependencies = project.get("optional-dependencies", {})
    if isinstance(optional_dependencies, dict):
        for group, values in sorted(optional_dependencies.items()):
            dependencies.extend(
                _python_dependencies_from_values(
                    values,
                    rel_path,
                    f"project.optional-dependencies.{group}",
                )
            )

    poetry_dependencies = (
        data.get("tool", {})
        .get("poetry", {})
        .get("dependencies", {})
    )
    if isinstance(poetry_dependencies, dict):
        for name, specifier in sorted(poetry_dependencies.items()):
            if name.lower() == "python":
                continue
            dependencies.append(
                PackageDependency(
                    name=str(name),
                    ecosystem="python",
                    source_path=rel_path,
                    dependency_type="tool.poetry.dependencies",
                    specifier=_poetry_specifier(specifier),
                )
            )
    return dependencies


def _read_requirements(path: Path, rel_path: str) -> list[PackageDependency]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []

    dependencies: list[PackageDependency] = []
    for line in lines:
        requirement = line.split("#", 1)[0].strip()
        if not requirement or requirement.startswith(("-", "--")):
            continue
        dependency = _parse_python_requirement(
            requirement,
            rel_path,
            "requirements",
        )
        if dependency:
            dependencies.append(dependency)
    return dependencies


def _python_dependencies_from_values(
    values: Any,
    rel_path: str,
    dependency_type: str,
) -> list[PackageDependency]:
    if not isinstance(values, list):
        return []
    dependencies: list[PackageDependency] = []
    for value in values:
        dependency = _parse_python_requirement(str(value), rel_path, dependency_type)
        if dependency:
            dependencies.append(dependency)
    return dependencies


def _parse_python_requirement(
    requirement: str,
    rel_path: str,
    dependency_type: str,
) -> PackageDependency | None:
    match = _REQUIREMENT_NAME_RE.match(requirement)
    if not match:
        return None
    name = match.group(1)
    specifier = match.group(2).strip()
    return PackageDependency(
        name=name,
        ecosystem="python",
        source_path=rel_path,
        dependency_type=dependency_type,
        specifier=specifier,
    )


def _poetry_specifier(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)
