"""Tests for the nightly provider e2e probe runner.

The runner is exercised entirely without spawning real subprocesses or
contacting live providers — the ``runner`` callable is mocked so we
can pin its argument shape, JSON parsing, credential gating, and the
aggregate status math.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent / "scripts" / "nightly_provider_e2e.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("nightly_provider_e2e", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclass introspection (which reads
    # cls.__module__ -> sys.modules[name].__dict__) can find it.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runner_module():
    return _load_module()


def _fake_completed(stdout: str, stderr: str = "", returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def _success_payload(provider: str) -> str:
    return json.dumps(
        {
            "success": True,
            "provider": provider,
            "message": "Provider e2e smoke suite passed",
            "runtime_diagnostics": {
                "provider_e2e_suite": {
                    "status": "passed",
                    "runs": [{}, {}, {}],
                },
                "provider_reliability": {"status": "complete"},
                "provider_autonomous_readiness": {
                    "status": "full_autonomous_candidate",
                    "recommendation": "api_runtime_full_autonomous_candidate",
                },
                "provider_autonomous_promotion_gate": {
                    "status": "passed",
                    "promotion_ready": True,
                },
                "provider_e2e_mcp_execution_smokes": {"status": "skipped"},
            },
        }
    )


def _failure_payload(provider: str) -> str:
    return json.dumps(
        {
            "success": False,
            "provider": provider,
            "message": "Provider e2e smoke suite failed",
            "runtime_diagnostics": {
                "provider_e2e_suite": {"status": "failed", "runs": []},
                "provider_reliability": {"status": "partial_coverage"},
            },
        }
    )


def test_skips_providers_with_missing_credentials(runner_module, tmp_path):
    """Providers without env vars are reported as skipped, not attempted."""
    runner_mock = MagicMock()
    summary = runner_module.run_nightly_probes(
        providers=["openai", "google"],
        backend_dir=tmp_path,
        env={},  # no credentials
        runner=runner_mock,
    )

    assert summary.providers_attempted == 0
    assert summary.providers_skipped == 2
    assert summary.overall_status == "none_attempted"
    runner_mock.assert_not_called()
    for result in summary.per_provider:
        assert result.status == "skipped"
        assert "credentials_missing" in result.reason


def test_runs_only_credentialed_providers(runner_module, tmp_path):
    """Providers with credentials get a subprocess call; others are skipped."""

    def runner(cmd, **kwargs):
        provider_index = cmd.index("--provider") + 1
        return _fake_completed(_success_payload(cmd[provider_index]))

    summary = runner_module.run_nightly_probes(
        providers=["openai", "google", "openrouter"],
        backend_dir=tmp_path,
        env={"OPENAI_API_KEY": "sk-test", "GOOGLE_API_KEY": "g-test"},
        runner=runner,
    )

    assert summary.providers_attempted == 2
    assert summary.providers_passed == 2
    assert summary.providers_skipped == 1
    assert summary.overall_status == "all_passed"
    statuses = {r.provider: r.status for r in summary.per_provider}
    assert statuses == {
        "openai": "passed",
        "google": "passed",
        "openrouter": "skipped",
    }


def test_failure_marks_overall_some_failed(runner_module, tmp_path):
    """A single provider failure flips overall_status to some_failed."""

    def runner(cmd, **kwargs):
        provider_index = cmd.index("--provider") + 1
        provider = cmd[provider_index]
        if provider == "openai":
            return _fake_completed(_success_payload(provider))
        return _fake_completed(_failure_payload(provider), returncode=1)

    summary = runner_module.run_nightly_probes(
        providers=["openai", "google"],
        backend_dir=tmp_path,
        env={"OPENAI_API_KEY": "sk", "GOOGLE_API_KEY": "g"},
        runner=runner,
    )

    assert summary.providers_passed == 1
    assert summary.providers_failed == 1
    assert summary.overall_status == "some_failed"


def test_unparseable_output_reports_error(runner_module, tmp_path):
    """Non-JSON stdout is reported as a probe error with an excerpt."""

    def runner(cmd, **kwargs):
        return _fake_completed("not valid json\n", stderr="oops")

    summary = runner_module.run_nightly_probes(
        providers=["openai"],
        backend_dir=tmp_path,
        env={"OPENAI_API_KEY": "sk"},
        runner=runner,
    )

    result = summary.per_provider[0]
    assert result.status == "error"
    assert result.reason == "probe_output_not_json"
    assert result.error and "oops" in result.error
    assert summary.overall_status == "some_failed"


def test_timeout_is_recorded_as_error(runner_module, tmp_path):
    """A subprocess.TimeoutExpired surfaces as a structured error."""
    import subprocess

    def runner(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=1.0)

    summary = runner_module.run_nightly_probes(
        providers=["openai"],
        backend_dir=tmp_path,
        env={"OPENAI_API_KEY": "sk"},
        runner=runner,
    )

    result = summary.per_provider[0]
    assert result.status == "error"
    assert result.reason == "probe_timed_out"
    assert result.duration_seconds is not None


def test_unknown_provider_rejected(runner_module, tmp_path):
    """Providers outside the direct-API allowlist are reported as errors."""
    summary = runner_module.run_nightly_probes(
        providers=["claude"],  # not in DEFAULT_PROVIDERS
        backend_dir=tmp_path,
        env={},
        runner=MagicMock(),
    )

    result = summary.per_provider[0]
    assert result.status == "error"
    assert result.reason == "provider_not_in_direct_api_allowlist"


def test_command_uses_provider_smoke_runtime_provider_e2e_json(runner_module, tmp_path):
    """The script always asks for the full provider_e2e JSON output."""
    captured = {}

    def runner(cmd, **kwargs):
        captured["cmd"] = list(cmd)
        return _fake_completed(_success_payload("openai"))

    runner_module.run_nightly_probes(
        providers=["openai"],
        backend_dir=tmp_path,
        env={"OPENAI_API_KEY": "sk"},
        runner=runner,
    )

    assert "--provider" in captured["cmd"]
    assert "openai" in captured["cmd"]
    assert "--provider-smoke" in captured["cmd"]
    assert "--provider-smoke-runtime" in captured["cmd"]
    assert "provider_e2e" in captured["cmd"]
    assert "--json" in captured["cmd"]


def test_extract_diagnostics_summary_handles_missing_fields(runner_module):
    """Diagnostics summary stays empty when no diagnostics are present."""
    payload = {"success": True}
    summary = runner_module._extract_diagnostics_summary(payload)
    assert summary == {}


def test_extract_diagnostics_summary_pulls_known_keys(runner_module):
    parsed = json.loads(_success_payload("openai"))
    summary = runner_module._extract_diagnostics_summary(parsed)

    assert summary["provider_e2e_status"] == "passed"
    assert summary["provider_e2e_run_count"] == 3
    assert summary["provider_reliability_status"] == "complete"
    assert summary["autonomous_readiness_status"] == "full_autonomous_candidate"
    assert summary["autonomous_promotion_status"] == "passed"
    assert summary["autonomous_promotion_ready"] is True
    assert summary["mcp_execution_smoke_status"] == "skipped"


def test_main_returns_2_when_backend_dir_missing(runner_module, tmp_path, capsys):
    rc = runner_module.main(["--backend-dir", str(tmp_path / "nope")])
    assert rc == 2
    err = capsys.readouterr().err
    assert "not found" in err


def test_main_writes_output_to_file(runner_module, tmp_path, monkeypatch, capsys):
    """``--output PATH`` writes the JSON summary to disk."""
    backend = tmp_path / "apps" / "backend"
    backend.mkdir(parents=True)
    (backend / "run.py").write_text("# stub")

    def fake_run(cmd, **kwargs):
        return _fake_completed(_success_payload("openai"))

    monkeypatch.setattr(
        runner_module.subprocess,
        "run",
        fake_run,
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    out_path = tmp_path / "summary.json"
    rc = runner_module.main(
        [
            "--backend-dir",
            str(backend),
            "--providers",
            "openai",
            "--output",
            str(out_path),
        ]
    )

    assert rc == 0
    payload = json.loads(out_path.read_text())
    assert payload["overall_status"] == "all_passed"
    assert payload["providers_passed"] == 1


def test_main_returns_1_when_a_provider_fails(
    runner_module, tmp_path, monkeypatch, capsys
):
    backend = tmp_path / "apps" / "backend"
    backend.mkdir(parents=True)
    (backend / "run.py").write_text("# stub")

    def fake_run(cmd, **kwargs):
        return _fake_completed(_failure_payload("openai"), returncode=1)

    monkeypatch.setattr(runner_module.subprocess, "run", fake_run)
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    rc = runner_module.main(["--backend-dir", str(backend), "--providers", "openai"])
    assert rc == 1


def test_probe_failure_excerpt_prefers_stderr_tail(runner_module):
    """The diagnostic excerpt keeps the traceback tail and the exit code.

    A benign startup warning at the head of stderr (e.g. the Linux
    ``secretstorage`` notice) must not crowd out the real exception, which
    Python prints last.
    """
    completed = SimpleNamespace(
        stdout="",
        stderr="benign secretstorage warning\n" + ("x" * 5000) + "\nRealError: boom",
        returncode=1,
    )
    excerpt = runner_module._probe_failure_excerpt(completed, limit=2000)
    assert "run.py exited 1" in excerpt
    assert "RealError: boom" in excerpt  # tail preserved
    assert "benign secretstorage warning" not in excerpt  # head dropped
    assert "truncated" in excerpt


def test_provider_run_command_prefers_backend_venv_python(runner_module, tmp_path):
    """run.py is invoked with the backend venv interpreter when present.

    Guards the CI failure where the probe ran run.py under the bare system
    Python (no backend deps) and it aborted before emitting JSON.
    """
    backend = tmp_path / "backend"
    venv_python = backend / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("")  # presence is all that matters

    cmd = runner_module._provider_run_command(
        provider="openai", backend_dir=backend, timeout_seconds=10
    )

    assert cmd[0] == str(venv_python)
    assert cmd[1] == str(backend / "run.py")


def test_provider_run_command_falls_back_to_sys_executable(runner_module, tmp_path):
    """Without a backend venv, fall back to the current interpreter."""
    cmd = runner_module._provider_run_command(
        provider="openai", backend_dir=tmp_path, timeout_seconds=10
    )

    assert cmd[0] == sys.executable


def test_runs_per_provider_repeats_credentialed_probe(runner_module, tmp_path):
    """``runs_per_provider=N`` invokes the probe N times for one provider.

    The provider-smoke command appends one history record per invocation,
    so N passing runs in a single job leave a trailing streak the gate
    counts toward ``min_stable_runs`` — yet the summary still reports one
    provider (not N) as attempted/passed.
    """
    calls: list[str] = []

    def runner(cmd, **kwargs):
        provider_index = cmd.index("--provider") + 1
        calls.append(cmd[provider_index])
        return _fake_completed(_success_payload(cmd[provider_index]))

    summary = runner_module.run_nightly_probes(
        providers=["openai"],
        backend_dir=tmp_path,
        env={"OPENAI_API_KEY": "sk"},
        runs_per_provider=3,
        runner=runner,
    )

    assert calls == ["openai", "openai", "openai"]
    assert summary.providers_attempted == 1
    assert summary.providers_passed == 1
    assert summary.overall_status == "all_passed"
    result = summary.per_provider[0]
    assert result.status == "passed"
    assert result.runs_attempted == 3
    assert result.runs_passed == 3


def test_runs_per_provider_any_failure_blocks_provider(runner_module, tmp_path):
    """One flaky run inside the night marks the whole provider failed."""
    outcomes = iter(["passed", "failed", "passed"])

    def runner(cmd, **kwargs):
        provider_index = cmd.index("--provider") + 1
        provider = cmd[provider_index]
        if next(outcomes) == "passed":
            return _fake_completed(_success_payload(provider))
        return _fake_completed(_failure_payload(provider), returncode=1)

    summary = runner_module.run_nightly_probes(
        providers=["openai"],
        backend_dir=tmp_path,
        env={"OPENAI_API_KEY": "sk"},
        runs_per_provider=3,
        runner=runner,
    )

    result = summary.per_provider[0]
    assert result.status == "failed"
    assert result.runs_attempted == 3
    assert result.runs_passed == 2
    assert summary.providers_passed == 0
    assert summary.overall_status == "some_failed"


def test_runs_per_provider_does_not_repeat_skipped(runner_module, tmp_path):
    """A provider without credentials is probed zero times, not N times."""
    runner_mock = MagicMock()

    summary = runner_module.run_nightly_probes(
        providers=["google"],
        backend_dir=tmp_path,
        env={},  # no credentials
        runs_per_provider=3,
        runner=runner_mock,
    )

    runner_mock.assert_not_called()
    result = summary.per_provider[0]
    assert result.status == "skipped"
    assert result.runs_attempted == 0
    assert result.runs_passed == 0


def test_main_runs_per_provider_invokes_probe_n_times(
    runner_module, tmp_path, monkeypatch
):
    """``--runs-per-provider 3`` reaches the subprocess as 3 invocations."""
    backend = tmp_path / "apps" / "backend"
    backend.mkdir(parents=True)
    (backend / "run.py").write_text("# stub")
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return _fake_completed(_success_payload("openai"))

    monkeypatch.setattr(runner_module.subprocess, "run", fake_run)
    monkeypatch.setenv("OPENAI_API_KEY", "sk")
    rc = runner_module.main(
        [
            "--backend-dir",
            str(backend),
            "--providers",
            "openai",
            "--runs-per-provider",
            "3",
        ]
    )

    assert rc == 0
    assert len(calls) == 3
