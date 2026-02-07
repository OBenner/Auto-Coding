# Store: Kanban Settings Store

Zustand store for managing Kanban board column preferences including width, collapse state, and lock state.

## Overview

**Type:** Zustand State Management Store
**Location:** `apps/frontend/src/renderer/stores/kanban-settings-store.ts`
**Category:** State Management / UI Preferences
**Status:** Stable

### Purpose

The Kanban Settings Store manages per-project column preferences for the Kanban board view. It persists column width, collapse state, and lock state to localStorage, allowing users to customize their board layout. Preferences are scoped by project ID, enabling different layouts for different projects.

### Key Features

- **Column Width Management:** Adjust column widths within 180-600px range with automatic clamping
- **Collapse State:** Toggle columns between full width and collapsed (48px vertical strip)
- **Lock State:** Prevent accidental column width changes by locking columns
- **localStorage Persistence:** Auto-save preferences per project with validation
- **Safe Defaults:** Automatic fallback to defaults on invalid/missing data
- **Width Constraints:** Enforce minimum (180px) and maximum (600px) column widths
- **Validation:** Type-safe preference validation before applying stored data

### Use Cases

- **Custom Board Layouts:** Users can resize columns to fit their workflow (e.g., wider "In Progress" column)
- **Focus Mode:** Collapse unused columns to focus on active work
- **Screen Space Optimization:** Adjust column widths for different monitor sizes
- **Lock Preferred Layouts:** Prevent accidental resizing after finding optimal layout
- **Per-Project Preferences:** Different projects can have different column layouts
- **Recovery from Corruption:** Automatic reset to defaults if localStorage data is invalid

---

## Installation / Import

### Store Hook Import

```typescript
import { useKanbanSettingsStore } from '@/renderer/stores/kanban-settings-store';
```

### Type and Constant Imports

```typescript
import type { ColumnPreferences, KanbanColumnPreferences } from '@/renderer/stores/kanban-settings-store';
import {
  DEFAULT_COLUMN_WIDTH,
  MIN_COLUMN_WIDTH,
  MAX_COLUMN_WIDTH,
  COLLAPSED_COLUMN_WIDTH
} from '@/renderer/stores/kanban-settings-store';
```

### Dependencies

**Required:**
- `zustand` - State management library
- `@/shared/constants/task` - TaskStatusColumn and TASK_STATUS_COLUMNS

**Optional:**
- None (all dependencies are required)

---

## Store State

### State Shape

```typescript
interface KanbanSettingsState {
  // Core state
  columnPreferences: KanbanColumnPreferences | null; // Preferences for all columns (null until initialized)

  // Actions
  initializePreferences: () => void;
  setColumnWidth: (column: TaskStatusColumn, width: number) => void;
  toggleColumnCollapsed: (column: TaskStatusColumn) => void;
  setColumnCollapsed: (column: TaskStatusColumn, isCollapsed: boolean) => void;
  toggleColumnLocked: (column: TaskStatusColumn) => void;
  setColumnLocked: (column: TaskStatusColumn, isLocked: boolean) => void;
  loadPreferences: (projectId: string) => void;
  savePreferences: (projectId: string) => boolean;
  resetPreferences: (projectId: string) => void;
  getColumnPreferences: (column: TaskStatusColumn) => ColumnPreferences;
}
```

### Column Preferences Structure

Each column has three preference fields:

| Field | Type | Range/Values | Description |
|-------|------|--------------|-------------|
| `width` | `number` | 180-600 | Column width in pixels |
| `isCollapsed` | `boolean` | true/false | Whether column is collapsed to 48px vertical strip |
| `isLocked` | `boolean` | true/false | Whether width changes are prevented |

**Note:** When `isLocked` is true, `setColumnWidth()` is a no-op for that column.

---

## Actions

### Initialization

#### `initializePreferences()`

**Description:** Initialize column preferences with defaults if not already set. Should be called on mount before any other operations.

**Parameters:** None

**Returns:** void

**Example:**
```typescript
const { initializePreferences } = useKanbanSettingsStore();

// In component mount effect
useEffect(() => {
  initializePreferences();
}, []);
```

**Behavior:**
- If `columnPreferences` is `null`, creates default preferences for all columns
- If already initialized, does nothing (idempotent)
- Default: 320px width, not collapsed, not locked

---

### Column Width Management

#### `setColumnWidth(column: TaskStatusColumn, width: number)`

**Description:** Set the width of a column with automatic clamping to valid range (180-600px). Respects locked state.

**Parameters:**
- `column` (TaskStatusColumn) - Target column ('not_started', 'in_progress', 'qa_ready', etc.)
- `width` (number) - Desired width in pixels (will be clamped to 180-600 range)

**Returns:** void

**Example:**
```typescript
const { setColumnWidth } = useKanbanSettingsStore();

// Set column width during resize
const handleResize = (newWidth: number) => {
  setColumnWidth('in_progress', newWidth);
};

// Width is automatically clamped
setColumnWidth('in_progress', 1000); // Clamped to 600px
setColumnWidth('in_progress', 50);   // Clamped to 180px
```

**Behavior:**
- Clamps width to MIN_COLUMN_WIDTH (180px) - MAX_COLUMN_WIDTH (600px)
- No-op if column is locked (`isLocked: true`)
- No-op if `columnPreferences` is null (call `initializePreferences()` first)

---

### Collapse State Management

#### `toggleColumnCollapsed(column: TaskStatusColumn)`

**Description:** Toggle a column between collapsed (48px vertical strip) and expanded state.

**Parameters:**
- `column` (TaskStatusColumn) - Target column to toggle

**Returns:** void

**Example:**
```typescript
const { toggleColumnCollapsed } = useKanbanSettingsStore();

// Toggle on button click
<button onClick={() => toggleColumnCollapsed('not_started')}>
  {isCollapsed ? 'Expand' : 'Collapse'}
</button>
```

**Behavior:**
- Flips `isCollapsed` boolean
- Does NOT affect `width` (width is preserved when re-expanding)
- No-op if `columnPreferences` is null

#### `setColumnCollapsed(column: TaskStatusColumn, isCollapsed: boolean)`

**Description:** Explicitly set a column's collapsed state (instead of toggling).

**Parameters:**
- `column` (TaskStatusColumn) - Target column
- `isCollapsed` (boolean) - Desired collapsed state

**Returns:** void

**Example:**
```typescript
const { setColumnCollapsed } = useKanbanSettingsStore();

// Collapse all columns
['not_started', 'in_progress', 'qa_ready', 'done'].forEach(col => {
  setColumnCollapsed(col, true);
});

// Expand specific column
setColumnCollapsed('in_progress', false);
```

**Behavior:**
- Sets `isCollapsed` to the specified value
- No-op if `columnPreferences` is null

---

### Lock State Management

#### `toggleColumnLocked(column: TaskStatusColumn)`

**Description:** Toggle a column's lock state. Locked columns cannot be resized.

**Parameters:**
- `column` (TaskStatusColumn) - Target column to toggle lock

**Returns:** void

**Example:**
```typescript
const { toggleColumnLocked } = useKanbanSettingsStore();

// Lock/unlock column on click
<button onClick={() => toggleColumnLocked('in_progress')}>
  {isLocked ? '🔒 Locked' : '🔓 Unlocked'}
</button>
```

**Behavior:**
- Flips `isLocked` boolean
- When locked, `setColumnWidth()` becomes a no-op for that column
- No-op if `columnPreferences` is null

#### `setColumnLocked(column: TaskStatusColumn, isLocked: boolean)`

**Description:** Explicitly set a column's lock state (instead of toggling).

**Parameters:**
- `column` (TaskStatusColumn) - Target column
- `isLocked` (boolean) - Desired lock state

**Returns:** void

**Example:**
```typescript
const { setColumnLocked } = useKanbanSettingsStore();

// Lock all columns
['not_started', 'in_progress', 'qa_ready', 'done'].forEach(col => {
  setColumnLocked(col, true);
});

// Unlock specific column
setColumnLocked('in_progress', false);
```

**Behavior:**
- Sets `isLocked` to the specified value
- No-op if `columnPreferences` is null

---

### Persistence

#### `loadPreferences(projectId: string)`

**Description:** Load column preferences from localStorage for a specific project. Automatically validates data and falls back to defaults if invalid.

**Parameters:**
- `projectId` (string) - Project identifier for preference scoping

**Returns:** void

**Example:**
```typescript
const { loadPreferences } = useKanbanSettingsStore();

// Load preferences when project changes
useEffect(() => {
  if (currentProjectId) {
    loadPreferences(currentProjectId);
  }
}, [currentProjectId]);
```

**Behavior:**
- Reads from localStorage key: `kanban-column-prefs-{projectId}`
- Validates structure before applying (checks all columns exist, types are correct, widths in range)
- Falls back to defaults if:
  - No stored data exists
  - Data is invalid JSON
  - Data structure is incomplete/incorrect
  - Width values are out of range
- Logs warnings/errors to console on failure

**localStorage Key Format:** `kanban-column-prefs-{projectId}`

#### `savePreferences(projectId: string)`

**Description:** Save current column preferences to localStorage for a specific project.

**Parameters:**
- `projectId` (string) - Project identifier for preference scoping

**Returns:** boolean - `true` if save succeeded, `false` if failed

**Example:**
```typescript
const { savePreferences } = useKanbanSettingsStore();

// Save after width change
const handleResizeEnd = () => {
  const success = savePreferences(currentProjectId);
  if (!success) {
    console.error('Failed to save column preferences');
  }
};

// Auto-save on changes (debounced)
useEffect(() => {
  const timer = setTimeout(() => {
    savePreferences(currentProjectId);
  }, 500); // Debounce for 500ms

  return () => clearTimeout(timer);
}, [columnPreferences, currentProjectId]);
```

**Behavior:**
- Serializes `columnPreferences` to JSON
- Writes to localStorage key: `kanban-column-prefs-{projectId}`
- Returns `false` if `columnPreferences` is null
- Returns `false` if localStorage write fails (quota exceeded, private browsing, etc.)
- Logs errors to console on failure

#### `resetPreferences(projectId: string)`

**Description:** Reset column preferences to defaults and clear localStorage for a project.

**Parameters:**
- `projectId` (string) - Project identifier for preference scoping

**Returns:** void

**Example:**
```typescript
const { resetPreferences } = useKanbanSettingsStore();

// Reset button handler
const handleReset = () => {
  if (confirm('Reset all column settings to defaults?')) {
    resetPreferences(currentProjectId);
  }
};
```

**Behavior:**
- Removes localStorage key: `kanban-column-prefs-{projectId}`
- Sets `columnPreferences` to defaults (320px, not collapsed, not locked)
- Logs errors to console on failure

---

### Getters

#### `getColumnPreferences(column: TaskStatusColumn)`

**Description:** Get preferences for a single column. Returns safe defaults if store is uninitialized.

**Parameters:**
- `column` (TaskStatusColumn) - Target column

**Returns:** ColumnPreferences - Preferences for the column (width, isCollapsed, isLocked)

**Example:**
```typescript
const { getColumnPreferences } = useKanbanSettingsStore();

const columnPrefs = getColumnPreferences('in_progress');

// Use in component
const columnStyle = {
  width: columnPrefs.isCollapsed ? COLLAPSED_COLUMN_WIDTH : columnPrefs.width,
  cursor: columnPrefs.isLocked ? 'not-allowed' : 'col-resize'
};
```

**Behavior:**
- Returns actual preferences if `columnPreferences` is initialized
- Returns defaults if `columnPreferences` is null:
  ```typescript
  {
    width: DEFAULT_COLUMN_WIDTH,  // 320
    isCollapsed: false,
    isLocked: false
  }
  ```

---

## Type Definitions

### TypeScript Types

```typescript
/**
 * Column preferences for a single kanban column
 */
interface ColumnPreferences {
  /** Column width in pixels (180-600px range) */
  width: number;
  /** Whether the column is collapsed (narrow vertical strip) */
  isCollapsed: boolean;
  /** Whether the column width is locked (prevents resize) */
  isLocked: boolean;
}

/**
 * All column preferences keyed by status column
 */
type KanbanColumnPreferences = Record<TaskStatusColumn, ColumnPreferences>;

/**
 * Task status column types
 * (from @/shared/constants/task)
 */
type TaskStatusColumn =
  | 'not_started'
  | 'in_progress'
  | 'qa_ready'
  | 'blocked'
  | 'qa_fixing'
  | 'qa_passed'
  | 'done';
```

---

## Constants

### Width Constraints

```typescript
/** Default column width in pixels */
export const DEFAULT_COLUMN_WIDTH = 320;

/** Minimum column width in pixels */
export const MIN_COLUMN_WIDTH = 180;

/** Maximum column width in pixels */
export const MAX_COLUMN_WIDTH = 600;

/** Collapsed column width in pixels (vertical strip) */
export const COLLAPSED_COLUMN_WIDTH = 48;
```

### localStorage Key

```typescript
/** localStorage key prefix for kanban settings persistence */
const KANBAN_SETTINGS_KEY_PREFIX = 'kanban-column-prefs';

// Actual key: `kanban-column-prefs-{projectId}`
```

---

## Usage Examples

### Basic Setup (Component Mount)

```typescript
import { useEffect } from 'react';
import { useKanbanSettingsStore } from '@/renderer/stores/kanban-settings-store';

function KanbanBoard({ projectId }: { projectId: string }) {
  const {
    initializePreferences,
    loadPreferences,
    getColumnPreferences
  } = useKanbanSettingsStore();

  // Initialize on mount
  useEffect(() => {
    initializePreferences();
    loadPreferences(projectId);
  }, [projectId]);

  // Use preferences
  const inProgressPrefs = getColumnPreferences('in_progress');

  return (
    <div style={{ width: inProgressPrefs.width }}>
      {/* Column content */}
    </div>
  );
}
```

### Column Resizing with Auto-Save

```typescript
import { useState, useEffect } from 'react';
import { useKanbanSettingsStore } from '@/renderer/stores/kanban-settings-store';

function ResizableColumn({ column, projectId }: Props) {
  const { setColumnWidth, savePreferences, getColumnPreferences } = useKanbanSettingsStore();
  const prefs = getColumnPreferences(column);

  const handleResize = (newWidth: number) => {
    setColumnWidth(column, newWidth);
  };

  // Auto-save with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      savePreferences(projectId);
    }, 500);

    return () => clearTimeout(timer);
  }, [prefs.width, projectId]);

  return (
    <div
      style={{
        width: prefs.width,
        cursor: prefs.isLocked ? 'not-allowed' : 'col-resize'
      }}
      onMouseDown={prefs.isLocked ? undefined : startResize}
    >
      {/* Column content */}
    </div>
  );
}
```

### Collapse/Expand Column

```typescript
import { useKanbanSettingsStore, COLLAPSED_COLUMN_WIDTH } from '@/renderer/stores/kanban-settings-store';

function ColumnHeader({ column }: { column: TaskStatusColumn }) {
  const { toggleColumnCollapsed, getColumnPreferences, savePreferences } = useKanbanSettingsStore();
  const prefs = getColumnPreferences(column);

  const handleToggleCollapse = () => {
    toggleColumnCollapsed(column);
    savePreferences(currentProjectId); // Save immediately
  };

  return (
    <div style={{ width: prefs.isCollapsed ? COLLAPSED_COLUMN_WIDTH : prefs.width }}>
      <button onClick={handleToggleCollapse}>
        {prefs.isCollapsed ? '→' : '←'}
      </button>
      {!prefs.isCollapsed && <h2>{column}</h2>}
    </div>
  );
}
```

### Lock/Unlock Column

```typescript
import { useKanbanSettingsStore } from '@/renderer/stores/kanban-settings-store';

function ColumnControls({ column, projectId }: Props) {
  const { toggleColumnLocked, getColumnPreferences, savePreferences } = useKanbanSettingsStore();
  const prefs = getColumnPreferences(column);

  const handleToggleLock = () => {
    toggleColumnLocked(column);
    savePreferences(projectId);
  };

  return (
    <button onClick={handleToggleLock} title={prefs.isLocked ? 'Unlock column' : 'Lock column'}>
      {prefs.isLocked ? '🔒' : '🔓'}
    </button>
  );
}
```

### Reset to Defaults

```typescript
import { useKanbanSettingsStore } from '@/renderer/stores/kanban-settings-store';

function SettingsPanel({ projectId }: { projectId: string }) {
  const { resetPreferences } = useKanbanSettingsStore();

  const handleReset = () => {
    if (confirm('Reset all column settings to defaults?')) {
      resetPreferences(projectId);
    }
  };

  return (
    <button onClick={handleReset}>
      Reset Column Layout
    </button>
  );
}
```

### Bulk Operations

```typescript
import { useKanbanSettingsStore } from '@/renderer/stores/kanban-settings-store';
import { TASK_STATUS_COLUMNS } from '@/shared/constants/task';

function BulkActions({ projectId }: { projectId: string }) {
  const { setColumnCollapsed, setColumnLocked, savePreferences } = useKanbanSettingsStore();

  const collapseAll = () => {
    TASK_STATUS_COLUMNS.forEach(col => setColumnCollapsed(col, true));
    savePreferences(projectId);
  };

  const expandAll = () => {
    TASK_STATUS_COLUMNS.forEach(col => setColumnCollapsed(col, false));
    savePreferences(projectId);
  };

  const lockAll = () => {
    TASK_STATUS_COLUMNS.forEach(col => setColumnLocked(col, true));
    savePreferences(projectId);
  };

  const unlockAll = () => {
    TASK_STATUS_COLUMNS.forEach(col => setColumnLocked(col, false));
    savePreferences(projectId);
  };

  return (
    <div>
      <button onClick={collapseAll}>Collapse All</button>
      <button onClick={expandAll}>Expand All</button>
      <button onClick={lockAll}>Lock All</button>
      <button onClick={unlockAll}>Unlock All</button>
    </div>
  );
}
```

---

## Persistence Strategy

### localStorage Structure

**Key:** `kanban-column-prefs-{projectId}`

**Value:** JSON-serialized `KanbanColumnPreferences`

```json
{
  "not_started": {
    "width": 280,
    "isCollapsed": false,
    "isLocked": false
  },
  "in_progress": {
    "width": 400,
    "isCollapsed": false,
    "isLocked": true
  },
  "qa_ready": {
    "width": 320,
    "isCollapsed": false,
    "isLocked": false
  },
  "blocked": {
    "width": 180,
    "isCollapsed": true,
    "isLocked": false
  },
  "qa_fixing": {
    "width": 320,
    "isCollapsed": false,
    "isLocked": false
  },
  "qa_passed": {
    "width": 320,
    "isCollapsed": false,
    "isLocked": false
  },
  "done": {
    "width": 320,
    "isCollapsed": true,
    "isLocked": false
  }
}
```

### Validation

Before applying stored preferences, the store validates:

1. **Structure:** All required columns exist
2. **Types:** `width` is number, `isCollapsed` and `isLocked` are booleans
3. **Range:** `width` is within MIN_COLUMN_WIDTH (180) and MAX_COLUMN_WIDTH (600)

Invalid data triggers automatic fallback to defaults with console warning.

### Scoping

Preferences are scoped by `projectId`, allowing:
- Different layouts for different projects
- Safe project switching without losing preferences
- Independent preference management per workspace

---

## Best Practices

### 1. Always Initialize First

```typescript
// ✅ CORRECT - Initialize before use
useEffect(() => {
  initializePreferences();
  loadPreferences(projectId);
}, [projectId]);

// ❌ WRONG - Using store before initialization
const prefs = getColumnPreferences('in_progress'); // May return defaults incorrectly
```

### 2. Debounce Auto-Save

```typescript
// ✅ CORRECT - Debounce frequent updates
useEffect(() => {
  const timer = setTimeout(() => {
    savePreferences(projectId);
  }, 500);
  return () => clearTimeout(timer);
}, [columnPreferences]);

// ❌ WRONG - Save on every width change (performance issue)
const handleResize = (width: number) => {
  setColumnWidth(column, width);
  savePreferences(projectId); // Too frequent!
};
```

### 3. Respect Lock State in UI

```typescript
// ✅ CORRECT - Disable resize UI when locked
const cursor = prefs.isLocked ? 'not-allowed' : 'col-resize';
const onMouseDown = prefs.isLocked ? undefined : startResize;

// ❌ WRONG - Allow resizing locked columns
<div onMouseDown={startResize}> {/* Ignores lock state */}
```

### 4. Handle Collapsed State for Width

```typescript
// ✅ CORRECT - Apply COLLAPSED_COLUMN_WIDTH when collapsed
const effectiveWidth = prefs.isCollapsed ? COLLAPSED_COLUMN_WIDTH : prefs.width;

// ❌ WRONG - Ignore collapse state
<div style={{ width: prefs.width }}> {/* Shows full width when collapsed */}
```

### 5. Provide Reset Functionality

```typescript
// ✅ CORRECT - Allow users to reset to defaults
<button onClick={() => resetPreferences(projectId)}>
  Reset Layout
</button>

// ❌ WRONG - No way to recover from bad settings
```

### 6. Check Save Success

```typescript
// ✅ CORRECT - Handle save failures
const success = savePreferences(projectId);
if (!success) {
  toast.error('Failed to save column preferences');
}

// ⚠️ ACCEPTABLE - Silent failure (save is non-critical)
savePreferences(projectId); // Returns boolean but not checked
```

### 7. Use Getters, Not Direct State Access

```typescript
// ✅ CORRECT - Use getter method
const prefs = getColumnPreferences('in_progress');

// ❌ WRONG - Access state directly (no null safety)
const prefs = columnPreferences['in_progress']; // Error if null
```

---

## Related Documentation

- **[Task Store](./task-store.md)** - Main task state management (uses Kanban Settings Store)
- **[Component API Template](../templates/api/component-api.md)** - Documentation template for components
- **[Task Constants](../../apps/frontend/src/shared/constants/task.ts)** - TaskStatusColumn definitions
- **Zustand Documentation** - https://github.com/pmndrs/zustand

---

## Common Pitfalls

### Pitfall 1: Forgetting to Initialize

**Problem:** Using store before calling `initializePreferences()` causes `columnPreferences` to be `null`.

**Solution:**
```typescript
useEffect(() => {
  initializePreferences(); // Call first!
  loadPreferences(projectId);
}, []);
```

### Pitfall 2: Not Saving After Changes

**Problem:** Changes are applied to store but not persisted to localStorage.

**Solution:**
```typescript
const handleChange = () => {
  setColumnWidth(column, newWidth);
  savePreferences(projectId); // Don't forget!
};
```

### Pitfall 3: Ignoring Validation Failures

**Problem:** Invalid localStorage data silently falls back to defaults, confusing users.

**Solution:** Check console for warnings:
```
[KanbanSettingsStore] Invalid preferences in localStorage, using defaults
```

### Pitfall 4: localStorage Quota Exceeded

**Problem:** `savePreferences()` fails silently when localStorage quota is exceeded.

**Solution:** Handle failure and notify user:
```typescript
if (!savePreferences(projectId)) {
  toast.error('Failed to save preferences - localStorage full');
}
```

### Pitfall 5: Not Handling Project Switches

**Problem:** Preferences from old project shown when switching projects.

**Solution:** Reload on project change:
```typescript
useEffect(() => {
  if (projectId) {
    loadPreferences(projectId);
  }
}, [projectId]);
```

---

## Changelog

### v1.0.0 (Current)
- Initial implementation
- Column width, collapse, and lock state management
- localStorage persistence with validation
- Per-project preference scoping
- Automatic width clamping (180-600px)
- Safe defaults for missing/invalid data
