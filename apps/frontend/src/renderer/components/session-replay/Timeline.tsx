/**
 * Timeline Component
 *
 * Horizontal timeline display for session entries with decision point markers.
 * Provides visual navigation through recorded session events.
 */

import { motion, AnimatePresence } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { memo, useRef, useState, useEffect, useCallback } from 'react';
import { Star, Circle } from 'lucide-react';
import { cn } from '../lib/utils';

// LogEntry interface matching SessionPlayer
export interface TimelineEntry {
  /** Unique identifier */
  id: string;
  /** Timestamp of the entry */
  timestamp: string;
  /** Entry phase (planning, coding, validation) */
  phase: string;
  /** Whether this is a decision point */
  is_decision_point: boolean;
  /** Entry index in the timeline */
  index: number;
}

interface TimelineProps {
  /** All timeline entries */
  entries: TimelineEntry[];
  /** Currently active entry index */
  currentIndex: number | null;
  /** Callback when an entry is clicked */
  onEntryClick?: (index: number) => void;
  /** Maximum visible markers before showing scroll (-1 for no limit) */
  maxVisible?: number;
  className?: string;
}

// Phase colors for markers
const PHASE_COLORS: Record<string, { color: string; bgColor: string }> = {
  planning: { color: 'bg-blue-500', bgColor: 'bg-blue-500/20' },
  coding: { color: 'bg-purple-500', bgColor: 'bg-purple-500/20' },
  validation: { color: 'bg-green-500', bgColor: 'bg-green-500/20' },
  default: { color: 'bg-gray-500', bgColor: 'bg-gray-500/20' },
};

/**
 * Timeline component with decision point markers
 * Supports horizontal scrolling, click navigation, and visual highlighting
 */
export const Timeline = memo(function Timeline({
  entries,
  currentIndex,
  onEntryClick,
  maxVisible = -1,
  className,
}: TimelineProps) {
  const { t } = useTranslation('session-replay');
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(true);
  const [isOverflowing, setIsOverflowing] = useState(false);
  const prevVisibleRef = useRef(true);

  // Use IntersectionObserver to pause animations when component is not visible
  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        const nowVisible = entry.isIntersecting;

        if (prevVisibleRef.current !== nowVisible && window.DEBUG) {
          console.log(`[Timeline] Visibility changed: ${prevVisibleRef.current} -> ${nowVisible}, animations ${nowVisible ? 'resumed' : 'paused'}`);
        }

        prevVisibleRef.current = nowVisible;
        setIsVisible(nowVisible);
      },
      { threshold: 0.1 }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // Check if content overflows and needs scroll indicators
  useEffect(() => {
    const checkOverflow = () => {
      const container = scrollContainerRef.current;
      if (container) {
        setIsOverflowing(container.scrollWidth > container.clientWidth);
      }
    };

    checkOverflow();
    window.addEventListener('resize', checkOverflow);
    return () => window.removeEventListener('resize', checkOverflow);
  }, [entries.length]);

  // Auto-scroll to current entry when it changes
  useEffect(() => {
    if (currentIndex !== null && scrollContainerRef.current) {
      const container = scrollContainerRef.current;
      const markers = container.querySelectorAll('[data-timeline-marker]');
      const activeMarker = markers[currentIndex] as HTMLElement;

      if (activeMarker) {
        activeMarker.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      }
    }
  }, [currentIndex]);

  // Only animate when visible
  const shouldAnimate = isVisible;

  // Handle entry click
  const handleEntryClick = useCallback(
    (index: number) => {
      onEntryClick?.(index);
    },
    [onEntryClick]
  );

  // Get phase colors for an entry
  const getPhaseColors = useCallback(
    (phase: string) => {
      return PHASE_COLORS[phase] || PHASE_COLORS.default;
    },
    []
  );

  if (entries.length === 0) {
    return (
      <div ref={containerRef} className={cn('flex items-center justify-center h-12 text-muted-foreground', className)}>
        <span className="text-xs">{t('sessionPlayer.entries')}: 0</span>
      </div>
    );
  }

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      {/* Timeline container with scroll */}
      <div
        ref={scrollContainerRef}
        className="flex items-center gap-1 overflow-x-auto scrollbar-thin scrollbar-thumb-muted-foreground/20 scrollbar-track-transparent px-2 py-3"
        role="navigation"
        aria-label={t('accessibility.navigateTimeline')}
      >
        {/* Connection line */}
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-border -translate-y-1/2 mx-2 pointer-events-none" />

        {/* Timeline markers */}
        <AnimatePresence mode="popLayout">
          {entries.map((entry, index) => {
            const isCurrent = index === currentIndex;
            const isPast = currentIndex !== null && index < currentIndex;
            const isDecisionPoint = entry.is_decision_point;
            const colors = getPhaseColors(entry.phase);

            return (
              <motion.button
                key={entry.id}
                data-timeline-marker
                onClick={() => handleEntryClick(index)}
                className={cn(
                  'relative shrink-0 z-10 transition-all',
                  'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
                  'rounded-full',
                  isCurrent
                    ? 'scale-125 ring-2 ring-primary ring-offset-2'
                    : 'hover:scale-110'
                )}
                initial={{ opacity: 0, scale: 0 }}
                animate={shouldAnimate ? {
                  opacity: isPast ? 0.5 : 1,
                  scale: isCurrent ? 1.25 : 1,
                } : {
                  opacity: isPast ? 0.5 : 1,
                  scale: 1,
                }}
                transition={{
                  delay: index * 0.02, // Stagger animation
                  duration: 0.2,
                }}
                aria-label={`${t('sessionPlayer.goToEntry')} ${index + 1} ${t('sessionPlayer.of')} ${entries.length}`}
                title={isDecisionPoint ? t('sessionPlayer.decisionPointMarker') : t('sessionPlayer.regularEntryMarker')}
              >
                {/* Marker */}
                {isDecisionPoint ? (
                  // Decision point marker - star icon
                  <motion.div
                    className={cn(
                      'relative w-6 h-6 rounded-full flex items-center justify-center',
                      colors.bgColor,
                      isCurrent && 'ring-2 ring-primary ring-offset-2'
                    )}
                    animate={shouldAnimate && isCurrent ? {
                      rotate: [0, -10, 10, -10, 0],
                    } : { rotate: 0 }}
                    transition={shouldAnimate && isCurrent ? {
                      duration: 0.5,
                      repeat: 1,
                      repeatDelay: 0.5,
                    } : undefined}
                  >
                    <Star
                      className={cn(
                        'w-3.5 h-3.5',
                        isCurrent ? 'text-primary fill-primary' : colors.color.replace('bg-', 'text-')
                      )}
                    />
                  </motion.div>
                ) : (
                  // Regular entry marker - circle
                  <div
                    className={cn(
                      'w-3 h-3 rounded-full',
                      isCurrent ? colors.color : cn(colors.color, 'opacity-70')
                    )}
                  />
                )}

                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-popover text-popover-foreground text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-20">
                  {index + 1}
                  {isDecisionPoint && (
                    <Star className="inline-block w-3 h-3 ml-1 fill-current" />
                  )}
                </div>
              </motion.button>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Scroll indicators */}
      <AnimatePresence>
        {isOverflowing && (
          <>
            <motion.div
              className="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-background to-transparent pointer-events-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
            <motion.div
              className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-background to-transparent pointer-events-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
          </>
        )}
      </AnimatePresence>

      {/* Entry counter */}
      {currentIndex !== null && (
        <motion.div
          className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-xs text-muted-foreground"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {currentIndex + 1} / {entries.length}
        </motion.div>
      )}
    </div>
  );
});
