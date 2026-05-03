# Auto Code Advanced Usage

This document covers advanced usage patterns for power users who want to customize and optimize their Auto Code experience. If you're new to Auto Code, start with the [Quick Start Guide](QUICK-START.md) or [CLI Usage Guide](CLI-USAGE.md).

## Table of Contents

- [Parallel Execution](#parallel-execution)
- [Agent Customization](#agent-customization)
- [Memory System](#memory-system)
- [LLM Provider Configuration](#llm-provider-configuration)
- [Third-Party Integrations](#third-party-integrations)
- [QA Customization](#qa-customization)
- [Interactive Controls](#interactive-controls)
- [Workspace Best Practices](#workspace-best-practices)

---

## Parallel Execution

Auto Code supports running multiple specs in parallel and can spawn subagents for concurrent subtask work.

### Running Multiple Specs Simultaneously

You can run multiple specs at the same time from different terminal windows:

```bash
# Terminal 1
cd apps/backend
python run.py --spec 001-auth

# Terminal 2
cd apps/backend
python run.py --spec 002-dashboard

# Terminal 3
cd apps/backend
python run.py --spec 003-api-endpoints
```

**Resource Requirements:**
- Each active spec consumes ~500MB RAM
- CPU usage scales with agent activity
- Network bandwidth depends on LLM provider

**Best Practices:**
- Start with 2-3 parallel specs
- Monitor system resources
- Avoid parallel specs that modify the same files
- Use for independent features only

### Subagent Spawning

The Coder agent automatically spawns subagents for parallelizable subtasks:

```bash
# Example: Implementing a feature with independent components
Task: "Add user authentication with OAuth, registration, and password reset"

# Agent may spawn subagents for:
# - Subagent 1: OAuth integration (Google, GitHub)
# - Subagent 2: Registration form and validation
# - Subagent 3: Password reset flow
```

**How it Works:**
1. Planner identifies independent subtasks in implementation plan
2. Coder creates subagent sessions for parallel work
3. Each subagent works on isolated files/components
4. Coder merges all subagent results

**Configuration:**
```bash
# Maximum concurrent subagents (default: 4)
# Set in apps/backend/.env
MAX_SUBAGENTS=4
```

---

## Agent Customization

You can customize agent behavior by modifying system prompts or creating custom agents.

### Modifying Agent Prompts

All agent prompts live in `apps/backend/prompts/`:

```
apps/backend/prompts/
├── planner.md           # Creates implementation plans
├── coder.md             # Implements subtasks
├── coder_recovery.md    # Recovers from stuck states
├── qa_reviewer.md       # Validates acceptance criteria
├── qa_fixer.md          # Fixes QA-reported issues
├── spec_gatherer.md     # Collects requirements
├── spec_researcher.md   # Validates external integrations
├── spec_writer.md       # Creates spec.md documents
└── spec_critic.md       # Self-critique and refinement
```

**Example: Customizing the Coder Agent**

1. Read the existing prompt:
```bash
cat apps/backend/prompts/coder.md
```

2. Make your modifications:
```markdown
# Add custom coding standards
## Coding Standards
- Follow PEP 8 for Python code
- Use TypeScript strict mode
- Add JSDoc comments to all functions
- Write tests for all new features

# Add project-specific patterns
## Project-Specific Patterns
- Use React Query for data fetching
- Follow the existing component structure in src/components/
- Add error handling with try-catch blocks
```

3. Restart Auto Code to apply changes

**Best Practices:**
- Keep prompts focused on the agent's role
- Provide examples in prompts
- Test modifications on simple specs first
- Document your changes in prompt comments

### Creating Custom Agents

For specialized workflows, you can create custom agents:

1. Create a new prompt file:
```bash
# Example: Performance optimization specialist
apps/backend/prompts/optimizer.md
```

2. Define the agent role and behavior:
```markdown
# Performance Optimizer Agent

You are a performance optimization specialist. Your role is to:
1. Analyze code for performance bottlenecks
2. Propose optimizations with trade-offs
3. Implement approved optimizations
4. Benchmark before/after results

## Optimization Principles
- Profile before optimizing
- Prioritize user-facing improvements
- Document trade-offs clearly
- Avoid premature optimization
```

3. Integrate into the workflow:
```python
# In your custom run.py or agent orchestration
from agents.custom_agent import CustomOptimizerAgent

optimizer = CustomOptimizerAgent(
    project_dir=project_dir,
    spec_dir=spec_dir
)
optimizer.run()
```

---

## Memory System

Auto Code uses Graphiti to maintain a knowledge graph across sessions, storing patterns, gotchas, and discoveries.

### How Memory Works

The memory system automatically:
- Extracts patterns from each agent session
- Stores code relationships and dependencies
- Remembers what worked and what didn't
- Provides context to future sessions

**Memory Storage:**
```bash
# Memory data lives in spec directories
.auto-claude/specs/XXX/graphiti/
├── graphiti.db          # Knowledge graph database
├── embeddings/          # Vector embeddings for search
└── insights/            # Extracted session insights
```

### Configuring Memory Providers

Memory supports multiple LLM and embedding providers:

**OpenAI (Recommended):**
```bash
# In apps/backend/.env
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=openai
GRAPHITI_EMBEDDER_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**Anthropic Claude:**
```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=anthropic
GRAPHITI_EMBEDDER_PROVIDER=voyage
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=sk-voyage-...
```

**Ollama (Local, Free):**
```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

### Inspecting Memory

View what the memory system has learned:

```bash
# View recent insights
cat .auto-claude/specs/XXX/graphiti/insights/latest.json

# Search memory programmatically
cd apps/backend
python -c "
from integrations.graphiti.memory import get_graphiti_memory
memory = get_graphiti_memory('specs/XXX', '.')
results = memory.search('authentication patterns')
print(results)
"
```

### Managing Memory

**Disable Memory (Not Recommended):**
```bash
# In apps/backend/.env
GRAPHITI_ENABLED=false
```

**Clear Memory:**
```bash
# Delete memory for a specific spec
rm -rf .auto-claude/specs/XXX/graphiti/

# Memory will rebuild on next run
```

### Best Practices

- **Keep memory enabled** - improves agent performance over time
- **Use OpenAI or Voyage embeddings** - best quality
- **Local development** - Ollama is free and private
- **Production** - Use hosted providers for reliability
- **Cost management** - Memory adds ~10% to API costs

---

## LLM Provider Configuration

Auto Code supports multiple LLM providers beyond Claude, but provider support
has two layers:

- The provider adapter creates a model session.
- The runtime mode decides whether that session can use tools, MCP, shell
  commands, filesystem edits, or only text/patch proposals.

Claude remains required for full autonomous coding. Other providers can run
`analysis_only`, `patch_proposal`, or the experimental `generic_edit` local
tool runtime. See [Provider Runtime Modes](../docs/architecture/provider-runtime-modes.md).

Multi-provider support is useful for:
- Cost optimization (mix and match providers)
- Redundancy and failover
- Feature-specific model selection

### Supported Providers

| Provider | Models | Use Case | Cost (per 1M tokens) |
|----------|--------|----------|---------------------|
| **Claude** | Opus 4.5, Sonnet 4.5 | Best reasoning, complex tasks | $15-$75 |
| **OpenAI** | GPT-4o, GPT-4o-mini | Fast, cost-effective | $2.5-$5 |
| **Google** | Gemini 2.5 Pro | Multimodal, long context | Variable |
| **Azure OpenAI** | GPT-4 variants | Enterprise, compliance | Variable |
| **Ollama** | Llama 3, Mistral | Local, private | Free |

### Configuring Alternative Providers

**Note:** The Claude Code OAuth token is required for the full agent SDK runtime. Alternative providers can be used for specific limited phases when configured with a compatible runtime mode.

**Patch proposal mode for coder subtasks:**

```bash
AI_ENGINE_PROVIDER=claude
AGENT_PROVIDER_CODER=openai
AGENT_MODEL_CODER=gpt-4o
AGENT_RUNTIME_MODE_CODER=patch_proposal
OPENAI_API_KEY=sk-...
```

In this mode, the provider returns a structured unified diff. Auto Code validates
the diff locally before applying it and does not give the provider direct tool or
filesystem access.

**Generic edit mode for coder subtasks:**

```bash
AI_ENGINE_PROVIDER=claude
AGENT_PROVIDER_CODER=openai
AGENT_MODEL_CODER=gpt-4o
AGENT_RUNTIME_MODE_CODER=generic_edit
OPENAI_API_KEY=sk-...
```

In this mode, Auto Code exposes a small local action loop for workspace-relative
file reads, validated patches, bounded file writes, and security-checked single
commands. OpenAI-compatible sessions use provider-native tool calls when
available; direct OpenAI, Ollama, OpenRouter, and LiteLLM sessions expose this
normalized bridge when the routed model/gateway supports tools. If native tool
calls are rejected, Auto Code falls back to the JSON action loop.

**Runtime-aware fallback for non-Claude providers:**

```bash
AI_ENGINE_PROVIDER=openai
AUTO_CODE_RUNTIME_MODE=full_autonomous
AUTO_CODE_RUNTIME_FALLBACK=true
OPENAI_API_KEY=sk-...
```

This degrades to the first compatible limited runtime, usually `generic_edit`.
It does not grant MCP/tool/subagent parity to the selected provider.

**OpenAI (for memory system):**
```bash
# apps/backend/.env
GRAPHITI_LLM_PROVIDER=openai
GRAPHITI_EMBEDDER_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

**Ollama (local models):**
```bash
# Install Ollama
ollama pull llama3.2
ollama pull mistral

# Configure
GRAPHITI_LLM_PROVIDER=ollama
GRAPHITI_EMBEDDER_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_LLM_MODEL=mistral
OLLAMA_EMBEDDER_MODEL=nomic-embed-text
```

**Google Gemini:**
```bash
GRAPHITI_LLM_PROVIDER=google
GRAPHITI_EMBEDDER_PROVIDER=google
GOOGLE_API_KEY=...
```

### Cost Optimization Strategy

**Tiered Approach:**
1. **Claude Opus** - For planning, complex architecture (highest quality)
2. **Claude Sonnet** - For coding, QA (balanced cost/quality)
3. **OpenAI GPT-4o-mini** - For memory embeddings (cheapest)
4. **Ollama** - For local development (free)

**Example Configuration:**
```bash
# Use Claude for agents, OpenAI for memory
AUTO_BUILD_MODEL=claude-sonnet-4-5-20250929
GRAPHITI_LLM_PROVIDER=openai
GRAPHITI_EMBEDDER_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

---

## Third-Party Integrations

Auto Code integrates with GitHub, GitLab, and Linear for issue tracking and progress management.

### GitHub Integration

**Setup:**
1. Create GitHub Personal Access Token:
   - Go to https://github.com/settings/tokens
   - Generate token with `repo`, `issues`, `pull_requests` scopes

2. Configure Auto Code:
```bash
# apps/backend/.env
GITHUB_TOKEN=ghp_...
GITHUB_DEFAULT_BRANCH=main
```

**Features:**
- Import GitHub issues as specs
- Create PRs from completed builds
- Update issue status automatically
- Link specs to issues

**Usage:**
```bash
# Import issue as spec
cd apps/backend
python runners/github_import.py --issue 123

# Create PR after merge
python run.py --spec 001 --create-pr
```

### GitLab Integration

**Setup:**
```bash
# apps/backend/.env
GITLAB_TOKEN=glpat-...
GITLAB_INSTANCE_URL=https://gitlab.com  # or self-hosted
```

**Features:**
- Import GitLab issues
- Create merge requests
- Update issue status

### Linear Integration

**Setup:**
1. Get Linear API key:
   - Go to https://linear.app/settings/api
   - Create personal API key

2. Configure:
```bash
# apps/backend/.env
LINEAR_API_KEY=lin_...
```

**Features:**
- Import Linear issues as specs
- Sync spec status back to Linear
- Create Linear issues from QA failures

**Desktop UI Import:**
1. Open Auto Code desktop app
2. Click "Import from Linear"
3. Select issues to import
4. Specs created automatically

---

## QA Customization

Tailor the QA validation loop to your project's standards and requirements.

### Custom QA Criteria

Modify the QA reviewer prompt to add custom checks:

```bash
# Edit apps/backend/prompts/qa_reviewer.md
```

**Add Custom Validation:**
```markdown
## Custom Validation Rules

### Security Checklist
- [ ] No hardcoded secrets or API keys
- [ ] User input is sanitized
- [ ] Authentication is properly implemented
- [ ] SQL injection protection in place

### Performance Checklist
- [ ] No N+1 queries
- [ ] Images are optimized
- [ ] Caching strategy implemented
- [ ] Bundle size under 500KB

### Accessibility Checklist
- [ ] ARIA labels on interactive elements
- [ ] Keyboard navigation works
- [ ] Color contrast meets WCAG AA
- [ ] Screen reader compatible
```

### Custom Test Commands

Add project-specific test commands to QA:

```bash
# Edit .auto-claude/specs/XXX/implementation_plan.json
```

```json
{
  "verification_strategy": {
    "test_types_required": ["unit", "integration"],
    "commands": {
      "unit_tests": "pytest tests/unit/ -v",
      "integration_tests": "pytest tests/integration/ -v",
      "e2e_tests": "npm run test:e2e",
      "linting": "eslint src/ && black apps/backend/",
      "type_check": "tsc --noEmit && mypy apps/backend/"
    }
  }
```

### E2E Testing with Electron

For frontend changes, QA agents can perform automated E2E testing:

```bash
# Enable Electron MCP
# apps/backend/.env
ELECTRON_MCP_ENABLED=true
ELECTRON_DEBUG_PORT=9222

# Start Electron with debugging
npm run dev

# Run QA - will automatically test UI
python run.py --spec 001 --qa
```

**Capabilities:**
- Take screenshots
- Click buttons/links
- Fill forms
- Navigate routes
- Verify elements exist

---

## Interactive Controls

Intervene in agent sessions to provide guidance, fix issues, or change direction.

### Pause and Resume

**Keyboard Controls (CLI):**
```bash
# While agent is running:
Ctrl+C (once)  # Pause after current session
Ctrl+C (twice) # Exit immediately
```

**File-Based Controls:**
```bash
# Pause after current session
touch .auto-claude/specs/XXX/PAUSE

# Resume
rm .auto-claude/specs/XXX/PAUSE
```

### Human Input

Provide guidance to agents during builds:

```bash
# Create instruction file
echo "Focus on the authentication bug first, ignore dashboard for now" > .auto-claude/specs/XXX/HUMAN_INPUT.md

# Agent reads instructions on next session
```

**Example Scenarios:**
- Change implementation approach mid-build
- Prioritize specific subtasks
- Skip certain components
- Request different architecture

### Session Interruption

Pause builds to review progress or fix issues:

```bash
# Trigger PAUSE
touch .auto-claude/specs/001-feature/PAUSE

# Wait for agent to finish current session

# Review progress
cat .auto-claude/specs/001-feature/build-progress.txt

# Add guidance
echo "The approach looks good, but use Redux instead of Context API" > .auto-claude/specs/001-feature/HUMAN_INPUT.md

# Resume
rm .auto-claude/specs/001-feature/PAUSE
```

---

## Workspace Best Practices

Advanced strategies for managing Git worktrees and merging builds.

### Merge Strategies

**Approach 1: Test Before Merge**
```bash
# 1. Run build
python run.py --spec 001

# 2. Test in worktree
cd .worktrees/auto-code-001-feature/
npm run dev
# Manual testing...

# 3. Review changes
cd apps/backend
python run.py --spec 001 --review

# 4. Merge if satisfied
python run.py --spec 001 --merge
```

**Approach 2: Parallel Testing**
```bash
# Test multiple builds simultaneously
cd .worktrees/auto-code-001-feature/
npm run dev &

cd .worktrees/auto-code-002-feature/
npm run dev &

# Compare both implementations
```

**Approach 3: Incremental Merge**
```bash
# Merge specific files manually
cd .worktrees/auto-code-001-feature/
git checkout main -- package.json  # Keep original

cd apps/backend
python run.py --spec 001 --merge
# Resolve conflicts interactively
```

### Worktree Management

**List All Worktrees:**
```bash
git worktree list
```

**Clean Up Old Worktrees:**
```bash
# Remove worktree after merge
git worktree remove .worktrees/auto-code-001-feature

# Or prune all merged worktrees
git worktree prune
```

**Switch Between Worktrees:**
```bash
# Work on build 1
cd .worktrees/auto-code-001-feature/
npm run dev

# Work on build 2
cd .worktrees/auto-code-002-feature/
npm run dev
```

### Handling Merge Conflicts

When conflicts arise during merge:

```bash
# 1. Review conflicts
python run.py --spec 001 --merge

# 2. Auto Code pauses for conflict resolution

# 3. Resolve conflicts manually
cd .worktrees/auto-code-001-feature/
# Edit conflicted files...

# 4. Mark as resolved
git add <resolved-files>
git commit --no-edit

# 5. Return to backend
cd apps/backend

# 6. Continue merge
python run.py --spec 001 --merge
```

### When to Discard Builds

**Scenarios for Discarding:**
- Wrong implementation approach
- Test coverage insufficient
- Performance issues discovered
- Better alternative identified

```bash
# Discard build completely
python run.py --spec 001 --discard

# Build is deleted, worktree cleaned up
```

**Tip:** Review the build before discarding to learn from the agent's approach:

```bash
# Review even if discarding
python run.py --spec 001 --review

# Read agent's thought process
cat .auto-claude/specs/001/build-progress.txt

# Then discard
python run.py --spec 001 --discard
```

---

## Performance Optimization

Optimize Auto Code for faster builds and lower costs.

### Reduce API Costs

**Use Smaller Models:**
```bash
# Use Sonnet instead of Opus for simpler tasks
AUTO_BUILD_MODEL=claude-sonnet-4-5-20250929
```

**Limit Iterations:**
```bash
# Stop after 5 QA iterations (default: 50)
python run.py --spec 001 --max-qa-iterations 5
```

**Skip QA for Simple Changes:**
```bash
# Skip QA loop for text changes, simple fixes
python run.py --spec 001 --skip-qa
```

### Speed Up Builds

**Parallel Subagents:**
```bash
# Increase subagent limit (default: 4)
MAX_SUBAGENTS=8
```

**Reduce Context Window:**
```bash
# Use smaller context for faster token processing
# In apps/backend/core/client.py
max_tokens=4000  # instead of 8000
```

**Cache Dependencies:**
```bash
# Use local caching for faster iterations
# Ollama for memory (no API calls)
GRAPHITI_LLM_PROVIDER=ollama
```

---

## Troubleshooting Advanced Issues

See the [Troubleshooting Guide](TROUBLESHOOTING.md) for solutions to common issues.

### Debug Mode

Enable detailed logging for debugging:

```bash
# apps/backend/.env
DEBUG=true
LOG_LEVEL=debug
```

### Agent Recovery

If an agent gets stuck:

```bash
# 1. Pause the build
touch .auto-claude/specs/XXX/PAUSE

# 2. Review progress
cat .auto-claude/specs/XXX/build-progress.txt

# 3. Add recovery instructions
echo "The agent is stuck on X, try approach Y instead" > .auto-claude/specs/XXX/HUMAN_INPUT.md

# 4. Resume
rm .auto-claude/specs/XXX/PAUSE

# Agent will read HUMAN_INPUT.md and adjust
```

### Subtask Recovery

Retry specific subtasks:

```bash
# Edit implementation_plan.json
# Set subtask status from "completed" to "pending"

# Resume build
python run.py --spec XXX
```

---

## Further Reading

- [Quick Start Guide](QUICK-START.md) - Get started in 15 minutes
- [CLI Usage Guide](CLI-USAGE.md) - Terminal-only usage
- [Spec Creation Pipeline](SPEC-CREATION-PIPELINE.md) - How specs are created
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Solve common issues
- [CLAUDE.md](../CLAUDE.md) - Architecture and development

---

**Last Updated:** 2025-02-12
