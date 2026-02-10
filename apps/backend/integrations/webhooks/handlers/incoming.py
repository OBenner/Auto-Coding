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
# GitHub Webhook Handler
# =============================================================================


class GitHubWebhookHandler(IncomingWebhookHandler):
    """
    Handler for GitHub webhooks.

    Processes incoming webhooks from GitHub for events like:
    - Push events (commits pushed to a branch)
    - Pull request events (PR opened, merged, closed)

    Extracts repository, branch, and commit information to trigger builds.
    """

    def validate_payload(self, payload: dict[str, Any]) -> bool:
        """
        Validate that the payload is a correctly formatted GitHub webhook.

        Args:
            payload: Webhook payload data

        Returns:
            True if payload is valid GitHub webhook, False otherwise
        """
        # GitHub webhooks should have a 'repository' key
        if "repository" not in payload:
            return False

        # Repository should be a dict with 'name' and 'full_name'
        repository = payload.get("repository", {})
        if not isinstance(repository, dict):
            return False

        if "name" not in repository or "full_name" not in repository:
            return False

        # Should have some kind of event indicator
        # Either 'ref' (for push) or 'pull_request' (for PR events)
        # or 'action' (for most other events)
        if not any(key in payload for key in ["ref", "pull_request", "action"]):
            return False

        return True

    def extract_event_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Extract relevant data from the GitHub webhook payload.

        Args:
            payload: Webhook payload data

        Returns:
            Dictionary with extracted data (event type, repo, branch, etc.)
        """
        repository = payload.get("repository", {})

        # Extract repository information
        repo_name = repository.get("name", "")
        repo_full_name = repository.get("full_name", "")
        repo_url = repository.get("html_url", "")
        clone_url = repository.get("clone_url", "")

        # Determine event type
        event_type = "unknown"
        if "ref" in payload:
            event_type = "push"
        elif "pull_request" in payload:
            event_type = "pull_request"

        # Extract branch/ref information
        ref = payload.get("ref", "")
        branch = ""

        if ref.startswith("refs/heads/"):
            branch = ref.replace("refs/heads/", "")
        elif ref.startswith("refs/tags/"):
            branch = ref.replace("refs/tags/", "")

        # Extract PR information if present
        pr_info = {}
        if "pull_request" in payload:
            pr = payload.get("pull_request", {})
            pr_info = {
                "pr_number": pr.get("number"),
                "pr_title": pr.get("title"),
                "pr_action": payload.get("action", ""),
                "pr_state": pr.get("state", ""),
                "pr_merged": pr.get("merged", False),
                "pr_merge_commit_sha": pr.get("merge_commit_sha"),
            }

        # Extract sender/actor information
        sender = payload.get("sender", {})
        actor = sender.get("login", "")

        # Extract commit information
        commit_info = {}
        if event_type == "push":
            commit_info = {
                "before": payload.get("before", ""),
                "after": payload.get("after", ""),
                "commits": [
                    {
                        "id": c.get("id"),
                        "message": c.get("message"),
                        "author": c.get("author", {}).get("name"),
                        "url": c.get("url"),
                    }
                    for c in payload.get("commits", [])
                ],
                "pusher": payload.get("pusher", {}).get("email", ""),
            }
        elif event_type == "pull_request":
            pr = payload.get("pull_request", {})
            commit_info = {
                "pr_head_sha": pr.get("head", {}).get("sha"),
                "pr_base_sha": pr.get("base", {}).get("sha"),
                "pr_merge_commit_sha": pr.get("merge_commit_sha"),
            }

        # Build extracted data
        extracted = {
            "integration": "github",
            "event_type": event_type,
            "repo_name": repo_name,
            "repo_full_name": repo_full_name,
            "repo_url": repo_url,
            "clone_url": clone_url,
            "ref": ref,
            "branch": branch,
            "actor": actor,
            **pr_info,
            "commits": commit_info,
        }

        # Add spec_id if available from webhook config mapping
        # This would be set when the webhook is configured
        # For now, we'll derive it from the branch name or PR title
        if branch:
            # Try to extract spec ID from branch name (e.g., "feature/084-xxx")
            if "-" in branch:
                parts = branch.split("-")
                if len(parts) >= 2 and parts[1].isdigit():
                    extracted["spec_id"] = f"{parts[0]}-{parts[1]}"

        return extracted

    def determine_action(self, payload: dict[str, Any]) -> WebhookAction:
        """
        Determine what action to take based on the GitHub webhook payload.

        Args:
            payload: Webhook payload data

        Returns:
            WebhookAction indicating what action to take
        """
        # Handle push events
        if "ref" in payload:
            ref = payload.get("ref", "")

            # Only trigger on branch pushes, not tags
            if ref.startswith("refs/heads/"):
                branch = ref.replace("refs/heads/", "")

                # Skip specific branches if needed
                # For example, skip build branches or dependency update bots
                if branch in ["main", "master", "develop"]:
                    # Could still trigger if configured
                    logger.debug(f"Push to {branch} - no action by default")
                    return WebhookAction.NO_ACTION

                # Trigger build for feature branches
                logger.info(f"Push to feature branch {branch} - triggering build")
                return WebhookAction.TRIGGER_BUILD

        # Handle pull request events
        if "pull_request" in payload:
            action = payload.get("action", "")
            pr = payload.get("pull_request", {})
            merged = pr.get("merged", False)

            # Only trigger on merged PRs
            if action == "closed" and merged:
                logger.info("PR merged - triggering build")
                return WebhookAction.TRIGGER_BUILD

            # Could also trigger when PR is opened for testing
            if action == "opened":
                logger.info("PR opened - could trigger test build")
                return WebhookAction.NO_ACTION

        return WebhookAction.NO_ACTION


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


# =============================================================================
# Handler Registration
# =============================================================================


# Register built-in handlers
HandlerRegistry.register("github", GitHubWebhookHandler)
