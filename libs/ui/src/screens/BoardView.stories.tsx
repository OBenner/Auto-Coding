import type { Meta, StoryObj } from '@storybook/react-vite';
import { BoardView, buildBoardViewLabels } from './BoardView';
import { SAMPLE_TASKS } from './__fixtures__/sample-tasks';

const LABELS = buildBoardViewLabels((key, opts) => {
  const map: Record<string, string> = {
    'tb.searchPlaceholder': 'Search specs, files, agents…',
    'tb.searchLabel': 'Search specs',
    'tb.filtersLabel': 'Filter tasks',
    'tb.viewsLabel': 'Select view',
    'tb.noMatches': 'No tasks match your search or filter',
    'tb.filters.all': 'All projects',
    'tb.filters.running': 'Running',
    'tb.filters.review': 'Needs review',
    'tb.views.board': 'Board',
    'tb.views.table': 'Table',
    'tb.views.timeline': 'Timeline',
  };
  if (key === 'tb.matchCount') return `${opts?.count} matching tasks`;
  return map[key] ?? key;
}, 'tb');

const meta = {
  title: 'Screens/BoardView',
  component: BoardView,
  parameters: { layout: 'fullscreen' },
  args: {
    tasks: SAMPLE_TASKS,
    labels: LABELS,
    onSelectTask: () => {},
    emptyTitle: 'No tasks yet',
    emptyDescription: 'Create your first spec to see it on the board.',
  },
} satisfies Meta<typeof BoardView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const FilterableBoard: Story = {};

export const EmptyState: Story = {
  args: { tasks: [] },
};
