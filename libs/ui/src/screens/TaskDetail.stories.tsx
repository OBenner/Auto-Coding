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
      badges: [
        { label: 'Coder', tone: 'info' },
        { label: 'On track', tone: 'good' },
        { label: 'Worktree: ac/spec-004', tone: 'neutral' },
      ],
      progressBreakdown: {
        completed: 2,
        inProgress: 1,
        pending: 3,
        failed: 1,
        total: 7,
      },
      specContent:
        '# 004 — Add user authentication\n\n## Goal\nEmail+password auth with JWT and refresh rotation.\n\n## Acceptance\n- POST /api/users/register issues a token\n- Passwords hashed with bcrypt',
      subtasks: [
        {
          id: 'st-1',
          title: 'Scaffold auth module + routes',
          description: 'users router, auth middleware, config plumbing',
          status: 'completed',
        },
        {
          id: 'st-2',
          title: 'Password hashing with bcrypt',
          status: 'completed',
        },
        {
          id: 'st-3',
          title: 'JWT access + refresh token issuing',
          description: 'rotation on refresh, revocation list',
          status: 'in_progress',
        },
        {
          id: 'st-4',
          title: 'Login/logout endpoints',
          status: 'pending',
        },
        {
          id: 'st-5',
          title: 'Session persistence across restarts',
          status: 'pending',
        },
        {
          id: 'st-6',
          title: 'Rate-limit login attempts',
          status: 'pending',
        },
        {
          id: 'st-7',
          title: 'Legacy session migration',
          description: 'blocked: legacy store schema mismatch',
          status: 'failed',
        },
      ],
      metaSections: [
        {
          title: 'Workspace',
          rows: [
            { label: 'Branch', value: 'ac/spec-004' },
            { label: 'Base', value: 'develop' },
            { label: 'Worktree', value: '.worktrees/spec-004' },
          ],
        },
        {
          title: 'Cost & tokens',
          rows: [
            { label: 'Cost', value: '$4.87' },
            { label: 'Input', value: '112k' },
            { label: 'Output', value: '28k' },
            { label: 'Sessions', value: '9' },
          ],
        },
        {
          title: 'Next checkpoint',
          rows: [
            { label: 'Gate', value: 'QA review after subtask 4' },
            { label: 'Mode', value: 'Full autonomous' },
          ],
        },
      ],
    },
  },
} satisfies Meta<typeof TaskDetail>;

export default meta;
type Story = StoryObj<typeof meta>;

export const RunningTask: Story = {};

export const OverviewOnly: Story = {
  args: {
    task: {
      id: '002',
      title: 'Fix board drag-and-drop',
      status: 'review',
      description: 'Cards drop on the wrong column when the board scrolls.',
      progress: 100,
      badges: [{ label: 'QA', tone: 'warn' }],
      specContent: '# 002 — Fix board drag-and-drop\n\nRepro + fix notes.',
    },
  },
};

export const Loading: Story = {
  args: { task: null, loading: true },
};

export const ErrorState: Story = {
  args: { task: null, error: new Error('Task 004 not found') },
};
