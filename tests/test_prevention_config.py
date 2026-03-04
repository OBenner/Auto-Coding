#!/usr/bin/env python3
"""
Tests for Prevention Scanner Configuration
===========================================

Tests the prevention_config module which handles configuration
for the proactive issue prevention scanner system.
"""

import os

# Add apps/backend to path for imports
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from analysis.prevention_config import (
    DEFAULT_ARCHITECTURE_ENABLED,
    DEFAULT_BLOCK_ON_CRITICAL,
    DEFAULT_BLOCK_ON_HIGH,
    DEFAULT_BREAKING_CHANGES_ENABLED,
    DEFAULT_FAIL_ON_SCAN_ERROR,
    DEFAULT_PERFORMANCE_ENABLED,
    DEFAULT_SAVE_REPORTS,
    DEFAULT_SECURITY_ENABLED,
    DEFAULT_WARN_ON_MEDIUM,
    PreventionConfig,
    get_prevention_status,
    is_prevention_enabled,
    load_prevention_config,
    validate_prevention_config,
)


class TestPreventionConfig:
    """Test PreventionConfig dataclass."""

    def test_default_config(self):
        """Test creating config with default values."""
        config = PreventionConfig()

        assert config.security_enabled == DEFAULT_SECURITY_ENABLED
        assert config.performance_enabled == DEFAULT_PERFORMANCE_ENABLED
        assert config.breaking_changes_enabled == DEFAULT_BREAKING_CHANGES_ENABLED
        assert config.architecture_enabled == DEFAULT_ARCHITECTURE_ENABLED
        assert config.block_on_critical == DEFAULT_BLOCK_ON_CRITICAL
        assert config.block_on_high == DEFAULT_BLOCK_ON_HIGH
        assert config.warn_on_medium == DEFAULT_WARN_ON_MEDIUM
        assert config.fail_on_scan_error == DEFAULT_FAIL_ON_SCAN_ERROR
        assert config.save_reports == DEFAULT_SAVE_REPORTS

    def test_custom_config(self):
        """Test creating config with custom values."""
        config = PreventionConfig(
            security_enabled=False,
            performance_enabled=False,
            breaking_changes_enabled=True,
            architecture_enabled=False,
            block_on_critical=False,
            block_on_high=True,
            warn_on_medium=False,
            fail_on_scan_error=True,
            save_reports=False,
        )

        assert config.security_enabled is False
        assert config.performance_enabled is False
        assert config.breaking_changes_enabled is True
        assert config.architecture_enabled is False
        assert config.block_on_critical is False
        assert config.block_on_high is True
        assert config.warn_on_medium is False
        assert config.fail_on_scan_error is True
        assert config.save_reports is False

    def test_from_env_with_no_env_vars(self):
        """Test from_env with no environment variables set."""
        with patch.dict(os.environ, {}, clear=True):
            config = PreventionConfig.from_env()

            # Should use defaults
            assert config.security_enabled == DEFAULT_SECURITY_ENABLED
            assert config.performance_enabled == DEFAULT_PERFORMANCE_ENABLED
            assert config.breaking_changes_enabled == DEFAULT_BREAKING_CHANGES_ENABLED
            assert config.architecture_enabled == DEFAULT_ARCHITECTURE_ENABLED

    def test_from_env_with_true_values(self):
        """Test from_env with environment variables set to true."""
        env = {
            "PREVENTION_SECURITY_ENABLED": "true",
            "PREVENTION_PERFORMANCE_ENABLED": "1",
            "PREVENTION_BREAKING_CHANGES_ENABLED": "yes",
            "PREVENTION_ARCHITECTURE_ENABLED": "TRUE",
            "PREVENTION_BLOCK_ON_CRITICAL": "1",
            "PREVENTION_BLOCK_ON_HIGH": "true",
            "PREVENTION_WARN_ON_MEDIUM": "YES",
            "PREVENTION_FAIL_ON_SCAN_ERROR": "True",
            "PREVENTION_SAVE_REPORTS": "yes",
        }

        with patch.dict(os.environ, env, clear=True):
            config = PreventionConfig.from_env()

            assert config.security_enabled is True
            assert config.performance_enabled is True
            assert config.breaking_changes_enabled is True
            assert config.architecture_enabled is True
            assert config.block_on_critical is True
            assert config.block_on_high is True
            assert config.warn_on_medium is True
            assert config.fail_on_scan_error is True
            assert config.save_reports is True

    def test_from_env_with_false_values(self):
        """Test from_env with environment variables set to false."""
        env = {
            "PREVENTION_SECURITY_ENABLED": "false",
            "PREVENTION_PERFORMANCE_ENABLED": "0",
            "PREVENTION_BREAKING_CHANGES_ENABLED": "no",
            "PREVENTION_ARCHITECTURE_ENABLED": "FALSE",
            "PREVENTION_BLOCK_ON_CRITICAL": "0",
            "PREVENTION_BLOCK_ON_HIGH": "false",
            "PREVENTION_WARN_ON_MEDIUM": "NO",
            "PREVENTION_FAIL_ON_SCAN_ERROR": "False",
            "PREVENTION_SAVE_REPORTS": "no",
        }

        with patch.dict(os.environ, env, clear=True):
            config = PreventionConfig.from_env()

            assert config.security_enabled is False
            assert config.performance_enabled is False
            assert config.breaking_changes_enabled is False
            assert config.architecture_enabled is False
            assert config.block_on_critical is False
            assert config.block_on_high is False
            assert config.warn_on_medium is False
            assert config.fail_on_scan_error is False
            assert config.save_reports is False

    def test_from_env_with_invalid_values_uses_defaults(self):
        """Test from_env with invalid values falls back to defaults."""
        env = {
            "PREVENTION_SECURITY_ENABLED": "invalid",
            "PREVENTION_PERFORMANCE_ENABLED": "maybe",
        }

        with patch.dict(os.environ, env, clear=True):
            config = PreventionConfig.from_env()

            # Should use defaults for invalid values
            assert config.security_enabled == DEFAULT_SECURITY_ENABLED
            assert config.performance_enabled == DEFAULT_PERFORMANCE_ENABLED

    def test_default_classmethod(self):
        """Test default() classmethod returns defaults."""
        config = PreventionConfig.default()

        assert config.security_enabled == DEFAULT_SECURITY_ENABLED
        assert config.performance_enabled == DEFAULT_PERFORMANCE_ENABLED
        assert config.breaking_changes_enabled == DEFAULT_BREAKING_CHANGES_ENABLED
        assert config.architecture_enabled == DEFAULT_ARCHITECTURE_ENABLED

    def test_is_valid_with_all_disabled(self):
        """Test is_valid returns False when all scanners are disabled."""
        config = PreventionConfig(
            security_enabled=False,
            performance_enabled=False,
            breaking_changes_enabled=False,
            architecture_enabled=False,
        )

        assert config.is_valid() is False

    def test_is_valid_with_one_enabled(self):
        """Test is_valid returns True when at least one scanner is enabled."""
        config = PreventionConfig(
            security_enabled=True,
            performance_enabled=False,
            breaking_changes_enabled=False,
            architecture_enabled=False,
        )

        assert config.is_valid() is True

    def test_is_valid_with_all_enabled(self):
        """Test is_valid returns True when all scanners are enabled."""
        config = PreventionConfig(
            security_enabled=True,
            performance_enabled=True,
            breaking_changes_enabled=True,
            architecture_enabled=True,
        )

        assert config.is_valid() is True

    def test_get_validation_errors_with_all_disabled(self):
        """Test get_validation_errors returns error when all disabled."""
        config = PreventionConfig(
            security_enabled=False,
            performance_enabled=False,
            breaking_changes_enabled=False,
            architecture_enabled=False,
        )

        errors = config.get_validation_errors()

        assert len(errors) == 1
        assert "At least one scanner must be enabled" in errors[0]

    def test_get_validation_errors_with_valid_config(self):
        """Test get_validation_errors returns empty list for valid config."""
        config = PreventionConfig(security_enabled=True)

        errors = config.get_validation_errors()

        assert len(errors) == 0

    def test_should_block_with_critical_issues(self):
        """Test should_block returns True when critical issues and block_on_critical."""
        config = PreventionConfig(block_on_critical=True, block_on_high=False)

        assert config.should_block(critical_count=1, high_count=0) is True
        assert config.should_block(critical_count=5, high_count=3) is True

    def test_should_block_with_high_issues(self):
        """Test should_block returns True when high issues and block_on_high."""
        config = PreventionConfig(block_on_critical=False, block_on_high=True)

        assert config.should_block(critical_count=0, high_count=1) is True
        assert config.should_block(critical_count=0, high_count=5) is True

    def test_should_block_with_both_critical_and_high(self):
        """Test should_block with both critical and high issues."""
        config = PreventionConfig(block_on_critical=True, block_on_high=True)

        assert config.should_block(critical_count=1, high_count=1) is True
        assert config.should_block(critical_count=1, high_count=0) is True
        assert config.should_block(critical_count=0, high_count=1) is True

    def test_should_block_returns_false_when_no_blocking_issues(self):
        """Test should_block returns False when no blocking issues."""
        config = PreventionConfig(block_on_critical=True, block_on_high=False)

        assert config.should_block(critical_count=0, high_count=5) is False

    def test_should_warn_with_high_issues_when_not_blocking(self):
        """Test should_warn returns True for high issues when not blocking on them."""
        config = PreventionConfig(block_on_high=False, warn_on_medium=False)

        assert config.should_warn(high_count=1, medium_count=0) is True

    def test_should_warn_with_medium_issues(self):
        """Test should_warn returns True when medium issues and warn_on_medium."""
        config = PreventionConfig(block_on_high=True, warn_on_medium=True)

        assert config.should_warn(high_count=0, medium_count=1) is True
        assert config.should_warn(high_count=0, medium_count=5) is True

    def test_should_warn_returns_false_when_no_warning_issues(self):
        """Test should_warn returns False when no warning issues."""
        config = PreventionConfig(block_on_high=True, warn_on_medium=False)

        assert config.should_warn(high_count=0, medium_count=5) is False

    def test_get_enabled_scanners_all_enabled(self):
        """Test get_enabled_scanners returns all when all enabled."""
        config = PreventionConfig(
            security_enabled=True,
            performance_enabled=True,
            breaking_changes_enabled=True,
            architecture_enabled=True,
        )

        scanners = config.get_enabled_scanners()

        assert len(scanners) == 4
        assert "security" in scanners
        assert "performance" in scanners
        assert "breaking_changes" in scanners
        assert "architecture" in scanners

    def test_get_enabled_scanners_partial(self):
        """Test get_enabled_scanners returns only enabled scanners."""
        config = PreventionConfig(
            security_enabled=True,
            performance_enabled=False,
            breaking_changes_enabled=True,
            architecture_enabled=False,
        )

        scanners = config.get_enabled_scanners()

        assert len(scanners) == 2
        assert "security" in scanners
        assert "breaking_changes" in scanners
        assert "performance" not in scanners
        assert "architecture" not in scanners

    def test_get_enabled_scanners_none(self):
        """Test get_enabled_scanners returns empty list when none enabled."""
        config = PreventionConfig(
            security_enabled=False,
            performance_enabled=False,
            breaking_changes_enabled=False,
            architecture_enabled=False,
        )

        scanners = config.get_enabled_scanners()

        assert len(scanners) == 0

    def test_get_summary(self):
        """Test get_summary returns expected structure."""
        config = PreventionConfig(
            security_enabled=True,
            performance_enabled=True,
            block_on_critical=True,
            block_on_high=False,
            warn_on_medium=True,
            fail_on_scan_error=False,
            save_reports=True,
        )

        summary = config.get_summary()

        assert "enabled_scanners" in summary
        assert "blocking_policy" in summary
        assert "behavior" in summary
        assert summary["blocking_policy"]["block_on_critical"] is True
        assert summary["blocking_policy"]["block_on_high"] is False
        assert summary["blocking_policy"]["warn_on_medium"] is True
        assert summary["behavior"]["fail_on_scan_error"] is False
        assert summary["behavior"]["save_reports"] is True


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_load_prevention_config(self):
        """Test load_prevention_config loads from environment."""
        env = {
            "PREVENTION_SECURITY_ENABLED": "true",
            "PREVENTION_PERFORMANCE_ENABLED": "false",
        }

        with patch.dict(os.environ, env, clear=True):
            config = load_prevention_config()

            assert isinstance(config, PreventionConfig)
            assert config.security_enabled is True
            assert config.performance_enabled is False

    def test_is_prevention_enabled_returns_true_when_valid(self):
        """Test is_prevention_enabled returns True for valid config."""
        env = {"PREVENTION_SECURITY_ENABLED": "true"}

        with patch.dict(os.environ, env, clear=True):
            assert is_prevention_enabled() is True

    def test_is_prevention_enabled_returns_false_when_invalid(self):
        """Test is_prevention_enabled returns False when all disabled."""
        env = {
            "PREVENTION_SECURITY_ENABLED": "false",
            "PREVENTION_PERFORMANCE_ENABLED": "false",
            "PREVENTION_BREAKING_CHANGES_ENABLED": "false",
            "PREVENTION_ARCHITECTURE_ENABLED": "false",
        }

        with patch.dict(os.environ, env, clear=True):
            assert is_prevention_enabled() is False

    def test_get_prevention_status(self):
        """Test get_prevention_status returns expected structure."""
        env = {
            "PREVENTION_SECURITY_ENABLED": "true",
            "PREVENTION_PERFORMANCE_ENABLED": "true",
        }

        with patch.dict(os.environ, env, clear=True):
            status = get_prevention_status()

            assert "enabled" in status
            assert "enabled_scanners" in status
            assert "blocking_policy" in status
            assert "behavior" in status
            assert "errors" in status
            assert status["enabled"] is True
            assert len(status["enabled_scanners"]) >= 2

    def test_get_prevention_status_with_errors(self):
        """Test get_prevention_status includes errors for invalid config."""
        env = {
            "PREVENTION_SECURITY_ENABLED": "false",
            "PREVENTION_PERFORMANCE_ENABLED": "false",
            "PREVENTION_BREAKING_CHANGES_ENABLED": "false",
            "PREVENTION_ARCHITECTURE_ENABLED": "false",
        }

        with patch.dict(os.environ, env, clear=True):
            status = get_prevention_status()

            assert status["enabled"] is False
            assert len(status["errors"]) > 0

    def test_validate_prevention_config_valid(self):
        """Test validate_prevention_config returns True for valid config."""
        env = {"PREVENTION_SECURITY_ENABLED": "true"}

        with patch.dict(os.environ, env, clear=True):
            is_valid, errors = validate_prevention_config()

            assert is_valid is True
            assert len(errors) == 0

    def test_validate_prevention_config_invalid(self):
        """Test validate_prevention_config returns False and errors for invalid config."""
        env = {
            "PREVENTION_SECURITY_ENABLED": "false",
            "PREVENTION_PERFORMANCE_ENABLED": "false",
            "PREVENTION_BREAKING_CHANGES_ENABLED": "false",
            "PREVENTION_ARCHITECTURE_ENABLED": "false",
        }

        with patch.dict(os.environ, env, clear=True):
            is_valid, errors = validate_prevention_config()

            assert is_valid is False
            assert len(errors) > 0
            assert any("At least one scanner must be enabled" in err for err in errors)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_should_block_with_zero_counts(self):
        """Test should_block with zero counts."""
        config = PreventionConfig(block_on_critical=True, block_on_high=True)

        assert config.should_block(critical_count=0, high_count=0) is False

    def test_should_warn_with_zero_counts(self):
        """Test should_warn with zero counts."""
        config = PreventionConfig(block_on_high=False, warn_on_medium=True)

        assert config.should_warn(high_count=0, medium_count=0) is False

    def test_config_with_all_scanners_disabled_except_breaking_changes(self):
        """Test configuration with only breaking_changes enabled."""
        config = PreventionConfig(
            security_enabled=False,
            performance_enabled=False,
            breaking_changes_enabled=True,
            architecture_enabled=False,
        )

        assert config.is_valid() is True
        scanners = config.get_enabled_scanners()
        assert scanners == ["breaking_changes"]
