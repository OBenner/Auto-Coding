# Auto Code Documentation

Central documentation hub for Auto Code architecture, templates, and guides.

## Search & Navigation

**Looking for something specific?**

- **[📖 Search Index](search/INDEX.md)** - Comprehensive searchable index with keywords
- **[🔍 Search Guide](search/SEARCH-GUIDE.md)** - Learn effective search strategies

**Quick links:**
- [Getting Started](../../guides/QUICK-START.md) - New to Auto Code? Start here
- [CLAUDE.md](../../CLAUDE.md) - Architecture for AI agents
- [Contributing](../../CONTRIBUTING.md) - Contribution guidelines

## Documentation Structure

This directory contains comprehensive documentation for understanding, extending, and contributing to Auto Code.

### Directory Organization

| Directory | Purpose |
|-----------|---------|
| **[templates/](templates/)** | Reusable documentation templates for features, architecture, APIs, and guides |
| **[components/](components/)** | Frontend component API documentation (React components, Zustand stores) |
| **[stores/](stores/)** | Zustand store documentation (task-store, kanban-settings-store) |
| **modules/** | Per-module architecture documentation (backend, frontend, memory system, security) |
| **diagrams/** | Architecture diagrams (system overview, spec pipeline, agent workflow) |
| **STYLE_GUIDE.md** | Writing style, formatting conventions, and documentation best practices |

### Available Templates

Templates are organized by documentation type in `docs/templates/`:

#### Feature Documentation

| Template | Purpose | When to Use |
|----------|---------|-------------|
| **[feature/spec.md](templates/feature/)** | Feature specification | When planning a new feature or enhancement |
| **[feature/implementation-guide.md](templates/feature/)** | Implementation details | After implementing a feature to document how it works |
| **[feature/feature-overview.md](templates/feature/)** | User-facing description | For end-user documentation of a feature |

#### Architecture Documentation

| Template | Purpose | When to Use |
|----------|---------|-------------|
| **[architecture/module-architecture.md](templates/architecture/)** | Module documentation | Documenting a specific module or component |
| **[architecture/system-overview.md](templates/architecture/)** | High-level architecture | Documenting system-wide architecture |
| **[architecture/integration-guide.md](templates/architecture/)** | Integration documentation | Documenting third-party integrations (Graphiti, Linear, GitHub) |

#### API Documentation

| Template | Purpose | When to Use |
|----------|---------|-------------|
| **[api/endpoint-documentation.md](templates/api/)** | API endpoint details | Documenting backend API routes |
| **[api/component-api.md](templates/api/)** | Component API | Documenting React components (props, events, usage) |
| **[api/websocket-api.md](templates/api/)** | WebSocket API | Documenting real-time communication endpoints |

#### Guide Templates

| Template | Purpose | When to Use |
|----------|---------|-------------|
| **[guides/user-guide.md](templates/guides/)** | User-facing guides | Creating tutorials or how-to guides for users |
| **[guides/developer-guide.md](templates/guides/)** | Developer guides | Creating guides for developers working on the codebase |
| **[guides/troubleshooting-guide.md](templates/guides/)** | Troubleshooting | Documenting common issues and solutions |

## Quick Start

**Creating new documentation:**

1. Choose the appropriate template from `docs/templates/`
2. Copy the template to your target location
3. Follow the fill-in instructions within the template
4. Review against `docs/STYLE_GUIDE.md` for consistency

**Example:**
```bash
# Document a new feature
cp docs/templates/feature/spec.md .auto-claude/specs/XXX-my-feature/spec.md

# Document a module
cp docs/templates/architecture/module-architecture.md docs/modules/my-module.md

# Document an API endpoint
cp docs/templates/api/endpoint-documentation.md docs/api/my-endpoint.md
```

## Frontend Documentation

Comprehensive API documentation for React components and Zustand stores:

| Category | Documentation |
|----------|---------------|
| **Components** | [KanbanBoard](components/KanbanBoard.md), [Sidebar](components/Sidebar.md), [TaskCard](components/TaskCard.md) |
| **Stores** | [task-store](stores/task-store.md), [kanban-settings-store](stores/kanban-settings-store.md) |
| **Component Index** | [components/README.md](components/README.md) - Full component documentation index |

See **[components/README.md](components/README.md)** for complete frontend component documentation including usage examples, type definitions, and integration patterns.

## Documentation Locations

Auto Code documentation is spread across multiple locations, each serving a specific purpose:

| Location | Purpose | Examples |
|----------|---------|----------|
| **Root README.md** | Project overview, downloads, quick start | Installation, features, requirements |
| **CLAUDE.md** | Comprehensive architecture for AI agents | Project structure, commands, patterns |
| **CONTRIBUTING.md** | Contribution guidelines and dev setup | Development setup, PR process, testing |
| **guides/** | User and developer guides | CLI usage, spec pipeline, platform guides |
| **docs/** | Templates and architecture docs | This directory - templates and deep-dives |
| **apps/backend/** | Backend-specific documentation | Agent implementations, core modules |
| **apps/frontend/** | Frontend-specific documentation | Components, state management, UI patterns |
| **.auto-claude/specs/** | Feature specifications | Individual feature specs created by spec pipeline |

## Style Guidelines

All documentation should follow the conventions defined in **[docs/STYLE_GUIDE.md](STYLE_GUIDE.md)**:

- Clear, concise technical writing
- Code examples with syntax highlighting
- Consistent heading hierarchy
- Tables for structured data
- Markdown best practices

## Naming Conventions

Follow these naming patterns for consistency:

| Documentation Type | Pattern | Example |
|-------------------|---------|---------|
| **Feature specs** | `{number}-{feature-name}` | `094-project-documentation-structure-templates` |
| **Module docs** | `{module-name}-architecture.md` | `backend-architecture.md` |
| **Guide docs** | `{topic}-guide.md` or `{TOPIC}.md` | `developer-guide.md`, `CLI-USAGE.md` |
| **API docs** | `{endpoint-or-component}.md` | `create-spec-endpoint.md` |
| **Templates** | Descriptive lowercase with hyphens | `implementation-guide.md` |

## Maintenance Guidelines

### When to Update Documentation

- **Immediately**: When adding/removing features, changing APIs, or modifying architecture
- **Before PR**: Documentation changes should be part of the same PR as code changes
- **During QA**: QA agents verify documentation completeness

### Documentation Lifecycle

1. **Plan**: Feature spec created in `.auto-claude/specs/`
2. **Implement**: Code changes with inline documentation
3. **Document**: User-facing guides updated in `guides/`
4. **Review**: QA agent verifies documentation completeness
5. **Maintain**: Update as the feature evolves

## Quick Links

- [Main README](../README.md) - Getting started
- [CLAUDE.md](../CLAUDE.md) - Architecture for AI agents
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [guides/](../guides/) - User and developer guides
- [CHANGELOG.md](../CHANGELOG.md) - Release history

## Contributing

When contributing documentation:

1. **Use templates** - Start from `docs/templates/` for consistency
2. **Follow style guide** - Review `docs/STYLE_GUIDE.md` before writing
3. **Include examples** - Code examples and practical use cases
4. **Keep it current** - Update documentation when code changes
5. **Link appropriately** - Use relative links for internal docs

For detailed contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).
