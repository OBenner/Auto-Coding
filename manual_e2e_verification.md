# End-to-End Decision Tracking Verification Guide

This guide provides step-by-step instructions for manually verifying the AI Decision Explainability feature end-to-end.

## Overview

The AI Decision Explainability feature enables transparent tracking of AI agent decisions across:
- **Backend**: DecisionTracker captures decisions with alternatives, confidence levels, and reasoning chains
- **Frontend**: DecisionExplainer and DecisionTree components visualize decisions in the UI
- **Integration**: Decisions are logged to both `task_logs.json` and `decisions.json`

## Prerequisites

- Auto-Claude project set up and running
- Python backend dependencies installed
- Frontend development environment ready

## Automated Verification

Run the comprehensive E2E test suite:

```bash
cd apps/backend
python -m pytest ../../tests/test_decision_tracking_e2e.py -v
```

**Expected Result**: All 8 tests should pass, covering:
1. Complete decision lifecycle (tracking, alternatives, reasoning chains)
2. Multiple decision types (approach, implementation, tool selection, etc.)
3. Low confidence review flagging
4. Decision filtering by phase, type, subtask, confidence
5. Decision statistics generation
6. Persistence and reload across sessions
7. Frontend data format compatibility
8. Integration with TaskLogger phases

## Manual Verification Steps

### Step 1: Run a Task with Decision Points

Create a test spec with decision tracking:

```bash
cd apps/backend

# Create a simple test spec
python -c "
from pathlib import Path
import json

spec_dir = Path('.auto-claude/specs/test-decision-e2e')
spec_dir.mkdir(parents=True, exist_ok=True)

spec = {
    'feature': 'Test Decision Tracking',
    'acceptance_criteria': ['Verify decisions are tracked']
}

with open(spec_dir / 'spec.md', 'w') as f:
    f.write('# Test Decision Tracking\n\nTest spec for verifying decision tracking.')

print(f'Created test spec at {spec_dir}')
"
```

Now run a test that exercises decision tracking:

```python
cd apps/backend
python3 << 'EOF'
from pathlib import Path
from agents.decision_tracker import DecisionTracker
from task_logger.decision_models import Alternative, DecisionType
from task_logger.logger import TaskLogger
from task_logger.models import LogPhase

# Setup
spec_dir = Path('.auto-claude/specs/test-decision-e2e')
task_logger = TaskLogger(spec_dir, emit_markers=False)
task_logger.start_phase(LogPhase.CODING, "Testing decision tracking")

# Initialize decision tracker
tracker = DecisionTracker(spec_dir, task_logger, LogPhase.CODING)
tracker.set_session(1)
tracker.set_subtask("test-subtask-1")

# Track a decision with alternatives
decision = tracker.track_decision(
    decision_type=DecisionType.IMPLEMENTATION,
    context="Choose data validation approach for user input",
    chosen_approach="Use Pydantic models for type-safe validation",
    reasoning="Provides compile-time type checking, auto-documentation, and better IDE support",
    confidence=0.87,
    impact="Improves code quality and reduces runtime errors by 30-40%",
    reversible=True,
    dependencies=["pydantic>=2.0"]
)

# Add alternatives
alt1 = Alternative(
    description="Manual validation with if/else statements",
    reasoning="No external dependencies, straightforward",
    rejected_reason="Verbose, error-prone, lacks type safety",
    tradeoffs=["Simple", "No dependencies", "Hard to maintain"]
)
tracker.add_alternative(decision, alt1)

alt2 = Alternative(
    description="Use Marshmallow validation library",
    reasoning="Popular library with good ecosystem",
    rejected_reason="Less type-safe, requires more boilerplate",
    tradeoffs=["Flexible", "Good docs", "Steeper learning curve"]
)
tracker.add_alternative(decision, alt2)

# Add reasoning chain
tracker.add_reasoning_step(decision, "Analyzed project requirements for input validation")
tracker.add_reasoning_step(decision, "Compared three approaches: manual, Marshmallow, Pydantic")
tracker.add_reasoning_step(decision, "Evaluated trade-offs: type safety vs simplicity")
tracker.add_reasoning_step(decision, "Selected Pydantic for long-term maintainability")

# Log the decision
tracker.log_decision(decision, print_to_console=True)

# Track another decision (low confidence to test review flagging)
low_conf_decision = tracker.track_decision(
    decision_type=DecisionType.ARCHITECTURE,
    context="Design caching strategy for API responses",
    chosen_approach="Use Redis with TTL-based expiration",
    reasoning="Might improve performance, but impact unclear without benchmarks",
    confidence=0.52,  # Low confidence - should flag for review
    impact="Potentially 20-50% faster response times (needs verification)",
    reversible=True
)
tracker.log_decision(low_conf_decision, print_to_console=True)

# Show statistics
stats = tracker.get_decision_stats()
print("\n=== Decision Statistics ===")
print(f"Total decisions: {stats['total']}")
print(f"By type: {stats['by_type']}")
print(f"By confidence level: {stats['by_confidence_level']}")
print(f"Average confidence: {stats['avg_confidence']:.2f}")
print(f"Requiring review: {stats['requiring_review']}")

task_logger.end_phase(LogPhase.CODING, success=True)
print(f"\n✓ Decisions saved to {spec_dir}")
EOF
```

**Expected Output**:
- Two decisions tracked and logged
- Statistics showing decision breakdown
- Success message with spec directory path

### Step 2: Verify Decisions in decisions.json

```bash
cd apps/backend
python3 << 'EOF'
from pathlib import Path
import json

spec_dir = Path('.auto-claude/specs/test-decision-e2e')
decisions_file = spec_dir / 'decisions.json'

with open(decisions_file, 'r') as f:
    data = json.load(f)

print("=== decisions.json Content ===")
print(f"Total decisions: {len(data['decisions'])}")
print(f"\nDecision 1:")
d1 = data['decisions'][0]
print(f"  Type: {d1['decision_type']}")
print(f"  Approach: {d1['chosen_approach']}")
print(f"  Confidence: {d1['confidence']} ({d1['confidence_level']})")
print(f"  Alternatives: {len(d1['alternatives'])}")
print(f"  Reasoning chain: {len(d1['reasoning_chain'])} steps")
print(f"  Requires review: {d1['requires_review']}")

print(f"\nDecision 2:")
d2 = data['decisions'][1]
print(f"  Type: {d2['decision_type']}")
print(f"  Approach: {d2['chosen_approach']}")
print(f"  Confidence: {d2['confidence']} ({d2['confidence_level']})")
print(f"  Requires review: {d2['requires_review']} (flagged for low confidence)")

print("\n✓ Decision data structure verified")
EOF
```

**Expected Output**:
- JSON file exists and is well-formed
- Two decisions present with all metadata
- First decision has 2 alternatives and 4 reasoning steps
- Second decision is flagged for review (low confidence)

### Step 3: Verify Decisions in task_logs.json

```bash
cd apps/backend
python3 << 'EOF'
from pathlib import Path
import json

spec_dir = Path('.auto-claude/specs/test-decision-e2e')
logs_file = spec_dir / 'task_logs.json'

with open(logs_file, 'r') as f:
    data = json.load(f)

print("=== task_logs.json Content ===")
coding_phase = data['phases']['coding']
print(f"Phase status: {coding_phase['status']}")
print(f"Total entries: {len(coding_phase['entries'])}")

# Find decision log entries
decision_entries = [
    entry for entry in coding_phase['entries']
    if 'Decision:' in entry.get('content', '')
]

print(f"\nDecision log entries: {len(decision_entries)}")
for i, entry in enumerate(decision_entries, 1):
    print(f"\nDecision Entry {i}:")
    print(f"  Summary: {entry['content']}")
    print(f"  Has detail: {'detail' in entry}")
    print(f"  Collapsed: {entry.get('collapsed', 'N/A')}")
    if 'detail' in entry:
        detail = entry['detail']
        print(f"  Detail preview: {detail[:100]}...")

print("\n✓ Task log entries verified")
EOF
```

**Expected Output**:
- task_logs.json exists with coding phase
- Two decision log entries found
- Each entry has expandable detail content
- Details include alternatives, reasoning, and confidence

### Step 4: Frontend Visualization (Optional)

If the frontend is running, you can verify the UI components:

1. **Start the frontend**:
   ```bash
   cd apps/frontend
   npm run dev
   ```

2. **Open the test spec in the UI**:
   - Navigate to the task/spec view
   - Open the "test-decision-e2e" spec
   - View the task logs

3. **Verify DecisionExplainer display**:
   - [ ] Decision entries appear in the log stream
   - [ ] Confidence badges are visible (HIGH, LOW)
   - [ ] Entries are expandable to show details
   - [ ] Alternatives section displays both alternatives
   - [ ] Reasoning chain shows all 4 steps
   - [ ] Low confidence decision has "Needs Review" badge
   - [ ] Metadata (impact, dependencies) is visible

4. **Verify DecisionTree visualization**:
   - [ ] Decision tree component renders
   - [ ] Decisions are grouped by phase
   - [ ] Tree shows hierarchical structure
   - [ ] Confidence levels are color-coded
   - [ ] Clicking nodes expands decision details

5. **Verify decision filtering**:
   - [ ] Filter dropdown includes "decisions" option
   - [ ] Selecting "decisions" filter shows only decision entries
   - [ ] Filter persists across page navigation

### Step 5: Cleanup

Remove the test spec:

```bash
rm -rf apps/backend/.auto-claude/specs/test-decision-e2e
```

## Verification Checklist

Backend:
- [x] DecisionTracker captures decisions correctly
- [x] Alternatives and reasoning chains are stored
- [x] Low confidence decisions are flagged for review
- [x] Decisions persist to decisions.json
- [x] Decisions log to task_logs.json
- [x] Decision filtering works correctly
- [x] Statistics generation is accurate
- [x] Data format matches TypeScript interfaces

Frontend (if running):
- [ ] Decision entries render in TaskLogs
- [ ] Expandable details show full decision info
- [ ] Confidence badges display correctly
- [ ] Alternatives and reasoning chains visible
- [ ] "Needs Review" flag appears for low confidence
- [ ] DecisionTree visualization renders
- [ ] Decision filtering works in UI
- [ ] No console errors

## Test Results

All 8 automated tests passed:
- ✓ test_decision_lifecycle
- ✓ test_multiple_decision_types
- ✓ test_low_confidence_review_flagging
- ✓ test_decision_filtering
- ✓ test_decision_statistics
- ✓ test_decision_persistence_and_reload
- ✓ test_frontend_data_format_compatibility
- ✓ test_integration_with_task_logger_phases

## Known Limitations

- Frontend visualization testing requires manual verification (automated E2E tests would require Electron MCP setup)
- Decision export functionality not yet implemented (future enhancement)
- Decision comparison across tasks not yet implemented (future enhancement)

## Conclusion

The AI Decision Explainability feature is fully functional and ready for use. All backend components work correctly, and the data format is compatible with the frontend TypeScript interfaces. Manual UI verification is recommended for the complete end-to-end experience.
