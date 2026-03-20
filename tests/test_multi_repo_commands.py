#!/usr/bin/env python3
"""
Tests for Multi-Repo CLI Commands
===================================

Tests the cli/multi_repo_commands.py module including:
- handle_workspace_create_command: Create a new workspace
- handle_workspace_list_command: List existing workspaces
- handle_workspace_add_project_command: Add a project to a workspace
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# sys.path is set by conftest.py (apps/backend is already on the path)
# Keep a local fallback for running this file directly
if not any("apps/backend" in p or "apps\\backend" in p for p in sys.path):
    sys.path.insert(0, "apps/backend")


# =============================================================================
# handle_workspace_create_command Tests
# =============================================================================


class TestHandleWorkspaceCreateCommandSuccess:
    """Tests for successful workspace creation."""

    def test_creates_workspace_with_name_only(self, tmp_path):
        """Creates workspace when name is provided and workspace doesn't exist."""
        mock_manager = MagicMock()
        mock_manager.workspace_dir = tmp_path / "test-ws"
        mock_manager.config.description = None
        mock_manager.config.project_count = 0

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("cli.multi_repo_commands.print_banner"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = False
            mock_wm_class.create_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_create_command

            result = handle_workspace_create_command(
                name="test-ws",
                base_dir=tmp_path,
            )

        assert result is True
        mock_wm_class.create_workspace.assert_called_once_with(
            name="test-ws",
            base_dir=tmp_path,
            description=None,
        )

    def test_creates_workspace_with_description(self, tmp_path):
        """Creates workspace with optional description."""
        mock_manager = MagicMock()
        mock_manager.workspace_dir = tmp_path / "my-ws"
        mock_manager.config.description = "My workspace description"

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("cli.multi_repo_commands.print_banner"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = False
            mock_wm_class.create_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_create_command

            result = handle_workspace_create_command(
                name="my-ws",
                description="My workspace description",
                base_dir=tmp_path,
            )

        assert result is True
        mock_wm_class.create_workspace.assert_called_once_with(
            name="my-ws",
            base_dir=tmp_path,
            description="My workspace description",
        )

    def test_uses_default_base_dir_when_not_provided(self):
        """Uses .auto-claude/workspaces as default base_dir."""
        mock_manager = MagicMock()
        mock_manager.workspace_dir = Path(".auto-claude/workspaces/ws")
        mock_manager.config.description = None

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("cli.multi_repo_commands.print_banner"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = False
            mock_wm_class.create_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_create_command

            result = handle_workspace_create_command(name="ws")

        assert result is True
        # Verify workspace_exists was called with the default base dir
        call_args = mock_wm_class.workspace_exists.call_args
        assert call_args[0][1] == Path(".auto-claude/workspaces")

    def test_calls_print_banner(self, tmp_path):
        """Calls print_banner when creating a workspace."""
        mock_manager = MagicMock()
        mock_manager.workspace_dir = tmp_path / "ws"
        mock_manager.config.description = None

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("cli.multi_repo_commands.print_banner") as mock_banner,
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = False
            mock_wm_class.create_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_create_command

            handle_workspace_create_command(name="ws", base_dir=tmp_path)

        mock_banner.assert_called_once()


class TestHandleWorkspaceCreateCommandAlreadyExists:
    """Tests for workspace creation when workspace already exists."""

    def test_returns_false_when_workspace_exists(self, tmp_path):
        """Returns False when workspace already exists."""
        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("cli.multi_repo_commands.print_banner"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True

            from cli.multi_repo_commands import handle_workspace_create_command

            result = handle_workspace_create_command(name="existing", base_dir=tmp_path)

        assert result is False

    def test_does_not_create_when_workspace_exists(self, tmp_path):
        """Does not call create_workspace when workspace already exists."""
        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("cli.multi_repo_commands.print_banner"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True

            from cli.multi_repo_commands import handle_workspace_create_command

            handle_workspace_create_command(name="existing", base_dir=tmp_path)

        mock_wm_class.create_workspace.assert_not_called()


class TestHandleWorkspaceCreateCommandErrors:
    """Tests for error handling during workspace creation."""

    def test_returns_false_on_value_error(self, tmp_path):
        """Returns False when ValueError is raised during creation."""
        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("cli.multi_repo_commands.print_banner"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = False
            mock_wm_class.create_workspace.side_effect = ValueError("Invalid name")

            from cli.multi_repo_commands import handle_workspace_create_command

            result = handle_workspace_create_command(name="bad name", base_dir=tmp_path)

        assert result is False

    def test_returns_false_on_os_error(self, tmp_path):
        """Returns False when OSError is raised during creation."""
        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("cli.multi_repo_commands.print_banner"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = False
            mock_wm_class.create_workspace.side_effect = OSError("Permission denied")

            from cli.multi_repo_commands import handle_workspace_create_command

            result = handle_workspace_create_command(name="ws", base_dir=tmp_path)

        assert result is False


# =============================================================================
# handle_workspace_list_command Tests
# =============================================================================


class TestHandleWorkspaceListCommandNoWorkspaces:
    """Tests for listing workspaces when none exist."""

    def test_returns_true_when_base_dir_missing(self, tmp_path):
        """Returns True when base directory doesn't exist."""
        non_existent = tmp_path / "no-workspaces"

        with (
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            from cli.multi_repo_commands import handle_workspace_list_command

            result = handle_workspace_list_command(base_dir=non_existent)

        assert result is True

    def test_returns_true_when_no_workspaces_in_dir(self, tmp_path):
        """Returns True when base dir exists but has no workspace.json files."""
        base_dir = tmp_path / "workspaces"
        base_dir.mkdir()
        # Create directories without workspace.json
        (base_dir / "not-a-workspace").mkdir()

        with (
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            from cli.multi_repo_commands import handle_workspace_list_command

            result = handle_workspace_list_command(base_dir=base_dir)

        assert result is True

    def test_uses_default_base_dir_when_not_provided(self):
        """Uses .auto-claude/workspaces as default base_dir."""
        with (
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            from cli.multi_repo_commands import handle_workspace_list_command

            # Should not raise; returns True even if default dir doesn't exist
            result = handle_workspace_list_command()

        # May return True (dir doesn't exist) or True (listed)
        assert isinstance(result, bool)


class TestHandleWorkspaceListCommandWithWorkspaces:
    """Tests for listing workspaces when workspaces exist."""

    def test_returns_true_when_workspaces_found(self, tmp_path):
        """Returns True when workspaces are found and listed."""
        base_dir = tmp_path / "workspaces"
        base_dir.mkdir()
        ws_dir = base_dir / "my-workspace"
        ws_dir.mkdir()
        (ws_dir / "workspace.json").write_text("{}")

        mock_manager = MagicMock()
        mock_manager.config.description = "A workspace"
        mock_manager.get_workspace_stats.return_value = {
            "name": "my-workspace",
            "total_projects": 2,
            "enabled_projects": 2,
            "project_names": ["frontend", "backend"],
        }

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.highlight", return_value="my-workspace"),
            patch("builtins.print"),
        ):
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_list_command

            result = handle_workspace_list_command(base_dir=base_dir)

        assert result is True

    def test_loads_each_workspace(self, tmp_path):
        """Loads each workspace directory that has workspace.json."""
        base_dir = tmp_path / "workspaces"
        base_dir.mkdir()
        for name in ["ws1", "ws2"]:
            ws_dir = base_dir / name
            ws_dir.mkdir()
            (ws_dir / "workspace.json").write_text("{}")

        mock_manager = MagicMock()
        mock_manager.config.description = None
        mock_manager.get_workspace_stats.return_value = {
            "name": "ws",
            "total_projects": 0,
            "enabled_projects": 0,
            "project_names": [],
        }

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.highlight", return_value="ws"),
            patch("builtins.print"),
        ):
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_list_command

            handle_workspace_list_command(base_dir=base_dir)

        assert mock_wm_class.load_workspace.call_count == 2

    def test_handles_load_error_gracefully(self, tmp_path):
        """Handles errors loading individual workspaces gracefully."""
        base_dir = tmp_path / "workspaces"
        base_dir.mkdir()
        ws_dir = base_dir / "broken-ws"
        ws_dir.mkdir()
        (ws_dir / "workspace.json").write_text("{}")

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("builtins.print"),
        ):
            mock_wm_class.load_workspace.side_effect = ValueError("Corrupt config")

            from cli.multi_repo_commands import handle_workspace_list_command

            # Should not raise; broken workspaces are reported and skipped
            result = handle_workspace_list_command(base_dir=base_dir)

        assert result is True

    def test_skips_dirs_without_workspace_json(self, tmp_path):
        """Only counts directories that have workspace.json."""
        base_dir = tmp_path / "workspaces"
        base_dir.mkdir()
        # Valid workspace
        valid_dir = base_dir / "valid"
        valid_dir.mkdir()
        (valid_dir / "workspace.json").write_text("{}")
        # Directory without workspace.json
        (base_dir / "not-workspace").mkdir()

        mock_manager = MagicMock()
        mock_manager.config.description = None
        mock_manager.get_workspace_stats.return_value = {
            "name": "valid",
            "total_projects": 0,
            "enabled_projects": 0,
            "project_names": [],
        }

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.highlight", return_value="valid"),
            patch("builtins.print"),
        ):
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_list_command

            handle_workspace_list_command(base_dir=base_dir)

        # Only the valid workspace should be loaded
        assert mock_wm_class.load_workspace.call_count == 1


# =============================================================================
# handle_workspace_add_project_command Tests
# =============================================================================


class TestHandleWorkspaceAddProjectCommandSuccess:
    """Tests for successful project addition."""

    def test_adds_project_to_workspace(self, tmp_path):
        """Adds a project to an existing workspace."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()

        mock_project = MagicMock()
        mock_project.name = "my-project"
        mock_project.path = str(project_dir)
        mock_project.relationship.value = "independent"
        mock_project.dependencies = []
        mock_project.description = None

        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = None
        mock_manager.add_project.return_value = mock_project
        mock_manager.config.project_count = 1

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            result = handle_workspace_add_project_command(
                workspace_name="my-ws",
                project_path=str(project_dir),
                base_dir=tmp_path,
            )

        assert result is True
        mock_manager.add_project.assert_called_once()
        mock_manager.save.assert_called_once()

    def test_uses_directory_name_as_default_project_name(self, tmp_path):
        """Uses directory name as default project name when not specified."""
        project_dir = tmp_path / "cool-project"
        project_dir.mkdir()

        mock_project = MagicMock()
        mock_project.name = "cool-project"
        mock_project.path = str(project_dir)
        mock_project.relationship.value = "independent"
        mock_project.dependencies = []
        mock_project.description = None

        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = None
        mock_manager.add_project.return_value = mock_project
        mock_manager.config.project_count = 1

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            handle_workspace_add_project_command(
                workspace_name="my-ws",
                project_path=str(project_dir),
                base_dir=tmp_path,
            )

        # project_name defaults to directory name
        call_kwargs = mock_manager.add_project.call_args[1]
        assert call_kwargs["name"] == "cool-project"

    def test_uses_provided_project_name(self, tmp_path):
        """Uses explicitly provided project name."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()

        mock_project = MagicMock()
        mock_project.name = "custom-name"
        mock_project.path = str(project_dir)
        mock_project.relationship.value = "independent"
        mock_project.dependencies = []
        mock_project.description = None

        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = None
        mock_manager.add_project.return_value = mock_project
        mock_manager.config.project_count = 1

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            handle_workspace_add_project_command(
                workspace_name="my-ws",
                project_path=str(project_dir),
                project_name="custom-name",
                base_dir=tmp_path,
            )

        call_kwargs = mock_manager.add_project.call_args[1]
        assert call_kwargs["name"] == "custom-name"

    def test_passes_dependencies_to_add_project(self, tmp_path):
        """Passes dependencies list to add_project."""
        project_dir = tmp_path / "frontend"
        project_dir.mkdir()

        mock_project = MagicMock()
        mock_project.name = "frontend"
        mock_project.path = str(project_dir)
        mock_project.relationship.value = "depends_on"
        mock_project.dependencies = ["backend", "shared"]
        mock_project.description = None

        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = None
        mock_manager.add_project.return_value = mock_project
        mock_manager.config.project_count = 3

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            result = handle_workspace_add_project_command(
                workspace_name="my-ws",
                project_path=str(project_dir),
                relationship="depends_on",
                dependencies=["backend", "shared"],
                base_dir=tmp_path,
            )

        assert result is True
        call_kwargs = mock_manager.add_project.call_args[1]
        assert call_kwargs["dependencies"] == ["backend", "shared"]

    def test_saves_workspace_after_adding_project(self, tmp_path):
        """Saves the workspace after adding a project."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        mock_project = MagicMock()
        mock_project.name = "proj"
        mock_project.path = str(project_dir)
        mock_project.relationship.value = "independent"
        mock_project.dependencies = []
        mock_project.description = None

        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = None
        mock_manager.add_project.return_value = mock_project
        mock_manager.config.project_count = 1

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            handle_workspace_add_project_command(
                workspace_name="ws",
                project_path=str(project_dir),
                base_dir=tmp_path,
            )

        mock_manager.save.assert_called_once()


class TestHandleWorkspaceAddProjectCommandValidation:
    """Tests for input validation in add_project command."""

    def test_returns_false_when_workspace_not_found(self, tmp_path):
        """Returns False when workspace doesn't exist."""
        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = False

            from cli.multi_repo_commands import handle_workspace_add_project_command

            result = handle_workspace_add_project_command(
                workspace_name="nonexistent",
                project_path="/some/path",
                base_dir=tmp_path,
            )

        assert result is False

    def test_returns_false_when_project_path_not_exists(self, tmp_path):
        """Returns False when project path doesn't exist on filesystem."""
        non_existent = tmp_path / "does-not-exist"

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True

            from cli.multi_repo_commands import handle_workspace_add_project_command

            result = handle_workspace_add_project_command(
                workspace_name="ws",
                project_path=str(non_existent),
                base_dir=tmp_path,
            )

        assert result is False

    def test_returns_false_when_project_path_is_file(self, tmp_path):
        """Returns False when project path points to a file, not a directory."""
        file_path = tmp_path / "a-file.txt"
        file_path.write_text("I am a file")

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True

            from cli.multi_repo_commands import handle_workspace_add_project_command

            result = handle_workspace_add_project_command(
                workspace_name="ws",
                project_path=str(file_path),
                base_dir=tmp_path,
            )

        assert result is False

    def test_returns_false_for_invalid_relationship(self, tmp_path):
        """Returns False when an invalid relationship value is given."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True

            from cli.multi_repo_commands import handle_workspace_add_project_command

            result = handle_workspace_add_project_command(
                workspace_name="ws",
                project_path=str(project_dir),
                relationship="not-a-valid-relationship",
                base_dir=tmp_path,
            )

        assert result is False

    def test_returns_false_when_project_name_already_exists(self, tmp_path):
        """Returns False when a project with the same name already exists."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        mock_existing_state = MagicMock()  # Non-None means project exists
        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = mock_existing_state

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            result = handle_workspace_add_project_command(
                workspace_name="ws",
                project_path=str(project_dir),
                project_name="proj",
                base_dir=tmp_path,
            )

        assert result is False
        mock_manager.add_project.assert_not_called()


class TestHandleWorkspaceAddProjectCommandErrors:
    """Tests for error handling when adding a project fails."""

    def test_returns_false_on_value_error(self, tmp_path):
        """Returns False when ValueError is raised during add_project."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = None
        mock_manager.add_project.side_effect = ValueError("Circular dependency")

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            result = handle_workspace_add_project_command(
                workspace_name="ws",
                project_path=str(project_dir),
                base_dir=tmp_path,
            )

        assert result is False

    def test_returns_false_on_file_not_found_error(self, tmp_path):
        """Returns False when FileNotFoundError is raised."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = None
        mock_manager.add_project.side_effect = FileNotFoundError("Workspace file missing")

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            result = handle_workspace_add_project_command(
                workspace_name="ws",
                project_path=str(project_dir),
                base_dir=tmp_path,
            )

        assert result is False

    def test_returns_false_on_os_error(self, tmp_path):
        """Returns False when OSError is raised."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = None
        mock_manager.add_project.side_effect = OSError("Disk full")

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            result = handle_workspace_add_project_command(
                workspace_name="ws",
                project_path=str(project_dir),
                base_dir=tmp_path,
            )

        assert result is False


class TestHandleWorkspaceAddProjectCommandRelationships:
    """Tests for relationship handling when adding projects."""

    @pytest.mark.parametrize(
        "relationship",
        ["independent", "depends_on", "library", "monorepo_package"],
    )
    def test_accepts_all_valid_relationships(self, tmp_path, relationship):
        """Accepts all valid ProjectRelationship values."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        mock_project = MagicMock()
        mock_project.name = "proj"
        mock_project.path = str(project_dir)
        mock_project.relationship.value = relationship
        mock_project.dependencies = []
        mock_project.description = None

        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = None
        mock_manager.add_project.return_value = mock_project
        mock_manager.config.project_count = 1

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            result = handle_workspace_add_project_command(
                workspace_name="ws",
                project_path=str(project_dir),
                relationship=relationship,
                base_dir=tmp_path,
            )

        assert result is True

    def test_uses_independent_as_default_relationship(self, tmp_path):
        """Uses 'independent' as default relationship."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        mock_project = MagicMock()
        mock_project.name = "proj"
        mock_project.path = str(project_dir)
        mock_project.relationship.value = "independent"
        mock_project.dependencies = []
        mock_project.description = None

        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = None
        mock_manager.add_project.return_value = mock_project
        mock_manager.config.project_count = 1

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            handle_workspace_add_project_command(
                workspace_name="ws",
                project_path=str(project_dir),
                base_dir=tmp_path,
            )

        # The add_project should have been called with independent relationship
        from core.workspace_config import ProjectRelationship

        call_kwargs = mock_manager.add_project.call_args[1]
        assert call_kwargs["relationship"] == ProjectRelationship.INDEPENDENT


class TestHandleWorkspaceAddProjectCommandDefaultDependencies:
    """Tests for default dependencies handling."""

    def test_uses_empty_list_when_no_dependencies(self, tmp_path):
        """Uses empty list as default dependencies when none specified."""
        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        mock_project = MagicMock()
        mock_project.name = "proj"
        mock_project.path = str(project_dir)
        mock_project.relationship.value = "independent"
        mock_project.dependencies = []
        mock_project.description = None

        mock_manager = MagicMock()
        mock_manager.get_project_state.return_value = None
        mock_manager.add_project.return_value = mock_project
        mock_manager.config.project_count = 1

        with (
            patch("cli.multi_repo_commands.WorkspaceManager") as mock_wm_class,
            patch("cli.multi_repo_commands.print_status"),
            patch("builtins.print"),
        ):
            mock_wm_class.workspace_exists.return_value = True
            mock_wm_class.load_workspace.return_value = mock_manager

            from cli.multi_repo_commands import handle_workspace_add_project_command

            handle_workspace_add_project_command(
                workspace_name="ws",
                project_path=str(project_dir),
                base_dir=tmp_path,
            )

        call_kwargs = mock_manager.add_project.call_args[1]
        assert call_kwargs["dependencies"] == []
