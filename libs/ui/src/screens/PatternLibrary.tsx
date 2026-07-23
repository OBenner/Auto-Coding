import type { KeyboardEvent } from 'react';
import { Input } from '../primitives/Input';
import type {
  UiMetaSection,
  UiPattern,
  UiPatternKind,
} from '../client/types';
import './PatternLibrary.css';

const KIND_GLYPHS: Record<UiPatternKind, string> = {
  pattern: 'PAT',
  gotcha: '⚠',
  decision: 'D',
  rule: 'R',
};

const KIND_LABELS: Record<UiPatternKind, string> = {
  pattern: 'Pattern',
  gotcha: 'Gotcha',
  decision: 'Decision',
  rule: 'Rule',
};

export interface PatternLibraryFilter {
  id: string;
  label: string;
  count?: number;
}

export interface PatternLibraryStateLabels {
  loading?: string;
  retry?: string;
  empty?: string;
}

export interface PatternLibraryProps {
  patterns: UiPattern[] | null;
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  searchPlaceholder?: string;
  /** Accessible name for the search input. */
  searchLabel?: string;
  filters?: PatternLibraryFilter[];
  activeFilterId?: string;
  onSelectFilter?: (id: string) => void;
  /** Accessible name for the filter chip group. */
  filtersLabel?: string;
  onSelectPattern?: (pattern: UiPattern) => void;
  /** Localized loading/retry/empty state labels; falls back to English. */
  stateLabels?: PatternLibraryStateLabels;
  /** Localized pattern-kind glyph labels (accessible names). */
  kindLabels?: Partial<Record<UiPatternKind, string>>;
  /** Right-rail meta cards (stats, default bundle, …). */
  metaSections?: UiMetaSection[];
}

/**
 * Presentational patterns library mirroring the `.lazyweb` mockup: a
 * search + filter-chip toolbar over a two-column body — a 2-up grid of
 * pattern cards (kind glyph, title, lang chip, description, optional code
 * snippet, tags, footer facts) beside an optional right meta rail.
 * Data-agnostic — pair with an adapter that maps the app's pattern store
 * onto UiPattern[].
 */
export function PatternLibrary({
  patterns,
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
  onSelectPattern,
  stateLabels,
  kindLabels,
  metaSections,
}: Readonly<PatternLibraryProps>) {
  const hasToolbar =
    onSearchChange != null || (filters != null && filters.length > 0);
  const sections = metaSections ?? [];

  return (
    <section className="ac-patterns">
      {hasToolbar && (
        <div className="ac-patterns__toolbar">
          {onSearchChange != null && (
            <Input
              type="search"
              className="ac-patterns__search"
              value={searchValue ?? ''}
              placeholder={searchPlaceholder}
              aria-label={searchLabel ?? searchPlaceholder}
              onChange={(event) => onSearchChange(event.target.value)}
            />
          )}
          {filters != null && filters.length > 0 && (
            <fieldset className="ac-patterns__filters" aria-label={filtersLabel}>
              {filters.map((filter) => (
                <button
                  key={filter.id}
                  type="button"
                  className={`ac-patterns__chip${
                    filter.id === activeFilterId
                      ? ' ac-patterns__chip--active'
                      : ''
                  }`}
                  aria-pressed={filter.id === activeFilterId}
                  onClick={() => onSelectFilter?.(filter.id)}
                >
                  {filter.label}
                  {filter.count != null && (
                    <span className="ac-patterns__chip-count">
                      {filter.count}
                    </span>
                  )}
                </button>
              ))}
            </fieldset>
          )}
        </div>
      )}

      {loading && (
        <p className="ac-patterns__state">{stateLabels?.loading ?? 'Loading…'}</p>
      )}

      {!loading && error != null && (
        <p className="ac-patterns__state ac-patterns__state--error" role="alert">
          {error.message}
          {onRetry != null && (
            <button
              type="button"
              className="ac-patterns__retry"
              onClick={onRetry}
            >
              {stateLabels?.retry ?? 'Retry'}
            </button>
          )}
        </p>
      )}

      {!loading &&
        error == null &&
        (patterns == null || patterns.length === 0) && (
          <p className="ac-patterns__state">
            {stateLabels?.empty ?? 'No patterns yet.'}
          </p>
        )}

      {!loading && error == null && patterns != null && patterns.length > 0 && (
        <div
          className={`ac-patterns__body${
            sections.length > 0 ? '' : ' ac-patterns__body--no-rail'
          }`}
        >
          <div className="ac-patterns__grid">
            {patterns.map((pattern) => (
              <PatternCard
                key={pattern.id}
                pattern={pattern}
                onSelect={onSelectPattern}
                kindLabels={kindLabels}
              />
            ))}
          </div>

          {sections.length > 0 && (
            <aside className="ac-patterns__rail">
              {sections.map((section) => (
                <div key={section.title} className="ac-patterns__meta-card">
                  <h3>{section.title}</h3>
                  {section.rows.map((row) => (
                    <div key={row.label} className="ac-patterns__kv">
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

function PatternCard({
  pattern,
  onSelect,
  kindLabels,
}: Readonly<{
  pattern: UiPattern;
  onSelect?: (pattern: UiPattern) => void;
  kindLabels?: Partial<Record<UiPatternKind, string>>;
}>) {
  const interactive = onSelect != null;
  return (
    <article
      className={`ac-patterns__card${
        interactive ? ' ac-patterns__card--link' : ''
      }`}
      {...(interactive
        ? {
            role: 'button',
            tabIndex: 0,
            onClick: () => onSelect(pattern),
            onKeyDown: (event: KeyboardEvent) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                onSelect(pattern);
              }
            },
          }
        : {})}
    >
      <div className="ac-patterns__top">
        <span
          role="img"
          aria-label={kindLabels?.[pattern.kind] ?? KIND_LABELS[pattern.kind]}
          className={`ac-patterns__ico ac-patterns__ico--${pattern.kind}`}
        >
          {KIND_GLYPHS[pattern.kind]}
        </span>
        <h3 className="ac-patterns__title">
          {pattern.code != null && (
            <span className="ac-patterns__code">{pattern.code}</span>
          )}
          {pattern.title}
        </h3>
        {pattern.lang != null && (
          <span className="ac-patterns__lang">{pattern.lang}</span>
        )}
      </div>

      {pattern.description != null && pattern.description !== '' && (
        <p className="ac-patterns__desc">{pattern.description}</p>
      )}

      {pattern.snippet != null && (
        <pre className="ac-patterns__snippet">
          <code>{pattern.snippet.code}</code>
        </pre>
      )}

      {pattern.tags != null && pattern.tags.length > 0 && (
        <div className="ac-patterns__tags">
          {pattern.tags.map((tag) => (
            <span key={tag} className="ac-patterns__tag">
              {tag}
            </span>
          ))}
        </div>
      )}

      {pattern.footer != null && pattern.footer.length > 0 && (
        <div className="ac-patterns__footer">
          {pattern.footer.map((stat, index) => (
            <span
              key={`${index}-${stat.text}`}
              className={
                stat.tone != null && stat.tone !== 'default'
                  ? `ac-patterns__stat--${stat.tone}`
                  : undefined
              }
            >
              {stat.text}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
