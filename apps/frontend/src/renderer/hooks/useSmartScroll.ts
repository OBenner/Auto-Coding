import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Smart auto-scroll hook that only auto-scrolls when the user is near the bottom.
 * Prevents the jarring experience of being yanked to the bottom while reading earlier content.
 *
 * @param deps - Dependencies that trigger a scroll check (e.g., messages array, log entries)
 * @param threshold - Distance from bottom (in px) to consider "near bottom" (default: 100)
 * @returns Object with refs and handlers for scroll management
 */
export function useSmartScroll(deps: unknown[] = [], threshold = 100) {
  const [isUserScrolledUp, setIsUserScrolledUp] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement;
    const isNearBottom = target.scrollHeight - target.scrollTop - target.clientHeight < threshold;
    setIsUserScrolledUp(!isNearBottom);
  }, [threshold]);

  // Auto-scroll to bottom when deps change, but only if user hasn't scrolled up
  useEffect(() => {
    if (!isUserScrolledUp && endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, isUserScrolledUp]);

  // Reset scroll state (e.g., when switching tabs or starting a new session)
  const resetScroll = useCallback(() => {
    setIsUserScrolledUp(false);
  }, []);

  return {
    endRef,
    containerRef,
    isUserScrolledUp,
    handleScroll,
    resetScroll,
  };
}
