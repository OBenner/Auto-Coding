import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CommentThread } from './CommentThread';

// Mock collaboration store
vi.mock('@/renderer/stores/collaboration-store', () => ({
  useCollaborationStore: vi.fn(() => ({
    getComments: vi.fn(() => []),
    addComment: vi.fn(),
    resolveComment: vi.fn(),
  })),
}));

describe('CommentThread', () => {
  it('renders comment thread component', () => {
    const comments = [
      {
        id: 'c1',
        author: 'user1',
        authorName: 'Alice',
        content: 'Test comment',
        status: 'active' as const,
        createdAt: new Date().toISOString()
      }
    ];
    render(<CommentThread comments={comments} specId="test" onAddComment={() => {}} />);
    expect(screen.getByText('Alice')).toBeDefined();
  });
});
