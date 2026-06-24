"""Tests for out-of-scope edit detection (P1.T2)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from qa.scope_check import detect_out_of_scope_edits, get_planned_files  # noqa: E402


def _plan(*subtasks):
    """Build a plan dict from (files_to_modify, files_to_create) tuples."""
    built = []
    for mod, create in subtasks:
        st = {"id": "s", "description": "d", "status": "completed"}
        if mod:
            st["files_to_modify"] = mod
        if create:
            st["files_to_create"] = create
        built.append(st)
    return {"phases": [{"phase": 1, "name": "p", "subtasks": built}]}


def test_get_planned_files_unions_modify_and_create():
    plan = _plan((["a.py", "b.py"], ["c.py"]), ([], ["d.py"]))
    assert get_planned_files(plan) == {"a.py", "b.py", "c.py", "d.py"}


def test_get_planned_files_supports_chunks_alias():
    plan = {"phases": [{"chunks": [{"files_to_modify": ["x.py"]}]}]}
    assert get_planned_files(plan) == {"x.py"}


def test_get_planned_files_empty_or_none():
    assert get_planned_files(None) == set()
    assert get_planned_files({}) == set()
    assert get_planned_files({"phases": []}) == set()


def test_get_planned_files_normalizes_paths():
    plan = _plan(([".\\a.py", "./b.py", "dir\\c.py"], []))
    assert get_planned_files(plan) == {"a.py", "b.py", "dir/c.py"}


def test_detect_flags_only_unplanned_sorted():
    planned = {"a.py", "src/b.py"}
    changed = ["a.py", "src/b.py", "rogue.py", "src/other.py"]
    result = detect_out_of_scope_edits(planned, changed)
    assert [r["file"] for r in result] == ["rogue.py", "src/other.py"]
    assert all(r["reason"] for r in result)


def test_detect_ignores_framework_paths_and_dupes():
    changed = [
        ".auto-claude/specs/001/x.json",
        ".auto-claude-security.json",
        "z.py",
        "z.py",
    ]
    result = detect_out_of_scope_edits(set(), changed)
    assert [r["file"] for r in result] == ["z.py"]


def test_detect_normalizes_before_compare():
    planned = {"src/a.py"}
    changed = ["./src/a.py", "src\\b.py"]
    result = detect_out_of_scope_edits(planned, changed)
    assert [r["file"] for r in result] == ["src/b.py"]
