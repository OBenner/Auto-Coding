import { useState } from 'react';
import { Badge } from '../primitives/Badge';
import type {
  BadgeTone,
  TaskStatus,
  UiSubtask,
  UiSubtaskStatus,
  UiTaskDetail,
} from '../client/types';
import './TaskDetail.css';

const STATUS_LABELS: Record<TaskStatus, string> = {
  draft: 'Draft',
  running: 'Running',
  review: 'Review',
  done: 'Done',
};

const TAB_IDS = ['overview', 'subtasks', 'logs', 'files', 'timeline'] as const;
export type TaskDetailTabId = (typeof TAB_IDS)[number];

const TAB_LABELS: Record<TaskDetailTabId, string> = {
  overview: 'Overview',
  subtasks: 'Subtasks',
  logs: 'Logs',
  files: 'Files',
  timeline: 'Timeline',
};

const SUBTASK_STATUS_LABELS: Record<UiSubtaskStatus, string> = {
  pending: 'Pending',
  in_progress: 'Running',
  completed: 'Done',
  failed: 'Failed',
};

const SUBTASK_STATUS_TONES: Record<UiSubtaskStatus, BadgeTone> = {
  pending: 'neutral',
  in_progress: 'info',
  completed: 'good',
  failed: 'bad',
};

export interface TaskDetailProps {
  task: UiTaskDetail | null;
  loading?: boolean;
  error?: Error | null;
  /** Optional back affordance (e.g. return to the board). */
  onBack?: () => void;
  onRetry?: () => void;
  /** Localized status labels; falls back to English. */
  statusLabels?: Partial<Record<TaskStatus, string>>;
  /** Localized tab labels; falls back to English. */
  tabLabels?: Partial<Record<TaskDetailTabId, string>>;
  /** Localized subtask status labels; falls back to English. */
  subtaskStatusLabels?: Partial<Record<UiSubtaskStatus, string>>;
}

/**
 * Presentational task/spec detail mirroring the `.lazyweb` pipeline view:
 * header (id, title, status, badges), tab bar, a two-column body with the
 * overview/subtasks content on the left and meta cards (workspace, cost &
 * tokens, …) on the right rail. Logs/Files/Timeline tabs are rendered but
 * disabled until their data flows land. Data-agnostic — pair with
 * `useTask()` + an AutoCodeClient adapter.
 */
export function TaskDetail({
  task,
  loading = false,
  error = null,
  onBack,
  onRetry,
  statusLabels,
  tabLabels,
  subtaskStatusLabels,
}: Readonly<TaskDetailProps>) {
  return (
    <section className="ac-task-detail">
      {onBack != null && (
        <button type="button" className="ac-task-detail__back" onClick={onBack}>
          ← Back
        </button>
      )}

      {loading && <p className="ac-task-detail__state">Loading…</p>}

      {!loading && error != null && (
        <p className="ac-task-detail__state ac-task-detail__state--error" role="alert">
          {error.message}
          {onRetry != null && (
            <button
              type="button"
              className="ac-task-detail__retry"
              onClick={onRetry}
            >
              Retry
            </button>
          )}
        </p>
      )}

      {!loading && error == null && task == null && (
        <p className="ac-task-detail__state">No task selected.</p>
      )}

      {!loading && error == null && task != null && (
        <TaskDetailBody
          key={task.id}
          task={task}
          statusLabels={statusLabels}
          tabLabels={tabLabels}
          subtaskStatusLabels={subtaskStatusLabels}
        />
      )}
    </section>
  );
}

interface TaskDetailBodyProps {
  task: UiTaskDetail;
  statusLabels?: Partial<Record<TaskStatus, string>>;
  tabLabels?: Partial<Record<TaskDetailTabId, string>>;
  subtaskStatusLabels?: Partial<Record<UiSubtaskStatus, string>>;
}

function TaskDetailBody({
  task,
  statusLabels,
  tabLabels,
  subtaskStatusLabels,
}: Readonly<TaskDetailBodyProps>) {
  const [activeTab, setActiveTab] = useState<TaskDetailTabId>('overview');
  const statusLabel = statusLabels?.[task.status] ?? STATUS_LABELS[task.status];
  const subtasks = task.subtasks ?? [];
  const metaSections = task.metaSections ?? [];

  // Only tabs whose content exists are selectable; the rest are rendered
  // disabled so the pipeline chrome matches the mockup honestly.
  const enabled: Record<TaskDetailTabId, boolean> = {
    overview: true,
    subtasks: subtasks.length > 0,
    logs: false,
    files: false,
    timeline: false,
  };
  // A live update can disable the selected tab (e.g. subtasks emptied) —
  // fall back to Overview rather than rendering a dead panel.
  const currentTab = enabled[activeTab] ? activeTab : 'overview';
  const counts: Partial<Record<TaskDetailTabId, number>> = {
    subtasks: subtasks.length > 0 ? subtasks.length : undefined,
  };

  return (
    <>
      <header className="ac-task-detail__header">
        <div className="ac-task-detail__heading">
          <span className="ac-task-detail__id">{task.id}</span>
          <h1 className="ac-task-detail__title">{task.title}</h1>
        </div>
        <span
          className={`ac-task-detail__status ac-task-detail__status--${task.status}`}
        >
          {statusLabel}
        </span>
      </header>

      {task.badges != null && task.badges.length > 0 && (
        <div className="ac-task-detail__badges">
          {task.badges.map((badge) => (
            <Badge
              key={`${badge.tone ?? 'neutral'}:${badge.label}`}
              tone={badge.tone ?? 'neutral'}
              size="md"
            >
              {badge.label}
            </Badge>
          ))}
        </div>
      )}

      <nav className="ac-task-detail__tabs">
        {TAB_IDS.map((tab) => (
          <button
            key={tab}
            type="button"
            disabled={!enabled[tab]}
            className={`ac-task-detail__tab${
              tab === currentTab ? ' ac-task-detail__tab--on' : ''
            }`}
            aria-pressed={enabled[tab] ? tab === currentTab : undefined}
            onClick={() => setActiveTab(tab)}
          >
            {tabLabels?.[tab] ?? TAB_LABELS[tab]}
            {counts[tab] != null && (
              <span className="ac-task-detail__tab-count">{counts[tab]}</span>
            )}
          </button>
        ))}
      </nav>

      <div
        className={`ac-task-detail__body${
          metaSections.length > 0 ? '' : ' ac-task-detail__body--single'
        }`}
      >
        <div className="ac-task-detail__center">
          {currentTab === 'overview' && <OverviewTab task={task} />}
          {currentTab === 'subtasks' && (
            <SubtasksPanel
              subtasks={subtasks}
              statusLabels={subtaskStatusLabels}
            />
          )}
        </div>

        {metaSections.length > 0 && (
          <aside className="ac-task-detail__rail">
            {metaSections.map((section) => (
              <div key={section.title} className="ac-task-detail__card">
                <h3>{section.title}</h3>
                {section.rows.map((row) => (
                  <div key={row.label} className="ac-task-detail__kv">
                    <span>{row.label}</span>
                    <strong>{row.value}</strong>
                  </div>
                ))}
              </div>
            ))}
          </aside>
        )}
      </div>
    </>
  );
}

function OverviewTab({ task }: Readonly<{ task: UiTaskDetail }>) {
  const breakdown = task.progressBreakdown;
  return (
    <>
      {task.description != null && task.description !== '' && (
        <p className="ac-task-detail__desc">{task.description}</p>
      )}

      {breakdown != null && breakdown.total > 0 && (
        <div className="ac-task-detail__progress">
          <div className="ac-task-detail__progress-bar">
            <span
              style={{
                width: `${Math.round(
                  (breakdown.completed / breakdown.total) * 100,
                )}%`,
              }}
            />
          </div>
          <ul className="ac-task-detail__counts">
            <li>{breakdown.completed} done</li>
            <li>{breakdown.inProgress} running</li>
            <li>{breakdown.pending} pending</li>
            {breakdown.failed > 0 && (
              <li className="ac-task-detail__count--bad">
                {breakdown.failed} failed
              </li>
            )}
            <li className="ac-task-detail__count--total">
              of {breakdown.total}
            </li>
          </ul>
        </div>
      )}

      {task.specContent != null && task.specContent !== '' && (
        <pre className="ac-task-detail__spec">{task.specContent}</pre>
      )}
    </>
  );
}

function SubtasksPanel({
  subtasks,
  statusLabels,
}: Readonly<{
  subtasks: UiSubtask[];
  statusLabels?: Partial<Record<UiSubtaskStatus, string>>;
}>) {
  return (
    <article className="ac-task-detail__panel">
      {subtasks.map((subtask) => (
        <div key={subtask.id} className="ac-task-detail__subtask">
          <span
            className={`ac-task-detail__check ac-task-detail__check--${subtask.status}`}
          />
          <div>
            <h3>{subtask.title}</h3>
            {subtask.description != null && subtask.description !== '' && (
              <p>{subtask.description}</p>
            )}
          </div>
          <Badge tone={SUBTASK_STATUS_TONES[subtask.status]} size="md">
            {statusLabels?.[subtask.status] ??
              SUBTASK_STATUS_LABELS[subtask.status]}
          </Badge>
        </div>
      ))}
    </article>
  );
}
