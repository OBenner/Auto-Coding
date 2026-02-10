"""
Webhook Data Models
====================

Pydantic models for webhook configuration, logging, and event handling.
Provides type-safe, validated data structures for the webhook integration system.

Key Models:
- WebhookConfig: Configuration for webhook endpoints (incoming and outgoing)
- WebhookLog: Audit log of webhook deliveries
- WebhookEvent: Event types that trigger webhooks
- WebhookDelivery: Status of webhook delivery attempts
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Constants and Enums
# =============================================================================


class WebhookType(str, Enum):
    """Type of webhook integration."""

    INCOMING = "incoming"  # Receive webhooks from external services
    OUTGOING = "outgoing"  # Send webhooks to external services


class WebhookIntegration(str, Enum):
    """Pre-built webhook integrations."""

    SLACK = "slack"
    DISCORD = "discord"
    TEAMS = "teams"
    JIRA = "jira"
    GITHUB = "github"
    GITLAB = "gitlab"
    GENERIC = "generic"


class WebhookEventType(str, Enum):
    """Events that can trigger outgoing webhooks."""

    BUILD_STARTED = "build_started"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"
    SUBTASK_STARTED = "subtask_started"
    SUBTASK_COMPLETED = "subtask_completed"
    SUBTASK_FAILED = "subtask_failed"
    PR_OPENED = "pr_opened"
    PR_MERGED = "pr_merged"
    PR_CLOSED = "pr_closed"
    CUSTOM = "custom"


class WebhookDeliveryStatus(str, Enum):
    """Status of webhook delivery attempts."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


# =============================================================================
# Configuration Models
# =============================================================================


class RetryConfig(BaseModel):
    """Retry configuration for webhook deliveries."""

    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum number of retry attempts"
    )
    retry_delay_seconds: int = Field(
        default=5, ge=1, le=300, description="Initial delay before first retry"
    )
    backoff_multiplier: float = Field(
        default=2.0, ge=1.0, le=5.0, description="Exponential backoff multiplier"
    )
    retry_on_status_codes: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="HTTP status codes that trigger retry",
    )


class AuthenticationConfig(BaseModel):
    """Authentication configuration for webhook endpoints."""

    auth_type: Literal[
        "none", "api_key", "bearer_token", "basic_auth", "signature"
    ] = Field(default="none", description="Type of authentication")

    # API key / Bearer token
    api_key: str | None = Field(default=None, description="API key or bearer token")
    api_key_header: str | None = Field(
        default="Authorization", description="Header name for API key"
    )

    # Basic auth
    username: str | None = Field(default=None, description="Basic auth username")
    password: str | None = Field(default=None, description="Basic auth password")

    # Signature verification (for incoming webhooks)
    secret: str | None = Field(
        default=None, description="Shared secret for signature verification"
    )
    signature_algorithm: Literal["hmac_sha256", "hmac_sha512"] = Field(
        default="hmac_sha256", description="Signature hash algorithm"
    )
    signature_header: str | None = Field(
        default="X-Hub-Signature-256",
        description="Header containing the signature",
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str | None, info) -> str | None:
        """Validate API key is present when auth_type requires it."""
        if info.data.get("auth_type") in ["api_key", "bearer_token"] and not v:
            raise ValueError("API key is required for api_key and bearer_token auth")
        return v

    @model_validator(mode="after")
    def validate_basic_auth(self) -> "AuthenticationConfig":
        """Validate both username and password are present for basic auth."""
        if self.auth_type == "basic_auth":
            if not self.username or not self.password:
                raise ValueError("Both username and password required for basic auth")
        return self


class WebhookConfig(BaseModel):
    """
    Configuration for a webhook integration.

    Supports both incoming (receiving webhooks) and outgoing (sending notifications)
    webhooks with various authentication methods.
    """

    id: str = Field(description="Unique identifier for this webhook config")
    name: str = Field(description="Human-readable name for this webhook")

    # Type and integration
    type: WebhookType = Field(description="Webhook direction (incoming/outgoing)")
    integration: WebhookIntegration = Field(description="Integration type")

    # Endpoint configuration
    url: str | None = Field(
        default=None, description="Webhook URL (for outgoing webhooks)"
    )
    path: str | None = Field(
        default=None, description="Webhook endpoint path (for incoming webhooks)"
    )

    # Authentication
    auth: AuthenticationConfig = Field(
        default_factory=AuthenticationConfig,
        description="Authentication configuration",
    )

    # Event configuration
    events: list[WebhookEventType] = Field(
        default_factory=list,
        description="Events that trigger this webhook (for outgoing webhooks)",
    )
    custom_event_filter: str | None = Field(
        default=None,
        description="Custom event filter expression (e.g., 'subtask_id.startswith(\"2-1\")')",
    )

    # Payload template
    payload_template: dict[str, Any] | str | None = Field(
        default=None,
        description="Custom payload template (JSON dict or Jinja2 template string)",
    )

    # Status
    enabled: bool = Field(default=True, description="Whether this webhook is active")

    # Retry configuration
    retry_config: RetryConfig = Field(
        default_factory=RetryConfig,
        description="Retry configuration for failed deliveries",
    )

    # Metadata
    description: str | None = Field(default=None, description="Optional description")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Last update timestamp",
    )

    @field_validator("url")
    @classmethod
    def validate_outgoing_url(cls, v: str | None, info) -> str | None:
        """Validate URL is present for outgoing webhooks."""
        if info.data.get("type") == WebhookType.OUTGOING and not v:
            raise ValueError("URL is required for outgoing webhooks")
        return v

    @field_validator("path")
    @classmethod
    def validate_incoming_path(cls, v: str | None, info) -> str | None:
        """Validate path is present for incoming webhooks."""
        if info.data.get("type") == WebhookType.INCOMING and not v:
            raise ValueError("Path is required for incoming webhooks")
        if v and not v.startswith("/"):
            raise ValueError("Path must start with /")
        return v

    @model_validator(mode="after")
    def validate_events_for_outgoing(self) -> "WebhookConfig":
        """Validate events are specified for outgoing webhooks."""
        if self.type == WebhookType.OUTGOING and not self.events:
            raise ValueError("At least one event must be specified for outgoing webhooks")
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "integration": self.integration.value,
            "url": self.url,
            "path": self.path,
            "auth": self.auth.model_dump(),
            "events": [e.value for e in self.events],
            "custom_event_filter": self.custom_event_filter,
            "payload_template": self.payload_template,
            "enabled": self.enabled,
            "retry_config": self.retry_config.model_dump(),
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WebhookConfig":
        """Create WebhookConfig from dictionary."""
        # Convert enum values back to enums
        if "type" in data and isinstance(data["type"], str):
            data["type"] = WebhookType(data["type"])
        if "integration" in data and isinstance(data["integration"], str):
            data["integration"] = WebhookIntegration(data["integration"])
        if "events" in data and isinstance(data["events"], list):
            data["events"] = [WebhookEventType(e) for e in data["events"]]

        # Handle nested auth config
        if "auth" in data and isinstance(data["auth"], dict):
            data["auth"] = AuthenticationConfig(**data["auth"])

        # Handle nested retry config
        if "retry_config" in data and isinstance(data["retry_config"], dict):
            data["retry_config"] = RetryConfig(**data["retry_config"])

        return cls(**data)


# =============================================================================
# Logging Models
# =============================================================================


class WebhookLog(BaseModel):
    """
    Audit log entry for webhook delivery attempts.

    Tracks all webhook deliveries including requests, responses, and errors
    for debugging and audit purposes.
    """

    id: str = Field(description="Unique log entry ID")
    webhook_id: str = Field(description="ID of the webhook config that was used")

    # Event info
    event_type: WebhookEventType = Field(description="Type of event that triggered webhook")
    event_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload data",
    )

    # Delivery info
    status: WebhookDeliveryStatus = Field(
        default=WebhookDeliveryStatus.PENDING,
        description="Delivery status",
    )

    # Request
    request_url: str | None = Field(default=None, description="URL webhook was sent to")
    request_method: str = Field(default="POST", description="HTTP method used")
    request_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Request headers (sanitized)",
    )
    request_body: dict[str, Any] | None = Field(
        default=None,
        description="Request payload (sanitized)",
    )

    # Response
    response_status_code: int | None = Field(
        default=None,
        description="HTTP status code received",
    )
    response_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Response headers",
    )
    response_body: str | None = Field(
        default=None,
        description="Response body (truncated if large)",
    )

    # Error info
    error_message: str | None = Field(default=None, description="Error message if failed")
    error_type: str | None = Field(
        default=None,
        description="Type of error (connection, timeout, validation, etc.)",
    )

    # Retry info
    attempt_number: int = Field(default=1, description="Which retry attempt this is")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    # Timestamps
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="When the webhook delivery was attempted",
    )
    completed_at: str | None = Field(
        default=None,
        description="When the webhook delivery completed",
    )
    duration_ms: int | None = Field(
        default=None,
        description="Time taken for delivery in milliseconds",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "webhook_id": self.webhook_id,
            "event_type": self.event_type.value,
            "event_data": self.event_data,
            "status": self.status.value,
            "request_url": self.request_url,
            "request_method": self.request_method,
            "request_headers": self.request_headers,
            "request_body": self.request_body,
            "response_status_code": self.response_status_code,
            "response_headers": self.response_headers,
            "response_body": self.response_body,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "attempt_number": self.attempt_number,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WebhookLog":
        """Create WebhookLog from dictionary."""
        if "event_type" in data and isinstance(data["event_type"], str):
            data["event_type"] = WebhookEventType(data["event_type"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = WebhookDeliveryStatus(data["status"])
        return cls(**data)

    def mark_completed(
        self,
        status: WebhookDeliveryStatus,
        status_code: int | None = None,
        response_body: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Mark the webhook delivery as completed."""
        self.status = status
        self.completed_at = datetime.now().isoformat()

        if status_code:
            self.response_status_code = status_code
        if response_body:
            self.response_body = response_body
        if error_message:
            self.error_message = error_message

        # Calculate duration
        if self.created_at:
            try:
                start = datetime.fromisoformat(self.created_at)
                end = datetime.fromisoformat(self.completed_at)
                self.duration_ms = int((end - start).total_seconds() * 1000)
            except (ValueError, TypeError):
                pass


# =============================================================================
# Event Models
# =============================================================================


@dataclass
class WebhookEvent:
    """
    Event that can trigger outgoing webhooks.

    Encapsulates event data for build lifecycle events that can
    trigger notifications to external services.
    """

    type: WebhookEventType
    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WebhookEvent":
        """Create WebhookEvent from dictionary."""
        event_type = data.get("type", "custom")
        if isinstance(event_type, str):
            event_type = WebhookEventType(event_type)

        return cls(
            type=event_type,
            data=data.get("data", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def build_started(
        cls,
        spec_id: str,
        spec_name: str,
        total_subtasks: int,
        metadata: dict[str, Any] | None = None,
    ) -> "WebhookEvent":
        """Create a build started event."""
        return cls(
            type=WebhookEventType.BUILD_STARTED,
            data={
                "spec_id": spec_id,
                "spec_name": spec_name,
                "total_subtasks": total_subtasks,
            },
            metadata=metadata or {},
        )

    @classmethod
    def build_completed(
        cls,
        spec_id: str,
        spec_name: str,
        success: bool,
        duration_seconds: float,
        metadata: dict[str, Any] | None = None,
    ) -> "WebhookEvent":
        """Create a build completed event."""
        return cls(
            type=WebhookEventType.BUILD_COMPLETED,
            data={
                "spec_id": spec_id,
                "spec_name": spec_name,
                "success": success,
                "duration_seconds": duration_seconds,
            },
            metadata=metadata or {},
        )

    @classmethod
    def build_failed(
        cls,
        spec_id: str,
        spec_name: str,
        error_message: str,
        failed_subtask: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "WebhookEvent":
        """Create a build failed event."""
        return cls(
            type=WebhookEventType.BUILD_FAILED,
            data={
                "spec_id": spec_id,
                "spec_name": spec_name,
                "error_message": error_message,
                "failed_subtask": failed_subtask,
            },
            metadata=metadata or {},
        )

    @classmethod
    def subtask_started(
        cls,
        spec_id: str,
        subtask_id: str,
        subtask_description: str,
        metadata: dict[str, Any] | None = None,
    ) -> "WebhookEvent":
        """Create a subtask started event."""
        return cls(
            type=WebhookEventType.SUBTASK_STARTED,
            data={
                "spec_id": spec_id,
                "subtask_id": subtask_id,
                "subtask_description": subtask_description,
            },
            metadata=metadata or {},
        )

    @classmethod
    def subtask_completed(
        cls,
        spec_id: str,
        subtask_id: str,
        session_number: int,
        metadata: dict[str, Any] | None = None,
    ) -> "WebhookEvent":
        """Create a subtask completed event."""
        return cls(
            type=WebhookEventType.SUBTASK_COMPLETED,
            data={
                "spec_id": spec_id,
                "subtask_id": subtask_id,
                "session_number": session_number,
            },
            metadata=metadata or {},
        )

    @classmethod
    def subtask_failed(
        cls,
        spec_id: str,
        subtask_id: str,
        error_message: str,
        attempt_number: int,
        metadata: dict[str, Any] | None = None,
    ) -> "WebhookEvent":
        """Create a subtask failed event."""
        return cls(
            type=WebhookEventType.SUBTASK_FAILED,
            data={
                "spec_id": spec_id,
                "subtask_id": subtask_id,
                "error_message": error_message,
                "attempt_number": attempt_number,
            },
            metadata=metadata or {},
        )


