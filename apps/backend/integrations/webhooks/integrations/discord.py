"""
Discord Integration
===================

Discord webhook integration for sending build notifications to Discord channels.

Supports:
- Incoming webhooks (send notifications to Discord)
- Rich message formatting with embeds
- Custom message templates
- Color-coded status messages
- Field and footer support for detailed information

Configuration:
    DISCORD_WEBHOOK_URL: Discord incoming webhook URL

Usage:
    >>> from integrations.webhooks.integrations.discord import DiscordIntegration
    >>> integration = DiscordIntegration(spec_dir=Path("/path/to/spec"))
    >>> if integration.is_enabled:
    ...     result = await integration.send_notification(event)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from ..models import WebhookConfig, WebhookEvent, WebhookIntegration, WebhookType
from .base import BaseIntegration


# =============================================================================
# Logging
# =============================================================================


logger = logging.getLogger(__name__)


# =============================================================================
# Discord Integration
# =============================================================================


class DiscordIntegration(BaseIntegration):
    """
    Discord webhook integration for build notifications.

    Sends build lifecycle events (start, complete, fail) to Discord channels
    using incoming webhooks. Supports rich message formatting with embeds.

    Configuration:
        - DISCORD_WEBHOOK_URL: Incoming webhook URL (required)

    Features:
        - Rich message formatting with Discord embeds
        - Build status notifications with color coding
        - Subtask progress updates
        - Customizable message templates
        - Field support for structured information
    """

    INTEGRATION_NAME = "discord"

    def __init__(self, spec_dir: Path, project_dir: Path | None = None):
        """
        Initialize the Discord integration.

        Args:
            spec_dir: Spec directory (for state persistence)
            project_dir: Optional project root directory
        """
        # Load Discord-specific configuration BEFORE calling super().__init__()
        # because _check_configured() is called in parent's __init__
        self.webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

        super().__init__(spec_dir=spec_dir, project_dir=project_dir)

    def _check_configured(self) -> bool:
        """
        Check if Discord integration has required credentials.

        Returns:
            True if DISCORD_WEBHOOK_URL is configured
        """
        return bool(self.webhook_url)

    def get_config(self) -> WebhookConfig:
        """
        Build the WebhookConfig for Discord.

        Returns:
            WebhookConfig for sending Discord notifications

        Raises:
            ValueError: If DISCORD_WEBHOOK_URL is not configured
        """
        if not self.webhook_url:
            raise ValueError("DISCORD_WEBHOOK_URL environment variable is not set")

        return WebhookConfig(
            id="discord-notification",
            name="Discord Build Notifications",
            type=WebhookType.OUTGOING,
            integration=WebhookIntegration.DISCORD,
            url=self.webhook_url,
            enabled=True,
        )

    async def test_connection(self) -> tuple[bool, str]:
        """
        Test the Discord webhook connection.

        Sends a test message to verify the webhook is working.

        Returns:
            Tuple of (success, message) with test result
        """
        try:
            # Create a test event
            test_event = WebhookEvent(
                type="custom",  # type: ignore[arg-type]
                data={
                    "test": True,
                    "message": "This is a test notification from Auto Claude",
                },
            )

            # Send test notification
            success, message = await self.send_notification(test_event)

            if success:
                return True, "Successfully sent test message to Discord"
            else:
                return False, f"Failed to send test message: {message}"

        except Exception as e:
            logger.error(f"Discord connection test failed: {e}", exc_info=True)
            return False, f"Connection test failed: {e}"

    def format_payload(self, event: WebhookEvent) -> dict[str, Any]:
        """
        Format the webhook payload for Discord.

        Transforms WebhookEvent into Discord message format with embeds.
        Supports rich formatting with title, description, fields, color,
        footer, and timestamp.

        Args:
            event: Webhook event to format

        Returns:
            Discord-formatted message payload

        Discord Message Format:
            {
                "content": "Message text (optional)",
                "embeds": [
                    {
                        "title": "Embed title",
                        "description": "Embed description",
                        "color": 0x36a64f,  # Decimal color value
                        "fields": [
                            {
                                "name": "Field name",
                                "value": "Field value",
                                "inline": false
                            }
                        ],
                        "footer": {
                            "text": "Footer text"
                        },
                        "timestamp": "ISO 8601 timestamp"
                    }
                ]
            }
        """
        event_type = event.type.value
        event_data = event.data

        # Build base message
        title, description, color, emoji = self._get_message_details(event_type, event_data)

        # Create embed
        embed = {
            "title": f"{emoji} {title}",
            "description": description,
            "color": color,
            "timestamp": event.timestamp,
            "fields": [],
        }

        # Add event-specific fields
        if event_type in ["build_started", "build_completed", "build_failed"]:
            spec_name = event_data.get("spec_name", "Unknown")
            spec_id = event_data.get("spec_id", "Unknown")

            embed["fields"].extend([
                {
                    "name": "Spec",
                    "value": spec_name,
                    "inline": True,
                },
                {
                    "name": "ID",
                    "value": spec_id,
                    "inline": True,
                },
            ])

        elif event_type in ["subtask_started", "subtask_completed", "subtask_failed"]:
            subtask_id = event_data.get("subtask_id", "Unknown")
            subtask_desc = event_data.get("subtask_description", "")

            embed["fields"].append({
                "name": "Subtask",
                "value": f"{subtask_id}\n{subtask_desc}",
                "inline": False,
            })

        # Add event-specific details
        if event_type == "build_started":
            total_subtasks = event_data.get("total_subtasks", 0)
            embed["fields"].append({
                "name": "Total Subtasks",
                "value": str(total_subtasks),
                "inline": True,
            })

        elif event_type == "build_completed":
            success = event_data.get("success", False)
            duration = event_data.get("duration_seconds", 0)

            status_text = "✅ Success" if success else "⚠️ Failed"
            duration_str = f"{duration:.1f}s" if duration < 60 else f"{duration/60:.1f}m"

            embed["fields"].extend([
                {
                    "name": "Status",
                    "value": status_text,
                    "inline": True,
                },
                {
                    "name": "Duration",
                    "value": duration_str,
                    "inline": True,
                },
            ])

        elif event_type == "build_failed":
            error = event_data.get("error_message", "Unknown error")
            failed_subtask = event_data.get("failed_subtask")

            error_value = f"```{error}```"
            if failed_subtask:
                embed["fields"].append({
                    "name": "Failed Subtask",
                    "value": failed_subtask,
                    "inline": False,
                })

            embed["fields"].append({
                "name": "Error",
                "value": error_value,
                "inline": False,
            })

        elif event_type == "subtask_completed":
            session = event_data.get("session_number", "Unknown")
            embed["fields"].append({
                "name": "Session",
                "value": str(session),
                "inline": True,
            })

        elif event_type == "subtask_failed":
            error = event_data.get("error_message", "Unknown error")
            attempt = event_data.get("attempt_number", 1)

            embed["fields"].extend([
                {
                    "name": "Error",
                    "value": f"```{error}```",
                    "inline": False,
                },
                {
                    "name": "Attempt",
                    "value": str(attempt),
                    "inline": True,
                },
            ])

        # Add footer with metadata if available
        footer_text = "Auto Claude"
        if event.metadata:
            metadata_items = []
            for key, value in event.metadata.items():
                if key not in ["internal_only"]:  # Skip internal fields
                    metadata_items.append(f"{key}: {value}")

            if metadata_items:
                footer_text += " | " + " | ".join(metadata_items)

        embed["footer"] = {
            "text": footer_text,
        }

        # Build the final payload
        payload = {
            "embeds": [embed],
        }

        # Add optional content for test messages
        if event_type == "custom":
            content = event_data.get("message", "")
            if content:
                payload["content"] = content

        return payload

    def _get_message_details(
        self, event_type: str, event_data: dict[str, Any]
    ) -> tuple[str, str, int, str]:
        """
        Get message title, description, color, and emoji for an event type.

        Discord colors are decimal values (e.g., 0x36a64f = 3581519 for green)

        Args:
            event_type: Type of webhook event
            event_data: Event data dictionary

        Returns:
            Tuple of (title, description, color_decimal, emoji)
        """
        if event_type == "build_started":
            return (
                "Build Started",
                f"Starting build for spec: {event_data.get('spec_name', 'Unknown')}",
                0x36A64F,  # Green
                "🚀",
            )

        elif event_type == "build_completed":
            success = event_data.get("success", False)
            if success:
                return (
                    "Build Completed Successfully",
                    f"Build completed for spec: {event_data.get('spec_name', 'Unknown')}",
                    0x36A64F,  # Green
                    "✅",
                )
            else:
                return (
                    "Build Completed with Warnings",
                    f"Build completed with warnings for spec: {event_data.get('spec_name', 'Unknown')}",
                    0xFF9900,  # Orange
                    "⚠️",
                )

        elif event_type == "build_failed":
            return (
                "Build Failed",
                f"Build failed for spec: {event_data.get('spec_name', 'Unknown')}",
                0xFF0000,  # Red
                "❌",
            )

        elif event_type == "subtask_started":
            return (
                "Subtask Started",
                f"Working on: {event_data.get('subtask_description', 'Unknown')}",
                0x36A64F,  # Green
                "🔧",
            )

        elif event_type == "subtask_completed":
            return (
                "Subtask Completed",
                f"Completed subtask: {event_data.get('subtask_id', 'Unknown')}",
                0x36A64F,  # Green
                "✅",
            )

        elif event_type == "subtask_failed":
            return (
                "Subtask Failed",
                f"Failed subtask: {event_data.get('subtask_id', 'Unknown')}",
                0xFF0000,  # Red
                "❌",
            )

        elif event_type == "pr_opened":
            return (
                "Pull Request Opened",
                "A new pull request has been opened",
                0x36A64F,  # Green
                "🔌",
            )

        elif event_type == "pr_merged":
            return (
                "Pull Request Merged",
                "A pull request has been merged",
                0x36A64F,  # Green
                "🔀",
            )

        elif event_type == "pr_closed":
            return (
                "Pull Request Closed",
                "A pull request has been closed",
                0xFF9900,  # Orange
                "🔒",
            )

        else:
            return (
                "Auto Claude Notification",
                "Build notification from Auto Claude",
                0x36A64F,  # Green
                "📢",
            )
