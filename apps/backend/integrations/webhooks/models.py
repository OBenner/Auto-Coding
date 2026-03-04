"""
Webhook Data Models and Schemas
================================

Data models for webhook configuration, events, and delivery tracking.

This module defines the core data structures for the webhook system:
- WebhookEvent: Enum of supported event types
- WebhookConfig: Configuration for webhook endpoints
- WebhookDelivery: Record of delivery attempts with retry tracking
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class WebhookEvent(str, Enum):
    """Webhook event types for agent lifecycle events."""

    # Spec lifecycle
    SPEC_CREATED = "spec_created"
    SPEC_UPDATED = "spec_updated"

    # Build lifecycle
    BUILD_STARTED = "build_started"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"

    # QA lifecycle
    QA_PASSED = "qa_passed"
    QA_FAILED = "qa_failed"

    # Git operations
    MERGED = "merged"
    PR_CREATED = "pr_created"

    @classmethod
    def all_events(cls) -> list[str]:
        """Get all event type strings."""
        return [e.value for e in cls]

    @classmethod
    def from_string(cls, value: str) -> WebhookEvent:
        """Convert string to WebhookEvent, case-insensitive."""
        normalized = value.lower().replace("-", "_")
        for event in cls:
            if event.value == normalized or event.name.lower() == normalized:
                return event
        raise ValueError(f"Invalid WebhookEvent: {value}")

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a string is a valid event type."""
        try:
            cls.from_string(value)
            return True
        except ValueError:
            return False


class WebhookDeliveryStatus(str, Enum):
    """Status of a webhook delivery attempt."""

    PENDING = "pending"  # Scheduled but not yet sent
    SENDING = "sending"  # Currently being sent
    SUCCESS = "success"  # Successfully delivered
    FAILED = "failed"  # Failed to deliver (will retry)
    PERMANENT_FAILURE = "permanent_failure"  # Failed after all retries
    TIMEOUT = "timeout"  # Request timed out


class WebhookTemplate(str, Enum):
    """Built-in webhook payload templates."""

    GENERIC = "generic"  # JSON with event data
    SLACK = "slack"  # Slack message format
    DISCORD = "discord"  # Discord webhook format
    TEAMS = "teams"  # Microsoft Teams adaptive card
    JIRA = "jira"  # JIRA comment format


@dataclass
class WebhookConfig:
    """
    Configuration for a webhook endpoint.

    Represents a single webhook subscription that will receive
    events based on the configured filters.

    Attributes:
        webhook_id: Unique identifier for this webhook
        name: Human-readable name
        url: Webhook URL to send events to
        secret: Optional secret for signature verification (HMAC-SHA256)
        events: List of event types to subscribe to
        template: Payload template to use
        enabled: Whether this webhook is active
        headers: Optional custom HTTP headers
        retry_config: Retry configuration
        created_at: When this webhook was created
        updated_at: When this webhook was last updated
    """

    webhook_id: str
    name: str
    url: str
    secret: str | None = None
    events: list[str] = field(default_factory=list)
    template: str = WebhookTemplate.GENERIC
    enabled: bool = True
    headers: dict[str, str] = field(default_factory=dict)
    retry_config: dict[str, Any] = field(
        default_factory=lambda: {
            "max_retries": 3,
            "initial_delay": 1.0,  # seconds
            "max_delay": 60.0,  # seconds
            "backoff_multiplier": 2.0,
        }
    )
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def should_send_event(self, event: WebhookEvent) -> bool:
        """
        Check if this webhook should be triggered for an event.

        Args:
            event: Event type to check

        Returns:
            True if webhook is enabled and subscribed to this event
        """
        if not self.enabled:
            return False
        return event.value in self.events or "*" in self.events

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "webhook_id": self.webhook_id,
            "name": self.name,
            "url": self.url,
            "secret": self.secret,  # Include for completeness (secure in storage)
            "events": self.events,
            "template": self.template,
            "enabled": self.enabled,
            "headers": self.headers,
            "retry_config": self.retry_config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebhookConfig:
        """Create from dictionary."""
        return cls(
            webhook_id=data["webhook_id"],
            name=data["name"],
            url=data["url"],
            secret=data.get("secret"),
            events=data.get("events", []),
            template=data.get("template", WebhookTemplate.GENERIC),
            enabled=data.get("enabled", True),
            headers=data.get("headers", {}),
            retry_config=data.get("retry_config", {}),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=data.get("updated_at", datetime.now(UTC).isoformat()),
        )

    def save(self, config_dir: Path) -> None:
        """
        Save webhook configuration to disk.

        Args:
            config_dir: Directory to save configuration in
        """
        config_file = config_dir / f"{self.webhook_id}.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, config_dir: Path, webhook_id: str) -> WebhookConfig | None:
        """
        Load webhook configuration from disk.

        Args:
            config_dir: Directory containing webhook configurations
            webhook_id: Webhook ID to load

        Returns:
            WebhookConfig or None if not found
        """
        config_file = config_dir / f"{webhook_id}.json"
        if not config_file.exists():
            return None

        try:
            with open(config_file, encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    @classmethod
    def load_all(cls, config_dir: Path) -> list[WebhookConfig]:
        """
        Load all webhook configurations from a directory.

        Args:
            config_dir: Directory containing webhook configurations

        Returns:
            List of WebhookConfig objects
        """
        configs = []
        config_dir.mkdir(parents=True, exist_ok=True)

        for config_file in config_dir.glob("*.json"):
            try:
                with open(config_file, encoding="utf-8") as f:
                    data = json.load(f)
                configs.append(cls.from_dict(data))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                continue

        return configs


@dataclass
class WebhookDelivery:
    """
    Record of a webhook delivery attempt.

    Tracks delivery attempts for retry logic and debugging.

    Attributes:
        delivery_id: Unique identifier for this delivery attempt
        webhook_id: ID of the webhook being delivered
        event: Event type being delivered
        status: Current delivery status
        attempt_number: Which retry attempt this is (1-indexed)
        response_status_code: HTTP status code from server (if received)
        response_body: Response body from server (if received)
        error_message: Error message if delivery failed
        duration_ms: How long the request took in milliseconds
        next_retry_at: When to retry (if status is FAILED)
        created_at: When this delivery was attempted
        completed_at: When this delivery completed (success or failure)
    """

    delivery_id: str
    webhook_id: str
    event: str
    status: WebhookDeliveryStatus = WebhookDeliveryStatus.PENDING
    attempt_number: int = 1
    response_status_code: int | None = None
    response_body: str | None = None
    error_message: str | None = None
    duration_ms: int | None = None
    next_retry_at: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def is_final(self) -> bool:
        """
        Check if this delivery is in a terminal state.

        Returns:
            True if no further retries will be attempted
        """
        return self.status in {
            WebhookDeliveryStatus.SUCCESS,
            WebhookDeliveryStatus.PERMANENT_FAILURE,
        }

    def should_retry(self) -> bool:
        """
        Check if this delivery should be retried.

        Returns:
            True if status indicates a retry is needed
        """
        return self.status == WebhookDeliveryStatus.FAILED

    def get_next_retry_delay(self, retry_config: dict[str, Any]) -> float:
        """
        Calculate delay before next retry using exponential backoff.

        Args:
            retry_config: Retry configuration from WebhookConfig

        Returns:
            Delay in seconds before next retry
        """
        multiplier = retry_config.get("backoff_multiplier", 2.0)
        initial_delay = retry_config.get("initial_delay", 1.0)
        max_delay = retry_config.get("max_delay", 60.0)

        # Exponential backoff: delay = initial * multiplier^(attempt-1)
        delay = initial_delay * (multiplier ** (self.attempt_number - 1))
        return min(delay, max_delay)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "delivery_id": self.delivery_id,
            "webhook_id": self.webhook_id,
            "event": self.event,
            "status": self.status.value,
            "attempt_number": self.attempt_number,
            "response_status_code": self.response_status_code,
            "response_body": self.response_body,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "next_retry_at": self.next_retry_at,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebhookDelivery:
        """Create from dictionary."""
        return cls(
            delivery_id=data["delivery_id"],
            webhook_id=data["webhook_id"],
            event=data["event"],
            status=WebhookDeliveryStatus(data.get("status", "pending")),
            attempt_number=data.get("attempt_number", 1),
            response_status_code=data.get("response_status_code"),
            response_body=data.get("response_body"),
            error_message=data.get("error_message"),
            duration_ms=data.get("duration_ms"),
            next_retry_at=data.get("next_retry_at"),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            completed_at=data.get("completed_at"),
            payload=data.get("payload", {}),
        )

    def save(self, delivery_dir: Path) -> None:
        """
        Save delivery record to disk.

        Args:
            delivery_dir: Directory to save delivery records in
        """
        delivery_dir.mkdir(parents=True, exist_ok=True)
        delivery_file = delivery_dir / f"{self.delivery_id}.json"
        with open(delivery_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, delivery_dir: Path, delivery_id: str) -> WebhookDelivery | None:
        """
        Load delivery record from disk.

        Args:
            delivery_dir: Directory containing delivery records
            delivery_id: Delivery ID to load

        Returns:
            WebhookDelivery or None if not found
        """
        delivery_file = delivery_dir / f"{delivery_id}.json"
        if not delivery_file.exists():
            return None

        try:
            with open(delivery_file, encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    @classmethod
    def load_by_webhook(
        cls, delivery_dir: Path, webhook_id: str
    ) -> list[WebhookDelivery]:
        """
        Load all delivery records for a specific webhook.

        Args:
            delivery_dir: Directory containing delivery records
            webhook_id: Webhook ID to filter by

        Returns:
            List of WebhookDelivery objects for this webhook
        """
        deliveries = []
        delivery_dir.mkdir(parents=True, exist_ok=True)

        for delivery_file in delivery_dir.glob("*.json"):
            try:
                with open(delivery_file, encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("webhook_id") == webhook_id:
                    deliveries.append(cls.from_dict(data))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                continue

        # Sort by created_at descending (newest first)
        deliveries.sort(key=lambda d: d.created_at, reverse=True)
        return deliveries

    @classmethod
    def load_pending(cls, delivery_dir: Path) -> list[WebhookDelivery]:
        """
        Load all delivery records that need retry.

        Args:
            delivery_dir: Directory containing delivery records

        Returns:
            List of WebhookDelivery objects with FAILED status
        """
        deliveries = []
        delivery_dir.mkdir(parents=True, exist_ok=True)

        for delivery_file in delivery_dir.glob("*.json"):
            try:
                with open(delivery_file, encoding="utf-8") as f:
                    data = json.load(f)
                delivery = cls.from_dict(data)
                if delivery.should_retry():
                    # Check if it's time to retry
                    if delivery.next_retry_at:
                        retry_time = datetime.fromisoformat(delivery.next_retry_at)
                        if datetime.now(UTC) >= retry_time:
                            deliveries.append(delivery)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                continue

        return deliveries


# Utility functions


def generate_webhook_id() -> str:
    """
    Generate a unique webhook ID.

    Returns:
        Unique webhook ID string
    """
    import uuid

    return f"wh_{uuid.uuid4().hex[:16]}"


def generate_delivery_id() -> str:
    """
    Generate a unique delivery ID.

    Returns:
        Unique delivery ID string
    """
    import uuid

    return f"del_{uuid.uuid4().hex[:16]}"
