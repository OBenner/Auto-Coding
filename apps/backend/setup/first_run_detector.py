"""
First-run detection for Auto Code setup wizard.

Detects whether Auto Code has been configured by checking for:
1. .env file in the backend directory
2. Setup completion marker at ~/.auto-claude/.setup_complete

If neither exists, the setup wizard should be launched.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def detect_first_run() -> bool:
    """
    Detect if this is the first run of Auto Code.

    Returns:
        bool: True if setup is needed (first run), False if already configured.

    The function checks for two indicators that setup has been completed:
    - .env file in apps/backend/ directory
    - Setup completion marker at ~/.auto-claude/.setup_complete

    If either exists, setup is considered complete.
    """
    try:
        # Get the backend directory (where .env should be)
        backend_dir = Path(__file__).parent.parent.resolve()
        env_file = backend_dir / ".env"

        # Check for .env file
        if env_file.exists():
            logger.debug(f".env file found at {env_file}")
            return False

        # Check for setup completion marker in user's home directory
        home_dir = Path(os.path.expanduser("~"))
        setup_marker = home_dir / ".auto-claude" / ".setup_complete"

        if setup_marker.exists():
            logger.debug(f"Setup marker found at {setup_marker}")
            return False

        # Neither exists - this is a first run
        logger.info("First run detected: no .env or setup marker found")
        return True

    except Exception as e:
        # If we can't determine, assume first run to be safe
        logger.warning(f"Error detecting first run status: {e}. Assuming first run.")
        return True


def mark_setup_complete() -> bool:
    """
    Create the setup completion marker file.

    Returns:
        bool: True if marker was created successfully, False otherwise.

    Creates the ~/.auto-claude/.setup_complete file to indicate that
    setup has been completed successfully.
    """
    try:
        home_dir = Path(os.path.expanduser("~"))
        auto_claude_dir = home_dir / ".auto-claude"
        setup_marker = auto_claude_dir / ".setup_complete"

        # Create directory if it doesn't exist
        auto_claude_dir.mkdir(parents=True, exist_ok=True)

        # Create marker file with timestamp
        from datetime import UTC, datetime

        timestamp = datetime.now(UTC).isoformat()
        setup_marker.write_text(f"Setup completed at: {timestamp}\n")

        logger.info(f"Setup completion marker created at {setup_marker}")
        return True

    except Exception as e:
        logger.error(f"Failed to create setup marker: {e}")
        return False


def reset_first_run() -> bool:
    """
    Remove the setup completion marker to force wizard to run again.

    Returns:
        bool: True if marker was removed, False if it didn't exist or couldn't be removed.

    This is useful for testing or when a user wants to reconfigure Auto Code.
    Note: This does NOT remove the .env file.
    """
    try:
        home_dir = Path(os.path.expanduser("~"))
        setup_marker = home_dir / ".auto-claude" / ".setup_complete"

        if setup_marker.exists():
            setup_marker.unlink()
            logger.info(f"Setup marker removed from {setup_marker}")
            return True
        else:
            logger.debug("Setup marker does not exist, nothing to remove")
            return False

    except Exception as e:
        logger.error(f"Failed to remove setup marker: {e}")
        return False
