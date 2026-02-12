"""
Template Storage Layer
======================

File-based storage for custom agent templates.

Stores templates as JSON files in .auto-claude/templates/ directory.
Each template is saved as a separate file named {template-name}.json.

This enables:
- Persistence across sessions
- Version control friendly (git-trackable templates)
- Easy import/export (copy JSON files)
- Simple backup and restoration
"""

import json
from pathlib import Path
from typing import Optional

from agents.templates.models import AgentTemplate


def get_templates_dir(project_dir: Path) -> Path:
    """
    Get the templates directory path for a project.

    Creates the directory if it doesn't exist.

    Args:
        project_dir: Root directory of the project

    Returns:
        Path to .auto-claude/templates/ directory
    """
    templates_dir = project_dir / ".auto-claude" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    return templates_dir


def save_template(template: AgentTemplate, project_dir: Path) -> None:
    """
    Save a template to disk.

    Writes template to .auto-claude/templates/{name}.json

    Args:
        template: AgentTemplate instance to save
        project_dir: Root directory of the project

    Raises:
        ValueError: If template validation fails
        OSError: If file write fails
    """
    # Validate template before saving
    errors = template.validate()
    if errors:
        raise ValueError(f"Cannot save invalid template: {', '.join(errors)}")

    templates_dir = get_templates_dir(project_dir)
    template_file = templates_dir / f"{template.name}.json"

    try:
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise OSError(f"Failed to save template '{template.name}': {e}") from e


def load_template(name: str, project_dir: Path) -> Optional[AgentTemplate]:
    """
    Load a template from disk by name.

    Reads from .auto-claude/templates/{name}.json

    Args:
        name: Template name (without .json extension)
        project_dir: Root directory of the project

    Returns:
        AgentTemplate instance or None if not found
    """
    templates_dir = get_templates_dir(project_dir)
    template_file = templates_dir / f"{name}.json"

    if not template_file.exists():
        return None

    try:
        with open(template_file, encoding="utf-8") as f:
            data = json.load(f)
            return AgentTemplate.from_dict(data)
    except (json.JSONDecodeError, OSError):
        # If file is corrupted or unreadable, return None
        return None


def load_templates(project_dir: Path) -> list[AgentTemplate]:
    """
    Load all templates from disk.

    Scans .auto-claude/templates/ directory and loads all .json files.

    Args:
        project_dir: Root directory of the project

    Returns:
        List of AgentTemplate instances (empty if no templates or directory doesn't exist)
    """
    templates_dir = get_templates_dir(project_dir)

    if not templates_dir.exists():
        return []

    templates = []
    try:
        # Find all .json files in templates directory
        for template_file in templates_dir.glob("*.json"):
            try:
                with open(template_file, encoding="utf-8") as f:
                    data = json.load(f)
                    template = AgentTemplate.from_dict(data)
                    templates.append(template)
            except (json.JSONDecodeError, OSError, KeyError, ValueError):
                # Skip corrupted or invalid template files
                continue
    except OSError:
        # If directory is not accessible, return empty list
        return []

    return templates


def delete_template(name: str, project_dir: Path) -> bool:
    """
    Delete a template from disk.

    Removes .auto-claude/templates/{name}.json

    Args:
        name: Template name (without .json extension)
        project_dir: Root directory of the project

    Returns:
        True if template was found and deleted, False otherwise
    """
    templates_dir = get_templates_dir(project_dir)
    template_file = templates_dir / f"{name}.json"

    if not template_file.exists():
        return False

    try:
        template_file.unlink()
        return True
    except OSError:
        return False


def template_exists(name: str, project_dir: Path) -> bool:
    """
    Check if a template file exists on disk.

    Args:
        name: Template name (without .json extension)
        project_dir: Root directory of the project

    Returns:
        True if template file exists, False otherwise
    """
    templates_dir = get_templates_dir(project_dir)
    template_file = templates_dir / f"{name}.json"
    return template_file.exists()


def list_template_names(project_dir: Path) -> list[str]:
    """
    List all template names (without loading full templates).

    Useful for quick listing without parsing all JSON files.

    Args:
        project_dir: Root directory of the project

    Returns:
        List of template names (without .json extension)
    """
    templates_dir = get_templates_dir(project_dir)

    if not templates_dir.exists():
        return []

    try:
        # Get all .json files and extract names
        return [f.stem for f in templates_dir.glob("*.json")]
    except OSError:
        return []


def export_template(template: AgentTemplate, export_path: Path) -> None:
    """
    Export a template to a specific JSON file path.

    This allows exporting templates to custom locations for sharing,
    backup, or distribution purposes.

    Args:
        template: AgentTemplate instance to export
        export_path: Full path where the template JSON file should be saved

    Raises:
        ValueError: If template validation fails
        OSError: If file write fails
    """
    # Validate template before exporting
    errors = template.validate()
    if errors:
        raise ValueError(f"Cannot export invalid template: {', '.join(errors)}")

    # Create parent directories if they don't exist
    export_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise OSError(f"Failed to export template to '{export_path}': {e}") from e
