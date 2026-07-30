# Documentation Portal

> **⚠️ Context Notice:** This portal only links to `README.md` and `shared_docs/` — files
> guaranteed present in isolated worktrees and release packages. For full docs, visit the
> main repository.

---

## About This Portal

Navigation hub for Auto Claude documentation, compatible with all deployment contexts.
Links only to `README.md` and `shared_docs/` — present in every worktree and release package.

### Overview

This portal provides a single entry point to all Auto Claude documentation resources,
organized by topic and audience for quick discovery.

---

## Quick Navigation

| Goal | Resource |
|------|----------|
| Get started | [README.md](../README.md) |
| Security commands | [shared_docs/SECURITY_COMMANDS.md](../shared_docs/SECURITY_COMMANDS.md) |
| Docker vs native | [shared_docs/DOCKER_NATIVE_DESIGN.md](../shared_docs/DOCKER_NATIVE_DESIGN.md) |
| Prompt injection | [shared_docs/PROMPT_INJECTION_DEFENSE.md](../shared_docs/PROMPT_INJECTION_DEFENSE.md) |

### Getting Started

1. **Read the README** — [README.md](../README.md) has complete setup and requirements.
2. **Install** — `npm run install:all` (Python 3.12+ and Node.js required).
3. **Authenticate** — Run `claude`, then `/login` to complete OAuth.
4. **Create a spec** — `python spec_runner.py --interactive`
5. **Run a build** — `python run.py --spec 001`

### Key Documentation

| Document | Purpose |
|----------|---------|
| [README.md](../README.md) | Primary reference — setup, commands, architecture |
| [shared_docs/SECURITY_COMMANDS.md](../shared_docs/SECURITY_COMMANDS.md) | Security reference |
| [shared_docs/DOCKER_NATIVE_DESIGN.md](../shared_docs/DOCKER_NATIVE_DESIGN.md) | Deployment design |
| [shared_docs/PROMPT_INJECTION_DEFENSE.md](../shared_docs/PROMPT_INJECTION_DEFENSE.md) | Security hardening |

### Finding Information

Use Ctrl+F / Cmd+F to search this file. See [Search & Browse by Category](#search--browse-by-category)
for topic-organized links. Full-text search: use GitHub on the main repo or `docs/search/`.

### Getting Help

1. [README.md](../README.md) — comprehensive coverage of most topics
2. [shared_docs/SECURITY_COMMANDS.md](../shared_docs/SECURITY_COMMANDS.md) — security issues
3. [shared_docs/DOCKER_NATIVE_DESIGN.md](../shared_docs/DOCKER_NATIVE_DESIGN.md) — deployment
4. Main repository — open an issue for unresolved bugs or questions

---

## Feature Documentation

> See [README.md](../README.md) for the complete feature reference.

### Core Features Overview

| Feature | Description |
|---------|-------------|
| **Multi-Agent Pipeline** | Planner → Coder → QA Reviewer → QA Fixer |
| **Spec-Driven Development** | AI creates implementation specs before coding |
| **Git Worktree Isolation** | Each build runs in an isolated worktree |
| **Graphiti Memory** | Cross-session knowledge graph for context retention |
| **CI/CD Integration** | Headless mode with JSON output and exit codes |
| **Security Sandbox** | Three-layer: OS sandbox, filesystem limits, allowlist |

Config in `apps/backend/.env`. Required: `CLAUDE_CODE_OAUTH_TOKEN`. Providers: OpenAI,
Anthropic, Azure, Ollama, Google AI. Full details in [README.md](../README.md).

---

## API Reference

### CLI Overview

Two primary scripts: `spec_runner.py` creates specs; `run.py` executes builds.

```bash
python spec_runner.py --interactive           # interactive spec creation
python spec_runner.py --task "Add OAuth"      # from description
python spec_runner.py --task "Fix X" --complexity simple
python run.py --list                          # list specs
python run.py --spec 001                      # run build
python run.py --spec 001 --review             # review in worktree
python run.py --spec 001 --merge              # merge into project
python run.py --spec 001 --discard            # discard build
```

### Core Commands

```bash
python run.py --spec 001 --qa
python run.py --spec 001 --qa-status
python validate_spec.py --spec-dir apps/backend/specs/001-feature --checkpoint all
AUTO_CLAUDE_CI=true AUTO_CLAUDE_JSON_OUTPUT=true python run.py --spec 001 --ci --json
```

### Usage Examples

```bash
python spec_runner.py --task "Add OAuth login"   # 1. create spec
python run.py --spec 001                          # 2. build
python run.py --spec 001 --review                 # 3. review changes
python run.py --spec 001 --merge                  # 4. merge
git push origin main                              # 5. push when ready
```

---

## Architecture & Design

> See [README.md](../README.md#architecture) for full architecture details.

### System Architecture

Multi-agent pipeline on the Claude Agent SDK — each agent runs in an isolated git worktree:
```
User Task → Spec Runner → Planner → Coder (+ subagents) → QA Reviewer
                                                             ├── Pass → merge
                                                             └── Fail → QA Fixer → loop
```

No automatic remote pushes — users control when to push after reviewing and merging.

### Security Design

Three-layer model — details in [shared_docs/SECURITY_COMMANDS.md](../shared_docs/SECURITY_COMMANDS.md):

1. **OS Sandbox** — Bash isolation at operating-system level
2. **Filesystem Limits** — Operations restricted to project directory
3. **Dynamic Allowlist** — Derived from stack analysis, cached in `.auto-claude-security.json`

Hardening: [shared_docs/PROMPT_INJECTION_DEFENSE.md](../shared_docs/PROMPT_INJECTION_DEFENSE.md)

### Deployment Options

Full design: [shared_docs/DOCKER_NATIVE_DESIGN.md](../shared_docs/DOCKER_NATIVE_DESIGN.md)

| Aspect | Docker | Native |
|--------|--------|--------|
| Isolation | Container-level | Process-level |
| Setup | Requires Docker | Python 3.12+ + Node.js |
| Portability | High | Environment-dependent |

Multi-provider LLM: OpenAI, Anthropic, Azure, Ollama, Google AI. Config in [README.md](../README.md).

---

## Guides & Tutorials

> Detailed guides live in `guides/` in the main repository.

### User Guides

| Guide | Topic |
|-------|-------|
| Quick Start | First-time setup and first autonomous build |
| Spec Creation | Writing effective task descriptions |
| Workspace Management | Review, merge, and discard workflows |
| QA & Validation | Understanding QA cycles and fixing rejections |

### Developer Guides

| Guide | Topic |
|-------|-------|
| Adding Agent Types | Implementing new agent roles |
| Security Configuration | Customizing command allowlists |
| Memory Integration | Graphiti knowledge graph setup |

### Integration Guides

| Integration | Resource |
|-------------|---------|
| Linear, GitHub, Graphiti, Electron MCP | [README.md](../README.md) |
| Docker deployment | [shared_docs/DOCKER_NATIVE_DESIGN.md](../shared_docs/DOCKER_NATIVE_DESIGN.md) |
| Prompt security | [shared_docs/PROMPT_INJECTION_DEFENSE.md](../shared_docs/PROMPT_INJECTION_DEFENSE.md) |

---

## Search & Browse by Category

### Browse by Topic

| Topic | Resource |
|-------|----------|
| Setup & Install | [README.md](../README.md#setup) |
| Spec creation & builds | [README.md](../README.md#creating-and-running-specs) |
| Workspace operations | [README.md](../README.md#workspace-management) |
| Security commands | [shared_docs/SECURITY_COMMANDS.md](../shared_docs/SECURITY_COMMANDS.md) |
| Deployment design | [shared_docs/DOCKER_NATIVE_DESIGN.md](../shared_docs/DOCKER_NATIVE_DESIGN.md) |
| Prompt injection | [shared_docs/PROMPT_INJECTION_DEFENSE.md](../shared_docs/PROMPT_INJECTION_DEFENSE.md) |
| CI/CD & memory | [README.md](../README.md#cicd-integration) |

### Browse by Role

**New User:** [README.md](../README.md) → [Getting Started](#getting-started) above
**Developer / Contributor:** [README.md](../README.md) → [shared_docs/SECURITY_COMMANDS.md](../shared_docs/SECURITY_COMMANDS.md) → [shared_docs/PROMPT_INJECTION_DEFENSE.md](../shared_docs/PROMPT_INJECTION_DEFENSE.md)
**DevOps / Platform Engineer:** [shared_docs/DOCKER_NATIVE_DESIGN.md](../shared_docs/DOCKER_NATIVE_DESIGN.md) → [README.md](../README.md#cicd-integration) → [shared_docs/SECURITY_COMMANDS.md](../shared_docs/SECURITY_COMMANDS.md)

---

## Troubleshooting

### Common Issues

| Symptom | Solution |
|---------|---------|
| Auth failure | Re-run `claude` → `/login` to refresh OAuth |
| Build hangs | Check `.auto-claude/specs/XXX/` logs; verify token |
| QA keeps rejecting | Review `QA_FIX_REQUEST.md` in spec dir |
| Worktree conflict | `python run.py --spec 001 --discard` then rebuild |

### Error Messages & Solutions

| Error | Cause | Fix |
|-------|-------|-----|
| `OAuth token invalid` | Token expired | Re-run `/login` |
| `Worktree already exists` | Prior failed build | Run `--discard` first |
| `Security hook blocked` | Not allowlisted | Check `.auto-claude-security.json` |
| `Spec not found` | Wrong ID | `python run.py --list` |

### Environment Setup Issues

Requires Python 3.12+ and Node.js. Always activate the virtual environment before running:

```bash
source apps/backend/.venv/bin/activate    # Unix/macOS
apps/backend/.venv/Scripts/activate       # Windows
```

Reinstall: `npm run install:all`
Security issues: [shared_docs/SECURITY_COMMANDS.md](../shared_docs/SECURITY_COMMANDS.md)

### Getting Support

1. Search this portal (Ctrl+F) for your error message.
2. Check [README.md](../README.md) — it covers most common issues.
3. Review `.auto-claude/specs/XXX/` logs and `qa_report.md`.
4. Open an issue in the main repository for unresolved problems.

---

## Documentation Structure

### File Organization

```
project-root/
├── README.md                     # Primary reference — all contexts
├── docs/
│   ├── PORTAL.md                 # This file — worktree-safe nav hub
│   ├── STYLE_GUIDE.md            # Writing conventions
│   └── templates/                # Doc templates (main repo only)
├── guides/                       # Detailed guides (main repo only)
└── shared_docs/                  # Safe to link in all contexts
    ├── DOCKER_NATIVE_DESIGN.md
    ├── PROMPT_INJECTION_DEFENSE.md
    └── SECURITY_COMMANDS.md
```

> In isolated worktrees and release packages, only `README.md`, `docs/PORTAL.md`, and
> `shared_docs/` are guaranteed present. `guides/` and `docs/search/` require the full repo.

### Directory Overview

| Location | Contents | Always Available |
|----------|----------|-----------------|
| `README.md` | Complete reference documentation | ✅ |
| `docs/PORTAL.md` | This navigation portal | ✅ |
| `shared_docs/` | Architecture and security docs | ✅ |
| `docs/templates/` | Documentation templates | Main repo only |
| `guides/` | User and developer guides | Main repo only |

---

## Documentation Quality

### Writing Standards

Following conventions in `docs/STYLE_GUIDE.md` (main repository):

- **Clarity first** — Write for the reader, not the writer; avoid "quick", "simple", "fast"
- **Working examples** — Include copy-pasteable code samples with language tags
- **Portability** — Worktree-safe docs must only link to `README.md` or `shared_docs/`

### Style Guide Summary

| Element | Convention |
|---------|-----------|
| Headings | Title Case H1/H2, sentence case H3+ |
| Code blocks | Always specify language (` ```bash `, ` ```python `) |
| Tables | Use for comparisons with 3+ comparable items |
| Links | Descriptive text, never "click here" |
| Notes | `> **Note:**` blockquote format |
| Warnings | `> **⚠️ Warning:**` blockquote format |

### Review Process

1. **Draft** — Write content following the style guide.
2. **Self-review** — Check links, examples, formatting, and portability.
3. **Peer review** — At least one reviewer for significant changes.
4. **Link validation** — Verify all referenced paths exist in target deployment contexts.

---

## Contributing to Documentation

> For code contributions, see the main repository.

### How to Contribute

1. Fork the repository; branch from `upstream/develop`.
2. Follow `docs/STYLE_GUIDE.md` conventions.
3. Only link to `README.md` or `shared_docs/` from worktree-safe docs.
4. Submit a PR targeting `develop` (not `main`).

### Submission Guidelines

```bash
git checkout -b docs/my-improvement upstream/develop
git commit -s -m "docs: describe your change"
git push origin docs/my-improvement
gh pr create --base develop --title "docs: describe your change"
```

### Community Standards

- Be respectful and constructive in reviews.
- Update existing docs rather than creating duplicates.
- Portability constraint: links in `docs/PORTAL.md` must reference only `README.md` or `shared_docs/`.

---

*Auto Claude Documentation Portal — for full docs, visit the main repository.*
