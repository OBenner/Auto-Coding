#!/usr/bin/env python3
"""Nightly provider e2e probe runner.

Phase 2.1 of ``docs/roadmap/non-claude-provider-autonomy.md``: iterates
over the direct API providers Auto Code supports, invokes
``run.py --provider <name> --provider-smoke --provider-smoke-runtime
provider_e2e --json`` for each provider whose credentials are
configured, and aggregates the results into a single JSON summary so
scheduled CI (and ``scripts/migrate_*`` companion tools) can decide
whether to update the persisted provider-smoke history.

The script is intentionally minimal so it stays runnable from any host
with the backend installed:

- pure subprocess driver, no extra Python deps beyond stdlib
- credentials read from environment, not flags, so secrets stay out of
  process arguments / shell history
- structured JSON output to stdout (or ``--output PATH``) plus a
  human-readable summary on stderr
- exit codes: 0 if every attempted provider passed, 1 if any provider
  failed, 2 for usage / configuration errors before probes ran

The companion GitHub Actions workflow lives at
``.github/workflows/nightly-provider-autonomy.yml``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

# Direct API providers we can probe; mirrors
# ``core.autonomy_policy.DIRECT_API_PROVIDERS``.
DEFAULT_PROVIDERS: tuple[str, ...] = (
    "openai",
    "google",
    "openrouter",
    "litellm",
    "zhipuai",
    "ollama",
)

# Map provider -> env var(s) whose presence indicates the provider is
# configured for this run. Ollama is local-only so it has no API key.
_PROVIDER_CREDENTIAL_ENV: dict[str, tuple[str, ...]] = {
    "openai": ("OPENAI_API_KEY",),
    "google": ("GOOGLE_API_KEY",),
    "openrouter": ("OPENROUTER_API_KEY",),
    "litellm": ("LITELLM_API_KEY", "LITELLM_API_BASE"),
    "zhipuai": ("ZHIPUAI_API_KEY",),
    "ollama": (),  # No credentials; local Ollama bridge.
}


@dataclass
class ProviderProbeResult:
    """Result of one provider probe run."""

    provider: str
    attempted: bool
    status: str  # "passed" | "failed" | "skipped" | "error"
    reason: str
    duration_seconds: float | None = None
    runtime_diagnostics_summary: dict[str, object] | None = None
    error: str | None = None
    stdout_excerpt: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        return payload


@dataclass
class NightlySummary:
    """Aggregate summary across all providers."""

    started_at: str
    finished_at: str
    overall_status: str  # "all_passed" | "some_failed" | "none_attempted"
    providers_attempted: int
    providers_passed: int
    providers_failed: int
    providers_skipped: int
    per_provider: list[ProviderProbeResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "overall_status": self.overall_status,
            "providers_attempted": self.providers_attempted,
            "providers_passed": self.providers_passed,
            "providers_failed": self.providers_failed,
            "providers_skipped": self.providers_skipped,
            "per_provider": [r.to_dict() for r in self.per_provider],
        }


def _has_credentials(provider: str, env: Mapping[str, str]) -> bool:
    """Return True when ``provider`` has every required env var set."""
    required = _PROVIDER_CREDENTIAL_ENV.get(provider, ())
    return all(env.get(name) for name in required)


def _provider_run_command(
    *,
    provider: str,
    backend_dir: Path,
    timeout_seconds: float,
) -> list[str]:
    """Build the ``run.py --provider-smoke`` invocation for a provider."""
    return [
        sys.executable,
        str(backend_dir / "run.py"),
        "--provider",
        provider,
        "--provider-smoke",
        "--provider-smoke-runtime",
        "provider_e2e",
        "--provider-smoke-timeout",
        str(timeout_seconds),
        "--json",
    ]


def _extract_diagnostics_summary(
    parsed: Mapping[str, object],
) -> dict[str, object]:
    """Return a compact summary of the runtime_diagnostics for the report."""
    runtime_diagnostics = parsed.get("runtime_diagnostics")
    if not isinstance(runtime_diagnostics, dict):
        return {}
    summary: dict[str, object] = {}
    suite = runtime_diagnostics.get("provider_e2e_suite")
    if isinstance(suite, dict):
        summary["provider_e2e_status"] = suite.get("status")
        runs = suite.get("runs")
        if isinstance(runs, list):
            summary["provider_e2e_run_count"] = len(runs)
    reliability = runtime_diagnostics.get("provider_reliability")
    if isinstance(reliability, dict):
        summary["provider_reliability_status"] = reliability.get("status")
    readiness = runtime_diagnostics.get("provider_autonomous_readiness")
    if isinstance(readiness, dict):
        summary["autonomous_readiness_status"] = readiness.get("status")
        summary["autonomous_readiness_recommendation"] = readiness.get("recommendation")
    promotion = runtime_diagnostics.get("provider_autonomous_promotion_gate")
    if isinstance(promotion, dict):
        summary["autonomous_promotion_status"] = promotion.get("status")
        summary["autonomous_promotion_ready"] = promotion.get("promotion_ready")
    mcp_smokes = runtime_diagnostics.get("provider_e2e_mcp_execution_smokes")
    if isinstance(mcp_smokes, dict):
        summary["mcp_execution_smoke_status"] = mcp_smokes.get("status")
    return summary


def _run_one_provider(
    *,
    provider: str,
    backend_dir: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
    runner: callable | None = None,  # injectable for testing
) -> ProviderProbeResult:
    if runner is None:
        runner = subprocess.run
    """Run a single provider probe and capture its JSON output."""
    if provider not in DEFAULT_PROVIDERS:
        return ProviderProbeResult(
            provider=provider,
            attempted=False,
            status="error",
            reason="provider_not_in_direct_api_allowlist",
        )
    if not _has_credentials(provider, env):
        missing = ", ".join(
            name
            for name in _PROVIDER_CREDENTIAL_ENV.get(provider, ())
            if not env.get(name)
        )
        return ProviderProbeResult(
            provider=provider,
            attempted=False,
            status="skipped",
            reason=(
                f"credentials_missing: {missing}"
                if missing
                else "credentials_not_configured"
            ),
        )

    cmd = _provider_run_command(
        provider=provider,
        backend_dir=backend_dir,
        timeout_seconds=timeout_seconds,
    )
    started = datetime.now(UTC)
    try:
        completed = runner(
            cmd,
            cwd=str(backend_dir),
            env=dict(env),
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 30,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = (datetime.now(UTC) - started).total_seconds()
        return ProviderProbeResult(
            provider=provider,
            attempted=True,
            status="error",
            reason="probe_timed_out",
            duration_seconds=elapsed,
            error=str(exc),
        )
    elapsed = (datetime.now(UTC) - started).total_seconds()

    stdout = completed.stdout or ""
    parsed: dict[str, object]
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return ProviderProbeResult(
            provider=provider,
            attempted=True,
            status="error",
            reason="probe_output_not_json",
            duration_seconds=elapsed,
            error=(completed.stderr or stdout)[:500],
            stdout_excerpt=stdout[:500],
        )

    summary = _extract_diagnostics_summary(parsed)
    success = bool(parsed.get("success"))
    status = "passed" if success else "failed"
    return ProviderProbeResult(
        provider=provider,
        attempted=True,
        status=status,
        reason=str(parsed.get("message") or "")[:200],
        duration_seconds=elapsed,
        runtime_diagnostics_summary=summary,
    )


def run_nightly_probes(
    providers: Iterable[str],
    *,
    backend_dir: Path,
    env: Mapping[str, str],
    timeout_seconds: float = 600.0,
    runner: callable | None = None,
) -> NightlySummary:
    if runner is None:
        runner = subprocess.run
    """Run probes for ``providers`` and return an aggregate summary."""
    started = datetime.now(UTC)
    results: list[ProviderProbeResult] = []
    for provider in providers:
        results.append(
            _run_one_provider(
                provider=provider,
                backend_dir=backend_dir,
                env=env,
                timeout_seconds=timeout_seconds,
                runner=runner,
            )
        )
    finished = datetime.now(UTC)

    attempted = sum(1 for r in results if r.attempted)
    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status == "skipped")
    if attempted == 0:
        overall = "none_attempted"
    elif failed == 0 and any(r.status == "passed" for r in results):
        overall = "all_passed"
    else:
        overall = "some_failed"

    return NightlySummary(
        started_at=started.isoformat().replace("+00:00", "Z"),
        finished_at=finished.isoformat().replace("+00:00", "Z"),
        overall_status=overall,
        providers_attempted=attempted,
        providers_passed=passed,
        providers_failed=failed,
        providers_skipped=skipped,
        per_provider=results,
    )


def _print_human_summary(summary: NightlySummary, stream) -> None:
    print(
        f"[nightly-provider-e2e] {summary.overall_status} "
        f"attempted={summary.providers_attempted} "
        f"passed={summary.providers_passed} "
        f"failed={summary.providers_failed} "
        f"skipped={summary.providers_skipped}",
        file=stream,
    )
    for result in summary.per_provider:
        line = f"  - {result.provider}: {result.status}"
        if result.reason:
            line += f" ({result.reason})"
        print(line, file=stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--providers",
        nargs="+",
        default=list(DEFAULT_PROVIDERS),
        help="Direct API providers to probe (default: all known).",
    )
    parser.add_argument(
        "--backend-dir",
        type=Path,
        default=Path("apps/backend"),
        help="Path to apps/backend (default: ./apps/backend).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="Per-provider timeout in seconds passed to provider-smoke.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the JSON summary to this path (default: stdout).",
    )
    args = parser.parse_args(argv)

    backend_dir = args.backend_dir.resolve()
    if not (backend_dir / "run.py").is_file():
        print(
            f"[error] {backend_dir / 'run.py'} not found; pass --backend-dir.",
            file=sys.stderr,
        )
        return 2

    summary = run_nightly_probes(
        providers=args.providers,
        backend_dir=backend_dir,
        env=os.environ,
        timeout_seconds=args.timeout,
    )
    payload = json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    _print_human_summary(summary, sys.stderr)

    if summary.overall_status == "some_failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
