# Multi-Codebase Orchestration CLI

Coordinate work across multiple repositories from a single Auto Code workspace. The Multi-Codebase Orchestration CLI manages a shared workspace, tracks cross-repo dependencies, and enables multi-repo builds.

## CLI Commands

### Workspace Management

```bash
cd apps/backend

# Initialize a multi-repo workspace
python cli/main.py --workspace init --workspace-name "my-platform"

# Add a project to the workspace
python cli/main.py --workspace add --workspace-dir /path/to/workspace \
  --project-path /path/to/repo --project-role backend

# List projects in the workspace
python cli/main.py --workspace list --workspace-dir /path/to/workspace

# Remove a project
python cli/main.py --workspace remove --workspace-dir /path/to/workspace \
  --project-name my-repo

# Analyze cross-repo dependency graph
python cli/main.py --workspace deps --workspace-dir /path/to/workspace

# Show workspace status
python cli/main.py --workspace status --workspace-dir /path/to/workspace
```

### Project Roles

Projects can be assigned roles for orchestration:

| Role | Description |
|------|-------------|
| `backend` | Backend service (Python, Node.js, etc.) |
| `frontend` | Frontend application |
| `shared` | Shared library consumed by other projects |
| `infra` | Infrastructure/deployment configuration |

## Architecture

### Backend

- **`apps/backend/cli/multi_repo_commands.py`** -- CLI handlers for workspace init, add, remove, list, deps, status
- **`apps/backend/analysis/dependency_graph.py`** -- Cross-repository dependency analysis. Parses `requirements.txt`, `package.json`, `pyproject.toml`, `Cargo.toml`, and `go.mod` to build a directed dependency graph

### Dependency Graph Analysis

The `DependencyGraph` class:
1. Scans each project for package manifest files
2. Extracts declared dependencies with version constraints
3. Detects cross-project dependencies (Project A depends on a package that Project B provides)
4. Builds a directed graph for visualization and build ordering

Supported ecosystems: Python (pip/poetry), Node.js (npm/yarn), Rust (cargo), Go (modules).

## Data Storage

Workspace configuration is stored in `<workspace-dir>/workspace.json`:

```json
{
  "name": "my-platform",
  "projects": [
    {
      "name": "api-service",
      "path": "/path/to/api-service",
      "role": "backend"
    }
  ],
  "created_at": "2026-03-20T12:00:00Z"
}
```
