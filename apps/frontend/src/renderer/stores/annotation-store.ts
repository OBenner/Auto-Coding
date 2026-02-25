import { create } from 'zustand';
import type {
  Annotation,
  AnnotationFormData,
  AnnotationCoordinates,
  AnnotationSeverity,
  AnnotationViewport
} from '../../shared/types/annotation';

// ============================================
// Types
// ============================================

/**
 * Draft annotation data (incomplete, being created)
 */
export interface DraftAnnotation {
  /** Temporary ID while creating */
  id: string;
  /** Screenshot as base64 encoded PNG */
  screenshot: string;
  /** Coordinates of annotated area */
  coordinates: AnnotationCoordinates;
  /** Viewport dimensions at time of annotation */
  viewportSize: AnnotationViewport;
  /** Current route/page path */
  route?: string;
  /** Auto-detected component name (if available) */
  component?: string;
}

/**
 * Annotation store state
 */
interface AnnotationState {
  /** Whether annotation mode is currently active */
  isAnnotationMode: boolean;
  /** All annotations in current session */
  annotations: Annotation[];
  /** Current draft annotation (being filled in form) */
  draftAnnotation: DraftAnnotation | null;

  // Actions
  /** Toggle annotation mode on/off */
  toggleAnnotationMode: () => void;
  /** Set annotation mode explicitly */
  setAnnotationMode: (enabled: boolean) => void;
  /** Create a new draft annotation from selection */
  createDraftAnnotation: (
    screenshot: string,
    coordinates: AnnotationCoordinates,
    viewportSize: AnnotationViewport,
    route?: string,
    component?: string
  ) => void;
  /** Submit draft annotation with form data */
  submitDraftAnnotation: (formData: AnnotationFormData) => Annotation | null;
  /** Cancel/discard current draft annotation */
  cancelDraftAnnotation: () => void;
  /** Add a completed annotation to the store */
  addAnnotation: (annotation: Annotation) => void;
  /** Update an existing annotation */
  updateAnnotation: (id: string, updates: Partial<Annotation>) => void;
  /** Delete an annotation by ID */
  deleteAnnotation: (id: string) => void;
  /** Clear all annotations */
  clearAnnotations: () => void;
  /** Get annotation by ID */
  getAnnotation: (id: string) => Annotation | undefined;
  /** Get annotations count by status */
  getAnnotationsCountByStatus: () => Record<string, number>;
  /** Get annotations count by severity */
  getAnnotationsCountBySeverity: () => Record<AnnotationSeverity, number>;
}

// ============================================
// Constants
// ============================================

/** localStorage key for annotation mode persistence */
const ANNOTATION_MODE_KEY = 'annotation-mode-enabled';

/** localStorage key prefix for annotations persistence */
const ANNOTATIONS_KEY_PREFIX = 'annotations-session-';

// ============================================
// Helper Functions
// ============================================

/**
 * Generate a unique ID for an annotation
 */
function generateAnnotationId(): string {
  return `annotation-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Get the localStorage key for the current session's annotations
 */
function getAnnotationsSessionKey(): string {
  // Use a session-based key (resets on app restart)
  return `${ANNOTATIONS_KEY_PREFIX}${new Date().toISOString().split('T')[0]}`;
}

/**
 * Create an Annotation from draft data and form data
 */
function createAnnotationFromDraft(
  draft: DraftAnnotation,
  formData: AnnotationFormData
): Annotation {
  return {
    id: generateAnnotationId(),
    timestamp: new Date().toISOString(),
    screenshot: draft.screenshot,
    coordinates: draft.coordinates,
    viewportSize: draft.viewportSize,
    route: draft.route,
    component: draft.component,
    description: formData.description,
    severity: formData.severity,
    status: 'draft'
  };
}

/**
 * Validate annotation coordinates
 */
function validateCoordinates(coords: AnnotationCoordinates): boolean {
  return (
    coords.x >= 0 &&
    coords.y >= 0 &&
    coords.width > 0 &&
    coords.height > 0
  );
}

// ============================================
// Store
// ============================================

export const useAnnotationStore = create<AnnotationState>((set, get) => ({
  isAnnotationMode: false,
  annotations: [],
  draftAnnotation: null,

  toggleAnnotationMode: () => {
    set((state) => {
      const newMode = !state.isAnnotationMode;

      // Persist to localStorage
      try {
        localStorage.setItem(ANNOTATION_MODE_KEY, String(newMode));
      } catch {
        // Silently fail if localStorage unavailable
      }

      return { isAnnotationMode: newMode };
    });
  },

  setAnnotationMode: (enabled) => {
    set(() => {
      // Persist to localStorage
      try {
        localStorage.setItem(ANNOTATION_MODE_KEY, String(enabled));
      } catch {
        // Silently fail if localStorage unavailable
      }

      return { isAnnotationMode: enabled };
    });
  },

  createDraftAnnotation: (screenshot, coordinates, viewportSize, route, component) => {
    // Validate coordinates before creating draft
    if (!validateCoordinates(coordinates)) {
      console.warn('[AnnotationStore] Invalid coordinates for draft annotation');
      return;
    }

    set({
      draftAnnotation: {
        id: generateAnnotationId(),
        screenshot,
        coordinates,
        viewportSize,
        route,
        component
      }
    });
  },

  submitDraftAnnotation: (formData) => {
    const state = get();

    if (!state.draftAnnotation) {
      console.warn('[AnnotationStore] No draft annotation to submit');
      return null;
    }

    // Validate form data
    if (!formData.description || formData.description.trim().length < 10) {
      console.warn('[AnnotationStore] Description too short (min 10 characters)');
      return null;
    }

    const annotation = createAnnotationFromDraft(state.draftAnnotation, formData);

    // Add to annotations array
    set((state) => ({
      annotations: [...state.annotations, annotation],
      draftAnnotation: null
    }));

    return annotation;
  },

  cancelDraftAnnotation: () => {
    set({ draftAnnotation: null });
  },

  addAnnotation: (annotation) => {
    set((state) => ({
      annotations: [...state.annotations, annotation]
    }));
  },

  updateAnnotation: (id, updates) => {
    set((state) => ({
      annotations: state.annotations.map((ann) =>
        ann.id === id ? { ...ann, ...updates } : ann
      )
    }));
  },

  deleteAnnotation: (id) => {
    set((state) => ({
      annotations: state.annotations.filter((ann) => ann.id !== id)
    }));
  },

  clearAnnotations: () => {
    set({ annotations: [] });

    // Also clear from localStorage
    try {
      const key = getAnnotationsSessionKey();
      localStorage.removeItem(key);
    } catch {
      // Silently fail if localStorage unavailable
    }
  },

  getAnnotation: (id) => {
    const state = get();
    return state.annotations.find((ann) => ann.id === id);
  },

  getAnnotationsCountByStatus: () => {
    const state = get();
    const counts: Record<string, number> = {};

    for (const ann of state.annotations) {
      counts[ann.status] = (counts[ann.status] || 0) + 1;
    }

    return counts;
  },

  getAnnotationsCountBySeverity: () => {
    const state = get();
    const counts: Record<AnnotationSeverity, number> = {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0
    };

    for (const ann of state.annotations) {
      counts[ann.severity]++;
    }

    return counts;
  }
}));
