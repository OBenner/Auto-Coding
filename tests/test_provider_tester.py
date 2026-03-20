"""
Unit Tests for Provider Tester
================================

Tests for apps/backend/core/provider_tester.py
"""

import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from apps.backend.core.provider_tester import (
    check_provider_connection,
    ProviderTestResult,
    get_provider_from_env,
    check_all_configured_providers,
    _test_openai,
    _test_anthropic,
    _test_ollama,
)


class TestProviderTestResult:
    """Tests for ProviderTestResult dataclass."""

    def test_provider_test_result_creation(self):
        """Test creating a ProviderTestResult."""
        result = ProviderTestResult(
            success=True,
            message="Connection successful",
            provider="openai",
            fix_command="Set API key",
            error_details="None"
        )

        assert result.success is True
        assert result.message == "Connection successful"
        assert result.provider == "openai"
        assert result.fix_command == "Set API key"
        assert result.error_details == "None"


class TestCheckProviderConnection:
    """Tests for check_provider_connection() function."""

    def test_openai_provider_success(self, monkeypatch):
        """Test OpenAI provider connection with mock successful connection."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        # Mock the async function at the module level
        async def mock_test_openai_async(*args, **kwargs):
            return ProviderTestResult(
                success=True,
                message="OpenAI connection successful",
                provider="openai"
            )

        with patch("apps.backend.core.provider_tester.check_provider_connection_async", side_effect=mock_test_openai_async):
            result = check_provider_connection("openai", api_key="sk-test-key")

            assert result.success is True
            assert result.provider == "openai"

    def test_anthropic_provider_auth_failure(self, monkeypatch):
        """Test Anthropic provider with mock auth failure."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-invalid")

        # Mock the async function at the module level
        async def mock_test_anthropic_async(*args, **kwargs):
            return ProviderTestResult(
                success=False,
                message="Anthropic authentication failed - invalid API key",
                provider="anthropic",
                fix_command="Check your ANTHROPIC_API_KEY is valid",
                error_details="Invalid API key"
            )

        with patch("apps.backend.core.provider_tester.check_provider_connection_async", side_effect=mock_test_anthropic_async):
            result = check_provider_connection("anthropic", api_key="sk-ant-invalid")

            assert result.success is False
            assert "authentication failed" in result.message.lower()
            assert result.fix_command is not None

    def test_unsupported_provider_returns_error(self):
        """Test unsupported provider returns appropriate error."""
        result = check_provider_connection("unsupported_provider")

        assert result.success is False
        assert "Unknown provider" in result.message
        assert result.provider == "unsupported_provider"

    def test_provider_test_result_has_fix_command(self):
        """Test ProviderTestResult includes fix command on failure."""
        result = ProviderTestResult(
            success=False,
            message="Connection failed",
            provider="openai",
            fix_command="Set OPENAI_API_KEY in your .env file"
        )

        assert result.fix_command is not None
        assert "OPENAI_API_KEY" in result.fix_command


class TestCheckAllConfiguredProviders:
    """Tests for check_all_configured_providers() function."""

    def test_auto_detects_from_env(self, monkeypatch):
        """Test check_all_configured_providers() auto-detects from env variables."""
        # Set env vars for multiple providers
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        # Mock the actual test functions
        async def mock_test(*args, **kwargs):
            return ProviderTestResult(
                success=True,
                message="Test passed",
                provider="test"
            )

        with patch("apps.backend.core.provider_tester._test_openai", side_effect=mock_test):
            with patch("apps.backend.core.provider_tester._test_anthropic", side_effect=mock_test):
                results = check_all_configured_providers()

                # Should have results for both providers
                assert "openai" in results
                assert "anthropic" in results

    def test_no_providers_configured(self, monkeypatch):
        """Test when no providers are configured."""
        # Clear all provider env vars
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "AZURE_OPENAI_API_KEY", "OLLAMA_BASE_URL", "OLLAMA_LLM_MODEL", "OPENROUTER_API_KEY", "VOYAGE_API_KEY"]:
            monkeypatch.delenv(key, raising=False)

        results = check_all_configured_providers()

        # Should return empty dict when no providers configured
        assert results == {}


class TestGetProviderFromEnv:
    """Tests for get_provider_from_env() function."""

    def test_detect_openai_from_env(self, monkeypatch):
        """Test detecting OpenAI from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        provider = get_provider_from_env()

        assert provider == "openai"

    def test_detect_anthropic_from_env(self, monkeypatch):
        """Test detecting Anthropic from environment."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        provider = get_provider_from_env()

        assert provider == "anthropic"

    def test_detect_google_from_env(self, monkeypatch):
        """Test detecting Google AI from environment."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "google-test")

        provider = get_provider_from_env()

        assert provider == "google"

    def test_no_provider_detected(self, monkeypatch):
        """Test when no provider is configured."""
        # Clear all provider env vars
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "AZURE_OPENAI_API_KEY", "OLLAMA_BASE_URL"]:
            monkeypatch.delenv(key, raising=False)

        provider = get_provider_from_env()

        assert provider is None


class TestProviderSpecificTests:
    """Tests for provider-specific test functions."""

    @pytest.mark.asyncio
    async def test_openai_missing_api_key(self, monkeypatch):
        """Test OpenAI test when API key is missing."""
        # Clear env var
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        result = await _test_openai(api_key=None)

        assert result.success is False
        # Could be either "API key not provided" or "package not installed"
        assert ("API key not provided" in result.message or "package not installed" in result.message.lower())
        assert result.provider == "openai"
        assert result.fix_command is not None

    @pytest.mark.asyncio
    async def test_openai_missing_package(self):
        """Test OpenAI test when openai package is not installed."""
        with patch.dict("sys.modules", {"openai": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module named 'openai'")):
                result = await _test_openai(api_key="sk-test")

                assert result.success is False
                assert "package not installed" in result.message.lower()
                assert "pip install openai" in result.fix_command

    @pytest.mark.asyncio
    async def test_anthropic_missing_api_key(self):
        """Test Anthropic test when API key is missing."""
        result = await _test_anthropic(api_key=None)

        assert result.success is False
        assert "API key not provided" in result.message
        assert result.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_ollama_connection_success(self):
        """Test Ollama connection with mocked successful response."""
        import urllib.request
        import json

        # Mock successful Ollama API response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "models": [
                {"name": "llama2"},
                {"name": "codellama"}
            ]
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = await _test_ollama(base_url="http://localhost:11434")

            assert result.success is True
            assert "Ollama connection successful" in result.message

    @pytest.mark.asyncio
    async def test_ollama_connection_failure(self):
        """Test Ollama connection when server is not reachable."""
        import urllib.error

        # Mock URLError (server not reachable)
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            result = await _test_ollama(base_url="http://localhost:11434")

            assert result.success is False
            assert "Cannot connect to Ollama" in result.message
            assert "ollama serve" in result.fix_command.lower()

    @pytest.mark.asyncio
    async def test_ollama_model_not_found(self):
        """Test Ollama when requested model is not available."""
        import urllib.request
        import json

        # Mock Ollama API response with different models
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "models": [
                {"name": "llama2"}
            ]
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = lambda s, *args: None

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = await _test_ollama(base_url="http://localhost:11434", model="missing-model")

            assert result.success is False
            assert "model not found" in result.message.lower()
            assert "ollama pull" in result.fix_command.lower()
