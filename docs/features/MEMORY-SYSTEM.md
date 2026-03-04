# Memory System

Auto Code's memory system provides persistent, semantic knowledge storage and retrieval across AI agent sessions using Graphiti knowledge graphs with LadybugDB (embedded, no Docker required).

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Core Components](#core-components)
- [Multi-Provider Support](#multi-provider-support)
- [Episode Types](#episode-types)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [State Management](#state-management)
- [Migration](#migration)
- [Advanced Features](#advanced-features)
- [Performance Considerations](#performance-considerations)

## Overview

The memory system enables **cross-session learning** by storing agent insights, codebase discoveries, patterns, and gotchas in a knowledge graph. Agents can retrieve relevant context from past sessions to improve future performance.

### What It Does

- **Persistent memory** - Stores insights across sessions using Graphiti knowledge graphs
- **Semantic search** - Retrieves context using natural language queries
- **Cross-session learning** - Patterns and gotchas discovered in one spec help future specs
- **Multi-provider support** - Works with OpenAI, Anthropic, Voyage AI, Azure OpenAI, Ollama, Google AI, and OpenRouter
- **Graceful fallback** - File-based memory when Graphiti is unavailable

### Key Benefits

✅ **Zero dependencies** - LadybugDB embedded, no Docker required
✅ **Semantic retrieval** - Find context by purpose, not just keywords
✅ **Cross-project learning** - Project-wide memory mode enables knowledge sharing
✅ **Provider flexibility** - Switch between LLM and embedder providers without code changes
✅ **Automatic migration** - Database namespacing prevents embedding dimension conflicts

## Architecture

The memory system uses a dual-layer architecture with Graphiti as primary and file-based storage as fallback.

```
┌─────────────────────────────────────────────────────────────┐
│                   Memory System                        │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴─────────────────┐
        │                                 │
        ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│   PRIMARY       │            │   FALLBACK      │
│  Graphiti       │            │  File-based      │
│  (when enabled) │            │  (always works)  │
└──────────────────┘            └──────────────────┘
        │                                 │
        │                                 │
        ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│ LadybugDB       │            │  JSON files in  │
│ (embedded graph  │            │  memory/        │
│   database)     │            │  session_*json  │
└──────────────────┘            └──────────────────┘
```

### Memory Modes

**1. Project Mode (Default)**

```python
memory = GraphitiMemory(
    spec_dir=spec_dir,
    project_dir=project_dir,
    group_id_mode="project"  # Default
)
```

- **Shared knowledge** across all specs in the same project
- **Cross-spec learning** - discoveries from Spec 001 help Spec 002
- **Group ID:** `project_{name}_{hash}` (e.g., `project_auto-claude_a1b2c3d4`)

**2. Spec Mode (Isolated)**

```python
memory = GraphitiMemory(
    spec_dir=spec_dir,
    project_dir=project_dir,
    group_id_mode="spec"  # Isolated per spec
)
```

- **Isolated memory** per spec
- **No cross-contamination** between unrelated features
- **Group ID:** Spec folder name (e.g., `001-add-auth`)

### Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              GraphitiMemory (Facade)                   │
│  apps/backend/integrations/graphiti/queries_pkg/       │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Client      │  │   Queries    │  │   Search     │
│              │  │              │  │              │
│ Connection   │  │ Episode      │  │ Semantic     │
│ management   │  │ storage      │  │ retrieval    │
│              │  │              │  │              │
│ initialize() │  │ add_*()      │  │ get_*()     │
│ close()      │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┴─────────────────┘
                          │
                          ▼
                ┌──────────────────┐
                │  LadybugDB      │
                │  (Knowledge Graph)│
                └──────────────────┘
```

## Quick Start

### Step 1: Enable Graphiti

Set environment variable in `apps/backend/.env`:

```bash
# Enable Graphiti
GRAPHITI_ENABLED=true

# Configure providers (default: OpenAI)
GRAPHITI_LLM_PROVIDER=openai
GRAPHITI_EMBEDDER_PROVIDER=openai

# Set API keys
OPENAI_API_KEY=sk-...
```

### Step 2: Use Memory in Agents

```python
from pathlib import Path
from memory import get_graphiti_memory

# Get memory instance
memory = get_graphiti_memory(
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("/path/to/project")
)

# Initialize (connects to LadybugDB)
await memory.initialize()

# Save session insights
await memory.save_session_insights(
    session_num=1,
    insights={
        "discoveries": {
            "files_understood": {
                "auth.py": "Handles user authentication with JWT tokens"
            }
        },
        "patterns_found": [
            {
                "pattern": "Use @login_required decorator for protected routes",
                "applies_to": "authentication"
            }
        ],
        "gotchas_encountered": [
            {
                "gotcha": "JWT tokens expire after 1 hour",
                "solution": "Implement refresh token rotation"
            }
        ]
    }
)

# Retrieve relevant context
context = await memory.get_relevant_context(
    query="How to implement user authentication?",
    num_results=5
)

# Close connection
await memory.close()
```

### Step 3: Retrieve Context for New Sessions

```python
from agents.memory_manager import get_graphiti_context

# Get context for current subtask
context = await get_graphiti_context(
    spec_dir=spec_dir,
    project_dir=project_dir,
    subtask={
        "id": "subtask-1",
        "description": "Implement user authentication"
    }
)

# Context includes:
# - Past session insights
# - Learned patterns (cross-session!)
# - Known gotchas (cross-session!)
# - Relevant codebase discoveries
```

## Core Components

### GraphitiMemory

**Location:** `apps/backend/integrations/graphiti/queries_pkg/graphiti.py`

**Purpose:** High-level facade for Graphiti memory operations

**Key Methods:**

```python
class GraphitiMemory:
    """Manage Graphiti-based persistent memory for sessions."""

    async def initialize(self) -> bool:
        """Initialize LadybugDB connection and build indices."""

    async def close(self) -> None:
        """Close database connection."""

    # Storage methods
    async def save_session_insights(self, session_num: int, insights: dict) -> bool:
        """Save session insights as an episode."""

    async def save_codebase_discoveries(self, discoveries: dict[str, str]) -> bool:
        """Save file purposes and patterns discovered."""

    async def save_pattern(self, pattern: str) -> bool:
        """Save a code pattern to knowledge graph."""

    async def save_gotcha(self, gotcha: str) -> bool:
        """Save a pitfall to avoid."""

    async def save_task_outcome(self, task_id: str, success: bool, outcome: str) -> bool:
        """Save task outcome for learning."""

    async def save_user_correction(self, what_was_wrong: str, what_was_corrected: str) -> bool:
        """Save user correction for learning from mistakes."""

    async def save_preference_profile(self, profile_data: dict) -> bool:
        """Save user preference profile."""

    # Retrieval methods
    async def get_relevant_context(self, query: str, num_results: int = 5) -> list[dict]:
        """Search knowledge graph for relevant context."""

    async def get_session_history(self, limit: int = 5) -> list[dict]:
        """Get recent session insights."""

    async def get_patterns_and_gotchas(self, query: str, num_results: int = 5) -> tuple[list[dict], list[dict]]:
        """Get patterns and gotchas for cross-session learning."""

    async def get_preference_profile(self) -> dict | None:
        """Retrieve user preference profile."""

    # Properties
    @property
    def is_enabled(self) -> bool:
        """Check if Graphiti is enabled and configured."""

    @property
    def is_initialized(self) -> bool:
        """Check if database connection is ready."""

    @property
    def group_id(self) -> str:
        """Get memory namespace (spec or project)."""

    @property
    def spec_context_id(self) -> str:
        """Get spec-specific context ID."""
```

### Memory Manager

**Location:** `apps/backend/agents/memory_manager.py`

**Purpose:** Orchestrates memory operations with dual-layer fallback

**Key Functions:**

```python
async def get_graphiti_context(
    spec_dir: Path,
    project_dir: Path,
    subtask: dict
) -> str | None:
    """
    Retrieve relevant context from Graphiti for the current subtask.

    Returns formatted context with:
    - Relevant knowledge from past sessions
    - Learned patterns (cross-session)
    - Known gotchas (cross-session)
    - Recent session history
    """

async def save_session_memory(
    spec_dir: Path,
    project_dir: Path,
    subtask_id: str,
    session_num: int,
    success: bool,
    subtasks_completed: list[str],
    discoveries: dict | None = None,
) -> tuple[bool, str]:
    """
    Save session insights to memory.

    Memory Strategy:
    - PRIMARY: Graphiti (when enabled) - semantic search, cross-session context
    - FALLBACK: File-based (when Graphiti is disabled) - zero dependencies

    Returns:
        Tuple of (success, storage_type) where storage_type is "graphiti" or "file"
    """

async def save_feedback(
    spec_dir: Path,
    project_dir: Path,
    feedback_type: str,
    task_description: str,
    agent_type: str,
    context: dict | None = None,
) -> bool:
    """
    Save user feedback (accept/reject/modify) to memory and update preferences.

    Tracks all user interactions with agent outputs and updates preference
    profile to enable adaptive behavior.
    """

async def get_pattern_suggestions(
    spec_dir: Path,
    project_dir: Path,
    query: str,
    categories: list[str] | None = None,
    num_results: int = 5,
    min_score: float = 0.5,
) -> str | None:
    """
    Retrieve pattern suggestions from Graphiti for the current task.

    Searches knowledge graph for relevant code patterns that match
    the task query, returning categorized patterns with confidence scores.
    """
```

### SessionContext

**Location:** `apps/backend/agents/session_context.py`

**Purpose:** Manages conversation history and context storage in Graphiti

**Features:**
- Persist conversation history across restarts
- Track code references
- Optimize context window for AI sessions

## Multi-Provider Support

The memory system supports multiple LLM and embedding providers through a factory pattern.

### Supported Providers

**LLM Providers:**
- **OpenAI** - GPT-4, GPT-4o, GPT-5-mini
- **Anthropic** - Claude Sonnet 4.5 (Claude Agent SDK default)
- **Azure OpenAI** - Azure-hosted GPT models
- **Google AI** - Gemini 2.0 Flash
- **Ollama** - Local models (DeepSeek, Llama, Mistral)
- **OpenRouter** - Multi-provider aggregator

**Embedder Providers:**
- **OpenAI** - text-embedding-3-small (1536 dimensions)
- **Voyage AI** - voyage-3 (1024 dimensions)
- **Azure OpenAI** - Azure-hosted embeddings
- **Google AI** - text-embedding-004 (768 dimensions)
- **Ollama** - Local embedding models (auto-detects dimensions)
- **OpenRouter** - Multi-provider embeddings

### Provider Configuration

**OpenAI (Default):**

```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=openai
GRAPHITI_EMBEDDER_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

**Anthropic + Voyage AI (Common):**

```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=voyage
ANTHROPIC_API_KEY=sk-ant-...
GRAPHITI_ANTHROPIC_MODEL=claude-sonnet-4-5
VOYAGE_API_KEY=...
VOYAGE_EMBEDDING_MODEL=voyage-3
```

**Ollama (Local):**

```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=deepseek-r1:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
# OLLAMA_EMBEDDING_DIM auto-detected for known models
```

**Azure OpenAI:**

```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=azure_openai
GRAPHITI_EMBEDDER_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_BASE_URL=https://...openai.azure.com/
AZURE_OPENAI_LLM_DEPLOYMENT=gpt-4o-deployment
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=embedding-deployment
```

### Provider Factory

**Location:** `apps/backend/integrations/graphiti/providers_pkg/factory.py`

**Functionality:**
- Creates LLM and embedder instances based on configuration
- Validates provider credentials
- Handles provider-specific initialization
- Returns consistent interfaces for all providers

**Usage:**

```python
from graphiti_providers import create_llm_client, create_embedder
from graphiti_config import GraphitiConfig

config = GraphitiConfig.from_env()

# Create LLM client
llm_client = create_llm_client(config)

# Create embedder
embedder = create_embedder(config)

# Both work with any supported provider
```

## Episode Types

The memory system stores different types of knowledge as episodes in the knowledge graph.

### Session Insight

**Type:** `session_insight`

**Purpose:** General learnings from a session

**Content:**
```python
{
    "session_number": 1,
    "subtasks_completed": ["subtask-1", "subtask-2"],
    "discoveries": {
        "files_understood": {...},
        "patterns_found": [...],
        "gotchas_encountered": [...]
    },
    "what_worked": ["Used React hooks for state"],
    "what_failed": ["Forgot to handle error case"],
    "recommendations_for_next_session": ["Add error handling"]
}
```

### Codebase Discovery

**Type:** `codebase_discovery`

**Purpose:** File purposes and code structure understanding

**Content:**
```python
{
    "auth.py": "Handles user authentication with JWT tokens",
    "database.py": "PostgreSQL connection pool with retry logic",
    "utils/helpers.py": "Common utility functions for formatting"
}
```

### Pattern

**Type:** `pattern`

**Purpose:** Reusable code patterns discovered in implementation

**Content:**
```python
{
    "pattern": "Use @login_required decorator for protected routes",
    "applies_to": "authentication",
    "category": "security",
    "reasoning": "Prevents unauthorized access consistently"
}
```

### Gotcha

**Type:** `gotcha`

**Purpose:** Pitfalls to avoid in future implementations

**Content:**
```python
{
    "gotcha": "JWT tokens expire after 1 hour",
    "solution": "Implement refresh token rotation",
    "applies_to": "authentication",
    "context": "User sessions were dropping unexpectedly"
}
```

### Task Outcome

**Type:** `task_outcome`

**Purpose:** Learn from task successes and failures

**Content:**
```python
{
    "task_id": "subtask-3-2",
    "success": true,
    "outcome": "Successfully implemented user login",
    "metadata": {
        "files_modified": ["auth.py"],
        "time_taken": "45 minutes"
    }
}
```

### Root Cause

**Type:** `root_cause`

**Purpose:** Store failure analysis for debugging

**Content:**
```python
{
    "failure_type": "database_connection_timeout",
    "root_cause": {
        "issue": "Connection pool exhausted",
        "evidence": "Logs show no available connections",
        "solution": "Increase pool size or add timeout"
    },
    "failure_context": {
        "timestamp": "2025-01-15T10:30:00Z",
        "affected_files": ["database.py"]
    }
}
```

### User Correction

**Type:** `user_correction`

**Purpose:** Learn from user fixing agent mistakes

**Content:**
```python
{
    "what_was_wrong": "Agent used global state instead of React hooks",
    "what_was_corrected": "Refactored to useState for component state",
    "correction_context": {
        "file": "UserProfile.tsx",
        "subtask": "subtask-4-1"
    }
}
```

### Preference Profile

**Type:** `preference_profile`

**Purpose:** User preferences and adaptive behavior settings

**Content:**
```python
{
    "version": "1.0",
    "last_updated": "2025-01-15T10:30:00Z",
    "feedback_history": [...],
    "learned_preferences": {
        "code_style": "functional components preferred",
        "documentation": "detailed docstrings required",
        "testing": "pytest with fixtures expected"
    }
}
```

## Configuration

### Environment Variables

**Core Settings:**

| Variable | Type | Default | Description |
|-----------|--------|----------|-------------|
| `GRAPHITI_ENABLED` | bool | false | Enable Graphiti memory integration |
| `GRAPHITI_LLM_PROVIDER` | string | openai | LLM provider for RAG queries |
| `GRAPHITI_EMBEDDER_PROVIDER` | string | openai | Embedding provider for semantic search |
| `GRAPHITI_DATABASE` | string | auto_claude_memory | Graph database name |
| `GRAPHITI_DB_PATH` | string | ~/.auto-claude/memories | Database storage path |

**Provider-Specific Settings:**

| Variable | Provider | Description |
|-----------|-----------|-------------|
| `OPENAI_API_KEY` | OpenAI | OpenAI API key |
| `OPENAI_MODEL` | OpenAI | LLM model (default: gpt-5-mini) |
| `OPENAI_EMBEDDING_MODEL` | OpenAI | Embedding model (default: text-embedding-3-small) |
| `ANTHROPIC_API_KEY` | Anthropic | Anthropic API key |
| `GRAPHITI_ANTHROPIC_MODEL` | Anthropic | Model (default: claude-sonnet-4-5) |
| `VOYAGE_API_KEY` | Voyage AI | Voyage API key |
| `VOYAGE_EMBEDDING_MODEL` | Voyage AI | Model (default: voyage-3) |
| `AZURE_OPENAI_API_KEY` | Azure | Azure OpenAI API key |
| `AZURE_OPENAI_BASE_URL` | Azure | Azure endpoint URL |
| `AZURE_OPENAI_LLM_DEPLOYMENT` | Azure | LLM deployment name |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Azure | Embedding deployment name |
| `GOOGLE_API_KEY` | Google | Google AI API key |
| `GOOGLE_LLM_MODEL` | Google | LLM model (default: gemini-2.0-flash) |
| `GOOGLE_EMBEDDING_MODEL` | Google | Embedding model (default: text-embedding-004) |
| `OLLAMA_BASE_URL` | Ollama | Ollama server URL (default: http://localhost:11434) |
| `OLLAMA_LLM_MODEL` | Ollama | LLM model (e.g., deepseek-r1:7b) |
| `OLLAMA_EMBEDDING_MODEL` | Ollama | Embedding model (e.g., nomic-embed-text) |
| `OLLAMA_EMBEDDING_DIM` | Ollama | Embedding dimension (optional, auto-detected for known models) |

### Validation

```python
from graphiti_config import validate_graphiti_config

# Check if configuration is valid
is_valid, errors = validate_graphiti_config()

if not is_valid:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
```

**Common Validation Errors:**
- `GRAPHITI_ENABLED not set to true` - Set environment variable
- `OpenAI embedder provider requires OPENAI_API_KEY` - Missing API key
- `Ollama embedder provider requires OLLAMA_EMBEDDING_MODEL` - Model not specified

## API Reference

### Memory Factory

```python
from memory import get_graphiti_memory

# Get memory instance (async initialization required)
memory = get_graphiti_memory(
    spec_dir=Path(".auto-claude/specs/001-feature"),
    project_dir=Path("/path/to/project"),
    group_id_mode="project"  # or "spec"
)

# Initialize connection
await memory.initialize()

# Check if enabled
if memory.is_enabled:
    print("Graphiti is available")

# Check if initialized
if memory.is_initialized:
    print("Ready to use")
```

### Saving Insights

```python
# Session insights
await memory.save_session_insights(
    session_num=1,
    insights={
        "subtasks_completed": ["subtask-1", "subtask-2"],
        "discoveries": {
            "files_understood": {
                "auth.py": "User authentication with JWT"
            },
            "patterns_found": [
                {
                    "pattern": "Use decorators for route protection",
                    "applies_to": "authentication"
                }
            ],
            "gotchas_encountered": [
                {
                    "gotcha": "JWT expires in 1 hour",
                    "solution": "Implement refresh tokens"
                }
            ]
        },
        "what_worked": ["Decorator pattern works well"],
        "what_failed": ["Forgot error handling"],
        "recommendations_for_next_session": ["Add try/except blocks"]
    }
)

# Codebase discoveries
await memory.save_codebase_discoveries({
    "auth.py": "JWT authentication logic",
    "database.py": "PostgreSQL connection pool",
    "utils.py": "Helper functions"
})

# Individual pattern
await memory.save_pattern({
    "pattern": "Use @login_required decorator",
    "applies_to": "authentication",
    "category": "security"
})

# Individual gotcha
await memory.save_gotcha({
    "gotcha": "JWT tokens expire",
    "solution": "Implement refresh token rotation",
    "applies_to": "authentication"
})

# Task outcome
await memory.save_task_outcome(
    task_id="subtask-1",
    success=True,
    outcome="Successfully implemented authentication",
    metadata={"time_taken": "45 minutes"}
)

# Root cause analysis
await memory.save_root_cause(
    failure_type="database_timeout",
    root_cause={
        "issue": "Connection pool exhausted",
        "solution": "Increase pool size"
    },
    failure_context={"timestamp": "2025-01-15T10:30:00Z"}
)

# User correction
await memory.save_user_correction(
    what_was_wrong="Used global state",
    what_was_corrected="Refactored to useState",
    correction_context={"file": "UserProfile.tsx"}
)

# Preference profile
await memory.save_preference_profile({
    "version": "1.0",
    "learned_preferences": {
        "code_style": "functional components",
        "testing": "pytest with fixtures"
    }
})
```

### Retrieving Context

```python
# General context search
context = await memory.get_relevant_context(
    query="How to implement authentication?",
    num_results=5,
    include_project_context=True  # Include project-wide memories
)

# Session history
history = await memory.get_session_history(
    limit=5,
    spec_only=False  # False = include project-wide history
)

# Patterns and gotchas (cross-session learning!)
patterns, gotchas = await memory.get_patterns_and_gotchas(
    query="Implement user authentication",
    num_results=3,
    min_score=0.5
)

# Preference profile
profile = await memory.get_preference_profile()
```

### Status and Diagnostics

```python
# Get status summary
status = memory.get_status_summary()

print(f"Enabled: {status['enabled']}")
print(f"Initialized: {status['initialized']}")
print(f"Database: {status['database']}")
print(f"LLM Provider: {status['llm_provider']}")
print(f"Embedder Provider: {status['embedder_provider']}")
print(f"Episode Count: {status['episode_count']}")
print(f"Last Session: {status['last_session']}")
print(f"Errors: {status['errors']}")

# Get provider summary
provider_summary = memory.config.get_provider_summary()
print(f"Providers: {provider_summary}")  # "LLM: anthropic, Embedder: voyage"

# Get embedding dimension
dim = memory.config.get_embedding_dimension()
print(f"Embedding Dimension: {dim}")  # 1024 for voyage-3

# Get provider-specific database name
db_name = memory.config.get_provider_specific_database_name()
print(f"Database: {db_name}")  # "auto_claude_memory_voyage_1024"
```

## Usage Examples

### Example 1: Cross-Session Pattern Learning

**Session 1 (Spec 001):**

```python
# Agent discovers a pattern
await memory.save_pattern({
    "pattern": "Use React hooks for component state",
    "applies_to": "frontend",
    "category": "react",
    "reasoning": "Avoids class component complexity"
})
```

**Session 2 (Spec 002 - Same Project):**

```python
# Agent retrieves the pattern from previous spec
patterns, gotchas = await memory.get_patterns_and_gotchas(
    query="Implement frontend component state",
    num_results=3
)

# Result: Pattern from Spec 001 is returned!
for pattern in patterns:
    print(f"Pattern: {pattern['pattern']}")
    print(f"Applies to: {pattern['applies_to']}")
    # Output:
    # Pattern: Use React hooks for component state
    # Applies to: frontend
```

### Example 2: Gotcha Avoidance

**Session 1 (Learn the hard way):**

```python
# Agent encounters a bug
await memory.save_gotcha({
    "gotcha": "JWT tokens expire after 1 hour, causing logout",
    "solution": "Implement refresh token rotation before expiry",
    "applies_to": "authentication",
    "context": "Users reported sudden logouts"
})
```

**Session 2 (Avoid the bug):**

```python
# Agent retrieves gotchas before implementing auth
context = await memory.get_relevant_context(
    query="Implement JWT authentication",
    num_results=5
)

# Result: Gotcha from Session 1 is included!
# Agent now knows to implement refresh tokens upfront
```

### Example 3: User Feedback Learning

```python
from agents.memory_manager import save_feedback

# User rejects agent output
await save_feedback(
    spec_dir=spec_dir,
    project_dir=project_dir,
    feedback_type="rejected",
    task_description="Add user login form",
    agent_type="coder",
    context={
        "reason": "Used class components instead of functional components",
        "preferred_approach": "Use functional components with hooks"
    }
)

# Future sessions now prefer functional components for this project
```

### Example 4: File-Based Fallback

```python
# Graphiti disabled or unavailable
# Memory manager automatically falls back to file-based storage

from agents.memory_manager import save_session_memory

success, storage_type = await save_session_memory(
    spec_dir=spec_dir,
    project_dir=project_dir,
    subtask_id="subtask-1",
    session_num=1,
    success=True,
    subtasks_completed=["subtask-1"],
    discoveries={"files_understood": {}}
)

print(f"Storage type: {storage_type}")  # "file" (fallback)
print(f"Saved: {success}")

# Files stored in: .auto-claude/specs/001-feature/memory/session_001.json
```

## State Management

The memory system tracks initialization state and provider configuration to prevent embedding dimension mismatches.

### GraphitiState

**Location:** `apps/backend/integrations/graphiti/config.py`

**Stored in:** `.auto-claude/specs/XXX-feature/.graphiti_state.json`

**Fields:**

```python
@dataclass
class GraphitiState:
    """State of Graphiti integration for a spec."""

    initialized: bool = False
    database: str | None = None
    indices_built: bool = False
    created_at: str | None = None
    last_session: int | None = None
    episode_count: int = 0
    error_log: list = field(default_factory=list)

    # V2 additions
    llm_provider: str | None = None
    embedder_provider: str | None = None
```

**State File Example:**

```json
{
  "initialized": true,
  "database": "auto_claude_memory_voyage_1024",
  "indices_built": true,
  "created_at": "2025-01-15T10:30:00Z",
  "last_session": 5,
  "episode_count": 23,
  "error_log": [],
  "llm_provider": "anthropic",
  "embedder_provider": "voyage"
}
```

### Provider Change Detection

The memory system detects when the embedding provider changes and prevents database corruption:

```python
# State tracks previous provider
state = GraphitiState.load(spec_dir)

# Check if provider changed
if state.has_provider_changed(config):
    migration_info = state.get_migration_info(config)

    print("⚠️  Embedding provider changed!")
    print(f"Old: {migration_info['old_provider']}")
    print(f"New: {migration_info['new_provider']}")
    print(f"Episodes in old database: {migration_info['episode_count']}")
    print("Run migration or start fresh")
```

## Migration

### Provider-Specific Database Names

To prevent embedding dimension mismatches, each provider configuration gets its own database:

```python
# OpenAI (1536 dimensions)
database: "auto_claude_memory_openai_1536"

# Voyage AI (1024 dimensions)
database: "auto_claude_memory_voyage_1024"

# Ollama nomic-embed-text (768 dimensions)
database: "auto_claude_memory_ollama_nomic-embed-text_768"
```

### Migration Script

**Location:** `apps/backend/integrations/graphiti/migrate_embeddings.py`

**Purpose:** Migrate episodes when changing embedding providers

**Usage:**

```bash
# Migrate from OpenAI to Voyage AI
python integrations/graphiti/migrate_embeddings.py \
  --spec-dir .auto-claude/specs/001-feature \
  --old-provider openai \
  --new-provider voyage
```

**Process:**
1. Connect to old database (e.g., `auto_claude_memory_openai_1536`)
2. Read all episodes with content
3. Re-embed using new provider (e.g., voyage-1024)
4. Store in new database (e.g., `auto_claude_memory_voyage_1024`)
5. Update state file to point to new database

### Manual Migration

If automatic migration fails, you can start fresh:

```bash
# Remove state file (keeps old database intact)
rm .auto-claude/specs/001-feature/.graphiti_state.json

# Next run creates new database with new provider
python run.py --spec 001-feature
```

**Warning:** Old database remains on disk but won't be used. Delete manually to reclaim space:

```bash
# Remove old database
rm ~/.auto-claude/memories/auto_claude_memory_openai_1536
```

## Advanced Features

### Structured Insights

Rich insights extraction from sessions for granular knowledge storage:

```python
# Extract structured insights from session
insights = {
    "file_insights": {
        "auth.py": {
            "purpose": "JWT authentication handler",
            "patterns": ["Decorator-based route protection"],
            "gotchas": ["Token expiry needs refresh logic"]
        }
    },
    "cross_file_patterns": [
        {
            "pattern": "Use dependency injection for services",
            "evidence": ["auth.py", "database.py", "cache.py"],
            "category": "architecture"
        }
    ],
    "session_outcomes": [
        {
            "type": "success",
            "task": "Implement login",
            "lesson": "JWT works well with refresh tokens"
        }
    ]
}

# Save as multiple focused episodes
await memory.save_structured_insights(insights)
```

### Pattern Categorization

Patterns are categorized for better retrieval:

```python
from integrations.graphiti.pattern_categorizer import categorize_patterns

# Auto-categorize patterns
patterns = [
    {"pattern": "Use React hooks", "applies_to": "frontend"},
    {"pattern": "Decorator pattern for auth", "applies_to": "backend"}
]

categorized = categorize_patterns(patterns)

# Result:
# [
#     {"pattern": "Use React hooks", "category": "frontend", "subcategory": "react"},
#     {"pattern": "Decorator pattern", "category": "backend", "subcategory": "security"}
# ]
```

**Categories:**
- `frontend` - UI components, React, state management
- `backend` - API routes, services, business logic
- `database` - Queries, migrations, connection handling
- `security` - Authentication, authorization, encryption
- `testing` - Test patterns, fixtures, mocking
- `architecture` - Design patterns, structure, organization

### Pattern Suggestions

Proactively suggest patterns based on task description:

```python
from agents.memory_manager import get_pattern_suggestions

# Get pattern suggestions before starting task
suggestions = await get_pattern_suggestions(
    spec_dir=spec_dir,
    project_dir=project_dir,
    query="Implement JWT authentication for user login",
    categories=["security", "backend"],
    num_results=5,
    min_score=0.6
)

if suggestions:
    print(suggestions)
    # Output:
    # ## Pattern Suggestions
    #
    # ### Security
    # - **Pattern**: Use @login_required decorator
    #   _Applies to_: authentication
    #   _Confidence_: 0.85 | _Relevance_: 0.92
    #
    # ### Backend
    # - **Pattern**: Validate JWT signature on every request
    #   _Applies to_: authentication
    #   _Confidence_: 0.78 | _Relevance_: 0.88
```

### Session Context Storage

Store and retrieve conversation history:

```python
from agents.memory_manager import get_session_context

# Get session context instance
session_ctx = await get_session_context(
    spec_dir=spec_dir,
    project_dir=project_dir
)

if session_ctx:
    # Add message to history
    await session_ctx.add_message(
        role="user",
        content="Implement user authentication"
    )

    await session_ctx.add_message(
        role="assistant",
        content="I'll implement JWT-based authentication"
    )

    # Retrieve recent context
    context = await session_ctx.get_context(window_size=10)
    # Returns last 10 messages for context window
```

## Performance Considerations

### Database Performance

**LadybugDB (Embedded Graph Database):**
- **No network overhead** - In-process database
- **Fast lookups** - Graph traversal optimized for social knowledge graphs
- **Automatic indexing** - Indices built on first initialization

**Indices Built:**

```python
# Automatic indices on first run
await memory.initialize()  # Builds indices if not present

# Indices created:
# - Episode content (full-text search)
# - Entity embeddings (vector similarity)
# - Relationships (graph traversal)
# - Timestamp (temporal queries)
```

### Semantic Search Performance

**Embedding-Based Search:**
- **O(log n)** vector similarity search
- **Returns top-k most relevant** results
- **Filters by episode type** for targeted queries

**Keyword Fallback:**
- **Works without embedder** - If provider not configured
- **Full-text search** - Finds matching terms in content
- **Lower quality** - No semantic understanding

**Recommendation:** Always configure an embedder for best results.

### Memory Usage

**Database Size:**

| Episodes | Approx. Size | Notes |
|-----------|---------------|-------|
| 10 | ~5 MB | Fresh spec |
| 100 | ~50 MB | Active development |
| 1000 | ~500 MB | Long-term project |

**Storage Location:**
```bash
~/.auto-claude/memories/
├── auto_claude_memory_openai_1536/
│   ├── graph.db
│   └── embeddings/
└── auto_claude_memory_voyage_1024/
    ├── graph.db
    └── embeddings/
```

### Optimization Tips

**1. Use Project Mode for Related Specs**

```python
# GOOD: Shared memory across related features
memory = get_graphiti_memory(
    spec_dir=spec_dir,
    project_dir=project_dir,
    group_id_mode="project"  # Cross-spec learning
)
```

**2. Batch Save Operations**

```python
# GOOD: Save multiple insights at once
await memory.save_structured_insights({
    "file_insights": {...},
    "cross_file_patterns": [...],
    "session_outcomes": [...]
})

# AVOID: Multiple separate saves
await memory.save_pattern(pattern1)
await memory.save_pattern(pattern2)
await memory.save_pattern(pattern3)
```

**3. Retrieve Only What You Need**

```python
# GOOD: Targeted retrieval
patterns, gotchas = await memory.get_patterns_and_gotchas(
    query="authentication",
    num_results=3,  # Limit results
    min_score=0.6  # Filter low-quality matches
)

# AVOID: Broad searches that return everything
context = await memory.get_relevant_context(
    query="authentication",
    num_results=100  # Too many results
)
```

**4. Close Connections When Done**

```python
# GOOD: Explicit cleanup
try:
    await memory.initialize()
    # ... use memory
finally:
    await memory.close()  # Release resources
```

## Troubleshooting

### Graphiti Not Connecting

**Symptom:** `is_enabled=False` or initialization fails

**Check:**
```bash
# Verify environment variables
echo $GRAPHITI_ENABLED
echo $GRAPHITI_EMBEDDER_PROVIDER

# Check validation errors
python -c "from graphiti_config import validate_graphiti_config; print(validate_graphiti_config())"
```

**Common Solutions:**
1. Set `GRAPHITI_ENABLED=true`
2. Add API key for your provider (e.g., `OPENAI_API_KEY`)
3. Verify Python 3.12+ is installed (required for LadybugDB)

### Embedding Dimension Mismatch

**Symptom:** Errors about dimension mismatch when changing providers

**Cause:** Old embeddings with different dimensions in database

**Solution:**

```bash
# Option 1: Run migration script
python integrations/graphiti/migrate_embeddings.py \
  --spec-dir .auto-claude/specs/001-feature \
  --old-provider openai \
  --new-provider voyage

# Option 2: Start fresh
rm .auto-claude/specs/001-feature/.graphiti_state.json
```

### Semantic Search Returns No Results

**Symptom:** `get_relevant_context()` returns empty list

**Causes:**
1. Database is empty (first session)
2. Query is too specific
3. Embedder not configured (keyword fallback has limited data)

**Solutions:**
1. Check episode count: `memory.get_status_summary()['episode_count']`
2. Use broader query terms
3. Verify embedder is configured: `memory.config.embedder_provider`

### Ollama Connection Refused

**Symptom:** Provider errors when using Ollama

**Check:**
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# List available models
ollama list
```

**Solution:**
```bash
# Start Ollama
ollama serve

# Pull embedding model
ollama pull nomic-embed-text
```

## See Also

- [Code Relationship Graph](./CODE_RELATIONSHIP_GRAPH.md) - Code structure analysis using Graphiti
- [Graphiti Documentation](https://github.com/getgriti/graphiti) - Upstream Graphiti library
- [LadybugDB Documentation](https://github.com/getgrati/ladybug) - Embedded graph database

---

**Questions or issues?** Open an issue or check existing Graphiti memory episodes for similar problems.
