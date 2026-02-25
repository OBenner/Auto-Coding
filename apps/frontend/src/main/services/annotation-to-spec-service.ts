/**
 * Annotation-to-Spec Service
 *
 * Transforms visual UI annotations into Auto-Claude spec folder structure.
 * Creates spec folders with spec.md, requirements.json, and screenshot.png
 * from annotation data submitted via the visual feedback system.
 */

import { promises as fsPromises } from 'fs';
import * as path from 'path';
import { atomicWriteFile } from '../fs-utils';
import { AUTO_BUILD_PATHS } from '../../shared/constants';
import type {
  Annotation,
  AnnotationSpecOptions,
  AnnotationSubmissionResult
} from '../../shared/types/annotation';

/**
 * Service class for converting annotations to spec folders
 */
export class AnnotationToSpecService {
  /**
   * Convert annotation to URL-friendly slug
   * Converts description to kebab-case for use in folder names
   */
  private slugify(text: string): string {
    return text
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, '') // Remove special characters
      .replace(/[\s_-]+/g, '-') // Replace spaces and underscores with hyphens
      .replace(/^-+|-+$/g, ''); // Remove leading/trailing hyphens
  }

  /**
   * Generate spec ID from annotation
   * Format: {number}-annotation-{slug}
   * Uses first 8 chars of UUID as number for uniqueness
   */
  private generateSpecId(annotation: Annotation): string {
    const shortId = annotation.id.substring(0, 8);
    const slug = this.slugify(annotation.description);
    return `${shortId}-annotation-${slug}`;
  }

  /**
   * Generate spec.md content from annotation
   */
  private generateSpecMd(annotation: Annotation, options?: AnnotationSpecOptions): string {
    const title = options?.title || `Fix: ${annotation.description}`;
    const severityMap: Record<Annotation['severity'], string> = {
      low: 'Low',
      medium: 'Medium',
      high: 'High',
      critical: 'Critical'
    };

    const coordinates = annotation.coordinates;
    const viewport = annotation.viewportSize;

    let content = `# ${title}\n\n`;

    content += `## Overview\n\n`;
    content += `This spec was generated from a visual UI annotation submitted during prototype development.\n\n`;

    content += `### Issue Details\n\n`;
    content += `- **Description**: ${annotation.description}\n`;
    content += `- **Severity**: ${severityMap[annotation.severity]}\n`;
    content += `- **Component**: ${annotation.component || 'Unknown'}\n`;
    content += `- **Route**: ${annotation.route || 'Unknown'}\n\n`;

    content += `### Screen Context\n\n`;
    content += `The issue was identified at the following screen coordinates:\n\n`;
    content += `- **X**: ${coordinates.x}px\n`;
    content += `- **Y**: ${coordinates.y}px\n`;
    content += `- **Width**: ${coordinates.width}px\n`;
    content += `- **Height**: ${coordinates.height}px\n\n`;

    content += `**Viewport Size**:\n`;
    content += `- **Width**: ${viewport.width}px\n`;
    content += `- **Height**: ${viewport.height}px\n`;
    if (viewport.devicePixelRatio) {
      content += `- **Device Pixel Ratio**: ${viewport.devicePixelRatio}\n`;
    }
    content += `\n`;

    content += `## Workflow Type\n\n`;
    content += `**Type**: bug_fix\n\n`;
    content += `**Rationale**: This issue was identified through visual annotation during prototype development, indicating a UI/UX problem that needs to be addressed.\n\n`;

    content += `## Task Scope\n\n`;
    content += `### This Task Will:\n`;
    content += `- [ ] Investigate and fix the reported UI issue\n`;
    content += `- [ ] Verify the fix works at the reported viewport size\n`;
    content += `- [ ] Ensure no regressions in related functionality\n\n`;

    content += `### Out of Scope:\n`;
    content += `- Feature additions beyond fixing the reported issue\n`;
    content += `- Changes to unrelated components or routes\n\n`;

    content += `## Service Context\n\n`;
    content += `### Frontend (Primary Service)\n\n`;
    content += `**Tech Stack:**\n`;
    content += `- Language: TypeScript\n`;
    content += `- Framework: React 19.x + Electron 40.6.0\n`;
    content += `- Styling: Tailwind CSS\n\n`;

    content += `**Issue Location:**\n`;
    if (annotation.component) {
      content += `- Component: ${annotation.component}\n`;
    }
    if (annotation.route) {
      content += `- Route: ${annotation.route}\n`;
    }
    content += `- Coordinates: (${coordinates.x}, ${coordinates.y}) size ${coordinates.width}x${coordinates.height}\n\n`;

    content += `## Requirements\n\n`;
    content += `### Functional Requirements\n\n`;
    content += `1. **Fix the Issue**\n`;
    content += `   - Description: ${annotation.description}\n`;
    content += `   - Acceptance: Issue is resolved, UI behaves correctly\n\n`;

    if (annotation.severity === 'critical' || annotation.severity === 'high') {
      content += `2. **No Regressions**\n`;
      content += `   - Description: Related functionality continues to work correctly\n`;
      content += `   - Acceptance: All related features pass tests\n\n`;
    }

    content += `### Non-Functional Requirements\n\n`;
    content += `1. **Performance**\n`;
    content += `   - Description: Fix should not impact app performance\n`;
    content += `   - Acceptance: No perceptible lag when interacting with fixed component\n\n`;

    content += `2. **Cross-Platform Compatibility**\n`;
    content += `   - Description: Fix works on Windows, macOS, and Linux\n`;
    content += `   - Acceptance: Verified on all platforms\n\n`;

    content += `## Edge Cases\n\n`;
    content += `1. **Viewport Sizes** - Ensure fix works at different viewport sizes\n`;
    content += `2. **High DPI Displays** - Verify rendering on retina/high-DPI screens\n`;
    if (annotation.severity === 'critical') {
      content += `3. **Error Handling** - Component handles errors gracefully\n`;
    }
    content += `\n`;

    content += `## Success Criteria\n\n`;
    content += `The task is complete when:\n\n`;
    content += `1. [ ] The reported issue is resolved\n`;
    content += `2. [ ] Visual inspection shows correct behavior\n`;
    content += `3. [ ] No regressions in related functionality\n`;
    content += `4. [ ] All existing tests still pass\n`;
    content += `5. [ ] Works on Windows, macOS, and Linux\n\n`;

    content += `## Attachment\n\n`;
    content += `A screenshot of the annotated area has been included as \`screenshot.png\` for reference.\n`;

    return content;
  }

  /**
   * Generate requirements.json content from annotation
   */
  private generateRequirementsJson(
    annotation: Annotation,
    specId: string
  ): string {
    const requirements = {
      task_description: annotation.description,
      severity: annotation.severity,
      component: annotation.component || null,
      route: annotation.route || null,
      coordinates: annotation.coordinates,
      viewport_size: annotation.viewportSize,
      annotation_id: annotation.id,
      annotation_timestamp: annotation.timestamp,
      generated_from: 'visual_annotation',
      spec_id: specId
    };

    return JSON.stringify(requirements, null, 2);
  }

  /**
   * Save screenshot from base64 string
   */
  private async saveScreenshot(
    specDir: string,
    base64Screenshot: string
  ): Promise<void> {
    const screenshotPath = path.join(specDir, 'screenshot.png');

    // Strip data URL prefix if present (e.g., "data:image/png;base64,")
    const base64Data = base64Screenshot.replace(/^data:image\/png;base64,/, '');
    const buffer = Buffer.from(base64Data, 'base64');

    await fsPromises.writeFile(screenshotPath, buffer);
  }

  /**
   * Validate annotation before creating spec
   * Throws error if annotation is invalid
   */
  private validateAnnotation(annotation: Annotation): void {
    if (!annotation.id || annotation.id.trim() === '') {
      throw new Error('Annotation ID is required');
    }

    if (!annotation.description || annotation.description.trim() === '') {
      throw new Error('Annotation description is required');
    }

    if (annotation.description.length < 10) {
      throw new Error('Annotation description must be at least 10 characters');
    }

    if (!annotation.screenshot || annotation.screenshot.trim() === '') {
      throw new Error('Annotation screenshot is required');
    }

    if (!annotation.coordinates) {
      throw new Error('Annotation coordinates are required');
    }

    const { x, y, width, height } = annotation.coordinates;
    if (typeof x !== 'number' || typeof y !== 'number' ||
        typeof width !== 'number' || typeof height !== 'number') {
      throw new Error('Annotation coordinates must be valid numbers');
    }

    if (width <= 0 || height <= 0) {
      throw new Error('Annotation coordinates must have positive width and height');
    }
  }

  /**
   * Create spec folder from annotation
   *
   * Creates a new spec folder in .auto-claude/specs/ with:
   * - spec.md: Generated spec document
   * - requirements.json: Annotation data as requirements
   * - screenshot.png: Captured screenshot
   *
   * @param projectPath - Root path of the project
   * @param annotation - The annotation to convert
   * @param options - Optional generation options
   * @returns Promise<AnnotationSubmissionResult> Result with spec ID and path
   */
  async createSpecFromAnnotation(
    projectPath: string,
    annotation: Annotation,
    options?: AnnotationSpecOptions
  ): Promise<AnnotationSubmissionResult> {
    // Validate annotation before proceeding
    this.validateAnnotation(annotation);

    // Generate spec ID
    const specId = this.generateSpecId(annotation);

    // Create spec directory path
    const specsDir = path.join(projectPath, AUTO_BUILD_PATHS.SPECS_DIR);
    const specDir = path.join(specsDir, specId);

    // Ensure spec directory exists
    await fsPromises.mkdir(specDir, { recursive: true });

    // Generate and write spec.md
    const specMdContent = this.generateSpecMd(annotation, options);
    const specMdPath = path.join(specDir, AUTO_BUILD_PATHS.SPEC_FILE);
    await atomicWriteFile(specMdPath, specMdContent);

    // Generate and write requirements.json
    const requirementsContent = this.generateRequirementsJson(annotation, specId);
    const requirementsPath = path.join(specDir, AUTO_BUILD_PATHS.REQUIREMENTS);
    await atomicWriteFile(requirementsPath, requirementsContent);

    // Save screenshot if not explicitly disabled
    if (options?.includeScreenshot !== false) {
      await this.saveScreenshot(specDir, annotation.screenshot);
    }

    // Update annotation with spec ID
    annotation.specId = specId;
    annotation.status = 'completed';

    return {
      annotation,
      specId,
      specPath: specDir
    };
  }

  /**
   * Check if a spec directory exists for an annotation
   */
  async specExists(projectPath: string, annotation: Annotation): Promise<boolean> {
    const specId = this.generateSpecId(annotation);
    const specDir = path.join(projectPath, AUTO_BUILD_PATHS.SPECS_DIR, specId);

    try {
      await fsPromises.access(specDir);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Delete a spec directory created from an annotation
   * Use with caution - this permanently deletes the spec folder
   */
  async deleteSpec(projectPath: string, annotation: Annotation): Promise<void> {
    const specId = annotation.specId || this.generateSpecId(annotation);
    const specDir = path.join(projectPath, AUTO_BUILD_PATHS.SPECS_DIR, specId);

    await fsPromises.rm(specDir, { recursive: true, force: true });
  }
}

// Singleton instance
export const annotationToSpecService = new AnnotationToSpecService();
