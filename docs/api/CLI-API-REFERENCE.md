# CLI API Reference

Complete reference for Auto Code's command-line interface (CLI) commands.

## Overview

Auto Code's CLI provides two main entry points:
- **`run.py`** - Build execution and workspace management
- **`spec_runner.py`** - Spec creation and management

All commands are run from the `apps/backend/` directory.

---

## `run.py` - Build Execution and Management

Main entry point for running autonomous builds and managing workspaces.

**Location:** `apps/backend/run.py`

### Basic Usage

```bash
cd apps/backend

# List all available specs
python run.py --list

# Run a build (by spec number or full name)
python run.py --spec 001
python run.py --spec 001-feature-name
```

### Build Options

| Option | Description |
|--------|-------------|
| `--spec SPEC` | Spec to run (number or full name, e.g., '001' or '001-feature-name') |
| `--max-iterations N` | Maximum number of agent sessions (default: unlimited) |
| `--model MODEL` | Claude model to use (default: claude-sonnet-4-5-20250929) |
| `--verbose` | Enable verbose output for debugging |
| `--force` | Skip approval check and start build immediately (debugging only) |
| `--auto-continue` | Non-interactive mode for UI integration |
| `--skip-qa` | Skip automatic QA validation after build completes |

### Workspace Options

| Option | Description |
|--------|-------------|
| `--isolated` | Force building in isolated workspace (safer, default) |
| `--direct` | Build directly in project without isolation (not recommended) |
| `--base-branch BRANCH` | Base branch for worktree creation (default: auto-detect) |

### Workspace Management Commands

#### Review Build

Review what was built in the isolated workspace:

```bash
python run.py --spec 001 --review
```

This opens the worktree directory for inspection.

#### Merge Build

Merge completed build into your project:

```bash
# Basic merge (stages and commits changes)
python run.py --spec 001 --merge

# Stage only, don't commit (for manual review)
python run.py --spec 001 --merge --no-commit

# Preview merge conflicts (JSON output)
python run.py --spec 001 --merge-preview
```

The merge operation:
1. Switches to your main branch
2. Merges the spec branch (`auto-code/{spec-name}`)
3. Creates a commit with changes
4. Cleans up the worktree

#### Discard Build

Discard a build and clean up the worktree:

```bash
python run.py --spec 001 --discard
```

This requires confirmation and will:
- Delete the spec branch
- Remove the worktree
- Clean up temporary files

#### Create GitHub Pull Request

Create a PR for the completed build:

```bash
# Basic PR (targets main branch)
python run.py --spec 001 --create-pr

# Target specific branch (e.g., for contributions)
python run.py --spec 001 --create-pr --pr-target develop

# Custom PR title
python run.py --spec 001 --create-pr --pr-title "Fix: Authentication bug"

# Create as draft PR
python run.py --spec 001 --create-pr --pr-draft
```

### QA Commands

#### Run QA Validation

Run the QA validation loop:

```bash
python run.py --spec 001 --qa
```

This runs the QA reviewer agent which:
- Validates all acceptance criteria
- Tests implemented features
- Can perform E2E testing via Electron MCP (for frontend changes)
- Creates a QA report

#### Check QA Status

Check the current QA status:

```bash
python run.py --spec 001 --qa-status
```

Returns:
- Current QA status (pending, passed, failed)
- Number of issues found
- Test results summary

#### Check Review Status

Check the review/approval status:

```bash
python run.py --spec 001 --review-status
```

### Follow-up Tasks

Add follow-up tasks to a completed spec:

```bash
python run.py --spec 001 --followup
```

This prompts for additional task descriptions and creates new subtasks.

### Worktree Management

#### List All Worktrees

List all spec worktrees:

```bash
python run.py --list-worktrees
```

Shows:
- Worktree paths
- Associated spec names
- Branch names
- Last modified dates

#### Clean Up Worktrees

Clean up all worktrees (with confirmation):

```bash
python run.py --cleanup-worktrees
```

This requires confirmation and will remove all spec worktrees.

### Batch Operations

#### Create Multiple Tasks

Create multiple tasks from a JSON file:

```bash
python run.py --batch-create tasks.json
```

**Batch JSON Format:**
```json
{
  "tasks": [
    {
      "title": "Fix button color in Header",
      "complexity": "simple"
    },
    {
      "title": "Add user authentication",
      "complexity": "standard"
    }
  ]
}
```

#### Batch Status

Show status of all specs:

```bash
python run.py --batch-status
```

Shows:
- All specs and their status
- Progress information
- QA status

#### Batch Cleanup

Clean up completed specs:

```bash
# Dry-run (preview what would be deleted)
python run.py --batch-cleanup

# Actually delete completed specs
python run.py --batch-cleanup --no-dry-run
```

### Scheduler Commands

Schedule builds to run at specific times or manage the scheduler service.

#### Schedule a Build

```bash
# Schedule for specific time (ISO format)
python run.py --schedule 001 --schedule-at "2026-02-12T22:00:00"

# Schedule with natural language
python run.py --schedule 001 --schedule-at "tonight 10pm"

# Schedule with dependencies
python run.py --schedule 002 --schedule-at "tomorrow 9am" --schedule-deps "001"

# Schedule with priority
python run.py --schedule 001 --schedule-at "tonight 10pm" --schedule-priority high
```

**Scheduler Options:**

| Option | Description |
|--------|-------------|
| `--schedule SPEC` | Spec ID to schedule |
| `--schedule-at TIME` | When to run (ISO format or natural language like "tonight 10pm") |
| `--schedule-priority LEVEL` | Priority: low, normal, high, urgent (default: normal) |
| `--schedule-deps SPECS` | Comma-separated spec IDs this build depends on |

#### Scheduler Management

```bash
# Start scheduler service
python run.py --schedule-start

# Stop scheduler service
python run.py --schedule-stop

# Check scheduler status
python run.py --schedule-status

# Cancel scheduled build
python run.py --schedule-cancel BUILD_ID
```

The scheduler service runs in the background and executes builds at their scheduled times. Use `--schedule-status` to see upcoming builds and their IDs.

### Merge Analytics Commands

Track and analyze merge operations.

#### List Merge History

```bash
# List recent merge operations
python run.py --merge-analytics-list

# Limit results
python run.py --merge-analytics-list --analytics-limit 50

# Filter by task
python run.py --merge-analytics-list --analytics-task 001-feature
```

#### Merge Analytics Summary

```bash
# Show aggregated statistics
python run.py --merge-analytics-summary
```

Shows:
- Total merges
- Success/failure rate
- Average time to merge
- Conflict rate

#### Export Merge Analytics

```bash
# Export as JSON
python run.py --merge-analytics-export --analytics-output merges.json --analytics-format json

# Export as CSV
python run.py --merge-analytics-export --analytics-output merges.csv --analytics-format csv
```

**Analytics Options:**

| Option | Description |
|--------|-------------|
| `--analytics-format FORMAT` | Export format: json or csv (default: json) |
| `--analytics-output FILE` | Output file path |
| `--analytics-limit N` | Limit list results (default: 100) |
| `--analytics-task TASK_ID` | Filter by task ID |

### Productivity Analytics Commands

Track productivity and development trends across all specs.

#### Show Productivity Analytics

```bash
# Show overall analytics
python run.py --analytics

# Show trends over time
python run.py --analytics --analytics-trends

# Customize trends
python run.py --analytics --analytics-trends --analytics-days 60 --analytics-granularity weekly
```

**Analytics Options:**

| Option | Description |
|--------|-------------|
| `--analytics-trends` | Show productivity trends over time |
| `--analytics-days N` | Number of days to analyze (default: 30) |
| `--analytics-granularity LEVEL` | Time granularity: daily, weekly, monthly (default: daily) |
| `--analytics-export-path FILE` | Export analytics to file |

#### Export Analytics

```bash
# Export analytics to file
python run.py --analytics --analytics-export-path analytics.json --analytics-format json

# Export trends
python run.py --analytics --analytics-trends --analytics-export-path trends.csv --analytics-format csv
```

Analytics include:
- Build completion rates
- Average build times
- QA pass rates
- Productivity trends
- Time distribution by phase

### Examples

```bash
# Simple build with auto-detected model
python run.py --spec 001

# Custom model with verbose output
python run.py --spec 001 --model claude-opus-4-5-20250929 --verbose

# Run in project directly (no worktree isolation)
python run.py --spec 001 --direct

# Build with limited iterations
python run.py --spec 001 --max-iterations 5

# Build and skip QA
python run.py --spec 001 --skip-qa

# Review completed build
python run.py --spec 001 --review

# Merge after review
python run.py --spec 001 --merge

# Create PR to develop branch
python run.py --spec 001 --create-pr --pr-target develop

# Run QA on existing build
python run.py --spec 001 --qa

# Add follow-up task
python run.py --spec 001 --followup
```

---

## `spec_runner.py` - Spec Creation

Dynamic spec creation with AI-powered complexity assessment.

**Location:** `apps/backend/runners/spec_runner.py`

### Basic Usage

```bash
cd apps/backend

# Interactive mode (recommended for new users)
python runners/spec_runner.py --interactive

# Create spec from task description
python runners/spec_runner.py --task "Add user authentication to the app"

# Force specific complexity level
python runners/spec_runner.py --task "Fix button" --complexity simple

# Continue existing spec from last checkpoint
python runners/spec_runner.py --continue 001-feature
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `--task TEXT` | Task description describing what to build |
| `--task-file FILE` | Read task description from file (for long descriptions) |
| `--interactive` | Interactive mode with prompts (recommended) |
| `--continue SPEC` | Continue existing spec from last checkpoint |
| `--complexity LEVEL` | Force complexity level: `simple`, `standard`, or `complex` |
| `--no-ai-assessment` | Skip AI complexity analysis, use heuristic rules only |
| `--model MODEL` | Claude model to use (haiku, sonnet, opus, or full model ID) |
| `--thinking-level LEVEL` | Extended thinking level: none, low, medium, high, ultrathink |
| `--project-dir PATH` | Project directory (default: current directory) |
| `--no-build` | Don't automatically start build after spec creation |

### Complexity Tiers

Auto Code uses a dynamic pipeline based on task complexity:

#### SIMPLE (3 phases)

**Characteristics:**
- 1-2 files to modify
- No external integrations
- Clear requirements

**Pipeline:**
1. Discovery (analyze codebase)
2. Quick Spec (create specification)
3. Validate (check completeness)

**Example:**
```bash
python runners/spec_runner.py --task "Fix button color in Header component"
```

#### STANDARD (6 phases)

**Characteristics:**
- 3-10 files to modify
- May have external dependencies
- Moderate complexity

**Pipeline:**
1. Discovery (analyze codebase)
2. Requirements (gather detailed requirements)
3. Context (collect codebase context)
4. Spec (create specification)
5. Plan (create implementation plan)
6. Validate (check completeness)

**Example:**
```bash
python runners/spec_runner.py --task "Add dark mode toggle to settings"
```

#### STANDARD + Research (7 phases)

**Characteristics:**
- Same as Standard but with external integrations
- Requires research phase

**Pipeline:**
1. Discovery (analyze codebase)
2. Requirements (gather detailed requirements)
3. Research (investigate external libraries/APIs)
4. Context (collect codebase context)
5. Spec (create specification)
6. Plan (create implementation plan)
7. Validate (check completeness)

**Example:**
```bash
python runners/spec_runner.py --task "Integrate Stripe payments"
```

#### COMPLEX (8 phases)

**Characteristics:**
- 10+ files to modify
- Major architectural changes
- Multiple services/integrations

**Pipeline:**
1. Discovery (analyze codebase)
2. Requirements (gather detailed requirements)
3. Research (investigate all integrations)
4. Context (collect codebase context)
5. Spec (create specification)
6. Plan (create implementation plan)
7. Self-Critique (review with ultrathink)
8. Validate (check completeness)

**Example:**
```bash
python runners/spec_runner.py --task "Add Graphiti memory system with FalkorDB"
```

### AI Complexity Assessment

By default, Auto Code uses AI to assess task complexity. The assessment considers:

- **Number of files/services involved** - More files = higher complexity
- **External integrations** - Third-party APIs increase complexity
- **Infrastructure changes** - Docker, databases, etc. increase complexity
- **Existing patterns** - Following existing patterns reduces complexity
- **Risk factors** - Potential edge cases increase complexity

**Override AI assessment:**
```bash
# Force simple mode (skips AI analysis)
python runners/spec_runner.py --task "Simple fix" --complexity simple

# Use heuristics instead of AI
python runners/spec_runner.py --task "Medium task" --no-ai-assessment
```

### Task File Usage

For complex task descriptions, use a file:

```bash
# Create task file
cat > task.txt << EOF
Add comprehensive error handling to the authentication system:
- Validate all user inputs
- Handle network errors gracefully
- Show user-friendly error messages
- Log errors for debugging
EOF

# Use file for spec creation
python runners/spec_runner.py --task-file task.txt
```

### Continuing Existing Specs

If a spec creation was interrupted, continue from the last checkpoint:

```bash
python runners/spec_runner.py --continue 001-feature-name
```

This resumes from the last completed phase.

### Examples

```bash
# Interactive mode (recommended for new users)
python runners/spec_runner.py --interactive

# Simple fix (auto-detected complexity)
python runners/spec_runner.py --task "Fix button color in Header component"

# Feature with external integration (auto-detected)
python runners/spec_runner.py --task "Add Graphiti memory with FalkorDB"

# Force simple complexity
python runners/spec_runner.py --task "Update text on homepage" --complexity simple

# Use heuristics instead of AI assessment
python runners/spec_runner.py --task "Medium complexity feature" --no-ai-assessment

# Complex feature with custom model and thinking level
python runners/spec_runner.py \
  --task "Refactor authentication system with OAuth providers" \
  --model opus \
  --thinking-level ultrathink

# Create spec without auto-starting build
python runners/spec_runner.py \
  --task "Add user settings page" \
  --no-build

# Continue interrupted spec
python runners/spec_runner.py --continue 001-auth-feature
```

---

## `validate_spec.py` - Spec Validation

Validate spec files against checkpoints to ensure completeness.

**Location:** `apps/backend/spec/validate_spec.py`

### Usage

```bash
# Validate all checkpoints
python apps/backend/spec/validate_spec.py \
  --spec-dir .auto-claude/specs/001-feature \
  --checkpoint all

# Validate specific checkpoint
python apps/backend/spec/validate_spec.py \
  --spec-dir .auto-claude/specs/001-feature \
  --checkpoint spec

# Auto-fix common issues
python apps/backend/spec/validate_spec.py \
  --spec-dir .auto-claude/specs/001-feature \
  --auto-fix

# Output as JSON
python apps/backend/spec/validate_spec.py \
  --spec-dir .auto-claude/specs/001-feature \
  --json
```

### Options

| Option | Description |
|--------|-------------|
| `--spec-dir PATH` | Directory containing spec files (required) |
| `--checkpoint CHECKPOINT` | Checkpoint to validate: prereqs, context, spec, plan, all |
| `--auto-fix` | Attempt to auto-fix common issues |
| `--json` | Output validation results as JSON |

### Checkpoints

Validates the following checkpoints:

- `prereqs` - Prerequisites and environment setup
- `context` - Codebase context collection
- `spec` - Specification document completeness
- `plan` - Implementation plan validation
- `all` - Validate all checkpoints

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All validations passed |
| 1 | One or more validations failed |

### Examples

```bash
# Validate complete spec
python apps/backend/spec/validate_spec.py \
  --spec-dir .auto-claude/specs/001-feature \
  --checkpoint all

# Validate spec document only
python apps/backend/spec/validate_spec.py \
  --spec-dir .auto-claude/specs/001-feature \
  --checkpoint spec

# Validate and auto-fix issues
python apps/backend/spec/validate_spec.py \
  --spec-dir .auto-claude/specs/001-feature \
  --auto-fix

# Get JSON output for automation
python apps/backend/spec/validate_spec.py \
  --spec-dir .auto-claude/specs/001-feature \
  --json
```

---

## Common Workflows

### First-Time Setup

```bash
# 1. Install dependencies
cd apps/backend
uv venv
uv pip install -r requirements.txt

# 2. Authenticate
claude
# Then type: /login

# 3. Create first spec
python runners/spec_runner.py --interactive

# 4. Run build
python run.py --spec 001

# 5. Review build
python run.py --spec 001 --review

# 6. Merge to project
python run.py --spec 001 --merge
```

### Daily Development

```bash
# 1. Create new spec
python runners/spec_runner.py --task "Fix login bug"

# 2. Run build (auto-detected from most recent spec)
python run.py --list  # Find spec number
python run.py --spec 002

# 3. Run QA
python run.py --spec 002 --qa

# 4. Merge if QA passes
python run.py --spec 002 --merge
```

### Debugging Failed Builds

```bash
# 1. Check build progress
cat .auto-claude/specs/001-feature/build-progress.txt

# 2. Run with verbose output
python run.py --spec 001 --verbose

# 3. Review agent outputs
ls -la .auto-claude/specs/001-feature/

# 4. Continue from last state (default behavior)
python run.py --spec 001
```

### Working with Multiple Specs

```bash
# List all specs
python run.py --list

# Check status of all specs
python run.py --batch-status

# Run specific spec
python run.py --spec 003

# List all worktrees
python run.py --list-worktrees

# Clean up old specs
python run.py --batch-cleanup
```

---

## Environment Configuration

### Required Environment Variables

Set these in `apps/backend/.env`:

```bash
# Authentication (from Claude Code CLI)
CLAUDE_CODE_OAUTH_TOKEN=eyJ0eXAi...

# Graphiti Memory System
GRAPHITI_ENABLED=true

# LLM Provider (choose one)
ANTHROPIC_API_KEY=sk-ant-...
# Or: OPENAI_API_KEY=sk-...
# Or: GOOGLE_API_KEY=...
```

### Optional Environment Variables

```bash
# Model Configuration
AUTO_BUILD_MODEL=claude-sonnet-4-5-20250929

# Custom API Endpoint
ANTHROPIC_BASE_URL=https://api.anthropic.com

# Linear Integration
LINEAR_API_KEY=lin_api_
LINEAR_TEAM_ID=TEAM_ID

# Electron E2E Testing (for frontend builds)
ELECTRON_MCP_ENABLED=true
ELECTRON_DEBUG_PORT=9222

# Debug Output
DEBUG=false
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Validation error |
| 3 | Authentication error |
| 4 | Spec not found |
| 5 | Build failed |
| 6 | QA failed |

---

## Troubleshooting

### Common Issues

**Authentication Failed:**
```bash
Error: No authentication token found
```
**Solution:** Run `claude` CLI and type `/login` to authenticate.

**Python Version:**
```bash
Error: Auto Code requires Python 3.10 or higher
```
**Solution:** Upgrade to Python 3.12+ (required for Graphiti).

**Build Stuck:**
```bash
# Check progress
cat .auto-claude/specs/001/build-progress.txt

# Limit iterations
python run.py --spec 001 --max-iterations 10

# Run with verbose output
python run.py --spec 001 --verbose
```

**Worktree Conflicts:**
```bash
# Preview conflicts
python run.py --spec 001 --merge-preview

# Resolve manually in worktree
cd .worktrees/001-feature
# ... resolve conflicts ...

# Re-run merge
python run.py --spec 001 --merge
```

### Getting Help

```bash
# Show help for run.py
python run.py --help

# Show help for spec_runner.py
python runners/spec_runner.py --help

# Show help for validate_spec.py
python apps/backend/validate_spec.py --help
```

---

## See Also

- [Backend API Reference](./backend-api.md) - Programmatic API and module documentation
- [Web Backend API](./web-backend-api.md) - FastAPI endpoints reference
- [Getting Started Guide](../guides/getting-started.md) - Setup and first build
- [Troubleshooting Guide](../guides/troubleshooting.md) - Common issues and solutions

---

**Version:** 2.8.0
**Last Updated:** 2026-02-12
**Maintained By:** Auto Code Team
