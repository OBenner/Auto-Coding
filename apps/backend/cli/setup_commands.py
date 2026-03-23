"""
Setup Commands
==============

CLI commands for environment setup and synchronization.
"""

from pathlib import Path

from ui import (
    Icons,
    icon,
)

from .utils import print_banner


def handle_setup_command(
    project_dir: Path | str = ".",
    dry_run: bool = False,
    skip_install: bool = False,
    skip_config: bool = False,
    skip_validation: bool = False,
    interactive: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Handle the --setup command: one-command environment synchronization.

    Orchestrates:
    1. Package manager detection
    2. Dependency installation
    3. Environment configuration (.env setup)
    4. Graphiti memory validation
    5. LLM provider connection testing
    6. Setup report generation

    Args:
        project_dir: Root directory of the project (default: current directory)
        dry_run: If True, show what would be done without executing
        skip_install: If True, skip dependency installation
        skip_config: If True, skip environment configuration
        skip_validation: If True, skip Graphiti and provider validation
        interactive: If True, prompt for environment variable values
        verbose: If True, print detailed progress

    Returns:
        Dictionary with setup results:
        - success: bool - Overall success status
        - duration: str - Time taken (e.g., "2m 15s")
        - summary: str - One-line summary
        - issues: list - Critical issues found
        - warnings: list - Non-critical warnings
        - fixes: list - Recommended fixes
        - report: str - Markdown report

    Example:
        >>> result = handle_setup_command(project_dir=".", dry_run=False)
        >>> if result["success"]:
        ...     print("✓ Environment ready!")
        ... else:
        ...     print(f"✗ Failed: {result['summary']}")
    """
    from core.env_sync import run_env_sync

    # Convert Path to string if needed
    project_path = Path(project_dir)

    # Print banner if verbose
    if verbose:
        print_banner()
        print("\n" + "=" * 70)
        print("  ENVIRONMENT SETUP")
        print("=" * 70)
        print(f"\n{icon(Icons.INFO)} Project: {project_path.resolve()}")
        if dry_run:
            print(f"{icon(Icons.INFO)} Mode: DRY-RUN (no changes will be made)")
        print()

    # Run environment sync
    try:
        result = run_env_sync(
            project_dir=str(project_path),
            dry_run=dry_run,
            interactive=interactive,
            skip_install=skip_install,
            skip_config=skip_config,
            skip_validation=skip_validation,
            verbose=verbose,
        )

        # Display summary
        if verbose:
            _display_result(result)

        return result

    except Exception as e:
        error_result = {
            "success": False,
            "duration": "0s",
            "summary": f"Setup failed: {str(e)}",
            "issues": [str(e)],
            "warnings": [],
            "fixes": [],
            "report": "",
        }

        if verbose:
            print(f"\n{icon(Icons.ERROR)} Setup failed with exception: {e}")
            import traceback

            print("\nTraceback:")
            traceback.print_exc()

        return error_result


def _display_result(result: dict) -> None:
    """Display verbose setup result output.

    Args:
        result: Dictionary with setup results from run_env_sync.
    """
    if result["success"]:
        print(f"\n{icon(Icons.SUCCESS)} Environment setup completed successfully!")
        print(f"   Duration: {result['duration']}")
    else:
        print(f"\n{icon(Icons.WARNING)} Environment setup completed with issues")
        print(f"   Duration: {result['duration']}")
        print(f"   Summary: {result['summary']}")

    # Show critical issues
    if result.get("issues"):
        print(f"\n{icon(Icons.ERROR)} Critical Issues:")
        for issue in result["issues"]:
            print(f"  - {issue}")

    # Show warnings
    if result.get("warnings"):
        print(f"\n{icon(Icons.WARNING)} Warnings:")
        for warning in result["warnings"]:
            print(f"  - {warning}")

    # Show recommended fixes
    if result.get("fixes"):
        print(f"\n{icon(Icons.INFO)} Recommended Fixes:")
        for i, fix in enumerate(result["fixes"], 1):
            print(f"  {i}. {fix}")

    # Show next steps
    if result["success"]:
        print(f"\n{icon(Icons.SUCCESS)} Next Steps:")
        print("  1. Review the setup report above")
        print("  2. Run your first build: python run.py --task 'your task'")
        print("  3. Check the Quick Start Guide for more information")
    else:
        print(f"\n{icon(Icons.INFO)} Next Steps:")
        print("  1. Review the issues and warnings above")
        print("  2. Apply the recommended fixes")
        print("  3. Run --setup again to verify")
