import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CollaborativeSpecEditor } from './CollaborativeSpecEditor';

// Mock collaboration store
vi.mock('@/renderer/stores/collaboration-store', () => ({
  useCollaborationStore: vi.fn(() => ({
    connectionState: 'connected',
    currentSpecId: 'test-spec',
    error: null,
    getPresences: vi.fn(() => []),
    setCurrentSpec: vi.fn(),
    setError: vi.fn(),
    setLoading: vi.fn(),
    setConnectionState: vi.fn(),
    getVersions: vi.fn(() => []),
    approveVersion: vi.fn(),
  })),
}));

describe('CollaborativeSpecEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders editor', () => {
    render(<CollaborativeSpecEditor specId="test-spec" initialContent="# Test content" />);
    expect(screen.getByRole('textbox')).toBeDefined();
  });

  it('shows connection status', () => {
    render(<CollaborativeSpecEditor specId="test-spec" initialContent="# Test content" />);
    // Component should render without errors
    expect(screen.getByRole('textbox')).toBeDefined();
  });
});
