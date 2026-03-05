/**
 * Timeline export utilities for generating PNG images
 *
 * Provides functions to capture timeline visualization as downloadable images
 * using html2canvas for rendering DOM elements to canvas.
 */

import html2canvas from 'html2canvas';
import type { TimelineExportOptions } from '../types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExportResult {
  /** Data URL of the exported image */
  dataUrl: string;
  /** Blob of the exported image */
  blob: Blob;
  /** Width of the exported image in pixels */
  width: number;
  /** Height of the exported image in pixels */
  height: number;
}

export interface ExportProgress {
  /** Current progress percentage (0-100) */
  progress: number;
  /** Current step in the export process */
  step: 'preparing' | 'rendering' | 'processing' | 'complete';
}

// ---------------------------------------------------------------------------
// Default Options
// ---------------------------------------------------------------------------

const DEFAULT_EXPORT_OPTIONS: Required<TimelineExportOptions> = {
  format: 'png',
  scale: 2,
  backgroundColor: '#ffffff',
  includeDetails: false,
  filename: 'timeline',
};

// ---------------------------------------------------------------------------
// Helper Functions
// ---------------------------------------------------------------------------

/**
 * Generate timestamp for filename
 */
function getTimestamp(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');

  return `${year}${month}${day}-${hours}${minutes}${seconds}`;
}

/**
 * Generate filename with timestamp
 */
function generateFilename(baseFilename: string, format: 'png' | 'svg'): string {
  const timestamp = getTimestamp();
  const extension = format === 'png' ? 'png' : 'svg';
  return `${baseFilename}-${timestamp}.${extension}`;
}

/**
 * Convert canvas to blob with error handling
 */
async function canvasToBlob(
  canvas: HTMLCanvasElement,
  type: string = 'image/png'
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error('Failed to convert canvas to blob'));
        }
      },
      type,
      1.0
    );
  });
}

// ---------------------------------------------------------------------------
// Export Functions
// ---------------------------------------------------------------------------

/**
 * Capture a DOM element as an image using html2canvas
 *
 * @param element - The DOM element to capture
 * @param options - Export options
 * @param onProgress - Optional progress callback
 * @returns Promise resolving to export result with data URL and blob
 *
 * @example
 * ```tsx
 * const elementRef = useRef<HTMLDivElement>(null);
 *
 * const handleExport = async () => {
 *   if (!elementRef.current) return;
 *
 *   try {
 *     const result = await exportAsImage(elementRef.current, {
 *       format: 'png',
 *       scale: 2,
 *       filename: 'my-timeline'
 *     });
 *
 *     // Download the image
 *     downloadImage(result.dataUrl, result.filename);
 *   } catch (error) {
 *     console.error('Export failed:', error);
 *   }
 * };
 * ```
 */
export async function exportAsImage(
  element: HTMLElement,
  options: Partial<TimelineExportOptions> = {},
  onProgress?: (progress: ExportProgress) => void
): Promise<ExportResult & { filename: string }> {
  // Merge options with defaults
  const config: Required<TimelineExportOptions> = {
    ...DEFAULT_EXPORT_OPTIONS,
    ...options,
  };

  // Notify progress: preparing
  onProgress?.({ progress: 10, step: 'preparing' });

  try {
    // Notify progress: rendering
    onProgress?.({ progress: 30, step: 'rendering' });

    // Configure html2canvas options
    const canvasOptions: html2canvas.Options = {
      scale: config.scale,
      backgroundColor: config.backgroundColor,
      logging: false,
      useCORS: true,
      allowTaint: true,
      // Exclude interactive elements from export
      ignoreElements: (element) => {
        const className = element.className;
        if (typeof className === 'string') {
          // Exclude zoom controls and pan buttons
          return (
            className.includes('zoom-controls') ||
            className.includes('pan-controls') ||
            className.includes('cursor-hint')
          );
        }
        return false;
      },
    };

    // Capture the element
    const canvas = await html2canvas(element, canvasOptions);

    // Notify progress: processing
    onProgress?.({ progress: 70, step: 'processing' });

    // Convert to blob
    const blob = await canvasToBlob(canvas, 'image/png');

    // Get data URL
    const dataUrl = canvas.toDataURL('image/png', 1.0);

    // Generate filename
    const filename = generateFilename(config.filename, config.format);

    // Notify progress: complete
    onProgress?.({ progress: 100, step: 'complete' });

    return {
      dataUrl,
      blob,
      width: canvas.width,
      height: canvas.height,
      filename,
    };
  } catch (error) {
    throw new Error(
      `Failed to export timeline as image: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Download an image from data URL
 *
 * @param dataUrl - Data URL of the image to download
 * @param filename - Filename for the downloaded file
 *
 * @example
 * ```tsx
 * const handleDownload = async () => {
 *   const result = await exportAsImage(elementRef.current);
 *   downloadImage(result.dataUrl, result.filename);
 * };
 * ```
 */
export function downloadImage(dataUrl: string, filename: string): void {
  try {
    // Create a temporary link element
    const link = document.createElement('a');
    link.href = dataUrl;
    link.download = filename;

    // Append to document, click, and remove
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Revoke the object URL to free memory
    if (link.href.startsWith('blob:')) {
      URL.revokeObjectURL(link.href);
    }
  } catch (error) {
    throw new Error(
      `Failed to download image: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Export and download timeline image in one step
 *
 * @param element - The DOM element to capture
 * @param options - Export options
 * @param onProgress - Optional progress callback
 * @returns Promise resolving when download is complete
 *
 * @example
 * ```tsx
 * const elementRef = useRef<HTMLDivElement>(null);
 *
 * const handleExportAndDownload = async () => {
 *   if (!elementRef.current) return;
 *
 *   try {
 *     await exportAndDownloadImage(elementRef.current, {
 *       filename: 'my-timeline'
 *     });
 *     console.log('Timeline exported successfully!');
 *   } catch (error) {
 *     console.error('Export failed:', error);
 *   }
 * };
 * ```
 */
export async function exportAndDownloadImage(
  element: HTMLElement,
  options: Partial<TimelineExportOptions> = {},
  onProgress?: (progress: ExportProgress) => void
): Promise<void> {
  const result = await exportAsImage(element, options, onProgress);
  downloadImage(result.dataUrl, result.filename);
}

/**
 * Copy image to clipboard
 *
 * @param element - The DOM element to capture
 * @param options - Export options (without filename)
 * @returns Promise resolving when image is copied to clipboard
 *
 * @example
 * ```tsx
 * const handleCopyToClipboard = async () => {
 *   if (!elementRef.current) return;
 *
 *   try {
 *     await copyImageToClipboard(elementRef.current);
 *     console.log('Timeline copied to clipboard!');
 *   } catch (error) {
 *     console.error('Copy failed:', error);
 *   }
 * };
 * ```
 */
export async function copyImageToClipboard(
  element: HTMLElement,
  options: Partial<Omit<TimelineExportOptions, 'filename'>> = {},
  onProgress?: (progress: ExportProgress) => void
): Promise<void> {
  // Merge options with defaults (without filename)
  const config: Required<TimelineExportOptions> = {
    ...DEFAULT_EXPORT_OPTIONS,
    ...options,
    filename: DEFAULT_EXPORT_OPTIONS.filename, // Ignore filename for clipboard
  };

  try {
    const result = await exportAsImage(element, config, onProgress);

    // Convert blob to ClipboardItem
    const clipboardItem = new ClipboardItem({
      'image/png': result.blob,
    });

    // Write to clipboard
    await navigator.clipboard.write([clipboardItem]);
  } catch (error) {
    throw new Error(
      `Failed to copy image to clipboard: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Check if clipboard API is available
 */
export function isClipboardAvailable(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    'clipboard' in navigator &&
    'write' in navigator.clipboard &&
    'ClipboardItem' in window
  );
}

/**
 * Get optimal scale for export based on device pixel ratio
 *
 * @param maxScale - Maximum scale to use (default: 3)
 * @returns Optimal scale factor
 */
export function getOptimalScale(maxScale: number = 3): number {
  const dpr = window.devicePixelRatio || 1;
  return Math.min(Math.ceil(dpr), maxScale);
}
