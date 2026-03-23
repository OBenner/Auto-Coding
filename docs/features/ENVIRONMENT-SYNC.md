# Environment Sync (One-Command Setup)

Automatically detect, install, configure, and validate your entire development environment with a single command.

## Overview

The `--setup` command orchestrates a complete environment synchronization pipeline:

1. **Package Detection** - Scans your project for package managers (npm, pip, cargo, go)
2. **Dependency Installation** - Installs all detected dependencies
3. **Environment Configuration** - Creates/updates `.env` from `.env.example` with interactive prompting
4. **Graphiti Validation** - Validates memory system configuration (LLM + embedder providers)
5. **Provider Testing** - Tests connectivity to configured LLM/embedder providers
6. **Report Generation** - Produces a summary with actionable fix recommendations

## Quick Start

```bash
cd apps/backend

# Interactive setup (recommended for first run)
python run.py --setup

# Non-interactive setup (for CI/automation)
python run.py --setup --non-interactive

# Dry-run to preview changes without executing
python run.py --setup --dry-run

# JSON output for scripting
python run.py --setup --json
```

## CLI Flags

| Flag | Description |
|------|-------------|
| `--setup` | Run the environment sync pipeline |
| `--dry-run` | Preview what would be done without making changes |
| `--skip-install` | Skip dependency installation phase |
| `--skip-config` | Skip `.env` configuration phase |
| `--skip-validation` | Skip Graphiti and provider validation |
| `--non-interactive` | Don't prompt for input (use defaults/env vars) |
| `--verbose` | Show detailed progress for each phase |
| `--json` | Output results as JSON (for automation) |

## Pipeline Phases

### Phase 1: Package Detection

Scans the project directory tree for package manager indicators:

- `package.json` / `package-lock.json` / `yarn.lock` / `pnpm-lock.yaml` -> **npm/yarn/pnpm**
- `requirements.txt` / `setup.py` / `pyproject.toml` -> **pip**
- `Cargo.toml` -> **cargo**
- `go.mod` -> **go**

Automatically skips ignored directories (`node_modules`, `.git`, `.venv`, `target`, `vendor`, `dist`, `build`).

### Phase 2: Dependency Installation

Runs the appropriate install command for each detected package manager:

| Package Manager | Command |
|----------------|---------|
| npm | `npm install` |
| yarn | `yarn install` |
| pnpm | `pnpm install` |
| pip (requirements.txt) | `pip install -r requirements.txt` |
| pip (setup.py) | `pip install -e .` |
| pip (pyproject.toml) | `pip install -e .` |
| cargo | `cargo build` |
| go | `go mod download` |

### Phase 3: Environment Configuration

Parses `.env.example` to identify required and optional environment variables:

- **Required variables** - Must be configured (e.g., `ANTHROPIC_API_KEY`)
- **Optional variables** - Commented out in `.env.example` with `# VAR=default`
- **Existing values** - Preserved from current `.env` file

In interactive mode, prompts for each missing required variable. In non-interactive mode, reports missing variables as warnings.

**Security**: Dry-run mode masks sensitive values (API keys, tokens, secrets) in output.

### Phase 4: Graphiti Validation

Validates the Graphiti memory system configuration:

- LLM provider configuration (API key, model, base URL)
- Embedder provider configuration
- Database backend availability (embedded LadybugDB)

Supports providers: OpenAI, Anthropic, Azure OpenAI, Ollama, Google AI, OpenRouter.

### Phase 5: Provider Connectivity

Tests actual connections to configured providers:

- LLM provider - sends a minimal test request
- Embedder provider - tests embedding generation
- Reports latency and error details for failed connections

### Phase 6: Report Generation

Generates a markdown-formatted report with:

- Overall status (pass/fail)
- Per-phase results with timing
- List of issues found
- Actionable fix recommendations

## Output Format

### Human-Readable (default)

```
╔══════════════════════════════════════╗
║     Auto Code Environment Sync      ║
╚══════════════════════════════════════╝

Phase 1: Package Detection... ✓ (0.2s)
  Found: npm (1 dir), pip (2 dirs)

Phase 2: Dependency Installation... ✓ (15.3s)
  ✓ npm install (apps/frontend)
  ✓ pip install -r requirements.txt (apps/backend)

Phase 3: Environment Config... ✓ (1.1s)
  ✓ .env file updated (3 new values)

Phase 4: Graphiti Validation... ✓ (0.5s)
  LLM Provider: openai ✓
  Embedder: openai ✓

Phase 5: Provider Testing... ✓ (2.1s)
  ✓ OpenAI LLM connected (234ms)
  ✓ OpenAI Embedder connected (156ms)

═══════════════════════════════════════
✓ Environment ready (19.2s)
```

### JSON (with `--json`)

```json
{
  "success": true,
  "duration": "19.2s",
  "detection": {
    "npm": ["apps/frontend"],
    "pip": ["apps/backend", "apps/web-backend"]
  },
  "installation": {
    "dry_run": false,
    "installed": ["npm", "pip"],
    "failed": [],
    "skipped": []
  },
  "configuration": {
    "success": true,
    "env_file": "apps/backend/.env",
    "variables_set": 3
  },
  "graphiti": {
    "llm_valid": true,
    "embedder_valid": true,
    "database_valid": true
  },
  "providers": {
    "llm": {"connected": true, "latency_ms": 234},
    "embedder": {"connected": true, "latency_ms": 156}
  },
  "issues": [],
  "report": "..."
}
```

## Architecture

### Module Structure

```
apps/backend/
├── cli/
│   └── setup_commands.py      # CLI handler and display logic
├── core/
│   ├── env_sync.py            # Orchestrator (main pipeline)
│   ├── package_detector.py    # Phase 1: Package detection
│   ├── dependency_installer.py # Phase 2: Dependency installation
│   ├── env_configurator.py    # Phase 3: .env configuration
│   ├── graphiti_validator.py  # Phase 4: Graphiti validation
│   └── provider_tester.py     # Phase 5: Provider connectivity
```

### Key Design Decisions

- **Phased pipeline** - Each phase is independent and can be skipped
- **Dry-run support** - Preview all changes without side effects
- **Secret masking** - API keys and tokens are never printed in dry-run output
- **Pruned directory walking** - Uses `os.walk()` with directory pruning instead of `rglob()` for performance in large repos
- **Graceful degradation** - Failures in optional phases (Graphiti, providers) don't fail the overall setup

## Testing

```bash
# Run all env-sync tests
apps/backend/.venv/bin/pytest tests/test_env_sync.py tests/test_package_detector.py tests/test_dependency_installer.py tests/test_env_configurator.py tests/test_graphiti_validator.py tests/test_provider_tester.py -v
```

Test coverage includes:
- Unit tests for each phase module
- Integration test for the full pipeline
- Dry-run behavior verification
- Error handling and edge cases
- Provider-specific connectivity tests
