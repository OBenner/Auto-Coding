"""
Microsoft Teams Integration
===========================

Microsoft Teams webhook integration for sending build notifications to Teams channels.

Supports:
- Incoming webhooks (send notifications to Teams)
- Rich message formatting with Adaptive Cards
- Custom message templates
- Color-coded status messages
- Fact and section support for detailed information

Configuration:
    TEAMS_WEBHOOK_URL: Microsoft Teams incoming webhook URL

Usage:
    >>> from integrations.webhooks.integrations.teams import TeamsIntegration
    >>> integration = TeamsIntegration(spec_dir=Path("/path/to/spec"))
    >>> if integration.is_enabled:
    ...     result = await integration.send_notification(event)
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any

from ..models import (
    WebhookConfig,
    WebhookEvent,
    WebhookIntegration,
    WebhookType,
)
from .base import BaseIntegration

# =============================================================================
# Logging
# =============================================================================


logger = logging.getLogger(__name__)


# =============================================================================
# Teams Integration
# =============================================================================


class TeamsIntegration(BaseIntegration):
    """
    Microsoft Teams webhook integration for build notifications.

    Sends build lifecycle events (start, complete, fail) to Teams channels
    using incoming webhooks. Supports rich message formatting with Adaptive Cards.

    Configuration:
        - TEAMS_WEBHOOK_URL: Incoming webhook URL (required)

    Features:
        - Rich message formatting with Adaptive Cards
        - Build status notifications with color coding
        - Subtask progress updates
        - Customizable message templates
        - Fact sets for structured information
    """

    INTEGRATION_NAME = "teams"

    def __init__(self, spec_dir: Path, project_dir: Path | None = None):
        """
        Initialize the Teams integration.

        Args:
            spec_dir: Spec directory (for state persistence)
            project_dir: Optional project root directory
        """
        # Load Teams-specific configuration BEFORE calling super().__init__()
        # because _check_configured() is called in parent's __init__
        self.webhook_url = os.environ.get("TEAMS_WEBHOOK_URL")

        super().__init__(spec_dir=spec_dir, project_dir=project_dir)

    def _check_configured(self) -> bool:
        """
        Check if Teams integration has required credentials.

        Returns:
            True if TEAMS_WEBHOOK_URL is configured
        """
        return bool(self.webhook_url)

    def get_config(self) -> WebhookConfig:
        """
        Build the WebhookConfig for Teams.

        Returns:
            WebhookConfig for sending Teams notifications

        Raises:
            ValueError: If TEAMS_WEBHOOK_URL is not configured
        """
        if not self.webhook_url:
            raise ValueError("TEAMS_WEBHOOK_URL environment variable is not set")

        return WebhookConfig(
            id=f"teams-notification-{uuid.uuid4().hex[:8]}",
            name="Microsoft Teams Build Notifications",
            type=WebhookType.OUTGOING,
            integration=WebhookIntegration.TEAMS,
            url=self.webhook_url,
            enabled=True,
        )

    async def test_connection(self) -> tuple[bool, str]:
        """
        Test the Teams webhook connection.

        Sends a test message directly (bypasses is_enabled check)
        to verify the webhook URL is working.

        Returns:
            Tuple of (success, message) with test result
        """
        try:
            import httpx

            if not self.webhook_url:
                return False, "TEAMS_WEBHOOK_URL is not configured"

            test_payload = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "contentUrl": None,
                        "content": {
                            "$schema": "https://adaptivecards.io/schemas/adaptive-card.json",
                            "type": "AdaptiveCard",
                            "version": "1.4",
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": "Auto Claude Test Connection",
                                    "weight": "Bolder",
                                    "size": "Large",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": "This is a test notification from Auto Claude.",
                                    "wrap": True,
                                },
                            ],
                        },
                    }
                ],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=test_payload,
                    timeout=10.0,
                )

                if response.is_success:
                    return True, "Successfully sent test message to Microsoft Teams"
                else:
                    return (
                        False,
                        f"Failed to send test message: HTTP {response.status_code}",
                    )

        except Exception as e:
            logger.error(f"Teams connection test failed: {e}", exc_info=True)
            return False, f"Connection test failed: {e}"

    def format_payload(self, event: WebhookEvent) -> dict[str, Any]:
        """
        Format the webhook payload for Microsoft Teams.

        Transforms WebhookEvent into Teams message format with Adaptive Cards.
        Supports rich formatting with title, text, facts, and color theming.

        Args:
            event: Webhook event to format

        Returns:
            Teams-formatted message payload

        Teams Message Format:
            {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "contentUrl": null,
                        "content": {
                            "$schema": "https://adaptivecards.io/schemas/adaptive-card.json",
                            "type": "AdaptiveCard",
                            "version": "1.4",
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": "Title",
                                    "weight": "Bolder",
                                    "size": "Large"
                                },
                                {
                                    "type": "TextBlock",
                                    "text": "Description",
                                    "wrap": True
                                },
                                {
                                    "type": "FactSet",
                                    "facts": [
                                        {
                                            "title": "Spec:",
                                            "value": "spec-name"
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
        """
        event_type = event.type.value
        event_data = event.data

        # Build base message
        title, text, _color, theme_color = self._get_message_details(
            event_type, event_data
        )

        # Create Adaptive Card body
        body = []

        # Title block with emoji
        body.append(
            {
                "type": "TextBlock",
                "text": title,
                "weight": "Bolder",
                "size": "Large",
            }
        )

        # Add text description
        if text:
            body.append(
                {
                    "type": "TextBlock",
                    "text": text,
                    "wrap": True,
                }
            )

        # Collect facts for event details
        facts = []

        # Add event-specific facts
        if event_type in ["build_started", "build_completed", "build_failed"]:
            spec_name = event_data.get("spec_name", "Unknown")
            spec_id = event_data.get("spec_id", "Unknown")

            facts.extend(
                [
                    {"title": "Spec", "value": spec_name},
                    {"title": "ID", "value": spec_id},
                ]
            )

        elif event_type in ["subtask_started", "subtask_completed", "subtask_failed"]:
            subtask_id = event_data.get("subtask_id", "Unknown")
            subtask_desc = event_data.get("subtask_description", "")

            facts.append({"title": "Subtask", "value": f"{subtask_id}"})
            if subtask_desc:
                facts.append({"title": "Description", "value": subtask_desc})

        # Add event-specific details
        if event_type == "build_started":
            total_subtasks = event_data.get("total_subtasks", 0)
            facts.append({"title": "Total Subtasks", "value": str(total_subtasks)})

        elif event_type == "build_completed":
            success = event_data.get("success", False)
            duration = event_data.get("duration_seconds", 0)

            status_text = "✅ Success" if success else "⚠️ Failed"
            duration_str = (
                f"{duration:.1f}s" if duration < 60 else f"{duration / 60:.1f}m"
            )

            facts.extend(
                [
                    {"title": "Status", "value": status_text},
                    {"title": "Duration", "value": duration_str},
                ]
            )

        elif event_type == "build_failed":
            error = event_data.get("error_message", "Unknown error")
            failed_subtask = event_data.get("failed_subtask")

            facts.append({"title": "Error", "value": error})
            if failed_subtask:
                facts.append({"title": "Failed Subtask", "value": failed_subtask})

        elif event_type == "subtask_completed":
            session = event_data.get("session_number", "Unknown")
            facts.append({"title": "Session", "value": str(session)})

        elif event_type == "subtask_failed":
            error = event_data.get("error_message", "Unknown error")
            attempt = event_data.get("attempt_number", 1)

            facts.extend(
                [
                    {"title": "Error", "value": error},
                    {"title": "Attempt", "value": str(attempt)},
                ]
            )

        # Add metadata facts if available
        if event.metadata:
            for key, value in event.metadata.items():
                if key not in ["internal_only"]:  # Skip internal fields
                    facts.append({"title": key.title(), "value": str(value)})

        # Add FactSet if we have facts
        if facts:
            body.append(
                {
                    "type": "FactSet",
                    "facts": facts,
                }
            )

        # Build the Adaptive Card
        card = {
            "$schema": "https://adaptivecards.io/schemas/adaptive-card.json",
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": body,
        }

        # Add theme color if provided
        if theme_color:
            card["msteams"] = {
                "width": "full",
            }

        # Build the final payload
        # Note: themeColor is NOT supported on Adaptive Cards by Teams.
        # It only applies to the legacy MessageCard format.
        payload: dict[str, Any] = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": card,
                }
            ],
        }

        return payload

    def _get_message_details(
        self, event_type: str, event_data: dict[str, Any]
    ) -> tuple[str, str, str, str]:
        """
        Get message title, text, color name, and theme color for an event type.

        Teams theme colors are hex colors (e.g., "0078D4" for blue, "00FF00" for green)

        Args:
            event_type: Type of webhook event
            event_data: Event data dictionary

        Returns:
            Tuple of (title, text, color_name, theme_color_hex)
        """
        if event_type == "build_started":
            return (
                "🚀 Build Started",
                f"Starting build for spec: {event_data.get('spec_name', 'Unknown')}",
                "accent",
                "0078D4",  # Microsoft Blue
            )

        elif event_type == "build_completed":
            success = event_data.get("success", False)
            if success:
                return (
                    "✅ Build Completed Successfully",
                    f"Build completed for spec: {event_data.get('spec_name', 'Unknown')}",
                    "good",
                    "00FF00",  # Green
                )
            else:
                return (
                    "⚠️ Build Completed with Warnings",
                    f"Build completed with warnings for spec: {event_data.get('spec_name', 'Unknown')}",
                    "warning",
                    "FF9900",  # Orange
                )

        elif event_type == "build_failed":
            return (
                "❌ Build Failed",
                f"Build failed for spec: {event_data.get('spec_name', 'Unknown')}",
                "attention",
                "FF0000",  # Red
            )

        elif event_type == "subtask_started":
            return (
                "🔧 Subtask Started",
                f"Working on: {event_data.get('subtask_description', 'Unknown')}",
                "accent",
                "0078D4",  # Microsoft Blue
            )

        elif event_type == "subtask_completed":
            return (
                "✅ Subtask Completed",
                f"Completed subtask: {event_data.get('subtask_id', 'Unknown')}",
                "good",
                "00FF00",  # Green
            )

        elif event_type == "subtask_failed":
            return (
                "❌ Subtask Failed",
                f"Failed subtask: {event_data.get('subtask_id', 'Unknown')}",
                "attention",
                "FF0000",  # Red
            )

        elif event_type == "pr_opened":
            return (
                "🔌 Pull Request Opened",
                "A new pull request has been opened",
                "good",
                "00FF00",  # Green
            )

        elif event_type == "pr_merged":
            return (
                "🔀 Pull Request Merged",
                "A pull request has been merged",
                "good",
                "00FF00",  # Green
            )

        elif event_type == "pr_closed":
            return (
                "🔒 Pull Request Closed",
                "A pull request has been closed",
                "warning",
                "FF9900",  # Orange
            )

        else:
            return (
                "📢 Auto Claude Notification",
                "Build notification from Auto Claude",
                "default",
                "0078D4",  # Microsoft Blue
            )
