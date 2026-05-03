"""Shared process runner for local CLI-backed runtimes."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from core.platform import build_windows_command, find_executable

MAX_CLI_OUTPUT_CHARS = 200_000


@dataclass(frozen=True)
class CliRuntimeCommand:
    """One local CLI invocation for a runtime adapter."""

    executable: str
    args: list[str]
    cwd: Path
    env: Mapping[str, str]
    stdin_text: str
    final_message_path: Path | None = None


@dataclass(frozen=True)
class CliRuntimeProcessResult:
    """Captured result from one CLI runtime process."""

    returncode: int | None
    stdout_text: str
    stderr_text: str
    final_message: str
    cancelled: bool
    truncated: bool = False


class CliRuntimeProcess:
    """Run and cancel a single active CLI runtime process."""

    def __init__(self, *, max_output_chars: int = MAX_CLI_OUTPUT_CHARS) -> None:
        self._current_process: asyncio.subprocess.Process | None = None
        self._cancel_requested = False
        self._max_output_chars = max(1, max_output_chars)

    async def cancel(self) -> bool:
        """Cancel the active CLI process, if one is running."""
        process = self._current_process
        if process is None or process.returncode is not None:
            return False

        self._cancel_requested = True
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=10)
        except TimeoutError:
            process.kill()
            await process.wait()
        return True

    async def run(self, command: CliRuntimeCommand) -> CliRuntimeProcessResult:
        """Run one CLI command and capture stdout, stderr, and final message."""
        executable = find_executable(command.executable) or command.executable
        process_args = build_windows_command(executable, command.args)
        self._cancel_requested = False

        process = await asyncio.create_subprocess_exec(
            *process_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(command.cwd),
            env=dict(command.env),
        )
        self._current_process = process
        output_capture = CliOutputCapture(remaining=self._max_output_chars)
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        stdout_task = asyncio.create_task(
            capture_cli_stream(process.stdout, stdout_parts, output_capture, process)
        )
        stderr_task = asyncio.create_task(
            capture_cli_stream(process.stderr, stderr_parts, output_capture, process)
        )
        try:
            await write_process_stdin(process, command.stdin_text)
            await process.wait()
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        finally:
            self._current_process = None

        final_message = ""
        if command.final_message_path and command.final_message_path.exists():
            final_message = command.final_message_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        return CliRuntimeProcessResult(
            returncode=process.returncode,
            stdout_text="".join(stdout_parts),
            stderr_text="".join(stderr_parts),
            final_message=final_message,
            cancelled=self._cancel_requested,
            truncated=output_capture.truncated,
        )


@dataclass
class CliOutputCapture:
    """Shared stdout/stderr budget for one CLI runtime process."""

    remaining: int
    truncated: bool = False

    def append(self, text: str, parts: list[str]) -> bool:
        """Append text within the shared capture budget."""
        if self.remaining > 0:
            piece = text[: self.remaining]
            parts.append(piece)
            self.remaining -= len(piece)
            if len(piece) == len(text):
                return True
        self.truncated = True
        return False


async def write_process_stdin(
    process: asyncio.subprocess.Process,
    stdin_text: str,
) -> None:
    """Write stdin to a subprocess and close the pipe."""
    if process.stdin is None:
        return
    try:
        process.stdin.write(stdin_text.encode("utf-8"))
        await process.stdin.drain()
    except (BrokenPipeError, ConnectionResetError):
        return
    finally:
        process.stdin.close()
    try:
        await process.stdin.wait_closed()
    except (BrokenPipeError, ConnectionResetError):
        return


async def capture_cli_stream(
    stream: asyncio.StreamReader | None,
    parts: list[str],
    capture: CliOutputCapture,
    process: asyncio.subprocess.Process,
) -> None:
    """Capture one CLI stream and terminate the process if output is too large."""
    if stream is None:
        return
    while chunk := await stream.read(4096):
        text = chunk.decode("utf-8", errors="replace")
        if capture.append(text, parts):
            continue
        if process.returncode is None:
            process.terminate()
        break
