"""
Spec Commands
=============

CLI commands for managing specs (listing, finding, etc.)
"""

import json
import sys
from pathlib import Path
from typing import Any

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from progress import count_subtasks
from ui import Icons, box, icon, muted, print_status
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
    project_dir: Path, category: str | None = None, tags: list[str] | None = None
) -> list[dict[str, Any]]:
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
    project_dir: Path, category: str | None = None, tags: list[str] | None = None
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
    categories: dict[str, list[dict[str, Any]]] = {}
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
    project_dir: Path, template_name: str, params: dict[str, Any]
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


def validate_template_command(
    project_dir: Path, template_name: str, strict: bool = True
) -> None:
    """
    Validate a spec template for security and correctness.

    Args:
        project_dir: Project root directory
        template_name: Name of the template to validate
        strict: If True, fail on warnings. If False, allow warnings.
    """
    # Import here to avoid import errors if template system is not available
    try:
        from spec.templates.library import TemplateLibrary
        from spec.templates.validator import validate_template
    except ImportError:
        print("\nTemplate system not available.")
        sys.exit(1)

    library = TemplateLibrary()
    template = library.get_template(template_name)

    if not template:
        print(f"\n✗ Template not found: {template_name}")
        print("\nAvailable templates:")
        templates = library.list_templates()
        for tmpl in templates:
            print(f"  • {tmpl['name']}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print(f"  VALIDATING TEMPLATE: {template_name}")
    print("=" * 80)
    print()

    # Run validation
    is_valid, errors = validate_template(template, strict=strict)

    if is_valid:
        print("✓ Template is valid!")
        print()

        # Show summary
        print("Summary:")
        print(f"  Name: {template.name}")
        print(f"  Category: {template.category}")
        print(f"  Description: {template.description[:80]}...")
        if template.parameters:
            print(f"  Parameters: {len(template.parameters)}")
        if template.placeholders:
            print(f"  Placeholders: {len(template.placeholders)}")
        print()

        # Show parameters
        if template.parameters:
            print("Parameters:")
            for param_name, param_def in template.parameters.items():
                param_type = param_def.get("type", str)
                type_name = param_type.__name__ if hasattr(param_type, "__name__") else str(param_type)
                required = param_def.get("required", False)
                req_marker = " (required)" if required else " (optional)"
                print(f"  • {param_name}: {type_name}{req_marker}")
            print()

        # Show placeholders
        if template.placeholders:
            print(f"Placeholders: {', '.join(template.placeholders)}")
            print()

        print("-" * 80)
        print()
        sys.exit(0)
    else:
        print("✗ Template validation failed!")
        print()

        # Show errors
        print("Errors:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        print()

        print("-" * 80)
        print()
        sys.exit(1)


def export_template_command(
    project_dir: Path, template_name: str, output_file: str | None = None
) -> None:
    """
    Export a spec template to JSON format.

    Args:
        project_dir: Project root directory
        template_name: Name of the template to export
        output_file: Optional output file path (defaults to template_name.json)
    """
    # Import here to avoid import errors if template system is not available
    try:
        from spec.templates.library import TemplateLibrary
        from spec.templates.io import export_template
    except ImportError:
        print("\nTemplate system not available.")
        sys.exit(1)

    library = TemplateLibrary()
    template = library.get_template(template_name)

    if not template:
        print(f"\n✗ Template not found: {template_name}")
        print("\nAvailable templates:")
        templates = library.list_templates()
        for tmpl in templates:
            print(f"  • {tmpl['name']}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print(f"  EXPORTING TEMPLATE: {template_name}")
    print("=" * 80)
    print()

    # Export template to dictionary
    try:
        export_data = export_template(template)
    except Exception as e:
        print(f"✗ Failed to export template: {e}")
        sys.exit(1)

    # Determine output file path
    if output_file:
        output_path = Path(output_file)
    else:
        output_path = Path(f"{template_name}.json")

    # Create parent directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Template exported successfully!")
        print()
        print(f"Output file: {output_path.absolute()}")
        print(f"File size: {output_path.stat().st_size} bytes")
        print()
    except Exception as e:
        print(f"✗ Failed to write export file: {e}")
        sys.exit(1)

    print("-" * 80)
    print()


def import_template_command(
    project_dir: Path, input_file: str, validate: bool = True
) -> None:
    """
    Import a spec template from JSON format.

    Args:
        project_dir: Project root directory
        input_file: Path to the JSON file to import
        validate: If True, validate template before importing
    """
    # Import here to avoid import errors if template system is not available
    try:
        from spec.templates.io import import_template
        from spec.templates.validator import validate_import
    except ImportError:
        print("\nTemplate system not available.")
        sys.exit(1)

    input_path = Path(input_file)

    if not input_path.exists():
        print(f"\n✗ Template file not found: {input_file}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print(f"  IMPORTING TEMPLATE FROM: {input_path.name}")
    print("=" * 80)
    print()

    # Read JSON file
    try:
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON format: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Failed to read file: {e}")
        sys.exit(1)

    # Validate template data before importing
    if validate:
        is_valid, errors = validate_import(data)
        if not is_valid:
            print("✗ Template validation failed!")
            print()
            print("Errors:")
            for i, error in enumerate(errors, 1):
                print(f"  {i}. {error}")
            print()
            print("-" * 80)
            print()
            sys.exit(1)

    # Import template
    try:
        template = import_template(data)
    except Exception as e:
        print(f"✗ Failed to import template: {e}")
        sys.exit(1)

    print("✓ Template imported successfully!")
    print()

    # Show summary
    print("Template details:")
    print(f"  Name: {template.name}")
    print(f"  Category: {template.category}")
    print(f"  Description: {template.description[:80]}...")
    if template.parameters:
        print(f"  Parameters: {len(template.parameters)}")
    if template.placeholders:
        print(f"  Placeholders: {len(template.placeholders)}")
    print()

    # Save to custom templates directory
    custom_templates_dir = project_dir / ".auto-claude" / "templates"
    custom_templates_dir.mkdir(parents=True, exist_ok=True)

    output_path = custom_templates_dir / f"{template.name}.json"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved to: {output_path.absolute()}")
    except Exception as e:
        print(f"Warning: Failed to save template to custom directory: {e}")

    print()
    print("-" * 80)
    print()


def prompt_for_template_parameters(template: Any) -> dict[str, Any] | None:
    """
    Interactively prompt the user for template parameter values.

    Shows each parameter's description, type, default value, and whether it's required.
    Validates input types and provides helpful error messages.

    Args:
        template: Template object with parameters to collect

    Returns:
        Dictionary of parameter values, or None if cancelled
    """
    print()
    print("=" * 80)
    print("  TEMPLATE PARAMETERS")
    print("=" * 80)
    print()
    print(f"{icon(Icons.INFO)} Template: {template.name}")
    print(f"{icon(Icons.INFO)} {template.description}")
    print()

    if not template.parameters:
        print(f"{icon(Icons.INFO)} This template has no parameters.")
        print()
        return {}

    print(
        muted(
            f"Please provide values for {len(template.parameters)} parameter(s). Press Ctrl+C to cancel."
        )
    )
    print()

    params = {}

    for param_name, param_def in template.parameters.items():
        param_type = param_def.get("type", str)
        required = param_def.get("required", False)
        default = param_def.get("default")
        description = param_def.get("description", "")

        # Display parameter info
        print("-" * 80)
        print()
        print(f"{icon(Icons.POINTER)} {param_name}")
        if description:
            print(f"   {description}")
        print(f"   Type: {param_type.__name__}")
        if required:
            print(f"   {icon(Icons.WARNING)} Required")
        if default is not None:
            print(f"   Default: {default}")
        print()

        # Prompt based on type
        while True:
            try:
                if param_type == bool:
                    # Boolean parameters - yes/no prompt
                    default_str = "y" if default else "n"
                    prompt = f"   {icon(Icons.EDIT)} Enter value (y/n)"
                    if default is not None:
                        prompt += f" [{default_str}]"
                    prompt += ": "

                    user_input = input(prompt).strip().lower()

                    if not user_input and default is not None:
                        params[param_name] = default
                        break
                    elif not user_input and not required:
                        # Skip optional parameter with no default
                        break
                    elif user_input in ["y", "yes", "true", "1"]:
                        params[param_name] = True
                        break
                    elif user_input in ["n", "no", "false", "0"]:
                        params[param_name] = False
                        break
                    else:
                        print(
                            f"   {icon(Icons.WARNING)} Invalid input. Please enter 'y' or 'n'."
                        )

                elif param_type == int:
                    # Integer parameters
                    prompt = f"   {icon(Icons.EDIT)} Enter value"
                    if default is not None:
                        prompt += f" [{default}]"
                    prompt += ": "

                    user_input = input(prompt).strip()

                    if not user_input and default is not None:
                        params[param_name] = default
                        break
                    elif not user_input and not required:
                        # Skip optional parameter with no default
                        break
                    else:
                        try:
                            params[param_name] = int(user_input)
                            break
                        except ValueError:
                            print(
                                f"   {icon(Icons.WARNING)} Invalid input. Please enter a number."
                            )

                elif param_type == list:
                    # List parameters - comma-separated values
                    prompt = f"   {icon(Icons.EDIT)} Enter values (comma-separated)"
                    if default is not None:
                        default_str = ", ".join(str(v) for v in default)
                        prompt += f" [{default_str}]"
                    prompt += ": "

                    user_input = input(prompt).strip()

                    if not user_input and default is not None:
                        params[param_name] = default
                        break
                    elif not user_input and not required:
                        # Skip optional parameter with no default
                        break
                    else:
                        # Split by comma and strip whitespace
                        values = [v.strip() for v in user_input.split(",") if v.strip()]
                        params[param_name] = values
                        break

                else:  # Default to string
                    # String parameters
                    prompt = f"   {icon(Icons.EDIT)} Enter value"
                    if default is not None:
                        prompt += f" [{default}]"
                    prompt += ": "

                    user_input = input(prompt).strip()

                    if not user_input and default is not None:
                        params[param_name] = default
                        break
                    elif not user_input and not required:
                        # Skip optional parameter with no default
                        break
                    elif user_input:
                        params[param_name] = user_input
                        break
                    elif required:
                        print(
                            f"   {icon(Icons.WARNING)} This parameter is required. Please provide a value."
                        )

            except (KeyboardInterrupt, EOFError):
                print()
                print()
                print_status("Parameter collection cancelled.", "warning")
                return None

        print()

    print("=" * 80)
    print(f"{icon(Icons.CHECK)} Parameters collected successfully!")
    print()

    # Show summary
    print("Summary:")
    for param_name, value in params.items():
        print(f"  {param_name}: {value}")
    print()

    return params
