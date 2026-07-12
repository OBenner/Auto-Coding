import type { Meta, StoryObj } from '@storybook/react-vite';
import { TaskDetail } from './TaskDetail';

const meta = {
  title: 'Screens/TaskDetail',
  component: TaskDetail,
  parameters: { layout: 'fullscreen' },
  args: {
    loading: false,
    error: null,
    onBack: () => {},
    onRetry: () => {},
    task: {
      id: '004',
      title: 'Add user authentication',
      status: 'running',
      description: 'JWT access + refresh, bcrypt hashing, workspace bootstrap.',
      progress: 40,
      badges: [{ label: 'coder', tone: 'info' }],
      progressBreakdown: {
        completed: 2,
        inProgress: 1,
        pending: 2,
        failed: 0,
        total: 5,
      },
      specContent:
        '# 004 — Add user authentication\n\n## Goal\nEmail+password auth with JWT and refresh rotation.\n\n## Acceptance\n- POST /api/users/register issues a token\n- Passwords hashed with bcrypt',
    },
  },
} satisfies Meta<typeof TaskDetail>;

export default meta;
type Story = StoryObj<typeof meta>;

export const RunningTask: Story = {};

export const Loading: Story = {
  args: { task: null, loading: true },
};

export const ErrorState: Story = {
  args: { task: null, error: new Error('Task 004 not found') },
};
