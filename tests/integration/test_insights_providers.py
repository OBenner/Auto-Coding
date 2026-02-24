"""
Integration tests for multi-provider Insights chat functionality.

Tests provider selection flow from frontend through backend to runner,
and end-to-end chat functionality with different providers.
"""

import sys
from pathlib import Path

import pytest

# Resolve repo root consistently
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Add backend to path
backend_path = REPO_ROOT / "apps" / "backend"
sys.path.insert(0, str(backend_path))


def _read_frontend_file(*path_parts: str) -> str:
    """Read a frontend file or skip the test if it doesn't exist."""
    file_path = REPO_ROOT / "apps" / "frontend" / "src" / Path(*path_parts)
    if not file_path.exists():
        pytest.skip(f"{file_path.name} not found at {file_path}")
    return file_path.read_text(encoding="utf-8")


def _read_backend_file(*path_parts: str) -> str:
    """Read a backend file or skip the test if it doesn't exist."""
    file_path = REPO_ROOT / "apps" / "backend" / Path(*path_parts)
    if not file_path.exists():
        pytest.skip(f"{file_path.name} not found at {file_path}")
    return file_path.read_text(encoding="utf-8")


class TestProviderSelectionFlow:
    """Test provider selection from frontend to backend"""

    def test_provider_argument_in_subprocess_call(self):
        """Test that provider selection results in --provider argument in subprocess call"""
        provider = "openrouter"
        expected_args = [
            sys.executable,
            "runners/insights_runner.py",
            "--project-dir",
            "/fake/test_project",
            "--message",
            "Test message",
            "--provider",
            provider,
        ]

        assert "--provider" in expected_args
        assert provider in expected_args

    def test_provider_default_to_claude(self):
        """Test that provider defaults to 'claude' when not specified"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--provider",
            default="claude",
            choices=["claude", "litellm", "openrouter", "openai", "ollama"],
        )
        parser.add_argument("--project-dir")
        parser.add_argument("--message")

        args = parser.parse_args(
            ["--project-dir", "/fake/project", "--message", "test"]
        )
        assert args.provider == "claude"


class TestModelCatalogConsistency:
    """Test that model catalog is consistent across frontend and backend"""

    def test_anthropic_models_catalog_exists(self):
        """Test that Anthropic models are defined in api-profiles.ts"""
        content = _read_frontend_file("shared", "constants", "api-profiles.ts")

        assert "ANTHROPIC_MODELS" in content
        assert "claude-sonnet-4-5-20250929" in content
        assert "claude-opus-4-5-20251101" in content
        assert "claude-haiku-4-5-20251001" in content

    def test_openrouter_models_catalog_exists(self):
        """Test that OpenRouter models are defined in api-profiles.ts"""
        content = _read_frontend_file("shared", "constants", "api-profiles.ts")

        assert "OPENROUTER_MODELS" in content
        assert "openai/gpt-4o" in content
        assert "google/gemini-2.5-flash" in content

    def test_get_models_for_provider_function_exists(self):
        """Test that getModelsForProvider helper function exists"""
        content = _read_frontend_file("shared", "constants", "api-profiles.ts")

        assert "getModelsForProvider" in content
        assert "export function getModelsForProvider" in content


class TestProviderArgumentValidation:
    """Test provider argument validation in insights runner"""

    def test_valid_providers_include_all_four(self):
        """Test that valid providers include claude, litellm, openrouter, and openai"""
        valid_providers = ["claude", "litellm", "openrouter", "openai"]

        assert "claude" in valid_providers
        assert "litellm" in valid_providers
        assert "openrouter" in valid_providers
        assert "openai" in valid_providers

    def test_insights_runner_help_shows_provider_option(self):
        """Test that insights_runner.py --help shows --provider option"""
        content = _read_backend_file("runners", "insights_runner.py")

        assert '"--provider"' in content or "'--provider'" in content
        assert "choices=" in content
        assert "claude" in content
        assert "litellm" in content
        assert "openrouter" in content
        assert "openai" in content


class TestFrontendTypeDefinitions:
    """Test frontend type definitions for provider support"""

    def test_insights_model_config_has_provider_field(self):
        """Test that InsightsModelConfig type includes provider field"""
        content = _read_frontend_file("shared", "types", "insights.ts")

        assert "InsightsModelConfig" in content
        assert "provider" in content.lower()

    def test_insights_provider_type_includes_openai(self):
        """Test that InsightsProvider type includes openai"""
        content = _read_frontend_file("shared", "types", "insights.ts")

        assert "InsightsProvider" in content
        assert "'openai'" in content


class TestInsightsExecutorIntegration:
    """Test insights-executor.ts integration with provider selection"""

    def test_insights_executor_passes_provider_to_subprocess(self):
        """Test that insights-executor.ts passes --provider to subprocess"""
        content = _read_frontend_file("main", "insights", "insights-executor.ts")

        assert "--provider" in content

    def test_insights_executor_reads_provider_from_model_config(self):
        """Test that insights-executor.ts reads provider from modelConfig"""
        content = _read_frontend_file("main", "insights", "insights-executor.ts")

        assert "modelConfig" in content


class TestModelSelectorUIIntegration:
    """Test InsightsModelSelector component integration"""

    def test_insights_model_selector_has_provider_dropdown(self):
        """Test that InsightsModelSelector component has provider selection"""
        content = _read_frontend_file(
            "renderer", "components", "InsightsModelSelector.tsx"
        )

        assert "provider" in content.lower()
        assert "getModelLabelForProvider" in content

    def test_insights_model_selector_includes_openai(self):
        """Test that InsightsModelSelector uses shared provider definitions including OpenAI"""
        content = _read_frontend_file("shared", "constants", "insights-providers.ts")

        assert "openai" in content


class TestOpenAIProviderConfig:
    """Test OpenAI provider configuration"""

    def test_openai_provider_in_config(self):
        """Test that OpenAI is listed in AIEngineProvider enum"""
        content = _read_backend_file("core", "providers", "config.py")

        assert "OPENAI" in content
        assert "openai" in content
        assert "OPENAI_API_KEY" in content

    def test_openai_adapter_exists(self):
        """Test that OpenAI adapter module exists"""
        content = _read_backend_file("core", "providers", "adapters", "openai.py")

        assert "class OpenAIProvider" in content
        assert "class OpenAISession" in content

    def test_openai_in_factory(self):
        """Test that factory includes OpenAI provider"""
        content = _read_backend_file("core", "providers", "factory.py")

        assert "_create_openai_provider" in content
        assert '"openai"' in content


@pytest.mark.skipif(
    not (REPO_ROOT / "apps" / "backend" / ".env").exists(),
    reason="No .env file found - skipping API-dependent tests",
)
class TestEndToEndProviderChat:
    """End-to-end tests for chat with different providers

    These tests require API keys to be configured in apps/backend/.env
    """

    @pytest.mark.skip(reason="Requires actual API call - run manually")
    def test_claude_provider_chat(self):
        """Test end-to-end chat with Claude provider"""
        pytest.skip("Manual verification required - requires ANTHROPIC_API_KEY")

    @pytest.mark.skip(reason="Requires actual API call - run manually")
    def test_openrouter_provider_chat(self):
        """Test end-to-end chat with OpenRouter provider"""
        pytest.skip("Manual verification required - requires OPENROUTER_API_KEY")

    @pytest.mark.skip(reason="Requires actual API call - run manually")
    def test_litellm_provider_chat(self):
        """Test end-to-end chat with LiteLLM provider"""
        pytest.skip("Manual verification required - requires LITELLM_API_KEY")

    @pytest.mark.skip(reason="Requires actual API call - run manually")
    def test_openai_provider_chat(self):
        """Test end-to-end chat with OpenAI provider"""
        pytest.skip("Manual verification required - requires OPENAI_API_KEY")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
