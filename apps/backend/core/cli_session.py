"""
CLI Session Runner
==================

Runs a command-line application end-to-end for QA verification: spawn the
process, optionally feed scripted stdin lines, capture combined output, and
enforce a timeout.

On POSIX the process runs inside a pseudo-terminal so applications that
check isatty() (prompts, progress bars, colored output) behave like they
do for a real user. On Windows there is no stdlib pty; plain pipes are
used, which covers argument-driven CLIs and simple stdin protocols.
"""

import os
import shlex
import subprocess
import time
from dataclasses import dataclass

from core.platform import is_windows

# Cap captured output so a chatty process cannot blow up the result
MAX_OUTPUT_CHARS = 100_000

# Delay between scripted stdin lines, giving the app time to prompt
INPUT_INTERVAL_SECONDS = 0.2


@dataclass
class CliSessionResult:
    """Outcome of a CLI session run."""

    exit_code: int | None
    output: str
    timed_out: bool


def run_cli_session(
    command: str,
    cwd: str,
    inputs: list[str] | None = None,
    timeout_seconds: int = 30,
) -> CliSessionResult:
    """
    Run a CLI application and capture its output.

    Args:
        command: Command line to run (parsed with shlex, no shell)
        cwd: Working directory for the process
        inputs: Lines to send to stdin, in order (newline appended)
        timeout_seconds: Kill the process after this many seconds

    Returns:
        CliSessionResult with exit code, combined output, and timeout flag
    """
    argv = shlex.split(command, posix=not is_windows())
    if not argv:
        return CliSessionResult(exit_code=None, output="", timed_out=False)

    if is_windows():
        return _run_with_pipes(argv, cwd, inputs, timeout_seconds)
    return _run_with_pty(argv, cwd, inputs, timeout_seconds)


def _run_with_pipes(
    argv: list[str],
    cwd: str,
    inputs: list[str] | None,
    timeout_seconds: int,
) -> CliSessionResult:
    """Run with plain pipes (Windows fallback, no pty in stdlib)."""
    stdin_data = "".join(line + "\n" for line in inputs) if inputs else None
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        output, _ = proc.communicate(input=stdin_data, timeout=timeout_seconds)
        timed_out = False
    except subprocess.TimeoutExpired:
        proc.kill()
        output, _ = proc.communicate()
        timed_out = True

    return CliSessionResult(
        exit_code=proc.returncode,
        output=(output or "")[:MAX_OUTPUT_CHARS],
        timed_out=timed_out,
    )


def _run_with_pty(
    argv: list[str],
    cwd: str,
    inputs: list[str] | None,
    timeout_seconds: int,
) -> CliSessionResult:
    """Run inside a pseudo-terminal (POSIX)."""
    import pty
    import select

    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        start_new_session=True,
    )
    os.close(slave_fd)

    pending = list(inputs or [])
    chunks: list[bytes] = []
    total = 0
    deadline = time.monotonic() + timeout_seconds
    next_write = time.monotonic() + INPUT_INTERVAL_SECONDS
    timed_out = False

    try:
        while True:
            if time.monotonic() > deadline:
                timed_out = True
                proc.kill()
                break

            eof = _drain_output(master_fd, chunks, total)
            total = sum(len(c) for c in chunks)
            if eof:
                break

            if pending and time.monotonic() >= next_write:
                os.write(master_fd, (pending.pop(0) + "\n").encode())
                next_write = time.monotonic() + INPUT_INTERVAL_SECONDS

            if proc.poll() is not None:
                # Process exited: drain whatever is left, then stop
                while not _drain_output(master_fd, chunks, total):
                    total = sum(len(c) for c in chunks)
                break

            select.select([master_fd], [], [], 0.05)
    finally:
        os.close(master_fd)
        if proc.poll() is None:
            proc.kill()
        proc.wait()

    output = b"".join(chunks).decode("utf-8", errors="replace")
    return CliSessionResult(
        exit_code=proc.returncode,
        output=output[:MAX_OUTPUT_CHARS],
        timed_out=timed_out,
    )


def _drain_output(master_fd: int, chunks: list[bytes], total: int) -> bool:
    """
    Read available pty output without blocking.

    Returns:
        True when the pty reached EOF (process side closed)
    """
    import select

    while True:
        readable, _, _ = select.select([master_fd], [], [], 0)
        if not readable:
            return False
        try:
            data = os.read(master_fd, 4096)
        except OSError:
            # EIO: slave side closed - treat as EOF
            return True
        if not data:
            return True
        if total < MAX_OUTPUT_CHARS:
            chunks.append(data)
            total += len(data)


__all__ = ["CliSessionResult", "run_cli_session", "MAX_OUTPUT_CHARS"]
