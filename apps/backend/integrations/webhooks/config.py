"""
Webhook Integration Configuration
==================================

Constants, event types, and configuration helpers for webhook integration.
Provides webhook management for agent lifecycle events.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# Webhook Event Types
EVENT_SPEC_CREATED = "spec.created"
EVENT_BUILD_STARTED = "build.started"
EVENT_BUILD_COMPLETED = "build.completed"
EVENT_QA_PASSED = "qa.passed"
EVENT_QA_FAILED = "qa.failed"
EVENT_BUILD_MERGED = "build.merged"
EVENT_SUBTASK_STARTED = "subtask.started"
EVENT_SUBTASK_COMPLETED = "subtask.completed"
EVENT_SUBTASK_STUCK = "subtask.stuck"

# All event types for validation
ALL_EVENTS = [
    EVENT_SPEC_CREATED,
    EVENT_BUILD_STARTED,
    EVENT_BUILD_COMPLETED,
    EVENT_QA_PASSED,
    EVENT_QA_FAILED,
    EVENT_BUILD_MERGED,
    EVENT_SUBTASK_STARTED,
    EVENT_SUBTASK_COMPLETED,
    EVENT_SUBTASK_STUCK,
]

# Webhook Delivery Status
STATUS_PENDING = "pending"
STATUS_DELIVERED = "delivered"
STATUS_FAILED = "failed"
STATUS_RETRYING = "retrying"

# Webhook signature header
SIGNATURE_HEADER = "X-Auto-Clause-Signature"
SIGNATURE_VERSION = "v1"

# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
RETRY_BACKOFF_MULTIPLIER = 2.0

# Webhook timeouts (seconds)
DEFAULT_TIMEOUT = 10
MAX_TIMEOUT = 30

# Supported webhook service templates
SERVICE_SLACK = "slack"
SERVICE_DISCORD = "discord"
SERVICE_TEAMS = "teams"
SERVICE_GENERIC = "generic"
SERVICE_EMAIL = "email"

SERVICE_TEMPLATES = {
    SERVICE_SLACK: "Slack",
    SERVICE_DISCORD: "Discord",
    SERVICE_TEAMS: "Microsoft Teams",
    SERVICE_GENERIC: "Generic Webhook",
    SERVICE_EMAIL: "Email",
}

# Webhook configuration file
WEBHOOK_CONFIG_FILE = ".webhooks.json"

# Webhook delivery log file
WEBHOOK_DELIVERY_LOG = ".webhook_deliveries.json"


@dataclass
class WebhookConfig:
    """Configuration for a webhook endpoint."""

    url: str
    events: list[str]  # List of event types to subscribe to
    service_type: str = SERVICE_GENERIC
    enabled: bool = True
    secret: str | None = None  # For signature verification
    headers: dict | None = None  # Custom headers
    template: str | None = None  # Custom payload template

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

    def is_valid(self) -> bool:
        """Check if webhook config is valid."""
        if not self.url:
            return False

        # Validate URL format
        try:
            result = urlparse(self.url)
            if not all([result.scheme, result.netloc]):
                return False
            if result.scheme not in ["http", "https"]:
                return False
        except Exception:
            return False

        # Validate events
        if not self.events:
            return False

        for event in self.events:
            if event not in ALL_EVENTS:
                return False

        return True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "url": self.url,
            "events": self.events,
            "service_type": self.service_type,
            "enabled": self.enabled,
            "secret": self.secret if self.secret else None,
            "headers": self.headers,
            "template": self.template,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WebhookConfig":
        """Create from dictionary."""
        return cls(
            url=data.get("url", ""),
            events=data.get("events", []),
            service_type=data.get("service_type", SERVICE_GENERIC),
            enabled=data.get("enabled", True),
            secret=data.get("secret"),
            headers=data.get("headers"),
            template=data.get("template"),
        )


@dataclass
class WebhookState:
    """State of webhook configuration for an auto-claude spec."""

    webhooks: list[WebhookConfig] | None = None
    version: str = "1.0"
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self):
        if self.webhooks is None:
            self.webhooks = []

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "webhooks": [w.to_dict() for w in self.webhooks],
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WebhookState":
        """Create from dictionary."""
        webhooks = []
        for webhook_data in data.get("webhooks", []):
            webhooks.append(WebhookConfig.from_dict(webhook_data))

        return cls(
            webhooks=webhooks,
            version=data.get("version", "1.0"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def save(self, spec_dir: Path) -> None:
        """Save state to the spec directory."""
        config_file = spec_dir / WEBHOOK_CONFIG_FILE
        self.updated_at = datetime.now().isoformat()

        if not self.created_at:
            self.created_at = datetime.now().isoformat()

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, spec_dir: Path) -> Optional["WebhookState"]:
        """Load state from the spec directory."""
        config_file = spec_dir / WEBHOOK_CONFIG_FILE
        if not config_file.exists():
            return None

        try:
            with open(config_file, encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def add_webhook(self, webhook: WebhookConfig) -> None:
        """Add a webhook configuration."""
        if not webhook.is_valid():
            raise ValueError("Invalid webhook configuration")

        self.webhooks.append(webhook)
        self.updated_at = datetime.now().isoformat()

    def remove_webhook(self, url: str) -> bool:
        """Remove a webhook by URL."""
        for i, webhook in enumerate(self.webhooks):
            if webhook.url == url:
                self.webhooks.pop(i)
                self.updated_at = datetime.now().isoformat()
                return True
        return False

    def get_webhooks_for_event(self, event_type: str) -> list[WebhookConfig]:
        """Get all webhooks subscribed to an event."""
        return [w for w in self.webhooks if w.enabled and event_type in w.events]

    def has_webhooks(self) -> bool:
        """Check if any webhooks are configured."""
        return any(w.enabled for w in self.webhooks)


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt."""

    webhook_url: str
    event_type: str
    status: str
    status_code: int | None = None
    attempt: int = 1
    timestamp: str | None = None
    error: str | None = None
    response_body: str | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "webhook_url": self.webhook_url,
            "event_type": self.event_type,
            "status": self.status,
            "status_code": self.status_code,
            "attempt": self.attempt,
            "timestamp": self.timestamp,
            "error": self.error,
            "response_body": self.response_body,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WebhookDelivery":
        """Create from dictionary."""
        return cls(
            webhook_url=data.get("webhook_url", ""),
            event_type=data.get("event_type", ""),
            status=data.get("status", STATUS_PENDING),
            status_code=data.get("status_code"),
            attempt=data.get("attempt", 1),
            timestamp=data.get("timestamp"),
            error=data.get("error"),
            response_body=data.get("response_body"),
        )


@dataclass
class WebhookDeliveryLog:
    """Log of webhook deliveries for a spec."""

    deliveries: list[WebhookDelivery] | None = None

    def __post_init__(self):
        if self.deliveries is None:
            self.deliveries = []

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "deliveries": [d.to_dict() for d in self.deliveries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WebhookDeliveryLog":
        """Create from dictionary."""
        deliveries = []
        for delivery_data in data.get("deliveries", []):
            deliveries.append(WebhookDelivery.from_dict(delivery_data))

        return cls(deliveries=deliveries)

    def save(self, spec_dir: Path) -> None:
        """Save log to the spec directory."""
        log_file = spec_dir / WEBHOOK_DELIVERY_LOG

        # Keep only last 1000 deliveries to prevent file bloat
        if len(self.deliveries) > 1000:
            self.deliveries = self.deliveries[-1000:]

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, spec_dir: Path) -> Optional["WebhookDeliveryLog"]:
        """Load log from the spec directory."""
        log_file = spec_dir / WEBHOOK_DELIVERY_LOG
        if not log_file.exists():
            return None

        try:
            with open(log_file, encoding="utf-8") as f:
                return cls.from_dict(json.load(f))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def add_delivery(self, delivery: WebhookDelivery) -> None:
        """Add a delivery record."""
        self.deliveries.append(delivery)

    def get_deliveries_for_webhook(
        self, webhook_url: str, limit: int = 10
    ) -> list[WebhookDelivery]:
        """Get recent deliveries for a webhook."""
        webhook_deliveries = [
            d for d in self.deliveries if d.webhook_url == webhook_url
        ]
        return webhook_deliveries[-limit:]

    def get_failed_deliveries(self, since: str | None = None) -> list[WebhookDelivery]:
        """Get failed deliveries since a timestamp."""
        failed = [d for d in self.deliveries if d.status == STATUS_FAILED]

        if since:
            failed = [d for d in failed if d.timestamp and d.timestamp >= since]

        return failed


def get_default_payload_template(service_type: str) -> str:
    """
    Get default payload template for a service type.

    Args:
        service_type: Service type (slack, discord, teams, generic)

    Returns:
        Default template string or None
    """
    templates = {
        SERVICE_SLACK: {
            "text": "Auto-Claude Event: {event_type}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "{event_title}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": "*Spec:* {spec_id}"},
                        {"type": "mrkdwn", "text": "*Status:* {status}"},
                    ],
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "{description}"},
                },
            ],
        },
        SERVICE_DISCORD: {
            "content": "**{event_title}**",
            "embeds": [
                {
                    "title": "{spec_title}",
                    "description": "{description}",
                    "fields": [
                        {"name": "Spec ID", "value": "{spec_id}", "inline": True},
                        {"name": "Status", "value": "{status}", "inline": True},
                    ],
                    "timestamp": "{timestamp}",
                }
            ],
        },
    }

    return templates.get(service_type)


def format_event_description(event_type: str, context: dict) -> str:
    """
    Format a human-readable event description.

    Args:
        event_type: Event type constant
        context: Event context data

    Returns:
        Formatted description string
    """
    spec_id = context.get("spec_id", "Unknown")

    descriptions = {
        EVENT_SPEC_CREATED: f"New spec created: {spec_id}",
        EVENT_BUILD_STARTED: f"Build started for spec: {spec_id}",
        EVENT_BUILD_COMPLETED: f"Build completed for spec: {spec_id}",
        EVENT_QA_PASSED: f"QA validation passed for spec: {spec_id}",
        EVENT_QA_FAILED: f"QA validation failed for spec: {spec_id}",
        EVENT_BUILD_MERGED: f"Build merged for spec: {spec_id}",
        EVENT_SUBTASK_STARTED: f"Subtask started: {context.get('subtask_id', 'Unknown')}",
        EVENT_SUBTASK_COMPLETED: f"Subtask completed: {context.get('subtask_id', 'Unknown')}",
        EVENT_SUBTASK_STUCK: f"Subtask stuck: {context.get('subtask_id', 'Unknown')}",
    }

    return descriptions.get(event_type, f"Event: {event_type}")


def get_event_title(event_type: str) -> str:
    """
    Get a short title for an event type.

    Args:
        event_type: Event type constant

    Returns:
        Short title string
    """
    titles = {
        EVENT_SPEC_CREATED: "Spec Created",
        EVENT_BUILD_STARTED: "Build Started",
        EVENT_BUILD_COMPLETED: "Build Completed",
        EVENT_QA_PASSED: "QA Passed",
        EVENT_QA_FAILED: "QA Failed",
        EVENT_BUILD_MERGED: "Build Merged",
        EVENT_SUBTASK_STARTED: "Subtask Started",
        EVENT_SUBTASK_COMPLETED: "Subtask Completed",
        EVENT_SUBTASK_STUCK: "Subtask Stuck",
    }

    return titles.get(event_type, "Webhook Event")
