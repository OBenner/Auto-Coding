"""
Terminal Manager Service

Service layer for managing PTY (pseudo-terminal) sessions for the web terminal.
Provides methods to create PTY processes, handle I/O, and manage terminal sessions.

Platform Support:
    - Unix/Linux/macOS: Uses ptyprocess for full PTY support
    - Windows: PTY not fully supported, subprocess with async I/O used as fallback
"""

import asyncio
import logging
import os
import sys
import platform
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)


def _sanitize_log(value: str) -> str:
    """Sanitize value for safe logging (prevent log injection)."""
    return str(value).replace("\n", "\\n").replace("\r", "\\r")


# Platform detection
IS_WINDOWS = platform.system() == "Windows"
IS_UNIX = not IS_WINDOWS

# Try to import ptyprocess on Unix systems
PTYPROCESS_AVAILABLE = False
if IS_UNIX:
    try:
        import ptyprocess
        PTYPROCESS_AVAILABLE = True
    except ImportError:
        logger.warning(
            "ptyprocess not available on Unix system. "
            "Terminal sessions will have limited functionality."
        )


class TerminalSession:
    """
    Represents a single active terminal session with a PTY or subprocess.

    Manages the process, provides methods for reading output
    and writing input.
    """

    def __init__(
        self,
        session_id: str,
        working_dir: str,
        shell: str = None,
        env: Optional[Dict[str, str]] = None,
        rows: int = 24,
        cols: int = 80
    ):
        """
        Initialize a terminal session.

        Args:
            session_id: Unique identifier for this session
            working_dir: Directory to start the shell in
            shell: Shell program to run (default: system default)
            env: Optional dictionary of environment variables
            rows: Initial terminal rows
            cols: Initial terminal columns
        """
        self.session_id = session_id
        self.working_dir = working_dir

        # Determine default shell based on platform
        if shell is None:
            if IS_WINDOWS:
                self.shell = os.environ.get("COMSPEC", "cmd.exe")
            else:
                self.shell = os.environ.get("SHELL", "/bin/bash")
        else:
            self.shell = shell

        self.rows = rows
        self.cols = cols
        self._is_running = False

        # Platform-specific process objects
        self.pty_process = None  # Unix ptyprocess
        self.process = None  # Windows subprocess
        self.stdout_reader = None  # Windows asyncio task

        # Prepare environment
        self.env = os.environ.copy()
        if env:
            self.env.update(env)
        # Set terminal type for proper color support
        self.env["TERM"] = "xterm-256color"

    async def start(self) -> bool:
        """
        Start the terminal session by creating PTY or subprocess.

        Returns:
            True if session started successfully, False otherwise
        """
        if IS_UNIX and PTYPROCESS_AVAILABLE:
            return await self._start_unix_pty()
        else:
            return await self._start_subprocess()

    async def _start_unix_pty(self) -> bool:
        """Start terminal with ptyprocess on Unix systems."""
        try:
            loop = asyncio.get_event_loop()

            def _create_pty():
                proc = ptyprocess.PtyProcess.spawn(
                    self.shell,
                    cwd=self.working_dir,
                    env=self.env,
                    rows=self.rows,
                    cols=self.cols
                )
                return proc

            self.pty_process = await loop.run_in_executor(None, _create_pty)

            logger.info(
                f"Started terminal session {_sanitize_log(self.session_id)} "
                f"(PTY pid: {self.pty_process.pid}, dir: {_sanitize_log(self.working_dir)})"
            )

            self._is_running = True
            return True

        except (ptyprocess.PtyProcessError, OSError) as e:
            logger.error(f"Failed to create PTY for session {_sanitize_log(self.session_id)}: {e}")
            return False

    async def _start_subprocess(self) -> bool:
        """Start terminal with asyncio subprocess (Windows fallback)."""
        try:
            # Create subprocess with pipes for stdin/stdout/stderr
            self.process = await asyncio.create_subprocess_exec(
                self.shell,
                cwd=self.working_dir,
                env=self.env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout
                creationflags=asyncio.subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
            )

            # Start stdout reader task
            self.stdout_reader = asyncio.create_task(self._read_subprocess_stdout())

            logger.info(
                f"Started terminal session {_sanitize_log(self.session_id)} "
                f"(subprocess pid: {self.process.pid}, dir: {_sanitize_log(self.working_dir)})"
            )

            self._is_running = True
            return True

        except OSError as e:
            logger.error(f"Failed to create subprocess for session {_sanitize_log(self.session_id)}: {e}")
            return False

    def resize(self, rows: int, cols: int):
        """
        Resize the terminal window.

        Args:
            rows: New number of rows
            cols: New number of columns
        """
        self.rows = rows
        self.cols = cols

        if self.pty_process is not None and self.pty_process.isalive():
            try:
                self.pty_process.setwinsize(rows, cols)
                logger.debug(
                    f"Resized PTY terminal {_sanitize_log(self.session_id)} to {rows}x{cols}"
                )
            except (OSError, ptyprocess.PtyProcessError) as e:
                logger.warning(f"Failed to set terminal size: {e}")

        # Subprocess doesn't support resize (Windows limitation)
        elif self.process is not None:
            logger.debug(
                f"Terminal resize requested for {_sanitize_log(self.session_id)} "
                f"but subprocess doesn't support dynamic resize"
            )

    async def read_output(self) -> str:
        """
        Read output from the terminal (non-blocking).

        Returns:
            String output from the terminal (may be empty)
        """
        if IS_UNIX and PTYPROCESS_AVAILABLE and self.pty_process:
            return await self._read_pty_output()
        elif self.process:
            # For subprocess, output is buffered internally
            return await self._get_subprocess_output()
        return ""

    async def _read_pty_output(self) -> str:
        """Read output from ptyprocess (non-blocking)."""
        if self.pty_process is None or not self.pty_process.isalive():
            return ""

        try:
            loop = asyncio.get_event_loop()

            def _read():
                try:
                    return self.pty_process.read(timeout=0)
                except ptyprocess.PtyProcessError:
                    return ""

            data = await loop.run_in_executor(None, _read)
            return data if data else ""

        except ptyprocess.PtyProcessError as e:
            if self._is_running:
                logger.warning(f"Error reading from PTY: {e}")
        except Exception as e:
            if self._is_running:
                logger.error(f"Unexpected error reading PTY: {e}")
        return ""

    async def _get_subprocess_output(self) -> str:
        """Get buffered output from subprocess reader."""
        # Output is accumulated by the reader task
        if hasattr(self, "_output_buffer"):
            output = self._output_buffer
            self._output_buffer = ""
            return output
        return ""

    async def _read_subprocess_stdout(self):
        """Continuously read from subprocess stdout (runs as background task)."""
        self._output_buffer = ""
        try:
            while self.process and self.process.stdout:
                try:
                    data = await asyncio.wait_for(
                        self.process.stdout.read(1024),
                        timeout=0.1
                    )
                    if data:
                        self._output_buffer += data.decode("utf-8", errors="replace")
                except asyncio.TimeoutError:
                    continue
        except Exception as e:
            if self._is_running:
                logger.warning(f"Subprocess stdout reader error: {e}")

    def write_input(self, data: str):
        """
        Write input to the terminal.

        Args:
            data: Input string to write to the terminal
        """
        if self.pty_process is not None and self.pty_process.isalive():
            try:
                self.pty_process.write(data)
            except ptyprocess.PtyProcessError as e:
                logger.error(f"Error writing to PTY: {e}")

        elif self.process is not None:
            try:
                if self.process.stdin:
                    self.process.stdin.write(data.encode("utf-8"))
                    # Note: We don't drain here to avoid blocking
                    # The stdin will be flushed periodically
            except OSError as e:
                logger.error(f"Error writing to subprocess: {e}")
        else:
            logger.warning(
                f"Cannot write to closed terminal session {_sanitize_log(self.session_id)}"
            )

    def close(self):
        """Close the terminal session and clean up resources."""
        self._is_running = False

        # Close ptyprocess
        if self.pty_process is not None and self.pty_process.isalive():
            try:
                self.pty_process.terminate(force=True)
            except ptyprocess.PtyProcessError:
                pass
        self.pty_process = None

        # Close subprocess
        if self.process is not None:
            try:
                self.process.terminate()
            except Exception:
                pass
        self.process = None

        # Cancel reader task
        if self.stdout_reader is not None:
            self.stdout_reader.cancel()
        self.stdout_reader = None

        logger.info(f"Closed terminal session {_sanitize_log(self.session_id)}")

    def is_alive(self) -> bool:
        """
        Check if the terminal session is still alive.

        Returns:
            True if session is active, False otherwise
        """
        if not self._is_running:
            return False

        if self.pty_process is not None:
            return self.pty_process.isalive()

        if self.process is not None:
            return self.process.returncode is None

        return False


class TerminalManager:
    """
    Manager for multiple terminal sessions.

    Creates, tracks, and manages the lifecycle of terminal sessions.
    """

    def __init__(self):
        """Initialize the terminal manager."""
        # Active sessions: {session_id: TerminalSession}
        self.sessions: Dict[str, TerminalSession] = {}

        # Log platform support
        if IS_UNIX and PTYPROCESS_AVAILABLE:
            logger.info("TerminalManager initialized with ptyprocess support")
        elif IS_UNIX:
            logger.warning(
                "TerminalManager initialized on Unix without ptyprocess. "
                "Install ptyprocess for full PTY support: pip install ptyprocess"
            )
        else:
            logger.info(
                "TerminalManager initialized on Windows. "
                "PTY not fully supported, using subprocess fallback."
            )

    def create_session(
        self,
        session_id: str,
        working_dir: str,
        shell: str = None,
        env: Optional[Dict[str, str]] = None,
        rows: int = 24,
        cols: int = 80
    ) -> Optional[TerminalSession]:
        """
        Create a new terminal session.

        Args:
            session_id: Unique identifier for the session
            working_dir: Working directory for the shell
            shell: Shell program to run (default: system default)
            env: Optional environment variables
            rows: Initial terminal rows
            cols: Initial terminal columns

        Returns:
            TerminalSession object if created successfully, None otherwise
        """
        if session_id in self.sessions:
            logger.warning(f"Session {_sanitize_log(session_id)} already exists")
            return self.sessions[session_id]

        # Validate working directory
        work_path = Path(working_dir)
        if not work_path.exists():
            logger.error(
                f"Working directory does not exist: {_sanitize_log(working_dir)}"
            )
            return None

        # Create new session
        session = TerminalSession(
            session_id=session_id,
            working_dir=working_dir,
            shell=shell,
            env=env,
            rows=rows,
            cols=cols
        )

        # Note: start() is async, but we call it synchronously here
        # The caller should await session.start() if needed
        self.sessions[session_id] = session
        logger.info(f"Created terminal session {_sanitize_log(session_id)}")

        return session

    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """
        Get an existing terminal session.

        Args:
            session_id: Session identifier

        Returns:
            TerminalSession if found, None otherwise
        """
        return self.sessions.get(session_id)

    def close_session(self, session_id: str):
        """
        Close and remove a terminal session.

        Args:
            session_id: Session identifier to close
        """
        session = self.sessions.get(session_id)
        if session:
            session.close()
            del self.sessions[session_id]
            logger.info(f"Removed terminal session {_sanitize_log(session_id)}")

    def close_all_sessions(self):
        """Close all active terminal sessions."""
        for session_id in list(self.sessions.keys()):
            self.close_session(session_id)
        logger.info("Closed all terminal sessions")

    def get_active_sessions(self) -> list[str]:
        """
        Get list of active session IDs.

        Returns:
            List of session IDs
        """
        return list(self.sessions.keys())


# Global terminal manager instance
terminal_manager = TerminalManager()
