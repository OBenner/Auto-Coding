/**
 * Annotation-related types
 *
 * Types for the visual UX feedback loop annotation system.
 * Allows developers to annotate UI defects and gaps directly on the running prototype,
 * with annotations automatically converted into actionable tasks/specs.
 */

import type { IPCResult } from './common';

/**
 * Severity level for an annotation
 * - 'low': Minor visual or UX issue, nice to have fix
 * - 'medium': Noticeable problem affecting some users
 * - 'high': Significant issue affecting many users or core functionality
 * - 'critical': Blocking issue that prevents core feature usage
 */
export type AnnotationSeverity = 'low' | 'medium' | 'high' | 'critical';

/**
 * Status of an annotation in the workflow
 * - 'draft': Annotation created but not yet submitted
 * - 'submitted': Annotation submitted for spec creation
 * - 'processing': Spec is being generated from annotation
 * - 'completed': Spec successfully created from annotation
 * - 'failed': Spec creation failed
 */
export type AnnotationStatus = 'draft' | 'submitted' | 'processing' | 'completed' | 'failed';

/**
 * Screen coordinates for the annotated area
 */
export interface AnnotationCoordinates {
  /** X position in pixels from left edge */
  x: number;
  /** Y position in pixels from top edge */
  y: number;
  /** Width of annotated area in pixels */
  width: number;
  /** Height of annotated area in pixels */
  height: number;
}

/**
 * Viewport size at time of annotation
 * Useful for responsive design context
 */
export interface AnnotationViewport {
  /** Total viewport width in pixels */
  width: number;
  /** Total viewport height in pixels */
  height: number;
  /** Device pixel ratio (for high-DPI displays) */
  devicePixelRatio?: number;
}

/**
 * Main annotation data structure
 * Represents a single visual annotation created by the user
 */
export interface Annotation {
  /** Unique identifier (UUID) */
  id: string;
  /** ISO 8601 timestamp when annotation was created */
  timestamp: string;
  /** Base64 encoded PNG screenshot of the annotated area */
  screenshot: string;
  /** Coordinates defining the annotated screen region */
  coordinates: AnnotationCoordinates;
  /** User-provided description of the issue */
  description: string;
  /** Severity level of the issue */
  severity: AnnotationSeverity;
  /** Auto-detected component name (if available) */
  component?: string;
  /** Current route/page path (e.g., '/settings/profile') */
  route?: string;
  /** Viewport dimensions at time of annotation */
  viewportSize: AnnotationViewport;
  /** Current workflow status */
  status: AnnotationStatus;
  /** ID of the generated spec (if created) */
  specId?: string;
  /** Error message if spec creation failed */
  error?: string;
}

/**
 * Summary representation of an annotation (for list views)
 */
export interface AnnotationSummary {
  id: string;
  timestamp: string;
  description: string;
  severity: AnnotationSeverity;
  status: AnnotationStatus;
  component?: string;
  route?: string;
}

/**
 * Form data for creating a new annotation
 */
export interface AnnotationFormData {
  /** User-provided description of the issue */
  description: string;
  /** Severity level of the issue */
  severity: AnnotationSeverity;
}

/**
 * Result of annotation submission
 */
export interface AnnotationSubmissionResult {
  /** The annotation that was submitted */
  annotation: Annotation;
  /** ID of the created spec */
  specId: string;
  /** Path to the spec directory */
  specPath: string;
}

/**
 * IPC payload for creating an annotation
 */
export interface AnnotationCreatePayload {
  /** Screenshot as base64 encoded PNG */
  screenshot: string;
  /** Coordinates of annotated area */
  coordinates: AnnotationCoordinates;
  /** User-provided description */
  description: string;
  /** Severity level */
  severity: AnnotationSeverity;
  /** Current route (optional) */
  route?: string;
}

/**
 * IPC payload for listing annotations
 */
export interface AnnotationListPayload {
  /** Optional filter by status */
  status?: AnnotationStatus;
  /** Optional filter by route */
  route?: string;
}

/**
 * IPC payload for deleting an annotation
 */
export interface AnnotationDeletePayload {
  /** ID of annotation to delete */
  id: string;
}

/**
 * IPC result types for annotation operations
 */
export type AnnotationCreateResult = IPCResult<AnnotationSubmissionResult>;
export type AnnotationListResult = IPCResult<Annotation[]>;
export type AnnotationDeleteResult = IPCResult<void>;

/**
 * Spec generation options for annotation-to-spec conversion
 */
export interface AnnotationSpecOptions {
  /** Custom title for the generated spec */
  title?: string;
  /** Custom description for the spec */
  description?: string;
  /** Whether to include the screenshot in the spec */
  includeScreenshot?: boolean;
  /** Priority level for the generated task */
  priority?: 'low' | 'medium' | 'high';
}

/**
 * Statistics about annotations in the current session
 */
export interface AnnotationStats {
  /** Total number of annotations */
  total: number;
  /** Count by severity level */
  bySeverity: Record<AnnotationSeverity, number>;
  /** Count by status */
  byStatus: Record<AnnotationStatus, number>;
  /** Number of annotations that generated specs successfully */
  specsGenerated: number;
  /** Number of annotations that failed to generate specs */
  specsFailed: number;
}
