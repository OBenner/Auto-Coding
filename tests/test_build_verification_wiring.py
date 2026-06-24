"""Tests for wiring the Trust Layer verification report into the build (P1.T1-wire).

Covers the build-layer helpers that read the persisted QA sign-off from
implementation_plan.json and write artifacts/verification-report.json on
every build (not only CI/json mode).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from cli.artifacts import VERIFICATION_REPORT_FILENAME  # noqa: E402
from cli.build_commands import (  # noqa: E402
    _generate_verification_report_data,
    _save_verification_report,
)


def _write_plan(spec_dir: Path, signoff_status: str) -> None:
    plan = {
        "qa_signoff": {
            "status": signoff_status,
            "qa_session": 2,
            "issues_found": [
                {"title": "missing null check", "type": "error", "location": "a.py"}
            ],
            "test_results": {
                "tests_passing": 41,
                "tests_skipped": 1,
                "coverage_overall": "85%",
            },
        },
        "qa_stats": {"last_iteration": 3, "last_status": signoff_status},
        "qa_iteration_history": [
            {"iteration": 1, "status": "rejected", "issues": [{}], "duration_seconds": 10.0},
            {"iteration": 2, "status": "rejected", "issues": [], "duration_seconds": 5.5},
        ],
    }
    (spec_dir / "implementation_plan.json").write_text(
        json.dumps(plan), encoding="utf-8"
    )


def test_generate_report_data_from_plan(tmp_path):
    _write_plan(tmp_path, "rejected")
    report = _generate_verification_report_data(
        tmp_path, qa_approved=False, changed_files=["a.py", "b.py"]
    )
    assert report["verdict"] == "rejected"
    assert report["issues"][0]["title"] == "missing null check"
    assert report["tests_run"]["tests_passing"] == 41
    assert report["diff_summary"]["files_changed"] == 2
    assert report["iteration"] == 3
    assert report["qa_session"] == 2
    assert report["duration_seconds"] == 15.5


def test_generate_report_data_approved_overrides_status(tmp_path):
    # qa_approved (the loop's outcome) is authoritative for the verdict.
    _write_plan(tmp_path, "rejected")
    report = _generate_verification_report_data(tmp_path, qa_approved=True)
    assert report["verdict"] == "approved"


def test_generate_report_data_missing_plan(tmp_path):
    report = _generate_verification_report_data(tmp_path, qa_approved=True)
    assert report["verdict"] == "approved"
    assert report["issues"] == []
    assert report["tests_run"] == {}
    assert report["diff_summary"] == {}


def test_save_writes_artifact_without_manager(tmp_path):
    _write_plan(tmp_path, "approved")
    _save_verification_report(
        tmp_path, qa_approved=True, changed_files=None, artifact_manager=None
    )
    artifact = tmp_path / "artifacts" / VERIFICATION_REPORT_FILENAME
    assert artifact.exists()
    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert data["verdict"] == "approved"
    assert "timestamp" in data
