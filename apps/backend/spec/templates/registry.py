"""
Template Registry
=================

Template base classes and registry for managing spec templates.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class Template(ABC):
    """Base class for all spec templates."""

    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        parameters: dict[str, Any],
        placeholders: Optional[list[str]] = None,
    ):
        """
        Initialize a template.

        Args:
            name: Unique template identifier
            description: Human-readable description
            category: Template category (e.g., 'api', 'ui', 'database')
            parameters: Parameter definitions with types and defaults
            placeholders: Optional list of placeholder names used in this template
        """
        self.name = name
        self.description = description
        self.category = category
        self.parameters = parameters
        self.placeholders = placeholders or []

    @abstractmethod
    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Generate spec content from template parameters.

        Args:
            params: User-provided parameter values

        Returns:
            Dictionary containing spec content
        """
        pass

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """
        Validate user-provided parameters.

        Args:
            params: User-provided parameter values

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        for param_name, param_def in self.parameters.items():
            required = param_def.get("required", False)
            if required and param_name not in params:
                errors.append(f"Missing required parameter: {param_name}")
            elif param_name in params:
                param_type = param_def.get("type")
                if param_type and not isinstance(params[param_name], param_type):
                    errors.append(
                        f"Invalid type for {param_name}: expected {param_type.__name__}"
                    )
        return errors

    def get_placeholders(self) -> list[str]:
        """
        Get all placeholders used in this template.

        Returns:
            List of unique placeholder names (without braces)

        Note:
            If placeholders were explicitly defined during initialization,
            those are returned. Otherwise, attempts to extract placeholders
            from a sample template generation.
        """
        # If placeholders were explicitly defined, use those
        if self.placeholders:
            return self.placeholders

        # Otherwise, try to extract from a sample generation
        try:
            # Import here to avoid circular dependency
            from .placeholders import PlaceholderParser

            parser = PlaceholderParser()

            # Build default params for sample generation
            sample_params = {}
            for param_name, param_def in self.parameters.items():
                if "default" in param_def:
                    sample_params[param_name] = param_def["default"]
                else:
                    # Provide a sample value based on type
                    param_type = param_def.get("type", str)
                    if param_type == str:
                        sample_params[param_name] = "sample"
                    elif param_type == bool:
                        sample_params[param_name] = False
                    elif param_type == list:
                        sample_params[param_name] = ["sample"]
                    elif param_type == dict:
                        sample_params[param_name] = {}
                    else:
                        sample_params[param_name] = None

            # Generate sample content
            content = self.generate(sample_params)

            # Extract placeholders from all string values in content
            placeholders = set()
            self._extract_placeholders_recursive(content, parser, placeholders)

            return sorted(placeholders)

        except Exception:
            # If extraction fails, return empty list
            return []

    def _extract_placeholders_recursive(
        self, obj: Any, parser: Any, placeholders: set[str]
    ) -> None:
        """
        Recursively extract placeholders from an object.

        Args:
            obj: Object to extract from (dict, list, str, etc.)
            parser: PlaceholderParser instance
            placeholders: Set to accumulate unique placeholder names
        """
        if isinstance(obj, str):
            # Extract from string
            found = parser.extract_placeholders(obj)
            placeholders.update(found)
        elif isinstance(obj, dict):
            # Recursively process dictionary values
            for value in obj.values():
                self._extract_placeholders_recursive(value, parser, placeholders)
        elif isinstance(obj, list):
            # Recursively process list items
            for item in obj:
                self._extract_placeholders_recursive(item, parser, placeholders)


class TemplateRegistry:
    """Registry for managing spec templates."""

    _instance: Optional["TemplateRegistry"] = None
    _templates: dict[str, Template] = {}

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._templates = {}
        return cls._instance

    def register(self, template: Template) -> None:
        """
        Register a template.

        Args:
            template: Template instance to register
        """
        self._templates[template.name] = template

    def get(self, name: str) -> Template | None:
        """
        Get template by name.

        Args:
            name: Template name

        Returns:
            Template instance or None if not found
        """
        return self._templates.get(name)

    def list_all(self) -> list[Template]:
        """
        List all registered templates.

        Returns:
            List of all templates
        """
        return list(self._templates.values())

    def list_by_category(self, category: str) -> list[Template]:
        """
        List templates by category.

        Args:
            category: Template category

        Returns:
            List of templates in the category
        """
        return [t for t in self._templates.values() if t.category == category]

    def get_categories(self) -> list[str]:
        """
        Get all unique template categories.

        Returns:
            List of category names
        """
        return list(set(t.category for t in self._templates.values()))

    def clear(self) -> None:
        """Clear all registered templates (mainly for testing)."""
        self._templates.clear()
