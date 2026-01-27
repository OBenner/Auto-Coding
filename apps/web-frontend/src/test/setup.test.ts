import { describe, it, expect } from 'vitest';

describe('Test Infrastructure', () => {
  it('should run tests with Vitest', () => {
    expect(true).toBe(true);
  });

  it('should have jest-dom matchers available', () => {
    const element = document.createElement('div');
    element.textContent = 'Hello World';
    document.body.appendChild(element);
    expect(element).toBeInTheDocument();
    document.body.removeChild(element);
  });

  it('should have jsdom environment', () => {
    expect(typeof window).toBe('object');
    expect(typeof document).toBe('object');
  });
});
