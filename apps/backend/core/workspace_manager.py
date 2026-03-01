"""
Workspace Manager
==================

Manages multi-project workspaces with:
- Workspace lifecycle (create, load, save)
- Per-project state isolation
- Coordinated operations across projects
- Workspace persistence and validation

Usage:
    # Create a new workspace
    manager = WorkspaceManager.create_workspace(
        name="my-workspace",
        base_dir=Path(".auto-claude/workspaces")
    )

    # Add projects
    manager.add_project(
        name="frontend",
        path="/path/to/frontend",
        relationship="depends_on",
        dependencies=["shared"]
    )

    # Get project state
    state = manager.get_project_state("frontend")

    # Save workspace
    manager.save()

    # Load existing workspace
    manager = WorkspaceManager.load_workspace(
        Path(".auto-claude/workspaces/my-workspace")
    )
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .workspace_config import (
    ProjectConfig,
    ProjectRelationship,
    WorkspaceConfig,
)


@dataclass
class ProjectState:
    """
    Isolated state for a project in a workspace.

    Each project has its own state directory to prevent conflicts
    and enable parallel operations.

    Attributes:
        config: Project configuration
        state_dir: Directory for project-specific state
        last_sync: Timestamp of last sync operation
    """

    config: ProjectConfig
    state_dir: Path
    last_sync: str | None = None

    @property
    def worktree_dir(self) -> Path:
        """Directory for git worktrees."""
        d = self.state_dir / "worktrees"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def spec_dir(self) -> Path:
        """Directory for spec state."""
        d = self.state_dir / "specs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def cache_dir(self) -> Path:
        """Directory for cached data."""
        d = self.state_dir / "cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def logs_dir(self) -> Path:
        """Directory for project logs."""
        d = self.state_dir / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "config": self.config.to_dict(),
            "state_dir": str(self.state_dir),
            "last_sync": self.last_sync,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectState:
        """Deserialize from dictionary."""
        return cls(
            config=ProjectConfig.from_dict(data["config"]),
            state_dir=Path(data["state_dir"]),
            last_sync=data.get("last_sync"),
        )


class WorkspaceManager:
    """
    Manager for multi-project workspaces.

    Handles:
    - Workspace configuration and persistence
    - Per-project state isolation
    - Project lifecycle management
    - Coordinated operations across projects

    Attributes:
        config: Workspace configuration
        base_dir: Base directory for workspace state
        _project_states: Cache of project states
    """

    def __init__(
        self,
        config: WorkspaceConfig,
        base_dir: Path | None = None,
    ):
        """
        Initialize workspace manager.

        Args:
            config: Workspace configuration
            base_dir: Base directory for workspace state (defaults to config.base_dir)
        """
        self.config = config
        self.base_dir = base_dir or config.base_dir or Path(".auto-claude/workspaces")
        self._project_states: dict[str, ProjectState] = {}

        # Ensure base directory exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Initialize project states
        self._initialize_project_states()

    @property
    def workspace_dir(self) -> Path:
        """Get workspace directory path."""
        return self.base_dir / self.config.name

    @property
    def config_file(self) -> Path:
        """Get workspace configuration file path."""
        return self.workspace_dir / "workspace.json"

    @property
    def state_file(self) -> Path:
        """Get workspace state file path."""
        return self.workspace_dir / "state.json"

    @classmethod
    def create_workspace(
        cls,
        name: str,
        base_dir: Path | None = None,
        description: str | None = None,
        projects: list[ProjectConfig] | None = None,
    ) -> WorkspaceManager:
        """
        Create a new workspace.

        Args:
            name: Workspace name
            base_dir: Base directory for workspace state
            description: Optional workspace description
            projects: Initial list of projects

        Returns:
            WorkspaceManager instance

        Raises:
            ValueError: If workspace already exists
        """
        base_dir = base_dir or Path(".auto-claude/workspaces")
        workspace_dir = base_dir / name
        config_file = workspace_dir / "workspace.json"

        if config_file.exists():
            raise ValueError(f"Workspace '{name}' already exists at {workspace_dir}")

        config = WorkspaceConfig(
            name=name,
            description=description,
            base_dir=base_dir,
            projects=projects or [],
        )

        manager = cls(config, base_dir)
        manager.save()

        return manager

    @classmethod
    def load_workspace(cls, workspace_dir: Path | str) -> WorkspaceManager:
        """
        Load an existing workspace.

        Args:
            workspace_dir: Path to workspace directory

        Returns:
            WorkspaceManager instance

        Raises:
            FileNotFoundError: If workspace doesn't exist
            ValueError: If workspace configuration is invalid
        """
        workspace_dir = Path(workspace_dir)
        config_file = workspace_dir / "workspace.json"

        if not config_file.exists():
            raise FileNotFoundError(
                f"Workspace configuration not found at {config_file}"
            )

        config = WorkspaceConfig.load(config_file)
        base_dir = config.base_dir or workspace_dir.parent

        manager = cls(config, base_dir)

        # Load state if it exists
        if manager.state_file.exists():
            manager._load_state()

        return manager

    @classmethod
    def workspace_exists(cls, name: str, base_dir: Path | None = None) -> bool:
        """
        Check if a workspace exists.

        Args:
            name: Workspace name
            base_dir: Base directory for workspaces

        Returns:
            True if workspace exists
        """
        base_dir = base_dir or Path(".auto-claude/workspaces")
        workspace_dir = base_dir / name
        config_file = workspace_dir / "workspace.json"
        return config_file.exists()

    def _initialize_project_states(self) -> None:
        """Initialize state for all projects."""
        for project in self.config.projects:
            state_dir = self.workspace_dir / "projects" / project.state_key
            state_dir.mkdir(parents=True, exist_ok=True)

            self._project_states[project.name] = ProjectState(
                config=project,
                state_dir=state_dir,
            )

    def get_project_state(self, project_name: str) -> ProjectState | None:
        """
        Get state for a project.

        Args:
            project_name: Name of project

        Returns:
            ProjectState or None if project not found
        """
        return self._project_states.get(project_name)

    def get_all_project_states(self) -> list[ProjectState]:
        """
        Get states for all projects.

        Returns:
            List of ProjectState objects
        """
        return list(self._project_states.values())

    def get_enabled_project_states(self) -> list[ProjectState]:
        """
        Get states for enabled projects only.

        Returns:
            List of ProjectState objects for enabled projects
        """
        return [
            state for state in self._project_states.values() if state.config.enabled
        ]

    def add_project(
        self,
        name: str,
        path: str | Path,
        enabled: bool = True,
        relationship: ProjectRelationship | str = ProjectRelationship.INDEPENDENT,
        dependencies: list[str] | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> ProjectConfig:
        """
        Add a project to the workspace.

        Args:
            name: Project name
            path: Path to project directory
            enabled: Whether project is enabled
            relationship: Relationship to other projects
            dependencies: List of project names this depends on
            description: Optional project description
            tags: Optional tags for categorization

        Returns:
            Created ProjectConfig

        Raises:
            ValueError: If project name already exists
        """
        if isinstance(relationship, str):
            relationship = ProjectRelationship(relationship)

        project = ProjectConfig(
            name=name,
            path=str(path),
            enabled=enabled,
            relationship=relationship,
            dependencies=dependencies or [],
            description=description,
            tags=tags or [],
        )

        self.config.add_project(project)

        # Initialize state for new project
        state_dir = self.workspace_dir / "projects" / project.state_key
        state_dir.mkdir(parents=True, exist_ok=True)

        self._project_states[project.name] = ProjectState(
            config=project,
            state_dir=state_dir,
        )

        return project

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
        result = self.config.remove_project(name)

        if result and name in self._project_states:
            del self._project_states[name]

        return result

    def update_project_sync(self, project_name: str) -> None:
        """
        Update last sync timestamp for a project.

        Args:
            project_name: Name of project to update
        """
        state = self.get_project_state(project_name)
        if state:
            state.last_sync = datetime.now(timezone.utc).isoformat()

    def get_project_by_path(self, file_path: str | Path) -> ProjectConfig | None:
        """
        Find which project a file path belongs to.

        Args:
            file_path: File path to check

        Returns:
            ProjectConfig or None if not found
        """
        return self.config.find_project_by_path(file_path)

    def get_build_order(self) -> list[ProjectConfig]:
        """
        Get projects in dependency order.

        Returns:
            List of projects in build order (dependencies first)

        Raises:
            ValueError: If circular dependencies detected
        """
        return self.config.get_build_order()

    def save(self) -> None:
        """
        Save workspace configuration and state to disk.

        Creates:
        - workspace.json: Configuration
        - state.json: Runtime state
        """
        # Save configuration
        self.config.save(self.config_file)

        # Save state
        self._save_state()

    def _save_state(self) -> None:
        """Save workspace state to disk using atomic write."""
        state = {
            "workspace": self.config.name,
            "last_saved": datetime.now(timezone.utc).isoformat(),
            "projects": {
                name: project_state.to_dict()
                for name, project_state in self._project_states.items()
            },
        }

        content = json.dumps(state, indent=2)
        # Atomic write: write to temp file then rename
        fd, tmp_path = tempfile.mkstemp(dir=str(self.state_file.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            Path(tmp_path).replace(self.state_file)
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    def _load_state(self) -> None:
        """Load workspace state from disk."""
        if not self.state_file.exists():
            return

        state = json.loads(self.state_file.read_text())

        # Restore project states
        for name, project_data in state.get("projects", {}).items():
            if name in self._project_states:
                self._project_states[name].last_sync = project_data.get("last_sync")

    def get_workspace_stats(self) -> dict[str, Any]:
        """
        Get workspace statistics.

        Returns:
            Dictionary with workspace stats
        """
        return {
            "name": self.config.name,
            "total_projects": self.config.project_count,
            "enabled_projects": len(self.config.enabled_projects),
            "project_names": [p.name for p in self.config.projects],
            "created_at": self.config.created_at,
            "updated_at": self.config.updated_at,
            "workspace_dir": str(self.workspace_dir),
        }

    def validate_workspace(self) -> list[str]:
        """
        Validate workspace configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check if project directories exist
        for project in self.config.projects:
            if not Path(project.path).exists():
                errors.append(
                    f"Project '{project.name}' path does not exist: {project.path}"
                )

        # Check for circular dependencies
        try:
            self.config.get_build_order()
        except ValueError as e:
            errors.append(f"Dependency error: {e}")

        # Check if state directories are accessible
        for name, state in self._project_states.items():
            if not state.state_dir.exists():
                errors.append(
                    f"State directory missing for project '{name}': {state.state_dir}"
                )

        return errors

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"WorkspaceManager(name='{self.config.name}', "
            f"projects={self.config.project_count}, "
            f"dir='{self.workspace_dir}')"
        )
