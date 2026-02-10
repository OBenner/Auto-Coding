"""
Webhook Templates Package
==========================

Pre-built templates for popular webhook services (Slack, Discord, Teams).

This package provides convenient access to webhook payload templates
optimized for different services.

Usage:
    from integrations.webhooks.templates import get_template, list_templates

    # Get a specific template
    slack_template = get_template("slack")

    # List all available templates
    templates = list_templates()
    print(templates)  # ['generic', 'slack', 'discord', 'teams', 'jira']
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


# Import template definitions from templates.py module
# Note: We use importlib to avoid the package/module naming conflict
# where this package (templates/) shadows the templates.py module
def _load_templates_module() -> Any:
    """
    Load the templates.py module (not this package).

    Returns:
        The templates module object
    """
    # Get the path to templates.py (sibling to this package directory)
    this_dir = Path(__file__).parent
    templates_module_path = this_dir.parent / "templates.py"

    # Load the module using importlib to avoid naming conflicts
    spec = importlib.util.spec_from_file_location(
        "integrations.webhooks.templates_module",
        templates_module_path
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load templates module from {templates_module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_builtin_templates() -> dict[str, dict[str, Any]]:
    """
    Load built-in webhook templates.

    Returns:
        Dictionary of template name to template structure
    """
    templates_module = _load_templates_module()
    engine = templates_module.TemplateEngine()
    return engine.BUILTIN_TEMPLATES


def get_template(name: str) -> dict[str, Any] | None:
    """
    Get a webhook template by name.

    Args:
        name: Template name (e.g., 'slack', 'discord', 'teams', 'generic')

    Returns:
        Template dictionary or None if not found

    Examples:
        >>> slack = get_template("slack")
        >>> print(slack["text"])
        'Auto-Claude Event: {event}'
    """
    templates = _load_builtin_templates()
    return templates.get(name)


def list_templates() -> list[str]:
    """
    List all available template names.

    Returns:
        List of template names

    Examples:
        >>> list_templates()
        ['generic', 'slack', 'discord', 'teams', 'jira']
    """
    templates = _load_builtin_templates()
    return list(templates.keys())


def get_template_variables(name: str) -> list[str]:
    """
    Get the required variables for a template.

    Args:
        name: Template name

    Returns:
        List of variable names required by the template

    Examples:
        >>> vars = get_template_variables("slack")
        >>> print(vars)
        ['event', 'event_title', 'status', 'spec_id', ...]
    """
    templates_module = _load_templates_module()
    engine = templates_module.TemplateEngine()
    variables = engine.extract_required_variables(name)
    return list(variables)


def render_template(
    name: str,
    context: dict[str, Any],
    *,
    strict: bool = False,
) -> dict[str, Any]:
    """
    Render a template with the given context.

    Args:
        name: Template name
        context: Variables for substitution
        strict: Whether to raise error on missing variables

    Returns:
        Rendered payload dictionary

    Raises:
        ValueError: If template not found or rendering fails

    Examples:
        >>> context = {
        ...     "event": "build_started",
        ...     "event_title": "Build Started",
        ...     "spec_id": "001",
        ...     "status": "in_progress",
        ...     "description": "Build has started",
        ...     "timestamp": "2024-02-10T12:00:00Z"
        ... }
        >>> payload = render_template("slack", context)
    """
    templates_module = _load_templates_module()
    return templates_module.render_template(name, context, strict=strict)


# Export commonly used functions
__all__ = [
    "get_template",
    "list_templates",
    "get_template_variables",
    "render_template",
]
