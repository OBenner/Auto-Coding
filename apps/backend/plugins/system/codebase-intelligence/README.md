# Codebase Intelligence Plugin

System integration plugin that builds a deterministic local graph of a project's
Python and TypeScript/JavaScript code. The plugin is intentionally self-contained:
core project analysis does not import or run it directly.

When enabled, Auto Code exposes the plugin to build agents as the
`codebase-intelligence-integration` MCP server through the normal client
configuration path.

## Tools

The plugin exposes these MCP tools to agent sessions:

- `build_codebase_index` - Build or refresh `.auto-claude/codebase_intelligence/index.json`.
- `get_codebase_summary` - Return compact file, symbol, dependency, and language counts.
- `find_file_dependents` - Return files that depend on a project-relative file.
- `find_file_dependencies` - Return resolved imports for a project-relative file.
- `find_symbol_callers` - Return resolved caller symbols and call sites for a symbol.
- `find_symbol_references` - Return lightweight call references for a symbol name.
- `trace_file_impact` - Traverse reverse dependencies and identify test candidates.
- `trace_symbol_impact` - Combine symbol callers with file impact and test candidates.
- `get_dependency_inventory` - Return npm and Python package manifest dependencies.
- `get_module_graph` - Return directory-level module nodes and dependency edges.
- `export_graph_dataset` - Export deterministic graph nodes/edges as JSON or CSV.
- `get_graph_neighbors` - Query incoming/outgoing neighbors for a graph node id.
- `get_index_status` - Report whether the sidecar is missing, fresh, or stale.
- `search_symbols` - Search symbols by name, path, signature, or docstring.

## Current Slice

This first version uses only Python stdlib parsing:

- Python: `ast` for imports, classes, functions, async functions, methods, and
  call references.
- TypeScript/JavaScript: lightweight import/export/require, declaration, and
  call-reference extraction.
- Packages: `package.json`, `pyproject.toml`, and `requirements*.txt`.
- Architecture: module graph grouping by directory depth and impact tracing
  through resolved reverse dependencies.
- Graph export: project/file/module/symbol/package nodes plus contains, defines,
  imports, references, calls, and declares-dependency edges.
- Freshness: source and package manifest fingerprints detect stale sidecars;
  query tools rebuild before answering when indexed sources changed.

This intentionally stays approximate for TypeScript and call graph facts. Future
versions can add Tree-sitter, SCIP/LSP, Semgrep, CodeQL, or a Kuzu graph backend
inside the plugin without expanding the Auto Code core path.
