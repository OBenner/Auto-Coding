"""Runtime artifact helpers."""

from datetime import UTC, datetime
from pathlib import Path

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

    phase_token = safe_artifact_token(phase, "phase")
    target_token = safe_artifact_token(subtask_id, f"session-{session_num}")
    artifact_path = artifact_dir / f"analysis_only_{phase_token}_{target_token}.md"
    metadata_path = artifact_dir / f"analysis_only_{phase_token}_{target_token}.json"
    timestamp = datetime.now(UTC).isoformat()

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
