/**
 * Annotation types for UX feedback loop feature
 * @see spec.md for complete feature documentation
 */

/**
 * Coordinate bounds for annotation selection
 */
export interface AnnotationCoordinates {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Viewport size at time of annotation
 */
export interface ViewportSize {
  width: number;
  height: number;
}

/**
 * Severity levels for annotations
 */
export type AnnotationSeverity = 'low' | 'medium' | 'high' | 'critical';

/**
 * Complete annotation data structure
 * Captures UI feedback with screenshot, coordinates, and metadata
 */
export interface Annotation {
  /** Unique identifier (UUID) */
  id: string;
  /** ISO 8601 timestamp */
  timestamp: string;
  /** Base64 encoded PNG screenshot */
  screenshot: string;
  /** Bounding box coordinates */
  coordinates: AnnotationCoordinates;
  /** User-provided issue description */
  description: string;
  /** Severity level */
  severity: AnnotationSeverity;
  /** Auto-detected component name (optional) */
  component?: string;
  /** Current route/page (optional) */
  route?: string;
  /** Viewport dimensions at capture time */
  viewportSize: ViewportSize;
}

/**
 * Props for annotation overlay component
 */
export interface AnnotationOverlayProps {
  /** Callback when annotation is submitted */
  onAnnotationSubmit: (annotation: Annotation) => void;
  /** Current route/page context */
  currentRoute?: string;
}

/**
 * Props for annotation form component
 */
export interface AnnotationFormProps {
  /** Coordinates of selected area */
  coordinates: AnnotationCoordinates;
  /** Captured screenshot */
  screenshot: string;
  /** Callback on form submit */
  onSubmit: (data: Omit<Annotation, 'id' | 'timestamp' | 'screenshot' | 'coordinates' | 'viewportSize'>) => void;
  /** Callback on cancel */
  onCancel: () => void;
}
