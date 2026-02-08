"""
Spec Commands
=============

CLI commands for managing specs (listing, finding, etc.)
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from progress import count_subtasks
from workspace import get_existing_build_worktree

from .utils import get_specs_dir


def list_specs(project_dir: Path) -> list[dict]:
    """
    List all specs in the project.

    Args:
        project_dir: Project root directory

    Returns:
        List of spec info dicts with keys: number, name, path, status, progress
    """
    specs_dir = get_specs_dir(project_dir)
    specs = []

    if not specs_dir.exists():
        return specs

    for spec_folder in sorted(specs_dir.iterdir()):
        if not spec_folder.is_dir():
            continue

        # Parse folder name (e.g., "001-initial-app")
        folder_name = spec_folder.name
        parts = folder_name.split("-", 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue

        number = parts[0]
        name = parts[1]

        # Check for spec.md
        spec_file = spec_folder / "spec.md"
        if not spec_file.exists():
            continue

        # Check for existing build in worktree
        has_build = get_existing_build_worktree(project_dir, folder_name) is not None

        # Check progress via implementation_plan.json
        plan_file = spec_folder / "implementation_plan.json"
        if plan_file.exists():
            completed, total = count_subtasks(spec_folder)
            if total > 0:
                if completed == total:
                    status = "complete"
                else:
                    status = "in_progress"
                progress = f"{completed}/{total}"
            else:
                status = "initialized"
                progress = "0/0"
        else:
            status = "pending"
            progress = "-"

        # Add build indicator
        if has_build:
            status = f"{status} (has build)"

        specs.append(
            {
                "number": number,
                "name": name,
                "folder": folder_name,
                "path": spec_folder,
                "status": status,
                "progress": progress,
                "has_build": has_build,
            }
        )

    return specs


def print_specs_list(project_dir: Path, auto_create: bool = True) -> None:
    """Print a formatted list of all specs.

    Args:
        project_dir: Project root directory
        auto_create: If True and no specs exist, automatically launch spec creation
    """
    import subprocess

    specs = list_specs(project_dir)

    if not specs:
        print("\nNo specs found.")

        if auto_create:
            # Get the backend directory and find spec_runner.py
            backend_dir = Path(__file__).parent.parent
            spec_runner = backend_dir / "runners" / "spec_runner.py"

            # Find Python executable - use current interpreter
            python_path = sys.executable

            if spec_runner.exists() and python_path:
                # Quick prompt for task description
                print("\n" + "=" * 60)
                print("  QUICK START")
                print("=" * 60)
                print("\nWhat do you want to build?")
                print(
                    "(Enter a brief description, or press Enter for interactive mode)\n"
                )

                try:
                    task = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\nCancelled.")
                    return

                if task:
                    # Direct mode: create spec and start building
                    print(f"\nStarting build for: {task}\n")
                    subprocess.run(
                        [
                            python_path,
                            str(spec_runner),
                            "--task",
                            task,
                            "--complexity",
                            "simple",
                            "--auto-approve",
                        ],
                        cwd=project_dir,
                    )
                else:
                    # Interactive mode
                    print("\nLaunching interactive mode...\n")
                    subprocess.run(
                        [python_path, str(spec_runner), "--interactive"],
                        cwd=project_dir,
                    )
                return
            else:
                print("\nCreate your first spec:")
                print("  python runners/spec_runner.py --interactive")
        else:
            print("\nCreate your first spec:")
            print("  python runners/spec_runner.py --interactive")
        return

    print("\n" + "=" * 70)
    print("  AVAILABLE SPECS")
    print("=" * 70)
    print()

    # Status symbols
    status_symbols = {
        "complete": "[OK]",
        "in_progress": "[..]",
        "initialized": "[--]",
        "pending": "[  ]",
    }

    for spec in specs:
        # Get base status for symbol
        base_status = spec["status"].split(" ")[0]
        symbol = status_symbols.get(base_status, "[??]")

        print(f"  {symbol} {spec['folder']}")
        status_line = f"       Status: {spec['status']} | Subtasks: {spec['progress']}"
        print(status_line)
        print()

    print("-" * 70)
    print("\nTo run a spec:")
    print("  python auto-claude/run.py --spec 001")
    print("  python auto-claude/run.py --spec 001-feature-name")
    print()


def list_templates(
    project_dir: Path, category: Optional[str] = None, tags: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    List all available templates with optional filtering.

    Args:
        project_dir: Project root directory
        category: Optional category filter
        tags: Optional tag filters

    Returns:
        List of template info dicts with keys: name, description, category, parameters
    """
    # Import here to avoid import errors if template system is not available
    try:
        from spec.templates.library import TemplateLibrary
    except ImportError:
        return []

    # Create template library
    library = TemplateLibrary()

    # Get templates with optional filtering
    templates = library.list_templates(category=category, tags=tags)

    return templates


def print_templates_list(
    project_dir: Path, category: Optional[str] = None, tags: Optional[List[str]] = None
) -> None:
    """
    Print a formatted list of all available templates.

    Args:
        project_dir: Project root directory
        category: Optional category filter
        tags: Optional tag filters
    """
    templates = list_templates(project_dir, category=category, tags=tags)

    if not templates:
        print("\nNo templates found.")
        return

    print("\n" + "=" * 70)
    print("  AVAILABLE TEMPLATES")
    print("=" * 70)
    print()

    # Group templates by category
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for template in templates:
        cat = template.get("category", "General")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(template)

    # Print templates grouped by category
    for cat_name, cat_templates in sorted(categories.items()):
        print(f"  {cat_name}")
        print(f"  {'-' * 70}")

        for template in cat_templates:
            name = template.get("name", "Unknown")
            description = template.get("description", "")

            print(f"    • {name}")
            if description:
                # Wrap description if too long
                if len(description) > 60:
                    desc_lines = [
                        description[i : i + 60] for i in range(0, len(description), 60)
                    ]
                    print(f"      {desc_lines[0]}")
                    for line in desc_lines[1:]:
                        print(f"      {line}")
                else:
                    print(f"      {description}")
            print()

    print("-" * 70)
    print()
    print(f"Total: {len(templates)} template(s)")
    print()


def show_template_info(project_dir: Path, template_name: str) -> None:
    """
    Show detailed information about a specific template.

    Args:
        project_dir: Project root directory
        template_name: Name of the template to show
    """
    # Import here to avoid import errors if template system is not available
    try:
        from spec.templates.library import TemplateLibrary
    except ImportError:
        print("\nTemplate system not available.")
        return

    library = TemplateLibrary()
    template = library.get_template(template_name)

    if not template:
        print(f"\nTemplate not found: {template_name}")
        return

    print("\n" + "=" * 70)
    print(f"  TEMPLATE: {template.name}")
    print("=" * 70)
    print()

    print(f"Category: {template.category}")
    print()
    print("Description:")
    print(f"  {template.description}")
    print()

    if template.parameters:
        print("Parameters:")
        for param_name, param_info in template.parameters.items():
            param_type = param_info.get("type", "string")
            param_desc = param_info.get("description", "")
            required = param_info.get("required", False)

            req_marker = " (required)" if required else " (optional)"
            print(f"  • {param_name}: {param_type}{req_marker}")
            if param_desc:
                print(f"    {param_desc}")
        print()
    else:
        print("Parameters: None (template uses defaults)")
        print()

    print("-" * 70)
    print()


def preview_template_spec(
    project_dir: Path, template_name: str, params: Dict[str, Any]
) -> None:
    """
    Preview a generated spec from a template without saving it.

    Args:
        project_dir: Project root directory
        template_name: Name of the template to preview
        params: Template parameters
    """
    # Import here to avoid import errors if template system is not available
    try:
        from spec.templates.library import TemplateLibrary
    except ImportError:
        print("\nTemplate system not available.")
        return

    library = TemplateLibrary()
    preview = library.preview_template(template_name, params)

    if not preview:
        print(f"\nTemplate not found: {template_name}")
        return

    print("\n" + "=" * 70)
    print(f"  SPEC PREVIEW: {template_name}")
    print("=" * 70)
    print()
    print(preview)
    print()
    print("-" * 70)
    print()
