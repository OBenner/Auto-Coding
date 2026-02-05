# Integration Guide: Graphiti Memory System

**Integration Type**: Memory/Storage
**Provider**: Graphiti Labs
**Status**: Production
**Documentation**: https://docs.graphiti.ai

## Overview

Graphiti provides a knowledge graph and semantic search system for Auto Claude's agent memory. It stores episodic memories, extracts entities and relationships, and enables context-aware retrieval across agent sessions.

## Purpose

Enable agents to:
- Store and retrieve context from previous sessions
- Build knowledge graphs of codebase relationships
- Learn patterns and best practices over time
- Avoid repeating mistakes

## Key Features

- **Knowledge Graph**: Entity-relationship graph for code context
- **Semantic Search**: Vector-based similarity search
- **Episode Storage**: Conversation history with embeddings
- **Multi-Provider**: Support for OpenAI, Anthropic, Ollama
- **Embedded DB**: LadybugDB (no Docker required)

## Prerequisites

### Required

- Python 3.12+
- Graphiti package: `pip install graphiti-core`
- OpenAI API key OR Anthropic API key

### Optional

- Ollama (for local embeddings)
- Voyage AI API key (for better embeddings)

## Configuration

### Environment Variables

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `GRAPHITI_ENABLED` | boolean | Yes | Enable Graphiti integration |
| `OPENAI_API_KEY` | string | Conditional | Required if using OpenAI provider |
| `ANTHROPIC_API_KEY` | string | Conditional | Required if using Anthropic provider |
| `GRAPHITI_LLM_PROVIDER` | string | No | LLM provider (default: anthropic) |
| `GRAPHITI_EMBEDDER_PROVIDER` | string | No | Embedder provider (default: openai) |

### Configuration File

Example `.env` file:

```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=openai
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### Setup Steps

1. Install Graphiti:
   ```bash
   cd apps/backend
   uv pip install graphiti-core
   ```

2. Configure environment variables in `apps/backend/.env`

3. Initialize memory system:
   ```python
   from integrations.graphiti.memory import get_graphiti_memory

   memory = get_graphiti_memory(
       spec_dir=".auto-claude/specs/001",
       project_dir="./"
   )
   ```

## Architecture

### Integration Structure

```
integrations/graphiti/
├── __init__.py              # Module exports
├── graphiti_config.py       # Configuration validation
├── graphiti_providers.py    # Multi-provider factory
├── memory.py               # High-level memory interface
└── queries_pkg/            # Query operations
    ├── graphiti.py         # GraphitiMemory class
    ├── client.py           # LadybugDB client
    ├── queries.py          # Graph queries
    ├── search.py           # Semantic search
    └── schema.py           # Graph schema
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `GraphitiMemory` | Main interface for memory operations |
| `ProviderFactory` | Creates LLM and embedder instances |
| `LadybugClient` | Manages embedded database connection |
| `QueryEngine` | Executes graph queries |
| `SearchEngine` | Semantic similarity search |

## Integration Points

| Location | Purpose |
|----------|---------|
| `agents/planner.py` | Load context for planning |
| `agents/coder.py` | Retrieve patterns and insights |
| `agents/qa_reviewer.py` | Check for known issues |
| `agents/memory_manager.py` | Orchestrate memory operations |

## Usage

### Basic Usage

```python
from integrations.graphiti.memory import get_graphiti_memory

# Initialize memory
memory = get_graphiti_memory(
    spec_dir=".auto-claude/specs/001",
    project_dir="./"
)

# Store episode
await memory.add_episode(
    name="Implementing auth",
    episode_body="User implemented OAuth authentication using PassportJS",
    source_description="coder-agent-session"
)

# Retrieve context
context = await memory.get_context_for_session(
    query="How to handle authentication?"
)

# Add insight
await memory.add_session_insight(
    insight="Pattern: Use middleware for auth validation",
    category="pattern"
)
```

### Advanced Usage

```python
# Search with filters
results = await memory.search(
    query="React component patterns",
    limit=10,
    category="pattern",
    min_confidence=0.8
)

# Query graph directly
entities = await memory.query_graph(
    "MATCH (e:Entity) WHERE e.type = 'module' RETURN e"
)

# Export memory for debugging
await memory.export_to_json("debug-memory.json")
```

## Authentication

### Credential Storage

- **API Keys**: Stored in `.env` file (gitignored)
- **Never commit**: Add `.env` to `.gitignore`

### Security Best Practices

- Rotate API keys regularly
- Use environment-specific keys
- Limit key permissions
- Monitor API usage

## API Reference

### GraphitiMemory Methods

#### `add_episode(name, episode_body, source_description)`

Store a conversation episode in memory.

**Parameters:**
- `name` (str): Episode title
- `episode_body` (str): Conversation content
- `source_description` (str): Source identifier

**Returns:** Episode ID

**Example:**
```python
episode_id = await memory.add_episode(
    name="Bug fix session",
    episode_body="Fixed null pointer in auth flow",
    source_description="coder-agent"
)
```

#### `get_context_for_session(query, limit=10)`

Retrieve relevant context for current session.

**Parameters:**
- `query` (str): Context query
- `limit` (int): Max results

**Returns:** List[ContextItem]

**Example:**
```python
context = await memory.get_context_for_session(
    query="Authentication implementation",
    limit=5
)
```

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `GraphitiNotEnabled` | Missing env var | Set `GRAPHITI_ENABLED=true` |
| `InvalidProvider` | Unknown provider | Check `GRAPHITI_LLM_PROVIDER` value |
| `APIKeyMissing` | No API key | Set provider API key in `.env` |
| `DatabaseConnectionFailed` | DB init failed | Check disk space and permissions |

### Handling Patterns

```python
from integrations.graphiti.exceptions import GraphitiError

try:
    context = await memory.get_context_for_session(query)
except GraphitiError as e:
    logger.error(f"Memory error: {e}")
    # Fall back to no context
    context = []
```

## Testing

### Unit Tests

```bash
pytest tests/test_graphiti_integration.py -v
```

### Integration Tests

```bash
# Requires API keys in .env.test
pytest tests/integration/test_graphiti_memory.py -v
```

### Manual Testing

1. Initialize memory system
2. Add test episode
3. Query for context
4. Verify results returned

## Performance Considerations

### Rate Limits

| Provider | Rate Limit | Retry Strategy |
|----------|-----------|----------------|
| OpenAI | 3,500 RPM | Exponential backoff |
| Anthropic | 4,000 RPM | Exponential backoff |
| Voyage AI | 300 RPM | Queue with retry |

### Optimization Tips

- Cache frequent queries
- Batch episode additions
- Use local embeddings (Ollama) for development
- Limit context retrieval size

## Troubleshooting

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

**Issue**: Slow context retrieval
**Diagnostic**: Check embedding provider latency
**Solution**: Use cached embeddings or switch to faster provider

**Issue**: Duplicate entities in graph
**Diagnostic**: Check entity extraction logic
**Solution**: Implement entity deduplication

## Related Documentation

- [Memory Architecture](../modules/memory-system.md)
- [Agent System](../modules/backend-architecture.md)
- [Graphiti Official Docs](https://docs.graphiti.ai)
