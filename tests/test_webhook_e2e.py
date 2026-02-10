#!/usr/bin/env python3
"""
End-to-End Webhook Flow Verification Tests
===========================================

Tests the complete webhook system integration including:
- Webhook configuration via API
- Event triggering and dispatching
- Payload delivery and verification
- Retry logic with exponential backoff
- Signature verification for security
- Template rendering for different services
- Delivery history and statistics
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from integrations.webhooks.models import (
    WebhookConfig,
    WebhookDelivery,
    WebhookEvent,
    WebhookTemplate,
)
from integrations.webhooks.delivery import (
    WebhookDeliverySystem,
    generate_signature,
    verify_signature,
)
from integrations.webhooks.dispatcher import (
    WebhookDispatcher,
    dispatch_event,
    dispatch_spec_created,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def temp_spec_dir(temp_dir: Path) -> Path:
    """Create a spec directory with webhook configuration."""
    spec_dir = temp_dir / "specs" / "test-webhook"
    spec_dir.mkdir(parents=True, exist_ok=True)

    # Create webhook config directory
    webhook_dir = spec_dir / ".webhooks" / "configs"
    webhook_dir.mkdir(parents=True, exist_ok=True)

    # Create delivery log directory
    delivery_dir = spec_dir / ".webhooks" / "deliveries"
    delivery_dir.mkdir(parents=True, exist_ok=True)

    return spec_dir


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for webhook delivery."""
    client = MagicMock()
    client.post = AsyncMock()

    # Default success response
    client.post.return_value = httpx.Response(
        200, request=MagicMock(), content=b'{"status": "ok"}'
    )

    return client


@pytest.fixture
def webhook_config_slack(temp_spec_dir: Path) -> WebhookConfig:
    """Create a Slack webhook configuration."""
    config = WebhookConfig(
        webhook_id="wh_test_slack_001",
        name="Slack Notifications",
        url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX",
        events=[WebhookEvent.BUILD_STARTED.value, WebhookEvent.BUILD_COMPLETED.value, WebhookEvent.QA_PASSED.value],
        template=WebhookTemplate.SLACK.value,
        secret="test_secret_slack",
        enabled=True,
    )
    return config


@pytest.fixture
def webhook_config_discord(temp_spec_dir: Path) -> WebhookConfig:
    """Create a Discord webhook configuration."""
    config = WebhookConfig(
        webhook_id="wh_test_discord_002",
        name="Discord Notifications",
        url="https://discord.com/api/webhooks/1234567890/abcdefg",
        events=[WebhookEvent.SPEC_CREATED.value, WebhookEvent.BUILD_COMPLETED.value],
        template=WebhookTemplate.DISCORD.value,
        secret="test_secret_discord",
        enabled=True,
    )
    return config


@pytest.fixture
def webhook_config_generic(temp_spec_dir: Path) -> WebhookConfig:
    """Create a generic webhook configuration."""
    config = WebhookConfig(
        webhook_id="wh_test_generic_003",
        name="Generic Webhook",
        url="https://example.com/webhook",
        events=[WebhookEvent.BUILD_STARTED.value, WebhookEvent.BUILD_COMPLETED.value],
        template=WebhookTemplate.GENERIC.value,
        secret="test_secret_generic",
        enabled=True,
    )
    return config


@pytest.fixture
def webhook_config_retry(temp_spec_dir: Path) -> WebhookConfig:
    """Create a webhook configuration with retry settings."""
    config = WebhookConfig(
        webhook_id="wh_test_retry_004",
        name="Retry Test Webhook",
        url="https://example.com/webhook",
        events=[WebhookEvent.BUILD_STARTED.value],
        template=WebhookTemplate.GENERIC.value,
        secret="test_secret_retry",
        enabled=True,
        retry_config={
            "max_retries": 3,
            "initial_delay": 0.1,  # Fast retry for tests
            "max_delay": 60.0,
            "backoff_multiplier": 2.0,
        }
    )
    return config


# =============================================================================
# TEST CLASS: Webhook Configuration
# =============================================================================


class TestWebhookConfiguration:
    """Tests for webhook configuration management."""

    def test_create_and_save_webhook_config(
        self, temp_spec_dir: Path, webhook_config_slack: WebhookConfig
    ):
        """Test creating and saving webhook configuration to file."""
        # Save webhook config
        config_dir = temp_spec_dir / ".webhooks" / "configs"
        webhook_config_slack.save(config_dir)

        # Verify file exists
        config_path = config_dir / f"{webhook_config_slack.webhook_id}.json"
        assert config_path.exists()

        # Load and verify
        loaded_config = WebhookConfig.load(config_dir, webhook_config_slack.webhook_id)
        assert loaded_config.webhook_id == webhook_config_slack.webhook_id
        assert loaded_config.name == webhook_config_slack.name
        assert loaded_config.url == webhook_config_slack.url
        assert loaded_config.template == WebhookTemplate.SLACK.value
        assert len(loaded_config.events) == 3

    def test_webhook_config_event_filtering(self, webhook_config_slack: WebhookConfig):
        """Test event filtering in webhook configuration."""
        # Test should_send_event
        assert webhook_config_slack.should_send_event(WebhookEvent.BUILD_STARTED)
        assert webhook_config_slack.should_send_event(WebhookEvent.BUILD_COMPLETED)
        assert webhook_config_slack.should_send_event(WebhookEvent.QA_PASSED)
        assert not webhook_config_slack.should_send_event(WebhookEvent.SPEC_CREATED)

    def test_multiple_webhook_configs(
        self, temp_spec_dir: Path, webhook_config_slack: WebhookConfig,
        webhook_config_discord: WebhookConfig
    ):
        """Test managing multiple webhook configurations."""
        # Save both configs
        config_dir = temp_spec_dir / ".webhooks" / "configs"
        webhook_config_slack.save(config_dir)
        webhook_config_discord.save(config_dir)

        # List all configs
        config_dir = temp_spec_dir / ".webhooks" / "configs"
        config_files = list(config_dir.glob("*.json"))
        assert len(config_files) == 2


# =============================================================================
# TEST CLASS: Webhook Delivery
# =============================================================================


class TestWebhookDelivery:
    """Tests for webhook delivery system."""

    @pytest.mark.asyncio
    async def test_successful_webhook_delivery(
        self, temp_spec_dir: Path, webhook_config_slack: WebhookConfig, mock_http_client: MagicMock
    ):
        """Test successful webhook delivery."""
        delivery_dir = temp_spec_dir / ".webhooks" / "deliveries"
        delivery_dir.mkdir(parents=True, exist_ok=True)
        delivery_system = WebhookDeliverySystem(delivery_dir)

        # Mock HTTP call
        with patch("httpx.AsyncClient.post", mock_http_client.post):
            delivery = await delivery_system.deliver(
                webhook_config=webhook_config_slack,
                event=WebhookEvent.BUILD_STARTED,
                payload={"event": "build.started", "spec_id": "test-001"},
            )

        # Verify delivery success
        assert delivery.status == "success"
        assert delivery.attempt_count == 1
        assert delivery.response_status == 200

    @pytest.mark.asyncio
    async def test_webhook_delivery_with_signature(
        self, temp_spec_dir: Path, webhook_config_slack: WebhookConfig
    ):
        """Test that webhook delivery includes signature."""
        received_signature = None
        received_payload = None
        delivery_dir = temp_spec_dir / ".webhooks" / "deliveries"
        delivery_dir.mkdir(parents=True, exist_ok=True)

        async def mock_post(url, *, headers, json, **kwargs):
            nonlocal received_signature, received_payload
            received_signature = headers.get("X-Auto-Clause-Signature")
            received_payload = json
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            delivery_system = WebhookDeliverySystem(delivery_dir)
            await delivery_system.deliver(
                webhook_config=webhook_config_slack,
                event=WebhookEvent.BUILD_STARTED,
                payload={"event": "build.started"},
            )

        # Verify signature was sent
        assert received_signature is not None
        assert received_signature.startswith("v1=")
        assert received_payload is not None

    @pytest.mark.asyncio
    async def test_webhook_retry_on_5xx_error(
        self, temp_spec_dir: Path, webhook_config_retry: WebhookConfig
    ):
        """Test retry logic with 5xx server errors."""
        attempt_count = 0
        delivery_dir = temp_spec_dir / ".webhooks" / "deliveries"
        delivery_dir.mkdir(parents=True, exist_ok=True)

        async def mock_post_5xx(url, *, headers, json, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                # First 2 attempts fail with 500
                return httpx.Response(
                    500, request=MagicMock(), content=b'{"error": "Internal Server Error"}'
                )
            # Third attempt succeeds
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post_5xx):
            delivery_system = WebhookDeliverySystem(delivery_dir)
            delivery = await delivery_system.deliver(
                webhook_config=webhook_config_retry,
                event=WebhookEvent.BUILD_STARTED,
                payload={"event": "build.started"},
            )

        # Verify retry logic
        assert delivery.attempt_count == 3
        assert delivery.status == "success"

    @pytest.mark.asyncio
    async def test_webhook_retry_on_timeout(
        self, temp_spec_dir: Path, webhook_config_retry: WebhookConfig
    ):
        """Test retry logic on timeout errors."""
        attempt_count = 0
        delivery_dir = temp_spec_dir / ".webhooks" / "deliveries"
        delivery_dir.mkdir(parents=True, exist_ok=True)

        async def mock_post_timeout(url, *, headers, json, timeout, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise httpx.TimeoutException("Request timed out")
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post_timeout):
            delivery_system = WebhookDeliverySystem(delivery_dir)
            delivery = await delivery_system.deliver(
                webhook_config=webhook_config_retry,
                event=WebhookEvent.BUILD_STARTED,
                payload={"event": "build.started"},
            )

        # Verify retry logic
        assert delivery.attempt_count == 2
        assert delivery.status == "success"

    @pytest.mark.asyncio
    async def test_webhook_permanent_failure_on_4xx(
        self, temp_spec_dir: Path, webhook_config_retry: WebhookConfig
    ):
        """Test that 4xx errors result in permanent failure (no retry)."""
        delivery_dir = temp_spec_dir / ".webhooks" / "deliveries"
        delivery_dir.mkdir(parents=True, exist_ok=True)

        async def mock_post_4xx(url, *, headers, json, **kwargs):
            return httpx.Response(
                404, request=MagicMock(), content=b'{"error": "Not Found"}'
            )

        with patch("httpx.AsyncClient.post", mock_post_4xx):
            delivery_system = WebhookDeliverySystem(delivery_dir)
            delivery = await delivery_system.deliver(
                webhook_config=webhook_config_retry,
                event=WebhookEvent.BUILD_STARTED,
                payload={"event": "build.started"},
            )

        # Verify no retry on 4xx
        assert delivery.attempt_count == 1
        assert delivery.status == "permanent_failure"

    @pytest.mark.asyncio
    async def test_batch_webhook_delivery(
        self,
        temp_spec_dir: Path,
        webhook_config_slack: WebhookConfig,
        webhook_config_discord: WebhookConfig,
    ):
        """Test parallel delivery to multiple webhooks."""
        delivery_dir = temp_spec_dir / ".webhooks" / "deliveries"
        delivery_dir.mkdir(parents=True, exist_ok=True)
        delivered_webhooks = []

        async def mock_post(url, *, headers, json, **kwargs):
            delivered_webhooks.append(url)
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            delivery_system = WebhookDeliverySystem(delivery_dir)
            webhooks = [webhook_config_slack, webhook_config_discord]
            payload = {"event": "build.started", "spec_id": "test-001"}

            deliveries = await delivery_system.deliver_batch(
                webhook_configs=webhooks, event=WebhookEvent.BUILD_STARTED, payload=payload
            )

        # Verify all webhooks received the event
        assert len(deliveries) == 2
        assert all(d.status == "success" for d in deliveries)
        assert len(delivered_webhooks) == 2


# =============================================================================
# TEST CLASS: Signature Verification
# =============================================================================


class TestSignatureVerification:
    """Tests for webhook signature verification."""

    def test_generate_signature(self):
        """Test signature generation."""
        payload = {"event": "build.started", "spec_id": "test-001"}
        secret = "test_secret"

        signature = generate_signature(payload, secret)

        # Verify signature format (v1=hash)
        assert signature.startswith("v1=")
        assert len(signature) > 4  # "v1=" + hash

    def test_signature_deterministic(self):
        """Test signature is deterministic for same input."""
        payload = json.dumps({"event": "build.started"})
        secret = "test_secret"

        sig1 = generate_signature(payload, secret)
        sig2 = generate_signature(payload, secret)

        assert sig1 == sig2

    def test_signature_unique_secrets(self):
        """Test signatures are different for different secrets."""
        payload = json.dumps({"event": "build.started"})

        sig1 = generate_signature(payload, "secret1")
        sig2 = generate_signature(payload, "secret2")

        assert sig1 != sig2

    def test_signature_unique_payloads(self):
        """Test signatures are different for different payloads."""
        secret = "test_secret"

        sig1 = generate_signature(json.dumps({"event": "build.started"}), secret)
        sig2 = generate_signature(json.dumps({"event": "build.completed"}), secret)

        assert sig1 != sig2

    def test_verify_valid_signature(self):
        """Test signature verification with valid signature."""
        payload = json.dumps({"event": "build.started"})
        secret = "test_secret"

        signature = generate_signature(payload, secret)
        is_valid = verify_signature(payload, signature, secret)

        assert is_valid is True

    def test_verify_invalid_signature(self):
        """Test signature verification with invalid signature."""
        payload = json.dumps({"event": "build.started"})
        secret = "test_secret"

        is_valid = verify_signature(payload, "sha256=invalid", secret)

        assert is_valid is False

    def test_verify_tampered_payload(self):
        """Test signature verification with tampered payload."""
        original_payload = json.dumps({"event": "build.started"})
        secret = "test_secret"

        signature = generate_signature(original_payload, secret)

        # Tamper with payload
        tampered_payload = json.dumps({"event": "build.completed"})

        is_valid = verify_signature(tampered_payload, signature, secret)

        assert is_valid is False


# =============================================================================
# TEST CLASS: Webhook Dispatcher
# =============================================================================


class TestWebhookDispatcher:
    """Tests for webhook event dispatcher."""

    @pytest.mark.asyncio
    async def test_dispatch_spec_created_event(
        self, temp_spec_dir: Path, webhook_config_discord: WebhookConfig
    ):
        """Test dispatching spec.created event."""
        # Save webhook config
        config_dir = temp_spec_dir / ".webhooks" / "configs"
        webhook_config_discord.save(config_dir)

        received_payloads = []

        async def mock_post(url, *, headers, json, **kwargs):
            received_payloads.append(json)
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))
            await dispatcher.dispatch_event(
                event=WebhookEvent.SPEC_CREATED,
                data={"spec_id": "test-001", "spec_title": "Test Feature"},
            )

        # Verify webhook was called
        assert len(received_payloads) == 1
        assert received_payloads[0]["event"] == "spec.created"

    @pytest.mark.asyncio
    async def test_dispatch_filters_by_event_subscription(
        self, temp_spec_dir: Path, webhook_config_slack: WebhookConfig
    ):
        """Test that dispatcher only sends to webhooks subscribed to event."""
        # Save webhook config (subscribed to BUILD_STARTED, BUILD_COMPLETED, QA_PASSED)
        config_dir = temp_spec_dir / ".webhooks" / "configs"
        webhook_config_slack.save(config_dir)

        received_count = [0]

        async def mock_post(url, *, headers, json, **kwargs):
            received_count[0] += 1
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))

            # Send SPEC_CREATED (not subscribed)
            await dispatcher.dispatch_event(
                event=WebhookEvent.SPEC_CREATED,
                data={},
            )

        # Verify webhook was not called (not subscribed to SPEC_CREATED)
        assert received_count[0] == 0

    @pytest.mark.asyncio
    async def test_dispatch_to_multiple_webhooks(
        self,
        temp_spec_dir: Path,
        webhook_config_slack: WebhookConfig,
        webhook_config_discord: WebhookConfig,
    ):
        """Test dispatching event to multiple subscribed webhooks."""
        # Save both configs
        slack_path = (
            temp_spec_dir / ".webhooks" / "configs" / f"{webhook_config_slack.webhook_id}.json"
        )
        discord_path = (
            temp_spec_dir / ".webhooks" / "configs" / f"{webhook_config_discord.webhook_id}.json"
        )

        webhook_config_slack.save(str(slack_path))
        webhook_config_discord.save(str(discord_path))

        received_urls = []

        async def mock_post(url, *, headers, json, **kwargs):
            received_urls.append(url)
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))

            # Send BUILD_COMPLETED (both Slack and Discord are subscribed)
            await dispatcher.dispatch_event(
                event=WebhookEvent.BUILD_COMPLETED,
                data={"spec_id": "test-001", "status": "success"},
            )

        # Verify both webhooks received the event
        assert len(received_urls) == 2

    @pytest.mark.asyncio
    async def test_test_webhook_endpoint(self, temp_spec_dir: Path, webhook_config_slack):
        """Test sending a test webhook event."""
        # Save webhook config
        config_dir = temp_spec_dir / ".webhooks" / "configs"
        webhook_config_slack.save(config_dir)

        received_payload = None

        async def mock_post(url, *, headers, json, **kwargs):
            nonlocal received_payload
            received_payload = json
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))
            result = await dispatcher.test_webhook(webhook_config_slack.webhook_id)

        # Verify test webhook was sent
        assert result is True
        assert received_payload is not None
        assert received_payload["event"] == "test"


# =============================================================================
# TEST CLASS: End-to-End Integration
# =============================================================================


class TestWebhookE2E:
    """End-to-end integration tests for webhook system."""

    @pytest.mark.asyncio
    async def test_complete_webhook_flow(
        self, temp_spec_dir: Path, webhook_config_slack: WebhookConfig
    ):
        """
        Test complete webhook flow:
        1. Configure webhook
        2. Trigger event
        3. Verify delivery
        4. Check delivery history
        """
        # Step 1: Configure webhook
        config_dir = temp_spec_dir / ".webhooks" / "configs"
        webhook_config_slack.save(config_dir)
        config_path = config_dir / f"{webhook_config_slack.webhook_id}.json"
        assert config_path.exists()

        # Step 2: Trigger event
        received_events = []

        async def mock_post(url, *, headers, json, **kwargs):
            received_events.append(json)
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))
            await dispatcher.dispatch_event(
                event=WebhookEvent.BUILD_STARTED,
                data={
                    "spec_id": "e2e-test-001",
                    "spec_title": "E2E Test Feature",
                    "phase": "planning",
                },
            )

        # Step 3: Verify delivery
        assert len(received_events) == 1
        payload = received_events[0]
        assert payload["event"] == "build.started"
        assert payload["spec"]["id"] == "e2e-test-001"
        assert "timestamp" in payload

        # Step 4: Check delivery history
        history = dispatcher.get_delivery_history(
            webhook_id=webhook_config_slack.webhook_id, limit=10
        )
        assert len(history) >= 1
        assert history[0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_webhook_with_retry_flow(
        self, temp_spec_dir: Path, webhook_config_retry: WebhookConfig
    ):
        """
        Test webhook delivery with retry flow:
        1. Configure webhook with retry settings
        2. Trigger event that initially fails
        3. Verify retry logic works
        4. Confirm eventual success
        """
        # Step 1: Configure webhook with retry
        config_dir = temp_spec_dir / ".webhooks" / "configs"
        webhook_config_retry.save(config_dir)

        # Step 2 & 3: Trigger event with simulated failures and retries
        attempt_times = []

        async def mock_post_with_retry(url, *, headers, json, **kwargs):
            attempt_times.append(time.time())
            if len(attempt_times) < 3:
                # First 2 attempts fail
                return httpx.Response(
                    500, request=MagicMock(), content=b'{"error": "Server Error"}'
                )
            # Third attempt succeeds
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post_with_retry):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))
            await dispatcher.dispatch_event(
                event=WebhookEvent.BUILD_STARTED,
                data={"spec_id": "retry-test-001"},
            )

        # Step 4: Verify retries happened with exponential backoff
        assert len(attempt_times) == 3

        # Check exponential backoff (allow some tolerance for timing)
        if len(attempt_times) >= 3:
            delay1 = attempt_times[1] - attempt_times[0]
            delay2 = attempt_times[2] - attempt_times[1]
            # Second delay should be longer (backoff multiplier)
            assert delay2 >= delay1 * 0.8  # Allow 20% tolerance

    @pytest.mark.asyncio
    async def test_webhook_signature_security_flow(
        self, temp_spec_dir: Path, webhook_config_generic: WebhookConfig
    ):
        """
        Test webhook signature verification flow:
        1. Configure webhook with secret
        2. Send event
        3. Verify signature is sent
        4. Verify signature can be validated
        """
        # Step 1: Configure webhook
        config_dir = temp_spec_dir / ".webhooks" / "configs"
        webhook_config_generic.save(config_dir)

        received_signature = None
        received_payload = None

        async def mock_post(url, *, headers, json, **kwargs):
            nonlocal received_signature, received_payload
            received_signature = headers.get("X-Auto-Clause-Signature")
            received_payload = json
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        # Step 2: Send event
        with patch("httpx.AsyncClient.post", mock_post):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))
            await dispatcher.dispatch_event(
                event=WebhookEvent.BUILD_COMPLETED,
                data={"spec_id": "security-test-001", "status": "completed"},
            )

        # Step 3: Verify signature was sent
        assert received_signature is not None
        assert received_signature.startswith("sha256=")
        assert received_payload is not None

        # Step 4: Verify signature can be validated
        payload_str = json.dumps(received_payload)
        is_valid = verify_signature(
            payload_str, received_signature, webhook_config_generic.secret
        )
        assert is_valid is True

        # Verify tampered payload fails validation
        tampered_payload = json.dumps({**received_payload, "status": "tampered"})
        is_valid_tampered = verify_signature(
            tampered_payload, received_signature, webhook_config_generic.secret
        )
        assert is_valid_tampered is False


# =============================================================================
# TEST CLASS: Template Rendering
# =============================================================================


class TestWebhookTemplates:
    """Tests for webhook payload template rendering."""

    @pytest.mark.asyncio
    async def test_slack_template_rendering(
        self, temp_spec_dir: Path, webhook_config_slack: WebhookConfig
    ):
        """Test Slack template is correctly rendered."""
        received_payload = None

        async def mock_post(url, *, headers, json, **kwargs):
            nonlocal received_payload
            received_payload = json
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))
            await dispatcher.dispatch_event(
                event=WebhookEvent.BUILD_STARTED,
                data={"spec_id": "slack-test-001", "spec_title": "Slack Test"},
            )

        # Verify Slack Block Kit format
        assert received_payload is not None
        assert "blocks" in received_payload
        assert isinstance(received_payload["blocks"], list)

    @pytest.mark.asyncio
    async def test_discord_template_rendering(
        self, temp_spec_dir: Path, webhook_config_discord: WebhookConfig
    ):
        """Test Discord template is correctly rendered."""
        received_payload = None

        async def mock_post(url, *, headers, json, **kwargs):
            nonlocal received_payload
            received_payload = json
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))
            await dispatcher.dispatch_event(
                event=WebhookEvent.SPEC_CREATED,
                data={"spec_id": "discord-test-001", "spec_title": "Discord Test"},
            )

        # Verify Discord embed format
        assert received_payload is not None
        assert "embeds" in received_payload
        assert isinstance(received_payload["embeds"], list)


# =============================================================================
# TEST CLASS: Delivery Statistics
# =============================================================================


class TestDeliveryStatistics:
    """Tests for webhook delivery statistics and history."""

    @pytest.mark.asyncio
    async def test_delivery_statistics_calculation(
        self, temp_spec_dir: Path, webhook_config_slack: WebhookConfig
    ):
        """Test delivery statistics are calculated correctly."""
        # Save webhook config
        config_dir = temp_spec_dir / ".webhooks" / "configs"
        webhook_config_slack.save(config_dir)

        async def mock_post(url, *, headers, json, **kwargs):
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))

            # Send 3 successful events
            for i in range(3):
                await dispatcher.dispatch_event(
                    event=WebhookEvent.BUILD_STARTED,
                    data={"spec_id": f"stats-test-{i}"},
                )

        # Check statistics
        stats = dispatcher.get_delivery_stats(webhook_config_slack.webhook_id)

        assert stats["total"] >= 3
        assert stats["success"] >= 3
        assert stats["failed"] == 0
        assert stats["success_rate"] == 100.0


# =============================================================================
# TEST CLASS: Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for webhook error handling."""

    @pytest.mark.asyncio
    async def test_invalid_webhook_url(self, temp_spec_dir: Path):
        """Test handling of invalid webhook URL."""
        # Create webhook with invalid URL
        invalid_config = WebhookConfig(
            webhook_id="wh_invalid_001",
            name="Invalid URL Webhook",
            url="not-a-valid-url",
            events=[WebhookEvent.BUILD_STARTED.value],
            enabled=True,
        )

        async def mock_post(url, *, headers, json, **kwargs):
            # This should fail with invalid URL
            raise httpx.UnsupportedProtocol("Invalid URL scheme")

        with patch("httpx.AsyncClient.post", mock_post):
            delivery_system = WebhookDeliverySystem()
            delivery = await delivery_system.deliver(
                webhook_config=invalid_config,
                event=WebhookEvent.BUILD_STARTED,
                payload={"event": "build.started"},
            )

        # Verify error was handled
        assert delivery.status in ["failed", "permanent_failure"]

    @pytest.mark.asyncio
    async def test_disabled_webhook_not_sent(
        self, temp_spec_dir: Path, webhook_config_slack: WebhookConfig
    ):
        """Test that disabled webhooks are not sent."""
        # Disable webhook
        webhook_config_slack.enabled = False

        call_count = [0]

        async def mock_post(url, *, headers, json, **kwargs):
            call_count[0] += 1
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))
            await dispatcher.dispatch_event(
                event=WebhookEvent.BUILD_STARTED,
                data={"spec_id": "test-001"},
            )

        # Verify webhook was not called
        assert call_count[0] == 0


# =============================================================================
# TEST CLASS: Performance
# =============================================================================


class TestPerformance:
    """Tests for webhook system performance."""

    @pytest.mark.asyncio
    async def test_concurrent_webhook_delivery(
        self, temp_spec_dir: Path
    ):
        """Test concurrent delivery to multiple webhooks is efficient."""
        # Create multiple webhook configs
        webhooks = []
        for i in range(5):
            config = WebhookConfig(
                webhook_id=f"wh_perf_{i}",
                name=f"Performance Webhook {i}",
                url=f"https://example.com/webhook/{i}",
                events=[WebhookEvent.BUILD_STARTED.value],
                enabled=True,
            )
            config_path = temp_spec_dir / ".webhooks" / "configs" / f"{config.webhook_id}.json"
            config.save(str(config_path))
            webhooks.append(config)

        delivery_times = []

        async def mock_post(url, *, headers, json, **kwargs):
            start = time.time()
            # Simulate network delay
            await asyncio.sleep(0.1)
            delivery_times.append(time.time() - start)
            return httpx.Response(200, request=MagicMock(), content=b'{"status": "ok"}')

        with patch("httpx.AsyncClient.post", mock_post):
            dispatcher = WebhookDispatcher(str(temp_spec_dir), str(temp_spec_dir.parent))
            start_time = time.time()
            await dispatcher.dispatch_event(
                event=WebhookEvent.BUILD_STARTED,
                data={"spec_id": "perf-test-001"},
            )
            total_time = time.time() - start_time

        # Verify concurrent delivery (should be much faster than sequential)
        # Sequential would be ~0.5s (5 * 0.1), concurrent should be < 0.2s
        assert total_time < 0.3
        assert len(delivery_times) == 5
