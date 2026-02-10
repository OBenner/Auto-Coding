"""
Incoming Webhook Handlers
=========================

Base classes and implementations for processing incoming webhooks from external services.
Handles parsing, validation, and triggering builds based on webhook events.

Design:
- Abstract base class `IncomingWebhookHandler` defines the handler interface
- Concrete implementations for GitHub, GitLab, and generic webhooks
- Each handler validates payload format, extracts relevant data, and triggers actions
- Handlers return structured results for logging and debugging

Usage:
    >>> from integrations.webhooks.handlers.incoming import GitHubWebhookHandler
    >>> handler = GitHubWebhookHandler(spec_dir=Path("/path/to/spec"))
    >>> result = handler.handle_webhook(webhook_config, payload)
    >>> print(result.action_taken)
"""

from __future__ import annotations

import logging
import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..models import WebhookConfig, WebhookEventType


# =============================================================================
# Logging
# =============================================================================


logger = logging.getLogger(__name__)


# =============================================================================
# Handler Result Types
# =============================================================================


class WebhookAction(str, Enum):
    """Actions that can be taken by webhook handlers."""

    TRIGGER_BUILD = "trigger_build"
    TRIGGER_SUBTASK = "trigger_subtask"
    UPDATE_STATUS = "update_status"
    NO_ACTION = "no_action"
    ERROR = "error"


class HandlerResult(BaseModel):
    """
    Result of processing a webhook.

    Encapsulates the outcome of webhook processing including
    what action was taken, any data extracted, and error information.
    """

    success: bool = Field(description="Whether processing was successful")
    action_taken: WebhookAction = Field(
        default=WebhookAction.NO_ACTION,
        description="What action was taken",
    )
    message: str = Field(
        default="",
        description="Human-readable result message",
    )
    extracted_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Data extracted from webhook payload",
    )
    error: str | None = Field(
        default=None,
        description="Error message if processing failed",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "action_taken": self.action_taken.value,
            "message": self.message,
            "extracted_data": self.extracted_data,
            "error": self.error,
        }


# =============================================================================
# Base Handler Interface
# =============================================================================


class IncomingWebhookHandler(ABC):
    """
    Abstract base class for incoming webhook handlers.

    Defines the interface for processing webhooks from external services.
    Concrete implementations handle specific webhook formats (GitHub, GitLab, etc.)

    Subclasses must implement:
    - validate_payload(): Check if payload is valid for this handler
    - extract_event_data(): Extract relevant data from payload
    - determine_action(): Decide what action to take based on payload

    The handler can optionally trigger builds or subtasks based on webhook events.
    """

    def __init__(
        self,
        spec_dir: Path,
        project_dir: Path | None = None,
    ):
        """
        Initialize the webhook handler.

        Args:
            spec_dir: Spec directory (contains implementation_plan.json)
            project_dir: Project root directory (for build triggering)
        """
        self.spec_dir = spec_dir
        self.project_dir = project_dir or spec_dir.parent.parent

    @abstractmethod
    def validate_payload(self, payload: dict[str, Any]) -> bool:
        """
        Validate that the payload is correctly formatted for this handler.

        Args:
            payload: Webhook payload data

        Returns:
            True if payload is valid, False otherwise
        """
        pass

    @abstractmethod
    def extract_event_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Extract relevant data from the webhook payload.

        Args:
            payload: Webhook payload data

        Returns:
            Dictionary of extracted data (event type, repo, branch, etc.)
        """
        pass

    @abstractmethod
    def determine_action(self, payload: dict[str, Any]) -> WebhookAction:
        """
        Determine what action to take based on the webhook payload.

        Args:
            payload: Webhook payload data

        Returns:
            WebhookAction indicating what action to take
        """
        pass

    def handle_webhook(
        self,
        webhook_config: WebhookConfig,
        payload: dict[str, Any],
    ) -> HandlerResult:
        """
        Process an incoming webhook.

        This is the main entry point for webhook processing. It validates
        the payload, extracts data, determines what action to take, and
        optionally executes that action (like triggering a build).

        Args:
            webhook_config: Configuration for this webhook
            payload: Webhook payload data

        Returns:
            HandlerResult with processing outcome
        """
        try:
            # Validate payload
            if not self.validate_payload(payload):
                return HandlerResult(
                    success=False,
                    action_taken=WebhookAction.ERROR,
                    message="Payload validation failed",
                    error="Invalid payload format for this handler",
                )

            # Extract event data
            event_data = self.extract_event_data(payload)
            logger.info(f"Extracted event data: {event_data}")

            # Determine action
            action = self.determine_action(payload)
            logger.info(f"Determined action: {action.value}")

            # Execute action if needed
            if action == WebhookAction.TRIGGER_BUILD:
                return self._handle_trigger_build(
                    webhook_config=webhook_config,
                    payload=payload,
                    event_data=event_data,
                )
            elif action == WebhookAction.TRIGGER_SUBTASK:
                return self._handle_trigger_subtask(
                    webhook_config=webhook_config,
                    payload=payload,
                    event_data=event_data,
                )
            else:
                return HandlerResult(
                    success=True,
                    action_taken=action,
                    message="Webhook processed successfully (no action taken)",
                    extracted_data=event_data,
                )

        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            return HandlerResult(
                success=False,
                action_taken=WebhookAction.ERROR,
                message="Webhook processing failed",
                error=str(e),
            )

    def _handle_trigger_build(
        self,
        webhook_config: WebhookConfig,
        payload: dict[str, Any],
        event_data: dict[str, Any],
    ) -> HandlerResult:
        """
        Handle triggering a build from a webhook.

        Args:
            webhook_config: Webhook configuration
            payload: Webhook payload
            event_data: Extracted event data

        Returns:
            HandlerResult with build trigger outcome
        """
        try:
            # For now, just log the intent to trigger
            # In a future subtask, this will integrate with the build system
            logger.info(
                f"Would trigger build for spec {event_data.get('spec_id')} "
                f"from webhook {webhook_config.id}"
            )

            return HandlerResult(
                success=True,
                action_taken=WebhookAction.TRIGGER_BUILD,
                message=f"Build trigger prepared for {event_data.get('spec_id', 'unknown')}",
                extracted_data=event_data,
            )

        except Exception as e:
            logger.error(f"Error triggering build: {e}", exc_info=True)
            return HandlerResult(
                success=False,
                action_taken=WebhookAction.ERROR,
                message="Failed to trigger build",
                error=str(e),
                extracted_data=event_data,
            )

    def _handle_trigger_subtask(
        self,
        webhook_config: WebhookConfig,
        payload: dict[str, Any],
        event_data: dict[str, Any],
    ) -> HandlerResult:
        """
        Handle triggering a specific subtask from a webhook.

        Args:
            webhook_config: Webhook configuration
            payload: Webhook payload
            event_data: Extracted event data

        Returns:
            HandlerResult with subtask trigger outcome
        """
        try:
            # For now, just log the intent to trigger
            # In a future subtask, this will integrate with the build system
            subtask_id = event_data.get("subtask_id", "unknown")
            logger.info(
                f"Would trigger subtask {subtask_id} "
                f"from webhook {webhook_config.id}"
            )

            return HandlerResult(
                success=True,
                action_taken=WebhookAction.TRIGGER_SUBTASK,
                message=f"Subtask trigger prepared for {subtask_id}",
                extracted_data=event_data,
            )

        except Exception as e:
            logger.error(f"Error triggering subtask: {e}", exc_info=True)
            return HandlerResult(
                success=False,
                action_taken=WebhookAction.ERROR,
                message="Failed to trigger subtask",
                error=str(e),
                extracted_data=event_data,
            )


# =============================================================================
# Handler Registry
# =============================================================================


class HandlerRegistry:
    """
    Registry for webhook handlers.

    Maps webhook integrations to their handler implementations.
    """

    _handlers: dict[str, type[IncomingWebhookHandler]] = {}

    @classmethod
    def register(
        cls,
        integration: str,
        handler_class: type[IncomingWebhookHandler],
    ) -> None:
        """
        Register a handler class for an integration type.

        Args:
            integration: Integration identifier (e.g., "github", "gitlab")
            handler_class: Handler class to register
        """
        cls._handlers[integration] = handler_class
        logger.debug(f"Registered webhook handler for integration: {integration}")

    @classmethod
    def get_handler(
        cls,
        integration: str,
        spec_dir: Path,
        project_dir: Path | None = None,
    ) -> IncomingWebhookHandler | None:
        """
        Get a handler instance for an integration.

        Args:
            integration: Integration identifier
            spec_dir: Spec directory
            project_dir: Project directory (optional)

        Returns:
            Handler instance or None if not registered
        """
        handler_class = cls._handlers.get(integration)
        if not handler_class:
            logger.warning(f"No handler registered for integration: {integration}")
            return None

        return handler_class(spec_dir=spec_dir, project_dir=project_dir)

    @classmethod
    def list_supported_integrations(cls) -> list[str]:
        """
        List all supported integrations.

        Returns:
            List of integration identifiers
        """
        return list(cls._handlers.keys())


# =============================================================================
# Utility Functions
# =============================================================================


def create_handler_for_webhook(
    webhook_config: WebhookConfig,
    spec_dir: Path,
    project_dir: Path | None = None,
) -> IncomingWebhookHandler | None:
    """
    Create a handler instance for a webhook configuration.

    Factory function that creates the appropriate handler based on
    the webhook's integration type.

    Args:
        webhook_config: Webhook configuration
        spec_dir: Spec directory
        project_dir: Project directory (optional)

    Returns:
        Handler instance or None if integration not supported

    Examples:
        >>> handler = create_handler_for_webhook(
        ...     webhook_config,
        ...     spec_dir=Path("/path/to/spec"),
        ... )
        >>> result = handler.handle_webhook(webhook_config, payload)
    """
    integration = webhook_config.integration.value
    return HandlerRegistry.get_handler(integration, spec_dir, project_dir)
