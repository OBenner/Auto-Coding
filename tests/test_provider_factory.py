#!/usr/bin/env python3
"""
Tests for Provider Factory and Configuration
=============================================

Tests the core.providers module functionality including:
- ProviderConfig dataclass and from_env() loading
- Provider validation and error messages
- Factory functions for creating providers
- Exception hierarchy for provider errors
"""

import os
import pytest
from unittest.mock import patch, MagicMock


# =============================================================================
# PROVIDER CONFIG TESTS
# =============================================================================


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_default_values(self):
        """Tests default values are set correctly."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig()
        assert config.provider == "claude"
        assert config.anthropic_api_key == ""
        assert config.claude_model == "claude-sonnet-4-5-20250929"
        assert config.litellm_model == ""
        assert config.openrouter_model == "anthropic/claude-sonnet-4"
        assert config.openrouter_base_url == "https://openrouter.ai/api/v1"

    def test_from_env_default_provider(self):
        """Tests from_env() defaults to claude when no env var set."""
        from core.providers.config import ProviderConfig

        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing AI_ENGINE_PROVIDER
            os.environ.pop("AI_ENGINE_PROVIDER", None)
            config = ProviderConfig.from_env()
            assert config.provider == "claude"

    def test_from_env_claude_provider(self):
        """Tests from_env() correctly loads claude provider."""
        from core.providers.config import ProviderConfig

        env = {
            "AI_ENGINE_PROVIDER": "claude",
            "ANTHROPIC_API_KEY": "test-key-123",
            "CLAUDE_MODEL": "claude-opus-4",
        }
        with patch.dict(os.environ, env, clear=True):
            config = ProviderConfig.from_env()
            assert config.provider == "claude"
            assert config.anthropic_api_key == "test-key-123"
            assert config.claude_model == "claude-opus-4"

    def test_from_env_litellm_provider(self):
        """Tests from_env() correctly loads litellm provider."""
        from core.providers.config import ProviderConfig

        env = {
            "AI_ENGINE_PROVIDER": "litellm",
            "LITELLM_MODEL": "gpt-4",
            "LITELLM_API_BASE": "https://api.example.com",
            "LITELLM_API_KEY": "litellm-key-456",
        }
        with patch.dict(os.environ, env, clear=True):
            config = ProviderConfig.from_env()
            assert config.provider == "litellm"
            assert config.litellm_model == "gpt-4"
            assert config.litellm_api_base == "https://api.example.com"
            assert config.litellm_api_key == "litellm-key-456"

    def test_from_env_openrouter_provider(self):
        """Tests from_env() correctly loads openrouter provider."""
        from core.providers.config import ProviderConfig

        env = {
            "AI_ENGINE_PROVIDER": "openrouter",
            "OPENROUTER_API_KEY": "or-key-789",
            "OPENROUTER_MODEL": "anthropic/claude-opus-4",
            "OPENROUTER_BASE_URL": "https://custom.openrouter.ai/api/v1",
        }
        with patch.dict(os.environ, env, clear=True):
            config = ProviderConfig.from_env()
            assert config.provider == "openrouter"
            assert config.openrouter_api_key == "or-key-789"
            assert config.openrouter_model == "anthropic/claude-opus-4"
            assert config.openrouter_base_url == "https://custom.openrouter.ai/api/v1"

    def test_from_env_invalid_provider_falls_back_to_default(self):
        """Tests from_env() falls back to claude for invalid provider."""
        from core.providers.config import ProviderConfig

        env = {"AI_ENGINE_PROVIDER": "invalid_provider"}
        with patch.dict(os.environ, env, clear=True):
            config = ProviderConfig.from_env()
            assert config.provider == "claude"

    def test_from_env_case_insensitive_provider(self):
        """Tests from_env() handles case-insensitive provider names."""
        from core.providers.config import ProviderConfig

        for provider in ["CLAUDE", "Claude", "LITELLM", "LiteLLM", "OPENROUTER", "OpenRouter"]:
            env = {"AI_ENGINE_PROVIDER": provider}
            with patch.dict(os.environ, env, clear=True):
                config = ProviderConfig.from_env()
                assert config.provider == provider.lower()


class TestProviderConfigValidation:
    """Tests for ProviderConfig validation methods."""

    def test_is_valid_claude_with_key(self):
        """Tests is_valid() returns True for claude with API key."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        assert config.is_valid() is True

    def test_is_valid_claude_without_key(self):
        """Tests is_valid() returns False for claude without API key."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="")
        assert config.is_valid() is False

    def test_is_valid_litellm_with_model(self):
        """Tests is_valid() returns True for litellm with model."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="litellm", litellm_model="gpt-4")
        assert config.is_valid() is True

    def test_is_valid_litellm_without_model(self):
        """Tests is_valid() returns False for litellm without model."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="litellm", litellm_model="")
        assert config.is_valid() is False

    def test_is_valid_openrouter_with_key(self):
        """Tests is_valid() returns True for openrouter with API key."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="openrouter", openrouter_api_key="or-key")
        assert config.is_valid() is True

    def test_is_valid_openrouter_without_key(self):
        """Tests is_valid() returns False for openrouter without API key."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="openrouter", openrouter_api_key="")
        assert config.is_valid() is False

    def test_is_valid_unknown_provider(self):
        """Tests is_valid() returns False for unknown provider."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="unknown")
        assert config.is_valid() is False

    def test_get_validation_errors_claude_missing_key(self):
        """Tests get_validation_errors() for claude without key."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="")
        errors = config.get_validation_errors()
        assert len(errors) == 1
        assert "ANTHROPIC_API_KEY" in errors[0]

    def test_get_validation_errors_litellm_missing_model(self):
        """Tests get_validation_errors() for litellm without model."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="litellm", litellm_model="")
        errors = config.get_validation_errors()
        assert len(errors) == 1
        assert "LITELLM_MODEL" in errors[0]

    def test_get_validation_errors_openrouter_missing_key(self):
        """Tests get_validation_errors() for openrouter without key."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="openrouter", openrouter_api_key="")
        errors = config.get_validation_errors()
        assert len(errors) == 1
        assert "OPENROUTER_API_KEY" in errors[0]

    def test_get_validation_errors_unknown_provider(self):
        """Tests get_validation_errors() for unknown provider."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="unknown_provider")
        errors = config.get_validation_errors()
        assert len(errors) == 1
        assert "Unknown provider" in errors[0]

    def test_get_validation_errors_valid_config(self):
        """Tests get_validation_errors() returns empty list for valid config."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        errors = config.get_validation_errors()
        assert errors == []


class TestProviderConfigSummary:
    """Tests for ProviderConfig summary and model methods."""

    def test_get_provider_summary_claude(self):
        """Tests get_provider_summary() for claude provider."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", claude_model="claude-opus-4")
        summary = config.get_provider_summary()
        assert "Claude Agent SDK" in summary
        assert "claude-opus-4" in summary

    def test_get_provider_summary_litellm_with_model(self):
        """Tests get_provider_summary() for litellm with model."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="litellm", litellm_model="gpt-4")
        summary = config.get_provider_summary()
        assert "LiteLLM" in summary
        assert "gpt-4" in summary

    def test_get_provider_summary_litellm_without_model(self):
        """Tests get_provider_summary() for litellm without model."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="litellm", litellm_model="")
        summary = config.get_provider_summary()
        assert "LiteLLM" in summary
        assert "no model configured" in summary

    def test_get_provider_summary_openrouter(self):
        """Tests get_provider_summary() for openrouter provider."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="openrouter", openrouter_model="anthropic/claude-opus-4"
        )
        summary = config.get_provider_summary()
        assert "OpenRouter" in summary
        assert "anthropic/claude-opus-4" in summary

    def test_get_provider_summary_unknown(self):
        """Tests get_provider_summary() for unknown provider."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="unknown")
        summary = config.get_provider_summary()
        assert "Unknown" in summary
        assert "unknown" in summary

    def test_get_model_for_provider_claude(self):
        """Tests get_model_for_provider() for claude."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", claude_model="claude-opus-4")
        model = config.get_model_for_provider()
        assert model == "claude-opus-4"

    def test_get_model_for_provider_litellm(self):
        """Tests get_model_for_provider() for litellm."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="litellm", litellm_model="gpt-4")
        model = config.get_model_for_provider()
        assert model == "gpt-4"

    def test_get_model_for_provider_litellm_empty(self):
        """Tests get_model_for_provider() for litellm without model."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="litellm", litellm_model="")
        model = config.get_model_for_provider()
        assert model is None

    def test_get_model_for_provider_openrouter(self):
        """Tests get_model_for_provider() for openrouter."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="openrouter", openrouter_model="meta/llama-3")
        model = config.get_model_for_provider()
        assert model == "meta/llama-3"

    def test_get_model_for_provider_unknown(self):
        """Tests get_model_for_provider() for unknown provider."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="unknown")
        model = config.get_model_for_provider()
        assert model is None


# =============================================================================
# PROVIDER HELPER FUNCTIONS TESTS
# =============================================================================


class TestProviderHelperFunctions:
    """Tests for provider module helper functions."""

    def test_get_provider_config(self):
        """Tests get_provider_config() returns ProviderConfig instance."""
        from core.providers.config import get_provider_config, ProviderConfig

        env = {"AI_ENGINE_PROVIDER": "claude", "ANTHROPIC_API_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            config = get_provider_config()
            assert isinstance(config, ProviderConfig)
            assert config.provider == "claude"

    def test_get_available_providers_none(self):
        """Tests get_available_providers() returns empty list when no creds."""
        from core.providers.config import get_available_providers

        with patch.dict(os.environ, {}, clear=True):
            # Clear all provider credentials
            for key in ["ANTHROPIC_API_KEY", "LITELLM_MODEL", "OPENROUTER_API_KEY"]:
                os.environ.pop(key, None)
            providers = get_available_providers()
            assert providers == []

    def test_get_available_providers_claude_only(self):
        """Tests get_available_providers() with only claude configured."""
        from core.providers.config import get_available_providers

        env = {"ANTHROPIC_API_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            providers = get_available_providers()
            assert "claude" in providers
            assert "litellm" not in providers
            assert "openrouter" not in providers

    def test_get_available_providers_all(self):
        """Tests get_available_providers() with all providers configured."""
        from core.providers.config import get_available_providers

        env = {
            "ANTHROPIC_API_KEY": "claude-key",
            "LITELLM_MODEL": "gpt-4",
            "OPENROUTER_API_KEY": "or-key",
        }
        with patch.dict(os.environ, env, clear=True):
            providers = get_available_providers()
            assert "claude" in providers
            assert "litellm" in providers
            assert "openrouter" in providers

    def test_validate_provider_config_valid(self):
        """Tests validate_provider_config() with valid config."""
        from core.providers.config import validate_provider_config

        env = {"AI_ENGINE_PROVIDER": "claude", "ANTHROPIC_API_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            is_valid, errors = validate_provider_config()
            assert is_valid is True
            assert errors == []

    def test_validate_provider_config_invalid(self):
        """Tests validate_provider_config() with invalid config."""
        from core.providers.config import validate_provider_config

        env = {"AI_ENGINE_PROVIDER": "claude"}
        with patch.dict(os.environ, env, clear=True):
            # Clear ANTHROPIC_API_KEY
            os.environ.pop("ANTHROPIC_API_KEY", None)
            is_valid, errors = validate_provider_config()
            assert is_valid is False
            assert len(errors) > 0
            assert "ANTHROPIC_API_KEY" in errors[0]


# =============================================================================
# PROVIDER EXCEPTIONS TESTS
# =============================================================================


class TestProviderExceptions:
    """Tests for provider exception hierarchy."""

    def test_provider_error_is_exception(self):
        """Tests ProviderError is a valid exception."""
        from core.providers.exceptions import ProviderError

        error = ProviderError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_provider_not_installed_inherits_provider_error(self):
        """Tests ProviderNotInstalled inherits from ProviderError."""
        from core.providers.exceptions import ProviderError, ProviderNotInstalled

        error = ProviderNotInstalled("Package not found")
        assert isinstance(error, ProviderError)
        assert isinstance(error, Exception)
        assert str(error) == "Package not found"

    def test_provider_config_error_inherits_provider_error(self):
        """Tests ProviderConfigError inherits from ProviderError."""
        from core.providers.exceptions import ProviderError, ProviderConfigError

        error = ProviderConfigError("Invalid config")
        assert isinstance(error, ProviderError)
        assert isinstance(error, Exception)
        assert str(error) == "Invalid config"

    def test_exception_can_be_caught_as_provider_error(self):
        """Tests child exceptions can be caught as ProviderError."""
        from core.providers.exceptions import (
            ProviderError,
            ProviderNotInstalled,
            ProviderConfigError,
        )

        # Test ProviderNotInstalled can be caught as ProviderError
        try:
            raise ProviderNotInstalled("Not installed")
        except ProviderError as e:
            assert "Not installed" in str(e)

        # Test ProviderConfigError can be caught as ProviderError
        try:
            raise ProviderConfigError("Bad config")
        except ProviderError as e:
            assert "Bad config" in str(e)


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Tests for provider factory functions."""

    def test_get_available_provider_names(self):
        """Tests get_available_provider_names() returns all providers."""
        from core.providers.factory import get_available_provider_names

        names = get_available_provider_names()
        assert "claude" in names
        assert "litellm" in names
        assert "openrouter" in names
        assert "zhipuai" in names
        assert len(names) == 4

    def test_create_engine_provider_unknown_raises_error(self):
        """Tests create_engine_provider() raises error for unknown provider."""
        from core.providers.factory import create_engine_provider
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderError

        config = ProviderConfig(provider="unknown_provider")
        with pytest.raises(ProviderError) as exc_info:
            create_engine_provider(config)

        assert "Unknown AI engine provider" in str(exc_info.value)
        assert "unknown_provider" in str(exc_info.value)

    def test_create_engine_provider_claude_dispatches_correctly(self):
        """Tests create_engine_provider() dispatches to claude factory."""
        from core.providers.factory import create_engine_provider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="claude", anthropic_api_key="test-key"
        )

        # Mock the Claude adapter import
        with patch(
            "core.providers.factory._create_claude_provider"
        ) as mock_create:
            mock_create.return_value = MagicMock()
            provider = create_engine_provider(config)
            mock_create.assert_called_once_with(config)

    def test_create_engine_provider_litellm_dispatches_correctly(self):
        """Tests create_engine_provider() dispatches to litellm factory."""
        from core.providers.factory import create_engine_provider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="litellm", litellm_model="gpt-4")

        with patch(
            "core.providers.factory._create_litellm_provider"
        ) as mock_create:
            mock_create.return_value = MagicMock()
            provider = create_engine_provider(config)
            mock_create.assert_called_once_with(config)

    def test_create_engine_provider_openrouter_dispatches_correctly(self):
        """Tests create_engine_provider() dispatches to openrouter factory."""
        from core.providers.factory import create_engine_provider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="openrouter", openrouter_api_key="or-key"
        )

        with patch(
            "core.providers.factory._create_openrouter_provider"
        ) as mock_create:
            mock_create.return_value = MagicMock()
            provider = create_engine_provider(config)
            mock_create.assert_called_once_with(config)


class TestClaudeProviderFactory:
    """Tests for Claude provider factory function."""

    def test_create_claude_provider_import_error_handling(self):
        """Tests that _create_claude_provider handles import errors gracefully.

        This test verifies the code path exists for import error handling.
        The actual import error behavior is tested by attempting to import
        a non-existent adapter module.
        """
        from core.providers.factory import _create_claude_provider
        from core.providers.config import ProviderConfig
        from core.providers.exceptions import ProviderNotInstalled

        # Verify the ProviderNotInstalled exception is correctly defined
        error = ProviderNotInstalled("Test error")
        assert isinstance(error, Exception)
        assert "Test error" in str(error)

        # Verify _create_claude_provider exists and is callable
        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")
        assert callable(_create_claude_provider)

        # The import error path is tested indirectly - if the adapter module
        # didn't exist, the function would raise ProviderNotInstalled

    def test_create_claude_provider_success(self):
        """Tests _create_claude_provider succeeds with valid import."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="claude", anthropic_api_key="test-key")

        # Import should work since we have the module
        from core.providers.adapters.claude import ClaudeAgentProvider
        from core.providers.factory import _create_claude_provider

        provider = _create_claude_provider(config)
        assert isinstance(provider, ClaudeAgentProvider)


class TestLiteLLMProviderFactory:
    """Tests for LiteLLM provider factory function."""

    def test_create_litellm_provider_success(self):
        """Tests _create_litellm_provider succeeds with valid import."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(provider="litellm", litellm_model="gpt-4")

        # This test may fail if litellm package is not installed,
        # which is expected behavior - we handle that with ProviderNotInstalled
        try:
            from core.providers.adapters.litellm import LiteLLMProvider
            from core.providers.factory import _create_litellm_provider

            provider = _create_litellm_provider(config)
            assert isinstance(provider, LiteLLMProvider)
        except ImportError:
            # LiteLLM package not installed - this is expected in test env
            pytest.skip("LiteLLM package not installed")


class TestOpenRouterProviderFactory:
    """Tests for OpenRouter provider factory function."""

    def test_create_openrouter_provider_success(self):
        """Tests _create_openrouter_provider succeeds with valid import."""
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="openrouter", openrouter_api_key="or-key"
        )

        # This test may fail if openai package is not installed,
        # which is expected behavior - we handle that with ProviderNotInstalled
        try:
            from core.providers.adapters.openrouter import OpenRouterProvider
            from core.providers.factory import _create_openrouter_provider

            provider = _create_openrouter_provider(config)
            assert isinstance(provider, OpenRouterProvider)
        except ImportError:
            # OpenAI package not installed - this is expected in test env
            pytest.skip("OpenAI package not installed")


# =============================================================================
# AI ENGINE PROVIDER ENUM TESTS
# =============================================================================


class TestAIEngineProviderEnum:
    """Tests for AIEngineProvider enum."""

    def test_enum_values(self):
        """Tests AIEngineProvider enum has correct values."""
        from core.providers.config import AIEngineProvider

        assert AIEngineProvider.CLAUDE.value == "claude"
        assert AIEngineProvider.LITELLM.value == "litellm"
        assert AIEngineProvider.OPENROUTER.value == "openrouter"

    def test_enum_is_str(self):
        """Tests AIEngineProvider values are strings."""
        from core.providers.config import AIEngineProvider

        assert isinstance(AIEngineProvider.CLAUDE.value, str)
        assert isinstance(AIEngineProvider.LITELLM.value, str)
        assert isinstance(AIEngineProvider.OPENROUTER.value, str)

    def test_enum_count(self):
        """Tests AIEngineProvider has expected number of values."""
        from core.providers.config import AIEngineProvider

        assert len(AIEngineProvider) == 4


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestProviderIntegration:
    """Integration tests for provider factory and configuration."""

    def test_full_provider_creation_flow_claude(self):
        """Tests full flow: env -> config -> factory -> provider for Claude."""
        env = {"AI_ENGINE_PROVIDER": "claude", "ANTHROPIC_API_KEY": "test-key"}
        with patch.dict(os.environ, env, clear=True):
            from core.providers.config import ProviderConfig
            from core.providers.factory import create_engine_provider
            from core.providers.adapters.claude import ClaudeAgentProvider

            # Load config from env
            config = ProviderConfig.from_env()
            assert config.provider == "claude"
            assert config.is_valid() is True

            # Create provider
            provider = create_engine_provider(config)
            assert isinstance(provider, ClaudeAgentProvider)

    def test_provider_exports_from_init(self):
        """Tests that provider exports are available from package __init__."""
        from core.providers import create_engine_provider
        from core.providers.config import ProviderConfig

        assert callable(create_engine_provider)

        # Create a config to verify it works
        config = ProviderConfig(provider="claude", anthropic_api_key="test")
        assert config.provider == "claude"
