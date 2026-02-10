"""
Webhook Delivery System - Reliable Webhook Delivery with Retry Logic
=====================================================================

Provides reliable webhook delivery with exponential backoff retry logic.
Handles HTTP delivery, signature generation, and delivery state tracking.

Design Principles:
- Exponential backoff retry for failed deliveries
- Graceful degradation if webhook endpoint is unavailable
- Comprehensive delivery tracking for debugging
- Timeout handling to prevent blocking

Delivery Flow:
  1. Generate payload with signature
  2. Send HTTP request with timeout
  3. Track delivery attempt (success/failure)
  4. Retry on failure with exponential backoff
  5. Mark as permanent failure after max retries
"""

from __future__ import annotations

import asyncio
import hmac
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

# Import models
from integrations.webhooks.models import (
    WebhookConfig,
    WebhookDelivery,
    WebhookDeliveryStatus,
    generate_delivery_id,
)

# Import configuration
from integrations.webhooks.config import (
    DEFAULT_TIMEOUT,
    MAX_TIMEOUT,
    SIGNATURE_HEADER,
    SIGNATURE_VERSION,
)

# Default retry configuration
DEFAULT_RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 1.0,  # seconds
    "max_delay": 60.0,  # seconds
    "backoff_multiplier": 2.0,
}


class WebhookDeliveryError(Exception):
    """Base exception for webhook delivery errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class WebhookTimeoutError(WebhookDeliveryError):
    """Exception raised when webhook request times out."""

    pass


class WebhookConnectionError(WebhookDeliveryError):
    """Exception raised when webhook connection fails."""

    pass


class WebhookPermanentError(WebhookDeliveryError):
    """Exception raised for permanent webhook failures (4xx errors)."""

    pass


def generate_signature(payload: dict[str, Any], secret: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.

    Args:
        payload: JSON payload to sign
        secret: Secret key for signature

    Returns:
        Signature string with version prefix
    """
    # Convert payload to JSON string without whitespace
    payload_str = json.dumps(payload, separators=(",", ":"))

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256,
    ).hexdigest()

    return f"{SIGNATURE_VERSION}={signature}"


def verify_signature(
    payload: dict[str, Any], signature: str, secret: str
) -> bool:
    """
    Verify webhook signature.

    Args:
        payload: JSON payload to verify
        signature: Signature from webhook header
        secret: Secret key for verification

    Returns:
        True if signature is valid
    """
    expected = generate_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


async def send_webhook_http(
    url: str,
    payload: dict[str, Any],
    secret: str | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[int, str | None]:
    """
    Send webhook via HTTP with optional signature.

    Args:
        url: Webhook URL
        payload: JSON payload to send
        secret: Optional secret for signature generation
        headers: Optional custom headers
        timeout: Request timeout in seconds

    Returns:
        Tuple of (status_code, response_body)

    Raises:
        WebhookTimeoutError: If request times out
        WebhookConnectionError: If connection fails
        WebhookPermanentError: For 4xx errors
        WebhookDeliveryError: For other delivery errors
    """
    # Prepare headers
    request_headers = {
        "Content-Type": "application/json",
        "User-Agent": "Auto-Claude-Webhook/1.0",
    }

    if headers:
        request_headers.update(headers)

    # Add signature if secret is provided
    if secret:
        signature = generate_signature(payload, secret)
        request_headers[SIGNATURE_HEADER] = signature

    # Clamp timeout to max
    timeout = min(timeout, MAX_TIMEOUT)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json=payload,
                headers=request_headers,
            )

            # Get response body (limit to 10KB to prevent memory issues)
            response_body = response.text[:10240] if response.text else None

            # Check for permanent errors (4xx)
            if 400 <= response.status_code < 500:
                raise WebhookPermanentError(
                    f"Permanent error: {response.status_code}",
                    status_code=response.status_code,
                )

            # Return status code and body
            return response.status_code, response_body

    except asyncio.TimeoutError as e:
        raise WebhookTimeoutError(f"Request timed out after {timeout}s") from e

    except httpx.ConnectError as e:
        raise WebhookConnectionError(f"Connection failed: {e}") from e

    except httpx.TimeoutException as e:
        raise WebhookTimeoutError(f"Request timed out: {e}") from e

    except WebhookPermanentError:
        raise

    except Exception as e:
        raise WebhookDeliveryError(f"Delivery failed: {e}") from e


class WebhookDeliverySystem:
    """
    Manages webhook delivery with retry logic.

    Handles delivery attempts, retry scheduling, and state tracking.
    """

    def __init__(
        self,
        delivery_dir: Path,
    ):
        """
        Initialize webhook delivery system.

        Args:
            delivery_dir: Directory to store delivery records
        """
        self.delivery_dir = delivery_dir
        self.delivery_dir.mkdir(parents=True, exist_ok=True)

    async def deliver(
        self,
        webhook: WebhookConfig,
        event: str,
        payload: dict[str, Any],
    ) -> WebhookDelivery:
        """
        Deliver a webhook with retry logic.

        Args:
            webhook: Webhook configuration
            event: Event type being delivered
            payload: Payload to deliver

        Returns:
            WebhookDelivery record with delivery status
        """
        delivery = WebhookDelivery(
            delivery_id=generate_delivery_id(),
            webhook_id=webhook.webhook_id,
            event=event,
            status=WebhookDeliveryStatus.SENDING,
            payload=payload,
        )

        # Save initial delivery record
        delivery.save(self.delivery_dir)

        # Attempt delivery with retries
        attempt = 0
        max_retries = webhook.retry_config.get("max_retries", DEFAULT_RETRY_CONFIG["max_retries"])

        while attempt <= max_retries:
            delivery.attempt_number = attempt + 1
            delivery.status = WebhookDeliveryStatus.SENDING
            delivery.save(self.delivery_dir)

            try:
                # Measure delivery time
                start_time = datetime.now(UTC)

                # Send webhook
                status_code, response_body = await send_webhook_http(
                    url=webhook.url,
                    payload=payload,
                    secret=webhook.secret,
                    headers=webhook.headers,
                    timeout=webhook.retry_config.get("timeout", DEFAULT_TIMEOUT),
                )

                # Calculate duration
                end_time = datetime.now(UTC)
                delivery.duration_ms = int((end_time - start_time).total_seconds() * 1000)

                # Success
                delivery.status = WebhookDeliveryStatus.SUCCESS
                delivery.response_status_code = status_code
                delivery.response_body = response_body
                delivery.completed_at = datetime.now(UTC).isoformat()
                delivery.save(self.delivery_dir)

                return delivery

            except WebhookPermanentError as e:
                # Permanent failure - don't retry
                delivery.status = WebhookDeliveryStatus.PERMANENT_FAILURE
                delivery.error_message = str(e)
                delivery.response_status_code = e.status_code
                delivery.completed_at = datetime.now(UTC).isoformat()
                delivery.save(self.delivery_dir)
                return delivery

            except (WebhookTimeoutError, WebhookConnectionError, WebhookDeliveryError) as e:
                # Temporary failure - may retry
                attempt += 1

                if attempt > max_retries:
                    # Exhausted retries
                    delivery.status = WebhookDeliveryStatus.PERMANENT_FAILURE
                    delivery.error_message = f"Failed after {max_retries} retries: {str(e)}"
                    delivery.completed_at = datetime.now(UTC).isoformat()
                    delivery.save(self.delivery_dir)
                    return delivery

                # Schedule retry
                delivery.status = WebhookDeliveryStatus.FAILED
                delivery.error_message = str(e)

                # Calculate next retry time
                retry_delay = delivery.get_next_retry_delay(webhook.retry_config)
                next_retry = datetime.now(UTC) + timedelta(seconds=retry_delay)
                delivery.next_retry_at = next_retry.isoformat()
                delivery.save(self.delivery_dir)

                # Wait before retry (for synchronous delivery)
                # For production, use a background task queue
                await asyncio.sleep(retry_delay)

        # Should not reach here, but handle gracefully
        delivery.status = WebhookDeliveryStatus.PERMANENT_FAILURE
        delivery.completed_at = datetime.now(UTC).isoformat()
        delivery.save(self.delivery_dir)
        return delivery

    async def deliver_batch(
        self,
        webhooks: list[WebhookConfig],
        event: str,
        payload: dict[str, Any],
    ) -> list[WebhookDelivery]:
        """
        Deliver to multiple webhooks in parallel.

        Args:
            webhooks: List of webhook configurations
            event: Event type being delivered
            payload: Payload to deliver

        Returns:
            List of WebhookDelivery records
        """
        # Filter enabled webhooks that subscribe to this event
        from integrations.webhooks.models import WebhookEvent

        event_obj = WebhookEvent.from_string(event) if isinstance(event, str) else event
        active_webhooks = [w for w in webhooks if w.should_send_event(event_obj)]

        if not active_webhooks:
            return []

        # Deliver to all webhooks in parallel
        tasks = [
            self.deliver(webhook, event, payload)
            for webhook in active_webhooks
        ]

        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_delivery_history(
        self,
        webhook_id: str | None = None,
        event: str | None = None,
        limit: int = 100,
    ) -> list[WebhookDelivery]:
        """
        Get delivery history.

        Args:
            webhook_id: Optional webhook ID to filter by
            event: Optional event type to filter by
            limit: Maximum number of records to return

        Returns:
            List of WebhookDelivery records
        """
        if webhook_id:
            deliveries = WebhookDelivery.load_by_webhook(self.delivery_dir, webhook_id)
        else:
            # Load all deliveries
            deliveries = []
            for delivery_file in self.delivery_dir.glob("*.json"):
                try:
                    with open(delivery_file, encoding="utf-8") as f:
                        data = json.load(f)
                    deliveries.append(WebhookDelivery.from_dict(data))
                except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                    continue

        # Filter by event
        if event:
            deliveries = [d for d in deliveries if d.event == event]

        # Sort by created_at descending (newest first)
        deliveries.sort(key=lambda d: d.created_at, reverse=True)

        # Apply limit
        return deliveries[:limit]

    def get_pending_retries(self) -> list[WebhookDelivery]:
        """
        Get deliveries that are ready to retry.

        Returns:
            List of WebhookDelivery records ready for retry
        """
        return WebhookDelivery.load_pending(self.delivery_dir)

    async def retry_pending(self) -> list[WebhookDelivery]:
        """
        Retry all pending deliveries.

        Returns:
            List of updated WebhookDelivery records
        """
        pending = self.get_pending_retries()

        if not pending:
            return []

        # Load webhooks
        # Note: Need access to webhook config, would need to pass config_dir
        # For now, return empty list (this is a TODO for integration)
        return []

    def get_delivery_stats(self, webhook_id: str | None = None) -> dict[str, Any]:
        """
        Get delivery statistics.

        Args:
            webhook_id: Optional webhook ID to filter by

        Returns:
            Dictionary with delivery statistics
        """
        deliveries = self.get_delivery_history(webhook_id, limit=10000)

        total = len(deliveries)
        success = sum(1 for d in deliveries if d.status == WebhookDeliveryStatus.SUCCESS)
        failed = sum(1 for d in deliveries if d.status == WebhookDeliveryStatus.PERMANENT_FAILURE)
        pending = sum(1 for d in deliveries if d.status == WebhookDeliveryStatus.FAILED)

        # Calculate average duration for successful deliveries
        successful_deliveries = [d for d in deliveries if d.duration_ms is not None]
        avg_duration = (
            sum(d.duration_ms for d in successful_deliveries) / len(successful_deliveries)
            if successful_deliveries
            else 0
        )

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "pending": pending,
            "success_rate": success / total if total > 0 else 0,
            "avg_duration_ms": avg_duration,
        }


# Convenience functions for common operations


async def deliver_webhook(
    webhook: WebhookConfig,
    event: str,
    payload: dict[str, Any],
    delivery_dir: Path,
) -> WebhookDelivery:
    """
    Deliver a single webhook.

    Convenience function that creates a delivery system and delivers.

    Args:
        webhook: Webhook configuration
        event: Event type
        payload: Payload to deliver
        delivery_dir: Directory for delivery records

    Returns:
        WebhookDelivery record
    """
    system = WebhookDeliverySystem(delivery_dir)
    return await system.deliver(webhook, event, payload)


async def deliver_to_all_webhooks(
    webhooks: list[WebhookConfig],
    event: str,
    payload: dict[str, Any],
    delivery_dir: Path,
) -> list[WebhookDelivery]:
    """
    Deliver to multiple webhooks in parallel.

    Convenience function for batch delivery.

    Args:
        webhooks: List of webhook configurations
        event: Event type
        payload: Payload to deliver
        delivery_dir: Directory for delivery records

    Returns:
        List of WebhookDelivery records
    """
    system = WebhookDeliverySystem(delivery_dir)
    return await system.deliver_batch(webhooks, event, payload)
