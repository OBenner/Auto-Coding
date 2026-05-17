"""Tests for the codebase intelligence integration plugin."""

from __future__ import annotations

import json
from pathlib import Path

from analysis.analyzers import analyze_project
from plugins.base import PluginType
from plugins.registry import PluginRegistry
from plugins.sdk.agent import AgentContext
from plugins.sdk.integration import IntegrationContext

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_sample_project(root: Path) -> Path:
    _write(
        root / "apps" / "backend" / "core" / "client.py",
        '''
"""Client factory."""

class Client:
    """Runtime client."""

    def run(self):
        return "ok"


def create_client():
    """Create a client."""
    return Client()
''',
    )
    _write(
        root / "apps" / "backend" / "agents" / "coder.py",
        """
from core.client import create_client


async def run_coder():
    client = create_client()
    return client.run()
""",
    )
    _write(
        root / "tests" / "test_coder.py",
        """
from apps.backend.agents.coder import run_coder


def test_run_coder_symbol():
    assert run_coder
""",
    )
    _write(
        root / "apps" / "frontend" / "src" / "components" / "Button.tsx",
        """
export interface ButtonProps {
  label: string;
}

export function Button(props: ButtonProps) {
  return props.label;
}
""",
    )
    _write(
        root / "apps" / "frontend" / "src" / "App.tsx",
        """
import { Button } from './components/Button';

export const App = () => {
  return Button({ label: 'Run' });
};
""",
    )
    _write(
        root / "package.json",
        json.dumps(
            {
                "dependencies": {"react": "^18.2.0"},
                "devDependencies": {"vitest": "^1.0.0"},
            }
        ),
    )
    _write(
        root / "pyproject.toml",
        """
[project]
dependencies = [
  "pytest>=8",
  "requests==2.31.0",
]
""",
    )
    _write(
        root / "requirements.txt",
        """
# runtime
fastapi>=0.100
uvicorn[standard]==0.30.0
""",
    )
    _write(
        root / "node_modules" / "ignored" / "index.ts",
        "export const ignored = true;\n",
    )
    return root


def _load_codebase_intelligence_plugin(project: Path):
    PluginRegistry.reset_instance()
    registry = PluginRegistry.get_instance(
        user_plugins_dir=project / ".auto-claude" / "plugins" / "user",
        system_plugins_dir=REPO_ROOT / "apps" / "backend" / "plugins" / "system",
        project_dir=project,
    )
    registry.load_all_plugins()
    plugin = registry.get_plugin("codebase-intelligence")
    assert plugin is not None
    assert plugin.plugin_type == PluginType.INTEGRATION
    assert plugin.is_enabled
    return plugin


def _make_context(project: Path) -> IntegrationContext:
    spec_dir = project / ".auto-claude" / "specs" / "001-test"
    spec_dir.mkdir(parents=True, exist_ok=True)
    return IntegrationContext(project_dir=project, spec_dir=spec_dir)


def test_codebase_intelligence_plugin_loads_and_exposes_tools(temp_dir: Path):
    """The system plugin loads as an integration and exposes query tools."""
    project = _make_sample_project(temp_dir)

    plugin = _load_codebase_intelligence_plugin(project)
    tools = {
        tool.__name__: tool for tool in plugin.create_mcp_tools(_make_context(project))
    }

    assert set(tools) == {
        "build_codebase_index",
        "export_graph_dataset",
        "find_file_dependencies",
        "find_file_dependents",
        "find_symbol_callers",
        "find_symbol_references",
        "get_dependency_inventory",
        "get_graph_neighbors",
        "get_index_status",
        "get_module_graph",
        "get_codebase_summary",
        "search_symbols",
        "trace_file_impact",
        "trace_symbol_impact",
    }


def test_codebase_intelligence_tools_build_sidecar_and_query_graph(temp_dir: Path):
    """Plugin tools build the graph sidecar and answer dependency/symbol queries."""
    project = _make_sample_project(temp_dir)
    plugin = _load_codebase_intelligence_plugin(project)
    tools = {
        tool.__name__: tool for tool in plugin.create_mcp_tools(_make_context(project))
    }

    build_result = json.loads(tools["build_codebase_index"]())

    assert build_result["summary"]["total_files"] == 5
    assert build_result["summary"]["total_symbols"] >= 7
    assert build_result["summary"]["total_dependencies"] == 3
    assert build_result["index_path"] == ".auto-claude/codebase_intelligence/index.json"
    assert (project / build_result["index_path"]).exists()

    dependents = json.loads(
        tools["find_file_dependents"]("apps/backend/core/client.py")
    )
    assert dependents == {
        "file_path": "apps/backend/core/client.py",
        "dependents": ["apps/backend/agents/coder.py"],
    }

    dependencies = json.loads(
        tools["find_file_dependencies"]("apps/backend/agents/coder.py")
    )
    assert dependencies["file_path"] == "apps/backend/agents/coder.py"
    assert dependencies["dependencies"][0]["resolved_path"] == (
        "apps/backend/core/client.py"
    )

    symbols = json.loads(tools["search_symbols"]("client"))
    symbol_names = {symbol["name"] for symbol in symbols["matches"]}
    assert {"Client", "create_client", "Client.run"} <= symbol_names


def test_codebase_intelligence_tools_explain_packages_modules_references_and_impact(
    temp_dir: Path,
):
    """Plugin tools expose richer graph facts needed by agents."""
    project = _make_sample_project(temp_dir)
    plugin = _load_codebase_intelligence_plugin(project)
    tools = {
        tool.__name__: tool for tool in plugin.create_mcp_tools(_make_context(project))
    }

    json.loads(tools["build_codebase_index"]())

    references = json.loads(tools["find_symbol_references"]("create_client"))
    assert references["symbol_name"] == "create_client"
    assert {
        "file_path": "apps/backend/agents/coder.py",
        "line": 6,
        "container": "run_coder",
        "kind": "call",
        "name": "create_client",
    } in references["references"]

    impact = json.loads(
        tools["trace_file_impact"]("apps/backend/core/client.py", depth=2)
    )
    assert impact["file_path"] == "apps/backend/core/client.py"
    assert impact["impacted_files"] == [
        {
            "file_path": "apps/backend/agents/coder.py",
            "distance": 1,
            "is_test": False,
        },
        {
            "file_path": "tests/test_coder.py",
            "distance": 2,
            "is_test": True,
        },
    ]
    assert impact["test_candidates"] == ["tests/test_coder.py"]

    inventory = json.loads(tools["get_dependency_inventory"]())
    package_names = {dependency["name"] for dependency in inventory["dependencies"]}
    assert {
        "react",
        "vitest",
        "pytest",
        "requests",
        "fastapi",
        "uvicorn",
    } <= package_names

    module_graph = json.loads(tools["get_module_graph"](depth=3))
    module_paths = {module["path"] for module in module_graph["modules"]}
    assert {"apps/backend/core", "apps/backend/agents", "tests"} <= module_paths
    assert {
        "source": "apps/backend/agents",
        "target": "apps/backend/core",
        "weight": 1,
    } in module_graph["edges"]


def test_codebase_intelligence_resolves_symbol_callers_and_symbol_impact(
    temp_dir: Path,
):
    """Analyzer resolves symbol-level call graph facts for agent impact analysis."""
    project = _make_sample_project(temp_dir)
    plugin = _load_codebase_intelligence_plugin(project)
    tools = {
        tool.__name__: tool for tool in plugin.create_mcp_tools(_make_context(project))
    }

    json.loads(tools["build_codebase_index"]())

    callers = json.loads(tools["find_symbol_callers"]("create_client"))
    assert callers["symbol_name"] == "create_client"
    assert callers["target_symbols"] == [
        {
            "file_path": "apps/backend/core/client.py",
            "id": "symbol:apps/backend/core/client.py:create_client",
            "kind": "function",
            "line": 11,
            "name": "create_client",
        }
    ]
    assert callers["callers"] == [
        {
            "caller_symbol": {
                "file_path": "apps/backend/agents/coder.py",
                "id": "symbol:apps/backend/agents/coder.py:run_coder",
                "kind": "function",
                "line": 5,
                "name": "run_coder",
            },
            "file_path": "apps/backend/agents/coder.py",
            "line": 6,
            "reference_name": "create_client",
            "target_symbol_id": "symbol:apps/backend/core/client.py:create_client",
        }
    ]

    impact = json.loads(tools["trace_symbol_impact"]("create_client", depth=2))
    assert impact["symbol_name"] == "create_client"
    assert impact["direct_caller_files"] == ["apps/backend/agents/coder.py"]
    assert impact["test_candidates"] == ["tests/test_coder.py"]
    assert impact["impacted_files"] == [
        {
            "distance": 1,
            "file_path": "apps/backend/agents/coder.py",
            "is_test": False,
            "via_symbol": "symbol:apps/backend/core/client.py:create_client",
        },
        {
            "distance": 2,
            "file_path": "tests/test_coder.py",
            "is_test": True,
            "via_symbol": "symbol:apps/backend/core/client.py:create_client",
        },
    ]


def test_codebase_intelligence_tools_export_graph_dataset_and_neighbors(
    temp_dir: Path,
):
    """Plugin tools export graph datasets and query graph neighbors."""
    project = _make_sample_project(temp_dir)
    plugin = _load_codebase_intelligence_plugin(project)
    tools = {
        tool.__name__: tool for tool in plugin.create_mcp_tools(_make_context(project))
    }

    json.loads(tools["build_codebase_index"]())

    graph_result = json.loads(tools["export_graph_dataset"]("json"))
    graph_path = project / graph_result["artifacts"]["graph_json"]
    assert graph_path.exists()

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    node_ids = {node["id"] for node in graph["nodes"]}
    edge_keys = {
        (edge["source"], edge["target"], edge["kind"]) for edge in graph["edges"]
    }
    assert "file:apps/backend/core/client.py" in node_ids
    assert "symbol:apps/backend/core/client.py:create_client" in node_ids
    assert "package:npm:react" in node_ids
    assert (
        "file:apps/backend/agents/coder.py",
        "file:apps/backend/core/client.py",
        "imports",
    ) in edge_keys
    assert (
        "symbol:apps/backend/agents/coder.py:run_coder",
        "symbol:apps/backend/core/client.py:create_client",
        "calls",
    ) in edge_keys

    csv_result = json.loads(tools["export_graph_dataset"]("kuzu_csv"))
    assert (project / csv_result["artifacts"]["nodes_csv"]).exists()
    assert (project / csv_result["artifacts"]["edges_csv"]).exists()
    assert (project / csv_result["artifacts"]["schema_cypher"]).exists()

    incoming = json.loads(
        tools["get_graph_neighbors"](
            "file:apps/backend/core/client.py",
            direction="in",
            edge_kind="imports",
        )
    )
    assert incoming["node_id"] == "file:apps/backend/core/client.py"
    assert incoming["neighbors"] == [
        {
            "edge": {
                "kind": "imports",
                "source": "file:apps/backend/agents/coder.py",
                "target": "file:apps/backend/core/client.py",
            },
            "node": {
                "id": "file:apps/backend/agents/coder.py",
                "kind": "file",
                "label": "coder.py",
            },
        }
    ]


def test_codebase_intelligence_detects_and_rebuilds_stale_sidecar(temp_dir: Path):
    """Queries rebuild the sidecar when source hashes changed after indexing."""
    project = _make_sample_project(temp_dir)
    plugin = _load_codebase_intelligence_plugin(project)
    tools = {
        tool.__name__: tool for tool in plugin.create_mcp_tools(_make_context(project))
    }

    json.loads(tools["build_codebase_index"]())
    fresh_status = json.loads(tools["get_index_status"]())

    assert fresh_status["status"] == "fresh"
    assert fresh_status["fresh"] is True

    _write(
        project / "apps" / "backend" / "core" / "client.py",
        '''
"""Client factory."""

class Client:
    """Runtime client."""

    def run(self):
        return "ok"


def create_client():
    """Create a client."""
    return Client()


def create_special_client():
    """Create a special client."""
    return Client()
''',
    )

    stale_status = json.loads(tools["get_index_status"]())
    assert stale_status["status"] == "stale"
    assert stale_status["fresh"] is False
    assert stale_status["changed_files"] == ["apps/backend/core/client.py"]

    symbols = json.loads(tools["search_symbols"]("create_special_client"))
    assert [symbol["name"] for symbol in symbols["matches"]] == [
        "create_special_client"
    ]

    rebuilt_status = json.loads(tools["get_index_status"]())
    assert rebuilt_status["status"] == "fresh"
    assert rebuilt_status["fresh"] is True


def test_project_analysis_does_not_run_plugin_directly(temp_dir: Path):
    """Core project analysis stays plugin-optional and does not write graph sidecars."""
    project = _make_sample_project(temp_dir)
    output_file = project / ".auto-claude" / "project_index.json"

    project_index = analyze_project(project, output_file)

    assert "codebase_intelligence" not in project_index
    assert not (project / ".auto-claude" / "codebase_intelligence").exists()


def test_codebase_intelligence_prompt_augmentation_builds_summary_and_trace(
    temp_dir: Path,
):
    """The integration plugin contributes compact runtime context and trace."""
    project = _make_sample_project(temp_dir)
    plugin = _load_codebase_intelligence_plugin(project)
    integration_context = _make_context(project)
    agent_context = AgentContext(
        project_dir=project,
        spec_dir=integration_context.spec_dir,
        phase="coder",
        metadata={
            "agent_type": "coder",
            "task": "Refactor create_client usage",
            "files": ["apps/backend/agents/coder.py"],
        },
    )

    prompt = plugin.augment_prompt(agent_context)

    assert "Codebase Intelligence Runtime Context" in prompt
    assert "codebase-intelligence-integration" in prompt
    assert ".auto-claude/codebase_intelligence/index.json" in prompt
    assert "total_files: 5" in prompt
    assert "total_symbols:" in prompt
    assert "find_file_dependencies" in prompt
    assert "trace_file_impact" in prompt
    assert "trace_symbol_impact" in prompt
    assert (project / ".auto-claude" / "codebase_intelligence" / "index.json").exists()

    trace_path = (
        project / ".auto-claude" / "plugin_traces" / "codebase-intelligence.jsonl"
    )
    trace = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
    assert trace["plugin"] == "codebase-intelligence"
    assert trace["phase"] == "coder"
    assert trace["reason"] == "attached compact graph summary to agent prompt"
    assert trace["index_path"] == ".auto-claude/codebase_intelligence/index.json"
    assert trace["summary"]["total_files"] == 5
