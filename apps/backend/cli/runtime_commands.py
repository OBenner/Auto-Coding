"""CLI helpers for runtime/provider compatibility."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from agents.runtime.adapters.generic_edit import inspect_generic_edit_resume_artifacts
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
    CUSTOM_MCP_SERVERS_CONFIG_KEY,
    EXTERNAL_MCP_CLIENT_ENV,
    LOCAL_BRIDGE_SERVER,
    MCP_SERVER_CATALOG,
    build_external_mcp_health_matrix,
    check_external_mcp_contracts,
    describe_external_mcp_server_health,
    discover_external_mcp_tools,
    executable_external_mcp_servers,
    executable_external_mcp_tools,
    normalize_mcp_input_schema,
    registered_external_mcp_servers,
    resolve_runtime_mcp_support,
)
from agents.runtime.subagents import (
    DEFAULT_SUBAGENT_MAX_ATTEMPTS,
    DEFAULT_SUBAGENT_MERGE_POLICY,
    resolve_runtime_subagent_support,
)
from cli.provider_smoke_commands import (
    PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS,
    PROVIDER_SMOKE_HISTORY_RELATIVE_PATH,
)

DEFAULT_MCP_DIAGNOSTIC_SERVERS = tuple(MCP_SERVER_CATALOG)
DEFAULT_EXTERNAL_MCP_SMOKE_SERVERS = registered_external_mcp_servers()
logger = logging.getLogger(__name__)

RUNTIME_POLICY_PHASES = (
    {
        "phase": "planner",
        "direct_provider_mode": "blocked",
        "fallback_modes": (),
        "requires_full_autonomous": True,
        "fallback_allowed": False,
        "policy": "must_use_full_runtime",
        "reason": "planner_requires_workspace_tools",
    },
    {
        "phase": "coder",
        "direct_provider_mode": "generic_edit",
        "fallback_modes": ("patch_proposal", "analysis_only"),
        "requires_full_autonomous": False,
        "fallback_allowed": True,
        "policy": "prefer_generic_edit",
        "reason": "coder_can_use_generic_edit_transactions",
    },
    {
        "phase": "qa_reviewer",
        "direct_provider_mode": "analysis_only",
        "fallback_modes": (),
        "requires_full_autonomous": False,
        "fallback_allowed": True,
        "policy": "prefer_analysis_only",
        "reason": "qa_review_can_run_without_mutation",
    },
    {
        "phase": "qa_fixer",
        "direct_provider_mode": "generic_edit",
        "fallback_modes": ("patch_proposal", "analysis_only"),
        "requires_full_autonomous": False,
        "fallback_allowed": True,
        "policy": "prefer_generic_edit",
        "reason": "qa_fix_needs_transactional_mutations",
    },
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
            available_servers = (LOCAL_BRIDGE_SERVER,) if bridge_available else ()
            if bridge_available:
                available_servers = (
                    *available_servers,
                    *executable_external_mcp_servers(
                        requested_servers=DEFAULT_MCP_DIAGNOSTIC_SERVERS,
                    ),
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
                    "external_bridge_required_servers": plan[
                        "external_bridge_required_servers"
                    ],
                    "external_bridge_ready_servers": plan[
                        "external_bridge_ready_servers"
                    ],
                    "external_bridge_adapter_missing_servers": plan[
                        "external_bridge_adapter_missing_servers"
                    ],
                    "external_bridge_unsupported_transport_servers": plan[
                        "external_bridge_unsupported_transport_servers"
                    ],
                    "unsupported_servers": plan["unsupported_servers"],
                    "bridged_servers": plan["bridged_servers"],
                    "local_bridged_servers": plan["local_bridged_servers"],
                    "external_bridged_servers": plan["external_bridged_servers"],
                    "executable_external_tools": list(
                        executable_external_mcp_tools(
                            requested_servers=DEFAULT_MCP_DIAGNOSTIC_SERVERS,
                        )
                    )
                    if bridge_available
                    else [],
                }
            )
    return matrix


def _subagent_orchestrator_available(provider: str, runtime_mode: str) -> bool:
    """Return true when the runtime can use Auto Code's child-session orchestrator."""
    if provider == "codex":
        return runtime_mode == "full_autonomous"
    return runtime_mode in {"analysis_only", "generic_edit", "patch_proposal"}


def build_runtime_subagent_matrix() -> list[dict[str, Any]]:
    """Build provider/runtime subagent support diagnostics."""
    matrix: list[dict[str, Any]] = []
    for provider_row in PROVIDER_RUNTIME_COMPATIBILITY:
        for mode in RUNTIME_MODE_INFO:
            capabilities = capabilities_for_runtime_mode(
                provider_row.provider,
                mode.mode,
            )
            support = resolve_runtime_subagent_support(
                provider_name=provider_row.provider,
                runtime_name=mode.mode,
                capabilities=capabilities,
                orchestrator_available=_subagent_orchestrator_available(
                    provider_row.provider,
                    mode.mode,
                ),
            )
            row = support.to_dict()
            row["runtime_mode"] = row.pop("runtime")
            row["max_attempts"] = DEFAULT_SUBAGENT_MAX_ATTEMPTS
            row["merge_policy"] = DEFAULT_SUBAGENT_MERGE_POLICY
            row["artifact_support"] = True
            matrix.append(row)
    return matrix


def build_runtime_policy_matrix() -> list[dict[str, Any]]:
    """Build phase/provider runtime policy diagnostics."""
    full_runtime_runner_candidates = list(
        select_cli_runner_profiles(
            runtime_mode="full_autonomous",
        ).selected_runner_ids
    )
    matrix: list[dict[str, Any]] = []
    for provider_row in PROVIDER_RUNTIME_COMPATIBILITY:
        has_full_runtime = provider_row.full_autonomous == "yes"
        for phase_policy in RUNTIME_POLICY_PHASES:
            phase = str(phase_policy["phase"])
            selected_mode = (
                "full_autonomous"
                if has_full_runtime
                else str(phase_policy["direct_provider_mode"])
            )
            requires_full_autonomous = bool(phase_policy["requires_full_autonomous"])
            requires_cli_runner = requires_full_autonomous and not has_full_runtime
            matrix.append(
                {
                    "phase": phase,
                    "provider": provider_row.provider,
                    "required_runtime_mode": "full_autonomous"
                    if requires_full_autonomous
                    else selected_mode,
                    "selected_runtime_mode": selected_mode,
                    "fallback_allowed": bool(phase_policy["fallback_allowed"])
                    and selected_mode != "blocked",
                    "fallback_modes": list(phase_policy["fallback_modes"])
                    if selected_mode != "blocked"
                    else [],
                    "requires_full_autonomous": requires_full_autonomous,
                    "requires_cli_runner": requires_cli_runner,
                    "runner_candidates": full_runtime_runner_candidates
                    if requires_cli_runner
                    else [],
                    "policy": str(phase_policy["policy"])
                    if not has_full_runtime
                    else "use_full_runtime",
                    "reason": str(phase_policy["reason"])
                    if not has_full_runtime
                    else "provider_has_full_runtime",
                }
            )
    return matrix


def build_runtime_eval_matrix() -> list[dict[str, Any]]:
    """Build runtime eval/smoke cases required before declaring full autonomy."""
    return [
        {
            "case_id": "provider_e2e",
            "runtime_mode": "provider_e2e",
            "required_for_full_autonomous": True,
            "providers": list(PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS),
            "required_artifacts": [
                "provider_e2e_suite",
                "provider_e2e_negative_fixtures",
                "provider_reliability",
            ],
        },
        {
            "case_id": "generic_edit_recovery",
            "runtime_mode": "generic_edit",
            "required_for_full_autonomous": True,
            "providers": list(PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS),
            "required_artifacts": [
                "generic_edit_recovery_checkpoint.json",
                "generic_edit_session_state.json",
                "generic_edit_transaction_groups.json",
            ],
        },
        {
            "case_id": "mcp_bridge_contract",
            "runtime_mode": "generic_edit",
            "required_for_full_autonomous": True,
            "providers": list(PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS),
            "required_artifacts": ["external_mcp_contract_checks"],
        },
        {
            "case_id": "subagent_orchestrator",
            "runtime_mode": "generic_edit",
            "required_for_full_autonomous": True,
            "providers": list(PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS),
            "required_artifacts": [
                "runtime_subagents.json",
                "runtime_subagents__<child>.json",
            ],
        },
        {
            "case_id": "cli_full_runtime",
            "runtime_mode": "full_autonomous",
            "required_for_full_autonomous": True,
            "providers": ["codex"],
            "required_artifacts": [
                "codex_cli_result.json",
                "codex_cli_timeline.json",
            ],
        },
    ]


def _runtime_eval_provider_history_status(provider_stats: dict[str, Any]) -> str:
    """Classify a provider's latest persisted e2e eval evidence."""
    if not provider_stats:
        return "not_observed"
    if (
        provider_stats.get("last_status") == "passed"
        and provider_stats.get("last_reliability_status") == "complete"
        and provider_stats.get("last_provider_e2e_status") == "passed"
    ):
        return "passed"
    return "failed"


def _runtime_eval_history_status(provider_rows: list[dict[str, Any]]) -> str:
    """Classify aggregate provider e2e history coverage."""
    statuses = {row["status"] for row in provider_rows}
    if statuses == {"passed"}:
        return "complete"
    if statuses == {"not_observed"}:
        return "not_observed"
    return "partial"


def _runtime_eval_int_stat(value: Any) -> int:
    """Return a safe integer stat from persisted history payloads."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def build_runtime_eval_history(
    *,
    project_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Build persisted runtime eval evidence from provider smoke history."""
    history_path = (project_dir or Path.cwd()) / PROVIDER_SMOKE_HISTORY_RELATIVE_PATH
    provider_stats_by_name: dict[str, Any] = {}
    history_status = "not_observed"
    if history_path.exists():
        try:
            payload = json.loads(history_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("providers"), dict):
                provider_stats_by_name = payload["providers"]
            else:
                history_status = "unreadable"
        except Exception:
            history_status = "unreadable"

    provider_rows: list[dict[str, Any]] = []
    total_runs = 0
    passed_runs = 0
    failed_runs = 0
    missing_providers: list[str] = []
    for provider in PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS:
        provider_stats = provider_stats_by_name.get(provider)
        provider_stats = provider_stats if isinstance(provider_stats, dict) else {}
        status = _runtime_eval_provider_history_status(provider_stats)
        if status == "not_observed":
            missing_providers.append(provider)
        provider_total_runs = _runtime_eval_int_stat(provider_stats.get("total_runs"))
        provider_passed_runs = _runtime_eval_int_stat(provider_stats.get("passed_runs"))
        provider_failed_runs = _runtime_eval_int_stat(provider_stats.get("failed_runs"))
        total_runs += provider_total_runs
        passed_runs += provider_passed_runs
        failed_runs += provider_failed_runs
        provider_rows.append(
            {
                "provider": provider,
                "status": status,
                "total_runs": provider_total_runs,
                "passed_runs": provider_passed_runs,
                "failed_runs": provider_failed_runs,
                "last_status": provider_stats.get("last_status"),
                "last_reliability_status": provider_stats.get(
                    "last_reliability_status",
                ),
                "last_provider_e2e_status": provider_stats.get(
                    "last_provider_e2e_status",
                ),
                "last_run_at": provider_stats.get("last_run_at"),
            }
        )

    if history_status != "unreadable":
        history_status = _runtime_eval_history_status(provider_rows)
    return [
        {
            "case_id": "provider_e2e",
            "runtime_mode": "provider_e2e",
            "history_path": PROVIDER_SMOKE_HISTORY_RELATIVE_PATH.as_posix(),
            "status": history_status,
            "total_runs": total_runs,
            "passed_runs": passed_runs,
            "failed_runs": failed_runs,
            "missing_providers": missing_providers,
            "providers": provider_rows,
        }
    ]


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
        "external_mcp_server_health": build_external_mcp_health_matrix(
            requested_servers=DEFAULT_MCP_DIAGNOSTIC_SERVERS,
        ),
        "runtime_subagent_matrix": build_runtime_subagent_matrix(),
        "runtime_policy_matrix": build_runtime_policy_matrix(),
        "runtime_eval_matrix": build_runtime_eval_matrix(),
        "runtime_eval_history": build_runtime_eval_history(),
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
            "generic_edit_resume_preflight": (
                "Use --generic-edit-resume-preflight PATH before resuming "
                "a stopped generic_edit session."
            ),
            "external_mcp_smoke": (
                "Use --external-mcp-smoke --json to run live external MCP "
                "tools/list contract checks."
            ),
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
            "external_mcp_client": (
                f"Set {EXTERNAL_MCP_CLIENT_ENV}=true only when you are ready "
                "to enable the provider-neutral external MCP client bridge."
            ),
        },
    }


def build_external_mcp_smoke_payload(
    *,
    project_dir: Path,
    sync_custom_tools: bool = False,
) -> dict[str, Any]:
    """Run opt-in external MCP tools/list contract checks."""
    project_mcp_config = load_project_mcp_config_for_runtime_commands(project_dir)
    requested_servers = registered_external_mcp_servers(
        project_mcp_config=project_mcp_config or None,
    )
    checks = asyncio.run(
        check_external_mcp_contracts(
            requested_servers=requested_servers,
            project_dir=project_dir,
            project_mcp_config=project_mcp_config or None,
        )
    )
    skipped = sum(1 for check in checks if check["status"] == "skipped")
    payload = {
        "external_mcp_contract_checks": checks,
        "summary": {
            "total": len(checks),
            "ok": sum(1 for check in checks if check["ok"]),
            "skipped": skipped,
            "failed": sum(
                1
                for check in checks
                if not check["ok"] and check["status"] != "skipped"
            ),
        },
    }
    if sync_custom_tools:
        payload["custom_mcp_tool_schema_sync"] = asyncio.run(
            sync_custom_mcp_tool_schemas(
                project_dir=project_dir,
                project_mcp_config=project_mcp_config,
            )
        )
    return payload


def load_project_mcp_config_for_runtime_commands(project_dir: Path) -> dict[str, Any]:
    """Load project MCP config for runtime diagnostics without SDK coupling."""
    try:
        from core.client import load_project_mcp_config
    except Exception as exc:
        logger.warning(
            "load_project_mcp_config_for_runtime_commands could not import "
            "load_project_mcp_config: %s",
            exc,
        )
        return {}
    try:
        config = load_project_mcp_config(project_dir)
    except Exception as exc:
        logger.warning(
            "load_project_mcp_config_for_runtime_commands could not load "
            "project MCP config with load_project_mcp_config: %s",
            exc,
        )
        return {}
    if not isinstance(config, dict):
        logger.warning(
            "load_project_mcp_config_for_runtime_commands ignored non-dict "
            "load_project_mcp_config result: %s",
            type(config).__name__,
        )
        return {}
    return config


async def sync_custom_mcp_tool_schemas(
    *,
    project_dir: Path,
    project_mcp_config: dict[str, Any],
) -> dict[str, Any]:
    """Discover and persist live tools/list schemas for custom MCP servers."""
    custom_servers = [
        dict(server)
        for server in project_mcp_config.get(CUSTOM_MCP_SERVERS_CONFIG_KEY, ())
        if isinstance(server, dict)
    ]
    updated_servers: list[str] = []
    skipped_servers: list[str] = []
    failed_servers: list[str] = []
    server_results: list[dict[str, Any]] = []

    for index, server_config in enumerate(custom_servers):
        server_id = str(server_config.get("id") or "").strip()
        if not server_id:
            continue
        health = describe_external_mcp_server_health(
            server_id,
            project_mcp_config={
                **project_mcp_config,
                CUSTOM_MCP_SERVERS_CONFIG_KEY: custom_servers,
            },
        )
        if not health.ready_to_connect or not health.execution_supported:
            skipped_servers.append(server_id)
            server_results.append(
                {
                    "server": server_id,
                    "status": "skipped",
                    "reason": health.reason,
                    "tool_count": 0,
                }
            )
            continue
        try:
            result = await discover_external_mcp_tools(
                health=health,
                project_dir=project_dir,
                project_mcp_config={
                    **project_mcp_config,
                    CUSTOM_MCP_SERVERS_CONFIG_KEY: custom_servers,
                },
            )
        except Exception as exc:
            failed_servers.append(server_id)
            server_results.append(
                {
                    "server": server_id,
                    "status": "failed",
                    "reason": str(exc),
                    "tool_count": 0,
                }
            )
            continue
        tools = normalize_mcp_tools_for_persistence(result)
        if not tools:
            skipped_servers.append(server_id)
            server_results.append(
                {
                    "server": server_id,
                    "status": "skipped",
                    "reason": "tools_list_empty",
                    "tool_count": 0,
                }
            )
            continue
        custom_servers[index] = {**server_config, "tools": tools}
        updated_servers.append(server_id)
        server_results.append(
            {
                "server": server_id,
                "status": "updated",
                "reason": "tools_synced",
                "tool_count": len(tools),
            }
        )

    if updated_servers:
        write_project_custom_mcp_servers(project_dir, custom_servers)

    return {
        "updated_servers": updated_servers,
        "skipped_servers": skipped_servers,
        "failed_servers": failed_servers,
        "server_results": server_results,
    }


def normalize_mcp_tools_for_persistence(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize live MCP tools/list output for CUSTOM_MCP_SERVERS storage."""
    raw_tools = result.get("tools", ())
    if not isinstance(raw_tools, (list, tuple)):
        return []
    tools: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for raw_tool in raw_tools:
        if not isinstance(raw_tool, dict):
            continue
        name = str(raw_tool.get("name") or "").strip()
        if not name or name in seen_names:
            continue
        seen_names.add(name)
        tool: dict[str, Any] = {"name": name}
        description = str(raw_tool.get("description") or "").strip()
        if description:
            tool["description"] = description
        schema = (
            raw_tool.get("inputSchema")
            or raw_tool.get("input_schema")
            or raw_tool.get("parameters")
        )
        if schema is not None:
            tool["inputSchema"] = normalize_mcp_input_schema(raw_tool)
        tools.append(tool)
    return tools


def write_project_custom_mcp_servers(
    project_dir: Path,
    custom_servers: list[dict[str, Any]],
) -> None:
    """Persist CUSTOM_MCP_SERVERS into the project env file."""
    env_dir = project_dir / ".auto-claude"
    env_dir.mkdir(parents=True, exist_ok=True)
    env_path = env_dir / ".env"
    value = json.dumps(custom_servers, ensure_ascii=False)
    replacement = f"{CUSTOM_MCP_SERVERS_CONFIG_KEY}={value}"

    lines = (
        env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    )
    for index, line in enumerate(lines):
        if line.startswith(f"{CUSTOM_MCP_SERVERS_CONFIG_KEY}="):
            lines[index] = replacement
            break
    else:
        lines.append(replacement)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def external_mcp_smoke_has_failures(payload: dict[str, Any]) -> bool:
    """Return whether an external MCP smoke payload has hard failures."""
    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        return False
    return int(summary.get("failed") or 0) > 0


def format_external_mcp_smoke_text(payload: dict[str, Any]) -> str:
    """Format external MCP smoke results for humans."""
    rows = [
        [
            row["server"],
            "yes" if row["ok"] else "no",
            row["status"],
            row["transport"] or "n/a",
            ", ".join(row["adapter_tools"]) or "none",
            ", ".join(row["server_tools"]) or "none",
            row["error"] or row["reason"],
        ]
        for row in payload["external_mcp_contract_checks"]
    ]
    return "\n\n".join(
        [
            "External MCP Contract Smoke",
            _format_table(
                [
                    "Server",
                    "OK",
                    "Status",
                    "Transport",
                    "Adapter tools",
                    "Server tools",
                    "Reason",
                ],
                rows,
            ),
        ]
    )


def handle_external_mcp_smoke_command(
    *,
    project_dir: Path,
    output_json: bool = False,
    sync_custom_tools: bool = False,
) -> dict[str, Any]:
    """Run opt-in external MCP tools/list contract checks."""
    payload = build_external_mcp_smoke_payload(
        project_dir=project_dir,
        sync_custom_tools=sync_custom_tools,
    )
    if output_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(format_external_mcp_smoke_text(payload))
    return payload


def generic_edit_resume_preflight_has_failures(payload: dict[str, Any]) -> bool:
    """Return true when a generic_edit resume preflight is blocked."""
    return payload.get("status") != "ready"


def _generic_edit_resume_spec_dir(checkpoint_path: Path) -> Path:
    """Infer the spec directory from a generic_edit resume artifact path."""
    artifact_dir = checkpoint_path.parent
    if artifact_dir.name == "artifacts":
        return artifact_dir.parent
    return artifact_dir


def format_generic_edit_resume_preflight_text(payload: dict[str, Any]) -> str:
    """Format generic_edit resume preflight diagnostics for humans."""
    artifacts = (
        payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    )
    artifact_rows = [
        [
            name,
            str(row.get("status", "unknown")),
            str(row.get("path", "")),
        ]
        for name, row in artifacts.items()
        if isinstance(row, dict)
    ]
    sections = [
        "Generic Edit Resume Preflight",
        f"Status: {payload.get('status', 'unknown')}",
        f"Requested path: {payload.get('requested_path', '')}",
    ]
    checkpoint_path = payload.get("checkpoint_path")
    if isinstance(checkpoint_path, str) and checkpoint_path:
        sections.append(f"Checkpoint: {checkpoint_path}")

    resume = payload.get("resume") if isinstance(payload.get("resume"), dict) else {}
    if resume:
        sections.append(f"Strategy: {resume.get('strategy', 'unknown')}")
        sections.append(f"Next iteration: {resume.get('next_iteration', 'unknown')}")
        if resume.get("active_batch_id"):
            sections.append(f"Active batch: {resume['active_batch_id']}")

    if artifact_rows:
        sections.extend(
            [
                "",
                _format_table(["Artifact", "Status", "Path"], artifact_rows),
            ]
        )

    blocker = payload.get("resume_artifact_health")
    if isinstance(blocker, dict):
        sections.extend(
            [
                "",
                "Blocker:",
                f"  artifact: {blocker.get('artifact', 'unknown')}",
                f"  reason: {blocker.get('reason', 'unknown')}",
            ]
        )
        for key in (
            "artifact_name",
            "path",
            "owner_artifact",
            "owner_path",
            "expected_path",
            "actual_path",
        ):
            value = blocker.get(key)
            if isinstance(value, str) and value:
                sections.append(f"  {key}: {value}")
        for key in ("line_number", "expected_count", "actual_count"):
            value = blocker.get(key)
            if isinstance(value, int):
                sections.append(f"  {key}: {value}")
        for key in (
            "missing_snapshot_ids",
            "drift_paths",
            "expected_snapshot_ids",
            "actual_snapshot_ids",
        ):
            value = blocker.get(key)
            if isinstance(value, list) and value:
                items = [str(item) for item in value[:10]]
                sections.append(f"  {key}: {', '.join(items)}")
        message = blocker.get("message")
        if isinstance(message, str) and message:
            sections.append(f"  message: {message}")

    workspace_guard = payload.get("workspace_guard")
    if isinstance(workspace_guard, dict):
        sections.extend(
            [
                "",
                "Workspace guard:",
                f"  status: {workspace_guard.get('status', 'unknown')}",
                f"  drift_count: {workspace_guard.get('drift_count', 0)}",
                "  unverified_path_count: "
                f"{workspace_guard.get('unverified_path_count', 0)}",
            ]
        )

    return "\n".join(sections)


def handle_generic_edit_resume_preflight_command(
    *,
    checkpoint_path: Path,
    project_dir: Path,
    output_json: bool = False,
) -> dict[str, Any]:
    """Run a read-only generic_edit resume artifact preflight."""
    payload = inspect_generic_edit_resume_artifacts(
        checkpoint_path=checkpoint_path,
        spec_dir=_generic_edit_resume_spec_dir(checkpoint_path),
        project_dir=project_dir,
    )
    if output_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(format_generic_edit_resume_preflight_text(payload))
    return payload


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
            ", ".join(row["external_bridged_servers"]) or "none",
            ", ".join(row["external_bridge_required_servers"]) or "none",
        ]
        for row in build_mcp_bridge_plan_matrix()
        if row["runtime_mode"] in {"full_autonomous", "generic_edit"}
    ]
    external_mcp_health_rows = [
        [
            row["server"],
            row["status"],
            "yes" if row["configured"] else "no",
            row["transport"] or "n/a",
            ", ".join(row["missing_env"]) or "none",
            ", ".join(row["executable_tools"]) or "none",
        ]
        for row in build_external_mcp_health_matrix(
            requested_servers=DEFAULT_MCP_DIAGNOSTIC_SERVERS,
        )
        if row["bridgeable"]
    ]
    subagent_rows = [
        [
            row["provider"],
            row["runtime_mode"],
            row["strategy"],
            "yes" if row["available"] else "no",
            ", ".join(row["missing_capabilities"]) or "none",
            row["merge_policy"],
            str(row["max_attempts"]),
        ]
        for row in build_runtime_subagent_matrix()
        if row["runtime_mode"] in {"full_autonomous", "generic_edit"}
    ]
    runtime_policy_rows = [
        [
            row["phase"],
            row["provider"],
            row["required_runtime_mode"],
            row["selected_runtime_mode"],
            "yes" if row["fallback_allowed"] else "no",
            row["policy"],
            row["reason"],
            ", ".join(row["runner_candidates"]) or "none",
        ]
        for row in build_runtime_policy_matrix()
        if row["provider"] in {"claude", "codex", "openai", "google", "ollama"}
    ]
    runtime_eval_rows = [
        [
            row["case_id"],
            row["runtime_mode"],
            "yes" if row["required_for_full_autonomous"] else "no",
            ", ".join(row["providers"]),
            ", ".join(row["required_artifacts"]),
        ]
        for row in build_runtime_eval_matrix()
    ]
    runtime_eval_history_rows = [
        [
            row["case_id"],
            row["status"],
            str(row["total_runs"]),
            str(row["passed_runs"]),
            str(row["failed_runs"]),
            ", ".join(row["missing_providers"]) or "none",
            row["history_path"],
        ]
        for row in build_runtime_eval_history()
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
                    "External bridged",
                    "External required",
                ],
                mcp_bridge_rows,
            ),
            "External MCP Client Health",
            _format_table(
                [
                    "Server",
                    "Status",
                    "Configured",
                    "Transport",
                    "Missing config",
                    "Executable tools",
                ],
                external_mcp_health_rows,
            ),
            "Subagent Orchestrator Matrix",
            _format_table(
                [
                    "Provider",
                    "Runtime",
                    "Strategy",
                    "Available",
                    "Missing capabilities",
                    "Merge policy",
                    "Max attempts",
                ],
                subagent_rows,
            ),
            "Runtime Policy Matrix",
            _format_table(
                [
                    "Phase",
                    "Provider",
                    "Required",
                    "Selected",
                    "Fallback",
                    "Policy",
                    "Reason",
                    "Runner candidates",
                ],
                runtime_policy_rows,
            ),
            "Runtime Eval Matrix",
            _format_table(
                [
                    "Case",
                    "Runtime",
                    "Full required",
                    "Providers",
                    "Required artifacts",
                ],
                runtime_eval_rows,
            ),
            "Runtime Eval History",
            _format_table(
                [
                    "Case",
                    "Status",
                    "Runs",
                    "Passed",
                    "Failed",
                    "Missing providers",
                    "Artifact",
                ],
                runtime_eval_history_rows,
            ),
            "Recommended commands",
            "  Full autonomous: python run.py --spec 001 --provider claude",
            "  Generic edit:    AGENT_PROVIDER_CODER=openai AGENT_RUNTIME_MODE_CODER=generic_edit python run.py --spec 001",
            "  Analysis:        python run.py --spec 001 --provider openai --analyze",
            "  Patch proposal:  python run.py --spec 001 --provider openai --runtime-mode patch_proposal",
            "  Runtime fallback: AUTO_CODE_RUNTIME_FALLBACK=true python run.py --spec 001 --provider openai",
            "  Runner router:   AUTO_CODE_CLI_RUNNER_ROUTER=true python run.py --spec 001 --provider openai",
            "  Provider smoke:  python run.py --provider openai --provider-smoke",
            "  Resume preflight: python run.py --generic-edit-resume-preflight "
            ".auto-Codex/specs/001/artifacts/generic_edit_recovery_checkpoint.json",
            "  External MCP:    python run.py --external-mcp-smoke --json",
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
