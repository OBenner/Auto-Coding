#!/usr/bin/env python3
"""Tests for graphiti_validator.py module."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from setup.graphiti_validator import (
    validate_graphiti_config,
    get_graphiti_status,
)


class TestValidateGraphitiConfig:
    """Test suite for validate_graphiti_config() function."""

    def test_validate_graphiti_config_returns_dict(self):
        """Test that validation returns a dictionary with required keys."""
        result = validate_graphiti_config()

        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'enabled' in result
        assert 'llm_provider' in result
        assert 'embedder_provider' in result
        assert 'issues' in result
        assert 'warnings' in result
        assert 'message' in result

    def test_validate_graphiti_config_types(self):
        """Test that result has correct types."""
        result = validate_graphiti_config()

        assert isinstance(result['valid'], bool)
        assert isinstance(result['enabled'], bool)
        assert isinstance(result['llm_provider'], str)
        assert isinstance(result['embedder_provider'], str)
        assert isinstance(result['issues'], list)
        assert isinstance(result['warnings'], list)
        assert isinstance(result['message'], str)

    def test_validate_graphiti_config_issues_are_strings(self):
        """Test that all issues are strings."""
        result = validate_graphiti_config()

        for issue in result['issues']:
            assert isinstance(issue, str)

    def test_validate_graphiti_config_warnings_are_strings(self):
        """Test that all warnings are strings."""
        result = validate_graphiti_config()

        for warning in result['warnings']:
            assert isinstance(warning, str)

    def test_validate_graphiti_config_message_not_empty(self):
        """Test that message is never empty."""
        result = validate_graphiti_config()

        assert len(result['message']) > 0

    def test_validate_graphiti_config_exception_handling(self):
        """Test exception handling when validation fails."""
        with patch('setup.graphiti_validator.is_graphiti_enabled', side_effect=Exception("Test error")):
            result = validate_graphiti_config()

            assert result['valid'] is False
            assert result['enabled'] is False
            assert len(result['issues']) > 0
            assert 'Failed to validate Graphiti configuration' in result['issues'][0]

    def test_validate_graphiti_config_when_disabled(self):
        """Test validation when Graphiti is disabled."""
        with patch('setup.graphiti_validator.is_graphiti_enabled', return_value=False):
            result = validate_graphiti_config()

            assert result['valid'] is True  # Valid to be disabled
            assert result['enabled'] is False
            assert result['llm_provider'] == 'none'
            assert result['embedder_provider'] == 'none'
            assert len(result['issues']) == 0


class TestGetGraphitiStatus:
    """Test suite for get_graphiti_status() function."""

    def test_get_graphiti_status_returns_dict(self):
        """Test that get_graphiti_status returns a dictionary."""
        status = get_graphiti_status()

        assert isinstance(status, dict)

    def test_get_graphiti_status_has_required_keys(self):
        """Test that status has all required keys."""
        status = get_graphiti_status()

        assert 'enabled' in status
        assert 'llm_provider' in status
        assert 'embedder_provider' in status

    def test_get_graphiti_status_enabled_is_bool(self):
        """Test that enabled field is boolean."""
        status = get_graphiti_status()

        assert isinstance(status['enabled'], bool)

    def test_get_graphiti_status_llm_provider_is_string(self):
        """Test that llm_provider field is string."""
        status = get_graphiti_status()

        assert isinstance(status['llm_provider'], str)

    def test_get_graphiti_status_embedder_provider_is_string(self):
        """Test that embedder_provider field is string."""
        status = get_graphiti_status()

        assert isinstance(status['embedder_provider'], str)

    def test_get_graphiti_status_exception_handling(self):
        """Test exception handling in get_graphiti_status."""
        with patch('setup.graphiti_validator.is_graphiti_enabled', side_effect=Exception("Test error")):
            status = get_graphiti_status()

            # Should return a dict even on error
            assert isinstance(status, dict)
            assert 'enabled' in status

    def test_get_graphiti_status_when_disabled(self):
        """Test status when Graphiti is disabled."""
        with patch('setup.graphiti_validator.is_graphiti_enabled', return_value=False):
            status = get_graphiti_status()

            assert status['enabled'] is False
            assert 'llm_provider' in status
            assert 'embedder_provider' in status


class TestGraphitiValidationIntegration:
    """Integration tests for Graphiti validation."""

    def test_validate_and_status_consistency(self):
        """Test that validate and status return consistent enabled state."""
        validation_result = validate_graphiti_config()
        status = get_graphiti_status()

        # Both should report the same enabled state
        assert validation_result['enabled'] == status['enabled']

    def test_validation_issues_affect_valid_flag(self):
        """Test that issues result in valid=False."""
        result = validate_graphiti_config()

        # If there are issues, valid should be False
        if len(result['issues']) > 0:
            assert result['valid'] is False

    def test_disabled_graphiti_has_no_issues(self):
        """Test that disabled Graphiti has no blocking issues."""
        with patch('setup.graphiti_validator.is_graphiti_enabled', return_value=False):
            result = validate_graphiti_config()

            # Disabled state should not have issues
            assert len(result['issues']) == 0
            assert result['valid'] is True
