"""Discovery and lazy loading for project-local SKILL.md packs."""

from __future__ import annotations

from pathlib import Path

from plugins.markdown_frontmatter import split_frontmatter

from .models import SkillCatalogEntry, SkillDefinition, SkillResource


class SkillPackLoader:
    """Read `skills/*/SKILL.md` using progressive disclosure semantics."""

    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.skills_dir = self.project_dir / "skills"

    def discover_catalog(self) -> list[SkillCatalogEntry]:
        """Return name/description catalog entries without skill bodies."""
        if not self.skills_dir.exists():
            return []

        entries: list[SkillCatalogEntry] = []
        for skill_md_path in sorted(self.skills_dir.glob("*/SKILL.md")):
            metadata, body = split_frontmatter(
                skill_md_path.read_text(encoding="utf-8")
            )
            skill_dir = skill_md_path.parent
            name = str(metadata.get("name") or skill_dir.name).strip()
            description = str(
                metadata.get("description") or _first_paragraph(body)
            ).strip()
            if not name or not description:
                continue
            entries.append(
                SkillCatalogEntry(
                    name=name,
                    description=description,
                    skill_id=skill_dir.name,
                    skill_dir=skill_dir,
                    skill_md_path=skill_md_path,
                    resources=self._resources_for(skill_dir),
                )
            )

        return sorted(entries, key=lambda entry: entry.name)

    def load_skill(self, skill_id_or_name: str) -> SkillDefinition | None:
        """Load the full SKILL.md body for one selected skill."""
        for entry in self.discover_catalog():
            if skill_id_or_name not in {entry.skill_id, entry.name}:
                continue
            metadata, body = split_frontmatter(
                entry.skill_md_path.read_text(encoding="utf-8")
            )
            return SkillDefinition(catalog=entry, instructions=body, metadata=metadata)
        return None

    def _resources_for(self, skill_dir: Path) -> list[SkillResource]:
        resources: list[SkillResource] = []
        resource_kinds = {
            "scripts": "script",
            "references": "reference",
            "assets": "asset",
        }
        for folder_name, kind in resource_kinds.items():
            folder = skill_dir / folder_name
            if not folder.exists():
                continue
            for path in sorted(item for item in folder.rglob("*") if item.is_file()):
                resources.append(
                    SkillResource(
                        relative_path=path.relative_to(skill_dir).as_posix(),
                        kind=kind,
                    )
                )
        return resources


def _first_paragraph(markdown: str) -> str:
    for block in markdown.split("\n\n"):
        cleaned = " ".join(line.strip() for line in block.splitlines()).strip()
        if cleaned and not cleaned.startswith("#"):
            return cleaned
    return ""
