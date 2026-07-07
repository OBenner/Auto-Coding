import { BoardToolbar } from './BoardToolbar';
import { KanbanBoard } from './KanbanBoard';
import type { KanbanColumn } from './KanbanBoard';
import { FILTER_IDS, useBoardFilter } from '../client/useBoardFilter';
import type { FilterId } from '../client/useBoardFilter';
import type { UiTask } from '../client/types';
import './BoardView.css';

/** View-switch ids; only 'board' is implemented today. */
const VIEW_IDS = ['board', 'table', 'timeline'] as const;
type ViewId = (typeof VIEW_IDS)[number];

/**
 * All display strings BoardView needs, already localized by the caller. Keeps
 * `libs/ui` framework-agnostic — the app maps its i18n into this shape (see
 * {@link buildBoardViewLabels}).
 */
export interface BoardViewLabels {
  searchPlaceholder: string;
  searchLabel: string;
  filtersLabel: string;
  viewsLabel: string;
  noMatches: string;
  matchCount: (count: number) => string;
  filters: Record<FilterId, string>;
  views: Record<ViewId, string>;
}

/** Minimal translate signature (i18next's `t` is assignable to it). */
export type Translate = (key: string, options?: Record<string, unknown>) => string;

/**
 * Build BoardViewLabels from a translate function and a key prefix, so both
 * pilots produce the labels identically (only the namespace prefix differs).
 */
export function buildBoardViewLabels(
  translate: Translate,
  prefix: string,
): BoardViewLabels {
  return {
    searchPlaceholder: translate(`${prefix}.searchPlaceholder`),
    searchLabel: translate(`${prefix}.searchLabel`),
    filtersLabel: translate(`${prefix}.filtersLabel`),
    viewsLabel: translate(`${prefix}.viewsLabel`),
    noMatches: translate(`${prefix}.noMatches`),
    matchCount: (count) => translate(`${prefix}.matchCount`, { count }),
    filters: {
      all: translate(`${prefix}.filters.all`),
      running: translate(`${prefix}.filters.running`),
      review: translate(`${prefix}.filters.review`),
    },
    views: {
      board: translate(`${prefix}.views.board`),
      table: translate(`${prefix}.views.table`),
      timeline: translate(`${prefix}.views.timeline`),
    },
  };
}

export interface BoardViewProps {
  tasks: UiTask[];
  columns?: KanbanColumn[];
  labels: BoardViewLabels;
  onSelectTask: (task: UiTask) => void;
  /** Heading for the genuinely-empty board (no tasks at all). */
  emptyTitle?: string;
  /** Sub-text under the empty heading. */
  emptyDescription?: string;
}

/**
 * The filterable Kanban board: BoardToolbar (search + filter chips + view
 * switch) over a live-narrowing KanbanBoard, with a polite status line for
 * the match count (WCAG 4.1.3). Both app pilots render this identically;
 * loading/error states stay with the caller.
 *
 * With zero tasks it shows a centered empty state (when emptyTitle is given)
 * instead of an empty toolbar over four blank columns.
 */
export function BoardView({
  tasks,
  columns,
  labels,
  onSelectTask,
  emptyTitle,
  emptyDescription,
}: Readonly<BoardViewProps>) {
  const { query, setQuery, filterId, setFilterId, filtering, visibleTasks } =
    useBoardFilter(tasks);

  if (tasks.length === 0 && emptyTitle != null) {
    return (
      <div className="ac-board-view__empty">
        <h2 className="ac-board-view__empty-title">{emptyTitle}</h2>
        {emptyDescription != null && (
          <p className="ac-board-view__empty-desc">{emptyDescription}</p>
        )}
      </div>
    );
  }

  let matchStatus = '';
  if (filtering) {
    matchStatus =
      visibleTasks.length === 0
        ? labels.noMatches
        : labels.matchCount(visibleTasks.length);
  }

  return (
    <>
      <BoardToolbar
        searchValue={query}
        searchPlaceholder={labels.searchPlaceholder}
        searchLabel={labels.searchLabel}
        onSearchChange={setQuery}
        filters={FILTER_IDS.map((id) => ({ id, label: labels.filters[id] }))}
        filtersLabel={labels.filtersLabel}
        activeFilterId={filterId}
        // BoardView owns FILTER_IDS, so every emitted id is a FilterId.
        onSelectFilter={(id) => setFilterId(id as FilterId)}
        views={VIEW_IDS.map((id) => ({
          id,
          label: labels.views[id],
          disabled: id !== 'board',
        }))}
        viewsLabel={labels.viewsLabel}
        activeViewId="board"
      />
      {/* Always mounted so screen readers announce narrowing (WCAG 4.1.3);
          <output> carries an implicit status role. */}
      <output className="ac-board-view__status">{matchStatus}</output>
      <KanbanBoard
        tasks={visibleTasks}
        columns={columns}
        onSelectTask={onSelectTask}
      />
    </>
  );
}
