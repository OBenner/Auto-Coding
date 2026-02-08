"""
Template Library
================

Template library manager for browsing, searching, and managing templates.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .generator import SpecGenerator
from .registry import Template, TemplateRegistry


class TemplateLibrary:
    """Manages the template library and provides search/filter capabilities."""

    def __init__(self, custom_templates_dir: Optional[Path] = None):
        """
        Initialize the template library.

        Args:
            custom_templates_dir: Optional directory for custom user templates
        """
        self.registry = TemplateRegistry()
        self.custom_templates_dir = custom_templates_dir
        if custom_templates_dir:
            self._load_custom_templates()

    def get_template(self, name: str) -> Optional[Template]:
        """
        Get a template by name.

        Args:
            name: Template name

        Returns:
            Template instance or None if not found
        """
        return self.registry.get(name)

    def list_templates(
        self, category: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List available templates with optional filtering.

        Args:
            category: Optional category filter
            tags: Optional tag filters

        Returns:
            List of template info dictionaries
        """
        if category:
            templates = self.registry.list_by_category(category)
        else:
            templates = self.registry.list_all()

        # Convert to info dictionaries
        template_info = []
        for template in templates:
            info = {
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "parameters": template.parameters,
            }
            template_info.append(info)

        # Filter by tags if provided
        if tags:
            template_info = [
                t
                for t in template_info
                if any(
                    tag in t.get("tags", []) for tag in tags
                )  # Templates can optionally have tags
            ]

        return template_info

    def get_categories(self) -> List[str]:
        """
        Get all available template categories.

        Returns:
            List of category names
        """
        return self.registry.get_categories()

    def search_templates(self, query: str) -> List[Dict[str, Any]]:
        """
        Search templates by name or description.

        Args:
            query: Search query string

        Returns:
            List of matching template info dictionaries
        """
        all_templates = self.list_templates()
        query_lower = query.lower()

        matches = []
        for template in all_templates:
            if (
                query_lower in template["name"].lower()
                or query_lower in template["description"].lower()
            ):
                matches.append(template)

        return matches

    def create_spec_from_template(
        self, template_name: str, params: Dict[str, Any], spec_dir: Path
    ) -> Dict[str, Any]:
        """
        Create a spec from a template.

        Args:
            template_name: Name of the template to use
            params: Template parameters
            spec_dir: Directory to save the spec to

        Returns:
            Generated spec content

        Raises:
            ValueError: If template not found or parameters invalid
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")

        generator = SpecGenerator(template)
        return generator.generate_spec(params, spec_dir)

    def preview_template(
        self, template_name: str, params: Dict[str, Any]
    ) -> Optional[str]:
        """
        Preview a spec without saving it.

        Args:
            template_name: Name of the template to preview
            params: Template parameters

        Returns:
            Markdown preview of the spec or None if template not found
        """
        template = self.get_template(template_name)
        if not template:
            return None

        generator = SpecGenerator(template)
        return generator.preview_spec(params)

    def save_custom_template(self, template: Template) -> None:
        """
        Save a custom user-created template.

        Args:
            template: Template to save
        """
        self.registry.register(template)

        if self.custom_templates_dir:
            self.custom_templates_dir.mkdir(parents=True, exist_ok=True)
            template_file = self.custom_templates_dir / f"{template.name}.json"

            template_data = {
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "parameters": template.parameters,
            }

            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(template_data, f, indent=2)

    def _load_custom_templates(self) -> None:
        """Load custom templates from disk."""
        if not self.custom_templates_dir or not self.custom_templates_dir.exists():
            return

        for template_file in self.custom_templates_dir.glob("*.json"):
            try:
                with open(template_file, encoding="utf-8") as f:
                    template_data = json.load(f)

                # Note: We'd need to implement a way to reconstruct Template instances
                # from JSON data. For now, we just skip custom templates.
                # This would be implemented when we add custom template creation UI.
            except Exception:
                # Skip invalid template files
                pass


def suggest_templates(project_dir: Path, task_description: str) -> List[str]:
    """
    Suggest templates based on project analysis and task description.

    Args:
        project_dir: Project directory to analyze
        task_description: User's task description

    Returns:
        List of suggested template names
    """
    suggestions = []

    # Analyze task description for keywords
    task_lower = task_description.lower()

    # API-related keywords
    if any(
        keyword in task_lower
        for keyword in ["api", "endpoint", "rest", "graphql", "crud"]
    ):
        suggestions.append("crud_api")

    # Authentication keywords
    if any(
        keyword in task_lower for keyword in ["auth", "login", "signup", "jwt", "oauth"]
    ):
        suggestions.append("authentication")

    # Database keywords
    if any(
        keyword in task_lower
        for keyword in ["database", "migration", "schema", "table", "model"]
    ):
        suggestions.append("database_migration")

    # UI keywords
    if any(
        keyword in task_lower
        for keyword in ["component", "ui", "frontend", "react", "vue", "button", "form"]
    ):
        suggestions.append("ui_component")

    # Testing keywords
    if any(keyword in task_lower for keyword in ["test", "testing", "spec", "unit"]):
        suggestions.append("test_suite")

    # Documentation keywords
    if any(keyword in task_lower for keyword in ["docs", "documentation", "readme"]):
        suggestions.append("documentation")

    return suggestions[:5]  # Return top 5 suggestions
