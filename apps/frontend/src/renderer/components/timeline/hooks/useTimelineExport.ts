/**
 * useTimelineExport hook
 *
 * React hook for exporting timeline visualization as PNG images.
 * Provides functions to export, download, and copy timeline to clipboard.
 */

import { useState, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import type { TimelineExportOptions } from '../types';
import {
  exportAsImage,
  downloadImage,
  exportAndDownloadImage,
  copyImageToClipboard,
  isClipboardAvailable,
  getOptimalScale,
  type ExportProgress,
} from '../utils/export-as-image';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UseTimelineExportOptions {
  /** Default export options */
  defaultOptions?: Partial<TimelineExportOptions>;
  /** Whether to enable export functionality */
  enabled?: boolean;
  /** Callback when export starts */
  onExportStart?: () => void;
  /** Callback when export completes successfully */
  onExportSuccess?: (result: { filename: string; width: number; height: number }) => void;
  /** Callback when export fails */
  onExportError?: (error: Error) => void;
}

export interface UseTimelineExportResult {
  /** Export timeline and download as PNG */
  exportAndDownload: (element: HTMLElement) => Promise<void>;
  /** Export timeline to data URL without downloading */
  exportToDataUrl: (element: HTMLElement) => Promise<{
    dataUrl: string;
    filename: string;
    width: number;
    height: number;
  }>;
  /** Copy timeline to clipboard */
  copyToClipboard: (element: HTMLElement) => Promise<void>;
  /** Whether export is currently in progress */
  isExporting: boolean;
  /** Export progress (0-100) */
  exportProgress: number;
  /** Export progress step */
  exportStep: 'idle' | 'preparing' | 'rendering' | 'processing' | 'complete';
  /** Whether clipboard API is available */
  canCopyToClipboard: boolean;
  /** Last export error */
  exportError: Error | null;
  /** Clear the last export error */
  clearError: () => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * React hook for timeline export functionality
 *
 * @param options - Hook options
 * @returns Export functions and state
 *
 * @example
 * ```tsx
 * function TimelineComponent() {
 *   const timelineRef = useRef<HTMLDivElement>(null);
 *   const { exportAndDownload, isExporting, exportProgress } = useTimelineExport({
 *     defaultOptions: {
 *       filename: 'my-timeline',
 *       scale: 2,
 *     },
 *     onExportSuccess: (result) => {
 *       console.log('Exported:', result.filename);
 *     },
 *   });
 *
 *   return (
 *     <div>
 *       <div ref={timelineRef}>
 *         {/* Timeline content *\/}
 *       </div>
 *       <button
 *         onClick={() => timelineRef.current && exportAndDownload(timelineRef.current)}
 *         disabled={isExporting}
 *       >
 *         {isExporting ? `Exporting... ${exportProgress}%` : 'Export as PNG'}
 *       </button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useTimelineExport(
  options: UseTimelineExportOptions = {}
): UseTimelineExportResult {
  const {
    defaultOptions = {},
    enabled = true,
    onExportStart,
    onExportSuccess,
    onExportError,
  } = options;

  const { t } = useTranslation('timeline');

  // State
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [exportStep, setExportStep] = useState<UseTimelineExportResult['exportStep']>('idle');
  const [exportError, setExportError] = useState<Error | null>(null);

  // Ref to track current export
  const exportRef = useRef<{ aborted: boolean } | null>(null);

  /**
   * Clear the last export error
   */
  const clearError = useCallback(() => {
    setExportError(null);
  }, []);

  /**
   * Handle export progress
   */
  const handleProgress = useCallback((progress: ExportProgress) => {
    if (exportRef.current?.aborted) return;

    setExportProgress(progress.progress);
    setExportStep(progress.step);
  }, []);

  /**
   * Export timeline and download as PNG
   */
  const exportAndDownload = useCallback(
    async (element: HTMLElement) => {
      if (!enabled) {
        throw new Error('Export functionality is disabled');
      }

      // Reset state
      setIsExporting(true);
      setExportProgress(0);
      setExportStep('preparing');
      setExportError(null);

      // Create export tracker
      exportRef.current = { aborted: false };

      try {
        // Notify start
        onExportStart?.();

        // Generate export options
        const exportOptions: Partial<TimelineExportOptions> = {
          ...defaultOptions,
          filename: defaultOptions.filename || t('export.defaultFilename', { defaultValue: 'timeline' }),
          scale: defaultOptions.scale || getOptimalScale(),
        };

        // Export and download
        await exportAndDownloadImage(element, exportOptions, handleProgress);

        // Check if aborted
        if (exportRef.current.aborted) {
          return;
        }

        // Get result for callback
        const canvas = await exportAsImage(element, exportOptions);

        // Notify success
        onExportSuccess?.({
          filename: canvas.filename,
          width: canvas.width,
          height: canvas.height,
        });
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Export failed');
        setExportError(err);
        onExportError?.(err);
      } finally {
        setIsExporting(false);
        setExportStep('complete');
        exportRef.current = null;
      }
    },
    [enabled, defaultOptions, onExportStart, onExportSuccess, onExportError, handleProgress, t]
  );

  /**
   * Export timeline to data URL without downloading
   */
  const exportToDataUrl = useCallback(
    async (element: HTMLElement) => {
      if (!enabled) {
        throw new Error('Export functionality is disabled');
      }

      // Reset state
      setIsExporting(true);
      setExportProgress(0);
      setExportStep('preparing');
      setExportError(null);

      // Create export tracker
      exportRef.current = { aborted: false };

      try {
        // Notify start
        onExportStart?.();

        // Generate export options
        const exportOptions: Partial<TimelineExportOptions> = {
          ...defaultOptions,
          filename: defaultOptions.filename || t('export.defaultFilename', { defaultValue: 'timeline' }),
          scale: defaultOptions.scale || getOptimalScale(),
        };

        // Export to data URL
        const result = await exportAsImage(element, exportOptions, handleProgress);

        // Check if aborted
        if (exportRef.current.aborted) {
          return result;
        }

        // Notify success
        onExportSuccess?.({
          filename: result.filename,
          width: result.width,
          height: result.height,
        });

        return result;
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Export failed');
        setExportError(err);
        onExportError?.(err);
        throw err;
      } finally {
        setIsExporting(false);
        setExportStep('complete');
        exportRef.current = null;
      }
    },
    [enabled, defaultOptions, onExportStart, onExportSuccess, onExportError, handleProgress, t]
  );

  /**
   * Copy timeline to clipboard
   */
  const copyToClipboard = useCallback(
    async (element: HTMLElement) => {
      if (!enabled) {
        throw new Error('Export functionality is disabled');
      }

      if (!isClipboardAvailable()) {
        throw new Error('Clipboard API is not available in this browser');
      }

      // Reset state
      setIsExporting(true);
      setExportProgress(0);
      setExportStep('preparing');
      setExportError(null);

      // Create export tracker
      exportRef.current = { aborted: false };

      try {
        // Notify start
        onExportStart?.();

        // Generate export options (without filename)
        const exportOptions: Partial<Omit<TimelineExportOptions, 'filename'>> = {
          ...defaultOptions,
          scale: defaultOptions.scale || getOptimalScale(),
        };

        // Copy to clipboard
        await copyImageToClipboard(element, exportOptions, handleProgress);

        // Check if aborted
        if (exportRef.current.aborted) {
          return;
        }

        // Notify success (without filename for clipboard)
        onExportSuccess?.({
          filename: t('export.clipboardFilename', { defaultValue: 'clipboard' }),
          width: 0,
          height: 0,
        });
      } catch (error) {
        const err = error instanceof Error ? error : new Error('Copy to clipboard failed');
        setExportError(err);
        onExportError?.(err);
        throw err;
      } finally {
        setIsExporting(false);
        setExportStep('complete');
        exportRef.current = null;
      }
    },
    [enabled, defaultOptions, onExportStart, onExportSuccess, onExportError, handleProgress, t]
  );

  return {
    exportAndDownload,
    exportToDataUrl,
    copyToClipboard,
    isExporting,
    exportProgress,
    exportStep,
    canCopyToClipboard: isClipboardAvailable(),
    exportError,
    clearError,
  };
}
