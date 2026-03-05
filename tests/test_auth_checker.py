"""
Tests for auth_checker.py module.

This module tests the OAuth token validation functionality that is
critical for the setup wizard's authentication step.
"""

import pytest
from unittest.mock import patch
from setup.auth_checker import check_oauth_token, AuthCheckResult


class TestCheckOAuthToken:
    """Test suite for check_oauth_token() function."""

    def test_oauth_token_found(self):
        """Test OAuth token found in keychain (success case)."""
        with patch('core.auth.get_auth_token', return_value='sk-ant-test123456'):
            result = check_oauth_token()

            assert result['authenticated'] is True
            assert result['hasToken'] is True
            assert 'OAuth token found' in result['message']

    def test_oauth_token_missing(self):
        """Test OAuth token not found (failure case)."""
        with patch('core.auth.get_auth_token', return_value=None):
            result = check_oauth_token()

            assert result['authenticated'] is False
            assert result['hasToken'] is False
            assert 'No authentication token found' in result['message']

    def test_import_error_handling(self):
        """Test ImportError handling when auth module not available."""
        with patch('core.auth.get_auth_token', side_effect=ImportError('No module named \'core.auth\'')):
            result = check_oauth_token()

            assert result['authenticated'] is False
            assert result['hasToken'] is False
            assert 'not available' in result['message'].lower()

    def test_generic_exception_handling(self):
        """Test generic exception handling."""
        with patch('core.auth.get_auth_token', side_effect=Exception('Keychain access failed')):
            result = check_oauth_token()

            assert result['authenticated'] is False
            assert result['hasToken'] is False
            assert 'check failed' in result['message'].lower()

    def test_auth_check_result_typed_dict(self):
        """Test that AuthCheckResult is properly structured."""
        with patch('core.auth.get_auth_token', return_value='sk-ant-test'):
            result = check_oauth_token()

            # Verify all required keys are present
            assert 'authenticated' in result
            assert 'hasToken' in result
            assert 'message' in result

            # Verify types
            assert isinstance(result['authenticated'], bool)
            assert isinstance(result['hasToken'], bool)
            assert isinstance(result['message'], str)

    def test_empty_token_string(self):
        """Test handling of empty string as token."""
        with patch('core.auth.get_auth_token', return_value=''):
            result = check_oauth_token()

            # Empty string should be treated as falsy
            assert result['authenticated'] is False
            assert result['hasToken'] is False

    def test_exception_with_detailed_error(self):
        """Test exception handling preserves error details."""
        error_msg = "Permission denied accessing keychain"
        with patch('core.auth.get_auth_token', side_effect=Exception(error_msg)):
            result = check_oauth_token()

            assert result['authenticated'] is False
            assert error_msg in result['message']

    def test_successful_auth_message_content(self):
        """Test success message contains expected keywords."""
        with patch('core.auth.get_auth_token', return_value='sk-ant-api-key'):
            result = check_oauth_token()

            assert 'configured' in result['message'].lower()
            assert 'oauth token found' in result['message'].lower()
            assert 'system keychain' in result['message'].lower()

    def test_missing_auth_message_content(self):
        """Test missing token message contains guidance."""
        with patch('core.auth.get_auth_token', return_value=None):
            result = check_oauth_token()

            assert 'please run' in result['message'].lower()
            assert 'claude' in result['message'].lower()
            assert 'oauth login' in result['message'].lower()
