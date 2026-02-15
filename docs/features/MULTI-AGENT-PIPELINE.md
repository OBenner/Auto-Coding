# Multi-Agent Pipeline

**Documentation Date:** 2026-02-12

## Pattern Overview

**Overall:** Dual-Phase Autonomous Development Pipeline with Dynamic Complexity Adaptation

**Key Characteristics:**
- Two-phase pipeline: Spec Creation (planning) → Implementation (building)
- Complexity-adaptive spec creation: SIMPLE (3 phases), STANDARD (6-7 phases), COMPLEX (8 phases)
- Agent-based execution: Each phase runs as a Claude Agent SDK session with phase-specific prompts
- Subtask-based implementation: Planner breaks work into atomic subtasks, Coder executes sequentially
- QA validation loop: Reviewer validates → Fixer resolves → repeats until approval
- Git worktree isolation: Each spec builds in isolated environment on `auto-code/{spec-name}` branch
- Memory system integration: Graphiti provides cross-session context and pattern suggestions

---

## Pipeline Architecture

The multi-agent pipeline consists of two major stages:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SPEC CREATION PHASE                         │
│  (SpecOrchestrator: apps/backend/spec/pipeline/orchestrator.py)│
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  IMPLEMENTATION PHASE                          │
│     (Coder Agent: apps/backend/agents/coder.py)              │
│  ┌────────────────┐    ┌────────────────┐    ┌─────────────┐ │
│  │ Planner Agent  │───▶│  Coder Agent   │───▶│   QA Loop    │ │
│  │ (plan creation)│    │ (subtask impl.) │    │ (validate+fix)│ │
│  └────────────────┘    └────────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Spec Creation Pipeline

**Orchestrator:** `apps/backend/spec/pipeline/orchestrator.py:SpecOrchestrator`

The spec creation pipeline uses **dynamic complexity assessment** to determine which phases to execute based on task complexity.

### Complexity Levels

| Complexity | Phases | Use Case |
|------------|---------|----------|
| **SIMPLE** | 3 phases (Discovery → Quick Spec → Validate) | Quick bug fixes, trivial changes |
| **STANDARD** | 6-7 phases (Discovery → Requirements → [Research] → Context → Spec → Plan → Validate) | Typical feature development |
| **COMPLEX** | 8 phases (Full pipeline with Research and Self-Critique) | Multi-service features, architectural changes |

### Phase Flow

```
Phase 1: Discovery
    ↓
Phase 2: Requirements
    ↓
Phase 3: Complexity Assessment (AI-based or heuristic)
    ↓
[Phase 4: Historical Context]  # Only if project has prior specs
    ↓
[Phase 5: Research]  # Only if complexity.research_enabled == True
    ↓
Phase 6: Context Gathering
    ↓
Phase 7: Spec Writing
    ↓
[Phase 8: Self-Critique]  # Only if complexity.self_critique_enabled == True
    ↓
Phase 9: Implementation Planning
    ↓
Phase 10: Validation
    ↓
Human Review Checkpoint
```

### Phase Details

| Phase | Purpose | Output | Agent Prompt |
|-------|---------|--------|-------------|
| **Discovery** | Analyze project structure, identify files involved | File list, stack detection | `prompts/spec_gatherer.md` |
| **Requirements** | Gather user requirements via interactive interview | `requirements.json` | `prompts/spec_gatherer.md` |
| **Complexity Assessment** | AI determines which phases to run | `complexity_assessment.json` | `prompts/complexity_assessor.md` |
| **Historical Context** | Review prior specs for patterns | Context summary | `prompts/spec_researcher.md` |
| **Research** | Validate external dependencies/APIs | Research findings | `prompts/spec_researcher.md` |
| **Context Gathering** | Collect codebase patterns, architecture docs | `context.json` | `prompts/spec_writer.md` |
| **Spec Writing** | Generate comprehensive specification | `spec.md` | `prompts/spec_writer.md` |
| **Self-Critique** | Review and refine spec using ultrathink | Refined `spec.md` | `prompts/spec_critic.md` |
| **Implementation Planning** | Create detailed implementation plan | `implementation_plan.json` | `prompts/planner.md` |
| **Validation** | Verify spec completeness and correctness | Validation report | `spec/validate_pkg/` |

### Key Abstractions

**SpecOrchestrator:**
- Location: `apps/backend/spec/pipeline/orchestrator.py`
- Purpose: Coordinates spec creation phases with dynamic phase selection
- Pattern: Orchestrator with complexity-based phase routing

**PhaseExecutor:**
- Location: `apps/backend/spec/phases/phases.py`
- Purpose: Executes individual spec creation phases
- Pattern: Phase runner with retry logic (MAX_RETRIES=3)

**AgentRunner:**
- Location: `apps/backend/spec/pipeline/agent_runner.py`
- Purpose: Creates Claude Agent SDK sessions for spec phases
- Pattern: Session factory with thinking budget management

**Conversation Compaction:**
- Location: `apps/backend/spec/compaction.py`
- Purpose: Summarizes completed phases to provide context to subsequent phases
- Pattern: Phase summarization with target word count (500 words per phase)

---

## Implementation Pipeline

**Orchestrator:** `apps/backend/agents/coder.py:run_autonomous_agent()`

The implementation pipeline uses **subtask-based execution** where the Planner agent breaks work into atomic subtasks, and the Coder agent executes them sequentially.

### Implementation Flow

```
1. Planner Agent (Session 1)
   ↓
   Reads spec.md → Creates implementation_plan.json
   ↓
   Breaks feature into subtasks (atomic, scoped to one service)
   ↓
   Each subtask: description, acceptance criteria, files to modify
   ↓

2. Coder Agent (Session 2-N)
   ↓
   Iterates through subtasks in order
   ↓
   For each subtask:
     - Runs Claude Agent SDK session with subtask context
     - Can spawn subagents (via Task tool) for parallel work
     - Commits changes after completion
     - Updates implementation_plan.json status
   ↓

3. QA Validation Loop
   ↓
   QA Reviewer Agent validates against acceptance criteria
   ↓
   If issues found: QA Fixer Agent resolves
   ↓
   Loop until approved or max iterations (50)
```

### Agent Types

| Agent | Purpose | Prompt | Session Type |
|-------|---------|--------|--------------|
| **Planner** | Create subtask-based implementation plan | `prompts/planner.md` | Single session (first) |
| **Coder** | Implement subtasks, spawn subagents as needed | `prompts/coder.md` | Multiple sessions (one per subtask) |
| **QA Reviewer** | Validate implementation against acceptance criteria | `prompts/qa_reviewer.md` | Single session |
| **QA Fixer** | Fix issues found by QA reviewer | `prompts/qa_fixer.md` | Multiple sessions (until approved) |
| **Coder Recovery** | Recover from stuck/failed subtasks | `prompts/coder_recovery.md` | On-demand (when stuck) |

### Subtask Structure

Each subtask in `implementation_plan.json` contains:

```json
{
  "subtask_id": "subtask-1-1",
  "title": "Create authentication service",
  "status": "pending",
  "phase": "Backend Authentication",
  "description": "Implement JWT authentication service",
  "acceptance_criteria": [
    "Users can authenticate with email/password",
    "JWT tokens are generated and validated",
    "Tokens expire after 24 hours"
  ],
  "files_to_create": [
    "apps/backend/services/auth_service.py"
  ],
  "files_to_modify": [
    "apps/backend/core/auth.py"
  ],
  "dependencies": [],
  "verification_steps": [
    "Run authentication tests",
    "Verify token generation"
  ]
}
```

### Key Abstractions

**run_autonomous_agent():**
- Location: `apps/backend/agents/coder.py`
- Purpose: Main orchestration loop for implementation
- Pattern: Iterative subtask execution with recovery support

**RecoveryManager:**
- Location: `apps/backend/agents/recovery.py`
- Purpose: Tracks agent sessions for resumption after interruption
- Pattern: Session state persistence with recovery checkpoints

**Subagent Spawning:**
- Mechanism: Coder agent uses Claude SDK `Task` tool to spawn subagents
- Decision: Agent autonomously decides when to use parallel work
- Use case: Independent tasks that can run concurrently (e.g., testing multiple platforms)

**QA Loop:**
- Location: `apps/backend/qa/loop.py`
- Purpose: Validation loop with reviewer → fixer cycle
- Pattern: Iterative improvement with max iteration limit (50)
- Escalation: Human review after max iterations or recurring issues

---

## Memory System Integration

**Memory Provider:** `apps/backend/integrations/graphiti/`

The multi-agent pipeline integrates with **Graphiti** (graph-based memory) for cross-session context:

### Memory Usage

| Pipeline Stage | Memory Usage | Purpose |
|--------------|--------------|---------|
| **Spec Creation** | Pattern suggestions | Recommend relevant codebase patterns for feature |
| **Planning** | Historical context | Access prior spec patterns and gotchas |
| **Implementation** | Session insights | Store discoveries, gotchas, patterns during build |
| **QA** | Recurring issues | Detect patterns in bugs to prevent future issues |

### Key Memory Operations

**Pattern Suggestions:**
- Query: "spec creation" or task description
- Returns: Relevant codebase patterns ranked by semantic similarity
- Used by: Spec writer, planner agents

**Session Insights:**
- Automatic extraction after each agent session
- Categories: Discoveries, Gotchas, Patterns, Optimizations
- Stored in: `.auto-claude/specs/XXX/graphiti/`

**Memory Queries:**
- `get_graphiti_context()` - Retrieve relevant context for session
- `get_pattern_suggestions()` - Get codebase patterns for feature
- `save_user_correction()` - Store human corrections for learning

---

## Agent Prompts

**Location:** `apps/backend/prompts/`

Each agent type has a dedicated system prompt that defines its role and behavior:

| Prompt | Agent Type | Key Instructions |
|--------|-----------|------------------|
| **planner.md** | Planner Agent | Deep codebase investigation, subtask creation (not tests), dependency ordering |
| **coder.md** | Coder Agent | Implement subtasks, spawn subagents for parallel work, follow patterns |
| **coder_recovery.md** | Recovery Agent | Detect stuck state, try alternative approaches, escalate if needed |
| **qa_reviewer.md** | QA Reviewer | Validate acceptance criteria, check for edge cases, E2E testing (Electron) |
| **qa_fixer.md** | QA Fixer | Fix reported issues, verify fixes, prevent regressions |
| **spec_gatherer.md** | Spec Gatherer | Interactive requirements gathering, file discovery |
| **spec_researcher.md** | Spec Researcher | Validate external APIs, dependencies, third-party services |
| **spec_writer.md** | Spec Writer | Generate comprehensive specs with acceptance criteria |
| **spec_critic.md** | Spec Critic | Self-critique using ultrathink, refine spec quality |
| **complexity_assessor.md** | Complexity Assessor | AI-based task complexity evaluation |

---

## Data Flow

### Spec Creation Data Flow

```
User Task (--task "Add user authentication")
    ↓
SpecOrchestrator.initialize()
    ↓
[Discovery Phase]
    → Finds: apps/backend/core/auth.py, apps/frontend/src/auth/
    → Detects: JWT library, OAuth integration
    ↓
[Requirements Phase]
    → Interactive interview
    → Output: requirements.json
    ↓
[Complexity Assessment]
    → AI analyzes task complexity
    → Output: complexity_assessment.json
    → Determines: Run 6 phases (STANDARD workflow)
    ↓
[Context Phase]
    → Loads project_index.json
    → Reads: ARCHITECTURE.md, similar features
    → Output: context.json
    ↓
[Spec Writing Phase]
    → Generates: spec.md
    → Uses pattern suggestions from Graphiti
    ↓
[Planning Phase]
    → Planner agent creates: implementation_plan.json
    → Subtasks: Auth service → API routes → Frontend login → Tests
    ↓
[Validation Phase]
    → Validates spec schema
    → Checks acceptance criteria are testable
    ↓
[Human Review Checkpoint]
    → User reviews and approves
    ↓
Output: Ready for implementation
```

### Implementation Data Flow

```
python run.py --spec 001
    ↓
run_autonomous_agent(spec_dir, project_dir)
    ↓
[Planner Session]
    → Reads: spec.md, requirements.json, context.json
    → Investigates codebase (find, grep, read patterns)
    → Creates: implementation_plan.json with 8 subtasks
    ↓
[Coder Loop - Subtask 1]
    → Session: "Implement authentication service"
    → Reads: auth patterns in codebase
    → Creates: apps/backend/services/auth_service.py
    → Tests: python -m pytest tests/test_auth.py
    → Commits: "auto-claude: subtask-1-1 - Create authentication service"
    → Updates: implementation_plan.json[subtask-1-1].status = "completed"
    ↓
[Coder Loop - Subtask 2-N]
    → Repeat for each subtask
    → Can spawn subagents for parallel work (agent decides)
    ↓
[All Subtasks Complete]
    → Emits phase: BUILD_COMPLETE
    ↓
[QA Loop - Iteration 1]
    → QA Reviewer validates acceptance criteria
    → Finds: Missing test for token expiration
    → Creates: QA_FIX_REQUEST.md
    → Status: REJECTED
    ↓
[QA Loop - Iteration 2]
    → QA Fixer resolves issues
    → Adds test for token expiration
    → Commits fix
    ↓
[QA Loop - Iteration 3]
    → QA Reviewer re-validates
    → All acceptance criteria met
    → Status: APPROVED
    ↓
Output: Build complete, ready for merge
```

---

## State Management

### Spec Creation State

| File | Purpose | Updated By |
|------|---------|-----------|
| `spec.md` | Feature specification with acceptance criteria | Spec Writer Agent |
| `requirements.json` | Structured user requirements | Spec Gatherer Agent |
| `context.json` | Codebase context and patterns | Context Phase |
| `implementation_plan.json` | Subtask-based implementation plan | Planner Agent |
| `complexity_assessment.json` | AI complexity evaluation | Complexity Assessor Agent |
| `complexity_report.md` | Human-readable complexity report | Spec Orchestrator |

### Implementation State

| File | Purpose | Updated By |
|------|---------|-----------|
| `implementation_plan.json` | Subtask tracking (status, commits, notes) | Coder Agent |
| `build-progress.txt` | Human-readable build progress | Coder Agent |
| `qa_report.md` | QA validation results | QA Reviewer Agent |
| `QA_FIX_REQUEST.md` | Issues to fix (when rejected) | QA Reviewer Agent |
| `task.log` | Structured event log for debugging | All agents |

### Session Recovery

**RecoveryManager** tracks:
- Current agent session ID
- Last completed subtask
- Token usage statistics
- Session interruption points

Stored in: `.auto-claude/specs/XXX/.recovery/`

---

## Security & Validation

### Command Security

**Three-layer defense:**
1. **OS Sandbox** - Bash command isolation
2. **Filesystem Permissions** - Operations restricted to project directory
3. **Command Allowlist** - Dynamic allowlist from project analysis

**Implementation:** `apps/backend/security/`

- `project_analyzer.py` - Detects project stack (Python, Node.js, etc.)
- `security.py` - Base + stack-specific command allowlists
- `tool_input_validator.py` - Validates Claude tool arguments
- `hooks/` - Pre-tool-use security hooks

### QA Validation

**Acceptance Criteria Validation:**
- All subtasks marked as completed
- All acceptance criteria verified (manual or automated)
- No console errors (browser, terminal)
- No security vulnerabilities (secrets scan, dependency check)
- Cross-platform compatibility (Windows, macOS, Linux)

**E2E Testing (Electron Apps):**
- QA agents can use Electron MCP server for automated testing
- `mcp__electron__take_screenshot` - Visual verification
- `mcp__electron__send_command_to_electron` - UI interaction
- `mcp__electron__read_electron_logs` - Console log inspection

---

## Error Handling

### Spec Creation Errors

| Error Type | Handling |
|-----------|----------|
| **Phase failure** | Retry up to MAX_RETRIES (3) with exponential backoff |
| **Agent session error** | Log to task.log, continue to next phase if non-critical |
| **Validation error** | Report errors, halt pipeline for human review |
| **User interrupt** | Graceful shutdown, save partial state for recovery |

### Implementation Errors

| Error Type | Handling |
|-----------|----------|
| **Subtask failure** | Coder Recovery Agent attempts alternative approach |
| **Stuck subtask** | Recovery escalation after MAX_STUCK_COUNT (3) |
| **QA rejection** | QA Fixer loop (max 50 iterations) |
| **Max QA iterations** | Escalate to human review with recurring issue summary |
| **Git conflict** | Abort with instructions to resolve manually |

### Recovery Patterns

**Session Resumption:**
```python
# RecoveryManager restores state
recovery_manager = RecoveryManager(spec_dir, project_dir)
last_session = recovery_manager.get_last_session()
if last_session and not last_session.completed:
    # Resume from last checkpoint
    session = client.resume_session(last_session.id)
```

**Stuck Subtask Detection:**
```python
# After 3 consecutive failures on same subtask
if consecutive_failures >= MAX_STUCK_COUNT:
    # Spawn coder recovery agent
    agent = spawn_recovery_agent(subtask_id)
    agent.try_alternative_approach()
```

---

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `GRAPHITI_ENABLED` | Enable Graphiti memory system | `true` |
| `LINEAR_ENABLED` | Enable Linear task integration | `false` |
| `ELECTRON_MCP_ENABLED` | Enable Electron E2E testing | `false` |
| `PROJECT_DIR` | Project root directory (auto-detected) | CWD |
| `ANTHROPIC_API_KEY` | Claude API authentication | Required |

### Phase Configuration

**Thinking Budgets:** `apps/backend/phase_config.py`

| Phase | Default Thinking Budget |
|-------|----------------------|
| Spec creation (all phases) | Medium (32K tokens) |
| Planner | High (64K tokens) |
| Coder | None (no extended thinking) |
| QA Reviewer | High (64K tokens) |
| QA Fixer | Medium (32K tokens) |

**Model Selection:**
- Resolved via API Profile (if configured)
- Fallback to hardcoded shorthands (sonnet, haiku, opus)
- Per-phase model override available

---

## Performance Characteristics

### Spec Creation Performance

| Metric | Typical Value |
|--------|--------------|
| SIMPLE spec (3 phases) | 2-3 minutes |
| STANDARD spec (6-7 phases) | 5-8 minutes |
| COMPLEX spec (8 phases) | 10-15 minutes |
| Phase summarization | +30 seconds per phase |

### Implementation Performance

| Metric | Typical Value |
|--------|--------------|
| Subtask implementation | 2-10 minutes (varies by complexity) |
| QA iteration | 1-5 minutes |
| Full build (10 subtasks) | 30-60 minutes |
| QA fixer loop (2-3 iterations) | +5-15 minutes |

### Scalability

**Parallelization:**
- Subagent spawning for independent tasks
- Multi-platform testing via subagents
- Graphiti memory queries are cached

**Bottlenecks:**
- Sequential subtask execution (by design for dependency management)
- QA validation loop (can require multiple iterations)
- Extended thinking phases (high thinking budget = longer response time)

---

## Monitoring & Observability

### Logging

**Task Logger:** `apps/backend/task_logger.py`

- Structured event log: `task.log`
- Log levels: INFO, WARNING, ERROR, DEBUG
- Phases: PLANNING, IMPLEMENTATION, QA, RECOVERY
- Entry types: PHASE_START, PHASE_END, SUBTASK_COMPLETE, TOOL_USE, ERROR

**Event Emission:** `apps/backend/phase_event.py`

- Emits events to frontend for real-time progress
- Events: PHASE_START, PHASE_COMPLETE, SUBTASK_START, SUBTASK_COMPLETE, BUILD_COMPLETE, QA_START, QA_COMPLETE, ERROR

### Progress Tracking

**build-progress.txt:**
Human-readable progress summary:
```
Build Progress: 3/10 subtasks completed (30%)

Completed:
  ✓ subtask-1-1: Create authentication service
  ✓ subtask-1-2: Implement login API endpoint
  ✓ subtask-1-3: Create JWT token management

In Progress:
  → subtask-2-1: Build login form UI

Pending:
  ○ subtask-2-2: Connect form to API
  ○ subtask-2-3: Implement error handling
  ...
```

**implementation_plan.json:**
Machine-readable subtask status:
```json
{
  "subtasks": [
    {
      "subtask_id": "subtask-1-1",
      "status": "completed",
      "commit_hash": "abc123",
      "completed_at": "2026-02-12T10:30:00Z"
    }
  ]
}
```

---

## Integration Points

### Linear Integration (Optional)

**Location:** `apps/backend/linear_updater.py`

When enabled, creates and updates Linear tasks:
- Spec creation: Creates task with spec name
- Implementation start: Updates status to "In Progress"
- QA approval: Updates status to "Done"
- Build failure: Updates status to "Cancelled" with error notes

### GitHub Integration (Optional)

**Location:** `apps/backend/runners/github/`

Automates GitHub Issues and PRs:
- Create issue from spec
- Create PR when build approved
- Link PR to issue

### Electron MCP Integration (E2E Testing)

**Location:** `apps/frontend/src/main/mcp/electron/`

Allows QA agents to interact with running Electron app:
- Take screenshots
- Click buttons, fill forms
- Navigate routes
- Read console logs

**Prerequisites:**
- `ELECTRON_MCP_ENABLED=true` in `.env`
- App running with `--remote-debugging-port=9222`
- Agent type: `qa_reviewer` or `qa_fixer`

---

## Best Practices

### Spec Creation

**DO:**
- Let AI assess complexity (don't override unless necessary)
- Run research phase for external dependencies
- Review generated spec before approval
- Keep acceptance criteria testable and specific
- Use pattern suggestions from Graphiti

**DON'T:**
- Skip complexity assessment for complex tasks
- Leave placeholders in spec.md
- Make acceptance criteria vague ("should work properly")
- Override to SIMPLE workflow for multi-service features

### Implementation

**DO:**
- Let planner create subtasks (don't manually edit implementation_plan.json)
- Follow codebase patterns found during investigation
- Commit after each subtask completion
- Use recovery agent when stuck
- Run QA validation even if you think it's ready

**DON'T:**
- Implement multiple subtasks in one session
- Skip subtasks or change order
- Ignore QA feedback
- Commit without testing
- Manually mark subtasks as completed

### QA

**DO:**
- Be thorough (you're the last line of defense)
- Test edge cases, not just happy path
- Use E2E testing for frontend changes
- Verify all acceptance criteria
- Check for security vulnerabilities

**DON'T:**
- Approve without full validation
- Ignore console errors
- Skip regression testing
- Assume code works without verification

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| **Spec creation stuck in phase** | Agent not responding to tool calls | Check Claude API status, resume with `--resume` |
| **Implementation plan has no subtasks** | Planner didn't break down task | Check spec.md clarity, re-run planner |
| **Subtask marked completed but not working** | Coder agent skipped verification | Run QA manually, report issue |
| **QA loop exceeds max iterations** | Recurring issue or bug | Escalate to human review |
| **Recovery fails to resume** | Recovery state corrupted | Delete `.recovery/` folder, start fresh |
| **Memory system returns no patterns** | Graphiti not initialized | Check `GRAPHITI_ENABLED=true` |
| **Electron MCP not available** | App not running or port mismatch | Start app with `--remote-debugging-port=9222` |

---

## References

- **Architecture Documentation:** [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
- **Spec Creation:** `apps/backend/spec/pipeline/orchestrator.py` - Spec orchestrator implementation
- **Implementation:** `apps/backend/agents/coder.py` - Coder agent orchestration
- **QA Loop:** `apps/backend/qa/loop.py` - QA validation loop
- **Memory System:** `apps/backend/integrations/graphiti/` - Graphiti memory integration
- **Agent Prompts:** `apps/backend/prompts/` - System prompts for all agent types
- **Security:** `apps/backend/security/` - Command validation and allowlists

---

*Documentation generated: 2026-02-12*
