"""
Unit Tests for Env Configurator
=================================

Tests for apps/backend/core/env_configurator.py
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from apps.backend.core.env_configurator import (
    EnvConfigurator,
    EnvVariable,
    setup_env,
)


class TestEnvVariable:
    """Tests for EnvVariable class."""

    def test_env_variable_creation(self):
        """Test creating an environment variable."""
        var = EnvVariable(
            name="API_KEY",
            value="test_value",
            description="API key for testing",
            required=True,
            section="Authentication"
        )

        assert var.name == "API_KEY"
        assert var.value == "test_value"
        assert var.description == "API key for testing"
        assert var.required is True
        assert var.section == "Authentication"


class TestEnvConfigurator:
    """Tests for EnvConfigurator class."""

    def test_parse_env_example_extracts_variables(self, tmp_path):
        """Test parsing .env.example file extracts variables correctly."""
        # Create apps/backend directory structure
        backend_dir = tmp_path / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        # Create .env.example with variables
        env_example = backend_dir / ".env.example"
        env_example.write_text("""# Authentication (REQUIRED)
# Claude OAuth token from: claude setup-token --print
CLAUDE_CODE_OAUTH_TOKEN=

# API Keys (OPTIONAL)
# OpenAI API key for LLM provider
OPENAI_API_KEY=sk-test-key
""")

        configurator = EnvConfigurator(tmp_path)
        variables = configurator.parse_env_example()

        # Verify variables were extracted
        assert len(variables) == 2

        # Check first variable (required)
        assert variables[0].name == "CLAUDE_CODE_OAUTH_TOKEN"
        assert variables[0].required is True
        assert "Claude OAuth token" in variables[0].description

        # Check second variable (optional)
        assert variables[1].name == "OPENAI_API_KEY"
        assert variables[1].required is False
        assert "OpenAI API key" in variables[1].description

    def test_parse_env_example_missing_file_raises_error(self, tmp_path):
        """Test parsing missing .env.example raises FileNotFoundError."""
        configurator = EnvConfigurator(tmp_path)

        with pytest.raises(FileNotFoundError, match=".env.example not found"):
            configurator.parse_env_example()

    def test_get_existing_env_values(self, tmp_path):
        """Test reading existing .env file values."""
        backend_dir = tmp_path / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        # Create existing .env file
        env_file = backend_dir / ".env"
        env_file.write_text("""OPENAI_API_KEY=sk-existing-key
ANTHROPIC_API_KEY=sk-ant-existing
# Comment line
GRAPHITI_ENABLED=true
""")

        configurator = EnvConfigurator(tmp_path)
        existing_values = configurator.get_existing_env_values()

        # Verify values were read
        assert existing_values["OPENAI_API_KEY"] == "sk-existing-key"
        assert existing_values["ANTHROPIC_API_KEY"] == "sk-ant-existing"
        assert existing_values["GRAPHITI_ENABLED"] == "true"

    def test_get_existing_env_values_no_file(self, tmp_path):
        """Test reading non-existent .env file returns empty dict."""
        configurator = EnvConfigurator(tmp_path)
        existing_values = configurator.get_existing_env_values()

        assert existing_values == {}

    def test_create_env_file_interactive_false_uses_defaults(self, tmp_path):
        """Test non-interactive mode uses default values."""
        backend_dir = tmp_path / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        # Create .env.example
        env_example = backend_dir / ".env.example"
        env_example.write_text("""# Config
API_KEY=default_value
""")

        configurator = EnvConfigurator(tmp_path)
        result = configurator.create_env_file(interactive=False, dry_run=False)

        # Verify success
        assert result["success"] is True
        assert result["variables_configured"] >= 1

        # Verify .env file was created
        env_file = backend_dir / ".env"
        assert env_file.exists()
        content = env_file.read_text()
        assert "API_KEY=default_value" in content

    def test_create_env_file_dry_run_no_file_written(self, tmp_path):
        """Test dry-run mode doesn't write .env file."""
        backend_dir = tmp_path / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        # Create .env.example
        env_example = backend_dir / ".env.example"
        env_example.write_text("""# Config
API_KEY=test_value
""")

        configurator = EnvConfigurator(tmp_path)

        # Patch print to suppress dry-run output
        with patch("builtins.print"):
            result = configurator.create_env_file(interactive=False, dry_run=True)

        # Verify no file was written
        env_file = backend_dir / ".env"
        assert not env_file.exists(), ".env file should NOT be written in dry-run mode"

        # Result should still show success
        assert result["success"] is True

    def test_validate_required_vars_missing_required(self, tmp_path):
        """Test validation fails when required variables are missing."""
        backend_dir = tmp_path / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        # Create .env.example with required variable
        env_example = backend_dir / ".env.example"
        env_example.write_text("""# Authentication (REQUIRED)
REQUIRED_KEY=
""")

        # Create .env without the required variable
        env_file = backend_dir / ".env"
        env_file.write_text("""# Empty .env
""")

        configurator = EnvConfigurator(tmp_path)
        validation = configurator.validate_required_vars()

        # Validation should fail
        assert validation["valid"] is False
        assert "REQUIRED_KEY" in validation["missing_required"]

    def test_validate_required_vars_all_present(self, tmp_path):
        """Test validation passes when all required variables are set."""
        backend_dir = tmp_path / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        # Create .env.example with required variable
        env_example = backend_dir / ".env.example"
        env_example.write_text("""# Authentication (REQUIRED)
REQUIRED_KEY=
""")

        # Create .env with the required variable
        env_file = backend_dir / ".env"
        env_file.write_text("""REQUIRED_KEY=some_value
""")

        configurator = EnvConfigurator(tmp_path)
        validation = configurator.validate_required_vars()

        # Validation should pass
        assert validation["valid"] is True
        assert validation["missing_required"] == []

    def test_setup_env_convenience_function(self, tmp_path):
        """Test setup_env() convenience function."""
        backend_dir = tmp_path / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        # Create .env.example
        env_example = backend_dir / ".env.example"
        env_example.write_text("""# Config (REQUIRED)
API_KEY=test_key
""")

        # Patch print to suppress output
        with patch("builtins.print"):
            success = setup_env(tmp_path, interactive=False, dry_run=False)

        # Verify success
        assert success is True

        # Verify .env file was created
        env_file = backend_dir / ".env"
        assert env_file.exists()

    def test_prompt_for_value_with_user_input(self, tmp_path):
        """Test prompting for value with mocked user input."""
        backend_dir = tmp_path / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        configurator = EnvConfigurator(tmp_path)

        var = EnvVariable(
            name="TEST_VAR",
            value="default",
            description="Test variable",
            required=False,
            section="Testing"
        )

        # Mock user input
        with patch("builtins.input", return_value="user_value"):
            with patch("builtins.print"):  # Suppress print output
                value = configurator.prompt_for_value(var, existing_value=None)

        assert value == "user_value"

    def test_prompt_for_value_empty_input_returns_default(self, tmp_path):
        """Test that empty input returns default value."""
        backend_dir = tmp_path / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        configurator = EnvConfigurator(tmp_path)

        var = EnvVariable(
            name="TEST_VAR",
            value="default_value",
            description="Test variable",
            required=False,
            section="Testing"
        )

        # Mock empty user input (just press enter)
        with patch("builtins.input", return_value=""):
            with patch("builtins.print"):  # Suppress print output
                value = configurator.prompt_for_value(var, existing_value=None)

        assert value == "default_value"

    def test_prompt_for_value_keyboard_interrupt_returns_none(self, tmp_path):
        """Test that KeyboardInterrupt during prompt returns None."""
        backend_dir = tmp_path / "apps" / "backend"
        backend_dir.mkdir(parents=True)

        configurator = EnvConfigurator(tmp_path)

        var = EnvVariable(
            name="TEST_VAR",
            value="default",
            description="Test variable",
            required=False,
            section="Testing"
        )

        # Mock KeyboardInterrupt
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            with patch("builtins.print"):  # Suppress print output
                value = configurator.prompt_for_value(var, existing_value=None)

        assert value is None
