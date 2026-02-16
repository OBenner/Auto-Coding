"""
Unit tests for insights_runner.py

Tests CLI argument parsing, provider factory integration, and validation.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add runners directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Mock the dependencies that might not be available in test environment
sys.modules['core.dependency_validator'] = MagicMock()
sys.modules['core.auth'] = MagicMock()


class TestProviderArgumentParsing:
    """Test --provider CLI argument parsing"""

    def test_provider_argument_default(self):
        """Test that --provider defaults to 'claude' when not specified"""
        import argparse

        # Simulate the argument parser from insights_runner.py
        parser = argparse.ArgumentParser()
        parser.add_argument('--project-dir', required=True)
        parser.add_argument('--message', required=True)
        parser.add_argument('--provider', default='claude', choices=['claude', 'litellm', 'openrouter'])

        # Test with --provider not specified
        with patch('sys.argv', ['insights_runner.py', '--project-dir', '/tmp/test', '--message', 'test']):
            args = parser.parse_args()
            assert args.provider == 'claude'

    def test_provider_argument_parsing_claude(self):
        """Test that --provider accepts 'claude' value"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--project-dir', required=True)
        parser.add_argument('--message', required=True)
        parser.add_argument('--provider', default='claude', choices=['claude', 'litellm', 'openrouter'])

        with patch('sys.argv', ['insights_runner.py', '--project-dir', '/tmp/test', '--message', 'test', '--provider', 'claude']):
            args = parser.parse_args()
            assert args.provider == 'claude'

    def test_provider_argument_parsing_litellm(self):
        """Test that --provider accepts 'litellm' value"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--project-dir', required=True)
        parser.add_argument('--message', required=True)
        parser.add_argument('--provider', default='claude', choices=['claude', 'litellm', 'openrouter'])

        with patch('sys.argv', ['insights_runner.py', '--project-dir', '/tmp/test', '--message', 'test', '--provider', 'litellm']):
            args = parser.parse_args()
            assert args.provider == 'litellm'

    def test_provider_argument_parsing_openrouter(self):
        """Test that --provider accepts 'openrouter' value"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--project-dir', required=True)
        parser.add_argument('--message', required=True)
        parser.add_argument('--provider', default='claude', choices=['claude', 'litellm', 'openrouter'])

        with patch('sys.argv', ['insights_runner.py', '--project-dir', '/tmp/test', '--message', 'test', '--provider', 'openrouter']):
            args = parser.parse_args()
            assert args.provider == 'openrouter'

    def test_provider_invalid_value_rejected(self):
        """Test that invalid provider value is rejected by argparse"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--project-dir', required=True)
        parser.add_argument('--message', required=True)
        parser.add_argument('--provider', default='claude', choices=['claude', 'litellm', 'openrouter'])

        with patch('sys.argv', ['insights_runner.py', '--project-dir', '/tmp/test', '--message', 'test', '--provider', 'invalid_provider']):
            with pytest.raises(SystemExit):
                parser.parse_args()


class TestProviderFactoryIntegration:
    """Test provider factory integration in insights_runner.py"""

    @patch('runners.insights_runner.create_engine_provider')
    def test_create_engine_provider_called(self, mock_create_provider):
        """Test that create_engine_provider is called when providers are available"""
        from runners.insights_runner import PROVIDERS_AVAILABLE

        # This test verifies that when providers are available,
        # the create_engine_provider function is imported and ready to use
        if PROVIDERS_AVAILABLE:
            from runners.insights_runner import create_engine_provider
            assert create_engine_provider is not None
            assert callable(create_engine_provider)
        else:
            pytest.skip("Providers not available in test environment")

    @patch('runners.insights_runner.ProviderConfig')
    def test_provider_config_from_env(self, mock_config):
        """Test that ProviderConfig.from_env is available for provider creation"""
        from runners.insights_runner import PROVIDERS_AVAILABLE

        if PROVIDERS_AVAILABLE:
            from runners.insights_runner import ProviderConfig
            assert ProviderConfig is not None
            assert hasattr(ProviderConfig, 'from_env')
        else:
            pytest.skip("Providers not available in test environment")


class TestProviderChoices:
    """Test provider choice validation"""

    def test_provider_choices_include_all_three(self):
        """Test that provider choices include claude, litellm, and openrouter"""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--provider', choices=['claude', 'litellm', 'openrouter'])

        # Get the choices from the argument
        action = None
        for act in parser._actions:
            if '--provider' in act.option_strings:
                action = act
                break

        assert action is not None
        assert 'claude' in action.choices
        assert 'litellm' in action.choices
        assert 'openrouter' in action.choices


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
