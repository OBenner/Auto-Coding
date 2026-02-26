"""
Agent Template Registry
=======================

Registry for managing custom agent templates.

Provides a singleton registry for storing, retrieving, and managing
custom agent templates. Templates can be filtered by category and listed
for use in the agent system.
"""

import threading
from typing import Optional

from agents.templates.models import AgentTemplate


class AgentTemplateRegistry:
    """Registry for managing agent templates."""

    _instance: Optional["AgentTemplateRegistry"] = None
    _templates: dict[str, AgentTemplate] = {}
    _lock: threading.Lock = threading.Lock()

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._templates = {}
        return cls._instance

    def register(self, template: AgentTemplate) -> None:
        """
        Register an agent template.

        Args:
            template: AgentTemplate instance to register

        Raises:
            ValueError: If template validation fails
        """
        # Validate template before registering
        errors = template.validate()
        if errors:
            raise ValueError(f"Template validation failed: {', '.join(errors)}")

        with self._lock:
            self._templates[template.name] = template

    def get(self, name: str) -> AgentTemplate | None:
        """
        Get template by name.

        Args:
            name: Template name

        Returns:
            AgentTemplate instance or None if not found
        """
        return self._templates.get(name)

    def list_all(self) -> list[AgentTemplate]:
        """
        List all registered templates.

        Returns:
            List of all templates
        """
        return list(self._templates.values())

    def list_by_category(self, category: str) -> list[AgentTemplate]:
        """
        List templates by category.

        Args:
            category: Template category (e.g., 'testing', 'documentation')

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

    def list_by_tag(self, tag: str) -> list[AgentTemplate]:
        """
        List templates by tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of templates with the specified tag
        """
        return [t for t in self._templates.values() if tag in t.tags]

    def search(self, query: str) -> list[AgentTemplate]:
        """
        Search templates by name, description, or tags.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching templates
        """
        query_lower = query.lower()
        results = []
        for template in self._templates.values():
            if (
                query_lower in template.name.lower()
                or query_lower in template.description.lower()
                or any(query_lower in tag.lower() for tag in template.tags)
            ):
                results.append(template)
        return results

    def update(self, template: AgentTemplate) -> None:
        """
        Update an existing template.

        Args:
            template: Updated AgentTemplate instance

        Raises:
            ValueError: If template validation fails or template doesn't exist
        """
        with self._lock:
            if template.name not in self._templates:
                raise ValueError(f"Template '{template.name}' not found in registry")

            # Validate template before updating
            errors = template.validate()
            if errors:
                raise ValueError(f"Template validation failed: {', '.join(errors)}")

            # Update timestamp
            template.update_timestamp()
            self._templates[template.name] = template

    def unregister(self, name: str) -> bool:
        """
        Unregister a template.

        Args:
            name: Template name to unregister

        Returns:
            True if template was found and removed, False otherwise
        """
        with self._lock:
            if name in self._templates:
                del self._templates[name]
                return True
            return False

    def exists(self, name: str) -> bool:
        """
        Check if a template exists in the registry.

        Args:
            name: Template name to check

        Returns:
            True if template exists, False otherwise
        """
        return name in self._templates

    def clear(self) -> None:
        """Clear all registered templates (mainly for testing)."""
        with self._lock:
            self._templates.clear()
