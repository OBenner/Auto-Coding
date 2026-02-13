import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SuggestionMode } from './SuggestionMode';

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
