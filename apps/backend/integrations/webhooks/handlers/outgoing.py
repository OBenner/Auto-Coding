"""
Outgoing Webhook Sender
========================

Sends outgoing webhooks to external services with retry logic and exponential backoff.
Handles authentication, payload transformation, and delivery logging.

Design:
- OutgoingWebhookSender sends HTTP POST requests to configured webhook URLs
- Retry logic with exponential backoff for transient failures
- Support for multiple authentication methods (API key, bearer token, basic auth)
- Comprehensive logging of all delivery attempts
- Payload template support for custom integrations

Usage:
    >>> from integrations.webhooks.handlers.outgoing import OutgoingWebhookSender
    >>> sender = OutgoingWebhookSender(spec_dir=Path("/path/to/spec"))
    >>> result = await sender.send_webhook(webhook_config, webhook_event)
    >>> print(result.success)
"""

from __future__ import annotations

import ast
import asyncio
import json
import logging
import operator
import uuid
from pathlib import Path
from typing import Any

import httpx

from ..models import (
    WebhookConfig,
    WebhookDeliveryStatus,
    WebhookEvent,
    WebhookEventType,
    WebhookLog,
)
from ..storage import WebhookStorage

# =============================================================================
# Logging
# =============================================================================


logger = logging.getLogger(__name__)


# =============================================================================
# Delivery Result
# =============================================================================


class DeliveryResult:
    """
    Result of a webhook delivery attempt.

    Encapsulates the outcome of sending a webhook including success status,
    HTTP response, and any error information.
    """

    def __init__(
        self,
        success: bool,
        webhook_id: str,
        event_type: WebhookEventType,
        log_entry: WebhookLog,
    ):
        """
        Initialize delivery result.

        Args:
            success: Whether the delivery was successful
            webhook_id: ID of the webhook config
            event_type: Type of event that triggered the webhook
            log_entry: Webhook log entry with delivery details
        """
        self.success = success
        self.webhook_id = webhook_id
        self.event_type = event_type
        self.log_entry = log_entry

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "webhook_id": self.webhook_id,
            "event_type": self.event_type.value,
            "log_entry": self.log_entry.to_dict(),
        }


# =============================================================================
# Outgoing Webhook Sender
# =============================================================================


class OutgoingWebhookSender:
    """
    Sends outgoing webhooks to external services.

    Features:
    - HTTP POST requests with configurable timeouts
    - Multiple authentication methods (API key, bearer token, basic auth)
    - Retry logic with exponential backoff for transient failures
    - Payload template support for custom integrations
    - Comprehensive logging of all delivery attempts
    - Sanitization of sensitive data in logs

    The sender implements retry logic that:
    - Retries on configurable HTTP status codes (429, 500, 502, 503, 504)
    - Uses exponential backoff with configurable multiplier
    - Respects maximum retry limit
    - Logs each retry attempt separately
    """

    def __init__(
        self,
        spec_dir: Path,
        storage: WebhookStorage | None = None,
        timeout_seconds: int = 30,
    ):
        """
        Initialize the outgoing webhook sender.

        Args:
            spec_dir: Spec directory for webhook storage
            storage: Optional WebhookStorage instance (created if not provided)
            timeout_seconds: HTTP request timeout in seconds
        """
        self.spec_dir = spec_dir
        self.storage = storage or WebhookStorage(spec_dir=spec_dir)
        self.timeout_seconds = timeout_seconds

        # HTTP client with timeouts
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=True,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def send_webhook(
        self,
        webhook_config: WebhookConfig,
        event: WebhookEvent,
    ) -> DeliveryResult:
        """
        Send an outgoing webhook.

        This is the main entry point for sending webhooks. It:
        1. Validates the webhook configuration
        2. Builds the payload (with template support)
        3. Applies authentication
        4. Sends the HTTP request
        5. Implements retry logic if needed
        6. Logs all delivery attempts

        Args:
            webhook_config: Configuration for the webhook
            event: Webhook event to send

        Returns:
            DeliveryResult with delivery outcome and log entry

        Examples:
            >>> sender = OutgoingWebhookSender(spec_dir=Path("/path/to/spec"))
            >>> event = WebhookEvent.build_completed("001", "My Feature", True, 120.5)
            >>> result = await sender.send_webhook(webhook_config, event)
            >>> print(f"Webhook delivered: {result.success}")
        """
        # Validate webhook config
        if not webhook_config.enabled:
            logger.warning(f"Webhook {webhook_config.id} is disabled, skipping")
            return self._create_skipped_result(
                webhook_config, event, "Webhook is disabled"
            )

        if not webhook_config.url:
            logger.error(f"Webhook {webhook_config.id} has no URL configured")
            return self._create_skipped_result(
                webhook_config, event, "No URL configured"
            )

        if event.type not in webhook_config.events:
            logger.debug(
                f"Event {event.type.value} not in webhook {webhook_config.id} events, skipping"
            )
            return self._create_skipped_result(
                webhook_config, event, "Event type not configured for this webhook"
            )

        # Check custom event filter if configured
        if webhook_config.custom_event_filter:
            if not self._evaluate_event_filter(
                event, webhook_config.custom_event_filter
            ):
                logger.info(
                    f"Event filter did not match for webhook {webhook_config.id}"
                )
                return self._create_skipped_result(
                    webhook_config, event, "Event filter did not match"
                )

        # Build payload
        payload = self._build_payload(webhook_config, event)

        # Send with retry logic
        return await self._send_with_retry(webhook_config, event, payload)

    async def _send_with_retry(
        self,
        webhook_config: WebhookConfig,
        event: WebhookEvent,
        payload: dict[str, Any],
    ) -> DeliveryResult:
        """
        Send webhook with retry logic.

        Implements exponential backoff retry for transient failures.
        Retries on configured HTTP status codes and connection errors.

        Args:
            webhook_config: Webhook configuration
            event: Webhook event
            payload: Request payload

        Returns:
            DeliveryResult with final outcome
        """
        retry_config = webhook_config.retry_config
        last_log_entry = None
        # total_attempts = initial request (1) + max_retries
        total_attempts = retry_config.max_retries + 1

        for attempt in range(1, total_attempts + 1):
            # Create log entry for this attempt
            log_entry = WebhookLog(
                id=str(uuid.uuid4()),
                webhook_id=webhook_config.id,
                event_type=event.type,
                event_data=event.data,
                status=WebhookDeliveryStatus.PENDING,
                attempt_number=attempt,
                max_retries=retry_config.max_retries,
                request_url=webhook_config.url,
                request_method="POST",
                request_body=self._sanitize_payload(payload),
            )

            try:
                # Prepare request headers
                headers = self._build_headers(webhook_config, payload)

                # Update log entry with sanitized headers
                log_entry.request_headers = self._sanitize_headers(headers)

                # Send request
                logger.info(
                    f"Sending webhook {webhook_config.id} (attempt {attempt}/{total_attempts})"
                )

                response = await self.client.post(
                    webhook_config.url,
                    json=payload,
                    headers=headers,
                )

                # Update log entry with response
                log_entry.response_status_code = response.status_code
                log_entry.response_headers = dict(response.headers)

                # Check if request was successful
                if response.is_success:
                    # Success
                    log_entry.mark_completed(WebhookDeliveryStatus.SUCCESS)
                    self.storage.save_log(log_entry)

                    logger.info(
                        f"Webhook {webhook_config.id} delivered successfully "
                        f"(status {response.status_code})"
                    )

                    return DeliveryResult(
                        success=True,
                        webhook_id=webhook_config.id,
                        event_type=event.type,
                        log_entry=log_entry,
                    )

                # Check if we should retry
                if response.status_code in retry_config.retry_on_status_codes:
                    # Retryable status code
                    if attempt < total_attempts:
                        # Will retry
                        log_entry.mark_completed(
                            WebhookDeliveryStatus.RETRYING,
                            error_message=f"HTTP {response.status_code}: {response.text[:200]}",
                        )
                        self.storage.save_log(log_entry)
                        last_log_entry = log_entry

                        # Calculate delay with exponential backoff
                        delay = retry_config.retry_delay_seconds * (
                            retry_config.backoff_multiplier ** (attempt - 1)
                        )

                        logger.warning(
                            f"Webhook {webhook_config.id} failed with status {response.status_code}, "
                            f"retrying in {delay}s (attempt {attempt}/{retry_config.max_retries})"
                        )

                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Max retries exceeded
                        log_entry.mark_completed(
                            WebhookDeliveryStatus.FAILED,
                            error_message=f"Max retries exceeded. Last status: {response.status_code}",
                        )
                        self.storage.save_log(log_entry)

                        logger.error(
                            f"Webhook {webhook_config.id} failed after {attempt} attempts "
                            f"(status {response.status_code})"
                        )

                        return DeliveryResult(
                            success=False,
                            webhook_id=webhook_config.id,
                            event_type=event.type,
                            log_entry=log_entry,
                        )
                else:
                    # Non-retryable error (4xx client errors except 429)
                    response_body = response.text[:500] if response.text else None
                    log_entry.mark_completed(
                        WebhookDeliveryStatus.FAILED,
                        error_message=f"HTTP {response.status_code}: {response_body}",
                    )
                    self.storage.save_log(log_entry)

                    logger.error(
                        f"Webhook {webhook_config.id} failed with non-retryable status {response.status_code}"
                    )

                    return DeliveryResult(
                        success=False,
                        webhook_id=webhook_config.id,
                        event_type=event.type,
                        log_entry=log_entry,
                    )

            except httpx.TimeoutException as e:
                # Timeout - retryable
                log_entry.error_type = "timeout"
                log_entry.error_message = str(e)

                if attempt < total_attempts:
                    log_entry.status = WebhookDeliveryStatus.RETRYING
                    self.storage.save_log(log_entry)
                    last_log_entry = log_entry

                    delay = retry_config.retry_delay_seconds * (
                        retry_config.backoff_multiplier ** (attempt - 1)
                    )

                    logger.warning(
                        f"Webhook {webhook_config.id} timed out, retrying in {delay}s "
                        f"(attempt {attempt}/{total_attempts})"
                    )

                    await asyncio.sleep(delay)
                    continue
                else:
                    log_entry.mark_completed(
                        WebhookDeliveryStatus.FAILED,
                        error_message=f"Timeout after {attempt} attempts",
                    )
                    self.storage.save_log(log_entry)

                    logger.error(
                        f"Webhook {webhook_config.id} failed due to timeout after {attempt} attempts"
                    )

                    return DeliveryResult(
                        success=False,
                        webhook_id=webhook_config.id,
                        event_type=event.type,
                        log_entry=log_entry,
                    )

            except httpx.NetworkError as e:
                # Network error - retryable
                log_entry.error_type = "network_error"
                log_entry.error_message = str(e)

                if attempt < total_attempts:
                    log_entry.status = WebhookDeliveryStatus.RETRYING
                    self.storage.save_log(log_entry)
                    last_log_entry = log_entry

                    delay = retry_config.retry_delay_seconds * (
                        retry_config.backoff_multiplier ** (attempt - 1)
                    )

                    logger.warning(
                        f"Webhook {webhook_config.id} network error, retrying in {delay}s "
                        f"(attempt {attempt}/{total_attempts})"
                    )

                    await asyncio.sleep(delay)
                    continue
                else:
                    log_entry.mark_completed(
                        WebhookDeliveryStatus.FAILED,
                        error_message=f"Network error after {attempt} attempts: {str(e)}",
                    )
                    self.storage.save_log(log_entry)

                    logger.error(
                        f"Webhook {webhook_config.id} failed due to network error after {attempt} attempts"
                    )

                    return DeliveryResult(
                        success=False,
                        webhook_id=webhook_config.id,
                        event_type=event.type,
                        log_entry=log_entry,
                    )

            except Exception as e:
                # Unexpected error - not retryable
                log_entry.error_type = "unexpected_error"
                log_entry.mark_completed(
                    WebhookDeliveryStatus.FAILED,
                    error_message=f"Unexpected error: {str(e)}",
                )
                self.storage.save_log(log_entry)

                logger.error(
                    f"Webhook {webhook_config.id} failed with unexpected error: {e}",
                    exc_info=True,
                )

                return DeliveryResult(
                    success=False,
                    webhook_id=webhook_config.id,
                    event_type=event.type,
                    log_entry=log_entry,
                )

        # Should not reach here, but handle gracefully
        if last_log_entry:
            return DeliveryResult(
                success=False,
                webhook_id=webhook_config.id,
                event_type=event.type,
                log_entry=last_log_entry,
            )

        # Fallback: create failed log entry
        log_entry = WebhookLog(
            id=str(uuid.uuid4()),
            webhook_id=webhook_config.id,
            event_type=event.type,
            event_data=event.data,
            status=WebhookDeliveryStatus.FAILED,
            error_message="Unknown error - webhook not delivered",
        )
        self.storage.save_log(log_entry)

        return DeliveryResult(
            success=False,
            webhook_id=webhook_config.id,
            event_type=event.type,
            log_entry=log_entry,
        )

    def _build_payload(
        self,
        webhook_config: WebhookConfig,
        event: WebhookEvent,
    ) -> dict[str, Any]:
        """
        Build the webhook payload.

        Applies payload template if configured, otherwise uses standard event format.
        Supports integration-specific payload formats (Slack, Discord, Teams).

        Args:
            webhook_config: Webhook configuration
            event: Webhook event

        Returns:
            Payload dictionary to send in request body
        """
        # Base event data
        base_payload = {
            "event": event.type.value,
            "timestamp": event.timestamp,
            "data": event.data,
            "metadata": event.metadata,
        }

        # Apply custom template if configured
        if webhook_config.payload_template:
            return self._apply_payload_template(
                base_payload, webhook_config.payload_template
            )

        # Apply integration-specific format
        integration = webhook_config.integration.value

        if integration == "slack":
            return self._build_slack_payload(base_payload)
        elif integration == "discord":
            return self._build_discord_payload(base_payload)
        elif integration == "teams":
            return self._build_teams_payload(base_payload)
        else:
            # Generic format
            return base_payload

    def _build_slack_payload(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Build Slack-specific payload format.

        Args:
            event: Base event data

        Returns:
            Slack-formatted payload
        """
        event_type = event.get("event", "unknown")
        data = event.get("data", {})

        # Build message based on event type
        if event_type == "build_started":
            text = f":construction: Build started for spec `{data.get('spec_name', 'Unknown')}`"
        elif event_type == "build_completed":
            status = ":white_check_mark:" if data.get("success") else ":x:"
            text = f"{status} Build completed for spec `{data.get('spec_name', 'Unknown')}`"
        elif event_type == "build_failed":
            text = f":x: Build failed for spec `{data.get('spec_name', 'Unknown')}`"
        elif event_type == "subtask_started":
            text = f":arrow_forward: Subtask started: {data.get('subtask_description', 'Unknown')}"
        elif event_type == "subtask_completed":
            text = f":white_check_mark: Subtask completed: {data.get('subtask_id', 'Unknown')}"
        elif event_type == "subtask_failed":
            text = f":x: Subtask failed: {data.get('subtask_id', 'Unknown')}"
        else:
            text = f":bell: Webhook event: {event_type}"

        return {
            "text": text,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text,
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Event:*\n{event_type}"},
                        {
                            "type": "mrkdwn",
                            "text": f"*Timestamp:*\n{event.get('timestamp', 'Unknown')}",
                        },
                    ],
                },
            ],
        }

    def _build_discord_payload(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Build Discord-specific payload format.

        Args:
            event: Base event data

        Returns:
            Discord-formatted payload
        """
        event_type = event.get("event", "unknown")
        data = event.get("data", {})

        # Build description based on event type
        if event_type == "build_started":
            description = (
                f"Build started for spec **{data.get('spec_name', 'Unknown')}**"
            )
            color = 0x0099FF  # Blue
        elif event_type == "build_completed":
            if data.get("success"):
                description = f"Build completed successfully for spec **{data.get('spec_name', 'Unknown')}**"
                color = 0x00FF00  # Green
            else:
                description = f"Build completed with errors for spec **{data.get('spec_name', 'Unknown')}**"
                color = 0xFF9900  # Orange
        elif event_type == "build_failed":
            description = (
                f"Build failed for spec **{data.get('spec_name', 'Unknown')}**"
            )
            color = 0xFF0000  # Red
        elif event_type == "subtask_started":
            description = (
                f"Subtask started: {data.get('subtask_description', 'Unknown')}"
            )
            color = 0x0099FF  # Blue
        elif event_type == "subtask_completed":
            description = f"Subtask completed: {data.get('subtask_id', 'Unknown')}"
            color = 0x00FF00  # Green
        elif event_type == "subtask_failed":
            description = f"Subtask failed: {data.get('subtask_id', 'Unknown')}"
            color = 0xFF0000  # Red
        else:
            description = f"Webhook event: {event_type}"
            color = 0x99AAFF  # Light blue

        return {
            "embeds": [
                {
                    "title": f"Auto Claude Event: {event_type.replace('_', ' ').title()}",
                    "description": description,
                    "color": color,
                    "fields": [
                        {"name": "Event", "value": event_type, "inline": True},
                        {
                            "name": "Timestamp",
                            "value": event.get("timestamp", "Unknown"),
                            "inline": True,
                        },
                    ],
                }
            ]
        }

    def _build_teams_payload(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Build Microsoft Teams-specific payload format.

        .. deprecated::
            This uses the legacy MessageCard format. Microsoft recommends migrating
            to Adaptive Cards for new integrations. See TeamsIntegration.format_payload()
            for the Adaptive Card implementation.

        Args:
            event: Base event data

        Returns:
            Teams-formatted payload (legacy MessageCard format)
        """
        event_type = event.get("event", "unknown")
        data = event.get("data", {})

        # Build message based on event type
        if event_type == "build_started":
            text = f"Build started for spec **{data.get('spec_name', 'Unknown')}**"
        elif event_type == "build_completed":
            status = (
                "completed successfully"
                if data.get("success")
                else "completed with errors"
            )
            text = f"Build {status} for spec **{data.get('spec_name', 'Unknown')}**"
        elif event_type == "build_failed":
            text = f"Build failed for spec **{data.get('spec_name', 'Unknown')}**"
        elif event_type == "subtask_started":
            text = f"Subtask started: {data.get('subtask_description', 'Unknown')}"
        elif event_type == "subtask_completed":
            text = f"Subtask completed: {data.get('subtask_id', 'Unknown')}"
        elif event_type == "subtask_failed":
            text = f"Subtask failed: {data.get('subtask_id', 'Unknown')}"
        else:
            text = f"Webhook event: {event_type}"

        return {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": f"Auto Claude Event: {event_type}",
            "themeColor": "0078D7"
            if event_type in ["build_started", "subtask_started"]
            else "FF0000",
            "title": f"Auto Claude Event: {event_type.replace('_', ' ').title()}",
            "text": text,
        }

    def _apply_payload_template(
        self,
        event: dict[str, Any],
        template: dict[str, Any] | str,
    ) -> dict[str, Any]:
        """
        Apply custom payload template to event data.

        Supports Jinja2-style template strings and dict templates.

        Args:
            event: Base event data
            template: Custom template from webhook config

        Returns:
            Transformed payload
        """
        if isinstance(template, str):
            # Jinja2-style template string (using sandboxed environment for security)
            try:
                from jinja2.sandbox import SandboxedEnvironment

                env = SandboxedEnvironment()
                tmpl = env.from_string(template)
                rendered = tmpl.render(**event)
                return json.loads(rendered)
            except Exception as e:
                logger.warning(
                    f"Failed to apply Jinja2 template: {e}, using event as-is"
                )
                return event

        elif isinstance(template, dict):
            # Dict template with variable substitution
            result = {}
            for key, value in template.items():
                if (
                    isinstance(value, str)
                    and value.startswith("{{")
                    and value.endswith("}}")
                ):
                    # Simple variable substitution
                    var_name = value[2:-2].strip()
                    result[key] = event.get(var_name, value)
                else:
                    result[key] = value
            return result

        else:
            # Unknown template type, return event as-is
            return event

    def _build_headers(
        self,
        webhook_config: WebhookConfig,
        payload: dict[str, Any],
    ) -> dict[str, str]:
        """
        Build HTTP headers for webhook request.

        Applies authentication headers and content type.

        Args:
            webhook_config: Webhook configuration
            payload: Request payload

        Returns:
            HTTP headers dictionary
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Auto-Claude-Webhook/1.0",
        }

        auth = webhook_config.auth

        if auth.auth_type == "api_key":
            key_header = auth.api_key_header or "X-API-Key"
            headers[key_header] = auth.api_key or ""

        elif auth.auth_type == "bearer_token":
            headers["Authorization"] = f"Bearer {auth.api_key or ''}"

        elif auth.auth_type == "basic_auth":
            # Build basic auth header
            import base64

            credentials = f"{auth.username or ''}:{auth.password or ''}"
            encoded = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        # Add integration-specific headers
        if webhook_config.integration.value == "slack":
            headers["Content-Type"] = "application/json; charset=utf-8"

        return headers

    def _sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize payload for logging by removing sensitive data.

        Args:
            payload: Original payload

        Returns:
            Sanitized payload safe for logging
        """
        # Create a copy to avoid modifying original
        sanitized = payload.copy()

        # List of keys to sanitize
        sensitive_keys = [
            "password",
            "secret",
            "token",
            "api_key",
            "apikey",
            "authorization",
            "credentials",
        ]

        def sanitize_dict(d: dict[str, Any]) -> dict[str, Any]:
            """Recursively sanitize dictionary."""
            result = {}
            for key, value in d.items():
                key_lower = key.lower()
                if any(sensitive in key_lower for sensitive in sensitive_keys):
                    result[key] = "***REDACTED***"
                elif isinstance(value, dict):
                    result[key] = sanitize_dict(value)
                elif isinstance(value, list):
                    result[key] = [
                        sanitize_dict(item) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    result[key] = value
            return result

        return sanitize_dict(sanitized)

    def _sanitize_headers(self, headers: dict[str, str]) -> dict[str, str]:
        """
        Sanitize headers for logging by removing sensitive data.

        Args:
            headers: Original headers

        Returns:
            Sanitized headers safe for logging
        """
        sensitive_headers = {"authorization", "x-api-key", "x-auth-token", "cookie"}
        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in sensitive_headers or any(
                s in key_lower
                for s in ("token", "secret", "password", "api_key", "apikey")
            ):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        return sanitized

    def _evaluate_event_filter(
        self,
        event: WebhookEvent,
        filter_expr: str,
    ) -> bool:
        """
        Evaluate a custom event filter expression safely.

        Supports simple comparison expressions like:
        - "field == 'value'"
        - "field != 'value'"
        - "field == 'value1' and other_field == 'value2'"

        Uses AST parsing instead of eval() to prevent code injection.

        Args:
            event: Webhook event
            filter_expr: Filter expression to evaluate

        Returns:
            True if filter matches, False otherwise
        """
        try:
            event_dict = event.to_dict()
            # Flatten: merge top-level metadata (type, timestamp) with data fields
            # so filter expressions like "subtask_id == 'abc'" resolve correctly
            context: dict[str, Any] = {}
            context.update(event_dict.get("data", {}))
            context.update(event_dict.get("metadata", {}))
            context["type"] = event_dict.get("type")
            context["timestamp"] = event_dict.get("timestamp")
            tree = ast.parse(filter_expr, mode="eval")
            return bool(self._safe_eval_node(tree.body, context))
        except Exception as e:
            logger.warning(f"Failed to evaluate event filter '{filter_expr}': {e}")
            return False

    @staticmethod
    def _safe_eval_node(node: ast.AST, context: dict[str, Any]) -> Any:
        """Safely evaluate an AST node against context data."""
        _SAFE_OPS: dict[type, Any] = {
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
            ast.In: lambda a, b: a in b,
            ast.NotIn: lambda a, b: a not in b,
        }

        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return context.get(node.id)
        elif isinstance(node, ast.Compare):
            left = OutgoingWebhookSender._safe_eval_node(node.left, context)
            for op_node, comparator in zip(node.ops, node.comparators):
                op_func = _SAFE_OPS.get(type(op_node))
                if op_func is None:
                    raise ValueError(
                        f"Unsupported comparison: {type(op_node).__name__}"
                    )
                right = OutgoingWebhookSender._safe_eval_node(comparator, context)
                if not op_func(left, right):
                    return False
                left = right
            return True
        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(
                    OutgoingWebhookSender._safe_eval_node(v, context)
                    for v in node.values
                )
            elif isinstance(node.op, ast.Or):
                return any(
                    OutgoingWebhookSender._safe_eval_node(v, context)
                    for v in node.values
                )
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not OutgoingWebhookSender._safe_eval_node(node.operand, context)
        elif isinstance(node, ast.Attribute):
            value = OutgoingWebhookSender._safe_eval_node(node.value, context)
            if isinstance(value, dict):
                return value.get(node.attr)
            return getattr(value, node.attr, None)
        elif isinstance(node, ast.Call):
            # Only allow safe string methods
            if isinstance(node.func, ast.Attribute) and node.func.attr in (
                "startswith",
                "endswith",
                "lower",
                "upper",
                "strip",
            ):
                obj = OutgoingWebhookSender._safe_eval_node(node.func.value, context)
                args = [
                    OutgoingWebhookSender._safe_eval_node(a, context) for a in node.args
                ]
                if isinstance(obj, str):
                    return getattr(obj, node.func.attr)(*args)
            raise ValueError(f"Unsupported function call: {ast.dump(node.func)}")

        raise ValueError(f"Unsupported AST node: {type(node).__name__}")

    def _create_skipped_result(
        self,
        webhook_config: WebhookConfig,
        event: WebhookEvent,
        reason: str,
    ) -> DeliveryResult:
        """
        Create a delivery result for a skipped webhook.

        Args:
            webhook_config: Webhook configuration
            event: Webhook event
            reason: Reason for skipping

        Returns:
            DeliveryResult indicating webhook was skipped
        """
        log_entry = WebhookLog(
            id=str(uuid.uuid4()),
            webhook_id=webhook_config.id,
            event_type=event.type,
            event_data=event.data,
            status=WebhookDeliveryStatus.FAILED,
            error_message=f"Skipped: {reason}",
        )

        # Don't log skipped webhooks to storage
        # (they're not actual delivery attempts)

        return DeliveryResult(
            success=False,
            webhook_id=webhook_config.id,
            event_type=event.type,
            log_entry=log_entry,
        )


# =============================================================================
# Utility Functions
# =============================================================================


async def send_webhook_event(
    webhook_config: WebhookConfig,
    event: WebhookEvent,
    spec_dir: Path,
) -> DeliveryResult:
    """
    Convenience function to send a webhook event.

    Creates a sender, sends the webhook, and cleans up.

    Args:
        webhook_config: Webhook configuration
        event: Webhook event to send
        spec_dir: Spec directory

    Returns:
        DeliveryResult with delivery outcome

    Examples:
        >>> from integrations.webhooks.models import WebhookEvent, WebhookConfig
        >>> event = WebhookEvent.build_completed("001", "My Feature", True, 120.5)
        >>> result = await send_webhook_event(webhook_config, event, Path("/path/to/spec"))
        >>> print(f"Delivered: {result.success}")
    """
    sender = OutgoingWebhookSender(spec_dir=spec_dir)

    try:
        return await sender.send_webhook(webhook_config, event)
    finally:
        await sender.close()
