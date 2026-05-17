"""Provider-neutral CLI runtime adapter core."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..capabilities import RuntimeCapabilities
from ..result import AgentRunResult
from .cli_runner import CliRuntimeCommand, CliRuntimeProcess
from .codex_cli import (
    build_codex_event_timeline,
    build_codex_usage_metadata,
    extract_codex_final_message,
    looks_like_json_object,
    parse_codex_json_events,
    summarize_codex_account,
    summarize_codex_events,
)

GENERIC_CLI_OUTPUT_ARG_ATTRS = (
    "cli_output_last_message_arg",
    "cli_runner_output_last_message_arg",
)
GENERIC_CLI_ARGS_ATTRS = ("cli_runner_args", "cli_args")
GENERIC_CLI_COMMAND_ATTRS = ("cli_runner_command", "cli_command")
GENERIC_CLI_ENV_ATTRS = ("cli_runner_env", "cli_env")
GENERIC_CLI_MODEL_ARG_ATTRS = ("cli_runner_model_arg", "cli_model_arg")
GENERIC_CLI_PROMPT_ARG_ATTRS = ("cli_runner_prompt_arg", "cli_prompt_arg")


class GenericCliRuntimeSession:
    """Run prompts through a configured local coding CLI.

    This adapter is intentionally small and contract-driven: concrete runner
    adapters can specialize command construction later, while this core already
    supplies the shared run/cancel/artifact/event parsing surface.
    """

    capabilities = RuntimeCapabilities.codex_cli()

    def __init__(self, *, runner_id: str, agent_session: Any, project_dir: Path):
        self.runner_id = normalize_cli_runner_id(runner_id)
        self.agent_session = agent_session
        self.project_dir = project_dir
        self._process = CliRuntimeProcess()

    @property
    def name(self) -> str:
        return self.runner_id

    @property
    def provider_name(self) -> str:
        return self.runner_id

    @property
    def context_client(self) -> None:
        return None

    async def cancel(self) -> bool:
        """Cancel the active CLI process, if one is running."""
        return await self._process.cancel()

    async def run(
        self,
        *,
        message: str,
        spec_dir: Path,
        verbose: bool,
        phase: Any,
        subtask_id: str | None = None,
    ) -> AgentRunResult:
        del verbose, phase

        executable = resolve_generic_cli_executable(
            self.agent_session,
            runner_id=self.runner_id,
        )
        env = {
            **os.environ,
            **resolve_generic_cli_env(self.agent_session),
        }
        with tempfile.TemporaryDirectory(prefix=f"auto-code-{self.runner_id}-") as tmp:
            output_path = Path(tmp) / "last-message.txt"
            command_args, stdin_text, final_message_path = build_generic_cli_command(
                agent_session=self.agent_session,
                project_dir=self.project_dir,
                output_path=output_path,
                message=message,
            )
            process_result = await self._process.run(
                CliRuntimeCommand(
                    executable=executable,
                    args=command_args,
                    cwd=self.project_dir,
                    env=env,
                    stdin_text=stdin_text,
                    final_message_path=final_message_path,
                )
            )

        stdout_text = process_result.stdout_text
        stderr_text = process_result.stderr_text
        events = parse_codex_json_events(stdout_text)
        event_summary = summarize_codex_events(events)
        event_final_message = extract_codex_final_message(events)
        status = "complete" if process_result.returncode == 0 else "error"
        if process_result.cancelled:
            status = "cancelled"

        response_text = build_generic_cli_response_text(
            runner_id=self.runner_id,
            status=status,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
            final_message=process_result.final_message,
            event_final_message=event_final_message,
            output_truncated=process_result.truncated,
        )
        artifacts = save_generic_cli_artifacts(
            spec_dir=spec_dir,
            runner_id=self.runner_id,
            subtask_id=subtask_id,
            status=status,
            returncode=process_result.returncode,
            command_args=command_args,
            events=events,
            event_summary=event_summary,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
            final_message=process_result.final_message or event_final_message,
            output_truncated=process_result.truncated,
        )

        return AgentRunResult(
            status=status,
            response_text=response_text,
            usage_metadata=build_codex_usage_metadata(event_summary),
            decision_tracker=None,
            artifacts=artifacts,
        )


def normalize_cli_runner_id(runner_id: str) -> str:
    """Return a filesystem-safe CLI runner id."""
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(runner_id).strip().lower())
    return normalized.strip("._-") or "generic_cli"


def resolve_generic_cli_executable(agent_session: Any, *, runner_id: str) -> str:
    """Resolve the executable configured for a generic CLI runner."""
    for attr_name in (
        f"{runner_id}_command",
        *GENERIC_CLI_COMMAND_ATTRS,
        "command",
    ):
        value = getattr(agent_session, attr_name, None)
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError(
        f"cli_runner_command is required for generic CLI runner {runner_id}."
    )


def resolve_generic_cli_env(agent_session: Any) -> dict[str, str]:
    """Return string-only environment overrides for the CLI runner."""
    for attr_name in GENERIC_CLI_ENV_ATTRS:
        value = getattr(agent_session, attr_name, None)
        if isinstance(value, dict):
            return {str(key): str(item) for key, item in value.items()}
    return {}


def build_generic_cli_command(
    *,
    agent_session: Any,
    project_dir: Path,
    output_path: Path,
    message: str,
) -> tuple[list[str], str, Path | None]:
    """Build command args, stdin, and optional final-message path."""
    command_args = replace_generic_cli_tokens(
        values=coerce_generic_cli_args(
            first_attr(agent_session, GENERIC_CLI_ARGS_ATTRS)
        ),
        project_dir=project_dir,
        output_path=output_path,
        message=message,
        model=getattr(agent_session, "model", ""),
    )
    final_message_path: Path | None = None
    output_arg = first_string_attr(agent_session, GENERIC_CLI_OUTPUT_ARG_ATTRS)
    if output_arg:
        command_args.extend([output_arg, str(output_path)])
        final_message_path = output_path

    model_arg = first_string_attr(agent_session, GENERIC_CLI_MODEL_ARG_ATTRS)
    model = getattr(agent_session, "model", None)
    if model_arg and model:
        command_args.extend([model_arg, str(model)])

    prompt_arg = first_string_attr(agent_session, GENERIC_CLI_PROMPT_ARG_ATTRS)
    if prompt_arg:
        command_args.extend([prompt_arg, message])
        return command_args, "", final_message_path
    return command_args, message, final_message_path


def first_attr(agent_session: Any, attr_names: tuple[str, ...]) -> Any:
    """Return the first non-empty configured attribute."""
    for attr_name in attr_names:
        value = getattr(agent_session, attr_name, None)
        if value:
            return value
    return None


def first_string_attr(agent_session: Any, attr_names: tuple[str, ...]) -> str:
    """Return the first non-empty string configured attribute."""
    value = first_attr(agent_session, attr_names)
    return value if isinstance(value, str) and value.strip() else ""


def coerce_generic_cli_args(value: Any) -> list[str]:
    """Coerce configured CLI args to a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list | tuple):
        return [str(item) for item in value]
    raise TypeError("cli_runner_args must be a string or a list of strings.")


def replace_generic_cli_tokens(
    *,
    values: list[str],
    project_dir: Path,
    output_path: Path,
    message: str,
    model: Any,
) -> list[str]:
    """Replace portable placeholders in configured CLI args."""
    replacements = {
        "{project_dir}": str(project_dir),
        "{output_path}": str(output_path),
        "{prompt}": message,
        "{model}": str(model or ""),
    }
    replaced: list[str] = []
    for value in values:
        item = value
        for token, replacement in replacements.items():
            item = item.replace(token, replacement)
        replaced.append(item)
    return replaced


def build_generic_cli_response_text(
    *,
    runner_id: str,
    status: str,
    stdout_text: str,
    stderr_text: str,
    final_message: str,
    event_final_message: str,
    output_truncated: bool,
) -> str:
    """Return a user-visible response from CLI output and artifacts."""
    non_json_stdout = "\n".join(
        line for line in stdout_text.splitlines() if not looks_like_json_object(line)
    )
    response_parts = [
        part.rstrip("\r\n")
        for part in (final_message, event_final_message, non_json_stdout)
        if part.strip()
    ]
    if status == "cancelled":
        response_parts.append(f"{runner_id} run was cancelled.")
    if output_truncated:
        response_parts.append(f"{runner_id} output exceeded the runtime capture limit.")
    if status == "error" and stderr_text.strip():
        response_parts.append(stderr_text.rstrip("\r\n"))
    return "\n".join(response_parts)


def save_generic_cli_artifacts(
    *,
    spec_dir: Path,
    runner_id: str,
    subtask_id: str | None,
    status: str,
    returncode: int | None,
    command_args: list[str],
    events: list[dict[str, Any]],
    event_summary: dict[str, Any],
    stdout_text: str,
    stderr_text: str,
    final_message: str,
    output_truncated: bool,
) -> dict[str, str]:
    """Persist generic CLI artifacts under stable runner-specific names."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    events_path = artifact_dir / f"{runner_id}_events.jsonl"
    timeline_path = artifact_dir / f"{runner_id}_timeline.json"
    result_path = artifact_dir / f"{runner_id}_result.json"
    stdout_path = artifact_dir / f"{runner_id}_stdout.txt"

    events_path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )
    stdout_path.write_text(stdout_text, encoding="utf-8")

    event_timeline = build_codex_event_timeline(events)
    now = datetime.now(timezone.utc).isoformat()
    timeline_path.write_text(
        json.dumps(
            {
                "timestamp": now,
                "provider": runner_id,
                "runtime": runner_id,
                "subtask_id": subtask_id,
                "status": status,
                "session_id": event_summary.get("session_id"),
                "event_count": len(events),
                "events": event_timeline,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    safe_event_summary = safe_generic_cli_event_summary(event_summary)
    result_path.write_text(
        json.dumps(
            {
                "timestamp": now,
                "provider": runner_id,
                "runtime": runner_id,
                "subtask_id": subtask_id,
                "status": status,
                "returncode": returncode,
                "output_truncated": output_truncated,
                "session_id": event_summary.get("session_id"),
                "usage": event_summary.get("usage", {}),
                "cost_usd": event_summary.get("cost_usd"),
                "account_summary": summarize_codex_account(
                    event_summary.get("account")
                ),
                "command_options": safe_generic_cli_command_options(command_args),
                "event_summary": safe_event_summary,
                "event_timeline_count": len(event_timeline),
                "non_json_stdout_line_count": len(
                    [
                        line
                        for line in stdout_text.splitlines()
                        if not looks_like_json_object(line)
                    ]
                ),
                "stderr_excerpt": stderr_text[:2000],
                "final_message_excerpt": final_message[:2000],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    artifacts = {
        f"{runner_id}_events": str(events_path),
        f"{runner_id}_timeline": str(timeline_path),
        f"{runner_id}_result": str(result_path),
        f"{runner_id}_stdout": str(stdout_path),
    }
    if stderr_text.strip():
        stderr_path = artifact_dir / f"{runner_id}_stderr.txt"
        stderr_path.write_text(stderr_text, encoding="utf-8")
        artifacts[f"{runner_id}_stderr"] = str(stderr_path)
    return artifacts


def safe_generic_cli_event_summary(event_summary: dict[str, Any]) -> dict[str, Any]:
    """Return event summary metadata without credential-like account fields."""
    safe_summary = dict(event_summary)
    if "account" in safe_summary:
        safe_summary["account"] = summarize_codex_account(safe_summary.get("account"))
    return safe_summary


def safe_generic_cli_command_options(command_args: list[str]) -> list[str]:
    """Return CLI command args with artifact paths redacted."""
    sanitized: list[str] = []
    redact_next = False
    for arg in command_args:
        if redact_next:
            sanitized.append("<artifact-path>")
            redact_next = False
            continue
        sanitized.append(arg)
        if arg in {"--output-last-message", "--output", "--json-output"}:
            redact_next = True
    return sanitized
