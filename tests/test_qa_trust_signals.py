"""Tests for Trust Layer confidence/uncertainty signals (P1.T3).

Covers the runtime qa_signoff merge carrying + sanitizing the model's
self-reported confidence and uncertainty, and the build reading them into the
verification report.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from cli.build_commands import _generate_verification_report_data  # noqa: E402
from qa.reviewer import merge_runtime_qa_signoff_artifact  # noqa: E402


def _write_plan(spec_dir: Path, signoff=None) -> Path:
    plan = spec_dir / "implementation_plan.json"
    plan.write_text(json.dumps({"qa_signoff": signoff}), encoding="utf-8")
    return plan


def _write_artifact(spec_dir: Path, payload: dict) -> None:
    (spec_dir / "qa_signoff.json").write_text(json.dumps(payload), encoding="utf-8")


def test_merge_carries_confidence_and_uncertainty(tmp_path):
    plan = _write_plan(tmp_path)
    _write_artifact(
        tmp_path,
        {
            "status": "approved",
            "confidence": 0.83,
            "uncertainty": [{"area": "timeouts", "reason": "no test"}],
        },
    )
    assert merge_runtime_qa_signoff_artifact(tmp_path, qa_session=1) is True
    signoff = json.loads(plan.read_text())["qa_signoff"]
    assert signoff["confidence"] == pytest.approx(0.83)
    assert signoff["uncertainty"] == [{"area": "timeouts", "reason": "no test"}]


def test_merge_clamps_confidence_and_filters_uncertainty(tmp_path):
    plan = _write_plan(tmp_path)
    _write_artifact(
        tmp_path,
        {
            "status": "approved",
            "confidence": 1.7,
            "uncertainty": [{"area": "ok"}, "nope", 5],
        },
    )
    assert merge_runtime_qa_signoff_artifact(tmp_path, qa_session=1) is True
    signoff = json.loads(plan.read_text())["qa_signoff"]
    assert signoff["confidence"] == pytest.approx(1.0)
    assert signoff["uncertainty"] == [{"area": "ok"}]


def test_merge_drops_bool_confidence(tmp_path):
    # bool is an int subclass; it must not be coerced into a 1.0 confidence.
    plan = _write_plan(tmp_path)
    _write_artifact(tmp_path, {"status": "approved", "confidence": True})
    assert merge_runtime_qa_signoff_artifact(tmp_path, qa_session=1) is True
    signoff = json.loads(plan.read_text())["qa_signoff"]
    assert "confidence" not in signoff


def test_merge_without_signals_omits_them(tmp_path):
    plan = _write_plan(tmp_path)
    _write_artifact(tmp_path, {"status": "approved"})
    assert merge_runtime_qa_signoff_artifact(tmp_path, qa_session=1) is True
    signoff = json.loads(plan.read_text())["qa_signoff"]
    assert "confidence" not in signoff
    assert "uncertainty" not in signoff


def test_report_reads_confidence_and_uncertainty(tmp_path):
    plan = {
        "qa_signoff": {
            "status": "approved",
            "confidence": 0.77,
            "uncertainty": [{"area": "x", "reason": "y"}],
        }
    }
    (tmp_path / "implementation_plan.json").write_text(
        json.dumps(plan), encoding="utf-8"
    )
    report = _generate_verification_report_data(tmp_path, qa_approved=True)
    assert report["confidence"] == pytest.approx(0.77)
    assert report["uncertainty"] == [{"area": "x", "reason": "y"}]
