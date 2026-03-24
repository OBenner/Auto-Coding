# Intelligent Auto-Recovery with Failure Pattern Recognition

## Overview

Auto Code's recovery system automatically detects, classifies, and learns from build failures. When a subtask fails during implementation, the system:

1. **Classifies the failure** into a known pattern type
2. **Looks up historical patterns** from Graphiti memory for similar failures
3. **Generates targeted recovery prompts** based on pattern-specific strategies
4. **Stores new patterns** for future reference, building institutional memory

## Failure Pattern Types

| Type | Description | Recovery Strategy |
|------|-------------|-------------------|
| `recurring_error` | Same error appearing across multiple attempts | Escalate approach, try alternative solutions |
| `escalating_complexity` | Each fix introduces new problems | Simplify, revert to known-good state |
| `model_limitation` | Task exceeds model capabilities | Break into smaller subtasks, use different model |
| `circular_fix` | Fixes oscillate between two states | Detect cycle, apply combined fix |
| `context_exhaustion` | Context window exceeded | Summarize context, focus on essential files |

## Architecture

### Backend Components

```text
apps/backend/
├── services/recovery.py                    # Core recovery service with pattern-aware strategies
├── analysis/failure_pattern_extractor.py    # Extracts patterns from failure history
├── integrations/graphiti/
│   └── failure_pattern_store.py            # Stores/queries patterns in Graphiti memory
├── agents/coder.py                         # Coder agent integration (recovery hook)
└── prompts/coder_recovery.md               # Recovery prompt template with pattern context
```

### Data Flow

1. **Coder agent** encounters a failure during subtask implementation
2. **Recovery service** (`services/recovery.py`) classifies the failure
3. **Pattern extractor** (`analysis/failure_pattern_extractor.py`) analyzes attempt history
4. **Pattern store** queries Graphiti for matching historical patterns
5. Recovery service generates a **pattern-aware recovery prompt** with specific strategies
6. Coder agent retries with the enhanced prompt
7. After resolution, new patterns are **stored back** to Graphiti for future use

### Pattern Storage (Graphiti)

Patterns are stored as Graphiti episodes with:
- **Pattern type** and **confidence score** (0.0–1.0)
- **Error signatures** for matching
- **Recovery recommendations** (what worked before)
- **Frequency count** (how often this pattern occurs)
- **Subtask context** (which types of tasks trigger this)

## CLI Commands

```bash
cd apps/backend

# Analyze failure patterns from a spec's attempt history
python run.py --spec 001 --failure-pattern-analyze

# Query stored failure patterns
python run.py --spec 001 --failure-pattern-query "import error"

# Filter by pattern type
python run.py --spec 001 --failure-pattern-query "timeout" --pattern-type recurring_error

# Filter by confidence
python run.py --spec 001 --failure-pattern-query "error" --min-confidence 0.7

# Show statistics
python run.py --spec 001 --failure-pattern-stats
```

## How It Works

### Failure Classification

When a subtask fails, the `FailurePatternExtractor` analyzes:
- Error message content and stack traces
- Number of previous attempts on the same subtask
- Whether the same error has appeared before
- Whether fixes are cycling between states

### Pattern Matching

The system searches Graphiti memory for similar historical patterns using:
- Semantic similarity on error descriptions
- Pattern type filtering
- Confidence-weighted ranking

### Recovery Prompt Enhancement

The recovery prompt (`coder_recovery.md`) is enhanced with:
- Historical pattern context ("This looks like a recurring_error pattern")
- Specific recommendations from past successful recoveries
- Strategy adjustments based on attempt count

## Testing

```bash
# Run failure pattern extractor tests
python -m pytest tests/test_failure_pattern_extractor.py -v

# Run failure pattern store tests (Graphiti integration)
python -m pytest apps/backend/integrations/graphiti/test_failure_pattern_store.py -v
```

## Configuration

The recovery system works automatically when Graphiti memory is enabled:

```bash
# In apps/backend/.env
GRAPHITI_ENABLED=true
```

Pattern recognition thresholds can be adjusted in `services/recovery.py`:
- Minimum confidence for pattern application
- Maximum recovery attempts before escalation
- Pattern type detection heuristics
