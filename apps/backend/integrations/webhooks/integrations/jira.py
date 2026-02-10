"""
Jira Integration
================

Jira webhook integration for sending build notifications to Jira issues.
Supports project sync by creating comments and updating Jira issues.

Supports:
- Sending build notifications to Jira issues as comments
- Creating new Jira issues for build events
- Updating issue status based on build results
- Rich comment formatting with Jira markup
- Project and issue key mapping

Configuration:
    JIRA_API_URL: Jira instance URL (e.g., https://your-domain.atlassian.net)
    JIRA_API_EMAIL: Jira account email
    JIRA_API_TOKEN: Jira API token (from https://id.atlassian.com/manage-profile/security/api-tokens)
    JIRA_PROJECT_KEY: Default Jira project key (e.g., PROJ)
    JIRA_ISSUE_KEY: Default issue key for build notifications (e.g., PROJ-123)

Usage:
    >>> from integrations.webhooks.integrations.jira import JiraIntegration
    >>> integration = JiraIntegration(spec_dir=Path("/path/to/spec"))
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
# Jira Integration
# =============================================================================


class JiraIntegration(BaseIntegration):
    """
    Jira integration for build notifications and project sync.

    Sends build lifecycle events (start, complete, fail) to Jira issues
    using the Jira REST API. Supports creating comments on existing issues
    or creating new issues for build events.

    Configuration:
        - JIRA_API_URL: Jira instance URL (required)
        - JIRA_API_EMAIL: Jira account email (required)
        - JIRA_API_TOKEN: Jira API token (required)
        - JIRA_PROJECT_KEY: Default Jira project key (optional)
        - JIRA_ISSUE_KEY: Default issue key for comments (optional)

    Features:
        - Add build notifications as comments to Jira issues
        - Create new Jira issues for build events
        - Update issue status based on build results
        - Rich comment formatting with Jira markup
        - Support for multiple Jira projects and issue types
    """

    INTEGRATION_NAME = "jira"

    def __init__(self, spec_dir: Path, project_dir: Path | None = None):
        """
        Initialize the Jira integration.

        Args:
            spec_dir: Spec directory (for state persistence)
            project_dir: Optional project root directory
        """
        # Load Jira-specific configuration BEFORE calling super().__init__()
        # because _check_configured() is called in parent's __init__
        self.api_url = os.environ.get("JIRA_API_URL")
        self.api_email = os.environ.get("JIRA_API_EMAIL")
        self.api_token = os.environ.get("JIRA_API_TOKEN")
        self.project_key = os.environ.get("JIRA_PROJECT_KEY")
        self.issue_key = os.environ.get("JIRA_ISSUE_KEY")

        super().__init__(spec_dir=spec_dir, project_dir=project_dir)

    def _check_configured(self) -> bool:
        """
        Check if Jira integration has required credentials.

        Returns:
            True if JIRA_API_URL, JIRA_API_EMAIL, and JIRA_API_TOKEN are configured
        """
        return bool(self.api_url and self.api_email and self.api_token)

    def get_config(self) -> WebhookConfig:
        """
        Build the WebhookConfig for Jira.

        Constructs the Jira REST API endpoint URL for creating comments.

        Returns:
            WebhookConfig for sending Jira notifications

        Raises:
            ValueError: If JIRA_API_URL is not configured
        """
        if not self.api_url:
            raise ValueError("JIRA_API_URL environment variable is not set")

        # Build the Jira API URL for adding comments
        # If issue_key is set, use that specific issue
        # Otherwise, use a generic endpoint (will be determined per event)
        if self.issue_key:
            webhook_url = f"{self.api_url.rstrip('/')}/rest/api/3/issue/{self.issue_key}/comment"
        else:
            # Generic API URL - the actual issue key will be added dynamically
            webhook_url = f"{self.api_url.rstrip('/')}/rest/api/3/issue"

        return WebhookConfig(
            id="jira-notification",
            name="Jira Build Notifications",
            type=WebhookType.OUTGOING,
            integration=WebhookIntegration.JIRA,
            url=webhook_url,
            enabled=True,
            headers={
                "Authorization": f"Basic {self._get_auth_header()}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    def _get_auth_header(self) -> str:
        """
        Generate HTTP Basic Auth header for Jira API.

        Returns:
            Base64-encoded auth header string

        Raises:
            ValueError: If email or token are not configured
        """
        if not self.api_email or not self.api_token:
            raise ValueError("JIRA_API_EMAIL and JIRA_API_TOKEN must be set")

        import base64

        auth_string = f"{self.api_email}:{self.api_token}"
        encoded = base64.b64encode(auth_string.encode()).decode()
        return encoded

    async def test_connection(self) -> tuple[bool, str]:
        """
        Test the Jira API connection.

        Attempts to get the current user info from Jira to verify credentials.

        Returns:
            Tuple of (success, message) with test result
        """
        try:
            import httpx

            # Build API URL for getting current user
            api_url = f"{self.api_url.rstrip('/')}/rest/api/3/myself"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    api_url,
                    headers={
                        "Authorization": f"Basic {self._get_auth_header()}",
                        "Accept": "application/json",
                    },
                    timeout=10.0,
                )

                if response.status_code == 200:
                    user_data = response.json()
                    display_name = user_data.get("displayName", "Unknown")
                    return True, f"Successfully connected to Jira as {display_name}"
                else:
                    error_text = response.text
                    return False, f"Authentication failed: {response.status_code} - {error_text}"

        except Exception as e:
            logger.error(f"Jira connection test failed: {e}", exc_info=True)
            return False, f"Connection test failed: {e}"

    def format_payload(self, event: WebhookEvent) -> dict[str, Any]:
        """
        Format the webhook payload for Jira.

        Transforms WebhookEvent into Jira comment format using Jira markup.
        Supports rich formatting with headers, lists, code blocks, and tables.

        Args:
            event: Webhook event to format

        Returns:
            Jira-formatted comment payload

        Jira Comment Format:
            {
                "body": {
                    "version": 1,
                    "type": "doc",
                    "content": [...]
                }
            }

        Or for creating new issues:
            {
                "fields": {
                    "project": {"key": "PROJ"},
                    "summary": "...",
                    "description": {...},
                    "issuetype": {"name": "Task"}
                }
            }
        """
        event_type = event.type.value
        event_data = event.data

        # Get message details
        title, emoji = self._get_message_details(event_type, event_data)

        # Build comment body using Jira Atlassian Document Format (ADF)
        content = []

        # Header with emoji and title
        content.append({
            "type": "heading",
            "attrs": {"level": 3},
            "content": [
                {
                    "type": "text",
                    "text": f"{emoji} {title}",
                }
            ],
        })

        # Rule
        content.append({"type": "rule"})

        # Build event-specific content
        if event_type in ["build_started", "build_completed", "build_failed"]:
            spec_name = event_data.get("spec_name", "Unknown")
            spec_id = event_data.get("spec_id", "Unknown")

            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Spec: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": spec_name},
                ],
            })

            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "ID: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": spec_id},
                ],
            })

        elif event_type in ["subtask_started", "subtask_completed", "subtask_failed"]:
            subtask_id = event_data.get("subtask_id", "Unknown")
            subtask_desc = event_data.get("subtask_description", "")

            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Subtask: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": subtask_id},
                ],
            })

            if subtask_desc:
                content.append({
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": subtask_desc},
                    ],
                })

        # Add event-specific details
        if event_type == "build_started":
            total_subtasks = event_data.get("total_subtasks", 0)
            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Total Subtasks: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": str(total_subtasks)},
                ],
            })

        elif event_type == "build_completed":
            success = event_data.get("success", False)
            duration = event_data.get("duration_seconds", 0)

            status_text = "✅ Success" if success else "⚠️ Failed"
            duration_str = f"{duration:.1f}s" if duration < 60 else f"{duration/60:.1f}m"

            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Status: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": status_text},
                ],
            })

            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Duration: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": duration_str},
                ],
            })

        elif event_type == "build_failed":
            error = event_data.get("error_message", "Unknown error")
            failed_subtask = event_data.get("failed_subtask")

            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Error: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": error},
                ],
            })

            if failed_subtask:
                content.append({
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Failed Subtask: ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": failed_subtask},
                    ],
                })

        elif event_type == "subtask_completed":
            session = event_data.get("session_number", "Unknown")
            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Session: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": str(session)},
                ],
            })

        elif event_type == "subtask_failed":
            error = event_data.get("error_message", "Unknown error")
            attempt = event_data.get("attempt_number", 1)

            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Error: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": error},
                ],
            })

            content.append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Attempt: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": str(attempt)},
                ],
            })

        # Add metadata if available
        if event.metadata:
            metadata_items = []
            for key, value in event.metadata.items():
                if key not in ["internal_only"]:
                    metadata_items.append(f"{key}: {value}")

            if metadata_items:
                content.append({"type": "rule"})
                for item in metadata_items:
                    content.append({
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": item, "marks": [{"type": "code"}]},
                        ],
                    })

        # Build the final payload
        # If issue_key is set in config, create a comment
        # Otherwise, return data for creating a new issue
        if self.issue_key:
            # Create comment payload
            return {
                "body": {
                    "version": 1,
                    "type": "doc",
                    "content": content,
                }
            }
        else:
            # Create issue payload (for when no default issue is set)
            return {
                "fields": {
                    "project": {"key": self.project_key or "AUTO"},
                    "summary": f"{title} - {event_data.get('spec_name', 'Build')}",
                    "description": {
                        "version": 1,
                        "type": "doc",
                        "content": content,
                    },
                    "issuetype": {"name": "Task"},
                }
            }

    def _get_message_details(self, event_type: str, event_data: dict[str, Any]) -> tuple[str, str]:
        """
        Get message title and emoji for an event type.

        Args:
            event_type: Type of webhook event
            event_data: Event data dictionary

        Returns:
            Tuple of (title_text, emoji)
        """
        if event_type == "build_started":
            return "Build Started", "🚀"

        elif event_type == "build_completed":
            success = event_data.get("success", False)
            if success:
                return "Build Completed Successfully", "✅"
            else:
                return "Build Completed with Warnings", "⚠️"

        elif event_type == "build_failed":
            return "Build Failed", "❌"

        elif event_type == "subtask_started":
            return "Subtask Started", "🔧"

        elif event_type == "subtask_completed":
            return "Subtask Completed", "✅"

        elif event_type == "subtask_failed":
            return "Subtask Failed", "❌"

        elif event_type == "pr_opened":
            return "Pull Request Opened", "🔌"

        elif event_type == "pr_merged":
            return "Pull Request Merged", "🔀"

        elif event_type == "pr_closed":
            return "Pull Request Closed", "🔒"

        else:
            return "Auto Claude Notification", "📢"
