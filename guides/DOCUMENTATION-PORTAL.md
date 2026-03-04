# Documentation Portal

Comprehensive guide to navigating, searching, and contributing to Auto Code's documentation.

## Overview

Auto Code's documentation portal is organized into multiple interconnected directories, each serving a specific purpose. Whether you're a new user getting started, an advanced developer extending the system, or a contributor writing documentation, this portal helps you find exactly what you need.

## Documentation Structure

```
Auto Code/
├── README.md                    # Project overview, quick start, downloads
├── CLAUDE.md                    # Architecture for AI agents
├── CHANGELOG.md                 # Release history
├── guides/                      # User and developer guides
│   ├── QUICK-START.md          # Get started in 15 minutes
│   ├── CLI-USAGE.md            # Terminal-only usage
│   ├── ADVANCED-USAGE.md       # Advanced patterns and customization
│   ├── AGENT-CUSTOMIZATION.md  # Customize agents and prompts
│   └── DOCUMENTATION-PORTAL.md # This file
├── docs/                         # Technical documentation and templates
│   ├── README.md               # Documentation hub and template guide
│   ├── STYLE_GUIDE.md          # Writing style and conventions
│   ├── search/                 # Search index and strategies
│   │   ├── INDEX.md            # Comprehensive searchable index
│   │   └── SEARCH-GUIDE.md     # Effective search techniques
│   ├── features/               # Feature documentation
│   ├── modules/                # Architecture by module
│   ├── api/                    # API references
│   ├── templates/              # Reusable documentation templates
│   └── integration/            # Integration and testing docs
└── apps/                        # Application-specific documentation
    ├── backend/README.md        # Backend architecture and usage
    └── frontend/README.md       # Frontend architecture and usage
```

## Quick Navigation

### For New Users

| Goal | Document | Location |
|------|----------|----------|
| **Get started** | [Quick Start Guide](QUICK-START.md) | `guides/` |
| **Install Auto Code** | [Main README](../README.md) | Root |
| **First time setup** | [Quick Start Guide](QUICK-START.md) | `guides/` |
| **Understand basics** | [Main README](../README.md) | Root |

### For Users

| Goal | Document | Location |
|------|----------|----------|
| **Terminal usage** | [CLI Usage](CLI-USAGE.md) | `guides/` |
| **Advanced features** | [Advanced Usage](ADVANCED-USAGE.md) | `guides/` |
| **Customize agents** | [Agent Customization](AGENT-CUSTOMIZATION.md) | `guides/` |
| **Troubleshoot issues** | [Troubleshooting](TROUBLESHOOTING.md) | `guides/` |

### For Developers/Contributors

| Goal | Document | Location |
|------|----------|----------|
| **Architecture overview** | [CLAUDE.md](../CLAUDE.md) | Root |
| **Contribution guide** | [CONTRIBUTING.md](../CONTRIBUTING.md) | Root |
| **Backend architecture** | [Backend README](../apps/backend/README.md) | `apps/backend/` |
| **Frontend architecture** | [Frontend README](../apps/frontend/README.md) | `apps/frontend/` |
| **Write documentation** | [Style Guide](../docs/STYLE_GUIDE.md) | `docs/` |
| **Use templates** | [Docs README](../docs/README.md) | `docs/` |

### For Understanding Features

| Goal | Document | Location |
|------|----------|----------|
| **Memory system** | [Memory System](../docs/features/MEMORY-SYSTEM.md) | `docs/features/` |
| **Multi-agent pipeline** | [Multi-Agent Pipeline](../docs/features/MULTI-AGENT-PIPELINE.md) | `docs/features/` |
| **Parallel execution** | [Parallel Execution](../docs/features/PARALLEL-EXECUTION.md) | `docs/features/` |
| **QA loop** | [QA Loop](../docs/features/QA-LOOP.md) | `docs/features/` |
| **GitHub integration** | [GitHub Integration](../docs/features/GITHUB-INTEGRATION.md) | `docs/features/` |

## Search & Discovery

### Primary Search Tools

1. **[Search Index](../docs/search/INDEX.md)** - The most comprehensive search tool
   - Searchable index with keywords
   - Organized by category and topic
   - Quick access tables for common tasks
   - **Start here** when looking for documentation

2. **[Search Guide](../docs/search/SEARCH-GUIDE.md)** - Learn effective search strategies
   - How to search effectively
   - Keyword techniques
   - Category-based browsing
   - Advanced search patterns

### Search Tips

1. **Use the Search Index** - `docs/search/INDEX.md` is your best friend
   - Comprehensive coverage of all documentation
   - Keywords marked in bold for easy scanning
   - Organized by category (Getting Started, Features, API, etc.)
   - Quick reference tables for top searches

2. **Start with your goal** - Ask "What do I want to do?"
   - Install? → [Quick Start](QUICK-START.md)
   - Run commands? → [CLI Usage](CLI-USAGE.md)
   - Customize? → [Agent Customization](AGENT-CUSTOMIZATION.md)
   - Debug? → [Troubleshooting](TROUBLESHOOTING.md)
   - Contribute? → [Contributing](../CONTRIBUTING.md)

3. **Follow the documentation hierarchy** - Start broad, then narrow down
   - Root docs (`README.md`, `CLAUDE.md`) for overview
   - `guides/` for how-to and usage
   - `docs/` for technical details and architecture
   - Module-specific docs (`apps/backend/`, `apps/frontend/`) for deep dives

4. **Use Ctrl+F / Cmd+F** - Search within documents
   - Each document is searchable
   - Use keywords like "memory", "agent", "github", "cloud"

5. **Check related sections** - Look for "See Also" links
   - Documents link to related content
   - Follow the breadcrumbs to discover more

## Documentation by Category

### Getting Started

| Document | Description | Location |
|----------|-------------|----------|
| **[Quick Start](QUICK-START.md)** | Get started in 15 minutes | `guides/` |
| **[Main README](../README.md)** | Project overview, downloads, features | Root |
| **[CLI Usage](CLI-USAGE.md)** | Terminal-only usage | `guides/` |

### Usage Guides

| Document | Description | Location |
|----------|-------------|----------|
| **[Advanced Usage](ADVANCED-USAGE.md)** | Advanced patterns and customization | `guides/` |
| **[Agent Customization](AGENT-CUSTOMIZATION.md)** | Customize agents and prompts | `guides/` |
| **[Spec Creation Pipeline](SPEC-CREATION-PIPELINE.md)** | How specs are created | `guides/` |
| **[Troubleshooting](TROUBLESHOOTING.md)** | Common issues and solutions | `guides/` |

### Architecture & Design

| Document | Description | Location |
|----------|-------------|----------|
| **[CLAUDE.md](../CLAUDE.md)** | Architecture for AI agents | Root |
| **[Backend Architecture](../docs/modules/backend-architecture.md)** | Backend system design | `docs/modules/` |
| **[Frontend Architecture](../docs/modules/frontend-architecture.md)** | Frontend system design | `docs/modules/` |
| **[Memory System](../docs/features/MEMORY-SYSTEM.md)** | Graphiti memory system | `docs/features/` |

### Features

| Document | Description | Location |
|----------|-------------|----------|
| **[Multi-Agent Pipeline](../docs/features/MULTI-AGENT-PIPELINE.md)** | Agent workflow | `docs/features/` |
| **[Parallel Execution](../docs/features/PARALLEL-EXECUTION.md)** | Concurrent task execution | `docs/features/` |
| **[QA Loop](../docs/features/QA-LOOP.md)** | Quality assurance system | `docs/features/` |
| **[GitHub Integration](../docs/features/GITHUB-INTEGRATION.md)** | GitHub automation | `docs/features/` |

### API Documentation

| Document | Description | Location |
|----------|-------------|----------|
| **[Backend API](../docs/api/backend-api.md)** | Python backend endpoints | `docs/api/` |
| **[Web Backend API](../docs/api/web-backend-api.md)** | FastAPI web endpoints | `docs/api/` |
| **[CLI API](../docs/api/CLI-API-REFERENCE.md)** | Command-line API | `docs/api/` |
| **[IPC API](../docs/api/IPC-API-REFERENCE.md)** | Electron IPC communication | `docs/api/` |

### Cloud Deployment

| Document | Description | Location |
|----------|-------------|----------|
| **[Cloud README](CLOUD_README.md)** | Cloud overview and architecture | `guides/` |
| **[Cloud Setup](CLOUD_SETUP.md)** | Initial deployment setup | `guides/` |
| **[Cloud Deployment](CLOUD_DEPLOYMENT.md)** | Production operations | `guides/` |

### Platform-Specific

| Document | Description | Location |
|----------|-------------|----------|
| **[Windows Development](windows-development.md)** | Windows-specific guide | `guides/` |
| **[Linux Guide](linux.md)** | Linux build and install | `guides/` |
| **[Troubleshooting](TROUBLESHOOTING.md)** | Platform-specific issues | `guides/` |

### Integration & Testing

| Document | Description | Location |
|----------|-------------|----------|
| **[E2E Testing](../docs/integration/e2e-testing.md)** | End-to-end testing | `docs/integration/` |
| **[Performance Testing](../PERFORMANCE_TEST_GUIDE.md)** | Performance benchmarks | Root |

## Documentation Templates

Auto Code provides reusable templates for consistent documentation. See [docs/README.md](../docs/README.md) for the complete template guide.

### Available Templates

| Template | Purpose | Location |
|----------|---------|----------|
| **Feature Spec** | Planning new features | `docs/templates/feature/spec.md` |
| **Implementation Guide** | How features work | `docs/templates/feature/implementation-guide.md` |
| **Feature Overview** | User-facing descriptions | `docs/templates/feature/feature-overview.md` |
| **Module Architecture** | Component documentation | `docs/templates/architecture/module-architecture.md` |
| **System Overview** | High-level architecture | `docs/templates/architecture/system-overview.md` |
| **Integration Guide** | Third-party integrations | `docs/templates/architecture/integration-guide.md` |
| **API Endpoint** | REST API documentation | `docs/templates/api/endpoint-documentation.md` |
| **Component API** | React component props | `docs/templates/api/component-api.md` |
| **User Guide** | End-user tutorials | `docs/templates/guides/user-guide.md` |
| **Developer Guide** | Technical tutorials | `docs/templates/guides/developer-guide.md` |
| **Troubleshooting Guide** | Issue resolution | `docs/templates/guides/troubleshooting-guide.md` |

## Writing Documentation

### Getting Started

1. **Choose your template** - Browse `docs/templates/` for the right template
2. **Follow the style guide** - Review [docs/STYLE_GUIDE.md](../docs/STYLE_GUIDE.md)
3. **Use the template** - Copy and fill in the template sections
4. **Link appropriately** - Use relative paths for internal links
5. **Verify quality** - Use [docs/VERIFICATION-CHECKLIST.md](../docs/VERIFICATION-CHECKLIST.md)

### Documentation Locations

| Type | Location | Example |
|------|----------|---------|
| **Feature specs** | `.auto-claude/specs/` | `001-feature-name/spec.md` |
| **User guides** | `guides/` | `QUICK-START.md` |
| **Technical docs** | `docs/features/`, `docs/modules/` | `MEMORY-SYSTEM.md` |
| **API docs** | `docs/api/` | `backend-api.md` |
| **Templates** | `docs/templates/` | `feature/spec.md` |

### Style Guidelines

All documentation should follow [docs/STYLE_GUIDE.md](../docs/STYLE_GUIDE.md):

- Clear, concise technical writing
- Code examples with syntax highlighting
- Consistent heading hierarchy (ATX-style: `# H1`, `## H2`)
- Tables for structured data
- Relative paths for internal links
- Descriptive filenames with hyphens (kebab-case)

### Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Feature specs | `{number}-{feature-name}` | `094-documentation-portal` |
| Module docs | `{module-name}-architecture.md` | `backend-architecture.md` |
| Guide docs | `{topic}-guide.md` or `{TOPIC}.md` | `developer-guide.md`, `CLI-USAGE.md` |
| API docs | `{endpoint-or-component}.md` | `create-spec-endpoint.md` |
| Templates | Descriptive lowercase with hyphens | `implementation-guide.md` |

### Quick Start for Writers

```bash
# Document a new feature
cp docs/templates/feature/spec.md .auto-claude/specs/XXX-my-feature/spec.md

# Document a module
cp docs/templates/architecture/module-architecture.md docs/modules/my-module.md

# Document an API endpoint
cp docs/templates/api/endpoint-documentation.md docs/api/my-endpoint.md

# Create a user guide
cp docs/templates/guides/user-guide.md guides/my-topic-guide.md
```

## Documentation Lifecycle

1. **Plan** - Feature spec created in `.auto-claude/specs/`
2. **Implement** - Code changes with inline documentation
3. **Document** - User-facing guides updated in `guides/`
4. **Review** - QA agent verifies documentation completeness
5. **Maintain** - Update as the feature evolves

## Specialized Documentation

### For AI Agents

- **[CLAUDE.md](../CLAUDE.md)** - Comprehensive architecture for AI agents working on Auto Code
- Covers project structure, commands, patterns, and integration guidelines
- Required reading for all agent sessions

### For Contributors

- **[CONTRIBUTING.md](../CONTRIBUTING.md)** - Contribution guidelines and development setup
- **[Frontend Contributing](../apps/frontend/CONTRIBUTING.md)** - Frontend-specific contribution guide
- **[Style Guide](../docs/STYLE_GUIDE.md)** - Writing style and documentation conventions

### For Plugin Developers

- **[Plugin Getting Started](../guides/plugins/getting-started.md)** - Plugin system overview
- **[Agent Plugins](../guides/plugins/agent-plugins.md)** - Create custom agents
- **[Integration Plugins](../guides/plugins/integration-plugins.md)** - External service integrations
- **[UI Plugins](../guides/plugins/ui-plugins.md)** - UI component customization

## Keeping Documentation Current

### When to Update

- **Immediately** - When adding/removing features, changing APIs, or modifying architecture
- **Before PR** - Documentation changes should be part of the same PR as code changes
- **During QA** - QA agents verify documentation completeness

### Maintenance Workflow

1. Code changes require documentation updates
2. Use appropriate templates for consistency
3. Follow the style guide for formatting
4. Update related docs and links
5. QA verification includes documentation checks

## Quick Reference

### Common Documentation Tasks

| Task | Document | Section |
|------|----------|---------|
| Find documentation | [Search Index](../docs/search/INDEX.md) | Entire document |
| Get started | [Quick Start](QUICK-START.md) | Entire document |
| Write docs | [Style Guide](../docs/STYLE_GUIDE.md) | Entire document |
| Use templates | [Docs README](../docs/README.md) | Templates section |
| Contribute | [Contributing](../CONTRIBUTING.md) | Documentation section |
| Verify quality | [Verification Checklist](../docs/VERIFICATION-CHECKLIST.md) | Entire document |

### Documentation Hub Summary

| Hub | Purpose | Audience |
|-----|---------|----------|
| **Root README.md** | Project overview, downloads | All users |
| **CLAUDE.md** | Architecture for agents | AI agents, developers |
| **guides/** | How-to and usage guides | Users, developers |
| **docs/** | Technical documentation | Developers, contributors |
| **docs/search/** | Search and discovery | Everyone |

## Additional Resources

- **[Search Index](../docs/search/INDEX.md)** - Comprehensive search tool
- **[Search Guide](../docs/search/SEARCH-GUIDE.md)** - Learn to search effectively
- **[Style Guide](../docs/STYLE_GUIDE.md)** - Writing conventions
- **[Verification Checklist](../docs/VERIFICATION-CHECKLIST.md)** - Quality standards
- **[Changelog](../CHANGELOG.md)** - Release history and what's new

## Need Help?

- **Can't find something?** - Use the [Search Index](../docs/search/INDEX.md)
- **Having trouble?** - Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
- **Want to contribute?** - Read the [Contributing Guide](../CONTRIBUTING.md)
- **Need to write docs?** - Follow the [Style Guide](../docs/STYLE_GUIDE.md)
- **Report a documentation issue?** - [Open an issue](https://github.com/OBenner/Auto-Coding/issues)

---

**Last Updated:** 2025-02-12

**Maintained by:** Auto Code Documentation Team
