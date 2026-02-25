/**
 * Annotation IPC Handlers
 *
 * Handles IPC requests for annotation operations including create, list, get, and delete.
 * Annotations are visual UX feedback captured during prototype development.
 *
 * Storage: Annotations are persisted to a JSON file in the app's userData directory.
 */

import { ipcMain, app } from 'electron';
import * as path from 'path';
import { promises as fsPromises } from 'fs';
import { v4 as uuidv4 } from 'uuid';
import type { BrowserWindow } from 'electron';

import { IPC_CHANNELS } from '../../shared/constants';
import type {
  Annotation,
  AnnotationCreatePayload,
  AnnotationDeletePayload,
  AnnotationListPayload,
  AnnotationSubmissionResult
} from '../../shared/types/annotation';
import type { IPCResult } from '../../shared/types';
import { annotationToSpecService } from '../services/annotation-to-spec-service';
import { appLog } from '../app-logger';

/**
 * Get the annotations storage file path
 * Uses userData directory for app-specific data persistence
 */
function getAnnotationsPath(): string {
  const userDataPath = app.getPath('userData');
  return path.join(userDataPath, 'annotations.json');
}

/**
 * Load all annotations from storage
 * Returns empty array if file doesn't exist or is invalid
 */
async function loadAnnotations(): Promise<Annotation[]> {
  const annotationsPath = getAnnotationsPath();

  try {
    await fsPromises.access(annotationsPath);
    const content = await fsPromises.readFile(annotationsPath, 'utf-8');
    const annotations = JSON.parse(content);

    // Validate array structure
    if (!Array.isArray(annotations)) {
      appLog.error('[Annotations] Invalid storage format: expected array');
      return [];
    }

    return annotations as Annotation[];
  } catch (error) {
    // File doesn't exist or is invalid - return empty array
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
      appLog.error('[Annotations] Failed to load annotations:', error);
    }
    return [];
  }
}

/**
 * Save annotations to storage
 */
async function saveAnnotationsToFile(annotations: Annotation[]): Promise<void> {
  const annotationsPath = getAnnotationsPath();
  await fsPromises.writeFile(annotationsPath, JSON.stringify(annotations, null, 2), 'utf-8');
}

/**
 * Validate annotation create payload
 * Returns array of validation error messages (empty if valid)
 */
function validateAnnotationPayload(payload: AnnotationCreatePayload): string[] {
  const errors: string[] = [];

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
 * Create an annotation from capture data and viewport info
 * Adds metadata like ID, timestamp, viewport size, and component detection
 */
function createAnnotationFromPayload(
  payload: AnnotationCreatePayload,
  viewportSize: { width: number; height: number; devicePixelRatio?: number },
  component?: string
): Annotation {
  const now = new Date().toISOString();

  return {
    id: uuidv4(),
    timestamp: now,
    screenshot: payload.screenshot,
    coordinates: payload.coordinates,
    description: payload.description,
    severity: payload.severity,
    component,
    route: payload.route,
    viewportSize,
    status: 'draft'
  };
}

/**
 * Register all annotation-related IPC handlers
 *
 * @param getMainWindow - Function to get the main BrowserWindow
 */
export function registerAnnotationHandlers(
  getMainWindow: () => BrowserWindow | null
): void {
  /**
   * Submit an annotation and optionally create a spec from it
   */
  ipcMain.handle(
    IPC_CHANNELS.ANNOTATION_SUBMIT,
    async (
      _event,
      projectId: string,
      payload: AnnotationCreatePayload,
      viewportSize: { width: number; height: number; devicePixelRatio?: number },
      component?: string,
      createSpec?: boolean
    ): Promise<IPCResult<AnnotationSubmissionResult>> => {
      try {
        appLog.log('[Annotation] Submitting annotation:', payload.description.substring(0, 50));

        // Validate payload
        const validationErrors = validateAnnotationPayload(payload);
        if (validationErrors.length > 0) {
          return {
            success: false,
            error: validationErrors.join('; ')
          };
        }

        // Create annotation object
        const annotation = createAnnotationFromPayload(payload, viewportSize, component);

        // Get project path from project store
        const { projectStore } = await import('../project-store');
        const project = projectStore.getProject(projectId);

        if (!project) {
          return {
            success: false,
            error: 'Project not found'
          };
        }

        // Save annotation to storage
        const annotations = await loadAnnotations();
        annotations.push(annotation);
        await saveAnnotationsToFile(annotations);

        appLog.log('[Annotation] Saved annotation:', annotation.id);

        // If spec creation requested, use AnnotationToSpecService
        if (createSpec) {
          try {
            annotation.status = 'processing';

            const result = await annotationToSpecService.createSpecFromAnnotation(
              project.path,
              annotation
            );

            appLog.log('[Annotation] Created spec:', result.specId);
            return { success: true, data: result };
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            appLog.error('[Annotation] Failed to create spec:', error);

            // Update annotation status to failed
            const annotations = await loadAnnotations();
            const index = annotations.findIndex(a => a.id === annotation.id);
            if (index !== -1) {
              annotations[index].status = 'failed';
              annotations[index].error = errorMessage;
              await saveAnnotationsToFile(annotations);
            }

            return {
              success: false,
              error: `Failed to create spec: ${errorMessage}`
            };
          }
        }

        // Return annotation without spec creation
        return {
          success: true,
          data: {
            annotation,
            specId: '',
            specPath: ''
          }
        };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        appLog.error('[Annotation] Submit failed:', error);
        return {
          success: false,
          error: errorMessage
        };
      }
    }
  );

  /**
   * Get a single annotation by ID
   */
  ipcMain.handle(
    IPC_CHANNELS.ANNOTATION_GET,
    async (_event, annotationId: string): Promise<IPCResult<Annotation>> => {
      try {
        appLog.log('[Annotation] Getting annotation:', annotationId);

        const annotations = await loadAnnotations();
        const annotation = annotations.find(a => a.id === annotationId);

        if (!annotation) {
          return {
            success: false,
            error: `Annotation not found: ${annotationId}`
          };
        }

        return { success: true, data: annotation };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        appLog.error('[Annotation] Get failed:', error);
        return {
          success: false,
          error: errorMessage
        };
      }
    }
  );

  /**
   * List annotations with optional filtering
   */
  ipcMain.handle(
    IPC_CHANNELS.ANNOTATION_LIST,
    async (_event, payload?: AnnotationListPayload): Promise<IPCResult<Annotation[]>> => {
      try {
        appLog.log('[Annotation] Listing annotations:', payload);

        let annotations = await loadAnnotations();

        // Apply status filter if provided
        if (payload?.status) {
          annotations = annotations.filter(a => a.status === payload.status);
        }

        // Apply route filter if provided
        if (payload?.route) {
          annotations = annotations.filter(a => a.route === payload.route);
        }

        // Sort by timestamp descending (newest first)
        annotations.sort((a, b) => b.timestamp.localeCompare(a.timestamp));

        appLog.log('[Annotation] Returning', annotations.length, 'annotations');
        return { success: true, data: annotations };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        appLog.error('[Annotation] List failed:', error);
        return {
          success: false,
          error: errorMessage
        };
      }
    }
  );

  /**
   * Delete an annotation by ID
   * Optionally deletes the generated spec folder as well
   */
  ipcMain.handle(
    IPC_CHANNELS.ANNOTATION_DELETE,
    async (
      _event,
      projectId: string,
      payload: AnnotationDeletePayload,
      deleteSpec?: boolean
    ): Promise<IPCResult<void>> => {
      try {
        appLog.log('[Annotation] Deleting annotation:', payload.id);

        const annotations = await loadAnnotations();
        const annotation = annotations.find(a => a.id === payload.id);

        if (!annotation) {
          return {
            success: false,
            error: `Annotation not found: ${payload.id}`
          };
        }

        // Delete spec folder if requested and annotation has a spec
        if (deleteSpec && annotation.specId) {
          try {
            const { projectStore } = await import('../project-store');
            const project = projectStore.getProject(projectId);

            if (project) {
              await annotationToSpecService.deleteSpec(project.path, annotation);
              appLog.log('[Annotation] Deleted spec:', annotation.specId);
            }
          } catch (error) {
            appLog.error('[Annotation] Failed to delete spec:', error);
            // Continue with annotation deletion even if spec deletion fails
          }
        }

        // Remove annotation from storage
        const filteredAnnotations = annotations.filter(a => a.id !== payload.id);
        await saveAnnotationsToFile(filteredAnnotations);

        appLog.log('[Annotation] Deleted annotation:', payload.id);
        return { success: true, data: undefined };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        appLog.error('[Annotation] Delete failed:', error);
        return {
          success: false,
          error: errorMessage
        };
      }
    }
  );

  appLog.log('[Annotation] IPC handlers registered');
}
