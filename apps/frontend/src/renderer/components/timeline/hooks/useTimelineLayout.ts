/**
 * useTimelineLayout hook
 *
 * Hook for managing timeline view state including zoom, pan, and layout calculations.
 * Provides zoom in/out/reset, pan controls, drag-to-pan functionality, and CSS transforms.
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import type { TimelineViewState, TimelineConfig } from '../types';
import {
  clampZoom,
  calculateScrollAfterZoom,
} from '../utils/timeline-layout';

export interface UseTimelineLayoutResult {
  /** Current view state */
  viewState: TimelineViewState;
  /** CSS transform string for zoom/pan */
  transformStyle: string;
  /** Cursor style based on drag state */
  cursorStyle: string;
  /** Zoom in by one step */
  zoomIn: () => void;
  /** Zoom out by one step */
  zoomOut: () => void;
  /** Reset zoom to default */
  resetZoom: () => void;
  /** Set zoom to specific level */
  setZoom: (zoom: number) => void;
  /** Pan by delta pixels */
  pan: (deltaX: number, deltaY: number) => void;
  /** Set scroll position */
  scrollTo: (scrollX: number, scrollY: number) => void;
  /** Handle wheel event (zoom with Ctrl+wheel, pan with wheel) */
  handleWheel: (e: React.WheelEvent) => void;
  /** Handle mouse down for drag-to-pan */
  handleMouseDown: (e: React.MouseEvent) => void;
  /** Handle mouse move for dragging */
  handleMouseMove: (e: React.MouseEvent) => void;
  /** Handle mouse up to end drag */
  handleMouseUp: () => void;
}

export interface UseTimelineLayoutOptions {
  /** Timeline configuration */
  config: TimelineConfig;
  /** Container ref for calculating focus points */
  containerRef: React.RefObject<HTMLDivElement>;
  /** Initial zoom level (default: config.defaultZoom) */
  initialZoom?: number;
  /** Callback when view state changes */
  onViewStateChange?: (viewState: TimelineViewState) => void;
}

const ZOOM_STEP = 0.1;
const DRAG_THRESHOLD = 5; // Minimum pixels to register as drag

/**
 * Hook for managing timeline layout and view state
 */
export function useTimelineLayout({
  config,
  containerRef,
  initialZoom,
  onViewStateChange,
}: UseTimelineLayoutOptions): UseTimelineLayoutResult {
  // Initialize view state
  const [viewState, setViewState] = useState<TimelineViewState>({
    zoom: initialZoom ?? config.defaultZoom,
    scrollX: 0,
    scrollY: 0,
    isDragging: false,
  });

  // Refs for drag tracking
  const dragStartRef = useRef<{ x: number; y: number; scrollX: number; scrollY: number } | null>(null);
  const dragDistanceRef = useRef(0);

  // Notify parent of view state changes
  useEffect(() => {
    onViewStateChange?.(viewState);
  }, [viewState, onViewStateChange]);

  /**
   * Update view state with callback notification
   */
  const updateViewState = useCallback((updates: Partial<TimelineViewState>) => {
    setViewState((prev) => {
      const newState = { ...prev, ...updates };
      onViewStateChange?.(newState);
      return newState;
    });
  }, [onViewStateChange]);

  /**
   * Zoom in by one step
   */
  const zoomIn = useCallback(() => {
    setViewState((prev) => {
      const newZoom = clampZoom(prev.zoom + ZOOM_STEP, config);
      return { ...prev, zoom: newZoom };
    });
  }, [config]);

  /**
   * Zoom out by one step
   */
  const zoomOut = useCallback(() => {
    setViewState((prev) => {
      const newZoom = clampZoom(prev.zoom - ZOOM_STEP, config);
      return { ...prev, zoom: newZoom };
    });
  }, [config]);

  /**
   * Reset zoom to default level
   */
  const resetZoom = useCallback(() => {
    setViewState((prev) => ({
      ...prev,
      zoom: config.defaultZoom,
    }));
  }, [config.defaultZoom]);

  /**
   * Set zoom to specific level (clamped to min/max)
   */
  const setZoom = useCallback((zoom: number) => {
    const clampedZoom = clampZoom(zoom, config);
    setViewState((prev) => ({
      ...prev,
      zoom: clampedZoom,
    }));
  }, [config]);

  /**
   * Pan by delta pixels
   */
  const pan = useCallback((deltaX: number, deltaY: number) => {
    setViewState((prev) => ({
      ...prev,
      scrollX: prev.scrollX + deltaX,
      scrollY: prev.scrollY + deltaY,
    }));
  }, []);

  /**
   * Set scroll position to specific coordinates
   */
  const scrollTo = useCallback((scrollX: number, scrollY: number) => {
    setViewState((prev) => ({
      ...prev,
      scrollX,
      scrollY,
    }));
  }, []);

  /**
   * Handle wheel event for zooming and panning
   * - Ctrl/Cmd + wheel: zoom in/out
   * - Wheel alone: pan (handled by container scroll)
   */
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      // Zoom with Ctrl/Cmd+wheel
      e.preventDefault();

      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      // Calculate focus point relative to container
      const focusX = e.clientX - rect.left;
      const focusY = e.clientY - rect.top;

      // Calculate zoom delta (negative delta = zoom in, positive = zoom out)
      const delta = e.deltaY > 0 ? -1 : 1;
      const newZoom = clampZoom(viewState.zoom + delta * ZOOM_STEP, config);

      // Calculate new scroll position to maintain focus point
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
    // Regular wheel scrolling is handled by container's native scroll behavior
  }, [viewState, config, containerRef]);

  /**
   * Handle mouse down for drag-to-pan
   * Supports middle mouse button (button 1) and left mouse button (button 0)
   */
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // Start drag on middle mouse button or left mouse button
    if (e.button === 1 || e.button === 0) {
      e.preventDefault();

      dragStartRef.current = {
        x: e.clientX,
        y: e.clientY,
        scrollX: viewState.scrollX,
        scrollY: viewState.scrollY,
      };
      dragDistanceRef.current = 0;

      updateViewState({ isDragging: true });
    }
  }, [viewState, updateViewState]);

  /**
   * Handle mouse move for dragging
   */
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!viewState.isDragging || !dragStartRef.current) return;

    const deltaX = dragStartRef.current.x - e.clientX;
    const deltaY = dragStartRef.current.y - e.clientY;

    // Track total drag distance
    dragDistanceRef.current += Math.abs(deltaX) + Math.abs(deltaY);

    // Update scroll position
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
    // Only end drag if we moved beyond threshold (prevents accidental clicks)
    if (dragDistanceRef.current < DRAG_THRESHOLD) {
      // Reset scroll position if this was a click, not a drag
      if (dragStartRef.current) {
        setViewState({
          ...viewState,
          scrollX: dragStartRef.current.scrollX,
          scrollY: dragStartRef.current.scrollY,
        });
      }
    }

    dragStartRef.current = null;
    dragDistanceRef.current = 0;

    updateViewState({ isDragging: false });
  }, [viewState, updateViewState]);

  /**
   * Calculate CSS transform string for applying zoom
   * Uses CSS transform for smooth, hardware-accelerated zooming
   */
  const transformStyle = useMemo(() => {
    return `scale(${viewState.zoom})`;
  }, [viewState.zoom]);

  /**
   * Calculate cursor style based on drag state
   */
  const cursorStyle = useMemo(() => {
    return viewState.isDragging ? 'grabbing' : 'grab';
  }, [viewState.isDragging]);

  return {
    viewState,
    transformStyle,
    cursorStyle,
    zoomIn,
    zoomOut,
    resetZoom,
    setZoom,
    pan,
    scrollTo,
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
  };
}
