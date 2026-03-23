# Auto Code Documentation Portal

Welcome to the Auto Code documentation hub. Whether you're getting started, building features, or contributing to the project, you'll find comprehensive guides and references here.

---

## Search & Navigation

**Looking for something specific?**

- **[📖 Search Index](search/INDEX.md)** - Comprehensive searchable index with keywords
- **[🔍 Search Guide](search/SEARCH-GUIDE.md)** - Learn effective search strategies
- **[✅ Verification Checklist](VERIFICATION-CHECKLIST.md)** - Documentation quality verification

**Quick links:**
- [Getting Started](../guides/QUICK-START.md) - Get up and running in 15 minutes
- [CLI Usage](../guides/CLI-USAGE.md) - Terminal-only workflows
- [Troubleshooting](../guides/TROUBLESHOOTING.md) - Common issues and solutions

---

## Documentation by Role

### New Users

Start here if you're new to Auto Code:

| Guide | Purpose |
|-------|---------|
| **[Quick Start Guide](../guides/QUICK-START.md)** | Get started in 15 minutes with your first build |
| **[CLI Usage Guide](../guides/CLI-USAGE.md)** | Learn terminal commands for headless operation |
| **[Platform Guides](../guides/)** | Platform-specific setup (Windows, macOS, Linux) |
| **[Troubleshooting](../guides/TROUBLESHOOTING.md)** | Resolve common issues and errors |

### Developers

For developers working on Auto Code:

| Documentation | Purpose |
|---------------|---------|
| **[CLAUDE.md](../CLAUDE.md)** | Comprehensive architecture for AI agents |
| **[Architecture Overview](README.md#documentation-structure)** | System architecture and module organization |
| **[API Documentation](README.md#api-documentation)** | Backend endpoints and frontend components |
| **[Component Docs](components/)** | React component API reference |
| **[Store Docs](stores/)** | Zustand state management documentation |

### Contributors

Contributing to the project:

| Resource | Purpose |
|----------|---------|
| **[CONTRIBUTING.md](../CONTRIBUTING.md)** | Contribution guidelines and development setup |
| **[Documentation Style Guide](STYLE_GUIDE.md)** | Writing conventions and best practices |
| **[Documentation Templates](templates/)** | Reusable templates for features, APIs, and guides |
| **[Release Process](../RELEASE.md)** | Version management and release workflow |

---

## Documentation by Type

### Architecture & Design

Deep-dives into system architecture:

| Topic | Description |
|-------|-------------|
| **[System Architecture](README.md#documentation-structure)** | High-level system overview and component relationships |
| **[Agent Pipeline](../guides/SPEC-PIPELINE.md)** | Multi-agent spec creation and implementation workflow |
| **[Memory System](../CLAUDE.md#memory-system)** | Graphiti-powered cross-session knowledge graph |
| **[Security Model](../CLAUDE.md#security-model)** | Three-layer defense: sandbox, permissions, allowlist |

### API Reference

Complete API documentation:

| API Type | Documentation |
|----------|---------------|
| **[Backend API](README.md#api-documentation)** | REST endpoints and WebSocket handlers |
| **[Component API](components/)** | React component props, events, and usage |
| **[Store API](stores/)** | Zustand store actions and state structure |
| **[Agent Tools](../CLAUDE.md#agent-prompts-appsbackendprompts)** | Custom MCP tools for agent capabilities |

### Guides & Tutorials

Step-by-step instructions:

| Guide | Topic |
|-------|-------|
| **[Quick Start](../guides/QUICK-START.md)** | Your first build from task to merge |
| **[Spec Pipeline](../guides/SPEC-PIPELINE.md)** | Creating specifications from task descriptions |
| **[CLI Usage](../guides/CLI-USAGE.md)** | Command-line interface and automation |
| **[Cloud Setup](../guides/CLOUD_SETUP.md)** | Deploy to Kubernetes for multi-user access |
| **[Migration Assistant](migration-assistant.md)** | Framework and library migration workflows |

### Templates

Standardized documentation templates:

| Category | Templates |
|----------|-----------|
| **[Feature Templates](templates/feature/)** | Spec, implementation guide, feature overview |
| **[Architecture Templates](templates/architecture/)** | Module docs, system overview, integration guide |
| **[API Templates](templates/api/)** | Endpoint docs, component API, WebSocket API |
| **[Guide Templates](templates/guides/)** | User guides, developer guides, troubleshooting |

---

## Common Tasks

### Getting Started

```bash
# First-time setup
npm run install:all
cd apps/backend && python run.py

# Create your first task
python spec_runner.py --interactive
python run.py --spec 001
```

See the **[Quick Start Guide](../guides/QUICK-START.md)** for detailed instructions.

### Creating Documentation

```bash
# Choose a template
cp docs/templates/feature/spec.md .auto-claude/specs/XXX-my-feature/spec.md

# Follow the style guide
# See docs/STYLE_GUIDE.md for conventions
```

See **[Documentation Templates](templates/)** for all available templates.

### Finding Information

1. **Search first** - Use the [Search Index](search/INDEX.md) for keyword-based discovery
2. **Browse by role** - Navigate to documentation relevant to your needs
3. **Check CLAUDE.md** - Comprehensive architecture reference for developers
4. **Review guides** - Step-by-step instructions for common workflows

---

## Documentation Structure

```
docs/
├── index.md              # This file - documentation portal
├── README.md             # Documentation overview and organization
├── STYLE_GUIDE.md        # Writing conventions and best practices
├── VERIFICATION-CHECKLIST.md  # Quality verification checklist
├── templates/            # Reusable documentation templates
│   ├── feature/          # Feature specs and implementation guides
│   ├── architecture/     # Module and system architecture docs
│   ├── api/              # API endpoint and component documentation
│   └── guides/           # User and developer guide templates
├── components/           # Frontend component API documentation
├── stores/               # Zustand store documentation
├── modules/              # Per-module architecture documentation
├── diagrams/             # Architecture diagrams and visualizations
└── search/               # Search index and search guide
```

---

## Contributing to Documentation

When contributing documentation:

1. **Use templates** - Start from `docs/templates/` for consistency
2. **Follow style guide** - Review `STYLE_GUIDE.md` before writing
3. **Include examples** - Code examples and practical use cases
4. **Keep it current** - Update documentation when code changes
5. **Link appropriately** - Use relative links for internal documentation
6. **Verify quality** - Use the [Verification Checklist](VERIFICATION-CHECKLIST.md)

See **[CONTRIBUTING.md](../CONTRIBUTING.md)** for detailed guidelines.

---

## External Resources

- **[GitHub Repository](https://github.com/OBenner/Auto-Coding)** - Source code and releases
- **[Discord Community](https://discord.gg/KCXaPBr4Dj)** - Chat, get help, share what you're building
- **[Issue Tracker](https://github.com/OBenner/Auto-Coding/issues)** - Report bugs or request features
- **[Discussions](https://github.com/OBenner/Auto-Coding/discussions)** - Ask questions and share ideas

---

## Need Help?

- **Issues?** Check the [Troubleshooting Guide](../guides/TROUBLESHOOTING.md)
- **Questions?** Ask in [Discord](https://discord.gg/KCXaPBr4Dj) or [GitHub Discussions](https://github.com/OBenner/Auto-Coding/discussions)
- **Bug reports** Create an [issue](https://github.com/OBenner/Auto-Coding/issues)
- **Contributions** See [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## Recent Updates

Check the **[CHANGELOG.md](../CHANGELOG.md)** for the latest features, fixes, and improvements.

---

**[← Back to Main README](../README.md)**
