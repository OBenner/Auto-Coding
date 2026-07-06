import { Fragment } from 'react';
import type { KeyboardEvent } from 'react';
import type { TaskStatus, UiTask } from '../client/types';
import './KanbanBoard.css';

export interface KanbanColumn {
  status: TaskStatus;
  label: string;
}

export const DEFAULT_KANBAN_COLUMNS: KanbanColumn[] = [
  { status: 'draft', label: 'Draft' },
  { status: 'running', label: 'Running' },
  { status: 'review', label: 'Review' },
  { status: 'done', label: 'Done' },
];

export interface KanbanBoardProps {
  tasks: UiTask[];
  columns?: KanbanColumn[];
  onSelectTask?: (task: UiTask) => void;
}

/**
 * Presentational Kanban board: groups tasks into status columns and renders
 * cards. Data-agnostic — pair with `useTasks()` + an AutoCodeClient adapter.
 * Mirrors the `.lazyweb` desktop-kanban-board-v2 layout.
 */
export function KanbanBoard({
  tasks,
  columns = DEFAULT_KANBAN_COLUMNS,
  onSelectTask,
}: KanbanBoardProps) {
  return (
    <div className="ac-kanban">
      {columns.map((column) => {
        const columnTasks = tasks.filter((task) => task.status === column.status);
        return (
          <section
            key={column.status}
            className={`ac-kanban__column ac-kanban__column--${column.status}`}
          >
            <div className="ac-kanban__column-head">
              <h2 className="ac-kanban__column-title">{column.label}</h2>
              <span className="ac-kanban__count">{columnTasks.length}</span>
            </div>
            <div className="ac-kanban__column-body">
              {columnTasks.map((task) => (
                <KanbanCard key={task.id} task={task} onSelect={onSelectTask} />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

interface KanbanCardProps {
  task: UiTask;
  onSelect?: (task: UiTask) => void;
}

function KanbanCard({ task, onSelect }: KanbanCardProps) {
  const handleClick = () => onSelect?.(task);
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (onSelect && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      onSelect(task);
    }
  };

  return (
    <article
      className="ac-kanban__card"
      role={onSelect ? 'button' : undefined}
      tabIndex={onSelect ? 0 : undefined}
      onClick={onSelect ? handleClick : undefined}
      onKeyDown={onSelect ? handleKeyDown : undefined}
    >
      <div className="ac-kanban__card-top">
        <span className="ac-kanban__card-id">{task.id}</span>
        {task.statusChip != null && (
          <span
            className={`ac-kanban__badge ac-kanban__badge--${task.statusChip.tone ?? 'neutral'}`}
          >
            {task.statusChip.label}
          </span>
        )}
      </div>
      <h3 className="ac-kanban__card-title">{task.title}</h3>
      {task.description != null && (
        <p className="ac-kanban__card-desc">{task.description}</p>
      )}
      {task.progress != null && (
        <div className="ac-kanban__progress">
          <span style={{ width: `${Math.max(0, Math.min(100, task.progress))}%` }} />
        </div>
      )}
      {task.badges != null && task.badges.length > 0 && (
        <div className="ac-kanban__card-badges">
          {task.badges.map((badge) => (
            <span
              key={`${badge.tone ?? 'neutral'}:${badge.label}`}
              className={`ac-kanban__badge ac-kanban__badge--${badge.tone ?? 'neutral'}`}
            >
              {badge.label}
            </span>
          ))}
        </div>
      )}
      {task.meta != null && task.meta.length > 0 && (
        <div className="ac-kanban__card-meta">
          {task.meta.map((item, index) => (
            <Fragment key={`${index}:${item}`}>
              {index > 0 && <span className="ac-kanban__card-meta-sep" />}
              <span>{item}</span>
            </Fragment>
          ))}
        </div>
      )}
    </article>
  );
}
