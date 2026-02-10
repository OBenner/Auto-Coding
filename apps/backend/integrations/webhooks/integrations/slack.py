"""
Slack Integration
=================

Slack webhook integration for sending build notifications to Slack channels.

Supports:
- Incoming webhooks (send notifications to Slack)
- Slack API for advanced messaging
- Rich message formatting with blocks and attachments
- Channel, thread, and user mentions
- Custom message templates

Configuration:
    SLACK_WEBHOOK_URL: Slack incoming webhook URL
    SLACK_BOT_TOKEN: Optional Slack bot token for API features

Usage:
    >>> from integrations.webhooks.integrations.slack import SlackIntegration
    >>> integration = SlackIntegration(spec_dir=Path("/path/to/spec"))
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
# Slack Integration
# =============================================================================


class SlackIntegration(BaseIntegration):
    """
    Slack webhook integration for build notifications.

    Sends build lifecycle events (start, complete, fail) to Slack channels
    using incoming webhooks. Supports rich message formatting with blocks.

    Configuration:
        - SLACK_WEBHOOK_URL: Incoming webhook URL (required)
        - SLACK_BOT_TOKEN: Bot token for API features (optional)
        - SLACK_CHANNEL: Default channel (optional, uses webhook default)

    Features:
        - Rich message formatting with Slack blocks
        - Build status notifications with color coding
        - Subtask progress updates
        - Customizable message templates
        - Threaded replies for build updates
    """

    INTEGRATION_NAME = "slack"

    def __init__(self, spec_dir: Path, project_dir: Path | None = None):
        """
        Initialize the Slack integration.

        Args:
            spec_dir: Spec directory (for state persistence)
            project_dir: Optional project root directory
        """
        # Load Slack-specific configuration BEFORE calling super().__init__()
        # because _check_configured() is called in parent's __init__
        self.webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        self.bot_token = os.environ.get("SLACK_BOT_TOKEN")
        self.default_channel = os.environ.get("SLACK_CHANNEL")

        super().__init__(spec_dir=spec_dir, project_dir=project_dir)

    def _check_configured(self) -> bool:
        """
        Check if Slack integration has required credentials.

        Returns:
            True if SLACK_WEBHOOK_URL is configured
        """
        return bool(self.webhook_url)

    def get_config(self) -> WebhookConfig:
        """
        Build the WebhookConfig for Slack.

        Returns:
            WebhookConfig for sending Slack notifications

        Raises:
            ValueError: If SLACK_WEBHOOK_URL is not configured
        """
        if not self.webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL environment variable is not set")

        return WebhookConfig(
            id="slack-notification",
            name="Slack Build Notifications",
            type=WebhookType.OUTGOING,
            integration=WebhookIntegration.SLACK,
            url=self.webhook_url,
            enabled=True,
        )

    async def test_connection(self) -> tuple[bool, str]:
        """
        Test the Slack webhook connection.

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
                return True, "Successfully sent test message to Slack"
            else:
                return False, f"Failed to send test message: {message}"

        except Exception as e:
            logger.error(f"Slack connection test failed: {e}", exc_info=True)
            return False, f"Connection test failed: {e}"

    def format_payload(self, event: WebhookEvent) -> dict[str, Any]:
        """
        Format the webhook payload for Slack.

        Transforms WebhookEvent into Slack message format with blocks.
        Supports rich formatting with section blocks, divider blocks,
        and context blocks for build metadata.

        Args:
            event: Webhook event to format

        Returns:
            Slack-formatted message payload

        Slack Message Format:
            {
                "text": "Message text for notifications",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Formatted text"
                        }
                    },
                    ...
                ],
                "attachments": [...]  # Optional
            }
        """
        event_type = event.type.value
        event_data = event.data

        # Build base message
        message, color, emoji = self._get_message_details(event_type, event_data)

        # Create blocks for rich formatting
        blocks = []

        # Header block with emoji and status
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {message}",
                "emoji": True,
            },
        })

        # Divider
        blocks.append({"type": "divider"})

        # Build details section
        if event_type in ["build_started", "build_completed", "build_failed"]:
            spec_name = event_data.get("spec_name", "Unknown")
            spec_id = event_data.get("spec_id", "Unknown")

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Spec:* {spec_name}\n*ID:* {spec_id}",
                },
            })

        elif event_type in ["subtask_started", "subtask_completed", "subtask_failed"]:
            subtask_id = event_data.get("subtask_id", "Unknown")
            subtask_desc = event_data.get("subtask_description", "")

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Subtask:* {subtask_id}\n{subtask_desc}",
                },
            })

        # Add event-specific details
        if event_type == "build_started":
            total_subtasks = event_data.get("total_subtasks", 0)
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Total Subtasks:* {total_subtasks}",
                },
            })

        elif event_type == "build_completed":
            success = event_data.get("success", False)
            duration = event_data.get("duration_seconds", 0)

            status_emoji = "✅" if success else "⚠️"
            duration_str = f"{duration:.1f}s" if duration < 60 else f"{duration/60:.1f}m"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Status:* {status_emoji} {'Success' if success else 'Failed'}\n*Duration:* {duration_str}",
                },
            })

        elif event_type == "build_failed":
            error = event_data.get("error_message", "Unknown error")
            failed_subtask = event_data.get("failed_subtask")

            error_text = f"*Error:* {error}"
            if failed_subtask:
                error_text += f"\n*Failed Subtask:* {failed_subtask}"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": error_text,
                },
            })

        elif event_type == "subtask_completed":
            session = event_data.get("session_number", "Unknown")
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Session:* {session}",
                },
            })

        elif event_type == "subtask_failed":
            error = event_data.get("error_message", "Unknown error")
            attempt = event_data.get("attempt_number", 1)

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error:* {error}\n*Attempt:* {attempt}",
                },
            })

        # Add context metadata if available
        if event.metadata:
            context_items = []
            for key, value in event.metadata.items():
                if key not in ["internal_only"]:  # Skip internal fields
                    context_items.append(f"{key}: {value}")

            if context_items:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": " | ".join(context_items),
                        }
                    ],
                })

        # Build the final payload
        payload = {
            "text": message,  # Fallback text for notifications
            "blocks": blocks,
        }

        # Add attachment for color (legacy Slack format)
        if color:
            payload["attachments"] = [
                {
                    "color": color,
                    "blocks": blocks,
                }
            ]

        return payload

    def _get_message_details(self, event_type: str, event_data: dict[str, Any]) -> tuple[str, str, str]:
        """
        Get message text, color, and emoji for an event type.

        Args:
            event_type: Type of webhook event
            event_data: Event data dictionary

        Returns:
            Tuple of (message_text, color_hex, emoji)
        """
        if event_type == "build_started":
            return "Build Started", "#36a64f", "🚀"

        elif event_type == "build_completed":
            success = event_data.get("success", False)
            if success:
                return "Build Completed Successfully", "#36a64f", "✅"
            else:
                return "Build Completed with Warnings", "#ff9900", "⚠️"

        elif event_type == "build_failed":
            return "Build Failed", "#ff0000", "❌"

        elif event_type == "subtask_started":
            return "Subtask Started", "#36a64f", "🔧"

        elif event_type == "subtask_completed":
            return "Subtask Completed", "#36a64f", "✅"

        elif event_type == "subtask_failed":
            return "Subtask Failed", "#ff0000", "❌"

        elif event_type == "pr_opened":
            return "Pull Request Opened", "#36a64f", "🔌"

        elif event_type == "pr_merged":
            return "Pull Request Merged", "#36a64f", "🔀"

        elif event_type == "pr_closed":
            return "Pull Request Closed", "#ff9900", "🔒"

        else:
            return "Auto Claude Notification", "#36a64f", "📢"
