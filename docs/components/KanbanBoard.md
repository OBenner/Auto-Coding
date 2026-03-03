# Component: KanbanBoard

A powerful, feature-rich Kanban board component for managing task workflows with drag-and-drop, queue management, column customization, and real-time progress tracking.

## Overview

**Type:** React Component
**Location:** `apps/frontend/src/renderer/components/KanbanBoard.tsx`
**Category:** UI Component
**Status:** Stable

> **Source of truth:** Task types and status definitions are defined in [`apps/frontend/src/shared/types/task.ts`](../../apps/frontend/src/shared/types/task.ts) and [`apps/frontend/src/shared/constants/task.ts`](../../apps/frontend/src/shared/constants/task.ts). Type definitions in this document mirror those canonical sources.

### Purpose

The KanbanBoard component provides a visual task management interface that displays tasks across six workflow stages (Backlog, Queue, In Progress, AI Review, Human Review, Done). It implements drag-and-drop task movement, automatic queue processing, multi-selection for bulk actions, and extensive column customization features including collapsing, resizing, and locking.

### Key Features

- **Drag & Drop Task Management** - Intuitive task movement between columns using @dnd-kit
- **Automatic Queue System** - Enforces parallel task limits with FIFO queue auto-promotion
- **Column Customization** - Collapse, resize, and lock columns with per-project persistence
- **Multi-Selection & Bulk Actions** - Select multiple tasks in Human Review for bulk PR creation
- **Real-Time Progress Tracking** - Shows task execution progress with skeleton loaders
- **Archive Management** - Archive completed tasks with toggle to show/hide archived items
- **Worktree Integration** - Handles worktree cleanup confirmation dialogs
- **Smart Task Ordering** - Persistent custom task ordering within columns
- **Empty State Guidance** - Contextual empty states with helpful hints for each column

### Use Cases

- **Task Workflow Management** - Visualize and manage tasks through development lifecycle stages
- **Parallel Work Control** - Enforce limits on concurrent tasks with automatic queue processing
- **Bulk Operations** - Select and perform actions on multiple tasks simultaneously
- **Column Organization** - Customize board layout by collapsing unused columns or resizing active ones
- **Task Status Transitions** - Move tasks between workflow stages via drag-and-drop or status changes
- **Archive Management** - Keep completed tasks accessible but hidden from active workflow

---

## Installation / Import

### React Component Import

```typescript
import { KanbanBoard } from '@/renderer/components/KanbanBoard';
```

### Dependencies

**Required:**
- `react` - Core React library
- `react-i18next` - Internationalization (i18n) support
- `@dnd-kit/core` - Core drag-and-drop functionality
- `@dnd-kit/sortable` - Sortable list support for task reordering
- `lucide-react` - Icon components
- `zustand` - State management stores (task-store, project-store, kanban-settings-store)

**Optional:**
- None (all dependencies are required for full functionality)

---

## API Reference

### Props

#### Required Props

| Prop | Type | Description | Example |
|------|------|-------------|---------|
| `tasks` | `Task[]` | Array of task objects to display | `[{ id: '1', title: 'Implement login', ... }]` |
| `onTaskClick` | `(task: Task) => void` | Callback when a task card is clicked | `(task) => navigate(\`/tasks/${task.id}\`)` |

#### Optional Props

| Prop | Type | Default | Description | Example |
|------|------|---------|-------------|---------|
| `onNewTaskClick` | `() => void` | `undefined` | Callback for "Add Task" button in Backlog column | `() => setShowCreateDialog(true)` |
| `onRefresh` | `() => void` | `undefined` | Callback for refresh button (enables refresh UI) | `() => reloadTasks()` |
| `isRefreshing` | `boolean` | `false` | Shows loading state during refresh | `true` |

### Events / Callbacks

| Event/Callback | Signature | Description | When Triggered |
|----------------|-----------|-------------|----------------|
| `onTaskClick` | `(task: Task) => void` | Task card clicked | User clicks on a task card |
| `onNewTaskClick` | `() => void` | Add task button clicked | User clicks "+" button in Backlog |
| `onRefresh` | `() => void` | Refresh button clicked | User clicks refresh button in header |

### Internal Event Handlers (Not Props)

The KanbanBoard internally manages these interactions through store updates:

| Handler | Purpose | Store/System |
|---------|---------|--------------|
| `handleDragStart` | Initiates drag operation | `@dnd-kit/core` |
| `handleDragOver` | Updates hover state during drag | `@dnd-kit/core` |
| `handleDragEnd` | Persists task status change | `task-store` |
| `handleStatusChange` | Updates task status with validation | `task-store` |
| `handleArchiveAll` | Archives all done tasks | `task-store` |
| `handleQueueAll` | Moves all backlog tasks to queue | `task-store` + queue system |
| `handleToggleColumnCollapsed` | Collapses/expands column | `kanban-settings-store` |
| `handleResizeStart/Move/End` | Resizes column width | `kanban-settings-store` |
| `handleToggleColumnLocked` | Locks/unlocks column from resizing | `kanban-settings-store` |
| `toggleTaskSelection` | Selects/deselects task for bulk actions | Local state |
| `selectAllTasks` | Selects all tasks in Human Review | Local state |
| `deselectAllTasks` | Clears all task selections | Local state |

---

## Type Definitions

### TypeScript Types

```typescript
// Component props
interface KanbanBoardProps {
  tasks: Task[];
  onTaskClick: (task: Task) => void;
  onNewTaskClick?: () => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

// Column props (internal to KanbanBoard)
interface DroppableColumnProps {
  status: TaskStatus;
  tasks: Task[];
  onTaskClick: (task: Task) => void;
  onStatusChange: (taskId: string, newStatus: TaskStatus) => unknown;
  isOver: boolean;
  onAddClick?: () => void;
  onArchiveAll?: () => void;
  onQueueSettings?: () => void;
  onQueueAll?: () => void;
  maxParallelTasks?: number;
  archivedCount?: number;
  showArchived?: boolean;
  onToggleArchived?: () => void;
  // Selection props for human_review column
  selectedTaskIds?: Set<string>;
  onSelectAll?: () => void;
  onDeselectAll?: () => void;
  onToggleSelect?: (taskId: string) => void;
  // Collapse props
  isCollapsed?: boolean;
  onToggleCollapsed?: () => void;
  // Resize props
  columnWidth?: number;
  isResizing?: boolean;
  onResizeStart?: (startX: number) => void;
  onResizeEnd?: () => void;
  // Lock props
  isLocked?: boolean;
  onToggleLocked?: () => void;
  // Loading state
  isLoading?: boolean;
}

// Task type (from shared/types/task.ts)
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

// Task status (maps to Kanban columns)
type TaskStatus =
  | 'backlog'       // New tasks, not yet queued
  | 'queue'         // Waiting for available slot
  | 'in_progress'   // Currently executing
  | 'ai_review'     // QA validation in progress
  | 'human_review'  // Needs human attention
  | 'done'          // Completed
  | 'pr_created'    // PR created (shown in done column)
  | 'error';        // Failed (shown in human_review column)

// Task order state (for custom ordering within columns)
type TaskOrderState = Record<TaskStatus, string[]>;

// Column preferences (persisted per project)
interface ColumnPreferences {
  [columnId: string]: {
    isCollapsed?: boolean;
    width?: number;
    isLocked?: boolean;
  };
}
```

### Task Status Columns

The Kanban board displays six visual columns:

```typescript
const TASK_STATUS_COLUMNS = [
  'backlog',
  'queue',
  'in_progress',
  'ai_review',
  'human_review',
  'done'
] as const;
```

**Note:** Tasks with status `pr_created` are displayed in the `done` column, and tasks with status `error` are displayed in the `human_review` column (errors require human attention).

---

## Usage Examples

### Basic Usage

```typescript
import { KanbanBoard } from '@/renderer/components/KanbanBoard';
import { useTaskStore } from '@/renderer/stores/task-store';

function TaskManagementView() {
  const tasks = useTaskStore((state) => state.tasks);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  return (
    <div className="h-screen">
      <KanbanBoard
        tasks={tasks}
        onTaskClick={(task) => setSelectedTask(task)}
      />
    </div>
  );
}
```

### With Task Creation

```typescript
function TaskManagementView() {
  const tasks = useTaskStore((state) => state.tasks);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  return (
    <>
      <KanbanBoard
        tasks={tasks}
        onTaskClick={(task) => navigate(`/tasks/${task.id}`)}
        onNewTaskClick={() => setShowCreateDialog(true)}
      />
      {showCreateDialog && <TaskCreateDialog onClose={() => setShowCreateDialog(false)} />}
    </>
  );
}
```

### With Refresh Functionality

```typescript
function TaskManagementView() {
  const tasks = useTaskStore((state) => state.tasks);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await window.api.tasks.refreshAll();
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <KanbanBoard
      tasks={tasks}
      onTaskClick={(task) => setSelectedTask(task)}
      onRefresh={handleRefresh}
      isRefreshing={isRefreshing}
    />
  );
}
```

---

## Advanced Features

### 1. Drag & Drop Task Movement

The KanbanBoard uses [@dnd-kit](https://dndkit.com/) for drag-and-drop functionality:

**Features:**
- 8px activation distance prevents accidental drags
- Drag overlay shows card preview during drag
- Drop zones highlight on hover
- Empty columns show drop target indicator
- Keyboard navigation support

**Task Movement:**
- Drag between columns to change status
- Drag within column to reorder tasks
- Order persists per project

**Queue System Integration:**
- Dragging to "In Progress" when at capacity automatically queues the task
- Task order within columns uses custom ordering (newest first by default)

```typescript
// Internal drag handling
const sensors = useSensors(
  useSensor(PointerSensor, {
    activationConstraint: { distance: 8 }
  }),
  useSensor(KeyboardSensor, {
    coordinateGetter: sortableKeyboardCoordinates
  })
);

// Drag end handler enforces queue limits
if (newStatus === 'in_progress' && inProgressCount >= maxParallelTasks) {
  newStatus = 'queue'; // Auto-queue if at capacity
}
```

### 2. Queue System

The queue system enforces parallel task limits with automatic FIFO promotion:

**How It Works:**
1. Project has configurable `maxParallelTasks` (default: 3)
2. When In Progress is full, new tasks go to Queue
3. When a slot opens, oldest queued task auto-promotes
4. Manual drag to In Progress respects capacity

**Queue Settings:**
- Click settings icon in Queue column header
- Adjust `maxParallelTasks` value
- Persisted per project

```typescript
// Queue processing (FIFO order)
const processQueue = async () => {
  const queuedTasks = tasks
    .filter((t) => t.status === 'queue')
    .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));

  if (inProgressCount < maxParallelTasks && queuedTasks.length > 0) {
    await persistTaskStatus(queuedTasks[0].id, 'in_progress');
  }
};
```

**Queue Actions:**
- **Queue All** - Move all backlog tasks to queue (click ListPlus icon in Backlog)
- **Settings** - Configure max parallel tasks (click Settings icon in Queue)

### 3. Column Customization

Each column supports collapse, resize, and lock operations:

#### Collapse/Expand

- Click chevron icon to collapse column to narrow strip
- Collapsed columns show rotated title and task count
- Click expand icon to restore column
- "Expand All" button appears when 3+ columns collapsed

```typescript
// Collapse state persisted per project
const toggleColumnCollapsed = (status: TaskStatus) => {
  kanbanSettingsStore.toggleColumnCollapsed(status);
  kanbanSettingsStore.savePreferences(projectId);
};
```

#### Resize

- Drag right edge of column to resize
- Width constrained between `MIN_COLUMN_WIDTH` (300px) and `MAX_COLUMN_WIDTH` (800px)
- Resize persisted per project
- Cannot resize when column is locked

```typescript
// Column width constants
const MIN_COLUMN_WIDTH = 300;
const MAX_COLUMN_WIDTH = 800;
const DEFAULT_COLUMN_WIDTH = 400;
const COLLAPSED_COLUMN_WIDTH = 48;
```

#### Lock

- Click lock icon to prevent accidental resizing
- Locked columns show amber highlight on resize handle
- Lock state persisted per project

### 4. Multi-Selection & Bulk Actions

The Human Review column supports multi-selection for bulk operations:

**Selection UI:**
- Checkbox in column header for select all / deselect all
- Shows indeterminate state when some selected
- Each task card has selection checkbox
- Floating action bar shows selected count

**Bulk Actions:**
- **Create PRs** - Opens bulk PR dialog for selected tasks
- **Clear Selection** - Deselects all tasks

```typescript
// Selection state
const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());

// Bulk PR creation
const handleOpenBulkPRDialog = () => {
  if (selectedTaskIds.size > 0) {
    setBulkPRDialogOpen(true);
  }
};
```

**Floating Action Bar:**
Appears at bottom-center when tasks are selected, showing:
- Selected count
- "Create PRs" button
- "Clear Selection" button

### 5. Archive Management

Done column includes archive functionality:

**Features:**
- **Archive All** - Move all done tasks to archived state
- **Toggle Show Archived** - Show/hide archived tasks (button shows count)
- Archived tasks have `metadata.archivedAt` timestamp
- Archive state filters tasks across entire board

```typescript
// Archive all done tasks
const handleArchiveAll = async () => {
  const doneTaskIds = tasksByStatus.done.map((t) => t.id);
  await archiveTasks(projectId, doneTaskIds);
};

// Filter tasks based on archive visibility
const filteredTasks = showArchived
  ? tasks
  : tasks.filter((t) => !t.metadata?.archivedAt);
```

### 6. Empty States

Each column shows contextual empty state when no tasks:

- **Icon** - Column-specific icon (Inbox, Loader, Eye, CheckCircle)
- **Message** - Encouraging message (e.g., "No tasks in backlog")
- **Subtext** - Helpful hint (e.g., "Create a task to get started")
- **Drop Indicator** - Shows "Drop here" message during drag-over

Empty states use i18n keys from `tasks:kanban.empty*` namespace.

### 7. Worktree Cleanup

When moving a task to Done that has an active worktree:

1. Status change fails with worktree conflict
2. `WorktreeCleanupDialog` appears
3. User confirms to force-complete and clean up worktree
4. Task moves to Done and worktree is removed

```typescript
// Status change with worktree handling
const handleStatusChange = async (taskId: string, newStatus: TaskStatus) => {
  const result = await persistTaskStatus(taskId, newStatus);

  if (!result.success && result.worktreeExists) {
    // Show cleanup confirmation dialog
    setWorktreeCleanupDialog({
      open: true,
      taskId,
      worktreePath: result.worktreePath,
      // ...
    });
  }
};
```

### 8. Smart Task Ordering

Tasks within columns maintain custom order:

**Ordering Strategy:**
1. Load persisted order from `taskOrder` state
2. New tasks (not in order) appear at top
3. Dragging within column updates order
4. Order persists per project via `task-store`
5. Stale IDs (deleted tasks) pruned automatically

```typescript
// Task ordering with new tasks at top
const validOrder = columnOrder.filter(id => currentTaskIds.has(id));
const newTasks = columnTasks.filter(t => !validOrderSet.has(t.id));

// New tasks sorted by createdAt (newest first)
newTasks.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

// Final order: new tasks, then ordered tasks
grouped[status] = [...newTasks, ...orderedTasks];
```

---

## Store Integration

### Task Store (`task-store`)

**Responsibilities:**
- Provides `tasks` array
- Persists task status changes via `persistTaskStatus()`
- Manages task order via `reorderTasksInColumn()` and `moveTaskToColumnTop()`
- Handles archive operations via `archiveTasks()`
- Registers status change listeners for queue processing

```typescript
import { useTaskStore, persistTaskStatus } from '@/renderer/stores/task-store';

// Get tasks
const tasks = useTaskStore((state) => state.tasks);

// Change task status
await persistTaskStatus(taskId, 'done');

// Reorder tasks within column
reorderTasksInColumn('backlog', draggedTaskId, targetTaskId);
```

### Project Store (`project-store`)

**Responsibilities:**
- Provides project settings (maxParallelTasks)
- Updates queue settings via `updateProjectSettings()`

```typescript
import { useProjectStore, updateProjectSettings } from '@/renderer/stores/project-store';

// Get max parallel tasks
const projects = useProjectStore((state) => state.projects);
const project = projects.find((p) => p.id === projectId);
const maxParallelTasks = project?.settings?.maxParallelTasks ?? 3;

// Update queue settings
await updateProjectSettings(projectId, { maxParallelTasks: 5 });
```

### Kanban Settings Store (`kanban-settings-store`)

**Responsibilities:**
- Manages column preferences (collapsed, width, locked)
- Persists preferences per project
- Provides constants for column dimensions

```typescript
import {
  useKanbanSettingsStore,
  COLLAPSED_COLUMN_WIDTH,
  DEFAULT_COLUMN_WIDTH,
  MIN_COLUMN_WIDTH,
  MAX_COLUMN_WIDTH
} from '@/renderer/stores/kanban-settings-store';

// Get column preferences
const columnPreferences = useKanbanSettingsStore((state) => state.columnPreferences);
const isCollapsed = columnPreferences?.['backlog']?.isCollapsed;
const width = columnPreferences?.['backlog']?.width ?? DEFAULT_COLUMN_WIDTH;

// Toggle collapsed state
toggleColumnCollapsed('backlog');
saveKanbanPreferences(projectId);
```

### View State Context (`ViewStateContext`)

**Responsibilities:**
- Manages global view state (showArchived)
- Provides `toggleShowArchived()` action

```typescript
import { useViewState } from '@/renderer/contexts/ViewStateContext';

const { showArchived, toggleShowArchived } = useViewState();
```

---

## Performance Optimizations

### 1. Memoized Columns

`DroppableColumn` uses `React.memo()` with custom comparator:

- Shallow comparison of simple props
- Deep comparison of tasks array using `tasksAreEquivalent()`
- Reference equality for function props
- Set comparison for `selectedTaskIds`

```typescript
const DroppableColumn = memo(function DroppableColumn(props) {
  // ...
}, droppableColumnPropsAreEqual);
```

### 2. Stable Handler References

Task card handlers cached in `useRef` Maps:

- `onClickHandlers` - Click handlers per task
- `onStatusChangeHandlers` - Status change handlers per task
- `onToggleSelectHandlers` - Selection toggle handlers per task

Updated only when `tasks` or callbacks change:

```typescript
useEffect(() => {
  const clickHandlers = new Map<string, () => void>();
  tasks.forEach((task) => {
    clickHandlers.set(task.id, () => onTaskClick(task));
  });
  onClickHandlers.current = clickHandlers;
}, [tasks, onTaskClick]);
```

### 3. Memoized Task Cards

Task card elements memoized to prevent recreation:

```typescript
const taskCards = useMemo(() => {
  return tasks.map((task) => (
    <SortableTaskCard
      key={task.id}
      task={task}
      onClick={onClickHandlers.current.get(task.id)}
      onStatusChange={onStatusChangeHandlers.current.get(task.id)}
      // ...
    />
  ));
}, [tasks, selectedTaskIds]);
```

### 4. Efficient Task Grouping

`tasksByStatus` uses optimized sorting:

```typescript
// Pre-compute index map for O(n) sorting instead of O(n²)
const indexMap = new Map(validOrder.map((id, idx) => [id, idx]));
const orderedTasks = columnTasks
  .filter(t => validOrderSet.has(t.id))
  .sort((a, b) => (indexMap.get(a.id) ?? 0) - (indexMap.get(b.id) ?? 0));
```

---

## Accessibility

### ARIA Labels

- Column headers have semantic headings
- Buttons have `aria-label` attributes
- Checkboxes have `aria-label` for screen readers
- Lock toggle has `aria-pressed` state
- Collapse toggle has `aria-label` with dynamic text

### Keyboard Navigation

- Full keyboard support via `@dnd-kit` sensors
- Tab navigation through interactive elements
- Enter/Space to activate buttons
- Arrow keys for drag-and-drop navigation

### Visual Feedback

- Focus indicators on interactive elements
- Hover states for drag handles and buttons
- Color-coded status badges
- Loading skeletons during refresh

---

## Internationalization (i18n)

All user-facing text uses `react-i18next` translation keys:

### Translation Namespaces

- `tasks` - Task-related content (column labels, empty states, actions)
- `dialogs` - Dialog content (worktree cleanup, queue settings)
- `common` - Common terms (buttons, errors, accessibility)

### Key Examples

```typescript
// Column labels
t(TASK_STATUS_LABELS[status]) // 'columns.backlog'

// Empty states
t('kanban.emptyBacklog') // "No tasks in backlog"
t('kanban.emptyBacklogHint') // "Create a task to get started"

// Actions
t('kanban.addTaskAriaLabel') // "Add new task"
t('kanban.queueSettings') // "Queue settings"
t('kanban.archiveAllDone') // "Archive all completed tasks"

// Selection
t('kanban.selectAll') // "Select all"
t('kanban.selectedCountOther', { count: 5 }) // "5 tasks selected"
```

---

## Common Issues & Solutions

### Issue: Queue Not Auto-Processing

**Symptom:** Tasks stay in queue when slots available

**Causes:**
1. `processQueue()` not registered as status change listener
2. Race condition from concurrent processing
3. Stale task state in memoized values

**Solution:**
- Ensure `useEffect` registers listener on mount
- Use `isProcessingQueueRef` to prevent concurrent execution
- Get current state from store: `useTaskStore.getState().tasks`

### Issue: Column Width Not Persisting

**Symptom:** Column resets to default width on reload

**Causes:**
1. `projectId` is `undefined` when saving
2. Preferences not loaded on mount
3. Save called before state update completes

**Solution:**
- Capture `projectId` in ref at resize start
- Load preferences in `useEffect` when `projectId` changes
- Use `setTimeout` to ensure state update before save

### Issue: Task Selection Lost

**Symptom:** Selected tasks deselect unexpectedly

**Causes:**
1. Tasks move out of human_review column
2. Component remounts
3. Selection state not cleaned up

**Solution:**
- Prune stale IDs in `useEffect` when `tasksByStatus.human_review` changes
- Store selection in component state (not persisted)
- Clear selection after bulk actions complete

### Issue: Drag-and-Drop Not Working

**Symptom:** Tasks can't be dragged

**Causes:**
1. Task IDs not unique
2. `SortableContext` items not memoized
3. Activation constraint too strict

**Solution:**
- Ensure each task has unique `id` property
- Memoize `taskIds` array to prevent context re-render
- Adjust `activationConstraint.distance` if needed

---

## Related Components

- **TaskCard** - Individual task card component
- **SortableTaskCard** - Draggable wrapper for TaskCard
- **TaskCardSkeleton** - Loading skeleton for task cards
- **QueueSettingsModal** - Modal for configuring queue settings
- **WorktreeCleanupDialog** - Confirmation dialog for worktree cleanup
- **BulkPRDialog** - Dialog for bulk PR creation

---

## Related Stores

- **task-store** - Task data and operations
- **project-store** - Project settings and configuration
- **kanban-settings-store** - Column preferences (collapse, width, lock)

---

## References

- [Task Types](../../apps/frontend/src/shared/types/task.ts) - TypeScript type definitions
- [Task Constants](../../apps/frontend/src/shared/constants/task.ts) - Status, labels, colors
- [Task Store](../../apps/frontend/src/renderer/stores/task-store.ts) - State management
- [@dnd-kit Documentation](https://dndkit.com/) - Drag-and-drop library

---

## Version History

- **v1.0** - Initial implementation with drag-and-drop
- **v1.1** - Added queue system with auto-promotion
- **v1.2** - Added column collapse/expand functionality
- **v1.3** - Added column resize with persistence
- **v1.4** - Added column lock to prevent accidental resize
- **v1.5** - Added multi-selection and bulk PR creation
- **v1.6** - Performance optimizations (memoization, stable handlers)
- **v1.7** - Added worktree cleanup confirmation dialog
- **v1.8** - Added "Expand All" button for collapsed columns
