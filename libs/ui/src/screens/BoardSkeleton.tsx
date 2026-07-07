import './BoardSkeleton.css';

export interface BoardSkeletonProps {
  /** Number of placeholder columns (defaults to 4, matching the board). */
  columns?: number;
  /** Accessible loading label (announced to screen readers). */
  label?: string;
}

const CARDS_PER_COLUMN = [2, 3, 1, 2];

/**
 * Shimmer placeholder shown while the board's tasks load, mirroring the
 * KanbanBoard column/card layout so the transition to real data doesn't
 * shift the page. Presentational — pair with `useTasks().loading`.
 */
export function BoardSkeleton({ columns = 4, label }: Readonly<BoardSkeletonProps>) {
  return (
    <div
      className="ac-board-skeleton"
      role="status"
      aria-busy="true"
      aria-label={label}
    >
      {Array.from({ length: columns }, (_, columnIndex) => (
        <div key={columnIndex} className="ac-board-skeleton__column">
          <div className="ac-board-skeleton__head" />
          <div className="ac-board-skeleton__body">
            {Array.from(
              { length: CARDS_PER_COLUMN[columnIndex % CARDS_PER_COLUMN.length] },
              (_, cardIndex) => (
                <div key={cardIndex} className="ac-board-skeleton__card" />
              ),
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
