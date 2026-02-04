# Backend API Reference

Complete reference for Auto Claude's Python backend CLI commands and programmatic API.

## Commands

### `run.py` - Build Execution and Management

Main entry point for running autonomous builds and managing workspaces.

**Location:** `apps/backend/run.py`

#### Basic Usage

```bash
cd apps/backend

# List all specs
python run.py --list

# Run a build
python run.py --spec 001
python run.py --spec 001-feature-name
```

#### Build Options

| Option | Description |
|--------|-------------|
| `--spec SPEC` | Spec to run (number or full name, e.g., '001' or '001-feature-name') |
| `--max-iterations N` | Maximum number of agent sessions (default: unlimited) |
| `--model MODEL` | Claude model to use (default: claude-sonnet-4-5-20250929) |
| `--verbose` | Enable verbose output |
| `--force` | Skip approval check and start build (debugging only) |
| `--auto-continue` | Non-interactive mode for UI integration |
| `--skip-qa` | Skip automatic QA validation after build completes |

#### Workspace Options

| Option | Description |
|--------|-------------|
| `--isolated` | Force building in isolated workspace (safer, default) |
| `--direct` | Build directly in project (no isolation, not recommended) |
| `--base-branch BRANCH` | Base branch for worktree creation (default: auto-detect) |

#### Workspace Management

```bash
# Review what was built
python run.py --spec 001 --review

# Merge completed build into project
python run.py --spec 001 --merge

# Merge options
python run.py --spec 001 --merge --no-commit    # Stage only, don't commit
python run.py --spec 001 --merge-preview        # Preview conflicts (JSON output)

# Discard build (with confirmation)
python run.py --spec 001 --discard

# Create GitHub Pull Request
python run.py --spec 001 --create-pr
python run.py --spec 001 --create-pr --pr-target develop
python run.py --spec 001 --create-pr --pr-title "Custom Title"
python run.py --spec 001 --create-pr --pr-draft
```

#### QA Commands

```bash
# Run QA validation loop
python run.py --spec 001 --qa

# Check QA status
python run.py --spec 001 --qa-status

# Check review status
python run.py --spec 001 --review-status
```

#### Follow-up Tasks

```bash
# Add follow-up tasks to completed spec
python run.py --spec 001 --followup
```

#### Worktree Management

```bash
# List all spec worktrees
python run.py --list-worktrees

# Clean up all worktrees (with confirmation)
python run.py --cleanup-worktrees
```

#### Batch Operations

```bash
# Create multiple tasks from JSON file
python run.py --batch-create tasks.json

# Show status of all specs
python run.py --batch-status

# Clean up completed specs
python run.py --batch-cleanup                    # Dry-run (preview)
python run.py --batch-cleanup --no-dry-run       # Actually delete
```

**Batch JSON Format:**
```json
{
  "tasks": [
    {
      "title": "Task description",
      "complexity": "simple"
    }
  ]
}
```

---

### `spec_runner.py` - Spec Creation

Dynamic spec creation with AI-powered complexity assessment.

**Location:** `apps/backend/runners/spec_runner.py`

#### Basic Usage

```bash
cd apps/backend

# Interactive mode
python runners/spec_runner.py --interactive

# From task description
python runners/spec_runner.py --task "Add user authentication"

# Force complexity level
python runners/spec_runner.py --task "Fix button" --complexity simple

# Continue existing spec
python runners/spec_runner.py --continue 001-feature
```

#### Options

| Option | Description |
|--------|-------------|
| `--task TEXT` | Task description (what to build) |
| `--task-file FILE` | Read task from file (for long descriptions) |
| `--interactive` | Interactive mode with prompts |
| `--continue SPEC` | Continue existing spec from last checkpoint |
| `--complexity LEVEL` | Force complexity: simple, standard, complex |
| `--no-ai-assessment` | Skip AI complexity analysis, use heuristics |
| `--model MODEL` | Claude model for spec creation |
| `--max-thinking-tokens N` | Extended thinking budget (5000/10000/16000) |

#### Complexity Tiers

**SIMPLE (3 phases):**
- 1-2 files to modify
- No external integrations
- Pipeline: Discovery → Quick Spec → Validate

**STANDARD (6 phases):**
- 3-10 files to modify
- May have external dependencies
- Pipeline: Discovery → Requirements → Context → Spec → Plan → Validate

**STANDARD + Research (7 phases):**
- Same as Standard but with research phase for external integrations
- Pipeline: Discovery → Requirements → Research → Context → Spec → Plan → Validate

**COMPLEX (8 phases):**
- 10+ files or major architectural changes
- Multiple services/integrations
- Pipeline: Discovery → Requirements → Research → Context → Spec → Plan → Self-Critique → Validate

**AI Assessment Factors:**
- Number of files/services involved
- External integrations requiring research
- Infrastructure changes (Docker, databases, etc.)
- Existing codebase patterns to follow
- Risk factors and edge cases

#### Examples

```bash
# Simple UI fix (auto-detected)
python runners/spec_runner.py --task "Fix button color in Header component"

# Complex integration (auto-detected)
python runners/spec_runner.py --task "Add Graphiti memory with FalkorDB"

# Force simple mode
python runners/spec_runner.py --task "Update text" --complexity simple

# Use heuristics instead of AI assessment
python runners/spec_runner.py --task "Simple fix" --no-ai-assessment

# Interactive with full context
python runners/spec_runner.py --interactive
```

---

### `validate_spec.py` - Spec Validation

Validates spec files against checkpoints.

```bash
# Validate all checkpoints
python apps/backend/validate_spec.py --spec-dir apps/backend/specs/001-feature --checkpoint all

# Validate specific checkpoint
python apps/backend/validate_spec.py --spec-dir apps/backend/specs/001-feature --checkpoint requirements
```

---

## Core Modules

### `core.client` - Claude SDK Client Factory

**CRITICAL:** All AI interactions use the Claude Agent SDK, NOT the Anthropic API directly.

#### `create_client()`

Creates a configured `ClaudeSDKClient` instance with security and tool permissions.

**Signature:**
```python
def create_client(
    project_dir: Path,
    spec_dir: Path,
    model: str = "claude-sonnet-4-5-20250929",
    agent_type: str = "coder",
    max_thinking_tokens: int | None = None,
) -> ClaudeSDKClient:
    """
    Create Claude SDK client with security and MCP integration.

    Args:
        project_dir: Root project directory
        spec_dir: Spec-specific directory
        model: Claude model identifier
        agent_type: Agent role (planner, coder, qa_reviewer, qa_fixer)
        max_thinking_tokens: Extended thinking budget (5000/10000/16000)

    Returns:
        Configured ClaudeSDKClient instance
    """
```

**Usage:**
```python
from core.client import create_client

# Create client for coder agent
client = create_client(
    project_dir=Path("/path/to/project"),
    spec_dir=Path("/path/to/spec"),
    model="claude-sonnet-4-5-20250929",
    agent_type="coder",
    max_thinking_tokens=None
)

# Run agent session
response = client.create_agent_session(
    name="coder-agent-session",
    starting_message="Implement the authentication feature"
)
```

**Agent Types:**
- `planner` - Creates implementation plans with subtasks
- `coder` - Implements individual subtasks
- `qa_reviewer` - Validates acceptance criteria
- `qa_fixer` - Fixes QA-reported issues

**Key Features:**
- Project index caching (5-minute TTL)
- Agent-specific tool permissions
- Dynamic MCP server integration
- Extended thinking token control
- Multi-layered security

---

### `core.auth` - Authentication Management

OAuth token resolution and authentication handling.

#### Functions

**`get_auth_token()`**
```python
def get_auth_token() -> str:
    """
    Get authentication token from Claude Code CLI.

    Returns OAuth token from:
    1. CLAUDE_CODE_OAUTH_TOKEN env var
    2. ANTHROPIC_AUTH_TOKEN env var (CCR/proxy)
    3. Platform-specific secret storage (Keychain, Credential Manager, secret-service)

    Raises:
        RuntimeError: If no token found
    """
```

**Environment Variables (Priority Order):**
1. `CLAUDE_CODE_OAUTH_TOKEN` - OAuth token from Claude Code CLI
2. `ANTHROPIC_AUTH_TOKEN` - CCR/proxy token (enterprise)

**Passthrough Variables (for SDK subprocess):**
- `ANTHROPIC_BASE_URL` - Custom API endpoint
- `ANTHROPIC_AUTH_TOKEN` - Auth token
- `ANTHROPIC_MODEL` - Model override

---

### `core.workspace` - Workspace Management

Git worktree isolation for safe feature development.

#### Functions

**`create_worktree()`**
```python
def create_worktree(
    project_dir: Path,
    spec_name: str,
    base_branch: str | None = None
) -> Path:
    """
    Create isolated worktree for spec.

    Args:
        project_dir: Root project directory
        spec_name: Spec identifier (e.g., '001-feature')
        base_branch: Base branch (default: auto-detect)

    Returns:
        Path to created worktree
    """
```

**`merge_worktree()`**
```python
def merge_worktree(
    project_dir: Path,
    spec_name: str,
    commit: bool = True
) -> None:
    """
    Merge spec branch into main branch.

    Args:
        project_dir: Root project directory
        spec_name: Spec identifier
        commit: If False, only stage changes (no commit)
    """
```

**`discard_worktree()`**
```python
def discard_worktree(
    project_dir: Path,
    spec_name: str
) -> None:
    """
    Delete worktree and branch.

    Args:
        project_dir: Root project directory
        spec_name: Spec identifier
    """
```

**Key Features:**
- Worktree creation and management
- Spec branch isolation (`auto-claude/{spec-name}`)
- Workspace state tracking
- Merge operations (spec branch → main)
- Cleanup and discard operations

---

### `core.security` - Security Model

Dynamic command allowlisting based on project stack detection.

#### Functions

**`validate_bash_command()`**
```python
def validate_bash_command(command: str, project_dir: Path) -> bool:
    """
    Validate if bash command is allowed.

    Args:
        command: Bash command to validate
        project_dir: Project directory for stack detection

    Returns:
        True if command is allowed, False otherwise
    """
```

**Security Layers:**
1. **OS Sandbox** - Bash command isolation
2. **Filesystem Permissions** - Restricted to project directory
3. **Command Allowlist** - Dynamic from project analysis

**Security Profile:**
- Cached in `.auto-claude-security.json`
- Generated from project stack detection
- Includes allowed commands based on detected technologies

---

### `agents` - Agent Implementations

#### Available Agents

| Agent | Module | Purpose |
|-------|--------|---------|
| Planner | `agents.planner` | Creates subtask-based implementation plans |
| Coder | `agents.coder` | Implements individual subtasks |
| QA Reviewer | `agents.qa_reviewer` | Validates acceptance criteria |
| QA Fixer | `agents.qa_fixer` | Fixes QA-reported issues |

#### Base Agent

**`agents.base.Agent`**
```python
class Agent:
    """Base class for all agents."""

    def __init__(
        self,
        client: ClaudeSDKClient,
        project_dir: Path,
        spec_dir: Path
    ):
        """Initialize agent with SDK client."""

    def run(self, starting_message: str) -> dict:
        """
        Run agent session.

        Args:
            starting_message: Initial prompt for agent

        Returns:
            Agent response dictionary
        """
```

#### Memory Manager

**`agents.memory_manager.MemoryManager`**
```python
class MemoryManager:
    """Manages session memory and context."""

    def get_context_for_session(self, task: str) -> str:
        """Get relevant context from Graphiti memory."""

    def add_session_insight(self, insight: str) -> None:
        """Add insight to memory graph."""

    def record_discovery(
        self,
        file_path: str,
        description: str,
        category: str
    ) -> None:
        """Record codebase discovery."""

    def record_gotcha(self, gotcha: str, context: str) -> None:
        """Record pitfall to avoid."""
```

---

### `integrations.graphiti` - Memory System

Graph-based memory with semantic search.

#### GraphitiMemory

**`integrations.graphiti.memory.GraphitiMemory`**
```python
class GraphitiMemory:
    """Graphiti memory integration."""

    def __init__(self, spec_dir: Path, project_dir: Path):
        """Initialize with embedded LadybugDB."""

    def get_context_for_session(self, query: str) -> str:
        """Get relevant context via semantic search."""

    def add_episode(
        self,
        name: str,
        content: str,
        episode_type: str
    ) -> None:
        """Add episode to memory graph."""

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Semantic search across memory."""
```

**Factory Function:**
```python
def get_graphiti_memory(
    spec_dir: Path,
    project_dir: Path
) -> GraphitiMemory:
    """Get or create Graphiti memory instance."""
```

**Configuration:**
- Requires `GRAPHITI_ENABLED=true`
- Supports multiple LLM providers (OpenAI, Anthropic, Azure, Ollama, Google AI)
- Embedded LadybugDB (no Docker required)
- Memory stored in `.auto-claude/specs/XXX/graphiti/`

**Environment Variables:**
```bash
GRAPHITI_ENABLED=true
ANTHROPIC_API_KEY=sk-ant-...
# Or other provider keys
```

---

### `context` - Project Analysis

Stack detection and project understanding.

#### ProjectAnalyzer

**`context.project_analyzer.ProjectAnalyzer`**
```python
class ProjectAnalyzer:
    """Analyzes project structure and stack."""

    def __init__(self, project_dir: Path):
        """Initialize analyzer."""

    def analyze(self) -> dict:
        """
        Analyze project stack.

        Returns:
            Dictionary with detected technologies:
            - languages: List of programming languages
            - frameworks: List of frameworks
            - tools: List of development tools
            - capabilities: Project capabilities
        """

    def get_allowed_commands(self) -> list[str]:
        """Get allowed bash commands for project."""
```

**Detected Capabilities:**
- `is_python` - Python project
- `is_node` - Node.js project
- `is_electron` - Electron application
- `is_react` - React application
- `is_typescript` - TypeScript project
- `has_docker` - Docker support
- `has_git` - Git repository

---

### `cli` - Command-Line Interface

Modular CLI structure.

#### Modules

| Module | Purpose |
|--------|---------|
| `cli.main` | Argument parsing and command routing |
| `cli.spec_commands` | Spec listing and management |
| `cli.build_commands` | Build execution and follow-up tasks |
| `cli.workspace_commands` | Workspace management (merge, review, discard) |
| `cli.qa_commands` | QA validation commands |
| `cli.batch_commands` | Batch task operations |
| `cli.utils` | Shared utilities and configuration |

---

### `spec` - Spec Management

Spec creation and validation.

#### SpecOrchestrator

**`spec.orchestrator.SpecOrchestrator`**
```python
class SpecOrchestrator:
    """Orchestrates spec creation pipeline."""

    def __init__(
        self,
        project_dir: Path,
        task: str,
        complexity: str | None = None
    ):
        """Initialize orchestrator."""

    async def run(self) -> Path:
        """
        Run spec creation pipeline.

        Returns:
            Path to created spec directory
        """
```

**Spec Directory Structure:**
```
.auto-claude/specs/XXX-name/
├── spec.md                      # Feature specification
├── requirements.json            # Structured requirements
├── context.json                 # Codebase context
├── implementation_plan.json     # Subtask plan
├── qa_report.md                 # QA results
└── QA_FIX_REQUEST.md           # Issues to fix
```

---

### `prompts` - Agent Prompts

System prompts for each agent.

| Prompt | Agent | Purpose |
|--------|-------|---------|
| `planner.md` | Planner | Creates implementation plans |
| `coder.md` | Coder | Implements subtasks |
| `coder_recovery.md` | Coder | Recovers from failures |
| `qa_reviewer.md` | QA Reviewer | Validates acceptance criteria |
| `qa_fixer.md` | QA Fixer | Fixes QA issues |
| `spec_gatherer.md` | Spec Gatherer | Collects requirements |
| `spec_researcher.md` | Spec Researcher | Validates integrations |
| `spec_writer.md` | Spec Writer | Creates spec.md |
| `spec_critic.md` | Spec Critic | Self-critique using ultrathink |
| `complexity_assessor.md` | Assessor | AI complexity assessment |

---

## Python API Usage Examples

### Running a Build Programmatically

```python
from pathlib import Path
from core.client import create_client
from agents.planner import PlannerAgent
from agents.coder import CoderAgent

project_dir = Path("/path/to/project")
spec_dir = Path(".auto-claude/specs/001-feature")

# Create planner agent
planner_client = create_client(
    project_dir=project_dir,
    spec_dir=spec_dir,
    agent_type="planner"
)
planner = PlannerAgent(planner_client, project_dir, spec_dir)

# Create implementation plan
plan_response = planner.run("Create implementation plan")

# Create coder agent
coder_client = create_client(
    project_dir=project_dir,
    spec_dir=spec_dir,
    agent_type="coder"
)
coder = CoderAgent(coder_client, project_dir, spec_dir)

# Implement subtasks
coder_response = coder.run("Implement subtask-1")
```

### Using Memory System

```python
from pathlib import Path
from integrations.graphiti.memory import get_graphiti_memory

project_dir = Path("/path/to/project")
spec_dir = Path(".auto-claude/specs/001-feature")

# Get memory instance
memory = get_graphiti_memory(spec_dir, project_dir)

# Get context for session
context = memory.get_context_for_session(
    "Implementing authentication feature"
)

# Add session insights
memory.add_session_insight(
    "Pattern: Use React hooks for state management"
)

# Record codebase discovery
memory.record_discovery(
    file_path="apps/frontend/src/hooks/useAuth.ts",
    description="Custom hook for authentication state",
    category="pattern"
)

# Record gotcha
memory.record_gotcha(
    gotcha="Platform detection must use abstraction layer",
    context="Direct process.platform checks break cross-platform support"
)
```

### Project Analysis

```python
from pathlib import Path
from context.project_analyzer import ProjectAnalyzer

project_dir = Path("/path/to/project")

# Analyze project
analyzer = ProjectAnalyzer(project_dir)
analysis = analyzer.analyze()

print(f"Languages: {analysis['languages']}")
print(f"Frameworks: {analysis['frameworks']}")
print(f"Capabilities: {analysis['capabilities']}")

# Get allowed commands
allowed_commands = analyzer.get_allowed_commands()
print(f"Allowed commands: {allowed_commands}")
```

### Workspace Management

```python
from pathlib import Path
from core.workspace import (
    create_worktree,
    merge_worktree,
    discard_worktree
)

project_dir = Path("/path/to/project")
spec_name = "001-feature"

# Create isolated worktree
worktree_path = create_worktree(
    project_dir=project_dir,
    spec_name=spec_name,
    base_branch="main"
)
print(f"Worktree created at: {worktree_path}")

# ... build completes in worktree ...

# Merge into main
merge_worktree(
    project_dir=project_dir,
    spec_name=spec_name,
    commit=True
)

# Or discard if not needed
discard_worktree(
    project_dir=project_dir,
    spec_name=spec_name
)
```

---

## Environment Variables

### Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `CLAUDE_CODE_OAUTH_TOKEN` | OAuth token from Claude Code CLI | `eyJ0eXAi...` |
| `GRAPHITI_ENABLED` | Enable Graphiti memory system | `true` |
| `ANTHROPIC_API_KEY` | API key for Graphiti LLM | `sk-ant-...` |

### Optional

| Variable | Purpose | Default |
|----------|---------|---------|
| `AUTO_BUILD_MODEL` | Override default model | `claude-sonnet-4-5-20250929` |
| `ANTHROPIC_BASE_URL` | Custom API endpoint | `https://api.anthropic.com` |
| `LINEAR_API_KEY` | Linear integration | None |
| `LINEAR_TEAM_ID` | Linear team ID | None |
| `ELECTRON_MCP_ENABLED` | Enable Electron E2E testing | `false` |
| `ELECTRON_DEBUG_PORT` | Electron remote debugging port | `9222` |
| `DEBUG` | Enable debug output | `false` |

---

## Error Handling

### Common Errors

**Authentication Failed:**
```
Error: No authentication token found
```
**Solution:** Run `claude` CLI and type `/login` to authenticate.

**Graphiti Not Enabled:**
```
Error: Graphiti memory system not enabled
```
**Solution:** Set `GRAPHITI_ENABLED=true` in `apps/backend/.env`.

**Python Version Mismatch:**
```
Error: Auto Claude requires Python 3.10 or higher
```
**Solution:** Upgrade to Python 3.12+ (required for Graphiti).

**Platform Dependency Missing:**
```
Error: pywin32>=306 required on Windows
```
**Solution:** Install platform-specific dependencies:
```bash
# Windows
pip install pywin32>=306

# All platforms
uv pip install -r requirements.txt
```

---

## Security Considerations

### Command Validation

All bash commands are validated against a dynamic allowlist:

```python
from core.security import validate_bash_command

is_allowed = validate_bash_command(
    command="git status",
    project_dir=Path("/path/to/project")
)
```

### Filesystem Restrictions

All file operations are restricted to the project directory:
- Read operations: Project directory only
- Write operations: Project directory only
- Git operations: Repository-scoped only

### SDK Security

The Claude Agent SDK provides:
- OS-level sandboxing
- Tool permission controls
- Security hooks for command validation
- MCP server isolation

---

## Performance Notes

### Caching

- **Project Index:** 5-minute TTL cache for project analysis
- **Security Profile:** Cached in `.auto-claude-security.json`
- **Graphiti Memory:** Embedded database with persistent storage

### Parallel Execution

```bash
# Run multiple specs in parallel (use with caution)
python run.py --spec 001 &
python run.py --spec 002 &
wait
```

### Resource Usage

- **Memory:** ~500MB per agent session
- **Disk:** ~10MB per spec (includes memory data)
- **Network:** API calls to Claude SDK (rate-limited)

---

## Testing

### Unit Tests

```bash
cd apps/backend
../.venv/bin/pytest tests/ -v
```

### Integration Tests

```bash
# Test security validation
../.venv/bin/pytest tests/test_security.py -v

# Test workspace management
../.venv/bin/pytest tests/test_workspace.py -v
```

### E2E Tests

```bash
# Test full build pipeline
python run.py --spec test-001 --direct
```

---

## Troubleshooting

### Debug Mode

Enable debug output for troubleshooting:

```bash
DEBUG=true python run.py --spec 001 --verbose
```

### Common Issues

**Build Stuck:**
- Check `build-progress.txt` in spec directory
- Review agent logs in spec directory
- Use `--max-iterations` to limit sessions

**Worktree Conflicts:**
- Review conflicts: `python run.py --spec 001 --merge-preview`
- Resolve manually in worktree
- Re-run merge

**Memory Issues:**
- Check Graphiti configuration in `apps/backend/.env`
- Verify LadybugDB initialization
- Clear memory: Delete `graphiti/` directory in spec

---

## See Also

- [Backend Architecture](../modules/backend-architecture.md) - Detailed module documentation
- [Memory System Diagram](../diagrams/memory-system.mermaid) - Graphiti architecture
- [Agent Pipeline Diagram](../diagrams/agent-pipeline.mermaid) - Build workflow
- [Security Model Diagram](../diagrams/security-model.mermaid) - Security architecture
- [Web Backend API](./web-backend-api.md) - FastAPI endpoints reference

---

**Version:** 2.8.0
**Last Updated:** 2026-02-04
**Maintained By:** Auto Claude Team
