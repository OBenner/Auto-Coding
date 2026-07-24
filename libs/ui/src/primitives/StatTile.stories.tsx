import type { Meta, StoryObj } from '@storybook/react-vite';
import { StatTile } from './StatTile';
import { Sparkline } from './Sparkline';

const meta = {
  title: 'Primitives/StatTile',
  component: StatTile,
  decorators: [
    (Story) => (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 200px)', gap: 12, padding: 16 }}>
        <Story />
      </div>
    ),
  ],
  args: {
    value: '112',
    label: 'specs shipped',
    sub: 'this quarter',
  },
} satisfies Meta<typeof StatTile>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Plain: Story = {};

export const Toned: Story = {
  args: { value: '87%', label: 'QA pass rate', sub: 'last 30 days', tone: 'good' },
};

export const WithSparkline: Story = {
  args: {
    value: '4.2k',
    label: 'tokens / spec',
    sub: 'trending down',
    tone: 'warn',
    sparkline: (
      <Sparkline
        values={[28, 24, 26, 20, 22, 16, 18, 12, 14, 10]}
        tone="warn"
        area
        ariaLabel="Tokens per spec trending down"
      />
    ),
  },
};
