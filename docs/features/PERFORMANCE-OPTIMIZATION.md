# Performance Optimization

This document describes the performance optimizations added to both the frontend and backend of Auto Code.

## Overview

Performance improvements target four areas:

1. **Async event loop (uvloop)** -- Backend async operations run faster on Linux/macOS.
2. **Zustand useShallow selectors** -- Frontend re-renders are minimized by using shallow equality checks on store selectors.
3. **Bundle visualization** -- A build-time analysis tool identifies large dependencies.
4. **Database connection pooling** -- The web backend uses configurable connection pool parameters.

## Backend: uvloop Integration

`uvloop` is a drop-in replacement for Python's default `asyncio` event loop. It is based on libuv and provides 2-4x throughput improvement for async I/O operations.

**Location:** `apps/backend/core/client.py` (top-level initialization)

**Behavior:**

- On Linux and macOS, `uvloop.install()` is called at module load time.
- On Windows, the default proactor event loop is used (uvloop does not support Windows).
- If uvloop is not installed, the code falls back gracefully to the standard event loop.

**Installation:**

```bash
pip install uvloop  # Linux/macOS only
```

No configuration is needed. The optimization is automatic when the package is present.

## Frontend: Zustand useShallow Selectors

Zustand v4+ uses reference equality to decide whether a component re-renders. When a selector returns an object or array, every state change triggers a re-render even if the selected slice did not change. Wrapping selectors with `useShallow` from `zustand/react/shallow` switches to shallow equality, preventing unnecessary re-renders.

**Pattern:**

```typescript
import { useShallow } from 'zustand/react/shallow';

// Before (re-renders on every state change)
const projects = useProjectStore((state) => state.projects);

// After (re-renders only when projects actually change)
const projects = useProjectStore(useShallow((state) => state.projects));
```

**Scope:** Applied to components that consume array or object state from stores, including `KanbanBoard`, `Sidebar`, `TerminalGrid`, `GitHubIssues`, `GitLabIssues`, `TaskCreationWizard`, `Worktrees`, and `ProductivityDashboard`.

A full audit of all 22 Zustand stores is documented in `ZUSTAND_SELECTOR_AUDIT.md` at the repository root.

## Frontend: Bundle Visualization

The `rollup-plugin-visualizer` plugin generates an interactive HTML report of the renderer bundle composition after each build.

**Location:** `apps/frontend/electron.vite.config.ts` (renderer plugins)

**Output:** `apps/frontend/out/renderer/stats.html`

The report shows module sizes (raw, gzip, brotli) in a treemap. Use it to identify large dependencies and code-splitting opportunities.

**Configuration:**

```typescript
visualizer({
  filename: './out/renderer/stats.html',
  open: !process.env.CI,  // auto-open locally, skip in CI
  gzipSize: true,
  brotliSize: true,
})
```

## Web Backend: Connection Pool Parameterization

The web backend (`apps/web-backend/`) uses SQLAlchemy with configurable connection pool settings. SQLite connections use `check_same_thread=False` for thread safety; non-SQLite databases use pool parameters from environment variables.

**Location:** `apps/web-backend/core/database.py`

**Environment variables (non-SQLite databases only):**

| Variable | Default | Description |
|---|---|---|
| `DB_POOL_SIZE` | `10` | Maximum connections in the pool |
| `DB_MAX_OVERFLOW` | `20` | Extra connections beyond pool_size |
| `DB_POOL_TIMEOUT` | `30` | Seconds to wait for a connection |
| `DB_POOL_RECYCLE` | `3600` | Seconds before recycling a connection |
| `DB_ECHO` | `false` | Log SQL queries |

## Running Performance Tests

Performance regression tests live in `tests/performance/`.

```bash
# Run all performance tests
pytest tests/performance/ -v

# Run a specific suite
pytest tests/performance/test_async_performance.py -v
pytest tests/performance/test_memory_performance.py -v
pytest tests/performance/test_frontend_performance.py -v
pytest tests/performance/test_backend_performance.py -v

# Run only benchmark-marked tests
pytest tests/performance/ -m benchmark -v
```

**Test suites:**

| File | What it tests |
|---|---|
| `test_async_performance.py` | Async task creation, concurrency, event loop overhead, uvloop integration |
| `test_backend_performance.py` | Backend operation benchmarks |
| `test_frontend_performance.py` | Bundle size constraints, Zustand optimization patterns, build artifacts |
| `test_memory_performance.py` | Memory monitor performance, pressure detection, cleanup verification, data structure efficiency |
