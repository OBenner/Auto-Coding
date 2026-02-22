# Module Architecture: Memory Manager

## Overview

The Memory Manager module provides a unified interface for managing agent memory across different backends (Graphiti, session storage, file-based memory). It abstracts memory operations and provides a consistent API for storing and retrieving context, insights, and session data.

## Module Structure

```
memory/
├── __init__.py              # Public API exports
├── manager.py              # MemoryManager class (450 lines)
├── backends/               # Storage implementations
│   ├── graphiti.py        # Graphiti backend (320 lines)
│   ├── session.py         # Session memory (180 lines)
│   └── file.py            # File-based memory (150 lines)
├── models.py              # Data models (200 lines)
└── utils.py               # Helper functions (100 lines)
```

**Total:** ~1,400 lines

## Module Descriptions

### `manager.py`

**Key Exports:**
- `MemoryManager` - Main memory manager class
- `MemoryConfig` - Configuration data class

**Purpose**: Orchestrates memory operations across different backends

**Key Methods**:
- `add_context()` - Store context for retrieval
- `get_context()` - Retrieve relevant context
- `add_session_insight()` - Store learnings from session
- `search()` - Semantic search across memory

### `backends/graphiti.py`

**Key Exports:**
- `GraphitiBackend` - Graphiti integration

**Purpose**: Implements Graphiti graph database backend for persistent memory

**Key Methods**:
- `store_episode()` - Store conversation episode
- `query_graph()` - Query knowledge graph
- `add_entity()` - Add entity to graph

### `models.py`

**Key Exports:**
- `MemoryEntry` - Base memory entry model
- `SessionInsight` - Session insight model
- `ContextItem` - Context item model

**Purpose**: Data models for memory entries

## Public API

### Basic Usage

```python
from memory import MemoryManager

# Initialize memory manager
manager = MemoryManager(
    spec_dir=".auto-claude/specs/001",
    project_dir="./",
    backend="graphiti"
)

# Store context
manager.add_context(
    content="User prefers React hooks over class components",
    category="pattern"
)

# Retrieve context
context = manager.get_context_for_session(
    query="Implementing new React component"
)

# Add session insight
manager.add_session_insight(
    insight="Pattern: use Zustand for state management",
    confidence=0.9
)
```

### Advanced Usage

```python
# Multi-backend setup
manager = MemoryManager(
    spec_dir=".auto-claude/specs/001",
    project_dir="./",
    backends=["graphiti", "session", "file"]
)

# Search across all backends
results = manager.search(
    query="authentication patterns",
    limit=10,
    min_confidence=0.7
)

# Export memory for debugging
manager.export_to_json("debug-memory.json")
```

## Benefits

- **Unified Interface**: Single API across different memory backends
- **Pluggable Backends**: Easy to add new storage implementations
- **Type Safety**: Full type hints for better IDE support
- **Async Support**: Non-blocking memory operations
- **Context-Aware**: Retrieves relevant context based on current task

## Module Dependencies

```
memory/
├── graphiti (external) - Graph database integration
├── pydantic (external) - Data validation
└── core.client (internal) - Claude SDK client
```

## Configuration

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GRAPHITI_ENABLED` | boolean | `true` | Enable Graphiti backend |
| `MEMORY_CACHE_SIZE` | integer | `1000` | Max cached entries |
| `MEMORY_BACKEND` | string | `graphiti` | Default backend to use |

### Configuration File

```python
# memory_config.py
from memory import MemoryConfig

config = MemoryConfig(
    backend="graphiti",
    cache_enabled=True,
    cache_size=1000,
    auto_save=True
)
```

## Testing

### Unit Tests

```bash
pytest tests/test_memory_manager.py -v
```

**Coverage**: 92%

### Integration Tests

```bash
pytest tests/integration/test_memory_backends.py -v
```

## Migration Guide

### From Old Memory System

```python
# Old approach
from context import get_context
context = get_context(spec_dir)

# New approach
from memory import MemoryManager
manager = MemoryManager(spec_dir=spec_dir)
context = manager.get_context_for_session(query)
```

## Related Documentation

- [Graphiti Integration Guide](../../docs/architecture/integration-guide.md)
- [Session Management](../../docs/modules/session-manager.md)
- [Context System](../../docs/architecture/context-system.md)
