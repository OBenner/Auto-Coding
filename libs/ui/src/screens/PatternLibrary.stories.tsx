import { useState } from 'react';
import type React from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { PatternLibrary } from './PatternLibrary';
import type { UiPattern } from '../client/types';

const PATTERNS: UiPattern[] = [
  {
    id: 'p1',
    kind: 'pattern',
    title: 'Typed nav config from a string-literal union',
    lang: 'tsx',
    description: 'Derive the sidebar item ids from a union so a typo fails at compile time.',
    snippet: {
      code: "type View = 'kanban' | 'changelog';\nconst NAV: Record<View, string> = { … };",
    },
    tags: ['frontend', 'react', 'i18n', 'refactor'],
    footer: [
      { text: '3 reuses' },
      { text: 'conf 0.94' },
      { text: 'last used in SPEC-201 · 12m ago' },
    ],
  },
  {
    id: 'p2',
    kind: 'gotcha',
    title: 'i18n raw-key flash on lazy nav config',
    lang: 'tsx',
    description: 'Sidebar renders navigation:items.* before the bundle resolves at boot.',
    snippet: { code: 'useTranslation(ns); // resolves async — guard first paint' },
    tags: ['frontend', 'i18n', 'qa-gate'],
    footer: [
      { text: '2 past failures', tone: 'bad' },
      { text: 'conf 0.88' },
      { text: 'QA gate · screenshot guard required' },
    ],
  },
  {
    id: 'p3',
    kind: 'decision',
    code: 'D81',
    title: 'Prefer a single shared AppShell over per-page layouts',
    lang: 'arch',
    description: 'One AppShell primitive owns the sidebar + topbar slots; pages fill content only.',
    tags: ['architecture', 'shell', 'decided', '2026-04-02'],
    footer: [
      { text: 'cited by 5 specs' },
      { text: 'conf 1.00' },
      { text: 'locked — change requires retro' },
    ],
  },
  {
    id: 'p4',
    kind: 'rule',
    code: 'R03',
    title: 'All user-facing text uses translation keys',
    lang: 'policy',
    description: 'No hardcoded strings in JSX; every label goes through react-i18next.',
    snippet: { code: "t('navigation:items.kanban') // not 'Kanban'" },
    tags: ['policy', 'i18n', 'enforced'],
    footer: [{ text: 'applies to all frontend specs' }, { text: 'conf 1.00' }],
  },
  {
    id: 'p5',
    kind: 'pattern',
    title: 'Retry transient SDK errors with exponential backoff and jitter',
    lang: 'py',
    description: 'Wrap SDK calls; back off min(60, 2 ** attempt + random()) on 5xx.',
    snippet: { code: 'delay = min(60, 2 ** attempt + random())' },
    tags: ['backend', 'recovery', 'claude-sdk'],
    footer: [
      { text: '7 reuses' },
      { text: 'conf 0.96' },
      { text: 'last used in SPEC-203 · 8m ago' },
    ],
  },
  {
    id: 'p6',
    kind: 'pattern',
    title: 'Pilot one migration before bulk refactor',
    lang: 'process',
    description: 'Prove the contract on a single screen, then fan out via subagents.',
    tags: ['process', 'refactor', 'subagents'],
    footer: [
      { text: '3 reuses' },
      { text: 'conf 0.91' },
      { text: 'saved a full QA loop in SPEC-201', tone: 'good' },
    ],
  },
  {
    id: 'p7',
    kind: 'gotcha',
    title: 'Renaming a TS export without updating barrel files breaks watch-mode silently',
    lang: 'ts',
    tags: ['typescript', 'silent-fail', 'build'],
    footer: [{ text: '1 past failure', tone: 'bad' }, { text: 'conf 0.82' }],
  },
  {
    id: 'p8',
    kind: 'rule',
    code: 'R07',
    title: 'Branches stay local until the user explicitly pushes',
    lang: 'policy',
    tags: ['policy', 'git', 'safety'],
    footer: [{ text: 'applies to all specs' }, { text: 'conf 1.00' }],
  },
];

const meta = {
  title: 'Screens/PatternLibrary',
  component: PatternLibrary,
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
    patterns: PATTERNS,
    searchPlaceholder: 'Search by name, snippet, tag, language…',
    filters: [
      { id: 'all', label: 'All', count: 86 },
      { id: 'pattern', label: 'Patterns', count: 54 },
      { id: 'gotcha', label: 'Gotchas', count: 18 },
      { id: 'decision', label: 'Decisions', count: 11 },
      { id: 'rule', label: 'Rules', count: 14 },
    ],
    activeFilterId: 'all',
    onSelectPattern: () => {},
    metaSections: [
      {
        title: 'Stats',
        rows: [
          { label: 'Patterns', value: '54' },
          { label: 'Gotchas', value: '18' },
          { label: 'Decisions', value: '11' },
          { label: 'Rules', value: '14' },
          { label: 'Reuse hit', value: '74% this week' },
        ],
      },
      {
        title: 'Default context bundle',
        rows: [
          { label: 'Included', value: '12 patterns' },
          { label: 'Budget', value: '~8k tokens' },
        ],
      },
    ],
  },
} satisfies Meta<typeof PatternLibrary>;

export default meta;
type Story = StoryObj<typeof meta>;

function InteractivePatternLibrary(
  args: Readonly<React.ComponentProps<typeof PatternLibrary>>,
) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  return (
    <PatternLibrary
      {...args}
      searchValue={query}
      onSearchChange={setQuery}
      activeFilterId={filter}
      onSelectFilter={setFilter}
    />
  );
}

export const Library: Story = {
  render: (args) => <InteractivePatternLibrary {...args} />,
};

export const NoRail: Story = {
  args: { metaSections: undefined, onSelectPattern: undefined },
};

export const Loading: Story = {
  args: { patterns: null, loading: true, filters: undefined },
};

export const ErrorState: Story = {
  args: {
    patterns: null,
    error: new Error('Failed to load patterns'),
    filters: undefined,
  },
};

export const Empty: Story = {
  args: { patterns: [], filters: undefined, metaSections: undefined },
};
