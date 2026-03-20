/**
 * BuildTimeline main component
 *
 * Horizontal timeline visualization showing agent phases, subtasks, and their relationships
 * with real-time progress updates, zoom/pan controls, and export functionality.
 */

import { useState, useCallback, useRef, useEffect, memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';
import { cn } from '../../lib/utils';
import { useTimelineData } from './hooks/useTimelineData';
import { useTimelineExport } from './hooks/useTimelineExport';
import type {
  TimelineData,
  TimelineViewState,
  TimelineConfig,
  TimelineAnimationState,
  TimelinePhase,
  TimelineSubtask,
} from './types';
import {
  calculateAllPhaseLayouts,
  calculateAllSubtaskLayouts,
  calculateTimelineWidth,
  calculateTimelineHeight,
  clampZoom,
  calculateScrollAfterZoom,
} from './utils/timeline-layout';
import { DEFAULT_TIMELINE_CONFIG } from './types';
import { PhaseSwimLane } from './PhaseSwimLane';
import { TimelineControls } from './TimelineControls';
import { DependencyConnector } from './DependencyConnector';

interface BuildTimelineProps {
  /** Task ID to load implementation plan for */
  taskId: string;
  /** Current execution progress for real-time updates */
  executionProgress?: TimelineData['executionProgress'];
  /** Custom configuration options */
  config?: Partial<TimelineConfig>;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Main timeline component with horizontal layout, zoom/pan controls, and phase swim lanes
 * Handles view state, layout calculations, and provides context for child components
 */
export const BuildTimeline = memo(function BuildTimeline({
  taskId,
  executionProgress,
  config: customConfig,
  className,
}: BuildTimelineProps) {
  const { t } = useTranslation('tasks');

  // Merge custom config with defaults
  const config: TimelineConfig = {
    ...DEFAULT_TIMELINE_CONFIG,
    ...customConfig,
  };

  // Load timeline data
  const {
    timelineData,
    isLoading,
    error,
    refresh,
    getPhase,
    getSubtask,
    getSubtasksForPhase,
    getCurrentSubtask,
    getOverallProgress,
  } = useTimelineData(taskId, executionProgress);

  // View state for zoom and pan
  const [viewState, setViewState] = useState<TimelineViewState>({
    zoom: config.defaultZoom,
    scrollX: 0,
    scrollY: 0,
    isDragging: false,
  });

  // Animation state for performance optimization
  const [animationState, setAnimationState] = useState<TimelineAnimationState>({
    isEnabled: config.enableAnimations,
    isVisible: true,
  });

  // Refs for container and scroll handling
  const containerRef = useRef<HTMLDivElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const dragStartRef = useRef<{ x: number; y: number; scrollX: number; scrollY: number } | null>(null);

  // Export functionality
  const { exportAndDownload, isExporting } = useTimelineExport({
    defaultOptions: {
      filename: `timeline-${taskId}`,
    },
  });

  /**
   * Force refresh when executionProgress changes (for real-time updates)
   */
  useEffect(() => {
    if (executionProgress) {
      refresh();
    }
  }, [executionProgress, refresh]);

  /**
   * Handle export button click
   */
  const handleExport = useCallback(() => {
    if (timelineRef.current) {
      exportAndDownload(timelineRef.current);
    }
  }, [exportAndDownload]);

  /**
   * Handle scroll change
   */
  const handleScrollChange = useCallback((scrollX: number, scrollY: number) => {
    setViewState((prev) => ({
      ...prev,
      scrollX,
      scrollY,
    }));
  }, []);

  /**
   * Handle mouse wheel for zooming (Ctrl+wheel) and scrolling
   */
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        // Zoom with Ctrl/Cmd+wheel
        e.preventDefault();
        const delta = e.deltaY > 0 ? -1 : 1;
        const rect = containerRef.current?.getBoundingClientRect();
        if (!rect) return;

        const focusX = e.clientX - rect.left;
        const focusY = e.clientY - rect.top;

        const newZoom = clampZoom(viewState.zoom + delta * 0.1, config);
        const newScroll = calculateScrollAfterZoom(
          viewState.scrollX,
          viewState.scrollY,
          viewState.zoom,
          newZoom,
          focusX,
          focusY
        );

        setViewState({
          ...viewState,
          zoom: newZoom,
          scrollX: newScroll.scrollX,
          scrollY: newScroll.scrollY,
        });
      }
    },
    [viewState, config]
  );

  /**
   * Handle mouse down for drag-to-pan
   */
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // Only start drag on middle mouse button or space+left click
    if (e.button === 1 || (e.button === 0 && false)) {
      e.preventDefault();
      setViewState((prev) => ({
        ...prev,
        isDragging: true,
      }));
      dragStartRef.current = {
        x: e.clientX,
        y: e.clientY,
        scrollX: viewState.scrollX,
        scrollY: viewState.scrollY,
      };
    }
  }, [viewState]);

  /**
   * Handle mouse move for dragging
   */
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!viewState.isDragging || !dragStartRef.current) return;

    const deltaX = dragStartRef.current.x - e.clientX;
    const deltaY = dragStartRef.current.y - e.clientY;

    setViewState({
      ...viewState,
      scrollX: dragStartRef.current.scrollX + deltaX,
      scrollY: dragStartRef.current.scrollY + deltaY,
    });
  }, [viewState]);

  /**
   * Handle mouse up to end drag
   */
  const handleMouseUp = useCallback(() => {
    setViewState((prev) => ({
      ...prev,
      isDragging: false,
    }));
    dragStartRef.current = null;
  }, []);

  /**
   * Handle subtask click
   */
  const handleSubtaskClick = useCallback((subtask: TimelineSubtask) => {
    // TODO: Will be implemented when SubtaskBlock is created
    console.log('[BuildTimeline] Subtask clicked:', subtask.id);
  }, []);

  /**
   * Handle phase click
   */
  const handlePhaseClick = useCallback((phase: TimelinePhase) => {
    // Phase click handler - can be extended for phase selection/filtering
    console.log('[BuildTimeline] Phase clicked:', `phase-${phase.phase}`, phase.name);
  }, []);

  // IntersectionObserver for performance optimization
  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setAnimationState((prev) => ({
          ...prev,
          isVisible: entry.isIntersecting,
        }));
      },
      { threshold: 0.1 }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // Calculate layouts (memoized for performance)
  const phaseLayouts = useMemo(
    () =>
      timelineData
        ? calculateAllPhaseLayouts(timelineData.phases, viewState, config)
        : new Map(),
    [timelineData, viewState, config]
  );

  const subtasksByPhase = useMemo(
    () =>
      timelineData
        ? new Map(
            timelineData.phases.map((phase) => [
              `phase-${phase.phase}`,
              getSubtasksForPhase(phase.phase),
            ])
          )
        : new Map(),
    [timelineData, getSubtasksForPhase]
  );

  const subtaskLayouts = useMemo(
    () =>
      timelineData && phaseLayouts
        ? calculateAllSubtaskLayouts(subtasksByPhase, phaseLayouts, viewState, config)
        : new Map(),
    [timelineData, phaseLayouts, subtasksByPhase, viewState, config]
  );

  // Calculate timeline dimensions (memoized for performance)
  const timelineWidth = useMemo(
    () =>
      timelineData
        ? calculateTimelineWidth(timelineData.subtasks, config, viewState.zoom)
        : 0,
    [timelineData, config, viewState.zoom]
  );

  const timelineHeight = useMemo(
    () =>
      timelineData
        ? calculateTimelineHeight(timelineData.phases.length, config, viewState.zoom)
        : 0,
    [timelineData, config, viewState.zoom]
  );

  // Loading state
  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <motion.div
          className="flex flex-col items-center gap-3"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <p className="text-sm text-muted-foreground">
            {t('timeline.loading') || 'Loading timeline...'}
          </p>
        </motion.div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <motion.div
          className="flex flex-col items-center gap-3 text-center max-w-md"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div className="h-12 w-12 rounded-full bg-destructive/10 flex items-center justify-center">
            <svg className="h-6 w-6 text-destructive" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">
              {t('timeline.error') || 'Failed to load timeline'}
            </p>
            <p className="text-xs text-muted-foreground mt-1">{error}</p>
          </div>
        </motion.div>
      </div>
    );
  }

  // Empty state
  if (!timelineData || timelineData.phases.length === 0) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <motion.div
          className="flex flex-col items-center gap-3 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
            <svg className="h-6 w-6 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
            </svg>
          </div>
          <p className="text-sm text-muted-foreground">
            {t('timeline.noData') || 'No timeline data available'}
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn('relative w-full h-full overflow-hidden', className)}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Timeline controls overlay */}
      <TimelineControls
        viewState={viewState}
        config={config}
        onZoomChange={(zoom) => setViewState((prev) => ({ ...prev, zoom }))}
        onPanChange={(scrollX, scrollY) => setViewState((prev) => ({ ...prev, scrollX, scrollY }))}
        onExport={handleExport}
        isExporting={isExporting}
        position="top-right"
        showPanControls={false}
        showZoomControls={true}
        showExportButton={true}
      />

      {/* Scrollable timeline container */}
      <div
        ref={timelineRef}
        className="w-full h-full overflow-auto"
        style={{
          cursor: viewState.isDragging ? 'grabbing' : 'grab',
        }}
        onScroll={(e) => {
          handleScrollChange(e.currentTarget.scrollLeft, e.currentTarget.scrollTop);
        }}
      >
        {/* Timeline content with zoom transform */}
        <motion.div
          className="relative"
          style={{
            width: timelineWidth,
            height: timelineHeight,
            transform: `scale(${viewState.zoom})`,
            transformOrigin: 'top left',
          }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          {/* Phase swim lanes */}
          <div className="w-full h-full">
            {timelineData.phases.map((phase) => {
              const phaseId = `phase-${phase.phase}`;
              const layout = phaseLayouts.get(phaseId);

              if (!layout) return null;

              return (
                <PhaseSwimLane
                  key={phaseId}
                  phase={phase}
                  layout={layout}
                  progress={phase.progress}
                  enableAnimations={animationState.isEnabled && animationState.isVisible}
                  onClick={handlePhaseClick}
                />
              );
            })}
          </div>

          {/* SVG layer for dependency connectors */}
          <DependencyConnector
            phases={timelineData.phases}
            subtasks={timelineData.subtasks}
            phaseLayouts={phaseLayouts}
            subtaskLayouts={subtaskLayouts}
            config={config}
            viewState={viewState}
            className="absolute inset-0 pointer-events-none"
          />
        </motion.div>
      </div>

      {/* Cursor hint for drag-to-pan */}
      {viewState.isDragging && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-background/80 backdrop-blur-sm border rounded-lg px-3 py-1.5 text-xs text-muted-foreground pointer-events-none">
          {t('timeline.dragHint') || 'Drag to pan'}
        </div>
      )}
    </div>
  );
});
