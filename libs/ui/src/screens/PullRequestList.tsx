import type { KeyboardEvent } from 'react';
import { Badge } from '../primitives/Badge';
import { Input } from '../primitives/Input';
import type {
  UiPrCheckStatus,
  UiPrStat,
  UiPullRequest,
  UiPullRequestState,
} from '../client/types';
import './PullRequestList.css';

const STATE_GLYPHS: Record<UiPullRequestState, string> = {
  open: '↑',
  draft: '○',
  merged: '●',
  conflict: '⤫',
};

const CHECK_GLYPHS: Record<UiPrCheckStatus, string> = {
  good: '✓',
  bad: '✕',
  warn: '!',
  run: '↻',
  skip: '·',
};

export interface PullRequestFilter {
  id: string;
  label: string;
  count?: number;
}

export interface PullRequestListStateLabels {
  loading?: string;
  retry?: string;
  empty?: string;
}

export interface PullRequestListProps {
  pullRequests: UiPullRequest[] | null;
  /** Summary tiles above the toolbar (open PRs, conflicts, …). */
  stats?: UiPrStat[];
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  /** Accessible name for the search input. */
  searchLabel?: string;
  filters?: PullRequestFilter[];
  activeFilterId?: string;
  onSelectFilter?: (id: string) => void;
  /** Accessible name for the filter chip group. */
  filtersLabel?: string;
  onSelectPullRequest?: (pullRequest: UiPullRequest) => void;
  /** Localized loading/retry/empty state labels; falls back to English. */
  stateLabels?: PullRequestListStateLabels;
}

/**
 * Presentational GitHub PR list mirroring the `.lazyweb` mockup: summary
 * stat tiles, a search + filter-chip toolbar, and full-width PR rows with
 * state tile, branch/diff meta, CI check squares, reviewer avatars, and a
 * status badge column. Data-agnostic — pair with an adapter that maps the
 * app's PR source onto UiPullRequest[].
 */
export function PullRequestList({
  pullRequests,
  stats,
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
  onSelectPullRequest,
  stateLabels,
}: Readonly<PullRequestListProps>) {
  const hasToolbar =
    onSearchChange != null || (filters != null && filters.length > 0);

  return (
    <section className="ac-prs">
      {stats != null && stats.length > 0 && (
        <div className="ac-prs__summary">
          {stats.map((stat) => (
            <div key={stat.label} className="ac-prs__stat">
              <strong
                className={
                  stat.tone != null ? `ac-prs__stat-num--${stat.tone}` : undefined
                }
              >
                {stat.value}
              </strong>
              <span>{stat.label}</span>
              {stat.sub != null && (
                <span className="ac-prs__stat-sub">{stat.sub}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {hasToolbar && (
        <div className="ac-prs__toolbar">
          {onSearchChange != null && (
            <Input
              type="search"
              className="ac-prs__search"
              value={searchValue ?? ''}
              placeholder={searchPlaceholder}
              aria-label={searchLabel ?? searchPlaceholder}
              onChange={(event) => onSearchChange(event.target.value)}
            />
          )}
          {filters != null && filters.length > 0 && (
            <fieldset className="ac-prs__filters" aria-label={filtersLabel}>
              {filters.map((filter) => (
                <button
                  key={filter.id}
                  type="button"
                  className={`ac-prs__chip${
                    filter.id === activeFilterId ? ' ac-prs__chip--active' : ''
                  }`}
                  aria-pressed={filter.id === activeFilterId}
                  onClick={() => onSelectFilter?.(filter.id)}
                >
                  {filter.label}
                  {filter.count != null && (
                    <span className="ac-prs__chip-count">{filter.count}</span>
                  )}
                </button>
              ))}
            </fieldset>
          )}
        </div>
      )}

      {loading && (
        <p className="ac-prs__state">{stateLabels?.loading ?? 'Loading…'}</p>
      )}

      {!loading && error != null && (
        <p className="ac-prs__state ac-prs__state--error" role="alert">
          {error.message}
          {onRetry != null && (
            <button type="button" className="ac-prs__retry" onClick={onRetry}>
              {stateLabels?.retry ?? 'Retry'}
            </button>
          )}
        </p>
      )}

      {!loading &&
        error == null &&
        (pullRequests == null || pullRequests.length === 0) && (
          <p className="ac-prs__state">
            {stateLabels?.empty ?? 'No pull requests.'}
          </p>
        )}

      {!loading && error == null && pullRequests != null && pullRequests.length > 0 && (
        <div className="ac-prs__list">
          {pullRequests.map((pullRequest) => (
            <PullRequestRow
              key={pullRequest.id}
              pullRequest={pullRequest}
              onSelect={onSelectPullRequest}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function PullRequestRow({
  pullRequest,
  onSelect,
}: Readonly<{
  pullRequest: UiPullRequest;
  onSelect?: (pullRequest: UiPullRequest) => void;
}>) {
  const interactive = onSelect != null;
  return (
    <article
      className={`ac-prs__row${interactive ? ' ac-prs__row--link' : ''}`}
      {...(interactive
        ? {
            role: 'button',
            tabIndex: 0,
            onClick: () => onSelect(pullRequest),
            onKeyDown: (event: KeyboardEvent) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onSelect(pullRequest);
              }
            },
          }
        : {})}
    >
      <span
        aria-hidden="true"
        className={`ac-prs__tile ac-prs__tile--${pullRequest.state}`}
      >
        {STATE_GLYPHS[pullRequest.state]}
      </span>

      <div className="ac-prs__main">
        <h3 className="ac-prs__title">
          <span className="ac-prs__num">#{pullRequest.number}</span>
          {pullRequest.title}
        </h3>
        <div className="ac-prs__meta">
          {pullRequest.author != null && <strong>{pullRequest.author}</strong>}
          {pullRequest.headBranch != null && (
            <>
              <code className="ac-prs__branch">{pullRequest.headBranch}</code>
              {pullRequest.baseBranch != null && (
                <>
                  →
                  <code className="ac-prs__branch">{pullRequest.baseBranch}</code>
                </>
              )}
            </>
          )}
          {(pullRequest.additions != null || pullRequest.deletions != null) && (
            <span className="ac-prs__diff">
              {pullRequest.additions != null && (
                <span className="ac-prs__plus">+{pullRequest.additions}</span>
              )}{' '}
              {pullRequest.deletions != null && (
                <span className="ac-prs__minus">−{pullRequest.deletions}</span>
              )}
            </span>
          )}
          {pullRequest.metaText != null && <span>{pullRequest.metaText}</span>}
        </div>
      </div>

      {pullRequest.checks != null && pullRequest.checks.length > 0 && (
        <div className="ac-prs__checks">
          {pullRequest.checks.map((check) => (
            <span
              key={check.label}
              className={`ac-prs__check ac-prs__check--${check.status}`}
              title={check.label}
              aria-label={check.label}
            >
              {CHECK_GLYPHS[check.status]}
            </span>
          ))}
        </div>
      )}

      {pullRequest.reviewers != null && pullRequest.reviewers.length > 0 && (
        <div className="ac-prs__reviews">
          {pullRequest.reviewers.map((reviewer) => (
            <span
              key={reviewer.initials}
              className="ac-prs__avatar"
              title={reviewer.name ?? reviewer.initials}
            >
              {reviewer.initials}
              {reviewer.status != null && (
                <span
                  aria-hidden="true"
                  className={`ac-prs__ind ac-prs__ind--${reviewer.status}`}
                />
              )}
            </span>
          ))}
        </div>
      )}

      <div className="ac-prs__right">
        {pullRequest.badge != null && (
          <Badge tone={pullRequest.badge.tone ?? 'neutral'} size="sm">
            {pullRequest.badge.label}
          </Badge>
        )}
        {pullRequest.timeLabel != null && (
          <span className="ac-prs__time">{pullRequest.timeLabel}</span>
        )}
      </div>
    </article>
  );
}
