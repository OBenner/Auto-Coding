import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SuggestionMode } from './SuggestionMode';

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

describe('SuggestionMode', () => {
  it('renders suggestion mode component', () => {
    render(<SuggestionMode specId="test" isActive={true} onToggle={() => {}} />);
    expect(screen.getByText(/suggestion/i)).toBeDefined();
  });

  it('shows active state', () => {
    render(<SuggestionMode specId="test" isActive={true} onToggle={() => {}} />);
    const element = screen.getByText(/suggestion/i);
    expect(element).toBeDefined();
  });
});
