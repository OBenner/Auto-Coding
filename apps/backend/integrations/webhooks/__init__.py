"""
Webhook Integration
===================

Configurable webhooks for agent lifecycle events with retry logic,
signature verification, and template customization.

This integration provides:
- Event-driven webhooks for spec/build/QA lifecycle events
- Retry logic with exponential backoff
- Signature verification for security
- Template system for Slack, Discord, Teams
- Delivery tracking and logging
"""

from .models import (
    WebhookConfig,
    WebhookDelivery,
    WebhookDeliveryStatus,
    WebhookEvent,
)

__all__ = [
    "WebhookConfig",
    "WebhookDelivery",
    "WebhookDeliveryStatus",
    "WebhookEvent",
]
