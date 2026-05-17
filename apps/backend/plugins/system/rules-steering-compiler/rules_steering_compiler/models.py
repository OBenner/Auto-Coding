"""Data models for compiled steering context."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SteeringRule:
    """One imported steering instruction file."""

    source_type: str
    relative_path: str
    path: Path
    content: str
    phases: list[str] = field(default_factory=list)
    globs: list[str] = field(default_factory=list)
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "relative_path": self.relative_path,
            "phases": self.phases,
            "globs": self.globs,
            "description": self.description,
        }


@dataclass(frozen=True)
class CompiledSteeringContext:
    """Rules matched for one agent phase and optional file set."""

    project_dir: Path
    phase: str
    files: list[str]
    rules: list[SteeringRule]

    @property
    def text(self) -> str:
        if not self.rules:
            return ""

        lines = [
            "# Rules Steering Compiler",
            f"Compiled steering context for phase `{self.phase or 'unknown'}`.",
        ]
        if self.files:
            lines.append("Files: " + ", ".join(self.files))

        for rule in self.rules:
            lines.extend(
                [
                    "",
                    f"## {rule.relative_path} ({rule.source_type})",
                    rule.content.strip(),
                ]
            )

        return "\n".join(lines).strip()
