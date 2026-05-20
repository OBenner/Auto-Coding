import builtins
import json
import logging
import sys
from pathlib import Path

import pytest


def test_parse_args_with_runtime_modes():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = ["run.py", "--runtime-modes"]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.runtime_modes is True


def test_parse_args_with_external_mcp_smoke():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = ["run.py", "--external-mcp-smoke"]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.external_mcp_smoke is True


def test_parse_args_with_external_mcp_sync_custom_tools():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = ["run.py", "--external-mcp-smoke", "--external-mcp-sync-custom-tools"]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.external_mcp_smoke is True
    assert args.external_mcp_sync_custom_tools is True


def test_parse_args_with_generic_edit_resume_preflight():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = [
        "run.py",
        "--generic-edit-resume-preflight",
        ".auto-Codex/specs/001/artifacts/generic_edit_recovery_checkpoint.json",
    ]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert str(args.generic_edit_resume_preflight).endswith(
        "generic_edit_recovery_checkpoint.json"
    )


def test_parse_args_with_generic_edit_runtime_mode():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = ["run.py", "--runtime-mode", "generic-edit", "--runtime-modes"]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.runtime_mode == "generic-edit"


def test_runtime_modes_command_outputs_text(capsys):
    from cli.runtime_commands import handle_runtime_modes_command

    payload = handle_runtime_modes_command(output_json=False)
    output = capsys.readouterr().out

    assert "Provider Compatibility" in output
    assert "claude" in output
    assert "openai" in output
    assert "generic_edit" in output
    assert "patch_proposal" in output
    assert "CLI Runner Profiles" in output
    assert "CLI Runner Selection" in output
    assert "CLI Runner Contract Matrix" in output
    assert "Runtime Fallback Matrix" in output
    assert "Runtime Capability Matrix" in output
    assert "MCP Bridge Plan Matrix" in output
    assert "MCP Bridge Permission Matrix" in output
    assert "External MCP Client Health" in output
    assert "Subagent Orchestrator Matrix" in output
    assert "Mutating Subagent Policy" in output
    assert "Runtime Policy Matrix" in output
    assert "Autonomous gate" in output
    assert "Autonomy recommendation" in output
    assert "Runtime Eval Matrix" in output
    assert "Runtime Eval History" in output
    assert "Runtime Comparative Eval Matrix" in output
    assert "codex_cli" in output
    assert "generic_cli_pool" in output
    assert "opencode" in output
    assert "--provider-smoke" in output
    assert "--external-mcp-smoke" in output
    assert payload["providers"][0]["provider"] == "claude"


def test_runtime_modes_command_outputs_json(capsys, monkeypatch, tmp_path):
    from agents.runtime import EXTERNAL_MCP_CLIENT_ENV
    from cli.runtime_commands import handle_runtime_modes_command

    monkeypatch.delenv(EXTERNAL_MCP_CLIENT_ENV, raising=False)
    monkeypatch.chdir(tmp_path)

    handle_runtime_modes_command(output_json=True)
    output = capsys.readouterr().out
    payload = json.loads(output)

    provider_rows = {row["provider"]: row for row in payload["providers"]}
    assert provider_rows["claude"]["full_autonomous"] == "yes"
    assert provider_rows["openai"]["full_autonomous"] == "no"
    assert provider_rows["openai"]["generic_edit"] == "experimental"
    assert provider_rows["openai"]["analysis_only"] == "yes"
    assert provider_rows["claude"]["mcp_tools"] == "native"
    assert provider_rows["openai"]["mcp_tools"] == "local_bridge"
    assert provider_rows["claude"]["subagents"] == "native"
    assert provider_rows["openai"]["subagents"] == "orchestrated"
    assert "runtime_modes" in payload
    runner_rows = {row["runner_id"]: row for row in payload["cli_runner_profiles"]}
    assert runner_rows["codex_cli"]["runner_status"] == "wired"
    assert "full_autonomous" in runner_rows["codex_cli"]["supported_runtime_modes"]
    assert "availability" in runner_rows["codex_cli"]
    assert "executable_present" in runner_rows["codex_cli"]["availability"]
    assert "codex" in runner_rows["codex_cli"]["executable_candidates"]
    assert runner_rows["coderabbit_cli"]["role"] == "review"
    assert runner_rows["zai_claude_code"]["runner_status"] == "planned"
    assert "anthropic_compatible" in runner_rows["zai_claude_code"]["capability_tags"]
    assert "zai_compatible" in runner_rows["zai_claude_code"]["capability_tags"]
    assert runner_rows["generic_cli_pool"]["tier"] == "generic_pool"
    assert (
        runner_rows["generic_cli_pool"]["availability"]["status"] == "not_configurable"
    )
    assert runner_rows["opencode"]["tier"] == "generic_pool"
    assert "multi_provider" in runner_rows["opencode"]["capability_tags"]
    assert runner_rows["goose"]["role"] == "fallback"
    assert "mcp" in runner_rows["goose"]["capability_tags"]
    assert runner_rows["qwen_code"]["runner_status"] == "planned"
    contract_rows = {
        row["runner_id"]: row for row in payload["cli_runner_contract_matrix"]
    }
    assert contract_rows["codex_cli"]["contract_status"] == "ready"
    assert contract_rows["codex_cli"]["missing_contract_facets"] == []
    assert contract_rows["codex_cli"]["facets"] == {
        "run": "wired",
        "cancel": "wired",
        "resume": "wired",
        "artifacts": "wired",
        "event_parser": "wired",
        "cost_account": "wired",
    }
    assert contract_rows["opencode"]["contract_status"] == "partial"
    assert contract_rows["opencode"]["missing_contract_facets"] == [
        "resume",
    ]
    assert contract_rows["opencode"]["facets"] == {
        "run": "generic_core_configurable",
        "cancel": "generic_core_configurable",
        "resume": "missing_runner_resume",
        "artifacts": "generic_core_configurable",
        "event_parser": "generic_jsonl_core",
        "cost_account": "generic_jsonl_core",
    }
    assert contract_rows["opencode"]["adapter_required"] is True
    capability_rows = {
        row["provider"]: row for row in payload["runtime_capability_matrix"]
    }
    assert capability_rows["claude"]["readiness"] == "ready"
    assert capability_rows["claude"]["blockers"] == []
    assert capability_rows["openai"]["readiness"] == "blocked"
    assert capability_rows["openai"]["recommended_runtime_mode"] == "generic_edit"
    assert "codex_cli" in capability_rows["openai"]["cli_runner_candidates"]
    assert capability_rows["openai"]["blockers"] == [
        "missing_full_autonomous_runtime",
        "live_provider_e2e_required",
        "transactional_recovery_required",
        "provider_reliability_incomplete",
        "provider_history_latest_failed",
    ]
    assert capability_rows["openai"]["warnings"] == [
        "direct_full_autonomous_blocked",
        "provider_history_unknown",
        "live_fault_probe_evidence_missing",
    ]
    assert capability_rows["openai"]["autonomous_policy_gate"] == "blocked"
    assert capability_rows["openai"]["autonomous_readiness_recommendation"] == (
        "provider_e2e_required"
    )
    assert capability_rows["openai"]["autonomous_readiness_recommendation_reasons"] == [
        "provider_reliability_incomplete",
        "latest_provider_e2e_failed",
        "history_missing",
        "live_fault_probe_missing",
    ]
    assert capability_rows["openai"]["autonomous_readiness_requirements"] == {
        "min_stable_runs": 3,
        "observed_recent_window": 0,
        "observed_consecutive_passes": 0,
        "history_stability_complete": False,
        "required_live_fault_cases": [
            "gateway_model_limitations",
            "unsupported_tools",
        ],
        "live_fault_covered_cases": [],
        "live_fault_missing_cases": [
            "gateway_model_limitations",
            "unsupported_tools",
        ],
        "live_fault_coverage_complete": False,
    }
    assert capability_rows["openai"]["autonomous_readiness_missing_requirements"] == [
        "provider_reliability",
        "latest_provider_e2e_pass",
        "stable_history_runs",
        "live_fault_case_coverage",
    ]
    selection_rows = payload["cli_runner_selection"]
    assert selection_rows["full_autonomous"]["selected_runner_ids"] == [
        "codex_cli",
        "claude_code",
        "zai_claude_code",
    ]
    assert "gemini_cli" in selection_rows["analysis_only"]["selected_runner_ids"]
    assert "aider" in selection_rows["generic_edit"]["selected_runner_ids"]
    assert "generic_edit" in payload["recommendations"]
    assert "provider_smoke" in payload["recommendations"]
    assert "generic_edit_resume_preflight" in payload["recommendations"]
    assert "external_mcp_smoke" in payload["recommendations"]
    assert "runner_router" in payload["recommendations"]
    assert "external_mcp_client" in payload["recommendations"]
    assert "provider_autonomous_readiness" in payload["recommendations"]
    policy_rows = {
        (row["phase"], row["provider"]): row for row in payload["runtime_policy_matrix"]
    }
    assert policy_rows[("planner", "openai")] == {
        "phase": "planner",
        "provider": "openai",
        "required_runtime_mode": "full_autonomous",
        "selected_runtime_mode": "blocked",
        "fallback_allowed": False,
        "fallback_modes": [],
        "requires_full_autonomous": True,
        "requires_cli_runner": True,
        "runner_candidates": [
            "codex_cli",
            "claude_code",
            "zai_claude_code",
        ],
        "policy": "must_use_full_runtime",
        "reason": "planner_requires_workspace_tools",
        "autonomous_readiness_required": True,
        "autonomous_policy_gate": "blocked",
        "autonomous_readiness_status": "blocked",
        "autonomous_readiness_recommendation": "provider_e2e_required",
        "autonomous_readiness_recommendation_reasons": [
            "provider_reliability_incomplete",
            "latest_provider_e2e_failed",
            "history_missing",
            "live_fault_probe_missing",
        ],
        "autonomous_readiness_blockers": [
            "provider_reliability_incomplete",
            "provider_history_latest_failed",
        ],
        "autonomous_readiness_warnings": [
            "provider_history_unknown",
            "live_fault_probe_evidence_missing",
        ],
        "autonomous_readiness_requirements": {
            "min_stable_runs": 3,
            "observed_recent_window": 0,
            "observed_consecutive_passes": 0,
            "history_stability_complete": False,
            "required_live_fault_cases": [
                "gateway_model_limitations",
                "unsupported_tools",
            ],
            "live_fault_covered_cases": [],
            "live_fault_missing_cases": [
                "gateway_model_limitations",
                "unsupported_tools",
            ],
            "live_fault_coverage_complete": False,
        },
        "autonomous_readiness_missing_requirements": [
            "provider_reliability",
            "latest_provider_e2e_pass",
            "stable_history_runs",
            "live_fault_case_coverage",
        ],
    }
    assert policy_rows[("coder", "openai")]["selected_runtime_mode"] == "generic_edit"
    assert policy_rows[("coder", "openai")]["policy"] == "provider_e2e_required"
    assert policy_rows[("coder", "openai")]["autonomous_policy_gate"] == "blocked"
    assert (
        policy_rows[("qa_reviewer", "openai")]["selected_runtime_mode"]
        == "analysis_only"
    )
    assert (
        policy_rows[("qa_fixer", "openai")]["selected_runtime_mode"] == "generic_edit"
    )
    mutation_rows = {
        (row["provider"], row["runtime_mode"]): row
        for row in payload["runtime_subagent_mutation_policy"]
    }
    assert mutation_rows[("openai", "generic_edit")] == {
        "provider": "openai",
        "runtime_mode": "generic_edit",
        "mutating_subagents_enabled": False,
        "status": "blocked",
        "transaction_boundary_required": True,
        "parent_approval_required": True,
        "merge_protocol": "read_only_until_transactional_merge",
        "required_gates": [
            "isolated_child_contexts",
            "transaction_boundaries",
            "conflict_aware_merge",
            "parent_approved_apply_abort",
            "child_artifacts",
        ],
        "satisfied_gates": ["isolated_child_contexts", "child_artifacts"],
        "missing_gates": [
            "transaction_boundaries",
            "conflict_aware_merge",
            "parent_approved_apply_abort",
        ],
        "reason": "mutating_subagents_require_transactional_merge",
    }
    eval_rows = {row["case_id"]: row for row in payload["runtime_eval_matrix"]}
    assert eval_rows["provider_e2e"]["runtime_mode"] == "provider_e2e"
    assert eval_rows["provider_e2e"]["required_for_full_autonomous"] is True
    assert eval_rows["provider_e2e"]["providers"] == [
        "openai",
        "google",
        "openrouter",
        "litellm",
        "zhipuai",
        "ollama",
    ]
    assert eval_rows["subagent_orchestrator"]["required_artifacts"] == [
        "runtime_subagents.json",
        "runtime_subagents__<child>.json",
    ]
    external_health = {
        row["server"]: row for row in payload["external_mcp_server_health"]
    }
    assert external_health["context7"]["status"] == "client_disabled"
    assert external_health["context7"]["command"] == "npx"
    assert external_health["context7"]["execution_supported"] is True
    assert external_health["context7"]["adapter_registered"] is True
    assert external_health["context7"]["adapter_name"] == "Context7"
    assert external_health["context7"]["adapter_transport"] == "stdio"
    assert external_health["context7"]["transport_supported"] is True
    assert external_health["context7"]["supported_transports"] == ["stdio", "http"]
    assert external_health["context7"]["executable_tools"] == []
    assert external_health["context7"]["executable_tool_count"] == 0
    assert external_health["graphiti"]["status"] == "missing_configuration"
    assert external_health["graphiti"]["adapter_registered"] is True
    assert external_health["graphiti"]["adapter_name"] == "Graphiti"
    assert external_health["graphiti"]["adapter_transport"] == "http"
    assert external_health["graphiti"]["adapter_exposed_server"] == "graphiti-memory"
    assert external_health["graphiti"]["transport_supported"] is True

    assert external_health["electron"]["status"] == "server_disabled"
    assert external_health["electron"]["adapter_registered"] is True
    assert external_health["electron"]["execution_supported"] is True
    assert external_health["puppeteer"]["status"] == "server_disabled"
    assert external_health["puppeteer"]["adapter_registered"] is True
    assert external_health["puppeteer"]["execution_supported"] is True
    mcp_rows = {
        (row["provider"], row["runtime_mode"]): row
        for row in payload["mcp_bridge_plan_matrix"]
    }
    claude_mcp = mcp_rows[("claude", "full_autonomous")]
    assert claude_mcp["status"] == "ready"
    assert claude_mcp["action_required"] == "none"
    openai_generic_mcp = mcp_rows[("openai", "generic_edit")]
    assert openai_generic_mcp["status"] == "partial"
    assert openai_generic_mcp["bridged_servers"] == ["auto-claude"]
    assert "context7" in openai_generic_mcp["external_bridge_required_servers"]
    assert openai_generic_mcp["external_bridge_adapter_missing_servers"] == []
    assert openai_generic_mcp["external_bridge_unsupported_transport_servers"] == []
    assert openai_generic_mcp["action_required"] == "configure_external_mcp_client"
    permission_rows = {
        row["server"]: row for row in payload["mcp_bridge_permission_matrix"]
    }
    assert permission_rows["auto-claude"] == {
        "server": "auto-claude",
        "display_name": "Auto Code local tools",
        "bridge_path": "local_bridge",
        "status": "enforced",
        "permission_enforced": True,
        "strict_allowlist_configured": False,
        "allowlist_source": "allow_all_default",
        "audit_required": True,
        "audit_artifact": ".auto-Codex/specs/<spec>/artifacts/mcp_bridge_audit.jsonl",
        "tool_count": None,
        "tool_policy_coverage": "dynamic",
        "permissions": ["dynamic_auto_claude_tool_policy"],
        "mutating_permissions": ["dynamic_mutating_tool_policy"],
        "required_gates": [
            "tool_policy_metadata",
            "permission_allowlist_check",
            "deny_before_execution",
            "audit_artifact",
            "mutating_tool_classification",
        ],
        "satisfied_gates": [
            "tool_policy_metadata",
            "permission_allowlist_check",
            "deny_before_execution",
            "audit_artifact",
            "mutating_tool_classification",
        ],
        "missing_gates": [],
        "reason": "local_tools_receive_runtime_policy_before_execution",
    }
    assert permission_rows["context7"]["status"] == "enforced"
    assert permission_rows["context7"]["permission_enforced"] is True
    assert permission_rows["context7"]["strict_allowlist_configured"] is False
    assert permission_rows["context7"]["allowlist_source"] == "allow_all_default"
    assert permission_rows["context7"]["permissions"] == ["read_external_docs"]
    assert permission_rows["context7"]["mutating_permissions"] == []
    assert permission_rows["graphiti"]["permissions"] == [
        "read_memory",
        "write_memory",
    ]
    assert permission_rows["graphiti"]["mutating_permissions"] == ["write_memory"]
    assert permission_rows["linear"]["mutating_permissions"] == ["write_linear"]
    fallback_rows = {
        (row["provider"], row["requested_mode"]): row
        for row in payload["runtime_fallback_matrix"]
    }
    openai_full = fallback_rows[("openai", "full_autonomous")]
    assert openai_full["fail_fast_selected_mode"] == "full_autonomous"
    assert openai_full["fallback_selected_mode"] == "generic_edit"
    assert openai_full["fallback_applied"] is True
    assert openai_full["compatible_fallbacks"] == [
        "generic_edit",
        "patch_proposal",
        "analysis_only",
    ]
    assert openai_full["runner_candidate_ids_by_mode"]["full_autonomous"] == [
        "codex_cli",
        "claude_code",
        "zai_claude_code",
    ]
    assert openai_full["selected_mode_runner_candidates"] == [
        "aider",
        "cursor_cli",
        "opencode",
        "goose",
        "amp",
        "qwen_code",
    ]
    assert fallback_rows[("claude", "full_autonomous")]["fallback_applied"] is False
    subagent_rows = {
        (row["provider"], row["runtime_mode"]): row
        for row in payload["runtime_subagent_matrix"]
    }
    claude_subagents = subagent_rows[("claude", "full_autonomous")]
    assert claude_subagents["strategy"] == "native"
    assert claude_subagents["available"] is True
    assert claude_subagents["merge_policy"] == "read_only"
    assert claude_subagents["max_attempts"] == 1
    codex_subagents = subagent_rows[("codex", "full_autonomous")]
    assert codex_subagents["strategy"] == "orchestrated"
    assert codex_subagents["available"] is True
    openai_full_subagents = subagent_rows[("openai", "full_autonomous")]
    assert openai_full_subagents["strategy"] == "unavailable"
    assert openai_full_subagents["available"] is False
    openai_generic_subagents = subagent_rows[("openai", "generic_edit")]
    assert openai_generic_subagents["strategy"] == "orchestrated"
    assert openai_generic_subagents["available"] is True


def test_runtime_modes_command_reports_provider_eval_history(
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    from cli.runtime_commands import handle_runtime_modes_command

    history_path = tmp_path / ".auto-Codex" / "provider-smoke-history.json"
    history_path.parent.mkdir(parents=True)
    history_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "providers": {
                    "openai": {
                        "total_runs": 4,
                        "passed_runs": 3,
                        "failed_runs": 1,
                        "recent_window": 4,
                        "recent_passed_runs": 3,
                        "last_status": "passed",
                        "last_runtime_mode": "provider_e2e",
                        "last_model": "gpt-4o",
                        "last_run_at": "2026-05-17T00:00:00Z",
                        "last_reliability_status": "complete",
                        "last_provider_e2e_status": "passed",
                        "e2e_case_count": 10,
                        "e2e_passed_case_count": 9,
                        "e2e_failed_case_count": 1,
                        "e2e_case_pass_rate_percent": 90,
                        "reliability_observed_case_count": 8,
                        "reliability_passed_case_count": 7,
                        "reliability_required_case_count": 8,
                        "reliability_case_pass_rate_percent": 88,
                        "live_fault_probe_covered_cases": [
                            "unsupported_tools",
                            "unsupported_tools",
                            "gateway_model_limitations",
                        ],
                        "cost_status": "recorded",
                        "cost_observed_run_count": 1,
                        "cost_total_input_tokens": 1000,
                        "cost_total_output_tokens": 500,
                        "cost_total_usd": 0.0075,
                        "cost_total_formatted": "$0.0075",
                        "cost_last_input_tokens": 1000,
                        "cost_last_output_tokens": 500,
                        "cost_last_usd": 0.0075,
                        "cost_last_formatted": "$0.0075",
                        "cost_pricing_model": "gpt-4o",
                        "cost_pricing_provider": "openai",
                    },
                    "google": {
                        "total_runs": 1,
                        "passed_runs": 0,
                        "failed_runs": 1,
                        "last_status": "failed",
                        "last_runtime_mode": "provider_e2e",
                        "last_model": "gemini-2.0-flash",
                        "last_run_at": "2026-05-17T00:01:00Z",
                        "last_reliability_status": "partial_coverage",
                        "last_provider_e2e_status": "failed",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    handle_runtime_modes_command(output_json=True)
    payload = json.loads(capsys.readouterr().out)
    history_rows = {row["case_id"]: row for row in payload["runtime_eval_history"]}
    provider_e2e = history_rows["provider_e2e"]

    assert provider_e2e["status"] == "partial"
    assert provider_e2e["history_path"] == ".auto-Codex/provider-smoke-history.json"
    assert provider_e2e["total_runs"] == 5
    assert provider_e2e["passed_runs"] == 3
    assert provider_e2e["failed_runs"] == 2
    assert provider_e2e["missing_providers"] == [
        "openrouter",
        "litellm",
        "zhipuai",
        "ollama",
    ]
    provider_rows = {row["provider"]: row for row in provider_e2e["providers"]}
    assert provider_rows["openai"]["status"] == "passed"
    assert provider_rows["openai"]["last_model"] == "gpt-4o"
    assert provider_rows["openai"]["pass_rate_percent"] == 75
    assert provider_rows["openai"]["recent_pass_rate_percent"] == 75
    assert provider_rows["openai"]["e2e_case_pass_rate_percent"] == 90
    assert provider_rows["openai"]["reliability_case_pass_rate_percent"] == 88
    assert provider_rows["openai"]["observed_live_fault_case_count"] == 2
    assert provider_rows["openai"]["required_live_fault_case_count"] == 2
    assert provider_rows["openai"]["live_fault_probe_case_coverage_percent"] == 100
    assert provider_rows["google"]["status"] == "failed"
    assert provider_rows["openrouter"]["status"] == "not_observed"
    comparative_rows = {
        row["provider"]: row for row in payload["runtime_comparative_eval_matrix"]
    }
    assert comparative_rows["openai"]["quality_status"] == "passed"
    assert comparative_rows["openai"]["quality_score"] == 90
    assert comparative_rows["openai"]["quality_score_source"] == (
        "provider_e2e_case_pass_rate"
    )
    assert comparative_rows["openai"]["stability_score"] == 75
    assert comparative_rows["openai"]["safety_score"] == 88
    assert comparative_rows["openai"]["safety_score_source"] == (
        "provider_reliability_and_live_fault_coverage"
    )
    assert comparative_rows["openai"]["cost_status"] == "recorded"
    assert comparative_rows["openai"]["cost_pricing_model"] == "gpt-4o"
    assert comparative_rows["openai"]["cost_actual_usd"] == pytest.approx(0.0075)
    assert comparative_rows["openai"]["cost_actual_formatted"] == "$0.0075"
    assert comparative_rows["openai"]["cost_actual_input_tokens"] == 1000
    assert comparative_rows["openai"]["cost_actual_output_tokens"] == 500
    assert comparative_rows["openai"]["cost_observed_run_count"] == 1
    assert comparative_rows["openai"]["evidence_source"] == (
        ".auto-Codex/provider-smoke-history.json"
    )
    assert comparative_rows["google"]["quality_status"] == "failed"
    assert comparative_rows["google"]["quality_score"] == 0
    assert comparative_rows["google"]["cost_status"] == "estimated"
    assert comparative_rows["ollama"]["quality_status"] == "not_observed"
    assert comparative_rows["ollama"]["quality_score"] is None
    assert comparative_rows["ollama"]["cost_status"] == "not_recorded"
    assert comparative_rows["claude"]["safety_status"] == "native_runtime_policy"


def test_runtime_provider_history_logs_corrupt_artifact(
    tmp_path: Path,
    caplog,
):
    from cli.runtime_commands import _runtime_provider_history_stats_by_name

    history_path = tmp_path / ".auto-Codex" / "provider-smoke-history.json"
    history_path.parent.mkdir(parents=True)
    history_path.write_text("{", encoding="utf-8")

    with caplog.at_level(logging.DEBUG, logger="cli.runtime_commands"):
        assert _runtime_provider_history_stats_by_name(project_dir=tmp_path) == {}

    assert "Could not load provider history from" in caplog.text


def test_runtime_modes_policy_gate_uses_provider_autonomous_readiness_history(
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    from cli.runtime_commands import (
        build_runtime_modes_payload,
        format_runtime_modes_text,
        handle_runtime_modes_command,
    )

    history_path = tmp_path / ".auto-Codex" / "provider-smoke-history.json"
    history_path.parent.mkdir(parents=True)
    history_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "providers": {
                    "openai": {
                        "total_runs": 3,
                        "passed_runs": 3,
                        "failed_runs": 0,
                        "last_status": "passed",
                        "last_runtime_mode": "provider_e2e",
                        "last_run_at": "2026-05-18T00:00:00Z",
                        "last_reliability_status": "complete",
                        "last_provider_e2e_status": "passed",
                        "last_live_fault_probe_status": "passed",
                        "live_fault_probe_enabled_runs": 3,
                        "live_fault_probe_passed_runs": 3,
                        "live_fault_probe_covered_cases": [
                            "gateway_model_limitations",
                            "unsupported_tools",
                        ],
                        "trend": "provider_history_stable",
                    },
                    "google": {
                        "total_runs": 1,
                        "passed_runs": 1,
                        "failed_runs": 0,
                        "last_status": "passed",
                        "last_runtime_mode": "provider_e2e",
                        "last_run_at": "2026-05-18T00:01:00Z",
                        "last_reliability_status": "complete",
                        "last_provider_e2e_status": "passed",
                        "last_live_fault_probe_status": None,
                        "trend": "provider_history_warming_up",
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    handle_runtime_modes_command(output_json=True)
    payload = json.loads(capsys.readouterr().out)
    capability_rows = {
        row["provider"]: row for row in payload["runtime_capability_matrix"]
    }
    policy_rows = {
        (row["phase"], row["provider"]): row for row in payload["runtime_policy_matrix"]
    }

    assert capability_rows["openai"]["readiness"] == "full_autonomous_candidate"
    assert capability_rows["openai"]["autonomous_policy_gate"] == "passed"
    assert capability_rows["openai"]["autonomous_readiness_recommendation"] == (
        "api_runtime_full_autonomous_candidate"
    )
    assert capability_rows["openai"]["autonomous_readiness_recommendation_reasons"] == [
        "full_autonomy_candidate"
    ]
    assert capability_rows["openai"]["autonomous_readiness_blockers"] == []
    assert capability_rows["openai"]["autonomous_readiness_warnings"] == []
    assert capability_rows["openai"]["autonomous_readiness_evidence"] == [
        "provider_e2e_passed",
        "provider_reliability_complete",
        "provider_history_stable",
        "live_fault_probes_passed",
    ]
    assert capability_rows["openai"]["autonomous_readiness_requirements"] == {
        "min_stable_runs": 3,
        "observed_recent_window": 3,
        "observed_consecutive_passes": 3,
        "history_stability_complete": True,
        "required_live_fault_cases": [
            "gateway_model_limitations",
            "unsupported_tools",
        ],
        "live_fault_covered_cases": [
            "gateway_model_limitations",
            "unsupported_tools",
        ],
        "live_fault_missing_cases": [],
        "live_fault_coverage_complete": True,
    }
    assert capability_rows["openai"]["autonomous_readiness_missing_requirements"] == []
    assert policy_rows[("coder", "openai")]["autonomous_policy_gate"] == "passed"
    assert policy_rows[("coder", "openai")]["policy"] == "prefer_generic_edit"

    assert capability_rows["google"]["readiness"] == "needs_live_fault_evidence"
    assert capability_rows["google"]["autonomous_policy_gate"] == "blocked"
    assert capability_rows["google"]["autonomous_readiness_recommendation"] == (
        "limited_autonomous_until_live_faults"
    )
    assert capability_rows["google"]["autonomous_readiness_recommendation_reasons"] == [
        "history_warming_up",
        "live_fault_probe_missing",
    ]
    assert capability_rows["google"]["autonomous_readiness_warnings"] == [
        "provider_history_warming_up",
        "live_fault_probe_evidence_missing",
    ]
    assert policy_rows[("coder", "google")]["policy"] == (
        "limited_autonomous_until_live_faults"
    )
    assert policy_rows[("coder", "google")]["autonomous_policy_gate"] == "blocked"

    text_payload = build_runtime_modes_payload(project_dir=tmp_path)
    text_output = format_runtime_modes_text(text_payload)
    assert "api_runtime_full_autonomous_candidate" in text_output
    assert "limited_autonomous_until_live_faults" in text_output
    assert "--provider-smoke-runtime provider_e2e" in text_output


def test_runtime_provider_readiness_decouples_e2e_from_aggregate_status():
    from cli.runtime_commands import _runtime_provider_autonomous_readiness_from_history

    readiness = _runtime_provider_autonomous_readiness_from_history(
        "openai",
        {
            "total_runs": 3,
            "passed_runs": 2,
            "failed_runs": 1,
            "last_status": "failed",
            "last_reliability_status": "complete",
            "last_provider_e2e_status": "passed",
            "last_live_fault_probe_status": "passed",
            "live_fault_probe_covered_cases": [
                "unsupported_tools",
                "unsupported_tools",
                "gateway_model_limitations",
            ],
            "trend": "provider_history_stable",
            "recent_window": 3,
            "consecutive_passes": 3,
        },
    )

    assert "provider_e2e_passed" in readiness["evidence"]
    assert "provider_e2e_failed" not in readiness["blockers"]
    assert readiness["requirements"]["live_fault_covered_cases"] == [
        "gateway_model_limitations",
        "unsupported_tools",
    ]
    assert readiness["requirements"]["live_fault_coverage_complete"] is True
    assert readiness["missing_requirements"] == ["latest_provider_e2e_pass"]
    assert readiness["blockers"] == ["provider_history_latest_failed"]


def test_runtime_modes_policy_gate_requires_stability_counts_and_live_fault_coverage(
    tmp_path: Path,
    monkeypatch,
    capsys,
):
    from cli.runtime_commands import handle_runtime_modes_command

    history_path = tmp_path / ".auto-Codex" / "provider-smoke-history.json"
    history_path.parent.mkdir(parents=True)
    history_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "providers": {
                    "openai": {
                        "total_runs": 2,
                        "passed_runs": 2,
                        "failed_runs": 0,
                        "last_status": "passed",
                        "last_runtime_mode": "provider_e2e",
                        "last_run_at": "2026-05-18T00:00:00Z",
                        "last_reliability_status": "complete",
                        "last_provider_e2e_status": "passed",
                        "last_live_fault_probe_status": "passed",
                        "live_fault_probe_enabled_runs": 2,
                        "live_fault_probe_passed_runs": 2,
                        "live_fault_probe_covered_cases": [
                            "gateway_model_limitations",
                            "unsupported_tools",
                        ],
                        "trend": "provider_history_stable",
                        "recent_window": 2,
                        "consecutive_passes": 2,
                    },
                    "google": {
                        "total_runs": 3,
                        "passed_runs": 3,
                        "failed_runs": 0,
                        "last_status": "passed",
                        "last_runtime_mode": "provider_e2e",
                        "last_run_at": "2026-05-18T00:01:00Z",
                        "last_reliability_status": "complete",
                        "last_provider_e2e_status": "passed",
                        "last_live_fault_probe_status": "passed",
                        "live_fault_probe_enabled_runs": 3,
                        "live_fault_probe_passed_runs": 3,
                        "live_fault_probe_covered_cases": ["unsupported_tools"],
                        "trend": "provider_history_stable",
                        "recent_window": 3,
                        "consecutive_passes": 3,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    handle_runtime_modes_command(output_json=True)
    payload = json.loads(capsys.readouterr().out)
    capability_rows = {
        row["provider"]: row for row in payload["runtime_capability_matrix"]
    }
    policy_rows = {
        (row["phase"], row["provider"]): row for row in payload["runtime_policy_matrix"]
    }

    assert capability_rows["openai"]["readiness"] == "warming_up"
    assert capability_rows["openai"]["autonomous_policy_gate"] == "blocked"
    assert capability_rows["openai"]["autonomous_readiness_warnings"] == [
        "provider_history_insufficient_runs"
    ]
    assert capability_rows["openai"]["autonomous_readiness_recommendation_reasons"] == [
        "history_insufficient_runs"
    ]
    assert capability_rows["openai"]["autonomous_readiness_next_actions"] == [
        "collect_provider_history_runs"
    ]
    assert capability_rows["openai"]["autonomous_readiness_requirements"] == {
        "min_stable_runs": 3,
        "observed_recent_window": 2,
        "observed_consecutive_passes": 2,
        "history_stability_complete": False,
        "required_live_fault_cases": [
            "gateway_model_limitations",
            "unsupported_tools",
        ],
        "live_fault_covered_cases": [
            "gateway_model_limitations",
            "unsupported_tools",
        ],
        "live_fault_missing_cases": [],
        "live_fault_coverage_complete": True,
    }
    assert capability_rows["openai"]["autonomous_readiness_missing_requirements"] == [
        "stable_history_runs"
    ]
    assert policy_rows[("coder", "openai")]["policy"] == (
        "limited_autonomous_until_evidence_stable"
    )

    assert capability_rows["google"]["readiness"] == "needs_live_fault_evidence"
    assert capability_rows["google"]["autonomous_policy_gate"] == "blocked"
    assert capability_rows["google"]["autonomous_readiness_warnings"] == [
        "live_fault_probe_coverage_incomplete"
    ]
    assert capability_rows["google"]["autonomous_readiness_recommendation_reasons"] == [
        "live_fault_coverage_incomplete"
    ]
    assert capability_rows["google"]["autonomous_readiness_next_actions"] == [
        "enable_live_fault_probes"
    ]
    assert capability_rows["google"]["autonomous_readiness_requirements"] == {
        "min_stable_runs": 3,
        "observed_recent_window": 3,
        "observed_consecutive_passes": 3,
        "history_stability_complete": True,
        "required_live_fault_cases": [
            "gateway_model_limitations",
            "unsupported_tools",
        ],
        "live_fault_covered_cases": ["unsupported_tools"],
        "live_fault_missing_cases": ["gateway_model_limitations"],
        "live_fault_coverage_complete": False,
    }
    assert capability_rows["google"]["autonomous_readiness_missing_requirements"] == [
        "live_fault_case_coverage"
    ]
    assert policy_rows[("coder", "google")]["policy"] == (
        "limited_autonomous_until_live_faults"
    )


def test_runtime_modes_command_marks_context7_available_when_external_client_enabled(
    monkeypatch,
):
    from agents.runtime import EXTERNAL_MCP_CLIENT_ENV
    from cli.runtime_commands import build_runtime_modes_payload

    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")

    payload = build_runtime_modes_payload()
    mcp_rows = {
        (row["provider"], row["runtime_mode"]): row
        for row in payload["mcp_bridge_plan_matrix"]
    }
    openai_generic_mcp = mcp_rows[("openai", "generic_edit")]

    assert "context7" in openai_generic_mcp["available_servers"]
    assert "context7" not in openai_generic_mcp["external_bridge_required_servers"]
    assert openai_generic_mcp["external_bridged_servers"] == ["context7"]
    assert openai_generic_mcp["bridged_servers"] == ["auto-claude", "context7"]
    assert openai_generic_mcp["executable_external_tools"] == [
        "mcp__context7__resolve-library-id",
        "mcp__context7__get-library-docs",
    ]


def test_mcp_bridge_permission_matrix_reports_strict_allowlist_and_custom_server(
    monkeypatch,
):
    from agents.runtime import MCP_ALLOWED_PERMISSIONS_ENV
    from cli.runtime_commands import build_mcp_bridge_permission_matrix

    monkeypatch.setenv(MCP_ALLOWED_PERMISSIONS_ENV, "read_memory,call_custom_mcp")
    project_mcp_config = {
        "CUSTOM_MCP_SERVERS": [
            {
                "id": "my-docs",
                "name": "My Docs",
                "type": "http",
                "url": "http://localhost:8765/mcp",
                "tools": [
                    {
                        "name": "search",
                        "description": "Search custom docs.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                        },
                    }
                ],
            }
        ],
    }

    rows = {
        row["server"]: row
        for row in build_mcp_bridge_permission_matrix(
            project_mcp_config=project_mcp_config,
        )
    }

    assert rows["graphiti"]["strict_allowlist_configured"] is True
    assert rows["graphiti"]["allowlist_source"] == MCP_ALLOWED_PERMISSIONS_ENV
    assert rows["graphiti"]["allowed_permissions"] == [
        "call_custom_mcp",
        "read_memory",
    ]
    assert rows["my-docs"]["display_name"] == "My Docs"
    assert rows["my-docs"]["bridge_path"] == "external_bridge"
    assert rows["my-docs"]["tool_count"] == 2
    assert rows["my-docs"]["tool_policy_coverage"] == "static"
    assert rows["my-docs"]["permissions"] == ["call_custom_mcp"]
    assert rows["my-docs"]["mutating_permissions"] == ["call_custom_mcp"]
    assert rows["my-docs"]["missing_gates"] == []
    assert rows["my-docs"]["status"] == "enforced"


def test_runtime_modes_command_marks_browser_mcp_available_when_enabled(
    monkeypatch,
):
    from agents.runtime import EXTERNAL_MCP_CLIENT_ENV
    from cli.runtime_commands import build_runtime_modes_payload

    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")
    monkeypatch.setenv("PUPPETEER_MCP_ENABLED", "true")

    payload = build_runtime_modes_payload()
    external_health = {
        row["server"]: row for row in payload["external_mcp_server_health"]
    }
    mcp_rows = {
        (row["provider"], row["runtime_mode"]): row
        for row in payload["mcp_bridge_plan_matrix"]
    }
    openai_generic_mcp = mcp_rows[("openai", "generic_edit")]

    assert external_health["puppeteer"]["status"] == "ready_to_connect"
    assert "puppeteer_navigate" in external_health["puppeteer"]["executable_tools"]
    assert "puppeteer" in openai_generic_mcp["available_servers"]
    assert "puppeteer" in openai_generic_mcp["external_bridged_servers"]
    assert (
        "mcp__puppeteer__puppeteer_navigate"
        in openai_generic_mcp["executable_external_tools"]
    )


def test_runtime_modes_command_marks_configured_graphiti_as_external_bridged(
    monkeypatch,
):
    from agents.runtime import EXTERNAL_MCP_CLIENT_ENV
    from cli.runtime_commands import build_runtime_modes_payload

    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")
    monkeypatch.setenv("GRAPHITI_MCP_URL", "http://localhost:8000/mcp/")

    payload = build_runtime_modes_payload()
    external_health = {
        row["server"]: row for row in payload["external_mcp_server_health"]
    }
    mcp_rows = {
        (row["provider"], row["runtime_mode"]): row
        for row in payload["mcp_bridge_plan_matrix"]
    }
    openai_generic_mcp = mcp_rows[("openai", "generic_edit")]

    assert external_health["graphiti"]["status"] == "ready_to_connect"
    assert external_health["graphiti"]["configured"] is True
    assert external_health["graphiti"]["adapter_registered"] is True
    assert external_health["graphiti"]["adapter_transport"] == "http"
    assert "graphiti" in openai_generic_mcp["external_bridged_servers"]
    assert (
        "graphiti" not in openai_generic_mcp["external_bridge_adapter_missing_servers"]
    )
    assert (
        "mcp__graphiti-memory__search_nodes"
        in openai_generic_mcp["executable_external_tools"]
    )


def test_generic_edit_resume_preflight_command_outputs_json(
    capsys,
    monkeypatch,
    tmp_path,
):
    from cli.runtime_commands import (
        generic_edit_resume_preflight_has_failures,
        handle_generic_edit_resume_preflight_command,
    )

    checkpoint_path = (
        tmp_path / "spec-001" / "artifacts" / "generic_edit_recovery_checkpoint.json"
    )

    def fake_inspect_generic_edit_resume_artifacts(
        *,
        checkpoint_path,
        spec_dir,
        project_dir,
    ):
        assert checkpoint_path.name == "generic_edit_recovery_checkpoint.json"
        assert spec_dir == tmp_path / "spec-001"
        assert project_dir == tmp_path
        return {
            "runtime": "generic_edit",
            "status": "blocked",
            "requested_path": str(checkpoint_path),
            "resume_artifact_health": {
                "status": "blocked",
                "artifact": "trace",
                "reason": "missing",
            },
            "artifacts": {},
            "blockers": [],
        }

    monkeypatch.setattr(
        "cli.runtime_commands.inspect_generic_edit_resume_artifacts",
        fake_inspect_generic_edit_resume_artifacts,
    )

    payload = handle_generic_edit_resume_preflight_command(
        checkpoint_path=checkpoint_path,
        project_dir=tmp_path,
        output_json=True,
    )
    parsed = json.loads(capsys.readouterr().out)

    assert payload["status"] == "blocked"
    assert parsed["resume_artifact_health"]["reason"] == "missing"
    assert generic_edit_resume_preflight_has_failures(payload) is True


def test_generic_edit_resume_preflight_command_formats_blocker_details():
    from cli.runtime_commands import format_generic_edit_resume_preflight_text

    text = format_generic_edit_resume_preflight_text(
        {
            "runtime": "generic_edit",
            "status": "blocked",
            "requested_path": "/workspace/spec/artifacts/generic_edit_recovery_checkpoint.json",
            "resume_artifact_health": {
                "status": "blocked",
                "artifact": "mutation_snapshots",
                "reason": "checkpoint_mismatch",
                "path": "/workspace/spec/artifacts/generic_edit_mutation_snapshots.json",
                "artifact_name": "mutation_snapshot_artifact",
                "owner_artifact": "recovery_checkpoint",
                "missing_snapshot_ids": ["mutation-missing"],
            },
            "artifacts": {
                "recovery_checkpoint": {
                    "status": "ready",
                    "path": "/workspace/spec/artifacts/generic_edit_recovery_checkpoint.json",
                }
            },
        }
    )

    assert "artifact: mutation_snapshots" in text
    assert "reason: checkpoint_mismatch" in text
    assert "artifact_name: mutation_snapshot_artifact" in text
    assert "owner_artifact: recovery_checkpoint" in text
    assert "missing_snapshot_ids: mutation-missing" in text


def test_generic_edit_resume_preflight_command_formats_numeric_blocker_details():
    from cli.runtime_commands import format_generic_edit_resume_preflight_text

    text = format_generic_edit_resume_preflight_text(
        {
            "runtime": "generic_edit",
            "status": "blocked",
            "requested_path": "/workspace/spec/artifacts/generic_edit_recovery_checkpoint.json",
            "resume_artifact_health": {
                "status": "blocked",
                "artifact": "events",
                "reason": "corrupt_json",
                "path": "/workspace/spec/artifacts/generic_edit_events.jsonl",
                "line_number": 7,
                "expected_count": 1,
                "actual_count": 2,
            },
            "artifacts": {},
        }
    )

    assert "line_number: 7" in text
    assert "expected_count: 1" in text
    assert "actual_count: 2" in text


def test_external_mcp_smoke_command_outputs_json(
    capsys,
    monkeypatch,
    tmp_path,
):
    from cli.runtime_commands import (
        external_mcp_smoke_has_failures,
        handle_external_mcp_smoke_command,
    )

    async def fake_check_external_mcp_contracts(
        *,
        requested_servers,
        project_dir,
        project_mcp_config=None,
        environment=None,
    ):
        assert "context7" in requested_servers
        assert project_dir == tmp_path
        assert project_mcp_config is None
        assert environment is None
        return [
            {
                "server": "graphiti",
                "ok": True,
                "status": "ok",
                "reason": "Adapter tools match.",
                "transport": "http",
                "adapter_tools": ["search_nodes"],
                "server_tools": ["search_nodes"],
                "adapter_tools_missing_on_server": [],
                "server_tools_missing_in_adapter": [],
                "error": None,
            },
            {
                "server": "context7",
                "ok": False,
                "status": "skipped",
                "reason": "External MCP client bridge is disabled.",
                "transport": "stdio",
                "adapter_tools": ["resolve-library-id"],
                "server_tools": [],
                "adapter_tools_missing_on_server": [],
                "server_tools_missing_in_adapter": [],
                "error": None,
            },
            {
                "server": "linear",
                "ok": False,
                "status": "error",
                "reason": "External MCP tools/list failed.",
                "transport": "http",
                "adapter_tools": ["list_teams"],
                "server_tools": [],
                "adapter_tools_missing_on_server": [],
                "server_tools_missing_in_adapter": [],
                "error": "connection refused",
            },
        ]

    monkeypatch.setattr(
        "cli.runtime_commands.check_external_mcp_contracts",
        fake_check_external_mcp_contracts,
    )

    payload = handle_external_mcp_smoke_command(
        project_dir=tmp_path,
        output_json=True,
    )
    output = capsys.readouterr().out
    parsed = json.loads(output)

    assert parsed == payload
    assert parsed["summary"] == {
        "total": 3,
        "ok": 1,
        "skipped": 1,
        "failed": 1,
    }
    assert external_mcp_smoke_has_failures(parsed) is True


def test_external_mcp_smoke_includes_project_custom_servers(
    capsys,
    monkeypatch,
    tmp_path,
):
    from cli.runtime_commands import handle_external_mcp_smoke_command

    custom_servers = [
        {
            "id": "my-docs",
            "name": "My Docs",
            "type": "http",
            "url": "https://docs.example.test/mcp",
        }
    ]
    env_dir = tmp_path / ".auto-claude"
    env_dir.mkdir()
    (env_dir / ".env").write_text(
        f"CUSTOM_MCP_SERVERS={json.dumps(custom_servers)}\n",
        encoding="utf-8",
    )

    async def fake_check_external_mcp_contracts(
        *,
        requested_servers,
        project_dir,
        project_mcp_config=None,
        environment=None,
    ):
        assert "context7" in requested_servers
        assert "my-docs" in requested_servers
        assert project_dir == tmp_path
        assert project_mcp_config["CUSTOM_MCP_SERVERS"][0]["id"] == "my-docs"
        assert environment is None
        return []

    monkeypatch.setattr(
        "cli.runtime_commands.check_external_mcp_contracts",
        fake_check_external_mcp_contracts,
    )

    payload = handle_external_mcp_smoke_command(
        project_dir=tmp_path,
        output_json=True,
    )
    parsed = json.loads(capsys.readouterr().out)

    assert parsed == payload
    assert parsed["summary"] == {"total": 0, "ok": 0, "skipped": 0, "failed": 0}


def test_external_mcp_smoke_syncs_custom_tool_schemas(
    capsys,
    monkeypatch,
    tmp_path,
):
    from agents.runtime import EXTERNAL_MCP_CLIENT_ENV
    from cli.runtime_commands import handle_external_mcp_smoke_command
    from core.client import load_project_mcp_config

    custom_servers = [
        {
            "id": "my-docs",
            "name": "My Docs",
            "type": "http",
            "url": "https://docs.example.test/mcp",
            "description": "Private docs.",
        }
    ]
    env_dir = tmp_path / ".auto-claude"
    env_dir.mkdir()
    (env_dir / ".env").write_text(
        f"CUSTOM_MCP_SERVERS={json.dumps(custom_servers)}\n",
        encoding="utf-8",
    )

    async def fake_check_external_mcp_contracts(
        *,
        requested_servers,
        project_dir,
        project_mcp_config=None,
        environment=None,
    ):
        assert "my-docs" in requested_servers
        return [
            {
                "server": "my-docs",
                "ok": True,
                "status": "server_has_extra_tools",
                "reason": "Live MCP server returned extra tools.",
                "transport": "http",
                "adapter_tools": ["call_tool"],
                "server_tools": ["search_docs"],
                "adapter_tools_missing_on_server": [],
                "server_tools_missing_in_adapter": ["search_docs"],
                "error": None,
            }
        ]

    async def fake_discover_external_mcp_tools(
        *,
        health,
        project_dir,
        project_mcp_config=None,
        environment=None,
    ):
        assert health.server == "my-docs"
        assert project_dir == tmp_path
        return {
            "tools": [
                {
                    "name": "search_docs",
                    "description": "Search private docs.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query.",
                            }
                        },
                        "required": ["query"],
                    },
                },
                {
                    "name": "status",
                    "description": "Read server status.",
                },
            ]
        }

    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")
    monkeypatch.setattr(
        "cli.runtime_commands.check_external_mcp_contracts",
        fake_check_external_mcp_contracts,
    )
    monkeypatch.setattr(
        "cli.runtime_commands.discover_external_mcp_tools",
        fake_discover_external_mcp_tools,
    )

    payload = handle_external_mcp_smoke_command(
        project_dir=tmp_path,
        output_json=True,
        sync_custom_tools=True,
    )
    parsed = json.loads(capsys.readouterr().out)
    saved_servers = load_project_mcp_config(tmp_path)["CUSTOM_MCP_SERVERS"]

    assert parsed == payload
    assert parsed["custom_mcp_tool_schema_sync"] == {
        "updated_servers": ["my-docs"],
        "skipped_servers": [],
        "failed_servers": [],
        "server_results": [
            {
                "server": "my-docs",
                "status": "updated",
                "reason": "tools_synced",
                "tool_count": 2,
            }
        ],
    }
    assert saved_servers[0]["id"] == "my-docs"
    assert saved_servers[0]["description"] == "Private docs."
    assert saved_servers[0]["tools"] == [
        {
            "name": "search_docs",
            "description": "Search private docs.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query.",
                    }
                },
                "required": ["query"],
            },
        },
        {
            "name": "status",
            "description": "Read server status.",
        },
    ]


def test_external_mcp_smoke_syncs_custom_tool_schemas_from_mapping(
    capsys,
    monkeypatch,
    tmp_path,
):
    from agents.runtime import EXTERNAL_MCP_CLIENT_ENV
    from cli.runtime_commands import handle_external_mcp_smoke_command
    from core.client import load_project_mcp_config

    custom_servers = {
        "my-docs": {
            "name": "My Docs",
            "type": "http",
            "url": "https://docs.example.test/mcp",
        }
    }
    env_dir = tmp_path / ".auto-claude"
    env_dir.mkdir()
    (env_dir / ".env").write_text(
        f"CUSTOM_MCP_SERVERS={json.dumps(custom_servers)}\n",
        encoding="utf-8",
    )

    async def fake_check_external_mcp_contracts(
        *,
        requested_servers,
        project_dir,
        project_mcp_config=None,
        environment=None,
    ):
        assert "my-docs" in requested_servers
        return []

    async def fake_discover_external_mcp_tools(
        *,
        health,
        project_dir,
        project_mcp_config=None,
        environment=None,
    ):
        assert health.server == "my-docs"
        return {"tools": [{"name": "search_docs"}]}

    monkeypatch.setenv(EXTERNAL_MCP_CLIENT_ENV, "true")
    monkeypatch.setattr(
        "cli.runtime_commands.check_external_mcp_contracts",
        fake_check_external_mcp_contracts,
    )
    monkeypatch.setattr(
        "cli.runtime_commands.discover_external_mcp_tools",
        fake_discover_external_mcp_tools,
    )

    payload = handle_external_mcp_smoke_command(
        project_dir=tmp_path,
        output_json=True,
        sync_custom_tools=True,
    )
    parsed = json.loads(capsys.readouterr().out)
    saved_servers = load_project_mcp_config(tmp_path)["CUSTOM_MCP_SERVERS"]

    assert parsed == payload
    assert parsed["custom_mcp_tool_schema_sync"]["updated_servers"] == ["my-docs"]
    assert saved_servers[0]["id"] == "my-docs"
    assert saved_servers[0]["tools"] == [{"name": "search_docs"}]


def test_normalize_mcp_tools_for_persistence_normalizes_tool_schemas():
    from cli.runtime_commands import normalize_mcp_tools_for_persistence

    assert normalize_mcp_tools_for_persistence(
        {
            "tools": [
                {
                    "name": "search_docs",
                    "description": "  Search docs.  ",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                        },
                        "required": ("query",),
                    },
                },
                {
                    "name": "raw_status",
                    "inputSchema": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                {
                    "name": "search_docs",
                    "description": "Duplicate should be skipped.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "duplicate": {"type": "boolean"},
                        },
                    },
                },
            ]
        }
    ) == [
        {
            "name": "search_docs",
            "description": "Search docs.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "raw_status",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    ]


def test_load_project_mcp_config_warns_when_import_unavailable(
    tmp_path,
    monkeypatch,
    caplog,
):
    from cli.runtime_commands import load_project_mcp_config_for_runtime_commands

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "core.client" and "load_project_mcp_config" in fromlist:
            raise ImportError("missing optional sdk")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with caplog.at_level(logging.WARNING, logger="cli.runtime_commands"):
        config = load_project_mcp_config_for_runtime_commands(tmp_path)

    assert config == {}
    assert "could not import load_project_mcp_config" in caplog.text
    assert "missing optional sdk" in caplog.text


def test_load_project_mcp_config_warns_on_non_dict_result(
    tmp_path,
    monkeypatch,
    caplog,
):
    import core.client
    from cli.runtime_commands import load_project_mcp_config_for_runtime_commands

    monkeypatch.setattr(core.client, "load_project_mcp_config", lambda _project_dir: [])

    with caplog.at_level(logging.WARNING, logger="cli.runtime_commands"):
        config = load_project_mcp_config_for_runtime_commands(tmp_path)

    assert config == {}
    assert "ignored non-dict load_project_mcp_config result" in caplog.text
    assert "list" in caplog.text


def test_external_mcp_smoke_failure_detection_ignores_skipped():
    from cli.runtime_commands import external_mcp_smoke_has_failures

    assert (
        external_mcp_smoke_has_failures(
            {"summary": {"total": 5, "ok": 0, "skipped": 5, "failed": 0}}
        )
        is False
    )


def test_external_mcp_smoke_command_outputs_text(capsys, monkeypatch, tmp_path):
    from cli.runtime_commands import handle_external_mcp_smoke_command

    async def fake_check_external_mcp_contracts(
        *,
        requested_servers,
        project_dir,
        project_mcp_config=None,
        environment=None,
    ):
        assert project_mcp_config is None
        return [
            {
                "server": "graphiti",
                "ok": True,
                "status": "server_has_extra_tools",
                "reason": "Live MCP server returned extra tools.",
                "transport": "http",
                "adapter_tools": ["search_nodes"],
                "server_tools": ["search_nodes", "new_tool"],
                "adapter_tools_missing_on_server": [],
                "server_tools_missing_in_adapter": ["new_tool"],
                "error": None,
            }
        ]

    monkeypatch.setattr(
        "cli.runtime_commands.check_external_mcp_contracts",
        fake_check_external_mcp_contracts,
    )

    payload = handle_external_mcp_smoke_command(
        project_dir=tmp_path,
        output_json=False,
    )
    output = capsys.readouterr().out

    assert "External MCP Contract Smoke" in output
    assert "graphiti" in output
    assert "server_has_extra_tools" in output
    assert "search_nodes" in output
    assert payload["summary"]["ok"] == 1


def test_cli_runner_selection_filters_runtime_mode():
    from agents.runtime.cli_profiles import select_cli_runner_profiles

    analysis_selection = select_cli_runner_profiles(runtime_mode="analysis-only")
    assert analysis_selection.selected_runner_ids == (
        "gemini_cli",
        "coderabbit_cli",
        "github_copilot_cli",
        "opencode",
        "goose",
        "qwen_code",
        "deepv_code",
        "generic_cli_pool",
    )

    full_autonomous_selection = select_cli_runner_profiles(
        runtime_mode="full_autonomous",
    )
    assert full_autonomous_selection.selected_runner_ids == (
        "codex_cli",
        "claude_code",
        "zai_claude_code",
    )


def test_cli_runner_selection_filters_capability():
    from agents.runtime.cli_profiles import select_cli_runner_profiles

    selection = select_cli_runner_profiles(required_capabilities=("review_only",))

    assert selection.selected_runner_ids == ("coderabbit_cli",)
    rejected_reasons = {
        rejection.runner_id: rejection.reasons
        for rejection in selection.rejected_profiles
    }
    assert rejected_reasons["codex_cli"] == ("missing_capability:review_only",)

    anthropic_selection = select_cli_runner_profiles(
        required_capabilities=("anthropic_compatible",),
    )
    assert anthropic_selection.selected_runner_ids == ("zai_claude_code",)

    zai_selection = select_cli_runner_profiles(
        required_capabilities=("zai_compatible",),
    )
    assert zai_selection.selected_runner_ids == ("zai_claude_code",)


def test_cli_runner_selection_can_require_installed_runner(monkeypatch):
    from agents.runtime import cli_profiles

    def fake_find_executable(candidate: str) -> str | None:
        if candidate == "gemini":
            return "/usr/local/bin/gemini"
        return None

    monkeypatch.setattr(cli_profiles, "find_executable", fake_find_executable)

    selection = cli_profiles.select_cli_runner_profiles(
        runtime_mode="analysis_only",
        installed_only=True,
    )

    assert selection.selected_runner_ids == ("gemini_cli",)
    rejected_reasons = {
        rejection.runner_id: rejection.reasons
        for rejection in selection.rejected_profiles
    }
    assert "not_found" in rejected_reasons["coderabbit_cli"]
    assert "not_configurable" in rejected_reasons["generic_cli_pool"]
