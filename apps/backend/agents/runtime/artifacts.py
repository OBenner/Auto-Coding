"""Runtime artifact helpers."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.file_utils import atomic_write, write_json_atomic


def safe_artifact_token(value: str | None, fallback: str) -> str:
    """Return a filesystem-safe token for runtime artifact names."""
    raw_value = (value or fallback).strip() or fallback
    safe_chars = [
        char if char.isalnum() or char in {"-", "_", "."} else "-" for char in raw_value
    ]
    token = "".join(safe_chars).strip(".-_")
    return (token or fallback)[:80]


def save_analysis_only_artifact(
    *,
    spec_dir: Path,
    response_text: str,
    provider_name: str,
    phase: str,
    session_num: int,
    subtask_id: str | None = None,
) -> Path:
    """Persist text-only runtime output so limited providers leave useful work."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).isoformat()
    timestamp_token = safe_artifact_token(timestamp, "timestamp")
    phase_token = safe_artifact_token(phase, "phase")
    session_token = safe_artifact_token(f"session-{session_num}", "session")
    subtask_token = safe_artifact_token(subtask_id, "no-subtask")
    provider_token = safe_artifact_token(provider_name, "provider")
    basename = (
        "analysis_only_"
        f"{phase_token}_{session_token}_{subtask_token}_{provider_token}_"
        f"{timestamp_token}"
    )
    artifact_path = artifact_dir / f"{basename}.md"
    metadata_path = artifact_dir / f"{basename}.json"

    with atomic_write(artifact_path, "w", encoding="utf-8") as artifact:
        artifact.write("# Analysis-only Runtime Result\n\n")
        artifact.write(f"Provider: {provider_name}\n")
        artifact.write("Runtime mode: analysis_only\n")
        artifact.write(f"Phase: {phase}\n")
        artifact.write(f"Session: {session_num}\n")
        if subtask_id:
            artifact.write(f"Subtask: {subtask_id}\n")
        artifact.write(f"Timestamp: {timestamp}\n\n")
        artifact.write(response_text.rstrip())
        artifact.write("\n")

    write_json_atomic(
        metadata_path,
        {
            "status": "analysis_only",
            "provider": provider_name,
            "runtime_mode": "analysis_only",
            "phase": phase,
            "session": session_num,
            "subtask_id": subtask_id,
            "timestamp": timestamp,
            "analysis_artifact": str(artifact_path),
        },
        indent=2,
        ensure_ascii=False,
    )

    return artifact_path


def save_runtime_fallback_artifact(
    *,
    spec_dir: Path,
    decision: Any,
    phase: str,
    session_num: int | None = None,
    subtask_id: str | None = None,
) -> Path:
    """Persist runtime fallback metadata for diagnostics and UI consumers."""
    artifact_dir = spec_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).isoformat()
    timestamp_token = safe_artifact_token(timestamp, "timestamp")
    phase_token = safe_artifact_token(phase, "phase")
    session_token = safe_artifact_token(
        f"session-{session_num}" if session_num is not None else None,
        "no-session",
    )
    subtask_token = safe_artifact_token(subtask_id, "no-subtask")
    path = artifact_dir / (
        "runtime_fallback_"
        f"{phase_token}_{session_token}_{subtask_token}_{timestamp_token}.json"
    )

    decision_payload = (
        decision.to_dict()
        if hasattr(decision, "to_dict") and callable(decision.to_dict)
        else {"value": str(decision)}
    )
    write_json_atomic(
        path,
        {
            "timestamp": timestamp,
            "phase": phase,
            "session": session_num,
            "subtask_id": subtask_id,
            "decision": decision_payload,
        },
        indent=2,
        ensure_ascii=False,
    )
    return path
