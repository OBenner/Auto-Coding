"""
Prevention Scanner Configuration
=================================

Configuration for the proactive issue prevention scanner system.
Controls which scanners to run, severity thresholds, and default behaviors.

Environment Variables:
    # Scanner Enable/Disable
    PREVENTION_SECURITY_ENABLED: Enable security scanning (default: true)
    PREVENTION_PERFORMANCE_ENABLED: Enable performance analysis (default: true)
    PREVENTION_BREAKING_CHANGES_ENABLED: Enable breaking change detection (default: false)
    PREVENTION_ARCHITECTURE_ENABLED: Enable architecture validation (default: true)

    # Severity Thresholds
    PREVENTION_BLOCK_ON_CRITICAL: Block on critical issues (default: true)
    PREVENTION_BLOCK_ON_HIGH: Block on high severity issues (default: false)
    PREVENTION_WARN_ON_MEDIUM: Warn on medium severity issues (default: true)

    # Scanner Behavior
    PREVENTION_FAIL_ON_SCAN_ERROR: Fail entire scan if one scanner errors (default: false)
    PREVENTION_SAVE_REPORTS: Save individual scanner reports (default: true)
"""

import os
from dataclasses import dataclass
from typing import Literal


# Default configuration values
DEFAULT_SECURITY_ENABLED = True
DEFAULT_PERFORMANCE_ENABLED = True
DEFAULT_BREAKING_CHANGES_ENABLED = False  # Requires old version for comparison
DEFAULT_ARCHITECTURE_ENABLED = True

DEFAULT_BLOCK_ON_CRITICAL = True
DEFAULT_BLOCK_ON_HIGH = False
DEFAULT_WARN_ON_MEDIUM = True

DEFAULT_FAIL_ON_SCAN_ERROR = False
DEFAULT_SAVE_REPORTS = True


SeverityLevel = Literal["critical", "high", "medium", "low"]


@dataclass
class PreventionConfig:
    """
    Configuration for proactive issue prevention scanner.

    Attributes:
        # Scanner Enable/Disable
        security_enabled: Whether to run security scanning
        performance_enabled: Whether to run performance analysis
        breaking_changes_enabled: Whether to run breaking change detection
        architecture_enabled: Whether to run architecture validation

        # Severity Thresholds
        block_on_critical: Block implementation on critical issues
        block_on_high: Block implementation on high severity issues
        warn_on_medium: Show warnings for medium severity issues

        # Scanner Behavior
        fail_on_scan_error: Fail entire scan if one scanner errors
        save_reports: Save individual scanner reports to spec_dir
    """

    # Scanner Enable/Disable
    security_enabled: bool = DEFAULT_SECURITY_ENABLED
    performance_enabled: bool = DEFAULT_PERFORMANCE_ENABLED
    breaking_changes_enabled: bool = DEFAULT_BREAKING_CHANGES_ENABLED
    architecture_enabled: bool = DEFAULT_ARCHITECTURE_ENABLED

    # Severity Thresholds
    block_on_critical: bool = DEFAULT_BLOCK_ON_CRITICAL
    block_on_high: bool = DEFAULT_BLOCK_ON_HIGH
    warn_on_medium: bool = DEFAULT_WARN_ON_MEDIUM

    # Scanner Behavior
    fail_on_scan_error: bool = DEFAULT_FAIL_ON_SCAN_ERROR
    save_reports: bool = DEFAULT_SAVE_REPORTS

    @classmethod
    def from_env(cls) -> "PreventionConfig":
        """Create config from environment variables."""

        def get_bool(key: str, default: bool) -> bool:
            """Helper to parse boolean environment variables."""
            value = os.environ.get(key, "").lower()
            if value in ("true", "1", "yes"):
                return True
            elif value in ("false", "0", "no"):
                return False
            return default

        return cls(
            # Scanner Enable/Disable
            security_enabled=get_bool(
                "PREVENTION_SECURITY_ENABLED", DEFAULT_SECURITY_ENABLED
            ),
            performance_enabled=get_bool(
                "PREVENTION_PERFORMANCE_ENABLED", DEFAULT_PERFORMANCE_ENABLED
            ),
            breaking_changes_enabled=get_bool(
                "PREVENTION_BREAKING_CHANGES_ENABLED", DEFAULT_BREAKING_CHANGES_ENABLED
            ),
            architecture_enabled=get_bool(
                "PREVENTION_ARCHITECTURE_ENABLED", DEFAULT_ARCHITECTURE_ENABLED
            ),
            # Severity Thresholds
            block_on_critical=get_bool(
                "PREVENTION_BLOCK_ON_CRITICAL", DEFAULT_BLOCK_ON_CRITICAL
            ),
            block_on_high=get_bool("PREVENTION_BLOCK_ON_HIGH", DEFAULT_BLOCK_ON_HIGH),
            warn_on_medium=get_bool("PREVENTION_WARN_ON_MEDIUM", DEFAULT_WARN_ON_MEDIUM),
            # Scanner Behavior
            fail_on_scan_error=get_bool(
                "PREVENTION_FAIL_ON_SCAN_ERROR", DEFAULT_FAIL_ON_SCAN_ERROR
            ),
            save_reports=get_bool("PREVENTION_SAVE_REPORTS", DEFAULT_SAVE_REPORTS),
        )

    @classmethod
    def default(cls) -> "PreventionConfig":
        """Create config with default values."""
        return cls()

    def is_valid(self) -> bool:
        """
        Check if config has valid values.

        Returns True if at least one scanner is enabled.
        """
        return (
            self.security_enabled
            or self.performance_enabled
            or self.breaking_changes_enabled
            or self.architecture_enabled
        )

    def get_validation_errors(self) -> list[str]:
        """Get list of validation errors for current configuration."""
        errors = []

        if not self.is_valid():
            errors.append("At least one scanner must be enabled")

        return errors

    def should_block(self, critical_count: int, high_count: int) -> bool:
        """
        Determine if issues should block implementation.

        Args:
            critical_count: Number of critical severity issues
            high_count: Number of high severity issues

        Returns:
            True if issues should block implementation
        """
        if self.block_on_critical and critical_count > 0:
            return True
        if self.block_on_high and high_count > 0:
            return True
        return False

    def should_warn(self, high_count: int, medium_count: int) -> bool:
        """
        Determine if issues should trigger warnings.

        Args:
            high_count: Number of high severity issues
            medium_count: Number of medium severity issues

        Returns:
            True if issues should trigger warnings
        """
        if not self.block_on_high and high_count > 0:
            return True
        if self.warn_on_medium and medium_count > 0:
            return True
        return False

    def get_enabled_scanners(self) -> list[str]:
        """
        Get list of enabled scanner names.

        Returns:
            List of enabled scanner names
        """
        scanners = []
        if self.security_enabled:
            scanners.append("security")
        if self.performance_enabled:
            scanners.append("performance")
        if self.breaking_changes_enabled:
            scanners.append("breaking_changes")
        if self.architecture_enabled:
            scanners.append("architecture")
        return scanners

    def get_summary(self) -> dict:
        """
        Get a summary of the current configuration.

        Returns:
            Dict with configuration summary
        """
        return {
            "enabled_scanners": self.get_enabled_scanners(),
            "blocking_policy": {
                "block_on_critical": self.block_on_critical,
                "block_on_high": self.block_on_high,
                "warn_on_medium": self.warn_on_medium,
            },
            "behavior": {
                "fail_on_scan_error": self.fail_on_scan_error,
                "save_reports": self.save_reports,
            },
        }


def load_prevention_config() -> PreventionConfig:
    """
    Load prevention scanner configuration from environment.

    Returns:
        PreventionConfig instance with values from environment
    """
    return PreventionConfig.from_env()


def is_prevention_enabled() -> bool:
    """
    Quick check if prevention scanner is enabled.

    Returns True if at least one scanner is enabled.
    """
    config = load_prevention_config()
    return config.is_valid()


def get_prevention_status() -> dict:
    """
    Get the current prevention scanner configuration status.

    Returns:
        Dict with status information:
            - enabled: bool (at least one scanner enabled)
            - enabled_scanners: list[str]
            - blocking_policy: dict
            - behavior: dict
            - errors: list (validation errors if any)
    """
    config = load_prevention_config()

    status = {
        "enabled": config.is_valid(),
        "enabled_scanners": config.get_enabled_scanners(),
        "blocking_policy": {
            "block_on_critical": config.block_on_critical,
            "block_on_high": config.block_on_high,
            "warn_on_medium": config.warn_on_medium,
        },
        "behavior": {
            "fail_on_scan_error": config.fail_on_scan_error,
            "save_reports": config.save_reports,
        },
        "errors": [],
    }

    # Get validation errors
    errors = config.get_validation_errors()
    if errors:
        status["errors"] = errors

    return status


def validate_prevention_config() -> tuple[bool, list[str]]:
    """
    Validate prevention scanner configuration from environment.

    Returns:
        Tuple of (is_valid, error_messages)
        - is_valid: True if configuration is valid
        - error_messages: List of validation error messages (empty if valid)
    """
    config = load_prevention_config()

    if not config.is_valid():
        errors = config.get_validation_errors()
        return False, errors

    return True, []
