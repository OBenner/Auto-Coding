import type { Meta, StoryObj } from '@storybook/react-vite';
import { KanbanBoard } from './KanbanBoard';
import { SAMPLE_TASKS } from './__fixtures__/sample-tasks';

const meta = {
  title: 'Screens/KanbanBoard',
  component: KanbanBoard,
  parameters: { layout: 'fullscreen' },
  args: { tasks: SAMPLE_TASKS },
} satisfies Meta<typeof KanbanBoard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Board: Story = {};

export const EmptyColumns: Story = {
  args: { tasks: [] },
};
