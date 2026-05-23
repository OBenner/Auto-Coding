"""CLI helpers for runtime/provider compatibility."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
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
from agents.runtime.direct_api_autonomy import (
    DIRECT_API_AUTONOMOUS_ENV,
    DirectApiAutonomousGate,
    resolve_direct_api_autonomous_gate,
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
from cli.autonomous_readiness_text import format_autonomous_readiness_requirements
from cli.provider_smoke_commands import (
    PROVIDER_AUTONOMOUS_PROMOTION_REQUIRED_E2E_RUNS,
    PROVIDER_AUTONOMOUS_READINESS_MAX_HISTORY_AGE_SECONDS,
    PROVIDER_AUTONOMOUS_READINESS_MIN_STABLE_RUNS,
    PROVIDER_AUTONOMOUS_READINESS_RECOMMENDATION_REASON_BY_SIGNAL,
    PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES,
    PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_TASK_FAMILIES,
    PROVIDER_RELIABILITY_CASE_ORDER,
    PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS,
    PROVIDER_SMOKE_HISTORY_RELATIVE_PATH,
)
from core.providers.cost_calculator import MODEL_PRICING, estimate_session_cost

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
RUNTIME_PROVIDER_AUTONOMOUS_READINESS_RECOMMENDATION_REASON_BY_SIGNAL = {
    **PROVIDER_AUTONOMOUS_READINESS_RECOMMENDATION_REASON_BY_SIGNAL,
    "provider_history_latest_failed": "latest_provider_smoke_failed",
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
RUNTIME_COMPARATIVE_COST_ESTIMATE_INPUT_TOKENS = 10_000
RUNTIME_COMPARATIVE_COST_ESTIMATE_OUTPUT_TOKENS = 2_000

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


def _format_optional_percent(value: Any) -> str:
    """Format optional percent metrics for text diagnostics."""
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value}%"
    return "n/a"


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


def _runtime_policy_readiness_fields(
    readiness: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return readiness fields shared by runtime policy rows."""
    if readiness is None:
        return {
            "autonomous_readiness_required": False,
            "autonomous_policy_gate": "not_required",
            "autonomous_readiness_status": "not_required",
            "autonomous_readiness_recommendation": "not_required",
            "autonomous_readiness_recommendation_reasons": [],
            "autonomous_readiness_blockers": [],
            "autonomous_readiness_warnings": [],
            "autonomous_readiness_requirements": {},
            "autonomous_readiness_missing_requirements": [],
            "autonomous_promotion_gate": "not_required",
            "autonomous_promotion_ready": False,
            "autonomous_promotion_missing_reliability_cases": [],
            "autonomous_promotion_missing_e2e_runs": [],
        }
    promotion_gate = readiness["promotion_gate"]
    return {
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
        "autonomous_readiness_missing_requirements": readiness["missing_requirements"],
        "autonomous_promotion_gate": promotion_gate["status"],
        "autonomous_promotion_ready": promotion_gate["promotion_ready"],
        "autonomous_promotion_missing_reliability_cases": promotion_gate[
            "missing_reliability_cases"
        ],
        "autonomous_promotion_missing_e2e_runs": promotion_gate["missing_e2e_runs"],
    }


def _runtime_policy_decision(
    phase: str,
    phase_policy: Mapping[str, Any],
    has_full_runtime: bool,
    readiness: dict[str, Any] | None,
    direct_api_gate: DirectApiAutonomousGate | None,
) -> tuple[str, str]:
    """Return policy/reason after applying direct-provider readiness gates."""
    if has_full_runtime:
        return "use_full_runtime", "provider_has_full_runtime"
    if (
        direct_api_gate is not None
        and direct_api_gate.allowed
        and phase in {"coder", "qa_fixer"}
    ):
        return (
            "use_direct_api_autonomous_runtime",
            "direct_api_autonomous_gate_passed",
        )
    if (
        readiness is not None
        and readiness["policy_gate"] != "passed"
        and phase in {"coder", "qa_fixer"}
    ):
        promotion_gate = readiness.get("promotion_gate")
        if (
            isinstance(promotion_gate, dict)
            and promotion_gate.get("status") == "blocked"
            and readiness["status"] == "full_autonomous_candidate"
        ):
            return "provider_e2e_required", "provider_autonomous_promotion_blocked"
        return str(readiness["recommendation"]), str(readiness["status"])
    return str(phase_policy["policy"]), str(phase_policy["reason"])


def _runtime_policy_row(
    provider_row: Any,
    phase_policy: Mapping[str, Any],
    full_runtime_runner_candidates: list[str],
    readiness: dict[str, Any] | None,
    direct_api_gate: DirectApiAutonomousGate | None,
) -> dict[str, Any]:
    """Build one phase/provider runtime policy row."""
    phase = str(phase_policy["phase"])
    has_full_runtime = provider_row.full_autonomous == "yes"
    direct_api_autonomous_allowed = (
        direct_api_gate is not None
        and direct_api_gate.allowed
        and phase in {"coder", "qa_fixer"}
    )
    selected_mode = (
        "full_autonomous"
        if has_full_runtime or direct_api_autonomous_allowed
        else str(phase_policy["direct_provider_mode"])
    )
    requires_full_autonomous = bool(phase_policy["requires_full_autonomous"])
    requires_cli_runner = requires_full_autonomous and not has_full_runtime
    policy, reason = _runtime_policy_decision(
        phase,
        phase_policy,
        has_full_runtime,
        readiness,
        direct_api_gate,
    )
    return {
        "phase": phase,
        "provider": provider_row.provider,
        "required_runtime_mode": (
            "full_autonomous" if requires_full_autonomous else selected_mode
        ),
        "selected_runtime_mode": selected_mode,
        "fallback_allowed": bool(phase_policy["fallback_allowed"])
        and selected_mode != "blocked",
        "fallback_modes": (
            list(phase_policy["fallback_modes"]) if selected_mode != "blocked" else []
        ),
        "requires_full_autonomous": requires_full_autonomous,
        "requires_cli_runner": requires_cli_runner,
        "runner_candidates": (
            full_runtime_runner_candidates if requires_cli_runner else []
        ),
        "policy": policy,
        "reason": reason,
        **_runtime_policy_readiness_fields(readiness),
    }


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
    direct_api_gates = _runtime_direct_api_autonomous_gates_by_name(
        project_dir=project_dir,
    )
    return [
        _runtime_policy_row(
            provider_row,
            phase_policy,
            full_runtime_runner_candidates,
            readiness_by_provider.get(provider_row.provider),
            direct_api_gates.get(provider_row.provider),
        )
        for provider_row in PROVIDER_RUNTIME_COMPATIBILITY
        for phase_policy in RUNTIME_POLICY_PHASES
    ]


def _runtime_direct_api_autonomous_gates_by_name(
    *,
    project_dir: Path | None = None,
) -> dict[str, DirectApiAutonomousGate]:
    """Return direct API autonomous activation gates keyed by provider name."""
    base_dir = project_dir or Path.cwd()
    return {
        provider_row.provider: resolve_direct_api_autonomous_gate(
            provider_name=provider_row.provider,
            project_dir=base_dir,
            phase="coding",
        )
        for provider_row in PROVIDER_RUNTIME_COMPATIBILITY
    }


def _extend_unique(target: list[str], values: list[str]) -> None:
    """Append non-empty unique values to a diagnostic list."""
    for value in values:
        if value and value not in target:
            target.append(value)


def _runtime_capability_readiness_fields(
    readiness: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return autonomous readiness fields for capability diagnostics."""
    if readiness is None:
        return {
            "autonomous_readiness_required": False,
            "autonomous_policy_gate": "not_required",
            "autonomous_readiness_status": "not_required",
            "autonomous_readiness_recommendation": "not_required",
            "autonomous_readiness_recommendation_reasons": [],
            "autonomous_readiness_blockers": [],
            "autonomous_readiness_warnings": [],
            "autonomous_readiness_evidence": [],
            "autonomous_readiness_requirements": {},
            "autonomous_readiness_missing_requirements": [],
            "autonomous_readiness_next_actions": [],
            "autonomous_promotion_gate": "not_required",
            "autonomous_promotion_ready": False,
            "autonomous_promotion_missing_reliability_cases": [],
            "autonomous_promotion_missing_e2e_runs": [],
        }
    promotion_gate = readiness["promotion_gate"]
    return {
        "autonomous_readiness_required": True,
        "autonomous_policy_gate": readiness["policy_gate"],
        "autonomous_readiness_status": readiness["status"],
        "autonomous_readiness_recommendation": readiness["recommendation"],
        "autonomous_readiness_recommendation_reasons": readiness[
            "recommendation_reasons"
        ],
        "autonomous_readiness_blockers": readiness["blockers"],
        "autonomous_readiness_warnings": readiness["warnings"],
        "autonomous_readiness_evidence": readiness["evidence"],
        "autonomous_readiness_requirements": readiness["requirements"],
        "autonomous_readiness_missing_requirements": readiness["missing_requirements"],
        "autonomous_readiness_next_actions": readiness["next_actions"],
        "autonomous_promotion_gate": promotion_gate["status"],
        "autonomous_promotion_ready": promotion_gate["promotion_ready"],
        "autonomous_promotion_missing_reliability_cases": promotion_gate[
            "missing_reliability_cases"
        ],
        "autonomous_promotion_missing_e2e_runs": promotion_gate["missing_e2e_runs"],
    }


def _runtime_capability_blockers_and_warnings(
    provider_row: Any,
    has_full_runtime: bool,
    readiness: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    """Return capability blockers/warnings after provider readiness gates."""
    blockers: list[str] = []
    warnings: list[str] = []
    gate_passed = readiness is not None and readiness["policy_gate"] == "passed"
    if not has_full_runtime and not gate_passed:
        blockers.extend(
            [
                "missing_full_autonomous_runtime",
                "live_provider_e2e_required",
                "transactional_recovery_required",
            ]
        )
        warnings.append("direct_full_autonomous_blocked")
    if provider_row.provider in {"litellm", "openrouter"}:
        warnings.append("gateway_model_limitations")
    if provider_row.provider == "ollama":
        warnings.append("local_model_quality_varies")
    if readiness is not None:
        promotion_gate = readiness.get("promotion_gate")
        if (
            isinstance(promotion_gate, dict)
            and promotion_gate.get("status") == "blocked"
            and readiness["status"] == "full_autonomous_candidate"
        ):
            _extend_unique(blockers, ["provider_autonomous_promotion_blocked"])
        _extend_unique(blockers, readiness["blockers"])
        _extend_unique(warnings, readiness["warnings"])
    return blockers, warnings


def _runtime_capability_row(
    provider_row: Any,
    full_runtime_runner_candidates: list[str],
    readiness: dict[str, Any] | None,
    direct_api_gate: DirectApiAutonomousGate | None,
) -> dict[str, Any]:
    """Build one provider capability row."""
    has_full_runtime = provider_row.full_autonomous == "yes"
    readiness_status = "ready" if has_full_runtime else "limited"
    if not has_full_runtime and readiness is not None:
        readiness_status = str(readiness["status"])
    blockers, warnings = _runtime_capability_blockers_and_warnings(
        provider_row,
        has_full_runtime,
        readiness,
    )
    full_autonomous_ready = has_full_runtime or (
        readiness is not None
        and isinstance(readiness.get("promotion_gate"), dict)
        and readiness["promotion_gate"]["promotion_ready"] is True
    )
    direct_api_autonomous_allowed = (
        direct_api_gate is not None and direct_api_gate.allowed
    )
    return {
        "provider": provider_row.provider,
        "readiness": readiness_status,
        "full_autonomous_ready": full_autonomous_ready,
        "direct_api_autonomous_runtime": (
            direct_api_gate.status if direct_api_gate is not None else "not_applicable"
        ),
        "direct_api_autonomous_runtime_allowed": direct_api_autonomous_allowed,
        "direct_api_autonomous_runtime_reason": (
            direct_api_gate.reason if direct_api_gate is not None else "not_applicable"
        ),
        "direct_api_autonomous_missing_requirements": (
            direct_api_gate.missing_requirements if direct_api_gate is not None else []
        ),
        "direct_full_autonomous": provider_row.full_autonomous,
        "recommended_runtime_mode": (
            "full_autonomous"
            if has_full_runtime or direct_api_autonomous_allowed
            else "generic_edit"
        ),
        "generic_edit": provider_row.generic_edit,
        "analysis_only": provider_row.analysis_only,
        "patch_proposal": provider_row.patch_proposal,
        "mcp_tools": provider_row.mcp_tools,
        "subagents": provider_row.subagents,
        "cli_runner_candidates": (
            [] if has_full_runtime else full_runtime_runner_candidates
        ),
        **_runtime_capability_readiness_fields(readiness),
        "blockers": blockers,
        "warnings": warnings,
        "notes": provider_row.notes,
    }


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
    direct_api_gates = _runtime_direct_api_autonomous_gates_by_name(
        project_dir=project_dir,
    )
    return [
        _runtime_capability_row(
            provider_row,
            full_runtime_runner_candidates,
            readiness_by_provider.get(provider_row.provider),
            direct_api_gates.get(provider_row.provider),
        )
        for provider_row in PROVIDER_RUNTIME_COMPATIBILITY
    ]


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


def _runtime_eval_float_stat(value: Any) -> float | None:
    """Return a safe float stat from persisted history payloads."""
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def _runtime_eval_string_stat(value: Any, *, default: str = "not_recorded") -> str:
    """Return a safe string stat from persisted history payloads."""
    return value if isinstance(value, str) and value else default


def _runtime_eval_percent_metric(
    numerator: int,
    denominator: int,
) -> int | None:
    """Return a rounded percentage metric when a denominator is available."""
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100)


def _runtime_eval_percent_stat(provider_stats: dict[str, Any], key: str) -> int | None:
    """Return a safe persisted percentage stat."""
    value = provider_stats.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _runtime_eval_percent_stat_or_metric(
    provider_stats: dict[str, Any],
    key: str,
    numerator: int,
    denominator: int,
) -> int | None:
    """Return a persisted percentage stat, preserving zero, or compute it."""
    persisted = _runtime_eval_percent_stat(provider_stats, key)
    if persisted is not None:
        return persisted
    return _runtime_eval_percent_metric(numerator, denominator)


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
        logger.debug(
            "Could not load provider history from %s",
            history_path,
            exc_info=True,
        )
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
        "provider_history_stale": "rerun_provider_e2e",
        "provider_history_freshness_unknown": "rerun_provider_e2e",
        "live_fault_probe_evidence_missing": "enable_live_fault_probes",
        "live_fault_probe_coverage_incomplete": "enable_live_fault_probes",
        "quality_trend_degrading": "stabilize_provider_history",
        "stability_trend_degrading": "stabilize_provider_history",
        "safety_trend_degrading": "stabilize_provider_history",
    }
    actions: list[str] = []
    for reason in [*blockers, *warnings]:
        action = action_by_reason.get(reason)
        if action and action not in actions:
            actions.append(action)
    return actions


def _runtime_provider_readiness_status(
    blockers: list[str],
    warnings: list[str],
) -> tuple[str, str]:
    """Return readiness status/recommendation for accumulated gate signals."""
    if blockers:
        return "blocked", "provider_e2e_required"
    if any(
        signal in warnings
        for signal in (
            "live_fault_probe_evidence_missing",
            "live_fault_probe_coverage_incomplete",
        )
    ):
        return "needs_live_fault_evidence", "limited_autonomous_until_live_faults"
    if warnings:
        return "warming_up", "limited_autonomous_until_evidence_stable"
    return "full_autonomous_candidate", "api_runtime_full_autonomous_candidate"


def _runtime_provider_history_unknown(provider_stats: dict[str, Any]) -> bool:
    """Return whether provider history lacks the basic latest/trend markers."""
    last_status = provider_stats.get("last_status")
    trend = provider_stats.get("trend")
    return not (
        isinstance(last_status, str)
        and last_status
        and isinstance(trend, str)
        and trend
    )


def _runtime_provider_e2e_signals(
    provider_stats: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Return blocker/evidence signals from latest provider e2e status."""
    provider_e2e_status = provider_stats.get("last_provider_e2e_status")
    if provider_e2e_status == "passed":
        return [], ["provider_e2e_passed"]
    if provider_e2e_status == "failed":
        return ["provider_e2e_failed"], []
    return [], []


def _runtime_provider_reliability_signals(
    provider_stats: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Return blocker/evidence signals from latest reliability status."""
    if provider_stats.get("last_reliability_status") == "complete":
        return [], ["provider_reliability_complete"]
    return ["provider_reliability_incomplete"], []


def _runtime_provider_history_trend_signals(
    provider_stats: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Return blocker/warning/evidence signals from latest history trend."""
    last_status = provider_stats.get("last_status")
    trend = provider_stats.get("trend")
    blockers: list[str] = []
    warnings: list[str] = []
    evidence: list[str] = []

    if last_status != "passed":
        blockers.append("provider_history_latest_failed")

    if trend == "provider_history_stable":
        if _runtime_provider_readiness_history_is_stable_enough(provider_stats):
            evidence.append("provider_history_stable")
        else:
            warnings.append("provider_history_insufficient_runs")
    elif isinstance(trend, str) and trend:
        warnings.append(trend)

    _runtime_provider_history_freshness_signals(provider_stats, warnings)

    return blockers, warnings, evidence


def _runtime_provider_history_freshness_signals(
    provider_stats: dict[str, Any],
    warnings: list[str],
) -> None:
    """Append provider history freshness warnings when evidence is stale."""
    freshness = _runtime_provider_readiness_history_freshness_complete(provider_stats)
    if freshness is True:
        return
    if _runtime_provider_readiness_last_run_at(provider_stats) is None:
        warnings.append("provider_history_freshness_unknown")
    else:
        warnings.append("provider_history_stale")


def _runtime_provider_live_fault_signals(
    provider_stats: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Return warning/evidence signals from live-fault probe coverage."""
    if provider_stats.get("last_live_fault_probe_status") != "passed":
        return ["live_fault_probe_evidence_missing"], []
    if not _runtime_provider_live_fault_coverage_complete(provider_stats):
        return ["live_fault_probe_coverage_incomplete"], ["live_fault_probes_passed"]
    return [], ["live_fault_probes_passed"]


def _runtime_provider_live_task_family_signals(
    provider_stats: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Return warning/evidence signals from live task-family coverage."""
    if provider_stats.get("last_live_task_family_status") != "passed":
        return ["live_task_family_evidence_missing"], []
    if not _runtime_provider_live_task_family_coverage_complete(provider_stats):
        return ["live_task_family_coverage_incomplete"], ["live_task_families_passed"]
    return [], ["live_task_families_passed"]


def _runtime_provider_eval_trend_warnings(provider_stats: dict[str, Any]) -> list[str]:
    """Return readiness warnings for degrading eval trends."""
    trend_fields = {
        "quality_trend": "quality_trend_degrading",
        "stability_trend": "stability_trend_degrading",
        "safety_trend": "safety_trend_degrading",
    }
    return [
        warning
        for field, warning in trend_fields.items()
        if provider_stats.get(field) == "score_degrading"
    ]


def _runtime_provider_readiness_signals(
    provider_stats: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """Collect blockers, warnings, and evidence from provider history."""
    blockers: list[str] = []
    warnings: list[str] = []
    evidence: list[str] = []

    if _runtime_provider_history_unknown(provider_stats):
        warnings.append("provider_history_unknown")
    else:
        e2e_blockers, e2e_evidence = _runtime_provider_e2e_signals(provider_stats)
        blockers.extend(e2e_blockers)
        evidence.extend(e2e_evidence)

    reliability_blockers, reliability_evidence = _runtime_provider_reliability_signals(
        provider_stats
    )
    blockers.extend(reliability_blockers)
    evidence.extend(reliability_evidence)

    if not _runtime_provider_history_unknown(provider_stats):
        history_blockers, history_warnings, history_evidence = (
            _runtime_provider_history_trend_signals(provider_stats)
        )
        blockers.extend(history_blockers)
        warnings.extend(history_warnings)
        evidence.extend(history_evidence)

    live_fault_warnings, live_fault_evidence = _runtime_provider_live_fault_signals(
        provider_stats
    )
    warnings.extend(live_fault_warnings)
    evidence.extend(live_fault_evidence)
    live_task_warnings, live_task_evidence = _runtime_provider_live_task_family_signals(
        provider_stats
    )
    warnings.extend(live_task_warnings)
    warnings.extend(_runtime_provider_eval_trend_warnings(provider_stats))
    evidence.extend(live_task_evidence)

    return blockers, warnings, evidence


def _runtime_provider_autonomous_readiness_from_history(
    provider: str,
    provider_stats: dict[str, Any],
) -> dict[str, Any]:
    """Classify direct-provider autonomous readiness from persisted e2e history."""
    blockers, warnings, evidence = _runtime_provider_readiness_signals(provider_stats)
    status, recommendation = _runtime_provider_readiness_status(blockers, warnings)

    requirements = _runtime_provider_readiness_requirements(provider_stats)
    missing_requirements = _runtime_provider_missing_requirements(
        blockers,
        warnings,
        requirements,
    )
    promotion_gate = _runtime_provider_promotion_gate_from_history(
        provider,
        provider_stats,
        readiness_status=status,
        readiness_missing_requirements=missing_requirements,
    )
    return {
        "provider": provider,
        "status": status,
        "recommendation": recommendation,
        "recommendation_reasons": _runtime_provider_readiness_recommendation_reasons(
            status,
            blockers,
            warnings,
        ),
        "policy_gate": "passed" if promotion_gate["promotion_ready"] else "blocked",
        "blockers": blockers,
        "warnings": warnings,
        "evidence": evidence,
        "requirements": requirements,
        "missing_requirements": missing_requirements,
        "promotion_gate": promotion_gate,
        "next_actions": _runtime_provider_readiness_next_actions(blockers, warnings),
    }


def _runtime_provider_promotion_gate_from_history(
    provider: str,
    provider_stats: dict[str, Any],
    *,
    readiness_status: str,
    readiness_missing_requirements: list[str],
) -> dict[str, Any]:
    """Return the persisted direct-provider promotion gate for runtime policy."""
    if provider.lower() not in PROVIDER_RELIABILITY_DIRECT_API_PROVIDERS:
        return {
            "status": "not_required",
            "promotion_ready": False,
            "required_reliability_cases": [],
            "passed_reliability_cases": [],
            "missing_reliability_cases": [],
            "required_e2e_runs": [],
            "passed_e2e_runs": [],
            "missing_e2e_runs": [],
        }

    required_reliability_cases = _runtime_promotion_required_values(
        provider_stats,
        "promotion_required_reliability_cases",
        PROVIDER_RELIABILITY_CASE_ORDER,
    )
    passed_reliability_cases = _runtime_promotion_passed_values(
        provider_stats,
        "promotion_passed_reliability_cases",
        required_reliability_cases,
    )
    missing_reliability_cases = [
        case
        for case in required_reliability_cases
        if case not in passed_reliability_cases
    ]
    required_e2e_runs = _runtime_promotion_required_values(
        provider_stats,
        "promotion_required_e2e_runs",
        PROVIDER_AUTONOMOUS_PROMOTION_REQUIRED_E2E_RUNS,
    )
    passed_e2e_runs = _runtime_promotion_passed_values(
        provider_stats,
        "promotion_passed_e2e_runs",
        required_e2e_runs,
    )
    missing_e2e_runs = [run for run in required_e2e_runs if run not in passed_e2e_runs]
    promotion_ready = (
        readiness_status == "full_autonomous_candidate"
        and not readiness_missing_requirements
        and not missing_reliability_cases
        and not missing_e2e_runs
    )
    return {
        "status": "passed" if promotion_ready else "blocked",
        "promotion_ready": promotion_ready,
        "required_reliability_cases": required_reliability_cases,
        "passed_reliability_cases": passed_reliability_cases,
        "missing_reliability_cases": missing_reliability_cases,
        "required_e2e_runs": required_e2e_runs,
        "passed_e2e_runs": passed_e2e_runs,
        "missing_e2e_runs": missing_e2e_runs,
    }


def _runtime_promotion_required_values(
    provider_stats: dict[str, Any],
    key: str,
    fallback_values: tuple[str, ...],
) -> list[str]:
    """Return required promotion values from history or the current contract."""
    values = _runtime_string_list_payload(provider_stats.get(key))
    return values or list(fallback_values)


def _runtime_promotion_passed_values(
    provider_stats: dict[str, Any],
    key: str,
    required_values: list[str],
) -> list[str]:
    """Return passed promotion values in required contract order."""
    passed_values = set(_runtime_string_list_payload(provider_stats.get(key)))
    return [value for value in required_values if value in passed_values]


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


def _runtime_provider_readiness_last_run_at(
    provider_stats: dict[str, Any],
) -> str | None:
    """Return the persisted latest provider smoke timestamp."""
    last_run_at = provider_stats.get("last_run_at")
    return last_run_at if isinstance(last_run_at, str) and last_run_at else None


def _runtime_provider_readiness_last_run_datetime(
    provider_stats: dict[str, Any],
) -> datetime | None:
    """Return a normalized latest provider smoke timestamp when parseable."""
    last_run_at = _runtime_provider_readiness_last_run_at(provider_stats)
    if last_run_at is None:
        return None
    try:
        parsed = datetime.fromisoformat(last_run_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _runtime_provider_readiness_history_freshness_complete(
    provider_stats: dict[str, Any],
) -> bool:
    """Return whether latest provider smoke evidence is recent enough."""
    last_run_at = _runtime_provider_readiness_last_run_datetime(provider_stats)
    if last_run_at is None:
        return False
    max_age = timedelta(seconds=PROVIDER_AUTONOMOUS_READINESS_MAX_HISTORY_AGE_SECONDS)
    return datetime.now(timezone.utc) - last_run_at <= max_age


def _runtime_string_list_payload(value: Any) -> list[str]:
    """Return a safe string list from a persisted diagnostics payload."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value[:20] if isinstance(item, str) and item]


def _runtime_provider_eval_metrics(provider_stats: dict[str, Any]) -> dict[str, Any]:
    """Return quality/stability/safety metrics from provider smoke history."""
    if not provider_stats:
        return {
            "pass_rate_percent": None,
            "recent_pass_rate_percent": None,
            "e2e_case_count": 0,
            "e2e_passed_case_count": 0,
            "e2e_failed_case_count": 0,
            "e2e_case_pass_rate_percent": None,
            "reliability_observed_case_count": 0,
            "reliability_passed_case_count": 0,
            "reliability_required_case_count": 0,
            "reliability_case_pass_rate_percent": None,
            "quality_score": None,
            "quality_score_source": "not_recorded",
            "observed_live_fault_case_count": 0,
            "required_live_fault_case_count": len(
                PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES
            ),
            "live_fault_probe_case_coverage_percent": None,
            "safety_score": None,
            "safety_score_source": "not_recorded",
            "quality_trend": "not_recorded",
            "quality_delta_percent": None,
            "stability_trend": "not_recorded",
            "stability_delta_percent": None,
            "safety_trend": "not_recorded",
            "safety_delta_percent": None,
            "cost_trend": "not_recorded",
            "cost_delta_usd": None,
            "cost_delta_formatted": None,
        }

    total_runs = _runtime_eval_int_stat(provider_stats.get("total_runs"))
    passed_runs = _runtime_eval_int_stat(provider_stats.get("passed_runs"))
    recent_window = _runtime_eval_int_stat(provider_stats.get("recent_window"))
    if recent_window == 0:
        recent_window = total_runs
    recent_passed_runs = _runtime_eval_int_stat(
        provider_stats.get("recent_passed_runs")
    )
    if recent_passed_runs == 0 and recent_window == total_runs:
        recent_passed_runs = passed_runs
    e2e_case_count = _runtime_eval_int_stat(provider_stats.get("e2e_case_count"))
    e2e_passed_case_count = _runtime_eval_int_stat(
        provider_stats.get("e2e_passed_case_count")
    )
    e2e_failed_case_count = _runtime_eval_int_stat(
        provider_stats.get("e2e_failed_case_count")
    )
    reliability_observed_case_count = _runtime_eval_int_stat(
        provider_stats.get("reliability_observed_case_count")
    )
    reliability_passed_case_count = _runtime_eval_int_stat(
        provider_stats.get("reliability_passed_case_count")
    )
    reliability_required_case_count = _runtime_eval_int_stat(
        provider_stats.get("reliability_required_case_count")
    )
    required_live_fault_case_count = _runtime_eval_int_stat(
        provider_stats.get("required_live_fault_case_count")
    ) or len(PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES)
    observed_live_fault_case_count = _runtime_eval_int_stat(
        provider_stats.get("observed_live_fault_case_count")
    )
    if observed_live_fault_case_count == 0:
        observed_live_fault_case_count = len(
            set(
                _runtime_string_list_payload(
                    provider_stats.get("live_fault_probe_covered_cases")
                )
            )
        )
    pass_rate_percent = _runtime_eval_percent_stat_or_metric(
        provider_stats,
        "pass_rate_percent",
        passed_runs,
        total_runs,
    )
    recent_pass_rate_percent = _runtime_eval_percent_stat_or_metric(
        provider_stats,
        "recent_pass_rate_percent",
        recent_passed_runs,
        recent_window,
    )
    e2e_case_pass_rate_percent = _runtime_eval_percent_stat_or_metric(
        provider_stats,
        "e2e_case_pass_rate_percent",
        e2e_passed_case_count,
        e2e_case_count,
    )
    reliability_case_pass_rate_percent = _runtime_eval_percent_stat_or_metric(
        provider_stats,
        "reliability_case_pass_rate_percent",
        reliability_passed_case_count,
        reliability_required_case_count,
    )
    live_fault_probe_case_coverage_percent = _runtime_eval_percent_stat_or_metric(
        provider_stats,
        "live_fault_probe_case_coverage_percent",
        observed_live_fault_case_count,
        required_live_fault_case_count,
    )
    live_task_family_has_evidence = any(
        key in provider_stats
        for key in (
            "last_live_task_family_status",
            "live_task_family_covered_families",
            "observed_live_task_family_count",
            "live_task_family_coverage_percent",
        )
    )
    required_live_task_family_count = _runtime_eval_int_stat(
        provider_stats.get("required_live_task_family_count")
    ) or len(PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_TASK_FAMILIES)
    observed_live_task_family_count = 0
    live_task_family_coverage_percent = None
    if live_task_family_has_evidence:
        observed_live_task_family_count = _runtime_eval_int_stat(
            provider_stats.get("observed_live_task_family_count")
        )
        if observed_live_task_family_count == 0:
            observed_live_task_family_count = len(
                set(
                    _runtime_string_list_payload(
                        provider_stats.get("live_task_family_covered_families")
                    )
                )
            )
        live_task_family_coverage_percent = _runtime_eval_percent_stat_or_metric(
            provider_stats,
            "live_task_family_coverage_percent",
            observed_live_task_family_count,
            required_live_task_family_count,
        )
    quality_score = _runtime_provider_quality_score(
        e2e_case_pass_rate_percent,
        pass_rate_percent,
        live_task_family_coverage_percent,
    )
    quality_score_source = _runtime_provider_quality_score_source(
        e2e_case_pass_rate_percent,
        pass_rate_percent,
        live_task_family_coverage_percent,
    )
    safety_score = _runtime_provider_safety_score(
        reliability_passed_case_count,
        reliability_required_case_count,
        reliability_case_pass_rate_percent,
        live_fault_probe_case_coverage_percent,
    )
    safety_score_source = _runtime_provider_safety_score_source(
        reliability_case_pass_rate_percent,
        live_fault_probe_case_coverage_percent,
    )
    return {
        "pass_rate_percent": pass_rate_percent,
        "recent_pass_rate_percent": recent_pass_rate_percent,
        "e2e_case_count": e2e_case_count,
        "e2e_passed_case_count": e2e_passed_case_count,
        "e2e_failed_case_count": e2e_failed_case_count,
        "e2e_case_pass_rate_percent": e2e_case_pass_rate_percent,
        "reliability_observed_case_count": reliability_observed_case_count,
        "reliability_passed_case_count": reliability_passed_case_count,
        "reliability_required_case_count": reliability_required_case_count,
        "reliability_case_pass_rate_percent": reliability_case_pass_rate_percent,
        "quality_score": quality_score,
        "quality_score_source": quality_score_source,
        "observed_live_fault_case_count": observed_live_fault_case_count,
        "required_live_fault_case_count": required_live_fault_case_count,
        "live_fault_probe_case_coverage_percent": live_fault_probe_case_coverage_percent,
        "observed_live_task_family_count": observed_live_task_family_count,
        "required_live_task_family_count": required_live_task_family_count,
        "live_task_family_coverage_percent": live_task_family_coverage_percent,
        "safety_score": safety_score,
        "safety_score_source": safety_score_source,
        "quality_trend": _runtime_eval_string_stat(provider_stats.get("quality_trend")),
        "quality_delta_percent": _runtime_eval_int_stat(
            provider_stats.get("quality_delta_percent")
        )
        if provider_stats.get("quality_delta_percent") is not None
        else None,
        "stability_trend": _runtime_eval_string_stat(
            provider_stats.get("stability_trend")
        ),
        "stability_delta_percent": _runtime_eval_int_stat(
            provider_stats.get("stability_delta_percent")
        )
        if provider_stats.get("stability_delta_percent") is not None
        else None,
        "safety_trend": _runtime_eval_string_stat(provider_stats.get("safety_trend")),
        "safety_delta_percent": _runtime_eval_int_stat(
            provider_stats.get("safety_delta_percent")
        )
        if provider_stats.get("safety_delta_percent") is not None
        else None,
        "cost_trend": _runtime_eval_string_stat(provider_stats.get("cost_trend")),
        "cost_delta_usd": _runtime_eval_float_stat(
            provider_stats.get("cost_delta_usd")
        ),
        "cost_delta_formatted": provider_stats.get("cost_delta_formatted")
        if isinstance(provider_stats.get("cost_delta_formatted"), str)
        else None,
    }


def _runtime_provider_quality_score(
    e2e_case_pass_rate_percent: int | None,
    pass_rate_percent: int | None,
    live_task_family_coverage_percent: int | None,
) -> int | None:
    """Return the provider quality score from the strongest available evidence."""
    quality_candidates = [
        score
        for score in (e2e_case_pass_rate_percent, live_task_family_coverage_percent)
        if score is not None
    ]
    if quality_candidates:
        return min(quality_candidates)
    return pass_rate_percent


def _runtime_provider_quality_score_source(
    e2e_case_pass_rate_percent: int | None,
    pass_rate_percent: int | None,
    live_task_family_coverage_percent: int | None,
) -> str:
    """Return the evidence source used by the provider quality score."""
    if (
        e2e_case_pass_rate_percent is not None
        and live_task_family_coverage_percent is not None
    ):
        return "provider_e2e_and_live_task_coverage"
    if live_task_family_coverage_percent is not None:
        return "live_task_family_coverage"
    if e2e_case_pass_rate_percent is not None:
        return "provider_e2e_case_pass_rate"
    if pass_rate_percent is not None:
        return "provider_history_pass_rate"
    return "not_recorded"


def _runtime_provider_safety_score(
    reliability_passed_case_count: int,
    reliability_required_case_count: int,
    reliability_case_pass_rate_percent: int | None,
    live_fault_probe_case_coverage_percent: int | None,
) -> int | None:
    """Return the strictest provider safety score from reliability evidence."""
    reliability_score = reliability_case_pass_rate_percent
    if reliability_score is None:
        reliability_score = _runtime_eval_percent_metric(
            reliability_passed_case_count,
            reliability_required_case_count,
        )
    safety_candidates = [
        score
        for score in (reliability_score, live_fault_probe_case_coverage_percent)
        if score is not None
    ]
    return min(safety_candidates) if safety_candidates else None


def _runtime_provider_safety_score_source(
    reliability_case_pass_rate_percent: int | None,
    live_fault_probe_case_coverage_percent: int | None,
) -> str:
    """Return the evidence source used by the provider safety score."""
    if (
        reliability_case_pass_rate_percent is not None
        and live_fault_probe_case_coverage_percent is not None
    ):
        return "provider_reliability_and_live_fault_coverage"
    if reliability_case_pass_rate_percent is not None:
        return "provider_reliability_case_pass_rate"
    if live_fault_probe_case_coverage_percent is not None:
        return "live_fault_probe_case_coverage"
    return "not_recorded"


def _runtime_provider_cost_pricing_model(model: Any) -> str | None:
    """Return a known pricing model from direct provider history."""
    if not isinstance(model, str):
        return None
    trimmed = model.strip()
    if not trimmed:
        return None
    if trimmed in MODEL_PRICING and trimmed != "default":
        return trimmed
    for segment in reversed(trimmed.split("/")):
        if segment in MODEL_PRICING and segment != "default":
            return segment
    return None


def _runtime_provider_cost_estimate(provider_stats: dict[str, Any]) -> dict[str, Any]:
    """Return cost estimate evidence from the latest observed provider model."""
    actual_cost_usd = _runtime_eval_float_stat(provider_stats.get("cost_last_usd"))
    latest_cost_status = provider_stats.get("cost_last_status") or provider_stats.get(
        "cost_status"
    )
    if latest_cost_status == "recorded" and actual_cost_usd is not None:
        return {
            "cost_status": "recorded",
            "cost_pricing_model": provider_stats.get("cost_last_pricing_model")
            or provider_stats.get("cost_pricing_model"),
            "cost_pricing_provider": provider_stats.get("cost_last_pricing_provider")
            or provider_stats.get("cost_pricing_provider"),
            "cost_actual_usd": actual_cost_usd,
            "cost_actual_formatted": provider_stats.get("cost_last_formatted")
            or f"${actual_cost_usd:.4f}",
            "cost_actual_input_tokens": _runtime_eval_int_stat(
                provider_stats.get("cost_last_input_tokens")
            ),
            "cost_actual_output_tokens": _runtime_eval_int_stat(
                provider_stats.get("cost_last_output_tokens")
            ),
            "cost_observed_run_count": _runtime_eval_int_stat(
                provider_stats.get("cost_observed_run_count")
            ),
            "cost_estimate_usd": None,
            "cost_estimate_formatted": None,
            "cost_estimate_input_tokens": None,
            "cost_estimate_output_tokens": None,
        }
    if latest_cost_status == "estimated" and actual_cost_usd is not None:
        return {
            "cost_status": "estimated",
            "cost_pricing_model": provider_stats.get("cost_last_pricing_model")
            or provider_stats.get("cost_pricing_model"),
            "cost_pricing_provider": provider_stats.get("cost_last_pricing_provider")
            or provider_stats.get("cost_pricing_provider"),
            "cost_actual_usd": None,
            "cost_actual_formatted": None,
            "cost_actual_input_tokens": None,
            "cost_actual_output_tokens": None,
            "cost_observed_run_count": _runtime_eval_int_stat(
                provider_stats.get("cost_observed_run_count")
            ),
            "cost_estimate_usd": actual_cost_usd,
            "cost_estimate_formatted": provider_stats.get("cost_last_formatted")
            or f"${actual_cost_usd:.4f}",
            "cost_estimate_input_tokens": _runtime_eval_int_stat(
                provider_stats.get("cost_last_input_tokens")
            ),
            "cost_estimate_output_tokens": _runtime_eval_int_stat(
                provider_stats.get("cost_last_output_tokens")
            ),
        }

    pricing_model = _runtime_provider_cost_pricing_model(
        provider_stats.get("last_model")
    )
    if not pricing_model:
        return {
            "cost_status": "not_recorded",
            "cost_pricing_model": None,
            "cost_pricing_provider": None,
            "cost_actual_usd": None,
            "cost_actual_formatted": None,
            "cost_actual_input_tokens": None,
            "cost_actual_output_tokens": None,
            "cost_observed_run_count": None,
            "cost_estimate_usd": None,
            "cost_estimate_formatted": None,
            "cost_estimate_input_tokens": RUNTIME_COMPARATIVE_COST_ESTIMATE_INPUT_TOKENS,
            "cost_estimate_output_tokens": RUNTIME_COMPARATIVE_COST_ESTIMATE_OUTPUT_TOKENS,
        }

    estimate = estimate_session_cost(
        pricing_model,
        RUNTIME_COMPARATIVE_COST_ESTIMATE_INPUT_TOKENS,
        RUNTIME_COMPARATIVE_COST_ESTIMATE_OUTPUT_TOKENS,
    )
    estimated_cost = estimate["estimated_cost"]
    return {
        "cost_status": "local_zero_cost" if estimated_cost == 0 else "estimated",
        "cost_pricing_model": pricing_model,
        "cost_pricing_provider": estimate.get("provider"),
        "cost_actual_usd": None,
        "cost_actual_formatted": None,
        "cost_actual_input_tokens": None,
        "cost_actual_output_tokens": None,
        "cost_observed_run_count": None,
        "cost_estimate_usd": estimated_cost,
        "cost_estimate_formatted": estimate["formatted"],
        "cost_estimate_input_tokens": estimate["input_tokens"],
        "cost_estimate_output_tokens": estimate["output_tokens"],
    }


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


def _runtime_provider_live_task_family_coverage_complete(
    provider_stats: dict[str, Any],
) -> bool:
    """Return whether live task history covered every required task family."""
    covered_families = set(
        _runtime_string_list_payload(
            provider_stats.get("live_task_family_covered_families")
        )
    )
    return all(
        required_family in covered_families
        for required_family in PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_TASK_FAMILIES
    )


def _runtime_provider_readiness_requirements(
    provider_stats: dict[str, Any],
) -> dict[str, Any]:
    """Return structured readiness requirement evidence for runtime diagnostics."""
    required_live_fault_cases = sorted(
        PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_FAULT_CASES
    )
    live_fault_covered_cases = sorted(
        set(
            _runtime_string_list_payload(
                provider_stats.get("live_fault_probe_covered_cases")
            )
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
    required_live_task_families = sorted(
        PROVIDER_AUTONOMOUS_READINESS_REQUIRED_LIVE_TASK_FAMILIES
    )
    live_task_covered_families = sorted(
        set(
            _runtime_string_list_payload(
                provider_stats.get("live_task_family_covered_families")
            )
        )
    )
    live_task_missing_families = [
        required_family
        for required_family in required_live_task_families
        if required_family not in live_task_covered_families
    ]
    live_task_family_coverage_complete = (
        provider_stats.get("last_live_task_family_status") == "passed"
        and not live_task_missing_families
    )
    requirements = {
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
        "required_live_task_families": required_live_task_families,
        "live_task_covered_families": live_task_covered_families,
        "live_task_missing_families": live_task_missing_families,
        "live_task_family_coverage_complete": live_task_family_coverage_complete,
    }
    last_run_at = _runtime_provider_readiness_last_run_at(provider_stats)
    if last_run_at is not None:
        requirements.update(
            {
                "last_run_at": last_run_at,
                "max_history_age_seconds": (
                    PROVIDER_AUTONOMOUS_READINESS_MAX_HISTORY_AGE_SECONDS
                ),
                "history_freshness_complete": (
                    _runtime_provider_readiness_history_freshness_complete(
                        provider_stats
                    )
                ),
            }
        )
    return requirements


def _runtime_provider_missing_requirements(
    blockers: list[str],
    warnings: list[str],
    requirements: dict[str, Any],
) -> list[str]:
    """Return stable missing requirement ids for runtime automation."""
    missing: list[str] = []
    if "provider_e2e_failed" in blockers:
        missing.append("provider_e2e")
    if "provider_reliability_incomplete" in blockers:
        missing.append("provider_reliability")
    if "provider_history_latest_failed" in blockers:
        missing.append("latest_provider_smoke_pass")
    if requirements.get("history_stability_complete") is not True:
        missing.append("stable_history_runs")
    if (
        requirements.get("last_run_at") is not None
        and requirements.get("history_freshness_complete") is not True
    ):
        missing.append("fresh_provider_history")
    if requirements.get("live_fault_coverage_complete") is not True:
        missing.append("live_fault_case_coverage")
    if requirements.get("live_task_family_coverage_complete") is not True:
        missing.append("live_task_family_coverage")
    if any(warning.endswith("_trend_degrading") for warning in warnings):
        missing.append("stable_eval_trends")
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
        reason = (
            RUNTIME_PROVIDER_AUTONOMOUS_READINESS_RECOMMENDATION_REASON_BY_SIGNAL.get(
                signal
            )
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
        provider_metrics = _runtime_provider_eval_metrics(provider_stats)
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
                "last_model": provider_stats.get("last_model"),
                "last_run_at": provider_stats.get("last_run_at"),
                "cost_status": provider_stats.get("cost_status"),
                "cost_observed_run_count": provider_stats.get(
                    "cost_observed_run_count"
                ),
                "cost_total_input_tokens": provider_stats.get(
                    "cost_total_input_tokens"
                ),
                "cost_total_output_tokens": provider_stats.get(
                    "cost_total_output_tokens"
                ),
                "cost_total_usd": provider_stats.get("cost_total_usd"),
                "cost_total_formatted": provider_stats.get("cost_total_formatted"),
                "cost_last_status": provider_stats.get("cost_last_status"),
                "cost_last_source": provider_stats.get("cost_last_source"),
                "cost_last_input_tokens": provider_stats.get("cost_last_input_tokens"),
                "cost_last_output_tokens": provider_stats.get(
                    "cost_last_output_tokens"
                ),
                "cost_last_usd": provider_stats.get("cost_last_usd"),
                "cost_last_formatted": provider_stats.get("cost_last_formatted"),
                "cost_last_pricing_model": provider_stats.get(
                    "cost_last_pricing_model"
                ),
                "cost_last_pricing_provider": provider_stats.get(
                    "cost_last_pricing_provider"
                ),
                "cost_pricing_model": provider_stats.get("cost_pricing_model"),
                "cost_pricing_provider": provider_stats.get("cost_pricing_provider"),
                **provider_metrics,
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


def _runtime_full_runtime_cost_fields() -> dict[str, Any]:
    """Return empty cost fields for native full-runtime providers."""
    return {
        "cost_status": "not_recorded",
        "cost_pricing_model": None,
        "cost_pricing_provider": None,
        "cost_actual_usd": None,
        "cost_actual_formatted": None,
        "cost_actual_input_tokens": None,
        "cost_actual_output_tokens": None,
        "cost_observed_run_count": None,
        "cost_estimate_usd": None,
        "cost_estimate_formatted": None,
        "cost_estimate_input_tokens": None,
        "cost_estimate_output_tokens": None,
    }


def _runtime_comparative_full_runtime_row(provider: str) -> dict[str, Any]:
    """Return comparative eval row for native full-runtime providers."""
    return {
        "provider": provider,
        "runtime_path": "full_autonomous",
        "quality_status": "not_recorded",
        "quality_score": None,
        "quality_score_source": "native_runtime_policy",
        "quality_trend": None,
        "quality_delta_percent": None,
        "stability_score": None,
        "stability_trend": None,
        "stability_delta_percent": None,
        **_runtime_full_runtime_cost_fields(),
        "cost_trend": None,
        "cost_delta_usd": None,
        "cost_delta_formatted": None,
        "safety_status": "native_runtime_policy",
        "safety_score": None,
        "safety_score_source": "native_runtime_policy",
        "safety_trend": None,
        "safety_delta_percent": None,
        "evidence_source": "native_runtime",
        "required_before_full_autonomous": False,
        "blockers": [],
    }


def _runtime_comparative_provider_row(
    provider: str,
    provider_stats: dict[str, Any],
    history_path: Any,
) -> dict[str, Any]:
    """Return comparative eval row for direct-provider generic edit paths."""
    provider_metrics = _runtime_provider_eval_metrics(provider_stats)
    return {
        "provider": provider,
        "runtime_path": "generic_edit",
        "quality_status": str(provider_stats.get("status") or "not_observed"),
        "quality_score": provider_metrics["quality_score"],
        "quality_score_source": provider_metrics["quality_score_source"],
        "quality_trend": provider_metrics["quality_trend"],
        "quality_delta_percent": provider_metrics["quality_delta_percent"],
        "stability_score": provider_metrics["recent_pass_rate_percent"],
        "stability_trend": provider_metrics["stability_trend"],
        "stability_delta_percent": provider_metrics["stability_delta_percent"],
        **_runtime_provider_cost_estimate(provider_stats),
        "cost_trend": provider_metrics["cost_trend"],
        "cost_delta_usd": provider_metrics["cost_delta_usd"],
        "cost_delta_formatted": provider_metrics["cost_delta_formatted"],
        "safety_status": "policy_gated",
        "safety_score": provider_metrics["safety_score"],
        "safety_score_source": provider_metrics["safety_score_source"],
        "safety_trend": provider_metrics["safety_trend"],
        "safety_delta_percent": provider_metrics["safety_delta_percent"],
        "evidence_source": str(history_path),
        "required_before_full_autonomous": True,
        "blockers": ["provider_e2e", "generic_edit_recovery", "mcp_bridge_contract"],
    }


def _runtime_comparative_eval_row(
    provider: str,
    provider_row: Any,
    provider_stats: dict[str, Any],
    history_path: Any,
) -> dict[str, Any]:
    """Build one runtime comparative eval row."""
    if provider_row.full_autonomous == "yes":
        return _runtime_comparative_full_runtime_row(provider)
    return _runtime_comparative_provider_row(provider, provider_stats, history_path)


def build_runtime_comparative_eval_matrix(
    *,
    project_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Build provider comparison rows for quality/cost/safety eval evidence."""
    eval_history = build_runtime_eval_history(project_dir=project_dir)
    provider_rows = eval_history[0].get("providers", []) if eval_history else []
    provider_history = {
        row["provider"]: row for row in provider_rows if isinstance(row, dict)
    }
    history_path = (
        eval_history[0].get("history_path")
        if eval_history
        else PROVIDER_SMOKE_HISTORY_RELATIVE_PATH.as_posix()
    )
    compatibility = {row.provider: row for row in PROVIDER_RUNTIME_COMPATIBILITY}
    return [
        _runtime_comparative_eval_row(
            provider,
            compatibility[provider],
            provider_history.get(provider, {}),
            history_path,
        )
        for provider in ("claude", "codex", "openai", "google", "ollama")
    ]


def build_runtime_modes_payload(
    *,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """Build structured runtime compatibility payload."""
    from core.autonomy_level import resolve_autonomy_settings

    cli_runner_selection = {
        mode.mode: select_cli_runner_profiles(runtime_mode=mode.mode).to_dict(
            include_detection=True,
        )
        for mode in RUNTIME_MODE_INFO
    }
    autonomy_settings = resolve_autonomy_settings()
    return {
        "autonomy": autonomy_settings.to_dict(),
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
            "direct_api_autonomous_runtime": (
                f"Set {DIRECT_API_AUTONOMOUS_ENV}=true only after the provider "
                "autonomous readiness and promotion gates are clean; coder and "
                "QA fixer phases can then use the direct_api_autonomous adapter. "
                "Prefer AUTO_CODE_AUTONOMY=safe (see ADR-006); the legacy env "
                "var still works but is deprecated."
            ),
            "autonomy_level": (
                "Set AUTO_CODE_AUTONOMY=off|claude|safe|bold as the single "
                "top-level knob (see ADR-006). Low-level env vars stay as "
                "advanced overrides and win over the level mapping."
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


def _runtime_mode_text_rows() -> list[list[str]]:
    return [[mode.mode, mode.purpose, mode.capabilities] for mode in RUNTIME_MODE_INFO]


def _runtime_provider_text_rows() -> list[list[str]]:
    return [
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


def _runtime_cli_runner_text_rows() -> list[list[str]]:
    return [
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


def _runtime_cli_runner_selection_text_rows() -> list[list[str]]:
    return [
        [
            mode.mode,
            ", ".join(
                select_cli_runner_profiles(runtime_mode=mode.mode).selected_runner_ids
            )
            or "none",
        ]
        for mode in RUNTIME_MODE_INFO
    ]


def _runtime_cli_runner_contract_text_rows() -> list[list[str]]:
    return [
        [
            row["runner_id"],
            row["runner_status"],
            row["contract_status"],
            ", ".join(row["missing_contract_facets"]) or "none",
            row["artifact_contract"],
        ]
        for row in build_cli_runner_contract_matrix()
    ]


def _runtime_fallback_text_rows() -> list[list[str]]:
    return [
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


def _runtime_mcp_bridge_text_rows() -> list[list[str]]:
    return [
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


def _runtime_external_mcp_health_text_rows() -> list[list[str]]:
    return [
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


def _runtime_mcp_permission_text_rows() -> list[list[str]]:
    return [
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


def _runtime_subagent_text_rows() -> list[list[str]]:
    return [
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


def _runtime_mutating_subagent_text_rows() -> list[list[str]]:
    return [
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


def _runtime_policy_text_rows(payload: dict[str, Any]) -> list[list[str]]:
    return [
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
            format_autonomous_readiness_requirements(
                row.get("autonomous_readiness_requirements"),
                empty="none",
            ),
            row["reason"],
            ", ".join(row["runner_candidates"]) or "none",
        ]
        for row in payload["runtime_policy_matrix"]
        if row["provider"] in {"claude", "codex", "openai", "google", "ollama"}
    ]


def _runtime_capability_text_rows(payload: dict[str, Any]) -> list[list[str]]:
    return [
        [
            row["provider"],
            row["readiness"],
            row["recommended_runtime_mode"],
            row["autonomous_policy_gate"],
            row["autonomous_readiness_recommendation"],
            ", ".join(row["autonomous_readiness_recommendation_reasons"]) or "none",
            format_autonomous_readiness_requirements(
                row.get("autonomous_readiness_requirements"),
                empty="none",
            ),
            ", ".join(row["blockers"]) or "none",
            ", ".join(row["warnings"]) or "none",
            ", ".join(row["cli_runner_candidates"]) or "none",
        ]
        for row in payload["runtime_capability_matrix"]
    ]


def _runtime_eval_text_rows() -> list[list[str]]:
    return [
        [
            row["case_id"],
            row["runtime_mode"],
            "yes" if row["required_for_full_autonomous"] else "no",
            ", ".join(row["providers"]),
            ", ".join(row["required_artifacts"]),
        ]
        for row in build_runtime_eval_matrix()
    ]


def _runtime_eval_history_text_rows(payload: dict[str, Any]) -> list[list[str]]:
    return [
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


def _format_optional_delta_percent(value: Any) -> str:
    """Format a signed optional percentage-point delta."""
    if isinstance(value, int) and not isinstance(value, bool):
        sign = "+" if value > 0 else ""
        return f"{sign}{value}pp"
    return "n/a"


def _runtime_comparative_eval_trend_text(row: dict[str, Any]) -> str:
    """Return compact comparative trend text for human diagnostics."""
    trend_parts = [
        f"quality={row.get('quality_trend') or 'n/a'} "
        f"{_format_optional_delta_percent(row.get('quality_delta_percent'))}",
        f"stability={row.get('stability_trend') or 'n/a'} "
        f"{_format_optional_delta_percent(row.get('stability_delta_percent'))}",
        f"safety={row.get('safety_trend') or 'n/a'} "
        f"{_format_optional_delta_percent(row.get('safety_delta_percent'))}",
        f"cost={row.get('cost_trend') or 'n/a'} "
        f"{row.get('cost_delta_formatted') or 'n/a'}",
    ]
    return ", ".join(trend_parts)


def _runtime_comparative_eval_text_rows(payload: dict[str, Any]) -> list[list[str]]:
    return [
        [
            row["provider"],
            row["runtime_path"],
            row["quality_status"],
            _format_optional_percent(row.get("quality_score")),
            _format_optional_percent(row.get("stability_score")),
            row["cost_status"],
            row.get("cost_actual_formatted")
            or row.get("cost_estimate_formatted")
            or "n/a",
            row.get("cost_pricing_model") or "n/a",
            row["safety_status"],
            _format_optional_percent(row.get("safety_score")),
            _runtime_comparative_eval_trend_text(row),
            ", ".join(row["blockers"]) or "none",
            row["evidence_source"],
        ]
        for row in payload["runtime_comparative_eval_matrix"]
    ]


def format_runtime_modes_text(payload: dict[str, Any] | None = None) -> str:
    """Format runtime compatibility guidance for humans."""
    payload = payload or build_runtime_modes_payload()
    mode_rows = _runtime_mode_text_rows()
    provider_rows = _runtime_provider_text_rows()
    cli_runner_rows = _runtime_cli_runner_text_rows()
    cli_runner_selection_rows = _runtime_cli_runner_selection_text_rows()
    cli_runner_contract_rows = _runtime_cli_runner_contract_text_rows()
    runtime_fallback_rows = _runtime_fallback_text_rows()
    mcp_bridge_rows = _runtime_mcp_bridge_text_rows()
    external_mcp_health_rows = _runtime_external_mcp_health_text_rows()
    mcp_permission_rows = _runtime_mcp_permission_text_rows()
    subagent_rows = _runtime_subagent_text_rows()
    mutating_subagent_rows = _runtime_mutating_subagent_text_rows()
    runtime_policy_rows = _runtime_policy_text_rows(payload)
    runtime_capability_rows = _runtime_capability_text_rows(payload)
    runtime_eval_rows = _runtime_eval_text_rows()
    runtime_eval_history_rows = _runtime_eval_history_text_rows(payload)
    runtime_comparative_eval_rows = _runtime_comparative_eval_text_rows(payload)

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
                    "Autonomy requirements",
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
                    "Autonomy requirements",
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
                    "Quality score",
                    "Stability score",
                    "Cost",
                    "Cost estimate",
                    "Pricing model",
                    "Safety",
                    "Safety score",
                    "Trends",
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
            "  Readiness:       "
            + "python run.py --provider openai --provider-smoke --provider-smoke-runtime provider_e2e",
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
