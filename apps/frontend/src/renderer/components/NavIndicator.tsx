import { memo, useRef, useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';

export interface NavIndicatorProps {
  /** The active view ID */
  activeView: string;
  /** Container ref to measure positioning */
  containerRef: React.RefObject<HTMLDivElement>;
  /** Map of view IDs to their button elements */
  itemRefs: React.MutableRefObject<Map<string, HTMLButtonElement>>;
  /** Optional additional className */
  className?: string;
}

/**
 * Animated navigation indicator that slides to the active nav item.
 * Uses Motion's layout animations for smooth position/size transitions.
 *
 * Performance: Uses requestAnimationFrame for position updates and only
 * recalculates when the active view changes.
 */
export const NavIndicator = memo(function NavIndicator({
  activeView,
  containerRef,
  itemRefs,
  className,
}: NavIndicatorProps) {
  const rafRef = useRef<number | null>(null);
  const [position, setPosition] = useState<{
    top: number;
    height: number;
    opacity: number;
  }>({ top: 0, height: 0, opacity: 0 });

  // Update indicator position when active view changes
  useEffect(() => {
    const updatePosition = () => {
      const container = containerRef.current;
      const activeItem = itemRefs.current.get(activeView);

      if (!container || !activeItem) {
        // Fade out if we can't find the elements
        setPosition((prev) => ({ ...prev, opacity: 0 }));
        return;
      }

      const containerRect = container.getBoundingClientRect();
      const itemRect = activeItem.getBoundingClientRect();

      // Calculate position relative to container
      const top = itemRect.top - containerRect.top;
      const height = itemRect.height;

      // Cancel any pending RAF
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }

      // Schedule state update on next animation frame
      rafRef.current = requestAnimationFrame(() => {
        setPosition({ top, height, opacity: 1 });
        rafRef.current = null;
      });
    };

    // Initial update
    updatePosition();

    // Also update after a short delay to handle any layout transitions
    const timeoutId = setTimeout(updatePosition, 100);

    // Cleanup
    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
      clearTimeout(timeoutId);
    };
  }, [activeView, containerRef, itemRefs]);

  // Don't render if no position or invisible
  if (position.opacity === 0) {
    return null;
  }

  return (
    <motion.div
      className={cn(
        'absolute left-0 right-0 rounded-md bg-accent/50',
        'pointer-events-none',
        className
      )}
      layout
      initial={{ opacity: 0 }}
      animate={{
        top: position.top,
        height: position.height,
        opacity: position.opacity,
      }}
      transition={{
        type: 'spring',
        stiffness: 500,
        damping: 30,
        opacity: { duration: 0.15 },
      }}
      style={{
        // Use inline styles for layout properties that animate
        top: 0,
        height: 0,
      }}
    />
  );
});
