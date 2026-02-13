import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VersionHistory } from './VersionHistory';

// Mock collaboration store
vi.mock('@/renderer/stores/collaboration-store', () => ({
  useCollaborationStore: vi.fn((selector) => {
    const mockState = {
      getComments: (specId: string) => [],
      getSuggestions: (specId: string) => [],
      getPresences: (specId: string) => [],
      getVersions: (specId: string) => [],
      addComment: vi.fn(),
      updateComment: vi.fn(),
      deleteComment: vi.fn(),
      resolveComment: vi.fn(),
      addSuggestion: vi.fn(),
      reviewSuggestion: vi.fn(),
      updatePresence: vi.fn(),
      approveVersion: vi.fn(),
      connectionState: 'disconnected' as const,
      currentSpecId: null,
      error: null,
      setCurrentSpec: vi.fn(),
      setError: vi.fn(),
      setLoading: vi.fn(),
      setConnectionState: vi.fn(),
    };
    return selector ? selector(mockState) : mockState;
  }),
}));

describe('VersionHistory', () => {
  it('renders version history component', () => {
    const versions = [
      {
        id: 'v1',
        author: 'user1',
        authorName: 'Alice',
        content: 'Version 1',
        createdAt: new Date().toISOString()
      }
    ];
    render(<VersionHistory versions={versions} specId="test" />);
    expect(screen.getByText('Alice')).toBeDefined();
  });

  it('displays version list', () => {
    const versions = [
      {
        id: 'v1',
        author: 'user1',
        authorName: 'Alice',
        content: 'Version 1',
        createdAt: new Date().toISOString()
      }
    ];
    render(<VersionHistory versions={versions} specId="test" />);
    expect(screen.getByText(/version/i)).toBeDefined();
  });
});
