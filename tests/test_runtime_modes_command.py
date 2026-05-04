import json
import sys


def test_parse_args_with_runtime_modes():
    from cli.main import parse_args

    original_argv = sys.argv
    sys.argv = ["run.py", "--runtime-modes"]
    try:
        args = parse_args()
    finally:
        sys.argv = original_argv

    assert args.runtime_modes is True


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
    assert "Runtime Fallback Matrix" in output
    assert "MCP Bridge Plan Matrix" in output
    assert "Subagent Orchestrator Matrix" in output
    assert "codex_cli" in output
    assert "generic_cli_pool" in output
    assert "opencode" in output
    assert "--provider-smoke" in output
    assert payload["providers"][0]["provider"] == "claude"


def test_runtime_modes_command_outputs_json(capsys):
    from cli.runtime_commands import handle_runtime_modes_command

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
    assert "runner_router" in payload["recommendations"]
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
    assert "context7" in openai_generic_mcp["native_required_servers"]
    assert openai_generic_mcp["action_required"] == "use_native_mcp_runtime"
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
