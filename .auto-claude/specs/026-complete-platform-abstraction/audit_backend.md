# Backend Platform Check Audit

**Date:** 2026-01-27
**Scope:** All Python files in `apps/backend/`
**Search Pattern:** `sys.platform` and `platform.system()`

## Summary

**Total Occurrences:** 13
**Legitimate (in platform module):** 6
**Needs Refactoring:** 7

## Findings

### ✅ Legitimate Uses (Platform Module)

These are in `apps/backend/core/platform/__init__.py` where platform abstraction is supposed to happen:

1. **Line 5** - Documentation comment mentioning `sys.platform`
2. **Line 57** - `system = platform.system()` - Core platform detection
3. **Line 68** - `return platform.system() == "Windows"` - isWindows() implementation
4. **Line 73** - `return platform.system() == "Darwin"` - isMacOS() implementation
5. **Line 78** - `return platform.system() == "Linux"` - isLinux() implementation
6. **Line 512** - `get_current_os(), platform.system()` - Debug/validation

### ⚠️ Needs Refactoring

These files should use the platform module instead of direct checks:

#### 1. `apps/backend/core/workspace/setup.py:253`
```python
if sys.platform == "win32":
```
**Context:** Workspace setup code
**Recommendation:** Use `from core.platform import isWindows; if isWindows():`

#### 2. `apps/backend/integrations/graphiti/queries_pkg/client.py:42`
```python
if sys.platform == "win32" and sys.version_info >= (3, 12):
```
**Context:** Graphiti client initialization
**Recommendation:** Use `from core.platform import isWindows; if isWindows() and sys.version_info >= (3, 12):`

#### 3. `apps/backend/run.py:46`
```python
if sys.platform == "win32":
```
**Context:** Main CLI entry point - Windows asyncio policy
**Recommendation:** Use `from core.platform import isWindows; if isWindows():`

#### 4. `apps/backend/runners/github/runner.py:50`
```python
if sys.platform == "win32":
```
**Context:** GitHub runner - Windows asyncio policy
**Recommendation:** Use `from core.platform import isWindows; if isWindows():`

#### 5. `apps/backend/runners/spec_runner.py:55`
```python
if sys.platform == "win32":
```
**Context:** Spec runner - Windows asyncio policy
**Recommendation:** Use `from core.platform import isWindows; if isWindows():`

#### 6. `apps/backend/ui/capabilities.py:26`
```python
if sys.platform != "win32":
```
**Context:** Capabilities detection - fork capability
**Recommendation:** Use `from core.platform import isWindows; if not isWindows():`

#### 7. `apps/backend/ui/capabilities.py:83`
```python
if sys.platform != "win32":
```
**Context:** Capabilities detection - Unix-specific capabilities
**Recommendation:** Use `from core.platform import isWindows; if not isWindows():`

## Patterns Identified

### Common Pattern: Windows Asyncio Policy
Files using: `run.py`, `github/runner.py`, `spec_runner.py`

```python
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

**Recommendation:** Create a helper function in platform module:
```python
def configure_windows_event_loop():
    """Configure Windows-specific asyncio event loop policy if needed."""
    if isWindows():
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

### Common Pattern: Unix-Only Features
Files using: `ui/capabilities.py`

```python
if sys.platform != "win32":
    # Unix-specific capability
```

**Recommendation:** Use `from core.platform import isWindows` with `if not isWindows():`
Or add helper: `isUnix() = not isWindows()`

## Refactoring Priority

### High Priority (Entry Points)
1. `run.py` - Main CLI entry point
2. `runners/spec_runner.py` - Spec runner entry point
3. `runners/github/runner.py` - GitHub runner entry point

### Medium Priority
4. `core/workspace/setup.py` - Core workspace functionality
5. `ui/capabilities.py` - UI capabilities detection

### Low Priority
6. `integrations/graphiti/queries_pkg/client.py` - Third-party integration

## Next Steps

1. **Phase 1:** Refactor entry points (`run.py`, spec_runner, github runner)
2. **Phase 2:** Add helper function for Windows asyncio configuration
3. **Phase 3:** Refactor remaining files
4. **Phase 4:** Add tests to verify platform abstraction
5. **Phase 5:** Update documentation

## Verification Command

```bash
# Count remaining direct platform checks (excluding platform module itself)
grep -rn "sys\.platform\|platform\.system()" apps/backend --include="*.py" | grep -v "apps/backend/core/platform/__init__.py" | wc -l
```

**Expected Result After Refactoring:** 0

## Notes

- All direct platform checks follow the pattern of checking for Windows (`win32`)
- The platform module itself is properly implemented with the necessary abstractions
- Most violations are straightforward to fix with imports from `core.platform`
- The Windows asyncio policy pattern appears 3 times and should be centralized
