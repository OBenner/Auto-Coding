/**
 * Electron adapter for the shared UI's AutoCodeClient port (U1).
 *
 * `libs/ui` is transport-agnostic: its screens consume tasks through the
 * injected AutoCodeClient. In the desktop app the renderer's task store is
 * already kept live over IPC, so the adapter maps store state into the shared
 * `UiTask` shape and exposes real-time updates via the store subscription.
 */

import type {
  AutoCodeClient,
  TaskStatus as UiTaskStatus,
  UiMetaSection,
  UiTask,
  UiTaskBadge,
  UiTaskDetail,
} from '@auto-code/ui';
import type { ExecutionProgress, Task } from '../../shared/types/task';

/** User-facing badge labels, injected from the component so they go through i18n. */
export interface UiTaskBadgeLabels {
  error: string;
  prCreated: string;
  /** Chip label per raw desktop status (rendered next to the card id). */
  statusChips: Record<Task['status'], string>;
  /** Card meta-row label per execution phase (shown on active cards). */
  phases: Record<ExecutionProgress['phase'], string>;
}

const CHIP_TONES: Record<Task['status'], UiTaskBadge['tone']> = {
  backlog: 'neutral',
  queue: 'neutral',
  in_progress: 'info',
  ai_review: 'warn',
  human_review: 'warn',
  done: 'good',
  pr_created: 'good',
  error: 'bad',
};

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

/** "22m" / "1h 05m" from elapsed seconds; empty string when not renderable. */
export function formatElapsed(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 1) return '<1m';
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${String(minutes % 60).padStart(2, '0')}m`;
}

/** Bottom meta row for active cards: current phase label + elapsed time. */
function buildMeta(task: Task, labels: UiTaskBadgeLabels): string[] | undefined {
  const progress = task.executionProgress;
  // 'idle' is the frontend-only pre-start state — a meta row would be noise.
  if (progress == null || progress.phase === 'idle') return undefined;
  const parts: string[] = [];
  const phaseLabel = labels.phases?.[progress.phase];
  if (phaseLabel) parts.push(phaseLabel);
  if (progress.elapsed_seconds != null) {
    const elapsed = formatElapsed(progress.elapsed_seconds);
    if (elapsed) parts.push(elapsed);
  }
  return parts.length > 0 ? parts : undefined;
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
    statusChip: {
      label: labels.statusChips?.[task.status] ?? task.status,
      tone: CHIP_TONES[task.status],
    },
    badges: badges.length > 0 ? badges : undefined,
    progress: computeProgress(task),
    meta: buildMeta(task, labels),
  };
}

/** Detail view of a store task: base card fields + subtask breakdown + rows.

The renderer store carries no spec body; the client's ``loadSpecContent``
option fetches it separately (over IPC) when the detail is requested. */
export function mapTaskToUiTaskDetail(
  task: Task,
  labels: UiTaskBadgeLabels,
): UiTaskDetail {
  const subtasks = task.subtasks ?? [];
  const count = (status: string) =>
    subtasks.filter((subtask) => subtask.status === status).length;
  return {
    ...mapTaskToUiTask(task, labels),
    progressBreakdown:
      subtasks.length > 0
        ? {
            completed: count('completed'),
            inProgress: count('in_progress'),
            pending: count('pending'),
            failed: count('failed'),
            total: subtasks.length,
          }
        : undefined,
    // Desktop subtask statuses are already the shared closed set.
    subtasks:
      subtasks.length > 0
        ? subtasks.map((subtask) => ({
            id: subtask.id,
            title: subtask.title,
            description: subtask.description || undefined,
            status: subtask.status,
          }))
        : undefined,
  };
}

/** The slice of the zustand task store this adapter needs (unit-testable). */
export interface TaskStoreLike {
  getState(): { tasks: Task[] };
  subscribe(listener: (state: { tasks: Task[] }) => void): () => void;
}

export interface TaskStoreClientOptions {
  /**
   * Fetch the spec document body for a task (e.g. over IPC), or null when
   * unavailable. The spec body is progressive enhancement: failures are
   * swallowed and the detail view renders without it.
   */
  loadSpecContent?: (task: Task) => Promise<string | null>;
  /**
   * Build the detail's right-rail meta cards (cost & tokens, workspace, …)
   * for a task, or null when unavailable. Progressive enhancement like
   * ``loadSpecContent``: failures are swallowed.
   */
  loadMetaSections?: (task: Task) => Promise<UiMetaSection[] | null>;
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
  options: TaskStoreClientOptions = {},
): AutoCodeClient {
  const resolveLabels = typeof labels === 'function' ? labels : () => labels;
  const snapshot = (tasks: Task[]) => {
    const current = resolveLabels();
    return tasks.map((task) => mapTaskToUiTask(task, current));
  };
  return {
    listTasks: async () => snapshot(store.getState().tasks),
    getTask: async (id: string) => {
      const task = store.getState().tasks.find((candidate) => candidate.id === id);
      if (!task) throw new Error(`Task ${id} not found`);
      const detail = mapTaskToUiTaskDetail(task, resolveLabels());
      if (options.loadSpecContent) {
        try {
          detail.specContent = (await options.loadSpecContent(task)) ?? undefined;
        } catch (err) {
          // Spec body is progressive enhancement — the detail still renders,
          // but surface the failure so missing content stays diagnosable.
          console.warn('[autoCodeClient] Failed to load spec content:', err);
        }
      }
      if (options.loadMetaSections) {
        try {
          detail.metaSections =
            (await options.loadMetaSections(task)) ?? undefined;
        } catch (err) {
          // Same contract as the spec body: render without the rail.
          console.warn('[autoCodeClient] Failed to load meta sections:', err);
        }
      }
      return detail;
    },
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
