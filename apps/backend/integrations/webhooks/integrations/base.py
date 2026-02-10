"""
Base Integration Class
=======================

Abstract base class for all webhook integrations (Slack, Discord, Teams, Jira).

Provides a common interface for:
- Configuration management (load/save from env and JSON)
- Connection testing
- Webhook sending with integration-specific payload formatting
- State persistence
- Graceful degradation when integration is not configured

Design:
- BaseIntegration provides the interface and common functionality
- Each integration (Slack, Discord, etc.) extends BaseIntegration
- Integrations are OPTIONAL - if not configured, operations gracefully no-op
- State is persisted to spec_dir for each integration separately

Example:
    >>> from integrations.webhooks.integrations.slack import SlackIntegration
    >>> integration = SlackIntegration(spec_dir=Path("/path/to/spec"))
    >>> if integration.is_enabled:
    ...     result = await integration.send_notification(event)
"""

from __future__ import annotations

import abc
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ..models import WebhookConfig, WebhookEvent, WebhookIntegration, WebhookType


# =============================================================================
# Logging
# =============================================================================


logger = logging.getLogger(__name__)


# =============================================================================
# Integration State
# =============================================================================


class IntegrationStatus(str, Enum):
    """Status of integration connection."""

    NOT_CONFIGURED = "not_configured"  # No credentials/config
    DISABLED = "disabled"  # Configured but disabled
    CONNECTED = "connected"  # Successfully connected
    ERROR = "error"  # Connection error


@dataclass
class IntegrationState:
    """
    State of an integration for a spec.

    Tracks:
    - Whether integration is enabled
    - Last connection test result
    - Configuration metadata
    - Statistics (sent, failed, last sent timestamp)
    """

    enabled: bool = False
    configured: bool = False
    connection_status: IntegrationStatus = IntegrationStatus.NOT_CONFIGURED
    last_tested_at: str | None = None
    last_test_result: str | None = None
    total_sent: int = 0
    total_failed: int = 0
    last_sent_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "enabled": self.enabled,
            "configured": self.configured,
            "connection_status": self.connection_status.value,
            "last_tested_at": self.last_tested_at,
            "last_test_result": self.last_test_result,
            "total_sent": self.total_sent,
            "total_failed": self.total_failed,
            "last_sent_at": self.last_sent_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntegrationState":
        """Create IntegrationState from dictionary."""
        connection_status = data.get("connection_status", "not_configured")
        if isinstance(connection_status, str):
            connection_status = IntegrationStatus(connection_status)

        return cls(
            enabled=data.get("enabled", False),
            configured=data.get("configured", False),
            connection_status=connection_status,
            last_tested_at=data.get("last_tested_at"),
            last_test_result=data.get("last_test_result"),
            total_sent=data.get("total_sent", 0),
            total_failed=data.get("total_failed", 0),
            last_sent_at=data.get("last_sent_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata", {}),
        )

    def save(self, spec_dir: Path, integration_name: str) -> None:
        """Save state to the spec directory."""
        state_file = spec_dir / f".integration_{integration_name}.json"
        self.updated_at = datetime.now().isoformat()

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, spec_dir: Path, integration_name: str) -> "IntegrationState | None":
        """Load state from the spec directory."""
        state_file = spec_dir / f".integration_{integration_name}.json"
        if not state_file.exists():
            return None

        try:
            with open(state_file, encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to load integration state for {integration_name}: {e}")
            return None


# =============================================================================
# Base Integration Class
# =============================================================================


class BaseIntegration(abc.ABC):
    """
    Abstract base class for webhook integrations.

    All integrations (Slack, Discord, Teams, Jira) must:
    1. Implement the abstract methods (get_config, test_connection, format_payload)
    2. Call super().__init__ to set up common state
    3. Use send_notification for all webhook deliveries (handles logging + state)

    Integrations are OPTIONAL:
    - If not configured, is_enabled returns False
    - All operations gracefully no-op when not enabled
    - State is persisted to spec_dir for each integration

    Example:
        >>> class SlackIntegration(BaseIntegration):
        ...     def get_config(self) -> WebhookConfig:
        ...         # Build Slack webhook config
        ...         pass
        ...
        ...     async def test_connection(self) -> tuple[bool, str]:
        ...         # Test Slack webhook
        ...         pass
        ...
        ...     def format_payload(self, event: WebhookEvent) -> dict[str, Any]:
        ...         # Format Slack-specific payload
        ...         pass
    """

    # Integration identifier (must match WebhookIntegration enum)
    INTEGRATION_NAME: str = None  # type: ignore[assignment]

    def __init__(self, spec_dir: Path, project_dir: Path | None = None):
        """
        Initialize the integration.

        Args:
            spec_dir: Spec directory (for state persistence)
            project_dir: Optional project root directory
        """
        if not self.INTEGRATION_NAME:
            raise ValueError("INTEGRATION_NAME must be defined in subclass")

        self.spec_dir = spec_dir
        self.project_dir = project_dir or spec_dir.parent.parent

        # Load state from disk
        self.state = IntegrationState.load(spec_dir, self.INTEGRATION_NAME)
        if not self.state:
            self.state = IntegrationState()

        # Check if integration is configured (has credentials)
        self.state.configured = self._check_configured()

        # Update connection status based on configuration
        if not self.state.configured:
            self.state.connection_status = IntegrationStatus.NOT_CONFIGURED
        elif not self.state.enabled:
            self.state.connection_status = IntegrationStatus.DISABLED
        # If configured and enabled, keep last status or default to CONNECTED
        elif self.state.connection_status == IntegrationStatus.NOT_CONFIGURED:
            self.state.connection_status = IntegrationStatus.CONNECTED

    @property
    def is_enabled(self) -> bool:
        """Check if integration is enabled and configured."""
        return self.state.enabled and self.state.configured

    @property
    def is_configured(self) -> bool:
        """Check if integration has required credentials/configuration."""
        return self.state.configured

    @abc.abstractmethod
    def get_config(self) -> WebhookConfig:
        """
        Build the WebhookConfig for this integration.

        Called by send_notification to get the webhook configuration.
        Must return a valid WebhookConfig with URL and authentication.

        Returns:
            WebhookConfig for sending webhooks

        Example:
            >>> def get_config(self) -> WebhookConfig:
            ...     webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
            ...     return WebhookConfig(
            ...         id="slack-notification",
            ...         name="Slack Notifications",
            ...         type=WebhookType.OUTGOING,
            ...         integration=WebhookIntegration.SLACK,
            ...         url=webhook_url,
            ...     )
        """
        pass

    @abc.abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """
        Test the integration connection.

        Sends a test webhook to verify the integration is working.
        Updates state with test result.

        Returns:
            Tuple of (success, message) where:
            - success: True if connection test passed
            - message: Human-readable result message

        Example:
            >>> async def test_connection(self) -> tuple[bool, str]:
            ...     try:
            ...         await self.send_test_message()
            ...         return True, "Connection successful"
            ...     except Exception as e:
            ...         return False, f"Connection failed: {e}"
        """
        pass

    @abc.abstractmethod
    def format_payload(self, event: WebhookEvent) -> dict[str, Any]:
        """
        Format the webhook payload for this integration.

        Transforms the standard WebhookEvent into integration-specific format.
        Called by send_notification before sending the webhook.

        Args:
            event: Webhook event to format

        Returns:
            Integration-specific payload dictionary

        Example:
            >>> def format_payload(self, event: WebhookEvent) -> dict[str, Any]:
            ...     if event.type.value == "build_completed":
            ...         return {
            ...             "text": f"Build completed: {event.data['spec_name']}"
            ...         }
            ...     return {"text": f"Event: {event.type.value}"}
        """
        pass

    async def send_notification(self, event: WebhookEvent) -> tuple[bool, str]:
        """
        Send a notification webhook.

        Main entry point for sending notifications. This method:
        1. Checks if integration is enabled
        2. Gets the integration config
        3. Formats the payload
        4. Sends the webhook
        5. Updates state and logs

        Args:
            event: Webhook event to send

        Returns:
            Tuple of (success, message) where:
            - success: True if webhook was sent successfully
            - message: Human-readable result message

        Example:
            >>> integration = SlackIntegration(spec_dir=Path("/path/to/spec"))
            >>> event = WebhookEvent.build_completed("001", "My Feature", True, 120.5)
            >>> success, message = await integration.send_notification(event)
            >>> print(f"Notification sent: {success}")
        """
        # Check if integration is enabled
        if not self.is_enabled:
            logger.debug(f"{self.INTEGRATION_NAME} integration is not enabled, skipping notification")
            return False, "Integration is not enabled"

        # Get config
        try:
            config = self.get_config()
        except Exception as e:
            logger.error(f"Failed to get {self.INTEGRATION_NAME} config: {e}")
            return False, f"Configuration error: {e}"

        # Import here to avoid circular imports
        from ..handlers.outgoing import OutgoingWebhookSender

        # Send webhook
        sender = OutgoingWebhookSender(spec_dir=self.spec_dir)

        try:
            # Format payload using integration-specific formatter
            payload = self.format_payload(event)

            # Create a modified event with the formatted payload
            formatted_event = WebhookEvent(
                type=event.type,
                data=payload,  # Use formatted payload as event data
                timestamp=event.timestamp,
                metadata=event.metadata,
            )

            # Send webhook
            result = await sender.send_webhook(config, formatted_event)

            # Update state
            if result.success:
                self.state.total_sent += 1
                self.state.last_sent_at = datetime.now().isoformat()
                self.state.connection_status = IntegrationStatus.CONNECTED
                self.state.save(self.spec_dir, self.INTEGRATION_NAME)

                logger.info(f"{self.INTEGRATION_NAME} notification sent successfully")
                return True, "Notification sent successfully"
            else:
                self.state.total_failed += 1
                self.state.connection_status = IntegrationStatus.ERROR
                self.state.save(self.spec_dir, self.INTEGRATION_NAME)

                error_msg = result.log_entry.error_message or "Unknown error"
                logger.warning(f"{self.INTEGRATION_NAME} notification failed: {error_msg}")
                return False, f"Failed to send notification: {error_msg}"

        except Exception as e:
            # Update state with error
            self.state.total_failed += 1
            self.state.connection_status = IntegrationStatus.ERROR
            self.state.save(self.spec_dir, self.INTEGRATION_NAME)

            logger.error(f"Error sending {self.INTEGRATION_NAME} notification: {e}", exc_info=True)
            return False, f"Error: {e}"

        finally:
            await sender.close()

    async def test(self) -> tuple[bool, str]:
        """
        Test the integration connection and update state.

        Public method for testing integration from UI or CLI.
        Updates state with test result and timestamp.

        Returns:
            Tuple of (success, message) with test result
        """
        success, message = await self.test_connection()

        # Update state
        self.state.last_tested_at = datetime.now().isoformat()
        self.state.last_test_result = message

        if success:
            self.state.connection_status = IntegrationStatus.CONNECTED
        else:
            self.state.connection_status = IntegrationStatus.ERROR

        self.state.save(self.spec_dir, self.INTEGRATION_NAME)

        return success, message

    def enable(self) -> None:
        """Enable the integration."""
        self.state.enabled = True
        self.state.save(self.spec_dir, self.INTEGRATION_NAME)
        logger.info(f"{self.INTEGRATION_NAME} integration enabled")

    def disable(self) -> None:
        """Disable the integration."""
        self.state.enabled = False
        self.state.connection_status = IntegrationStatus.DISABLED
        self.state.save(self.spec_dir, self.INTEGRATION_NAME)
        logger.info(f"{self.INTEGRATION_NAME} integration disabled")

    def get_status(self) -> dict[str, Any]:
        """
        Get the current status of the integration.

        Returns:
            Dict with status information for UI display

        Example:
            >>> status = integration.get_status()
            >>> print(status['enabled'], status['connection_status'])
        """
        return {
            "integration": self.INTEGRATION_NAME,
            "enabled": self.state.enabled,
            "configured": self.state.configured,
            "connection_status": self.state.connection_status.value,
            "last_tested_at": self.state.last_tested_at,
            "last_test_result": self.state.last_test_result,
            "total_sent": self.state.total_sent,
            "total_failed": self.state.total_failed,
            "last_sent_at": self.state.last_sent_at,
        }

    def _check_configured(self) -> bool:
        """
        Check if integration has required credentials.

        Called during initialization to set state.configured.
        Subclasses can override for custom configuration checks.

        Returns:
            True if integration has required credentials

        Example:
            >>> def _check_configured(self) -> bool:
            ...     return bool(os.environ.get("SLACK_WEBHOOK_URL"))
        """
        # Default implementation: subclass should override
        return False


# =============================================================================
# Utility Functions
# =============================================================================


def get_integration(
    integration_name: str,
    spec_dir: Path,
    project_dir: Path | None = None,
) -> BaseIntegration | None:
    """
    Factory function to get an integration instance.

    Args:
        integration_name: Name of integration (slack, discord, teams, jira)
        spec_dir: Spec directory
        project_dir: Optional project root directory

    Returns:
        Integration instance or None if integration not found

    Example:
        >>> integration = get_integration("slack", spec_dir=Path("/path/to/spec"))
        >>> if integration and integration.is_enabled:
        ...     await integration.send_notification(event)
    """
    # Import integrations dynamically to avoid circular imports
    try:
        if integration_name == "slack":
            from .slack import SlackIntegration

            return SlackIntegration(spec_dir=spec_dir, project_dir=project_dir)
        elif integration_name == "discord":
            from .discord import DiscordIntegration

            return DiscordIntegration(spec_dir=spec_dir, project_dir=project_dir)
        elif integration_name == "teams":
            from .teams import TeamsIntegration

            return TeamsIntegration(spec_dir=spec_dir, project_dir=project_dir)
        elif integration_name == "jira":
            from .jira import JiraIntegration

            return JiraIntegration(spec_dir=spec_dir, project_dir=project_dir)
        else:
            logger.warning(f"Unknown integration: {integration_name}")
            return None
    except ImportError as e:
        logger.error(f"Failed to import integration {integration_name}: {e}")
        return None


def get_all_integrations(
    spec_dir: Path,
    project_dir: Path | None = None,
) -> dict[str, BaseIntegration]:
    """
    Get all available integration instances.

    Args:
        spec_dir: Spec directory
        project_dir: Optional project root directory

    Returns:
        Dict mapping integration name to instance

    Example:
        >>> integrations = get_all_integrations(spec_dir=Path("/path/to/spec"))
        >>> for name, integration in integrations.items():
        ...     print(f"{name}: enabled={integration.is_enabled}")
    """
    integrations = {}

    for name in ["slack", "discord", "teams", "jira"]:
        integration = get_integration(name, spec_dir, project_dir)
        if integration:
            integrations[name] = integration

    return integrations
