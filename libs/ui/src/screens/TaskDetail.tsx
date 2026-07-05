import type { TaskStatus, UiTaskDetail } from '../client/types';
import './TaskDetail.css';

const STATUS_LABELS: Record<TaskStatus, string> = {
  draft: 'Draft',
  running: 'Running',
  review: 'Review',
  done: 'Done',
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
}

/**
 * Presentational task/spec detail: header (id, title, status, badges),
 * a per-status progress breakdown, and the spec body. Data-agnostic — pair
 * with `useTask()` + an AutoCodeClient adapter. Mirrors the `.lazyweb`
 * task-detail layout.
 */
export function TaskDetail({
  task,
  loading = false,
  error = null,
  onBack,
  onRetry,
  statusLabels,
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
        <TaskDetailBody task={task} statusLabels={statusLabels} />
      )}
    </section>
  );
}

interface TaskDetailBodyProps {
  task: UiTaskDetail;
  statusLabels?: Partial<Record<TaskStatus, string>>;
}

function TaskDetailBody({ task, statusLabels }: Readonly<TaskDetailBodyProps>) {
  const statusLabel = statusLabels?.[task.status] ?? STATUS_LABELS[task.status];
  const breakdown = task.progressBreakdown;

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
            <span
              key={`${badge.tone ?? 'neutral'}:${badge.label}`}
              className={`ac-task-detail__badge ac-task-detail__badge--${badge.tone ?? 'neutral'}`}
            >
              {badge.label}
            </span>
          ))}
        </div>
      )}

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
