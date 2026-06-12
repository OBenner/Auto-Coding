#!/usr/bin/env python3
"""
Tests for Conditional Claude Auth in Environment Validation
===========================================================

validate_environment() must only require the Claude OAuth token when at
least one core agent role (planner, coder, qa_reviewer, qa_fixer) resolves
to the claude provider. Roles resolve the same way the runtime factory
does: AGENT_PROVIDER_<ROLE> > AI_ENGINE_PROVIDER > claude default.

Regression coverage for: a user with only OPENAI_API_KEY (all roles on a
non-Claude provider) could not run `python run.py` at all because the
OAuth check failed the build with exit code 3.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from cli.utils import (
    CORE_AGENT_ROLES,
    resolve_agent_providers,
    validate_environment,
)

# Env vars that influence provider resolution and validate_environment output
_PROVIDER_ENV_VARS = [
    "AI_ENGINE_PROVIDER",
    "AGENT_PROVIDER_PLANNER",
    "AGENT_PROVIDER_CODER",
    "AGENT_PROVIDER_QA_REVIEWER",
    "AGENT_PROVIDER_QA_FIXER",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "ANTHROPIC_BASE_URL",
    "LINEAR_API_KEY",
    "GRAPHITI_ENABLED",
    "AUTO_CLAUDE_CI",
    "AUTO_CLAUDE_JSON_OUTPUT",
]


@pytest.fixture
def clean_provider_env(monkeypatch):
    """Remove all provider/auth-related env vars for hermetic resolution."""
    for var in _PROVIDER_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


@pytest.fixture
def valid_spec_dir(tmp_path) -> Path:
    """Spec directory containing the spec.md validate_environment checks for."""
    spec_dir = tmp_path / "specs" / "001-test"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text("# Test Spec\n")
    return spec_dir


def run_validate(spec_dir: Path, token: str | None):
    """Call validate_environment with platform deps and auth lookup patched."""
    with patch("cli.utils.validate_platform_dependencies"):
        with patch("cli.utils.get_auth_token", return_value=token):
            with patch(
                "cli.utils.get_auth_token_source",
                return_value="CLAUDE_CODE_OAUTH_TOKEN (env)" if token else None,
            ):
                return validate_environment(spec_dir)


# =============================================================================
# ROLE -> PROVIDER RESOLUTION
# =============================================================================


class TestResolveAgentProviders:
    """Tests for resolve_agent_providers()."""

    def test_defaults_to_claude_for_all_roles(self, clean_provider_env):
        """Without provider env vars every core role resolves to claude."""
        providers = resolve_agent_providers()

        assert set(providers) == set(CORE_AGENT_ROLES)
        assert all(provider == "claude" for provider in providers.values())

    def test_global_provider_applies_to_all_roles(self, clean_provider_env):
        """AI_ENGINE_PROVIDER switches every role at once."""
        clean_provider_env.setenv("AI_ENGINE_PROVIDER", "openai")

        providers = resolve_agent_providers()

        assert all(provider == "openai" for provider in providers.values())

    def test_per_role_override_beats_global(self, clean_provider_env):
        """AGENT_PROVIDER_<ROLE> takes precedence over AI_ENGINE_PROVIDER."""
        clean_provider_env.setenv("AI_ENGINE_PROVIDER", "openai")
        clean_provider_env.setenv("AGENT_PROVIDER_CODER", "openrouter")

        providers = resolve_agent_providers()

        assert providers["coder"] == "openrouter"
        assert providers["planner"] == "openai"
        assert providers["qa_reviewer"] == "openai"
        assert providers["qa_fixer"] == "openai"

    def test_single_role_override_leaves_others_on_claude(self, clean_provider_env):
        """Setting one AGENT_PROVIDER_* var keeps the other roles on claude."""
        clean_provider_env.setenv("AGENT_PROVIDER_QA_FIXER", "openai")

        providers = resolve_agent_providers()

        assert providers["qa_fixer"] == "openai"
        assert providers["planner"] == "claude"
        assert providers["coder"] == "claude"
        assert providers["qa_reviewer"] == "claude"

    def test_invalid_provider_falls_back_to_claude(self, clean_provider_env):
        """Unknown provider names resolve to claude, like the runtime factory."""
        clean_provider_env.setenv("AI_ENGINE_PROVIDER", "not-a-provider")

        providers = resolve_agent_providers()

        assert all(provider == "claude" for provider in providers.values())


# =============================================================================
# CONDITIONAL CLAUDE OAUTH REQUIREMENT
# =============================================================================


class TestValidateEnvironmentClaudeAuth:
    """Tests for the conditional OAuth check in validate_environment()."""

    def test_no_token_fails_when_roles_default_to_claude(
        self, clean_provider_env, valid_spec_dir, capsys
    ):
        """Strict behavior is kept: claude roles without a token fail validation."""
        result = run_validate(valid_spec_dir, token=None)

        assert result is False
        output = capsys.readouterr().out
        assert "Error: No OAuth token found" in output
        assert "planner, coder, qa_reviewer, qa_fixer" in output

    def test_no_token_passes_when_no_role_uses_claude(
        self, clean_provider_env, valid_spec_dir, capsys
    ):
        """A user with only OPENAI_API_KEY can run without any Claude token."""
        clean_provider_env.setenv("AI_ENGINE_PROVIDER", "openai")
        clean_provider_env.setenv("OPENAI_API_KEY", "sk-test")

        result = run_validate(valid_spec_dir, token=None)

        assert result is True
        output = capsys.readouterr().out
        assert "Claude auth: not required" in output
        assert "Error: No OAuth token found" not in output

    def test_no_token_passes_with_per_role_overrides_only(
        self, clean_provider_env, valid_spec_dir, capsys
    ):
        """All four AGENT_PROVIDER_* vars set to openai need no Claude token."""
        for role in CORE_AGENT_ROLES:
            clean_provider_env.setenv(f"AGENT_PROVIDER_{role.upper()}", "openai")
        clean_provider_env.setenv("OPENAI_API_KEY", "sk-test")

        result = run_validate(valid_spec_dir, token=None)

        assert result is True
        output = capsys.readouterr().out
        assert "Claude auth: not required" in output

    def test_no_token_fails_when_one_role_still_uses_claude(
        self, clean_provider_env, valid_spec_dir, capsys
    ):
        """A single claude role keeps the OAuth requirement strict."""
        clean_provider_env.setenv("AI_ENGINE_PROVIDER", "openai")
        clean_provider_env.setenv("AGENT_PROVIDER_PLANNER", "claude")
        clean_provider_env.setenv("OPENAI_API_KEY", "sk-test")

        result = run_validate(valid_spec_dir, token=None)

        assert result is False
        output = capsys.readouterr().out
        assert "Error: No OAuth token found" in output
        assert "planner" in output

    def test_token_present_passes_with_claude_roles(
        self, clean_provider_env, valid_spec_dir, capsys
    ):
        """Existing happy path is unchanged: token + claude roles validates."""
        result = run_validate(valid_spec_dir, token="test-token")

        assert result is True
        output = capsys.readouterr().out
        assert "Auth: CLAUDE_CODE_OAUTH_TOKEN (env)" in output
        # All-claude setups keep their original output shape
        assert "AI providers:" not in output
        assert "Claude auth: not required" not in output

    def test_provider_summary_printed_for_non_claude_setup(
        self, clean_provider_env, valid_spec_dir, capsys
    ):
        """Multi-provider setups show which provider each role resolved to."""
        clean_provider_env.setenv("AI_ENGINE_PROVIDER", "openai")
        clean_provider_env.setenv("OPENAI_API_KEY", "sk-test")

        run_validate(valid_spec_dir, token=None)

        output = capsys.readouterr().out
        assert (
            "AI providers: planner=openai, coder=openai, "
            "qa_reviewer=openai, qa_fixer=openai" in output
        )

    def test_missing_non_claude_credentials_warns_but_passes(
        self, clean_provider_env, valid_spec_dir, capsys
    ):
        """Missing credentials for a non-claude provider warn without failing."""
        clean_provider_env.setenv("AI_ENGINE_PROVIDER", "openai")
        # OPENAI_API_KEY intentionally not set

        result = run_validate(valid_spec_dir, token=None)

        assert result is True
        output = capsys.readouterr().out
        assert "Warning:" in output
        assert "OPENAI_API_KEY" in output

    def test_missing_spec_still_fails_without_claude_roles(
        self, clean_provider_env, tmp_path, capsys
    ):
        """The spec.md check is independent of the auth gate."""
        clean_provider_env.setenv("AI_ENGINE_PROVIDER", "openai")
        clean_provider_env.setenv("OPENAI_API_KEY", "sk-test")
        empty_spec_dir = tmp_path / "specs" / "002-empty"
        empty_spec_dir.mkdir(parents=True)

        result = run_validate(empty_spec_dir, token=None)

        assert result is False
        output = capsys.readouterr().out
        assert "spec.md not found" in output
