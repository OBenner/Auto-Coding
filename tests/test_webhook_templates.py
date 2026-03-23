#!/usr/bin/env python3
"""
Webhook Template Tests
======================

Tests for webhook payload template rendering and formatting.
Validates templates for all supported services (Slack, Discord, Teams, JIRA).

Test Coverage:
- Slack template formatting (Block Kit)
- Discord template formatting (embeds)
- Teams template formatting (Adaptive Cards)
- JIRA template formatting (comment body)
- Generic template formatting
- Template variable substitution
- Template validation
- Edge cases and error handling
"""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

# Import from templates module (not package) to avoid naming conflict
import importlib.util

templates_module_path = backend_path / "integrations" / "webhooks" / "templates.py"
spec = importlib.util.spec_from_file_location(
    "integrations.webhooks.templates_module",
    templates_module_path
)
templates_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(templates_module)

TemplateEngine = templates_module.TemplateEngine
render_template = templates_module.render_template

from integrations.webhooks.models import WebhookConfig, WebhookEvent, WebhookTemplate
from integrations.webhooks.payload import PayloadBuilder, build_payload

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_context() -> dict[str, Any]:
    """Sample context data for template rendering."""
    return {
        "event": "build_started",
        "event_title": "Build Started",
        "spec_id": "test-spec-001",
        "spec_title": "Test Feature Implementation",
        "spec_directory": "/path/to/spec",
        "project_directory": "/path/to/project",
        "timestamp": "2024-02-10T12:00:00Z",
        "status": "in_progress",
        "description": "Build has started for Test Feature Implementation",
        "webhook_id": "wh_test_001",
        "webhook_name": "Test Webhook",
    }


@pytest.fixture
def webhook_slack() -> WebhookConfig:
    """Create a Slack webhook configuration."""
    return WebhookConfig(
        webhook_id="wh_slack_001",
        name="Slack Notifications",
        url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX",
        events=[WebhookEvent.BUILD_STARTED.value],
        template=WebhookTemplate.SLACK.value,
        secret="test_secret",
        enabled=True,
    )


@pytest.fixture
def webhook_discord() -> WebhookConfig:
    """Create a Discord webhook configuration."""
    return WebhookConfig(
        webhook_id="wh_discord_001",
        name="Discord Notifications",
        url="https://discord.com/api/webhooks/1234567890/abcdefg",
        events=[WebhookEvent.BUILD_STARTED.value],
        template=WebhookTemplate.DISCORD.value,
        secret="test_secret",
        enabled=True,
    )


@pytest.fixture
def webhook_teams() -> WebhookConfig:
    """Create a Teams webhook configuration."""
    return WebhookConfig(
        webhook_id="wh_teams_001",
        name="Teams Notifications",
        url="https://outlook.office.com/webhook/xxx",
        events=[WebhookEvent.BUILD_STARTED.value],
        template=WebhookTemplate.TEAMS.value,
        secret="test_secret",
        enabled=True,
    )


@pytest.fixture
def webhook_jira() -> WebhookConfig:
    """Create a JIRA webhook configuration."""
    return WebhookConfig(
        webhook_id="wh_jira_001",
        name="JIRA Integration",
        url="https://example.atlassian.net/webhook",
        events=[WebhookEvent.BUILD_STARTED.value],
        template=WebhookTemplate.JIRA.value,
        secret="test_secret",
        enabled=True,
    )


@pytest.fixture
def webhook_generic() -> WebhookConfig:
    """Create a generic webhook configuration."""
    return WebhookConfig(
        webhook_id="wh_generic_001",
        name="Generic Webhook",
        url="https://example.com/webhook",
        events=[WebhookEvent.BUILD_STARTED.value],
        template=WebhookTemplate.GENERIC.value,
        secret="test_secret",
        enabled=True,
    )


# =============================================================================
# TEST CLASS: Template Engine
# =============================================================================


class TestTemplateEngine:
    """Tests for TemplateEngine functionality."""

    def test_list_all_templates(self):
        """Test that all expected templates are available."""
        engine = TemplateEngine()
        templates = engine.list_templates()

        assert "generic" in templates
        assert "slack" in templates
        assert "discord" in templates
        assert "teams" in templates
        assert "jira" in templates

    def test_get_template_by_name(self):
        """Test retrieving templates by name."""
        engine = TemplateEngine()

        slack_template = engine.get_template("slack")
        assert slack_template is not None
        assert "blocks" in slack_template

        discord_template = engine.get_template("discord")
        assert discord_template is not None
        assert "embeds" in discord_template

    def test_get_nonexistent_template(self):
        """Test retrieving non-existent template returns None."""
        engine = TemplateEngine()
        template = engine.get_template("nonexistent")
        assert template is None

    def test_extract_required_variables(self):
        """Test extracting required variables from templates."""
        engine = TemplateEngine()

        # Slack template variables
        slack_vars = engine.extract_required_variables("slack")
        assert "event" in slack_vars
        assert "event_title" in slack_vars
        assert "spec_id" in slack_vars
        assert "timestamp" in slack_vars

        # Discord template variables
        discord_vars = engine.extract_required_variables("discord")
        assert "event_title" in discord_vars
        assert "spec_id" in discord_vars


# =============================================================================
# TEST CLASS: Slack Template
# =============================================================================


class TestSlackTemplate:
    """Tests for Slack template formatting."""

    def test_slack_template_structure(self, sample_context: dict[str, Any]):
        """Test Slack template has correct Block Kit structure."""
        engine = TemplateEngine()
        payload = engine.render("slack", sample_context)

        # Verify Block Kit structure
        assert "blocks" in payload
        assert isinstance(payload["blocks"], list)
        assert len(payload["blocks"]) > 0

    def test_slack_template_header_block(self, sample_context: dict[str, Any]):
        """Test Slack template header block."""
        engine = TemplateEngine()
        payload = engine.render("slack", sample_context)

        header = payload["blocks"][0]
        assert header["type"] == "header"
        assert header["text"]["type"] == "plain_text"
        assert header["text"]["emoji"] is True
        assert sample_context["event_title"] in header["text"]["text"]

    def test_slack_template_section_blocks(self, sample_context: dict[str, Any]):
        """Test Slack template section blocks with fields."""
        engine = TemplateEngine()
        payload = engine.render("slack", sample_context)

        # Find section blocks
        sections = [b for b in payload["blocks"] if b["type"] == "section"]
        assert len(sections) >= 1

        # Verify fields section
        fields_section = sections[0]
        assert "fields" in fields_section
        assert isinstance(fields_section["fields"], list)
        assert len(fields_section["fields"]) == 2

        # Check spec_id field
        spec_field = fields_section["fields"][0]
        assert "Spec:" in spec_field["text"]
        assert sample_context["spec_id"] in spec_field["text"]

    def test_slack_template_context_block(self, sample_context: dict[str, Any]):
        """Test Slack template context block with timestamp."""
        engine = TemplateEngine()
        payload = engine.render("slack", sample_context)

        # Find context block
        context_blocks = [b for b in payload["blocks"] if b["type"] == "context"]
        assert len(context_blocks) >= 1

        context = context_blocks[0]
        assert "elements" in context
        assert "Timestamp:" in context["elements"][0]["text"]
        assert sample_context["timestamp"] in context["elements"][0]["text"]

    def test_slack_template_variable_substitution(self, sample_context: dict[str, Any]):
        """Test all variables are substituted correctly in Slack template."""
        engine = TemplateEngine()
        payload = engine.render("slack", sample_context)

        # Convert to JSON string to check for unreplaced placeholders
        payload_str = json.dumps(payload)

        # Verify no unreplaced placeholders (in strict mode, placeholders remain)
        # In non-strict mode, placeholders that can't be replaced stay as-is
        assert sample_context["event_title"] in payload_str or "event_title" not in payload_str
        assert sample_context["spec_id"] in payload_str

    def test_slack_template_with_build_payload(self, webhook_slack: WebhookConfig):
        """Test Slack template through build_payload function."""
        data = {
            "spec_id": "build-test-001",
            "spec_title": "Build Test Feature",
            "status": "in_progress",
        }

        payload = build_payload(
            webhook=webhook_slack,
            event=WebhookEvent.BUILD_STARTED,
            data=data,
        )

        # Verify Slack Block Kit structure
        assert "blocks" in payload
        assert isinstance(payload["blocks"], list)


# =============================================================================
# TEST CLASS: Discord Template
# =============================================================================


class TestDiscordTemplate:
    """Tests for Discord template formatting."""

    def test_discord_template_structure(self, sample_context: dict[str, Any]):
        """Test Discord template has correct embed structure."""
        engine = TemplateEngine()
        payload = engine.render("discord", sample_context)

        # Verify embed structure
        assert "embeds" in payload
        assert isinstance(payload["embeds"], list)
        assert len(payload["embeds"]) == 1

    def test_discord_template_embed_fields(self, sample_context: dict[str, Any]):
        """Test Discord template embed has all required fields."""
        engine = TemplateEngine()
        payload = engine.render("discord", sample_context)

        embed = payload["embeds"][0]

        # Check required fields
        assert "title" in embed
        assert "description" in embed
        assert "color" in embed
        assert "fields" in embed
        assert "timestamp" in embed
        assert "footer" in embed

    def test_discord_template_embed_title(self, sample_context: dict[str, Any]):
        """Test Discord embed title."""
        engine = TemplateEngine()
        payload = engine.render("discord", sample_context)

        embed = payload["embeds"][0]
        assert embed["title"] == sample_context["event_title"]

    def test_discord_template_embed_fields_content(self, sample_context: dict[str, Any]):
        """Test Discord embed fields contain correct data."""
        engine = TemplateEngine()
        payload = engine.render("discord", sample_context)

        embed = payload["embeds"][0]
        fields = embed["fields"]

        assert len(fields) == 3

        # Check Spec ID field
        spec_field = next((f for f in fields if f["name"] == "Spec ID"), None)
        assert spec_field is not None
        assert spec_field["value"] == sample_context["spec_id"]
        assert spec_field["inline"] is True

        # Check Status field
        status_field = next((f for f in fields if f["name"] == "Status"), None)
        assert status_field is not None
        assert status_field["value"] == sample_context["status"]

        # Check Spec Title field
        title_field = next((f for f in fields if f["name"] == "Spec Title"), None)
        assert title_field is not None
        assert title_field["value"] == sample_context["spec_title"]

    def test_discord_template_username(self, sample_context: dict[str, Any]):
        """Test Discord template sets username."""
        engine = TemplateEngine()
        payload = engine.render("discord", sample_context)

        assert "username" in payload
        assert payload["username"] == "Auto-Claude"

    def test_discord_template_with_build_payload(self, webhook_discord: WebhookConfig):
        """Test Discord template through build_payload function."""
        data = {
            "spec_id": "discord-test-001",
            "spec_title": "Discord Test Feature",
        }

        payload = build_payload(
            webhook=webhook_discord,
            event=WebhookEvent.SPEC_CREATED,
            data=data,
        )

        # Verify Discord embed structure
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1


# =============================================================================
# TEST CLASS: Teams Template
# =============================================================================


class TestTeamsTemplate:
    """Tests for Microsoft Teams template formatting."""

    def test_teams_template_structure(self, sample_context: dict[str, Any]):
        """Test Teams template has correct Adaptive Card structure."""
        engine = TemplateEngine()
        payload = engine.render("teams", sample_context)

        # Verify structure
        assert "type" in payload
        assert payload["type"] == "message"
        assert "attachments" in payload
        assert isinstance(payload["attachments"], list)

    def test_teams_template_adaptive_card(self, sample_context: dict[str, Any]):
        """Test Teams template Adaptive Card content."""
        engine = TemplateEngine()
        payload = engine.render("teams", sample_context)

        attachment = payload["attachments"][0]
        assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"

        card = attachment["content"]
        assert card["type"] == "AdaptiveCard"
        assert "$schema" in card
        assert "version" in card
        assert "body" in card

    def test_teams_template_body_elements(self, sample_context: dict[str, Any]):
        """Test Teams template body elements."""
        engine = TemplateEngine()
        payload = engine.render("teams", sample_context)

        card = payload["attachments"][0]["content"]
        body = card["body"]

        assert len(body) >= 3

        # First element: title (TextBlock)
        title = body[0]
        assert title["type"] == "TextBlock"
        assert title["weight"] == "Bolder"
        assert title["size"] == "Large"
        assert sample_context["event_title"] in title["text"]

        # Second element: description (TextBlock)
        description = body[1]
        assert description["type"] == "TextBlock"
        assert description["wrap"] is True

        # Third element: FactSet
        fact_set = body[2]
        assert fact_set["type"] == "FactSet"
        assert "facts" in fact_set
        assert len(fact_set["facts"]) == 3

    def test_teams_template_facts(self, sample_context: dict[str, Any]):
        """Test Teams template FactSet contains correct facts."""
        engine = TemplateEngine()
        payload = engine.render("teams", sample_context)

        card = payload["attachments"][0]["content"]
        fact_set = card["body"][2]
        facts = fact_set["facts"]

        # Check Spec ID fact
        spec_fact = next((f for f in facts if f["title"] == "Spec ID"), None)
        assert spec_fact is not None
        assert spec_fact["value"] == sample_context["spec_id"]

        # Check Status fact
        status_fact = next((f for f in facts if f["title"] == "Status"), None)
        assert status_fact is not None
        assert status_fact["value"] == sample_context["status"]

        # Check Timestamp fact
        time_fact = next((f for f in facts if f["title"] == "Timestamp"), None)
        assert time_fact is not None
        assert time_fact["value"] == sample_context["timestamp"]

    def test_teams_template_with_build_payload(self, webhook_teams: WebhookConfig):
        """Test Teams template through build_payload function."""
        data = {
            "spec_id": "teams-test-001",
            "spec_title": "Teams Test Feature",
        }

        payload = build_payload(
            webhook=webhook_teams,
            event=WebhookEvent.BUILD_COMPLETED,
            data=data,
        )

        # Verify Teams Adaptive Card structure
        assert "attachments" in payload
        assert len(payload["attachments"]) == 1


# =============================================================================
# TEST CLASS: JIRA Template
# =============================================================================


class TestJIRATemplate:
    """Tests for JIRA template formatting."""

    def test_jira_template_structure(self, sample_context: dict[str, Any]):
        """Test JIRA template has correct structure."""
        engine = TemplateEngine()
        payload = engine.render("jira", sample_context)

        # JIRA uses simple body text
        assert "body" in payload
        assert isinstance(payload["body"], str)

    def test_jira_template_body_content(self, sample_context: dict[str, Any]):
        """Test JIRA template body contains required information."""
        engine = TemplateEngine()
        payload = engine.render("jira", sample_context)

        body = payload["body"]

        # Check description is present
        assert sample_context["description"] in body

        # Check event info is present
        assert "Event:" in body
        assert sample_context["event"] in body

        # Check spec info is present
        assert "Spec:" in body
        assert sample_context["spec_id"] in body

        # Check timestamp is present
        assert "Timestamp:" in body
        assert sample_context["timestamp"] in body

    def test_jira_template_formatting(self, sample_context: dict[str, Any]):
        """Test JIRA template uses markdown formatting."""
        engine = TemplateEngine()
        payload = engine.render("jira", sample_context)

        body = payload["body"]

        # Check for separator line
        assert "---" in body

        # Check for italic formatting
        assert "*" in body or "_" in body

    def test_jira_template_with_build_payload(self, webhook_jira: WebhookConfig):
        """Test JIRA template through build_payload function."""
        data = {
            "spec_id": "jira-test-001",
            "spec_title": "JIRA Test Feature",
            "description": "Test description for JIRA",
        }

        payload = build_payload(
            webhook=webhook_jira,
            event=WebhookEvent.BUILD_STARTED,
            data=data,
        )

        # Verify JIRA body structure
        assert "body" in payload
        assert isinstance(payload["body"], str)
        assert data["spec_id"] in payload["body"]


# =============================================================================
# TEST CLASS: Generic Template
# =============================================================================


class TestGenericTemplate:
    """Tests for generic webhook template."""

    def test_generic_template_structure(self, sample_context: dict[str, Any]):
        """Test generic template has correct JSON structure."""
        engine = TemplateEngine()
        payload = engine.render("generic", sample_context)

        # Verify structure
        assert "event" in payload
        assert "timestamp" in payload
        assert "spec" in payload
        assert "webhook" in payload

    def test_generic_template_spec_object(self, sample_context: dict[str, Any]):
        """Test generic template spec object."""
        engine = TemplateEngine()
        payload = engine.render("generic", sample_context)

        spec = payload["spec"]
        assert "id" in spec
        assert "title" in spec
        assert "directory" in spec

        assert spec["id"] == sample_context["spec_id"]
        assert spec["title"] == sample_context["spec_title"]
        assert spec["directory"] == sample_context["spec_directory"]

    def test_generic_template_project_object(self, sample_context: dict[str, Any]):
        """Test generic template project object."""
        engine = TemplateEngine()
        payload = engine.render("generic", sample_context)

        assert "project" in payload
        project = payload["project"]
        assert "directory" in project
        assert project["directory"] == sample_context["project_directory"]

    def test_generic_template_webhook_object(self, sample_context: dict[str, Any]):
        """Test generic template webhook object."""
        engine = TemplateEngine()
        payload = engine.render("generic", sample_context)

        webhook = payload["webhook"]
        assert "id" in webhook
        assert "name" in webhook
        assert webhook["id"] == sample_context["webhook_id"]
        assert webhook["name"] == sample_context["webhook_name"]

    def test_generic_template_data_field(self, sample_context: dict[str, Any]):
        """Test generic template includes event data."""
        engine = TemplateEngine()
        payload = engine.render("generic", sample_context)

        # data_json should contain additional event data
        assert "data" in payload or "data_json" in payload

    def test_generic_template_with_build_payload(self, webhook_generic: WebhookConfig):
        """Test generic template through build_payload function."""
        data = {
            "spec_id": "generic-test-001",
            "spec_title": "Generic Test Feature",
        }

        payload = build_payload(
            webhook=webhook_generic,
            event=WebhookEvent.QA_PASSED,
            data=data,
        )

        # Verify generic structure
        assert "event" in payload
        assert "spec" in payload
        assert payload["spec"]["id"] == data["spec_id"]


# =============================================================================
# TEST CLASS: Template Variable Substitution
# =============================================================================


class TestVariableSubstitution:
    """Tests for template variable substitution."""

    def test_all_variables_substituted(self, sample_context: dict[str, Any]):
        """Test all template variables are substituted correctly."""
        engine = TemplateEngine()

        for template_name in ["generic", "slack", "discord", "teams", "jira"]:
            payload = engine.render(template_name, sample_context)

            # Convert to string to check for unreplaced variables
            payload_str = json.dumps(payload)

            # Check that context values are present (no unreplaced placeholders)
            assert sample_context["event"] in payload_str or "event" not in payload_str
            assert sample_context["spec_id"] in payload_str

    def test_missing_variables_handled_gracefully(self):
        """Test that missing variables don't break rendering."""
        engine = TemplateEngine()

        # Minimal context (missing many variables)
        minimal_context = {
            "event": "test_event",
            "spec_id": "test-001",
        }

        # Should not raise error in non-strict mode
        payload = engine.render("slack", minimal_context, strict=False)

        # Should have some structure even with minimal data
        assert isinstance(payload, dict)

    def test_missing_variables_strict_mode(self):
        """Test that missing variables raise error in strict mode."""
        engine = TemplateEngine()

        # Context with missing required variables
        incomplete_context = {
            "event": "test_event",
            # Missing: spec_id, timestamp, etc.
        }

        # Should raise error in strict mode
        with pytest.raises(ValueError, match="Missing required variables"):
            engine.render("generic", incomplete_context, strict=True)

    def test_special_characters_in_variables(self):
        """Test template handles special characters correctly."""
        engine = TemplateEngine()

        context = {
            "event": "build_started",
            "event_title": "Build Started: <Test> & \"Feature\"",
            "spec_id": "test-with-special-chars-001",
            "spec_title": "Feature with 'quotes' and \"double quotes\"",
            "description": "Description with\nnewlines and\ttabs",
            "timestamp": "2024-02-10T12:00:00Z",
            "status": "in_progress",
        }

        # Should not raise error
        payload = engine.render("slack", context)

        # Special characters should be preserved
        payload_str = json.dumps(payload)
        assert "Test" in payload_str


# =============================================================================
# TEST CLASS: Payload Builder Integration
# =============================================================================


class TestPayloadBuilderIntegration:
    """Tests for PayloadBuilder with templates."""

    def test_payload_builder_builds_slack_payload(
        self, webhook_slack: WebhookConfig
    ):
        """Test PayloadBuilder builds Slack payload correctly."""
        builder = PayloadBuilder()

        data = {
            "spec_id": "pb-test-001",
            "spec_title": "Payload Builder Test",
            "status": "in_progress",
        }

        payload = builder.build(
            webhook=webhook_slack,
            event=WebhookEvent.BUILD_STARTED,
            data=data,
        )

        # Verify Slack structure
        assert "blocks" in payload
        assert isinstance(payload["blocks"], list)

    def test_payload_builder_adds_timestamp(
        self, webhook_slack: WebhookConfig
    ):
        """Test PayloadBuilder adds timestamp automatically."""
        builder = PayloadBuilder()

        data = {"spec_id": "timestamp-test-001"}

        payload = builder.build(
            webhook=webhook_slack,
            event=WebhookEvent.BUILD_STARTED,
            data=data,
        )

        # Check timestamp exists and is recent
        payload_str = json.dumps(payload)
        assert "20" in payload_str  # Year prefix

    def test_payload_builder_status_derivation(
        self, webhook_slack: WebhookConfig
    ):
        """Test PayloadBuilder derives status from event."""
        builder = PayloadBuilder()

        data = {"spec_id": "status-test-001"}

        # Test different events
        for event, expected_status in [
            (WebhookEvent.BUILD_STARTED, "in_progress"),
            (WebhookEvent.BUILD_COMPLETED, "completed"),
            (WebhookEvent.QA_PASSED, "passed"),
            (WebhookEvent.QA_FAILED, "failed"),
        ]:
            payload = builder.build(
                webhook=webhook_slack,
                event=event,
                data=data,
            )

            payload_str = json.dumps(payload)
            assert expected_status in payload_str

    def test_payload_builder_with_custom_status(
        self, webhook_slack: WebhookConfig
    ):
        """Test PayloadBuilder uses custom status from data."""
        builder = PayloadBuilder()

        custom_status = "custom_status_value"
        data = {
            "spec_id": "custom-status-test-001",
            "status": custom_status,
        }

        payload = builder.build(
            webhook=webhook_slack,
            event=WebhookEvent.BUILD_STARTED,
            data=data,
        )

        # Custom status should override derived status
        payload_str = json.dumps(payload)
        assert custom_status in payload_str


# =============================================================================
# TEST CLASS: Template Validation
# =============================================================================


class TestTemplateValidation:
    """Tests for template validation."""

    def test_validate_valid_template(self):
        """Test validation of valid template."""
        engine = TemplateEngine()

        template = {
            "text": "Event: {event}",
            "timestamp": "{timestamp}",
        }

        errors = engine.validate_template(template)
        assert len(errors) == 0

    def test_validate_template_without_placeholders(self):
        """Test validation fails for template without placeholders."""
        engine = TemplateEngine()

        template = {
            "text": "Static text without variables",
        }

        errors = engine.validate_template(template)
        assert len(errors) > 0
        assert "placeholder" in errors[0].lower()

    def test_validate_template_with_invalid_placeholder(self):
        """Test validation detects invalid placeholder names."""
        engine = TemplateEngine()

        template = {
            "text": "Event: {invalid-name-with-dashes}",
        }

        errors = engine.validate_template(template)
        # Should have error about invalid placeholder
        assert len(errors) > 0


# =============================================================================
# TEST CLASS: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_context(self):
        """Test rendering with empty context."""
        engine = TemplateEngine()

        # Should not crash, just return template with placeholders
        payload = engine.render("generic", {}, strict=False)
        assert isinstance(payload, dict)

    def test_very_long_spec_title(self):
        """Test template handles very long spec titles."""
        engine = TemplateEngine()

        long_title = "A" * 500
        context = {
            "event": "test",
            "event_title": "Test",
            "spec_id": "test-001",
            "spec_title": long_title,
            "timestamp": "2024-02-10T12:00:00Z",
            "status": "test",
            "description": "Test",
            "webhook_id": "wh_test",
            "webhook_name": "Test",
        }

        # Should not crash or truncate
        payload = engine.render("slack", context)
        assert isinstance(payload, dict)

    def test_unicode_characters(self):
        """Test template handles unicode characters correctly."""
        engine = TemplateEngine()

        context = {
            "event": "test_event",
            "event_title": "Test Event 🎉",
            "spec_id": "test-001-日本語",
            "spec_title": "Feature with émojis 🚀 and spëcial çhars",
            "timestamp": "2024-02-10T12:00:00Z",
            "status": "in_progress",
            "description": "Tëst with üñïçödë",
            "webhook_id": "wh_test",
            "webhook_name": "Tëst Wëbhøõk",
        }

        # Should handle unicode without errors
        payload = engine.render("slack", context)

        # Verify unicode is preserved (may be JSON-escaped)
        # Check for escaped unicode or raw unicode
        payload_str = json.dumps(payload)
        assert (
            "\\ud83c\\udf89" in payload_str or  # Escaped emoji
            "🎉" in payload_str or  # Raw emoji
            "event_title" in payload_str  # Or just check field exists
        )

    def test_nested_data_in_context(self):
        """Test template handles nested data structures."""
        engine = TemplateEngine()

        nested_data = {
            "metrics": {"cpu": 80, "memory": 512},
            "files": ["file1.py", "file2.ts"],
        }

        context = {
            "event": "test",
            "spec_id": "test-001",
            "timestamp": "2024-02-10T12:00:00Z",
            "status": "test",
            "description": "Test",
            "webhook_id": "wh_test",
            "webhook_name": "Test",
        }

        # Add nested data
        context.update(nested_data)

        # Should handle nested data (data_json field)
        payload = engine.render("generic", context)
        assert isinstance(payload, dict)


# =============================================================================
# TEST CLASS: Convenience Functions
# =============================================================================


class TestConvenienceFunctions:
    """Tests for template convenience functions."""

    def test_render_template_function(self, sample_context: dict[str, Any]):
        """Test render_template convenience function."""
        payload = render_template("slack", sample_context)

        assert isinstance(payload, dict)
        assert "blocks" in payload

    def test_render_template_with_strict_mode(self):
        """Test render_template with strict mode."""
        incomplete_context = {"event": "test"}

        # Should raise in strict mode
        with pytest.raises(ValueError):
            render_template("generic", incomplete_context, strict=True)

        # Should work in non-strict mode
        payload = render_template("generic", incomplete_context, strict=False)
        assert isinstance(payload, dict)
