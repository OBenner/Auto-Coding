# Long-Running Session Stability Test Guide

## Overview

This guide explains how to manually verify that Auto Claude maintains session context stability over 4+ hours of continuous operation, meeting the acceptance criteria for the Extended Context Session Manager feature.

## Acceptance Criteria

The test verifies the following criteria:

- ✅ Agent sessions maintain full context for 4+ hours of continuous operation
- ✅ Conversation history of 50+ rounds without quality degradation
- ✅ Highlighted code references persist across entire session
- ✅ Context window optimized to prioritize recent and relevant information
- ✅ Users can review full session context in structured format
- ✅ Session context survives app restart and agent respawns

## Prerequisites

1. **Auto Claude Backend**: Functional installation with all dependencies
2. **Test Spec**: A spec that will require 4+ hours of development work
3. **Monitoring Tools**: Optional system monitoring (memory, CPU usage)
4. **Time**: Dedicated 4+ hour testing window

## Test Setup

### 1. Prepare the Test Environment

```bash
# Navigate to your project
cd /path/to/your/project

# Verify Auto Claude is working
python apps/backend/run.py --list

# Choose a spec or create a test spec
# For this test, use a real spec that will require significant work
```

### 2. Create Test Log File

```bash
# Create a log file to track checkpoints
mkdir -p test_logs
STABILITY_LOG="test_logs/stability_test_$(date +%Y%m%d_%H%M%S).log"

# Add header
cat > "$STABILITY_LOG" << EOF
Long-Running Stability Test Log
================================
Start Time: $(date)
Test Duration Target: 4 hours minimum
Spec: [FILL IN]
EOF

echo "Log file: $STABILITY_LOG"
```

### 3. Start the Agent Session

```bash
# Start the session with your chosen spec
python apps/backend/run.py --spec [SPEC_NUMBER]
```

## Test Execution

### Checkpoint Schedule

Perform the following checks at each checkpoint:

| Time | Checkpoint | Actions |
|------|-----------|---------|
| **0 min** | Initial | Record session ID, verify initialization |
| **30 min** | Early | Check conversation history, code refs, tokens |
| **1 hour** | Mid-1 | Test context formatting, verify data integrity |
| **1.5 hours** | Mid-2 | Verify persistence, check for degradation |
| **2 hours** | Mid-3 | Test session restart (if safe) |
| **2.5 hours** | Mid-4 | Verify all checkpoints, check memory |
| **3 hours** | Mid-5 | Full integrity check, performance test |
| **3.5 hours** | Late | Verify data still accessible |
| **4 hours** | Final | Complete verification, generate report |

### At Each Checkpoint

#### Step 1: Record Current State

Add to your log file:

```bash
cat >> "$STABILITY_LOG" << EOF

Checkpoint: [TIME]
Timestamp: $(date)
-----------------------------------------------------------------------
EOF
```

#### Step 2: Check Conversation History

```python
# In Python shell or script
from pathlib import Path
import sys
sys.path.insert(0, "apps/backend")

from agents.session import ConversationHistory

spec_dir = Path(".auto-claude/specs/[SPEC_NUMBER]")
history = ConversationHistory.load_latest(spec_dir, "YOUR_SUBTASK_ID")

# Log results
print(f"Total rounds: {len(history.rounds)}")
print(f"Session ID: {history.session_id}")

# Verify no data corruption
for i, round_obj in enumerate(history.rounds[-5:], 1):
    assert round_obj.user_message, f"Round {i}: Missing user message"
    assert round_obj.assistant_response, f"Round {i}: Missing assistant response"
    assert len(round_obj.tool_calls) > 0, f"Round {i}: No tool calls"

print("✓ Last 5 rounds verified")
```

Add to log:

```
Conversation History:
  Total Rounds: [NUMBER]
  Session ID: [UUID]
  Last 5 Rounds: ✓ VERIFIED
```

#### Step 3: Check Code References

```python
# Get all code references
code_refs = history.get_all_code_references()
print(f"Unique code references: {len(code_refs)}")
print(f"Sample references: {list(code_refs)[:5]}")
```

Add to log:

```
Code References:
  Total Unique Files: [NUMBER]
  Sample: [FILE1, FILE2, FILE3, ...]
```

#### Step 4: Check Token Usage

```python
total_input, total_output = history.get_total_tokens()
print(f"Total tokens: {total_input + total_output:,}")
print(f"Input: {total_input:,}, Output: {total_output:,}")
```

Add to log:

```
Token Usage:
  Total: [NUMBER]
  Input: [NUMBER]
  Output: [NUMBER]
```

#### Step 5: Test Context Formatting (Every 1 hour)

```python
from agents.session import format_context_for_resume

context = format_context_for_resume(history)
print(f"Context length: {len(context)} characters")

# Verify required sections
required = ["Session Resume Context", "Previous Conversation Summary",
            "Code References", "Token Usage"]
missing = [s for s in required if s not in context]

if missing:
    print(f"✗ Missing sections: {missing}")
else:
    print("✓ All required sections present")
```

Add to log:

```
Context Formatting:
  Length: [NUMBER] characters
  Required Sections: ✓ ALL PRESENT or ✗ MISSING: [LIST]
```

#### Step 6: Test Session Restart (At 2 hours)

**⚠️ ONLY DO THIS IF IT'S SAFE TO INTERRUPT YOUR SESSION**

```bash
# Stop the current agent session (Ctrl+C or let it complete)

# Wait a few seconds
sleep 5

# Resume the session
python apps/backend/run.py --spec [SPEC_NUMBER] --resume

# Verify context restored
# Check that conversation history is intact
# Verify all previous work is accessible
```

Add to log:

```
Session Restart Test:
  Stopped: [TIMESTAMP]
  Resumed: [TIMESTAMP]
  Context Restored: ✓ YES or ✗ NO
  Data Integrity: ✓ VERIFIED or ✗ CORRUPTED
```

## Verification Criteria

At the end of 4+ hours, verify:

### ✅ Criterion 1: Duration
- [ ] Total time ≥ 4 hours
- [ ] No unplanned interruptions

### ✅ Criterion 2: Conversation Rounds
- [ ] Total rounds ≥ 50
- [ ] All rounds accessible
- [ ] No data corruption

### ✅ Criterion 3: Code References
- [ ] Code references tracked throughout
- [ ] Reference count increased over time
- [ ] All references retrievable

### ✅ Criterion 4: Context Optimization
- [ ] Context formatting works at all checkpoints
- [ ] Recent rounds prioritized
- [ ] Relevant information preserved

### ✅ Criterion 5: Structured Review
- [ ] Can review full conversation history
- [ ] Can export session context
- [ ] Timeline view works (if testing UI)

### ✅ Criterion 6: Session Persistence
- [ ] Context persists across checkpoints
- [ ] Session restart works (if tested)
- [ ] No data degradation over time

## Success Metrics

| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Duration | ≥ 4 hours | ___ hours | ⬜ |
| Conversation Rounds | ≥ 50 | ___ rounds | ⬜ |
| Degradation Events | 0 | ___ events | ⬜ |
| Code References | ≥ 10 | ___ refs | ⬜ |
| Context Formatting | Works at all checkpoints | ✅/❌ | ⬜ |
| Session Restart | Successful | ✅/❌ | ⬜ |

## Common Issues and Solutions

### Issue 1: Missing Conversation Rounds

**Symptoms**: Some rounds are not accessible or have missing data

**Checks**:
```python
# Check for gaps in round numbers
expected = set(range(1, len(history.rounds) + 1))
actual = {r.round_number for r in history.rounds}
missing = expected - actual
print(f"Missing rounds: {missing}")
```

**Solution**: Document the issue, check if it's a pattern or one-time event

### Issue 2: Code References Not Tracked

**Symptoms**: Code reference count is 0 or not increasing

**Checks**:
```python
# Check recent rounds for code references
for round_obj in history.rounds[-10:]:
    print(f"Round {round_obj.round_number}: {len(round_obj.code_references)} refs")
```

**Solution**: Verify tool calls include file paths (Read, Edit, Write)

### Issue 3: Context Formatting Fails

**Symptoms**: `format_context_for_resume()` returns empty string or raises error

**Checks**:
```python
# Test with minimal data
test_history = ConversationHistory(spec_dir, "test")
test_context = format_context_for_resume(test_history)
print(f"Test context length: {len(test_context)}")
```

**Solution**: Check for corrupted conversation data

### Issue 4: Performance Degradation

**Symptoms**: Session slows down over time, high memory usage

**Monitoring**:
```bash
# Check memory usage (Linux/Mac)
ps aux | grep python | grep run.py

# Check memory usage (Windows)
tasklist | findstr python
```

**Solution**: Document degradation rate, check for memory leaks

## Reporting

### Final Report Template

```markdown
# Long-Running Stability Test Report

**Date**: [DATE]
**Tester**: [NAME]
**Spec**: [SPEC_NUMBER]
**Task**: [BRIEF DESCRIPTION]

## Test Duration
- Start: [TIMESTAMP]
- End: [TIMESTAMP]
- Total: [HOURS] hours [MINUTES] minutes

## Results Summary
- Total Conversation Rounds: [NUMBER]
- Total Tokens Used: [NUMBER]
- Code References: [NUMBER]
- Degradation Events: [NUMBER]
- Session Restarts: [NUMBER] (successful/attempted)

## Acceptance Criteria Verification
- [x] Agent sessions maintain full context for 4+ hours
- [x] Conversation history of 50+ rounds without degradation
- [x] Code references persist across entire session
- [x] Context window optimized for recent/relevant info
- [x] Users can review full session context
- [x] Session context survives restart

## Issues Encountered
[List any issues with timestamps and details]

## Performance Observations
[Notes on performance, memory usage, etc.]

## Conclusion
✅ PASS / ⚠️ PASS WITH WARNINGS / ❌ FAIL

## Recommendations
[Any suggestions for improvements]
```

## Automated Test Alternative

If you don't have 4+ hours for manual testing, run the automated test:

```bash
# Run automated stability test (~5-10 minutes)
python tests/test_long_running_stability.py --mode automated

# Generate manual test plan
python tests/test_long_running_stability.py --mode manual --output-plan my_test_plan.json

# Run with custom duration
python tests/test_long_running_stability.py --mode automated --duration-minutes 480 --rounds-per-hour 10
```

## Notes

- **Real-World Testing**: For best results, test with actual development work, not artificial rounds
- **Monitoring**: Consider using system monitoring tools to track memory and CPU usage
- **Documentation**: The more detailed your logs, the easier it is to diagnose issues
- **Safety**: Only test session restart if it's safe to interrupt your work
- **Patience**: This is a marathon, not a sprint. Take breaks at checkpoints

## Support

If you encounter issues:

1. Check the logs in `.auto-claude/specs/[SPEC]/conversation_history/`
2. Review the automated test results for comparison
3. Document the issue with timestamps and error messages
4. Compare your results with the acceptance criteria

## Conclusion

Completing this 4-hour stability test provides confidence that Auto Claude can handle real-world, multi-hour development sessions without context loss or degradation—the key differentiator from competitors like Copilot.
