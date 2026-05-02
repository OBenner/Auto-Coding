"""CLI helpers for runtime/provider compatibility."""

from __future__ import annotations

import json
from typing import Any

from agents.runtime.cli_profiles import (
    CLI_RUNNER_PROFILES,
    cli_runner_profiles_as_dicts,
    detect_cli_runner_availability,
)
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
        "cli_runner_profiles": cli_runner_profiles_as_dicts(
            include_detection=True,
        ),
        "recommendations": {
            "full_autonomous": "Use provider=claude.",
            "generic_edit": (
                "Use --runtime-mode generic_edit for experimental local "
                "file/patch/shell actions with completion providers."
            ),
            "analysis_only": "Use --analyze with any configured provider.",
            "patch_proposal": (
                "Use a non-Claude completion provider with "
                "--runtime-mode patch_proposal for coder subtasks."
            ),
            "provider_smoke": "Use --provider-smoke before running a spec.",
            "runtime_fallback": (
                "Set AUTO_CODE_RUNTIME_FALLBACK=true only when you want "
                "incompatible non-Claude full_autonomous settings to degrade "
                "to a limited runtime."
            ),
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
            row.generic_edit,
            row.analysis_only,
            row.patch_proposal,
            row.mcp_tools,
            row.subagents,
            row.notes,
        ]
        for row in PROVIDER_RUNTIME_COMPATIBILITY
    ]
    cli_runner_rows = [
        [
            profile.runner_id,
            profile.tier,
            profile.role,
            profile.runner_status,
            "yes"
            if detect_cli_runner_availability(profile).executable_present
            else "no",
            ", ".join(profile.supported_runtime_modes),
            ", ".join(profile.capability_tags),
        ]
        for profile in CLI_RUNNER_PROFILES
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
                    "Generic edit",
                    "Analysis-only",
                    "Patch proposal",
                    "MCP",
                    "Subagents",
                    "Notes",
                ],
                provider_rows,
            ),
            "CLI Runner Profiles",
            _format_table(
                [
                    "Runner",
                    "Tier",
                    "Role",
                    "Status",
                    "Executable",
                    "Runtime modes",
                    "Capabilities",
                ],
                cli_runner_rows,
            ),
            "Recommended commands",
            "  Full autonomous: python run.py --spec 001 --provider claude",
            "  Generic edit:    AGENT_PROVIDER_CODER=openai AGENT_RUNTIME_MODE_CODER=generic_edit python run.py --spec 001",
            "  Analysis:        python run.py --spec 001 --provider openai --analyze",
            "  Patch proposal:  python run.py --spec 001 --provider openai --runtime-mode patch_proposal",
            "  Runtime fallback: AUTO_CODE_RUNTIME_FALLBACK=true python run.py --spec 001 --provider openai",
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
