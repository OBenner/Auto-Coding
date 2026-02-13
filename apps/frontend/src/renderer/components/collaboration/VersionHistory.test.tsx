import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VersionHistory } from './VersionHistory';

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
