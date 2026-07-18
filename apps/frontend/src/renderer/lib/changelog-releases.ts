/**
 * Parses a CHANGELOG.md body into the shared UiRelease[] shape for the
 * ChangelogView screen. Pure and defensive: the file is user-editable and
 * format drift is expected, so unrecognized lines are ignored rather than
 * thrown on. Handles keep-a-changelog (`## [1.2.3] - 2026-05-22`) plus the
 * loose `## v1.2.3 (2026-05-22)` and name-suffixed
 * `## 1.2.3 - Some Release Name` variants this project's generator emits.
 */

import type {
  UiRelease,
  UiReleaseSection,
  UiReleaseSectionKind,
  UiReleaseType,
} from '@auto-code/ui';

/**
 * `## [token] …` — the token is validated separately with VERSION_SHAPE so
 * the line regex stays free of overlapping quantifiers (linear-time).
 */
const RELEASE_HEADING = /^##\s+\[?(?<version>[^\][\s]+)\]?(?<rest>.*)$/i;

/** `Unreleased` or a semver-ish `v?MAJOR.MINOR…` token. */
const VERSION_SHAPE = /^(?:unreleased$|v?\d+\.\d+)/i;

const SECTION_HEADING = /^###\s+(?<title>\S.*)$/;

const ENTRY_LINE = /^[-*]\s+(?<text>\S.*)$/;

/** Trailing short-sha reference: "… fix the thing (a4f8e92)". */
const TRAILING_SHA = /\((?<sha>[0-9a-f]{7,40})\)$/i;

/** Calendar dates only — anything else is a release name, not a date. */
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

const SECTION_KINDS: ReadonlyArray<[RegExp, UiReleaseSectionKind]> = [
  [/break/i, 'breaking'],
  [/^(added|features?|new)/i, 'features'],
  [/^(fixed|fixes|bug ?fixes)/i, 'fixes'],
  [/^(docs|documentation)/i, 'docs'],
];

export function sectionKindFromTitle(title: string): UiReleaseSectionKind {
  for (const [pattern, kind] of SECTION_KINDS) {
    if (pattern.test(title)) return kind;
  }
  return 'other';
}

/**
 * Drop inline markdown so entries render as plain text: links keep their
 * label, emphasis/backtick markers are stripped.
 */
export function stripInlineMarkdown(text: string): string {
  return text
    .replace(/!?\[([^\][]*)\]\(([^()]*)\)/g, '$1')
    .replace(/\*\*([^*]*)\*\*/g, '$1')
    .replace(/__([^_]*)__/g, '$1')
    .replace(/\*([^*]*)\*/g, '$1')
    .replace(/_([^_]*)_/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .trim();
}

interface HeadingSuffix {
  dateRaw?: string;
  name?: string;
}

/**
 * Interpret the text after the version: an ISO calendar date becomes the
 * release date; anything else non-empty is the release name, verbatim.
 */
function parseHeadingSuffix(rest: string): HeadingSuffix {
  let text = rest.trim();
  // Version-link tail from generators: `[1.2.3](https://…/compare/…)`.
  text = text.replace(/^\((?:https?:\/\/)[^)]*\)\s*/, '');
  // Leading `-` / `–` / `—` separator.
  text = text.replace(/^[-–—]\s*/, '');
  // Fully parenthesized suffix: `(2026-01-05)`.
  const wrapped = /^\(([^()]*)\)$/.exec(text);
  if (wrapped != null) text = wrapped[1].trim();
  if (text === '') return {};
  if (ISO_DATE.test(text)) return { dateRaw: text };
  return { name: stripInlineMarkdown(text) };
}

interface RawRelease {
  version: string;
  name?: string;
  dateRaw?: string;
  sections: UiReleaseSection[];
}

function parseSemver(version: string): [number, number, number] | null {
  const match = /^v?(\d+)\.(\d+)(?:\.(\d+))?/.exec(version);
  if (match == null) return null;
  return [Number(match[1]), Number(match[2]), Number(match[3] ?? 0)];
}

/**
 * Classify a release against the one released before it (next in the
 * newest-first file order). Falls back to the version's own shape when
 * there is nothing to compare against.
 */
export function releaseTypeOf(version: string, previous?: string): UiReleaseType {
  if (/unreleased/i.test(version)) return 'draft';
  const own = parseSemver(version);
  if (own == null) return 'patch';
  const prev = previous != null ? parseSemver(previous) : null;
  if (prev != null) {
    if (own[0] !== prev[0]) return 'major';
    if (own[1] !== prev[1]) return 'minor';
    return 'patch';
  }
  if (own[1] === 0 && own[2] === 0) return 'major';
  if (own[2] === 0) return 'minor';
  return 'patch';
}

interface DateLabels {
  dateLabel?: string;
  yearLabel?: string;
}

/**
 * Format an ISO calendar date in UTC — changelog dates are calendar dates,
 * so local-timezone formatting would shift them a day west of UTC.
 */
function dateLabelsOf(dateRaw: string | undefined, locale?: string): DateLabels {
  const match = dateRaw != null ? ISO_DATE.exec(dateRaw) : null;
  if (match == null) return {};
  const parsed = new Date(dateRaw as string);
  if (
    Number.isNaN(parsed.getTime()) ||
    // Date() rolls impossible dates forward (2026-02-31 -> Mar 3) — reject.
    parsed.getUTCFullYear() !== Number(match[1]) ||
    parsed.getUTCMonth() + 1 !== Number(match[2]) ||
    parsed.getUTCDate() !== Number(match[3])
  ) {
    return {};
  }
  return {
    dateLabel: parsed.toLocaleDateString(locale, {
      month: 'short',
      day: 'numeric',
      timeZone: 'UTC',
    }),
    yearLabel: String(parsed.getUTCFullYear()),
  };
}

export function parseChangelogMarkdown(
  content: string,
  locale?: string,
): UiRelease[] {
  const raw: RawRelease[] = [];
  let release: RawRelease | null = null;
  let section: UiReleaseSection | null = null;

  for (const line of content.split(/\r?\n/)) {
    const releaseMatch = RELEASE_HEADING.exec(line);
    if (
      releaseMatch?.groups != null &&
      VERSION_SHAPE.test(releaseMatch.groups.version)
    ) {
      release = {
        version: releaseMatch.groups.version,
        ...parseHeadingSuffix(releaseMatch.groups.rest),
        sections: [],
      };
      section = null;
      raw.push(release);
      continue;
    }
    if (release == null) continue;

    const sectionMatch = SECTION_HEADING.exec(line);
    if (sectionMatch?.groups != null) {
      const title = stripInlineMarkdown(sectionMatch.groups.title);
      section = { kind: sectionKindFromTitle(title), title, entries: [] };
      release.sections.push(section);
      continue;
    }

    const entryMatch = ENTRY_LINE.exec(line.trim());
    if (entryMatch?.groups != null) {
      // Entries before any `###` heading land in an untitled default section.
      if (section == null) {
        section = { kind: 'other', title: '', entries: [] };
        release.sections.push(section);
      }
      const entryText = entryMatch.groups.text.trimEnd();
      const shaMatch = TRAILING_SHA.exec(entryText);
      section.entries.push({
        text: stripInlineMarkdown(entryText.replace(TRAILING_SHA, '')),
        sha: shaMatch?.groups?.sha,
      });
    }
  }

  const withEntries = raw.filter((item) =>
    item.sections.some((s) => s.entries.length > 0),
  );
  return withEntries.map((item, index) => ({
    // CHANGELOG files can repeat a version (e.g. a keep-a-changelog block
    // and a generator block for the same release) — qualify by position.
    id: `${item.version}#${index}`,
    version: item.version,
    name: item.name,
    // Compare against the next semantically different version so duplicate
    // blocks of one release don't misclassify each other as patches.
    type: releaseTypeOf(
      item.version,
      withEntries.slice(index + 1).find((r) => r.version !== item.version)
        ?.version,
    ),
    ...dateLabelsOf(item.dateRaw, locale),
    sections: item.sections.filter((s) => s.entries.length > 0),
  }));
}
