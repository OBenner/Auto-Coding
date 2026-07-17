import type { Meta, StoryObj } from '@storybook/react-vite';
import { ChangelogView } from './ChangelogView';

const meta = {
  title: 'Screens/ChangelogView',
  component: ChangelogView,
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
    releases: [
      {
        id: 'v2.10.0#0',
        version: 'v2.10.0',
        name: 'Drafting',
        type: 'draft',
        dateLabel: 'Jun 8 (planned)',
        yearLabel: '2026',
        meta: ['7 PRs queued', '1 spec running'],
        sections: [
          {
            kind: 'features',
            title: 'Planned features',
            entries: [
              { text: 'New desktop shell: shared AppShell + collapsible sidebar' },
              { text: 'Dark theme with system preference detection and per-user override' },
              { text: 'Command palette (⌘K) with cross-cutting search' },
            ],
          },
        ],
      },
      {
        id: 'v2.9.0#1',
        version: 'v2.9.0',
        name: 'The sturdy-foundation release',
        type: 'minor',
        dateLabel: 'May 22',
        yearLabel: '2026',
        meta: ['Released May 22', '18 PRs · 2 contributors'],
        sections: [
          {
            kind: 'features',
            title: 'Features',
            entries: [
              {
                text: 'i18n parity enforced in CI, screenshot guard rejects raw keys',
                sha: 'a4f8e92',
              },
              {
                text: 'Onboarding readiness flow: stable widths, unclipped header',
                sha: 'f3c91d0',
              },
            ],
          },
          {
            kind: 'fixes',
            title: 'Fixes',
            entries: [
              {
                text: 'Sidebar no longer leaks raw navigation keys offline at boot',
                sha: 'e6df2b8',
              },
              {
                text: 'QA fixer accepts mobile screenshots from any viewport',
                sha: '7e88a01',
              },
            ],
          },
          {
            kind: 'docs',
            title: 'Docs',
            entries: [{ text: 'Token usage guidelines added to CONTRIBUTING.md' }],
          },
        ],
      },
      {
        id: 'v2.8.3#2',
        version: 'v2.8.3',
        type: 'patch',
        dateLabel: 'May 14',
        yearLabel: '2026',
        sections: [
          {
            kind: 'fixes',
            title: 'Fixes',
            entries: [
              { text: 'Windows path separator fix in the i18n parity script' },
            ],
          },
        ],
      },
      {
        id: 'v2.0.0#3',
        version: 'v2.0.0',
        type: 'major',
        dateLabel: 'Dec 4',
        yearLabel: '2025',
        sections: [
          {
            kind: 'breaking',
            title: 'Breaking changes',
            entries: [
              { text: 'Dropped legacy .auto-claude/config.yaml — use settings.json' },
            ],
          },
        ],
      },
    ],
    metaSections: [
      {
        title: 'Latest release',
        rows: [
          { label: 'Version', value: 'v2.9.0' },
          { label: 'Channel', value: 'stable' },
          { label: 'Released', value: 'May 22 · 4 days ago' },
        ],
      },
      {
        title: 'Suggested next',
        rows: [
          { label: 'Queued', value: '7 PRs for v2.10.0' },
          { label: 'Freeze', value: 'Jun 8' },
        ],
      },
    ],
  },
} satisfies Meta<typeof ChangelogView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ReleaseHistory: Story = {};

export const NoMetaRail: Story = {
  args: { metaSections: undefined },
};

export const Loading: Story = {
  args: { releases: null, loading: true },
};

export const ErrorState: Story = {
  args: { releases: null, error: new Error('Failed to read CHANGELOG.md') },
};

export const Empty: Story = {
  args: { releases: [], metaSections: undefined },
};
