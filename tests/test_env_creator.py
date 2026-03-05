#!/usr/bin/env python3
"""Tests for env_creator.py module."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from setup.env_creator import (
    create_env_file,
    _backup_env_file,
    _generate_env_content,
    get_env_path,
    env_exists,
    read_env_value,
    get_minimal_config,
    EnvConfig,
    EnvCreationResult,
)


class TestCreateEnvFile:
    """Test suite for create_env_file() function."""

    def test_create_env_file_with_config(self):
        """Test .env file creation with configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create mock .env.example template
            backend_dir = Path(tmpdir) / "backend"
            backend_dir.mkdir()
            env_example = backend_dir / ".env.example"
            env_example.write_text("# Test Template\n# GRAPHITI_ENABLED=true\n# GRAPHITI_LLM_PROVIDER=openai\n")

            with patch('setup.env_creator.Path.__new__', side_effect=lambda cls, *args, **kwargs: Path(args[0]) if args else backend_dir):
                # Mock Path(__file__).parent to return our temp dir
                with patch('setup.env_creator.Path.resolve', return_value=backend_dir):
                    with patch.object(Path, 'parent', backend_dir):
                        config = {
                            'graphiti_enabled': True,
                            'graphiti_llm_provider': 'openai'
                        }
                        result = create_env_file(config, force=True)

                        assert result['success'] is True
                        assert result['created_new'] is True
                        assert result['backed_up'] is False
                        assert 'Successfully created' in result['message']

    def test_create_env_file_without_config(self):
        """Test .env file creation without configuration (template only)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend_dir = Path(tmpdir) / "backend"
            backend_dir.mkdir()
            env_example = backend_dir / ".env.example"
            env_example.write_text("# Test Template\n")

            with patch('setup.env_creator.Path.resolve', return_value=backend_dir):
                with patch.object(Path, 'parent', backend_dir):
                    result = create_env_file(None, force=True)

                    assert result['success'] is True
                    assert result['created_new'] is True

    def test_create_env_file_already_exists_without_force(self):
        """Test that .env creation fails when file exists without force."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend_dir = Path(tmpdir) / "backend"
            backend_dir.mkdir()
            env_file = backend_dir / ".env"
            env_file.write_text("existing content")

            with patch('setup.env_creator.Path.resolve', return_value=backend_dir):
                with patch.object(Path, 'parent', backend_dir):
                    result = create_env_file({}, force=False)

                    assert result['success'] is False
                    assert 'already exists' in result['message']

    def test_create_env_file_backup_existing(self):
        """Test that existing .env file is backed up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend_dir = Path(tmpdir) / "backend"
            backend_dir.mkdir()
            env_file = backend_dir / ".env"
            env_file.write_text("existing content")
            env_example = backend_dir / ".env.example"
            env_example.write_text("# Template\n")

            with patch('setup.env_creator.Path.resolve', return_value=backend_dir):
                with patch.object(Path, 'parent', backend_dir):
                    result = create_env_file({}, backup_existing=True, force=True)

                    assert result['success'] is True
                    assert result['backed_up'] is True
                    assert 'Backup saved' in result['message']

    def test_create_env_file_permission_error(self):
        """Test handling of permission errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend_dir = Path(tmpdir) / "backend"
            backend_dir.mkdir()
            env_example = backend_dir / ".env.example"
            env_example.write_text("# Template\n")

            with patch('setup.env_creator.Path.resolve', return_value=backend_dir):
                with patch.object(Path, 'parent', backend_dir):
                    with patch.object(Path, 'write_text', side_effect=PermissionError("Denied")):
                        result = create_env_file({}, force=True)

                        assert result['success'] is False
                        assert 'Permission denied' in result['message']


class TestBackupEnvFile:
    """Test suite for _backup_env_file() function."""

    def test_backup_env_file_success(self):
        """Test successful .env file backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("test content")

            result = _backup_env_file(env_file)

            assert result is True
            assert not env_file.exists()
            backup_file = Path(tmpdir) / ".env.backup"
            assert backup_file.exists()

    def test_backup_env_file_with_timestamp(self):
        """Test backup with timestamp when backup already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("test content")
            backup_file = Path(tmpdir) / ".env.backup"
            backup_file.write_text("old backup")

            result = _backup_env_file(env_file)

            assert result is True
            # Check that timestamped backup was created
            timestamped_backups = list(Path(tmpdir).glob(".env.backup.*"))
            assert len(timestamped_backups) == 1

    def test_backup_env_file_failure(self):
        """Test backup failure handling."""
        with patch('pathlib.Path.rename', side_effect=Exception("Backup failed")):
            env_file = Path("/fake/path/.env")
            result = _backup_env_file(env_file)
            assert result is False


class TestGenerateEnvContent:
    """Test suite for _generate_env_content() function."""

    def test_generate_env_content_with_values(self):
        """Test content generation with config values."""
        template = "# GRAPHITI_ENABLED=true\n# GRAPHITI_LLM_PROVIDER=openai\n"
        config = {
            'graphiti_enabled': True,
            'graphiti_llm_provider': 'openai'
        }

        result = _generate_env_content(template, config)

        assert "GRAPHITI_ENABLED=true" in result
        assert "GRAPHITI_LLM_PROVIDER=openai" in result

    def test_generate_env_content_with_boolean(self):
        """Test content generation with boolean values."""
        template = "# GRAPHITI_ENABLED=true\n"
        config = {'graphiti_enabled': False}

        result = _generate_env_content(template, config)

        assert "GRAPHITI_ENABLED=false" in result

    def test_generate_env_content_preserves_comments(self):
        """Test that comments are preserved in output."""
        template = "# This is a comment\n# GRAPHITI_ENABLED=true\n"
        config = {'graphiti_enabled': True}

        result = _generate_env_content(template, config)

        assert "# This is a comment" in result

    def test_generate_env_content_preserves_structure(self):
        """Test that template structure is preserved."""
        template = "# Comment 1\n\n# Comment 2\n# VAR=value\n"
        config = {}

        result = _generate_env_content(template, config)

        # Empty lines should be preserved
        assert "\n\n" in result

    def test_generate_env_content_updates_existing_vars(self):
        """Test updating existing variable values."""
        template = "GRAPHITI_ENABLED=false\n"
        config = {'graphiti_enabled': True}

        result = _generate_env_content(template, config)

        assert "GRAPHITI_ENABLED=true" in result

    def test_generate_env_content_with_none_values(self):
        """Test that None values are filtered out."""
        template = "# VAR1=value1\n# VAR2=value2\n"
        config = {'var1': 'value1', 'var2': None}

        result = _generate_env_content(template, config)

        # VAR1 should be uncommented, VAR2 should remain commented
        assert "VAR1=value1" in result
        assert "# VAR2=value2" in result


class TestGetEnvPath:
    """Test suite for get_env_path() function."""

    def test_get_env_path_returns_string(self):
        """Test that get_env_path returns a string."""
        result = get_env_path()
        assert isinstance(result, str)
        assert result.endswith('.env')


class TestEnvExists:
    """Test suite for env_exists() function."""

    def test_env_exists_when_file_exists(self):
        """Test env_exists returns True when .env exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend_dir = Path(tmpdir) / "backend"
            backend_dir.mkdir()
            env_file = backend_dir / ".env"
            env_file.write_text("test")

            with patch('setup.env_creator.get_env_path', return_value=str(env_file)):
                result = env_exists()
                assert result is True

    def test_env_exists_when_file_missing(self):
        """Test env_exists returns False when .env doesn't exist."""
        with patch('setup.env_creator.get_env_path', return_value='/fake/path/.env'):
            result = env_exists()
            assert result is False


class TestReadEnvValue:
    """Test suite for read_env_value() function."""

    def test_read_env_value_found(self):
        """Test reading an existing value from .env."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("VAR1=value1\nVAR2=value2\n")

            with patch('setup.env_creator.get_env_path', return_value=str(env_file)):
                result = read_env_value("VAR1")
                assert result == "value1"

    def test_read_env_value_not_found(self):
        """Test reading a non-existent value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("VAR1=value1\n")

            with patch('setup.env_creator.get_env_path', return_value=str(env_file)):
                result = read_env_value("VAR2")
                assert result is None

    def test_read_env_value_skips_comments(self):
        """Test that commented lines are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("# VAR1=commented\nVAR1=value1\n")

            with patch('setup.env_creator.get_env_path', return_value=str(env_file)):
                result = read_env_value("VAR1")
                assert result == "value1"

    def test_read_env_value_no_file(self):
        """Test reading when .env doesn't exist."""
        with patch('setup.env_creator.get_env_path', return_value='/fake/.env'):
            result = read_env_value("VAR1")
            assert result is None


class TestGetMinimalConfig:
    """Test suite for get_minimal_config() function."""

    def test_get_minimal_config_structure(self):
        """Test that minimal config has expected structure."""
        config = get_minimal_config()

        assert isinstance(config, dict)
        assert 'graphiti_enabled' in config
        assert 'graphiti_llm_provider' in config
        assert 'graphiti_embedder_provider' in config

    def test_get_minimal_config_values(self):
        """Test that minimal config has correct values."""
        config = get_minimal_config()

        assert config['graphiti_enabled'] is True
        assert config['graphiti_llm_provider'] == 'openai'
        assert config['graphiti_embedder_provider'] == 'openai'

    def test_get_minimal_config_is_env_config(self):
        """Test that minimal config matches EnvConfig type."""
        config = get_minimal_config()

        # Should only contain minimal keys
        expected_keys = {'graphiti_enabled', 'graphiti_llm_provider', 'graphiti_embedder_provider'}
        assert set(config.keys()) == expected_keys
