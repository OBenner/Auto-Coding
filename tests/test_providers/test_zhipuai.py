#!/usr/bin/env python3
"""
Tests for ZhipuAI Provider Adapter
===================================

Tests the core.providers.adapters.zhipuai module functionality including:
- ZhipuAISession class and its methods
- ZhipuAIProvider class implementing AIEngineProvider interface
- Session creation, management, and cleanup
- Configuration validation and health checks
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# ZHIPUAI MODELS CONSTANT TESTS
# =============================================================================


class TestZhipuAIModels:
    """Tests for ZHIPUAI_MODELS constant."""

    def test_zhipuai_models_is_list(self):
        """Tests ZHIPUAI_MODELS is a list."""
        from core.providers.adapters.zhipuai import ZHIPUAI_MODELS

        assert isinstance(ZHIPUAI_MODELS, list)

    def test_zhipuai_models_contains_expected_models(self):
        """Tests ZHIPUAI_MODELS contains expected model identifiers."""
        from core.providers.adapters.zhipuai import ZHIPUAI_MODELS

        assert "glm-4-flash-250414" in ZHIPUAI_MODELS
        assert "glm-4.7" in ZHIPUAI_MODELS
        assert "glm-4-air" in ZHIPUAI_MODELS
        assert "glm-4-plus" in ZHIPUAI_MODELS

    def test_zhipuai_models_not_empty(self):
        """Tests ZHIPUAI_MODELS is not empty."""
        from core.providers.adapters.zhipuai import ZHIPUAI_MODELS

        assert len(ZHIPUAI_MODELS) > 0


# =============================================================================
# ZHIPUAI SESSION TESTS
# =============================================================================


class TestZhipuAISession:
    """Tests for ZhipuAISession class."""

    def test_session_initialization(self):
        """Tests session initializes with correct attributes."""
        from core.providers.adapters.zhipuai import ZhipuAISession

        session = ZhipuAISession(
            session_id="test-session-123",
            model="glm-4-flash-250414",
            api_key="test-api-key",
            system_prompt="You are a helpful assistant",
            temperature=0.7,
            max_tokens=1000,
        )

        assert session.session_id == "test-session-123"
        assert session.provider_name == "zhipuai"
        assert session.is_active is True
        assert session.model == "glm-4-flash-250414"

    def test_session_initialization_minimal(self):
        """Tests session initializes with minimal params."""
        from core.providers.adapters.zhipuai import ZhipuAISession

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4.7",
            api_key="test-key",
        )

        assert session.session_id == "test-123"
        assert session.model == "glm-4.7"
        assert session.is_active is True

    def test_session_model_property(self):
        """Tests model property returns correct model."""
        from core.providers.adapters.zhipuai import ZhipuAISession

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4-air",
            api_key="test-key",
        )

        assert session.model == "glm-4-air"

    def test_session_messages_property_returns_copy(self):
        """Tests messages property returns a copy of messages."""
        from core.providers.adapters.zhipuai import ZhipuAISession

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4.7",
            api_key="test-key",
        )

        messages = session.messages
        messages.append({"role": "user", "content": "test"})

        # Original should not be affected
        assert len(session.messages) == 0

    def test_session_add_user_message(self):
        """Tests add_user_message adds to history."""
        from core.providers.adapters.zhipuai import ZhipuAISession

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4.7",
            api_key="test-key",
        )

        session.add_user_message("Hello, ZhipuAI!")

        messages = session.messages
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello, ZhipuAI!"

    def test_session_add_assistant_message(self):
        """Tests add_assistant_message adds to history."""
        from core.providers.adapters.zhipuai import ZhipuAISession

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4.7",
            api_key="test-key",
        )

        session.add_assistant_message("Hi there!")

        messages = session.messages
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"] == "Hi there!"

    def test_session_system_prompt_in_messages(self):
        """Tests system prompt is added to messages."""
        from core.providers.adapters.zhipuai import ZhipuAISession

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4.7",
            api_key="test-key",
            system_prompt="You are an expert",
        )

        messages = session.messages
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are an expert"

    def test_session_close(self):
        """Tests session close sets is_active to False."""
        from core.providers.adapters.zhipuai import ZhipuAISession

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4.7",
            api_key="test-key",
        )

        assert session.is_active is True
        session.close()
        assert session.is_active is False

    def test_session_clear_history_keep_system(self):
        """Tests clear_history preserves system prompt."""
        from core.providers.adapters.zhipuai import ZhipuAISession

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4.7",
            api_key="test-key",
            system_prompt="You are an expert",
        )

        session.add_user_message("Hello")
        session.add_assistant_message("Hi")

        assert len(session.messages) == 3  # system + user + assistant

        session.clear_history(keep_system=True)

        messages = session.messages
        assert len(messages) == 1
        assert messages[0]["role"] == "system"

    def test_session_clear_history_remove_system(self):
        """Tests clear_history removes system prompt when keep_system=False."""
        from core.providers.adapters.zhipuai import ZhipuAISession

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4.7",
            api_key="test-key",
            system_prompt="You are an expert",
        )

        session.add_user_message("Hello")

        assert len(session.messages) == 2  # system + user

        session.clear_history(keep_system=False)

        assert len(session.messages) == 0

    def test_complete_inactive_session_raises_error(self):
        """Tests complete() raises ProviderError when session is closed."""
        from core.providers.adapters.zhipuai import ZhipuAISession
        from core.providers.exceptions import ProviderError

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4.7",
            api_key="test-key",
        )
        session.close()

        async def complete():
            async for _ in session.complete("Hello"):
                pass

        loop = asyncio.new_event_loop()
        try:
            with pytest.raises(ProviderError) as exc_info:
                loop.run_until_complete(complete())
            assert "Session is closed" in str(exc_info.value)
        finally:
            loop.close()

    def test_complete_no_sdk_raises_not_installed(self):
        """Tests complete() raises ProviderNotInstalled when zai-sdk missing."""
        from core.providers.adapters.zhipuai import ZhipuAISession
        from core.providers.exceptions import ProviderNotInstalled

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4.7",
            api_key="test-key",
        )

        # Remove cached zai module and patch sys.modules to simulate missing SDK
        import sys

        saved_modules = {
            k: sys.modules.pop(k)
            for k in list(sys.modules)
            if k == "zai" or k.startswith("zai.")
        }
        try:
            with patch.dict("sys.modules", {"zai": None}):

                async def complete():
                    async for _ in session.complete("Hello"):
                        pass

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    with pytest.raises(ProviderNotInstalled) as exc_info:
                        loop.run_until_complete(complete())
                    assert "zai-sdk" in str(exc_info.value)
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)
        finally:
            sys.modules.update(saved_modules)


# =============================================================================
# ZHIPUAI PROVIDER INITIALIZATION TESTS
# =============================================================================


class TestZhipuAIProviderInit:
    """Tests for ZhipuAIProvider initialization."""

    def test_provider_initialization(self):
        """Tests provider initializes with config."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        assert provider.name == "zhipuai"
        assert provider.config is config
        assert provider._active_session is None
        assert provider._validation_errors == []

    def test_provider_name_property(self):
        """Tests name property returns 'zhipuai'."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        assert provider.name == "zhipuai"

    def test_provider_config_property(self):
        """Tests config property returns the configuration."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4-flash-250414",
        )
        provider = ZhipuAIProvider(config)

        assert provider.config is config
        assert provider.config.zhipuai_model == "glm-4-flash-250414"


# =============================================================================
# ZHIPUAI PROVIDER SESSION CREATION TESTS
# =============================================================================


class TestZhipuAIProviderCreateSession:
    """Tests for ZhipuAIProvider.create_session() method."""

    def test_create_session_missing_api_key_raises_error(self):
        """Tests create_session raises error when API key not configured."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderConfigError

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        session_config = SessionConfig(name="test-session")

        with pytest.raises(ProviderConfigError) as exc_info:
            provider.create_session(session_config)
        assert "API key" in str(exc_info.value)

    def test_create_session_missing_model_raises_error(self):
        """Tests create_session raises error when model not configured."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderConfigError

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="",  # Explicitly empty model
        )
        provider = ZhipuAIProvider(config)

        session_config = SessionConfig(name="test-session")

        # Mock the zai module import
        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            with pytest.raises(ProviderConfigError) as exc_info:
                provider.create_session(session_config)
            assert "model" in str(exc_info.value)

    def test_create_session_uses_zhipuai_api_key(self):
        """Tests create_session uses ZHIPUAI_API_KEY."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="zhipuai-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        # Mock the zai module import
        mock_zhipuai_client = MagicMock()
        with patch.dict(
            "sys.modules", {"zai": MagicMock(ZhipuAiClient=mock_zhipuai_client)}
        ):
            session = provider.create_session(SessionConfig(name="test"))

            assert session is not None
            assert session.is_active is True

    def test_create_session_uses_session_config_model(self):
        """Tests create_session uses model from session config if provided."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        session_config = SessionConfig(
            name="test-session",
            model="glm-4-flash-250414",
        )

        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            session = provider.create_session(session_config)

            assert session.model == "glm-4-flash-250414"

    def test_create_session_uses_provider_model_as_default(self):
        """Tests create_session uses provider model when session config has no model."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4-plus",
        )
        provider = ZhipuAIProvider(config)

        session_config = SessionConfig(name="test-session")

        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            session = provider.create_session(session_config)

            assert session.model == "glm-4-plus"

    def test_create_session_no_sdk_raises_not_installed(self):
        """Tests create_session raises ProviderNotInstalled when zai-sdk missing."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderNotInstalled

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        session_config = SessionConfig(name="test-session")

        # Simulate missing SDK via sys.modules patching
        import sys

        saved_modules = {
            k: sys.modules.pop(k)
            for k in list(sys.modules)
            if k == "zai" or k.startswith("zai.")
        }
        try:
            with patch.dict("sys.modules", {"zai": None}):
                with pytest.raises(ProviderNotInstalled) as exc_info:
                    provider.create_session(session_config)
                assert "zai-sdk" in str(exc_info.value)
        finally:
            sys.modules.update(saved_modules)

    def test_create_session_success(self):
        """Tests create_session succeeds with valid params."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider, ZhipuAISession
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        session_config = SessionConfig(
            name="test-session",
            system_prompt="You are helpful",
        )

        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            session = provider.create_session(session_config)

            assert isinstance(session, ZhipuAISession)
            assert session.is_active is True
            assert session.session_id.startswith("zhipuai-")
            assert provider._active_session is session

    def test_create_session_passes_temperature(self):
        """Tests create_session passes temperature to session."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        session_config = SessionConfig(
            name="test-session",
            temperature=0.8,
        )

        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            session = provider.create_session(session_config)

            # Temperature should be stored in session (via _temperature)
            assert abs(session._temperature - 0.8) < 1e-9

    def test_create_session_passes_max_tokens(self):
        """Tests create_session passes max_tokens to session."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        session_config = SessionConfig(
            name="test-session",
            max_tokens=2000,
        )

        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            session = provider.create_session(session_config)

            # Max tokens should be stored in session (via _max_tokens)
            assert session._max_tokens == 2000


# =============================================================================
# ZHIPUAI PROVIDER SEND MESSAGE TESTS
# =============================================================================


class TestZhipuAIProviderSendMessage:
    """Tests for ZhipuAIProvider.send_message() method."""

    def test_send_message_no_active_session_raises_error(self):
        """Tests send_message raises error when no active session."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderError

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

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
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderError

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        session_config = SessionConfig(name="test-session")

        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            session = provider.create_session(session_config)
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
# ZHIPUAI PROVIDER SUPPORTED MODELS TESTS
# =============================================================================


class TestZhipuAIProviderSupportedModels:
    """Tests for ZhipuAIProvider.get_supported_models() method."""

    def test_get_supported_models_returns_list(self):
        """Tests get_supported_models returns a list."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        models = provider.get_supported_models()
        assert isinstance(models, list)

    def test_get_supported_models_contains_expected_models(self):
        """Tests get_supported_models contains expected ZhipuAI models."""
        from core.providers.adapters.zhipuai import ZHIPUAI_MODELS, ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        models = provider.get_supported_models()
        for model in ZHIPUAI_MODELS:
            assert model in models

    def test_get_supported_models_returns_copy(self):
        """Tests get_supported_models returns a copy, not original."""
        from core.providers.adapters.zhipuai import ZHIPUAI_MODELS, ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        models = provider.get_supported_models()
        models.append("test-model")

        # Original ZHIPUAI_MODELS should not be affected
        assert "test-model" not in ZHIPUAI_MODELS


# =============================================================================
# ZHIPUAI PROVIDER VALIDATION TESTS
# =============================================================================


class TestZhipuAIProviderValidation:
    """Tests for ZhipuAIProvider validation methods."""

    def test_validate_config_with_api_key_and_model(self):
        """Tests validate_config returns True when API key and model set."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        assert provider.validate_config() is True

    def test_validate_config_missing_api_key(self):
        """Tests validate_config returns False when API key missing."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        assert provider.validate_config() is False

    def test_validate_config_missing_model(self):
        """Tests validate_config returns False when model missing."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="",  # Explicitly empty model
        )
        provider = ZhipuAIProvider(config)

        assert provider.validate_config() is False

    def test_validate_config_clears_validation_errors(self):
        """Tests validate_config clears previous validation errors."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        # Add some fake errors
        provider._validation_errors = ["error1", "error2"]

        # validate_config should clear them
        provider.validate_config()
        # But will add new errors since config is invalid
        assert len(provider._validation_errors) > 0

    def test_get_validation_errors_api_key(self):
        """Tests get_validation_errors reports missing API key."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        provider.validate_config()
        errors = provider.get_validation_errors()

        assert len(errors) > 0
        assert any("API_KEY" in error for error in errors)

    def test_get_validation_errors_model(self):
        """Tests get_validation_errors reports missing model."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="",  # Explicitly empty model
        )
        provider = ZhipuAIProvider(config)

        provider.validate_config()
        errors = provider.get_validation_errors()

        assert len(errors) > 0
        assert any("MODEL" in error for error in errors)

    def test_get_validation_errors_returns_copy(self):
        """Tests get_validation_errors returns a copy of errors list."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        provider.validate_config()
        errors = provider.get_validation_errors()
        errors.append("test-error")

        # Original should not be affected
        assert "test-error" not in provider._validation_errors


# =============================================================================
# ZHIPUAI PROVIDER HEALTH CHECK TESTS
# =============================================================================


class TestZhipuAIProviderHealthCheck:
    """Tests for ZhipuAIProvider.health_check() method."""

    def test_health_check_with_valid_config(self):
        """Tests health_check returns True when config is valid and SDK installed."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-api-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        # Mock ZhipuAiClient to be available
        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            result = provider.health_check()
            assert result is True

    def test_health_check_invalid_config(self):
        """Tests health_check returns False when config is invalid."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        result = provider.health_check()
        assert result is False

    def test_health_check_no_sdk(self):
        """Tests health_check returns False when SDK not installed."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-api-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        # Simulate missing SDK via scoped sys.modules patching
        import sys

        saved_modules = {
            k: sys.modules.pop(k)
            for k in list(sys.modules)
            if k == "zai" or k.startswith("zai.")
        }
        try:
            with patch.dict("sys.modules", {"zai": None}):
                result = provider.health_check()
                assert result is False
        finally:
            # Restore any removed modules
            sys.modules.update(saved_modules)

    def test_health_check_validates_config_first(self):
        """Tests health_check calls validate_config first."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        # Mock validate_config to return False
        with patch.object(provider, "validate_config", return_value=False):
            result = provider.health_check()
            assert result is False


# =============================================================================
# ZHIPUAI PROVIDER ACTIVE SESSION TESTS
# =============================================================================


class TestZhipuAIProviderActiveSession:
    """Tests for ZhipuAIProvider.get_active_session() method."""

    def test_get_active_session_no_session(self):
        """Tests get_active_session returns None when no session exists."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        assert provider.get_active_session() is None

    def test_get_active_session_with_active_session(self):
        """Tests get_active_session returns session when active."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            session = provider.create_session(SessionConfig(name="test"))

            active = provider.get_active_session()
            assert active is session

    def test_get_active_session_returns_none_when_closed(self):
        """Tests get_active_session returns None when session is closed."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            session = provider.create_session(SessionConfig(name="test"))
            session.close()

            assert provider.get_active_session() is None


# =============================================================================
# ZHIPUAI PROVIDER CLOSE AND CLEANUP TESTS
# =============================================================================


class TestZhipuAIProviderClose:
    """Tests for ZhipuAIProvider.close() method."""

    def test_close_with_no_session(self):
        """Tests close works when no active session."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        # Should not raise
        provider.close()
        assert provider._active_session is None

    def test_close_with_active_session(self):
        """Tests close closes active session."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )
        provider = ZhipuAIProvider(config)

        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            session = provider.create_session(SessionConfig(name="test"))

            provider.close()

            assert session.is_active is False
            assert provider._active_session is None


# =============================================================================
# ZHIPUAI PROVIDER REPR TESTS
# =============================================================================


class TestZhipuAIProviderRepr:
    """Tests for ZhipuAIProvider.__repr__() method."""

    def test_repr_format(self):
        """Tests __repr__ returns expected format."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_model="glm-4-flash-250414",
        )
        provider = ZhipuAIProvider(config)

        repr_str = repr(provider)
        assert "ZhipuAIProvider" in repr_str
        assert "name='zhipuai'" in repr_str
        assert "glm-4-flash-250414" in repr_str

    def test_repr_with_default_model(self):
        """Tests __repr__ with default model."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        repr_str = repr(provider)
        assert "ZhipuAIProvider" in repr_str
        # Default model is "glm-4-flash"
        assert "glm-4-flash" in repr_str


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestZhipuAIProviderIntegration:
    """Integration tests for ZhipuAI provider."""

    def test_full_provider_lifecycle(self):
        """Tests full lifecycle: init -> create session -> close."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import SessionConfig
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7",
        )

        provider = ZhipuAIProvider(config)
        assert provider.name == "zhipuai"

        with patch.dict("sys.modules", {"zai": MagicMock(ZhipuAiClient=MagicMock())}):
            # Create session
            session = provider.create_session(SessionConfig(name="test-session"))

            assert session is not None
            assert session.is_active is True
            assert provider.get_active_session() is session

            # Close provider
            provider.close()

            assert session.is_active is False
            assert provider.get_active_session() is None

    def test_provider_implements_aiengine_interface(self):
        """Tests ZhipuAIProvider implements AIEngineProvider interface."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.base import AIEngineProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="zhipuai")
        provider = ZhipuAIProvider(config)

        # Check it's an instance of the abstract base class
        assert isinstance(provider, AIEngineProvider)

        # Check required methods exist
        assert hasattr(provider, "name")
        assert hasattr(provider, "create_session")
        assert hasattr(provider, "send_message")
        assert hasattr(provider, "get_supported_models")
        assert hasattr(provider, "validate_config")

    def test_session_implements_agentsession(self):
        """Tests ZhipuAISession implements AgentSession interface."""
        from core.providers.adapters.zhipuai import ZhipuAISession
        from core.providers.base import AgentSession

        session = ZhipuAISession(
            session_id="test-123",
            model="glm-4.7",
            api_key="test-key",
        )

        # Check it's an instance of the base class
        assert isinstance(session, AgentSession)

        # Check required attributes/methods exist
        assert hasattr(session, "session_id")
        assert hasattr(session, "provider_name")
        assert hasattr(session, "is_active")
        assert hasattr(session, "close")
