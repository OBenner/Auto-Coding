# Spec Creation Pipeline Architecture

This document provides comprehensive documentation of Auto Code's spec creation system, covering the multi-phase pipeline, complexity assessment, phase compaction, validation strategy, and integration guides.

## Overview

The spec creation pipeline is a sophisticated multi-phase system that generates detailed specifications for software features before implementation begins. It adapts dynamically based on task complexity, running anywhere from **3 phases (SIMPLE)** to **8 phases (COMPLEX)**.

**Key Features:**
- **Dynamic Complexity Assessment** - AI + heuristic analysis determines which phases to run
- **Adaptive Pipeline** - 3-8 phases based on complexity (SIMPLE/STANDARD/COMPLEX)
- **Phase Compaction** - Automatic summarization of phase outputs for token efficiency
- **Memory Integration** - Optional Graphiti knowledge graph for cross-session context
- **Multi-Layered Validation** - Ensures spec quality before implementation begins

**Architecture Location:** `apps/backend/spec/`

---

## Pipeline Architecture

### High-Level Flow

```
User Input → Complexity Assessment → Dynamic Phase Selection → Phase Execution → Validation → Implementation Plan
```

### Complexity Tiers

The pipeline adapts based on task complexity:

| Complexity | Phases | Files | Services | Use Case |
|------------|--------|-------|----------|----------|
| **SIMPLE** | 3 | 1-2 | 1 | Typo fixes, color changes, simple bugs |
| **STANDARD** | 6-7 | 3-10 | 1-2 | New features, API endpoints, refactors |
| **COMPLEX** | 8 | 10+ | 2+ | Integrations, infrastructure, greenfield features |

### Phase Sequences

**SIMPLE (3 phases):**
```
discovery → historical_context → quick_spec → validation
```

**STANDARD (6 phases):**
```
discovery → historical_context → requirements → context → spec_writing → planning → validation
```

**STANDARD + Research (7 phases):**
```
discovery → historical_context → requirements → research → context → spec_writing → planning → validation
```

**COMPLEX (8 phases):**
```
discovery → historical_context → requirements → research → context → spec_writing → self_critique → planning → validation
```

---

## Complexity Assessment

**Module:** `spec/complexity.py`

The complexity assessment system uses a two-tier approach:

### 1. AI-Based Assessment

The primary method uses an AI agent (`complexity_assessor.md`) to analyze:
- **Scope Analysis** - Estimated files, services, and cross-cutting concerns
- **Integration Analysis** - External services, new dependencies, research needs
- **Infrastructure Analysis** - Docker, database, config changes
- **Knowledge Analysis** - Existing patterns vs. unfamiliar tech
- **Risk Analysis** - Security, breakage potential, validation depth

**Output:** `complexity_assessment.json`

```json
{
  "complexity": "standard",
  "workflow_type": "feature",
  "confidence": 0.85,
  "reasoning": "New API endpoint following existing patterns...",
  "analysis": {
    "scope": { "estimated_files": 4, "estimated_services": 1 },
    "integrations": { "external_services": [], "research_needed": false },
    "infrastructure": { "docker_changes": false, "database_changes": false }
  },
  "recommended_phases": ["discovery", "requirements", "context", ...],
  "flags": {
    "needs_research": false,
    "needs_self_critique": false
  }
}
```

### 2. Heuristic Fallback

If AI assessment fails, the system falls back to keyword-based heuristics:

**Simple Keywords:** fix, typo, update, change, style, color, button
**Complex Keywords:** integrate, api, database, docker, authentication, microservice
**Multi-Service Keywords:** backend, frontend, worker, service

**Decision Logic:**
```python
if estimated_files <= 2 and estimated_services == 1 and len(integrations) == 0:
    return SIMPLE
elif len(integrations) >= 2 or infra_changes or estimated_services >= 3:
    return COMPLEX
else:
    return STANDARD
```

### Validation Recommendations

The complexity assessment also determines validation depth for the QA phase:

| Risk Level | When Used | Test Types |
|------------|-----------|------------|
| **TRIVIAL** | Docs-only, whitespace | Skip validation |
| **LOW** | Single service, <5 files | Unit tests only |
| **MEDIUM** | Multiple files, API changes | Unit + Integration |
| **HIGH** | DB changes, auth/security | Unit + Integration + E2E + Security |
| **CRITICAL** | Payments, data deletion | All + Manual review + Staging |

---

## Phase Compaction (Token Efficiency)

**Module:** `spec/compaction.py`

As the pipeline progresses through phases, outputs accumulate. Phase compaction summarizes completed phases to maintain context while reducing token usage.

### How It Works

1. **After each phase completes**, the orchestrator calls `gather_phase_outputs()`
2. **Output files are read** (e.g., `requirements.json`, `spec.md`, `context.json`)
3. **AI summarization** (using Sonnet for cost efficiency) distills key findings to ~500 words
4. **Summaries are stored** in `_phase_summaries` dict on the orchestrator
5. **Subsequent phases receive** formatted summaries in their context via `format_phase_summaries()`

### Example Summarization

**Input** (2500 words from requirements phase):
```
User wants to add authentication with OAuth...
[Full requirements.json + discovery notes + user interaction transcript]
```

**Output** (500 words):
```
- User requirements: OAuth authentication with Google/GitHub providers
- Services affected: backend (auth routes), frontend (login UI)
- Key constraint: Must support existing session-based auth during migration
- Acceptance criteria: Users can log in with OAuth, existing sessions preserved
```

### Token Savings

Without compaction: ~10,000 tokens per phase × 8 phases = 80,000 tokens
With compaction: ~2,000 tokens per summary × 7 phases = 14,000 tokens
**Savings: ~80% reduction in accumulated context tokens**

---

## Phase Architecture

**Module:** `spec/phases/` (modular package using mixin pattern)

### Mixin Structure

The phase system uses the **Mixin Pattern** to separate concerns:

```
PhaseExecutor (main class)
├── DiscoveryPhaseMixin
│   ├── phase_discovery()
│   └── phase_context()
├── RequirementsPhaseMixin
│   ├── phase_historical_context()
│   ├── phase_requirements()
│   └── phase_research()
├── SpecPhaseMixin
│   ├── phase_quick_spec()
│   ├── phase_spec_writing()
│   └── phase_self_critique()
└── PlanningPhaseMixin
    ├── phase_planning()
    └── phase_validation()
```

### Phase Descriptions

| Phase | Purpose | Outputs | When Used |
|-------|---------|---------|-----------|
| **discovery** | Analyze project structure, find relevant files | `context.json` | Always (first phase) |
| **historical_context** | Query Graphiti knowledge graph for past insights | In-memory context | Always (if Graphiti enabled) |
| **requirements** | Interactive/automated requirements gathering | `requirements.json` | STANDARD, COMPLEX |
| **research** | Validate external integrations (docs, APIs) | `research.json` | COMPLEX, STANDARD+flag |
| **context** | Discover relevant files for implementation | `context.json` (updated) | STANDARD, COMPLEX |
| **quick_spec** | Generate minimal spec.md for simple tasks | `spec.md` | SIMPLE |
| **spec_writing** | Create comprehensive spec.md document | `spec.md` | STANDARD, COMPLEX |
| **self_critique** | AI-powered spec review using ultrathink | `critique_notes.md` | COMPLEX |
| **planning** | Generate implementation plan with subtasks | `implementation_plan.json` | Always (except SIMPLE) |
| **validation** | Multi-layered validation with auto-fix | Validation reports | Always (final phase) |

### Phase Execution Pattern

Each phase follows this pattern:

```python
async def phase_example(self) -> PhaseResult:
    """Execute example phase."""
    try:
        # 1. Log phase start
        self.task_logger.log("Starting phase...", LogEntryType.INFO)

        # 2. Run agent with prompt
        success, output = await self.run_agent_fn(
            "phase_prompt.md",
            additional_context="...",
            phase_name="example"
        )

        # 3. Validate outputs
        if not success or not output_file.exists():
            return PhaseResult("example", False, [], ["Error..."], retries)

        # 4. Return result
        return PhaseResult("example", True, [str(output_file)], [], 0)

    except Exception as e:
        return PhaseResult("example", False, [], [str(e)], 0)
```

---

## Orchestration

**Module:** `spec/pipeline/orchestrator.py`

The `SpecOrchestrator` class coordinates the entire spec creation process.

### Key Responsibilities

1. **Project Index Refresh** - Smart caching with dependency file tracking
2. **Spec Directory Creation** - Thread-safe spec numbering with locking
3. **Complexity Assessment** - Run AI or heuristic analysis
4. **Phase Selection** - Determine which phases to execute
5. **Phase Execution** - Run phases with compaction and error handling
6. **Human Review** - Checkpoint before implementation begins

### Initialization

```python
orchestrator = SpecOrchestrator(
    project_dir=Path("/path/to/project"),
    task_description="Add user authentication",
    model="sonnet",  # Resolved via API Profile
    thinking_level="medium",  # none/low/medium/high/ultrathink
    complexity_override=None,  # Force specific complexity
    use_ai_assessment=True  # Use AI vs heuristics
)
```

### Execution Flow

```python
success = await orchestrator.run(
    interactive=True,      # Interactive requirements gathering
    auto_approve=False     # Skip human review checkpoint
)
```

**Orchestrator Flow:**
```
1. Refresh project index (if dependencies changed)
2. Create PhaseExecutor with all mixins
3. Run Phase 1: Discovery
   → Store phase summary (compaction)
4. Run Phase 2: Requirements
   → Store phase summary (compaction)
   → Rename spec dir with better name
5. Run Complexity Assessment
   → Determine remaining phases
6. Run remaining phases dynamically
   → Store summaries after each phase
   → Inject prior summaries into subsequent phases
7. Print completion summary
8. Run human review checkpoint
9. Return success/failure
```

---

## Agent Runner

**Module:** `spec/pipeline/agent_runner.py`

The `AgentRunner` manages AI agent execution with logging and tool tracking.

### Responsibilities

1. **Client Creation** - Create Claude SDK client with security and MCP integration
2. **Prompt Loading** - Load prompt files from `apps/backend/prompts/`
3. **Context Injection** - Add spec dir, project dir, prior phase summaries
4. **Stream Processing** - Process agent response stream (text, tool calls, results)
5. **Logging** - Log all agent activity to task logger

### Usage Pattern

```python
runner = AgentRunner(
    project_dir=project_dir,
    spec_dir=spec_dir,
    model="sonnet",
    task_logger=logger
)

success, output = await runner.run_agent(
    "spec_writer.md",  # Prompt file
    additional_context="...",
    interactive=False,
    thinking_budget=5000,  # Extended thinking tokens
    prior_phase_summaries="..."  # Compacted context
)
```

### Tool Tracking

The runner tracks all tool calls made by the agent:

```python
# Tool start
[Tool: Read] file_path: apps/backend/auth.py

# Tool end (success)
✓ Read completed (1234 chars)

# Tool end (error)
✗ Edit failed: old_string not found
```

---

## Validation System

**Module:** `spec/validate_pkg/`

Multi-layered validation ensures spec quality before implementation.

### Validation Structure

```
spec/validate_pkg/
├── spec_validator.py      # Main orchestrator
├── models.py              # ValidationResult dataclass
├── schemas.py             # JSON schema definitions
├── auto_fix.py            # AI-powered auto-fix
└── validators/
    ├── prereqs.py         # Prerequisites validator
    ├── context.py         # Context.json validator
    ├── spec_document.py   # Spec.md validator
    └── plan.py            # Implementation plan validator
```

### Validation Checkpoints

**1. Prerequisites Validator**
- Checks: `requirements.json` exists and has required fields
- Auto-fix: ✅ Can generate missing requirements via AI

**2. Context Validator**
- Checks: `context.json` exists with valid structure
- Auto-fix: ✅ Can regenerate context

**3. Spec Document Validator**
- Checks: `spec.md` exists with required sections (Overview, Rationale, Acceptance Criteria)
- Auto-fix: ✅ Can regenerate spec sections

**4. Implementation Plan Validator**
- Checks: `implementation_plan.json` exists with valid schema
- Validates: Services, phases, subtasks structure
- Auto-fix: ❌ Plan is regenerated by planner agent

### Auto-Fix Strategy

When validation fails:
1. **First attempt**: Auto-fix with AI (if available for that checkpoint)
2. **Second attempt**: Return detailed errors for manual fix
3. **Max retries**: 3 attempts before failing the phase

```python
validator = SpecValidator(spec_dir)
results = validator.validate_all()

for result in results:
    if not result.is_valid():
        # Auto-fix will be attempted
        fixed_result = await auto_fix_checkpoint(result, spec_dir)
```

---

## Key Modules Reference

### `spec/complexity.py`

**Classes:**
- `Complexity(Enum)` - SIMPLE, STANDARD, COMPLEX
- `ComplexityAssessment` - Assessment result with phases and flags
- `ComplexityAnalyzer` - Heuristic-based analyzer

**Functions:**
- `run_ai_complexity_assessment()` - Run AI agent to assess complexity
- `save_assessment()` - Save assessment to JSON

**Usage:**
```python
from spec.complexity import ComplexityAnalyzer, run_ai_complexity_assessment

# Heuristic assessment
analyzer = ComplexityAnalyzer(project_index)
assessment = analyzer.analyze("Add user authentication")

# AI assessment
assessment = await run_ai_complexity_assessment(
    spec_dir, task_description, run_agent_fn
)

# Get phases to run
phases = assessment.phases_to_run()
# ['discovery', 'requirements', 'context', 'spec_writing', 'planning', 'validation']
```

### `spec/compaction.py`

**Functions:**
- `summarize_phase_output()` - Summarize phase output to ~500 words
- `format_phase_summaries()` - Format summaries for agent context
- `gather_phase_outputs()` - Collect output files from a phase

**Usage:**
```python
from spec.compaction import summarize_phase_output, format_phase_summaries

# After phase completes
phase_output = gather_phase_outputs(spec_dir, "requirements")
summary = await summarize_phase_output("requirements", phase_output)
summaries["requirements"] = summary

# Before next phase
formatted = format_phase_summaries(summaries)
# Pass to agent as additional_context
```

### `spec/phases/executor.py`

**Class:** `PhaseExecutor` (combines all mixins)

**Methods:**
- `phase_discovery()` - Project structure analysis
- `phase_historical_context()` - Graphiti memory integration
- `phase_requirements()` - Requirements gathering
- `phase_research()` - External integration validation
- `phase_context()` - Relevant file discovery
- `phase_quick_spec()` - Simple spec generation
- `phase_spec_writing()` - Full spec.md creation
- `phase_self_critique()` - AI-powered spec review
- `phase_planning()` - Implementation plan generation
- `phase_validation()` - Multi-layered validation

**Usage:**
```python
executor = PhaseExecutor(
    project_dir=project_dir,
    spec_dir=spec_dir,
    task_description="Add auth",
    spec_validator=validator,
    run_agent_fn=run_agent,
    task_logger=logger,
    ui_module=ui
)

result = await executor.phase_requirements(interactive=True)
if result.success:
    print(f"Created: {result.output_files}")
else:
    print(f"Errors: {result.errors}")
```

### `spec/pipeline/orchestrator.py`

**Class:** `SpecOrchestrator`

**Key Methods:**
- `__init__()` - Initialize with project dir and config
- `run()` - Execute full spec creation pipeline
- `_run_agent()` - Run agent with thinking budget and compaction
- `_store_phase_summary()` - Summarize and store phase output
- `_ensure_fresh_project_index()` - Smart cache refresh

**Usage:**
```python
orchestrator = SpecOrchestrator(
    project_dir=project_dir,
    task_description="Add authentication",
    model="sonnet",
    thinking_level="medium",
    use_ai_assessment=True
)

success = await orchestrator.run(interactive=True, auto_approve=False)
```

### `spec/pipeline/agent_runner.py`

**Class:** `AgentRunner`

**Methods:**
- `run_agent()` - Execute agent with prompt and context

**Usage:**
```python
runner = AgentRunner(project_dir, spec_dir, "sonnet", logger)
success, output = await runner.run_agent(
    "spec_writer.md",
    additional_context="...",
    thinking_budget=5000,
    prior_phase_summaries="..."
)
```

### `spec/validate_pkg/spec_validator.py`

**Class:** `SpecValidator`

**Methods:**
- `validate_all()` - Run all validations
- `validate_prereqs()` - Check requirements.json
- `validate_context()` - Check context.json
- `validate_spec_document()` - Check spec.md
- `validate_implementation_plan()` - Check implementation_plan.json

**Usage:**
```python
validator = SpecValidator(spec_dir)
results = validator.validate_all()

for result in results:
    if not result.is_valid():
        print(f"Checkpoint '{result.checkpoint}' failed:")
        for error in result.errors:
            print(f"  - {error}")
```

---

## Integration Guide: Adding New Phases

Follow this guide to add a new phase to the pipeline.

### Step 1: Create Phase Method

Add the phase method to the appropriate mixin in `spec/phases/`:

```python
# spec/phases/my_category_phases.py

class MyCategoryPhaseMixin:
    """Mixin for my category phases."""

    async def phase_my_new_phase(self) -> PhaseResult:
        """Execute my new phase.

        Returns:
            PhaseResult with success status and output files
        """
        output_file = self.spec_dir / "my_output.json"

        try:
            self.ui.print_status("Running my new phase...", "progress")

            # Run agent with custom prompt
            success, output = await self.run_agent_fn(
                "my_new_phase.md",
                additional_context=f"Output file: {output_file}",
                phase_name="my_new_phase"
            )

            # Validate output
            if not success or not output_file.exists():
                return PhaseResult(
                    "my_new_phase",
                    False,
                    [],
                    ["Phase failed or output file not created"],
                    0
                )

            self.ui.print_status("My new phase complete", "success")
            return PhaseResult(
                "my_new_phase",
                True,
                [str(output_file)],
                [],
                0
            )

        except Exception as e:
            return PhaseResult("my_new_phase", False, [], [str(e)], 0)
```

### Step 2: Add to PhaseExecutor

Include your mixin in `spec/phases/executor.py`:

```python
from .my_category_phases import MyCategoryPhaseMixin

class PhaseExecutor(
    DiscoveryPhaseMixin,
    RequirementsPhaseMixin,
    SpecPhaseMixin,
    PlanningPhaseMixin,
    MyCategoryPhaseMixin,  # Add your mixin
):
    """..."""
```

### Step 3: Create Agent Prompt

Create the prompt file in `apps/backend/prompts/`:

```markdown
<!-- apps/backend/prompts/my_new_phase.md -->

# My New Phase Agent

You are the My New Phase agent in the spec creation pipeline.

## Your Task

[Describe what this phase should accomplish]

## Input Files

- `requirements.json` - User requirements
- `context.json` - Project context

## Output

Create `my_output.json` with the following structure:

```json
{
  "my_field": "value",
  "created_at": "ISO timestamp"
}
```

## Instructions

1. Read input files
2. Process information
3. Create output file
4. Validate output
```

### Step 4: Update Complexity Assessment

Add the phase to appropriate complexity tiers in `spec/complexity.py`:

```python
def phases_to_run(self) -> list[str]:
    """Return list of phase names to run based on complexity."""
    if self.complexity == Complexity.SIMPLE:
        return ["discovery", "historical_context", "quick_spec", "validation"]
    elif self.complexity == Complexity.STANDARD:
        phases = ["discovery", "historical_context", "requirements"]
        if self.needs_research:
            phases.append("research")
        phases.extend(["context", "my_new_phase", "spec_writing", "planning", "validation"])
        return phases
    else:  # COMPLEX
        return [
            "discovery",
            "historical_context",
            "requirements",
            "research",
            "context",
            "my_new_phase",  # Add here
            "spec_writing",
            "self_critique",
            "planning",
            "validation",
        ]
```

### Step 5: Add Phase Display Info

Update `spec/pipeline/models.py` with display name and icon:

```python
PHASE_DISPLAY = {
    "discovery": ("PROJECT DISCOVERY", Icons.SEARCH),
    "historical_context": ("HISTORICAL CONTEXT", Icons.BRAIN),
    # ... other phases ...
    "my_new_phase": ("MY NEW PHASE", Icons.GEAR),
}
```

### Step 6: Add to Orchestrator

Register the phase in `spec/pipeline/orchestrator.py`:

```python
# Map of all available phases
all_phases = {
    "historical_context": phase_executor.phase_historical_context,
    "research": phase_executor.phase_research,
    "context": phase_executor.phase_context,
    "my_new_phase": phase_executor.phase_my_new_phase,  # Add here
    "spec_writing": phase_executor.phase_spec_writing,
    # ...
}
```

### Step 7: Add Compaction Support (Optional)

If your phase creates substantial output, add it to `spec/compaction.py`:

```python
phase_outputs: dict[str, list[str]] = {
    "discovery": ["context.json"],
    "requirements": ["requirements.json"],
    "my_new_phase": ["my_output.json"],  # Add here
    # ...
}
```

### Step 8: Add Validation (Optional)

If your phase output needs validation, create a validator in `spec/validate_pkg/validators/`:

```python
# spec/validate_pkg/validators/my_output_validator.py

from pathlib import Path
from ..models import ValidationResult

class MyOutputValidator:
    """Validates my_output.json structure."""

    def __init__(self, spec_dir: Path):
        self.spec_dir = spec_dir
        self.output_file = spec_dir / "my_output.json"

    def validate(self) -> ValidationResult:
        """Validate my_output.json."""
        if not self.output_file.exists():
            return ValidationResult(
                checkpoint="my_output",
                is_valid=False,
                errors=["my_output.json not found"]
            )

        # Add more validation logic here

        return ValidationResult(
            checkpoint="my_output",
            is_valid=True,
            errors=[]
        )
```

Add to `SpecValidator` in `spec/validate_pkg/spec_validator.py`:

```python
class SpecValidator:
    def __init__(self, spec_dir: Path):
        # ...
        self._my_output_validator = MyOutputValidator(self.spec_dir)

    def validate_all(self) -> list[ValidationResult]:
        results = [
            self.validate_prereqs(),
            self.validate_context(),
            self.validate_my_output(),  # Add here
            # ...
        ]
        return results

    def validate_my_output(self) -> ValidationResult:
        return self._my_output_validator.validate()
```

### Step 9: Test the Phase

Create a test spec and verify the phase executes correctly:

```bash
cd apps/backend
python runners/spec_runner.py --task "Test my new phase" --complexity standard
```

Check that:
- [ ] Phase appears in the phase list
- [ ] Agent prompt loads correctly
- [ ] Output file is created
- [ ] Phase summary is stored (if compaction enabled)
- [ ] Validation passes (if validator added)

---

## Advanced Topics

### Extended Thinking Integration

The pipeline supports extended thinking (chain-of-thought reasoning) for complex phases:

```python
# In orchestrator
thinking_budget = get_thinking_budget(self.thinking_level)
# "none" → None
# "low" → 5000 tokens
# "medium" → 10000 tokens
# "high" → 16000 tokens
# "ultrathink" → 16000 tokens

# Passed to agent runner
await runner.run_agent(
    prompt_file,
    thinking_budget=thinking_budget
)
```

Phases that benefit from extended thinking:
- **Complexity Assessment** - Deep analysis of task requirements
- **Research** - Evaluating multiple integration options
- **Self-Critique** - Thorough spec review
- **Planning** - Complex subtask breakdown

### Graphiti Memory Integration

The `historical_context` phase queries the Graphiti knowledge graph for insights from past sessions:

**When it runs:** After discovery phase (if `GRAPHITI_ENABLED=true`)

**What it does:**
1. Queries knowledge graph for related past implementations
2. Retrieves patterns, gotchas, and discoveries
3. Injects context into subsequent phases

**How to use in custom phases:**
```python
from integrations.graphiti.memory import get_graphiti_memory

memory = get_graphiti_memory(spec_dir, project_dir)
context = memory.get_context_for_session("Implementing my feature")
# Use context in agent prompt
```

### Phase Recovery and Retry

Phases can fail and retry with exponential backoff:

```python
MAX_RETRIES = 3  # From spec/phases/models.py

# In phase method
for retry in range(MAX_RETRIES):
    success, output = await self.run_agent_fn(...)
    if success:
        break
    # Retry with more context or different approach
```

### Spec Directory Structure

After a successful spec run:

```
.auto-claude/specs/001-add-authentication/
├── requirements.json              # User requirements
├── complexity_assessment.json     # Complexity analysis
├── context.json                   # Relevant files discovered
├── research.json                  # External integration research (if applicable)
├── spec.md                        # Feature specification
├── critique_notes.md              # Self-critique notes (if applicable)
├── implementation_plan.json       # Subtask-based plan
└── graphiti/                      # Graphiti memory data (if enabled)
    └── entities/
```

---

## Troubleshooting

### Phase Fails to Complete

**Symptoms:** Phase returns `PhaseResult(success=False)`

**Common Causes:**
1. **Agent prompt unclear** - Review prompt file for clarity
2. **Output file not created** - Agent may not understand file path
3. **Validation fails** - Check validation logic in phase method
4. **Token limit exceeded** - Reduce prior phase summaries or context

**Solutions:**
- Add explicit file path instructions to prompt
- Check agent logs in task logger
- Verify validation logic catches correct errors
- Enable phase compaction to reduce token usage

### Complexity Assessment Wrong

**Symptoms:** Task assessed as SIMPLE when it should be COMPLEX (or vice versa)

**Causes:**
1. **AI assessment fails** - Falls back to heuristics
2. **Heuristic keywords insufficient** - Task uses uncommon terminology
3. **Requirements unclear** - Not enough information to assess accurately

**Solutions:**
- Check `complexity_assessment.json` for reasoning
- Add keywords to `ComplexityAnalyzer` in `complexity.py`
- Improve requirements gathering to capture more detail
- Use `--complexity` flag to force specific complexity

### Validation Auto-Fix Loops

**Symptoms:** Validation fails, auto-fix runs, validation fails again (repeat)

**Causes:**
1. **Validator too strict** - Checks for impossible conditions
2. **Auto-fix agent misunderstands** - Prompt unclear
3. **File format issues** - JSON/Markdown parsing errors

**Solutions:**
- Review validator logic in `spec/validate_pkg/validators/`
- Update auto-fix prompt for clarity
- Add explicit format examples to validation errors

### Phase Summaries Too Long

**Symptoms:** Token limit exceeded despite compaction

**Causes:**
1. **Summarization model too verbose** - Not following word limit
2. **Too many phases** - Summaries accumulate
3. **Large output files** - gather_phase_outputs() loads full files

**Solutions:**
- Reduce `target_words` in `summarize_phase_output()` (default 500)
- Truncate large files in `gather_phase_outputs()` (already limits to 10KB per file)
- Skip compaction for phases with minimal output

---

## Performance Considerations

### Token Usage

**Typical token consumption per phase:**
- Discovery: 5,000 tokens
- Requirements: 8,000 tokens
- Context: 10,000 tokens
- Spec Writing: 15,000 tokens
- Planning: 12,000 tokens

**Total for STANDARD (6 phases):** ~60,000 tokens
**Total for COMPLEX (8 phases):** ~80,000 tokens

**With compaction:** Reduces accumulated context by ~80%

### Cost Optimization

**Use Sonnet for compaction:**
```python
summary = await summarize_phase_output(
    phase_name,
    phase_output,
    model="sonnet",  # Cost-efficient for summarization
    target_words=500
)
```

**Skip validation for trivial changes:**
```json
"validation_recommendations": {
  "skip_validation": true,  // Docs-only changes
  "minimal_mode": true      // Simple changes
}
```

**Use heuristic assessment when possible:**
```python
orchestrator = SpecOrchestrator(
    use_ai_assessment=False  # Skip AI complexity assessment
)
```

### Execution Time

**Typical phase execution times:**
- Discovery: 30-60 seconds
- Requirements: 1-2 minutes (interactive), 30 seconds (automated)
- Complexity Assessment: 20-30 seconds (AI), 1 second (heuristic)
- Context: 30-60 seconds
- Spec Writing: 2-3 minutes
- Planning: 1-2 minutes
- Validation: 10-30 seconds

**Total for STANDARD:** ~8-12 minutes
**Total for COMPLEX:** ~12-18 minutes

---

## Related Documentation

- **[CLI-USAGE.md](CLI-USAGE.md)** - Running spec creation from command line
- **[apps/backend/spec/phases/README.md](../apps/backend/spec/phases/README.md)** - Phase module refactoring details
- **[apps/backend/spec/validate_pkg/README.md](../apps/backend/spec/validate_pkg/README.md)** - Validation system details
- **[prompts/complexity_assessor.md](../apps/backend/prompts/complexity_assessor.md)** - Complexity assessment prompt
- **[prompts/spec_writer.md](../apps/backend/prompts/spec_writer.md)** - Spec writing prompt

---

## Summary

The spec creation pipeline is a sophisticated system that:

1. **Analyzes task complexity** using AI + heuristics
2. **Adapts dynamically** with 3-8 phases based on complexity
3. **Summarizes phase outputs** for token efficiency (80% reduction)
4. **Validates thoroughly** with multi-layered validation and auto-fix
5. **Integrates memory** via Graphiti knowledge graph (optional)
6. **Uses modular architecture** with mixin pattern for maintainability

**Key modules:**
- `spec/complexity.py` - Complexity assessment
- `spec/compaction.py` - Phase output summarization
- `spec/phases/executor.py` - Phase execution with mixins
- `spec/pipeline/orchestrator.py` - Pipeline coordination
- `spec/pipeline/agent_runner.py` - Agent execution
- `spec/validate_pkg/` - Multi-layered validation

**To add a new phase:**
1. Create phase method in appropriate mixin
2. Add to PhaseExecutor
3. Create agent prompt
4. Update complexity assessment
5. Add display info
6. Register in orchestrator
7. Add validation (optional)
8. Test thoroughly

For questions or contributions, see [CONTRIBUTING.md](../CONTRIBUTING.md).
