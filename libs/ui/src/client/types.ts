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
  /**
   * Small chip rendered next to the id (e.g. the source system's raw status:
   * "Coder", "Merged"). Distinct from `badges`, which annotate outcomes.
   */
  statusChip?: UiTaskBadge;
  badges?: UiTaskBadge[];
  /** 0–100 progress, typically for running tasks. */
  progress?: number;
  /**
   * Short bottom-row facts (e.g. active agent/phase, elapsed time), rendered
   * with dot separators. Plain strings so adapters own the formatting.
   */
  meta?: readonly string[];
}

/** Subtask counts backing the detail progress breakdown. */
export interface UiTaskProgress {
  completed: number;
  inProgress: number;
  pending: number;
  failed: number;
  total: number;
}

/**
 * The detail view of a task/spec. Extends UiTask with the spec body and a
 * per-status progress breakdown; each adapter maps its richer model down to
 * this shape (desktop spec/task over IPC, web spec over REST).
 */
export interface UiTaskDetail extends UiTask {
  /** Rendered spec document (markdown / plain text), when available. */
  specContent?: string;
  /** Subtask counts by status, when a build plan exists. */
  progressBreakdown?: UiTaskProgress;
}

/** Input for creating a new task/spec from the shared UI. */
export interface CreateTaskInput {
  name: string;
  description: string;
}
