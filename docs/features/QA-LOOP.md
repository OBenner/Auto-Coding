# QA Validation Loop

**Analysis Date:** 2026-02-12

## Overview

The QA Validation Loop is an automated quality assurance system that validates implementation against acceptance criteria through iterative review and fix cycles. It uses AI agents to identify issues, apply fixes, and ensure code quality before merging.

**Key Benefits:**
- Automated validation against acceptance criteria
- Iterative issue detection and resolution
- Recurring issue detection with human escalation
- Support for projects with and without test suites
- Integration with Linear for progress tracking
- E2E testing capabilities via Electron MCP for frontend changes

## Architecture

The QA system is organized into modular components:

```
qa/
├── loop.py           # Main orchestration loop
├── reviewer.py       # QA reviewer agent session
├── fixer.py          # QA fixer agent session
├── report.py         # Issue tracking, reporting, escalation
├── criteria.py       # Acceptance criteria and status management
├── coverage_validator.py   # Test coverage validation
├── pattern_validator.py    # Code pattern validation
└── recovery_metrics.py     # QA performance metrics
```

**Component Responsibilities:**
- **loop.py** - Coordinates reviewer/fixer sessions, manages iteration logic
- **reviewer.py** - Runs QA reviewer agent to validate acceptance criteria
- **fixer.py** - Runs QA fixer agent to resolve reported issues
- **report.py** - Tracks iteration history, detects recurring issues
- **criteria.py** - Manages QA signoff status, validates completion

## Workflow

### 1. Initial Validation

After all subtasks are completed, the QA loop automatically starts:

```bash
# Build completion triggers QA
python run.py --spec 001

# Or manually trigger QA
python run.py --spec 001 --qa
```

**Preconditions:**
- All implementation subtasks marked "completed"
- `implementation_plan.json` exists
- Build completion check passes

### 2. QA Reviewer Session

The QA reviewer agent validates the implementation:

**Input:**
- `spec.md` - Feature specification and requirements
- `implementation_plan.json` - Subtasks and acceptance criteria
- Project code - Implemented changes

**Validation Process:**
1. Reads acceptance criteria from spec
2. Inspects implemented code and tests
3. Runs test commands (if specified)
4. Performs E2E testing (for Electron apps with MCP enabled)
5. Checks test coverage requirements
6. Validates code patterns and conventions

**Output:**
- Status: `approved` or `rejected`
- Issues found (if rejected)
- Test results
- QA report: `qa_report.md`

**Example approval:**
```json
{
  "status": "approved",
  "qa_session": 1,
  "timestamp": "2026-02-12T10:30:00Z",
  "tests_passed": {
    "unit": true,
    "integration": true,
    "e2e": true
  }
}
```

**Example rejection:**
```json
{
  "status": "rejected",
  "qa_session": 1,
  "timestamp": "2026-02-12T10:30:00Z",
  "issues_found": [
    {
      "title": "Missing error handling for network failures",
      "type": "acceptance_criteria",
      "file": "src/api/client.py",
      "line": 42,
      "severity": "high"
    },
    {
      "title": "Unit test coverage below 80%",
      "type": "coverage",
      "severity": "medium"
    }
  ]
}
```

### 3. QA Fixer Session (if rejected)

When QA rejects the build, the fixer agent resolves issues:

**Input:**
- `QA_FIX_REQUEST.md` - Detailed issue report
- Current code implementation
- Original acceptance criteria

**Fix Process:**
1. Analyzes each issue in QA_FIX_REQUEST.md
2. Creates fix plan with subtasks
3. Implements fixes
4. Verifies fixes resolve issues
5. Updates status to `fixes_applied`

**Output:**
- Fixed code
- Updated `implementation_plan.json` with `fixes_applied` status

### 4. Re-validation Loop

After fixes are applied, QA reviewer runs again:

```
┌─────────────────┐
│ Build Complete  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ QA Reviewer     │─── Approved ──→ Merge
└────────┬────────┘
         │
         │ Rejected
         ▼
┌─────────────────┐
│ QA Fixer        │
└────────┬────────┘
         │
         │ Fixes Applied
         ▼
         (Loop back to QA Reviewer)
```

**Termination Conditions:**
- QA approves (success)
- Max iterations reached (`MAX_QA_ITERATIONS = 50`)
- Recurring issues detected (escalate to human)
- Consecutive errors (`MAX_CONSECUTIVE_ERRORS = 3`)

## Configuration

### Environment Variables

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GRAPHITI_ENABLED` | boolean | `false` | Enable Graphiti memory for QA context |
| `ELECTRON_MCP_ENABLED` | boolean | `false` | Enable E2E testing for Electron apps |
| `ELECTRON_DEBUG_PORT` | integer | `9222` | Chrome DevTools Protocol port |
| `LINEAR_API_KEY` | string | - | Linear API key for progress tracking |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_QA_ITERATIONS` | `50` | Maximum QA review cycles |
| `MAX_CONSECUTIVE_ERRORS` | `3` | Stop after N consecutive errors |
| `RECURRING_ISSUE_THRESHOLD` | `3` | Escalate if issue appears N times |
| `ISSUE_SIMILARITY_THRESHOLD` | `0.8` | Similarity score for recurring issues |

### Verification Strategy

The QA loop adapts its approach based on the verification strategy defined in `implementation_plan.json`:

```json
{
  "verification_strategy": {
    "risk_level": "critical",
    "acceptance_criteria": [...],
    "unit_tests": {
      "required": true,
      "minimum_coverage": 80
    },
    "integration_tests": {
      "required": true
    },
    "e2e_tests": {
      "required": true,
      "flows": ["user_login", "checkout"]
    },
    "browser_verification": {
      "required": true,
      "pages": ["/dashboard", "/settings"]
    }
  }
}
```

**Risk Levels:**
- `trivial` - No automated testing required
- `low` - Basic smoke tests
- `medium` - Unit + integration tests
- `high` - Full test suite + coverage requirements
- `critical` - All tests + E2E + manual verification

## Agent Types

### QA Reviewer Agent

**Location:** `apps/backend/qa/reviewer.py`

**Purpose:** Validates implementation against acceptance criteria

**Model Selection:**
```python
# Uses higher thinking budget for thorough analysis
model = get_phase_model("qa")
thinking_budget = get_phase_thinking_budget("qa")  # Typically 16000 tokens
```

**Tools Available:**
- **Bash** - Run test commands, linting, type checking
- **Read** - Inspect code, tests, configuration files
- **Write/Edit** - Create test files if needed
- **Electron MCP** (if enabled) - E2E testing for Electron apps
  - `mcp__electron__take_screenshot`
  - `mcp__electron__send_command_to_electron`
  - `mcp__electron__get_electron_window_info`

**Validation Steps:**

1. **Acceptance Criteria Check**
   - Reads spec.md for acceptance criteria
   - Verifies each criterion is met
   - Documents any missing requirements

2. **Test Execution**
   - Runs unit tests: `pytest tests/`
   - Runs integration tests (if required)
   - Validates test coverage (if minimum specified)

3. **Code Quality**
   - Checks for console.log/debugging statements
   - Validates error handling
   - Reviews code patterns

4. **E2E Testing** (if Electron app)
   - Takes screenshots to verify UI
   - Interacts with UI elements (click, fill forms)
   - Validates user flows

**Output:** `qa_report.md` with detailed findings

### QA Fixer Agent

**Location:** `apps/backend/qa/fixer.py`

**Purpose:** Resolves issues reported by QA reviewer

**Model Selection:**
```python
# Standard thinking budget for focused fixes
model = get_phase_model("coder")  # Reuses coder model
thinking_budget = get_phase_thinking_budget("coder")
```

**Tools Available:** Same as coder agent (Bash, Read, Write, Edit)

**Fix Process:**

1. **Read QA_FIX_REQUEST.md**
   - Parse issue list
   - Understand acceptance criteria gaps
   - Identify files to modify

2. **Plan Fixes**
   - Break fixes into small steps
   - Identify which files need changes
   - Plan test additions if needed

3. **Implement Fixes**
   - Edit code files
   - Add/update tests
   - Remove debug statements
   - Apply code patterns

4. **Verify Fixes**
   - Run tests to ensure fixes work
   - Check that new issues aren't introduced
   - Validate all acceptance criteria are met

**Output:** Fixed code + status update

## Issue Types

The QA system categorizes issues into types:

| Type | Description | Example |
|------|-------------|---------|
| `acceptance_criteria` | Missing or incomplete requirement | Feature doesn't match spec |
| `unit_test` | Missing or failing unit tests | No test for error case |
| `integration_test` | Integration test failures | API endpoint not tested |
| `e2e_test` | End-to-end test failures | User flow broken |
| `coverage` | Insufficient test coverage | Coverage below 80% |
| `code_quality` | Code pattern violations | Debug statements left in |
| `error_handling` | Missing error handling | No try/catch for network calls |
| `security` | Security concerns | Unvalidated user input |
| `performance` | Performance issues | Inefficient query |

## Recurring Issue Detection

The system detects when the same issue appears across multiple iterations:

### How It Works

1. **Normalize Issues**
   - Combines title + file + line into a key
   - Removes common prefixes ("error:", "issue:")
   - Lowercases and strips whitespace

2. **Similarity Matching**
   - Uses `SequenceMatcher` for fuzzy matching
   - Considers issues "same" if similarity >= 0.8

3. **Threshold Check**
   - Tracks occurrences across iterations
   - Escalates to human if issue appears >= 3 times

### Example

**Iteration 1:**
```json
{"title": "Missing error handling", "file": "api.py", "line": 42}
```

**Iteration 2:**
```json
{"title": "Error: Missing error handling", "file": "api.py", "line": 42}
```

**Iteration 3:**
```json
{"title": "No error handling for network failures", "file": "api.py", "line": 42}
```

**Result:** All three match (similarity > 0.8), escalate to human.

### Human Escalation

When recurring issues are detected:

1. Creates `QA_HUMAN_ESCALATION.md` with:
   - Recurring issue summary
   - All iterations where issue appeared
   - Suggested actions for human

2. Updates `implementation_plan.json`:
   ```json
   {
     "qa_signoff": {
       "status": "human_escalation",
       "recurring_issues": [...],
       "escalation_reason": "Issue appeared 3+ times"
     }
   }
   ```

3. User must:
   - Review `QA_HUMAN_ESCALATION.md`
   - Manually fix the recurring issue
   - Delete `QA_FIX_REQUEST.md` to resume QA

## No-Test Projects

The QA system handles projects without test suites:

### Detection

1. Checks for test directory existence
2. Runs test discovery command
3. If no tests found, marks as "no_test_project"

### Manual Test Plan

When no tests exist, QA creates a manual test plan:

```markdown
# Manual Test Plan

## Test Cases

1. **User Registration Flow**
   - Navigate to /register
   - Fill valid email and password
   - Submit form
   - Verify redirect to dashboard

2. **Login Validation**
   - Navigate to /login
   - Submit empty form
   - Verify error messages appear

...
```

### Validation Criteria

For no-test projects, QA validates:
- Acceptance criteria through code inspection
- Manual testing steps are documented
- Code quality and patterns
- Error handling coverage

## E2E Testing with Electron MCP

For Electron frontend projects, QA can perform automated E2E testing:

### Setup

1. **Start Electron with debugging:**
   ```bash
   npm run dev  # Already configured with --remote-debugging-port=9222
   ```

2. **Enable Electron MCP in `.env`:**
   ```bash
   ELECTRON_MCP_ENABLED=true
   ELECTRON_DEBUG_PORT=9222
   ```

3. **Run QA:**
   ```bash
   python run.py --spec 001 --qa
   ```

### Available E2E Tools

QA agents automatically get access to Electron MCP tools:

| Tool | Purpose |
|------|---------|
| `mcp__electron__take_screenshot` | Capture screenshots for visual verification |
| `mcp__electron__get_electron_window_info` | Get info about running windows |
| `mcp__electron__send_command_to_electron` | Interact with the app |
| `mcp__electron__read_electron_logs` | Read console logs for debugging |

### Interaction Commands

The `send_command_to_electron` tool supports:

**UI Interaction:**
- `click_by_text` - Click buttons/links by visible text
- `click_by_selector` - Click elements by CSS selector
- `fill_input` - Fill form fields by placeholder/selector
- `select_option` - Select dropdown options

**Navigation:**
- `navigate_to_hash` - Navigate to hash routes (#settings, #create)

**Input:**
- `send_keyboard_shortcut` - Send shortcuts (Enter, Ctrl+N, etc.)

**Inspection:**
- `get_page_structure` - Get organized overview of page elements
- `debug_elements` - Get debugging info about buttons/forms
- `verify_form_state` - Check form validation state

**Execution:**
- `eval` - Execute custom JavaScript code

### Example E2E Test Flow

```python
# 1. Take initial screenshot
agent: "Take a screenshot to see the current UI"
# Uses: mcp__electron__take_screenshot

# 2. Inspect page structure
agent: "Get page structure to find available buttons"
# Uses: mcp__electron__send_command_to_electron (command: "get_page_structure")

# 3. Click button to navigate
agent: "Click the 'Create New Spec' button"
# Uses: mcp__electron__send_command_to_electron (command: "click_by_text", args: {text: "Create New Spec"})

# 4. Fill out form
agent: "Fill the task description field"
# Uses: mcp__electron__send_command_to_electron (command: "fill_input", args: {placeholder: "Describe your task", value: "Add login feature"})

# 5. Submit and verify
agent: "Click Submit and verify success"
# Uses: click_by_text → take_screenshot → verify result
```

### When E2E Testing Is Used

- **Bug Fixes** - Reproduce the bug, apply fix, verify it's resolved
- **New Features** - Implement feature, test the UI flow end-to-end
- **UI Changes** - Verify visual changes and interactions work correctly
- **Form Validation** - Test form submission, validation, error handling

## Linear Integration

The QA system integrates with Linear for progress tracking:

### Status Updates

```python
# When QA starts
linear_qa_started(spec_id, iteration)

# When QA rejects
linear_qa_rejected(spec_id, iteration, issues_count)

# When QA approves
linear_qa_approved(spec_id, total_iterations, duration_seconds)

# When max iterations reached
linear_qa_max_iterations(spec_id, iteration)
```

### Configuration

Set environment variable:
```bash
LINEAR_API_KEY=lin_api_...
LINEAR_TEAM_ID=YOUR_TEAM_ID
```

## State Management

### QA Signoff States

```
pending → rejected → fixes_applied → rejected → ... → approved
                    ↑               │
                    └───────────────┘ (loop)
```

**State Descriptions:**
- `pending` - QA not yet run
- `rejected` - QA found issues, needs fixes
- `fixes_applied` - Fixer applied changes, ready for re-validation
- `approved` - All acceptance criteria met
- `human_escalation` - Recurring issues detected, human intervention required

### Data Storage

**`implementation_plan.json`:**
```json
{
  "qa_signoff": {
    "status": "approved",
    "qa_session": 2,
    "timestamp": "2026-02-12T10:30:00Z",
    "tests_passed": {
      "unit": true,
      "integration": true,
      "e2e": false
    }
  },
  "qa_iteration_history": [
    {
      "iteration": 1,
      "status": "rejected",
      "timestamp": "2026-02-12T09:00:00Z",
      "issues": [
        {"title": "Missing test", "type": "unit_test"}
      ]
    },
    {
      "iteration": 2,
      "status": "approved",
      "timestamp": "2026-02-12T10:30:00Z",
      "issues": []
    }
  ],
  "qa_stats": {
    "total_iterations": 2,
    "last_iteration": 2,
    "last_status": "approved",
    "issues_by_type": {
      "unit_test": 1
    }
  }
}
```

## CLI Commands

### Run QA Validation

```bash
# Automatic (triggered by build completion)
python run.py --spec 001

# Manual trigger
python run.py --spec 001 --qa

# With verbose output
python run.py --spec 001 --qa --verbose

# Use specific model
python run.py --spec 001 --qa --model claude-sonnet-4-5-20250929
```

### Check QA Status

```bash
python run.py --spec 001 --qa-status
```

**Output:**
```
Spec: 001-feature

QA Status: REJECTED
QA Sessions: 2
Last Check: 2026-02-12T10:30:00Z

Issues Found:
- Missing error handling (acceptance_criteria, high)
- Test coverage 65% (coverage, medium)

Iteration History:
  Iteration 1 (09:00): Rejected - 2 issues
  Iteration 2 (10:30): Rejected - 1 issue
```

## Customization

### Custom Acceptance Criteria

Define project-specific acceptance criteria in `spec.md`:

```markdown
## Acceptance Criteria

- [ ] User can register with email/password
- [ ] Password must be 8+ characters with special char
- [ ] Account created after email verification
- [ ] Login with valid credentials works
- [ ] Login with invalid credentials shows error

## Verification

**Unit Tests:**
- `pytest tests/test_auth.py` - All pass
- Coverage: >= 80%

**Integration Tests:**
- `pytest tests/integration/test_api.py` - All pass

**E2E Tests:**
- Manual: Register → Verify email → Login → Logout
```

### Custom QA Prompts

Modify QA behavior by editing agent prompts:

**apps/backend/prompts/qa_reviewer.md:**
```markdown
You are a QA reviewer. Focus on:
1. Security vulnerabilities
2. Error handling completeness
3. Test coverage for edge cases
4. Performance considerations
```

**apps/backend/prompts/qa_fixer.md:**
```markdown
You are a QA fixer. When fixing issues:
1. Add comprehensive tests
2. Follow project code patterns
3. Document complex logic
4. Remove all debug statements
```

## Performance Characteristics

**Typical Duration:**
- Simple feature QA: 2-5 minutes
- Standard feature QA: 5-15 minutes
- Complex feature QA: 15-30 minutes
- With E2E testing: Add 5-10 minutes

**Resource Usage:**
- Memory: ~500MB per QA session
- CPU: Moderate during test execution
- API calls: 10-50 per QA iteration (depends on test count)

**Iteration Statistics:**
- Median iterations to approval: 2
- 95th percentile: 5 iterations
- Max allowed: 50 iterations

## Best Practices

### For Users

1. **Write Clear Acceptance Criteria**
   - Be specific about requirements
   - Include edge cases
   - Define measurable outcomes

2. **Provide Test Commands**
   ```json
   {
     "verification_strategy": {
       "unit_tests": {
         "required": true,
         "commands": ["pytest tests/test_feature.py -v"]
       }
     }
   }
   ```

3. **Set Realistic Coverage Targets**
   - 80% is a good default
   - 100% is rarely practical
   - Focus on critical paths

4. **Review QA Reports**
   - Read `qa_report.md` after each iteration
   - Understand why issues were found
   - Learn patterns to avoid future issues

### For Developers Extending QA

1. **Add New Issue Types**
   - Define in `report.py`
   - Add validation logic
   - Document in acceptance criteria

2. **Create Custom Validators**
   ```python
   # qa/custom_validator.py
   def validate_custom_criteria(code: str) -> list[dict]:
       issues = []
       # Your validation logic
       return issues
   ```

3. **Integrate Additional Test Frameworks**
   - Add test runner in `reviewer.py`
   - Parse output format
   - Report failures as issues

## Troubleshooting

### QA Stuck in Loop

**Problem:** QA rejects with same issue repeatedly

**Solutions:**
1. Check for recurring issues - should auto-escalate
2. Review `QA_FIX_REQUEST.md` - is issue clear?
3. Manually fix and delete `QA_FIX_REQUEST.md`
4. Increase `ISSUE_SIMILARITY_THRESHOLD` if issues are too different

### Tests Not Running

**Problem:** QA reports tests but doesn't run them

**Solutions:**
1. Verify test commands in verification strategy
2. Check test files exist in worktree
3. Ensure dependencies installed in `.venv`
4. Check test framework compatibility (pytest, vitest, etc.)

### E2E Testing Not Working

**Problem:** Electron MCP tools not available

**Solutions:**
1. Ensure `ELECTRON_MCP_ENABLED=true` in `.env`
2. Start Electron with `npm run dev` (includes debug port)
3. Verify `ELECTRON_DEBUG_PORT=9222` matches app
4. Check Electron app is running before starting QA

### QA Approves Too Easily

**Problem:** QA approves without thorough validation

**Solutions:**
1. Review `qa_reviewer.md` prompt - make it stricter
2. Add more acceptance criteria to spec
3. Set higher coverage requirements
4. Enable E2E testing for UI changes
5. Review `qa_report.md` to see what was checked

### Max Iterations Reached

**Problem:** QA hit 50 iterations without approval

**Solutions:**
1. Review `qa_iteration_history` for patterns
2. Manually fix recurring issues
3. Simplify acceptance criteria if too strict
4. Break feature into smaller specs
5. Increase `MAX_QA_ITERATIONS` if needed (rare)

## Testing

### Unit Tests

**Location:** `tests/test_qa_loop.py`

**Run:**
```bash
pytest tests/test_qa_loop.py -v
```

**Coverage:**
- QA status management
- Iteration tracking
- Issue detection logic
- State machine transitions

### Integration Tests

Test QA system with real projects:

```bash
# Create test spec
python spec_runner.py --task "Test feature"

# Run build
python run.py --spec test-feature

# Verify QA runs
python run.py --spec test-feature --qa-status
```

## Related Documentation

- [Testing Patterns](../.planning/codebase/TESTING.md) - Test framework and patterns
- [Architecture Overview](../.planning/codebase/ARCHITECTURE.md) - System architecture
- [Multi-Agent Pipeline](MULTI-AGENT-PIPELINE.md) - Agent orchestration
- [Advanced Usage](../../guides/ADVANCED-USAGE.md) - QA customization
- [Agent Customization](../../guides/AGENT-CUSTOMIZATION.md) - Modifying QA prompts

---

*QA Loop documentation: 2026-02-12*
