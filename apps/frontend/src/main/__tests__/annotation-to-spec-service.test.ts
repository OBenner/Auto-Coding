/**
 * Tests for AnnotationToSpecService
 *
 * Tests the annotation to spec conversion service including:
 * - Annotation validation
 * - Spec ID generation
 * - Spec folder creation with files
 * - Spec existence checking
 * - Spec deletion
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { promises as fs } from 'fs';
import path from 'path';
import { AnnotationToSpecService } from '../services/annotation-to-spec-service';
import type { Annotation, AnnotationSubmissionResult } from '../../shared/types/annotation';

// Mock fs utilities
vi.mock('../fs-utils', () => ({
  atomicWriteFile: async (filePath: string, content: string) => {
    // Ensure directory exists
    const dir = path.dirname(filePath);
    await fs.mkdir(dir, { recursive: true });
    await fs.writeFile(filePath, content, 'utf-8');
  }
}));

describe('AnnotationToSpecService', () => {
  let service: AnnotationToSpecService;
  let tempDir: string;
  let projectPath: string;

  beforeEach(async () => {
    service = new AnnotationToSpecService();

    // Create temporary directory for testing
    tempDir = path.join(process.env.TMPDIR || '/tmp', `annotation-spec-test-${Date.now()}`);
    projectPath = tempDir;

    await fs.mkdir(tempDir, { recursive: true });
  });

  afterEach(async () => {
    // Clean up temporary directory
    try {
      await fs.rm(tempDir, { recursive: true, force: true });
    } catch {
      // Ignore cleanup errors
    }
  });

  describe('validateAnnotation (via createSpecFromAnnotation)', () => {
    it('should reject annotation with empty ID', async () => {
      const invalidAnnotation = {
        id: '',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Valid description',
        severity: 'low',
        status: 'draft'
      } as Annotation;

      await expect(service.createSpecFromAnnotation(projectPath, invalidAnnotation))
        .rejects.toThrow('Annotation ID is required');
    });

    it('should reject annotation with empty description', async () => {
      const invalidAnnotation = {
        id: 'test-id',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: '',
        severity: 'low',
        status: 'draft'
      } as Annotation;

      await expect(service.createSpecFromAnnotation(projectPath, invalidAnnotation))
        .rejects.toThrow('Annotation description is required');
    });

    it('should reject annotation with description too short (< 10 chars)', async () => {
      const invalidAnnotation = {
        id: 'test-id',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Short',
        severity: 'low',
        status: 'draft'
      } as Annotation;

      await expect(service.createSpecFromAnnotation(projectPath, invalidAnnotation))
        .rejects.toThrow('Annotation description must be at least 10 characters');
    });

    it('should reject annotation without screenshot', async () => {
      const invalidAnnotation = {
        id: 'test-id',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: '',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Valid description that is long enough',
        severity: 'low',
        status: 'draft'
      } as Annotation;

      await expect(service.createSpecFromAnnotation(projectPath, invalidAnnotation))
        .rejects.toThrow('Annotation screenshot is required');
    });

    it('should reject annotation without coordinates', async () => {
      const invalidAnnotation = {
        id: 'test-id',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: undefined as any,
        viewportSize: { width: 1920, height: 1080 },
        description: 'Valid description that is long enough',
        severity: 'low',
        status: 'draft'
      } as Annotation;

      await expect(service.createSpecFromAnnotation(projectPath, invalidAnnotation))
        .rejects.toThrow('Annotation coordinates are required');
    });

    it('should reject annotation with invalid coordinates (non-numeric)', async () => {
      const invalidAnnotation = {
        id: 'test-id',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 'not a number' as any, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Valid description that is long enough',
        severity: 'low',
        status: 'draft'
      } as Annotation;

      await expect(service.createSpecFromAnnotation(projectPath, invalidAnnotation))
        .rejects.toThrow('Annotation coordinates must be valid numbers');
    });

    it('should reject annotation with zero width', async () => {
      const invalidAnnotation = {
        id: 'test-id',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 0, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Valid description that is long enough',
        severity: 'low',
        status: 'draft'
      } as Annotation;

      await expect(service.createSpecFromAnnotation(projectPath, invalidAnnotation))
        .rejects.toThrow('Annotation coordinates must have positive width and height');
    });

    it('should reject annotation with zero height', async () => {
      const invalidAnnotation = {
        id: 'test-id',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 100, height: 0 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Valid description that is long enough',
        severity: 'low',
        status: 'draft'
      } as Annotation;

      await expect(service.createSpecFromAnnotation(projectPath, invalidAnnotation))
        .rejects.toThrow('Annotation coordinates must have positive width and height');
    });

    it('should accept valid annotation', async () => {
      const validAnnotation: Annotation = {
        id: 'test-annotation-id',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        coordinates: { x: 100, y: 200, width: 300, height: 400 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'This is a valid annotation description',
        severity: 'medium',
        status: 'draft'
      };

      const result = await service.createSpecFromAnnotation(projectPath, validAnnotation);

      expect(result).toBeDefined();
      expect(result.specId).toBeDefined();
      expect(result.annotation).toBeDefined();
    });
  });

  describe('generateSpecId (via createSpecFromAnnotation)', () => {
    it('should generate spec ID with first 8 chars of annotation UUID', async () => {
      const annotation: Annotation = {
        id: 'annotation-12345678-abcd-efgh-ijkl-mnopqrstuvwxyz',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Test button alignment issue',
        severity: 'low',
        status: 'draft'
      };

      const result = await service.createSpecFromAnnotation(projectPath, annotation);

      expect(result.specId).toMatch(/^annotation-/);
      expect(result.specId).toContain('test-button-alignment');
    });

    it('should slugify description in spec ID', async () => {
      const annotation: Annotation = {
        id: 'test-id',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Fix the spacing  issue!!! with    multiple   spaces',
        severity: 'low',
        status: 'draft'
      };

      const result = await service.createSpecFromAnnotation(projectPath, annotation);

      expect(result.specId).not.toContain('  ');
      expect(result.specId).not.toContain('!!!');
    });
  });

  describe('createSpecFromAnnotation', () => {
    it('should create spec folder with spec.md file', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        coordinates: { x: 100, y: 200, width: 300, height: 400 },
        viewportSize: { width: 1920, height: 1080, devicePixelRatio: 1 },
        description: 'Button text is not centered properly',
        severity: 'high',
        status: 'draft',
        component: 'SubmitButton',
        route: '/settings'
      };

      const result = await service.createSpecFromAnnotation(projectPath, annotation);

      // Check spec.md exists
      const specMdPath = path.join(result.specPath, 'spec.md');
      const specMdContent = await fs.readFile(specMdPath, 'utf-8');

      expect(specMdContent).toContain('Button text is not centered properly');
      expect(specMdContent).toContain('High');
      expect(specMdContent).toContain('SubmitButton');
      expect(specMdContent).toContain('/settings');
      expect(specMdContent).toContain('X: 100px');
      expect(specMdContent).toContain('Y: 200px');
      expect(specMdContent).toContain('Width: 300px');
      expect(specMdContent).toContain('Height: 400px');
    });

    it('should create requirements.json file', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 50, y: 50, width: 200, height: 150 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Viewport scaling issue on mobile',
        severity: 'medium',
        status: 'draft',
        route: '/dashboard'
      };

      const result = await service.createSpecFromAnnotation(projectPath, annotation);

      // Check requirements.json exists and has correct content
      const requirementsPath = path.join(result.specPath, 'requirements.json');
      const requirementsContent = await fs.readFile(requirementsPath, 'utf-8');
      const requirements = JSON.parse(requirementsContent);

      expect(requirements.task_description).toBe('Viewport scaling issue on mobile');
      expect(requirements.severity).toBe('medium');
      expect(requirements.route).toBe('/dashboard');
      expect(requirements.coordinates).toEqual({ x: 50, y: 50, width: 200, height: 150 });
      expect(requirements.annotation_id).toBe('test-annotation');
      expect(requirements.generated_from).toBe('visual_annotation');
    });

    it('should save screenshot.png from base64 data', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Test annotation',
        severity: 'low',
        status: 'draft'
      };

      const result = await service.createSpecFromAnnotation(projectPath, annotation);

      // Check screenshot.png exists
      const screenshotPath = path.join(result.specPath, 'screenshot.png');
      await fs.access(screenshotPath);
    });

    it('should handle screenshot without data URL prefix', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Test annotation',
        severity: 'low',
        status: 'draft'
      };

      const result = await service.createSpecFromAnnotation(projectPath, annotation);

      // Should still save screenshot correctly
      const screenshotPath = path.join(result.specPath, 'screenshot.png');
      await fs.access(screenshotPath);
    });

    it('should update annotation with spec ID and completed status', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Test annotation',
        severity: 'low',
        status: 'draft'
      };

      const result = await service.createSpecFromAnnotation(projectPath, annotation);

      expect(annotation.specId).toBe(result.specId);
      expect(annotation.status).toBe('completed');
    });

    it('should support custom title in spec generation', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Test annotation',
        severity: 'low',
        status: 'draft'
      };

      const result = await service.createSpecFromAnnotation(projectPath, annotation, {
        title: 'Custom Spec Title'
      });

      const specMdPath = path.join(result.specPath, 'spec.md');
      const specMdContent = await fs.readFile(specMdPath, 'utf-8');

      expect(specMdContent).toContain('# Custom Spec Title');
    });

    it('should skip screenshot when includeScreenshot is false', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Test annotation',
        severity: 'low',
        status: 'draft'
      };

      const result = await service.createSpecFromAnnotation(projectPath, annotation, {
        includeScreenshot: false
      });

      const screenshotPath = path.join(result.specPath, 'screenshot.png');

      await expect(fs.access(screenshotPath)).rejects.toThrow();
    });
  });

  describe('specExists', () => {
    it('should return false for non-existent spec', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Test annotation',
        severity: 'low',
        status: 'draft'
      };

      const exists = await service.specExists(projectPath, annotation);

      expect(exists).toBe(false);
    });

    it('should return true for existing spec', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Test annotation',
        severity: 'low',
        status: 'draft'
      };

      // Create spec first
      await service.createSpecFromAnnotation(projectPath, annotation);

      // Check if exists
      const exists = await service.specExists(projectPath, annotation);

      expect(exists).toBe(true);
    });
  });

  describe('deleteSpec', () => {
    it('should delete spec folder', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Test annotation',
        severity: 'low',
        status: 'draft'
      };

      // Create spec first
      const result = await service.createSpecFromAnnotation(projectPath, annotation);

      // Verify spec exists
      await expect(fs.access(result.specPath)).resolves.toBeUndefined();

      // Delete spec
      await service.deleteSpec(projectPath, annotation);

      // Verify spec folder deleted
      await expect(fs.access(result.specPath)).rejects.toThrow();
    });

    it('should delete spec using spec ID from annotation', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Test annotation',
        severity: 'low',
        status: 'draft'
      };

      // Create spec (which sets specId on annotation)
      const result = await service.createSpecFromAnnotation(projectPath, annotation);

      // Delete using annotation with specId
      await service.deleteSpec(projectPath, annotation);

      // Verify spec folder deleted
      await expect(fs.access(result.specPath)).rejects.toThrow();
    });

    it('should not throw when deleting non-existent spec', async () => {
      const annotation: Annotation = {
        id: 'test-annotation',
        timestamp: '2025-02-25T12:00:00Z',
        screenshot: 'data:image/png;base64,abc123',
        coordinates: { x: 0, y: 0, width: 100, height: 100 },
        viewportSize: { width: 1920, height: 1080 },
        description: 'Test annotation',
        severity: 'low',
        status: 'draft'
      };

      // Should not throw
      await expect(service.deleteSpec(projectPath, annotation)).resolves.toBeUndefined();
    });
  });
});
