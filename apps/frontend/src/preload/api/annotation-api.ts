/**
 * Annotation API
 *
 * Provides annotation functionality for visual UX feedback loop.
 * Allows developers to annotate UI defects and gaps directly on the running prototype.
 * Annotations can be automatically converted into actionable tasks/specs.
 */
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { ipcRenderer } from 'electron';
import type {
  Annotation,
  AnnotationCreatePayload,
  AnnotationDeletePayload,
  AnnotationListPayload,
  AnnotationSubmissionResult,
  AnnotationViewport
} from '../../shared/types/annotation';

/**
 * Annotation creation request
 */
export interface AnnotationCreateRequest {
  /** Project ID for the annotation */
  projectId: string;
  /** Annotation data */
  payload: AnnotationCreatePayload;
  /** Viewport dimensions at time of annotation */
  viewportSize: AnnotationViewport;
  /** Auto-detected component name (optional) */
  component?: string;
}

/**
 * Annotation submission request (with optional spec creation)
 */
export interface AnnotationSubmitRequest extends AnnotationCreateRequest {
  /** Whether to create a spec from this annotation */
  createSpec?: boolean;
}

/**
 * Annotation list request
 */
export interface AnnotationListRequest {
  /** Optional filter by status */
  status?: string;
  /** Optional filter by route */
  route?: string;
}

/**
 * Annotation delete request
 */
export interface AnnotationDeleteRequest {
  /** Project ID for the annotation */
  projectId: string;
  /** Delete payload with annotation ID */
  payload: AnnotationDeletePayload;
  /** Whether to also delete the generated spec */
  deleteSpec?: boolean;
}

/**
 * Annotation API interface
 */
export interface AnnotationAPI {
  /** Create a new annotation (without spec creation) */
  createAnnotation: (request: AnnotationCreateRequest) => Promise<{
    success: boolean;
    data?: AnnotationSubmissionResult;
    error?: string;
  }>;

  /** Submit an annotation (optionally with spec creation) */
  submitAnnotation: (request: AnnotationSubmitRequest) => Promise<{
    success: boolean;
    data?: AnnotationSubmissionResult;
    error?: string;
  }>;

  /** Get a single annotation by ID */
  getAnnotation: (annotationId: string) => Promise<{
    success: boolean;
    data?: Annotation;
    error?: string;
  }>;

  /** List annotations with optional filtering */
  listAnnotations: (request?: AnnotationListRequest) => Promise<{
    success: boolean;
    data?: Annotation[];
    error?: string;
  }>;

  /** Delete an annotation by ID */
  deleteAnnotation: (request: AnnotationDeleteRequest) => Promise<{
    success: boolean;
    error?: string;
  }>;
}

/**
 * Validate annotation create request
 */
function validateAnnotationRequest(request: AnnotationCreateRequest): string[] {
  const errors: string[] = [];

  if (!request.projectId || request.projectId.trim() === '') {
    errors.push('Project ID is required');
  }

  if (!request.payload) {
    errors.push('Payload is required');
    return errors;
  }

  const { payload } = request;

  if (!payload.description || payload.description.trim() === '') {
    errors.push('Description is required');
  }

  if (payload.description && payload.description.length < 10) {
    errors.push('Description must be at least 10 characters');
  }

  if (!payload.screenshot || payload.screenshot.trim() === '') {
    errors.push('Screenshot is required');
  }

  if (!payload.coordinates) {
    errors.push('Coordinates are required');
  } else {
    const { x, y, width, height } = payload.coordinates;
    if (typeof x !== 'number' || typeof y !== 'number' ||
        typeof width !== 'number' || typeof height !== 'number') {
      errors.push('Coordinates must be valid numbers');
    }

    if (width <= 0 || height <= 0) {
      errors.push('Coordinates must have positive width and height');
    }
  }

  if (!payload.severity || !['low', 'medium', 'high', 'critical'].includes(payload.severity)) {
    errors.push('Severity must be one of: low, medium, high, critical');
  }

  return errors;
}

/**
 * Sanitize and cap field lengths to prevent large payloads
 */
function sanitizeAnnotationRequest(request: AnnotationCreateRequest): AnnotationCreateRequest {
  return {
    projectId: request.projectId.trim().slice(0, 128),
    payload: {
      screenshot: request.payload.screenshot.slice(0, 5000000), // Max 5MB for base64 screenshot
      coordinates: request.payload.coordinates,
      description: request.payload.description.trim().slice(0, 2048),
      severity: request.payload.severity,
      route: request.payload.route?.trim().slice(0, 256)
    },
    viewportSize: request.viewportSize,
    component: request.component?.trim().slice(0, 128)
  };
}

/**
 * Create the annotation API
 */
export const createAnnotationAPI = (): AnnotationAPI => ({
  createAnnotation: (rawRequest) => {
    // Validate request
    const validationErrors = validateAnnotationRequest(rawRequest);
    if (validationErrors.length > 0) {
      return Promise.resolve({
        success: false,
        error: validationErrors.join('; ')
      });
    }

    // Sanitize request
    const request = sanitizeAnnotationRequest(rawRequest);

    // Call IPC handler without spec creation
    return ipcRenderer.invoke(
      IPC_CHANNELS.ANNOTATION_SUBMIT,
      request.projectId,
      request.payload,
      request.viewportSize,
      request.component,
      false // Don't create spec
    );
  },

  submitAnnotation: (rawRequest) => {
    // Validate request
    const validationErrors = validateAnnotationRequest(rawRequest);
    if (validationErrors.length > 0) {
      return Promise.resolve({
        success: false,
        error: validationErrors.join('; ')
      });
    }

    // Sanitize request
    const request = sanitizeAnnotationRequest(rawRequest);

    // Call IPC handler with optional spec creation
    return ipcRenderer.invoke(
      IPC_CHANNELS.ANNOTATION_SUBMIT,
      request.projectId,
      request.payload,
      request.viewportSize,
      request.component,
      rawRequest.createSpec ?? false // Default to false
    );
  },

  getAnnotation: (annotationId) => {
    if (!annotationId || annotationId.trim() === '') {
      return Promise.resolve({
        success: false,
        error: 'Annotation ID is required'
      });
    }

    return ipcRenderer.invoke(IPC_CHANNELS.ANNOTATION_GET, annotationId.trim());
  },

  listAnnotations: (request) => {
    const payload: AnnotationListPayload = {};

    if (request?.status) {
      payload.status = request.status as any;
    }

    if (request?.route) {
      payload.route = request.route.trim().slice(0, 256);
    }

    return ipcRenderer.invoke(IPC_CHANNELS.ANNOTATION_LIST, payload);
  },

  deleteAnnotation: (rawRequest) => {
    if (!rawRequest.projectId || rawRequest.projectId.trim() === '') {
      return Promise.resolve({
        success: false,
        error: 'Project ID is required'
      });
    }

    if (!rawRequest.payload?.id || rawRequest.payload.id.trim() === '') {
      return Promise.resolve({
        success: false,
        error: 'Annotation ID is required'
      });
    }

    const request: AnnotationDeleteRequest = {
      projectId: rawRequest.projectId.trim().slice(0, 128),
      payload: {
        id: rawRequest.payload.id.trim()
      },
      deleteSpec: rawRequest.deleteSpec ?? false
    };

    return ipcRenderer.invoke(
      IPC_CHANNELS.ANNOTATION_DELETE,
      request.projectId,
      request.payload,
      request.deleteSpec
    );
  }
});
