# Agent Customization Guide

This guide explains how to customize and extend Auto Code's agent system. You'll learn how to modify agent behavior, create custom agents, and integrate them into your workflow.

## Table of Contents

- [Understanding Agents](#understanding-agents)
- [Agent Architecture](#agent-architecture)
- [Modifying Agent Prompts](#modifying-agent-prompts)
- [Creating Custom Agents](#creating-custom-agents)
- [Agent Testing](#agent-testing)
- [Best Practices](#best-practices)
- [Advanced Patterns](#advanced-patterns)

---

## Understanding Agents

Auto Code uses a multi-agent system where each agent has a specific role in the development process. Agents are powered by the Claude Agent SDK and use system prompts to define their behavior.

### Core Agents

| Agent | Prompt File | Role | When Used |
|-------|-------------|------|-----------|
| **Planner** | `planner.md` | Creates implementation plans | Start of each spec |
| **Coder** | `coder.md` | Implements subtasks | Main development phase |
| **Coder Recovery** | `coder_recovery.md` | Handles stuck states | When coder fails |
| **QA Reviewer** | `qa_reviewer.md` | Validates acceptance criteria | After implementation |
| **QA Fixer** | `qa_fixer.md` | Fixes QA issues | In QA loop |

### Spec Creation Agents

| Agent | Prompt File | Role | When Used |
|-------|-------------|------|-----------|
| **Spec Gatherer** | `spec_gatherer.md` | Collects requirements | Spec creation phase |
| **Spec Researcher** | `spec_researcher.md` | Validates external integrations | Research phase |
| **Spec Writer** | `spec_writer.md` | Creates spec documents | Writing phase |
| **Spec Critic** | `spec_critic.md` | Refines specs | Critique phase |
| **Complexity Assessor** | `complexity_assessor.md` | Determines task complexity | Start of spec creation |

### Ideation Agents

| Agent | Prompt File | Role |
|-------|-------------|------|
| **Code Improvements** | `ideation_code_improvements.md` | Suggests code enhancements |
| **Code Quality** | `ideation_code_quality.md` | Improves code quality |
| **Performance** | `ideation_performance.md` | Optimizes performance |
| **Security** | `ideation_security.md` | Finds security issues |
| **UI/UX** | `ideation_ui_ux.md` | Improves user experience |

---

## Agent Architecture

### How Agents Work

1. **Prompt Loading**: System prompts are loaded from `apps/backend/prompts/`
2. **Session Creation**: Agent creates a Claude SDK session with the prompt
3. **Tool Access**: Agents receive tools based on their role (planner, coder, qa_reviewer, qa_fixer)
4. **Execution**: Agent processes tasks and produces outputs
5. **Memory Storage**: Session insights are stored in Graphiti for future context

### Agent Code Structure

```
apps/backend/
├── prompts/              # System prompts for all agents
│   ├── planner.md
│   ├── coder.md
│   ├── qa_reviewer.md
│   └── ...
├── agents/               # Agent implementations
│   ├── planner.py       # Planner agent logic
│   ├── coder.py         # Coder agent logic
│   └── session.py       # Session management
└── core/
    └── client.py        # Claude SDK client factory
```

### Agent Session Flow

```python
# Simplified agent execution flow
from core.client import create_client

# 1. Create SDK client with agent-specific configuration
client = create_client(
    project_dir=project_dir,
    spec_dir=spec_dir,
    model="claude-sonnet-4-5-20250929",
    agent_type="coder"  # Determines tool permissions
)

# 2. Load system prompt
with open("apps/backend/prompts/coder.md") as f:
    system_prompt = f.read()

# 3. Create agent session
response = client.create_agent_session(
    name="coder-session",
    starting_message="Implement the authentication feature"
)

# 4. Process response and update memory
```

---

## Modifying Agent Prompts

The simplest way to customize agent behavior is to modify existing system prompts.

### Finding the Right Prompt

All prompts live in `apps/backend/prompts/`:

```bash
# List all agent prompts
ls -la apps/backend/prompts/

# Read a specific prompt
cat apps/backend/prompts/coder.md
```

### Prompt Structure

Each prompt follows this structure:

```markdown
## YOUR ROLE - AGENT NAME

Brief description of the agent's purpose.

---

## Core Principles

- Principle 1
- Principle 2

---

## Phase 1: Understanding Context

Instructions for how to read and understand the task...

---

## Phase 2: Execution

Instructions for the main work...

---

## Phase 3: Output

Instructions for how to produce results...
```

### Modification Examples

#### Example 1: Add Coding Standards to Coder Agent

**File:** `apps/backend/prompts/coder.md`

**Add this section after the role definition:**

```markdown
## Coding Standards

**MANDATORY**: All code must follow these standards:

### Python Code
- Follow PEP 8 style guide
- Use type hints for all function parameters
- Add docstrings to all classes and functions
- Maximum line length: 100 characters

### TypeScript/JavaScript Code
- Use TypeScript strict mode
- Avoid `any` types
- Add JSDoc comments to exported functions
- Use ESLint with the project's configuration

### Testing
- Write unit tests for all new functions
- Aim for 80%+ code coverage
- Use descriptive test names that explain what is being tested

### Documentation
- Update README.md for user-facing changes
- Add inline comments for complex logic
- Document API endpoints in OpenAPI/Swagger format
```

#### Example 2: Customize QA Reviewer to Enforce Standards

**File:** `apps/backend/prompts/qa_reviewer.md`

**Add to the verification checklist:**

```markdown
## Additional Verification Checklist

### Code Quality
- [ ] Code follows project coding standards
- [ ] No TODO or FIXME comments left in production code
- [ ] All functions have descriptive names
- [ ] Error handling is implemented where needed

### Documentation
- [ ] README.md updated if needed
- [ ] API documentation updated for endpoints
- [ ] Database migrations documented

### Performance
- [ ] No N+1 query problems
- [ ] Caching implemented where appropriate
- [ ] Database queries optimized
```

#### Example 3: Modify Planner Agent for Different Project Structure

**File:** `apps/backend/prompts/planner.md`

**Add project-specific service detection:**

```markdown
## Project-Specific Service Patterns

When creating implementation plans, follow these patterns:

### Frontend Changes
- Use `src/components/` for React components
- Use `src/services/` for API calls
- Use `src/hooks/` for custom React hooks
- Always create TypeScript interfaces for data structures

### Backend Changes
- Use `apps/backend/api/` for FastAPI endpoints
- Use `apps/backend/models/` for database models
- Use `apps/backend/services/` for business logic
- Always add validation with Pydantic

### Database Changes
- Create migration files in `apps/backend/migrations/`
- Update models in `apps/backend/models/`
- Add seed data in `apps/backend/seeds/`
```

### Testing Prompt Modifications

1. **Make a backup:**
   ```bash
   cp apps/backend/prompts/coder.md apps/backend/prompts/coder.md.backup
   ```

2. **Edit the prompt:**
   ```bash
   nano apps/backend/prompts/coder.md
   ```

3. **Test on a simple spec:**
   ```bash
   cd apps/backend
   python spec_runner.py --task "Add a simple hello world function" --complexity simple
   ```

4. **Review the output:**
   - Check if agents follow your new standards
   - Verify code quality meets expectations
   - Adjust prompt if needed

5. **Restore from backup if issues occur:**
   ```bash
   cp apps/backend/prompts/coder.md.backup apps/backend/prompts/coder.md
   ```

---

## Creating Custom Agents

For specialized workflows, you can create entirely new agents.

### When to Create Custom Agents

Consider a custom agent when:
- You need specialized expertise not covered by existing agents
- Your workflow requires multiple custom passes
- You want to integrate external tools or APIs
- You need to enforce project-specific conventions

### Step 1: Create the Prompt File

Create a new prompt file in `apps/backend/prompts/`:

```bash
# Example: Performance optimization specialist
touch apps/backend/prompts/optimizer.md
```

**Example prompt content:**

```markdown
## YOUR ROLE - PERFORMANCE OPTIMIZER AGENT

You are a performance optimization specialist. Your role is to analyze code for performance bottlenecks and implement optimizations while maintaining functionality.

---

## Optimization Principles

1. **Profile Before Optimizing**: Never optimize without measurements
2. **Prioritize User-Facing Improvements**: Focus on what users experience
3. **Document Trade-offs**: Explain why an optimization was chosen
4. **Avoid Premature Optimization**: Optimize only when there's a measured problem

---

## Analysis Process

### 1. Identify Performance Issues

Look for:
- N+1 query problems
- Inefficient database queries
- Unnecessary loops or computations
- Missing caching opportunities
- Large payload transfers
- Unoptimized rendering (for frontend)

### 2. Measure Impact

```bash
# Profile the code
python -m cProfile -o profile.stats your_script.py
python -m pstats profile.stats

# Check query performance
EXPLAIN ANALYZE SELECT ...
```

### 3. Propose Solutions

For each issue, provide:
- **Current performance**: Baseline measurements
- **Proposed optimization**: What to change
- **Expected improvement**: Quantified impact
- **Trade-offs**: Any downsides (complexity, readability, etc.)

---

## Implementation

### Optimization Categories

#### Database Optimizations
- Add indexes to frequently queried columns
- Use select_related/prefetch_related (Django) or similar
- Implement query result caching
- Optimize complex joins

#### Caching Strategies
- Add Redis caching for expensive operations
- Implement HTTP caching headers
- Use memoization for pure functions
- Cache computed results

#### Code Optimizations
- Replace O(n²) algorithms with O(n log n)
- Use generators instead of lists for large datasets
- Implement lazy loading
- Optimize hot paths

#### Frontend Optimizations
- Implement virtual scrolling for long lists
- Add pagination to reduce initial load
- Code splitting and lazy loading
- Optimize images and assets

---

## Output Format

After optimization, provide:

```markdown
## Performance Report

### Changes Made

1. **Optimization 1**
   - **File**: `src/services/user.ts`
   - **Change**: Added Redis caching for user queries
   - **Impact**: Reduced query time from 500ms to 50ms
   - **Trade-off**: Requires Redis infrastructure

2. **Optimization 2**
   - **File**: `src/components/UserList.tsx`
   - **Change**: Implemented virtual scrolling
   - **Impact**: Render time reduced from 2s to 200ms for 10,000 items
   - **Trade-off**: Increased component complexity

### Before/After Metrics

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| API response time | 1200ms | 150ms | 87.5% faster |
| Initial page load | 4.5s | 1.2s | 73% faster |
| Memory usage | 450MB | 180MB | 60% reduction |

### Verification

- [ ] All existing tests pass
- [ ] No regressions in functionality
- [ ] Performance improvements verified with benchmarks
```

---

## CRITICAL: Safety

**ALWAYS:**
- Run tests before and after optimizations
- Use feature flags for risky changes
- Have a rollback plan ready
- Monitor production metrics after deployment

**NEVER:**
- Optimize code you don't understand
- Make optimizations that break functionality
- Remove error handling for "performance"
- Optimize without measuring first
```

### Step 2: Create Agent Implementation

Create the Python implementation in `apps/backend/agents/`:

```bash
# Create optimizer agent
touch apps/backend/agents/optimizer.py
```

**Example implementation:**

```python
"""
Performance Optimizer Agent

Analyzes code for performance bottlenecks and implements optimizations.
"""

from core.client import create_client
from agents.session import run_agent_session, post_session_processing
import logging

logger = logging.getLogger(__name__)


def run_optimizer_agent(project_dir: str, spec_dir: str, model: str = "claude-sonnet-4-5-20250929"):
    """
    Run the performance optimizer agent.

    Args:
        project_dir: Path to project root
        spec_dir: Path to spec directory
        model: Model to use for agent

    Returns:
        Agent session results
    """
    logger.info("Starting Performance Optimizer Agent")

    # Create SDK client with optimizer-specific configuration
    client = create_client(
        project_dir=project_dir,
        spec_dir=spec_dir,
        model=model,
        agent_type="optimizer"  # Custom agent type
    )

    # Read system prompt
    prompt_path = "apps/backend/prompts/optimizer.md"
    with open(prompt_path) as f:
        system_prompt = f.read()

    # Starting message for the optimizer
    starting_message = """
Analyze the current codebase for performance bottlenecks and propose optimizations.

Focus on:
1. Database query performance
2. Caching opportunities
3. Algorithmic complexity
4. Frontend rendering performance

Provide a detailed report with before/after metrics.
    """

    # Run the agent session
    try:
        response = run_agent_session(
            client=client,
            agent_name="optimizer",
            starting_message=starting_message,
            system_prompt=system_prompt
        )

        # Process results and save to memory
        post_session_processing(
            response=response,
            agent_name="optimizer",
            spec_dir=spec_dir,
            project_dir=project_dir
        )

        return response

    except Exception as e:
        logger.error(f"Optimizer agent failed: {e}")
        raise
```

### Step 3: Register Custom Agent Type

Update `core/client.py` to recognize your custom agent type:

```python
# In core/client.py

# Add your agent type to the permissions mapping
AGENT_TOOL_PERMISSIONS = {
    "planner": {
        "allowed_tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        "max_thinking_tokens": 20000
    },
    "coder": {
        "allowed_tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        "max_thinking_tokens": None
    },
    "qa_reviewer": {
        "allowed_tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Task"],
        "max_thinking_tokens": 16000
    },
    # Add your custom agent type
    "optimizer": {
        "allowed_tools": ["Read", "Bash", "Grep"],  # Read-only access for analysis
        "max_thinking_tokens": 20000
    }
}
```

### Step 4: Integrate into Workflow

Add your agent to the appropriate workflow:

**Option A: Add to main pipeline (run.py)**

```python
# In apps/backend/run.py

from agents.optimizer import run_optimizer_agent

def run_optimization_phase(project_dir: str, spec_dir: str):
    """Run performance optimization after QA passes."""
    logger.info("Running performance optimization...")

    response = run_optimizer_agent(
        project_dir=project_dir,
        spec_dir=spec_dir
    )

    return response
```

**Option B: Run as standalone command**

```python
# Add to apps/backend/cli.py or create new entry point

@app.command()
def optimize(spec_id: str):
    """Run performance optimization on a spec."""
    spec_dir = f".auto-claude/specs/{spec_id}"
    project_dir = "."

    run_optimizer_agent(project_dir, spec_dir)
```

**Option C: Create custom workflow**

```bash
# Create apps/backend/workflows/optimize.py

from agents.optimizer import run_optimizer_agent

def optimization_workflow(spec_id: str):
    """Run performance optimization workflow."""
    # Step 1: Analyze current state
    # Step 2: Run optimizer agent
    # Step 3: Implement optimizations
    # Step 4: Run tests
    # Step 5: Generate report
    pass
```

### Step 5: Test Your Custom Agent

```bash
# Test the optimizer agent
cd apps/backend
python -c "
from agents.optimizer import run_optimizer_agent
response = run_optimizer_agent('.', '.auto-claude/specs/001-feature')
print(response)
"
```

---

## Agent Testing

Testing agent modifications ensures they behave as expected.

### Unit Testing Agent Logic

```python
# tests/test_custom_agent.py

import pytest
from agents.optimizer import run_optimizer_agent

def test_optimizer_analyzes_code():
    """Test that optimizer analyzes code correctly."""
    response = run_optimizer_agent(
        project_dir="tests/fixtures/sample_project",
        spec_dir="tests/fixtures/sample_spec"
    )

    assert "performance" in response.lower()
    assert "optimization" in response.lower()

def test_optimizer_proposes_solutions():
    """Test that optimizer proposes concrete solutions."""
    # ... test implementation
```

### Integration Testing

```python
# tests/test_agent_integration.py

def test_full_agent_workflow():
    """Test agent in full workflow."""
    # 1. Create spec
    # 2. Run planner
    # 3. Run coder
    # 4. Run custom agent
    # 5. Verify results
```

### Prompt Validation

```bash
# Test prompt syntax and structure
cd apps/backend

# Validate prompt markdown
python -c "
import markdown
import sys

prompt_file = 'prompts/optimizer.md'
with open(prompt_file) as f:
    content = f.read()

try:
    markdown.markdown(content)
    print(f'✓ {prompt_file} is valid markdown')
except Exception as e:
    print(f'✗ {prompt_file} has errors: {e}')
    sys.exit(1)
"
```

---

## Best Practices

### Prompt Design

1. **Be Specific and Clear**
   ```markdown
   # ❌ Vague
   Write good code.

   # ✅ Specific
   Write Python code following PEP 8 guidelines with type hints and docstrings.
   ```

2. **Provide Examples**
   ```markdown
   ## Example Output

   Here's what a good response looks like:

   ```markdown
   ## Performance Report
   - Found 3 optimization opportunities
   - Estimated improvement: 40% faster
   ```
   ```

3. **Structure with Headings**
   ```markdown
   ## Phase 1: Analysis
   ## Phase 2: Planning
   ## Phase 3: Implementation
   ```

4. **Include Safety Rules**
   ```markdown
   ## Safety

   - ALWAYS run tests before committing
   - NEVER delete files without confirmation
   - ALWAYS backup before refactoring
   ```

### Agent Permissions

Only give agents the tools they need:

```python
# ❌ Too permissive
"optimizer": {
    "allowed_tools": ["*"]  # All tools
}

# ✅ Minimal permissions
"optimizer": {
    "allowed_tools": ["Read", "Grep"]  # Read-only access
}
```

### Thinking Tokens

Allocate thinking tokens based on task complexity:

```python
"planner": {
    "max_thinking_tokens": 20000  # Complex planning
},
"coder": {
    "max_thinking_tokens": None  # Unlimited for coding
},
"qa_reviewer": {
    "max_thinking_tokens": 16000  # Moderate for review
}
```

### Version Control

Track prompt changes:

```bash
# Commit prompt modifications
git add apps/backend/prompts/coder.md
git commit -m "docs: add TypeScript strict mode to coder prompt"
```

---

## Advanced Patterns

### Multi-Agent Workflows

Chain multiple agents together:

```python
def run_analysis_workflow(project_dir: str, spec_dir: str):
    """Run multi-agent analysis workflow."""

    # Agent 1: Security analysis
    security_response = run_agent_session(
        client=create_client(project_dir, spec_dir, agent_type="security"),
        agent_name="security_analyzer",
        starting_message="Analyze code for security vulnerabilities"
    )

    # Agent 2: Performance analysis
    perf_response = run_agent_session(
        client=create_client(project_dir, spec_dir, agent_type="optimizer"),
        agent_name="optimizer",
        starting_message=f"Optimize code, considering security issues: {security_response}"
    )

    # Agent 3: Generate combined report
    report_response = run_agent_session(
        client=create_client(project_dir, spec_dir, agent_type="reporter"),
        agent_name="reporter",
        starting_message=f"Generate report from:\nSecurity: {security_response}\nPerformance: {perf_response}"
    )

    return report_response
```

### Conditional Agent Execution

Run agents based on conditions:

```python
def smart_workflow(project_dir: str, spec_dir: str):
    """Run agents conditionally based on spec analysis."""

    # Check if spec involves database changes
    spec = load_spec(spec_dir)
    has_db_changes = "database" in spec.get("services", [])

    if has_db_changes:
        # Run database specialist agent
        run_db_specialist(project_dir, spec_dir)
    else:
        logger.info("No database changes, skipping DB specialist")

    # Always run QA
    run_qa_reviewer(project_dir, spec_dir)
```

### Agent Specialization

Create specialized versions of existing agents:

```bash
# Frontend-focused coder
apps/backend/prompts/coder_frontend.md

# Backend-focused coder
apps/backend/prompts/coder_backend.md

# Test-focused coder
apps/backend/prompts/coder_testing.md
```

Then route to the appropriate agent based on task type:

```python
def run_coder(project_dir: str, spec_dir: str):
    """Run specialized coder based on task."""

    spec = load_spec(spec_dir)
    services = spec.get("services", [])

    if all("frontend" in s for s in services):
        prompt_file = "coder_frontend.md"
    elif all("backend" in s for s in services):
        prompt_file = "coder_backend.md"
    else:
        prompt_file = "coder.md"  # Default

    run_agent_with_prompt(project_dir, spec_dir, prompt_file)
```

---

## Troubleshooting

### Agent Not Following Instructions

**Problem**: Agent ignores your custom prompt modifications.

**Solutions:**
1. Check prompt syntax - invalid markdown can cause issues
2. Ensure instructions are clear and unambiguous
3. Add examples to prompt
4. Increase thinking tokens to allow more reasoning
5. Test on simpler tasks first

### Agent Permission Errors

**Problem**: Agent can't access needed tools.

**Solutions:**
1. Check `AGENT_TOOL_PERMISSIONS` in `core/client.py`
2. Verify agent type is registered
3. Add required tools to allowed_tools list
4. Check if security rules block certain operations

### Poor Performance

**Problem**: Custom agent is slow or inefficient.

**Solutions:**
1. Reduce prompt length - focus on essentials
2. Add caching for repeated operations
3. Use parallel execution for independent tasks
4. Set appropriate `max_thinking_tokens`

---

## Examples

See the following for real-world examples:

- **Planner Agent**: `apps/backend/prompts/planner.md` + `apps/backend/agents/planner.py`
- **Coder Agent**: `apps/backend/prompts/coder.md` + `apps/backend/agents/coder.py`
- **QA Agents**: `apps/backend/prompts/qa_reviewer.md` and `qa_fixer.md`

---

## Related Documentation

- [Advanced Usage Guide](./ADVANCED-USAGE.md) - Agent customization overview
- [Spec Creation Pipeline](./SPEC-CREATION-PIPELINE.md) - Spec creation agents
- [Claude SDK Documentation](https://docs.anthropic.com/claude-sdk) - SDK reference
- [Agent System README](../apps/backend/agents/README.md) - Agent architecture

---

## Getting Help

- **[GitHub Issues](https://github.com/OBenner/Auto-Coding/issues)** - Report bugs
- **[GitHub Discussions](https://github.com/OBenner/Auto-Coding/discussions)** - Ask questions
