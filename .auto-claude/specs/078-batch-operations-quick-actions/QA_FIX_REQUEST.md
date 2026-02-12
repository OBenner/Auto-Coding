# QA Fix Request

**Status**: REJECTED
**Date**: 2025-02-10
**QA Session**: 1

## Critical Issues to Fix

### 1. TypeScript Compilation Errors (Blocking)

All 9 TypeScript errors MUST be fixed before sign-off.

#### Error 1.1: Invalid Task Status Comparison
**File**: `apps/frontend/src/main/ipc-handlers/task/execution-handlers.ts:1244`
**Problem**: Code checks for `'planning'` status which doesn't exist in TaskStatus type
**Current Code**:
```typescript
if (task.status === 'backlog' || task.status === 'planning') {
```
**Valid TaskStatus values**: `'backlog' | 'queue' | 'in_progress' | 'ai_review' | 'human_review' | 'done' | 'pr_created' | 'error'`
**Fix**: Remove the invalid comparison:
```typescript
if (task.status === 'backlog') {
```

---

#### Error 1.2: batchRunQA Type Definition Missing
**File**: `apps/frontend/src/renderer/components/BatchQADialog.tsx:116`
**Problem**: TypeScript cannot find `batchRunQA` on ElectronAPI type
**Note**: The method IS implemented in task-api.ts (line 77, 205) but type definition may not be properly exported
**Fix**: Verify that `src/shared/types/ipc.ts` exports the ElectronAPI interface with batchRunQA method signature:
```typescript
batchRunQA: (taskId: string) => Promise<IPCResult<{ success: boolean; issues?: Array<{ message: string; file?: string }> }>>;
```

---

#### Error 1.3: Null vs Undefined Type Mismatch (BatchQADialog)
**File**: `apps/frontend/src/renderer/components/BatchQADialog.tsx:162`
**Problem**: `Type 'null' is not assignable to type 'string | undefined'`
**Fix**: Find the assignment and either:
- Change `null` to `undefined`
- Or update the type definition to accept `null`

---

#### Error 1.4: Null vs Undefined Type Mismatch (BatchStatusUpdateDialog)
**File**: `apps/frontend/src/renderer/components/BatchStatusUpdateDialog.tsx:156`
**Problem**: `Type 'null' is not assignable to type 'string | undefined'`
**Fix**: Same as Error 1.3

---

#### Error 1.5: KeyboardShortcutAction Import Error
**File**: `apps/frontend/src/renderer/components/settings/KeyboardShortcutsSettings.tsx:21`
**Problem**: `KeyboardShortcutAction` is imported from store but not exported there. It's defined in `shared/types/settings.ts`
**Current Import**:
```typescript
import { useKeyboardShortcutsStore, formatKeyCombination, parseKeyboardEvent, type KeyboardShortcutAction } from '../../stores/keyboard-shortcuts-store';
```
**Fix**: Import type from correct location:
```typescript
import { useKeyboardShortcutsStore, formatKeyCombination, parseKeyboardEvent } from '../../stores/keyboard-shortcuts-store';
import type { KeyboardShortcutAction } from '../../../shared/types/settings';
```

---

#### Error 1.6-1.8: Index Signature Errors (KeyboardShortcutsSettings)
**File**: `apps/frontend/src/renderer/components/settings/KeyboardShortcutsSettings.tsx:91,112,183`
**Problem**: `Element implicitly has an 'any' type because expression of type 'KeyboardShortcutAction' can't be used to index type`
**Fix**: Add type assertion or use a helper function:
```typescript
// Option 1: Type assertion
const description = (actionDescriptions as Record<KeyboardShortcutAction, string>)[action];

// Option 2: Ensure Record type is properly defined
const actionDescriptions: Record<KeyboardShortcutAction, string> = { ... };
```

---

## Verification Steps After Fixes

1. **Verify TypeScript compilation**:
```bash
cd apps/frontend && npx tsc --noEmit
```
Expected: No errors

2. **Verify build succeeds**:
```bash
cd apps/frontend && npm run build
```
Expected: Build completes successfully

3. **Run unit tests**:
```bash
cd apps/frontend && npm test -- --run
```
Expected: All new tests pass (timeout failures in existing tests are acceptable)

4. **Manual testing checklist**:
- Press Cmd/Ctrl+K → Command palette opens
- Open Settings → Keyboard shortcuts section visible
- Customize a shortcut → Save → Restart app → Change persists
- Select multiple tasks in kanban → Batch QA button appears
- Run batch QA → Progress shows → Results display
- Navigate to GitHub/GitLab issues → Quick create button visible

---

## After Fixes

Once fixes are complete:
1. Commit with message: `fix: resolve TypeScript compilation errors in batch operations (qa-requested)`
2. QA will automatically re-run
3. Loop continues until all TypeScript errors are resolved

---

## Priority

**HIGH PRIORITY** - These are compilation errors that completely block the feature from running. The implementation cannot be tested or deployed until TypeScript compiles successfully.

---

## Notes

- The implementation logic appears sound
- All components are created and wired together
- i18n translations are complete (EN/FR)
- The only blockers are TypeScript type errors
- Unit tests mostly pass (2843/2856 passed, failures are timeouts in existing tests)
