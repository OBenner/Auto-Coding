export type TaskStatus = 'draft' | 'running' | 'review' | 'done';

export type BadgeTone = 'good' | 'info' | 'warn' | 'bad' | 'neutral';

export interface UiTaskBadge {
  label: string;
  tone?: BadgeTone;
}

/**
 * The lowest-common task shape the Kanban board renders. Each app maps its own
 * model (desktop spec/task over IPC, web task over REST) into this shape via its
 * AutoCodeClient adapter, so the board stays transport- and source-agnostic.
 */
export interface UiTask {
  id: string;
  title: string;
  status: TaskStatus;
  description?: string;
  badges?: UiTaskBadge[];
  /** 0–100 progress, typically for running tasks. */
  progress?: number;
}
