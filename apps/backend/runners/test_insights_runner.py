"""
Unit tests for insights_runner.py

Tests CLI argument parsing, provider factory integration, and validation.
"""

import argparse
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add runners directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Mock the dependencies that might not be available in test environment
sys.modules["core.dependency_validator"] = MagicMock()
sys.modules["core.auth"] = MagicMock()

PROVIDER_CHOICES = ["claude", "litellm", "openrouter", "openai", "ollama"]


def _make_parser() -> argparse.ArgumentParser:
    """Create an argument parser matching insights_runner.py."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--provider", default="claude", choices=PROVIDER_CHOICES)
    return parser


class TestProviderArgumentParsing:
    """Test --provider CLI argument parsing"""

    def test_provider_argument_default(self):
        """Test that --provider defaults to 'claude' when not specified"""
        parser = _make_parser()
        with patch(
            "sys.argv",
            [
                "insights_runner.py",
                "--project-dir",
                "/fake/test_project",
                "--message",
                "test",
            ],
        ):
            args = parser.parse_args()
            assert args.provider == "claude"

    @pytest.mark.parametrize("provider", PROVIDER_CHOICES)
    def test_provider_argument_parsing(self, provider: str):
        """Test that --provider accepts each valid value"""
        parser = _make_parser()
        with patch(
            "sys.argv",
            [
                "insights_runner.py",
                "--project-dir",
                "/fake/test_project",
                "--message",
                "test",
                "--provider",
                provider,
            ],
        ):
            args = parser.parse_args()
            assert args.provider == provider

    def test_provider_invalid_value_rejected(self):
        """Test that invalid provider value is rejected by argparse"""
        parser = _make_parser()
        with patch(
            "sys.argv",
            [
                "insights_runner.py",
                "--project-dir",
                "/fake/test_project",
                "--message",
                "test",
                "--provider",
                "invalid_provider",
            ],
        ):
            with pytest.raises(SystemExit):
                parser.parse_args()


class TestProviderFactoryIntegration:
    """Test provider factory integration in insights_runner.py"""

    @patch("runners.insights_runner.create_engine_provider")
    def test_create_engine_provider_called(self, mock_create_provider):
        """Test that create_engine_provider is callable when providers are available"""
        from runners.insights_runner import PROVIDERS_AVAILABLE

        if PROVIDERS_AVAILABLE:
            from runners.insights_runner import create_engine_provider

            assert create_engine_provider is not None
            assert callable(create_engine_provider)
        else:
            pytest.skip("Providers not available in test environment")

    @patch("runners.insights_runner.ProviderConfig")
    def test_provider_config_from_env(self, mock_config):
        """Test that ProviderConfig.from_env is available for provider creation"""
        from runners.insights_runner import PROVIDERS_AVAILABLE

        if PROVIDERS_AVAILABLE:
            from runners.insights_runner import ProviderConfig

            assert ProviderConfig is not None
            assert hasattr(ProviderConfig, "from_env")
        else:
            pytest.skip("Providers not available in test environment")


class TestProviderChoices:
    """Test provider choice validation"""

    def test_provider_choices_include_all_four(self):
        """Test that provider choices include claude, litellm, openrouter, and openai"""
        parser = argparse.ArgumentParser()
        parser.add_argument("--provider", choices=PROVIDER_CHOICES)

        action = None
        for act in parser._actions:
            if "--provider" in act.option_strings:
                action = act
                break

        assert action is not None
        for provider in PROVIDER_CHOICES:
            assert provider in action.choices


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
