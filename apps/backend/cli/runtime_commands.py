"""CLI helpers for runtime/provider compatibility."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
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
    MCP_ALLOWED_PERMISSIONS_ENV,
    MCP_SERVER_CATALOG,
    build_external_mcp_health_matrix,
    check_external_mcp_contracts,
    describe_external_mcp_server_health,
    discover_external_mcp_tools,
    executable_external_mcp_servers,
    executable_external_mcp_tools,
    external_mcp_adapter_for,
    mcp_server_catalog_entry,
    normalize_mcp_allowed_permissions,
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
    PROVIDER_AUTONOMOUS_READINESS_MIN_STABLE_RUNS,
    PROVIDER_AUTONOMOUS_READINESS_RECOMMENDATION_REASON_BY_SIGNAL,
    PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES,
    PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS,
    PROVIDER_SMOKE_HISTORY_RELATIVE_PATH,
)

DEFAULT_MCP_DIAGNOSTIC_SERVERS = tuple(MCP_SERVER_CATALOG)
DEFAULT_EXTERNAL_MCP_SMOKE_SERVERS = registered_external_mcp_servers()
logger = logging.getLogger(__name__)
CLI_RUNNER_CONTRACT_FACETS = (
    "run",
    "cancel",
    "resume",
    "artifacts",
    "event_parser",
    "cost_account",
)
CLI_RUNNER_WIRED_CONTRACTS = {
    "codex_cli": {
        "run": "wired",
        "cancel": "wired",
        "resume": "wired",
        "artifacts": "wired",
        "event_parser": "wired",
        "cost_account": "wired",
    },
}
CLI_RUNNER_CONTRACT_READY_STATUSES = {
    "wired",
    "generic_core_configurable",
    "generic_jsonl_core",
}
CLI_RUNNER_GENERIC_CORE_FACETS = {
    "run": "generic_core_configurable",
    "cancel": "generic_core_configurable",
    "resume": "missing_runner_resume",
    "artifacts": "generic_core_configurable",
    "event_parser": "generic_jsonl_core",
    "cost_account": "generic_jsonl_core",
}
MUTATING_SUBAGENT_REQUIRED_GATES = (
    "isolated_child_contexts",
    "transaction_boundaries",
    "conflict_aware_merge",
    "parent_approved_apply_abort",
    "child_artifacts",
)
MUTATING_SUBAGENT_SATISFIED_GATES = (
    "isolated_child_contexts",
    "child_artifacts",
)
MCP_PERMISSION_REQUIRED_GATES = (
    "tool_policy_metadata",
    "permission_allowlist_check",
    "deny_before_execution",
    "audit_artifact",
    "mutating_tool_classification",
)

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


def build_cli_runner_contract_matrix() -> list[dict[str, Any]]:
    """Build the shared full-runtime CLI runner contract matrix."""
    matrix: list[dict[str, Any]] = []
    for profile in CLI_RUNNER_PROFILES:
        wired_facets = CLI_RUNNER_WIRED_CONTRACTS.get(
            profile.runner_id,
            CLI_RUNNER_GENERIC_CORE_FACETS,
        )
        facets = {
            facet: wired_facets.get(facet, "missing_adapter")
            for facet in CLI_RUNNER_CONTRACT_FACETS
        }
        missing_facets = [
            facet
            for facet, status in facets.items()
            if status not in CLI_RUNNER_CONTRACT_READY_STATUSES
        ]
        if not missing_facets:
            contract_status = "ready"
        elif any(
            status in CLI_RUNNER_CONTRACT_READY_STATUSES for status in facets.values()
        ):
            contract_status = "partial"
        else:
            contract_status = "planned"
        matrix.append(
            {
                "runner_id": profile.runner_id,
                "display_name": profile.display_name,
                "runner_status": profile.runner_status,
                "contract_status": contract_status,
                "required_facets": list(CLI_RUNNER_CONTRACT_FACETS),
                "missing_contract_facets": missing_facets,
                "facets": facets,
                "adapter_required": bool(missing_facets),
                "supported_runtime_modes": list(profile.supported_runtime_modes),
                "artifact_contract": (
                    f"{profile.runner_id}_result.json, "
                    f"{profile.runner_id}_timeline.json"
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


def _unique_sorted(values: list[str]) -> list[str]:
    """Return deterministic unique values for diagnostic payloads."""
    return sorted({value for value in values if value})


def _mcp_allowlist_fields() -> dict[str, Any]:
    """Return the effective MCP permission allowlist diagnostic fields."""
    allowed_permissions = normalize_mcp_allowed_permissions(None)
    fields: dict[str, Any] = {
        "strict_allowlist_configured": allowed_permissions is not None,
        "allowlist_source": (
            MCP_ALLOWED_PERMISSIONS_ENV
            if allowed_permissions is not None
            else "allow_all_default"
        ),
    }
    if allowed_permissions is not None:
        fields["allowed_permissions"] = sorted(allowed_permissions)
    return fields


def build_mcp_bridge_permission_matrix(
    *,
    project_mcp_config: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build server-level MCP bridge permission/audit enforcement diagnostics."""
    allowlist_fields = _mcp_allowlist_fields()
    required_gates = list(MCP_PERMISSION_REQUIRED_GATES)
    audit_artifact = ".auto-Codex/specs/<spec>/artifacts/mcp_bridge_audit.jsonl"
    matrix: list[dict[str, Any]] = [
        {
            "server": LOCAL_BRIDGE_SERVER,
            "display_name": str(
                MCP_SERVER_CATALOG[LOCAL_BRIDGE_SERVER]["display_name"]
            ),
            "bridge_path": "local_bridge",
            "status": "enforced",
            "permission_enforced": True,
            **allowlist_fields,
            "audit_required": True,
            "audit_artifact": audit_artifact,
            "tool_count": None,
            "tool_policy_coverage": "dynamic",
            "permissions": ["dynamic_auto_claude_tool_policy"],
            "mutating_permissions": ["dynamic_mutating_tool_policy"],
            "required_gates": required_gates,
            "satisfied_gates": required_gates,
            "missing_gates": [],
            "reason": "local_tools_receive_runtime_policy_before_execution",
        }
    ]

    for server in registered_external_mcp_servers(
        project_mcp_config=project_mcp_config,
    ):
        adapter = external_mcp_adapter_for(
            server,
            project_mcp_config=project_mcp_config,
        )
        catalog_entry = mcp_server_catalog_entry(
            server,
            project_mcp_config=project_mcp_config,
        )
        if adapter is None or not adapter.tool_definitions:
            matrix.append(
                {
                    "server": server,
                    "display_name": str(catalog_entry.get("display_name", server)),
                    "bridge_path": "external_bridge",
                    "status": "missing_policy",
                    "permission_enforced": False,
                    **allowlist_fields,
                    "audit_required": False,
                    "audit_artifact": audit_artifact,
                    "tool_count": 0,
                    "tool_policy_coverage": "missing",
                    "permissions": [],
                    "mutating_permissions": [],
                    "required_gates": required_gates,
                    "satisfied_gates": [],
                    "missing_gates": required_gates,
                    "reason": "external_adapter_has_no_tool_policy_metadata",
                }
            )
            continue

        tool_definitions = adapter.tool_definitions
        missing_gates: list[str] = []
        if not all(definition.policy.audit_required for definition in tool_definitions):
            missing_gates.append("audit_artifact")
        satisfied_gates = [gate for gate in required_gates if gate not in missing_gates]
        matrix.append(
            {
                "server": server,
                "display_name": str(catalog_entry.get("display_name", server)),
                "bridge_path": "external_bridge",
                "status": "enforced" if not missing_gates else "partial",
                "permission_enforced": True,
                **allowlist_fields,
                "audit_required": not missing_gates,
                "audit_artifact": audit_artifact,
                "tool_count": len(tool_definitions),
                "tool_policy_coverage": "static",
                "permissions": _unique_sorted(
                    [definition.policy.permission for definition in tool_definitions]
                ),
                "mutating_permissions": _unique_sorted(
                    [
                        definition.policy.permission
                        for definition in tool_definitions
                        if definition.policy.mutating
                    ]
                ),
                "required_gates": required_gates,
                "satisfied_gates": satisfied_gates,
                "missing_gates": missing_gates,
                "reason": "external_tools_receive_runtime_policy_before_execution",
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


def build_runtime_subagent_mutation_policy() -> list[dict[str, Any]]:
    """Build explicit policy gates for future mutating subagent support."""
    missing_gates = [
        gate
        for gate in MUTATING_SUBAGENT_REQUIRED_GATES
        if gate not in MUTATING_SUBAGENT_SATISFIED_GATES
    ]
    matrix: list[dict[str, Any]] = []
    for provider_row in PROVIDER_RUNTIME_COMPATIBILITY:
        for mode in RUNTIME_MODE_INFO:
            if mode.mode not in {"full_autonomous", "generic_edit"}:
                continue
            matrix.append(
                {
                    "provider": provider_row.provider,
                    "runtime_mode": mode.mode,
                    "mutating_subagents_enabled": False,
                    "status": "blocked",
                    "transaction_boundary_required": True,
                    "parent_approval_required": True,
                    "merge_protocol": "read_only_until_transactional_merge",
                    "required_gates": list(MUTATING_SUBAGENT_REQUIRED_GATES),
                    "satisfied_gates": list(MUTATING_SUBAGENT_SATISFIED_GATES),
                    "missing_gates": missing_gates,
                    "reason": "mutating_subagents_require_transactional_merge",
                }
            )
    return matrix


def build_runtime_policy_matrix(
    *,
    project_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Build phase/provider runtime policy diagnostics."""
    full_runtime_runner_candidates = list(
        select_cli_runner_profiles(
            runtime_mode="full_autonomous",
        ).selected_runner_ids
    )
    readiness_by_provider = _runtime_provider_autonomous_readiness_by_name(
        project_dir=project_dir,
    )
    matrix: list[dict[str, Any]] = []
    for provider_row in PROVIDER_RUNTIME_COMPATIBILITY:
        has_full_runtime = provider_row.full_autonomous == "yes"
        readiness = readiness_by_provider.get(provider_row.provider)
        readiness_required = readiness is not None
        for phase_policy in RUNTIME_POLICY_PHASES:
            phase = str(phase_policy["phase"])
            selected_mode = (
                "full_autonomous"
                if has_full_runtime
                else str(phase_policy["direct_provider_mode"])
            )
            requires_full_autonomous = bool(phase_policy["requires_full_autonomous"])
            requires_cli_runner = requires_full_autonomous and not has_full_runtime
            policy = (
                str(phase_policy["policy"])
                if not has_full_runtime
                else "use_full_runtime"
            )
            reason = (
                str(phase_policy["reason"])
                if not has_full_runtime
                else "provider_has_full_runtime"
            )
            if (
                readiness_required
                and readiness["policy_gate"] != "passed"
                and phase in {"coder", "qa_fixer"}
            ):
                policy = str(readiness["recommendation"])
                reason = str(readiness["status"])
            readiness_fields = (
                {
                    "autonomous_readiness_required": True,
                    "autonomous_policy_gate": readiness["policy_gate"],
                    "autonomous_readiness_status": readiness["status"],
                    "autonomous_readiness_recommendation": readiness["recommendation"],
                    "autonomous_readiness_recommendation_reasons": readiness[
                        "recommendation_reasons"
                    ],
                    "autonomous_readiness_blockers": readiness["blockers"],
                    "autonomous_readiness_warnings": readiness["warnings"],
                    "autonomous_readiness_requirements": readiness["requirements"],
                    "autonomous_readiness_missing_requirements": readiness[
                        "missing_requirements"
                    ],
                }
                if readiness_required and readiness is not None
                else {
                    "autonomous_readiness_required": False,
                    "autonomous_policy_gate": "not_required",
                    "autonomous_readiness_status": "not_required",
                    "autonomous_readiness_recommendation": "not_required",
                    "autonomous_readiness_recommendation_reasons": [],
                    "autonomous_readiness_blockers": [],
                    "autonomous_readiness_warnings": [],
                    "autonomous_readiness_requirements": {},
                    "autonomous_readiness_missing_requirements": [],
                }
            )
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
                    "policy": policy,
                    "reason": reason,
                    **readiness_fields,
                }
            )
    return matrix


def _extend_unique(target: list[str], values: list[str]) -> None:
    """Append non-empty unique values to a diagnostic list."""
    for value in values:
        if value and value not in target:
            target.append(value)


def build_runtime_capability_matrix(
    *,
    project_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Build consolidated provider readiness diagnostics for the control plane."""
    full_runtime_runner_candidates = list(
        select_cli_runner_profiles(
            runtime_mode="full_autonomous",
        ).selected_runner_ids
    )
    readiness_by_provider = _runtime_provider_autonomous_readiness_by_name(
        project_dir=project_dir,
    )
    gateway_providers = {"litellm", "openrouter"}
    matrix: list[dict[str, Any]] = []
    for provider_row in PROVIDER_RUNTIME_COMPATIBILITY:
        has_full_runtime = provider_row.full_autonomous == "yes"
        readiness = readiness_by_provider.get(provider_row.provider)
        blockers: list[str] = []
        warnings: list[str] = []
        if not has_full_runtime and (
            readiness is None or readiness["policy_gate"] != "passed"
        ):
            blockers.extend(
                [
                    "missing_full_autonomous_runtime",
                    "live_provider_e2e_required",
                    "transactional_recovery_required",
                ]
            )
            warnings.append("direct_full_autonomous_blocked")
        if provider_row.provider in gateway_providers:
            warnings.append("gateway_model_limitations")
        if provider_row.provider == "ollama":
            warnings.append("local_model_quality_varies")
        if readiness is not None:
            _extend_unique(blockers, readiness["blockers"])
            _extend_unique(warnings, readiness["warnings"])

        matrix.append(
            {
                "provider": provider_row.provider,
                "readiness": "ready"
                if has_full_runtime
                else str(readiness["status"] if readiness is not None else "limited"),
                "full_autonomous_ready": has_full_runtime
                or (
                    readiness is not None
                    and readiness["status"] == "full_autonomous_candidate"
                ),
                "direct_full_autonomous": provider_row.full_autonomous,
                "recommended_runtime_mode": (
                    "full_autonomous" if has_full_runtime else "generic_edit"
                ),
                "generic_edit": provider_row.generic_edit,
                "analysis_only": provider_row.analysis_only,
                "patch_proposal": provider_row.patch_proposal,
                "mcp_tools": provider_row.mcp_tools,
                "subagents": provider_row.subagents,
                "cli_runner_candidates": []
                if has_full_runtime
                else full_runtime_runner_candidates,
                "autonomous_readiness_required": readiness is not None,
                "autonomous_policy_gate": readiness["policy_gate"]
                if readiness is not None
                else "not_required",
                "autonomous_readiness_status": readiness["status"]
                if readiness is not None
                else "not_required",
                "autonomous_readiness_recommendation": readiness["recommendation"]
                if readiness is not None
                else "not_required",
                "autonomous_readiness_recommendation_reasons": readiness[
                    "recommendation_reasons"
                ]
                if readiness is not None
                else [],
                "autonomous_readiness_blockers": readiness["blockers"]
                if readiness is not None
                else [],
                "autonomous_readiness_warnings": readiness["warnings"]
                if readiness is not None
                else [],
                "autonomous_readiness_evidence": readiness["evidence"]
                if readiness is not None
                else [],
                "autonomous_readiness_requirements": readiness["requirements"]
                if readiness is not None
                else {},
                "autonomous_readiness_missing_requirements": readiness[
                    "missing_requirements"
                ]
                if readiness is not None
                else [],
                "autonomous_readiness_next_actions": readiness["next_actions"]
                if readiness is not None
                else [],
                "blockers": blockers,
                "warnings": warnings,
                "notes": provider_row.notes,
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


def _runtime_provider_history_stats_by_name(
    *,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Return persisted provider smoke history stats keyed by provider."""
    history_path = (project_dir or Path.cwd()) / PROVIDER_SMOKE_HISTORY_RELATIVE_PATH
    if not history_path.exists():
        return {}
    try:
        payload = json.loads(history_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict) or not isinstance(payload.get("providers"), dict):
        return {}
    return payload["providers"]


def _runtime_provider_readiness_next_actions(
    blockers: list[str],
    warnings: list[str],
) -> list[str]:
    """Return ordered next actions for provider autonomous-readiness gates."""
    action_by_reason = {
        "provider_e2e_failed": "rerun_provider_e2e",
        "provider_reliability_incomplete": "inspect_uncovered_cases",
        "provider_history_latest_failed": "rerun_provider_e2e",
        "provider_history_unknown": "collect_provider_history_runs",
        "provider_history_warming_up": "collect_provider_history_runs",
        "provider_history_flaky": "stabilize_provider_history",
        "provider_history_recovering": "collect_provider_history_runs",
        "provider_history_degraded": "stabilize_provider_history",
        "provider_history_insufficient_runs": "collect_provider_history_runs",
        "live_fault_probe_evidence_missing": "enable_live_fault_probes",
        "live_fault_probe_coverage_incomplete": "enable_live_fault_probes",
    }
    actions: list[str] = []
    for reason in [*blockers, *warnings]:
        action = action_by_reason.get(reason)
        if action and action not in actions:
            actions.append(action)
    return actions


def _runtime_provider_autonomous_readiness_from_history(
    provider: str,
    provider_stats: dict[str, Any],
) -> dict[str, Any]:
    """Classify direct-provider autonomous readiness from persisted e2e history."""
    blockers: list[str] = []
    warnings: list[str] = []
    evidence: list[str] = []

    if (
        provider_stats.get("last_status") == "passed"
        and provider_stats.get("last_provider_e2e_status") == "passed"
    ):
        evidence.append("provider_e2e_passed")
    else:
        blockers.append("provider_e2e_failed")

    if provider_stats.get("last_reliability_status") == "complete":
        evidence.append("provider_reliability_complete")
    else:
        blockers.append("provider_reliability_incomplete")

    if provider_stats.get("last_status") != "passed":
        blockers.append("provider_history_latest_failed")

    trend = provider_stats.get("trend")
    if trend == "provider_history_stable":
        if _runtime_provider_readiness_history_is_stable_enough(provider_stats):
            evidence.append("provider_history_stable")
        else:
            warnings.append("provider_history_insufficient_runs")
    elif isinstance(trend, str) and trend:
        warnings.append(trend)
    else:
        warnings.append("provider_history_unknown")

    if provider_stats.get("last_live_fault_probe_status") == "passed":
        evidence.append("live_fault_probes_passed")
        if not _runtime_provider_live_fault_coverage_complete(provider_stats):
            warnings.append("live_fault_probe_coverage_incomplete")
    else:
        warnings.append("live_fault_probe_evidence_missing")

    if blockers:
        status = "blocked"
        recommendation = "provider_e2e_required"
    elif (
        "live_fault_probe_evidence_missing" in warnings
        or "live_fault_probe_coverage_incomplete" in warnings
    ):
        status = "needs_live_fault_evidence"
        recommendation = "limited_autonomous_until_live_faults"
    elif warnings:
        status = "warming_up"
        recommendation = "limited_autonomous_until_evidence_stable"
    else:
        status = "full_autonomous_candidate"
        recommendation = "api_runtime_full_autonomous_candidate"

    requirements = _runtime_provider_readiness_requirements(provider_stats)
    return {
        "provider": provider,
        "status": status,
        "recommendation": recommendation,
        "recommendation_reasons": _runtime_provider_readiness_recommendation_reasons(
            status,
            blockers,
            warnings,
        ),
        "policy_gate": "passed" if status == "full_autonomous_candidate" else "blocked",
        "blockers": blockers,
        "warnings": warnings,
        "evidence": evidence,
        "requirements": requirements,
        "missing_requirements": _runtime_provider_missing_requirements(
            blockers,
            requirements,
        ),
        "next_actions": _runtime_provider_readiness_next_actions(blockers, warnings),
    }


def _runtime_provider_readiness_history_is_stable_enough(
    provider_stats: dict[str, Any],
) -> bool:
    """Return whether persisted provider history has enough stable runs."""
    return (
        _runtime_provider_readiness_recent_window(provider_stats)
        >= PROVIDER_AUTONOMOUS_READINESS_MIN_STABLE_RUNS
        and _runtime_provider_readiness_consecutive_passes(provider_stats)
        >= PROVIDER_AUTONOMOUS_READINESS_MIN_STABLE_RUNS
    )


def _runtime_provider_readiness_recent_window(provider_stats: dict[str, Any]) -> int:
    """Return observed recent-window count from provider history."""
    recent_window = _runtime_eval_int_stat(provider_stats.get("recent_window"))
    if recent_window == 0:
        recent_window = _runtime_eval_int_stat(provider_stats.get("total_runs"))
    return recent_window


def _runtime_provider_readiness_consecutive_passes(
    provider_stats: dict[str, Any],
) -> int:
    """Return observed consecutive-pass count from provider history."""
    consecutive_passes = _runtime_eval_int_stat(
        provider_stats.get("consecutive_passes")
    )
    if consecutive_passes == 0:
        consecutive_passes = _runtime_eval_int_stat(provider_stats.get("passed_runs"))
    return consecutive_passes


def _runtime_string_list_payload(value: Any) -> list[str]:
    """Return a safe string list from a persisted diagnostics payload."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value[:20] if isinstance(item, str) and item]


def _runtime_provider_live_fault_coverage_complete(
    provider_stats: dict[str, Any],
) -> bool:
    """Return whether live fault history covered every required fault case."""
    covered_cases = set(
        _runtime_string_list_payload(
            provider_stats.get("live_fault_probe_covered_cases")
        )
    )
    return all(
        required_case in covered_cases
        for required_case in PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES
    )


def _runtime_provider_readiness_requirements(
    provider_stats: dict[str, Any],
) -> dict[str, Any]:
    """Return structured readiness requirement evidence for runtime diagnostics."""
    required_live_fault_cases = sorted(
        PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES
    )
    live_fault_covered_cases = sorted(
        _runtime_string_list_payload(
            provider_stats.get("live_fault_probe_covered_cases")
        )
    )
    live_fault_missing_cases = [
        required_case
        for required_case in required_live_fault_cases
        if required_case not in live_fault_covered_cases
    ]
    live_fault_coverage_complete = (
        provider_stats.get("last_live_fault_probe_status") == "passed"
        and not live_fault_missing_cases
    )
    return {
        "min_stable_runs": PROVIDER_AUTONOMOUS_READINESS_MIN_STABLE_RUNS,
        "observed_recent_window": _runtime_provider_readiness_recent_window(
            provider_stats
        ),
        "observed_consecutive_passes": _runtime_provider_readiness_consecutive_passes(
            provider_stats
        ),
        "history_stability_complete": _runtime_provider_readiness_history_is_stable_enough(
            provider_stats
        ),
        "required_live_fault_cases": required_live_fault_cases,
        "live_fault_covered_cases": live_fault_covered_cases,
        "live_fault_missing_cases": live_fault_missing_cases,
        "live_fault_coverage_complete": live_fault_coverage_complete,
    }


def _runtime_provider_missing_requirements(
    blockers: list[str],
    requirements: dict[str, Any],
) -> list[str]:
    """Return stable missing requirement ids for runtime automation."""
    missing: list[str] = []
    if "provider_e2e_failed" in blockers:
        missing.append("provider_e2e")
    if "provider_reliability_incomplete" in blockers:
        missing.append("provider_reliability")
    if "provider_history_latest_failed" in blockers:
        missing.append("latest_provider_e2e_pass")
    if requirements.get("history_stability_complete") is not True:
        missing.append("stable_history_runs")
    if requirements.get("live_fault_coverage_complete") is not True:
        missing.append("live_fault_case_coverage")
    return missing


def _runtime_provider_readiness_recommendation_reasons(
    status: str,
    blockers: list[str],
    warnings: list[str],
) -> list[str]:
    """Return stable reason ids behind a provider readiness recommendation."""
    if status == "full_autonomous_candidate":
        return ["full_autonomy_candidate"]

    reasons: list[str] = []
    for signal in [*blockers, *warnings]:
        reason = PROVIDER_AUTONOMOUS_READINESS_RECOMMENDATION_REASON_BY_SIGNAL.get(
            signal
        )
        if reason and reason not in reasons:
            reasons.append(reason)
    return reasons


def _runtime_provider_autonomous_readiness_by_name(
    *,
    project_dir: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Return direct-provider autonomous-readiness gates keyed by provider."""
    provider_stats_by_name = _runtime_provider_history_stats_by_name(
        project_dir=project_dir,
    )
    return {
        provider: _runtime_provider_autonomous_readiness_from_history(
            provider,
            provider_stats_by_name.get(provider)
            if isinstance(provider_stats_by_name.get(provider), dict)
            else {},
        )
        for provider in PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS
    }


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


def build_runtime_comparative_eval_matrix(
    *,
    project_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Build provider comparison rows for quality/cost/safety eval evidence."""
    eval_history = build_runtime_eval_history(project_dir=project_dir)
    provider_history = (
        {
            row["provider"]: row
            for row in eval_history[0].get("providers", [])
            if isinstance(row, dict)
        }
        if eval_history
        else {}
    )
    history_path = (
        eval_history[0].get("history_path")
        if eval_history
        else PROVIDER_SMOKE_HISTORY_RELATIVE_PATH.as_posix()
    )
    compatibility = {row.provider: row for row in PROVIDER_RUNTIME_COMPATIBILITY}
    comparison_providers = ("claude", "codex", "openai", "google", "ollama")
    matrix: list[dict[str, Any]] = []
    for provider in comparison_providers:
        provider_row = compatibility[provider]
        has_full_runtime = provider_row.full_autonomous == "yes"
        provider_stats = provider_history.get(provider, {})
        quality_status = (
            "not_recorded"
            if has_full_runtime
            else str(provider_stats.get("status") or "not_observed")
        )
        matrix.append(
            {
                "provider": provider,
                "runtime_path": "full_autonomous"
                if has_full_runtime
                else "generic_edit",
                "quality_status": quality_status,
                "cost_status": "not_recorded",
                "safety_status": "native_runtime_policy"
                if has_full_runtime
                else "policy_gated",
                "evidence_source": "native_runtime"
                if has_full_runtime
                else str(history_path),
                "required_before_full_autonomous": not has_full_runtime,
                "blockers": []
                if has_full_runtime
                else [
                    "provider_e2e",
                    "generic_edit_recovery",
                    "mcp_bridge_contract",
                ],
            }
        )
    return matrix


def build_runtime_modes_payload(
    *,
    project_dir: Path | None = None,
) -> dict[str, Any]:
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
        "cli_runner_contract_matrix": build_cli_runner_contract_matrix(),
        "runtime_fallback_matrix": build_runtime_fallback_matrix(),
        "mcp_bridge_plan_matrix": build_mcp_bridge_plan_matrix(),
        "mcp_bridge_permission_matrix": build_mcp_bridge_permission_matrix(),
        "external_mcp_server_health": build_external_mcp_health_matrix(
            requested_servers=DEFAULT_MCP_DIAGNOSTIC_SERVERS,
        ),
        "runtime_subagent_matrix": build_runtime_subagent_matrix(),
        "runtime_subagent_mutation_policy": build_runtime_subagent_mutation_policy(),
        "runtime_policy_matrix": build_runtime_policy_matrix(project_dir=project_dir),
        "runtime_capability_matrix": build_runtime_capability_matrix(
            project_dir=project_dir,
        ),
        "runtime_eval_matrix": build_runtime_eval_matrix(),
        "runtime_eval_history": build_runtime_eval_history(project_dir=project_dir),
        "runtime_comparative_eval_matrix": build_runtime_comparative_eval_matrix(
            project_dir=project_dir,
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
            "provider_autonomous_readiness": (
                "Run --provider-smoke --provider-smoke-runtime provider_e2e "
                "until provider_autonomous_readiness.status is "
                "full_autonomous_candidate before treating a direct API "
                "provider as autonomous."
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


def format_runtime_modes_text(payload: dict[str, Any] | None = None) -> str:
    """Format runtime compatibility guidance for humans."""
    payload = payload or build_runtime_modes_payload()
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
    cli_runner_contract_rows = [
        [
            row["runner_id"],
            row["runner_status"],
            row["contract_status"],
            ", ".join(row["missing_contract_facets"]) or "none",
            row["artifact_contract"],
        ]
        for row in build_cli_runner_contract_matrix()
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
    mcp_permission_rows = [
        [
            row["server"],
            row["bridge_path"],
            row["status"],
            "yes" if row["strict_allowlist_configured"] else "no",
            ", ".join(row["permissions"]) or "none",
            ", ".join(row["mutating_permissions"]) or "none",
            ", ".join(row["missing_gates"]) or "none",
        ]
        for row in build_mcp_bridge_permission_matrix()
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
    mutating_subagent_rows = [
        [
            row["provider"],
            row["runtime_mode"],
            row["status"],
            "yes" if row["mutating_subagents_enabled"] else "no",
            ", ".join(row["missing_gates"]) or "none",
            row["merge_protocol"],
        ]
        for row in build_runtime_subagent_mutation_policy()
        if row["provider"] in {"claude", "codex", "openai", "google", "ollama"}
    ]
    runtime_policy_rows = [
        [
            row["phase"],
            row["provider"],
            row["required_runtime_mode"],
            row["selected_runtime_mode"],
            "yes" if row["fallback_allowed"] else "no",
            row["policy"],
            row["autonomous_policy_gate"],
            row["autonomous_readiness_recommendation"],
            ", ".join(row["autonomous_readiness_recommendation_reasons"]) or "none",
            row["reason"],
            ", ".join(row["runner_candidates"]) or "none",
        ]
        for row in payload["runtime_policy_matrix"]
        if row["provider"] in {"claude", "codex", "openai", "google", "ollama"}
    ]
    runtime_capability_rows = [
        [
            row["provider"],
            row["readiness"],
            row["recommended_runtime_mode"],
            row["autonomous_policy_gate"],
            row["autonomous_readiness_recommendation"],
            ", ".join(row["autonomous_readiness_recommendation_reasons"]) or "none",
            ", ".join(row["blockers"]) or "none",
            ", ".join(row["warnings"]) or "none",
            ", ".join(row["cli_runner_candidates"]) or "none",
        ]
        for row in payload["runtime_capability_matrix"]
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
        for row in payload["runtime_eval_history"]
    ]
    runtime_comparative_eval_rows = [
        [
            row["provider"],
            row["runtime_path"],
            row["quality_status"],
            row["cost_status"],
            row["safety_status"],
            ", ".join(row["blockers"]) or "none",
            row["evidence_source"],
        ]
        for row in payload["runtime_comparative_eval_matrix"]
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
            "CLI Runner Contract Matrix",
            _format_table(
                [
                    "Runner",
                    "Runner status",
                    "Contract status",
                    "Missing facets",
                    "Artifact contract",
                ],
                cli_runner_contract_rows,
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
            "MCP Bridge Permission Matrix",
            _format_table(
                [
                    "Server",
                    "Path",
                    "Status",
                    "Strict allowlist",
                    "Permissions",
                    "Mutating",
                    "Missing gates",
                ],
                mcp_permission_rows,
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
            "Mutating Subagent Policy",
            _format_table(
                [
                    "Provider",
                    "Runtime",
                    "Status",
                    "Enabled",
                    "Missing gates",
                    "Merge protocol",
                ],
                mutating_subagent_rows,
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
                    "Autonomous gate",
                    "Autonomy recommendation",
                    "Recommendation reasons",
                    "Reason",
                    "Runner candidates",
                ],
                runtime_policy_rows,
            ),
            "Runtime Capability Matrix",
            _format_table(
                [
                    "Provider",
                    "Readiness",
                    "Recommended runtime",
                    "Autonomous gate",
                    "Autonomy recommendation",
                    "Recommendation reasons",
                    "Blockers",
                    "Warnings",
                    "CLI candidates",
                ],
                runtime_capability_rows,
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
            "Runtime Comparative Eval Matrix",
            _format_table(
                [
                    "Provider",
                    "Runtime path",
                    "Quality",
                    "Cost",
                    "Safety",
                    "Blockers",
                    "Evidence",
                ],
                runtime_comparative_eval_rows,
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
        print(format_runtime_modes_text(payload))
    return payload
