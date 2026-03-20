#!/usr/bin/env python3
"""Tests for Setup Wizard CLI."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from cli.setup_wizard import handle_setup_command


def test_handle_setup_command_basic_flow():
    """Tests basic setup command flow with mocked validations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        mock_python = MagicMock(return_value={
            "valid": True,
            "version": "3.12.0",
            "required_version": "3.12",
            "message": "OK"
        })

        mock_auth = MagicMock(return_value="sk-ant-test-token")

        mock_graphiti = MagicMock(return_value={
            "valid": True,
            "enabled": True,
            "llm_provider": "openai",
            "embedder_provider": "openai",
            "issues": [],
            "warnings": []
        })

        mock_env = MagicMock(return_value={
            "success": True,
            "env_path": str(project_dir / ".env"),
            "message": "OK",
            "backed_up": False
        })

        mock_test = MagicMock(return_value={
            "success": True,
            "steps_completed": ["Step 1"],
            "steps_failed": [],
            "error_message": None
        })

        mock_mark = MagicMock(return_value=True)

        with patch("cli.setup_wizard.validate_python_version", mock_python):
            with patch("core.auth.get_auth_token", mock_auth):
                with patch("cli.setup_wizard.validate_graphiti_config", mock_graphiti):
                    with patch("cli.setup_wizard.create_env_file", mock_env):
                        with patch("cli.setup_wizard.run_hello_world_test", mock_test):
                            with patch("cli.setup_wizard.mark_setup_complete", mock_mark):
                                with patch("sys.exit"):
                                    handle_setup_command(project_dir, skip_test=True)

        # Verify all steps were called
        mock_python.assert_called_once()
        mock_auth.assert_called_once()
        mock_graphiti.assert_called_once()
        mock_env.assert_called_once()
        mock_mark.assert_called_once()
        # Test should NOT be called when skip_test=True
        mock_test.assert_not_called()


def test_python_validation_fails_exits():
    """Tests that Python validation failure causes exit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        mock_python = MagicMock(return_value={
            "valid": False,
            "version": "3.11.0",
            "required_version": "3.12",
            "message": "Python 3.12+ required"
        })

        with patch("cli.setup_wizard.validate_python_version", mock_python):
            with patch("sys.exit") as mock_exit:
                handle_setup_command(project_dir)

                mock_exit.assert_called_with(1)


def test_authentication_fails_exits():
    """Tests that authentication failure causes exit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        mock_python = MagicMock(return_value={
            "valid": True,
            "version": "3.12.0",
            "required_version": "3.12",
            "message": "OK"
        })

        mock_auth = MagicMock(return_value=None)

        with patch("cli.setup_wizard.validate_python_version", mock_python):
            with patch("core.auth.get_auth_token", mock_auth):
                with patch("sys.exit") as mock_exit:
                    handle_setup_command(project_dir)

                    mock_exit.assert_called_with(1)


def test_env_creation_fails_exits():
    """Tests that .env creation failure causes exit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        mock_validations = {
            "python": MagicMock(return_value={
                "valid": True,
                "version": "3.12.0",
                "required_version": "3.12",
                "message": "OK"
            }),
            "auth": MagicMock(return_value="token"),
            "graphiti": MagicMock(return_value={
                "valid": True,
                "enabled": True,
                "llm_provider": "openai",
                "embedder_provider": "openai",
                "issues": [],
                "warnings": []
            }),
            "env": MagicMock(return_value={
                "success": False,
                "message": "Permission denied"
            })
        }

        with patch("cli.setup_wizard.validate_python_version", mock_validations["python"]):
            with patch("core.auth.get_auth_token", mock_validations["auth"]):
                with patch("cli.setup_wizard.validate_graphiti_config", mock_validations["graphiti"]):
                    with patch("cli.setup_wizard.create_env_file", mock_validations["env"]):
                        with patch("sys.exit") as mock_exit:
                            handle_setup_command(project_dir)

                            mock_exit.assert_called_with(1)


def test_keyboard_interrupt_handled():
    """Tests that KeyboardInterrupt is handled gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        mock_python = MagicMock(side_effect=KeyboardInterrupt())

        with patch("cli.setup_wizard.validate_python_version", mock_python):
            with patch("sys.exit") as mock_exit:
                handle_setup_command(project_dir)

                mock_exit.assert_called_with(130)


def test_unexpected_exception_handled():
    """Tests that unexpected exceptions are handled gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)

        mock_python = MagicMock(side_effect=Exception("Unexpected error"))

        with patch("cli.setup_wizard.validate_python_version", mock_python):
            with patch("sys.exit") as mock_exit:
                handle_setup_command(project_dir)

                mock_exit.assert_called_with(1)
