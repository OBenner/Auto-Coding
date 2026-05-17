# Codebase Intelligence Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first deterministic codebase intelligence slice for Auto Code as an optional system integration plugin: local Python/TypeScript symbol extraction, import graph construction, reverse dependency lookup, package inventory, module graph queries, impact tracing, MCP tools, and a JSON sidecar produced only when the plugin is invoked.

**Architecture:** Add `apps/backend/plugins/system/codebase-intelligence/` as an `integration` plugin with its own dataclass models, stdlib-only extractors, package manifest scanner, `CodebaseIndexer`, and MCP tool functions. Keep full graph data in `.auto-claude/codebase_intelligence/index.json`; core project analysis remains plugin-optional and does not import or run the indexer directly.

**Tech Stack:** Python 3.12, stdlib `ast`, regex-based TypeScript first slice, pytest.

---

### Task 1: Test Contract

**Files:**
- Create: `tests/test_codebase_intelligence.py`

- [ ] **Step 1: Write failing tests**

```python
def test_builds_python_and_typescript_dependency_graph(temp_dir: Path):
    project = make_sample_project(temp_dir)
    index = CodebaseIndexer(project).build_index()

    assert index.summary()["total_files"] == 4
    assert any(s.name == "create_client" for s in index.files["apps/backend/core/client.py"].symbols)
    assert "apps/backend/core/client.py" in index.reverse_dependencies
    assert "apps/backend/agents/coder.py" in index.reverse_dependencies["apps/backend/core/client.py"]
    assert "apps/frontend/src/components/Button.tsx" in index.reverse_dependencies
    assert "apps/frontend/src/App.tsx" in index.reverse_dependencies["apps/frontend/src/components/Button.tsx"]
```

- [ ] **Step 2: Run tests to verify RED**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'codebase_intelligence'`.

### Task 2: Plugin Models and Indexer

**Files:**
- Create: `apps/backend/plugins/system/codebase-intelligence/plugin.json`
- Create: `apps/backend/plugins/system/codebase-intelligence/plugin.py`
- Create: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/__init__.py`
- Create: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/models.py`
- Create: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/extractors.py`
- Create: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/indexer.py`

- [ ] **Step 1: Implement dataclass models**

Create `CodeSymbol`, `CodeDependency`, `CodeFile`, and `CodebaseIndex`, each with `to_dict()` methods for stable JSON output.

- [ ] **Step 2: Implement extractors**

Python extractor uses `ast` to collect imports, classes, functions, async functions, and methods. TypeScript extractor handles relative `import ... from`, `export ... from`, `require(...)`, `function`, `class`, `interface`, `type`, and arrow-function constants.

- [ ] **Step 3: Implement indexer**

`CodebaseIndexer.build_index()` walks supported code files while skipping `.git`, `.auto-claude`, `.worktrees`, `node_modules`, virtualenvs, build outputs, and caches. It resolves Python module imports through a module alias map and TypeScript relative imports through extension/index-file probing.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py -v`

Expected: PASS.

### Task 3: Integration Plugin Tooling

**Files:**
- Modify: `tests/test_codebase_intelligence.py`

- [ ] **Step 1: Add failing plugin tool test**

Test `PluginRegistry` loads `codebase-intelligence`, exposes `build_codebase_index`, `get_codebase_summary`, `find_file_dependents`, `find_file_dependencies`, and `search_symbols`, and writes `.auto-claude/codebase_intelligence/index.json` only when the tool is invoked.

- [ ] **Step 2: Run tests to verify RED**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py -v`

Expected: FAIL because the system plugin is not implemented.

- [ ] **Step 3: Implement plugin tools**

Create the system integration plugin and keep all graph building/query behavior inside the plugin directory. Leave `analysis.analyzers.analyze_project` free of direct codebase-intelligence imports.

- [ ] **Step 4: Run focused tests**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py tests/test_project_analyzer.py::TestLanguageDetection -v`

Expected: PASS.

### Task 4: Verification

**Files:**
- No additional production files.

- [ ] **Step 1: Run import/compile check**

Run: `apps/backend/.venv/bin/python -m py_compile apps/backend/plugins/system/codebase-intelligence/plugin.py apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/*.py apps/backend/analysis/analyzers/__init__.py`

Expected: PASS with no output.

- [ ] **Step 2: Inspect git diff**

Run: `git diff --stat`

Expected: only the new system plugin, tests, docs, and this plan file changed.

### Task 5: Strengthened Graph Queries

**Files:**
- Modify: `tests/test_codebase_intelligence.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/plugin.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/models.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/extractors.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/indexer.py`
- Create: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/packages.py`

- [x] **Step 1: Add RED tests for richer plugin facts**

The new contract covers `find_symbol_references`, `trace_file_impact`,
`get_dependency_inventory`, and `get_module_graph`.

- [x] **Step 2: Add references and package dependency models**

The index now stores lightweight call references and package dependencies from
`package.json`, `pyproject.toml`, and `requirements*.txt`.

- [x] **Step 3: Add impact and module graph queries**

Impact tracing walks reverse dependencies with a bounded depth and surfaces test
candidates. Module graph grouping is directory-depth based, which is stable and
cheap enough for agent context.

- [x] **Step 4: Keep the layer approximate and plugin-local**

This layer does not require Tree-sitter, Kuzu, SCIP, or LSP services yet. Those
can be added behind the same plugin tools once the first contract is useful.

### Task 6: Graph Dataset Export

**Files:**
- Modify: `tests/test_codebase_intelligence.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/plugin.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/__init__.py`
- Create: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/graph_export.py`

- [x] **Step 1: Add RED tests for graph export tools**

The plugin now tests `export_graph_dataset` and `get_graph_neighbors`. The graph
contract includes project, file, module, symbol, and package nodes plus
contains, defines, imports, references, and declares-dependency edges.

- [x] **Step 2: Export JSON and Kuzu-oriented CSV artifacts**

`export_graph_dataset("json")` writes a stable `graph.json`.
`export_graph_dataset("kuzu_csv")` also writes `nodes.csv`, `edges.csv`, and a
minimal `schema.cypher` under `.auto-claude/codebase_intelligence/graph/kuzu/`.

- [x] **Step 3: Add local graph neighbor query**

`get_graph_neighbors` lets agents ask for incoming, outgoing, or bidirectional
neighbors without requiring an embedded database process.

### Task 7: Sidecar Freshness

**Files:**
- Modify: `tests/test_codebase_intelligence.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/plugin.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/models.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/indexer.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/packages.py`

- [x] **Step 1: Add RED tests for stale sidecar detection**

The test builds an index, changes a source file, expects `get_index_status` to
report `stale`, then verifies a normal symbol query rebuilds the sidecar and
finds the new symbol.

- [x] **Step 2: Store source fingerprints in the sidecar**

The index now stores sha256 fingerprints for supported source files and package
manifests. Older sidecars can fall back to code-file hashes.

- [x] **Step 3: Rebuild before answering stale queries**

`_load_or_build_index` performs a cheap fingerprint comparison before loading.
When files changed, it writes a fresh index before answering the tool call.

### Task 8: Runtime MCP Wiring

**Files:**
- Modify: `apps/backend/core/client.py`
- Modify: `tests/test_client.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/README.md`

- [x] **Step 1: Add RED test for client session visibility**

The test verifies `create_client(..., agent_type="coder")` includes
`codebase-intelligence-integration` in SDK `mcp_servers` and allows plugin tool
names such as `mcp__codebase-intelligence-integration__build_codebase_index`.

- [x] **Step 2: Wire enabled integration plugins into SDK options**

`core.client` now loads enabled integration plugins for agents that already use
the `auto-claude` MCP server, creates SDK MCP servers for their tools, and adds
their prefixed tool names to `allowed_tools`.

- [x] **Step 3: Preserve compatibility wrapper**

`load_plugin_mcp_servers()` remains available as a server-only wrapper, while
`load_plugin_mcp_integrations()` returns both servers and allowed tool names.

### Task 9: Plugin Diagnostics Contract

**Files:**
- Modify: `tests/test_plugin_cli.py`
- Modify: `apps/backend/plugins/cli.py`
- Modify: `apps/backend/plugins/loader.py`
- Modify: `apps/frontend/src/main/plugins/types.ts`
- Modify: `apps/frontend/src/main/plugins/loader.ts`
- Modify: `apps/frontend/src/main/plugins/loader.test.ts`
- Modify: `apps/frontend/src/preload/api/plugin-api.ts`
- Modify: `apps/frontend/src/shared/constants/ipc.ts`
- Modify: `apps/frontend/src/shared/types/ipc.ts`
- Modify: `apps/frontend/src/renderer/lib/browser-mock.ts`

- [x] **Step 1: Add RED backend CLI diagnostics tests**

Add parser, dispatch, and JSON command tests for `health --json`. The command
must inspect plugin directories and manifests without importing plugin modules.
The regression also covers `re.compile(...)` so regex compilation does not get
misclassified as builtin `compile(...)` code execution.

- [x] **Step 2: Implement backend diagnostics**

Add a `health` command that reports plugin directories, manifest entries,
security warnings, duplicate plugin names, invalid manifests, and summary counts.
The implementation must use `PluginLoader._load_metadata()` and
`validate_plugin_security()`, not `PluginRegistry.load_all_plugins()`.
Narrow the dangerous-call scanner so builtin `compile(...)` remains blocked
while `re.compile(...)` stays allowed.

- [x] **Step 3: Add RED frontend IPC diagnostics tests**

Add an IPC handler test proving `plugin:health` invokes
`plugins/cli.py health --json` with the selected project cwd and returns the
diagnostic payload.

- [x] **Step 4: Implement frontend IPC/preload/types contract**

Expose `getPluginHealth(projectPath)` through the preload API and shared types.
Keep renderer UI changes for a later task.

- [x] **Step 5: Verify**

Run:
`apps/backend/.venv/bin/python -m pytest tests/test_plugin_cli.py -v`
`npm --prefix apps/frontend test -- src/main/plugins/loader.test.ts`
`npm --prefix apps/frontend run typecheck`
`/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff check apps/backend/plugins/cli.py apps/backend/plugins/loader.py tests/test_plugin_cli.py`
`/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff format apps/backend/plugins/cli.py apps/backend/plugins/loader.py tests/test_plugin_cli.py --check --diff`

### Task 10: Plugin Runtime Foundation

**Files:**
- Create: `apps/backend/plugins/runtime.py`
- Create: `tests/test_plugin_runtime.py`
- Modify: `apps/backend/plugins/base.py`
- Modify: `apps/backend/plugins/sdk/agent.py`
- Modify: `apps/backend/plugins/cli.py`
- Modify: `apps/backend/plugins/__init__.py`
- Modify: `apps/backend/core/client.py`
- Modify: `tests/test_plugin_cli.py`
- Modify: `tests/test_client.py`

- [x] **Step 1: Add RED tests for runtime capabilities and agent hooks**

Add tests for `PluginCapability` defaults, explicit manifest capabilities,
agent prompt augmentation, pre-tool blocking, post-tool observation, and smoke
contracts for `agent`, `integration`, and `ui` plugin types.

- [x] **Step 2: Add RED tests for client wiring and CLI permission diff**

Add a `create_client()` test proving enabled agent plugins append prompt
instructions and register plugin runtime SDK hooks. Add an `enable --json`
test proving the response includes `permission_diff` with capabilities and
required permissions.

- [x] **Step 3: Implement capability model**

Add `PluginCapability` with `analysis_only`, `generic_edit`, and
`full_agent_runtime`. Parse `capabilities` from `plugin.json`, defaulting
agent plugins to `full_agent_runtime` and integration/ui plugins to
`analysis_only`.

- [x] **Step 4: Implement agent runtime hooks**

Extend `AgentPlugin` with optional `augment_prompt`, `pre_tool`, and
`post_tool` hooks. Keep default implementations inert so existing plugins do
not need changes.

- [x] **Step 5: Implement runtime adapter**

Create `plugins.runtime` as the only bridge from loaded plugins to agent
runtime effects. It should collect prompt contributions, enforce capability
gates for tool hooks, normalize hook decisions, and build SDK hook matchers
for pre/post tool use.

- [x] **Step 6: Wire runtime adapter into `create_client()`**

Append plugin prompt blocks after base preferences and add plugin pre/post
tool matchers beside the existing bash security hook.

- [x] **Step 7: Verify**

Run:
`apps/backend/.venv/bin/python -m pytest tests/test_plugin_runtime.py tests/test_plugin_cli.py tests/test_client.py -v`
`/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff check apps/backend/plugins/base.py apps/backend/plugins/sdk/agent.py apps/backend/plugins/runtime.py apps/backend/plugins/cli.py apps/backend/core/client.py tests/test_plugin_runtime.py tests/test_plugin_cli.py tests/test_client.py`
`/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff format apps/backend/plugins/base.py apps/backend/plugins/sdk/agent.py apps/backend/plugins/runtime.py apps/backend/plugins/cli.py apps/backend/core/client.py tests/test_plugin_runtime.py tests/test_plugin_cli.py tests/test_client.py --check --diff`

### Task 11: Symbol-Level Codebase Intelligence

**Files:**
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/models.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/graph_export.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/plugin.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/README.md`
- Modify: `tests/test_codebase_intelligence.py`

- [x] **Step 1: Add RED tests for symbol call graph behavior**

Add tests proving the analyzer exposes `find_symbol_callers`,
`trace_symbol_impact`, and graph export `calls` edges between caller symbols
and callee symbols.

- [x] **Step 2: Implement symbol ids and call resolution**

Add stable symbol ids, compact symbol summaries, reference-to-symbol
resolution, caller-symbol lookup, and symbol impact aggregation on the
`CodebaseIndex` model.

- [x] **Step 3: Expose symbol-level tools and graph edges**

Expose MCP tools for symbol callers and symbol impact, and export symbol
`calls` edges alongside existing file-level `references` edges.

- [x] **Step 4: Verify**

Run:
`apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py -q`
`apps/backend/.venv/bin/python -m pytest tests/test_plugin_integration.py tests/test_plugin_mcp_integration.py tests/test_codebase_intelligence.py -q`
`/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff check apps/backend/plugins/system/codebase-intelligence apps/backend/plugins/system/codebase-intelligence/plugin.py tests/test_codebase_intelligence.py`
`/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff format --check apps/backend/plugins/system/codebase-intelligence apps/backend/plugins/system/codebase-intelligence/plugin.py tests/test_codebase_intelligence.py`
