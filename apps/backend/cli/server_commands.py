"""
Server Commands
===============

Commands for managing the Auto Code web-backend server daemon.
Supports start, stop, status, and logs subcommands.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path

from ui import print_status


# Default server configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_LOG_LINES = 50

# Relative path from the project root to the web-backend
_WEB_BACKEND_DIR = "apps/web-backend"


def _get_pid_file(project_dir: str) -> Path:
    """Return the path to the server PID file."""
    pid_env = os.getenv("AUTO_CLAUDE_PID_FILE")
    if pid_env:
        return Path(pid_env)
    return Path(project_dir) / "auto-claude-web.pid"


def _get_log_file(project_dir: str) -> Path:
    """Return the path to the server log file."""
    log_env = os.getenv("AUTO_CLAUDE_LOG_FILE")
    if log_env:
        return Path(log_env)
    return Path(project_dir) / ".auto-claude" / "server" / "server.log"


def _read_pid(pid_file: Path) -> int | None:
    """Read a PID from the given file; returns None if missing or invalid."""
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _is_running(pid_file: Path) -> bool:
    """Check whether the process described by the PID file is still running."""
    pid = _read_pid(pid_file)
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        # Stale PID file
        try:
            pid_file.unlink()
        except OSError:
            pass
        return False
    except PermissionError:
        # Process exists but belongs to a different user
        return True
    except OSError:
        return False


def handle_server_start_command(
    project_dir: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
) -> bool:
    """
    Start the Auto Code web-backend server as a background process.

    Args:
        project_dir: Project root directory
        host: Host to bind (default: 0.0.0.0)
        port: Port to listen on (default: 8000)

    Returns:
        True if the server started successfully
    """
    pid_file = _get_pid_file(project_dir)
    log_file = _get_log_file(project_dir)

    if _is_running(pid_file):
        pid = _read_pid(pid_file)
        print_status(f"Server is already running (PID {pid})", "warning")
        return False

    web_backend_dir = Path(project_dir) / _WEB_BACKEND_DIR
    if not web_backend_dir.exists():
        print_status(
            f"Web backend directory not found: {web_backend_dir}", "error"
        )
        return False

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["AUTO_CLAUDE_PID_FILE"] = str(pid_file)

    try:
        log_fd = open(log_file, "a", encoding="utf-8")  # noqa: WPS515
    except OSError as exc:
        print_status(f"Cannot open log file {log_file}: {exc}", "error")
        return False

    try:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                host,
                "--port",
                str(port),
            ],
            cwd=str(web_backend_dir),
            env=env,
            stdout=log_fd,
            stderr=log_fd,
            start_new_session=True,
        )
    except FileNotFoundError:
        log_fd.close()
        print_status(
            "uvicorn not found. Install with: pip install uvicorn", "error"
        )
        return False
    except OSError as exc:
        log_fd.close()
        print_status(f"Failed to start server: {exc}", "error")
        return False

    log_fd.close()

    # Write PID file from the parent process so CLI can track it
    try:
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(proc.pid), encoding="utf-8")
    except OSError as exc:
        print_status(f"Warning: could not write PID file: {exc}", "warning")

    print_status(
        f"Server started (PID {proc.pid}) on {host}:{port}", "success"
    )
    print_status(f"Logs: {log_file}", "info")
    return True


def handle_server_stop_command(project_dir: str) -> bool:
    """
    Stop the running Auto Code web-backend server.

    Args:
        project_dir: Project root directory

    Returns:
        True if the server was stopped (or was not running)
    """
    pid_file = _get_pid_file(project_dir)

    if not _is_running(pid_file):
        print_status("Server is not running", "info")
        return True

    pid = _read_pid(pid_file)
    if pid is None:
        print_status("Could not read server PID", "error")
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        print_status(f"Process {pid} not found; cleaning up PID file", "warning")
        try:
            pid_file.unlink()
        except OSError:
            pass
        return True
    except PermissionError:
        print_status(
            f"Permission denied sending SIGTERM to PID {pid}", "error"
        )
        return False
    except OSError as exc:
        print_status(f"Failed to stop server: {exc}", "error")
        return False

    print_status(f"SIGTERM sent to server (PID {pid})", "success")
    return True


def handle_server_status_command(project_dir: str) -> bool:
    """
    Show the current status of the Auto Code web-backend server.

    Args:
        project_dir: Project root directory

    Returns:
        True if the server is running, False if stopped
    """
    pid_file = _get_pid_file(project_dir)
    log_file = _get_log_file(project_dir)
    running = _is_running(pid_file)

    print_status("Auto Code Server Status", "info")
    print()

    if running:
        pid = _read_pid(pid_file)
        print(f"  Status : \033[32mRunning\033[0m")
        print(f"  PID    : {pid}")
    else:
        print(f"  Status : \033[31mStopped\033[0m")

    print(f"  PID file : {pid_file}")
    print(f"  Log file : {log_file}")
    print()

    return running


def handle_server_logs_command(
    project_dir: str,
    lines: int = DEFAULT_LOG_LINES,
) -> bool:
    """
    Display the tail of the server log file.

    Args:
        project_dir: Project root directory
        lines: Number of log lines to show (default: 50)

    Returns:
        True if successful
    """
    log_file = _get_log_file(project_dir)

    if not log_file.exists():
        print_status(f"Log file not found: {log_file}", "warning")
        return False

    try:
        content = log_file.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print_status(f"Cannot read log file: {exc}", "error")
        return False

    all_lines = content.splitlines()
    tail = all_lines[-lines:] if len(all_lines) > lines else all_lines

    print_status(
        f"Last {len(tail)} lines from {log_file}", "info"
    )
    print()
    for line in tail:
        print(line)

    return True


def handle_server_command(
    subcommand: str,
    project_dir: str,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    log_lines: int = DEFAULT_LOG_LINES,
) -> bool:
    """
    Dispatch a server subcommand to the appropriate handler.

    Args:
        subcommand: One of start, stop, status, logs
        project_dir: Project root directory
        host: Host to bind when starting (default: 0.0.0.0)
        port: Port when starting (default: 8000)
        log_lines: Number of log lines to show with 'logs' subcommand

    Returns:
        True if the operation succeeded
    """
    handlers = {
        "start": lambda: handle_server_start_command(project_dir, host, port),
        "stop": lambda: handle_server_stop_command(project_dir),
        "status": lambda: handle_server_status_command(project_dir),
        "logs": lambda: handle_server_logs_command(project_dir, log_lines),
    }

    handler = handlers.get(subcommand)
    if handler is None:
        valid = ", ".join(handlers.keys())
        print_status(
            f"Unknown server subcommand '{subcommand}'. Valid: {valid}", "error"
        )
        return False

    return handler()
