import type { Meta, StoryObj } from '@storybook/react-vite';
import { Badge } from './Badge';

const meta = {
  title: 'Primitives/Badge',
  component: Badge,
  args: { children: 'Coder', tone: 'info', size: 'md' },
} satisfies Meta<typeof Badge>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const AllTones: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <Badge tone="good">QA passed</Badge>
      <Badge tone="info">Coder</Badge>
      <Badge tone="warn">Recovery</Badge>
      <Badge tone="bad">Error</Badge>
      <Badge tone="neutral">Draft</Badge>
    </div>
  ),
};

export const CardChipSize: Story = {
  name: 'Size sm (card chip)',
  render: () => (
    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      <Badge size="sm" tone="neutral">
        Draft
      </Badge>
      <Badge size="sm" tone="info">
        Coder
      </Badge>
      <Badge size="sm" tone="good">
        Merged
      </Badge>
    </div>
  ),
};
