# RECOVERY AWARENESS ADDITIONS FOR CODER.MD

## Add to STEP 1 (Line 37):

```bash
# 10. CHECK ATTEMPT HISTORY (Recovery Context)
echo -e "\n=== RECOVERY CONTEXT ==="
if [ -f memory/attempt_history.json ]; then
  echo "Attempt History (for retry awareness):"
  cat memory/attempt_history.json

  # Show stuck subtasks if any
  stuck_count=$(cat memory/attempt_history.json | jq '.stuck_subtasks | length' 2>/dev/null || echo 0)
  if [ "$stuck_count" -gt 0 ]; then
    echo -e "\n⚠️  WARNING: Some subtasks are stuck and need different approaches!"
    cat memory/attempt_history.json | jq '.stuck_subtasks'
  fi
else
  echo "No attempt history yet (all subtasks are first attempts)"
fi
echo "=== END RECOVERY CONTEXT ==="
```

## Add to STEP 5 (Before 5.1):

### 5.0: Check Recovery History for This Subtask (CRITICAL - DO THIS FIRST)

```bash
# Check if this subtask was attempted before
SUBTASK_ID="your-subtask-id"  # Replace with actual subtask ID from implementation_plan.json

echo "=== CHECKING ATTEMPT HISTORY FOR $SUBTASK_ID ==="

if [ -f memory/attempt_history.json ]; then
  # Check if this subtask has attempts
  subtask_data=$(cat memory/attempt_history.json | jq ".subtasks[\"$SUBTASK_ID\"]" 2>/dev/null)

  if [ "$subtask_data" != "null" ]; then
    echo "⚠️⚠️⚠️ THIS SUBTASK HAS BEEN ATTEMPTED BEFORE! ⚠️⚠️⚠️"
    echo ""
    echo "Previous attempts:"
    cat memory/attempt_history.json | jq ".subtasks[\"$SUBTASK_ID\"].attempts[]"
    echo ""
    echo "CRITICAL REQUIREMENT: You MUST try a DIFFERENT approach!"
    echo "Review what was tried above and explicitly choose a different strategy."
    echo ""

    # Show count
    attempt_count=$(cat memory/attempt_history.json | jq ".subtasks[\"$SUBTASK_ID\"].attempts | length" 2>/dev/null || echo 0)
    echo "This is attempt #$((attempt_count + 1))"

    if [ "$attempt_count" -ge 2 ]; then
      echo ""
      echo "⚠️  HIGH RISK: Multiple attempts already. Consider:"
      echo "  - Using a completely different library or pattern"
      echo "  - Simplifying the approach"
      echo "  - Checking if requirements are feasible"
    fi
  else
    echo "✓ First attempt at this subtask - no recovery context needed"
  fi
else
  echo "✓ No attempt history file - this is a fresh start"
fi

echo "=== END ATTEMPT HISTORY CHECK ==="
echo ""
```

**WHAT THIS MEANS:**
- If you see previous attempts, you are RETRYING this subtask
- Previous attempts FAILED for a reason
- You MUST read what was tried and explicitly choose something different
- Repeating the same approach will trigger circular fix detection

## Add to STEP 6 (After marking in_progress):

### Record Your Approach (Recovery Tracking)

**IMPORTANT: Before you write any code, document your approach.**

```python
# Record your implementation approach for recovery tracking
import json
from pathlib import Path
from datetime import datetime

subtask_id = "your-subtask-id"  # Your current subtask ID
approach_description = """
Describe your approach here in 2-3 sentences:
- What pattern/library are you using?
- What files are you modifying?
- What's your core strategy?

Example: "Using async/await pattern from auth.py. Will modify user_routes.py
to add avatar upload endpoint using the same file handling pattern as
document_upload.py. Will store in S3 using boto3 library."
"""

# This will be used to detect circular fixes
approach_file = Path("memory/current_approach.txt")
approach_file.parent.mkdir(parents=True, exist_ok=True)

with open(approach_file, "a") as f:
    f.write(f"\n--- {subtask_id} at {datetime.now().isoformat()} ---\n")
    f.write(approach_description.strip())
    f.write("\n")

print(f"Approach recorded for {subtask_id}")
```

**Why this matters:**
- If your attempt fails, the recovery system will read this
- It helps detect if next attempt tries the same thing (circular fix)
- It creates a record of what was attempted for human review

## Add to STEP 7 (After verification section):

### If Verification Fails - Recovery Process

```python
# If verification failed, record the attempt
import json
from pathlib import Path
from datetime import datetime

subtask_id = "your-subtask-id"
approach = "What you tried"  # From your approach.txt
error_message = "What went wrong"  # The actual error

# Load or create attempt history
history_file = Path("memory/attempt_history.json")
if history_file.exists():
    with open(history_file) as f:
        history = json.load(f)
else:
    history = {"subtasks": {}, "stuck_subtasks": [], "metadata": {}}

# Initialize subtask if needed
if subtask_id not in history["subtasks"]:
    history["subtasks"][subtask_id] = {"attempts": [], "status": "pending"}

# Get current session number from build-progress.txt
session_num = 1  # You can extract from build-progress.txt

# Record the failed attempt
attempt = {
    "session": session_num,
    "timestamp": datetime.now().isoformat(),
    "approach": approach,
    "success": False,
    "error": error_message
}

history["subtasks"][subtask_id]["attempts"].append(attempt)
history["subtasks"][subtask_id]["status"] = "failed"
history["metadata"]["last_updated"] = datetime.now().isoformat()

# Save
with open(history_file, "w") as f:
    json.dump(history, f, indent=2)

print(f"Failed attempt recorded for {subtask_id}")

# Check if we should mark as stuck
attempt_count = len(history["subtasks"][subtask_id]["attempts"])
if attempt_count >= 3:
    print(f"\n⚠️  WARNING: {attempt_count} attempts failed.")
    print("Consider marking as stuck if you can't find a different approach.")
```

## Add NEW STEP between 9 and 10:

## STEP 9B: RECORD SUCCESSFUL ATTEMPT (If verification passed)

```python
# Record successful completion in attempt history
import json
from pathlib import Path
from datetime import datetime

subtask_id = "your-subtask-id"
approach = "What you tried"  # From your approach.txt

# Load attempt history
history_file = Path("memory/attempt_history.json")
if history_file.exists():
    with open(history_file) as f:
        history = json.load(f)
else:
    history = {"subtasks": {}, "stuck_subtasks": [], "metadata": {}}

# Initialize subtask if needed
if subtask_id not in history["subtasks"]:
    history["subtasks"][subtask_id] = {"attempts": [], "status": "pending"}

# Get session number
session_num = 1  # Extract from build-progress.txt or session count

# Record successful attempt
attempt = {
    "session": session_num,
    "timestamp": datetime.now().isoformat(),
    "approach": approach,
    "success": True,
    "error": None
}

history["subtasks"][subtask_id]["attempts"].append(attempt)
history["subtasks"][subtask_id]["status"] = "completed"
history["metadata"]["last_updated"] = datetime.now().isoformat()

# Save
with open(history_file, "w") as f:
    json.dump(history, f, indent=2)

# Also record as good commit
commit_hash = "$(git rev-parse HEAD)"  # Get current commit

commits_file = Path("memory/build_commits.json")
if commits_file.exists():
    with open(commits_file) as f:
        commits = json.load(f)
else:
    commits = {"commits": [], "last_good_commit": None, "metadata": {}}

commits["commits"].append({
    "hash": commit_hash,
    "subtask_id": subtask_id,
    "timestamp": datetime.now().isoformat()
})
commits["last_good_commit"] = commit_hash
commits["metadata"]["last_updated"] = datetime.now().isoformat()

with open(commits_file, "w") as f:
    json.dump(commits, f, indent=2)

print(f"✓ Success recorded for {subtask_id} at commit {commit_hash[:8]}")
```

## KEY RECOVERY PRINCIPLES TO ADD:

### The Recovery Loop

```
1. Start subtask
2. Check attempt_history.json for this subtask
3. If previous attempts exist:
   a. READ what was tried
   b. READ what failed
   c. Choose DIFFERENT approach
4. Record your approach
5. Implement
6. Verify
7. If SUCCESS: Record attempt, record good commit, mark complete
8. If FAILURE: Record attempt with error, check if stuck (3+ attempts)
```

### When to Mark as Stuck

A subtask should be marked as stuck if:
- 3+ attempts with different approaches all failed
- Circular fix detected (same approach tried multiple times)
- Requirements appear infeasible
- External blocker (missing dependency, etc.)

```python
# Mark subtask as stuck
subtask_id = "your-subtask-id"
reason = "Why it's stuck"

history_file = Path("memory/attempt_history.json")
with open(history_file) as f:
    history = json.load(f)

stuck_entry = {
    "subtask_id": subtask_id,
    "reason": reason,
    "escalated_at": datetime.now().isoformat(),
    "attempt_count": len(history["subtasks"][subtask_id]["attempts"])
}

history["stuck_subtasks"].append(stuck_entry)
history["subtasks"][subtask_id]["status"] = "stuck"

with open(history_file, "w") as f:
    json.dump(history, f, indent=2)

# Also update implementation_plan.json status to "blocked"
```

---

## FAILURE PATTERN INTEGRATION

### Automatic Failure Pattern Context (Enhanced Recovery)

When a subtask is being retried (attempt_count > 0), the coder agent now automatically retrieves relevant failure patterns from Graphiti memory.

**What this provides:**
- Historical context from similar past failures
- Root cause analyses from previous builds
- Proven recovery strategies that worked before
- Warnings about recurring failure patterns

**How it works:**

1. On retry attempts, `get_failure_patterns()` searches Graphiti for:
   - Similar error types (qa_rejection, build_error, test_failure)
   - Related task descriptions
   - Files with similar failure patterns

2. The failure patterns are formatted into a dedicated section:
   ```markdown
   ## Failure Pattern Analysis

   _Similar failures from past builds (learn from history):_

   ### QA Rejection

   #### Integration Issues
   - **Root Cause**: Missing import in newly added module
     _Files_: apps/backend/api/routes.py, apps/backend/models/user.py
     _Confidence_: 0.85 | _Relevance_: 0.92 | _From_: spec-145
     _Recommendations_:
     - Run linter before committing: `flake8 apps/backend/`
     - Check imports: `python -c "from api.routes import *"`
     - Use IDE autocomplete to verify imports

   ### Build Error

   #### Dependency Issues
   - **Root Cause**: Incompatible package version
     _Recurring_: ⚠️ Yes (seen in 3 builds)
     _Recommendations_:
     - Lock dependency versions in requirements.txt
     - Use virtual environment isolation
   ```

3. The AI agent uses this context to:
   - Avoid repeating the same mistakes
   - Apply proven fixes from similar situations
   - Check for recurring issues in the codebase
   - Choose recovery strategies with higher success rates

**When failure patterns are NOT included:**
- First attempt at a subtask (attempt_count = 0)
- Graphiti memory is disabled
- No similar patterns found in history

**Implementation details:**

In `apps/backend/agents/coder.py`, the failure pattern retrieval is integrated into the main agent loop:

```python
# After pattern suggestions retrieval (line 1010-1016)
if attempt_count > 0:
    failure_patterns = await get_failure_patterns(
        spec_dir=spec_dir,
        project_dir=project_dir,
        query=subtask_description,
        num_results=3,  # Top 3 most relevant patterns
    )
    if failure_patterns:
        print_status("Failure pattern context loaded for recovery", "success")

# Then added to prompt after recovery strategy (line 1035-1037)
if failure_patterns:
    prompt += f"\n\n{failure_patterns}\n"
```

**Benefits:**
- Faster recovery from failures (learn from past)
- Reduced circular fix attempts (see what didn't work)
- Higher success rate on retries (proven strategies)
- Cross-session learning (patterns persist across builds)

**Example impact:**

Without failure patterns:
- Attempt 1: Fails with import error
- Attempt 2: Fails with same import error (circular fix)
- Attempt 3: Still failing, marked as stuck

With failure patterns:
- Attempt 1: Fails with import error
- Attempt 2: System shows "Similar to spec-145 import error - solution: check flake8"
- Agent runs flake8, fixes all import issues
- Attempt 2 succeeds ✓
```
