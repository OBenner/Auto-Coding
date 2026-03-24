# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for Auto Code — a log of significant architectural and design choices made during development, along with their context and rationale.

## What is an ADR?

An Architecture Decision Record captures an important architectural decision made along with its context and consequences. ADRs help:

- **New contributors** understand *why* the codebase is structured the way it is
- **Maintainers** remember the constraints and trade-offs behind past decisions
- **Reviewers** evaluate whether a proposed change conflicts with existing decisions
- **The community** engage in informed debate rather than relitigating resolved questions

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](ADR-001-claude-agent-sdk.md) | Claude Agent SDK Adoption | Accepted | 2024-01-01 |
| [ADR-002](ADR-002-graphiti-memory.md) | Graphiti Memory System | Accepted | 2024-01-01 |
| [ADR-003](ADR-003-worktree-isolation.md) | Git Worktree Isolation Strategy | Accepted | 2024-01-01 |
| [ADR-004](ADR-004-multi-provider-support.md) | Multi-Provider LLM Support | Accepted | 2024-01-01 |

### Status Definitions

| Status | Meaning |
|--------|---------|
| **Proposed** | Decision is under discussion; not yet adopted |
| **Accepted** | Decision has been adopted and is in effect |
| **Deprecated** | Decision was once accepted but is no longer recommended |
| **Superseded** | Decision has been replaced by a newer ADR (link provided) |

## Proposing a New ADR

### When to Write an ADR

Write an ADR whenever you make a decision that:

- Affects the overall system architecture or project structure
- Involves a significant trade-off between competing approaches
- Is likely to be questioned or revisited by future contributors
- Requires adopting or replacing a major dependency or pattern
- Establishes a convention that all contributors should follow

You do **not** need an ADR for:
- Routine implementation choices within an already-decided pattern
- Purely stylistic preferences covered by the style guide
- Bug fixes that don't change architectural direction

### ADR Lifecycle

```
Proposed → Accepted → (optionally) Deprecated or Superseded
```

1. **Proposed** — Author opens a PR with a new ADR file. Status is `Proposed`.
2. **Review** — Maintainers and contributors discuss in the PR. See review process below.
3. **Accepted** — PR is merged, status updated to `Accepted`, and ADR added to this index.
4. **Superseded/Deprecated** — If a later decision replaces this one, update the old ADR's status to `Superseded` (linking to the new ADR) and create the new ADR.

### Review Process

1. **Copy the template** — Start from [`template.md`](template.md). Assign the next sequential number.
2. **Fill in all sections** — Context, Decision, Rationale, Alternatives, Consequences.
3. **Open a pull request** — Target the `develop` branch (see [Contributing Guide](../../../CONTRIBUTING.md)).
4. **Label the PR** — Add the `adr` label so reviewers can find it.
5. **Allow 48 hours** — Give maintainers and interested contributors time to review.
6. **Address feedback** — Revise the ADR based on discussion; do not change the decision number.
7. **Merge and update index** — Once approved, merge and add the ADR row to the table above.

### Naming Convention

```
ADR-NNN-short-kebab-case-title.md
```

Examples:
- `ADR-005-spec-complexity-levels.md`
- `ADR-006-electron-mcp-testing.md`

Numbers are assigned sequentially and never reused.

## Creating an ADR

```bash
# Copy the template
cp docs/architecture/adr/template.md docs/architecture/adr/ADR-005-my-decision.md

# Edit with your decision details
# Then open a PR targeting develop
```

See [`template.md`](template.md) for the full ADR format with field-level instructions.

## Quick Links

- [ADR Template](template.md) — Start here when writing a new ADR
- [Architecture Docs](../) — Broader architecture documentation
- [Documentation Templates](../../templates/) — Templates for features, APIs, and architecture
- [Contributing Guide](../../../CONTRIBUTING.md) — How to contribute to Auto Code
- [Style Guide](../../STYLE_GUIDE.md) — Documentation writing conventions

---

*ADRs are living documents. If a decision changes, update the existing ADR's status and create a new one — never silently rewrite history.*
