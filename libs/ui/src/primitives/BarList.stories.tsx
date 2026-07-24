import type { Meta, StoryObj } from '@storybook/react-vite';
import { BarList } from './BarList';

const meta = {
  title: 'Primitives/BarList',
  component: BarList,
  decorators: [
    (Story) => (
      <div style={{ maxWidth: 360, padding: 16 }}>
        <Story />
      </div>
    ),
  ],
  args: {
    ariaLabel: 'PR size distribution',
    items: [
      { label: 'XS <50', value: 26, tone: 'good' },
      { label: 'S 50–200', value: 21, tone: 'good' },
      { label: 'M 200–500', value: 10, tone: 'info' },
      { label: 'L 500–1k', value: 4, tone: 'warn' },
      { label: 'XL >1k', value: 1, tone: 'bad' },
    ],
  },
} satisfies Meta<typeof BarList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Distribution: Story = {};

export const WithValueLabels: Story = {
  args: {
    ariaLabel: 'Tokens by model',
    items: [
      { label: 'Sonnet 4.6', value: 1_240_000, valueLabel: '1.2M', tone: 'info' },
      { label: 'Haiku 4.5', value: 680_000, valueLabel: '680k', tone: 'good' },
      { label: 'Opus 4.8', value: 210_000, valueLabel: '210k', tone: 'warn' },
    ],
  },
};

export const SingleRow: Story = {
  args: { ariaLabel: 'One category', items: [{ label: 'Only', value: 7 }] },
};
