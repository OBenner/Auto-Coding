/**
 * AnnotationOverlay - Visual selection overlay for creating UX annotations
 *
 * This component provides a full-screen overlay that allows users to select
 * areas of the UI for annotation. When annotation mode is active, users can
 * click and drag to create a selection rectangle, which then triggers the
 * annotation form for providing feedback details.
 *
 * Features:
 * - Full-screen overlay with crosshair cursor when annotation mode is active
 * - Click and drag selection with visual feedback
 * - Touch support for mobile/tablet devices
 * - Automatic screenshot capture of selected area
 * - Escape key to cancel selection
 * - Only renders in development mode
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAnnotationStore } from '../../stores/annotation-store';
import { debugError } from '../../../shared/utils/debug-logger';
import type { AnnotationCoordinates } from './types';
import type { AnnotationViewport } from '../../../shared/types/annotation';

/**
 * Selection state during drag operation
 */
interface SelectionState {
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  isDragging: boolean;
}

/**
 * Props for the AnnotationOverlay component
 */
export interface AnnotationOverlayProps {
  /** Optional callback when annotation selection is complete */
  onSelectionComplete?: (coordinates: AnnotationCoordinates) => void;
  /** Current route/page context for the annotation */
  currentRoute?: string;
}

/**
 * Minimum selection size in pixels (smaller selections are ignored)
 */
const MIN_SELECTION_SIZE = 20;

/**
 * AnnotationOverlay component
 *
 * Renders a full-screen overlay that captures mouse/touch events for
 * creating visual annotations. Only visible when annotation mode is active.
 */
export function AnnotationOverlay({
  onSelectionComplete,
  currentRoute
}: AnnotationOverlayProps) {
  const { t } = useTranslation('common');
  const overlayRef = useRef<HTMLDivElement>(null);

  const { isAnnotationMode, createDraftAnnotation, draftAnnotation } = useAnnotationStore();

  const [selection, setSelection] = useState<SelectionState>({
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    isDragging: false
  });

  /**
   * Get the viewport dimensions
   */
  const getViewportSize = useCallback((): AnnotationViewport => {
    return {
      width: window.innerWidth,
      height: window.innerHeight,
      devicePixelRatio: window.devicePixelRatio
    };
  }, []);

  /**
   * Capture screenshot of the entire window
   * Note: For region-specific capture, the image will be cropped based on coordinates
   */
  const captureScreenshot = useCallback(async (): Promise<string | null> => {
    try {
      // Get screenshot sources from the main process
      const sourcesResult = await window.electronAPI.getSources();

      if (!sourcesResult.success || !sourcesResult.data || sourcesResult.data.length === 0) {
        debugError('[AnnotationOverlay] No screenshot sources available');
        return null;
      }

      // Use the first available source (typically the main window/screen)
      const firstSource = sourcesResult.data[0];

      // Capture the screenshot
      const captureResult = await window.electronAPI.capture({
        sourceId: firstSource.id
      });

      if (!captureResult.success || !captureResult.data) {
        debugError('[AnnotationOverlay] Failed to capture screenshot:', captureResult.error);
        return null;
      }

      return captureResult.data;
    } catch (err) {
      debugError('[AnnotationOverlay] Error capturing screenshot:', err);
      return null;
    }
  }, []);

  /**
   * Calculate selection rectangle coordinates from selection state
   */
  const getSelectionCoordinates = useCallback((): AnnotationCoordinates | null => {
    const { startX, startY, currentX, currentY } = selection;

    const x = Math.min(startX, currentX);
    const y = Math.min(startY, currentY);
    const width = Math.abs(currentX - startX);
    const height = Math.abs(currentY - startY);

    // Validate minimum selection size
    if (width < MIN_SELECTION_SIZE || height < MIN_SELECTION_SIZE) {
      return null;
    }

    return { x, y, width, height };
  }, [selection]);

  /**
   * Handle mouse down to start selection
   */
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // Only handle left mouse button
    if (e.button !== 0) return;

    setSelection({
      startX: e.clientX,
      startY: e.clientY,
      currentX: e.clientX,
      currentY: e.clientY,
      isDragging: true
    });
  }, []);

  /**
   * Handle touch start to start selection
   */
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (e.touches.length === 0) return;

    const touch = e.touches[0];
    setSelection({
      startX: touch.clientX,
      startY: touch.clientY,
      currentX: touch.clientX,
      currentY: touch.clientY,
      isDragging: true
    });
  }, []);

  /**
   * Handle mouse move during selection
   */
  useEffect(() => {
    if (!selection.isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      setSelection((prev) => ({
        ...prev,
        currentX: e.clientX,
        currentY: e.clientY
      }));
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 0) return;

      const touch = e.touches[0];
      setSelection((prev) => ({
        ...prev,
        currentX: touch.clientX,
        currentY: touch.clientY
      }));
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('touchmove', handleTouchMove, { passive: true });

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('touchmove', handleTouchMove);
    };
  }, [selection.isDragging]);

  /**
   * Handle mouse up to complete selection
   */
  useEffect(() => {
    if (!selection.isDragging) return;

    const handleMouseUp = async () => {
      const coordinates = getSelectionCoordinates();

      if (!coordinates) {
        // Selection too small, cancel
        setSelection((prev) => ({ ...prev, isDragging: false }));
        return;
      }

      // Stop dragging state
      setSelection((prev) => ({ ...prev, isDragging: false }));

      // Capture screenshot
      const screenshot = await captureScreenshot();

      if (!screenshot) {
        debugError('[AnnotationOverlay] Failed to capture screenshot, aborting annotation');
        return;
      }

      // Get viewport size
      const viewportSize = getViewportSize();

      // Create draft annotation - this will trigger the form to open
      createDraftAnnotation(
        screenshot,
        coordinates,
        viewportSize,
        currentRoute,
        undefined // component detection not implemented yet
      );

      // Call optional callback
      if (onSelectionComplete) {
        onSelectionComplete(coordinates);
      }
    };

    const handleTouchEnd = async () => {
      await handleMouseUp();
    };

    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('touchend', handleTouchEnd);

    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('touchend', handleTouchEnd);
    };
  }, [selection.isDragging, getSelectionCoordinates, captureScreenshot, getViewportSize, createDraftAnnotation, currentRoute, onSelectionComplete]);

  /**
   * Handle Escape key to cancel selection
   */
  useEffect(() => {
    if (!selection.isDragging) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSelection({
          startX: 0,
          startY: 0,
          currentX: 0,
          currentY: 0,
          isDragging: false
        });
      }
    };

    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [selection.isDragging]);

  /**
   * Set cursor style when annotation mode is active
   */
  useEffect(() => {
    if (!overlayRef.current) return;

    if (isAnnotationMode && !draftAnnotation) {
      overlayRef.current.style.cursor = 'crosshair';
    } else {
      overlayRef.current.style.cursor = 'default';
    }
  }, [isAnnotationMode, draftAnnotation]);

  // Don't render if annotation mode is not active
  if (!isAnnotationMode) {
    return null;
  }

  // Don't render interactive overlay if draft annotation exists (form is open)
  if (draftAnnotation) {
    return null;
  }

  // Calculate selection rectangle for display
  const selectionRect = getSelectionCoordinates();

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 bg-transparent"
      onMouseDown={handleMouseDown}
      onTouchStart={handleTouchStart}
      aria-label={t('annotation.overlayAriaLabel')}
      role="presentation"
    >
      {/* Selection rectangle */}
      {selection.isDragging && selectionRect && (
        <div
          className="absolute border-2 border-primary bg-primary/20 pointer-events-none"
          style={{
            left: `${selectionRect.x}px`,
            top: `${selectionRect.y}px`,
            width: `${selectionRect.width}px`,
            height: `${selectionRect.height}px`
          }}
        >
          {/* Selection dimensions indicator */}
          <div className="absolute -top-6 left-0 bg-primary text-primary-foreground text-xs px-2 py-0.5 rounded">
            {selectionRect.width} × {selectionRect.height}
          </div>
        </div>
      )}

      {/* Instructions hint (shown when not dragging) */}
      {!selection.isDragging && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-muted/90 backdrop-blur text-foreground text-sm px-4 py-2 rounded-lg border border-border shadow-lg pointer-events-none">
          {t('annotation.selectionHint')}
        </div>
      )}

      {/* Escape hint (shown when dragging) */}
      {selection.isDragging && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-muted/90 backdrop-blur text-muted-foreground text-xs px-3 py-1.5 rounded-md border border-border shadow-lg pointer-events-none">
          {t('annotation.cancelHint')}
        </div>
      )}
    </div>
  );
}
