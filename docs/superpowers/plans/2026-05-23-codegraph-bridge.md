# CodeGraph Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `codebase-intelligence` plugin read from an external CodeGraph (`colbymchenry/codegraph`) SQLite index when available, while keeping our deterministic Python/TypeScript indexer as a bounded fallback. The plugin remains the runtime "context director" (prompt augmentation, task briefing, traces); CodeGraph becomes the heavy-lifting "search engine" exposed to agents as a separate MCP server.

**Architecture:** Add a `backends/` subpackage under the existing plugin. `SidecarBackend` wraps the current JSON index for the fallback path. `CodeGraphBackend` reads `.codegraph/codegraph.db` (SQLite, FTS5) directly for summary, dependents, callers, symbol search, and impact queries — no subprocess on the hot path. A new `CodebaseGraphBackend` protocol unifies the read API used by `plugin.py`. Detection runs once per `create_client()` call through `prompts_pkg.project_context.detect_project_capabilities()` and decorates `project_capabilities` with `has_codegraph`. When CodeGraph is present, `core.client` also registers the external `codegraph` stdio MCP server alongside our `codebase-intelligence-integration` server, and `augment_prompt()` rewrites the tool-guidance block to route language-specific deep queries to CodeGraph tools.

**Tech Stack:** Python 3.12, stdlib `sqlite3`, pytest, existing plugin runtime substrate.

---

## Task 1: Backend Protocol and Fallback Refactor

**Files:**
- Create: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/backends/__init__.py`
- Create: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/backends/base.py`
- Create: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/backends/sidecar.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/__init__.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/plugin.py`
- Modify: `tests/test_codebase_intelligence.py`

- [ ] **Step 1: Write failing backend contract test**

Add a test proving `SidecarBackend` exposes a `name == "sidecar"`, returns the same `summary()`, `file_dependents()`, `file_dependencies()`, `symbol_callers()`, `symbol_impact()`, `module_graph()`, and `search_symbols()` payloads as the current `CodebaseIndex` methods on a sample project, and reports `is_available() is True` only when the JSON sidecar exists.

- [ ] **Step 2: Run focused RED test**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py::test_sidecar_backend_matches_index_contract -q`

Expected: FAIL with `ImportError` or `AttributeError` because `backends` does not exist.

- [ ] **Step 3: Define `CodebaseGraphBackend` protocol**

Create `backends/base.py` with a `Protocol` (or `ABC`) declaring read-only methods used by `plugin.py`: `is_available()`, `summary()`, `file_dependents(path)`, `file_dependencies(path, include_external)`, `symbol_callers(symbol, kind, limit)`, `symbol_references(symbol, kind, limit)`, `file_impact(path, depth)`, `symbol_impact(symbol, depth)`, `module_graph()`, `search_symbols(query, kind, limit)`, `dependency_inventory()`, `index_status()`. Each method returns a JSON-serializable dict matching the shape already produced by current MCP tools.

- [ ] **Step 4: Implement `SidecarBackend`**

`SidecarBackend(project_dir, sidecar_path)` wraps the existing `CodebaseIndexer` + `CodebaseIndex.load()` path with no behavior change. Reuse `_load_or_build_index()` for freshness. All current plugin queries should delegate to this backend.

- [ ] **Step 5: Wire plugin to use a backend**

In `plugin.py`, replace direct `CodebaseIndex` calls inside the MCP tool closures with calls to `self._backend(context)`. Default backend stays `SidecarBackend`. Keep `build_codebase_index` and `export_graph_dataset` calling the indexer directly — those write artifacts and are not part of the read protocol.

- [ ] **Step 6: Run GREEN test**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py -q`

Expected: PASS for all existing tests plus the new backend contract test.

## Task 2: CodeGraph Detection in Project Capabilities

**Files:**
- Modify: `apps/backend/prompts_pkg/project_context.py`
- Modify: `tests/test_project_context.py` (or whichever test file covers `detect_project_capabilities`)
- Modify: `apps/backend/core/client.py`
- Modify: `tests/test_client.py`

- [ ] **Step 1: Locate the capabilities detector**

Run: `grep -n "def detect_project_capabilities" apps/backend/prompts_pkg/project_context.py`

Confirm signature and current capability keys before editing.

- [ ] **Step 2: Add RED capability test**

Add a test proving `detect_project_capabilities(project_index, project_dir=...)` returns `has_codegraph=True` when `.codegraph/codegraph.db` exists at the project root, and `False` otherwise. Keep all existing capability keys stable.

- [ ] **Step 3: Run focused RED test**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_project_context.py -k codegraph -q`

Expected: FAIL because the key is missing.

- [ ] **Step 4: Implement detection**

Extend `detect_project_capabilities()` to accept an optional `project_dir` parameter (default `None`). When provided, set `has_codegraph` to `True` only when both `.codegraph/codegraph.db` is a file and its parent contains a `manifest.json` or similar marker (use whichever marker file CodeGraph writes — verify by inspecting a real `.codegraph/` directory first via `ls -la .codegraph/` in any test fixture). Do not invoke the `codegraph` CLI.

- [ ] **Step 5: Thread `project_dir` from `core.client`**

In `_get_cached_project_data()`, pass `project_dir` to `detect_project_capabilities()`. Add a test in `tests/test_client.py` verifying the cached capabilities dict includes `has_codegraph`.

- [ ] **Step 6: Run GREEN tests**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_project_context.py tests/test_client.py -q`

Expected: PASS.

## Task 3: CodeGraph SQLite Backend

**Files:**
- Create: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/backends/codegraph.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/__init__.py`
- Modify: `tests/test_codebase_intelligence.py`

- [ ] **Step 1: Inspect a real CodeGraph schema**

Before writing the backend, capture the actual SQLite schema. On a machine with `codegraph` installed, run:

```
codegraph init -i
sqlite3 .codegraph/codegraph.db ".schema"
sqlite3 .codegraph/codegraph.db "SELECT name FROM sqlite_master WHERE type IN ('table','view');"
```

Save the schema snippet into the task notes. Do **not** assume table names without inspection — CodeGraph is a moving target. If a schema is not yet observed, the test in Step 2 must mark itself with `pytest.mark.skipif(not CODEGRAPH_FIXTURE_AVAILABLE, ...)`.

- [ ] **Step 2: Add RED backend test with synthetic fixture**

Add a test that builds a minimal SQLite database matching the observed CodeGraph schema (symbols, edges, files tables) inside a temp dir as `.codegraph/codegraph.db`, instantiates `CodeGraphBackend(project_dir)`, and asserts: `is_available() is True`, `summary()` returns counts derived from the fixture, `search_symbols("foo")` returns FTS5 matches, `symbol_callers("bar")` reads the `references`/`calls` edge table. Mark the test `@pytest.mark.codegraph_backend` so it can be run in isolation.

- [ ] **Step 3: Run focused RED test**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py -k codegraph_backend -q`

Expected: FAIL with `ImportError` on `CodeGraphBackend`.

- [ ] **Step 4: Implement `CodeGraphBackend`**

Open the SQLite file with `sqlite3.connect(..., uri=True, ?mode=ro)` to enforce read-only. Implement each protocol method as a prepared statement. Cache the connection per-instance. Translate CodeGraph node kinds and edge types into our existing payload shape (same field names emitted by `SidecarBackend`) so plugin output stays stable. For methods we cannot satisfy from CodeGraph alone (e.g. `dependency_inventory` from `package.json` / `pyproject.toml`), fall through to the sidecar.

- [ ] **Step 5: Composite backend**

Add `CompositeBackend(primary, fallback)` to `backends/__init__.py`. It tries `primary` first; if `primary.is_available()` is False **or** a specific method raises `NotImplementedError`, it delegates to `fallback`. This is the wiring point that lets CodeGraph cover language coverage while sidecar handles package inventory and Kuzu export.

- [ ] **Step 6: Run GREEN tests**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py -q`

Expected: PASS.

## Task 4: Plugin Backend Selection

**Files:**
- Modify: `apps/backend/plugins/system/codebase-intelligence/plugin.py`
- Modify: `tests/test_codebase_intelligence.py`

- [ ] **Step 1: Add RED selection test**

Add a test proving that when `.codegraph/codegraph.db` exists in the test project, `CodebaseIntelligencePlugin._backend(context)` returns a `CompositeBackend` whose primary is `CodeGraphBackend`; when it does not exist, the backend is `SidecarBackend`. Also assert the `augment_prompt()` output contains a line `backend: codegraph` vs. `backend: sidecar`.

- [ ] **Step 2: Run focused RED test**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py::test_plugin_selects_codegraph_backend_when_db_present -q`

Expected: FAIL because the plugin currently always uses sidecar.

- [ ] **Step 3: Implement selection**

Add a `_backend(context)` method on the plugin that inspects `<project_dir>/.codegraph/codegraph.db`. If present, return `CompositeBackend(CodeGraphBackend(project_dir), SidecarBackend(project_dir, sidecar_path))`. Otherwise return `SidecarBackend(...)`. Cache the backend per-plugin-instance keyed by `project_dir`. Add the backend name to the runtime trace JSONL event and to the augmented prompt header.

- [ ] **Step 4: Update tool guidance text**

When the backend is `codegraph`, the tool-guidance block in `augment_prompt()` must:
- Keep `find_file_dependencies`/`find_file_dependents`/`search_symbols`/`trace_*` tool names (these are MCP tools defined by **our** plugin and just delegate to the active backend).
- Append a separate paragraph: "For non-Python/TypeScript files (Go, Rust, Java, C#, Swift, Kotlin, etc.) or framework route lookups, prefer `mcp__codegraph__codegraph_explore`, `codegraph_callers`, `codegraph_context`."

- [ ] **Step 5: Run GREEN tests**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py -q`

Expected: PASS.

## Task 5: External CodeGraph MCP Server Registration

**Files:**
- Modify: `apps/backend/core/client.py`
- Modify: `tests/test_client.py`

- [ ] **Step 1: Add RED MCP wiring test**

Add a test using a mocked `project_capabilities={"has_codegraph": True}` proving that `create_client(..., agent_type="coder")` results in SDK `mcp_servers` containing a `codegraph` stdio server with `command="codegraph"`, `args=["serve", "--mcp"]`, and that `allowed_tools` includes at least `mcp__codegraph__codegraph_search`, `mcp__codegraph__codegraph_context`, `mcp__codegraph__codegraph_callers`, `mcp__codegraph__codegraph_callees`, `mcp__codegraph__codegraph_impact`, `mcp__codegraph__codegraph_node`, `mcp__codegraph__codegraph_status`, `mcp__codegraph__codegraph_files`, `mcp__codegraph__codegraph_explore`. Add a complementary test proving the server is **not** registered when `has_codegraph=False`.

- [ ] **Step 2: Run focused RED test**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_client.py -k codegraph_mcp -q`

Expected: FAIL because the server is not wired.

- [ ] **Step 3: Implement registration**

In `core/client.py`, near the existing `load_plugin_mcp_integrations()` call, add a conditional block: when `project_capabilities.get("has_codegraph")` is truthy and `agent_type` is in `{"planner", "coder", "qa_reviewer", "qa_fixer"}`, append a stdio MCP server definition for `codegraph` and extend `allowed_tools` with the prefixed CodeGraph tool names. Resolve the `codegraph` binary via the platform abstraction (`findExecutable` equivalent — check `apps/backend/core/platform/` for the Python helper; if absent, use `shutil.which("codegraph")` and skip registration when not found).

- [ ] **Step 4: Run GREEN tests**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_client.py -q`

Expected: PASS.

## Task 6: Slim Down Indexer for Fallback-Only Role

**Files:**
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/indexer.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/extractors.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/README.md`
- Modify: `tests/test_codebase_intelligence.py`

- [ ] **Step 1: Verify what stays load-bearing**

Run `grep -rn "from codebase_intelligence" apps/backend tests` to enumerate all current callers of the indexer's internals (not just `CodebaseIndex`). Anything imported outside the plugin must keep its public name. Specifically confirm whether `GraphDataset` / Kuzu export is still required by anything other than the `export_graph_dataset` MCP tool; if not, mark it for removal in Step 4.

- [ ] **Step 2: Decide reduction scope from the grep output**

Write a short "removal list" inside this plan document below this checkbox. Candidates to consider:
- TypeScript extractor improvements (CodeGraph handles TS via tree-sitter; keep only enough to support fallback when CodeGraph is absent).
- Reverse dependency precomputation (CodeGraph stores edges directly; sidecar still needs it for its own queries — keep).
- Kuzu CSV export (no internal consumer found in this codebase per Step 1 grep; remove unless that grep shows otherwise).

- [ ] **Step 3: Add RED test for slimmed scope**

If the removal list includes Kuzu export, add a test asserting `export_graph_dataset("kuzu_csv")` raises a clear `NotImplementedError` with guidance to use `codegraph` instead. Keep the JSON export path tested.

- [ ] **Step 4: Apply removals and update README**

Delete only what Step 1 proved unused. Update `README.md` to describe the new two-backend model: CodeGraph for deep queries (when installed), sidecar for fallback / Python-side internal use / runtime context injection. Keep the existing tool list — the MCP surface does not change.

- [ ] **Step 5: Run full plugin test suite**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py tests/test_plugin_runtime.py tests/test_client.py -q`

Expected: PASS.

## Task 7: Verification

**Files:**
- No additional production files.

- [ ] **Step 1: Ruff + format check**

Run:
```
/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff check apps/backend/plugins/system/codebase-intelligence apps/backend/core/client.py apps/backend/prompts_pkg/project_context.py tests/test_codebase_intelligence.py tests/test_client.py tests/test_project_context.py
/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff format --check apps/backend/plugins/system/codebase-intelligence apps/backend/core/client.py apps/backend/prompts_pkg/project_context.py tests/test_codebase_intelligence.py tests/test_client.py tests/test_project_context.py
```

Expected: PASS with no findings.

- [ ] **Step 2: Manual end-to-end check (with CodeGraph installed)**

On a developer machine with `npm i -g @colbymchenry/codegraph` available:
1. `cd` to a non-trivial Go or Rust project (e.g. a clone of `gin` or `tokio`).
2. `codegraph init -i` to build the index.
3. Run a planner session against a small spec in that project.
4. Verify the agent receives `backend: codegraph` in its prompt header and that the SDK transcript shows both `mcp__codebase-intelligence-integration__*` and `mcp__codegraph__*` tool calls.
5. Confirm `.auto-claude/plugin_traces/codebase-intelligence.jsonl` records `backend: codegraph` for that session.

- [ ] **Step 3: Manual fallback check (CodeGraph not installed)**

On a machine without the `codegraph` binary (or after `which codegraph` returns nothing):
1. Run the same planner session.
2. Verify the agent receives `backend: sidecar` in its prompt header.
3. Verify no `codegraph` MCP server appears in the SDK options.
4. Verify `mcp__codebase-intelligence-integration__*` tools still answer Python/TS queries correctly.

- [ ] **Step 4: Inspect git diff**

Run: `git diff --stat`

Expected: changes confined to `apps/backend/plugins/system/codebase-intelligence/`, `apps/backend/core/client.py`, `apps/backend/prompts_pkg/project_context.py`, related tests, and this plan file.

## Task 8: Auto-Install Installer Module

**Files:**
- Create: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/installer.py`
- Create: `tests/test_codegraph_installer.py`

**Context:** CodeGraph publishes standalone tarballs/zips per platform at `https://github.com/colbymchenry/codegraph/releases`. As of `v0.9.3`, the asset matrix is:
- `codegraph-darwin-arm64.tar.gz`, `codegraph-darwin-x64.tar.gz`
- `codegraph-linux-arm64.tar.gz`, `codegraph-linux-x64.tar.gz`
- `codegraph-win32-arm64.zip`, `codegraph-win32-x64.zip`

We download the matching asset into `~/.auto-claude/bin/codegraph/<version>/` and never run `curl | sh`. This keeps the install user-local, sudo-free, reproducible, and removable.

- [ ] **Step 1: Add RED installer-resolution test**

Add a test proving `resolve_asset_name(os_name, arch)` returns the right tarball/zip name for each combination (`darwin`+`arm64` → `codegraph-darwin-arm64.tar.gz`, `windows`+`x64` → `codegraph-win32-x64.zip`, etc.) and raises `UnsupportedPlatformError` for unknown combinations (e.g. `linux`+`armv7`).

- [ ] **Step 2: Run RED test**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codegraph_installer.py::test_resolve_asset_name -q`

Expected: FAIL because `installer` does not exist.

- [ ] **Step 3: Implement asset resolver and install path**

Create `installer.py` with:
- `INSTALL_ROOT = Path.home() / ".auto-claude" / "bin" / "codegraph"` (override via `AUTO_CLAUDE_CODEGRAPH_DIR`).
- `resolve_asset_name(os_name, arch)` returning the asset filename. Use the `core.platform` module (`is_windows`/`is_macos`/`is_linux`) for OS detection and `platform.machine()` (normalized: `arm64`/`aarch64` → `arm64`, `x86_64`/`AMD64` → `x64`) for arch.
- `installed_version(install_root)` returning the version string of an existing install, or `None`.
- `binary_path(install_root, version)` returning the absolute path to the `codegraph`/`codegraph.exe` executable inside the unpacked tree.

- [ ] **Step 4: Add RED download/verify test**

Add a test using `responses`/`urllib.request` mocking (or `pytest-httpserver` if already in use) proving `download_and_install(version="v0.9.3", install_root=tmp_path, expected_sha256=...)`:
1. Downloads from the constructed GitHub release URL.
2. Verifies SHA256 against the provided value and raises `ChecksumMismatchError` if it differs.
3. Extracts the tarball/zip into `install_root/v0.9.3/`.
4. Chmod's the binary `0o755` on POSIX.
5. Returns the absolute `binary_path()`.
6. Refuses to overwrite an existing install of the same version unless `force=True`.

- [ ] **Step 5: Run RED test**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codegraph_installer.py -q`

Expected: FAIL.

- [ ] **Step 6: Implement downloader**

Implement `download_and_install()` using stdlib only (`urllib.request`, `tarfile`, `zipfile`, `hashlib`, `tempfile`). Stream into a temp file, hash while writing, verify, extract atomically (`os.replace` of the staging dir). Do **not** allow extraction outside `install_root` — guard against tar slip (`..` paths, symlink escape) with explicit `Path.resolve().is_relative_to(install_root.resolve())` checks per member.

- [ ] **Step 7: Add `latest_release()` helper**

Implement `latest_release()` that queries `https://api.github.com/repos/colbymchenry/codegraph/releases/latest` (no auth) and returns `(tag_name, {asset_name: (url, sha256_or_None)})`. SHA256s are read from a `*.sha256` companion asset if present; otherwise return `None` and let the caller decide whether to proceed without verification. Add a test that mocks the GitHub API.

- [ ] **Step 8: Run GREEN tests**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codegraph_installer.py -q`

Expected: PASS.

## Task 9: Per-Project Auto-Init

**Files:**
- Modify: `apps/backend/plugins/system/codebase-intelligence/codebase_intelligence/installer.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/plugin.py`
- Modify: `tests/test_codebase_intelligence.py`

- [ ] **Step 1: Add RED auto-init test**

Add a test using a fake `codegraph` binary (a shell script that creates `.codegraph/codegraph.db` and prints `ok`) proving:
1. When `binary_path()` resolves to the fake script and the project has no `.codegraph/`, `ensure_project_indexed(project_dir, binary)` runs the binary with `init --non-interactive` (whatever the verified flag is — see Step 2) and waits for completion with a bounded timeout.
2. When `.codegraph/codegraph.db` already exists, the function is a no-op.
3. When the binary exits non-zero, the function returns `False` and writes a `plugin_traces/codebase-intelligence.jsonl` event with `auto_init_failed`, but does not raise.

- [ ] **Step 2: Verify the non-interactive `init` flag**

Before implementing Step 3, check the actual CodeGraph CLI surface:
```
codegraph init --help
```
The plan currently assumes `init -i` is interactive and a non-interactive equivalent exists (likely `init` without `-i` or `init --yes`). Update Step 3 with the verified flag name and add the verification command output as a comment above the `subprocess.run` call.

- [ ] **Step 3: Implement `ensure_project_indexed()`**

In `installer.py`, add `ensure_project_indexed(project_dir, binary, timeout=120)` that:
- Returns immediately if `.codegraph/codegraph.db` exists.
- Runs `subprocess.run([binary, "init", <verified-non-interactive-flag>], cwd=project_dir, timeout=timeout, capture_output=True)`.
- On success, returns `True`. On failure, logs the stderr tail and returns `False`.
- Is fully synchronous — agent startup blocks for the (one-time) init.

- [ ] **Step 4: Wire auto-init into the plugin**

In `CodebaseIntelligencePlugin._backend(context)`, when `binary_path()` resolves and `.codegraph/codegraph.db` is missing, call `ensure_project_indexed()` synchronously **before** constructing `CodeGraphBackend`. If it fails, drop to `SidecarBackend` and record the reason in the trace event.

- [ ] **Step 5: Run GREEN tests**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_codebase_intelligence.py tests/test_codegraph_installer.py -q`

Expected: PASS.

## Task 10: Auto-Install Trigger and Plugin CLI

**Files:**
- Modify: `apps/backend/plugins/cli.py`
- Modify: `apps/backend/plugins/system/codebase-intelligence/plugin.py`
- Modify: `apps/backend/core/client.py`
- Modify: `tests/test_plugin_cli.py`
- Modify: `tests/test_codebase_intelligence.py`

- [ ] **Step 1: Decide auto-install policy**

We do **not** download a third-party binary without explicit consent. Therefore:
- Auto-install at session start is **off by default**.
- Opt-in via env var `AUTO_CLAUDE_CODEGRAPH_AUTOINSTALL=1`, project setting, or explicit CLI command.
- When off, the plugin still **detects need** (project has Go/Rust/Java/etc. and no codegraph binary) and emits a one-line guidance into `augment_prompt()` plus a `plugin_traces` event with `suggestion: install_codegraph`.

Add a test asserting all three: opt-in respected, off-by-default emits suggestion, opt-in actually invokes the installer.

- [ ] **Step 2: Add `plugins codegraph ...` subcommand group**

Extend `plugins/cli.py` with a `codegraph` subcommand:
- `plugins codegraph install [--version <tag>] [--force] [--no-verify]` — runs the installer Task 8.
- `plugins codegraph status [--json]` — reports binary path, version, and whether the current project is indexed.
- `plugins codegraph init [--project <path>]` — runs `ensure_project_indexed()` manually.
- `plugins codegraph uninstall [--purge-projects]` — removes `~/.auto-claude/bin/codegraph/`; with `--purge-projects` also walks known project dirs and removes `.codegraph/`.

Each command must have RED tests in `tests/test_plugin_cli.py` for argparse wiring and dispatch.

- [ ] **Step 3: Implement the subcommand handlers**

Handlers are thin wrappers over `installer.py` functions. Keep all download and subprocess logic inside `installer.py` for testability.

- [ ] **Step 4: Resolve binary in `core/client.py`**

When registering the external `codegraph` MCP server (from Task 5), resolution order is:
1. Auto-Coding-managed install: `~/.auto-claude/bin/codegraph/<latest>/<bin>`.
2. `shutil.which("codegraph")` (system install via npm or official installer).
3. None → skip registration and emit suggestion via plugin prompt.

Add a test for each resolution branch.

- [ ] **Step 5: Run GREEN tests**

Run: `apps/backend/.venv/bin/python -m pytest tests/test_plugin_cli.py tests/test_codebase_intelligence.py tests/test_client.py -q`

Expected: PASS.

## Task 11: Frontend Status and Install Action

**Files:**
- Modify: `apps/frontend/src/preload/api/plugin-api.ts`
- Modify: `apps/frontend/src/shared/constants/ipc.ts`
- Modify: `apps/frontend/src/shared/types/ipc.ts`
- Modify: `apps/frontend/src/renderer/components/plugins/PluginCard.tsx`
- Modify: `apps/frontend/src/shared/i18n/locales/en/plugins.json`
- Modify: `apps/frontend/src/shared/i18n/locales/fr/plugins.json`

- [ ] **Step 1: IPC contract for codegraph status**

Add an IPC channel `plugin:codegraph-status` (and matching preload `getCodegraphStatus(projectPath)`). It invokes `plugins/cli.py codegraph status --json`. Add an IPC handler test in the Electron main process.

- [ ] **Step 2: IPC contract for install/init/uninstall**

Add channels `plugin:codegraph-install`, `plugin:codegraph-init`, `plugin:codegraph-uninstall` that invoke the corresponding CLI subcommands. Stream stdout/stderr lines back to the renderer so the UI can show install progress (mirror the pattern used by spec runs if such streaming already exists; otherwise return the final result and a tail of last 50 stdout lines).

- [ ] **Step 3: Status pill in `PluginCard.tsx`**

For the `codebase-intelligence` plugin card (and only that card), render a sub-row with the four states:
- 🟢 `codegraph: ready (vX.Y.Z, project indexed)` — no action button.
- 🟡 `codegraph: binary ready, project not indexed` — button `Run codegraph init` calls `getCodegraphInit(projectPath)`.
- 🟠 `codegraph: not installed` — button `Install CodeGraph` calls `getCodegraphInstall()` (shows a confirmation dialog with the download URL and size first, **never silent**).
- ⚪ `codegraph: not needed (project is Python/TS only)` — informational, no button.

All strings go through i18n; never hardcoded. The decision between 🟢/🟡/🟠/⚪ comes from the IPC status response — do not duplicate detection logic in the renderer.

- [ ] **Step 4: Confirmation dialog before install**

Implement the install confirmation dialog with: download size, release tag, GitHub URL, SHA256 (if present). User must explicitly click `Install`. This is the consent boundary — no automatic third-party downloads without a click.

- [ ] **Step 5: Add minimal renderer test**

Add a Vitest component test rendering `PluginCard` with each of the four status states and asserting the correct button/label combination appears.

- [ ] **Step 6: Verify**

Run:
```
apps/backend/.venv/bin/python -m pytest tests/test_plugin_cli.py tests/test_codegraph_installer.py tests/test_codebase_intelligence.py tests/test_client.py -q
npm --prefix apps/frontend test -- src/renderer/components/plugins/PluginCard.test.tsx
npm --prefix apps/frontend run typecheck
/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff check apps/backend/plugins apps/backend/core/client.py
/Users/om/PycharmProjects/Auto-Coding/.venv/bin/ruff format --check apps/backend/plugins apps/backend/core/client.py
```

Expected: PASS.

## Task 12: End-to-End Auto-Install Verification

**Files:**
- No additional production files.

- [ ] **Step 1: Clean-slate install via CLI**

On a machine without any `codegraph` binary:
1. Run `python -m apps.backend.plugins.cli codegraph install --json`.
2. Verify `~/.auto-claude/bin/codegraph/<version>/codegraph` exists and is executable.
3. Verify `python -m apps.backend.plugins.cli codegraph status --json` reports `installed=true`, `project_indexed=false`.
4. Run `python -m apps.backend.plugins.cli codegraph init`.
5. Verify `.codegraph/codegraph.db` was created.
6. Start a coder session and confirm `backend: codegraph` in `plugin_traces`.

- [ ] **Step 2: Clean-slate install via Electron UI**

1. Fresh app start, no codegraph installed.
2. Open `PluginManager`, observe 🟠 `codegraph: not installed` pill on `codebase-intelligence` card.
3. Click `Install CodeGraph` → confirm dialog → install completes → pill turns 🟡.
4. Click `Run codegraph init` → pill turns 🟢.

- [ ] **Step 3: Mixed-language project sanity**

In a project that mixes Python and Go (e.g. a small monorepo):
1. Verify `augment_prompt()` mentions both `mcp__codebase-intelligence-integration__*` (for briefing) and `mcp__codegraph__*` (for Go queries).
2. Verify the agent transcript actually uses `mcp__codegraph__codegraph_search` for Go symbols.

- [ ] **Step 4: Uninstall verification**

1. Run `python -m apps.backend.plugins.cli codegraph uninstall`.
2. Verify `~/.auto-claude/bin/codegraph/` is removed.
3. Verify `.codegraph/` in the test project remains (was not purged).
4. Run with `--purge-projects` and verify `.codegraph/` is also removed.
