#!/usr/bin/env python3
"""
Integration Tests for Multi-Codebase Workspace Orchestration
==============================================================

Tests the end-to-end workspace management functionality for multi-codebase scenarios:
- Workspace creation with multiple projects
- Project loading and configuration validation
- Cross-project spec creation
- Coordinated operations across multiple projects

Coverage:
- WorkspaceConfig and WorkspaceManager basic operations
- Per-project state isolation
- Dependency tracking and build order calculation
- Multi-project worktree management
- Workspace persistence and recovery
"""

import json
import subprocess
from pathlib import Path

import pytest
from core.workspace import (
    find_workspace_for_project,
    get_workspace_config,
    get_workspace_manager,
    list_workspaces,
)

# Import workspace components
from core.workspace_config import (
    ProjectConfig,
    ProjectRelationship,
    WorkspaceConfig,
)
from core.workspace_manager import (
    ProjectState,
    WorkspaceManager,
)
from core.worktree import WorktreeManager


class TestWorkspaceCreation:
    """Tests for workspace creation with multiple projects."""

    def test_create_empty_workspace(self, temp_dir: Path):
        """Can create an empty workspace."""
        config = WorkspaceConfig(name="test-workspace")
        assert config.name == "test-workspace"
        assert config.project_count == 0
        assert len(config.projects) == 0

    def test_create_workspace_with_projects(self, temp_dir: Path):
        """Can create workspace with multiple projects."""
        # Create test project directories
        frontend_dir = temp_dir / "frontend"
        backend_dir = temp_dir / "backend"
        shared_dir = temp_dir / "shared"
        frontend_dir.mkdir()
        backend_dir.mkdir()
        shared_dir.mkdir()

        config = WorkspaceConfig(
            name="my-workspace",
            description="Test multi-project workspace",
            projects=[
                ProjectConfig(name="frontend", path=str(frontend_dir)),
                ProjectConfig(name="backend", path=str(backend_dir)),
                ProjectConfig(name="shared", path=str(shared_dir)),
            ],
        )

        assert config.name == "my-workspace"
        assert config.project_count == 3
        assert len(config.enabled_projects) == 3

    def test_workspace_projects_have_unique_names(self, temp_dir: Path):
        """Workspace validation rejects duplicate project names."""
        project_dir = temp_dir / "project"
        project_dir.mkdir()

        with pytest.raises(ValueError, match="Duplicate project names"):
            WorkspaceConfig(
                name="test-workspace",
                projects=[
                    ProjectConfig(name="project", path=str(project_dir)),
                    ProjectConfig(name="project", path=str(project_dir)),
                ],
            )

    def test_workspace_validates_dependencies(self, temp_dir: Path):
        """Workspace validation rejects unknown dependencies."""
        frontend_dir = temp_dir / "frontend"
        frontend_dir.mkdir()

        with pytest.raises(ValueError, match="depends on unknown project"):
            WorkspaceConfig(
                name="test-workspace",
                projects=[
                    ProjectConfig(
                        name="frontend",
                        path=str(frontend_dir),
                        dependencies=["nonexistent"],
                    ),
                ],
            )


class TestProjectConfiguration:
    """Tests for project configuration and state."""

    def test_project_path_detection(self, temp_dir: Path):
        """Can detect if file path belongs to project."""
        project_dir = temp_dir / "project"
        project_dir.mkdir()
        (project_dir / "src").mkdir()
        (project_dir / "src" / "file.py").write_text("# code")

        project = ProjectConfig(name="project", path=str(project_dir))

        # File inside project
        assert project.is_path_in_project(project_dir / "src" / "file.py")

        # File outside project
        assert not project.is_path_in_project(temp_dir / "outside.py")

    def test_project_state_key_sanitization(self, temp_dir: Path):
        """Project state keys are sanitized for safe directory names."""
        project = ProjectConfig(
            name="My Project / With Special-Chars!",
            path=str(temp_dir),
        )

        state_key = project.state_key
        assert " " not in state_key
        assert "/" not in state_key
        assert "!" not in state_key
        assert state_key == "my_project___with_special-chars_"

    def test_project_serialization(self, temp_dir: Path):
        """Can serialize and deserialize project config."""
        project_dir = temp_dir / "project"
        project_dir.mkdir()

        original = ProjectConfig(
            name="test-project",
            path=str(project_dir),
            enabled=True,
            relationship=ProjectRelationship.LIBRARY,
            dependencies=["dep1", "dep2"],
            description="Test project",
            tags=["tag1", "tag2"],
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = ProjectConfig.from_dict(data)

        assert restored.name == original.name
        assert restored.path == original.path
        assert restored.enabled == original.enabled
        assert restored.relationship == original.relationship
        assert restored.dependencies == original.dependencies
        assert restored.description == original.description
        assert restored.tags == original.tags


class TestWorkspaceManager:
    """Tests for workspace manager lifecycle operations."""

    def test_create_workspace_manager(self, temp_dir: Path):
        """Can create workspace manager."""
        config = WorkspaceConfig(name="test-workspace")
        manager = WorkspaceManager(config, base_dir=temp_dir / "workspaces")

        assert manager.config.name == "test-workspace"
        assert manager.workspace_dir.exists()

    def test_workspace_manager_add_project(self, temp_dir: Path):
        """Can add projects to workspace via manager."""
        config = WorkspaceConfig(name="test-workspace")
        manager = WorkspaceManager(config, base_dir=temp_dir / "workspaces")

        project_dir = temp_dir / "project"
        project_dir.mkdir()

        manager.add_project(
            name="test-project",
            path=str(project_dir),
            relationship=ProjectRelationship.INDEPENDENT,
        )

        assert manager.config.project_count == 1
        project = manager.config.get_project("test-project")
        assert project is not None
        assert project.name == "test-project"

    def test_workspace_manager_get_project_state(self, temp_dir: Path):
        """Can get per-project state."""
        project_dir = temp_dir / "project"
        project_dir.mkdir()

        config = WorkspaceConfig(
            name="test-workspace",
            projects=[ProjectConfig(name="project", path=str(project_dir))],
        )
        manager = WorkspaceManager(config, base_dir=temp_dir / "workspaces")

        state = manager.get_project_state("project")

        assert state is not None
        assert state.config.name == "project"
        assert state.state_dir.exists()
        assert state.worktree_dir.exists()
        assert state.spec_dir.exists()

    def test_workspace_manager_persistence(self, temp_dir: Path):
        """Can save and load workspace configuration."""
        project_dir = temp_dir / "project"
        project_dir.mkdir()

        # Create and save workspace
        config = WorkspaceConfig(
            name="test-workspace",
            description="Test workspace",
            projects=[ProjectConfig(name="project", path=str(project_dir))],
        )
        manager = WorkspaceManager(config, base_dir=temp_dir / "workspaces")
        manager.save()

        # Load workspace
        loaded_manager = WorkspaceManager.load_workspace(manager.workspace_dir)

        assert loaded_manager.config.name == "test-workspace"
        assert loaded_manager.config.description == "Test workspace"
        assert loaded_manager.config.project_count == 1
        assert loaded_manager.config.get_project("project") is not None


class TestDependencyTracking:
    """Tests for project dependency tracking and build order."""

    def test_get_project_dependencies(self, temp_dir: Path):
        """Can get dependencies for a project."""
        # Create project dirs
        frontend_dir = temp_dir / "frontend"
        shared_dir = temp_dir / "shared"
        frontend_dir.mkdir()
        shared_dir.mkdir()

        config = WorkspaceConfig(
            name="test-workspace",
            projects=[
                ProjectConfig(
                    name="frontend",
                    path=str(frontend_dir),
                    dependencies=["shared"],
                ),
                ProjectConfig(name="shared", path=str(shared_dir)),
            ],
        )

        deps = config.get_dependencies("frontend")

        assert len(deps) == 1
        assert deps[0].name == "shared"

    def test_get_project_dependents(self, temp_dir: Path):
        """Can get dependents for a project."""
        # Create project dirs
        frontend_dir = temp_dir / "frontend"
        backend_dir = temp_dir / "backend"
        shared_dir = temp_dir / "shared"
        frontend_dir.mkdir()
        backend_dir.mkdir()
        shared_dir.mkdir()

        config = WorkspaceConfig(
            name="test-workspace",
            projects=[
                ProjectConfig(
                    name="frontend",
                    path=str(frontend_dir),
                    dependencies=["shared"],
                ),
                ProjectConfig(
                    name="backend",
                    path=str(backend_dir),
                    dependencies=["shared"],
                ),
                ProjectConfig(name="shared", path=str(shared_dir)),
            ],
        )

        dependents = config.get_dependents("shared")

        assert len(dependents) == 2
        dependent_names = {d.name for d in dependents}
        assert "frontend" in dependent_names
        assert "backend" in dependent_names

    def test_get_build_order(self, temp_dir: Path):
        """Can compute build order based on dependencies."""
        # Create project dirs
        app_dir = temp_dir / "app"
        api_dir = temp_dir / "api"
        lib_dir = temp_dir / "lib"
        app_dir.mkdir()
        api_dir.mkdir()
        lib_dir.mkdir()

        # app -> api -> lib (linear chain)
        config = WorkspaceConfig(
            name="test-workspace",
            projects=[
                ProjectConfig(
                    name="app",
                    path=str(app_dir),
                    dependencies=["api"],
                ),
                ProjectConfig(
                    name="api",
                    path=str(api_dir),
                    dependencies=["lib"],
                ),
                ProjectConfig(name="lib", path=str(lib_dir)),
            ],
        )

        build_order = config.get_build_order()

        # lib should be built first, then api, then app
        assert len(build_order) == 3
        assert build_order[0].name == "lib"
        assert build_order[1].name == "api"
        assert build_order[2].name == "app"

    def test_build_order_detects_circular_dependencies(self, temp_dir: Path):
        """Build order calculation detects circular dependencies."""
        # Create project dirs
        a_dir = temp_dir / "a"
        b_dir = temp_dir / "b"
        a_dir.mkdir()
        b_dir.mkdir()

        # a -> b -> a (circular)
        config = WorkspaceConfig(
            name="test-workspace",
            projects=[
                ProjectConfig(name="a", path=str(a_dir), dependencies=["b"]),
                ProjectConfig(name="b", path=str(b_dir), dependencies=["a"]),
            ],
        )

        with pytest.raises(ValueError, match="Circular dependency"):
            config.get_build_order()

    def test_cannot_remove_project_with_dependents(self, temp_dir: Path):
        """Cannot remove project that other projects depend on."""
        # Create project dirs
        frontend_dir = temp_dir / "frontend"
        shared_dir = temp_dir / "shared"
        frontend_dir.mkdir()
        shared_dir.mkdir()

        config = WorkspaceConfig(
            name="test-workspace",
            projects=[
                ProjectConfig(
                    name="frontend",
                    path=str(frontend_dir),
                    dependencies=["shared"],
                ),
                ProjectConfig(name="shared", path=str(shared_dir)),
            ],
        )

        with pytest.raises(ValueError, match="projects .* depend on it"):
            config.remove_project("shared")


class TestMultiProjectWorktrees:
    """Tests for per-project worktree management."""

    def test_worktree_manager_multi_project_mode(self, temp_git_repo: Path):
        """WorktreeManager supports multi-project workspace mode."""
        # Create worktree manager for multi-project workspace
        manager = WorktreeManager(
            temp_git_repo,
            workspace_name="test-workspace",
            project_name="frontend",
        )

        manager.setup()
        worker_info = manager.create_worktree("test-spec")

        # Path should be: .auto-claude/workspaces/{workspace}/projects/{project}/worktrees/
        assert "workspaces" in str(worker_info.path)
        assert "test-workspace" in str(worker_info.path)
        assert "frontend" in str(worker_info.path)

    def test_worktree_manager_backward_compatibility(self, temp_git_repo: Path):
        """WorktreeManager maintains backward compatibility for single-project."""
        # Create worktree manager without workspace/project (single-project mode)
        manager = WorktreeManager(temp_git_repo)

        manager.setup()
        worker_info = manager.create_worktree("test-spec")

        # Path should be: .auto-claude/worktrees/tasks/
        assert "worktrees" in str(worker_info.path)
        assert "tasks" in str(worker_info.path)
        assert "workspaces" not in str(worker_info.path)


class TestWorkspaceUtilities:
    """Tests for workspace utility functions."""

    def test_get_workspace_config_for_project(self, temp_dir: Path):
        """Can load workspace config for a project."""
        # Create workspace with projects in the expected location
        project_dir = temp_dir / "project"
        project_dir.mkdir()

        # Save workspace in the project's .auto-claude/workspaces directory
        workspaces_dir = project_dir / ".auto-claude" / "workspaces"

        config = WorkspaceConfig(
            name="test-workspace",
            projects=[ProjectConfig(name="project", path=str(project_dir))],
        )
        manager = WorkspaceManager(config, base_dir=workspaces_dir)
        manager.save()

        # Load workspace config for project
        loaded_config = get_workspace_config(str(project_dir), "test-workspace")

        assert loaded_config is not None
        assert loaded_config.name == "test-workspace"

    def test_get_workspace_manager_for_project(self, temp_dir: Path):
        """Can load workspace manager for a project."""
        # Create workspace with projects in the expected location
        project_dir = temp_dir / "project"
        project_dir.mkdir()

        # Save workspace in the project's .auto-claude/workspaces directory
        workspaces_dir = project_dir / ".auto-claude" / "workspaces"

        config = WorkspaceConfig(
            name="test-workspace",
            projects=[ProjectConfig(name="project", path=str(project_dir))],
        )
        manager = WorkspaceManager(config, base_dir=workspaces_dir)
        manager.save()

        # Load workspace manager for project
        loaded_manager = get_workspace_manager(str(project_dir), "test-workspace")

        assert loaded_manager is not None
        assert loaded_manager.config.name == "test-workspace"

    def test_find_workspace_for_project(self, temp_dir: Path):
        """Can find workspace containing a project path."""
        # Create workspace with projects
        project_dir = temp_dir / "project"
        project_dir.mkdir()

        config = WorkspaceConfig(
            name="test-workspace",
            projects=[ProjectConfig(name="project", path=str(project_dir))],
        )
        manager = WorkspaceManager(config, base_dir=temp_dir / "workspaces")
        manager.save()

        # Find workspace for project (returns WorkspaceManager)
        workspace_manager = find_workspace_for_project(
            str(project_dir), base_dir=temp_dir / "workspaces"
        )

        assert workspace_manager is not None
        assert workspace_manager.config.name == "test-workspace"

    def test_list_workspaces(self, temp_dir: Path):
        """Can list all available workspaces."""
        base_dir = temp_dir / "workspaces"

        # Create multiple workspaces
        for i in range(3):
            config = WorkspaceConfig(name=f"workspace-{i}")
            manager = WorkspaceManager(config, base_dir=base_dir)
            manager.save()

        # List workspaces (returns list of dicts)
        workspaces = list_workspaces(base_dir)

        assert len(workspaces) == 3
        workspace_names = {w["name"] for w in workspaces}
        assert "workspace-0" in workspace_names
        assert "workspace-1" in workspace_names
        assert "workspace-2" in workspace_names


class TestWorkspaceContextForSpecs:
    """Tests for workspace context saved for spec creation."""

    def test_workspace_context_json_creation(self, temp_dir: Path):
        """Workspace context can be saved for spec access."""
        # Create workspace with multiple projects
        frontend_dir = temp_dir / "frontend"
        backend_dir = temp_dir / "backend"
        frontend_dir.mkdir()
        backend_dir.mkdir()

        config = WorkspaceConfig(
            name="test-workspace",
            projects=[
                ProjectConfig(name="frontend", path=str(frontend_dir)),
                ProjectConfig(name="backend", path=str(backend_dir)),
            ],
        )
        manager = WorkspaceManager(config, base_dir=temp_dir / "workspaces")

        # Simulate saving workspace context for a spec
        spec_dir = temp_dir / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        workspace_context = {
            "workspace_name": manager.config.name,
            "projects": [
                {
                    "name": p.name,
                    "path": p.path,
                    "enabled": p.enabled,
                }
                for p in manager.config.projects
            ],
        }

        context_file = spec_dir / "workspace_context.json"
        context_file.write_text(json.dumps(workspace_context, indent=2))

        # Verify context can be loaded
        loaded_context = json.loads(context_file.read_text())

        assert loaded_context["workspace_name"] == "test-workspace"
        assert len(loaded_context["projects"]) == 2
        assert loaded_context["projects"][0]["name"] == "frontend"
        assert loaded_context["projects"][1]["name"] == "backend"


class TestEndToEndWorkspaceFlow:
    """End-to-end integration tests for workspace orchestration."""

    def test_full_workspace_lifecycle(self, temp_dir: Path, temp_git_repo: Path):
        """
        Full workspace lifecycle test:
        1. Create workspace with multiple projects
        2. Verify projects loaded correctly
        3. Manage project state
        4. Persist and reload workspace
        """
        # Step 1: Create workspace with multiple projects
        frontend_dir = temp_dir / "frontend"
        backend_dir = temp_dir / "backend"
        shared_dir = temp_dir / "shared"

        for d in [frontend_dir, backend_dir, shared_dir]:
            d.mkdir()
            (d / "README.md").write_text(f"# {d.name}")

        config = WorkspaceConfig(
            name="microservices-workspace",
            description="Multi-service architecture",
            projects=[
                ProjectConfig(
                    name="frontend",
                    path=str(frontend_dir),
                    relationship=ProjectRelationship.DEPENDS_ON,
                    dependencies=["shared"],
                ),
                ProjectConfig(
                    name="backend",
                    path=str(backend_dir),
                    relationship=ProjectRelationship.DEPENDS_ON,
                    dependencies=["shared"],
                ),
                ProjectConfig(
                    name="shared",
                    path=str(shared_dir),
                    relationship=ProjectRelationship.LIBRARY,
                ),
            ],
        )

        # Step 2: Verify projects loaded correctly
        assert config.project_count == 3
        assert len(config.enabled_projects) == 3

        # Verify dependency relationships
        frontend_deps = config.get_dependencies("frontend")
        backend_deps = config.get_dependencies("backend")
        assert len(frontend_deps) == 1
        assert frontend_deps[0].name == "shared"
        assert len(backend_deps) == 1
        assert backend_deps[0].name == "shared"

        # Verify build order
        build_order = config.get_build_order()
        assert build_order[0].name == "shared"  # Library built first
        assert build_order[1].name in ["frontend", "backend"]
        assert build_order[2].name in ["frontend", "backend"]

        # Step 3: Create manager and get project state
        manager = WorkspaceManager(config, base_dir=temp_dir / "workspaces")

        frontend_state = manager.get_project_state("frontend")
        assert frontend_state is not None
        assert frontend_state.worktree_dir.exists()
        assert frontend_state.spec_dir.exists()

        # Step 4: Persist and reload workspace
        manager.save()

        loaded_manager = WorkspaceManager.load_workspace(manager.workspace_dir)
        assert loaded_manager.config.name == "microservices-workspace"
        assert loaded_manager.config.project_count == 3

        # Verify all project paths are correct after reload
        for project in loaded_manager.config.projects:
            assert Path(project.path).exists()
            assert Path(project.path).is_dir()

    def test_coordinated_multi_project_worktrees(self, temp_dir: Path):
        """
        Test coordinated worktree operations across multiple projects.

        This simulates a multi-project spec that needs to modify
        multiple repositories in coordination.
        """
        # Create separate git repos for each project
        workspace_name = "test-workspace"
        projects = ["frontend", "backend"]

        # Initialize separate git repos for each project
        project_repos = {}
        for project_name in projects:
            project_dir = temp_dir / project_name
            project_dir.mkdir()

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=project_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test User"],
                cwd=project_dir,
                capture_output=True,
            )

            # Create initial commit
            (project_dir / "README.md").write_text(f"# {project_name}")
            subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit"],
                cwd=project_dir,
                capture_output=True,
            )

            project_repos[project_name] = project_dir

        # Create worktree managers for each project
        worktree_managers = {}
        for project_name, project_dir in project_repos.items():
            manager = WorktreeManager(
                project_dir,
                workspace_name=workspace_name,
                project_name=project_name,
            )
            manager.setup()
            worktree_managers[project_name] = manager

        # Create worktrees for the same spec across all projects
        spec_name = "feature-001"
        worktrees = {}

        for project_name, manager in worktree_managers.items():
            worker_info = manager.create_worktree(spec_name)
            worktrees[project_name] = worker_info

            # Verify each project has its own isolated worktree
            assert worker_info.path.exists()
            assert workspace_name in str(worker_info.path)
            assert project_name in str(worker_info.path)

        # Verify all worktrees are in separate directories
        paths = [info.path for info in worktrees.values()]
        assert len(paths) == len(set(paths))  # All unique

        # Simulate making changes in each worktree
        for project_name, info in worktrees.items():
            test_file = info.path / f"{project_name}.txt"
            test_file.write_text(f"Changes for {project_name}")

            # Commit changes
            subprocess.run(["git", "add", "."], cwd=info.path, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"Update {project_name}"],
                cwd=info.path,
                capture_output=True,
            )

        # Verify commits exist in each worktree
        for info in worktrees.values():
            log = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                cwd=info.path,
                capture_output=True,
                text=True,
            )
            assert "Update" in log.stdout
