import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PresenceIndicators } from './PresenceIndicators';

// Mock collaboration store
vi.mock('@/renderer/stores/collaboration-store', () => ({
  useCollaborationStore: vi.fn(() => ({
    getPresences: vi.fn(() => []),
  })),
}));

describe('PresenceIndicators', () => {
  it('shows active users', () => {
    const users = [
      { userId: 'user1', userName: 'Alice', status: 'editing' as const }
    ];
    render(<PresenceIndicators users={users} />);
    expect(screen.getByText('Alice')).toBeDefined();
  });
});
