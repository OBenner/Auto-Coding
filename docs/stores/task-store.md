# Store: Task Store

Zustand store for managing task state, execution progress, and task lifecycle operations.

## Overview

**Type:** Zustand State Management Store
**Location:** `apps/frontend/src/renderer/stores/task-store.ts`
**Category:** State Management
**Status:** Stable

> **Source of truth:** Task types are defined in [`apps/frontend/src/shared/types/task.ts`](../../apps/frontend/src/shared/types/task.ts) and status constants in [`apps/frontend/src/shared/constants/task.ts`](../../apps/frontend/src/shared/constants/task.ts).

### Purpose

The Task Store is the central state management solution for tasks (specs) in Auto Code. It manages task data, execution progress, task status transitions, subtasks, logs, token statistics, and Kanban board ordering. It coordinates with the backend via IPC for persistence and provides a reactive state layer for the UI.

### Key Features

- **Task Lifecycle Management:** Create, update, delete, and transition tasks through workflow statuses
- **Execution Progress Tracking:** Real-time phase tracking (planning, coding, QA review, QA fixing) with progress percentages
- **Subtask Management:** Sync subtasks from implementation plans with status tracking
- **Token Statistics:** Automatic fetching and updating of token usage stats during execution
- **Kanban Board Ordering:** Per-column drag-and-drop task ordering with localStorage persistence
- **Task Status Listeners:** Event system for reacting to task status changes (used by queue auto-promotion)
- **Log Streaming:** Batch log appending for efficient real-time log display
- **Task Draft Management:** Save/restore task creation drafts to localStorage
- **Stuck Task Recovery:** Detect and recover tasks stuck in `in_progress` without active processes

### Use Cases

- **Task List UI:** Display tasks filtered by status with reactive updates
- **Task Detail View:** Show selected task with real-time execution progress
- **Kanban Board:** Drag-and-drop task reordering within and across status columns
- **Task Creation:** Draft management for multi-step task creation flow
- **Queue Management:** Auto-promote queued tasks when `in_progress` tasks complete
- **Recovery Flow:** Detect and fix stuck tasks (status shows `in_progress` but no process running)

---

## Installation / Import

### Store Hook Import

```typescript
import { useTaskStore } from '@/renderer/stores/task-store';
```

### Helper Functions Import

```typescript
import {
  loadTasks,
  createTask,
  startTask,
  stopTask,
  submitReview,
  persistTaskStatus,
  persistUpdateTask,
  checkTaskRunning,
  recoverStuckTask,
  deleteTask,
  archiveTasks,
  saveDraft,
  loadDraft,
  clearDraft,
  hasDraft,
  isDraftEmpty,
  getTaskByGitHubIssue,
  isIncompleteHumanReview,
  getCompletedSubtaskCount,
  getTaskProgress,
  forceCompleteTask
} from '@/renderer/stores/task-store';
```

### Dependencies

**Required:**
- `zustand` - State management library
- `@dnd-kit/sortable` - Array reordering utility for drag-and-drop
- `@/shared/types` - Task, TaskStatus, SubtaskStatus, and related types
- `@/shared/utils/debug-logger` - Debug logging utility
- `@/shared/constants/phase-protocol` - Phase terminal state detection

**Optional:**
- None (all dependencies are required)

### Constants

```typescript
/** Maximum log entries stored per task to prevent renderer OOM */
export const MAX_LOG_ENTRIES = 5000;
```

### Internal Helpers

```typescript
/** Find task by id or specId */
function findTaskIndex(tasks: Task[], taskId: string): number;

/** Efficiently update a single task without recreating the entire array (if no change) */
function updateTaskAtIndex(tasks: Task[], index: number, updater: (task: Task) => Task): Task[];

/** Validate plan data structure before processing */
function validatePlanData(plan: ImplementationPlan): boolean;

/** Create empty task order with all columns */
function createEmptyTaskOrder(): TaskOrderState;

/** Async fetch and update token stats for a task */
function fetchAndUpdateTokenStats(taskId: string): Promise<void>;
```

---

## Store State

### State Shape

```typescript
interface TaskState {
  // Core state
  tasks: Task[];                    // Array of all tasks
  selectedTaskId: string | null;    // Currently selected task ID
  isLoading: boolean;               // Loading state for task operations
  error: string | null;             // Error message if operation fails
  taskOrder: TaskOrderState | null; // Per-column task ordering for Kanban

  // Actions
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  updateTaskStatus: (taskId: string, status: TaskStatus) => void;
  updateTaskFromPlan: (taskId: string, plan: ImplementationPlan) => void;
  updateExecutionProgress: (taskId: string, progress: Partial<ExecutionProgress>) => void;
  updateTokenStats: (taskId: string, tokenStats: TaskTokenStats) => void;
  appendLog: (taskId: string, log: string) => void;
  batchAppendLogs: (taskId: string, logs: string[]) => void;
  selectTask: (taskId: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearTasks: () => void;

  // Task ordering actions
  setTaskOrder: (order: TaskOrderState) => void;
  reorderTasksInColumn: (status: TaskStatus, activeId: string, overId: string) => void;
  moveTaskToColumnTop: (taskId: string, targetStatus: TaskStatus, sourceStatus?: TaskStatus) => void;
  loadTaskOrder: (projectId: string) => void;
  saveTaskOrder: (projectId: string) => boolean;
  clearTaskOrder: (projectId: string) => void;

  // Task status listeners
  registerTaskStatusChangeListener: (
    listener: (taskId: string, oldStatus: TaskStatus | undefined, newStatus: TaskStatus) => void
  ) => () => void;

  // Selectors
  getSelectedTask: () => Task | undefined;
  getTasksByStatus: (status: TaskStatus) => Task[];
}
```

### Task Type

```typescript
interface Task {
  id: string;                              // Unique task ID
  specId: string;                          // Spec directory name (e.g., "001-feature-name")
  projectId: string;                       // Parent project ID
  title: string;                           // Task title
  description: string;                     // Task description
  status: TaskStatus;                      // Current workflow status
  reviewReason?: ReviewReason;             // Reason for human review (errors, qa_rejected, completed)
  subtasks: Subtask[];                     // Implementation plan subtasks
  qaReport?: QAReport;                     // QA review report
  logs: string[];                          // Execution logs (capped at MAX_LOG_ENTRIES)
  executionProgress?: ExecutionProgress;   // Real-time execution progress
  tokenStats?: TaskTokenStats;             // Token usage statistics
  metadata?: TaskMetadata;                 // Additional metadata (GitHub issue, priority, etc.)
  releasedInVersion?: string;              // Version in which task was released
  stagedInMainProject?: boolean;           // True if worktree merged with --no-commit
  stagedAt?: string;                       // ISO timestamp when changes were staged
  location?: 'main' | 'worktree';         // Where task was loaded from
  specsPath?: string;                      // Full path to specs directory
  createdAt: Date;                         // Creation timestamp
  updatedAt: Date;                         // Last update timestamp
}
```

### TaskStatus Type

```typescript
type TaskStatus =
  | 'backlog'       // Not started
  | 'queue'         // Queued for execution
  | 'in_progress'   // Currently executing
  | 'ai_review'     // Awaiting AI QA review
  | 'human_review'  // Awaiting human review
  | 'done'          // Completed
  | 'pr_created'    // PR created on GitHub
  | 'error';        // Execution error
```

### ExecutionProgress Type

```typescript
interface ExecutionProgress {
  phase: ExecutionPhase;            // Current execution phase
  phaseProgress: number;            // Progress within phase (0-100)
  overallProgress: number;          // Overall task progress (0-100)
  currentSubtask?: string;          // Current subtask being processed
  message?: string;                 // Current status message
  startedAt?: Date;                 // When execution started
  sequenceNumber?: number;          // Monotonically increasing counter for stale update detection
  completedPhases?: CompletablePhase[]; // Phases that have successfully completed
  // Resource metrics (from backend resource_tracker.py)
  cpu_percent?: number;
  memory_mb?: number;
  memory_percent?: number;
  elapsed_seconds?: number;
  // Timing estimates (from backend timing_history.py)
  estimated_seconds?: number;
  confidence?: 'high' | 'medium' | 'low';
  sample_size?: number;
}

type ExecutionPhase =
  | 'idle'         // No active execution
  | 'planning'     // Creating implementation plan
  | 'coding'       // Implementing subtasks
  | 'qa_review'    // Running QA validation
  | 'qa_fixing'    // Fixing QA issues
  | 'complete'     // Task completed successfully
  | 'failed';      // Task failed with errors
```

### TaskOrderState Type

```typescript
interface TaskOrderState {
  backlog: string[];      // Ordered task IDs for backlog column
  queue: string[];        // Ordered task IDs for queue column
  in_progress: string[];  // Ordered task IDs for in_progress column
  ai_review: string[];    // Ordered task IDs for ai_review column
  human_review: string[]; // Ordered task IDs for human_review column
  done: string[];         // Ordered task IDs for done column
  pr_created: string[];   // Ordered task IDs for pr_created column
  error: string[];        // Ordered task IDs for error column
}
```

---

## Store Actions

### Core Task Management

#### `setTasks(tasks: Task[]): void`

**Description:** Replace entire task array (used for initial load)

**Parameters:**
- `tasks` (Task[]) - Array of tasks to set

**Example:**
```typescript
const store = useTaskStore();
store.setTasks(loadedTasks);
```

#### `addTask(task: Task): void`

**Description:** Add a new task to the store and update task order

**Parameters:**
- `task` (Task) - Task to add

**Side Effects:**
- Adds task ID to top of appropriate column in `taskOrder`

**Example:**
```typescript
const store = useTaskStore();
store.addTask(newTask);
```

#### `updateTask(taskId: string, updates: Partial<Task>): void`

**Description:** Update task properties (shallow merge)

**Parameters:**
- `taskId` (string) - Task ID or specId to update
- `updates` (Partial<Task>) - Properties to update

**Example:**
```typescript
const store = useTaskStore();
store.updateTask(taskId, {
  title: 'New Title',
  description: 'Updated description'
});
```

#### `updateTaskStatus(taskId: string, status: TaskStatus): void`

**Description:** Update task status and handle side effects (execution progress reset, token stats fetching, status change listeners)

**Parameters:**
- `taskId` (string) - Task ID or specId
- `status` (TaskStatus) - New status

**Side Effects:**
- Resets execution progress to `idle` when moving to `backlog`
- Sets default `planning` phase when moving to `in_progress` without a phase
- Fetches token stats when moving to `in_progress` or `done`
- Notifies all registered status change listeners (for queue auto-promotion)

**Example:**
```typescript
const store = useTaskStore();
store.updateTaskStatus(taskId, 'done');
```

#### `updateTaskFromPlan(taskId: string, plan: ImplementationPlan): void`

**Description:** Sync task state from implementation plan (subtasks, status calculation, feature title)

**Parameters:**
- `taskId` (string) - Task ID or specId
- `plan` (ImplementationPlan) - Implementation plan object

**Side Effects:**
- Validates plan data structure before processing (`validatePlanData()`)
- Flattens phases into subtasks array (uses `crypto.randomUUID()` for IDs with fallback)
- Recalculates task status based on subtask states with multiple safety guards:
  - **Active phase guard:** Skips status recalculation during `planning`, `coding`, `qa_review`, `qa_fixing` phases
  - **Terminal phase guard:** Skips during `complete` or `failed` phases
  - **Terminal status guard:** Never recalculates `pr_created`, `done`, or `error` statuses (finalized workflow states)
  - **Explicit human_review:** Respects `plan.status === 'human_review'` without overriding
  - **ACS-203 validation:** Blocks invalid terminal transitions (e.g., moving to `done` with incomplete subtasks)
  - **Flip-flop prevention:** Won't downgrade from `human_review`/`done` to `ai_review`

**Example:**
```typescript
const store = useTaskStore();
store.updateTaskFromPlan(taskId, implementationPlan);
```

#### `updateExecutionProgress(taskId: string, progress: Partial<ExecutionProgress>): void`

**Description:** Update task execution progress (phase, progress percentages)

**Parameters:**
- `taskId` (string) - Task ID or specId
- `progress` (Partial<ExecutionProgress>) - Progress update

**Side Effects:**
- Drops out-of-order updates (based on sequence numbers)
- Only updates `updatedAt` on phase transitions (not progress ticks) to reduce re-renders
- Fetches token stats when phase changes

**Example:**
```typescript
const store = useTaskStore();
store.updateExecutionProgress(taskId, {
  phase: 'coding',
  phaseProgress: 45,
  overallProgress: 30,
  sequenceNumber: 5
});
```

#### `updateTokenStats(taskId: string, tokenStats: TaskTokenStats): void`

**Description:** Update task token usage statistics

**Parameters:**
- `taskId` (string) - Task ID or specId
- `tokenStats` (TaskTokenStats) - Token statistics object

**Example:**
```typescript
const store = useTaskStore();
store.updateTokenStats(taskId, {
  total_tokens: 12500,
  planning_tokens: 3200,
  coding_tokens: 8100,
  qa_tokens: 1200
});
```

### Log Management

#### `appendLog(taskId: string, log: string): void`

**Description:** Append a single log entry to task logs

**Parameters:**
- `taskId` (string) - Task ID or specId
- `log` (string) - Log line to append

**Example:**
```typescript
const store = useTaskStore();
store.appendLog(taskId, '[Coder] Implementing feature...');
```

#### `batchAppendLogs(taskId: string, logs: string[]): void`

**Description:** Append multiple log entries at once (more efficient than calling `appendLog` multiple times)

**Parameters:**
- `taskId` (string) - Task ID or specId
- `logs` (string[]) - Array of log lines to append

**Example:**
```typescript
const store = useTaskStore();
store.batchAppendLogs(taskId, [
  '[Planner] Creating implementation plan...',
  '[Planner] Plan created successfully'
]);
```

### Selection and UI State

#### `selectTask(taskId: string | null): void`

**Description:** Select a task for detail view

**Parameters:**
- `taskId` (string | null) - Task ID to select, or null to deselect

**Side Effects:**
- Fetches token stats for the selected task

**Example:**
```typescript
const store = useTaskStore();
store.selectTask(taskId);
```

#### `setLoading(loading: boolean): void`

**Description:** Set loading state for task operations

**Example:**
```typescript
const store = useTaskStore();
store.setLoading(true);
```

#### `setError(error: string | null): void`

**Description:** Set error message for task operations

**Example:**
```typescript
const store = useTaskStore();
store.setError('Failed to load tasks');
```

#### `clearTasks(): void`

**Description:** Clear all tasks and reset selection/task order

**Example:**
```typescript
const store = useTaskStore();
store.clearTasks();
```

### Task Ordering (Kanban Board)

#### `setTaskOrder(order: TaskOrderState): void`

**Description:** Set task ordering for all columns

**Parameters:**
- `order` (TaskOrderState) - Complete task order state

**Example:**
```typescript
const store = useTaskStore();
store.setTaskOrder(loadedOrder);
```

#### `reorderTasksInColumn(status: TaskStatus, activeId: string, overId: string): void`

**Description:** Reorder tasks within a single column (drag-and-drop)

**Parameters:**
- `status` (TaskStatus) - Column to reorder
- `activeId` (string) - Task ID being dragged
- `overId` (string) - Task ID being dragged over

**Example:**
```typescript
const store = useTaskStore();
store.reorderTasksInColumn('backlog', 'task-1', 'task-3');
```

#### `moveTaskToColumnTop(taskId: string, targetStatus: TaskStatus, sourceStatus?: TaskStatus): void`

**Description:** Move a task to the top of a column (used when status changes)

**Parameters:**
- `taskId` (string) - Task ID to move
- `targetStatus` (TaskStatus) - Target column
- `sourceStatus` (TaskStatus, optional) - Source column (to remove from)

**Example:**
```typescript
const store = useTaskStore();
store.moveTaskToColumnTop(taskId, 'in_progress', 'queue');
```

#### `loadTaskOrder(projectId: string): void`

**Description:** Load task order from localStorage

**Parameters:**
- `projectId` (string) - Project ID to load order for

**Side Effects:**
- Validates loaded data structure
- Falls back to empty order if validation fails

**Example:**
```typescript
const store = useTaskStore();
store.loadTaskOrder(projectId);
```

#### `saveTaskOrder(projectId: string): boolean`

**Description:** Save task order to localStorage

**Parameters:**
- `projectId` (string) - Project ID to save order for

**Returns:** `true` if saved successfully, `false` otherwise

**Example:**
```typescript
const store = useTaskStore();
const saved = store.saveTaskOrder(projectId);
```

#### `clearTaskOrder(projectId: string): void`

**Description:** Clear task order from localStorage

**Parameters:**
- `projectId` (string) - Project ID to clear order for

**Example:**
```typescript
const store = useTaskStore();
store.clearTaskOrder(projectId);
```

### Task Status Listeners

#### `registerTaskStatusChangeListener(listener: Function): () => void`

**Description:** Register a listener for task status changes (used by queue auto-promotion)

**Parameters:**
- `listener` (Function) - Callback function `(taskId, oldStatus, newStatus) => void`

**Returns:** Cleanup function to unregister the listener

**Example:**
```typescript
const store = useTaskStore();
const unregister = store.registerTaskStatusChangeListener((taskId, oldStatus, newStatus) => {
  console.log(`Task ${taskId} changed from ${oldStatus} to ${newStatus}`);
});

// Later, cleanup
unregister();
```

---

## Store Selectors

### `getSelectedTask(): Task | undefined`

**Description:** Get the currently selected task

**Returns:** Selected task or undefined

**Example:**
```typescript
const store = useTaskStore();
const selectedTask = store.getSelectedTask();
```

### `getTasksByStatus(status: TaskStatus): Task[]`

**Description:** Get all tasks with a specific status

**Parameters:**
- `status` (TaskStatus) - Status to filter by

**Returns:** Array of tasks matching the status

**Example:**
```typescript
const store = useTaskStore();
const inProgressTasks = store.getTasksByStatus('in_progress');
```

---

## Helper Functions (Exported)

### Task Loading

#### `loadTasks(projectId: string, options?: { forceRefresh?: boolean }): Promise<void>`

**Description:** Load tasks for a project from the backend

**Parameters:**
- `projectId` (string) - Project ID to load tasks for
- `options.forceRefresh` (boolean, optional) - If true, invalidates server-side cache before fetching

**Side Effects:**
- Sets loading state
- Calls `window.electronAPI.getTasks()`
- Updates store with loaded tasks

**Example:**
```typescript
await loadTasks(projectId);
await loadTasks(projectId, { forceRefresh: true }); // Force refresh
```

### Task Creation

#### `createTask(projectId: string, title: string, description: string, metadata?: TaskMetadata): Promise<Task | null>`

**Description:** Create a new task

**Parameters:**
- `projectId` (string) - Parent project ID
- `title` (string) - Task title
- `description` (string) - Task description
- `metadata` (TaskMetadata, optional) - Additional metadata

**Returns:** Created task or null on failure

**Side Effects:**
- Calls `window.electronAPI.createTask()`
- Adds task to store on success

**Example:**
```typescript
const task = await createTask(
  projectId,
  'Add user authentication',
  'Implement JWT-based authentication',
  { priority: 'high', complexity: 'standard' }
);
```

### Task Execution

#### `startTask(taskId: string, options?: { parallel?: boolean; workers?: number }): void`

**Description:** Start task execution

**Parameters:**
- `taskId` (string) - Task ID to start
- `options.parallel` (boolean, optional) - Enable parallel execution
- `options.workers` (number, optional) - Number of parallel workers

**Side Effects:**
- Calls `window.electronAPI.startTask()`

**Example:**
```typescript
startTask(taskId);
startTask(taskId, { parallel: true, workers: 2 }); // Parallel mode
```

#### `stopTask(taskId: string): void`

**Description:** Stop task execution

**Parameters:**
- `taskId` (string) - Task ID to stop

**Side Effects:**
- Calls `window.electronAPI.stopTask()`

**Example:**
```typescript
stopTask(taskId);
```

### Task Review

#### `submitReview(taskId: string, approved: boolean, feedback?: string, images?: ImageAttachment[]): Promise<boolean>`

**Description:** Submit human review decision for a task

**Parameters:**
- `taskId` (string) - Task ID to review
- `approved` (boolean) - Review decision
- `feedback` (string, optional) - Feedback message
- `images` (ImageAttachment[], optional) - Screenshot attachments

**Returns:** `true` if submitted successfully

**Side Effects:**
- Calls `window.electronAPI.submitReview()`
- Updates task status to `done` (approved) or `in_progress` (rejected)

**Example:**
```typescript
const success = await submitReview(
  taskId,
  false,
  'Please fix the login button styling',
  [{ data: 'base64...', filename: 'screenshot.png', mimeType: 'image/png' }]
);
```

### Task Status Persistence

#### `persistTaskStatus(taskId: string, status: TaskStatus, options?: { forceCleanup?: boolean }): Promise<PersistStatusResult>`

**Description:** Update task status and persist to backend

**Parameters:**
- `taskId` (string) - Task ID to update
- `status` (TaskStatus) - New status
- `options.forceCleanup` (boolean, optional) - Force worktree cleanup for `done` status

**Returns:** Result object with success flag and optional worktree info

**Side Effects:**
- Calls `window.electronAPI.updateTaskStatus()`
- Updates store only after backend confirms success
- May return worktree exists warning (requires user confirmation)

**Example:**
```typescript
const result = await persistTaskStatus(taskId, 'done');
if (result.worktreeExists) {
  // Show confirmation dialog
  console.log('Worktree exists at:', result.worktreePath);
}
```

#### `forceCompleteTask(taskId: string): Promise<PersistStatusResult>`

**Description:** Force complete a task by cleaning up its worktree

**Parameters:**
- `taskId` (string) - Task ID to complete

**Returns:** Result object with success flag

**Side Effects:**
- Calls `persistTaskStatus` with `forceCleanup: true`

**Example:**
```typescript
const result = await forceCompleteTask(taskId);
```

### Task Update Persistence

#### `persistUpdateTask(taskId: string, updates: { title?: string; description?: string; metadata?: Partial<TaskMetadata> }): Promise<boolean>`

**Description:** Update task title/description/metadata and persist to backend

**Parameters:**
- `taskId` (string) - Task ID to update
- `updates` (object) - Properties to update

**Returns:** `true` if updated successfully

**Side Effects:**
- Calls `window.electronAPI.updateTask()`
- Updates store with returned task data

**Example:**
```typescript
const success = await persistUpdateTask(taskId, {
  title: 'Updated Title',
  metadata: { priority: 'high' }
});
```

### Task Recovery

#### `checkTaskRunning(taskId: string): Promise<boolean>`

**Description:** Check if a task has an active running process

**Parameters:**
- `taskId` (string) - Task ID to check

**Returns:** `true` if process is running

**Example:**
```typescript
const isRunning = await checkTaskRunning(taskId);
```

#### `recoverStuckTask(taskId: string, options?: { targetStatus?: TaskStatus; autoRestart?: boolean }): Promise<{ success: boolean; message: string; autoRestarted?: boolean }>`

**Description:** Recover a stuck task (status shows `in_progress` but no process running)

**Parameters:**
- `taskId` (string) - Task ID to recover
- `options.targetStatus` (TaskStatus, optional) - Target status to reset to
- `options.autoRestart` (boolean, optional) - Auto-restart task (default: true)

**Returns:** Recovery result with success flag and message

**Side Effects:**
- Calls `window.electronAPI.recoverStuckTask()`
- Updates task status

**Example:**
```typescript
const result = await recoverStuckTask(taskId, { autoRestart: true });
console.log(result.message); // "Task recovered and restarted"
```

### Task Deletion

#### `deleteTask(taskId: string): Promise<{ success: boolean; error?: string }>`

**Description:** Delete a task and its spec directory

**Parameters:**
- `taskId` (string) - Task ID to delete

**Returns:** Result object with success flag

**Side Effects:**
- Calls `window.electronAPI.deleteTask()`
- Removes task from store
- Clears selection if deleted task was selected

**Example:**
```typescript
const result = await deleteTask(taskId);
if (result.success) {
  console.log('Task deleted');
}
```

### Task Archival

#### `archiveTasks(projectId: string, taskIds: string[], version?: string): Promise<{ success: boolean; error?: string }>`

**Description:** Archive tasks (marks them as archived in metadata)

**Parameters:**
- `projectId` (string) - Project ID
- `taskIds` (string[]) - Array of task IDs to archive
- `version` (string, optional) - Version tag for archived tasks

**Returns:** Result object with success flag

**Side Effects:**
- Calls `window.electronAPI.archiveTasks()`
- Reloads tasks to update UI

**Example:**
```typescript
const result = await archiveTasks(projectId, [taskId1, taskId2], 'v1.0.0');
```

### Draft Management

#### `saveDraft(draft: TaskDraft): void`

**Description:** Save task creation draft to localStorage

**Parameters:**
- `draft` (TaskDraft) - Draft object to save

**Side Effects:**
- Strips full image data (keeps only thumbnails) to avoid localStorage limits

**Example:**
```typescript
saveDraft({
  projectId,
  title: 'Partial title',
  description: '',
  images: [],
  category: 'feature'
});
```

#### `loadDraft(projectId: string): TaskDraft | null`

**Description:** Load task creation draft from localStorage

**Parameters:**
- `projectId` (string) - Project ID

**Returns:** Draft object or null if not found

**Example:**
```typescript
const draft = loadDraft(projectId);
```

#### `clearDraft(projectId: string): void`

**Description:** Clear task creation draft from localStorage

**Parameters:**
- `projectId` (string) - Project ID

**Example:**
```typescript
clearDraft(projectId);
```

#### `hasDraft(projectId: string): boolean`

**Description:** Check if a draft exists for a project

**Parameters:**
- `projectId` (string) - Project ID

**Returns:** `true` if draft exists

**Example:**
```typescript
if (hasDraft(projectId)) {
  // Show "Restore Draft" button
}
```

#### `isDraftEmpty(draft: TaskDraft | null): boolean`

**Description:** Check if a draft has any meaningful content

**Parameters:**
- `draft` (TaskDraft | null) - Draft to check

**Returns:** `true` if draft is empty (no title, description, images, or metadata)

**Example:**
```typescript
const draft = loadDraft(projectId);
if (!isDraftEmpty(draft)) {
  // Show restore prompt
}
```

### Task Query Helpers

#### `getTaskByGitHubIssue(issueNumber: number): Task | undefined`

**Description:** Find a task by GitHub issue number

**Parameters:**
- `issueNumber` (number) - GitHub issue number

**Returns:** Task with matching issue number or undefined

**Example:**
```typescript
const task = getTaskByGitHubIssue(42);
if (task) {
  console.log('Task already exists for issue #42');
}
```

#### `isIncompleteHumanReview(task: Task): boolean`

**Description:** Check if a task is in `human_review` but has no completed subtasks (indicates crash/exit before implementation)

**Parameters:**
- `task` (Task) - Task to check

**Returns:** `true` if task is incomplete human review

**Example:**
```typescript
if (isIncompleteHumanReview(task)) {
  // Show "Resume" button instead of "Review"
}
```

#### `getCompletedSubtaskCount(task: Task): number`

**Description:** Get the count of completed subtasks for a task

**Parameters:**
- `task` (Task) - Task to count

**Returns:** Number of completed subtasks

**Example:**
```typescript
const completed = getCompletedSubtaskCount(task);
console.log(`${completed} of ${task.subtasks?.length || 0} subtasks completed`);
```

#### `getTaskProgress(task: Task): { completed: number; total: number; percentage: number }`

**Description:** Get task progress info (completed, total, percentage)

**Parameters:**
- `task` (Task) - Task to calculate progress for

**Returns:** Progress object

**Example:**
```typescript
const { completed, total, percentage } = getTaskProgress(task);
console.log(`Progress: ${percentage}% (${completed}/${total})`);
```

---

## Usage Examples

### Basic Usage

#### Using the Store Hook

```typescript
import { useTaskStore } from '@/renderer/stores/task-store';

function TaskList() {
  // Subscribe to specific state slices
  const tasks = useTaskStore(state => state.tasks);
  const selectedTaskId = useTaskStore(state => state.selectedTaskId);
  const isLoading = useTaskStore(state => state.isLoading);

  // Access actions
  const selectTask = useTaskStore(state => state.selectTask);
  const updateTaskStatus = useTaskStore(state => state.updateTaskStatus);

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      {tasks.map(task => (
        <div
          key={task.id}
          onClick={() => selectTask(task.id)}
          className={selectedTaskId === task.id ? 'selected' : ''}
        >
          <h3>{task.title}</h3>
          <p>{task.status}</p>
        </div>
      ))}
    </div>
  );
}
```

#### Loading Tasks on Mount

```typescript
import { useEffect } from 'react';
import { useTaskStore, loadTasks } from '@/renderer/stores/task-store';
import { useProjectStore } from '@/renderer/stores/project-store';

function TasksView() {
  const currentProjectId = useProjectStore(state => state.currentProjectId);
  const tasks = useTaskStore(state => state.tasks);
  const isLoading = useTaskStore(state => state.isLoading);

  useEffect(() => {
    if (currentProjectId) {
      loadTasks(currentProjectId);
    }
  }, [currentProjectId]);

  if (isLoading) return <div>Loading tasks...</div>;

  return (
    <div>
      {tasks.map(task => (
        <TaskCard key={task.id} task={task} />
      ))}
    </div>
  );
}
```

### Advanced Usage

#### Task Creation with Draft Management

```typescript
import { useState, useEffect } from 'react';
import {
  createTask,
  saveDraft,
  loadDraft,
  clearDraft,
  hasDraft,
  isDraftEmpty
} from '@/renderer/stores/task-store';
import { useProjectStore } from '@/renderer/stores/project-store';

function CreateTaskDialog() {
  const currentProjectId = useProjectStore(state => state.currentProjectId);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [showRestoreDraft, setShowRestoreDraft] = useState(false);

  // Check for existing draft on mount
  useEffect(() => {
    if (currentProjectId) {
      const draft = loadDraft(currentProjectId);
      if (draft && !isDraftEmpty(draft)) {
        setShowRestoreDraft(true);
      }
    }
  }, [currentProjectId]);

  // Auto-save draft
  useEffect(() => {
    if (currentProjectId && (title || description)) {
      saveDraft({
        projectId: currentProjectId,
        title,
        description,
        images: [],
        savedAt: new Date()
      });
    }
  }, [title, description, currentProjectId]);

  const handleRestoreDraft = () => {
    const draft = loadDraft(currentProjectId);
    if (draft) {
      setTitle(draft.title);
      setDescription(draft.description);
      setShowRestoreDraft(false);
    }
  };

  const handleSubmit = async () => {
    const task = await createTask(currentProjectId, title, description);
    if (task) {
      clearDraft(currentProjectId);
      setTitle('');
      setDescription('');
    }
  };

  return (
    <div>
      {showRestoreDraft && (
        <button onClick={handleRestoreDraft}>Restore Draft</button>
      )}
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Task title"
      />
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Task description"
      />
      <button onClick={handleSubmit}>Create Task</button>
    </div>
  );
}
```

#### Real-Time Execution Progress Display

```typescript
import { useTaskStore } from '@/renderer/stores/task-store';

function TaskExecutionProgress({ taskId }: { taskId: string }) {
  const task = useTaskStore(state =>
    state.tasks.find(t => t.id === taskId)
  );

  if (!task?.executionProgress) return null;

  const { phase, phaseProgress, overallProgress } = task.executionProgress;

  const phaseLabels = {
    idle: 'Idle',
    planning: 'Planning',
    coding: 'Implementing',
    qa_review: 'QA Review',
    qa_fixing: 'Fixing Issues',
    complete: 'Complete',
    failed: 'Failed'
  };

  return (
    <div>
      <h4>Execution Progress</h4>
      <p>Phase: {phaseLabels[phase]}</p>
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${phaseProgress}%` }}
        />
      </div>
      <p>Phase Progress: {phaseProgress}%</p>
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${overallProgress}%` }}
        />
      </div>
      <p>Overall Progress: {overallProgress}%</p>
    </div>
  );
}
```

#### Queue Auto-Promotion

```typescript
import { useEffect, useRef } from 'react';
import { useTaskStore, startTask } from '@/renderer/stores/task-store';

function QueueAutoPromotion() {
  const tasks = useTaskStore(state => state.tasks);
  const registerListener = useTaskStore(state => state.registerTaskStatusChangeListener);

  // Use ref to access latest tasks inside listener without re-registering
  const tasksRef = useRef(tasks);
  tasksRef.current = tasks;

  useEffect(() => {
    // Register listener once on mount - use tasksRef for current tasks
    const unregister = registerListener((taskId, oldStatus, newStatus) => {
      // When a task moves out of in_progress, check queue
      if (oldStatus === 'in_progress' && newStatus !== 'in_progress') {
        const currentTasks = tasksRef.current;
        const queuedTasks = currentTasks.filter(t => t.status === 'queue');
        const inProgressTasks = currentTasks.filter(t => t.status === 'in_progress');

        // If queue has tasks and no other tasks are running, start the first queued task
        if (queuedTasks.length > 0 && inProgressTasks.length === 0) {
          const nextTask = queuedTasks[0];
          console.log(`[QueueAutoPromotion] Starting queued task: ${nextTask.title}`);
          startTask(nextTask.id);
        }
      }
    });

    // Cleanup on unmount
    return unregister;
  }, [registerListener]); // Only re-register if registerListener changes

  return null; // This is a logic-only component
}
```

#### Stuck Task Recovery

```typescript
import { useEffect, useState } from 'react';
import { useTaskStore, checkTaskRunning, recoverStuckTask } from '@/renderer/stores/task-store';

function StuckTaskDetector() {
  const tasks = useTaskStore(state => state.tasks);
  const [stuckTaskIds, setStuckTaskIds] = useState<string[]>([]);

  useEffect(() => {
    // Check for stuck tasks every 30 seconds
    const interval = setInterval(async () => {
      const inProgressTasks = tasks.filter(t => t.status === 'in_progress');
      const stuckIds: string[] = [];

      for (const task of inProgressTasks) {
        const isRunning = await checkTaskRunning(task.id);
        if (!isRunning) {
          stuckIds.push(task.id);
        }
      }

      setStuckTaskIds(stuckIds);
    }, 30000);

    return () => clearInterval(interval);
  }, [tasks]);

  const handleRecover = async (taskId: string) => {
    const result = await recoverStuckTask(taskId, { autoRestart: true });
    if (result.success) {
      console.log('Task recovered:', result.message);
      setStuckTaskIds(prev => prev.filter(id => id !== taskId));
    }
  };

  if (stuckTaskIds.length === 0) return null;

  return (
    <div className="stuck-task-alert">
      <h4>Stuck Tasks Detected</h4>
      {stuckTaskIds.map(taskId => {
        const task = tasks.find(t => t.id === taskId);
        return (
          <div key={taskId}>
            <p>{task?.title} is stuck</p>
            <button onClick={() => handleRecover(taskId)}>
              Recover and Restart
            </button>
          </div>
        );
      })}
    </div>
  );
}
```

#### Kanban Board with Drag-and-Drop

```typescript
import { useTaskStore, persistTaskStatus } from '@/renderer/stores/task-store';
import { DndContext, DragEndEvent } from '@dnd-kit/core';
import { SortableContext } from '@dnd-kit/sortable';

function KanbanBoard() {
  const tasks = useTaskStore(state => state.tasks);
  const taskOrder = useTaskStore(state => state.taskOrder);
  const reorderTasksInColumn = useTaskStore(state => state.reorderTasksInColumn);
  const moveTaskToColumnTop = useTaskStore(state => state.moveTaskToColumnTop);

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    const activeTask = tasks.find(t => t.id === activeId);
    const overTask = tasks.find(t => t.id === overId);

    if (!activeTask || !overTask) return;

    // Same column - reorder only
    if (activeTask.status === overTask.status) {
      reorderTasksInColumn(activeTask.status, activeId, overId);
    }
    // Different column - change status and move to top
    else {
      await persistTaskStatus(activeId, overTask.status);
      moveTaskToColumnTop(activeId, overTask.status, activeTask.status);
    }
  };

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="kanban-board">
        {(['backlog', 'queue', 'in_progress', 'done'] as const).map(status => (
          <div key={status} className="kanban-column">
            <h3>{status}</h3>
            <SortableContext items={taskOrder?.[status] || []}>
              {taskOrder?.[status]?.map(taskId => {
                const task = tasks.find(t => t.id === taskId);
                return task ? <TaskCard key={task.id} task={task} /> : null;
              })}
            </SortableContext>
          </div>
        ))}
      </div>
    </DndContext>
  );
}
```

---

## Performance Considerations

### Optimization Tips

1. **Selective State Subscription** - Subscribe only to needed state slices
   ```typescript
   // ❌ BAD - Subscribes to entire store
   const store = useTaskStore();

   // ✅ GOOD - Subscribes only to tasks array
   const tasks = useTaskStore(state => state.tasks);
   ```

2. **Memo Selectors** - Use memoized selectors for derived state
   ```typescript
   const inProgressTasks = useTaskStore(state =>
     state.tasks.filter(t => t.status === 'in_progress')
   );
   // Note: This creates a new array on every render - consider useMemo
   ```

3. **Batch Log Updates** - Use `batchAppendLogs` instead of multiple `appendLog` calls
   ```typescript
   // ❌ BAD
   store.appendLog(taskId, log1);
   store.appendLog(taskId, log2);
   store.appendLog(taskId, log3);

   // ✅ GOOD
   store.batchAppendLogs(taskId, [log1, log2, log3]);
   ```

4. **Sequence Numbers** - Use sequence numbers for execution progress to prevent out-of-order updates
   ```typescript
   store.updateExecutionProgress(taskId, {
     phase: 'coding',
     phaseProgress: 50,
     sequenceNumber: Date.now()
   });
   ```

### Performance Metrics

| Operation | Target | Notes |
|-----------|--------|-------|
| `setTasks()` | < 50ms | For ~100 tasks |
| `updateTask()` | < 5ms | Uses efficient array slicing |
| `updateTaskFromPlan()` | < 20ms | Includes subtask flattening and status calculation |
| `batchAppendLogs()` | < 10ms | Single state update for N logs |

---

## Best Practices

### DO

✅ **Use selective state subscription**
```typescript
const tasks = useTaskStore(state => state.tasks);
const selectTask = useTaskStore(state => state.selectTask);
```

✅ **Use helper functions for IPC operations**
```typescript
await loadTasks(projectId);
await createTask(projectId, title, description);
```

✅ **Check task running status before recovery**
```typescript
const isRunning = await checkTaskRunning(taskId);
if (!isRunning && task.status === 'in_progress') {
  await recoverStuckTask(taskId);
}
```

✅ **Save task order after reordering**
```typescript
const saveTaskOrder = useTaskStore(state => state.saveTaskOrder);
const saved = saveTaskOrder(projectId);
```

### DON'T

❌ **Don't mutate task objects directly**
```typescript
// WRONG
task.status = 'done';

// RIGHT
store.updateTask(task.id, { status: 'done' });
```

❌ **Don't call updateTaskStatus for local-only changes**
```typescript
// WRONG - Use persistTaskStatus for status changes that need backend persistence
store.updateTaskStatus(taskId, 'done');

// RIGHT
await persistTaskStatus(taskId, 'done');
```

❌ **Don't skip sequence numbers for execution progress**
```typescript
// WRONG - Allows out-of-order updates
store.updateExecutionProgress(taskId, { phase: 'coding', phaseProgress: 50 });

// RIGHT - Include sequence number
store.updateExecutionProgress(taskId, {
  phase: 'coding',
  phaseProgress: 50,
  sequenceNumber: Date.now()
});
```

---

## Troubleshooting

### Common Issues

#### Issue: Tasks not loading

**Cause:** Project not selected or IPC error

**Solution:**
1. Verify `currentProjectId` is set
2. Check browser console for IPC errors
3. Verify backend is running
4. Try force refresh: `loadTasks(projectId, { forceRefresh: true })`

#### Issue: Task status not persisting

**Cause:** Using `updateTaskStatus` instead of `persistTaskStatus`

**Solution:**
Use `persistTaskStatus` for status changes that need backend persistence:
```typescript
await persistTaskStatus(taskId, 'done');
```

#### Issue: Execution progress updates out of order

**Cause:** Missing sequence numbers

**Solution:**
Always include sequence numbers:
```typescript
store.updateExecutionProgress(taskId, {
  phase: 'coding',
  phaseProgress: 50,
  sequenceNumber: Date.now()
});
```

#### Issue: Stuck task not detected

**Cause:** Task is in `backlog` or other non-executing status

**Solution:**
Only check tasks with `status === 'in_progress'`:
```typescript
const inProgressTasks = tasks.filter(t => t.status === 'in_progress');
for (const task of inProgressTasks) {
  const isRunning = await checkTaskRunning(task.id);
  if (!isRunning) {
    await recoverStuckTask(task.id);
  }
}
```

#### Issue: Worktree exists error when marking task as done

**Cause:** Task has uncommitted work in its worktree

**Solution:**
Show confirmation dialog and use `forceCompleteTask`:
```typescript
const result = await persistTaskStatus(taskId, 'done');
if (result.worktreeExists) {
  const confirmed = confirm(`Worktree exists at ${result.worktreePath}. Delete and mark as done?`);
  if (confirmed) {
    await forceCompleteTask(taskId);
  }
}
```

---

## Related Stores/Modules

### Similar Stores

- [project-store](./project-store.md) - Manages projects and current project selection
- [settings-store](./settings-store.md) - Manages user settings and preferences

### Dependencies

- [Shared Types](../api/shared-types.md) - Task, TaskStatus, SubtaskStatus type definitions
- [IPC API](../api/electron-api.md) - Backend communication layer

### Used By

- [TaskList Component](../components/task-list.md) - Task list display
- [TaskDetail Component](../components/task-detail.md) - Task detail view
- [KanbanBoard Component](../components/kanban-board.md) - Kanban board UI
- [CreateTaskDialog Component](../components/create-task-dialog.md) - Task creation flow
- [QueueManager](../modules/queue-manager.md) - Queue auto-promotion logic

---

**Document Information:**
- **Store Version:** 2.8.0
- **Last Updated:** 2026-02-07
- **Maintainer:** Auto Code Team
- **Status:** Stable
- **Compatibility:** Zustand 5.0+, Electron 33+
