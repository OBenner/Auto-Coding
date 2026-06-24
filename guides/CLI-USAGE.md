# Auto Code CLI Usage

This document covers terminal-only usage of Auto Code. **For most users, we recommend using the [Desktop UI](#) or the [Web-Based IDE Interface](../docs/features/WEB-IDE-INTERFACE.md) instead** - they provide a better experience with visual task management, progress tracking, and automatic Python environment setup.

## When to Use CLI

- You prefer terminal workflows
- You're running on a headless server
- You're integrating Auto Code into scripts or CI/CD

## Prerequisites

- Python 3.12+
- Git
- At least one configured runtime:
  - Claude Code OAuth for the existing full SDK runtime
  - Codex CLI with a logged-in `CODEX_HOME` profile for the Codex CLI runner
  - API-key providers for compatible limited modes only

### Installing Python

**Windows:**
```bash
winget install Python.Python.3.12
```

**macOS:**
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install python3.12 python3.12-venv
```

**Linux (Fedora):**
```bash
sudo dnf install python3.12
```

## Setup

### Automated Setup (Recommended)

Use the `--setup` command to automatically detect, install, and configure everything:

```bash
cd apps/backend

# Interactive setup — detects packages, installs deps, configures .env, validates providers
python run.py --setup

# Preview what would be done without making changes
python run.py --setup --dry-run

# Non-interactive (for CI/automation)
python run.py --setup --non-interactive --json
```

The setup wizard runs 5 phases: package detection, dependency installation, `.env` configuration, Graphiti validation, and LLM provider connectivity testing. See [Environment Sync docs](../docs/features/ENVIRONMENT-SYNC.md) for details.

### Manual Setup

**Step 1:** Navigate to the backend directory

```bash
cd apps/backend
```

**Step 2:** Set up Python environment

```bash
# Using uv (recommended)
uv venv && uv pip install -r requirements.txt

# Or using standard Python
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

**Step 3:** Configure environment

```bash
cp .env.example .env

# Claude full-runtime path: get your OAuth token
claude setup-token

# Add the token to apps/backend/.env when using the Claude runtime
# CLAUDE_CODE_OAUTH_TOKEN=your-token-here

# Codex CLI runner path: make sure codex is logged in and CODEX_HOME is set
# CODEX_HOME=/path/to/codex-profile
```

Direct provider API keys can be used for compatible runtime modes such as
`analysis_only`, `patch_proposal`, and `generic_edit`. They do not automatically
provide full autonomous tools, MCP, shell, filesystem, or subagent behavior.

## Creating Specs

All commands below should be run from the `apps/backend/` directory:

```bash
# Activate the virtual environment (if not already active)
source .venv/bin/activate

# Create a spec interactively
python runners/spec_runner.py --interactive

# Or with a task description
python runners/spec_runner.py --task "Add user authentication with OAuth"

# Force a specific complexity level
python runners/spec_runner.py --task "Fix button color" --complexity simple

# Continue an interrupted spec
python runners/spec_runner.py --continue 001-feature
```

### Complexity Tiers

The spec runner automatically assesses task complexity:

| Tier | Phases | When Used |
|------|--------|-----------|
| **SIMPLE** | 3 | 1-2 files, single service, no integrations (UI fixes, text changes) |
| **STANDARD** | 6 | 3-10 files, 1-2 services, minimal integrations (features, bug fixes) |
| **COMPLEX** | 8 | 10+ files, multiple services, external integrations |

## Running Builds

```bash
# List all specs and their status
python run.py --list

# Run a specific spec
python run.py --spec 001
python run.py --spec 001-feature-name

# Limit iterations for testing
python run.py --spec 001 --max-iterations 5
```

## QA Validation

After all chunks are complete, QA validation runs automatically:

```bash
# Skip automatic QA
python run.py --spec 001 --skip-qa

# Run QA validation manually
python run.py --spec 001 --qa

# Check QA status
python run.py --spec 001 --qa-status
```

The QA validation loop:
1. **QA Reviewer** checks all acceptance criteria
2. If issues found → creates `QA_FIX_REQUEST.md`
3. **QA Fixer** applies fixes
4. Loop repeats until approved (up to 50 iterations)

## Workspace Management

Auto Code uses Git worktrees for isolated builds:

```bash
# Test the feature in the isolated workspace
cd .worktrees/<spec-name>/
npm run dev  # or your project's run command

# Return to backend directory to run management commands
cd apps/backend

# See what was changed
python run.py --spec 001 --review

# Merge changes into your project
python run.py --spec 001 --merge

# Discard if you don't like it
python run.py --spec 001 --discard
```

## Interactive Controls

While the agent is running:

```bash
# Pause and add instructions
Ctrl+C (once)

# Exit immediately
Ctrl+C (twice)
```

**File-based alternative:**
```bash
# Create PAUSE file to pause after current session
touch specs/001-name/PAUSE

# Add instructions
echo "Focus on fixing the login bug first" > specs/001-name/HUMAN_INPUT.md
```

## Spec Validation

```bash
python validate_spec.py --spec-dir specs/001-feature --checkpoint all
```

## Autonomy: one knob

How independent the agents are is controlled by a single setting — `AUTO_CODE_AUTONOMY`. Set it and you're done; you do not need to touch the low-level runtime/provider/policy variables.

```bash
# In apps/backend/.env (or the environment)
AUTO_CODE_AUTONOMY=claude   # default
```

| Level | What it allows |
|-------|----------------|
| `off` | Analysis and patch suggestions only — agents never write your workspace. |
| `claude` *(default)* | Full autonomy on the Claude SDK / Codex CLI runtimes. Direct-API providers (OpenAI, Google, …) are refused with a clear capability error. |
| `safe` | Adds direct-API providers: they run through `generic_edit` and are promoted to full autonomy once they pass the evidence gate. Mutating parallel subagents enabled (write-scope confined). Still fail-fast on missing capability. |
| `bold` | Power-user mode: direct providers run promoted without waiting for the gate. Use for benchmarking or seeding evidence. |

Optional second knob — how strict the promotion gate is:

```bash
AUTO_CODE_AUTONOMY_PRESET=standard   # strict | standard | lax
```

- `strict` — 10 stable runs / 3-day freshness / all required cases
- `standard` *(default)* — 3 stable runs / 7-day freshness / all required cases
- `lax` — 1 stable run / 30-day freshness / critical cases only

**Privacy / local-model recipe:** `AUTO_CODE_AUTONOMY=safe` together with `AI_ENGINE_PROVIDER=ollama` keeps the whole loop on a local model — your code never leaves the machine.

### Advanced overrides

Every low-level variable still works and **takes precedence** over the level — they are normally not needed. The matrix (`AUTO_CODE_RUNTIME_MODE`, `AGENT_RUNTIME_MODE_<TYPE>`, the per-provider `AUTO_CODE_AUTONOMY_<PROVIDER>_<KNOB>` policy knobs, …) is documented in [ADR-006: Autonomy levels](../docs/architecture/adr/ADR-006-autonomy-levels.md) and [Provider runtime modes](../docs/architecture/provider-runtime-modes.md). The legacy `AUTO_CODE_DIRECT_API_FULL_AUTONOMOUS` is deprecated — use `AUTO_CODE_AUTONOMY=safe` instead.

---

## Environment Variables

Copy `.env.example` to `.env` and configure as needed:

```bash
cp .env.example .env
```

### Core Settings

| Variable | Required | Description |
|----------|----------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Yes | OAuth token from `claude setup-token` |
| `AUTO_BUILD_MODEL` | No | Model override (default: claude-opus-4-5-20251101) |
| `DEFAULT_BRANCH` | No | Base branch for worktrees (auto-detects main/master) |
| `DEBUG` | No | Enable debug logging (default: false) |

### Integrations

| Variable | Required | Description |
|----------|----------|-------------|
| `LINEAR_API_KEY` | No | Linear API key for task sync |
| `GITLAB_TOKEN` | No | GitLab Personal Access Token |
| `GITLAB_INSTANCE_URL` | No | GitLab instance URL (defaults to gitlab.com) |

### Memory Layer (Graphiti)

| Variable | Required | Description |
|----------|----------|-------------|
| `GRAPHITI_ENABLED` | No | Enable Memory Layer (default: true) |
| `GRAPHITI_LLM_PROVIDER` | No | LLM provider: openai, anthropic, ollama, google, openrouter |
| `GRAPHITI_EMBEDDER_PROVIDER` | No | Embedder: openai, voyage, ollama, google, openrouter |

See `.env.example` for complete configuration options including provider-specific settings.

## Web-Based IDE Alternative

Auto Code also provides a web-based IDE interface for browser-based access. This is useful when you want a graphical interface without installing the Electron desktop app.

```bash
# Start the web backend
cd apps/web-backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Start the web frontend (in a separate terminal)
cd apps/web-frontend
npm run dev
```

The web IDE provides file browsing, code editing, agent execution, real-time progress monitoring, and a web terminal. See [Web IDE Interface documentation](../docs/features/WEB-IDE-INTERFACE.md) for details.
