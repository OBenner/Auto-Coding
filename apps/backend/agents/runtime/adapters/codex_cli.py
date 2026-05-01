"""Codex CLI runtime adapter."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from datetime import UTC, datetime
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
        self._current_process: asyncio.subprocess.Process | None = None
        self._cancel_requested = False

    @property
    def context_client(self) -> None:
        return None

    async def cancel(self) -> bool:
        """Cancel the active Codex CLI process, if one is running."""
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

        executable = find_executable(self.agent_session.codex_command)
        if executable is None:
            executable = self.agent_session.codex_command

        model = getattr(self.agent_session, "model", DEFAULT_CODEX_MODEL)
        env = {
            **os.environ,
            "CODEX_HOME": str(self.agent_session.codex_home),
        }
        self._cancel_requested = False
        with tempfile.TemporaryDirectory(prefix="auto-code-codex-") as temp_dir:
            output_path = Path(temp_dir) / "last-message.txt"
            command_args = build_codex_command_args(
                project_dir=self.project_dir,
                model=str(model or ""),
                output_path=output_path,
                resume_session_id=getattr(
                    self.agent_session,
                    "codex_resume_session_id",
                    None,
                ),
                resume_last=bool(
                    getattr(self.agent_session, "codex_resume_last", False)
                ),
            )
            command = build_windows_command(executable, command_args)

            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_dir),
                env=env,
            )
            self._current_process = process
            try:
                stdout, stderr = await process.communicate(message.encode("utf-8"))
            finally:
                self._current_process = None

            final_message = ""
            if output_path.exists():
                final_message = output_path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        events = parse_codex_json_events(stdout_text)
        event_summary = summarize_codex_events(events)
        status = "complete" if process.returncode == 0 else "error"
        if self._cancel_requested:
            status = "cancelled"
        artifacts = save_codex_cli_artifacts(
            spec_dir=spec_dir,
            subtask_id=subtask_id,
            status=status,
            returncode=process.returncode,
            command_args=command_args,
            events=events,
            event_summary=event_summary,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
            final_message=final_message,
        )

        response_parts = []
        if final_message.strip():
            response_parts.append(final_message)
        else:
            fallback_stdout = "\n".join(
                line
                for line in stdout_text.splitlines()
                if not looks_like_json_object(line)
            )
            response_parts.extend(
                part for part in (fallback_stdout, stderr_text) if part.strip()
            )
        if status == "cancelled":
            response_parts.append(
                f"Codex CLI run was cancelled. Artifacts: {artifacts['codex_cli_result']}"
            )
        if (
            process.returncode != 0
            and stderr_text.strip()
            and stderr_text not in response_parts
        ):
            response_parts.append(stderr_text)
        usage_metadata = build_codex_usage_metadata(event_summary)
        return AgentRunResult(
            status=status,
            response_text="\n".join(response_parts),
            usage_metadata=usage_metadata,
            decision_tracker=None,
            artifacts=artifacts,
        )


def build_codex_command_args(
    *,
    project_dir: Path,
    model: str,
    output_path: Path,
    resume_session_id: str | None = None,
    resume_last: bool = False,
) -> list[str]:
    """Build CLI args for new and resumed Codex exec sessions."""
    if resume_session_id or resume_last:
        args = ["exec", "resume"]
        if resume_last:
            args.append("--last")
        args.append("--json")
        if model and model != DEFAULT_CODEX_MODEL:
            args.extend(["--model", model])
        args.extend(["--output-last-message", str(output_path)])
        if resume_session_id:
            args.append(str(resume_session_id))
        return args

    args = [
        "exec",
        "--cd",
        str(project_dir),
        "--sandbox",
        "workspace-write",
        "--color",
        "never",
        "--json",
    ]
    if model and model != DEFAULT_CODEX_MODEL:
        args.extend(["--model", model])
    args.extend(["--output-last-message", str(output_path)])
    return args


def parse_codex_json_events(stdout_text: str) -> list[dict[str, Any]]:
    """Parse Codex CLI JSONL events while ignoring legacy/plain stdout lines."""
    events: list[dict[str, Any]] = []
    for line in stdout_text.splitlines():
        stripped = line.strip()
        if not looks_like_json_object(stripped):
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def summarize_codex_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract portable session, usage, cost, and account metadata from events."""
    event_types: dict[str, int] = {}
    summary: dict[str, Any] = {
        "event_count": len(events),
        "event_types": event_types,
        "session_id": None,
        "account": None,
        "usage": {},
        "cost_usd": None,
    }

    for event in events:
        event_type = codex_event_type(event)
        if event_type:
            event_types[event_type] = event_types.get(event_type, 0) + 1
        if summary["session_id"] is None:
            summary["session_id"] = first_string_at_paths(
                event,
                (
                    ("session_id",),
                    ("sessionId",),
                    ("conversation_id",),
                    ("conversationId",),
                    ("thread_id",),
                    ("threadId",),
                    ("session", "id"),
                    ("conversation", "id"),
                ),
            )
        if summary["account"] is None:
            summary["account"] = first_value_at_paths(
                event,
                (
                    ("account",),
                    ("account_info",),
                    ("user",),
                    ("auth", "account"),
                    ("auth", "user"),
                ),
            )
        merge_codex_usage(summary["usage"], event)
        cost = extract_max_number(
            event,
            (
                "cost_usd",
                "total_cost_usd",
                "estimated_cost_usd",
                "cost",
                "total_cost",
            ),
        )
        if cost is not None:
            summary["cost_usd"] = max(float(summary["cost_usd"] or 0.0), cost)

    return summary


def build_codex_usage_metadata(
    event_summary: dict[str, Any],
) -> dict[str, Any] | None:
    """Return token metadata only when standard token keys are available."""
    usage = event_summary.get("usage")
    if not isinstance(usage, dict):
        return None
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None

    metadata: dict[str, Any] = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
    for key in ("total_tokens", "cached_input_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            metadata[key] = value
    if isinstance(event_summary.get("cost_usd"), int | float):
        metadata["cost_usd"] = event_summary["cost_usd"]
    return metadata


def save_codex_cli_artifacts(
    *,
    spec_dir: Path,
    subtask_id: str | None,
    status: str,
    returncode: int | None,
    command_args: list[str],
    events: list[dict[str, Any]],
    event_summary: dict[str, Any],
    stdout_text: str,
    stderr_text: str,
    final_message: str,
) -> dict[str, str]:
    """Persist Codex CLI event and result artifacts for UI/debug consumers."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    events_path = artifact_dir / "codex_cli_events.jsonl"
    result_path = artifact_dir / "codex_cli_result.json"
    events_path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )

    non_json_stdout_lines = [
        line for line in stdout_text.splitlines() if not looks_like_json_object(line)
    ]
    result_payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "provider": "codex",
        "runtime": "codex_cli",
        "subtask_id": subtask_id,
        "status": status,
        "returncode": returncode,
        "mode": "resume" if command_args[:2] == ["exec", "resume"] else "exec",
        "resumed": command_args[:2] == ["exec", "resume"],
        "command_options": safe_codex_command_options(command_args),
        "event_summary": event_summary,
        "non_json_stdout_line_count": len(non_json_stdout_lines),
        "stderr_excerpt": stderr_text[:2000],
        "final_message_excerpt": final_message[:2000],
    }
    result_path.write_text(
        json.dumps(result_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    artifacts = {
        "codex_cli_events": str(events_path),
        "codex_cli_result": str(result_path),
    }
    if stderr_text.strip():
        stderr_path = artifact_dir / "codex_cli_stderr.txt"
        stderr_path.write_text(stderr_text, encoding="utf-8")
        artifacts["codex_cli_stderr"] = str(stderr_path)
    return artifacts


def safe_codex_command_options(command_args: list[str]) -> list[str]:
    """Return command args without volatile temp output paths."""
    sanitized: list[str] = []
    skip_next = False
    for arg in command_args:
        if skip_next:
            sanitized.append("<artifact-path>")
            skip_next = False
            continue
        sanitized.append(arg)
        if arg == "--output-last-message":
            skip_next = True
    return sanitized


def codex_event_type(event: dict[str, Any]) -> str | None:
    value = first_string_at_paths(
        event,
        (
            ("type",),
            ("event",),
            ("name",),
            ("msg", "type"),
            ("message", "type"),
            ("item", "type"),
            ("data", "type"),
        ),
    )
    return value or None


def merge_codex_usage(usage: dict[str, int], event: dict[str, Any]) -> None:
    token_map = {
        "input_tokens": (
            "input_tokens",
            "prompt_tokens",
            "inputTokens",
            "promptTokens",
        ),
        "output_tokens": (
            "output_tokens",
            "completion_tokens",
            "outputTokens",
            "completionTokens",
        ),
        "total_tokens": ("total_tokens", "totalTokens"),
        "cached_input_tokens": (
            "cached_input_tokens",
            "cachedPromptTokens",
            "cached_inputTokens",
        ),
    }
    for normalized_key, source_keys in token_map.items():
        value = extract_max_int(event, source_keys)
        if value is not None:
            usage[normalized_key] = max(usage.get(normalized_key, 0), value)


def extract_max_int(value: Any, keys: tuple[str, ...]) -> int | None:
    numbers = [
        int(candidate)
        for candidate in values_for_keys(value, keys)
        if isinstance(candidate, int) and not isinstance(candidate, bool)
    ]
    return max(numbers) if numbers else None


def extract_max_number(value: Any, keys: tuple[str, ...]) -> float | None:
    numbers: list[float] = []
    for candidate in values_for_keys(value, keys):
        if isinstance(candidate, bool):
            continue
        if isinstance(candidate, int | float):
            numbers.append(float(candidate))
        elif isinstance(candidate, str):
            try:
                numbers.append(float(candidate))
            except ValueError:
                continue
    return max(numbers) if numbers else None


def values_for_keys(value: Any, keys: tuple[str, ...]) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                found.append(item)
            found.extend(values_for_keys(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(values_for_keys(item, keys))
    return found


def first_string_at_paths(
    event: dict[str, Any],
    paths: tuple[tuple[str, ...], ...],
) -> str | None:
    value = first_value_at_paths(event, paths)
    return value if isinstance(value, str) and value else None


def first_value_at_paths(
    event: dict[str, Any],
    paths: tuple[tuple[str, ...], ...],
) -> Any:
    for path in paths:
        value: Any = event
        for key in path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if value:
            return value
    return None


def looks_like_json_object(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("{") and stripped.endswith("}")
