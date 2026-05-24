"""Project-relative paths for runtime artifacts.

Runtime artifacts (provider smoke history, autonomy policy overrides,
runtime diagnostics) live under :data:`AUTO_CODE_RUNTIME_DIR` from this
PR onward. The previous home was ``.auto-Codex/`` (introduced by the
Codex-agent series in PRs #250 - #263); reads remain tolerant of the
legacy location so a stale clone still works while
``scripts/migrate_auto_codex_dir.py`` is run.
"""

from __future__ import annotations

from pathlib import Path

# New canonical directory under the project for any runtime-related
# artifact produced by Auto Code (history, policy snapshots, eval data).
AUTO_CODE_RUNTIME_DIR = Path(".auto-claude", "runtime")

# Legacy directory carried forward from the Codex-agent PR series.
# Reads consult both locations during the migration window; writes always
# use the new canonical directory.
LEGACY_AUTO_CODEX_DIR = Path(".auto-Codex")

# Filename for the provider-smoke history artifact (location-independent).
PROVIDER_SMOKE_HISTORY_FILENAME = "provider-smoke-history.json"


def provider_smoke_history_path(project_dir: Path) -> Path:
    """Return the canonical write path for the provider-smoke history."""
    return project_dir / AUTO_CODE_RUNTIME_DIR / PROVIDER_SMOKE_HISTORY_FILENAME


def legacy_provider_smoke_history_path(project_dir: Path) -> Path:
    """Return the legacy ``.auto-Codex`` path for the provider-smoke history."""
    return project_dir / LEGACY_AUTO_CODEX_DIR / PROVIDER_SMOKE_HISTORY_FILENAME


def resolve_provider_smoke_history_path(project_dir: Path) -> Path:
    """Return the readable provider-smoke history path for ``project_dir``.

    Prefers :func:`provider_smoke_history_path`. Falls back to the legacy
    location when only the old file is present. Returns the new path
    (which may not yet exist) when neither file exists, so callers can
    write to it without further branching.
    """
    new_path = provider_smoke_history_path(project_dir)
    if new_path.is_file():
        return new_path
    legacy_path = legacy_provider_smoke_history_path(project_dir)
    if legacy_path.is_file():
        return legacy_path
    return new_path
