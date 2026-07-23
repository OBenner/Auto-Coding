import { useState } from 'react';
import type React from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { IssueList } from './IssueList';
import type { UiIssue } from '../client/types';

const ISSUES: UiIssue[] = [
  {
    id: 'issue#412',
    number: 412,
    title: 'QA fixer should accept screenshot evidence from any viewport',
    state: 'open',
    repo: 'obenner/auto-coding',
    metaText: 'opened 14m ago by nikitos · last activity 4m ago',
    labels: [
      { text: 'bug', tone: 'bug' },
      { text: 'area: qa-fixer', tone: 'area' },
      { text: 'priority: high', tone: 'feat' },
    ],
    assignees: [
      { initials: 'OM', name: 'om' },
      { initials: 'NK', name: 'nikitos' },
    ],
    commentsCount: 8,
  },
  {
    id: 'issue#411',
    number: 411,
    title: 'Add dark mode toggle to settings',
    state: 'open',
    repo: 'obenner/auto-coding',
    metaText: 'opened 2h ago by OM · linked to SPEC-201',
    labels: [
      { text: 'enhancement', tone: 'feat' },
      { text: 'area: frontend', tone: 'area' },
      { text: 'good first issue', tone: 'good-first' },
    ],
    assignees: [{ initials: 'OM', name: 'om' }],
    commentsCount: 3,
  },
  {
    id: 'issue#410',
    number: 410,
    title: 'Provider diagnostics drawer does not handle 502 from OpenRouter cleanly',
    state: 'open',
    repo: 'obenner/auto-coding',
    metaText: 'opened 4h ago by scout-agent · auto-filed from SPEC-203 recovery',
    labels: [
      { text: 'bug', tone: 'bug' },
      { text: 'area: providers', tone: 'area' },
      { text: 'needs repro', tone: 'help' },
    ],
    commentsCount: 0,
  },
  {
    id: 'issue#407',
    number: 407,
    title: String.raw`Document the new sidebar collapse behaviour (⌘\) in the keyboard cheatsheet`,
    state: 'open',
    repo: 'obenner/auto-coding',
    metaText: 'opened 2d ago by OM',
    labels: [
      { text: 'documentation', tone: 'docs' },
      { text: 'good first issue', tone: 'good-first' },
    ],
    commentsCount: 1,
  },
  {
    id: 'issue#403',
    number: 403,
    title: 'i18n parity script fails on Windows due to path separator',
    state: 'closed',
    repo: 'obenner/auto-coding',
    metaText: 'closed 3d ago by nikitos · fixed in #406',
    labels: [
      { text: 'bug', tone: 'bug' },
      { text: 'area: ci', tone: 'area' },
    ],
    assignees: [{ initials: 'NK', name: 'nikitos' }],
    commentsCount: 4,
  },
];

const meta = {
  title: 'Screens/IssueList',
  component: IssueList,
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
    issues: ISSUES,
    searchPlaceholder: 'Search title, body, author, label…',
    filters: [
      { id: 'open', label: 'Open', count: 38 },
      { id: 'closed', label: 'Closed', count: 214 },
      { id: 'all', label: 'All' },
    ],
    activeFilterId: 'open',
    onSelectIssue: () => {},
    metaSections: [
      {
        title: 'Connected repository',
        rows: [
          { label: 'Repository', value: 'obenner/auto-coding' },
          { label: 'Open issues', value: '38' },
          { label: 'Last synced', value: '4 minutes ago' },
        ],
      },
    ],
  },
} satisfies Meta<typeof IssueList>;

export default meta;
type Story = StoryObj<typeof meta>;

function InteractiveIssueList(
  args: Readonly<React.ComponentProps<typeof IssueList>>,
) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('open');
  return (
    <IssueList
      {...args}
      searchValue={query}
      onSearchChange={setQuery}
      activeFilterId={filter}
      onSelectFilter={setFilter}
    />
  );
}

export const OpenIssues: Story = {
  render: (args) => <InteractiveIssueList {...args} />,
};

export const NoRail: Story = {
  args: { metaSections: undefined, onSelectIssue: undefined },
};

export const Loading: Story = {
  args: { issues: null, loading: true, filters: undefined },
};

export const ErrorState: Story = {
  args: {
    issues: null,
    error: new Error('GitHub is not connected'),
    filters: undefined,
  },
};

export const Empty: Story = {
  args: { issues: [], filters: undefined, metaSections: undefined },
};
