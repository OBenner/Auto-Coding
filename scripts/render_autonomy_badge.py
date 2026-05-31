#!/usr/bin/env python3
"""Render a shields.io endpoint badge from ``--autonomy-readiness`` JSON.

Reads the ``run.py --autonomy-readiness <provider> --json`` payload on stdin
and writes a shields.io *endpoint* badge describing whether the provider's
recorded evidence is sufficient for promotion to full autonomous operation.

Drive it with ``AUTO_CODE_AUTONOMY=safe`` so the promotion gate actually
evaluates the evidence instead of short-circuiting on the (default) off knob:

    AUTO_CODE_AUTONOMY=safe python apps/backend/run.py \
        --autonomy-readiness openrouter --json \
      | python scripts/render_autonomy_badge.py --provider openrouter \
        --output .github/badges/autonomy-openrouter.json

The badge reflects committed evidence, so it lights up only once a provider's
passing runs are persisted to ``provider-smoke-history.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _provider_entry(payload: dict, provider: str) -> dict | None:
    """Return the readiness entry for ``provider``, or ``None``."""
    for entry in payload.get("providers", []) or []:
        if isinstance(entry, dict) and entry.get("provider") == provider:
            return entry
    return None


def render_badge(payload: dict, provider: str) -> dict:
    """Build a shields.io endpoint badge dict for ``provider``.

    - gate allowed -> "ready" (green): evidence is sufficient to promote.
    - accumulating -> "N/M stable" (yellow): trailing pass streak vs
      ``min_stable_runs``.
    - no history -> "no evidence" (lightgrey).
    - any other recorded history issue -> that issue (orange).
    """
    label = f"autonomy: {provider}"

    def badge(message: str, color: str) -> dict:
        return {
            "schemaVersion": 1,
            "label": label,
            "message": message,
            "color": color,
        }

    entry = _provider_entry(payload, provider)
    if entry is None:
        return badge("unknown", "lightgrey")

    gate = entry.get("gate") or {}
    if gate.get("allowed") is True:
        return badge("ready", "brightgreen")

    evidence = entry.get("evidence") or {}
    policy = entry.get("policy") or {}
    consecutive = evidence.get("consecutive_passes") if isinstance(evidence, dict) else None
    threshold = policy.get("min_stable_runs") if isinstance(policy, dict) else None
    if isinstance(consecutive, int) and isinstance(threshold, int):
        return badge(f"{consecutive}/{threshold} stable", "yellow")

    evidence_status = entry.get("evidence_status")
    if evidence_status in (None, "", "provider_history_missing"):
        return badge("no evidence", "lightgrey")

    pretty = str(evidence_status).replace("provider_history_", "").replace("_", " ")
    return badge(pretty, "orange")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", required=True, help="Provider to render.")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write the badge JSON here (default: stdout).",
    )
    args = parser.parse_args(argv)

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    badge = render_badge(payload, args.provider)
    text = json.dumps(badge, indent=2, sort_keys=True) + "\n"
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
