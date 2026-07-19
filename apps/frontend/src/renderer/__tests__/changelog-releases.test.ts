/**
 * Tests for the CHANGELOG.md → UiRelease[] parser feeding ChangelogView.
 */

import { describe, expect, it } from 'vitest';
import {
  parseChangelogMarkdown,
  releaseTypeOf,
  sectionKindFromTitle,
  stripInlineMarkdown,
} from '../lib/changelog-releases';

const KEEP_A_CHANGELOG = `# Changelog

All notable changes to this project.

## [Unreleased]

### Added
- Command palette with cross-cutting search

## [2.9.0] - 2026-05-22

### Added
- i18n parity enforced in CI (a4f8e92)
- Onboarding readiness flow

### Fixed
- Sidebar no longer leaks raw keys (e6df2b8)

### Documentation
- Token guidelines in CONTRIBUTING.md

## [2.8.3] - 2026-05-14

### Fixed
- Windows path separator fix

## [2.0.0] - 2025-12-04

### Breaking Changes
- Dropped legacy config.yaml
`;

describe('parseChangelogMarkdown', () => {
  const releases = parseChangelogMarkdown(KEEP_A_CHANGELOG, 'en-US');

  it('parses every release with entries, newest first', () => {
    expect(releases.map((release) => release.version)).toEqual([
      'Unreleased',
      '2.9.0',
      '2.8.3',
      '2.0.0',
    ]);
  });

  it('classifies release types against the previous release', () => {
    expect(releases.map((release) => release.type)).toEqual([
      'draft', // Unreleased
      'minor', // 2.9.0 vs 2.8.3
      'minor', // 2.8.3 vs 2.0.0 — the minor version moved
      'major', // 2.0.0 by its own shape (x.0.0), no earlier release
    ]);
  });

  it('maps section titles onto canonical kinds, keeping titles verbatim', () => {
    const v290 = releases[1];
    expect(v290.sections.map((section) => [section.kind, section.title])).toEqual([
      ['features', 'Added'],
      ['fixes', 'Fixed'],
      ['docs', 'Documentation'],
    ]);
  });

  it('extracts trailing short shas from entries', () => {
    const added = releases[1].sections[0];
    expect(added.entries[0]).toEqual({
      text: 'i18n parity enforced in CI',
      sha: 'a4f8e92',
    });
    expect(added.entries[1]).toEqual({
      text: 'Onboarding readiness flow',
      sha: undefined,
    });
  });

  it('formats calendar dates in UTC regardless of host timezone', () => {
    const v290 = releases[1];
    expect(v290.dateLabel).toBe('May 22');
    expect(v290.yearLabel).toBe('2026');
    expect(releases[0].dateLabel).toBeUndefined();
    // A Jan 1 release must stay in its own year even west of UTC.
    const newYear = parseChangelogMarkdown(
      '## [3.0.0] - 2026-01-01\n- entry\n',
      'en-US',
    );
    expect(newYear[0].yearLabel).toBe('2026');
    expect(newYear[0].dateLabel).toBe('Jan 1');
  });

  it('treats non-date heading suffixes as release names, never dates', () => {
    const named = parseChangelogMarkdown(
      [
        '## 2.7.5 - Security & Platform Improvements',
        '- hardened the thing',
        '## v2.10.0 - Jun 8 (planned)',
        '- big feature',
      ].join('\n'),
      'en-US',
    );
    expect(named[0].name).toBe('Security & Platform Improvements');
    expect(named[0].dateLabel).toBeUndefined();
    expect(named[0].yearLabel).toBeUndefined();
    // "Jun 8" must not Date-parse into a bogus 2001 year group.
    expect(named[1].name).toBe('Jun 8 (planned)');
    expect(named[1].yearLabel).toBeUndefined();
  });

  it('assigns position-qualified unique ids even for duplicate versions', () => {
    const duplicated = parseChangelogMarkdown(
      [
        '## [2.7.5] - 2026-01-27',
        '- from the keep-a-changelog block',
        '## 2.7.5 - Security & Platform Improvements',
        '- from the generator block',
      ].join('\n'),
      'en-US',
    );
    expect(duplicated.map((release) => release.version)).toEqual([
      '2.7.5',
      '2.7.5',
    ]);
    const ids = duplicated.map((release) => release.id);
    expect(new Set(ids).size).toBe(2);
  });

  it('classifies duplicate versions against the next distinct version', () => {
    const duplicated = parseChangelogMarkdown(
      [
        '## [3.0.0] - 2026-03-01',
        '- keep-a-changelog block',
        '## 3.0.0 - The big one',
        '- generator block',
        '## [2.9.0] - 2026-02-01',
        '- previous minor',
      ].join('\n'),
      'en-US',
    );
    // Both 3.0.0 blocks compare against 2.9.0 — not against each other.
    expect(duplicated.map((release) => release.type)).toEqual([
      'major',
      'major',
      'minor',
    ]);
  });

  it('rejects impossible calendar dates instead of rolling them forward', () => {
    const impossible = parseChangelogMarkdown(
      '## [1.0.1] - 2026-02-31\n- entry\n',
      'en-US',
    );
    expect(impossible[0].dateLabel).toBeUndefined();
    expect(impossible[0].yearLabel).toBeUndefined();
  });

  it('parses loose heading variants and entries without section headings', () => {
    const loose = parseChangelogMarkdown(
      `## v1.2.0 (2026-01-05)\n- did a thing\n- did another (deadbeef)\n`,
      'en-US',
    );
    expect(loose).toHaveLength(1);
    expect(loose[0].version).toBe('v1.2.0');
    expect(loose[0].dateLabel).toBe('Jan 5');
    expect(loose[0].sections).toEqual([
      {
        kind: 'other',
        title: '',
        entries: [
          { text: 'did a thing', sha: undefined },
          { text: 'did another', sha: 'deadbeef' },
        ],
      },
    ]);
  });

  it('strips inline markdown from entry texts', () => {
    const rich = parseChangelogMarkdown(
      '## [1.1.0] - 2026-02-02\n- **Bold** fix for [the docs](https://x.test) via `npm ci`\n',
      'en-US',
    );
    expect(rich[0].sections[0].entries[0].text).toBe(
      'Bold fix for the docs via npm ci',
    );
  });

  it('drops releases without entries and survives malformed input', () => {
    expect(parseChangelogMarkdown('')).toEqual([]);
    expect(parseChangelogMarkdown('## [1.0.0] - 2026-01-01\n\nno bullets')).toEqual([]);
    expect(parseChangelogMarkdown('just some prose\n- floating bullet')).toEqual([]);
  });
});

describe('releaseTypeOf', () => {
  it('compares against the previous release when available', () => {
    expect(releaseTypeOf('2.9.0', '2.8.3')).toBe('minor');
    expect(releaseTypeOf('3.0.0', '2.9.0')).toBe('major');
    expect(releaseTypeOf('2.8.3', '2.8.2')).toBe('patch');
  });

  it('falls back to the version shape without a comparison point', () => {
    expect(releaseTypeOf('2.0.0')).toBe('major');
    expect(releaseTypeOf('2.9.0')).toBe('minor');
    expect(releaseTypeOf('2.8.3')).toBe('patch');
  });

  it('handles drafts and unparseable versions', () => {
    expect(releaseTypeOf('Unreleased')).toBe('draft');
    expect(releaseTypeOf('next')).toBe('patch');
  });
});

describe('sectionKindFromTitle', () => {
  it('maps common titles and defaults to other', () => {
    expect(sectionKindFromTitle('Added')).toBe('features');
    expect(sectionKindFromTitle('Features')).toBe('features');
    expect(sectionKindFromTitle('Fixed')).toBe('fixes');
    expect(sectionKindFromTitle('Bug Fixes')).toBe('fixes');
    expect(sectionKindFromTitle('Breaking Changes')).toBe('breaking');
    expect(sectionKindFromTitle('Docs')).toBe('docs');
    expect(sectionKindFromTitle('Security')).toBe('other');
  });
});

describe('stripInlineMarkdown', () => {
  it('unwraps links, emphasis, and code spans', () => {
    expect(stripInlineMarkdown('[label](https://x.test)')).toBe('label');
    expect(stripInlineMarkdown('**bold** and _em_ and `code`')).toBe(
      'bold and em and code',
    );
    expect(stripInlineMarkdown('plain text stays')).toBe('plain text stays');
  });
});
