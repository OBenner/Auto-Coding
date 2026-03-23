# Memory System API Reference

Complete reference for Auto Code's Graphiti-based memory system, including configuration, pattern learning, code relationship tracking, and cross-session context retrieval.

## Overview

Auto Code uses **Graphiti** as its primary memory system with embedded LadybugDB (no Docker required). The memory system provides:

- **Persistent Knowledge Graph** - Semantic search across all sessions
- **Pattern Learning** - Automatic extraction of code patterns, gotchas, and best practices
- **Code Relationship Tracking** - Function calls, imports, inheritance hierarchies
- **Cross-Session Context** - Relevant context retrieval for new tasks
- **Multi-Provider Support** - OpenAI, Anthropic, Azure, Ollama, Google AI, OpenRouter

**Key Features:**
- Zero-dependency embedded database (LadybugDB)
- Dual-layer fallback (Graphiti PRIMARY, file-based FALLBACK)
- Multi-provider LLM and embedder support
- Project-wide or spec-isolated memory scopes
- Automatic pattern extraction from code changes

---

## Architecture

### Memory Layers

```
┌─────────────────────────────────────────┐
│         Agent Sessions                   │
│  (Planner, Coder, QA Reviewer/Fixer)   │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│      Memory Manager                      │
│  (agents/memory_manager.py)             │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┴─────────┐
    ▼                   ▼
┌─────────────┐   ┌─────────────────┐
│  Graphiti   │   │  File-based     │
│  (PRIMARY)  │   │  (FALLBACK)     │
└─────────────┘   └─────────────────┘
```

### Graphiti Components

The Graphiti integration is organized into specialized modules:

- **`integrations/graphiti/queries_pkg/graphiti.py`** - Main GraphitiMemory class (facade)
- **`integrations/graphiti/queries_pkg/client.py`** - LadybugDB client wrapper
- **`integrations/graphiti/queries_pkg/queries.py`** - Episode storage operations
- **`integrations/graphiti/queries_pkg/search.py`** - Semantic search logic
- **`integrations/graphiti/queries_pkg/schema.py`** - Data structures and constants
- **`integrations/graphiti/queries_pkg/code_relationships.py`** - Code graph operations
- **`integrations/graphiti/config.py`** - Configuration and validation
- **`integrations/graphiti/providers_pkg/`** - Multi-provider factory
- **`integrations/graphiti/pattern_learner.py`** - Pattern extraction engine
- **`integrations/graphiti/pattern_suggester.py`** - Context-aware pattern suggestions
- **`agents/memory_manager.py`** - Agent-facing memory API

---

## Core Memory API

### GraphitiMemory Class

Main interface for memory operations. Provides high-level API for storing and retrieving knowledge.

::: apps.backend.integrations.graphiti.queries_pkg.graphiti
    options:
      show_root_heading: true
      show_source: false
      members:
        - GraphitiMemory
        - GraphitiMemory.__init__
        - GraphitiMemory.initialize
        - GraphitiMemory.close
        - GraphitiMemory.add_episode
        - GraphitiMemory.add_session_insight
        - GraphitiMemory.add_codebase_discovery
        - GraphitiMemory.add_pattern
        - GraphitiMemory.add_gotcha
        - GraphitiMemory.search
        - GraphitiMemory.get_relevant_context
        - GraphitiMemory.get_context_for_session

**Usage Example:**
```python
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

# Create memory instance
memory = get_graphiti_memory(
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("/path/to/project"),
    group_id_mode="project"  # or "spec" for isolated memory
)

# Initialize connection
await memory.initialize()

# Store session insight
await memory.add_session_insight(
    content="React hooks pattern: useState for local state, useContext for shared state",
    source_description="Coder session - auth feature implementation"
)

# Store codebase discovery
await memory.add_codebase_discovery(
    file_path="src/auth/AuthProvider.tsx",
    purpose="Global authentication context provider using React Context API",
    key_insights=["Wraps entire app", "Manages login/logout state", "Provides useAuth hook"]
)

# Retrieve relevant context
context = await memory.get_context_for_session(
    task_description="Implement user profile page with authentication"
)
print(f"Found {len(context)} relevant facts from memory")

# Clean up
await memory.close()
```

---

### Memory Manager (Agent-Facing API)

Orchestrates memory operations for agent sessions. Provides simplified API for common agent workflows.

::: apps.backend.agents.memory_manager
    options:
      show_root_heading: true
      show_source: false
      members:
        - get_session_context
        - debug_memory_system_status
        - learn_patterns
        - save_session_memory

**Usage Example:**
```python
from pathlib import Path
from agents.memory_manager import get_session_context, learn_patterns

# Get session context manager
session_context = await get_session_context(
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("/path/to/project")
)

if session_context:
    # Load conversation history
    messages = await session_context.load_conversation_history()

    # Add message to history
    await session_context.add_message(
        role="user",
        content="Implement authentication"
    )

    # Save conversation
    await session_context.save_conversation_history()

# Learn patterns from modified files
patterns_learned = await learn_patterns(
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("/path/to/project"),
    modified_files=[Path("src/auth.js"), Path("src/login.js")],
    pattern_types=["api", "error", "state"]
)
print(f"Learned {patterns_learned} new patterns")
```

---

## Configuration

### GraphitiConfig Class

Manages Graphiti configuration from environment variables with validation.

::: apps.backend.integrations.graphiti.config
    options:
      show_root_heading: true
      show_source: false
      members:
        - GraphitiConfig
        - GraphitiConfig.from_env
        - GraphitiConfig.is_valid
        - GraphitiConfig.get_validation_errors
        - GraphitiConfig.get_provider_summary
        - is_graphiti_enabled
        - get_graphiti_status

**Usage Example:**
```python
from integrations.graphiti.config import GraphitiConfig, is_graphiti_enabled, get_graphiti_status

# Check if Graphiti is enabled
if is_graphiti_enabled():
    print("Graphiti memory system is enabled")

# Get detailed status
status = get_graphiti_status()
print(f"Available: {status['available']}")
print(f"LLM Provider: {status['llm_provider']}")
print(f"Embedder: {status['embedder_provider']}")

# Load configuration
config = GraphitiConfig.from_env()
if config.is_valid():
    print(f"Configuration valid: {config.get_provider_summary()}")
else:
    print(f"Errors: {config.get_validation_errors()}")
```

---

## Pattern Learning

### PatternLearner

Extracts code patterns from modified files during agent sessions.

::: apps.backend.integrations.graphiti.pattern_learner
    options:
      show_root_heading: true
      show_source: false
      members:
        - PatternLearner
        - PatternLearner.__init__
        - PatternLearner.learn_from_files
        - PatternLearner.extract_patterns_from_file

**Usage Example:**
```python
from pathlib import Path
from integrations.graphiti.pattern_learner import PatternLearner

# Create learner instance
learner = PatternLearner(
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("/path/to/project")
)

# Learn patterns from modified files
modified_files = [
    Path("src/components/Button.tsx"),
    Path("src/hooks/useAuth.ts")
]

patterns = await learner.learn_from_files(
    modified_files=modified_files,
    pattern_types=["api", "error", "state", "import"]
)

print(f"Extracted {len(patterns)} patterns")
for pattern in patterns:
    print(f"  - {pattern['category']}: {pattern['description']}")
```

---

### PatternSuggester

Suggests relevant patterns based on current task context.

::: apps.backend.integrations.graphiti.pattern_suggester
    options:
      show_root_heading: true
      show_source: false
      members:
        - PatternSuggester
        - PatternSuggester.__init__
        - PatternSuggester.get_suggestions
        - PatternSuggester.get_suggestions_for_file

**Usage Example:**
```python
from pathlib import Path
from integrations.graphiti.pattern_suggester import PatternSuggester

# Create suggester instance
suggester = PatternSuggester(
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("/path/to/project")
)

# Get suggestions for current task
suggestions = await suggester.get_suggestions(
    task_description="Implement user authentication with JWT tokens",
    file_context=["src/auth/", "src/api/"]
)

print(f"Found {len(suggestions)} relevant patterns:")
for suggestion in suggestions:
    print(f"  - {suggestion['pattern']}")
    print(f"    Confidence: {suggestion['confidence']}")
    print(f"    Source: {suggestion['source']}")
```

---

## Code Relationship Tracking

### CodeRelationshipQueries

Stores and queries code relationships (function calls, imports, inheritance).

::: apps.backend.integrations.graphiti.queries_pkg.code_relationships
    options:
      show_root_heading: true
      show_source: false
      members:
        - CodeRelationshipQueries
        - CodeRelationshipQueries.store_code_relationships
        - CodeRelationshipQueries.query_function_calls
        - CodeRelationshipQueries.query_imports
        - CodeRelationshipQueries.find_related_code

**Usage Example:**
```python
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

# Get memory instance
memory = get_graphiti_memory(
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("/path/to/project")
)
await memory.initialize()

# Store code relationships
relationships = [
    {
        "type": "calls",
        "source": "src/auth.js::login",
        "target": "src/api.js::post",
        "context": "Makes API call to /auth/login endpoint"
    },
    {
        "type": "imports",
        "source": "src/auth.js",
        "target": "src/api.js",
        "context": "Import { post } from './api'"
    }
]

await memory._code_relationships.store_code_relationships(relationships)

# Query function calls
calls = await memory._code_relationships.query_function_calls(
    function_name="login"
)
print(f"Function 'login' calls: {calls}")

# Find related code
related = await memory._code_relationships.find_related_code(
    file_path="src/auth.js",
    max_depth=2
)
print(f"Related files: {related}")

await memory.close()
```

---

## Session Context Management

### SessionContext

Manages conversation history and session state in Graphiti.

::: apps.backend.agents.session_context
    options:
      show_root_heading: true
      show_source: false
      members:
        - SessionContext
        - SessionContext.__init__
        - SessionContext.initialize
        - SessionContext.load_conversation_history
        - SessionContext.save_conversation_history
        - SessionContext.add_message
        - SessionContext.get_code_references
        - SessionContext.optimize_context_window

**Usage Example:**
```python
from pathlib import Path
from agents.session_context import SessionContext

# Create session context
session = SessionContext(
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("/path/to/project")
)

# Initialize Graphiti connection
if await session.initialize():
    # Load previous conversation
    messages = await session.load_conversation_history()
    print(f"Loaded {len(messages)} previous messages")

    # Add new messages
    await session.add_message(
        role="user",
        content="Implement user authentication"
    )
    await session.add_message(
        role="assistant",
        content="I'll implement JWT-based authentication...",
        code_references=["src/auth.js", "src/middleware/auth.js"]
    )

    # Optimize context window (remove old messages if needed)
    optimized = await session.optimize_context_window(
        max_tokens=100000
    )

    # Save updated conversation
    await session.save_conversation_history()
```

---

## Multi-Provider Support

### Provider Factory

Creates LLM and embedder instances for different providers.

::: apps.backend.integrations.graphiti.providers_pkg.factory
    options:
      show_root_heading: true
      show_source: false
      members:
        - create_llm
        - create_embedder

**Supported Providers:**

**LLM Providers:**
- **OpenAI** - GPT-4, GPT-3.5
- **Anthropic** - Claude Sonnet, Opus, Haiku
- **Azure OpenAI** - Enterprise deployments
- **Ollama** - Local models (DeepSeek, Llama, etc.)
- **Google AI** - Gemini models
- **OpenRouter** - Multi-model gateway

**Embedder Providers:**
- **OpenAI** - text-embedding-3-small, text-embedding-3-large
- **Voyage AI** - voyage-3, voyage-large-2
- **Azure OpenAI** - Enterprise embeddings
- **Ollama** - Local embedding models (nomic-embed-text, bge-large, etc.)
- **Google AI** - text-embedding-004
- **OpenRouter** - Multi-model embeddings

**Usage Example:**
```python
from integrations.graphiti.providers_pkg import create_llm, create_embedder

# Create OpenAI LLM
llm = create_llm(
    provider="openai",
    api_key="sk-...",
    model_name="gpt-4"
)

# Create Voyage embedder (common with Anthropic LLM)
embedder = create_embedder(
    provider="voyage",
    api_key="pa-...",
    model_name="voyage-3"
)

# Create Ollama local models
local_llm = create_llm(
    provider="ollama",
    base_url="http://localhost:11434",
    model_name="deepseek-r1:7b"
)

local_embedder = create_embedder(
    provider="ollama",
    base_url="http://localhost:11434",
    model_name="nomic-embed-text"
)
```

---

## Environment Variables

### Core Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `GRAPHITI_ENABLED` | Enable Graphiti memory system | `true` |
| `GRAPHITI_LLM_PROVIDER` | LLM provider (openai\|anthropic\|azure_openai\|ollama\|google\|openrouter) | `openai` |
| `GRAPHITI_EMBEDDER_PROVIDER` | Embedder provider (openai\|voyage\|azure_openai\|ollama\|google\|openrouter) | `openai` |
| `GRAPHITI_DATABASE` | Database name | `auto_claude_memory` |
| `GRAPHITI_DB_PATH` | Database storage path | `~/.auto-claude/memories` |

### OpenAI Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | API key | Required |
| `OPENAI_MODEL` | LLM model | `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | `text-embedding-3-small` |

### Anthropic Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | API key | Required |
| `GRAPHITI_ANTHROPIC_MODEL` | LLM model | `claude-sonnet-4-5-20250929` |

**Note:** Anthropic does not provide embeddings. Use Voyage AI or OpenAI embedder.

### Azure OpenAI Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `AZURE_OPENAI_API_KEY` | API key | Required |
| `AZURE_OPENAI_BASE_URL` | Endpoint URL | Required |
| `AZURE_OPENAI_LLM_DEPLOYMENT` | LLM deployment name | Required |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding deployment name | Required |

### Voyage AI Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `VOYAGE_API_KEY` | API key | Required |
| `VOYAGE_EMBEDDING_MODEL` | Embedding model | `voyage-3` |

### Google AI Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `GOOGLE_API_KEY` | API key | Required |
| `GOOGLE_LLM_MODEL` | LLM model | `gemini-2.0-flash-exp` |
| `GOOGLE_EMBEDDING_MODEL` | Embedding model | `text-embedding-004` |

### Ollama Configuration (Local)

| Variable | Purpose | Default |
|----------|---------|---------|
| `OLLAMA_BASE_URL` | Server URL | `http://localhost:11434` |
| `OLLAMA_LLM_MODEL` | LLM model (e.g., deepseek-r1:7b) | Required |
| `OLLAMA_EMBEDDING_MODEL` | Embedding model (e.g., nomic-embed-text) | Required |
| `OLLAMA_EMBEDDING_DIM` | Embedding dimension (auto-detected for known models) | Auto |

**Supported Ollama Embedding Models:**
- `nomic-embed-text` (768 dimensions)
- `mxbai-embed-large` (1024 dimensions)
- `bge-large` (1024 dimensions)
- `all-minilm` (384 dimensions)

### OpenRouter Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENROUTER_API_KEY` | API key | Required |
| `OPENROUTER_LLM_MODEL` | LLM model (e.g., anthropic/claude-3.5-sonnet) | Required |
| `OPENROUTER_EMBEDDING_MODEL` | Embedding model | Required |

---

## Memory Scopes

### Group ID Modes

Graphiti supports two memory scoping modes:

**1. Spec-Isolated Mode (GroupIdMode.SPEC)**
```python
memory = get_graphiti_memory(
    spec_dir=Path(".auto-claude/specs/001-auth"),
    project_dir=Path("/path/to/project"),
    group_id_mode="spec"  # Each spec has isolated memory
)
```

- Each spec gets its own isolated knowledge graph
- Patterns learned in spec 001 are NOT visible to spec 002
- Use when specs are unrelated or require strict isolation
- Namespace: `spec_001`, `spec_002`, etc.

**2. Project-Wide Mode (GroupIdMode.PROJECT)** *(Default)*
```python
memory = get_graphiti_memory(
    spec_dir=Path(".auto-claude/specs/001-auth"),
    project_dir=Path("/path/to/project"),
    group_id_mode="project"  # All specs share project memory
)
```

- All specs share the same knowledge graph
- Patterns learned in any spec benefit all future specs
- Enables cross-spec learning and context reuse
- Namespace: based on project path hash
- **Recommended for most use cases**

---

## Best Practices

### Memory System Usage

1. **Always initialize and close:**
   ```python
   memory = get_graphiti_memory(spec_dir, project_dir)
   await memory.initialize()
   try:
       # Use memory
       await memory.add_session_insight(...)
   finally:
       await memory.close()
   ```

2. **Use project-wide scope by default:**
   ```python
   # Enables cross-spec learning
   memory = get_graphiti_memory(
       spec_dir, project_dir,
       group_id_mode="project"
   )
   ```

3. **Store rich context in episodes:**
   ```python
   await memory.add_codebase_discovery(
       file_path="src/auth/AuthProvider.tsx",
       purpose="Detailed purpose with architecture context",
       key_insights=[
           "Specific pattern used",
           "Gotcha to avoid",
           "Integration point with X"
       ]
   )
   ```

4. **Check availability before use:**
   ```python
   if memory.is_enabled and await memory.initialize():
       # Use Graphiti
       context = await memory.get_context_for_session(task)
   else:
       # Fall back to file-based memory
       context = load_file_memory()
   ```

### Pattern Learning

1. **Learn patterns after each session:**
   ```python
   patterns_learned = await learn_patterns(
       spec_dir, project_dir,
       modified_files=modified_files,
       pattern_types=["api", "error", "state", "import"]
   )
   ```

2. **Use pattern suggestions during planning:**
   ```python
   suggester = PatternSuggester(spec_dir, project_dir)
   suggestions = await suggester.get_suggestions(task_description)
   # Include suggestions in planner prompt
   ```

3. **Store gotchas immediately when discovered:**
   ```python
   await memory.add_gotcha(
       content="Don't forget to call useEffect cleanup",
       context="React hooks - prevents memory leaks",
       severity="high"
   )
   ```

### Provider Selection

1. **OpenAI (Default)** - Best balance of speed, quality, cost
   ```bash
   export GRAPHITI_LLM_PROVIDER=openai
   export GRAPHITI_EMBEDDER_PROVIDER=openai
   export OPENAI_API_KEY=sk-...
   ```

2. **Anthropic + Voyage** - Best quality, higher cost
   ```bash
   export GRAPHITI_LLM_PROVIDER=anthropic
   export GRAPHITI_EMBEDDER_PROVIDER=voyage
   export ANTHROPIC_API_KEY=sk-ant-...
   export VOYAGE_API_KEY=pa-...
   ```

3. **Ollama (Local)** - Privacy, no API costs, requires local GPU
   ```bash
   export GRAPHITI_LLM_PROVIDER=ollama
   export GRAPHITI_EMBEDDER_PROVIDER=ollama
   export OLLAMA_LLM_MODEL=deepseek-r1:7b
   export OLLAMA_EMBEDDING_MODEL=nomic-embed-text
   ```

### Performance Optimization

1. **Limit search results:**
   ```python
   context = await memory.search(
       query="authentication patterns",
       max_results=10  # Don't retrieve too many
   )
   ```

2. **Use specific episode types:**
   ```python
   # More specific = faster retrieval
   patterns = await memory.search(
       query="error handling",
       episode_type="pattern"  # Only search patterns
   )
   ```

3. **Optimize conversation history:**
   ```python
   # Remove old messages to stay within context window
   await session_context.optimize_context_window(
       max_tokens=100000
   )
   ```

---

## Error Handling

### Common Memory Errors

**Graphiti Not Available:**
```
Error: Graphiti is not available
```
**Solution:** System automatically falls back to file-based memory. Check `get_graphiti_status()` for details.

**Configuration Error:**
```
Error: Missing required API key for provider 'openai'
```
**Solution:** Set required environment variable (e.g., `OPENAI_API_KEY`). Use `GraphitiConfig.get_validation_errors()` to see all issues.

**Database Connection Failed:**
```
Error: Failed to connect to LadybugDB
```
**Solution:** Ensure Python 3.12+ is installed and database path is writable. Check `GRAPHITI_DB_PATH` permissions.

**Provider Not Supported:**
```
Error: Unknown provider 'custom_llm'
```
**Solution:** Use one of the supported providers: openai, anthropic, azure_openai, ollama, google, openrouter.

**Embedding Dimension Mismatch:**
```
Error: Ollama embedding dimension not specified
```
**Solution:** Either use a known model (auto-detected) or set `OLLAMA_EMBEDDING_DIM` manually.

---

## Testing

### Memory System Tests

**Unit Tests:**
```bash
# Test Graphiti integration
pytest tests/test_graphiti_memory.py -v

# Test pattern learning
pytest tests/test_pattern_learner.py -v

# Test configuration
pytest tests/test_graphiti_config.py -v
```

**Integration Tests:**
```bash
# Test with real Graphiti instance (requires API keys)
export GRAPHITI_ENABLED=true
export OPENAI_API_KEY=sk-...
pytest tests/integration/test_memory_system.py -v
```

**Provider Tests:**
```bash
# Test multi-provider support
pytest tests/test_graphiti_providers.py -v
```

---

## See Also

- [Agents API Reference](./agents.md) - Agent system documentation
- [Backend API Reference](./backend-api.md) - Core module documentation
- [Memory System Diagram](../diagrams/memory-system.mermaid) - Architecture visualization
- [Pattern Learning Guide](../../guides/PATTERN_LEARNING.md) - How pattern learning works
- [Graphiti Documentation](https://github.com/getzep/graphiti) - Upstream Graphiti docs

---

**Version:** 2.8.0
**Last Updated:** 2026-03-05
**Maintained By:** Auto Code Team
