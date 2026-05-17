"""Small frontmatter parser shared by built-in plugins."""

from __future__ import annotations

from typing import Any


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return simple YAML-like frontmatter and markdown body."""
    if not text.startswith("---"):
        return {}, text.strip()

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, text.strip()

    metadata = parse_simple_frontmatter(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :]).strip()
    return metadata, body


def parse_simple_frontmatter(lines: list[str]) -> dict[str, Any]:
    """Parse a conservative subset of YAML frontmatter."""
    metadata: dict[str, Any] = {}
    current_key: str | None = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if current_key and stripped.startswith("- "):
            metadata.setdefault(current_key, []).append(_clean_value(stripped[2:]))
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key
        if value == "":
            metadata[key] = []
        else:
            metadata[key] = _parse_value(value)

    return metadata


def _parse_value(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_clean_value(part.strip()) for part in inner.split(",")]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return _clean_value(value)


def _clean_value(value: str) -> str:
    return value.strip().strip('"').strip("'")
