import { useRef, useState } from 'react';
import { Badge } from '../primitives/Badge';
import type {
  BadgeTone,
  UiMetaSection,
  UiRelease,
  UiReleaseSectionKind,
  UiReleaseType,
} from '../client/types';
import './ChangelogView.css';

const TYPE_LABELS: Record<UiReleaseType, string> = {
  major: 'Major',
  minor: 'Minor',
  patch: 'Patch',
  draft: 'Draft',
};

const TYPE_TONES: Record<UiReleaseType, BadgeTone> = {
  major: 'info',
  minor: 'good',
  patch: 'warn',
  draft: 'neutral',
};

const SECTION_GLYPHS: Record<UiReleaseSectionKind, string> = {
  features: '+',
  fixes: '!',
  breaking: '⚠',
  docs: 'd',
  other: '·',
};

export interface ChangelogViewProps {
  releases: UiRelease[] | null;
  loading?: boolean;
  error?: Error | null;
  onRetry?: () => void;
  /** Localized release-type badge labels; falls back to English. */
  typeLabels?: Partial<Record<UiReleaseType, string>>;
  /** Right-rail meta cards (latest release, cadence, …), when available. */
  metaSections?: UiMetaSection[];
}

/**
 * Presentational changelog browser mirroring the `.lazyweb` mockup: a
 * timeline rail (releases grouped by year, semver-type dots) next to a
 * scrollable feed of release articles, plus an optional right meta rail.
 * Data-agnostic — pair with an adapter that parses the project's
 * CHANGELOG.md (or a release API) into UiRelease[].
 */
export function ChangelogView({
  releases,
  loading = false,
  error = null,
  onRetry,
  typeLabels,
  metaSections,
}: Readonly<ChangelogViewProps>) {
  return (
    <section className="ac-changelog">
      {loading && <p className="ac-changelog__state">Loading…</p>}

      {!loading && error != null && (
        <p className="ac-changelog__state ac-changelog__state--error" role="alert">
          {error.message}
          {onRetry != null && (
            <button
              type="button"
              className="ac-changelog__retry"
              onClick={onRetry}
            >
              Retry
            </button>
          )}
        </p>
      )}

      {!loading && error == null && (releases == null || releases.length === 0) && (
        <p className="ac-changelog__state">No releases yet.</p>
      )}

      {!loading && error == null && releases != null && releases.length > 0 && (
        <ChangelogBody
          releases={releases}
          typeLabels={typeLabels}
          metaSections={metaSections}
        />
      )}
    </section>
  );
}

interface ChangelogBodyProps {
  releases: UiRelease[];
  typeLabels?: Partial<Record<UiReleaseType, string>>;
  metaSections?: UiMetaSection[];
}

interface YearGroup {
  year: string;
  releases: UiRelease[];
}

/** Group consecutive releases by year label, preserving feed order. */
function groupByYear(releases: UiRelease[]): YearGroup[] {
  const groups: YearGroup[] = [];
  for (const release of releases) {
    const year = release.yearLabel ?? '';
    const last = groups.at(-1);
    if (last?.year === year) {
      last.releases.push(release);
    } else {
      groups.push({ year, releases: [release] });
    }
  }
  return groups;
}

function ChangelogBody({
  releases,
  typeLabels,
  metaSections,
}: Readonly<ChangelogBodyProps>) {
  const [selected, setSelected] = useState(releases[0].id);
  const articleRefs = useRef(new Map<string, HTMLElement>());
  const groups = groupByYear(releases);
  const sections = metaSections ?? [];

  const open = (id: string) => {
    setSelected(id);
    articleRefs.current
      .get(id)
      ?.scrollIntoView({ block: 'start', behavior: 'smooth' });
  };

  return (
    <div
      className={`ac-changelog__body${
        sections.length > 0 ? '' : ' ac-changelog__body--no-rail'
      }`}
    >
      <nav className="ac-changelog__timeline">
        {groups.map((group) => (
          <div key={group.year || 'undated'} className="ac-changelog__year">
            {group.year !== '' && (
              <h3 className="ac-changelog__year-h">{group.year}</h3>
            )}
            {group.releases.map((release) => (
              <button
                key={release.id}
                type="button"
                className={`ac-changelog__rel-row${
                  release.id === selected ? ' ac-changelog__rel-row--on' : ''
                }`}
                aria-current={release.id === selected ? 'true' : undefined}
                onClick={() => open(release.id)}
              >
                <span
                  className={`ac-changelog__dot ac-changelog__dot--${release.type}`}
                />
                <span className="ac-changelog__rel-text">
                  <span className="ac-changelog__rel-ver">{release.version}</span>
                  {release.dateLabel != null && (
                    <span className="ac-changelog__rel-date">
                      {release.dateLabel}
                    </span>
                  )}
                </span>
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div className="ac-changelog__feed">
        {releases.map((release) => (
          <article
            key={release.id}
            ref={(node) => {
              if (node != null) {
                articleRefs.current.set(release.id, node);
              } else {
                articleRefs.current.delete(release.id);
              }
            }}
            className="ac-changelog__release"
          >
            <header className="ac-changelog__release-head">
              <h2 className="ac-changelog__release-title">
                <span className="ac-changelog__release-ver">
                  {release.version}
                </span>
                {release.name}
              </h2>
              <div className="ac-changelog__release-meta">
                <Badge tone={TYPE_TONES[release.type]} size="sm">
                  {typeLabels?.[release.type] ?? TYPE_LABELS[release.type]}
                </Badge>
                {(release.meta ?? []).map((item) => (
                  <span key={item} className="ac-changelog__meta-item">
                    {item}
                  </span>
                ))}
              </div>
            </header>

            {release.sections.map((section) => (
              <div
                key={`${section.kind}:${section.title}`}
                className="ac-changelog__section"
              >
                <h3 className="ac-changelog__section-h">
                  <span
                    aria-hidden="true"
                    className={`ac-changelog__ico ac-changelog__ico--${section.kind}`}
                  >
                    {SECTION_GLYPHS[section.kind]}
                  </span>
                  {section.title}
                </h3>
                <ul className="ac-changelog__entries">
                  {section.entries.map((entry, entryIndex) => (
                    <li key={`${entryIndex}-${entry.text}`}>
                      {entry.text}
                      {entry.sha != null && (
                        <code className="ac-changelog__sha">{entry.sha}</code>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </article>
        ))}
      </div>

      {sections.length > 0 && (
        <aside className="ac-changelog__rail">
          {sections.map((section) => (
            <div key={section.title} className="ac-changelog__card">
              <h3>{section.title}</h3>
              {section.rows.map((row) => (
                <div key={row.label} className="ac-changelog__kv">
                  <span>{row.label}</span>
                  <strong>{row.value}</strong>
                </div>
              ))}
            </div>
          ))}
        </aside>
      )}
    </div>
  );
}
