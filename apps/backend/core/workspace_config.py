"""
Workspace Configuration
========================

Enables managing multiple related codebases (monorepos, microservices, libraries)
from a single Auto Claude instance with:
- Multi-project configuration and state isolation
- Cross-project dependency tracking
- Coordinated operations across repositories
- Per-project worktree management

Usage:
    # Configure a workspace with multiple projects
    config = WorkspaceConfig(
        name="my-workspace",
        projects=[
            ProjectConfig(name="frontend", path="/path/to/frontend"),
            ProjectConfig(name="backend", path="/path/to/backend"),
            ProjectConfig(name="shared", path="/path/to/shared"),
        ]
    )

    # Get project by name
    project = config.get_project("frontend")

    # Check if path belongs to a project
    project = config.find_project_by_path("/path/to/frontend/src/App.tsx")
"""

from __future__ import annotations

import json
import os
import tempfile
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ProjectRelationship(str, Enum):
    """Relationship between projects in a workspace."""

    INDEPENDENT = "independent"  # No dependencies
    DEPENDS_ON = "depends_on"  # Depends on other projects
    LIBRARY = "library"  # Shared library used by others
    MONOREPO_PACKAGE = "monorepo_package"  # Package in a monorepo


@dataclass
class ProjectConfig:
    """
    Configuration for a single project in a workspace.

    Attributes:
        name: Human-readable project name
        path: Absolute path to project directory
        enabled: Whether this project is active in the workspace
        relationship: Relationship to other projects
        dependencies: List of project names this depends on
        description: Optional description of the project
        tags: Optional tags for categorization
    """

    name: str
    path: str  # Absolute path
    enabled: bool = True
    relationship: ProjectRelationship = ProjectRelationship.INDEPENDENT
    dependencies: list[str] = field(default_factory=list)
    description: str | None = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate and normalize project configuration."""
        # Convert path to absolute Path object
        self.path = str(Path(self.path).resolve())

    @property
    def state_key(self) -> str:
        """
        Get unique key for state isolation.

        Returns safe directory name for this project.
        """
        import re

        return re.sub(r"[^\w-]", "_", self.name.lower())

    @property
    def path_obj(self) -> Path:
        """Get path as Path object."""
        return Path(self.path)

    def is_path_in_project(self, file_path: str | Path) -> bool:
        """
        Check if a file path belongs to this project.

        Args:
            file_path: File path to check

        Returns:
            True if path is within project directory
        """
        try:
            file_path_obj = Path(file_path).resolve()
            project_path_obj = Path(self.path).resolve()
            return file_path_obj.is_relative_to(project_path_obj)
        except (ValueError, OSError):
            return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "path": self.path,
            "enabled": self.enabled,
            "relationship": self.relationship.value,
            "dependencies": self.dependencies,
            "description": self.description,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectConfig:
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            path=data["path"],
            enabled=data.get("enabled", True),
            relationship=ProjectRelationship(data.get("relationship", "independent")),
            dependencies=data.get("dependencies", []),
            description=data.get("description"),
            tags=data.get("tags", []),
        )


@dataclass
class WorkspaceConfig:
    """
    Configuration for a multi-project workspace.

    Manages multiple related codebases with dependency tracking,
    state isolation, and coordinated operations.

    Attributes:
        name: Workspace name
        projects: List of project configurations
        description: Optional workspace description
        base_dir: Base directory for workspace state (auto-generated if None)
        created_at: Timestamp of workspace creation
        updated_at: Timestamp of last update
    """

    name: str
    projects: list[ProjectConfig] = field(default_factory=list)
    description: str | None = None
    base_dir: Path | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self):
        """Initialize workspace state."""
        now = datetime.now(UTC).isoformat()

        if self.created_at is None:
            self.created_at = now

        if self.updated_at is None:
            self.updated_at = now

        # Validate project names are unique
        names = [p.name for p in self.projects]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate project names: {duplicates}")

        # Validate dependencies reference existing projects
        for project in self.projects:
            for dep in project.dependencies:
                if dep not in names:
                    raise ValueError(
                        f"Project '{project.name}' depends on unknown project '{dep}'"
                    )

    @property
    def project_count(self) -> int:
        """Get total number of projects."""
        return len(self.projects)

    @property
    def enabled_projects(self) -> list[ProjectConfig]:
        """Get list of enabled projects."""
        return [p for p in self.projects if p.enabled]

    def get_project(self, name: str) -> ProjectConfig | None:
        """
        Get project by name.

        Args:
            name: Project name

        Returns:
            ProjectConfig or None if not found
        """
        for project in self.projects:
            if project.name == name:
                return project
        return None

    def find_project_by_path(self, file_path: str | Path) -> ProjectConfig | None:
        """
        Find which project a file path belongs to.

        Args:
            file_path: File path to check

        Returns:
            ProjectConfig or None if not found
        """
        for project in self.enabled_projects:
            if project.is_path_in_project(file_path):
                return project
        return None

    def get_dependencies(self, project_name: str) -> list[ProjectConfig]:
        """
        Get all projects that a project depends on.

        Args:
            project_name: Name of project to get dependencies for

        Returns:
            List of ProjectConfig dependencies
        """
        project = self.get_project(project_name)
        if not project:
            return []

        deps = []
        for dep_name in project.dependencies:
            dep_project = self.get_project(dep_name)
            if dep_project:
                deps.append(dep_project)

        return deps

    def get_dependents(self, project_name: str) -> list[ProjectConfig]:
        """
        Get all projects that depend on a project.

        Args:
            project_name: Name of project to get dependents for

        Returns:
            List of ProjectConfig dependents
        """
        dependents = []
        for project in self.projects:
            if project_name in project.dependencies:
                dependents.append(project)
        return dependents

    def get_build_order(self) -> list[ProjectConfig]:
        """
        Get projects in dependency order (topological sort).

        Returns:
            List of projects in build order (dependencies first)

        Raises:
            ValueError: If circular dependencies detected
        """
        # Kahn's algorithm for topological sort
        in_degree = {p.name: 0 for p in self.enabled_projects}
        adj_list = {p.name: [] for p in self.enabled_projects}

        # Build adjacency list and in-degree count
        for project in self.enabled_projects:
            for dep in project.dependencies:
                if dep in adj_list:  # Only include enabled projects
                    adj_list[dep].append(project.name)
                    in_degree[project.name] += 1

        # Start with projects that have no dependencies
        queue = deque(name for name, degree in in_degree.items() if degree == 0)
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)

            # Reduce in-degree for dependents
            for dependent in adj_list[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Check for cycles
        if len(result) != len(self.enabled_projects):
            raise ValueError("Circular dependency detected in workspace")

        # Convert names back to ProjectConfig objects
        return [self.get_project(name) for name in result if self.get_project(name)]

    def add_project(self, project: ProjectConfig) -> None:
        """
        Add a project to the workspace.

        Args:
            project: Project configuration to add

        Raises:
            ValueError: If project name already exists or dependencies are invalid
        """
        if self.get_project(project.name):
            raise ValueError(f"Project '{project.name}' already exists")

        # Validate dependencies reference existing projects
        existing_names = {p.name for p in self.projects}
        for dep in project.dependencies:
            if dep not in existing_names:
                raise ValueError(
                    f"Project '{project.name}' depends on unknown project '{dep}'"
                )

        self.projects.append(project)
        self.updated_at = datetime.now(UTC).isoformat()

    def remove_project(self, name: str) -> bool:
        """
        Remove a project from the workspace.

        Args:
            name: Project name to remove

        Returns:
            True if removed, False if not found

        Raises:
            ValueError: If other projects depend on this project
        """
        project = self.get_project(name)
        if not project:
            return False

        # Check for dependents
        dependents = self.get_dependents(name)
        if dependents:
            dep_names = [p.name for p in dependents]
            raise ValueError(
                f"Cannot remove project '{name}': projects {dep_names} depend on it"
            )

        self.projects.remove(project)
        self.updated_at = datetime.now(UTC).isoformat()
        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "projects": [p.to_dict() for p in self.projects],
            "description": self.description,
            "base_dir": str(self.base_dir) if self.base_dir else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkspaceConfig:
        """Deserialize from dictionary."""
        return cls(
            name=data["name"],
            projects=[ProjectConfig.from_dict(p) for p in data.get("projects", [])],
            description=data.get("description"),
            base_dir=Path(data["base_dir"]) if data.get("base_dir") else None,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> WorkspaceConfig:
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def save(self, path: Path | str) -> None:
        """
        Save workspace configuration to file using atomic write.

        Args:
            path: File path to save to
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = self.to_json()
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            Path(tmp_path).replace(path)
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    @classmethod
    def load(cls, path: Path | str) -> WorkspaceConfig:
        """
        Load workspace configuration from file.

        Args:
            path: File path to load from

        Returns:
            WorkspaceConfig instance

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(path)
        return cls.from_json(path.read_text())
