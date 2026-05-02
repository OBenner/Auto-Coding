"""Shared process runner for local CLI-backed runtimes."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from core.platform import build_windows_command, find_executable


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


class CliRuntimeProcess:
    """Run and cancel a single active CLI runtime process."""

    def __init__(self) -> None:
        self._current_process: asyncio.subprocess.Process | None = None
        self._cancel_requested = False

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
        try:
            stdout, stderr = await process.communicate(
                command.stdin_text.encode("utf-8")
            )
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
            stdout_text=stdout.decode("utf-8", errors="replace"),
            stderr_text=stderr.decode("utf-8", errors="replace"),
            final_message=final_message,
            cancelled=self._cancel_requested,
        )
