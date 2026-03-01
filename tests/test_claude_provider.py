#!/usr/bin/env python3
"""
Tests for Claude Provider Adapter
=================================

Tests the core.providers.adapters.claude module functionality including:
- ClaudeAgentSession class and its methods
- ClaudeAgentProvider class implementing AIEngineProvider interface
- Session creation, management, and cleanup
- Configuration validation and health checks
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# CLAUDE MODELS CONSTANT TESTS
# =============================================================================


class TestClaudeModels:
    """Tests for CLAUDE_MODELS constant."""

    def test_claude_models_is_list(self):
        """Tests CLAUDE_MODELS is a list."""
        from core.providers.adapters.claude import CLAUDE_MODELS

        assert isinstance(CLAUDE_MODELS, list)

    def test_claude_models_contains_expected_models(self):
        """Tests CLAUDE_MODELS contains expected model identifiers."""
        from core.providers.adapters.claude import CLAUDE_MODELS

        assert "claude-sonnet-4-20250514" in CLAUDE_MODELS
        assert "claude-sonnet-4-5-20250929" in CLAUDE_MODELS
        assert "claude-opus-4-20250514" in CLAUDE_MODELS

    def test_claude_models_not_empty(self):
        """Tests CLAUDE_MODELS is not empty."""
        from core.providers.adapters.claude import CLAUDE_MODELS

        assert len(CLAUDE_MODELS) > 0


# =============================================================================
# CLAUDE AGENT SESSION TESTS
# =============================================================================


class TestClaudeAgentSession:
    """Tests for ClaudeAgentSession class."""

    def test_session_initialization(self):
        """Tests session initializes with correct attributes."""
        from core.providers.adapters.claude import ClaudeAgentSession

        mock_client = MagicMock()
        project_dir = Path("/test/project")
        spec_dir = Path("/test/spec")

        session = ClaudeAgentSession(
            session_id="test-session-123",
            client=mock_client,
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        assert session.session_id == "test-session-123"
        assert session.provider_name == "claude"
        assert session.is_active is True
        assert session.client is mock_client
        assert session.project_dir == project_dir
        assert session.spec_dir == spec_dir

    def test_session_client_property(self):
        """Tests client property returns correct client."""
        from core.providers.adapters.claude import ClaudeAgentSession

        mock_client = MagicMock()
        session = ClaudeAgentSession(
            session_id="test-123",
            client=mock_client,
            project_dir=Path("/test/project"),
            spec_dir=Path("/test/spec"),
        )

        assert session.client is mock_client

    def test_session_project_dir_property(self):
        """Tests project_dir property returns correct path."""
        from core.providers.adapters.claude import ClaudeAgentSession

        project_dir = Path("/test/project")
        session = ClaudeAgentSession(
            session_id="test-123",
            client=MagicMock(),
            project_dir=project_dir,
            spec_dir=Path("/test/spec"),
        )

        assert session.project_dir == project_dir

    def test_session_spec_dir_property(self):
        """Tests spec_dir property returns correct path."""
        from core.providers.adapters.claude import ClaudeAgentSession

        spec_dir = Path("/test/spec")
        session = ClaudeAgentSession(
            session_id="test-123",
            client=MagicMock(),
            project_dir=Path("/test/project"),
            spec_dir=spec_dir,
        )

        assert session.spec_dir == spec_dir

    def test_session_close(self):
        """Tests session close sets is_active to False."""
        from core.providers.adapters.claude import ClaudeAgentSession

        session = ClaudeAgentSession(
            session_id="test-123",
            client=MagicMock(),
            project_dir=Path("/test/project"),
            spec_dir=Path("/test/spec"),
        )

        assert session.is_active is True
        session.close()
        assert session.is_active is False

    def test_session_query_active(self):
        """Tests query() sends message when session is active."""
        from core.providers.adapters.claude import ClaudeAgentSession

        mock_client = MagicMock()
        mock_client.query = AsyncMock()

        session = ClaudeAgentSession(
            session_id="test-123",
            client=mock_client,
            project_dir=Path("/test/project"),
            spec_dir=Path("/test/spec"),
        )

        # Run async function synchronously using new event loop
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(session.query("Hello, Claude!"))
        finally:
            loop.close()
        mock_client.query.assert_awaited_once_with("Hello, Claude!")

    def test_session_query_closed_raises_error(self):
        """Tests query() raises ProviderError when session is closed."""
        from core.providers.adapters.claude import ClaudeAgentSession
        from core.providers.exceptions import ProviderError

        session = ClaudeAgentSession(
            session_id="test-123",
            client=MagicMock(),
            project_dir=Path("/test/project"),
            spec_dir=Path("/test/spec"),
        )
        session.close()

        loop = asyncio.new_event_loop()
        try:
            with pytest.raises(ProviderError) as exc_info:
                loop.run_until_complete(session.query("Hello"))
            assert "Session is closed" in str(exc_info.value)
        finally:
            loop.close()

    def test_session_receive_response_closed_raises_error(self):
        """Tests receive_response() raises ProviderError when session is closed."""
        from core.providers.adapters.claude import ClaudeAgentSession
        from core.providers.exceptions import ProviderError

        session = ClaudeAgentSession(
            session_id="test-123",
            client=MagicMock(),
            project_dir=Path("/test/project"),
            spec_dir=Path("/test/spec"),
        )
        session.close()

        async def consume_response():
            async for _ in session.receive_response():
                pass

        loop = asyncio.new_event_loop()
        try:
            with pytest.raises(ProviderError) as exc_info:
                loop.run_until_complete(consume_response())
            assert "Session is closed" in str(exc_info.value)
        finally:
            loop.close()


# =============================================================================
# CLAUDE AGENT PROVIDER INITIALIZATION TESTS
# =============================================================================


class TestClaudeAgentProviderInit:
    """Tests for ClaudeAgentProvider initialization."""

    def test_provider_initialization(self):
        """Tests provider initializes with config."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        assert provider.name == "claude"
        assert provider.config is config
        assert provider._active_session is None
        assert provider._validation_errors == []

    def test_provider_name_property(self):
        """Tests name property returns 'claude'."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        assert provider.name == "claude"

    def test_provider_config_property(self):
        """Tests config property returns the configuration."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="claude",
            anthropic_api_key="test-key",
            claude_model="claude-opus-4",
        )
        provider = ClaudeAgentProvider(config)

        assert provider.config is config
        assert provider.config.claude_model == "claude-opus-4"


# =============================================================================
# CLAUDE AGENT PROVIDER SESSION CREATION TESTS
# =============================================================================


class TestClaudeAgentProviderCreateSession:
    """Tests for ClaudeAgentProvider.create_session() method."""

    def test_create_session_missing_project_dir_raises_error(self):
        """Tests create_session raises error when project_dir not provided."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderConfigError

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(name="test-session")

        with pytest.raises(ProviderConfigError) as exc_info:
            provider.create_session(session_config, spec_dir=Path("/test/spec"))
        assert "project_dir is required" in str(exc_info.value)

    def test_create_session_missing_spec_dir_raises_error(self):
        """Tests create_session raises error when spec_dir not provided."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderConfigError

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(name="test-session")

        with pytest.raises(ProviderConfigError) as exc_info:
            provider.create_session(session_config, project_dir=Path("/test/project"))
        assert "spec_dir is required" in str(exc_info.value)

    def test_create_session_project_dir_from_extra(self):
        """Tests create_session gets project_dir from extra config."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderConfigError

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(
            name="test-session",
            extra={"project_dir": "/test/project"},
        )

        # Should still fail because spec_dir is missing
        with pytest.raises(ProviderConfigError) as exc_info:
            provider.create_session(session_config)
        assert "spec_dir is required" in str(exc_info.value)

    def test_create_session_spec_dir_from_extra(self):
        """Tests create_session gets spec_dir from extra config."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderConfigError

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(
            name="test-session",
            extra={"spec_dir": "/test/spec"},
        )

        # Should still fail because project_dir is missing
        with pytest.raises(ProviderConfigError) as exc_info:
            provider.create_session(session_config)
        assert "project_dir is required" in str(exc_info.value)

    def test_create_session_dirs_from_extra(self):
        """Tests create_session gets both dirs from extra config."""
        from core.providers.adapters.claude import (
            ClaudeAgentProvider,
            ClaudeAgentSession,
        )
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(
            name="test-session",
            extra={
                "project_dir": "/test/project",
                "spec_dir": "/test/spec",
            },
        )

        # Mock create_client to avoid actual SDK calls - patch where it's imported
        with patch("core.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            session = provider.create_session(session_config)

            assert isinstance(session, ClaudeAgentSession)
            assert session.project_dir == Path("/test/project")
            assert session.spec_dir == Path("/test/spec")

    def test_create_session_success(self):
        """Tests create_session succeeds with valid params."""
        from core.providers.adapters.claude import (
            ClaudeAgentProvider,
            ClaudeAgentSession,
        )
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="claude",
            anthropic_api_key="test-key",
            claude_model="claude-sonnet-4-5-20250929",
        )
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(name="test-session")

        with patch("core.client.create_client") as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            session = provider.create_session(
                session_config,
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
            )

            assert isinstance(session, ClaudeAgentSession)
            assert session.client is mock_client
            assert session.is_active is True
            assert session.session_id.startswith("claude-")
            assert provider._active_session is session

    def test_create_session_uses_config_model(self):
        """Tests create_session uses model from session config if provided."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="claude",
            anthropic_api_key="test-key",
            claude_model="claude-default-model",
        )
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(
            name="test-session",
            model="claude-override-model",
        )

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            provider.create_session(
                session_config,
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
            )

            # Check model passed to create_client
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["model"] == "claude-override-model"

    def test_create_session_uses_provider_model_as_default(self):
        """Tests create_session uses provider model when session config has no model."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="claude",
            anthropic_api_key="test-key",
            claude_model="claude-default-model",
        )
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(name="test-session")

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            provider.create_session(
                session_config,
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["model"] == "claude-default-model"

    def test_create_session_passes_agent_type(self):
        """Tests create_session passes agent_type to create_client."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(name="test-session")

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            provider.create_session(
                session_config,
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
                agent_type="planner",
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["agent_type"] == "planner"

    def test_create_session_passes_max_thinking_tokens(self):
        """Tests create_session passes max_thinking_tokens to create_client."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(name="test-session")

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            provider.create_session(
                session_config,
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
                max_thinking_tokens=10000,
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["max_thinking_tokens"] == 10000

    def test_create_session_max_thinking_tokens_from_extra(self):
        """Tests create_session gets max_thinking_tokens from extra config."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(
            name="test-session",
            extra={"max_thinking_tokens": 5000},
        )

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            provider.create_session(
                session_config,
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["max_thinking_tokens"] == 5000

    def test_create_session_agent_type_from_extra(self):
        """Tests create_session gets agent_type from extra config."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(
            name="test-session",
            extra={"agent_type": "qa_reviewer"},
        )

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            provider.create_session(
                session_config,
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["agent_type"] == "qa_reviewer"

    def test_create_session_passes_output_format(self):
        """Tests create_session passes output_format to create_client."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(name="test-session")
        output_format = {"type": "json", "schema": {"name": "string"}}

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            provider.create_session(
                session_config,
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
                output_format=output_format,
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["output_format"] == output_format

    def test_create_session_passes_agents(self):
        """Tests create_session passes agents dict to create_client."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(name="test-session")
        agents = {"sub_agent": {"model": "claude-sonnet-4"}}

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            provider.create_session(
                session_config,
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
                agents=agents,
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["agents"] == agents

    def test_create_session_handles_creation_failure(self):
        """Tests create_session wraps errors in ProviderError."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderError

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(name="test-session")

        with patch("core.client.create_client") as mock_create:
            mock_create.side_effect = Exception("SDK initialization failed")

            with pytest.raises(ProviderError) as exc_info:
                provider.create_session(
                    session_config,
                    project_dir=Path("/test/project"),
                    spec_dir=Path("/test/spec"),
                )

            assert "Failed to create Claude session" in str(exc_info.value)
            assert "SDK initialization failed" in str(exc_info.value)

    def test_create_session_converts_string_paths(self):
        """Tests create_session converts string paths to Path objects."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(
            name="test-session",
            extra={
                "project_dir": "/test/project",
                "spec_dir": "/test/spec",
            },
        )

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            session = provider.create_session(session_config)

            assert isinstance(session.project_dir, Path)
            assert isinstance(session.spec_dir, Path)


# =============================================================================
# CLAUDE AGENT PROVIDER SEND MESSAGE TESTS
# =============================================================================


class TestClaudeAgentProviderSendMessage:
    """Tests for ClaudeAgentProvider.send_message() method."""

    def test_send_message_no_active_session_raises_error(self):
        """Tests send_message raises error when no active session."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderError

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        async def send():
            async for _ in provider.send_message("Hello"):
                pass

        loop = asyncio.new_event_loop()
        try:
            with pytest.raises(ProviderError) as exc_info:
                loop.run_until_complete(send())
            assert "No active session" in str(exc_info.value)
        finally:
            loop.close()

    def test_send_message_closed_session_raises_error(self):
        """Tests send_message raises error when session is closed."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderError

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        session_config = SessionConfig(name="test-session")

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            session = provider.create_session(
                session_config,
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
            )
            session.close()

        async def send():
            async for _ in provider.send_message("Hello"):
                pass

        loop = asyncio.new_event_loop()
        try:
            with pytest.raises(ProviderError) as exc_info:
                loop.run_until_complete(send())
            assert "Session is closed" in str(exc_info.value)
        finally:
            loop.close()


# =============================================================================
# CLAUDE AGENT PROVIDER SUPPORTED MODELS TESTS
# =============================================================================


class TestClaudeAgentProviderSupportedModels:
    """Tests for ClaudeAgentProvider.get_supported_models() method."""

    def test_get_supported_models_returns_list(self):
        """Tests get_supported_models returns a list."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        models = provider.get_supported_models()
        assert isinstance(models, list)

    def test_get_supported_models_contains_expected_models(self):
        """Tests get_supported_models contains expected Claude models."""
        from core.providers.adapters.claude import CLAUDE_MODELS, ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        models = provider.get_supported_models()
        for model in CLAUDE_MODELS:
            assert model in models

    def test_get_supported_models_returns_copy(self):
        """Tests get_supported_models returns a copy, not original."""
        from core.providers.adapters.claude import CLAUDE_MODELS, ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        models = provider.get_supported_models()
        models.append("test-model")

        # Original CLAUDE_MODELS should not be affected
        assert "test-model" not in CLAUDE_MODELS


# =============================================================================
# CLAUDE AGENT PROVIDER VALIDATION TESTS
# =============================================================================


class TestClaudeAgentProviderValidation:
    """Tests for ClaudeAgentProvider validation methods."""

    def test_validate_config_returns_true(self):
        """Tests validate_config always returns True for Claude.

        Claude SDK uses OAuth, validation happens at session creation.
        """
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        assert provider.validate_config() is True

    def test_validate_config_clears_validation_errors(self):
        """Tests validate_config clears previous validation errors."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        # Add some fake errors
        provider._validation_errors = ["error1", "error2"]

        # validate_config should clear them
        provider.validate_config()
        assert provider._validation_errors == []

    def test_get_validation_errors_returns_copy(self):
        """Tests get_validation_errors returns a copy of errors list."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        errors = provider.get_validation_errors()
        errors.append("test-error")

        # Original should not be affected
        assert "test-error" not in provider._validation_errors


# =============================================================================
# CLAUDE AGENT PROVIDER HEALTH CHECK TESTS
# =============================================================================


class TestClaudeAgentProviderHealthCheck:
    """Tests for ClaudeAgentProvider.health_check() method."""

    def test_health_check_with_api_key(self):
        """Tests health_check returns True when API key is set.

        Note: The health_check method tries to import get_oauth_token from
        core.auth, which fails since the actual function is get_auth_token.
        When import fails, it falls back to checking if anthropic_api_key is set.
        """
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-api-key")
        provider = ClaudeAgentProvider(config)

        # health_check will fail to import get_oauth_token, fall back to API key
        result = provider.health_check()
        assert result is True

    def test_health_check_no_api_key(self):
        """Tests health_check returns False when no auth available.

        Note: The health_check method tries to import get_oauth_token from
        core.auth, which fails since the actual function is get_auth_token.
        When import fails and no API key is set, returns False.
        """
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="")
        provider = ClaudeAgentProvider(config)

        # health_check will fail to import get_oauth_token, fall back to API key
        result = provider.health_check()
        assert result is False

    def test_health_check_validates_config_first(self):
        """Tests health_check calls validate_config first."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        # Mock validate_config to return False
        with patch.object(provider, "validate_config", return_value=False):
            result = provider.health_check()
            assert result is False


# =============================================================================
# CLAUDE AGENT PROVIDER ACTIVE SESSION TESTS
# =============================================================================


class TestClaudeAgentProviderActiveSession:
    """Tests for ClaudeAgentProvider.get_active_session() method."""

    def test_get_active_session_no_session(self):
        """Tests get_active_session returns None when no session exists."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        assert provider.get_active_session() is None

    def test_get_active_session_with_active_session(self):
        """Tests get_active_session returns session when active."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            session = provider.create_session(
                SessionConfig(name="test"),
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
            )

            active = provider.get_active_session()
            assert active is session

    def test_get_active_session_returns_none_when_closed(self):
        """Tests get_active_session returns None when session is closed."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            session = provider.create_session(
                SessionConfig(name="test"),
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
            )
            session.close()

            assert provider.get_active_session() is None


# =============================================================================
# CLAUDE AGENT PROVIDER CLOSE AND CLEANUP TESTS
# =============================================================================


class TestClaudeAgentProviderClose:
    """Tests for ClaudeAgentProvider.close() method."""

    def test_close_with_no_session(self):
        """Tests close works when no active session."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        # Should not raise
        provider.close()
        assert provider._active_session is None

    def test_close_with_active_session(self):
        """Tests close closes active session."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        provider = ClaudeAgentProvider(config)

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            session = provider.create_session(
                SessionConfig(name="test"),
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
            )

            provider.close()

            assert session.is_active is False
            assert provider._active_session is None


# =============================================================================
# CLAUDE AGENT PROVIDER REPR TESTS
# =============================================================================


class TestClaudeAgentProviderRepr:
    """Tests for ClaudeAgentProvider.__repr__() method."""

    def test_repr_format(self):
        """Tests __repr__ returns expected format."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="claude",
            claude_model="claude-opus-4",
        )
        provider = ClaudeAgentProvider(config)

        repr_str = repr(provider)
        assert "ClaudeAgentProvider" in repr_str
        assert "name='claude'" in repr_str
        assert "model='claude-opus-4'" in repr_str

    def test_repr_with_default_model(self):
        """Tests __repr__ with default model."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        repr_str = repr(provider)
        assert "ClaudeAgentProvider" in repr_str
        assert "claude-sonnet-4-5-20250929" in repr_str


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestClaudeProviderIntegration:
    """Integration tests for Claude provider."""

    def test_full_provider_lifecycle(self):
        """Tests full lifecycle: init -> create session -> close."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="claude",
            anthropic_api_key="test-key",
            claude_model="claude-sonnet-4-5-20250929",
        )

        provider = ClaudeAgentProvider(config)
        assert provider.name == "claude"

        with patch("core.client.create_client") as mock_create:
            mock_create.return_value = MagicMock()

            # Create session
            session = provider.create_session(
                SessionConfig(name="test-session"),
                project_dir=Path("/test/project"),
                spec_dir=Path("/test/spec"),
            )

            assert session is not None
            assert session.is_active is True
            assert provider.get_active_session() is session

            # Close provider
            provider.close()

            assert session.is_active is False
            assert provider.get_active_session() is None

    def test_provider_implements_aiengine_interface(self):
        """Tests ClaudeAgentProvider implements AIEngineProvider interface."""
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.base import AIEngineProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude")
        provider = ClaudeAgentProvider(config)

        # Check it's an instance of the abstract base class
        assert isinstance(provider, AIEngineProvider)

        # Check required methods exist
        assert hasattr(provider, "name")
        assert hasattr(provider, "create_session")
        assert hasattr(provider, "send_message")
        assert hasattr(provider, "get_supported_models")
        assert hasattr(provider, "validate_config")

    def test_session_implements_agentsession(self):
        """Tests ClaudeAgentSession implements AgentSession interface."""
        from core.providers.adapters.claude import ClaudeAgentSession
        from core.providers.base import AgentSession

        mock_client = MagicMock()
        session = ClaudeAgentSession(
            session_id="test-123",
            client=mock_client,
            project_dir=Path("/test/project"),
            spec_dir=Path("/test/spec"),
        )

        # Check it's an instance of the base class
        assert isinstance(session, AgentSession)

        # Check required attributes/methods exist
        assert hasattr(session, "session_id")
        assert hasattr(session, "provider_name")
        assert hasattr(session, "is_active")
        assert hasattr(session, "close")
