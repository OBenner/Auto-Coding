/**
 * TimelineControls component
 *
 * Zoom and pan controls for the timeline visualization.
 * Provides buttons for zooming in/out, resetting zoom, and displaying current zoom level.
 */

import { memo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';
import { cn } from '../../lib/utils';
import type { TimelineViewState, TimelineConfig } from './types';

interface TimelineControlsProps {
  /** Current view state */
  viewState: TimelineViewState;
  /** Timeline configuration */
  config: TimelineConfig;
  /** Callback when zoom changes */
  onZoomChange?: (zoom: number) => void;
  /** Callback when pan changes */
  onPanChange?: (scrollX: number, scrollY: number) => void;
  /** Additional CSS classes */
  className?: string;
  /** Position variant for controls */
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  /** Whether to show pan controls */
  showPanControls?: boolean;
  /** Whether to show zoom controls */
  showZoomControls?: boolean;
}

/**
 * Timeline control buttons with zoom and pan functionality
 * Provides visual feedback and follows established UI patterns
 */
export const TimelineControls = memo(function TimelineControls({
  viewState,
  config,
  onZoomChange,
  onPanChange,
  className,
  position = 'top-right',
  showPanControls = false,
  showZoomControls = true,
}: TimelineControlsProps) {
  const { t } = useTranslation('timeline');

  /**
   * Handle zoom in
   */
  const handleZoomIn = useCallback(() => {
    const newZoom = Math.min(viewState.zoom + 0.1, config.maxZoom);
    onZoomChange?.(newZoom);
  }, [viewState.zoom, config.maxZoom, onZoomChange]);

  /**
   * Handle zoom out
   */
  const handleZoomOut = useCallback(() => {
    const newZoom = Math.max(viewState.zoom - 0.1, config.minZoom);
    onZoomChange?.(newZoom);
  }, [viewState.zoom, config.minZoom, onZoomChange]);

  /**
   * Handle zoom reset
   */
  const handleZoomReset = useCallback(() => {
    onZoomChange?.(config.defaultZoom);
  }, [config.defaultZoom, onZoomChange]);

  /**
   * Handle pan up
   */
  const handlePanUp = useCallback(() => {
    onPanChange?.(viewState.scrollX, viewState.scrollY - 100);
  }, [viewState.scrollX, viewState.scrollY, onPanChange]);

  /**
   * Handle pan down
   */
  const handlePanDown = useCallback(() => {
    onPanChange?.(viewState.scrollX, viewState.scrollY + 100);
  }, [viewState.scrollX, viewState.scrollY, onPanChange]);

  /**
   * Handle pan left
   */
  const handlePanLeft = useCallback(() => {
    onPanChange?.(viewState.scrollX - 100, viewState.scrollY);
  }, [viewState.scrollX, viewState.scrollY, onPanChange]);

  /**
   * Handle pan right
   */
  const handlePanRight = useCallback(() => {
    onPanChange?.(viewState.scrollX + 100, viewState.scrollY);
  }, [viewState.scrollX, viewState.scrollY, onPanChange]);

  // Position classes
  const positionClasses: Record<typeof position, string> = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4',
  };

  const canZoomIn = viewState.zoom < config.maxZoom;
  const canZoomOut = viewState.zoom > config.minZoom;

  return (
    <div
      className={cn(
        'absolute z-20 flex flex-col gap-2',
        positionClasses[position],
        className
      )}
    >
      {/* Zoom controls */}
      {showZoomControls && (
        <motion.div
          className="flex items-center gap-1 bg-background/80 backdrop-blur-sm border rounded-lg p-1 shadow-sm"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2 }}
        >
          {/* Zoom in button */}
          <motion.button
            whileHover={{ scale: canZoomIn ? 1.05 : 1 }}
            whileTap={{ scale: canZoomIn ? 0.95 : 1 }}
            onClick={handleZoomIn}
            disabled={!canZoomIn}
            className={cn(
              'p-1.5 rounded-md transition-colors',
              'hover:bg-accent',
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent'
            )}
            title={t('controls.zoomIn') || 'Zoom in'}
            aria-label={t('controls.zoomIn') || 'Zoom in'}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </motion.button>

          {/* Zoom reset button with percentage display */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleZoomReset}
            className="p-1.5 rounded-md hover:bg-accent transition-colors text-xs font-medium min-w-[3.5rem]"
            title={t('controls.reset') || 'Reset zoom'}
            aria-label={t('controls.reset') || 'Reset zoom'}
          >
            {Math.round(viewState.zoom * 100)}%
          </motion.button>

          {/* Zoom out button */}
          <motion.button
            whileHover={{ scale: canZoomOut ? 1.05 : 1 }}
            whileTap={{ scale: canZoomOut ? 0.95 : 1 }}
            onClick={handleZoomOut}
            disabled={!canZoomOut}
            className={cn(
              'p-1.5 rounded-md transition-colors',
              'hover:bg-accent',
              'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent'
            )}
            title={t('controls.zoomOut') || 'Zoom out'}
            aria-label={t('controls.zoomOut') || 'Zoom out'}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            </svg>
          </motion.button>
        </motion.div>
      )}

      {/* Pan controls */}
      {showPanControls && (
        <motion.div
          className="bg-background/80 backdrop-blur-sm border rounded-lg p-1.5 shadow-sm"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2, delay: 0.05 }}
        >
          <div className="grid grid-cols-3 gap-0.5">
            {/* Empty top-left */}
            <div />

            {/* Pan up */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handlePanUp}
              className="p-1.5 rounded-md hover:bg-accent transition-colors"
              title={t('controls.panUp') || 'Pan up'}
              aria-label={t('controls.panUp') || 'Pan up'}
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            </motion.button>

            {/* Empty top-right */}
            <div />

            {/* Pan left */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handlePanLeft}
              className="p-1.5 rounded-md hover:bg-accent transition-colors"
              title={t('controls.panLeft') || 'Pan left'}
              aria-label={t('controls.panLeft') || 'Pan left'}
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </motion.button>

            {/* Center indicator */}
            <div className="flex items-center justify-center">
              <div className="h-1.5 w-1.5 rounded-full bg-muted-foreground" />
            </div>

            {/* Pan right */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handlePanRight}
              className="p-1.5 rounded-md hover:bg-accent transition-colors"
              title={t('controls.panRight') || 'Pan right'}
              aria-label={t('controls.panRight') || 'Pan right'}
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </motion.button>

            {/* Empty bottom-left */}
            <div />

            {/* Pan down */}
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handlePanDown}
              className="p-1.5 rounded-md hover:bg-accent transition-colors"
              title={t('controls.panDown') || 'Pan down'}
              aria-label={t('controls.panDown') || 'Pan down'}
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </motion.button>

            {/* Empty bottom-right */}
            <div />
          </div>
        </motion.div>
      )}
    </div>
  );
});
