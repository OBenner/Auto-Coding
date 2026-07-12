import type { Meta, StoryObj } from '@storybook/react-vite';
import { BoardSkeleton } from './BoardSkeleton';

const meta = {
  title: 'Screens/BoardSkeleton',
  component: BoardSkeleton,
  parameters: { layout: 'fullscreen' },
  args: { label: 'Loading tasks…' },
} satisfies Meta<typeof BoardSkeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Loading: Story = {};
