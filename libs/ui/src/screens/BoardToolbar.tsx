import type { ChangeEvent } from 'react';
import { Kbd } from '../primitives/Kbd';
import './BoardToolbar.css';

export interface BoardToolbarFilter {
  id: string;
  label: string;
}

export interface BoardToolbarView {
  id: string;
  label: string;
  /** Rendered but not selectable (view not implemented yet). */
  disabled?: boolean;
}

export interface BoardToolbarProps {
  /** Controlled search value; the search box renders only with onSearchChange. */
  searchValue?: string;
  searchPlaceholder?: string;
  /** Accessible name for the search input; falls back to searchPlaceholder. */
  searchLabel?: string;
  /** Keyboard hint rendered inside the search box (e.g. "⌘K"). */
  searchShortcut?: string;
  onSearchChange?: (value: string) => void;
  /** Single-active filter chips. */
  filters?: BoardToolbarFilter[];
  /** Accessible name for the filter chip group. */
  filtersLabel?: string;
  activeFilterId?: string;
  onSelectFilter?: (id: string) => void;
  /** Segmented view switch (Board / Table / Timeline). */
  views?: BoardToolbarView[];
  /** Accessible name for the view switch group. */
  viewsLabel?: string;
  activeViewId?: string;
  onSelectView?: (id: string) => void;
}

/**
 * Presentational board toolbar: search box, filter chips, and the segmented
 * view switch. Mirrors the `.lazyweb` desktop-kanban-board-v2 toolbar; all
 * behavior (filtering, view routing) stays with the caller via callbacks.
 */
export function BoardToolbar({
  searchValue,
  searchPlaceholder,
  searchLabel,
  searchShortcut,
  onSearchChange,
  filters,
  filtersLabel,
  activeFilterId,
  onSelectFilter,
  views,
  viewsLabel,
  activeViewId,
  onSelectView,
}: Readonly<BoardToolbarProps>) {
  const handleSearch = (event: ChangeEvent<HTMLInputElement>) =>
    onSearchChange?.(event.target.value);

  return (
    <section className="ac-toolbar">
      {onSearchChange != null && (
        <div className="ac-toolbar__search">
          <input
            type="search"
            value={searchValue ?? ''}
            placeholder={searchPlaceholder}
            aria-label={searchLabel ?? searchPlaceholder}
            onChange={handleSearch}
          />
          {searchShortcut != null && <Kbd>{searchShortcut}</Kbd>}
        </div>
      )}
      {filters != null && filters.length > 0 && (
        <fieldset className="ac-toolbar__filters" aria-label={filtersLabel}>
          {filters.map((filter) => (
            <button
              key={filter.id}
              type="button"
              className={`ac-toolbar__chip${
                filter.id === activeFilterId ? ' ac-toolbar__chip--active' : ''
              }`}
              aria-pressed={filter.id === activeFilterId}
              onClick={() => onSelectFilter?.(filter.id)}
            >
              {filter.label}
            </button>
          ))}
        </fieldset>
      )}
      {views != null && views.length > 0 && (
        <fieldset className="ac-toolbar__views" aria-label={viewsLabel}>
          {views.map((view) => (
            <button
              key={view.id}
              type="button"
              disabled={view.disabled}
              className={`ac-toolbar__view${
                view.id === activeViewId ? ' ac-toolbar__view--on' : ''
              }`}
              aria-pressed={view.disabled ? undefined : view.id === activeViewId}
              onClick={() => onSelectView?.(view.id)}
            >
              {view.label}
            </button>
          ))}
        </fieldset>
      )}
    </section>
  );
}
