import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VersionHistory } from './VersionHistory';

// Mock collaboration store
vi.mock('@/renderer/stores/collaboration-store', () => ({
  useCollaborationStore: vi.fn(() => ({
    getVersions: vi.fn(() => []),
    restoreVersion: vi.fn(),
  })),
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
