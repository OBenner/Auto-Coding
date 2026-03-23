"""
Daemon Management for Auto Code Web Backend

Provides PID file management and signal handler registration for headless server mode.
Enables running the web backend as a background daemon process (systemd service or
standalone daemon).
"""

import logging
import os
import signal
import sys
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class DaemonManager:
    """
    Manages daemon lifecycle including PID file tracking and signal handling.

    Supports running the web backend as a background service with:
    - PID file creation and cleanup
    - Graceful shutdown via SIGTERM/SIGINT
    - Process existence checking
    - Custom shutdown callback registration
    """

    def __init__(
        self,
        pid_file: Optional[str] = None,
        shutdown_callback: Optional[Callable] = None,
    ):
        """
        Initialize the daemon manager.

        Args:
            pid_file: Path to the PID file. Defaults to /tmp/auto-claude-web.pid
                      or the AUTO_CLAUDE_PID_FILE environment variable.
            shutdown_callback: Optional async/sync callable invoked on shutdown signal.
        """
        default_pid_file = os.getenv(
            "AUTO_CLAUDE_PID_FILE",
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "auto-claude-web.pid"),
        )
        self._pid_file = Path(pid_file or default_pid_file).resolve()
        self._shutdown_callback: Optional[Callable] = shutdown_callback
        self._shutdown_requested: bool = False

    @property
    def pid_file(self) -> Path:
        """Path to the PID file"""
        return self._pid_file

    @property
    def shutdown_requested(self) -> bool:
        """Whether a shutdown signal has been received"""
        return self._shutdown_requested

    # ------------------------------------------------------------------
    # PID file management
    # ------------------------------------------------------------------

    def write_pid(self) -> None:
        """
        Write the current process ID to the PID file.

        Creates parent directories as needed. Raises OSError if the file
        cannot be written.
        """
        pid = os.getpid()
        try:
            self._pid_file.parent.mkdir(parents=True, exist_ok=True)
            self._pid_file.write_text(str(pid), encoding="utf-8")
            logger.info("PID %d written to %s", pid, self._pid_file)
        except OSError as exc:
            logger.error("Failed to write PID file %s: %s", self._pid_file, exc)
            raise

    def read_pid(self) -> Optional[int]:
        """
        Read the PID from the PID file.

        Returns:
            The process ID as an integer, or None if the file does not exist
            or contains invalid data.
        """
        if not self._pid_file.exists():
            return None
        try:
            content = self._pid_file.read_text(encoding="utf-8").strip()
            return int(content)
        except (OSError, ValueError) as exc:
            logger.warning("Could not read PID from %s: %s", self._pid_file, exc)
            return None

    def remove_pid(self) -> None:
        """
        Remove the PID file if it exists.

        Silently ignores errors if the file has already been deleted.
        """
        try:
            if self._pid_file.exists():
                self._pid_file.unlink()
                logger.info("PID file removed: %s", self._pid_file)
        except OSError as exc:
            logger.warning("Could not remove PID file %s: %s", self._pid_file, exc)

    def is_running(self) -> bool:
        """
        Check whether a daemon process described by the PID file is running.

        Returns:
            True if the process exists and is alive, False otherwise.
            Cleans up a stale PID file when the process is no longer running.
        """
        pid = self.read_pid()
        if pid is None:
            return False

        # On POSIX systems use signal 0 to probe process existence.
        # On Windows os.kill with signal 0 also works for this purpose.
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            # Process does not exist – PID file is stale
            logger.debug("Stale PID file found (pid %d); removing.", pid)
            self.remove_pid()
            return False
        except PermissionError:
            # Process exists but belongs to a different user
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------
    # Signal handling
    # ------------------------------------------------------------------

    def register_signal_handlers(self) -> None:
        """
        Register OS signal handlers for graceful shutdown.

        Handles:
        - SIGTERM – standard termination signal used by systemd / process managers
        - SIGINT  – keyboard interrupt (Ctrl+C)
        - SIGHUP  – hangup signal (log rotation / config reload trigger)

        On Windows SIGTERM and SIGINT are registered; SIGHUP is skipped as it
        is not available on that platform.
        """
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        # SIGHUP is POSIX-only
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, self._handle_hup)  # type: ignore[attr-defined]

        logger.info("Signal handlers registered (SIGTERM, SIGINT%s)",
                    ", SIGHUP" if hasattr(signal, "SIGHUP") else "")

    def _handle_shutdown(self, signum: int, frame) -> None:  # noqa: ANN001
        """Handle SIGTERM / SIGINT by initiating graceful shutdown."""
        sig_name = signal.Signals(signum).name
        logger.info("Received %s – initiating graceful shutdown", sig_name)
        self._shutdown_requested = True

        if self._shutdown_callback is not None:
            try:
                result = self._shutdown_callback()
                # Support both sync and async callbacks
                if result is not None and hasattr(result, "__await__"):
                    import asyncio

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(result)
                        else:
                            loop.run_until_complete(result)
                    except RuntimeError:
                        # No event loop available; skip async shutdown
                        logger.warning("No event loop available for async shutdown callback")
            except Exception as exc:
                logger.error("Error in shutdown callback: %s", exc)

        self.remove_pid()

    def _handle_hup(self, signum: int, frame) -> None:  # noqa: ANN001
        """Handle SIGHUP (config reload / log rotation)."""
        logger.info("Received SIGHUP – reloading configuration (no-op in current version)")

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "DaemonManager":
        """Write PID file and register signal handlers on context entry."""
        self.write_pid()
        self.register_signal_handlers()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Clean up PID file on context exit."""
        self.remove_pid()
        return False  # Do not suppress exceptions


def get_daemon_manager(
    pid_file: Optional[str] = None,
    shutdown_callback: Optional[Callable] = None,
) -> DaemonManager:
    """
    Factory function returning a configured DaemonManager instance.

    Args:
        pid_file: Optional explicit path to the PID file.
        shutdown_callback: Optional callback invoked on shutdown signals.

    Returns:
        A new DaemonManager instance.
    """
    return DaemonManager(pid_file=pid_file, shutdown_callback=shutdown_callback)
