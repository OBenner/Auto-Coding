# Token Optimization Guide

Practical strategies for reducing token consumption and associated costs when using Auto Code.

## Quick Reference

| Strategy | Impact | Effort |
|----------|--------|--------|
| Use specific, scoped requests | High | Low |
| Set appropriate thinking levels | High | Low |
| Choose right model for task | High | Medium |
| Manage context window | Medium | Low |
| Use compaction settings | Medium | Low |

---

## 1. Request Structuring

### Be Specific and Scoped

The more precise your task description, the less exploration and back-and-forth required.

**DO:**
```
Add a logout button to the header component in apps/frontend/src/components/Header.tsx.
It should call the existing logout() function from useAuth hook.
```

**DON'T:**
```
Add a logout feature to the app
```

### Key Principles

- **Name specific files** when you know them
- **Reference existing functions/components** to avoid rediscovery
- **Set clear acceptance criteria** to prevent over-engineering
- **Scope to one service** when possible (backend OR frontend, not both)

### Task Description Guidelines

| Description Length | Complexity | Thinking Budget |
|-------------------|------------|-----------------|
| < 100 chars | Simple | low (1,024 tokens) |
| 100-500 chars | Moderate | medium (4,096 tokens) |
| 500-1500 chars | Complex | high (16,384 tokens) |
| > 1500 chars | Very Complex | ultrathink (63,999 tokens) |

---

## 2. Context Management

### Minimize Context Window Usage

Each MCP server adds ~10-30K tokens of context. Auto Code loads only what's needed per agent type, but you can further optimize.

### Agent MCP Server Loading

| Agent Type | MCP Servers Loaded | Typical Context |
|------------|-------------------|-----------------|
| spec_gatherer | None | ~5K |
| spec_writer | None | ~5K |
| planner | context7, graphiti, auto-claude | ~45K |
| coder | context7, graphiti, auto-claude | ~45K |
| qa_reviewer | context7, graphiti, auto-claude, browser | ~60K |

### Tips for Reducing Context

1. **Scope file reads** - Reference specific files rather than directories
2. **Use simple tasks for simple work** - The complexity assessor routes simple tasks to lightweight pipelines
3. **Break complex tasks** - Split multi-service features into separate specs

### Session Management

- **New sessions start fresh** - Each spec run starts with minimal context
- **Compaction reduces carry-over** - Phase outputs are summarized before passing to next phase
- **Graphiti memory is selective** - Only relevant memories are retrieved, not full history

---

## 3. Model Selection

### When to Use Each Model

| Model | Cost | Best For | Avoid For |
|-------|------|----------|-----------|
| **Haiku** | Lowest | Summaries, simple extractions, formatting | Complex reasoning, architecture decisions |
| **Sonnet** | Medium | Most coding tasks, planning, QA | Ultra-complex analysis |
| **Opus** | Highest | Complex architecture, deep analysis | Routine tasks |

### Default Model Assignments

Auto Code assigns models by phase. You can override via task metadata or CLI.

| Phase | Default Model | Thinking Level |
|-------|---------------|----------------|
| Spec Creation | Sonnet | medium-ultrathink |
| Planning | Sonnet | high |
| Coding | Sonnet | none |
| QA Review | Sonnet | high |

### Override Model Selection

```bash
# Force a specific model for all phases
python run.py --spec 001 --model haiku

# Or configure per-task in the UI with "Auto" profile for phase-specific models
```

---

## 4. Thinking Budget Awareness

### Understanding Extended Thinking

Extended thinking tokens are billed as **output tokens** (2-5x more expensive than input).

| Thinking Level | Token Budget | Use Case |
|----------------|--------------|----------|
| none | 0 | Routine coding, formatting |
| low | 1,024 | Simple analysis, quick decisions |
| medium | 4,096 | Standard planning, moderate complexity |
| high | 16,384 | Deep analysis, QA review |
| ultrathink | 63,999 | Complex architecture, self-critique |

### When Thinking Budget Matters

**High thinking budget justified:**
- Architectural decisions affecting multiple components
- QA review requiring deep code analysis
- Self-critique loops for spec quality
- Complex debugging scenarios

**Low/no thinking budget sufficient:**
- Direct code implementation with clear instructions
- File formatting and refactoring
- Simple bug fixes with known solutions
- Commit message generation

### Automatic Budget Selection

Auto Code's `suggest_thinking_budget()` function analyzes:
- Description length (< 100 chars = simple)
- File count (1-3 files = simple)
- Service count (1 service = simpler scope)

Result: Automatic routing to appropriate thinking level.

---

## 5. Compaction Settings

### What is Compaction?

After each spec phase, outputs are summarized before passing to the next phase. This prevents context window overflow.

### Compaction Levels

| Level | Target Words | Max Input | Use Case |
|-------|-------------|-----------|----------|
| LIGHT | 500 | 15,000 chars | Complex phases needing detail |
| MEDIUM | 250 | 12,000 chars | Default for most phases |
| AGGRESSIVE | 100 | 8,000 chars | Token-constrained contexts |

### Default Compaction by Phase

- Discovery, spec_writing, self_critique: LIGHT (preserve detail)
- Requirements, research, context: MEDIUM (balanced)
- Validation, quick_spec: MEDIUM (balanced)

---

## 6. Practical Examples

### Example 1: Simple Bug Fix

**Task:** "Fix typo in README.md line 45: 'recieve' should be 'receive'"

- Complexity: Very low
- Thinking budget: none
- Model: Haiku (sufficient)
- Estimated tokens: < 2K

### Example 2: Feature Addition

**Task:** "Add dark mode toggle to settings page. Use existing ThemeContext from src/context/theme.tsx. Store preference in localStorage."

- Complexity: Medium
- Thinking budget: medium (4,096)
- Model: Sonnet
- Estimated tokens: 15-30K

### Example 3: Complex Architecture

**Task:** "Design and implement real-time notification system with WebSocket support, message queue, and offline sync"

- Complexity: Very high
- Thinking budget: ultrathink (63,999)
- Model: Sonnet/Opus
- Estimated tokens: 50-100K+

---

## 7. Monitoring Token Usage

### Enable Debug Mode

```bash
DEBUG=true python run.py --spec 001
```

Debug mode logs:
- Token counts per phase
- MCP server context overhead
- Model and thinking level used

### Review Build Costs

After completion, check:
- `.auto-claude/specs/XXX/build-progress.txt` for phase summaries
- Debug logs for detailed token breakdowns

---

## 8. Cost Reduction Checklist

Before creating a spec:

- [ ] Is task description specific and scoped?
- [ ] Have I named specific files when known?
- [ ] Is this one service or can I split it?
- [ ] Did I set appropriate complexity/thinking level?
- [ ] For simple tasks, am I using "simple" complexity?

During build:

- [ ] Check debug logs for unexpected token spikes
- [ ] Review if correct model is being used per phase
- [ ] Verify compaction is working (phase summaries are concise)

After build:

- [ ] Note which phases consumed most tokens
- [ ] Identify patterns for future optimization
- [ ] Record gotchas for similar future tasks

---

## Summary

| Optimization | Action | Expected Savings |
|--------------|--------|------------------|
| Specific requests | Name files, reference functions | 20-40% |
| Right thinking level | Match to complexity | 30-50% |
| Appropriate model | Haiku for simple, Sonnet for complex | 20-60% |
| Scoped tasks | One service at a time | 15-25% |
| Debug monitoring | Identify inefficiencies | Varies |

For more details, see:
- `apps/backend/phase_config.py` - Thinking budget configuration
- `apps/backend/spec/compaction.py` - Compaction settings
- `apps/backend/agents/tools_pkg/models.py` - Agent configurations
