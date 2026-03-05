"""
Setup Wizard Command
====================

Interactive setup wizard for first-time Auto Code users.
Guides through Python validation, authentication, Graphiti setup, .env creation, and test run.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Import UI utilities
# Import setup modules
from setup.env_creator import EnvConfig, create_env_file
from setup.first_run_detector import mark_setup_complete
from setup.graphiti_validator import validate_graphiti_config
from setup.hello_world_runner import run_hello_world_test
from setup.python_validator import validate_python_version
from ui import (
    Icons,
    bold,
    box,
    divider,
    error,
    highlight,
    icon,
    muted,
    print_key_value,
    success,
    warning,
)


def handle_setup_command(
    project_dir: Path,
    verbose: bool = False,
    skip_test: bool = False,
) -> None:
    """
    Handle the setup wizard command.

    Orchestrates the setup flow:
    1. Python version validation
    2. Claude SDK authentication check
    3. Graphiti memory configuration validation
    4. .env file creation
    5. Hello-world test run (optional)

    Args:
        project_dir: Project root directory
        verbose: Enable verbose output
        skip_test: Skip the hello-world test run
    """
    try:
        # Configure logging
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        # Print welcome banner
        _print_welcome_banner()

        # Step 1: Validate Python version
        if not _validate_python():
            sys.exit(1)

        # Step 2: Check Claude SDK authentication
        if not _check_authentication():
            sys.exit(1)

        # Step 3: Validate Graphiti configuration
        if not _validate_graphiti():
            sys.exit(1)

        # Step 4: Create .env file
        if not _create_env_file():
            sys.exit(1)

        # Step 5: Run hello-world test (optional)
        if not skip_test:
            if not _run_hello_world_test():
                sys.exit(1)

        # Mark setup as complete
        mark_setup_complete()

        # Print success message
        _print_success_message()

    except KeyboardInterrupt:
        print("\n")
        print(f"{icon(Icons.WARNING)} Setup wizard cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Setup wizard failed: {e}", exc_info=True)
        print(f"\n{icon(Icons.ERROR)} {error('Setup wizard failed:')}")
        print(f"  {error(str(e))}")
        print(
            f"\n{muted('For help, see: https://github.com/OBenner/Auto-Coding/blob/develop/guides/QUICK-START.md')}"
        )
        sys.exit(1)


def _print_welcome_banner() -> None:
    """Print welcome banner for setup wizard."""
    print("\n")
    print(box("Auto Code Setup Wizard", width=60))
    print()
    print("This wizard will guide you through setting up Auto Code.")
    print("The following will be validated:")
    print()
    print(f"  {icon(Icons.CHECKMARK)} Python 3.12+ installation")
    print(f"  {icon(Icons.CHECKMARK)} Claude SDK authentication")
    print(f"  {icon(Icons.CHECKMARK)} Graphiti memory system")
    print(f"  {icon(Icons.CHECKMARK)} Environment configuration (.env)")
    print(f"  {icon(Icons.CHECKMARK)} Hello-world test run")
    print()
    print(divider(width=60))
    print()


def _validate_python() -> bool:
    """
    Validate Python version.

    Returns:
        bool: True if validation passed, False otherwise.
    """
    print(f"{bold('Step 1:')} Validating Python version...")
    print()

    result = validate_python_version()

    if result["valid"]:
        print(f"  {icon(Icons.CHECKMARK)} {success('Python version OK')}")
        print_key_value("Version", result["version"], indent=4)
        print()
        return True
    else:
        print(f"  {icon(Icons.ERROR)} {error('Python version check failed')}")
        print()
        print(result["message"])
        print()
        print(f"{muted('Please upgrade Python and run setup again.')}")
        return False


def _check_authentication() -> bool:
    """
    Check Claude SDK authentication.

    Returns:
        bool: True if authentication is configured, False otherwise.
    """
    print(f"{bold('Step 2:')} Checking Claude SDK authentication...")
    print()

    try:
        from core.auth import get_auth_token

        token = get_auth_token()

        if token:
            print(f"  {icon(Icons.CHECKMARK)} {success('Authentication configured')}")
            print(f"    {muted('OAuth token found in system keychain')}")
            print()
            return True
        else:
            print(f"  {icon(Icons.WARNING)} {warning('No authentication token found')}")
            print()
            print("To authenticate with Claude SDK:")
            print()
            print(f"  1. Run: {highlight('claude')}")
            print(f"  2. Type: {highlight('/login')}")
            print("  3. Press Enter and complete OAuth flow in browser")
            print()
            print("After authenticating, run the setup wizard again.")
            return False

    except ImportError as e:
        print(
            f"  {icon(Icons.ERROR)} {error('Failed to import authentication module')}"
        )
        print(f"    {muted(str(e))}")
        return False
    except Exception as e:
        print(f"  {icon(Icons.ERROR)} {error('Authentication check failed')}")
        print(f"    {muted(str(e))}")
        return False


def _validate_graphiti() -> bool:
    """
    Validate Graphiti configuration.

    Returns:
        bool: True if validation passed, False otherwise.
    """
    print(f"{bold('Step 3:')} Validating Graphiti memory system...")
    print()

    result = validate_graphiti_config()

    if result["valid"]:
        if result["enabled"]:
            print(
                f"  {icon(Icons.CHECKMARK)} {success('Graphiti configured and ready')}"
            )
            print_key_value("LLM Provider", result["llm_provider"], indent=4)
            print_key_value("Embedder Provider", result["embedder_provider"], indent=4)
        else:
            print(
                f"  {icon(Icons.WARNING)} {warning('Graphiti is disabled (optional)')}"
            )
            print(f"    {muted('Memory features will not be available')}")
            print(
                f"    {muted('To enable: Set GRAPHITI_ENABLED=true in .env and configure providers')}"
            )
        print()
        return True
    else:
        print(f"  {icon(Icons.ERROR)} {error('Graphiti validation failed')}")
        print()
        if result["issues"]:
            print("Issues found:")
            for issue in result["issues"]:
                print(f"  - {error(issue)}")
        print()
        print("Graphiti is optional but recommended for better agent memory.")
        print("You can continue setup and configure Graphiti later.")
        print()

        # Ask if user wants to continue
        try:
            response = input(f"{highlight('Continue without Graphiti? (y/n):')} ")
            return response.lower().strip() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False


def _create_env_file() -> bool:
    """
    Create .env file with default configuration.

    Returns:
        bool: True if .env was created successfully, False otherwise.
    """
    print(f"{bold('Step 4:')} Creating .env configuration file...")
    print()

    # Create minimal .env with defaults
    # Users can edit it later to add optional integrations
    config: EnvConfig = {
        "graphiti_enabled": True,
        "graphiti_llm_provider": "openai",
        "graphiti_embedder_provider": "openai",
    }

    result = create_env_file(config=config, backup_existing=True, force=False)

    if result["success"]:
        print(f"  {icon(Icons.CHECKMARK)} {success('.env file created')}")
        print_key_value("Location", result["env_path"], indent=4)

        if result["backed_up"]:
            print(f"    {muted('Previous .env backed up')}")

        print()
        print(
            f"{muted('Note: Edit apps/backend/.env to configure optional integrations:')}"
        )
        print(f"{muted('  - Linear API (for issue tracking)')}")
        print(f"{muted('  - GitHub token (for PR automation)')}")
        print(f"{muted('  - Additional AI providers (OpenRouter, Ollama, etc.)')}")
        print()
        return True
    else:
        print(f"  {icon(Icons.ERROR)} {error('.env file creation failed')}")
        print(f"    {error(result['message'])}")
        return False


def _run_hello_world_test() -> bool:
    """
    Run hello-world test to verify setup.

    Returns:
        bool: True if test passed, False otherwise.
    """
    print(f"{bold('Step 5:')} Running hello-world test...")
    print()

    result = run_hello_world_test()

    if result["success"]:
        print(f"  {icon(Icons.CHECKMARK)} {success('All tests passed!')}")
        print()
        if result["steps_completed"]:
            print("  Completed steps:")
            for step in result["steps_completed"]:
                print(f"    {icon(Icons.CHECKMARK)} {step}")
        print()
        return True
    else:
        print(f"  {icon(Icons.ERROR)} {error('Test failed')}")
        print()
        if result["steps_completed"]:
            print("  Completed steps:")
            for step in result["steps_completed"]:
                print(f"    {icon(Icons.CHECKMARK)} {step}")
            print()
        if result["steps_failed"]:
            print("  Failed steps:")
            for step in result["steps_failed"]:
                print(f"    {icon(Icons.ERROR)} {step}")
            print()
        if result["error_message"]:
            print(f"  Error: {error(result['error_message'])}")
            print()
        return False


def _print_success_message() -> None:
    """Print success message and next steps."""
    print()
    print(divider(width=60))
    print()
    print(box(f"{icon(Icons.CHECKMARK)} Setup Complete!", width=60))
    print()
    print(f"{success('Auto Code is ready to use!')}")
    print()
    print("Next steps:")
    print()
    print(
        f"  1. Create a spec: {highlight('python apps/backend/spec_runner.py --interactive')}"
    )
    print(f"  2. Run a build: {highlight('python apps/backend/run.py --spec 001')}")
    print(
        f"  3. Review changes: {highlight('python apps/backend/run.py --spec 001 --review')}"
    )
    print(
        f"  4. Merge to project: {highlight('python apps/backend/run.py --spec 001 --merge')}"
    )
    print()
    print("Documentation:")
    print(
        f"  - Quick Start: {muted('https://github.com/OBenner/Auto-Coding/blob/develop/guides/QUICK-START.md')}"
    )
    print(
        f"  - User Guide: {muted('https://github.com/OBenner/Auto-Coding/blob/develop/guides/USER-GUIDE.md')}"
    )
    print()
    print(divider(width=60))
    print()
