/**
 * Electron adapter for the shared UI's AutoCodeClient port (U1).
 *
 * `libs/ui` is transport-agnostic: its screens consume tasks through the
 * injected AutoCodeClient. In the desktop app the renderer's task store is
 * already kept live over IPC, so the adapter maps store state into the shared
 * `UiTask` shape and exposes real-time updates via the store subscription.
 */

import type { AutoCodeClient, TaskStatus as UiTaskStatus, UiTask, UiTaskBadge } from '@auto-code/ui';
import type { Task } from '../../shared/types/task';

/** User-facing badge labels, injected from the component so they go through i18n. */
export interface UiTaskBadgeLabels {
  error: string;
  prCreated: string;
}

/** Map the desktop TaskStatus onto the shared closed set. */
export function mapStatus(status: Task['status']): UiTaskStatus {
  switch (status) {
    case 'in_progress':
      return 'running';
    case 'ai_review':
    case 'human_review':
      return 'review';
    case 'done':
    case 'pr_created':
      return 'done';
    case 'error':
      // Errored tasks need human attention: surface them in Review with a badge.
      return 'review';
    default:
      // backlog / queue / anything unknown starts in Draft.
      return 'draft';
  }
}

/** Subtask completion as 0-100, or undefined when there are no subtasks. */
export function computeProgress(task: Task): number | undefined {
  const total = task.subtasks?.length ?? 0;
  if (total <= 0) return undefined;
  const completed = task.subtasks.filter(
    (subtask) => subtask.status === 'completed',
  ).length;
  return Math.round((completed / total) * 100);
}

export function mapTaskToUiTask(task: Task, labels: UiTaskBadgeLabels): UiTask {
  const badges: UiTaskBadge[] = [];
  if (task.status === 'error') {
    badges.push({ label: labels.error, tone: 'bad' });
  }
  if (task.status === 'pr_created') {
    badges.push({ label: labels.prCreated, tone: 'good' });
  }
  return {
    id: task.id,
    title: task.title,
    status: mapStatus(task.status),
    description: task.description || undefined,
    badges: badges.length > 0 ? badges : undefined,
    progress: computeProgress(task),
  };
}

/** The slice of the zustand task store this adapter needs (unit-testable). */
export interface TaskStoreLike {
  getState(): { tasks: Task[] };
  subscribe(listener: (state: { tasks: Task[] }) => void): () => void;
}

/**
 * AutoCodeClient over the renderer task store. The store is already kept
 * fresh over IPC, so subscribeTasks piggybacks on its subscription — shared
 * screens stay live without duplicating transport logic.
 *
 * ``labels`` may be a getter so the client instance can stay stable while
 * localized badge text follows the active locale.
 */
export function createTaskStoreAutoCodeClient(
  store: TaskStoreLike,
  labels: UiTaskBadgeLabels | (() => UiTaskBadgeLabels),
): AutoCodeClient {
  const resolveLabels = typeof labels === 'function' ? labels : () => labels;
  const snapshot = (tasks: Task[]) => {
    const current = resolveLabels();
    return tasks.map((task) => mapTaskToUiTask(task, current));
  };
  return {
    listTasks: async () => snapshot(store.getState().tasks),
    subscribeTasks: (onChange) => {
      // The store fires on every state change; only re-map when the tasks
      // array itself was replaced (zustand updates it immutably).
      let lastTasks = store.getState().tasks;
      return store.subscribe((state) => {
        if (state.tasks === lastTasks) return;
        lastTasks = state.tasks;
        onChange(snapshot(state.tasks));
      });
    },
  };
}
