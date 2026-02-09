"""
Team Webhook Notification Plugin
==================================

Integration plugin that sends build notifications to a team webhook endpoint.

This plugin:
- Sends notifications when builds start and complete
- Optionally sends subtask progress updates
- Supports Slack, Discord, Microsoft Teams, or any webhook endpoint
- Configurable via TEAM_WEBHOOK_URL environment variable
- Handles errors gracefully without blocking builds

Configuration:
- TEAM_WEBHOOK_URL: Required webhook endpoint URL
- TEAM_WEBHOOK_NOTIFY_SUBTASKS: Optional, set to "true" to enable subtask notifications (default: false)
- TEAM_WEBHOOK_FORMAT: Optional, webhook format (slack, discord, teams, generic) (default: generic)

Example usage:
    export TEAM_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    export TEAM_WEBHOOK_NOTIFY_SUBTASKS="true"
    export TEAM_WEBHOOK_FORMAT="slack"
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional
from urllib import request
from urllib.error import HTTPError, URLError

from plugins.base import PluginMetadata
from plugins.sdk.integration import IntegrationContext, IntegrationPlugin

logger = logging.getLogger(__name__)


class CustomWebhookPlugin(IntegrationPlugin):
    """
    Integration plugin that sends build notifications to a webhook endpoint.

    This plugin hooks into the build lifecycle and sends notifications to a
    configured webhook URL. It supports multiple webhook formats and can be
    configured to send subtask updates in addition to build start/complete events.

    The plugin is designed to be non-blocking - if webhook delivery fails, it
    logs the error but does not interrupt the build.
    """

    def __init__(self, metadata: PluginMetadata):
        """Initialize the team webhook plugin."""
        super().__init__(metadata)
        self.webhook_url: Optional[str] = None
        self.notify_subtasks: bool = False
        self.webhook_format: str = "generic"
        logger.debug("CustomWebhookPlugin initialized")

    def on_load(self) -> None:
        """
        Called when plugin is loaded.

        Validates that TEAM_WEBHOOK_URL is configured.
        """
        logger.info("team-webhook: Plugin loaded")

        # Check for required configuration
        webhook_url = self.get_config_value("TEAM_WEBHOOK_URL")
        if not webhook_url:
            logger.warning(
                "team-webhook: TEAM_WEBHOOK_URL not configured - plugin will be disabled"
            )
        else:
            logger.info("team-webhook: Webhook URL configured")

    def on_enable(self) -> None:
        """
        Called when plugin is enabled.

        Loads configuration from environment variables.
        """
        logger.info("team-webhook: Plugin enabled")

        # Load configuration
        self.webhook_url = self.get_config_value("TEAM_WEBHOOK_URL")
        if not self.webhook_url:
            logger.error("team-webhook: No webhook URL configured")
            return

        # Load optional configuration
        notify_subtasks_str = self.get_config_value("TEAM_WEBHOOK_NOTIFY_SUBTASKS", "false")
        self.notify_subtasks = notify_subtasks_str.lower() in ("true", "1", "yes")

        self.webhook_format = self.get_config_value("TEAM_WEBHOOK_FORMAT", "generic").lower()
        if self.webhook_format not in ("slack", "discord", "teams", "generic"):
            logger.warning(
                f"team-webhook: Unknown format '{self.webhook_format}', using 'generic'"
            )
            self.webhook_format = "generic"

        logger.info(f"team-webhook: Configuration loaded (format: {self.webhook_format}, subtasks: {self.notify_subtasks})")

    def on_disable(self) -> None:
        """Called when plugin is disabled."""
        logger.info("team-webhook: Plugin disabled")
        self.webhook_url = None

    def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        logger.info("team-webhook: Plugin unloaded")

    def is_available(self) -> bool:
        """
        Check if the webhook integration is available.

        Returns:
            True if webhook URL is configured, False otherwise
        """
        return self.is_enabled and self.webhook_url is not None

    def _format_message(self, title: str, message: str, color: str = "info") -> dict[str, Any]:
        """
        Format a notification message for the configured webhook format.

        Args:
            title: Notification title
            message: Notification message body
            color: Message color/severity (success, error, info, warning)

        Returns:
            Formatted payload dictionary for the webhook
        """
        timestamp = datetime.now().isoformat()

        if self.webhook_format == "slack":
            # Slack webhook format
            color_map = {
                "success": "good",
                "error": "danger",
                "warning": "warning",
                "info": "#36a64f"
            }
            return {
                "attachments": [
                    {
                        "title": title,
                        "text": message,
                        "color": color_map.get(color, "#36a64f"),
                        "footer": "Auto Code",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }

        elif self.webhook_format == "discord":
            # Discord webhook format
            color_map = {
                "success": 3066993,  # Green
                "error": 15158332,   # Red
                "warning": 16776960, # Yellow
                "info": 3447003      # Blue
            }
            return {
                "embeds": [
                    {
                        "title": title,
                        "description": message,
                        "color": color_map.get(color, 3447003),
                        "footer": {"text": "Auto Code"},
                        "timestamp": timestamp
                    }
                ]
            }

        elif self.webhook_format == "teams":
            # Microsoft Teams webhook format
            color_map = {
                "success": "00FF00",
                "error": "FF0000",
                "warning": "FFA500",
                "info": "0078D4"
            }
            return {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": title,
                "themeColor": color_map.get(color, "0078D4"),
                "title": title,
                "text": message
            }

        else:
            # Generic format
            return {
                "title": title,
                "message": message,
                "color": color,
                "timestamp": timestamp,
                "source": "auto-code"
            }

    def _send_webhook(self, payload: dict[str, Any]) -> bool:
        """
        Send a payload to the configured webhook URL.

        Args:
            payload: JSON payload to send

        Returns:
            True if successful, False if error occurred
        """
        if not self.webhook_url:
            logger.warning("team-webhook: No webhook URL configured")
            return False

        try:
            data = json.dumps(payload).encode("utf-8")
            req = request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with request.urlopen(req, timeout=10) as response:
                if response.status >= 200 and response.status < 300:
                    logger.debug(f"team-webhook: Notification sent successfully (status: {response.status})")
                    return True
                else:
                    logger.warning(f"team-webhook: Webhook returned status {response.status}")
                    return False

        except HTTPError as e:
            logger.error(f"team-webhook: HTTP error sending notification: {e.code} {e.reason}")
            return False
        except URLError as e:
            logger.error(f"team-webhook: Network error sending notification: {e.reason}")
            return False
        except Exception as e:
            logger.error(f"team-webhook: Unexpected error sending notification: {e}")
            return False

    def on_build_start(self, context: IntegrationContext) -> None:
        """
        Called when a build starts.

        Sends a notification to the webhook with build start details.

        Args:
            context: Integration context
        """
        if not self.is_available():
            return

        logger.info(f"team-webhook: Build started for spec '{context.spec_name}'")

        title = f"🚀 Build Started: {context.spec_name}"
        message = (
            f"**Project:** {context.project_name}\n"
            f"**Spec:** {context.spec_name}\n"
            f"**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        payload = self._format_message(title, message, "info")
        self._send_webhook(payload)

        # Save state
        context.set_state("build_start_time", datetime.now().isoformat())
        context.set_state("notifications_sent", context.get_state("notifications_sent", 0) + 1)
        self.save_state(context)

    def on_build_complete(self, context: IntegrationContext, success: bool) -> None:
        """
        Called when a build completes.

        Sends a notification to the webhook with build completion details.

        Args:
            context: Integration context
            success: True if build succeeded, False if failed
        """
        if not self.is_available():
            return

        status = "succeeded" if success else "failed"
        emoji = "✅" if success else "❌"
        color = "success" if success else "error"

        logger.info(f"team-webhook: Build {status} for spec '{context.spec_name}'")

        # Calculate duration
        build_start = context.get_state("build_start_time")
        duration_str = "unknown"
        if build_start:
            try:
                start_time = datetime.fromisoformat(build_start)
                duration = datetime.now() - start_time
                hours, remainder = divmod(int(duration.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                if hours > 0:
                    duration_str = f"{hours}h {minutes}m {seconds}s"
                elif minutes > 0:
                    duration_str = f"{minutes}m {seconds}s"
                else:
                    duration_str = f"{seconds}s"
            except (ValueError, TypeError):
                pass

        title = f"{emoji} Build {status.capitalize()}: {context.spec_name}"
        message = (
            f"**Project:** {context.project_name}\n"
            f"**Spec:** {context.spec_name}\n"
            f"**Status:** {status.upper()}\n"
            f"**Duration:** {duration_str}\n"
            f"**Completed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        payload = self._format_message(title, message, color)
        self._send_webhook(payload)

        # Update state
        context.set_state("build_end_time", datetime.now().isoformat())
        context.set_state("build_success", success)
        context.set_state("notifications_sent", context.get_state("notifications_sent", 0) + 1)
        self.save_state(context)

    def on_subtask_update(
        self, context: IntegrationContext, subtask_id: str, status: str
    ) -> None:
        """
        Called when a subtask status changes.

        Optionally sends a notification if TEAM_WEBHOOK_NOTIFY_SUBTASKS is enabled.

        Args:
            context: Integration context
            subtask_id: ID of the subtask that changed
            status: New status (pending, in_progress, completed, failed)
        """
        if not self.is_available() or not self.notify_subtasks:
            return

        logger.info(f"team-webhook: Subtask {subtask_id} updated to {status}")

        # Map status to emoji
        status_emoji = {
            "pending": "⏳",
            "in_progress": "🔄",
            "completed": "✅",
            "failed": "❌"
        }
        emoji = status_emoji.get(status, "📝")

        # Map status to color
        status_color = {
            "pending": "info",
            "in_progress": "info",
            "completed": "success",
            "failed": "error"
        }
        color = status_color.get(status, "info")

        title = f"{emoji} Subtask Update: {subtask_id}"
        message = (
            f"**Spec:** {context.spec_name}\n"
            f"**Subtask:** {subtask_id}\n"
            f"**Status:** {status}"
        )

        payload = self._format_message(title, message, color)
        self._send_webhook(payload)

        # Update state
        context.set_state("notifications_sent", context.get_state("notifications_sent", 0) + 1)
        self.save_state(context)
