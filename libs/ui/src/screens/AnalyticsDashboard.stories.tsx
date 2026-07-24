import type { Meta, StoryObj } from '@storybook/react-vite';
import { AnalyticsDashboard } from './AnalyticsDashboard';

const TREND = [42, 44, 41, 48, 46, 52, 50, 56, 54, 60, 58, 64];

const meta = {
  title: 'Screens/AnalyticsDashboard',
  component: AnalyticsDashboard,
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
    kpis: [
      { value: '112', label: 'specs shipped', sub: 'this quarter', trend: TREND, trendTone: 'good' },
      { value: '87%', label: 'success rate', sub: '+4pt vs last month', tone: 'good', trend: [80, 82, 81, 84, 85, 87], trendTone: 'good' },
      { value: '$142', label: 'total cost', sub: 'across 112 specs', trend: [8, 10, 9, 12, 11, 14, 13, 16], trendTone: 'warn' },
      { value: '4.2M', label: 'tokens used', sub: 'input + output', trend: [30, 28, 32, 31, 35, 34, 38], trendTone: 'info' },
    ],
    charts: [
      {
        title: 'Spec velocity',
        ariaLabel: 'Completed vs failed specs per week over 12 weeks',
        showLegend: true,
        xLabels: ['W1', 'W3', 'W5', 'W7', 'W9', 'W12'],
        series: [
          { label: 'Completed', tone: 'good', values: [4, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16] },
          { label: 'Failed', tone: 'bad', values: [2, 1, 2, 1, 2, 1, 1, 2, 1, 1, 0, 1] },
        ],
      },
      {
        title: 'Success rate trend',
        ariaLabel: 'Overall success rate over 12 weeks',
        xLabels: ['W1', 'W6', 'W12'],
        series: [{ label: 'Success rate', tone: 'info', values: [72, 74, 71, 78, 80, 82, 81, 84, 85, 86, 87, 88] }],
      },
    ],
    sections: [
      {
        title: 'Outcomes',
        rows: [
          { label: 'Completed', value: '98' },
          { label: 'Failed', value: '9' },
          { label: 'In progress', value: '5' },
        ],
      },
      {
        title: 'QA',
        rows: [
          { label: 'Reviews', value: '204' },
          { label: 'Approved', value: '181' },
          { label: 'Rejection rate', value: '11%' },
        ],
      },
    ],
  },
} satisfies Meta<typeof AnalyticsDashboard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Dashboard: Story = {};

export const NoRail: Story = {
  args: { sections: undefined },
};

export const Loading: Story = {
  args: { kpis: null, loading: true },
};

export const ErrorState: Story = {
  args: { kpis: null, error: new Error('Failed to load analytics') },
};

export const Empty: Story = {
  args: { kpis: [], charts: undefined, sections: undefined },
};
