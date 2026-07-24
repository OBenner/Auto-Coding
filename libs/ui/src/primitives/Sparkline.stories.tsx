import type { Meta, StoryObj } from '@storybook/react-vite';
import { Sparkline } from './Sparkline';

const meta = {
  title: 'Primitives/Sparkline',
  component: Sparkline,
  decorators: [
    (Story) => (
      <div style={{ width: 240, padding: 16 }}>
        <Story />
      </div>
    ),
  ],
  args: {
    values: [28, 26, 22, 24, 18, 20, 14, 16, 12, 10, 8, 6, 4],
    tone: 'info',
    ariaLabel: 'Throughput trending up over 13 days',
  },
} satisfies Meta<typeof Sparkline>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Rising: Story = {};

export const WithArea: Story = {
  args: { area: true },
};

export const Falling: Story = {
  args: {
    values: [8, 12, 10, 14, 16, 18, 20, 18, 22, 24, 22, 26, 28],
    tone: 'warn',
    ariaLabel: 'Latency trending up over 13 days',
  },
};

export const Flat: Story = {
  args: { values: [10, 10, 10, 10, 10], tone: 'neutral' },
};

export const Good: Story = {
  args: {
    values: [4, 6, 5, 8, 7, 10, 9, 12, 11, 14],
    tone: 'good',
    area: true,
  },
};
