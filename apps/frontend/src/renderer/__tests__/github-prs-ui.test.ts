/**
 * Tests for the PRData → PullRequestList mapping helpers.
 */

import { describe, expect, it } from 'vitest';
import {
  computePrStatValues,
  filterPullRequests,
  initialsOf,
  mapPRToUi,
  relativeAge,
} from '../lib/github-prs-ui';
import type { PRData } from '../../preload/api/modules/github-api';

const NOW = new Date('2026-07-19T12:00:00Z');

function makePR(overrides: Partial<PRData> = {}): PRData {
  return {
    number: 264,
    title: 'refactor(shell): extract AppShell',
    body: '',
    state: 'OPEN',
    author: { login: 'auto-code' },
    headRefName: 'ac/spec-201',
    baseRefName: 'develop',
    additions: 482,
    deletions: 137,
    changedFiles: 14,
    assignees: [{ login: 'om' }],
    files: [],
    createdAt: '2026-07-19T11:38:00Z',
    updatedAt: '2026-07-19T11:38:00Z',
    htmlUrl: 'https://github.com/o/r/pull/264',
    ...overrides,
  };
}

describe('initialsOf', () => {
  it('takes two segment initials or the first two letters', () => {
    expect(initialsOf('auto-code')).toBe('AC');
    expect(initialsOf('renovate_bot')).toBe('RB');
    expect(initialsOf('om')).toBe('OM');
    expect(initialsOf('x')).toBe('X');
  });
});

describe('relativeAge', () => {
  it('renders minute, hour, and day buckets', () => {
    expect(relativeAge('2026-07-19T11:59:40Z', NOW)).toBe('<1m');
    expect(relativeAge('2026-07-19T11:38:00Z', NOW)).toBe('22m');
    expect(relativeAge('2026-07-19T08:00:00Z', NOW)).toBe('4h');
    expect(relativeAge('2026-07-17T12:00:00Z', NOW)).toBe('2d');
  });

  it('returns an empty string for unparseable input', () => {
    expect(relativeAge('not a date', NOW)).toBe('');
  });
});

describe('mapPRToUi', () => {
  it('maps the row fields and assignee avatars', () => {
    const ui = mapPRToUi(makePR(), NOW);
    expect(ui).toEqual({
      id: 'pr#264',
      number: 264,
      title: 'refactor(shell): extract AppShell',
      state: 'open',
      author: 'auto-code',
      headBranch: 'ac/spec-201',
      baseBranch: 'develop',
      additions: 482,
      deletions: 137,
      reviewers: [{ initials: 'OM', name: 'om' }],
      timeLabel: '22m',
    });
  });

  it('omits reviewers when there are no assignees', () => {
    const ui = mapPRToUi(makePR({ assignees: [] }), NOW);
    expect(ui.reviewers).toBeUndefined();
  });
});

describe('computePrStatValues', () => {
  it('counts PRs, distinct authors, and summed line changes', () => {
    const values = computePrStatValues([
      makePR(),
      makePR({ number: 262, author: { login: 'om' }, additions: 18, deletions: 2 }),
      makePR({ number: 258, additions: 0, deletions: 0 }),
    ]);
    expect(values).toEqual({
      open: 3,
      authors: 2,
      additions: 500,
      deletions: 139,
    });
  });
});

describe('filterPullRequests', () => {
  const prs = [
    mapPRToUi(makePR(), NOW),
    mapPRToUi(makePR({ number: 262, title: 'fix(i18n): seal raw keys', author: { login: 'om' } }), NOW),
  ];

  it('matches number, title, author, and branch, case-insensitively', () => {
    expect(filterPullRequests(prs, '#264').map((pr) => pr.number)).toEqual([264]);
    expect(filterPullRequests(prs, 'I18N').map((pr) => pr.number)).toEqual([262]);
    expect(filterPullRequests(prs, 'spec-201')).toHaveLength(2);
    expect(filterPullRequests(prs, 'nothing-here')).toEqual([]);
  });

  it('returns everything for a blank query', () => {
    expect(filterPullRequests(prs, '  ')).toHaveLength(2);
  });
});
