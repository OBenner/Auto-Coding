"""
Webhook Payload Builder
========================

Builds webhook payloads using the template system.

This module provides the bridge between webhook events and formatted payloads
for different services (Slack, Discord, Teams, etc.).

Design Principles:
- Template-driven: Uses TemplateEngine for flexible payload formatting
- Type-safe: Validates context variables before rendering
- Service-aware: Optimizes payloads for different webhook services
- Extensible: Easy to add custom payload builders

Usage:
    payload = build_payload(webhook, event, data)
    # or
    builder = PayloadBuilder()
    payload = builder.build(webhook, WebhookEvent.BUILD_STARTED, {...})
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Import models and template system
# Note: Import from templates.py module, not templates package
import importlib.util
from pathlib import Path

from integrations.webhooks.config import format_event_description, get_event_title
from integrations.webhooks.models import WebhookConfig, WebhookEvent


def _load_templates_module():
    """
    Load the templates.py module (not the templates package).

    Returns:
        The templates module with TemplateEngine
    """
    # Get the path to templates.py (sibling to this file)
    this_dir = Path(__file__).parent
    templates_module_path = this_dir / "templates.py"

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


# Get template engine from templates.py module
_templates_module = _load_templates_module()
get_template_engine = _templates_module.get_template_engine


class PayloadBuilder:
    """
    Builder for webhook payloads.

    Creates formatted payloads for different webhook services
    using the template system.
    """

    def __init__(self) -> None:
        """Initialize the payload builder."""
        self.template_engine = get_template_engine()

    def build(
        self,
        webhook: WebhookConfig,
        event: WebhookEvent,
        data: dict[str, Any],
        spec_dir: Path | None = None,
        project_dir: Path | None = None,
    ) -> dict[str, Any]:
        """
        Build a webhook payload using the configured template.

        Args:
            webhook: Webhook configuration
            event: Event type
            data: Event-specific data
            spec_dir: Optional spec directory path
            project_dir: Optional project directory path

        Returns:
            Rendered payload dictionary

        Raises:
            ValueError: If template not found or rendering fails
        """
        # Build template context
        context = self._build_context(
            webhook, event, data, spec_dir, project_dir
        )

        # Render template
        template_name = webhook.template
        try:
            payload = self.template_engine.render(
                template_name,
                context,
                strict=False,  # Don't fail on missing variables
            )
            return payload
        except (ValueError, KeyError, TypeError) as e:
            # Fallback to generic payload if template rendering fails
            return self._build_generic_payload(context, webhook)

    def _build_context(
        self,
        webhook: WebhookConfig,
        event: WebhookEvent,
        data: dict[str, Any],
        spec_dir: Path | None,
        project_dir: Path | None,
    ) -> dict[str, Any]:
        """
        Build template context from event data.

        Args:
            webhook: Webhook configuration
            event: Event type
            data: Event-specific data
            spec_dir: Optional spec directory path
            project_dir: Optional project directory path

        Returns:
            Template context dictionary
        """
        event_str = event.value
        timestamp = datetime.now(UTC).isoformat()

        # Extract spec information
        spec_id = data.get("spec_id", "")
        spec_title = data.get("spec_title", "")
        spec_directory = str(spec_dir) if spec_dir else ""

        # Determine status
        status = self._get_status_from_event(event, data)

        # Get event title and description
        event_title = get_event_title(event_str)
        description = format_event_description(event_str, data)

        # Build base context
        context: dict[str, Any] = {
            "event": event_str,
            "event_title": event_title,
            "spec_id": spec_id,
            "spec_title": spec_title,
            "spec_directory": spec_directory,
            "timestamp": timestamp,
            "status": status,
            "description": description,
            "webhook_id": webhook.webhook_id,
            "webhook_name": webhook.name,
        }

        # Add project directory if available
        if project_dir:
            context["project_directory"] = str(project_dir)
        else:
            context["project_directory"] = ""

        # Add event-specific data as JSON
        event_data = {k: v for k, v in data.items()
                     if k not in ("spec_id", "spec_title")}
        context["data_json"] = event_data

        # Merge all additional data
        context.update(data)

        return context

    def _get_status_from_event(
        self,
        event: WebhookEvent,
        data: dict[str, Any],
    ) -> str:
        """
        Get status string from event and data.

        Args:
            event: Event type
            data: Event-specific data

        Returns:
            Status string
        """
        # Check if data has explicit status
        if "status" in data:
            return str(data["status"])

        # Derive status from event type
        status_map = {
            WebhookEvent.SPEC_CREATED: "created",
            WebhookEvent.SPEC_UPDATED: "updated",
            WebhookEvent.BUILD_STARTED: "in_progress",
            WebhookEvent.BUILD_COMPLETED: "completed",
            WebhookEvent.BUILD_FAILED: "failed",
            WebhookEvent.QA_PASSED: "passed",
            WebhookEvent.QA_FAILED: "failed",
            WebhookEvent.MERGED: "merged",
            WebhookEvent.PR_CREATED: "created",
        }

        return status_map.get(event, "unknown")

    def _build_generic_payload(
        self,
        context: dict[str, Any],
        webhook: WebhookConfig,
    ) -> dict[str, Any]:
        """
        Build a generic JSON payload as fallback.

        Args:
            context: Template context
            webhook: Webhook configuration

        Returns:
            Generic payload dictionary
        """
        payload = {
            "event": context.get("event", ""),
            "timestamp": context.get("timestamp", ""),
            "spec": {
                "id": context.get("spec_id", ""),
                "title": context.get("spec_title", ""),
                "directory": context.get("spec_directory", ""),
            },
            "status": context.get("status", ""),
            "webhook": {
                "id": webhook.webhook_id,
                "name": webhook.name,
            },
        }

        # Add project directory if available
        if context.get("project_directory"):
            payload["project"] = {
                "directory": context["project_directory"],
            }

        # Add event data
        if "data_json" in context:
            payload["data"] = context["data_json"]

        return payload


# Convenience functions


def build_payload(
    webhook: WebhookConfig,
    event: WebhookEvent,
    data: dict[str, Any],
    spec_dir: Path | None = None,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Build a webhook payload (convenience function).

    This is the main entry point for building webhook payloads.
    Uses the configured template from the webhook to format the payload.

    Args:
        webhook: Webhook configuration
        event: Event type
        data: Event-specific data (spec_id, status, metrics, etc.)
        spec_dir: Optional spec directory path
        project_dir: Optional project directory path

    Returns:
        Rendered payload dictionary

    Examples:
        >>> webhook = WebhookConfig(
        ...     webhook_id="wh_123",
        ...     name="Slack notifications",
        ...     url="https://hooks.slack.com/...",
        ...     template="slack",
        ...     events=["build_started", "build_completed"]
        ... )
        >>> payload = build_payload(
        ...     webhook,
        ...     WebhookEvent.BUILD_STARTED,
        ...     {"spec_id": "001", "spec_title": "My Feature"}
        ... )
        >>> print(payload["text"])
        'Auto-Claude Event: build_started'
    """
    builder = PayloadBuilder()
    return builder.build(webhook, event, data, spec_dir, project_dir)


def build_test_payload(
    webhook: WebhookConfig,
    spec_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Build a test webhook payload.

    Useful for testing webhook configuration in the UI.

    Args:
        webhook: Webhook configuration
        spec_dir: Optional spec directory path

    Returns:
        Test payload dictionary
    """
    test_data = {
        "spec_id": spec_dir.name if spec_dir else "test-spec",
        "spec_title": "Test Webhook",
        "test": True,
        "message": "This is a test webhook event",
        "status": "test",
    }

    return build_payload(
        webhook,
        WebhookEvent.SPEC_CREATED,
        test_data,
        spec_dir,
    )


def validate_payload(
    payload: dict[str, Any],
) -> list[str]:
    """
    Validate a webhook payload.

    Args:
        payload: Payload dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required fields
    if "event" not in payload:
        errors.append("Missing required field: event")

    if "timestamp" not in payload:
        errors.append("Missing required field: timestamp")

    # Check spec info
    if "spec" in payload:
        spec = payload["spec"]
        if not isinstance(spec, dict):
            errors.append("Field 'spec' must be a dictionary")
        elif "id" not in spec:
            errors.append("Missing required field: spec.id")

    return errors


def get_payload_summary(payload: dict[str, Any]) -> str:
    """
    Get a human-readable summary of a payload.

    Args:
        payload: Payload dictionary

    Returns:
        Summary string
    """
    event = payload.get("event", "unknown")
    timestamp = payload.get("timestamp", "")
    spec_id = payload.get("spec", {}).get("id", "unknown")

    return f"Event: {event}, Spec: {spec_id}, Time: {timestamp}"
