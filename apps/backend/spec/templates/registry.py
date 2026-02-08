"""
Template Registry
=================

Template base classes and registry for managing spec templates.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Template(ABC):
    """Base class for all spec templates."""

    def __init__(
        self,
        name: str,
        description: str,
        category: str,
        parameters: Dict[str, Any],
    ):
        """
        Initialize a template.

        Args:
            name: Unique template identifier
            description: Human-readable description
            category: Template category (e.g., 'api', 'ui', 'database')
            parameters: Parameter definitions with types and defaults
        """
        self.name = name
        self.description = description
        self.category = category
        self.parameters = parameters

    @abstractmethod
    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate spec content from template parameters.

        Args:
            params: User-provided parameter values

        Returns:
            Dictionary containing spec content
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
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


class TemplateRegistry:
    """Registry for managing spec templates."""

    _instance: Optional["TemplateRegistry"] = None
    _templates: Dict[str, Template] = {}

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

    def get(self, name: str) -> Optional[Template]:
        """
        Get template by name.

        Args:
            name: Template name

        Returns:
            Template instance or None if not found
        """
        return self._templates.get(name)

    def list_all(self) -> List[Template]:
        """
        List all registered templates.

        Returns:
            List of all templates
        """
        return list(self._templates.values())

    def list_by_category(self, category: str) -> List[Template]:
        """
        List templates by category.

        Args:
            category: Template category

        Returns:
            List of templates in the category
        """
        return [t for t in self._templates.values() if t.category == category]

    def get_categories(self) -> List[str]:
        """
        Get all unique template categories.

        Returns:
            List of category names
        """
        return list(set(t.category for t in self._templates.values()))

    def clear(self) -> None:
        """Clear all registered templates (mainly for testing)."""
        self._templates.clear()
