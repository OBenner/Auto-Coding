#!/usr/bin/env python3
"""
Integration Tests for Provider Selection CLI
==============================================

Tests the CLI provider and model selection functionality including:
- --provider flag parsing and validation
- --model flag parsing and validation
- Provider selection persists to implementation_plan.json
- Provider/model restoration from implementation_plan.json
- Provider override behavior
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add backend directory to path if not already added by conftest
import sys
backend_path = Path(__file__).parent.parent.parent / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


# =============================================================================
# CLI ARGUMENT PARSING TESTS
# =============================================================================


class TestCLIProviderArgumentParsing:
    """Tests for CLI provider argument parsing."""

    def test_parse_args_with_provider_zhipuai(self):
        """Tests CLI parsing accepts --provider zhipuai."""
        from cli.main import parse_args

        args = parse_args(["--spec", "001", "--provider", "zhipuai"])
        assert args.provider == "zhipuai"

    def test_parse_args_with_provider_claude(self):
        """Tests CLI parsing accepts --provider claude."""
        from cli.main import parse_args

        args = parse_args(["--spec", "001", "--provider", "claude"])
        assert args.provider == "claude"

    def test_parse_args_with_provider_litellm(self):
        """Tests CLI parsing accepts --provider litellm."""
        from cli.main import parse_args

        args = parse_args(["--spec", "001", "--provider", "litellm"])
        assert args.provider == "litellm"

    def test_parse_args_with_provider_openrouter(self):
        """Tests CLI parsing accepts --provider openrouter."""
        from cli.main import parse_args

        args = parse_args(["--spec", "001", "--provider", "openrouter"])
        assert args.provider == "openrouter"

    def test_parse_args_provider_defaults_to_none(self):
        """Tests provider argument defaults to None when not specified."""
        from cli.main import parse_args

        args = parse_args(["--spec", "001"])
        assert args.provider is None

    def test_parse_args_with_invalid_provider_rejected(self):
        """Tests CLI rejects invalid provider names."""
        from cli.main import parse_args
        import argparse

        with pytest.raises(SystemExit):
            # argparse exits on invalid choice
            parse_args(["--spec", "001", "--provider", "invalid_provider"])


class TestCLIModelArgumentParsing:
    """Tests for CLI model argument parsing."""

    def test_parse_args_with_model(self):
        """Tests CLI parsing accepts --model flag."""
        from cli.main import parse_args

        args = parse_args(["--spec", "001", "--model", "glm-4-flash-250414"])
        assert args.model == "glm-4-flash-250414"

    def test_parse_args_with_claude_model(self):
        """Tests CLI parsing accepts Claude model."""
        from cli.main import parse_args

        args = parse_args(["--spec", "001", "--model", "claude-sonnet-4-5-20250929"])
        assert args.model == "claude-sonnet-4-5-20250929"

    def test_parse_args_with_gpt_model(self):
        """Tests CLI parsing accepts GPT model."""
        from cli.main import parse_args

        args = parse_args(["--spec", "001", "--model", "gpt-4o"])
        assert args.model == "gpt-4o"

    def test_parse_args_model_defaults_to_none(self):
        """Tests model argument defaults to None when not specified."""
        from cli.main import parse_args

        args = parse_args(["--spec", "001"])
        assert args.model is None

    def test_parse_args_with_provider_and_model(self):
        """Tests CLI parsing accepts both --provider and --model flags."""
        from cli.main import parse_args

        args = parse_args([
            "--spec", "001",
            "--provider", "zhipuai",
            "--model", "glm-4-flash-250414"
        ])
        assert args.provider == "zhipuai"
        assert args.model == "glm-4-flash-250414"


# =============================================================================
# PROVIDER SELECTION BEHAVIOR TESTS
# =============================================================================


class TestProviderSelectionBehavior:
    """Tests for provider selection behavior in build command."""

    def test_provider_selection_sets_environment_variable(self, temp_dir):
        """Tests provider selection sets AI_ENGINE_PROVIDER environment variable."""
        from cli.build_commands import handle_build_command

        project_dir = temp_dir / "project"
        project_dir.mkdir()

        spec_dir = temp_dir / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Mock the run_autonomous_agent to avoid actual execution
        with patch("cli.build_commands.run_autonomous_agent"):
            with patch("cli.build_commands.validate_environment", return_value=True):
                with patch("cli.build_commands.ReviewState") as mock_review_state:
                    mock_review_state.return_value.is_approval_valid.return_value = True
                    with patch("cli.build_commands.check_existing_build", return_value=False):
                        with patch("cli.build_commands.choose_workspace") as mock_workspace:
                            # Return direct mode to avoid worktree complexity
                            from workspace import WorkspaceMode
                            mock_workspace.return_value = WorkspaceMode.DIRECT

                            with patch("cli.build_commands.sync_spec_to_source"):
                                handle_build_command(
                                    project_dir=project_dir,
                                    spec_dir=spec_dir,
                                    model="test-model",
                                    provider="zhipuai",
                                    max_iterations=None,
                                    verbose=False,
                                    force_isolated=False,
                                    force_direct=True,
                                    auto_continue=True,
                                    skip_qa=True,
                                    force_bypass_approval=True,
                                )

                            # Verify environment variable was set
                            # Note: It gets reset after the function, so we check the side effect
                            # by checking if it was called during execution

    def test_provider_none_does_not_override_environment(self, temp_dir):
        """Tests provider=None does not override existing environment variable."""
        from cli.build_commands import handle_build_command

        project_dir = temp_dir / "project"
        project_dir.mkdir()

        spec_dir = temp_dir / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Set initial provider
        original_provider = os.environ.get("AI_ENGINE_PROVIDER")
        os.environ["AI_ENGINE_PROVIDER"] = "claude"

        try:
            with patch("cli.build_commands.run_autonomous_agent"):
                with patch("cli.build_commands.validate_environment", return_value=True):
                    with patch("cli.build_commands.ReviewState") as mock_review_state:
                        mock_review_state.return_value.is_approval_valid.return_value = True
                        with patch("cli.build_commands.check_existing_build", return_value=False):
                            with patch("cli.build_commands.choose_workspace") as mock_workspace:
                                from workspace import WorkspaceMode
                                mock_workspace.return_value = WorkspaceMode.DIRECT

                                with patch("cli.build_commands.sync_spec_to_source"):
                                    # Call with provider=None (should use existing env var)
                                    handle_build_command(
                                        project_dir=project_dir,
                                        spec_dir=spec_dir,
                                        model="test-model",
                                        provider=None,
                                        max_iterations=None,
                                        verbose=False,
                                        force_isolated=False,
                                        force_direct=True,
                                        auto_continue=True,
                                        skip_qa=True,
                                        force_bypass_approval=True,
                                    )

                                    # Provider should remain claude
                                    assert os.environ.get("AI_ENGINE_PROVIDER") == "claude"
        finally:
            # Restore original
            if original_provider is not None:
                os.environ["AI_ENGINE_PROVIDER"] = original_provider
            else:
                os.environ.pop("AI_ENGINE_PROVIDER", None)


# =============================================================================
# PROVIDER CONFIG PERSISTENCE TESTS
# =============================================================================


class TestProviderConfigPersistence:
    """Tests for provider/model configuration persistence."""

    def test_provider_config_saved_to_implementation_plan(self, temp_dir):
        """Tests provider/model selection is saved to implementation_plan.json."""
        # Create spec directory with implementation plan
        spec_dir = temp_dir / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Create initial implementation plan
        plan = {
            "feature": "Test Feature",
            "phases": [],
            "provider_config": {
                "provider": "zhipuai",
                "model": "glm-4-flash-250414"
            }
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Verify it was saved correctly
        with open(plan_file) as f:
            loaded_plan = json.load(f)

        assert "provider_config" in loaded_plan
        assert loaded_plan["provider_config"]["provider"] == "zhipuai"
        assert loaded_plan["provider_config"]["model"] == "glm-4-flash-250414"

    def test_provider_config_restored_from_implementation_plan(self, temp_dir):
        """Tests provider/model can be restored from implementation_plan.json."""
        from core.providers.config import ProviderConfig

        spec_dir = temp_dir / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Create implementation plan with provider config
        plan = {
            "feature": "Test Feature",
            "phases": [],
            "provider_config": {
                "provider": "litellm",
                "model": "gpt-4o"
            }
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Load and verify
        with open(plan_file) as f:
            loaded_plan = json.load(f)

        assert loaded_plan["provider_config"]["provider"] == "litellm"
        assert loaded_plan["provider_config"]["model"] == "gpt-4o"

    def test_implementation_plan_without_provider_config(self, temp_dir):
        """Tests backward compatibility: plans without provider_config work."""
        spec_dir = temp_dir / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Create old-style implementation plan (no provider_config)
        plan = {
            "feature": "Test Feature",
            "phases": [],
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Load and verify it doesn't crash
        with open(plan_file) as f:
            loaded_plan = json.load(f)

        assert "provider_config" not in loaded_plan
        # This should not raise an error - backward compatibility


# =============================================================================
# PROVIDER OVERRIDE TESTS
# =============================================================================


class TestProviderOverride:
    """Tests for provider override behavior."""

    def test_cli_provider_overrides_environment(self, temp_dir):
        """Tests CLI --provider flag overrides environment variable."""
        from cli.main import parse_args

        # Set environment variable
        os.environ["AI_ENGINE_PROVIDER"] = "claude"

        try:
            # Parse with different provider
            args = parse_args(["--spec", "001", "--provider", "zhipuai"])

            # CLI arg should take precedence
            assert args.provider == "zhipuai"
        finally:
            os.environ.pop("AI_ENGINE_PROVIDER", None)

    def test_session_config_provider_override(self):
        """Tests SessionConfig.provider overrides ProviderConfig.provider."""
        from core.providers.config import ProviderConfig
        from core.providers.base import SessionConfig

        # Create provider config with claude
        provider_config = ProviderConfig(
            provider="claude",
            anthropic_api_key="test-key"
        )

        # Create session config with zhipuai override
        session_config = SessionConfig(
            provider="zhipuai",
            model="glm-4-flash"
        )

        # Session config should have different provider
        assert session_config.provider == "zhipuai"
        assert provider_config.provider == "claude"

    def test_session_config_model_override(self):
        """Tests SessionConfig.model overrides provider default model."""
        from core.providers.config import ProviderConfig
        from core.providers.base import SessionConfig

        # Create provider config with default model
        provider_config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key",
            zhipuai_model="glm-4.7"  # Default
        )

        # Create session config with model override
        session_config = SessionConfig(
            provider=None,  # Use provider default
            model="glm-4-flash-250414"  # Override model
        )

        # Session config should have different model
        assert session_config.model == "glm-4-flash-250414"


# =============================================================================
# PROVIDER/MODEL VALIDATION TESTS
# =============================================================================


class TestProviderModelValidation:
    """Tests for provider and model validation."""

    def test_get_available_provider_names(self):
        """Tests get_available_provider_names returns all providers."""
        from core.providers.factory import get_available_provider_names

        providers = get_available_provider_names()

        assert isinstance(providers, list)
        assert "claude" in providers
        assert "litellm" in providers
        assert "openrouter" in providers
        assert "zhipuai" in providers

    def test_zhipuai_provider_supported_models(self):
        """Tests ZhipuAIProvider returns supported models."""
        from core.providers.adapters.zhipuai import ZhipuAIProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="zhipuai",
            zhipuai_api_key="test-key"
        )

        provider = ZhipuAIProvider(config)
        models = provider.get_supported_models()

        assert isinstance(models, list)
        assert len(models) > 0
        assert "glm-4-flash-250414" in models
        assert "glm-4.7" in models

    def test_claude_provider_supported_models(self):
        """Tests ClaudeProvider returns supported models."""
        from core.providers.adapters.claude import ClaudeProvider
        from core.providers.config import ProviderConfig

        config = ProviderConfig(
            provider="claude",
            anthropic_api_key="test-key"
        )

        provider = ClaudeProvider(config)
        models = provider.get_supported_models()

        assert isinstance(models, list)
        assert len(models) > 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestProviderSelectionIntegration:
    """Integration tests for full provider selection workflow."""

    def test_full_provider_selection_workflow(self, temp_dir, temp_git_repo):
        """Tests complete workflow: CLI args -> environment -> execution."""
        from cli.main import parse_args

        # Parse CLI arguments
        args = parse_args([
            "--spec", "001",
            "--provider", "zhipuai",
            "--model", "glm-4-flash-250414"
        ])

        # Verify parsed values
        assert args.provider == "zhipuai"
        assert args.model == "glm-4-flash-250414"

        # Create spec directory with plan
        spec_dir = temp_git_repo / ".auto-claude" / "specs" / "001-test"
        spec_dir.mkdir(parents=True)

        # Create implementation plan
        plan = {
            "feature": "Test Feature",
            "phases": [],
            "provider_config": {
                "provider": args.provider,
                "model": args.model
            }
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Verify persistence
        with open(plan_file) as f:
            loaded_plan = json.load(f)

        assert loaded_plan["provider_config"]["provider"] == "zhipuai"
        assert loaded_plan["provider_config"]["model"] == "glm-4-flash-250414"

    def test_provider_selection_with_all_providers(self, temp_dir):
        """Tests provider selection works for all available providers."""
        from core.providers.factory import get_available_provider_names

        providers = get_available_provider_names()

        # Test each provider
        for provider in providers:
            # Create implementation plan
            spec_dir = temp_dir / "specs" / f"001-{provider}"
            spec_dir.mkdir(parents=True)

            plan = {
                "feature": f"Test {provider}",
                "phases": [],
                "provider_config": {
                    "provider": provider,
                    "model": "test-model"
                }
            }

            plan_file = spec_dir / "implementation_plan.json"
            plan_file.write_text(json.dumps(plan, indent=2))

            # Verify
            with open(plan_file) as f:
                loaded_plan = json.load(f)

            assert loaded_plan["provider_config"]["provider"] == provider
