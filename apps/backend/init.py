"""
Auto Code project initialization utilities.

Handles first-time setup of .auto-claude directory and ensures proper gitignore configuration.
"""

import logging
import os
import subprocess
import threading
from pathlib import Path

from core.git_executable import get_git_executable

logger = logging.getLogger(__name__)

# Global reference to webhook server thread (for cleanup/monitoring)
_webhook_server_thread: threading.Thread | None = None
_webhook_server_started = False

# All entries that should be added to .gitignore for auto-claude projects
AUTO_CLAUDE_GITIGNORE_ENTRIES = [
    ".auto-claude/",
    ".auto-claude-security.json",
    ".auto-claude-status",
    ".claude_settings.json",
    ".worktrees/",
    ".security-key",
    "logs/security/",
]


def _run_webhook_server(
    spec_dir: Path,
    host: str,
    port: int,
) -> None:
    """
    Run the webhook server using uvicorn.

    This function is intended to be run in a background thread.

    Args:
        spec_dir: Directory containing webhook configurations
        host: Host to bind to (e.g., "0.0.0.0" or "127.0.0.1")
        port: Port to listen on
    """
    try:
        # Import here to avoid dependency issues if webhooks aren't used
        import uvicorn
        from integrations.webhooks.server import create_webhook_server

        # Create FastAPI app
        app = create_webhook_server(spec_dir=spec_dir)

        # Run server (blocking call - runs in background thread)
        logger.info(f"Starting webhook server on {host}:{port}")
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
        )
    except Exception as e:
        logger.error(f"Failed to start webhook server: {e}")
        # Don't raise - let the main application continue


def start_webhook_server_if_enabled(spec_dir: Path) -> bool:
    """
    Start the webhook server in a background thread if enabled.

    The server is started if the WEBHOOKS_ENABLED environment variable is set to "true".
    The server runs on the host and port specified by WEBHOOK_HOST and WEBHOOK_PORT
    environment variables (default: 127.0.0.1:8080).

    Args:
        spec_dir: Directory containing webhook configurations

    Returns:
        True if webhook server was started, False otherwise
    """
    global _webhook_server_thread, _webhook_server_started

    # Check if already started
    if _webhook_server_started:
        logger.debug("Webhook server already started")
        return True

    # Check if webhooks are enabled
    webhooks_enabled = os.getenv("WEBHOOKS_ENABLED", "").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )
    if not webhooks_enabled:
        logger.debug("Webhooks not enabled (set WEBHOOKS_ENABLED=true to enable)")
        return False

    # Get host and port from environment
    webhook_host = os.getenv("WEBHOOK_HOST", "127.0.0.1")
    try:
        webhook_port = int(os.getenv("WEBHOOK_PORT", "8080"))
    except ValueError:
        logger.warning("Invalid WEBHOOK_PORT value, falling back to 8080")
        webhook_port = 8080

    logger.info(f"Webhooks enabled - starting server on {webhook_host}:{webhook_port}")

    # Start server in background thread
    _webhook_server_thread = threading.Thread(
        target=_run_webhook_server,
        args=(spec_dir, webhook_host, webhook_port),
        daemon=True,  # Daemon thread will be killed when main process exits
        name="webhook-server",
    )
    _webhook_server_thread.start()
    _webhook_server_started = True

    logger.info(f"Webhook server started in background thread (port: {webhook_port})")
    return True


def _entry_exists_in_gitignore(lines: list[str], entry: str) -> bool:
    """Check if an entry already exists in gitignore (handles trailing slash variations)."""
    entry_normalized = entry.rstrip("/")
    for line in lines:
        line_stripped = line.strip()
        # Match both "entry" and "entry/"
        if (
            line_stripped == entry
            or line_stripped == entry_normalized
            or line_stripped == entry_normalized + "/"
        ):
            return True
    return False


def ensure_gitignore_entry(project_dir: Path, entry: str = ".auto-claude/") -> bool:
    """
    Ensure an entry exists in the project's .gitignore file.

    Creates .gitignore if it doesn't exist.

    Args:
        project_dir: The project root directory
        entry: The gitignore entry to add (default: ".auto-claude/")

    Returns:
        True if entry was added, False if it already existed
    """
    gitignore_path = project_dir / ".gitignore"

    # Check if .gitignore exists and if entry is already present
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        if _entry_exists_in_gitignore(lines, entry):
            return False  # Already exists

        # Entry doesn't exist, append it
        # Ensure file ends with newline before adding our entry
        if content and not content.endswith("\n"):
            content += "\n"

        # Add a comment and the entry
        content += "\n# Auto Code data directory\n"
        content += entry + "\n"

        gitignore_path.write_text(content, encoding="utf-8")
        return True
    else:
        # Create new .gitignore with the entry
        content = "# Auto Code data directory\n"
        content += entry + "\n"

        gitignore_path.write_text(content, encoding="utf-8")
        return True


def _is_git_repo(project_dir: Path) -> bool:
    """Check if the directory is a git repository."""
    try:
        result = subprocess.run(
            [get_git_executable(), "rev-parse", "--is-inside-work-tree"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception as e:
        logger.debug("Git repo check failed: %s", e)
        return False


def _commit_gitignore(project_dir: Path) -> bool:
    """
    Commit .gitignore changes with a standard message.

    FIX (#1087): Auto-commit .gitignore changes to prevent merge failures.
    Without this, merging tasks fails with "local changes would be overwritten".

    Args:
        project_dir: The project root directory

    Returns:
        True if commit succeeded, False otherwise
    """
    if not _is_git_repo(project_dir):
        return False

    try:
        # Use LC_ALL=C to ensure English git output for reliable parsing
        git_env = {**os.environ, "LC_ALL": "C"}

        # Stage .gitignore
        result = subprocess.run(
            [get_git_executable(), "add", ".gitignore"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
            env=git_env,
        )
        if result.returncode != 0:
            return False

        # Commit with standard message - explicitly specify .gitignore to avoid
        # committing other staged files the user may have
        result = subprocess.run(
            [
                get_git_executable(),
                "commit",
                ".gitignore",
                "-m",
                "chore: add auto-claude entries to .gitignore",
            ],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
            env=git_env,
        )
        # Return True even if commit "fails" due to nothing to commit
        # Check both stdout and stderr as message location varies by git version
        combined_output = result.stdout + result.stderr
        return result.returncode == 0 or "nothing to commit" in combined_output

    except Exception as e:
        logger.debug("Git commit failed: %s", e)
        return False


def ensure_all_gitignore_entries(
    project_dir: Path, auto_commit: bool = False
) -> list[str]:
    """
    Ensure all auto-claude related entries exist in the project's .gitignore file.

    Creates .gitignore if it doesn't exist.

    Args:
        project_dir: The project root directory
        auto_commit: If True, automatically commit the .gitignore changes

    Returns:
        List of entries that were added (empty if all already existed)
    """
    gitignore_path = project_dir / ".gitignore"
    added_entries: list[str] = []

    # Read existing content or start fresh
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        lines = content.splitlines()
    else:
        content = ""
        lines = []

    # Find entries that need to be added
    entries_to_add = [
        entry
        for entry in AUTO_CLAUDE_GITIGNORE_ENTRIES
        if not _entry_exists_in_gitignore(lines, entry)
    ]

    if not entries_to_add:
        return []

    # Build the new content to append
    # Ensure file ends with newline before adding our entries
    if content and not content.endswith("\n"):
        content += "\n"

    content += "\n# Auto Code generated files\n"
    for entry in entries_to_add:
        content += entry + "\n"
        added_entries.append(entry)

    gitignore_path.write_text(content, encoding="utf-8")

    # Auto-commit if requested and entries were added
    if auto_commit and added_entries:
        if not _commit_gitignore(project_dir):
            logger.warning(
                "Failed to auto-commit .gitignore changes in %s. "
                "Manual commit may be required to avoid merge conflicts.",
                project_dir,
            )

    return added_entries


def init_auto_claude_dir(project_dir: Path) -> tuple[Path, bool]:
    """
    Initialize the .auto-claude directory for a project.

    Creates the directory if needed and ensures all auto-claude files are in .gitignore.
    Also starts the webhook server if webhooks are enabled.

    Args:
        project_dir: The project root directory

    Returns:
        Tuple of (auto_claude_dir path, gitignore_was_updated)
    """
    project_dir = Path(project_dir)
    auto_claude_dir = project_dir / ".auto-claude"

    # Create the directory if it doesn't exist
    dir_created = not auto_claude_dir.exists()
    auto_claude_dir.mkdir(parents=True, exist_ok=True)

    # Ensure all auto-claude entries are in .gitignore (only on first creation)
    # FIX (#1087): Auto-commit the changes to prevent merge failures
    gitignore_updated = False
    if dir_created:
        added = ensure_all_gitignore_entries(project_dir, auto_commit=True)
        gitignore_updated = len(added) > 0
    else:
        # Even if dir exists, check gitignore on first run
        # Use a marker file to track if we've already checked
        marker = auto_claude_dir / ".gitignore_checked"
        if not marker.exists():
            added = ensure_all_gitignore_entries(project_dir, auto_commit=True)
            gitignore_updated = len(added) > 0
            marker.touch()

    # Start webhook server if enabled (guard in start_webhook_server_if_enabled
    # handles duplicate calls, so it's safe to always attempt startup)
    start_webhook_server_if_enabled(spec_dir=auto_claude_dir)

    return auto_claude_dir, gitignore_updated


def get_auto_claude_dir(project_dir: Path, ensure_exists: bool = True) -> Path:
    """
    Get the .auto-claude directory path, optionally ensuring it exists.

    Args:
        project_dir: The project root directory
        ensure_exists: If True, create directory and update gitignore if needed

    Returns:
        Path to the .auto-claude directory
    """
    if ensure_exists:
        auto_claude_dir, _ = init_auto_claude_dir(project_dir)
        return auto_claude_dir

    return Path(project_dir) / ".auto-claude"


def repair_gitignore(project_dir: Path) -> list[str]:
    """
    Repair an existing project's .gitignore to include all auto-claude entries.

    This is useful for projects created before all entries were being added,
    or when gitignore entries were manually removed.

    Also resets the .gitignore_checked marker to allow future updates.
    Changes are automatically committed if the project is a git repository.

    Args:
        project_dir: The project root directory

    Returns:
        List of entries that were added (empty if all already existed)
    """
    project_dir = Path(project_dir)
    auto_claude_dir = project_dir / ".auto-claude"

    # Remove the marker file so future checks will also run
    marker = auto_claude_dir / ".gitignore_checked"
    if marker.exists():
        marker.unlink()

    # Add all missing entries and auto-commit
    added = ensure_all_gitignore_entries(project_dir, auto_commit=True)

    # Re-create the marker
    if auto_claude_dir.exists():
        marker.touch()

    return added
