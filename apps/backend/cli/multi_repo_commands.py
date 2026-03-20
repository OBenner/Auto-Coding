"""
Multi-Repo Commands
====================

CLI commands for multi-repository workspace management.

Handles:
- workspace create: Create a new multi-repo workspace
- workspace list: List all existing workspaces
- workspace add-project: Add a project to an existing workspace
"""

import sys
from pathlib import Path

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from core.workspace_config import ProjectRelationship
from core.workspace_manager import WorkspaceManager
from ui import highlight, print_status

from .utils import print_banner


def handle_workspace_create_command(
    name: str,
    description: str | None = None,
    base_dir: Path | None = None,
) -> bool:
    """
    Create a new multi-repo workspace.

    Args:
        name: Name for the new workspace
        description: Optional description of the workspace
        base_dir: Base directory for workspace state (defaults to .auto-claude/workspaces)

    Returns:
        True if workspace was created successfully, False otherwise
    """
    print_banner()

    base_dir = base_dir or Path(".auto-claude/workspaces")

    # Check if workspace already exists
    if WorkspaceManager.workspace_exists(name, base_dir):
        print_status(f"Workspace '{name}' already exists", "error")
        print(f"  Location: {base_dir / name}")
        print()
        print("To list workspaces: python run.py --workspace-list")
        return False

    try:
        manager = WorkspaceManager.create_workspace(
            name=name,
            base_dir=base_dir,
            description=description,
        )

        print_status(f"Workspace '{name}' created successfully", "success")
        print()
        print(f"  Location:    {manager.workspace_dir}")
        if description:
            print(f"  Description: {description}")
        print(f"  Projects:    0 (use --workspace-add-project to add projects)")
        print()
        print("Next steps:")
        print(f"  Add a project:  python run.py --workspace-add-project {name} <path>")
        print(f"  List workspaces: python run.py --workspace-list")
        return True

    except ValueError as e:
        print_status(f"Failed to create workspace: {e}", "error")
        return False
    except OSError as e:
        print_status(f"File system error creating workspace: {e}", "error")
        return False


def handle_workspace_list_command(
    base_dir: Path | None = None,
) -> bool:
    """
    List all existing multi-repo workspaces.

    Args:
        base_dir: Base directory to search for workspaces (defaults to .auto-claude/workspaces)

    Returns:
        True if listing succeeded (even if no workspaces found), False on error
    """
    base_dir = base_dir or Path(".auto-claude/workspaces")

    if not base_dir.exists():
        print_status("No workspaces found", "info")
        print()
        print("Create a workspace: python run.py --workspace-create <name>")
        return True

    workspaces = []
    for entry in sorted(base_dir.iterdir()):
        if entry.is_dir() and (entry / "workspace.json").exists():
            workspaces.append(entry)

    if not workspaces:
        print_status("No workspaces found", "info")
        print()
        print("Create a workspace: python run.py --workspace-create <name>")
        return True

    print()
    print(highlight(f"Multi-Repo Workspaces ({len(workspaces)} found)"))
    print()

    for workspace_path in workspaces:
        try:
            manager = WorkspaceManager.load_workspace(workspace_path)
            stats = manager.get_workspace_stats()

            print(f"  {highlight(stats['name'])}")
            if manager.config.description:
                print(f"    Description: {manager.config.description}")
            print(f"    Projects:    {stats['total_projects']} total, {stats['enabled_projects']} enabled")
            if stats["project_names"]:
                print(f"    Project names: {', '.join(stats['project_names'])}")
            print(f"    Location:    {workspace_path}")
            print()

        except (FileNotFoundError, ValueError, KeyError) as e:
            print(f"  {workspace_path.name} (error loading: {e})")
            print()

    print("Commands:")
    print("  Add project:   python run.py --workspace-add-project <workspace> <path>")
    print("  Create new:    python run.py --workspace-create <name>")
    return True


def handle_workspace_add_project_command(
    workspace_name: str,
    project_path: str,
    project_name: str | None = None,
    relationship: str = "independent",
    dependencies: list[str] | None = None,
    description: str | None = None,
    base_dir: Path | None = None,
) -> bool:
    """
    Add a project to an existing multi-repo workspace.

    Args:
        workspace_name: Name of the workspace to add project to
        project_path: Path to the project directory
        project_name: Optional name for the project (defaults to directory name)
        relationship: Relationship type (independent, depends_on, library, monorepo_package)
        dependencies: List of project names this depends on
        description: Optional description of the project
        base_dir: Base directory for workspaces (defaults to .auto-claude/workspaces)

    Returns:
        True if project was added successfully, False otherwise
    """
    base_dir = base_dir or Path(".auto-claude/workspaces")

    # Validate workspace exists
    if not WorkspaceManager.workspace_exists(workspace_name, base_dir):
        print_status(f"Workspace '{workspace_name}' not found", "error")
        print()
        print("To list workspaces: python run.py --workspace-list")
        print("To create a workspace: python run.py --workspace-create <name>")
        return False

    # Resolve project path
    resolved_path = Path(project_path).resolve()
    if not resolved_path.exists():
        print_status(f"Project path does not exist: {project_path}", "error")
        return False

    if not resolved_path.is_dir():
        print_status(f"Project path is not a directory: {project_path}", "error")
        return False

    # Default project name to directory name
    if not project_name:
        project_name = resolved_path.name

    # Validate relationship type
    try:
        rel = ProjectRelationship(relationship)
    except ValueError:
        valid_rels = [r.value for r in ProjectRelationship]
        print_status(f"Invalid relationship '{relationship}'", "error")
        print(f"  Valid values: {', '.join(valid_rels)}")
        return False

    try:
        workspace_dir = base_dir / workspace_name
        manager = WorkspaceManager.load_workspace(workspace_dir)

        # Check if project name already exists
        existing = manager.get_project_state(project_name)
        if existing:
            print_status(f"Project '{project_name}' already exists in workspace '{workspace_name}'", "error")
            return False

        project = manager.add_project(
            name=project_name,
            path=str(resolved_path),
            relationship=rel,
            dependencies=dependencies or [],
            description=description,
        )

        # Save workspace after adding project
        manager.save()

        print_status(f"Project '{project_name}' added to workspace '{workspace_name}'", "success")
        print()
        print(f"  Project:      {project.name}")
        print(f"  Path:         {project.path}")
        print(f"  Relationship: {project.relationship.value}")
        if project.dependencies:
            print(f"  Depends on:   {', '.join(project.dependencies)}")
        if project.description:
            print(f"  Description:  {project.description}")
        print()
        print(f"  Workspace now has {manager.config.project_count} project(s)")
        return True

    except FileNotFoundError as e:
        print_status(f"Workspace not found: {e}", "error")
        return False
    except ValueError as e:
        print_status(f"Failed to add project: {e}", "error")
        return False
    except OSError as e:
        print_status(f"File system error adding project: {e}", "error")
        return False
