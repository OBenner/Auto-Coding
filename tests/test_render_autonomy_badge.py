"""Tests for the autonomy readiness shields.io badge renderer."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "render_autonomy_badge.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("render_autonomy_badge", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_MOD = _load_module()
render_badge = _MOD.render_badge


def _entry(**over):
    base = {"provider": "openrouter", "gate": {"allowed": False}}
    base.update(over)
    return {"providers": [base]}


def test_ready_when_gate_allowed():
    badge = render_badge(_entry(gate={"allowed": True}), "openrouter")
    assert badge["message"] == "ready"
    assert badge["color"] == "brightgreen"
    assert badge["label"] == "autonomy: openrouter"
    assert badge["schemaVersion"] == 1


def test_shows_stable_progress_while_accumulating():
    badge = render_badge(
        _entry(evidence={"consecutive_passes": 2}, policy={"min_stable_runs": 3}),
        "openrouter",
    )
    assert badge["message"] == "2/3 stable"
    assert badge["color"] == "yellow"


def test_no_evidence_when_history_missing():
    badge = render_badge(
        _entry(evidence={}, evidence_status="provider_history_missing"),
        "openrouter",
    )
    assert badge["message"] == "no evidence"
    assert badge["color"] == "lightgrey"


def test_other_history_issue_is_surfaced():
    badge = render_badge(
        _entry(evidence={}, evidence_status="provider_history_flaky"),
        "openrouter",
    )
    assert badge["message"] == "flaky"
    assert badge["color"] == "orange"


def test_unknown_provider():
    badge = render_badge({"providers": []}, "openrouter")
    assert badge["message"] == "unknown"


def test_main_writes_output_file(tmp_path, monkeypatch, capsys):
    payload = {"providers": [{"provider": "openrouter", "gate": {"allowed": True}}]}
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(json.dumps(payload)))
    out = tmp_path / "badge.json"
    rc = _MOD.main(["--provider", "openrouter", "--output", str(out)])
    assert rc == 0
    written = json.loads(out.read_text())
    assert written["message"] == "ready"
    assert written["schemaVersion"] == 1
