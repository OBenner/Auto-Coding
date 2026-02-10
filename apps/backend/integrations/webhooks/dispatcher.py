"""
Webhook Event Dispatcher
========================

Central dispatcher for webhook events throughout the agent lifecycle.
Bridges phase events, build lifecycle, and QA events to webhook delivery.

Design Principles:
- Non-blocking: Webhook delivery never blocks main execution
- Graceful degradation: Failures don't crash the application
- Simple API: Single function call to dispatch events
- Async-first: Uses asyncio for parallel webhook delivery

Event Flow:
  1. Application calls dispatch_event()
  2. Dispatcher loads webhook configs for spec
  3. Filters webhooks by event subscription
  4. Builds payloads for each webhook template
  5. Delivers in parallel via WebhookDeliverySystem
  6. Returns immediately (delivery happens in background)
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Import models and delivery
from integrations.webhooks.config import get_event_title
from integrations.webhooks.delivery import (
    WebhookDeliverySystem,
)
from integrations.webhooks.models import (
    WebhookConfig,
    WebhookEvent,
)

# Debug mode for verbose logging
_DEBUG = os.environ.get("DEBUG_WEBHOOKS", "").lower() in ("1", "true", "yes")


def _log_debug(message: str) -> None:
    """Log debug message if debug mode is enabled."""
    if _DEBUG:
        try:
            print(f"[webhook:dispatcher] {message}", flush=True)
        except (OSError, UnicodeEncodeError):
            pass  # Silent on I/O failure


class WebhookDispatcher:
    """
    Central dispatcher for webhook events.

    Manages webhook event delivery throughout the agent lifecycle.
    Loads configuration, builds payloads, and coordinates delivery.
    """

    def __init__(
        self,
        spec_dir: Path,
        project_dir: Path | None = None,
    ):
        """
        Initialize webhook dispatcher.

        Args:
            spec_dir: Spec directory containing webhook configuration
            project_dir: Optional project directory for additional context
        """
        self.spec_dir = spec_dir
        self.project_dir = project_dir
        self.config_dir = spec_dir / ".webhooks" / "configs"
        self.delivery_dir = spec_dir / ".webhooks" / "deliveries"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.delivery_dir.mkdir(parents=True, exist_ok=True)

    def dispatch_event(
        self,
        event: WebhookEvent | str,
        data: dict[str, Any] | None = None,
        *,
        blocking: bool = False,
    ) -> list[Any] | None:
        """
        Dispatch a webhook event (sync wrapper).

        This is the main entry point for sending webhook events.
        By default, returns immediately and delivers in the background.

        Args:
            event: Event type to dispatch
            data: Event-specific data (spec_id, status, metrics, etc.)
            blocking: If True, wait for delivery to complete (default: False)

        Returns:
            None if blocking=False, list of delivery results if blocking=True
        """
        # Create async task
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context - create task
                asyncio.create_task(self._dispatch_async(event, data or {}))
                return None
            else:
                # Not in async context - run in new loop
                if blocking:
                    return asyncio.run(self._dispatch_async(event, data or {}))
                else:
                    # Run in background thread
                    asyncio.run(self._dispatch_async(event, data or {}))
                    return None
        except (RuntimeError, OSError) as e:
            _log_debug(f"Failed to dispatch event: {e}")
            return None

    async def _dispatch_async(
        self,
        event: WebhookEvent | str,
        data: dict[str, Any],
    ) -> list[Any]:
        """
        Internal async dispatch implementation.

        Args:
            event: Event type to dispatch
            data: Event-specific data

        Returns:
            List of delivery results
        """
        try:
            # Normalize event
            event_obj = (
                WebhookEvent.from_string(event)
                if isinstance(event, str)
                else event
            )
            event_str = event_obj.value
        except (ValueError, AttributeError):
            _log_debug(f"Invalid event type: {event}")
            return []

        # Load webhook configurations
        try:
            all_webhooks = WebhookConfig.load_all(self.config_dir)
            # Filter webhooks that should receive this event
            webhooks = [w for w in all_webhooks if w.should_send_event(event_obj)]
        except (OSError, ValueError) as e:
            _log_debug(f"Failed to load webhooks: {e}")
            return []

        if not webhooks:
            _log_debug(f"No webhooks configured for event: {event_str}")
            return []

        _log_debug(
            f"Dispatching {event_str} to {len(webhooks)} webhook(s)"
        )

        # Build payload for each webhook
        # For now, use generic payload (template system comes in phase-3)
        payloads = []
        for webhook in webhooks:
            payload = self._build_payload(webhook, event_obj, data)
            payloads.append(payload)

        # Deliver webhooks in parallel
        delivery_system = WebhookDeliverySystem(self.delivery_dir)

        results = []
        for webhook, payload in zip(webhooks, payloads):
            try:
                delivery = await delivery_system.deliver(
                    webhook,
                    event_str,
                    payload,
                )
                results.append(delivery)

                _log_debug(
                    f"Webhook {webhook.webhook_id}: "
                    f"{delivery.status.value}"
                )
            except Exception as e:
                _log_debug(
                    f"Webhook {webhook.webhook_id} failed: {e}"
                )
                # Continue with other webhooks

        return results

    def _build_payload(
        self,
        webhook: WebhookConfig,
        event: WebhookEvent,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build webhook payload.

        Creates a standardized payload with event data and context.
        Template customization will be added in phase-3.

        Args:
            webhook: Webhook configuration
            event: Event type
            data: Event-specific data

        Returns:
            Payload dictionary
        """
        # Extract common context
        spec_id = data.get("spec_id", self.spec_dir.name)
        spec_title = data.get("spec_title", "")
        project_dir = str(self.project_dir) if self.project_dir else ""

        # Build standardized payload
        payload: dict[str, Any] = {
            "event": event.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "spec": {
                "id": spec_id,
                "title": spec_title,
                "directory": str(self.spec_dir),
            },
        }

        # Add project context if available
        if project_dir:
            payload["project"] = {
                "directory": project_dir,
            }

        # Merge event-specific data
        payload.update(data)

        # Add webhook metadata
        payload["webhook"] = {
            "id": webhook.webhook_id,
            "name": webhook.name,
            "delivered_at": datetime.now(UTC).isoformat(),
        }

        return payload

    def dispatch_sync(
        self,
        event: WebhookEvent | str,
        data: dict[str, Any] | None = None,
    ) -> list[Any]:
        """
        Dispatch event and wait for completion (sync).

        Convenience method for blocking delivery.

        Args:
            event: Event type to dispatch
            data: Event-specific data

        Returns:
            List of delivery results
        """
        return self.dispatch_event(event, data, blocking=True) or []

    def test_webhook(
        self,
        webhook_id: str,
    ) -> dict[str, Any]:
        """
        Send a test event to a webhook.

        Useful for verifying webhook configuration in the UI.

        Args:
            webhook_id: ID of webhook to test

        Returns:
            Test result dictionary
        """
        try:
            # Load webhook configuration
            webhook = WebhookConfig.load(self.config_dir, webhook_id)
            if not webhook:
                return {
                    "success": False,
                    "error": "Webhook not found",
                }

            # Build test payload
            test_data = {
                "spec_id": self.spec_dir.name,
                "spec_title": "Test Webhook",
                "test": True,
                "message": "This is a test webhook event",
            }

            # Deliver test event
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context
                result = asyncio.create_task(
                    self._test_webhook_async(webhook, test_data)
                )
                return {
                    "success": True,
                    "message": "Test webhook sent",
                    "webhook_id": webhook_id,
                }
            else:
                # Run in new loop
                delivery = asyncio.run(
                    self._test_webhook_async(webhook, test_data)
                )

                return {
                    "success": delivery.status.value == "success",
                    "message": "Test webhook delivered",
                    "webhook_id": webhook_id,
                    "status": delivery.status.value,
                    "response_code": delivery.response_status_code,
                    "error": delivery.error_message,
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "webhook_id": webhook_id,
            }

    async def _test_webhook_async(
        self,
        webhook: WebhookConfig,
        test_data: dict[str, Any],
    ) -> Any:
        """Async test webhook delivery."""
        delivery_system = WebhookDeliverySystem(self.delivery_dir)
        payload = self._build_payload(
            webhook,
            WebhookEvent.SPEC_CREATED,
            test_data,
        )
        payload["test"] = True
        return await delivery_system.deliver(
            webhook,
            "test",
            payload,
        )

    def get_delivery_history(
        self,
        webhook_id: str | None = None,
        event: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get webhook delivery history.

        Args:
            webhook_id: Optional webhook ID to filter by
            event: Optional event type to filter by
            limit: Maximum number of records to return

        Returns:
            List of delivery records as dictionaries
        """
        try:
            delivery_system = WebhookDeliverySystem(self.delivery_dir)
            deliveries = delivery_system.get_delivery_history(
                webhook_id, event, limit
            )
            return [d.to_dict() for d in deliveries]
        except (OSError, ValueError):
            return []

    def get_delivery_stats(
        self,
        webhook_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Get webhook delivery statistics.

        Args:
            webhook_id: Optional webhook ID to filter by

        Returns:
            Statistics dictionary
        """
        try:
            delivery_system = WebhookDeliverySystem(self.delivery_dir)
            return delivery_system.get_delivery_stats(webhook_id)
        except (OSError, ValueError):
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "pending": 0,
                "success_rate": 0,
                "avg_duration_ms": 0,
            }


# Convenience functions for quick dispatch


def get_dispatcher(spec_dir: Path, project_dir: Path | None = None) -> WebhookDispatcher:
    """
    Get or create a webhook dispatcher for a spec.

    Args:
        spec_dir: Spec directory
        project_dir: Optional project directory

    Returns:
        WebhookDispatcher instance
    """
    return WebhookDispatcher(spec_dir, project_dir)


def dispatch_event(
    spec_dir: Path,
    event: WebhookEvent | str,
    data: dict[str, Any] | None = None,
    *,
    blocking: bool = False,
    project_dir: Path | None = None,
) -> list[Any] | None:
    """
    Dispatch a webhook event (convenience function).

    Quick one-liner to dispatch events without managing dispatcher instance.

    Args:
        spec_dir: Spec directory
        event: Event type to dispatch
        data: Event-specific data
        blocking: If True, wait for delivery to complete
        project_dir: Optional project directory

    Returns:
        None if blocking=False, list of delivery results if blocking=True

    Example:
        dispatch_event(
            spec_dir,
            WebhookEvent.BUILD_STARTED,
            {"spec_id": "123", "spec_title": "My Feature"}
        )
    """
    dispatcher = get_dispatcher(spec_dir, project_dir)
    return dispatcher.dispatch_event(event, data, blocking=blocking)


def dispatch_spec_created(
    spec_dir: Path,
    spec_id: str,
    spec_title: str,
    **extra_data,
) -> None:
    """
    Dispatch spec_created event.

    Convenience function for spec creation events.

    Args:
        spec_dir: Spec directory
        spec_id: Spec ID
        spec_title: Spec title
        **extra_data: Additional event data
    """
    data = {
        "spec_id": spec_id,
        "spec_title": spec_title,
        **extra_data,
    }
    dispatch_event(spec_dir, WebhookEvent.SPEC_CREATED, data)


def dispatch_build_started(
    spec_dir: Path,
    spec_id: str,
    **extra_data,
) -> None:
    """
    Dispatch build_started event.

    Convenience function for build start events.

    Args:
        spec_dir: Spec directory
        spec_id: Spec ID
        **extra_data: Additional event data
    """
    data = {
        "spec_id": spec_id,
        **extra_data,
    }
    dispatch_event(spec_dir, WebhookEvent.BUILD_STARTED, data)


def dispatch_build_completed(
    spec_dir: Path,
    spec_id: str,
    success: bool = True,
    **extra_data,
) -> None:
    """
    Dispatch build_completed event.

    Convenience function for build completion events.

    Args:
        spec_dir: Spec directory
        spec_id: Spec ID
        success: Whether build succeeded
        **extra_data: Additional event data
    """
    event = (
        WebhookEvent.BUILD_COMPLETED
        if success
        else WebhookEvent.BUILD_FAILED
    )
    data = {
        "spec_id": spec_id,
        "success": success,
        **extra_data,
    }
    dispatch_event(spec_dir, event, data)


def dispatch_qa_result(
    spec_dir: Path,
    spec_id: str,
    passed: bool,
    **extra_data,
) -> None:
    """
    Dispatch QA result event.

    Convenience function for QA completion events.

    Args:
        spec_dir: Spec directory
        spec_id: Spec ID
        passed: Whether QA passed
        **extra_data: Additional event data
    """
    event = (
        WebhookEvent.QA_PASSED
        if passed
        else WebhookEvent.QA_FAILED
    )
    data = {
        "spec_id": spec_id,
        **extra_data,
    }
    dispatch_event(spec_dir, event, data)


def dispatch_merged(
    spec_dir: Path,
    spec_id: str,
    **extra_data,
) -> None:
    """
    Dispatch merged event.

    Convenience function for merge events.

    Args:
        spec_dir: Spec directory
        spec_id: Spec ID
        **extra_data: Additional event data
    """
    data = {
        "spec_id": spec_id,
        **extra_data,
    }
    dispatch_event(spec_dir, WebhookEvent.MERGED, data)
