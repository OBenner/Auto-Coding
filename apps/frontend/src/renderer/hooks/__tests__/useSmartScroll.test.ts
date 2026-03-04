/**
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSmartScroll } from '../useSmartScroll';

describe('useSmartScroll', () => {
  it('should initialize with user not scrolled up', () => {
    const { result } = renderHook(() => useSmartScroll());

    expect(result.current.isUserScrolledUp).toBe(false);
    expect(result.current.endRef).toBeDefined();
    expect(result.current.containerRef).toBeDefined();
  });

  it('should detect when user scrolls up (far from bottom)', () => {
    const { result } = renderHook(() => useSmartScroll([], 100));

    act(() => {
      const event = {
        target: {
          scrollHeight: 1000,
          scrollTop: 200,
          clientHeight: 500,
        },
      } as unknown as React.UIEvent<HTMLDivElement>;

      result.current.handleScroll(event);
    });

    // 1000 - 200 - 500 = 300 > 100 threshold
    expect(result.current.isUserScrolledUp).toBe(true);
  });

  it('should detect when user is near bottom', () => {
    const { result } = renderHook(() => useSmartScroll([], 100));

    // Scroll up first
    act(() => {
      result.current.handleScroll({
        target: { scrollHeight: 1000, scrollTop: 200, clientHeight: 500 },
      } as unknown as React.UIEvent<HTMLDivElement>);
    });
    expect(result.current.isUserScrolledUp).toBe(true);

    // Scroll near bottom
    act(() => {
      result.current.handleScroll({
        target: { scrollHeight: 1000, scrollTop: 450, clientHeight: 500 },
      } as unknown as React.UIEvent<HTMLDivElement>);
    });

    // 1000 - 450 - 500 = 50 < 100 threshold
    expect(result.current.isUserScrolledUp).toBe(false);
  });

  it('should respect custom threshold', () => {
    const { result } = renderHook(() => useSmartScroll([], 50));

    // 70px from bottom (> 50 threshold)
    act(() => {
      result.current.handleScroll({
        target: { scrollHeight: 1000, scrollTop: 880, clientHeight: 50 },
      } as unknown as React.UIEvent<HTMLDivElement>);
    });
    expect(result.current.isUserScrolledUp).toBe(true);

    // 40px from bottom (< 50 threshold)
    act(() => {
      result.current.handleScroll({
        target: { scrollHeight: 1000, scrollTop: 910, clientHeight: 50 },
      } as unknown as React.UIEvent<HTMLDivElement>);
    });
    expect(result.current.isUserScrolledUp).toBe(false);
  });

  it('should reset scroll state', () => {
    const { result } = renderHook(() => useSmartScroll([], 100));

    act(() => {
      result.current.handleScroll({
        target: { scrollHeight: 1000, scrollTop: 0, clientHeight: 500 },
      } as unknown as React.UIEvent<HTMLDivElement>);
    });
    expect(result.current.isUserScrolledUp).toBe(true);

    act(() => {
      result.current.resetScroll();
    });
    expect(result.current.isUserScrolledUp).toBe(false);
  });

  it('should return stable refs across renders', () => {
    const { result, rerender } = renderHook(() => useSmartScroll());

    const firstEndRef = result.current.endRef;
    const firstContainerRef = result.current.containerRef;

    rerender();

    expect(result.current.endRef).toBe(firstEndRef);
    expect(result.current.containerRef).toBe(firstContainerRef);
  });

  it('should detect at-bottom when scroll is exactly at bottom', () => {
    const { result } = renderHook(() => useSmartScroll([], 100));

    act(() => {
      result.current.handleScroll({
        target: { scrollHeight: 1000, scrollTop: 500, clientHeight: 500 },
      } as unknown as React.UIEvent<HTMLDivElement>);
    });

    // 1000 - 500 - 500 = 0 < 100 threshold
    expect(result.current.isUserScrolledUp).toBe(false);
  });
});
