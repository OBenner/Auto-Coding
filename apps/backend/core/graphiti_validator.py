"""
Graphiti Setup Validator
=========================

Comprehensive validation for Graphiti memory system setup.
Tests configuration, database connectivity, and provider connections.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from integrations.graphiti.config import GraphitiConfig

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""

    success: bool
    message: str
    fix_command: str | None = None


@dataclass
class GraphitiValidationReport:
    """Complete validation report for Graphiti setup."""

    enabled: bool
    config_valid: bool
    database_available: bool
    embedder_valid: bool
    embedder_connected: bool
    errors: list[str]
    warnings: list[str]
    fixes: list[str]

    def is_operational(self) -> bool:
        """Check if Graphiti is fully operational."""
        return (
            self.enabled and self.config_valid and self.database_available
            # Embedder is optional - keyword search works without it
        )

    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "enabled": self.enabled,
            "config_valid": self.config_valid,
            "database_available": self.database_available,
            "embedder_valid": self.embedder_valid,
            "embedder_connected": self.embedder_connected,
            "operational": self.is_operational(),
            "errors": self.errors,
            "warnings": self.warnings,
            "fixes": self.fixes,
        }


def validate_graphiti_setup(verbose: bool = False) -> GraphitiValidationReport:
    """
    Validate complete Graphiti setup.

    Args:
        verbose: If True, print detailed validation steps

    Returns:
        GraphitiValidationReport with validation results
    """
    errors = []
    warnings = []
    fixes = []

    if verbose:
        print("Validating Graphiti memory system setup...")

    # Step 1: Check if Graphiti is enabled
    try:
        from integrations.graphiti.config import GraphitiConfig
    except ImportError:
        errors.append("Cannot import GraphitiConfig - check installation")
        fixes.append("pip install -r requirements.txt")
        return GraphitiValidationReport(
            enabled=False,
            config_valid=False,
            database_available=False,
            embedder_valid=False,
            embedder_connected=False,
            errors=errors,
            warnings=warnings,
            fixes=fixes,
        )

    config = GraphitiConfig.from_env()

    if not config.enabled:
        errors.append("GRAPHITI_ENABLED not set to true")
        fixes.append("Set GRAPHITI_ENABLED=true in your .env file")
        return GraphitiValidationReport(
            enabled=False,
            config_valid=False,
            database_available=False,
            embedder_valid=False,
            embedder_connected=False,
            errors=errors,
            warnings=warnings,
            fixes=fixes,
        )

    if verbose:
        print(f"✓ Graphiti enabled: {config.get_provider_summary()}")

    # Step 2: Validate configuration
    config_errors = config.get_validation_errors()
    if config_errors:
        # These are warnings for embedder - not blockers
        warnings.extend(config_errors)
        if verbose:
            print(f"! Embedder configuration warnings: {len(config_errors)}")
            for error in config_errors:
                print(f"  - {error}")

    config_valid = config.is_valid()

    # Step 3: Check database backend availability
    db_result = _validate_database_backend(verbose)
    if not db_result.success:
        errors.append(db_result.message)
        if db_result.fix_command:
            fixes.append(db_result.fix_command)

    # Step 4: Validate embedder configuration (optional)
    embedder_valid = False
    embedder_connected = False

    if config_errors:
        # Embedder not properly configured
        if verbose:
            print("! Embedder not configured - keyword search will be used")
        warnings.append(
            "Embedder not configured - memory will use keyword search fallback"
        )
    else:
        embedder_valid = True
        if verbose:
            print("✓ Embedder configuration valid")

        # Step 5: Test embedder connection (async)
        embedder_result = _test_embedder_connection(config, verbose)
        if embedder_result.success:
            embedder_connected = True
            if verbose:
                print("✓ Embedder connection successful")
        else:
            warnings.append(embedder_result.message)
            if embedder_result.fix_command:
                fixes.append(embedder_result.fix_command)
            if verbose:
                print(f"! {embedder_result.message}")

    # Generate report
    report = GraphitiValidationReport(
        enabled=True,
        config_valid=config_valid,
        database_available=db_result.success,
        embedder_valid=embedder_valid,
        embedder_connected=embedder_connected,
        errors=errors,
        warnings=warnings,
        fixes=fixes,
    )

    if verbose:
        if report.is_operational():
            print("\n✓ Graphiti is fully operational")
        else:
            print("\n✗ Graphiti has validation errors")

    return report


def _validate_database_backend(verbose: bool = False) -> ValidationResult:
    """
    Validate that database backend (LadybugDB or Kuzu) is available.

    Args:
        verbose: If True, print validation steps

    Returns:
        ValidationResult
    """
    # Check Python version for LadybugDB
    if sys.version_info < (3, 12):
        return ValidationResult(
            success=False,
            message="LadybugDB requires Python 3.12+",
            fix_command="Upgrade to Python 3.12 or newer",
        )

    # Try importing LadybugDB first (preferred)
    try:
        import real_ladybug  # noqa: F401

        if verbose:
            print("✓ LadybugDB available")
        return ValidationResult(success=True, message="LadybugDB available")
    except ImportError:
        pass

    # Fall back to Kuzu
    try:
        import kuzu  # noqa: F401

        if verbose:
            print("✓ Kuzu available")
        return ValidationResult(success=True, message="Kuzu available")
    except ImportError:
        pass

    # Neither backend available
    return ValidationResult(
        success=False,
        message="No graph database backend available (need real_ladybug or kuzu)",
        fix_command="pip install real-ladybug-db  # or: pip install kuzu",
    )


def _test_embedder_connection(
    config: GraphitiConfig, verbose: bool = False
) -> ValidationResult:
    """
    Test embedder provider connection.

    Args:
        config: GraphitiConfig to test
        verbose: If True, print test steps

    Returns:
        ValidationResult
    """
    try:
        # Import async validators
        from integrations.graphiti.providers_pkg.validators import (
            test_embedder_connection,
            test_ollama_connection,
        )
    except ImportError as e:
        return ValidationResult(
            success=False,
            message=f"Cannot import Graphiti validators: {e}",
            fix_command="pip install -r requirements.txt",
        )

    # Create a single event loop for all async operations
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Special handling for Ollama - test server connection first
        if config.embedder_provider == "ollama":
            if verbose:
                print(f"Testing Ollama connection at {config.ollama_base_url}...")

            success, message = loop.run_until_complete(
                test_ollama_connection(config.ollama_base_url)
            )

            if not success:
                return ValidationResult(
                    success=False,
                    message=f"Ollama server not reachable: {message}",
                    fix_command="Start Ollama server: ollama serve",
                )

        # Test embedder connection
        if verbose:
            print(f"Testing {config.embedder_provider} embedder connection...")

        success, message = loop.run_until_complete(test_embedder_connection(config))
    finally:
        loop.close()

    if not success:
        # Generate provider-specific fix command
        fix_command = _get_embedder_fix_command(config)
        return ValidationResult(success=False, message=message, fix_command=fix_command)

    return ValidationResult(success=True, message=message)


def _get_embedder_fix_command(config: GraphitiConfig) -> str:
    """
    Get provider-specific fix command for embedder setup.

    Args:
        config: GraphitiConfig

    Returns:
        Fix command string
    """
    provider = config.embedder_provider

    if provider == "openai":
        return "Set OPENAI_API_KEY in your .env file"
    elif provider == "voyage":
        return "Set VOYAGE_API_KEY in your .env file"
    elif provider == "azure_openai":
        return (
            "Set AZURE_OPENAI_API_KEY, AZURE_OPENAI_BASE_URL, "
            "and AZURE_OPENAI_EMBEDDING_DEPLOYMENT in your .env file"
        )
    elif provider == "ollama":
        return (
            "1. Start Ollama: ollama serve\n"
            f"2. Pull embedding model: ollama pull {config.ollama_embedding_model}\n"
            "3. Set OLLAMA_EMBEDDING_DIM in your .env file"
        )
    elif provider == "google":
        return "Set GOOGLE_API_KEY in your .env file"
    elif provider == "openrouter":
        return "Set OPENROUTER_API_KEY in your .env file"
    else:
        return f"Configure {provider} provider credentials in your .env file"


def print_validation_report(report: GraphitiValidationReport) -> None:
    """
    Print formatted validation report.

    Args:
        report: GraphitiValidationReport to print
    """
    print("\n" + "=" * 60)
    print("Graphiti Memory System Validation Report")
    print("=" * 60)

    print(
        f"\nStatus: {'✓ OPERATIONAL' if report.is_operational() else '✗ NOT OPERATIONAL'}"
    )

    print("\nChecks:")
    print(f"  Enabled:              {'✓' if report.enabled else '✗'}")
    print(f"  Configuration:        {'✓' if report.config_valid else '✗'}")
    print(f"  Database Backend:     {'✓' if report.database_available else '✗'}")
    print(f"  Embedder Config:      {'✓' if report.embedder_valid else '!'}")
    print(f"  Embedder Connection:  {'✓' if report.embedder_connected else '!'}")

    if report.errors:
        print(f"\n✗ Errors ({len(report.errors)}):")
        for error in report.errors:
            print(f"  - {error}")

    if report.warnings:
        print(f"\n! Warnings ({len(report.warnings)}):")
        for warning in report.warnings:
            print(f"  - {warning}")

    if report.fixes:
        print("\nRecommended Fixes:")
        for i, fix in enumerate(report.fixes, 1):
            print(f"  {i}. {fix}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # Allow running as standalone validator
    report = validate_graphiti_setup(verbose=True)
    print_validation_report(report)
    sys.exit(0 if report.is_operational() else 1)
