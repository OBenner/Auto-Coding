"""Tests for ``core.paths`` and the ``.auto-Codex`` -> ``.auto-claude/runtime`` migration.

Pins the contract documented in
``docs/roadmap/non-claude-provider-autonomy.md`` (Phase 0.3):

- Writes go to ``.auto-claude/runtime/``.
- Reads tolerate the legacy ``.auto-Codex/`` location.
- New path wins when both exist.
- The migration script moves files in place and is idempotent.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from core.paths import (
    AUTO_CODE_RUNTIME_DIR,
    LEGACY_AUTO_CODEX_DIR,
    PROVIDER_SMOKE_HISTORY_FILENAME,
    legacy_provider_smoke_history_path,
    provider_smoke_history_path,
    resolve_provider_smoke_history_path,
)

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "scripts"
    / "migrate_auto_codex_dir.py"
)


def _load_migrate_module():
    spec = importlib.util.spec_from_file_location(
        "migrate_auto_codex_dir", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_new_runtime_dir_is_under_auto_claude():
    """``.auto-claude/runtime`` is the canonical home."""
    assert AUTO_CODE_RUNTIME_DIR.parts == (".auto-claude", "runtime")


def test_legacy_dir_matches_codex_agent_series_convention():
    """The legacy location is the ``.auto-Codex`` path PRs #250-#263 used."""
    assert LEGACY_AUTO_CODEX_DIR.parts == (".auto-Codex",)


def test_provider_smoke_history_filename_is_unchanged():
    """The filename stays stable across the directory rename."""
    assert PROVIDER_SMOKE_HISTORY_FILENAME == "provider-smoke-history.json"


def test_resolve_prefers_new_path_when_both_exist(tmp_path: Path):
    new_path = provider_smoke_history_path(tmp_path)
    legacy_path = legacy_provider_smoke_history_path(tmp_path)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.write_text("{}", encoding="utf-8")
    legacy_path.write_text("{}", encoding="utf-8")

    assert resolve_provider_smoke_history_path(tmp_path) == new_path


def test_resolve_falls_back_to_legacy_when_only_legacy_present(tmp_path: Path):
    legacy_path = legacy_provider_smoke_history_path(tmp_path)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text("{}", encoding="utf-8")

    assert resolve_provider_smoke_history_path(tmp_path) == legacy_path


def test_resolve_returns_new_path_when_neither_exists(tmp_path: Path):
    """A caller can write to the resolved path even on a fresh project."""
    new_path = provider_smoke_history_path(tmp_path)

    assert resolve_provider_smoke_history_path(tmp_path) == new_path
    assert not new_path.exists()


def test_provider_smoke_history_uses_new_path_when_writing(tmp_path: Path):
    """Writing through ``_with_provider_run_history`` lands in the new location."""
    from cli.provider_smoke_commands import (
        ProviderSmokeResult,
        _with_provider_run_history,
    )

    _with_provider_run_history(
        tmp_path,
        ProviderSmokeResult(
            success=True,
            provider="openai",
            model="gpt-4o",
            runtime_mode="provider_e2e",
            message="ok",
            runtime_diagnostics={
                "provider_e2e_suite": {"status": "passed", "runs": []},
                "provider_reliability": {"status": "complete"},
            },
        ),
    )

    new_path = provider_smoke_history_path(tmp_path)
    legacy_path = legacy_provider_smoke_history_path(tmp_path)
    assert new_path.exists()
    assert not legacy_path.exists()


def test_provider_smoke_history_reads_legacy_when_only_legacy_present(
    tmp_path: Path,
):
    """A stale clone with only ``.auto-Codex/`` history still gets read on write."""
    from cli.provider_smoke_commands import (
        ProviderSmokeResult,
        _with_provider_run_history,
    )

    legacy_path = legacy_provider_smoke_history_path(tmp_path)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "provider": "openai",
                        "runtime_mode": "provider_e2e",
                        "status": "passed",
                    }
                ],
                "providers": {},
            }
        ),
        encoding="utf-8",
    )

    _with_provider_run_history(
        tmp_path,
        ProviderSmokeResult(
            success=True,
            provider="openai",
            model="gpt-4o",
            runtime_mode="provider_e2e",
            message="ok",
            runtime_diagnostics={
                "provider_e2e_suite": {"status": "passed", "runs": []},
                "provider_reliability": {"status": "complete"},
            },
        ),
    )

    new_path = provider_smoke_history_path(tmp_path)
    new_payload = json.loads(new_path.read_text(encoding="utf-8"))
    # New record was appended onto the legacy history rather than overwriting it.
    assert len(new_payload["runs"]) == 2


def test_migrate_script_dry_run_does_not_move_files(tmp_path: Path):
    legacy_path = legacy_provider_smoke_history_path(tmp_path)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text("{}", encoding="utf-8")
    new_path = provider_smoke_history_path(tmp_path)

    migrate = _load_migrate_module()
    exit_code = migrate.migrate(
        tmp_path, apply=False, delete_empty_source=False
    )

    assert exit_code == 0
    assert legacy_path.exists()
    assert not new_path.exists()


def test_migrate_script_apply_moves_files(tmp_path: Path):
    legacy_path = legacy_provider_smoke_history_path(tmp_path)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text('{"runs": []}', encoding="utf-8")
    new_path = provider_smoke_history_path(tmp_path)

    migrate = _load_migrate_module()
    exit_code = migrate.migrate(
        tmp_path, apply=True, delete_empty_source=True
    )

    assert exit_code == 0
    assert not legacy_path.exists()
    assert new_path.exists()
    assert new_path.read_text(encoding="utf-8") == '{"runs": []}'
    assert not (tmp_path / ".auto-Codex").exists()


def test_migrate_script_is_idempotent(tmp_path: Path):
    legacy_path = legacy_provider_smoke_history_path(tmp_path)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text("{}", encoding="utf-8")

    migrate = _load_migrate_module()
    first = migrate.migrate(tmp_path, apply=True, delete_empty_source=True)
    second = migrate.migrate(tmp_path, apply=True, delete_empty_source=True)

    assert first == 0
    assert second == 0


def test_migrate_script_skips_when_target_exists(tmp_path: Path):
    legacy_path = legacy_provider_smoke_history_path(tmp_path)
    new_path = provider_smoke_history_path(tmp_path)
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text("legacy", encoding="utf-8")
    new_path.write_text("new", encoding="utf-8")

    migrate = _load_migrate_module()
    exit_code = migrate.migrate(
        tmp_path, apply=True, delete_empty_source=False
    )

    assert exit_code == 0
    # Both files remain untouched because the target already existed.
    assert legacy_path.read_text(encoding="utf-8") == "legacy"
    assert new_path.read_text(encoding="utf-8") == "new"


def test_migrate_script_rejects_legacy_file_in_place_of_directory(
    tmp_path: Path,
):
    (tmp_path / ".auto-Codex").write_text("not a directory", encoding="utf-8")

    migrate = _load_migrate_module()
    exit_code = migrate.migrate(
        tmp_path, apply=False, delete_empty_source=False
    )

    assert exit_code == 2


def test_migrate_script_is_noop_when_legacy_missing(tmp_path: Path):
    migrate = _load_migrate_module()
    exit_code = migrate.migrate(
        tmp_path, apply=True, delete_empty_source=True
    )

    assert exit_code == 0
