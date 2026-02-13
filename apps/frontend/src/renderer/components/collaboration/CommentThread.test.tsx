import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CommentThread } from './CommentThread';

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
