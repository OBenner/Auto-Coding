"""CLI helpers for runtime/provider compatibility."""

from __future__ import annotations

import json
from typing import Any

from agents.runtime.cli_profiles import (
    CLI_RUNNER_PROFILES,
    cli_runner_profiles_as_dicts,
    detect_cli_runner_availability,
    select_cli_runner_profiles,
)
from agents.runtime.compatibility import (
    PROVIDER_RUNTIME_COMPATIBILITY,
    RUNTIME_MODE_INFO,
    provider_runtime_compatibility_as_dicts,
    runtime_mode_info_as_dicts,
)
from agents.runtime.fallback import (
    RuntimePhase,
    capabilities_for_runtime_mode,
    resolve_runtime_mode_with_fallback,
)
from agents.runtime.mcp_bridge import (
    LOCAL_BRIDGE_SERVER,
    MCP_SERVER_CATALOG,
    resolve_runtime_mcp_support,
)

DEFAULT_MCP_DIAGNOSTIC_SERVERS = tuple(MCP_SERVER_CATALOG)


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


def _runner_candidate_ids_by_mode(
    runner_candidates: dict[str, Any] | None,
) -> dict[str, list[str]]:
    """Extract compact runner IDs from fallback candidate diagnostics."""
    if not runner_candidates:
        return {}
    modes = runner_candidates.get("modes", {})
    if not isinstance(modes, dict):
        return {}
    return {
        mode: list(selection.get("selected_runner_ids", []))
        for mode, selection in modes.items()
        if isinstance(selection, dict)
    }


def build_runtime_fallback_matrix(
    *,
    phase: RuntimePhase = "coding",
) -> list[dict[str, Any]]:
    """Build fail-fast and opt-in fallback diagnostics for every provider/mode."""
    matrix: list[dict[str, Any]] = []
    for provider_row in PROVIDER_RUNTIME_COMPATIBILITY:
        for mode in RUNTIME_MODE_INFO:
            fail_fast = resolve_runtime_mode_with_fallback(
                provider_name=provider_row.provider,
                requested_mode=mode.mode,
                phase=phase,
                allow_fallback=False,
            )
            fallback = resolve_runtime_mode_with_fallback(
                provider_name=provider_row.provider,
                requested_mode=mode.mode,
                phase=phase,
                allow_fallback=True,
            )
            runner_candidates = (
                fallback.runner_candidates or fail_fast.runner_candidates
            )
            matrix.append(
                {
                    "provider": provider_row.provider,
                    "phase": phase,
                    "requested_mode": mode.mode,
                    "fail_fast_selected_mode": fail_fast.selected_mode,
                    "fallback_selected_mode": fallback.selected_mode,
                    "fallback_applied": fallback.fallback_applied,
                    "fallback_reason": fallback.reason,
                    "missing_capabilities": list(fail_fast.missing_capabilities),
                    "compatible_fallbacks": list(fail_fast.compatible_fallbacks),
                    "runner_candidate_ids_by_mode": _runner_candidate_ids_by_mode(
                        runner_candidates,
                    ),
                    "selected_mode_runner_candidates": (runner_candidates or {}).get(
                        "selected_mode_runner_candidates", []
                    ),
                }
            )
    return matrix


def build_mcp_bridge_plan_matrix() -> list[dict[str, Any]]:
    """Build provider/runtime MCP bridge plan diagnostics."""
    matrix: list[dict[str, Any]] = []
    for provider_row in PROVIDER_RUNTIME_COMPATIBILITY:
        for mode in RUNTIME_MODE_INFO:
            capabilities = capabilities_for_runtime_mode(
                provider_row.provider,
                mode.mode,
            )
            bridge_available = mode.mode == "generic_edit"
            available_servers = (
                (LOCAL_BRIDGE_SERVER,) if bridge_available else ()
            )
            support = resolve_runtime_mcp_support(
                provider_name=provider_row.provider,
                runtime_name=mode.mode,
                capabilities=capabilities,
                bridge_available=bridge_available,
                tool_count=1 if bridge_available else 0,
                requested_servers=DEFAULT_MCP_DIAGNOSTIC_SERVERS,
                available_servers=available_servers,
            )
            plan = support.bridge_plan.to_dict()
            matrix.append(
                {
                    "provider": provider_row.provider,
                    "runtime_mode": mode.mode,
                    "strategy": support.strategy,
                    "available": support.available,
                    "status": plan["status"],
                    "action_required": plan["action_required"],
                    "recommended_runtime_path": plan["recommended_runtime_path"],
                    "available_servers": plan["available_servers"],
                    "unavailable_servers": plan["unavailable_servers"],
                    "native_required_servers": plan["native_required_servers"],
                    "local_bridge_required_servers": plan[
                        "local_bridge_required_servers"
                    ],
                    "unsupported_servers": plan["unsupported_servers"],
                    "bridged_servers": plan["bridged_servers"],
                }
            )
    return matrix


def build_runtime_modes_payload() -> dict[str, Any]:
    """Build structured runtime compatibility payload."""
    cli_runner_selection = {
        mode.mode: select_cli_runner_profiles(runtime_mode=mode.mode).to_dict(
            include_detection=True,
        )
        for mode in RUNTIME_MODE_INFO
    }
    return {
        "runtime_modes": runtime_mode_info_as_dicts(),
        "providers": provider_runtime_compatibility_as_dicts(),
        "cli_runner_profiles": cli_runner_profiles_as_dicts(
            include_detection=True,
        ),
        "cli_runner_selection": cli_runner_selection,
        "runtime_fallback_matrix": build_runtime_fallback_matrix(),
        "mcp_bridge_plan_matrix": build_mcp_bridge_plan_matrix(),
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
            "runner_router": (
                "Set AUTO_CODE_CLI_RUNNER_ROUTER=true only when you want "
                "incompatible direct full_autonomous requests to route to a "
                "wired CLI runner such as Codex CLI."
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
    cli_runner_selection_rows = [
        [
            mode.mode,
            ", ".join(
                select_cli_runner_profiles(runtime_mode=mode.mode).selected_runner_ids
            )
            or "none",
        ]
        for mode in RUNTIME_MODE_INFO
    ]
    runtime_fallback_rows = [
        [
            row["provider"],
            row["requested_mode"],
            ", ".join(row["missing_capabilities"]) or "none",
            ", ".join(row["compatible_fallbacks"]) or "none",
            row["fallback_selected_mode"],
            ", ".join(row["selected_mode_runner_candidates"]) or "none",
        ]
        for row in build_runtime_fallback_matrix()
        if row["requested_mode"] == "full_autonomous" or row["missing_capabilities"]
    ]
    mcp_bridge_rows = [
        [
            row["provider"],
            row["runtime_mode"],
            row["strategy"],
            row["status"],
            row["action_required"],
            ", ".join(row["bridged_servers"]) or "none",
            ", ".join(row["native_required_servers"]) or "none",
        ]
        for row in build_mcp_bridge_plan_matrix()
        if row["runtime_mode"] in {"full_autonomous", "generic_edit"}
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
            "CLI Runner Selection",
            _format_table(
                ["Runtime mode", "Eligible runners"],
                cli_runner_selection_rows,
            ),
            "Runtime Fallback Matrix (coding)",
            _format_table(
                [
                    "Provider",
                    "Requested",
                    "Missing capabilities",
                    "Compatible fallbacks",
                    "Opt-in selected",
                    "Runner candidates",
                ],
                runtime_fallback_rows,
            ),
            "MCP Bridge Plan Matrix",
            _format_table(
                [
                    "Provider",
                    "Runtime",
                    "Strategy",
                    "Status",
                    "Action",
                    "Bridged",
                    "Native required",
                ],
                mcp_bridge_rows,
            ),
            "Recommended commands",
            "  Full autonomous: python run.py --spec 001 --provider claude",
            "  Generic edit:    AGENT_PROVIDER_CODER=openai AGENT_RUNTIME_MODE_CODER=generic_edit python run.py --spec 001",
            "  Analysis:        python run.py --spec 001 --provider openai --analyze",
            "  Patch proposal:  python run.py --spec 001 --provider openai --runtime-mode patch_proposal",
            "  Runtime fallback: AUTO_CODE_RUNTIME_FALLBACK=true python run.py --spec 001 --provider openai",
            "  Runner router:   AUTO_CODE_CLI_RUNNER_ROUTER=true python run.py --spec 001 --provider openai",
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
