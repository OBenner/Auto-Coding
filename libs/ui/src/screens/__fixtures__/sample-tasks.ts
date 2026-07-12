import type { UiTask } from '../../client/types';

/** Story/demo fixture: one board with every card affordance exercised. */
export const SAMPLE_TASKS: UiTask[] = [
  {
    id: '007',
    title: 'Dark mode for settings pane',
    status: 'draft',
    statusChip: { label: 'Draft', tone: 'neutral' },
  },
  {
    id: '008',
    title: 'Export usage report as CSV',
    status: 'draft',
    description: 'Finance asked for month-end exports',
  },
  {
    id: '004',
    title: 'Add user authentication',
    status: 'running',
    progress: 40,
    description: 'JWT + refresh flow',
    statusChip: { label: 'Coder', tone: 'info' },
    badges: [
      { label: 'Frontend', tone: 'info' },
      { label: 'On track', tone: 'good' },
    ],
    meta: ['coder-1', '22m'],
  },
  {
    id: '005',
    title: 'Realtime terminal streaming',
    status: 'running',
    progress: 72,
  },
  {
    id: '003',
    title: 'Workspace invitations by email',
    status: 'review',
    badges: [{ label: 'QA passed', tone: 'good' }],
  },
  {
    id: '006',
    title: 'Flaky e2e: retry uploads',
    status: 'review',
    badges: [{ label: 'Error', tone: 'bad' }],
  },
  {
    id: '001',
    title: 'Spec index + audit trail',
    status: 'done',
    statusChip: { label: 'Merged', tone: 'good' },
    badges: [{ label: 'PR', tone: 'info' }],
  },
  { id: '002', title: 'Per-user PTY isolation', status: 'done' },
];
