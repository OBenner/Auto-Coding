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

export type UiSubtaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

/** One subtask row in the detail's pipeline view. */
export interface UiSubtask {
  id: string;
  title: string;
  description?: string;
  status: UiSubtaskStatus;
}

/** Key-value row inside a detail meta card. */
export interface UiMetaRow {
  label: string;
  value: string;
}

/** Right-rail meta card on the detail (e.g. "Cost & tokens"). */
export interface UiMetaSection {
  title: string;
  rows: UiMetaRow[];
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
  /** Subtask rows for the pipeline view, when the source exposes them. */
  subtasks?: UiSubtask[];
  /** Right-rail meta cards (workspace, cost & tokens, …), when available. */
  metaSections?: UiMetaSection[];
}

/** Input for creating a new task/spec from the shared UI. */
export interface CreateTaskInput {
  name: string;
  description: string;
}

/** Semver bump class of a release; drives the timeline dot + badge color. */
export type UiReleaseType = 'major' | 'minor' | 'patch' | 'draft';

/** Canonical section kinds; drive the section icon. Unknown kinds -> 'other'. */
export type UiReleaseSectionKind =
  | 'features'
  | 'fixes'
  | 'breaking'
  | 'docs'
  | 'other';

export interface UiReleaseEntry {
  text: string;
  /** Short commit sha shown after the entry, when known. */
  sha?: string;
}

export interface UiReleaseSection {
  kind: UiReleaseSectionKind;
  /** Display title, verbatim from the source (e.g. "Added", "Fixes"). */
  title: string;
  entries: UiReleaseEntry[];
}

/** One release in the changelog feed. Adapters own all label formatting. */
export interface UiRelease {
  /**
   * Unique key for React identity and selection. Version alone is not
   * enough — real CHANGELOG files repeat versions across format blocks.
   */
  id: string;
  /** Display version including any prefix (e.g. "v2.9.0", "Unreleased"). */
  version: string;
  /** Optional release name shown after the version. */
  name?: string;
  type: UiReleaseType;
  /** Short date label for the timeline rail (e.g. "May 22"). */
  dateLabel?: string;
  /** Year group header in the timeline rail (e.g. "2026"). */
  yearLabel?: string;
  /** Extra meta strings shown dot-separated in the release head. */
  meta?: readonly string[];
  sections: UiReleaseSection[];
}

/** Lifecycle tile of a PR row; drives the state glyph + colors. */
export type UiPullRequestState = 'open' | 'draft' | 'merged' | 'conflict';

export type UiPrCheckStatus = 'good' | 'bad' | 'warn' | 'run' | 'skip';

/** One CI check square; label doubles as tooltip and accessible name. */
export interface UiPrCheck {
  label: string;
  status: UiPrCheckStatus;
}

export interface UiPrReviewer {
  /** Short initials shown in the avatar circle (e.g. "OM"). */
  initials: string;
  name?: string;
  status?: 'good' | 'warn' | 'bad';
}

/** One pull request row. Adapters own all label formatting. */
export interface UiPullRequest {
  /** Unique key for React identity (e.g. "repo#264"). */
  id: string;
  number: number;
  title: string;
  state: UiPullRequestState;
  author?: string;
  headBranch?: string;
  baseBranch?: string;
  additions?: number;
  deletions?: number;
  /** Pre-localized trailing meta (e.g. "14 files · opened 22 min ago"). */
  metaText?: string;
  checks?: UiPrCheck[];
  reviewers?: UiPrReviewer[];
  badge?: UiTaskBadge;
  /** Right-column relative time (e.g. "22m"). */
  timeLabel?: string;
}

/** Summary tile above the PR toolbar. */
export interface UiPrStat {
  value: string;
  label: string;
  sub?: string;
  tone?: 'good' | 'warn' | 'bad';
}

/** Lifecycle of an issue row; drives the circular state pill. */
export type UiIssueState = 'open' | 'closed' | 'draft';

/** Semantic tone of a label pill; drives the pill colors. */
export type UiIssueLabelTone =
  | 'bug'
  | 'feat'
  | 'docs'
  | 'good-first'
  | 'help'
  | 'area';

export interface UiIssueLabel {
  text: string;
  tone: UiIssueLabelTone;
}

export interface UiIssueAssignee {
  /** Short initials shown in the avatar circle (e.g. "OM"). */
  initials: string;
  name?: string;
}

/** One issue row. Adapters own all label formatting. */
export interface UiIssue {
  /** Unique key for React identity (e.g. "issue#412"). */
  id: string;
  number: number;
  title: string;
  state: UiIssueState;
  /** Mono repo slug shown first in the meta line (e.g. "o/auto-coding"). */
  repo?: string;
  /** Pre-localized meta text (e.g. "opened 14m ago by nikitos"). */
  metaText?: string;
  labels?: UiIssueLabel[];
  assignees?: UiIssueAssignee[];
  commentsCount?: number;
}
