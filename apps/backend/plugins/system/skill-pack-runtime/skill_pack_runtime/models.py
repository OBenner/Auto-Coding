"""Data models for portable SKILL.md packs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillResource:
    """A project-local resource bundled with a skill."""

    relative_path: str
    kind: str

    def to_dict(self) -> dict[str, str]:
        return {"relative_path": self.relative_path, "kind": self.kind}


@dataclass(frozen=True)
class SkillCatalogEntry:
    """Lightweight skill advertisement shown before activation."""

    name: str
    description: str
    skill_id: str
    skill_dir: Path
    skill_md_path: Path
    resources: list[SkillResource] = field(default_factory=list)

    @property
    def has_scripts(self) -> bool:
        return any(resource.kind == "script" for resource in self.resources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "skill_id": self.skill_id,
            "skill_dir": str(self.skill_dir),
            "skill_md_path": str(self.skill_md_path),
            "has_scripts": self.has_scripts,
            "resources": [resource.to_dict() for resource in self.resources],
        }


@dataclass(frozen=True)
class SkillDefinition:
    """Full skill instructions loaded only after activation."""

    catalog: SkillCatalogEntry
    instructions: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.catalog.name

    @property
    def description(self) -> str:
        return self.catalog.description

    @property
    def resources(self) -> list[SkillResource]:
        return self.catalog.resources
