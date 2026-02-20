/**
 * Task Store
 *
 * Manages task/spec state with real-time updates for the web frontend.
 * Follows patterns from desktop app stores (task-store.ts) and web stores (auth-store.ts, spec-store.ts).
 *
 * WebSocket integration is available via websocket-task-integration.ts.
 * Import and initialize in your app root:
 * ```tsx
 * import { initializeWebSocketTaskIntegration } from './store/websocket-task-integration';
 * useEffect(() => {
 *   const cleanup = initializeWebSocketTaskIntegration();
 *   return cleanup;
 * }, []);
 * ```
 */

import { create } from 'zustand';
import { apiClient } from '../api/client';
import type {
  TaskSummary,
  TaskDetail,
  TaskProgressDetail,
  ExecutionProgressData,
  LogEvent
} from '../api/types';

// ============================================
// TYPES
// ============================================

/**
 * Task state shape
 */
export interface TaskState {
  // State
  tasks: TaskSummary[];
  selectedTaskId: string | null;
  currentTask: TaskDetail | null;
  taskLogs: Record<string, string[]>; // taskId -> array of log lines
  isLoading: boolean;
  isLoadingDetail: boolean;
  error: string | null;
  detailError: string | null;

  // Execution progress (for real-time updates)
  executionProgress: Record<string, ExecutionProgressData>; // taskId -> progress data

  // Actions
  setTasks: (tasks: TaskSummary[]) => void;
  addTask: (task: TaskSummary) => void;
  updateTask: (taskId: string, updates: Partial<TaskSummary>) => void;
  updateTaskStatus: (taskId: string, status: string) => void;
  selectTask: (taskId: string | null) => void;
  setLoading: (loading: boolean) => void;
  setLoadingDetail: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setDetailError: (error: string | null) => void;
  clearError: () => void;
  clearTasks: () => void;

  // Task operations
  fetchTasks: () => Promise<boolean>;
  fetchTask: (taskId: string) => Promise<boolean>;
  refreshTasks: () => Promise<boolean>;
  clearSelectedTask: () => void;

  // Log management
  appendLog: (taskId: string, log: string) => void;
  batchAppendLogs: (taskId: string, logs: string[]) => void;
  clearLogs: (taskId: string) => void;

  // Execution progress (for WebSocket updates in phase 4)
  updateExecutionProgress: (taskId: string, progress: ExecutionProgressData) => void;
  getExecutionProgress: (taskId: string) => ExecutionProgressData | undefined;

  // Task status change listeners (for queue auto-promotion)
  registerTaskStatusChangeListener: (
    listener: (taskId: string, oldStatus: string | undefined, newStatus: string) => void
  ) => () => void;

  // Selectors
  getSelectedTask: () => TaskSummary | undefined;
  getTaskById: (taskId: string) => TaskSummary | undefined;
  getTasksByStatus: (status: string) => TaskSummary[];
  getTaskLogs: (taskId: string) => string[];
}

// ============================================
// TASK STATUS CHANGE LISTENERS
// ============================================

/**
 * Task status change listeners for queue auto-promotion
 * Stored outside the store to avoid triggering re-renders
 */
const taskStatusChangeListeners = new Set<
  (taskId: string, oldStatus: string | undefined, newStatus: string) => void
>();

/**
 * Notify all registered listeners when a task status changes
 */
function notifyTaskStatusChange(
  taskId: string,
  oldStatus: string | undefined,
  newStatus: string
): void {
  for (const listener of taskStatusChangeListeners) {
    try {
      listener(taskId, oldStatus, newStatus);
    } catch (error) {
      console.error('[TaskStore] Error in task status change listener:', error);
    }
  }
}

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Helper to find task index by id or number.
 * Returns -1 if not found.
 */
function findTaskIndex(tasks: TaskSummary[], taskId: string): number {
  return tasks.findIndex((t) => t.number === taskId);
}

/**
 * Helper to update a single task efficiently.
 * Uses slice instead of map to avoid iterating all tasks.
 */
function updateTaskAtIndex(
  tasks: TaskSummary[],
  index: number,
  updater: (task: TaskSummary) => TaskSummary
): TaskSummary[] {
  if (index < 0 || index >= tasks.length) return tasks;

  const updatedTask = updater(tasks[index]);

  // If the task reference didn't change, return original array
  if (updatedTask === tasks[index]) {
    return tasks;
  }

  // Create new array with only the changed task replaced
  const newTasks = [...tasks];
  newTasks[index] = updatedTask;

  return newTasks;
}

// ============================================
// STORE
// ============================================

export const useTaskStore = create<TaskState>((set, get) => ({
  // Initial state
  tasks: [],
  selectedTaskId: null,
  currentTask: null,
  taskLogs: {},
  isLoading: false,
  isLoadingDetail: false,
  error: null,
  detailError: null,
  executionProgress: {},

  // Simple setters
  setTasks: (tasks) => set({ tasks }),

  addTask: (task) => {
    const state = get();
    const exists = state.tasks.some((t) => t.number === task.number);
    if (!exists) {
      set({ tasks: [...state.tasks, task] });
    }
  },

  updateTask: (taskId, updates) => {
    const state = get();
    const index = findTaskIndex(state.tasks, taskId);

    if (index === -1) return;

    const oldStatus = state.tasks[index].status;
    const newStatus = updates.status || oldStatus;

    const newTasks = updateTaskAtIndex(state.tasks, index, (task) => ({
      ...task,
      ...updates
    }));

    set({ tasks: newTasks });

    // Notify listeners if status changed
    if (oldStatus !== newStatus) {
      notifyTaskStatusChange(taskId, oldStatus, newStatus);
    }
  },

  updateTaskStatus: (taskId, status) => {
    const state = get();
    const index = findTaskIndex(state.tasks, taskId);

    if (index === -1) return;

    const oldStatus = state.tasks[index].status;

    const newTasks = updateTaskAtIndex(state.tasks, index, (task) => ({
      ...task,
      status
    }));

    set({ tasks: newTasks });

    // Notify listeners
    if (oldStatus !== status) {
      notifyTaskStatusChange(taskId, oldStatus, status);
    }
  },

  selectTask: (selectedTaskId) => set({ selectedTaskId }),

  setLoading: (isLoading) => set({ isLoading }),

  setLoadingDetail: (isLoadingDetail) => set({ isLoadingDetail }),

  setError: (error) => set({ error }),

  setDetailError: (detailError) => set({ detailError }),

  clearError: () => set({ error: null, detailError: null }),

  clearTasks: () =>
    set({
      tasks: [],
      selectedTaskId: null,
      currentTask: null,
      taskLogs: {},
      executionProgress: {},
      error: null,
      detailError: null
    }),

  // Task operations
  fetchTasks: async (): Promise<boolean> => {
    set({ isLoading: true, error: null });

    try {
      const result = await apiClient.listTasks();

      if (result.tasks) {
        set({
          tasks: result.tasks,
          isLoading: false,
          error: null
        });
        return true;
      }

      // No tasks returned
      set({
        tasks: [],
        isLoading: false,
        error: null
      });
      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch tasks';
      set({
        isLoading: false,
        error: errorMessage
      });
      return false;
    }
  },

  fetchTask: async (taskId: string): Promise<boolean> => {
    set({ isLoadingDetail: true, detailError: null });

    try {
      const task = await apiClient.getTask(taskId);

      set({
        currentTask: task,
        selectedTaskId: taskId,
        isLoadingDetail: false,
        detailError: null
      });
      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to fetch task details';
      set({
        currentTask: null,
        isLoadingDetail: false,
        detailError: errorMessage
      });
      return false;
    }
  },

  refreshTasks: async (): Promise<boolean> => {
    return get().fetchTasks();
  },

  clearSelectedTask: () => {
    set({
      selectedTaskId: null,
      currentTask: null,
      detailError: null
    });
  },

  // Log management
  appendLog: (taskId, log) => {
    const state = get();
    const existingLogs = state.taskLogs[taskId] || [];
    set({
      taskLogs: {
        ...state.taskLogs,
        [taskId]: [...existingLogs, log]
      }
    });
  },

  batchAppendLogs: (taskId, logs) => {
    const state = get();
    const existingLogs = state.taskLogs[taskId] || [];
    set({
      taskLogs: {
        ...state.taskLogs,
        [taskId]: [...existingLogs, ...logs]
      }
    });
  },

  clearLogs: (taskId) => {
    const state = get();
    const { [taskId]: _, ...remainingLogs } = state.taskLogs;
    set({ taskLogs: remainingLogs });
  },

  // Execution progress
  updateExecutionProgress: (taskId, progress) => {
    const state = get();
    set({
      executionProgress: {
        ...state.executionProgress,
        [taskId]: progress
      }
    });
  },

  getExecutionProgress: (taskId) => {
    return get().executionProgress[taskId];
  },

  // Task status change listeners
  registerTaskStatusChangeListener: (listener) => {
    taskStatusChangeListeners.add(listener);

    // Return unsubscribe function
    return () => {
      taskStatusChangeListeners.delete(listener);
    };
  },

  // Selectors
  getSelectedTask: () => {
    const state = get();
    return state.tasks.find((t) => t.number === state.selectedTaskId);
  },

  getTaskById: (taskId) => {
    const state = get();
    return state.tasks.find((t) => t.number === taskId);
  },

  getTasksByStatus: (status) => {
    const state = get();
    return state.tasks.filter((t) => t.status === status);
  },

  getTaskLogs: (taskId) => {
    const state = get();
    return state.taskLogs[taskId] || [];
  }
}));

// ============================================
// EXPORTED HELPER FUNCTIONS
// ============================================

/**
 * Initialize task store on app startup
 * Loads the initial list of tasks
 */
export async function initializeTasks(): Promise<void> {
  const store = useTaskStore.getState();
  await store.fetchTasks();
}

/**
 * Load a specific task by ID
 */
export async function loadTask(taskId: string): Promise<boolean> {
  const store = useTaskStore.getState();
  return await store.fetchTask(taskId);
}

/**
 * Refresh the task list
 */
export async function refreshTasks(): Promise<boolean> {
  const store = useTaskStore.getState();
  return await store.refreshTasks();
}

/**
 * Get all tasks
 */
export function getTasks(): TaskSummary[] {
  return useTaskStore.getState().tasks;
}

/**
 * Get selected task
 */
export function getSelectedTask(): TaskSummary | undefined {
  return useTaskStore.getState().getSelectedTask();
}

/**
 * Get current task detail
 */
export function getCurrentTask(): TaskDetail | null {
  return useTaskStore.getState().currentTask;
}

/**
 * Select a task by ID
 */
export function selectTask(taskId: string | null): void {
  useTaskStore.getState().selectTask(taskId);
}

/**
 * Clear selected task
 */
export function clearSelectedTask(): void {
  useTaskStore.getState().clearSelectedTask();
}

/**
 * Get tasks by status
 */
export function getTasksByStatus(status: string): TaskSummary[] {
  return useTaskStore.getState().getTasksByStatus(status);
}

/**
 * Get task logs
 */
export function getTaskLogs(taskId: string): string[] {
  return useTaskStore.getState().getTaskLogs(taskId);
}

/**
 * Append a log line to a task
 */
export function appendTaskLog(taskId: string, log: string): void {
  useTaskStore.getState().appendLog(taskId, log);
}

/**
 * Update task status
 */
export function updateTaskStatus(taskId: string, status: string): void {
  useTaskStore.getState().updateTaskStatus(taskId, status);
}

/**
 * Update execution progress for real-time updates (WebSocket integration in phase 4)
 */
export function updateExecutionProgress(taskId: string, progress: ExecutionProgressData): void {
  useTaskStore.getState().updateExecutionProgress(taskId, progress);
}

/**
 * Register a listener for task status changes (for queue auto-promotion)
 */
export function registerTaskStatusChangeListener(
  listener: (taskId: string, oldStatus: string | undefined, newStatus: string) => void
): () => void {
  return useTaskStore.getState().registerTaskStatusChangeListener(listener);
}
