import type { Meta, StoryObj } from '@storybook/react-vite';
import { Button } from './Button';

const meta = {
  title: 'Primitives/Button',
  component: Button,
  args: { children: 'Import spec', variant: 'default' },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Playground: Story = {};

export const HeaderActions: Story = {
  name: 'Header actions (mock)',
  render: () => (
    <div style={{ display: 'flex', gap: 8 }}>
      <Button>Import spec</Button>
      <Button>Bulk QA</Button>
      <Button variant="primary">+ New spec</Button>
      <Button disabled>Disabled</Button>
    </div>
  ),
};
