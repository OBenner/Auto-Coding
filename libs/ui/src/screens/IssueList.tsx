import type { KeyboardEvent } from 'react';
import { Input } from '../primitives/Input';
import type {
  UiIssue,
  UiIssueState,
  UiMetaSection,
} from '../client/types';
import './IssueList.css';

const STATE_GLYPHS: Record<UiIssueState, string> = {
  open: '○',
  closed: '●',
  draft: '◌',
};

const STATE_LABELS: Record<UiIssueState, string> = {
  open: 'Open',
  closed: 'Closed',
  draft: 'Draft',
};

export interface IssueListFilter {
  id: string;
  label: string;
  count?: number;
}

export interface IssueListStateLabels {
  loading?: string;
  retry?: string;
  empty?: string;
}

export interface IssueListProps {
  issues: UiIssue[] | null;
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  /** Accessible name for the search input. */
  searchLabel?: string;
  filters?: IssueListFilter[];
  activeFilterId?: string;
  onSelectFilter?: (id: string) => void;
  /** Accessible name for the filter chip group. */
  filtersLabel?: string;
  onSelectIssue?: (issue: UiIssue) => void;
  /** Localized loading/retry/empty state labels; falls back to English. */
  stateLabels?: IssueListStateLabels;
  /** Localized issue-state pill labels (accessible names). */
  issueStateLabels?: Partial<Record<UiIssueState, string>>;
  /** Accessible name for the per-row comment count. */
  commentsLabel?: string;
  /** Right-rail meta cards (connected repo, sync status, …). */
  metaSections?: UiMetaSection[];
}

/**
 * Presentational GitHub issue list mirroring the `.lazyweb` mockup: a
 * search + filter-chip toolbar over a two-column body — issue rows
 * (circular state pill, repo slug meta, label pills, assignee stack,
 * comment count) beside an optional right meta rail. Data-agnostic —
 * pair with an adapter that maps the app's issue source onto UiIssue[].
 */
export function IssueList({
  issues,
  loading = false,
  error = null,
  onRetry,
  searchValue,
  onSearchChange,
  searchPlaceholder,
  searchLabel,
  filters,
  activeFilterId,
  onSelectFilter,
  filtersLabel,
  onSelectIssue,
  stateLabels,
  issueStateLabels,
  commentsLabel,
  metaSections,
}: Readonly<IssueListProps>) {
  const hasToolbar =
    onSearchChange != null || (filters != null && filters.length > 0);
  const sections = metaSections ?? [];

  return (
    <section className="ac-issues">
      {hasToolbar && (
        <div className="ac-issues__toolbar">
          {onSearchChange != null && (
            <Input
              type="search"
              className="ac-issues__search"
              value={searchValue ?? ''}
              placeholder={searchPlaceholder}
              aria-label={searchLabel ?? searchPlaceholder}
              onChange={(event) => onSearchChange(event.target.value)}
            />
          )}
          {filters != null && filters.length > 0 && (
            <fieldset className="ac-issues__filters" aria-label={filtersLabel}>
              {filters.map((filter) => (
                <button
                  key={filter.id}
                  type="button"
                  className={`ac-issues__chip${
                    filter.id === activeFilterId ? ' ac-issues__chip--active' : ''
                  }`}
                  aria-pressed={filter.id === activeFilterId}
                  onClick={() => onSelectFilter?.(filter.id)}
                >
                  {filter.label}
                  {filter.count != null && (
                    <span className="ac-issues__chip-count">{filter.count}</span>
                  )}
                </button>
              ))}
            </fieldset>
          )}
        </div>
      )}

      {loading && (
        <p className="ac-issues__state">{stateLabels?.loading ?? 'Loading…'}</p>
      )}

      {!loading && error != null && (
        <p className="ac-issues__state ac-issues__state--error" role="alert">
          {error.message}
          {onRetry != null && (
            <button type="button" className="ac-issues__retry" onClick={onRetry}>
              {stateLabels?.retry ?? 'Retry'}
            </button>
          )}
        </p>
      )}

      {!loading && error == null && (issues == null || issues.length === 0) && (
        <p className="ac-issues__state">{stateLabels?.empty ?? 'No issues.'}</p>
      )}

      {!loading && error == null && issues != null && issues.length > 0 && (
        <div
          className={`ac-issues__body${
            sections.length > 0 ? '' : ' ac-issues__body--no-rail'
          }`}
        >
          <div className="ac-issues__list">
            {issues.map((issue) => (
              <IssueRow
                key={issue.id}
                issue={issue}
                onSelect={onSelectIssue}
                issueStateLabels={issueStateLabels}
                commentsLabel={commentsLabel}
              />
            ))}
          </div>

          {sections.length > 0 && (
            <aside className="ac-issues__rail">
              {sections.map((section) => (
                <div key={section.title} className="ac-issues__card">
                  <h3>{section.title}</h3>
                  {section.rows.map((row) => (
                    <div key={row.label} className="ac-issues__kv">
                      <span>{row.label}</span>
                      <strong>{row.value}</strong>
                    </div>
                  ))}
                </div>
              ))}
            </aside>
          )}
        </div>
      )}
    </section>
  );
}

function IssueRow({
  issue,
  onSelect,
  issueStateLabels,
  commentsLabel,
}: Readonly<{
  issue: UiIssue;
  onSelect?: (issue: UiIssue) => void;
  issueStateLabels?: Partial<Record<UiIssueState, string>>;
  commentsLabel?: string;
}>) {
  const interactive = onSelect != null;
  return (
    <article
      className={`ac-issues__row${interactive ? ' ac-issues__row--link' : ''}`}
      {...(interactive
        ? {
            role: 'button',
            tabIndex: 0,
            onClick: () => onSelect(issue),
            onKeyDown: (event: KeyboardEvent) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onSelect(issue);
              }
            },
          }
        : {})}
    >
      <span
        role="img"
        aria-label={issueStateLabels?.[issue.state] ?? STATE_LABELS[issue.state]}
        className={`ac-issues__pill ac-issues__pill--${issue.state}`}
      >
        {STATE_GLYPHS[issue.state]}
      </span>

      <div className="ac-issues__main">
        <h3 className="ac-issues__title">
          <span className="ac-issues__num">#{issue.number}</span>
          {issue.title}
        </h3>
        <div className="ac-issues__meta">
          {issue.repo != null && (
            <code className="ac-issues__repo">{issue.repo}</code>
          )}
          {issue.metaText != null && <span>{issue.metaText}</span>}
        </div>
        {issue.labels != null && issue.labels.length > 0 && (
          <div className="ac-issues__labels">
            {issue.labels.map((label) => (
              <span
                key={label.text}
                className={`ac-issues__label ac-issues__label--${label.tone}`}
              >
                {label.text}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="ac-issues__right">
        {issue.assignees != null && issue.assignees.length > 0 && (
          <div className="ac-issues__assignees">
            {issue.assignees.map((assignee, index) => (
              <span
                key={assignee.name ?? `${assignee.initials}#${index}`}
                className="ac-issues__avatar"
                title={assignee.name ?? assignee.initials}
              >
                {assignee.initials}
              </span>
            ))}
          </div>
        )}
        {issue.commentsCount != null && (
          <span
            className="ac-issues__comments"
            aria-label={
              commentsLabel != null
                ? `${issue.commentsCount} ${commentsLabel}`
                : undefined
            }
          >
            💬 {issue.commentsCount}
          </span>
        )}
      </div>
    </article>
  );
}
