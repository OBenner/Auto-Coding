# Context Priority Configuration

This file allows you to control which files are prioritized or excluded from AI context during autonomous builds.

## Quick Start

1. Copy `context-priority.example.json` to `context-priority.json`
2. Customize the rules for your project
3. Place it in your project's `.auto-claude/` directory

## Priority Levels

| Level | Score | Description |
|-------|-------|-------------|
| **never** | -100 | Completely exclude from context |
| **low** | -1 | Lower priority than normal |
| **normal** | 0 | Default priority (no adjustment) |
| **medium** | +1 | Higher than normal priority |
| **high** | +2 | Much higher priority |
| **always** | +100 | Always include regardless of context limits |

## Pattern Matching

File patterns use glob syntax (fnmatch):

- `**/*.py` - All Python files recursively
- `apps/backend/**` - All files in backend directory
- `*.test.js` - Test files in root only
- `core/*.py` - Python files in core directory

## Example Configuration

```json
{
  "apps/backend/core/client.py": {
    "priority": "always",
    "reason": "Critical SDK client"
  },
  "apps/backend/agents/*.py": {
    "priority": "high",
    "reason": "Core agent implementations"
  },
  "**/*_test.py": {
    "priority": "low",
    "reason": "Test files less relevant"
  },
  "node_modules/**": {
    "priority": "never",
    "reason": "Third-party dependencies"
  }
}
```

## Best Practices

1. **Always include** critical architecture files (e.g., `core/client.py`, main agent files)
2. **High priority** for core business logic and frequently modified code
3. **Never include** dependencies, build artifacts, and generated files
4. **Low priority** for tests, docs, and configuration files
5. Use specific patterns for important files, general patterns for exclusions

## How It Works

The priority system adjusts file relevance scores during context selection:

1. Files are scored by semantic relevance to the task
2. User priorities add/subtract from the base score
3. Files are sorted by final score (highest first)
4. Context is filled from highest to lowest score until token limit

## Validation

For IDE validation, add the schema reference:

```json
{
  "$schema": ".auto-claude/context-priority.schema.json",
  ...
}
```

## See Also

- [Context Optimization Documentation](../../docs/context-optimization.md)
- [Smart Context Window Spec](./specs/148-smart-context-window-optimization/spec.md)
