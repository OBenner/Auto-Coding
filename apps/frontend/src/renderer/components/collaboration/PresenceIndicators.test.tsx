import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PresenceIndicators } from './PresenceIndicators';

describe('PresenceIndicators', () => {
  it('shows active users', () => {
    const users = [
      { userId: 'user1', userName: 'Alice', status: 'editing' as const }
    ];
    render(<PresenceIndicators users={users} />);
    expect(screen.getByText('Alice')).toBeDefined();
  });
});
