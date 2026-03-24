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

        // Single export pass: render, then download
        const result = await exportAsImage(element, exportOptions, handleProgress);

        // Check if aborted
        if (exportRef.current.aborted) {
          return;
        }

        // Download the image
        downloadImage(result.dataUrl, result.filename);

        // Notify success
        onExportSuccess?.({
          filename: result.filename,
          width: result.width,
          height: result.height,
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

        // Render image first to get dimensions, then copy blob to clipboard
        const result = await exportAsImage(element, exportOptions, handleProgress);

        // Copy to clipboard using the rendered blob
        const clipboardItem = new ClipboardItem({ 'image/png': result.blob });
        await navigator.clipboard.write([clipboardItem]);

        // Check if aborted
        if (exportRef.current.aborted) {
          return;
        }

        // Notify success with actual dimensions
        onExportSuccess?.({
          filename: t('export.clipboardFilename', { defaultValue: 'clipboard' }),
          width: result.width,
          height: result.height,
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
