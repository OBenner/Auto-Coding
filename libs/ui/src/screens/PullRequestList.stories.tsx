import { useState } from 'react';
import type React from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { PullRequestList } from './PullRequestList';
import type { UiPullRequest } from '../client/types';

const CHECK_NAMES = ['lint', 'tsc', 'tests', 'i18n parity', 'bundle size'];

const checks = (...statuses: ('good' | 'bad' | 'warn' | 'run' | 'skip')[]) =>
  statuses.map((status, index) => ({ label: CHECK_NAMES[index], status }));

const PRS: UiPullRequest[] = [
  {
    id: 'pr#264',
    number: 264,
    title: 'refactor(shell): extract AppShell + sidebar primitives from monolithic layout',
    state: 'open',
    author: 'OM',
    headBranch: 'ac/spec-201',
    baseBranch: 'develop',
    additions: 482,
    deletions: 137,
    metaText: '14 files · opened 22 min ago',
    checks: checks('good', 'good', 'run', 'good', 'warn'),
    reviewers: [
      { initials: 'NK', status: 'good' },
      { initials: 'LP', status: 'warn' },
    ],
    badge: { label: 'Auto Code', tone: 'info' },
    timeLabel: '22m',
  },
  {
    id: 'pr#262',
    number: 262,
    title: 'fix(i18n): seal raw translation keys behind a screenshot guard',
    state: 'open',
    author: 'Auto Code',
    headBranch: 'ac/spec-199',
    baseBranch: 'develop',
    additions: 318,
    deletions: 94,
    metaText: '42 files · opened 1 h ago',
    checks: checks('good', 'good', 'good', 'good', 'good'),
    reviewers: [
      { initials: 'OM', status: 'good' },
      { initials: 'NK', status: 'good' },
    ],
    badge: { label: 'Ready to merge', tone: 'good' },
    timeLabel: '1h',
  },
  {
    id: 'pr#258',
    number: 258,
    title: 'feat(provider): diagnostics drawer with retest and safe fallback',
    state: 'conflict',
    author: 'Auto Code',
    headBranch: 'ac/spec-203',
    baseBranch: 'develop',
    additions: 112,
    deletions: 18,
    metaText: '6 files · opened 4 h ago',
    checks: checks('good', 'good', 'bad', 'good', 'skip'),
    reviewers: [{ initials: 'OM', status: 'warn' }],
    badge: { label: 'Conflict', tone: 'bad' },
    timeLabel: '4h',
  },
  {
    id: 'pr#253',
    number: 253,
    title: 'wip: provider auto-recover orchestration with exponential backoff',
    state: 'draft',
    author: 'NK',
    headBranch: 'nk/provider-auto-recover',
    baseBranch: 'develop',
    additions: 78,
    deletions: 12,
    metaText: '3 files · last activity 2 d ago',
    checks: checks('good', 'warn', 'skip', 'skip', 'skip'),
    badge: { label: 'Draft', tone: 'neutral' },
    timeLabel: '2d',
  },
  {
    id: 'pr#243',
    number: 243,
    title: 'refactor(settings): consolidate provider cards into a single component',
    state: 'merged',
    author: 'Auto Code',
    headBranch: 'ac/spec-196',
    baseBranch: 'develop',
    additions: 162,
    deletions: 218,
    metaText: '9 files · merged yesterday',
    checks: checks('good', 'good', 'good', 'good', 'good'),
    reviewers: [
      { initials: 'OM', status: 'good' },
      { initials: 'NK', status: 'good' },
    ],
    badge: { label: 'Merged', tone: 'neutral' },
    timeLabel: '1d',
  },
];

const meta = {
  title: 'Screens/PullRequestList',
  component: PullRequestList,
  parameters: { layout: 'fullscreen' },
  decorators: [
    (Story) => (
      <div style={{ height: '100vh' }}>
        <Story />
      </div>
    ),
  ],
  args: {
    loading: false,
    error: null,
    pullRequests: PRS,
    stats: [
      { value: '12', label: 'open PRs', sub: 'across 4 repos', tone: 'good' },
      { value: '3', label: 'need your review', sub: 'waiting > 24h', tone: 'warn' },
      { value: '2', label: 'merge conflicts', sub: 'vs base develop', tone: 'bad' },
      { value: '5', label: 'ready to merge', sub: 'all checks pass' },
      { value: '87%', label: 'median CI pass', sub: 'last 30 days' },
    ],
    searchPlaceholder: 'Search title, branch, author…',
    filters: [
      { id: 'all', label: 'All', count: 12 },
      { id: 'open', label: 'Open', count: 8 },
      { id: 'draft', label: 'Draft', count: 3 },
      { id: 'conflict', label: 'Conflicts', count: 2 },
    ],
    activeFilterId: 'all',
    onSelectPullRequest: () => {},
  },
} satisfies Meta<typeof PullRequestList>;

export default meta;
type Story = StoryObj<typeof meta>;

function InteractivePullRequestList(
  args: Readonly<React.ComponentProps<typeof PullRequestList>>,
) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  return (
    <PullRequestList
      {...args}
      searchValue={query}
      onSearchChange={setQuery}
      activeFilterId={filter}
      onSelectFilter={setFilter}
    />
  );
}

export const OpenPRs: Story = {
  render: (args) => <InteractivePullRequestList {...args} />,
};

export const NoToolbar: Story = {
  args: {
    stats: undefined,
    filters: undefined,
    onSelectPullRequest: undefined,
  },
};

export const Loading: Story = {
  args: { pullRequests: null, loading: true, stats: undefined, filters: undefined },
};

export const ErrorState: Story = {
  args: {
    pullRequests: null,
    error: new Error('GitHub is not connected'),
    stats: undefined,
    filters: undefined,
  },
};

export const Empty: Story = {
  args: { pullRequests: [], stats: undefined, filters: undefined },
};
