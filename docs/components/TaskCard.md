# Component: TaskCard & SortableTaskCard

High-performance task card components optimized for Kanban board display with real-time progress tracking, execution monitoring, multi-selection support, and drag-and-drop integration.

## Overview

**Type:** React Component
**Location:** `apps/frontend/src/renderer/components/TaskCard.tsx`, `apps/frontend/src/renderer/components/SortableTaskCard.tsx`
**Category:** UI Component
**Status:** Stable

> **Source of truth:** Task types and status definitions are defined in [`apps/frontend/src/shared/types/task.ts`](../../apps/frontend/src/shared/types/task.ts) and [`apps/frontend/src/shared/constants/task.ts`](../../apps/frontend/src/shared/constants/task.ts). Type definitions in this document mirror those canonical sources.

### Purpose

TaskCard is a memoized, performance-optimized component that displays task information with rich metadata, execution progress, and contextual actions. SortableTaskCard wraps TaskCard with drag-and-drop capabilities using @dnd-kit/sortable for seamless integration into the KanbanBoard.

### Key Features

- **Performance Optimization** - Custom `React.memo` comparator prevents unnecessary re-renders on task updates
- **Real-Time Execution Monitoring** - Displays execution phase, progress indicators, and stuck detection
- **Multi-Selection Support** - Checkbox-based selection for bulk operations in Human Review column
- **Stuck Task Detection** - Automatically detects and recovers tasks with crashed/orphaned processes
- **Rich Metadata Display** - Shows category, complexity, priority, impact, and security severity badges
- **Contextual Actions** - Start/Stop, Archive, Recover, View PR buttons based on task state
- **Phase-Aware Progress** - Integrates with PhaseProgressIndicator for animated progress display
- **Internationalization** - Full i18n support via react-i18next
- **Accessibility** - ARIA labels, keyboard navigation, and proper focus management
- **Drag & Drop Integration** - SortableTaskCard provides sortable wrapper for KanbanBoard

### Use Cases

- **KanbanBoard Display** - Primary component for task visualization in Kanban columns
- **Task Monitoring** - Real-time tracking of task execution with phase and progress display
- **Bulk Operations** - Multi-select tasks for batch PR creation or bulk status changes
- **Stuck Task Recovery** - Detect and recover tasks that crashed or lost their process
- **Task Metadata Visualization** - Display category, complexity, priority, and other metadata
- **Archive Management** - Archive completed tasks to declutter the board

---

## Installation / Import

### React Component Import

```typescript
import { TaskCard } from '@/renderer/components/TaskCard';
import { SortableTaskCard } from '@/renderer/components/SortableTaskCard';
```

### Dependencies

**Required:**
- `react` - Core React library
- `react-i18next` - Internationalization (i18n) support
- `lucide-react` - Icon components
- `@/components/ui/*` - Radix UI components (Card, Badge, Button, Checkbox, DropdownMenu)
- `@/lib/utils` - Utility functions (cn, formatRelativeTime, sanitizeMarkdownForDisplay)
- `@/stores/task-store` - Task state management (startTask, stopTask, checkTaskRunning, recoverStuckTask, archiveTasks)
- `@/shared/constants` - Task constants and labels
- `@/shared/types` - TypeScript type definitions

**Optional (for SortableTaskCard):**
- `@dnd-kit/sortable` - Sortable drag-and-drop integration
- `@dnd-kit/utilities` - CSS transform utilities
- `motion/react` (Framer Motion) - Smooth drag animations (scale, opacity, shadow)

---

## API Reference

### TaskCard Props

#### Required Props

| Prop | Type | Description | Example |
|------|------|-------------|---------|
| `task` | `Task` | Task object to display | `{ id: '001', title: 'Add login', status: 'in_progress', ... }` |
| `onClick` | `() => void` | Callback when card is clicked | `() => setSelectedTask(task)` |

#### Optional Props

| Prop | Type | Default | Description | Example |
|------|------|---------|-------------|---------|
| `onStatusChange` | `(newStatus: TaskStatus) => unknown` | `undefined` | Callback for status changes via dropdown menu | `(status) => updateTaskStatus(task.id, status)` |
| `isSelectable` | `boolean` | `false` | Enable checkbox for multi-selection | `true` |
| `isSelected` | `boolean` | `false` | Whether task is currently selected | `true` |
| `onToggleSelect` | `() => void` | `undefined` | Callback when selection checkbox is toggled | `() => toggleSelection(task.id)` |

### SortableTaskCard Props

#### Required Props

| Prop | Type | Description | Example |
|------|------|-------------|---------|
| `task` | `Task` | Task object to display | `{ id: '001', title: 'Add login', ... }` |
| `onClick` | `() => void` | Callback when card is clicked | `() => setSelectedTask(task)` |

#### Optional Props

| Prop | Type | Default | Description | Example |
|------|------|---------|-------------|---------|
| `onStatusChange` | `(newStatus: TaskStatus) => unknown` | `undefined` | Callback for status changes | `(status) => updateTaskStatus(task.id, status)` |
| `isSelectable` | `boolean` | `false` | Enable checkbox for multi-selection | `true` |
| `isSelected` | `boolean` | `false` | Whether task is currently selected | `true` |
| `onToggleSelect` | `() => void` | `undefined` | Callback when selection checkbox is toggled | `() => toggleSelection(task.id)` |

### Events / Callbacks

| Event/Callback | Signature | Description | When Triggered |
|----------------|-----------|-------------|----------------|
| `onClick` | `() => void` | Card clicked | User clicks anywhere on the card |
| `onStatusChange` | `(newStatus: TaskStatus) => unknown` | Status changed via menu | User selects new status from dropdown |
| `onToggleSelect` | `() => void` | Selection toggled | User clicks selection checkbox |

### Internal Event Handlers (Not Props)

The TaskCard internally manages these interactions:

| Handler | Purpose | Store/System |
|---------|---------|--------------|
| `handleStartStop` | Start or stop task execution | `task-store` (startTask, stopTask) |
| `handleRecover` | Recover stuck task and restart | `task-store` (recoverStuckTask) |
| `handleArchive` | Archive completed task | `task-store` (archiveTasks) |
| `handleViewPR` | Open PR URL in external browser | `window.electronAPI.openExternal` |
| `performStuckCheck` | Check if task process is still running | `task-store` (checkTaskRunning) |

---

## Type Definitions

### TypeScript Types

```typescript
// TaskCard props
interface TaskCardProps {
  task: Task;
  onClick: () => void;
  onStatusChange?: (newStatus: TaskStatus) => unknown;
  // Optional selectable mode props for multi-selection
  isSelectable?: boolean;
  isSelected?: boolean;
  onToggleSelect?: () => void;
}

// SortableTaskCard props
interface SortableTaskCardProps {
  task: Task;
  onClick: () => void;
  onStatusChange?: (newStatus: TaskStatus) => unknown;
  // Optional selection props for multi-selection in Human Review column
  isSelectable?: boolean;
  isSelected?: boolean;
  onToggleSelect?: () => void;
}

// Task type (from @/shared/types/task)
interface Task {
  id: string;
  specId: string;
  projectId: string;
  title: string;
  description: string;
  status: TaskStatus;
  reviewReason?: ReviewReason;
  subtasks: Subtask[];
  qaReport?: QAReport;
  logs: string[];
  metadata?: TaskMetadata;
  executionProgress?: ExecutionProgress;
  releasedInVersion?: string;
  stagedInMainProject?: boolean;
  stagedAt?: string;
  location?: 'main' | 'worktree';
  specsPath?: string;
  tokenStats?: TaskTokenStats;
  createdAt: Date;
  updatedAt: Date;
}

// ExecutionProgress (from @/shared/types/task)
interface ExecutionProgress {
  phase: ExecutionPhase;
  phaseProgress: number;       // 0-100 within current phase
  overallProgress: number;     // 0-100 overall
  currentSubtask?: string;
  message?: string;
  startedAt?: Date;
  sequenceNumber?: number;     // Monotonically increasing counter for stale update detection
  completedPhases?: CompletablePhase[];
  // Resource usage metrics (from backend)
  cpu_percent?: number;
  memory_mb?: number;
  memory_percent?: number;
  elapsed_seconds?: number;
  // Timing estimates
  estimated_seconds?: number;
  confidence?: 'high' | 'medium' | 'low';
  sample_size?: number;
}

// Task status (from @/shared/types/task)
type TaskStatus = 'backlog' | 'queue' | 'in_progress' | 'ai_review' | 'human_review' | 'done' | 'pr_created' | 'error';

// Review reasons
type ReviewReason = 'completed' | 'errors' | 'qa_rejected' | 'plan_review';

// Execution phase
type ExecutionPhase = 'idle' | 'planning' | 'coding' | 'qa_review' | 'qa_fixing' | 'complete' | 'failed';

// Subtask status
type SubtaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

// Task category
type TaskCategory = 'feature' | 'bug_fix' | 'refactoring' | 'documentation' | 'security' | 'performance' | 'ui_ux' | 'infrastructure' | 'testing';

// Task complexity (5 levels)
type TaskComplexity = 'trivial' | 'small' | 'medium' | 'large' | 'complex';

// Task priority
type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';

// Task impact
type TaskImpact = 'low' | 'medium' | 'high' | 'critical';

// Security severity
type SecuritySeverity = 'low' | 'medium' | 'high' | 'critical';
```

---

## Performance Optimization

### Custom Memo Comparator

Both TaskCard and SortableTaskCard use custom `React.memo` comparators to prevent unnecessary re-renders:

**TaskCard:**
```typescript
function taskCardPropsAreEqual(prevProps: TaskCardProps, nextProps: TaskCardProps): boolean {
  const prevTask = prevProps.task;
  const nextTask = nextProps.task;

  // Fast path: same reference (include selectable props)
  if (
    prevTask === nextTask &&
    prevProps.onClick === nextProps.onClick &&
    prevProps.onStatusChange === nextProps.onStatusChange &&
    prevProps.isSelectable === nextProps.isSelectable &&
    prevProps.isSelected === nextProps.isSelected &&
    prevProps.onToggleSelect === nextProps.onToggleSelect
  ) {
    return true;
  }

  // Check selectable props first (cheap comparison)
  if (prevProps.isSelectable !== nextProps.isSelectable || prevProps.isSelected !== nextProps.isSelected) {
    return false;
  }

  // Compare only the fields that affect rendering
  return (
    prevTask.id === nextTask.id &&
    prevTask.status === nextTask.status &&
    prevTask.title === nextTask.title &&
    prevTask.description === nextTask.description &&
    prevTask.updatedAt === nextTask.updatedAt &&
    prevTask.reviewReason === nextTask.reviewReason &&
    prevTask.executionProgress?.phase === nextTask.executionProgress?.phase &&
    prevTask.executionProgress?.phaseProgress === nextTask.executionProgress?.phaseProgress &&
    prevTask.subtasks.length === nextTask.subtasks.length &&
    prevTask.metadata?.category === nextTask.metadata?.category &&
    prevTask.metadata?.complexity === nextTask.metadata?.complexity &&
    prevTask.metadata?.archivedAt === nextTask.metadata?.archivedAt &&
    prevTask.metadata?.prUrl === nextTask.metadata?.prUrl &&
    prevTask.subtasks.every((s, i) => s.status === nextTask.subtasks[i]?.status)
  );
}

export const TaskCard = memo(function TaskCard({ ... }) { ... }, taskCardPropsAreEqual);
```

**SortableTaskCard:**
```typescript
function sortableTaskCardPropsAreEqual(
  prevProps: SortableTaskCardProps,
  nextProps: SortableTaskCardProps
): boolean {
  // Check reference equality for task and callbacks
  return (
    prevProps.task === nextProps.task &&
    prevProps.onClick === nextProps.onClick &&
    prevProps.onStatusChange === nextProps.onStatusChange &&
    prevProps.isSelectable === nextProps.isSelectable &&
    prevProps.isSelected === nextProps.isSelected &&
    prevProps.onToggleSelect === nextProps.onToggleSelect
  );
}

export const SortableTaskCard = memo(function SortableTaskCard({ ... }) { ... }, sortableTaskCardPropsAreEqual);
```

### Memoization Patterns

**Expensive computations are memoized:**
```typescript
// Sanitized description (only recalculates when task.description changes)
const sanitizedDescription = useMemo(() => {
  return task.description ? sanitizeMarkdownForDisplay(task.description, 120) : null;
}, [task.description]);

// Relative time (only recalculates when updatedAt changes)
const relativeTime = useMemo(
  () => formatRelativeTime(task.updatedAt),
  [task.updatedAt]
);

// Status menu items (only recalculates when status changes)
const statusMenuItems = useMemo(() => {
  return TASK_STATUS_COLUMNS.filter(status => status !== task.status).map(...);
}, [task.status, onStatusChange, t]);
```

**Callbacks are memoized:**
```typescript
// Stuck check callback (prevents recreation on every render)
const performStuckCheck = useCallback(() => {
  checkTaskRunning(task.id).then((actuallyRunning) => {
    setIsStuck(!actuallyRunning);
  });
}, [task.id, task.executionProgress?.phase]);
```

---

## Features

### 1. Stuck Task Detection

Automatically detects tasks that are marked as `in_progress` but have no running process (crashed/orphaned):

**How it works:**
- Initial check after 5-second grace period (prevents false positives during process spawn)
- Periodic re-check every 30 seconds while task is running
- Re-validates when browser tab becomes visible (visibility API)
- Skips detection for terminal phases (`complete`, `failed`) and `planning` phase
- Uses `requestIdleCallback` for non-blocking checks when available (with `setTimeout` fallback for environments that don't support it, e.g., `const scheduleIdle = window.requestIdleCallback ?? ((cb: () => void) => setTimeout(cb, 0))`)

**User experience:**
```
┌─────────────────────────────────────┐
│ Task Title                          │
│ ⚠ Stuck   🔄 Running                │  ← Stuck badge shown
│ ━━━━━━━━━━━━━━━━━━━━━━━ 45%        │
│                                     │
│ 🕒 5 min ago    [🔄 Recover]        │  ← Recover button
└─────────────────────────────────────┘
```

**Recovery:**
```typescript
const handleRecover = async (e: React.MouseEvent) => {
  e.stopPropagation();
  setIsRecovering(true);
  // Auto-restart the task after recovery (no need to click Start again)
  const result = await recoverStuckTask(task.id, { autoRestart: true });
  if (result.success) {
    setIsStuck(false);
  }
  setIsRecovering(false);
};
```

### 2. Multi-Selection Support

Enable checkbox-based selection for bulk operations:

**Usage:**
```tsx
<TaskCard
  task={task}
  onClick={() => openTaskDetails(task)}
  isSelectable={true}
  isSelected={selectedIds.has(task.id)}
  onToggleSelect={() => toggleSelection(task.id)}
/>
```

**Visual layout:**
```
┌───┬─────────────────────────────────┐
│ ☑ │ Task Title                      │  ← Checkbox (stops propagation)
│   │ Description text...             │
│   │ 🎯 Feature   🟡 Standard        │
│   │ ━━━━━━━━━━━━━━━ 75%            │
│   │ 🕒 2 hours ago   [⬛ Stop]      │
└───┴─────────────────────────────────┘
```

**Implementation notes:**
- Checkbox stops event propagation to prevent card click
- Selection state highlighted with ring border (`ring-2 ring-ring border-ring`)
- ARIA label for accessibility: `aria-label={t('tasks:actions.selectTask', { title })}`

### 3. Execution Progress Display

Integrates with `PhaseProgressIndicator` for animated progress:

**Progress data sources:**
- `task.executionProgress.phase` - Current execution phase (planning, implementation, qa, fixing)
- `task.executionProgress.phaseProgress` - Phase completion percentage (0-100)
- `task.subtasks` - Array of subtasks with individual status tracking

**Phase badge display:**
```tsx
{hasActiveExecution && executionPhase && !isStuck && !isIncomplete && (
  <Badge variant="outline" className={EXECUTION_PHASE_BADGE_COLORS[executionPhase]}>
    <Loader2 className="h-2.5 w-2.5 animate-spin" />
    {EXECUTION_PHASE_LABELS[executionPhase]}
  </Badge>
)}
```

### 4. Metadata Badges

Displays rich task metadata with color-coded badges:

**Badge hierarchy (display priority):**
1. **Stuck indicator** - `⚠ Stuck` (highest priority, orange)
2. **Incomplete indicator** - `⚠ Incomplete` (task in human_review with no completed subtasks)
3. **Archived indicator** - `📦 Archived` (task has been released)
4. **Execution phase** - `🔄 Planning/Implementation/QA/Fixing` (animated spinner)
5. **Status badge** - `Pending/Running/Needs Review/Complete`
6. **Review reason** - `✅ Completed/❌ Has Errors/⚠ QA Issues/📝 Approve Plan` (variant-colored badges)
7. **Category & Complexity** - Shown in an expandable **Popover** (click "More Info" badge to expand)
8. **Impact** - `High Impact/Critical` (only show high/critical)
9. **Priority** - `Urgent/High` (only show urgent/high)
10. **Security severity** - `Low/Medium/High/Critical Severity` (always shown)

**Review Reason Badges:**
```typescript
const getReviewReasonLabel = (reason?: ReviewReason) => {
  switch (reason) {
    case 'completed':   return { label: t('reviewReason.completed'), variant: 'success' };
    case 'errors':      return { label: t('reviewReason.hasErrors'), variant: 'destructive' };
    case 'qa_rejected': return { label: t('reviewReason.qaIssues'), variant: 'warning' };
    case 'plan_review': return { label: t('reviewReason.approvePlan'), variant: 'warning' };
  }
};
```

**Expandable Metadata Popover:**

Category and complexity badges are shown inside a Radix UI `Popover` triggered by a "More Info" badge. This keeps the card compact while providing detail on demand. Category badges include icons via `renderCategoryIcon()`.

**Badge constants:**
```typescript
import {
  TASK_CATEGORY_COLORS,
  TASK_CATEGORY_LABELS,
  TASK_COMPLEXITY_COLORS,
  TASK_COMPLEXITY_LABELS,
  TASK_IMPACT_COLORS,
  TASK_IMPACT_LABELS,
  TASK_PRIORITY_COLORS,
  TASK_PRIORITY_LABELS,
  EXECUTION_PHASE_LABELS,
  EXECUTION_PHASE_BADGE_COLORS
} from '../../shared/constants';
```

### 5. Contextual Actions

Actions change based on task state:

| Task State | Primary Action | Secondary Actions |
|------------|----------------|-------------------|
| `backlog` | `▶ Start` | Move To menu |
| `in_progress` (running) | `⬛ Stop` | Move To menu |
| `in_progress` (stuck) | `🔄 Recover` | - |
| `human_review` (incomplete) | `▶ Resume` | - |
| `done` (with PR) | `📄 View PR` | `📦 Archive` |
| `done` (no PR) | `📦 Archive` | - |

**Action buttons:**
```typescript
{isStuck ? (
  <Button variant="warning" onClick={handleRecover}>
    <RotateCcw className="mr-1.5 h-3 w-3" />
    {t('actions.recover')}
  </Button>
) : isIncomplete ? (
  <Button variant="default" onClick={handleStartStop}>
    <Play className="mr-1.5 h-3 w-3" />
    {t('actions.resume')}
  </Button>
) : task.status === 'done' && task.metadata?.prUrl ? (
  <>
    <Button variant="ghost" onClick={handleViewPR}>
      <GitPullRequest className="h-3 w-3" />
    </Button>
    <Button variant="ghost" onClick={handleArchive}>
      <Archive className="h-3 w-3" />
    </Button>
  </>
) : ...}
```

### 6. Internationalization (i18n)

Full i18n support via `react-i18next`:

**Translation namespaces:**
- `tasks` - Task labels, actions, tooltips, metadata
- `errors` - Error messages for JSON error tasks

**JSON error handling:**
```typescript
// Detect JSON error marker and use i18n (guard against undefined description)
if (task.description?.startsWith(JSON_ERROR_PREFIX)) {
  const errorMessage = task.description.slice(JSON_ERROR_PREFIX.length);
  const translatedDesc = t('errors:task.jsonError.description', { error: errorMessage });
  return sanitizeMarkdownForDisplay(translatedDesc, 120);
}

// Handle title suffix
if (task.title.endsWith(JSON_ERROR_TITLE_SUFFIX)) {
  const baseName = task.title.slice(0, -JSON_ERROR_TITLE_SUFFIX.length);
  return `${baseName} ${t('errors:task.jsonError.titleSuffix')}`;
}
```

### 7. Archive Management

Archive completed tasks to keep the board clean:

**Archive action:**
```typescript
const handleArchive = async (e: React.MouseEvent) => {
  e.stopPropagation();
  const result = await archiveTasks(task.projectId, [task.id]);
  if (!result.success) {
    console.error('[TaskCard] Failed to archive task:', task.id, result.error);
  }
};
```

**Archived task styling:**
```tsx
<Card
  className={cn(
    'card-surface task-card-enhanced cursor-pointer',
    isArchived && 'opacity-60 hover:opacity-80'
  )}
>
```

### 8. SortableTaskCard Animations (Framer Motion)

SortableTaskCard wraps TaskCard with smooth drag animations via `motion/react`:

```typescript
<motion.div
  animate={{
    scale: isDragging ? 1.05 : 1,
    opacity: isDragging ? 0.8 : 1,
    boxShadow: isDragging
      ? '0 10px 40px -10px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(0, 0, 0, 0.05)'
      : '0 0 0 0 rgba(0, 0, 0, 0)',
  }}
  transition={{ type: 'spring', stiffness: 300, damping: 25, mass: 0.5 }}
>
```

**Visual feedback:**
- **Dragging**: Card scales up (1.05x), reduces opacity (0.8), gains shadow
- **Over drop target**: Ring glow effect (`ring-2 ring-primary/30`)
- **Auto-sort disabled**: When `isDragDisabled` is true, card shows tooltip explaining drag is disabled and applies `cursor-not-allowed`

---

## Usage Examples

### Basic TaskCard

```tsx
import { TaskCard } from '@/renderer/components/TaskCard';

function TaskList() {
  const tasks = useTaskStore((state) => state.tasks);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  return (
    <div className="space-y-2">
      {tasks.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          onClick={() => setSelectedTask(task)}
        />
      ))}
    </div>
  );
}
```

### TaskCard with Status Change

```tsx
import { TaskCard } from '@/renderer/components/TaskCard';
import { updateTaskStatus } from '@/stores/task-store';

function TaskList() {
  const handleStatusChange = (task: Task, newStatus: TaskStatus) => {
    updateTaskStatus(task.id, newStatus);
  };

  return (
    <TaskCard
      task={task}
      onClick={() => openTaskModal(task)}
      onStatusChange={(status) => handleStatusChange(task, status)}
    />
  );
}
```

### TaskCard with Multi-Selection

```tsx
import { TaskCard } from '@/renderer/components/TaskCard';
import { useState } from 'react';

function HumanReviewColumn() {
  const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());

  const toggleSelection = (taskId: string) => {
    setSelectedTaskIds((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  };

  return (
    <div>
      {tasks.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          onClick={() => openTaskModal(task)}
          isSelectable={true}
          isSelected={selectedTaskIds.has(task.id)}
          onToggleSelect={() => toggleSelection(task.id)}
        />
      ))}
    </div>
  );
}
```

### SortableTaskCard in KanbanBoard

```tsx
import { SortableTaskCard } from '@/renderer/components/SortableTaskCard';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';

function KanbanColumn() {
  const tasks = useTaskStore((state) => state.getTasksByStatus('in_progress'));

  return (
    <SortableContext items={tasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
      {tasks.map((task) => (
        <SortableTaskCard
          key={task.id}
          task={task}
          onClick={() => openTaskDetails(task)}
          onStatusChange={(status) => updateTaskStatus(task.id, status)}
        />
      ))}
    </SortableContext>
  );
}
```

### SortableTaskCard with Multi-Selection (Human Review)

```tsx
import { SortableTaskCard } from '@/renderer/components/SortableTaskCard';
import { useState } from 'react';

function HumanReviewColumn() {
  const tasks = useTaskStore((state) => state.getTasksByStatus('human_review'));
  const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());

  const toggleSelection = (taskId: string) => {
    setSelectedTaskIds((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  };

  return (
    <SortableContext items={tasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
      {tasks.map((task) => (
        <SortableTaskCard
          key={task.id}
          task={task}
          onClick={() => openTaskDetails(task)}
          isSelectable={true}
          isSelected={selectedTaskIds.has(task.id)}
          onToggleSelect={() => toggleSelection(task.id)}
        />
      ))}
    </SortableContext>
  );
}
```

---

## Integration with Stores

### Task Store

**Actions used by TaskCard:**
```typescript
import {
  startTask,      // Start task execution
  stopTask,       // Stop running task
  checkTaskRunning, // Check if task process is running (for stuck detection)
  recoverStuckTask, // Recover stuck task and optionally restart
  isIncompleteHumanReview, // Check if task is in human_review but incomplete
  archiveTasks    // Archive completed tasks
} from '@/stores/task-store';
```

**Usage examples:**
```typescript
// Start task
const handleStart = () => {
  startTask(task.id);
};

// Stop task
const handleStop = () => {
  stopTask(task.id);
};

// Check if task is stuck
const isStuck = !(await checkTaskRunning(task.id));

// Recover stuck task with auto-restart
const result = await recoverStuckTask(task.id, { autoRestart: true });

// Check if task is incomplete (in human_review with no completed subtasks)
const isIncomplete = isIncompleteHumanReview(task);

// Archive task
const result = await archiveTasks(task.projectId, [task.id]);
```

### Constants

**Import task constants:**
```typescript
import {
  TASK_CATEGORY_LABELS,           // Category display labels
  TASK_CATEGORY_COLORS,            // Category badge colors
  TASK_COMPLEXITY_COLORS,          // Complexity badge colors
  TASK_COMPLEXITY_LABELS,          // Complexity display labels
  TASK_IMPACT_COLORS,              // Impact badge colors
  TASK_IMPACT_LABELS,              // Impact display labels
  TASK_PRIORITY_COLORS,            // Priority badge colors
  TASK_PRIORITY_LABELS,            // Priority display labels
  EXECUTION_PHASE_LABELS,          // Execution phase labels
  EXECUTION_PHASE_BADGE_COLORS,    // Execution phase badge colors
  TASK_STATUS_COLUMNS,             // Available task statuses
  TASK_STATUS_LABELS,              // Status display labels
  JSON_ERROR_PREFIX,               // Prefix for JSON error tasks
  JSON_ERROR_TITLE_SUFFIX          // Suffix for JSON error task titles
} from '../../shared/constants';
```

---

## Styling

### CSS Classes

**Card states:**
- `task-card-enhanced` - Base card styling
- `task-running-pulse` - Animated pulse for running tasks
- `task-stuck-pulse` - Warning pulse for stuck tasks
- `dragging-placeholder` - Semi-transparent placeholder during drag

**Card modifiers:**
```tsx
<Card
  className={cn(
    'card-surface task-card-enhanced cursor-pointer',
    isRunning && !isStuck && 'ring-2 ring-primary border-primary task-running-pulse',
    isStuck && 'ring-2 ring-warning border-warning task-stuck-pulse',
    isArchived && 'opacity-60 hover:opacity-80',
    isSelectable && isSelected && 'ring-2 ring-ring border-ring bg-accent/10'
  )}
/>
```

### Badge Styling

**Badge size and spacing:**
```tsx
<Badge
  variant="outline"
  className="text-[10px] px-1.5 py-0.5 flex items-center gap-1"
>
  <Icon className="h-2.5 w-2.5" />
  {label}
</Badge>
```

**Badge variants:**
- `default` - Default badge style
- `outline` - Outlined badge (most common for metadata)
- `info` - Blue badge (in_progress status)
- `warning` - Yellow/orange badge (ai_review, stuck)
- `purple` - Purple badge (human_review)
- `success` - Green badge (done, completed)
- `destructive` - Red badge (errors)

---

## Accessibility

### ARIA Labels

```tsx
// Selection checkbox
<Checkbox
  checked={isSelected}
  onCheckedChange={onToggleSelect}
  aria-label={t('tasks:actions.selectTask', { title: displayTitle })}
/>

// Actions menu
<Button
  variant="ghost"
  onClick={(e) => e.stopPropagation()}
  aria-label={t('actions.taskActions')}
>
  <MoreVertical className="h-4 w-4" />
</Button>
```

### Keyboard Navigation

- **Enter/Space on card** - Opens task details (via onClick)
- **Enter/Space on checkbox** - Toggles selection
- **Tab navigation** - Focus moves through action buttons and menu
- **Dropdown menu** - Accessible via keyboard (Radix UI)

### Focus Management

- Card is clickable (`cursor-pointer`)
- Action buttons stop event propagation (`onClick={(e) => e.stopPropagation()}`)
- Selection checkbox stops propagation to prevent card click

---

## Testing

### Unit Test Examples

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TaskCard } from '@/renderer/components/TaskCard';
import { checkTaskRunning } from '@/stores/task-store';

describe('TaskCard', () => {
  it('displays task title and description', () => {
    const task = createMockTask({ title: 'Test Task', description: 'Test description' });
    render(<TaskCard task={task} onClick={() => {}} />);

    expect(screen.getByText('Test Task')).toBeInTheDocument();
    expect(screen.getByText(/Test description/)).toBeInTheDocument();
  });

  it('shows stuck indicator when task process is not running', async () => {
    const task = createMockTask({ status: 'in_progress' });
    vi.mocked(checkTaskRunning).mockResolvedValue(false);

    render(<TaskCard task={task} onClick={() => {}} />);

    // Wait for stuck check (5s grace period + check)
    await waitFor(() => {
      expect(screen.getByText('Stuck')).toBeInTheDocument();
    }, { timeout: 6000 });
  });

  it('handles selection checkbox click without triggering card click', () => {
    const task = createMockTask();
    const onCardClick = vi.fn();
    const onToggleSelect = vi.fn();

    render(
      <TaskCard
        task={task}
        onClick={onCardClick}
        isSelectable={true}
        isSelected={false}
        onToggleSelect={onToggleSelect}
      />
    );

    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);

    expect(onToggleSelect).toHaveBeenCalled();
    expect(onCardClick).not.toHaveBeenCalled();
  });

  it('displays execution phase badge for running tasks', () => {
    const task = createMockTask({
      status: 'in_progress',
      executionProgress: { phase: 'implementation', phaseProgress: 45 }
    });

    render(<TaskCard task={task} onClick={() => {}} />);

    expect(screen.getByText('Implementation')).toBeInTheDocument();
  });
});
```

---

## Performance Considerations

### Re-Render Prevention

1. **Custom memo comparator** - Only re-render when relevant fields change
2. **Memoized computations** - Expensive operations cached with `useMemo`
3. **Memoized callbacks** - Event handlers cached with `useCallback`
4. **Selective field comparison** - Only compare fields that affect rendering

### Debug Logging

Enable debug logging to see re-render reasons:
```javascript
window.DEBUG = true;
```

**Console output:**
```
[TaskCard] Re-render: 001 | status: backlog -> in_progress
[TaskCard] Re-render: 002 | phase: planning -> implementation, subtasks: 0 -> 3
```

### Stuck Check Optimization

- Uses `requestIdleCallback` for non-blocking checks (when available)
- Increased grace period (5s) to prevent false positives
- Reduced check frequency (30s interval) to minimize overhead
- Skips checks for terminal phases (`complete`, `failed`, `planning`)
- Debounced visibility change handler (500ms)

---

## Common Patterns

### 1. KanbanBoard Integration

```tsx
// In KanbanBoard columns
<SortableContext items={tasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
  {tasks.map((task) => (
    <SortableTaskCard
      key={task.id}
      task={task}
      onClick={() => onTaskClick(task)}
      onStatusChange={(status) => handleStatusChange(task.id, status)}
      isSelectable={status === 'human_review'}
      isSelected={selectedTaskIds.has(task.id)}
      onToggleSelect={() => toggleTaskSelection(task.id)}
    />
  ))}
</SortableContext>
```

### 2. Task Details Modal Trigger

```tsx
const [selectedTask, setSelectedTask] = useState<Task | null>(null);

<TaskCard
  task={task}
  onClick={() => setSelectedTask(task)}
/>

{selectedTask && (
  <TaskDetailsModal
    task={selectedTask}
    onClose={() => setSelectedTask(null)}
  />
)}
```

### 3. Bulk PR Creation

```tsx
// Human Review column with multi-selection
const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());

const handleCreateBulkPRs = async () => {
  const tasks = Array.from(selectedTaskIds).map(id => getTaskById(id));
  await createPullRequests(tasks);
  setSelectedTaskIds(new Set());
};

<div>
  <Button
    onClick={handleCreateBulkPRs}
    disabled={selectedTaskIds.size === 0}
  >
    Create {selectedTaskIds.size} PRs
  </Button>

  {tasks.map((task) => (
    <TaskCard
      key={task.id}
      task={task}
      onClick={() => openTaskDetails(task)}
      isSelectable={true}
      isSelected={selectedTaskIds.has(task.id)}
      onToggleSelect={() => toggleSelection(task.id)}
    />
  ))}
</div>
```

---

## Troubleshooting

### Issue: False Stuck Detection

**Symptom:** Tasks marked as stuck immediately after starting

**Solution:** Increased grace period to 5 seconds:
```typescript
// Initial check after 5s grace period (increased from 2s)
stuckCheckRef.current.timeout = setTimeout(performStuckCheck, 5000);
```

### Issue: Excessive Re-Renders

**Symptom:** TaskCard re-renders on every task store update

**Solution:** Custom memo comparator prevents re-renders when unrelated fields change. Enable debug logging to diagnose:
```javascript
window.DEBUG = true;
```

### Issue: Checkbox Clicks Trigger Card Click

**Symptom:** Clicking selection checkbox opens task modal

**Solution:** Checkbox stops event propagation:
```tsx
<Checkbox
  onClick={(e) => e.stopPropagation()}
  onCheckedChange={onToggleSelect}
/>
```

### Issue: Incomplete Tasks Not Detected

**Symptom:** Task in human_review with no completed subtasks doesn't show "Incomplete"

**Solution:** Use `isIncompleteHumanReview` helper from task-store:
```typescript
import { isIncompleteHumanReview } from '@/stores/task-store';

const isIncomplete = isIncompleteHumanReview(task);
```

---

## Related Components

- **[KanbanBoard](./KanbanBoard.md)** - Parent component that uses SortableTaskCard
- **[PhaseProgressIndicator](./PhaseProgressIndicator.md)** - Progress display component (if documented)
- **[Sidebar](./Sidebar.md)** - Navigation component

## Related Stores

- **[task-store](../stores/task-store.md)** - Task state management (if documented)
- **[project-store](../stores/project-store.md)** - Project state management (if documented)

## Related Documentation

- **[Drag & Drop System](../architecture/dnd-system.md)** - @dnd-kit integration (if documented)
- **[Task Workflow](../architecture/task-workflow.md)** - Task lifecycle and status transitions (if documented)
- **[Internationalization](../guides/i18n.md)** - i18n integration guide (if documented)
