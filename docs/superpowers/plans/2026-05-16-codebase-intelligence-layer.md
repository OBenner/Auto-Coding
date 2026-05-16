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
