# Parallel Execution Feature

This document provides comprehensive documentation of Auto Code's parallel execution capabilities, covering subagent spawning, task distribution, and orchestration strategies.

## Overview

The parallel execution feature enables AI agents to spawn specialized subagents for concurrent work, accelerating implementation of independent tasks. The system uses the **Claude Agent SDK's Task tool** to manage parallel execution, with agents autonomously deciding when parallelism is beneficial.

**Key Features:**
- **Autonomous Decision-Making** - Agents decide when to spawn subagents based on task complexity
- **SDK-Managed Orchestration** - Claude Agent SDK handles parallel execution automatically
- **No CLI Flags** - No `--parallel` flag needed; parallelism is agent-driven
- **Intelligent Work Distribution** - Subagents handle independent tasks concurrently

**Architecture Location:** `apps/backend/agents/`, `apps/backend/core/client.py`

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Coder Agent Session                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Claude Agent SDK Task Tool                 │
│  (Manages subagent spawning and coordination)      │
└─────────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┬───────────────┬───────────────┐
            ▼               ▼               ▼               ▼
    ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
    │Subagent 1│  │Subagent 2│  │Subagent 3│  │Subagent N│
    │(testing) │  │(coding)  │  │(research)│  │(docs)   │
    └─────────┘  └─────────┘  └─────────┘  └─────────┘
            │               │               │               │
            └───────────────┴───────────────┴───────────────┘
                            │
                            ▼
                ┌─────────────────────────────────────┐
                │       Results Synthesis          │
                │  (Collected by SDK)            │
                └─────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────────────┐
                    │ Main Agent Continues  │
                    │ (with subagent results) │
                    └───────────────────────┘
```

### Parallelism Types

**1. Phase-Level Parallelism (Documentation Only)**

The planner agent documents potential parallelism in `implementation_plan.json`:

```json
{
  "summary": {
    "parallelism": {
      "max_parallel_phases": 2,
      "parallel_groups": [
        {
          "phases": ["phase-4-display", "phase-5-save"],
          "reason": "Both depend only on phase-3, different file sets"
        }
      ],
      "recommended_workers": 2,
      "speedup_estimate": "1.5x faster than sequential"
    }
  }
}
```

**Purpose:** Document which phases could theoretically run in parallel if they had:
- The same `depends_on` arrays (or compatible dependency sets)
- No overlapping `files_to_modify` or `files_to_create`
- Work in different services

**Note:** This is **documentation only** - phases execute sequentially by design for dependency safety. Actual parallelism happens at the subagent level.

**2. Subagent-Level Parallelism (Actual Implementation)**

Agents spawn subagents via the SDK `Task` tool for concurrent work:

```python
# Coder agent spawns subagents for independent tasks
client.query("Create unit tests while I update the documentation")
# SDK handles spawning multiple agents via Task tool
```

**When Agents Use Parallelism:**
- Independent subtasks that can run concurrently (e.g., testing multiple platforms)
- Background tasks that don't block main agent workflow
- Multi-file processing across different services
- Research and investigation tasks in parallel

**When Agents Avoid Parallelism:**
- Complex dependencies between tasks
- Sequential subtasks that must complete in order
- Resource-intensive operations that would conflict

---

## Implementation

### Agent-Managed Decision Making

**Key Principle:** Agents autonomously decide when to spawn subagents. No human configuration needed.

**Decision Factors:**
- **Task Independence** - Can subtasks run concurrently without blocking?
- **Complexity** - Multiple independent work items worth spawning subagents?
- **Efficiency** - Will parallelism reduce overall execution time?

### SDK Task Tool

**Module:** `claude_agent_sdk`

**Location:** `apps/backend/core/client.py` (via `create_client()`)

**Functionality:**
- Automatically spawns and manages subagent processes
- Collects results from all subagents
- Returns synthesized output to main agent
- Handles error propagation and timeout management

**Usage in Agent Prompts:**

```markdown
## SPAWNING SUBAGENTS

When appropriate, you can spawn specialized subagents using the Task tool:

- Use for: Independent tasks that can run concurrently
- Examples: Testing on multiple platforms, parallel file processing
- The SDK will handle spawning and result collection automatically
```

### Subagent Capabilities

Subagents inherit the main agent's context and tools:

**Available Tools:**
- `Read` - File reading
- `Grep` - Code search
- `Glob` - Pattern matching
- `Write` - File creation (if permitted)
- `Edit` - File modification (if permitted)
- `Bash` - Command execution (if permitted)

**Inherited Context:**
- Project directory restrictions
- Security sandbox
- MCP server integrations
- Environment variables

**Result Collection:**
- SDK automatically collects all subagent outputs
- Main agent receives synthesized results
- No manual coordination needed

---

## Phase Parallelism Analysis

### Parallel Group Detection

**Module:** `apps/backend/prompts/planner.md`

**Phase 4 of Planning:**

The planner agent analyzes the implementation plan to identify parallelism opportunities:

1. **Find parallel groups:** Phases with identical `depends_on` arrays
2. **Check file conflicts:** Ensure no overlapping `files_to_modify` or `files_to_create`
3. **Count max parallel workers:** Maximum parallelizable phases at any point

**Example:**

```json
{
  "phases": [
    {
      "id": "phase-3-backend",
      "depends_on": ["phase-1-setup"],
      "parallel_safe": true,
      "subtasks": [...]
    },
    {
      "id": "phase-4-frontend",
      "depends_on": ["phase-1-setup"],
      "parallel_safe": true,
      "subtasks": [...]
    },
    {
      "id": "phase-5-integration",
      "depends_on": ["phase-3-backend", "phase-4-frontend"],
      "parallel_safe": false,
      "subtasks": [...]
    }
  ]
}
```

**Analysis:**
- Phases 3 and 4 both depend on phase-1
- They have no overlapping files
- They can run in parallel (different services)
- Phase 5 must wait for both to complete

**Summary Output:**

```json
{
  "parallelism": {
    "max_parallel_phases": 2,
    "parallel_groups": [
      {
        "phases": ["phase-3-backend", "phase-4-frontend"],
        "reason": "Both depend only on phase-1, different file sets"
      }
    ],
    "recommended_workers": 2,
    "speedup_estimate": "1.5x faster than sequential"
  }
}
```

### Determining Recommended Workers

**Guidelines:**

| Workers | When to Use | Example |
|---------|---------------|----------|
| **1 worker** | Sequential phases, file conflicts, investigation workflows | Single service refactor |
| **2 workers** | 2 independent phases at some point | Backend + Frontend development |
| **3+ workers** | Large projects with 3+ independent phases | Multi-platform feature development |

**Conservative Default:** If unsure, recommend 1 worker. Parallel execution adds complexity.

---

## Key Modules Reference

### Agent Orchestration

**`apps/backend/agents/coder.py`** - Main autonomous agent loop
- Coordinates subtask execution
- Can spawn subagents via SDK Task tool
- Manages session lifecycle and recovery

**`apps/backend/agents/session.py`** - Session management
- Tracks conversation rounds
- Manages agent context across sessions
- Records tool calls and code references

**`apps/backend/agents/base.py`** - Shared agent infrastructure
- Common imports and constants
- Base patterns for all agents

### Client Configuration

**`apps/backend/core/client.py`** - Claude SDK client factory

**Function:** `create_client()`

**Parameters:**
```python
client = create_client(
    project_dir=project_dir,
    spec_dir=spec_dir,
    model=model,
    agent_type="coder",  # Determines tool permissions
    max_thinking_tokens=thinking_budget,
    agents={  # Optional subagent definitions
        "researcher": AgentDefinition(...),
        "tester": AgentDefinition(...)
    }
)
```

**Agent Types:**
- `planner` - Creates implementation plans
- `coder` - Implements subtasks (main loop)
- `qa_reviewer` - Validates acceptance criteria
- `qa_fixer` - Resolves QA issues
- `pr_orchestrator_parallel` - Orchestrates parallel specialist agents

### Progress Tracking

**`apps/backend/ui/statusline.py`** - Worker count display

**Method:** `update_workers(active, max_workers)`

**Functionality:**
- Updates `workers_active` field in `.auto-claude/status.json`
- Displays parallel execution status
- Shows: `[0/2 workers]` format in status bar

---

## Usage Examples

### Agent Spawning Subagents

**Scenario:** Coder agent needs to test changes on multiple platforms

**Agent Prompt (coder.md):**

```markdown
You need to verify the authentication feature works on:
1. Linux (backend tests)
2. Windows (frontend tests)
3. macOS (integration tests)

These are independent - spawn subagents for parallel testing.
```

**Agent Execution:**

```python
# Agent spawns subagents via Task tool
client.query("""
Test authentication on multiple platforms concurrently.
- Use Task tool to spawn 3 subagents (one per platform)
- Wait for all results before continuing
""")

# SDK automatically:
# - Spawns 3 subagent processes
# - Runs them concurrently
# - Collects all results
# - Returns to main agent
```

### Phase Parallelism Documentation

**Scenario:** Planner creates plan with potential parallel phases

**implementation_plan.json:**

```json
{
  "feature": "Cross-platform authentication",
  "workflow_type": "feature",
  "phases": [
    {
      "id": "phase-2-backend",
      "name": "Backend Implementation",
      "depends_on": ["phase-1-setup"],
      "parallel_safe": true,
      "subtasks": [...]
    },
    {
      "id": "phase-3-frontend",
      "name": "Frontend Implementation",
      "depends_on": ["phase-1-setup"],
      "parallel_safe": true,
      "subtasks": [...]
    }
  ]
}
```

**Analysis Output:**

```json
{
  "summary": {
    "parallelism": {
      "max_parallel_phases": 2,
      "parallel_groups": [
        {
          "phases": ["phase-2-backend", "phase-3-frontend"],
          "reason": "Both depend only on phase-1, work on different services"
        }
      ],
      "recommended_workers": 2,
      "speedup_estimate": "1.5x faster than sequential",
      "startup_command": "source auto-claude/.venv/bin/activate && python auto-claude/run.py --spec 001 --parallel 2"
    }
  }
}
```

**Note:** The `--parallel 2` in startup_command is for documentation only. Actual execution is agent-driven.

---

## Advanced Topics

### Extended Thinking with Subagents

**Main Agent:** No extended thinking (runs standard model)
**Subagents:** Inherit model setting (default or specified)

```python
# Main agent uses standard thinking
main_client = create_client(
    project_dir,
    spec_dir,
    model="sonnet",
    agent_type="coder",
    max_thinking_tokens=None  # No extended thinking
)

# Subagents inherit model setting
subagents = {
    "researcher": AgentDefinition(
        prompt=research_prompt,
        model="inherit"  # Uses same model as main agent
    )
}
```

### Cross-Platform Parallelism

**Use Case:** Testing on Windows, macOS, and Linux

**Agent Decision:**

```markdown
The authentication changes need verification on:
1. Windows (frontend components)
2. macOS (Electron app behavior)
3. Linux (backend deployment)

These are independent - spawn subagents for each platform.
```

**Benefits:**
- Reduces total test time from 15 minutes to 5 minutes
- Each subagent focuses on one platform
- Main agent synthesizes results

### Error Handling

**Subagent Failure:**

```python
# SDK propagates errors to main agent
try:
    result = await client.query(prompt)
except SubagentError as e:
    # Main agent handles error, retries, or escalates
    logger.error(f"Subagent failed: {e}")
```

**Main Agent Recovery:**

- Detects stuck subtasks (3 consecutive failures)
- Spawns recovery agent with alternative approach
- Can escalate to human if recovery fails

---

## Verification

### Manual Verification

**Verify parallel worker configuration is explained:**

1. **Phase-Level Analysis** documented in implementation_plan.json
2. **Subagent Spawning** documented in agent prompts
3. **SDK Task Tool** usage documented
4. **Progress tracking** via statusline

**Checklist:**
- [ ] Parallel group detection logic is clear
- [ ] Subagent spawning decision process is explained
- [ ] SDK orchestration is documented
- [ ] Worker count display is explained
- [ ] Use cases are provided with examples

---

## Best Practices

### When to Use Parallel Execution

**DO:**
- Let agents decide when parallelism is beneficial
- Use for independent tasks (testing, multi-platform, research)
- Document phase parallelism in implementation_plan.json
- Monitor subagent results via SDK synthesis

**DON'T:**
- Force parallelism via CLI flags (no `--parallel` flag exists)
- Manually configure worker counts
- Spawn subagents for tightly coupled tasks
- Expect parallelism without understanding agent decision-making

### Agent Prompt Guidelines

**For spawning subagents:**

```markdown
## SPAWNING SUBAGENTS

When appropriate, use the Task tool to spawn subagents:

**When to use:**
- Independent tasks that can run concurrently
- Different platforms or services
- Parallelizable research or investigation

**The SDK will:**
- Spawn subagents automatically
- Collect all results
- Return synthesized output to you

**You don't need to:**
- Manually coordinate subagents
- Collect individual results
- Manage process lifecycle
```

### Implementation Plan Considerations

**For planner agents documenting phase parallelism:**

1. **Analyze dependencies** - Find phases with identical `depends_on` arrays
2. **Check file conflicts** - No overlapping `files_to_modify` or `files_to_create`
3. **Document parallel groups** - List which phases can run together
4. **Recommend workers** - Based on max parallelizable phases
5. **Include startup command** - For documentation purposes only

---

## Troubleshooting

### Subagents Not Spawning

**Symptoms:** Task tool called but no subagents spawn

**Causes:**
1. **SDK not initialized** - Check `create_client()` includes `agents` parameter
2. **Agent definitions invalid** - Verify `AgentDefinition` structure
3. **Task tool not available** - Ensure SDK version supports subagents

**Solutions:**
- Verify SDK client initialization
- Check agent prompts for Task tool usage
- Review SDK documentation for subagent requirements

### Parallel Phases Execute Sequentially

**Symptoms:** Phases marked as `parallel_safe: true` run one at a time

**Expected Behavior:** This is correct - phase parallelism is documentation only

**For Actual Parallelism:** Use subagent spawning for concurrent execution

### Worker Count Display Issues

**Symptoms:** Status line shows incorrect worker count

**Debug:**
```bash
# Check status file
cat .auto-claude/status.json
```

**Verify:** `workers_active` matches expected number

---

## Performance Characteristics

### Parallel Execution Benefits

**Speedup Estimates:**

| Workers | Speedup | Use Case |
|---------|---------|-----------|
| 1 worker | 1.0x (baseline) | Sequential tasks |
| 2 workers | 1.5x-2.0x | Two independent phases |
| 3 workers | 2.0x-3.0x | Multi-platform development |

**Actual Performance:** Depends on task independence and resource constraints

### Bottlenecks

**Sequential by Design:**
- Subtask execution respects dependencies (order matters)
- QA validation runs after all subtasks complete
- Phase parallelism is for documentation only

**Parallelization Opportunities:**
- Independent subtasks within a phase
- Multi-platform testing
- Background research tasks
- Non-blocking file operations

---

## Related Documentation

- **[MULTI-AGENT-PIPELINE.md](MULTI-AGENT-PIPELINE.md)** - Complete agent system architecture
- **[apps/backend/prompts/planner.md](../../apps/backend/prompts/planner.md)** - Planner agent prompt with parallelism analysis
- **[apps/backend/prompts/coder.md](../../apps/backend/prompts/coder.md)** - Coder agent prompt with subagent spawning
- **[apps/backend/core/client.py](../../apps/backend/core/client.py)** - SDK client factory
- **[CLAUDE.md](../CLAUDE.md)** - Project architecture overview

---

## Summary

The parallel execution feature enables efficient AI-driven development through:

1. **Autonomous Decision-Making** - Agents decide when to spawn subagents based on task complexity
2. **SDK-Managed Orchestration** - Claude Agent SDK handles parallel execution via Task tool
3. **Documentation-Level Analysis** - Planner documents potential phase parallelism in implementation_plan.json
4. **Intelligent Work Distribution** - Subagents handle independent tasks concurrently
5. **No Manual Configuration** - No `--parallel` CLI flag needed; agent-driven parallelism

**Key Modules:**
- `apps/backend/agents/coder.py` - Main orchestration loop
- `apps/backend/core/client.py` - SDK client with subagent support
- `apps/backend/agents/session.py` - Session and conversation tracking
- `apps/backend/ui/statusline.py` - Worker count display

**To add parallel subagents:**
1. Define AgentDefinition with prompt, tools, and model
2. Pass to `create_client()` via `agents` parameter
3. Use Task tool in agent prompts when appropriate
4. Collect synthesized results from SDK

**For phase parallelism documentation:**
1. Analyze phase dependencies in planner prompt
2. Document parallel groups in implementation_plan.json summary
3. Include recommended_workers and speedup_estimate
4. Add startup_command example (for documentation only)
