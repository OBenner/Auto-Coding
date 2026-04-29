"""CLI helpers for runtime/provider compatibility."""

from __future__ import annotations

import json
from typing import Any

from agents.runtime.compatibility import (
    PROVIDER_RUNTIME_COMPATIBILITY,
    RUNTIME_MODE_INFO,
    provider_runtime_compatibility_as_dicts,
    runtime_mode_info_as_dicts,
)


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format a compact ASCII table."""
    widths = [
        max(len(str(cell)) for cell in column)
        for column in zip(headers, *rows, strict=True)
    ]
    header = "  ".join(cell.ljust(width) for cell, width in zip(headers, widths))
    divider = "  ".join("-" * width for width in widths)
    body = [
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)) for row in rows
    ]
    return "\n".join([header, divider, *body])


def build_runtime_modes_payload() -> dict[str, Any]:
    """Build structured runtime compatibility payload."""
    return {
        "runtime_modes": runtime_mode_info_as_dicts(),
        "providers": provider_runtime_compatibility_as_dicts(),
        "recommendations": {
            "full_autonomous": "Use provider=claude.",
            "analysis_only": "Use --analyze with any configured provider.",
            "patch_proposal": (
                "Use a non-Claude completion provider with "
                "--runtime-mode patch_proposal for coder subtasks."
            ),
            "provider_smoke": "Use --provider-smoke before running a spec.",
        },
    }


def format_runtime_modes_text() -> str:
    """Format runtime compatibility guidance for humans."""
    mode_rows = [
        [mode.mode, mode.purpose, mode.capabilities] for mode in RUNTIME_MODE_INFO
    ]
    provider_rows = [
        [
            row.provider,
            row.full_autonomous,
            row.analysis_only,
            row.patch_proposal,
            row.notes,
        ]
        for row in PROVIDER_RUNTIME_COMPATIBILITY
    ]

    return "\n\n".join(
        [
            "Runtime Modes",
            _format_table(
                ["Mode", "Purpose", "Required runtime surface"],
                mode_rows,
            ),
            "Provider Compatibility",
            _format_table(
                [
                    "Provider",
                    "Full autonomous",
                    "Analysis-only",
                    "Patch proposal",
                    "Notes",
                ],
                provider_rows,
            ),
            "Recommended commands",
            "  Full autonomous: python run.py --spec 001 --provider claude",
            "  Analysis:        python run.py --spec 001 --provider openai --analyze",
            "  Patch proposal:  python run.py --spec 001 --provider openai --runtime-mode patch_proposal",
            "  Provider smoke:  python run.py --provider openai --provider-smoke",
        ]
    )


def handle_runtime_modes_command(*, output_json: bool = False) -> dict[str, Any]:
    """Print provider/runtime compatibility information."""
    payload = build_runtime_modes_payload()
    if output_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(format_runtime_modes_text())
    return payload
