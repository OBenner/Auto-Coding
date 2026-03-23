"""
Environment Sync Orchestrator
==============================

One-command environment setup for Auto Code projects.

Orchestrates:
1. Package manager detection
2. Dependency installation
3. Environment configuration (.env setup)
4. Graphiti memory validation
5. LLM provider connection testing
6. Setup report generation

Usage:
    from core.env_sync import run_env_sync

    # Interactive setup
    result = run_env_sync(project_dir=".", dry_run=False, interactive=True)

    # Non-interactive (CI/automation)
    result = run_env_sync(project_dir=".", dry_run=True, interactive=False)

    if result["success"]:
        print(f"✓ Environment ready ({result['duration']})")
    else:
        print(f"✗ Setup failed: {result['summary']}")
        for issue in result["issues"]:
            print(f"  - {issue}")
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EnvSyncResult:
    """Result of environment sync operation."""

    def __init__(self):
        self.success = False
        self.start_time = time.time()
        self.end_time: float | None = None

        # Phase results
        self.detection_result: dict[str, Any] | None = None
        self.installation_result: Any = None
        self.configuration_result: dict[str, Any] | None = None
        self.graphiti_result: Any = None
        self.provider_results: dict[str, Any] = {}

        # Issues and fixes
        self.issues: list[str] = []
        self.warnings: list[str] = []
        self.fixes: list[str] = []

    def finish(self, success: bool = True) -> None:
        """Mark sync as finished."""
        self.success = success
        self.end_time = time.time()

    def get_duration(self) -> str:
        """Get formatted duration string."""
        if self.end_time is None:
            duration = time.time() - self.start_time
        else:
            duration = self.end_time - self.start_time

        delta = timedelta(seconds=int(duration))
        minutes = delta.seconds // 60
        seconds = delta.seconds % 60

        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        installation = None
        if self.installation_result:
            installation = {
                "dry_run": self.installation_result.dry_run,
                "installed": len(self.installation_result.installed),
                "failed": len(self.installation_result.failed),
                "skipped": len(self.installation_result.skipped),
            }

        graphiti = None
        if self.graphiti_result and hasattr(self.graphiti_result, "to_dict"):
            graphiti = self.graphiti_result.to_dict()

        return {
            "success": self.success,
            "duration": self.get_duration(),
            "detection": self.detection_result,
            "installation": installation,
            "configuration": self.configuration_result,
            "graphiti": graphiti,
            "providers": self.provider_results,
            "issues": self.issues,
            "warnings": self.warnings,
            "fixes": self.fixes,
        }


def run_env_sync(
    project_dir: str = ".",
    dry_run: bool = False,
    interactive: bool = True,
    skip_install: bool = False,
    skip_config: bool = False,
    skip_validation: bool = False,
    verbose: bool = True,
) -> dict[str, Any]:
    """
    Run complete environment sync for Auto Code project.

    Args:
        project_dir: Root directory of the project (default: current directory)
        dry_run: If True, show what would be done without executing
        interactive: If True, prompt for environment variable values
        skip_install: If True, skip dependency installation
        skip_config: If True, skip environment configuration
        skip_validation: If True, skip Graphiti and provider validation
        verbose: If True, print detailed progress

    Returns:
        Dictionary with sync results:
        - success: bool - Overall success status
        - duration: str - Time taken (e.g., "2m 15s")
        - detection: dict - Detected package managers
        - installation: dict - Installation results
        - configuration: dict - Environment configuration results
        - graphiti: dict - Graphiti validation results
        - providers: dict - Provider test results
        - issues: list - Critical issues found
        - warnings: list - Non-critical warnings
        - fixes: list - Recommended fixes
        - report: str - Markdown report

    Example:
        >>> result = run_env_sync(project_dir=".", dry_run=False)
        >>> if result["success"]:
        ...     print("✓ Environment ready!")
        ... else:
        ...     print(f"✗ Failed: {result['summary']}")
    """
    result = EnvSyncResult()
    project_path = Path(project_dir).resolve()

    if verbose:
        print("=" * 70)
        print("Auto Code Environment Sync")
        print("=" * 70)
        if dry_run:
            print("\nDry-run mode: No changes will be made\n")

    try:
        # Phase 1: Package Manager Detection
        if verbose:
            print("\n[1/5] Detecting package managers...")

        result.detection_result = _detect_packages(project_path, verbose)

        # Phase 2: Dependency Installation
        if not skip_install:
            if verbose:
                print("\n[2/5] Installing dependencies...")

            result.installation_result = _install_dependencies(
                project_path,
                result.detection_result,
                dry_run,
                verbose,
            )

            # Collect installation issues
            if result.installation_result and result.installation_result.failed:
                for pm, directory, error in result.installation_result.failed:
                    result.issues.append(
                        f"Failed to install {pm} in {directory}: {error}"
                    )
        else:
            if verbose:
                print("\n[2/5] Skipping dependency installation (--skip-install)")

        # Phase 3: Environment Configuration
        if not skip_config:
            if verbose:
                print("\n[3/5] Configuring environment variables...")

            result.configuration_result = _configure_environment(
                project_path,
                interactive,
                dry_run,
                verbose,
            )

            # Collect configuration issues
            if result.configuration_result and not result.configuration_result.get(
                "success"
            ):
                for error in result.configuration_result.get("errors", []):
                    result.issues.append(f"Configuration error: {error}")
        else:
            if verbose:
                print("\n[3/5] Skipping environment configuration (--skip-config)")

        # Phase 4: Graphiti Validation
        if not skip_validation:
            if verbose:
                print("\n[4/5] Validating Graphiti memory system...")

            result.graphiti_result = _validate_graphiti(verbose)

            # Collect Graphiti issues
            if result.graphiti_result:
                result.issues.extend(result.graphiti_result.errors)
                result.warnings.extend(result.graphiti_result.warnings)
                result.fixes.extend(result.graphiti_result.fixes)
        else:
            if verbose:
                print("\n[4/5] Skipping Graphiti validation (--skip-validation)")

        # Phase 5: Provider Connection Testing
        if not skip_validation:
            if verbose:
                print("\n[5/5] Testing LLM provider connections...")

            result.provider_results = _test_providers(verbose)

            # Collect provider issues
            for provider, test_result in result.provider_results.items():
                if not test_result.success:
                    result.warnings.append(f"{provider}: {test_result.message}")
                    if test_result.fix_command:
                        result.fixes.append(f"{provider}: {test_result.fix_command}")
        else:
            if verbose:
                print("\n[5/5] Skipping provider validation (--skip-validation)")

        # Determine overall success
        # Success if no critical issues (warnings are OK)
        result.finish(success=len(result.issues) == 0)

        # Generate report
        report = _generate_report(result, project_path, dry_run)

        if verbose:
            print("\n" + "=" * 70)
            if result.success:
                print(
                    f"✓ Environment sync completed successfully ({result.get_duration()})"
                )
            else:
                print(
                    f"✗ Environment sync completed with issues ({result.get_duration()})"
                )
            print("=" * 70)

            if result.issues:
                print(f"\n✗ Critical Issues ({len(result.issues)}):")
                for issue in result.issues:
                    print(f"  - {issue}")

            if result.warnings:
                print(f"\n⚠ Warnings ({len(result.warnings)}):")
                for warning in result.warnings:
                    print(f"  - {warning}")

            if result.fixes:
                print("\nRecommended Fixes:")
                for i, fix in enumerate(result.fixes, 1):
                    print(f"  {i}. {fix}")

        # Return dictionary result
        return_dict = result.to_dict()
        return_dict["report"] = report
        return_dict["summary"] = _get_summary(result)

        return return_dict

    except Exception as e:
        logger.exception("Environment sync failed with exception")
        result.finish(success=False)
        result.issues.append(f"Unexpected error: {str(e)}")

        return {
            "success": False,
            "duration": result.get_duration(),
            "summary": f"Failed: {str(e)}",
            "detection": result.detection_result,
            "installation": None,
            "configuration": result.configuration_result,
            "graphiti": None,
            "providers": result.provider_results,
            "issues": result.issues,
            "warnings": result.warnings,
            "fixes": result.fixes,
            "report": "",
        }


def _detect_packages(project_path: Path, verbose: bool) -> dict[str, Any]:
    """Detect package managers in project."""
    try:
        from core.package_detector import detect_package_managers

        detected = detect_package_managers(str(project_path))

        if verbose:
            total_locations = sum(len(dirs) for dirs in detected.values())
            print(f"  Found {total_locations} package manager locations")

            for pm, directories in detected.items():
                if directories:
                    print(f"    - {pm}: {len(directories)} location(s)")

        return detected

    except Exception as e:
        logger.exception("Package detection failed")
        if verbose:
            print(f"  ✗ Failed: {e}")
        return {}


def _install_dependencies(
    project_path: Path,
    detected: dict[str, Any],
    dry_run: bool,
    verbose: bool,
) -> Any:
    """Install dependencies for detected package managers."""
    try:
        from core.dependency_installer import DependencyInstaller

        installer = DependencyInstaller(str(project_path))
        install_result = installer.install(detected, dry_run=dry_run)

        if verbose:
            _log_install_result(install_result, dry_run)

        return install_result

    except Exception as e:
        logger.exception("Dependency installation failed")
        if verbose:
            print(f"  ✗ Failed: {e}")
        return None


def _log_install_result(install_result: Any, dry_run: bool) -> None:
    """Display verbose installation result details.

    Args:
        install_result: InstallResult from DependencyInstaller.
        dry_run: Whether this was a dry-run.
    """
    if dry_run:
        print(f"  Would install {len(install_result.installed)} package manager(s)")
    elif install_result.success:
        print(f"  ✓ Installed {len(install_result.installed)} package manager(s)")
    else:
        print(f"  ✗ Installation issues: {len(install_result.failed)} failed")

    for pm, directory in install_result.installed:
        status = "Would install" if dry_run else "Installed"
        print(f"    - {status}: {pm} in {directory}")

    for pm, directory, reason in install_result.skipped:
        print(f"    - Skipped: {pm} in {directory} ({reason})")

    for pm, directory, error in install_result.failed:
        print(f"    - Failed: {pm} in {directory}")
        error_short = error[:100] + "..." if len(error) > 100 else error
        print(f"      Error: {error_short}")


def _configure_environment(
    project_path: Path,
    interactive: bool,
    dry_run: bool,
    verbose: bool,
) -> dict[str, Any]:
    """Configure environment variables from .env.example."""
    try:
        from core.env_configurator import EnvConfigurator

        configurator = EnvConfigurator(project_path)

        # Check if .env already exists
        if configurator.env_file.exists() and not interactive:
            if verbose:
                print("  ✓ .env file already exists")
            return {"success": True, "variables_configured": 0, "errors": []}

        # Create or update .env
        config_result = configurator.create_env_file(
            interactive=interactive,
            dry_run=dry_run,
        )

        if verbose:
            if config_result["success"]:
                if dry_run:
                    print(
                        f"  Would configure {config_result['variables_configured']} variables"
                    )
                else:
                    print(
                        f"  ✓ Configured {config_result['variables_configured']} variables"
                    )
            else:
                print("  ✗ Configuration failed")
                for error in config_result.get("errors", []):
                    print(f"    - {error}")

        return config_result

    except Exception as e:
        logger.exception("Environment configuration failed")
        if verbose:
            print(f"  ✗ Failed: {e}")
        return {"success": False, "errors": [str(e)]}


def _validate_graphiti(verbose: bool) -> Any:
    """Validate Graphiti memory system setup."""
    try:
        from core.graphiti_validator import validate_graphiti_setup

        graphiti_result = validate_graphiti_setup(verbose=False)

        if verbose:
            if graphiti_result.is_operational():
                print("  ✓ Graphiti operational")
            elif graphiti_result.enabled:
                print("  ⚠ Graphiti enabled but has issues")
            else:
                print("  ! Graphiti not enabled")

        return graphiti_result

    except Exception as e:
        logger.exception("Graphiti validation failed")
        if verbose:
            print(f"  ✗ Failed: {e}")
        return None


def _test_providers(verbose: bool) -> dict[str, Any]:
    """Test LLM provider connections."""
    try:
        from core.provider_tester import check_all_configured_providers

        provider_results = check_all_configured_providers()

        if verbose:
            if not provider_results:
                print("  ! No providers configured")
            else:
                for provider, test_result in provider_results.items():
                    status = "✓" if test_result.success else "✗"
                    print(f"  {status} {provider}: {test_result.message}")

        return provider_results

    except Exception as e:
        logger.exception("Provider testing failed")
        if verbose:
            print(f"  ✗ Failed: {e}")
        return {}


def _generate_report(result: EnvSyncResult, project_path: Path, dry_run: bool) -> str:
    """Generate markdown setup report."""
    lines = []

    lines.append("# Auto Code Environment Setup Report")
    lines.append("")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Project:** {project_path}")
    lines.append(f"**Duration:** {result.get_duration()}")
    lines.append(f"**Status:** {'✓ SUCCESS' if result.success else '✗ ISSUES FOUND'}")
    if dry_run:
        lines.append("**Mode:** DRY-RUN (no changes made)")
    lines.append("")

    # Environment section
    lines.append("## Environment")
    lines.append("")

    # Package Managers
    if result.detection_result:
        lines.append("### Package Managers")
        lines.append("")
        for pm, directories in result.detection_result.items():
            if directories:
                lines.append(f"- **{pm}**: {len(directories)} location(s)")
                for directory in directories:
                    lines.append(f"  - `{directory}`")
        lines.append("")

    # Installation Results
    if result.installation_result:
        lines.append("### Dependency Installation")
        lines.append("")
        inst = result.installation_result
        lines.append(f"- Installed: {len(inst.installed)}")
        lines.append(f"- Failed: {len(inst.failed)}")
        lines.append(f"- Skipped: {len(inst.skipped)}")
        lines.append("")

        if inst.failed:
            lines.append("#### Failed Installations")
            lines.append("")
            for pm, directory, error in inst.failed:
                lines.append(f"- **{pm}** in `{directory}`")
                error_short = error[:200] + "..." if len(error) > 200 else error
                lines.append("  ```")
                lines.append(f"  {error_short}")
                lines.append("  ```")
            lines.append("")

    # Configuration section
    if result.configuration_result:
        lines.append("## Configuration")
        lines.append("")
        config = result.configuration_result
        if config.get("success"):
            lines.append(
                f"- ✓ Environment variables: {config.get('variables_configured', 0)} configured"
            )
        else:
            lines.append("- ✗ Configuration failed")
            for error in config.get("errors", []):
                lines.append(f"  - {error}")
        lines.append("")

    # Graphiti section
    if result.graphiti_result:
        lines.append("## Graphiti Memory System")
        lines.append("")
        gr = result.graphiti_result
        lines.append(f"- Enabled: {'✓' if gr.enabled else '✗'}")
        lines.append(f"- Configuration: {'✓' if gr.config_valid else '✗'}")
        lines.append(f"- Database: {'✓' if gr.database_available else '✗'}")
        lines.append(f"- Embedder: {'✓' if gr.embedder_valid else '!'}")
        lines.append(f"- Connection: {'✓' if gr.embedder_connected else '!'}")
        lines.append("")

    # Providers section
    if result.provider_results:
        lines.append("## LLM Providers")
        lines.append("")
        for provider, test_result in result.provider_results.items():
            status = "✓" if test_result.success else "✗"
            lines.append(f"- {status} **{provider}**: {test_result.message}")
        lines.append("")

    # Issues section
    if result.issues:
        lines.append("## Issues")
        lines.append("")
        for issue in result.issues:
            lines.append(f"- ✗ {issue}")
        lines.append("")

    # Warnings section
    if result.warnings:
        lines.append("## Warnings")
        lines.append("")
        for warning in result.warnings:
            lines.append(f"- ⚠ {warning}")
        lines.append("")

    # Next Steps
    if result.fixes:
        lines.append("## Recommended Fixes")
        lines.append("")
        for i, fix in enumerate(result.fixes, 1):
            lines.append(f"{i}. {fix}")
        lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    if result.success:
        lines.append("✓ Environment is ready for development")
    else:
        lines.append("✗ Environment has issues that need to be resolved")
        lines.append("")
        lines.append("Please review the issues and apply recommended fixes.")
    lines.append("")

    return "\n".join(lines)


def _get_summary(result: EnvSyncResult) -> str:
    """Get one-line summary of sync result."""
    if result.success:
        return f"Environment ready ({result.get_duration()})"
    else:
        issue_count = len(result.issues)
        warning_count = len(result.warnings)
        return f"{issue_count} issue(s), {warning_count} warning(s)"
