#!/usr/bin/env python3
"""Tests for python_validator.py module."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from setup.python_validator import (
    validate_python_version,
    get_python_info,
    REQUIRED_PYTHON_VERSION,
)


class TestValidatePythonVersion:
    """Test suite for validate_python_version() function."""

    def test_validate_python_version_returns_dict(self):
        """Test that validation returns a dictionary with required keys."""
        result = validate_python_version()

        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'version' in result
        assert 'required_version' in result
        assert 'message' in result

    def test_validate_python_version_current_version(self):
        """Test validation with current Python version."""
        result = validate_python_version()

        assert isinstance(result['valid'], bool)
        assert isinstance(result['version'], str)
        assert isinstance(result['required_version'], str)
        assert isinstance(result['message'], str)

    def test_validate_python_version_required_version_is_3_12(self):
        """Test that required version is 3.12."""
        result = validate_python_version()

        assert result['required_version'] == '3.12'

    def test_validate_python_version_message_is_not_empty(self):
        """Test that message is never empty."""
        result = validate_python_version()

        assert len(result['message']) > 0

    def test_validate_python_version_exception_handling(self):
        """Test exception handling when version check fails."""
        with patch('setup.python_validator.sys.version_info', side_effect=Exception("Version error")):
            result = validate_python_version()

            assert result['valid'] is False
            assert result['version'] == 'unknown'
            assert 'Failed to validate Python version' in result['message']

    def test_validate_python_version_version_format(self):
        """Test that version string is in expected format."""
        result = validate_python_version()

        # Version should be in format X.Y.Z or "unknown"
        if result['version'] != 'unknown':
            parts = result['version'].split('.')
            assert len(parts) == 3
            # All parts should be numeric
            for part in parts:
                assert part.isdigit() or part.lstrip('-').isdigit()


class TestGetPythonInfo:
    """Test suite for get_python_info() function."""

    def test_get_python_info_returns_dict(self):
        """Test that get_python_info returns a dictionary."""
        info = get_python_info()

        assert isinstance(info, dict)

    def test_get_python_info_has_required_keys(self):
        """Test that get_python_info has all required keys."""
        info = get_python_info()

        assert 'version' in info
        assert 'executable' in info
        assert 'platform' in info
        assert 'implementation' in info

    def test_get_python_info_version_field(self):
        """Test that version field contains Python version."""
        info = get_python_info()

        assert isinstance(info['version'], str)
        assert len(info['version']) > 0
        # Should contain "Python" in the version string
        assert 'python' in info['version'].lower() or info['version'].startswith('3')

    def test_get_python_info_executable_field(self):
        """Test that executable field contains path or is empty."""
        info = get_python_info()

        assert isinstance(info['executable'], str)
        # If not empty, should contain 'python' in the path
        if info['executable']:
            assert 'python' in info['executable'].lower() or 'py.exe' in info['executable'].lower()

    def test_get_python_info_platform_field(self):
        """Test that platform field is valid."""
        info = get_python_info()

        assert isinstance(info['platform'], str)
        assert len(info['platform']) > 0
        # Should be a known platform
        assert info['platform'] in ['linux', 'darwin', 'win32', 'cygwin', 'msys']

    def test_get_python_info_implementation_field(self):
        """Test that implementation field is valid."""
        info = get_python_info()

        assert isinstance(info['implementation'], str)
        assert len(info['implementation']) > 0
        # Most common implementations
        assert info['implementation'] in ['cpython', 'pypy', 'jython', 'ironpython']

    def test_get_python_info_all_values_are_strings(self):
        """Test that all returned values are strings."""
        info = get_python_info()

        for key, value in info.items():
            assert isinstance(value, str), f"Value for {key} should be string, got {type(value)}"


class TestRequiredPythonVersion:
    """Test suite for REQUIRED_PYTHON_VERSION constant."""

    def test_required_python_version_is_tuple(self):
        """Test that REQUIRED_PYTHON_VERSION is a tuple."""
        assert isinstance(REQUIRED_PYTHON_VERSION, tuple)

    def test_required_python_version_length(self):
        """Test that REQUIRED_PYTHON_VERSION has 2 elements."""
        assert len(REQUIRED_PYTHON_VERSION) == 2

    def test_required_python_version_values(self):
        """Test that REQUIRED_PYTHON_VERSION is (3, 12)."""
        assert REQUIRED_PYTHON_VERSION == (3, 12)
