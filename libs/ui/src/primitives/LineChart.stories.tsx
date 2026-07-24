import type { Meta, StoryObj } from '@storybook/react-vite';
import { LineChart } from './LineChart';

const meta = {
  title: 'Primitives/LineChart',
  component: LineChart,
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 760, padding: 16 }}>
        <Story />
      </div>
    ),
  ],
  args: {
    series: [
      {
        label: 'Merged',
        tone: 'good',
        values: [4, 6, 5, 8, 7, 10, 9, 12, 11, 14, 13, 16],
      },
      {
        label: 'Opened',
        tone: 'info',
        values: [8, 9, 7, 11, 10, 12, 11, 13, 12, 14, 13, 15],
      },
    ],
    xLabels: ['Apr 1', 'Apr 8', 'Apr 15', 'Apr 22', 'May 1', 'May 8'],
    gridLines: 4,
    showLegend: true,
    ariaLabel: 'Merged vs opened PRs over six weeks',
  },
} satisfies Meta<typeof LineChart>;

export default meta;
type Story = StoryObj<typeof meta>;

export const TwoSeries: Story = {};

export const SingleSeries: Story = {
  args: {
    series: [
      { label: 'Throughput', tone: 'info', values: [12, 14, 11, 18, 16, 22, 20, 26] },
    ],
    showLegend: false,
  },
};

export const NoAxisLabels: Story = {
  args: { xLabels: undefined },
};
