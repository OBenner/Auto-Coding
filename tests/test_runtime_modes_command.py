import builtins
import json
import logging
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
    assert "External MCP Client Health" in output
    assert "Subagent Orchestrator Matrix" in output
    assert "codex_cli" in output
    assert "generic_cli_pool" in output
    assert "opencode" in output
    assert "--provider-smoke" in output
    assert "--external-mcp-smoke" in output
    assert payload["providers"][0]["provider"] == "claude"


def test_runtime_modes_command_outputs_json(capsys, monkeypatch):
    from agents.runtime import EXTERNAL_MCP_CLIENT_ENV
    from cli.runtime_commands import handle_runtime_modes_command

    monkeypatch.delenv(EXTERNAL_MCP_CLIENT_ENV, raising=False)

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
    assert "external_mcp_smoke" in payload["recommendations"]
    assert "runner_router" in payload["recommendations"]
    assert "external_mcp_client" in payload["recommendations"]
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
