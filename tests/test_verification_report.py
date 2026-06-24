"""Tests for the Trust Layer verification report artifact (P1·T1).

Covers the pure ``build_verification_report`` builder (schema, verdict
normalization, confidence clamping, defensive copies) and the
``ArtifactManager.save_verification_report`` writer (round-trip, timestamp
stamping, disabled no-op).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from cli.artifacts import (  # noqa: E402
    VERIFICATION_REPORT_FILENAME,
    VERIFICATION_REPORT_SCHEMA_VERSION,
    ArtifactManager,
    build_verification_report,
)


def test_build_minimal_has_contract_defaults():
    report = build_verification_report(verdict="approved")

    assert report["schema_version"] == VERIFICATION_REPORT_SCHEMA_VERSION
    assert report["verdict"] == "approved"
    assert report["confidence"] is None
    assert report["tests_run"] == {}
    assert report["diff_summary"] == {}
    assert report["issues"] == []
    assert report["uncertainty"] == []
    assert report["out_of_scope_edits"] == []
    # No timestamp in the pure builder output — the writer stamps it.
    assert "timestamp" not in report


def test_build_normalizes_verdict():
    assert build_verification_report(verdict="APPROVED")["verdict"] == "approved"
    assert build_verification_report(verdict=" Rejected ")["verdict"] == "rejected"
    assert build_verification_report(verdict="weird")["verdict"] == "error"
    assert build_verification_report(verdict=None)["verdict"] == "error"


def test_build_clamps_confidence():
    assert build_verification_report(verdict="approved", confidence=1.5)["confidence"] == 1.0
    assert build_verification_report(verdict="approved", confidence=-0.3)["confidence"] == 0.0
    assert build_verification_report(verdict="approved", confidence=0.42)["confidence"] == 0.42
    # Non-numeric confidence degrades to None rather than raising.
    assert build_verification_report(verdict="approved", confidence="oops")["confidence"] is None


def test_build_does_not_mutate_caller_collections():
    issues = [{"title": "x"}]
    report = build_verification_report(verdict="rejected", issues=issues)
    report["issues"].append({"title": "y"})
    assert issues == [{"title": "x"}]


def test_build_rounds_duration():
    report = build_verification_report(verdict="approved", duration_seconds=12.3456)
    assert report["duration_seconds"] == 12.35


def test_save_and_load_round_trip(tmp_path):
    manager = ArtifactManager(spec_dir=tmp_path)
    report = build_verification_report(
        verdict="rejected",
        qa_session=1,
        iteration=2,
        tests_run={"passed": 10, "failed": 1, "total": 11},
        issues=[{"title": "boom", "type": "error"}],
    )

    path = manager.save_verification_report(report)
    assert path is not None
    assert path.name == VERIFICATION_REPORT_FILENAME

    loaded = manager.load_artifact(VERIFICATION_REPORT_FILENAME)
    assert loaded is not None
    assert loaded["verdict"] == "rejected"
    assert loaded["iteration"] == 2
    assert loaded["tests_run"]["failed"] == 1
    assert loaded["issues"][0]["title"] == "boom"
    # Writer stamps a timestamp when the caller omits one.
    assert "timestamp" in loaded


def test_save_disabled_returns_none(tmp_path):
    manager = ArtifactManager(spec_dir=tmp_path, enabled=False)
    report = build_verification_report(verdict="approved")
    assert manager.save_verification_report(report) is None
