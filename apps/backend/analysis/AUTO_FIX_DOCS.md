# Auto-Fix Generation

## Overview

The Predictive Scanner now includes **auto-fix generation** capabilities using the Claude Agent SDK. When code quality issues are detected, the system can automatically generate specific, ready-to-apply code fixes.

## Features

- **Automatic fix generation** for critical and high-severity issues
- **Multiple fix approaches** with context on when to use each
- **Risk assessment** for each generated fix
- **Testing advice** to verify fixes work correctly
- **High confidence scores** to indicate fix reliability

## Supported Issue Categories

### Bug Fixes (Highest Priority)
- `NoneType error` - Guard clauses and null checks
- `IndexError` - Bounds checking for list access
- `KeyError` - Dictionary key validation
- `Division by zero` - Zero denominator handling
- `Missing error handling` - Try/except blocks

### Performance Fixes
- `N+1 query` - Bulk database operations
- `Memory leak` - Resource cleanup patterns

### Code Smell Fixes
- `Long function` - Function extraction
- `Deep nesting` - Early returns and guard clauses

## Usage

### Basic Scan with Auto-Fixes

```python
from pathlib import Path
from analysis.predictive_scanner import PredictiveScanner

scanner = PredictiveScanner()
result = scanner.scan(
    project_dir=Path("/path/to/project"),
    run_llm_analysis=True  # Enables auto-fix generation
)

# Issues with auto-fixes
for issue in result.issues:
    if issue.auto_fix:
        print(f"Fix available for {issue.file}:{issue.line}")
        print(f"Fixed code:\n{issue.auto_fix['fixed_code']}")
```

### Generate Auto-Fix for Specific Issue

```python
from analysis.predictive_scanner import PredictiveIssue, generate_auto_fix

# Create issue from detector
issue = PredictiveIssue(
    issue_type="bug",
    severity="critical",
    category="NoneType error",
    # ... other fields ...
)

# Generate fix
auto_fix = generate_auto_fix(issue)

if auto_fix:
    print(f"Fix: {auto_fix['fixed_code']}")
    print(f"Confidence: {auto_fix['confidence']}")
```

### CLI Usage

```bash
# Run scan with auto-fixes (requires --no-llm flag to be absent)
python -m analysis.predictive_scanner /path/to/project

# Output includes auto-fix information for fixable issues
```

## Auto-Fix Structure

Each auto-fix contains:

```json
{
  "fix_type": "guard_clause | conditional_assignment | bulk_operation | error_handling | refactoring",
  "original_code": "user_id = user.id",
  "fixed_code": "if user is None:\n    raise ValueError('User not found')\nuser_id = user.id",
  "description": "Add null check before accessing user.id to prevent AttributeError",
  "applies_to_line": 42,
  "scope": "single_line | multi_line | function | file",
  "confidence": 0.95,
  "risks": ["Calling code may not expect ValueError"],
  "testing_advice": "Test with user=None, user={id: 1}, and user={id: 0} scenarios",
  "alternate_fixes": [
    {
      "approach": "early_return",
      "code": "if user is None:\n    return None\nuser_id = user.id",
      "when_to_use": "If None is a valid expected value"
    }
  ]
}
```

## Fix Patterns

### 1. Guard Clause (for NoneType errors)

```python
# Before
user_id = user.id

# After
if user is None:
    raise ValueError('User not found')
user_id = user.id
```

### 2. Bulk Operation (for N+1 queries)

```python
# Before
for post in posts:
    user = db.query(User).filter(User.id == post.user_id).first()
    post.user_name = user.name

# After
user_ids = [p.user_id for p in posts]
users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
for post in posts:
    user = users.get(post.user_id)
    post.user_name = user.name if user else "Unknown"
```

### 3. Error Handling (for missing try/except)

```python
# Before
data = json.loads(raw_data)

# After
try:
    data = json.loads(raw_data)
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON: {e}")
    raise ValueError(f"Invalid JSON data: {e}") from e
```

## Configuration

### Environment Variables

```bash
# Enable/disable auto-fix generation
PREDICTIVE_ANALYSIS_ENABLED=true

# Specify model for auto-fix generation
AUTO_FIX_MODEL=claude-haiku-4-5-20251001
```

### Model Selection

- **Haiku** (default): Fast, cost-effective for simple fixes
- **Sonnet**: Higher quality for complex refactoring
- **Opus**: Best for critical bugs requiring deep analysis

## Testing

### Run Test Script

```bash
cd apps/backend
python analysis/test_auto_fix.py
```

This will:
1. Create a sample issue
2. Generate an auto-fix
3. Display the fix with all metadata
4. Show alternate approaches

### Manual Verification

```python
# 1. Detect issues
scanner = PredictiveScanner()
result = scanner.scan(project_dir)

# 2. Review auto-fixes
for issue in result.issues:
    if issue.auto_fix:
        print(f"Issue: {issue.title}")
        print(f"Fix: {issue.auto_fix['fixed_code']}")
        print(f"Confidence: {issue.auto_fix['confidence']}")
        print(f"Risks: {issue.auto_fix['risks']}")
        print("-" * 60)

# 3. Manually verify fixes
# 4. Apply fixes to code
# 5. Run tests to verify
```

## Best Practices

### 1. Review Before Applying

Even with high confidence scores, always review auto-fixes:
- Check if the fix matches your code style
- Verify edge cases are handled
- Ensure tests exist for the code

### 2. Test Thoroughly

For each applied fix:
- Run existing test suite
- Add tests for the specific issue
- Test edge cases mentioned in `testing_advice`
- Monitor for regressions

### 3. Consider Alternatives

The `alternate_fixes` array provides different approaches:
- **Guard clause**: Use when invalid state should raise error
- **Early return**: Use when None is valid
- **Default value**: Use when fallback makes sense

### 4. Handle Risks

Review the `risks` array and:
- Update calling code if needed
- Add error handling
- Update documentation
- Communicate changes to team

## Limitations

### When Auto-Fixes Are Not Generated

Auto-fixes are only generated for issues that meet these criteria:
- Severity is `critical` or `high`
- Code snippet is available
- File and line number are known
- Issue category is in fixable list

### Requires Manual Review

Auto-fixes have low confidence (< 0.5) when:
- Issue requires business logic context
- Multiple valid fix approaches exist
- Code pattern is unusual
- Dependencies are unclear

### Not a Replacement For

- Human code review
- Understanding business requirements
- Architectural decisions
- Security audits

## Examples

### Example 1: Critical NoneType Error

**Issue:**
```python
user_id = user.id  # user may be None
```

**Auto-Fix:**
```python
if user is None:
    raise ValueError('User not found')
user_id = user.id
```

**Confidence:** 0.98
**Testing:** Test with valid user, None user, invalid user_id

### Example 2: N+1 Query

**Issue:**
```python
for post in posts:
    author = db.query(User).filter(User.id == post.author_id).first()
```

**Auto-Fix:**
```python
author_ids = [p.author_id for p in posts]
authors = {a.id: a for a in db.query(User).filter(User.id.in_(author_ids)).all()}
for post in posts:
    author = authors.get(post.author_id)
```

**Confidence:** 0.95
**Testing:** Verify mappings, test empty list, test missing IDs

## Troubleshooting

### Auto-fixes Not Generated

**Problem:** No auto-fixes in results

**Solutions:**
1. Check `PREDICTIVE_ANALYSIS_ENABLED=true`
2. Verify authentication token is set: `claude`
3. Ensure issue severity is `critical` or `high`
4. Confirm code_snippet is available
5. Check issue category is fixable

### Fix Syntax Errors

**Problem:** Generated fix has syntax error

**Solutions:**
1. Report the issue with code snippet
2. Try alternate fix approach
3. Manually adjust fix based on pattern
4. Check if fix_type matches issue category

### Low Confidence Scores

**Problem:** Fix has low confidence (< 0.5)

**Solutions:**
1. Review manually before applying
2. Consider alternate approaches
3. Add tests to verify fix
4. May need context beyond available code

## Contributing

To add support for new issue categories:

1. Add pattern to `prompts/auto_fix_generation.md`
2. Add category to `_should_generate_fix()` method
3. Update this documentation with examples
4. Add test cases

## Related Files

- `analysis/predictive_scanner.py` - Main implementation
- `analysis/prompts/auto_fix_generation.md` - LLM prompt
- `analysis/test_auto_fix.py` - Test script
- `analysis/failure_analyzer.py` - Pattern reference
