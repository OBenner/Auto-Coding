import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CollaborativeSpecEditor } from './CollaborativeSpecEditor';

// Mock window.api
vi.mock('@/preload/api', () => ({
  collaboration: {
    connect: vi.fn(),
    disconnect: vi.fn(),
  }
}));

describe('CollaborativeSpecEditor', () => {
  it('renders editor', () => {
    render(<CollaborativeSpecEditor specId="test-spec" />);
    expect(screen.getByRole('textbox')).toBeDefined();
  });

  it('shows connection status', () => {
    render(<CollaborativeSpecEditor specId="test-spec" />);
    expect(screen.getByText(/connecting|connected/i)).toBeDefined();
  });
});
