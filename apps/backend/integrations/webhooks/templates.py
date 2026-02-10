"""
Webhook Template Engine
=======================

Template rendering system for webhook payloads.
Supports built-in templates for Slack, Discord, Teams, and generic webhooks.

Design Principles:
- Simple: Uses Python string formatting for variable substitution
- Extensible: Easy to add custom templates
- Type-safe: Template validation before rendering
- Service-aware: Optimized templates for popular webhook services

Template Variables:
  {event} - Event type (e.g., "build_started")
  {event_title} - Human-readable event title (e.g., "Build Started")
  {spec_id} - Spec identifier
  {spec_title} - Spec title
  {spec_directory} - Spec directory path
  {project_directory} - Project directory path
  {timestamp} - ISO format timestamp
  {status} - Status message (if applicable)
  {description} - Event description
  {webhook_id} - Webhook ID
  {webhook_name} - Webhook name
  ... plus any event-specific variables

Usage:
  engine = TemplateEngine()
  payload = engine.render("slack", context={"event": "build_started", ...})
"""

from __future__ import annotations

import re
from string import Formatter
from typing import Any


class TemplateEngine:
    """
    Engine for rendering webhook payload templates.

    Supports variable substitution and built-in templates
    for popular webhook services (Slack, Discord, Teams, etc.).

    Template variables use Python format() syntax:
      {event}, {spec_id}, {timestamp}, etc.
    """

    # Built-in templates for different services
    BUILTIN_TEMPLATES: dict[str, dict[str, Any]] = {
        "generic": {
            "event": "{event}",
            "timestamp": "{timestamp}",
            "spec": {
                "id": "{spec_id}",
                "title": "{spec_title}",
                "directory": "{spec_directory}",
            },
            "project": {
                "directory": "{project_directory}",
            },
            "webhook": {
                "id": "{webhook_id}",
                "name": "{webhook_name}",
            },
            "data": "{data_json}",
        },
        "slack": {
            "text": "Auto-Claude Event: {event}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "{event_title}",
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": "*Spec:*\n{spec_id}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": "*Status:*\n{status}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "{description}",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Timestamp: {timestamp}",
                        },
                    ],
                },
            ],
        },
        "discord": {
            "content": "",
            "embeds": [
                {
                    "title": "{event_title}",
                    "description": "{description}",
                    "color": 5814783,  # Blue
                    "fields": [
                        {
                            "name": "Spec ID",
                            "value": "{spec_id}",
                            "inline": True,
                        },
                        {
                            "name": "Status",
                            "value": "{status}",
                            "inline": True,
                        },
                        {
                            "name": "Spec Title",
                            "value": "{spec_title}",
                            "inline": False,
                        },
                    ],
                    "timestamp": "{timestamp}",
                    "footer": {
                        "text": "Auto-Claude Webhook",
                    },
                }
            ],
            "username": "Auto-Claude",
        },
        "teams": {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "type": "AdaptiveCard",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": "{event_title}",
                                "weight": "Bolder",
                                "size": "Large",
                            },
                            {
                                "type": "TextBlock",
                                "text": "{description}",
                                "wrap": True,
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {
                                        "title": "Spec ID",
                                        "value": "{spec_id}",
                                    },
                                    {
                                        "title": "Status",
                                        "value": "{status}",
                                    },
                                    {
                                        "title": "Timestamp",
                                        "value": "{timestamp}",
                                    },
                                ],
                            },
                        ],
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.4",
                    },
                }
            ],
        },
        "jira": {
            "body": "{description}\n\n---\n*Event: {event}*\n*Spec: {spec_id}*\n*Timestamp: {timestamp}*",
        },
    }

    def __init__(self) -> None:
        """Initialize the template engine."""
        self._custom_templates: dict[str, dict[str, Any]] = {}

    def register_template(
        self,
        name: str,
        template: dict[str, Any],
    ) -> None:
        """
        Register a custom template.

        Args:
            name: Template name
            template: Template dictionary with format placeholders

        Raises:
            ValueError: If template name is invalid or template is malformed
        """
        if not name or not isinstance(name, str):
            raise ValueError("Template name must be a non-empty string")

        if not isinstance(template, dict):
            raise ValueError("Template must be a dictionary")

        # Validate template has at least one placeholder
        if not self._extract_placeholders(template):
            raise ValueError(
                "Template must contain at least one placeholder "
                "(e.g., '{event}')"
            )

        self._custom_templates[name] = template

    def get_template(self, name: str) -> dict[str, Any] | None:
        """
        Get a template by name.

        Checks custom templates first, then built-in templates.

        Args:
            name: Template name

        Returns:
            Template dictionary or None if not found
        """
        # Check custom templates first
        if name in self._custom_templates:
            return self._custom_templates[name]

        # Fall back to built-in templates
        return self.BUILTIN_TEMPLATES.get(name)

    def list_templates(self) -> list[str]:
        """
        List all available template names.

        Returns:
            List of template names (built-in + custom)
        """
        builtin = list(self.BUILTIN_TEMPLATES.keys())
        custom = list(self._custom_templates.keys())
        return builtin + custom

    def render(
        self,
        template: str | dict[str, Any],
        context: dict[str, Any],
        *,
        strict: bool = False,
    ) -> dict[str, Any]:
        """
        Render a template with the given context.

        Args:
            template: Template name or template dictionary
            context: Variables to substitute into the template
            strict: If True, raise error on missing variables;
                    If False, leave placeholders as-is (default)

        Returns:
            Rendered payload dictionary

        Raises:
            ValueError: If template not found or rendering fails
        """
        # Resolve template
        if isinstance(template, str):
            template_dict = self.get_template(template)
            if template_dict is None:
                raise ValueError(f"Template not found: {template}")
        elif isinstance(template, dict):
            template_dict = template
        else:
            raise ValueError(
                "Template must be a string (name) or dictionary"
            )

        # Render template
        try:
            return self._render_dict(template_dict, context, strict)
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Failed to render template: {e}") from e

    def validate_template(
        self,
        template: dict[str, Any],
    ) -> list[str]:
        """
        Validate a template and return any issues.

        Args:
            template: Template dictionary to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not isinstance(template, dict):
            errors.append("Template must be a dictionary")
            return errors

        # Check if template has any placeholders
        placeholders = self._extract_placeholders(template)
        if not placeholders:
            errors.append(
                "Template must contain at least one placeholder "
                "(e.g., '{event}')"
            )

        # Check for invalid placeholder syntax
        for placeholder in placeholders:
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", placeholder):
                errors.append(
                    f"Invalid placeholder name: {{{placeholder}}}. "
                    "Must be a valid Python identifier"
                )

        return errors

    def extract_required_variables(
        self,
        template: str | dict[str, Any],
    ) -> set[str]:
        """
        Extract required variables from a template.

        Args:
            template: Template name or dictionary

        Returns:
            Set of variable names required by the template
        """
        # Resolve template
        if isinstance(template, str):
            template_dict = self.get_template(template)
            if template_dict is None:
                return set()
        elif isinstance(template, dict):
            template_dict = template
        else:
            return set()

        # Extract placeholders
        return set(self._extract_placeholders(template_dict))

    def _render_dict(
        self,
        data: Any,
        context: dict[str, Any],
        strict: bool,
    ) -> Any:
        """
        Recursively render a dictionary template.

        Args:
            data: Template data (dict, list, or string)
            context: Variables for substitution
            strict: Whether to raise error on missing variables

        Returns:
            Rendered data structure
        """
        if isinstance(data, dict):
            return {
                key: self._render_dict(value, context, strict)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [
                self._render_dict(item, context, strict)
                for item in data
            ]
        elif isinstance(data, str):
            return self._render_string(data, context, strict)
        else:
            # Numbers, booleans, None - return as-is
            return data

    def _render_string(
        self,
        template: str,
        context: dict[str, Any],
        strict: bool,
    ) -> str:
        """
        Render a string template with variable substitution.

        Args:
            template: String template with {placeholders}
            context: Variables for substitution
            strict: Whether to raise error on missing variables

        Returns:
            Rendered string
        """
        # Extract all placeholders from the template
        placeholders = self._extract_placeholders_from_string(template)

        if not placeholders:
            # No placeholders, return as-is
            return template

        # Build replacement dict with defaults
        replacement: dict[str, Any] = {}
        missing = []

        for placeholder in placeholders:
            if placeholder in context:
                value = context[placeholder]
                # Convert complex values to JSON
                if placeholder == "data_json" and isinstance(value, dict):
                    import json
                    value = json.dumps(value)
                elif not isinstance(value, (str, int, float, bool)):
                    import json
                    value = json.dumps(value)
                replacement[placeholder] = value
            elif strict:
                missing.append(placeholder)
            else:
                # Leave placeholder as-is
                replacement[placeholder] = f"{{{placeholder}}}"

        if strict and missing:
            raise ValueError(
                f"Missing required variables: {', '.join(missing)}"
            )

        try:
            return template.format(**replacement)
        except (KeyError, ValueError) as e:
            if strict:
                raise ValueError(f"Template formatting error: {e}") from e
            # Return original template on error
            return template

    def _extract_placeholders(
        self,
        data: Any,
    ) -> list[str]:
        """
        Extract all unique placeholder names from template data.

        Args:
            data: Template data (dict, list, or string)

        Returns:
            List of unique placeholder names
        """
        placeholders = set()

        if isinstance(data, dict):
            for value in data.values():
                placeholders.update(self._extract_placeholders(value))
        elif isinstance(data, list):
            for item in data:
                placeholders.update(self._extract_placeholders(item))
        elif isinstance(data, str):
            placeholders.update(
                self._extract_placeholders_from_string(data)
            )

        return list(placeholders)

    def _extract_placeholders_from_string(
        self,
        template: str,
    ) -> list[str]:
        """
        Extract placeholder names from a string template.

        Args:
            template: String template with {placeholders}

        Returns:
            List of placeholder names
        """
        placeholders = []

        for _, field_name, _, _ in Formatter().parse(template):
            if field_name:
                # Extract the base name (before any '.' or '[')
                base_name = field_name.split(".")[0].split("[")[0]
                placeholders.append(base_name)

        return placeholders


# Convenience functions


def get_template_engine() -> TemplateEngine:
    """
    Get a shared template engine instance.

    Returns:
        TemplateEngine instance
    """
    # Singleton pattern for convenience
    if not hasattr(get_template_engine, "_instance"):
        get_template_engine._instance = TemplateEngine()  # type: ignore
    return get_template_engine._instance  # type: ignore


def render_template(
    template: str | dict[str, Any],
    context: dict[str, Any],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """
    Convenience function to render a template.

    Args:
        template: Template name or dictionary
        context: Variables for substitution
        strict: Whether to raise error on missing variables

    Returns:
        Rendered payload dictionary
    """
    engine = get_template_engine()
    return engine.render(template, context, strict=strict)
