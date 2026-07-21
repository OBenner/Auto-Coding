/**
 * Tests for the GitHubIssue → IssueList mapping helpers.
 */

import { describe, expect, it } from 'vitest';
import {
  filterIssues,
  labelToneOf,
  mapIssueToUi,
} from '../lib/github-issues-ui';
import type { GitHubIssue } from '../../shared/types';

function makeIssue(overrides: Partial<GitHubIssue> = {}): GitHubIssue {
  return {
    id: 1,
    number: 412,
    title: 'QA fixer should accept screenshot evidence',
    body: '',
    state: 'open',
    labels: [
      { id: 1, name: 'bug', color: 'ff0000' },
      { id: 2, name: 'area: qa-fixer', color: '888888' },
    ],
    assignees: [{ login: 'om' }, { login: 'nikitos' }],
    author: { login: 'nikitos' },
    createdAt: '2026-07-20T10:00:00Z',
    updatedAt: '2026-07-20T11:00:00Z',
    commentsCount: 8,
    url: 'https://api.github.com/x',
    htmlUrl: 'https://github.com/o/r/issues/412',
    repoFullName: 'obenner/auto-coding',
    ...overrides,
  } as GitHubIssue;
}

describe('labelToneOf', () => {
  it('maps common label families onto semantic tones', () => {
    expect(labelToneOf('bug')).toBe('bug');
    expect(labelToneOf('regression')).toBe('bug');
    expect(labelToneOf('documentation')).toBe('docs');
    expect(labelToneOf('good first issue')).toBe('good-first');
    expect(labelToneOf('needs repro')).toBe('help');
    expect(labelToneOf('discussion')).toBe('help');
    expect(labelToneOf('enhancement')).toBe('feat');
    expect(labelToneOf('priority: high')).toBe('feat');
    expect(labelToneOf('area: frontend')).toBe('area');
    expect(labelToneOf('anything-else')).toBe('area');
  });
});

describe('mapIssueToUi', () => {
  it('maps the row fields, labels, and assignee avatars', () => {
    const ui = mapIssueToUi(makeIssue());
    expect(ui).toEqual({
      id: 'issue#412',
      number: 412,
      title: 'QA fixer should accept screenshot evidence',
      state: 'open',
      repo: 'obenner/auto-coding',
      author: 'nikitos',
      labels: [
        { text: 'bug', tone: 'bug' },
        { text: 'area: qa-fixer', tone: 'area' },
      ],
      assignees: [
        { initials: 'OM', name: 'om' },
        { initials: 'NI', name: 'nikitos' },
      ],
      commentsCount: 8,
    });
  });

  it('maps closed state and omits empty labels/assignees', () => {
    const ui = mapIssueToUi(
      makeIssue({ state: 'closed', labels: [], assignees: [] }),
    );
    expect(ui.state).toBe('closed');
    expect(ui.labels).toBeUndefined();
    expect(ui.assignees).toBeUndefined();
  });
});

describe('filterIssues', () => {
  const issues = [
    mapIssueToUi(makeIssue()),
    mapIssueToUi(
      makeIssue({
        number: 411,
        title: 'Add dark mode toggle',
        labels: [{ id: 3, name: 'enhancement', color: '00f' }],
        assignees: [{ login: 'om' }],
      }),
    ),
  ];

  it('matches number, title, label, and assignee, case-insensitively', () => {
    expect(filterIssues(issues, '#412').map((issue) => issue.number)).toEqual([412]);
    expect(filterIssues(issues, 'DARK MODE').map((issue) => issue.number)).toEqual([411]);
    expect(filterIssues(issues, 'qa-fixer').map((issue) => issue.number)).toEqual([412]);
    expect(filterIssues(issues, 'zzz')).toEqual([]);
  });

  it('matches the issue author, as the search label promises', () => {
    const authored = [
      mapIssueToUi(makeIssue({ number: 500, author: { login: 'scout-agent' } })),
      mapIssueToUi(makeIssue({ number: 501, author: { login: 'om' } })),
    ];
    expect(filterIssues(authored, 'scout').map((issue) => issue.number)).toEqual([
      500,
    ]);
  });

  it('returns everything for a blank query', () => {
    expect(filterIssues(issues, '  ')).toHaveLength(2);
  });
});
