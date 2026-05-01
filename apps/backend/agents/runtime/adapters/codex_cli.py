"""Codex CLI runtime adapter."""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

from core.platform import build_windows_command, find_executable
from core.providers.config import DEFAULT_CODEX_MODEL

from ..capabilities import RuntimeCapabilities
from ..result import AgentRunResult


class CodexCliRuntimeSession:
    """Run Auto Code prompts through `codex exec`."""

    name = "codex_cli"
    provider_name = "codex"
    capabilities = RuntimeCapabilities.codex_cli()

    def __init__(self, *, agent_session: Any, project_dir: Path):
        self.agent_session = agent_session
        self.project_dir = project_dir

    @property
    def context_client(self) -> None:
        return None

    async def run(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None = None,
    ) -> AgentRunResult:
        del spec_dir, verbose, phase, subtask_id

        executable = find_executable(self.agent_session.codex_command)
        if executable is None:
            executable = self.agent_session.codex_command

        command_args = [
            "exec",
            "--cd",
            str(self.project_dir),
            "--sandbox",
            "workspace-write",
            "--color",
            "never",
        ]
        model = getattr(self.agent_session, "model", DEFAULT_CODEX_MODEL)
        if model and model != DEFAULT_CODEX_MODEL:
            command_args.extend(["--model", str(model)])

        env = {
            **os.environ,
            "CODEX_HOME": str(self.agent_session.codex_home),
        }
        with tempfile.TemporaryDirectory(prefix="auto-code-codex-") as temp_dir:
            output_path = Path(temp_dir) / "last-message.txt"
            command_args.extend(["--output-last-message", str(output_path)])
            command = build_windows_command(executable, command_args)

            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_dir),
                env=env,
            )
            stdout, stderr = await process.communicate(message.encode("utf-8"))

            final_message = ""
            if output_path.exists():
                final_message = output_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        response_parts = []
        if final_message.strip():
            response_parts.append(final_message)
        else:
            response_parts.extend(
                part for part in (stdout_text, stderr_text) if part.strip()
            )
        if (
            process.returncode != 0
            and stderr_text.strip()
            and stderr_text not in response_parts
        ):
            response_parts.append(stderr_text)
        return AgentRunResult(
            status="complete" if process.returncode == 0 else "error",
            response_text="\n".join(response_parts),
            usage_metadata=None,
            decision_tracker=None,
        )
