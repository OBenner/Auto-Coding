# Multi-Codebase Orchestration

**Manage multiple related codebases (monorepos, microservices, libraries) from a single Auto Claude instance.**

---

## Table of Contents

- [Overview](#overview)
- [Why Use Multi-Codebase Orchestration](#why-use-multi-codebase-orchestration)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Usage Guide](#usage-guide)
- [Examples](#examples)
- [API Reference](#api-reference)
- [Advanced Topics](#advanced-topics)
- [Troubleshooting](#troubleshooting)

---

## Overview

Multi-codebase orchestration allows you to work with multiple related codebases simultaneously. This feature enables coordinated changes across repositories, tracks dependencies between projects, and maintains isolated state for each project.

### Key Capabilities

- **Multi-Project Workspaces**: Add multiple project directories to a single workspace
- **Cross-Project Specs**: Reference and modify code across multiple projects in a single spec
- **Dependency Tracking**: Define and respect relationships between projects
- **Coordinated Operations**: Create coordinated commits/PRs across repositories
- **Per-Project Isolation**: Each project gets its own worktrees, specs, and state
- **Backward Compatible**: Single-project mode continues to work as before

---

## Why Use Multi-Codebase Orchestration

### Use Cases

#### 1. Microservices Architecture
Update an API and all its clients in one spec to keep changes synchronized:
```
Workspace: "payment-system"
├── api-gateway (depends on: shared-types)
├── payment-service (depends on: shared-types)
├── notification-service (depends on: shared-types)
└── shared-types (library)
```

#### 2. Monorepo Management
Manage packages within a monorepo with dependency tracking:
```
Workspace: "acme-monorepo"
├── @acme/ui-components (library)
├── @acme/utils (library)
├── web-app (depends on: ui-components, utils)
└── mobile-app (depends on: ui-components, utils)
```

#### 3. Library + Examples
Keep library and example projects in sync:
```
Workspace: "react-charts"
├── react-charts (library)
├── docs-site (depends on: react-charts)
└── example-gallery (depends on: react-charts)
```

#### 4. Full-Stack Applications
Coordinate changes across frontend, backend, and shared code:
```
Workspace: "ecommerce-platform"
├── frontend (depends on: types)
├── backend (depends on: types)
├── types (library)
└── mobile (depends on: types)
```

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Auto Claude Workspace                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Project A   │  │  Project B   │  │  Project C   │      │
│  │              │  │              │  │              │      │
│  │ Config       │  │ Config       │  │ Config       │      │
│  │ State        │  │ State        │  │ State        │      │
│  │ Worktrees    │  │ Worktrees    │  │ Worktrees    │      │
│  │ Specs        │  │ Specs        │  │ Specs        │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                 │                 │               │
│         └─────────────────┴─────────────────┘               │
│                           │                                 │
│                  ┌────────▼────────┐                        │
│                  │ Workspace Config │                        │
│                  │  - Dependencies  │                        │
│                  │  - Build Order   │                        │
│                  │  - State Mgmt    │                        │
│                  └─────────────────┘                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Backend Components

#### 1. WorkspaceConfig (`core/workspace_config.py`)
Defines the structure of a multi-project workspace:
- **ProjectConfig**: Configuration for individual projects
- **ProjectRelationship**: Dependency relationships between projects
- **WorkspaceConfig**: Container for all project configurations

#### 2. WorkspaceManager (`core/workspace_manager.py`)
Manages workspace lifecycle:
- Create/load/save workspaces
- Per-project state isolation
- Coordinated operations across projects
- Workspace persistence and validation

#### 3. Spec Runner Integration (`runners/spec_runner.py`)
Enables multi-project specs:
- Auto-detect workspaces
- Save workspace context to `workspace_context.json`
- Support `--workspace` CLI argument

#### 4. Agent Context (`agents/utils.py`)
Provides workspace context to agents:
- `load_workspace_context()`: Load workspace configuration
- `get_workspace_project_dirs()`: Get all project paths

#### 5. WorktreeManager Updates (`core/worktree.py`)
Per-project worktree isolation:
- Multi-project mode: `.auto-claude/workspaces/{workspace}/projects/{project}/worktrees/`
- Single-project mode: `.auto-claude/worktrees/tasks/` (backward compatible)

### Frontend Components

#### 1. WorkspaceStore (`main/workspace-store.ts`)
Manages workspace data with:
- Persistent storage to `userData/workspaces/workspaces.json`
- Atomic write pattern with backup recovery
- Workspace lifecycle operations
- Dependency tracking and build order calculation

#### 2. IPC Handlers (`main/ipc-handlers/workspace-handlers.ts`)
Exposes workspace operations:
- `WORKSPACE_LIST`, `WORKSPACE_GET`, `WORKSPACE_CREATE`
- `WORKSPACE_UPDATE`, `WORKSPACE_DELETE`, `WORKSPACE_RENAME`
- `WORKSPACE_ADD_PROJECT`, `WORKSPACE_REMOVE_PROJECT`
- `WORKSPACE_UPDATE_PROJECT`, `WORKSPACE_GET_BUILD_ORDER`

#### 3. ProjectStore Integration (`main/project-store.ts`)
Links projects to workspaces:
- Optional `workspaceName` field on projects
- Methods to get projects by workspace
- Associate/dissociate projects with workspaces

### Directory Structure

```
.auto-claude/
├── workspaces/
│   └── {workspace-name}/
│       ├── workspace.json          # Workspace configuration
│       └── projects/
│           ├── {project-a}/
│           │   ├── worktrees/      # Git worktrees for project A
│           │   ├── specs/          # Spec state for project A
│           │   ├── cache/          # Cache for project A
│           │   └── logs/           # Logs for project A
│           └── {project-b}/
│               ├── worktrees/      # Git worktrees for project B
│               └── ...
└── worktrees/                      # Single-project mode (legacy)
    └── tasks/
```

---

## Getting Started

### Prerequisites

- Auto Claude installed and configured
- Multiple git repositories you want to manage together
- Claude API token configured

### Create Your First Workspace

#### Option 1: CLI (Backend)

```bash
cd apps/backend

# Create a workspace interactively
python -c "
from core.workspace_manager import WorkspaceManager
from pathlib import Path

# Create workspace
manager = WorkspaceManager.create_workspace(
    name='my-workspace',
    base_dir=Path('.auto-claude/workspaces')
)

# Add projects
manager.add_project(
    name='frontend',
    path='/path/to/frontend',
    description='React frontend application'
)

manager.add_project(
    name='backend',
    path='/path/to/backend',
    description='Python API server',
    relationship='independent'
)

manager.add_project(
    name='shared-types',
    path='/path/to/shared-types',
    description='Shared TypeScript types',
    relationship='library'
)

# Set dependencies
manager.set_dependency('frontend', ['shared-types'])
manager.set_dependency('backend', ['shared-types'])

# Save workspace
manager.save()
print(f'✓ Workspace created: {manager.config.name}')
"
```

#### Option 2: Frontend (Desktop App)

1. **Open Auto Claude desktop app**
2. **Navigate to Workspace Management** (in settings or project panel)
3. **Create New Workspace**:
   - Name: `my-workspace`
   - Description: `Full-stack application workspace`
4. **Add Projects**:
   - Click "Add Project"
   - Select project directory
   - Set relationship type
   - Define dependencies
5. **Save Workspace**

### Create a Multi-Project Spec

```bash
cd apps/backend

# Create spec with workspace context
python run.py --spec-create --workspace my-workspace

# Or manually create spec file
cat > .auto-claude/specs/001-sync-types/spec.md << 'EOF'
# Sync Type Definitions

Update the User type definition in shared-types and propagate changes to frontend and backend.

## Changes Required

### shared-types
- Add `emailVerified` boolean field to User type
- Add `lastLoginAt` timestamp field

### frontend
- Update user profile component to display new fields
- Update user list to show verification status

### backend
- Update user model to include new fields
- Add migration for database schema
- Update API responses

## Acceptance Criteria
- [ ] Type definitions match across all projects
- [ ] Frontend components use new fields
- [ ] Backend API returns new fields
- [ ] Tests pass in all projects
EOF

# Run the spec with workspace context
python run.py --spec 001 --workspace my-workspace
```

---

## Usage Guide

### CLI Commands

#### List Workspaces

```bash
python -c "
from core.workspace import list_workspaces

workspaces = list_workspaces()
for ws in workspaces:
    print(f'- {ws.name}: {len(ws.projects)} projects')
"
```

#### Get Workspace Info

```bash
python -c "
from core.workspace import get_workspace_config

config = get_workspace_config('my-workspace')
print(f'Workspace: {config.name}')
print(f'Projects: {len(config.projects)}')
for project in config.projects:
    print(f'  - {project.name}: {project.path}')
"
```

#### Add Project to Workspace

```bash
python -c "
from core.workspace import get_workspace_manager

manager = get_workspace_manager('my-workspace')
manager.add_project(
    name='mobile-app',
    path='/path/to/mobile-app',
    relationship='depends_on',
    dependencies=['shared-types']
)
manager.save()
print('✓ Project added')
"
```

#### Get Build Order

```bash
python -c "
from core.workspace import get_workspace_config

config = get_workspace_config('my-workspace')
build_order = config.get_build_order()
print('Build order:')
for i, project_name in enumerate(build_order, 1):
    print(f'  {i}. {project_name}')
"
```

#### Run Spec with Workspace

```bash
# Run spec in workspace context
python run.py --spec 001 --workspace my-workspace

# The spec runner will:
# 1. Load workspace configuration
# 2. Save workspace context to spec directory
# 3. Make all project paths available to agents
# 4. Create per-project worktrees
```

### Agent API

Within your agents, access workspace context:

```python
from agents import load_workspace_context, get_workspace_project_dirs

# Load workspace context
workspace = load_workspace_context(spec_dir)

if workspace:
    print(f"Running in workspace: {workspace['name']}")

    # Get all project directories
    project_dirs = get_workspace_project_dirs(spec_dir)

    for project_name, project_path in project_dirs.items():
        print(f"  {project_name}: {project_path}")

    # Access specific project
    frontend_path = project_dirs.get('frontend')
    if frontend_path:
        # Work with frontend project
        pass
else:
    # Single-project mode
    print("Running in single-project mode")
```

### Frontend IPC API

Access workspace operations from renderer process:

```typescript
import { ipcRenderer } from 'electron';

// List all workspaces
const workspaces = await ipcRenderer.invoke('WORKSPACE_LIST');

// Get specific workspace
const workspace = await ipcRenderer.invoke('WORKSPACE_GET', 'my-workspace');

// Create workspace
await ipcRenderer.invoke('WORKSPACE_CREATE', {
  name: 'new-workspace',
  description: 'My new workspace',
  projects: [
    { name: 'project-a', path: '/path/to/a' },
    { name: 'project-b', path: '/path/to/b' }
  ]
});

// Add project to workspace
await ipcRenderer.invoke('WORKSPACE_ADD_PROJECT', {
  workspaceName: 'my-workspace',
  project: {
    name: 'project-c',
    path: '/path/to/c',
    relationship: 'depends_on',
    dependencies: ['project-a']
  }
});

// Get build order
const buildOrder = await ipcRenderer.invoke('WORKSPACE_GET_BUILD_ORDER', 'my-workspace');
console.log('Build order:', buildOrder);
```

---

## Examples

### Example 1: Microservices Update

**Scenario**: Update authentication logic across API gateway and multiple services.

```bash
# Create workspace
python -c "
from core.workspace_manager import WorkspaceManager
from pathlib import Path

manager = WorkspaceManager.create_workspace(
    name='auth-update',
    base_dir=Path('.auto-claude/workspaces')
)

manager.add_project('api-gateway', '/repos/api-gateway')
manager.add_project('user-service', '/repos/user-service')
manager.add_project('payment-service', '/repos/payment-service')
manager.add_project('auth-lib', '/repos/auth-lib', relationship='library')

manager.set_dependency('api-gateway', ['auth-lib'])
manager.set_dependency('user-service', ['auth-lib'])
manager.set_dependency('payment-service', ['auth-lib'])

manager.save()
"

# Create spec
cat > .auto-claude/specs/042-jwt-refresh/spec.md << 'EOF'
# Implement JWT Refresh Token Flow

Add refresh token support to authentication library and update all services.

## Changes

### auth-lib
- Add refresh token generation
- Add refresh token validation
- Add token rotation logic

### api-gateway
- Add /auth/refresh endpoint
- Update authentication middleware

### user-service, payment-service
- Update token validation to support refresh
- Add refresh token storage

## Acceptance Criteria
- [ ] Refresh tokens work in all services
- [ ] Token rotation prevents replay attacks
- [ ] All tests pass
EOF

# Run spec
python run.py --spec 042 --workspace auth-update
```

### Example 2: Monorepo Package Update

**Scenario**: Update shared UI component and propagate to all apps.

```bash
# Create workspace for monorepo
python -c "
from core.workspace_manager import WorkspaceManager
from pathlib import Path

manager = WorkspaceManager.create_workspace(
    name='acme-monorepo',
    base_dir=Path('.auto-claude/workspaces')
)

manager.add_project('ui-components', '/repos/acme/packages/ui', relationship='library')
manager.add_project('web-app', '/repos/acme/apps/web',
                   relationship='monorepo_package', dependencies=['ui-components'])
manager.add_project('admin-app', '/repos/acme/apps/admin',
                   relationship='monorepo_package', dependencies=['ui-components'])
manager.add_project('mobile-app', '/repos/acme/apps/mobile',
                   relationship='monorepo_package', dependencies=['ui-components'])

manager.save()
"

# Create spec
cat > .auto-claude/specs/050-button-update/spec.md << 'EOF'
# Update Button Component

Add loading state and icon support to Button component.

## Changes

### ui-components
- Add `loading` prop to Button
- Add `icon` and `iconPosition` props
- Update Button styles

### web-app, admin-app, mobile-app
- Update Button imports
- Add loading states to form buttons
- Add icons to action buttons

## Acceptance Criteria
- [ ] Button component has new props
- [ ] All apps use updated Button
- [ ] Storybook stories updated
- [ ] All tests pass
EOF

# Run spec
python run.py --spec 050 --workspace acme-monorepo
```

### Example 3: Library + Docs Sync

**Scenario**: Add new feature to library and document it.

```bash
# Create workspace
python -c "
from core.workspace_manager import WorkspaceManager
from pathlib import Path

manager = WorkspaceManager.create_workspace(
    name='react-charts',
    base_dir=Path('.auto-claude/workspaces')
)

manager.add_project('library', '/repos/react-charts', relationship='library')
manager.add_project('docs', '/repos/react-charts-docs', dependencies=['library'])
manager.add_project('examples', '/repos/react-charts-examples', dependencies=['library'])

manager.save()
"

# Create spec
cat > .auto-claude/specs/060-pie-chart/spec.md << 'EOF'
# Add Pie Chart Component

Implement PieChart component with docs and examples.

## Changes

### library
- Create PieChart component
- Add tests for PieChart
- Export from index

### docs
- Add PieChart API documentation
- Add PieChart usage guide
- Add interactive examples

### examples
- Add basic pie chart example
- Add customized pie chart example
- Add animated pie chart example

## Acceptance Criteria
- [ ] PieChart component works
- [ ] Documentation is complete
- [ ] Examples run successfully
- [ ] All tests pass
EOF

# Run spec
python run.py --spec 060 --workspace react-charts
```

---

## API Reference

### WorkspaceConfig

```python
from core.workspace_config import WorkspaceConfig, ProjectConfig, ProjectRelationship

# Create project config
project = ProjectConfig(
    name="frontend",
    path="/path/to/frontend",
    enabled=True,
    relationship=ProjectRelationship.DEPENDS_ON,
    dependencies=["shared"],
    description="React frontend",
    tags=["typescript", "react"]
)

# Create workspace config
workspace = WorkspaceConfig(
    name="my-workspace",
    projects=[project],
    description="My workspace"
)

# Get project
project = workspace.get_project("frontend")

# Find project by path
project = workspace.find_project_by_path("/path/to/frontend/src/App.tsx")

# Get build order (topological sort)
build_order = workspace.get_build_order()
# Returns: ["shared", "frontend"]

# Validate (checks for circular dependencies)
is_valid, errors = workspace.validate()
```

### WorkspaceManager

```python
from core.workspace_manager import WorkspaceManager
from pathlib import Path

# Create workspace
manager = WorkspaceManager.create_workspace(
    name="my-workspace",
    base_dir=Path(".auto-claude/workspaces"),
    description="My workspace"
)

# Add project
manager.add_project(
    name="frontend",
    path="/path/to/frontend",
    relationship="depends_on",
    dependencies=["shared"],
    description="Frontend app",
    tags=["typescript"]
)

# Remove project
manager.remove_project("frontend")

# Update project
manager.update_project(
    name="frontend",
    enabled=False
)

# Set dependency
manager.set_dependency("frontend", ["shared", "api-client"])

# Get project state
state = manager.get_project_state("frontend")
print(state.worktree_dir)  # Path to worktrees
print(state.spec_dir)      # Path to specs

# Get build order
build_order = manager.get_build_order()

# Validate
is_valid, errors = manager.validate()

# Save
manager.save()

# Load
manager = WorkspaceManager.load_workspace(
    Path(".auto-claude/workspaces/my-workspace")
)
```

### Workspace Utilities

```python
from core.workspace import (
    get_workspace_config,
    get_workspace_manager,
    find_workspace_for_project,
    list_workspaces
)

# Get workspace config
config = get_workspace_config("my-workspace")

# Get workspace manager
manager = get_workspace_manager("my-workspace")

# Find workspace containing a project path
workspace_name = find_workspace_for_project("/path/to/frontend")

# List all workspaces
workspaces = list_workspaces()
for workspace in workspaces:
    print(f"{workspace.name}: {len(workspace.projects)} projects")
```

### Agent Context API

```python
from agents import load_workspace_context, get_workspace_project_dirs

# Load workspace context (from workspace_context.json)
workspace = load_workspace_context(spec_dir)
if workspace:
    print(workspace["name"])
    print(workspace["projects"])

# Get project directories
project_dirs = get_workspace_project_dirs(spec_dir)
# Returns: {"frontend": "/path/to/frontend", "backend": "/path/to/backend"}

# Use in agent
for project_name, project_path in project_dirs.items():
    print(f"Working on {project_name} at {project_path}")
```

### WorktreeManager (Multi-Project Mode)

```python
from core.worktree import WorktreeManager

# Single-project mode (default)
wt_manager = WorktreeManager(project_dir="/path/to/project")
# Uses: .auto-claude/worktrees/tasks/

# Multi-project mode
wt_manager = WorktreeManager(
    project_dir="/path/to/frontend",
    workspace_name="my-workspace",
    project_name="frontend"
)
# Uses: .auto-claude/workspaces/my-workspace/projects/frontend/worktrees/
```

---

## Advanced Topics

### Dependency Graph

The workspace system uses topological sorting to determine build order:

```python
# Define dependencies
workspace.projects = [
    ProjectConfig("shared", "/path/shared", relationship="library"),
    ProjectConfig("api", "/path/api", dependencies=["shared"]),
    ProjectConfig("web", "/path/web", dependencies=["shared", "api-client"]),
    ProjectConfig("api-client", "/path/client", dependencies=["shared"]),
]

# Get build order
build_order = workspace.get_build_order()
# Returns: ["shared", "api-client", "api", "web"]
```

### Circular Dependency Detection

```python
# This will fail validation
workspace.projects = [
    ProjectConfig("a", "/path/a", dependencies=["b"]),
    ProjectConfig("b", "/path/b", dependencies=["c"]),
    ProjectConfig("c", "/path/c", dependencies=["a"]),  # Circular!
]

is_valid, errors = workspace.validate()
# is_valid = False
# errors = ["Circular dependency detected: a -> b -> c -> a"]
```

### Per-Project State Isolation

Each project gets its own state directory:

```
.auto-claude/workspaces/my-workspace/projects/
├── frontend/
│   ├── worktrees/       # Git worktrees for frontend
│   │   └── tasks/
│   │       └── 001-feature/
│   ├── specs/           # Spec state for frontend
│   │   └── 001-feature/
│   ├── cache/           # Cache for frontend
│   └── logs/            # Logs for frontend
└── backend/
    ├── worktrees/       # Git worktrees for backend
    ├── specs/
    ├── cache/
    └── logs/
```

This isolation ensures:
- No conflicts between projects
- Parallel operations are safe
- Clean separation of concerns

### Workspace Persistence

Workspaces are saved as JSON:

```json
{
  "name": "my-workspace",
  "version": "1.0.0",
  "description": "My workspace",
  "projects": [
    {
      "name": "frontend",
      "path": "/path/to/frontend",
      "enabled": true,
      "relationship": "depends_on",
      "dependencies": ["shared"],
      "description": "React frontend",
      "tags": ["typescript", "react"]
    }
  ],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Atomic Writes with Backup

WorkspaceStore uses atomic write pattern:

1. Write to `.tmp` file
2. Backup existing file to `.backup`
3. Rename `.tmp` to final filename
4. Remove backup on success

This ensures data integrity even if the process crashes.

---

## Troubleshooting

### "Workspace not found"

**Problem**: Cannot load workspace.

**Solution**:
```bash
# List available workspaces
python -c "from core.workspace import list_workspaces; print([w.name for w in list_workspaces()])"

# Check workspace directory exists
ls -la .auto-claude/workspaces/
```

### "Circular dependency detected"

**Problem**: Projects have circular dependencies.

**Solution**: Review and fix dependency graph:
```bash
python -c "
from core.workspace import get_workspace_config

config = get_workspace_config('my-workspace')
is_valid, errors = config.validate()
if not is_valid:
    for error in errors:
        print(f'ERROR: {error}')
"
```

### "Project path not found"

**Problem**: Project path doesn't exist or isn't accessible.

**Solution**: Verify paths:
```bash
python -c "
from core.workspace import get_workspace_config
from pathlib import Path

config = get_workspace_config('my-workspace')
for project in config.projects:
    path = Path(project.path)
    if not path.exists():
        print(f'MISSING: {project.name} at {project.path}')
    elif not path.is_dir():
        print(f'NOT A DIR: {project.name} at {project.path}')
    else:
        print(f'OK: {project.name}')
"
```

### "Cannot save workspace"

**Problem**: Permission error or disk full.

**Solution**:
```bash
# Check permissions
ls -la .auto-claude/workspaces/

# Check disk space
df -h

# Try manual save with error handling
python -c "
from core.workspace import get_workspace_manager

try:
    manager = get_workspace_manager('my-workspace')
    manager.save()
    print('✓ Saved successfully')
except Exception as e:
    print(f'ERROR: {e}')
"
```

### "Spec not finding workspace context"

**Problem**: Agent can't load workspace context.

**Solution**: Verify workspace context was saved:
```bash
# Check if workspace_context.json exists
ls -la .auto-claude/specs/001-my-spec/workspace_context.json

# If missing, re-run spec with --workspace flag
python run.py --spec 001 --workspace my-workspace
```

### "Worktree path conflicts"

**Problem**: Worktree paths overlap between projects.

**Solution**: Workspace system automatically isolates worktrees:
```bash
# Single-project mode
.auto-claude/worktrees/tasks/001-feature/

# Multi-project mode (automatic)
.auto-claude/workspaces/my-workspace/projects/frontend/worktrees/tasks/001-feature/
.auto-claude/workspaces/my-workspace/projects/backend/worktrees/tasks/001-feature/
```

No action needed - system handles this automatically.

---

## Best Practices

### 1. Use Descriptive Names

```python
# Good
manager.add_project("payment-api", "/repos/payment-service")
manager.add_project("payment-web", "/repos/payment-dashboard")

# Bad
manager.add_project("proj1", "/repos/service1")
manager.add_project("proj2", "/repos/service2")
```

### 2. Define Clear Dependencies

```python
# Good - explicit and accurate
manager.add_project("shared-types", "/repos/types", relationship="library")
manager.add_project("api", "/repos/api", dependencies=["shared-types"])
manager.add_project("web", "/repos/web", dependencies=["shared-types"])

# Bad - missing or incorrect dependencies
manager.add_project("api", "/repos/api")  # Missing dependency
manager.add_project("web", "/repos/web", dependencies=["api"])  # Wrong dependency
```

### 3. Use Tags for Organization

```python
manager.add_project(
    "payment-service",
    "/repos/payment",
    tags=["microservice", "python", "critical"]
)

manager.add_project(
    "analytics-service",
    "/repos/analytics",
    tags=["microservice", "python", "non-critical"]
)
```

### 4. Keep Workspaces Focused

```python
# Good - related projects
Workspace: "payment-system"
- payment-api
- payment-web
- payment-types

# Bad - unrelated projects
Workspace: "all-projects"
- payment-api
- user-management
- analytics-dashboard
- mobile-app
```

### 5. Document Relationships

```python
manager.add_project(
    "api-gateway",
    "/repos/gateway",
    description="Main API gateway - routes to all services",
    relationship="depends_on",
    dependencies=["auth-service", "payment-service"]
)
```

---

## Migration Guide

### From Single-Project to Multi-Project

If you're currently using Auto Claude in single-project mode:

#### Step 1: Create Workspace

```bash
python -c "
from core.workspace_manager import WorkspaceManager
from pathlib import Path

# Create workspace
manager = WorkspaceManager.create_workspace(
    name='my-workspace',
    base_dir=Path('.auto-claude/workspaces')
)

# Add your current project
manager.add_project(
    name='main-project',
    path='/path/to/current/project',
    description='Main project'
)

manager.save()
print('✓ Workspace created')
"
```

#### Step 2: Run Existing Specs

Your existing specs continue to work:

```bash
# Single-project mode (still works)
python run.py --spec 001

# Or use explicit workspace
python run.py --spec 001 --workspace my-workspace
```

#### Step 3: Add More Projects

```bash
python -c "
from core.workspace import get_workspace_manager

manager = get_workspace_manager('my-workspace')
manager.add_project('second-project', '/path/to/second')
manager.save()
"
```

**No breaking changes**: Single-project mode continues to work exactly as before.

---

## Support

For issues or questions:

1. Check this documentation
2. Review [GitHub Issues](https://github.com/AndyMik90/Auto-Claude/issues)
3. Join [Discord Community](https://discord.gg/KCXaPBr4Dj)
4. Create a new issue with:
   - Workspace configuration
   - Error messages
   - Steps to reproduce

---

## License

AGPL-3.0 - See [LICENSE](../agpl-3.0.txt) for details
