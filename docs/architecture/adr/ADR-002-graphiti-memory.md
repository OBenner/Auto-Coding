# ADR-002: Adopt Graphiti as the Persistent Memory System

**Date:** 2024-01-15
**Status:** Accepted
**Deciders:** Auto Code Core Team
**Tags:** memory, persistence, knowledge-graph, ai, architecture

---

## Context

Auto Code runs multiple AI agent sessions across many builds and specs. Without persistent memory, every new session starts from scratch — agents cannot learn from previous runs, cannot recall discovered patterns or gotchas, and cannot share knowledge between specs on the same project.

A persistent memory system is required to support:
- **Cross-session context retrieval** — providing agents with relevant historical knowledge at the start of each new session.
- **Pattern and gotcha storage** — recording recurring patterns, anti-patterns, and pitfalls discovered during builds.
- **Codebase discovery** — storing knowledge about file purposes, module relationships, and project structure.
- **Code relationship tracking** — recording function calls, imports, and inheritance hierarchies to support impact analysis.
- **Cross-spec learning** — sharing insights discovered in one spec with all subsequent specs on the same project.

The system must:
- Work without requiring a separately managed infrastructure (no Docker, no external database server).
- Support multiple LLM and embedding providers (not just OpenAI).
- Degrade gracefully — if the memory system is unavailable, agents must still function.
- Store data locally alongside spec artifacts.

## Decision

We will use **Graphiti** backed by the embedded **LadybugDB** graph database as the primary persistent memory system for Auto Code.

All memory access goes through `GraphitiMemory` from `integrations.graphiti.memory`. Direct access to the underlying database is prohibited outside the `queries_pkg` internal modules.

```python
# ✅ CORRECT — use the factory function
from integrations.graphiti.memory import get_graphiti_memory

memory = get_graphiti_memory(spec_dir, project_dir)
context = await memory.get_context_for_session("Implementing feature X")
await memory.add_session_insight("Pattern: use React hooks for state")

# ❌ WRONG — do not access LadybugDB or Graphiti internals directly
from integrations.graphiti.queries_pkg.client import GraphitiClient
client = GraphitiClient(...)
```

Graphiti is **mandatory** — it is enabled by default when provider credentials are present. The integration is opt-out rather than opt-in, ensuring agents benefit from memory whenever possible.

## Rationale

Graphiti was chosen because it combines a **knowledge graph** with **semantic search**, giving agents both structured relational retrieval and fuzzy natural-language queries over stored knowledge.

### Key factors

- **Embedded database (no Docker)** — LadybugDB runs in-process using KùzuDB as the underlying graph store. No external database process is required. Memory data is stored as local files in `.auto-claude/specs/XXX/graphiti/`, keeping the system entirely self-contained.
- **Graph-native knowledge representation** — Architectural knowledge (patterns, relationships, gotchas) is inherently relational. A graph model captures these connections naturally, whereas a vector store alone would lose structural context.
- **Semantic search over episodes** — Graphiti indexes stored episodes as semantic embeddings, enabling agents to retrieve contextually relevant knowledge with natural-language queries rather than exact-match lookups.
- **Multi-provider flexibility** — The `providers_pkg` factory pattern supports OpenAI, Anthropic, Azure OpenAI, Ollama, Google AI (Gemini), and Voyage AI for both LLM extraction and embedding. Teams are not locked into a single vendor.
- **Graceful degradation** — All `GraphitiMemory` operations are async and include error handling. If Graphiti is disabled or unavailable, every method returns empty results or no-ops rather than raising exceptions, ensuring agents function normally even without memory.
- **Scoped namespacing** — The `GroupIdMode` (`SPEC` vs `PROJECT`) allows memory to be either isolated per spec or shared project-wide. The default is project-wide (`GroupIdMode.PROJECT`), enabling cross-spec learning.

### Alternatives considered

| Option | Pros | Cons |
|--------|------|------|
| **Graphiti + LadybugDB** (chosen) | Embedded — no infra; graph + semantic search; multi-provider; graceful degradation | Additional Python dependencies; LadybugDB is not a mainstream database; KùzuDB path patching required on some platforms |
| **Vector store only (e.g. Chroma, FAISS)** | Simple; fast similarity search; many libraries | No relational structure; poor at capturing code relationships and causal chains; requires separate infrastructure or in-memory mode |
| **Neo4j / full graph database** | Powerful graph queries; mature ecosystem | Requires Docker or external server; too heavy for a local dev tool; no native semantic search without additional components |
| **SQLite with full-text search** | Zero dependencies; reliable; embedded | No semantic similarity; poor at capturing cross-session knowledge relationships; must manually model graph traversal |
| **Stateless (no memory)** | Zero complexity; no dependencies | Agents restart blind on every session; no learning; no cross-spec reuse; degrades QA quality over time |

## Consequences

### Positive

- Agents accumulate knowledge across sessions, improving quality and reducing repeated mistakes on the same project.
- Patterns and gotchas discovered during one spec are automatically surfaced in subsequent specs on the same project.
- The embedded LadybugDB means zero infrastructure setup — developers get persistent memory out of the box.
- Multi-provider support means teams can use Ollama for fully local/offline operation, or choose any cloud provider.
- Code relationship tracking enables impact analysis, helping agents understand which parts of the codebase are affected by a change.

### Negative

- The `KùzuDB` driver requires a patched asyncio driver (`kuzu_driver_patched.py`) due to upstream compatibility issues — this is a maintenance liability.
- Memory quality depends on the LLM and embedding providers configured. Poor providers produce low-quality episode extraction and degraded retrieval.
- Graphiti adds several Python dependencies (`graphiti-core`, `kuzudb`, and embedding-provider-specific packages) that increase install time and environment complexity.
- The `GROUP_ID` hashing strategy ties memory scoping to filesystem paths — if a project is moved or renamed, existing memory becomes inaccessible.

### Neutral

- Graphiti must be enabled explicitly via `GRAPHITI_ENABLED=true` and the appropriate provider credentials in `apps/backend/.env`. The system is passive — it never fails hard if unconfigured.
- Memory data is stored in `.auto-claude/specs/XXX/graphiti/` alongside spec artifacts. This is included in the spec's git worktree and is not pushed to remote by default.
- The `GroupIdMode` default changed from `SPEC` to `PROJECT` to enable cross-spec learning. Callers that require isolated per-spec memory must pass `GroupIdMode.SPEC` explicitly.
- All agents access memory through `agents/memory_manager.py`, which wraps `GraphitiMemory` with session-level orchestration (context retrieval on start, insight storage on end).

## Implementation notes

The memory system is organised into discrete modules under `integrations/graphiti/queries_pkg/`:

- **`graphiti.py`** — `GraphitiMemory` class; high-level facade delegating to the modules below.
- **`client.py`** — `GraphitiClient`; manages the LadybugDB connection lifecycle (connect, close, health check).
- **`queries.py`** — `GraphitiQueries`; episode storage operations (session insights, gotchas, patterns, task outcomes).
- **`search.py`** — `GraphitiSearch`; semantic search and context assembly for new sessions.
- **`schema.py`** — Shared constants (`EPISODE_TYPE_*`, `GroupIdMode`, `MAX_CONTEXT_RESULTS`) and data structures.
- **`code_relationships.py`** — `CodeRelationshipQueries`; stores and retrieves code-level relationships for impact analysis.

The provider factory lives in `integrations/graphiti/providers_pkg/factory.py` and is configured via environment variables parsed by `graphiti_config.py`.

**Adding a new provider:**

1. Implement the LLM or embedder interface in `providers_pkg/llm_providers/` or `providers_pkg/embedder_providers/`.
2. Register it in `providers_pkg/factory.py`.
3. Add the required env vars to `.env.example`.

**Configuring memory scope:**

```python
from integrations.graphiti.memory import get_graphiti_memory
from integrations.graphiti.queries_pkg.schema import GroupIdMode

# Shared project-wide memory (default — recommended)
memory = get_graphiti_memory(spec_dir, project_dir)

# Isolated per-spec memory
memory = get_graphiti_memory(spec_dir, project_dir, group_id_mode=GroupIdMode.SPEC)
```

## References

- `apps/backend/integrations/graphiti/memory.py` — Public entry point and backward-compatibility facade
- `apps/backend/integrations/graphiti/queries_pkg/graphiti.py` — `GraphitiMemory` implementation
- `apps/backend/integrations/graphiti/queries_pkg/client.py` — LadybugDB connection management
- `apps/backend/integrations/graphiti/providers_pkg/factory.py` — Multi-provider factory
- `apps/backend/integrations/graphiti/config.py` — Configuration and validation
- `apps/backend/agents/memory_manager.py` — Session-level memory orchestration
- [ADR-001: Adopt Claude Agent SDK](./ADR-001-claude-agent-sdk.md) — Foundational SDK decision
- [CLAUDE.md](../../../CLAUDE.md) — Memory system overview and configuration

---

*This ADR follows the [Auto Code ADR format](./template.md). See the [ADR index](./README.md) for all decisions.*
