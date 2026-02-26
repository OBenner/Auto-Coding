/**
 * Template IPC handlers
 *
 * Handlers for template library operations including listing templates,
 * getting template details, previewing specs, and creating specs from templates.
 */

import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult, TemplateInfo, GeneratedSpec, TemplateCategory } from '../../shared/types';
import path from 'path';
import { promises as fsPromises } from 'fs';
import { projectStore } from '../project-store';
import { runPythonSubprocess } from './github/utils/subprocess-runner';
import { getRunnerEnv } from './github/utils/runner-env';
import { debugLog, debugError } from '../../shared/utils/debug-logger';

/**
 * Helper to get the backend directory path
 */
function getBackendDir(): string {
  // The backend is at apps/backend/ from the project root
  // From the Electron app's perspective, we need to navigate to it
  const projectRoot = path.resolve(__dirname, '../../../..');
  return path.join(projectRoot, 'apps', 'backend');
}

/**
 * Helper to get Python executable path and environment
 */
async function getPythonEnv(_projectPath: string): Promise<{ pythonPath: string; env: Record<string, string> }> {
  const env = await getRunnerEnv();

  // Get Python path - check if there's a configured venv Python
  // For now, we'll use 'python' as the command and let the PATH resolve it
  // In production, this would use pythonEnvManager.getPythonPath()
  const pythonPath = 'python';

  return {
    pythonPath,
    env
  };
}

/**
 * Register template-related IPC handlers
 */
export function registerTemplateHandlers(): void {
  /**
   * List all available templates with optional filtering
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_LIST,
    async (
      _,
      projectId: string,
      options?: { category?: TemplateCategory | 'all'; tags?: string[] }
    ): Promise<IPCResult<TemplateInfo[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[TEMPLATE_LIST] Listing templates for project:', projectId, 'options:', options);

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        // Build Python script arguments
        const args = [
          '-c',
          `
import sys
import json

# Add backend to path
sys.path.insert(0, ${JSON.stringify(backendDir)})

from cli.spec_commands import list_templates
from pathlib import Path

project_dir = Path(${JSON.stringify(project.path)})
category = ${JSON.stringify(options?.category !== 'all' ? options?.category : null)}
tags = ${JSON.stringify(options?.tags || null)}

templates = list_templates(project_dir, category=category, tags=tags)
print(json.dumps(templates))
          `
        ];

        const { promise } = runPythonSubprocess<{ templates: TemplateInfo[] }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[TEMPLATE_LIST] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to list templates' };
        }

        const templates = JSON.parse(result.stdout.trim()) as TemplateInfo[];
        debugLog('[TEMPLATE_LIST] Returning', templates.length, 'templates');

        return { success: true, data: templates };
      } catch (error) {
        debugError('[TEMPLATE_LIST] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Get detailed information about a specific template
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_GET,
    async (_, projectId: string, templateName: string): Promise<IPCResult<TemplateInfo>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[TEMPLATE_GET] Getting template:', templateName);

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

sys.path.insert(0, ${JSON.stringify(backendDir)})

from cli.spec_commands import show_template_info
from spec.templates.library import TemplateLibrary
from pathlib import Path
from io import StringIO
import sys

project_dir = Path(${JSON.stringify(project.path)})
library = TemplateLibrary()
template = library.get_template(${JSON.stringify(templateName)})

if not template:
    print(json.dumps({"error": "Template not found"}))
    sys.exit(1)

# Capture template info as dict
info = {
    "name": template.name,
    "description": template.description,
    "category": template.category,
    "parameters": template.parameters,
    "tags": getattr(template, 'tags', None)  # Keep None here - it's Python code
}

print(json.dumps(info))
          `
        ];

        const { promise } = runPythonSubprocess<{ template: TemplateInfo }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[TEMPLATE_GET] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to get template' };
        }

        const templateInfo = JSON.parse(result.stdout.trim()) as TemplateInfo;
        return { success: true, data: templateInfo };
      } catch (error) {
        debugError('[TEMPLATE_GET] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Get all available template categories
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_GET_CATEGORIES,
    async (_, projectId: string): Promise<IPCResult<string[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[TEMPLATE_GET_CATEGORIES] Getting categories');

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

sys.path.insert(0, ${JSON.stringify(backendDir)})

from spec.templates.library import TemplateLibrary

library = TemplateLibrary()
categories = library.get_categories()

print(json.dumps(categories))
          `
        ];

        const { promise } = runPythonSubprocess<{ categories: string[] }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[TEMPLATE_GET_CATEGORIES] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to get categories' };
        }

        const categories = JSON.parse(result.stdout.trim()) as string[];
        return { success: true, data: categories };
      } catch (error) {
        debugError('[TEMPLATE_GET_CATEGORIES] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Search templates by query string
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_SEARCH,
    async (_, projectId: string, query: string): Promise<IPCResult<TemplateInfo[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[TEMPLATE_SEARCH] Searching templates:', query);

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

sys.path.insert(0, ${JSON.stringify(backendDir)})

from spec.templates.library import TemplateLibrary

library = TemplateLibrary()
results = library.search_templates(${JSON.stringify(query)})

print(json.dumps(results))
          `
        ];

        const { promise } = runPythonSubprocess<{ results: TemplateInfo[] }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[TEMPLATE_SEARCH] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to search templates' };
        }

        const searchResults = JSON.parse(result.stdout.trim()) as TemplateInfo[];
        return { success: true, data: searchResults };
      } catch (error) {
        debugError('[TEMPLATE_SEARCH] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Preview a spec from a template without saving
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_PREVIEW,
    async (
      _,
      projectId: string,
      templateName: string,
      parameters: Record<string, unknown>
    ): Promise<IPCResult<GeneratedSpec>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[TEMPLATE_PREVIEW] Previewing template:', templateName);

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        // Escape parameters properly for Python
        const paramsJson = JSON.stringify(parameters);

        const args = [
          '-c',
          `
import sys
import json

sys.path.insert(0, ${JSON.stringify(backendDir)})

from spec.templates.library import TemplateLibrary

library = TemplateLibrary()
preview = library.preview_template(${JSON.stringify(templateName)}, ${paramsJson})

if not preview:
    print(json.dumps({"error": "Template not found or preview failed"}))
    sys.exit(1)

# Parse the markdown preview into GeneratedSpec structure
# For now, return the raw markdown as description
spec = {
    "title": "${templateName}",
    "description": preview,
    "rationale": "",
    "user_stories": [],
    "acceptance_criteria": [],
    "technical_details": preview
}

print(json.dumps(spec))
          `
        ];

        const { promise } = runPythonSubprocess<{ spec: GeneratedSpec }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[TEMPLATE_PREVIEW] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to preview template' };
        }

        const spec = JSON.parse(result.stdout.trim()) as GeneratedSpec;
        return { success: true, data: spec };
      } catch (error) {
        debugError('[TEMPLATE_PREVIEW] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Create a spec from a template
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_CREATE_SPEC,
    async (
      _,
      projectId: string,
      templateName: string,
      parameters: Record<string, unknown>,
      specId?: string
    ): Promise<IPCResult<{ specId: string; specPath: string }>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[TEMPLATE_CREATE_SPEC] Creating spec from template:', templateName);

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        // Generate spec ID if not provided
        let finalSpecId = specId;
        if (!finalSpecId) {
          // Find next available spec number
          const autoBuildPath = project.autoBuildPath || '.auto-claude';
          const specsDir = path.join(project.path, autoBuildPath, 'specs');

          let specNumber = 1;
          if (await fsPromises.access(specsDir).then(() => true).catch(() => false)) {
            const existingDirs = await fsPromises.readdir(specsDir, { withFileTypes: true });
            const dirNames = existingDirs.filter(d => d.isDirectory()).map(d => d.name);

            const existingNumbers = dirNames
              .map(name => {
                const match = name.match(/^(\d+)/);
                return match ? parseInt(match[1], 10) : 0;
              })
              .filter(n => n > 0);

            if (existingNumbers.length > 0) {
              specNumber = Math.max(...existingNumbers) + 1;
            }
          }

          finalSpecId = `${String(specNumber).padStart(3, '0')}-${templateName}`;
        }

        const specDir = path.join(project.path, project.autoBuildPath || '.auto-claude', 'specs', finalSpecId);

        // Create spec directory
        await fsPromises.mkdir(specDir, { recursive: true });

        const paramsJson = JSON.stringify(parameters);

        const args = [
          '-c',
          `
import sys
import json
from pathlib import Path

sys.path.insert(0, ${JSON.stringify(backendDir)})

from spec.templates.library import TemplateLibrary

library = TemplateLibrary()
spec_dir = Path(${JSON.stringify(specDir)})

result = library.create_spec_from_template(
    ${JSON.stringify(templateName)},
    ${paramsJson},
    spec_dir
)

print(json.dumps({
    "success": True,
    "specId": ${JSON.stringify(finalSpecId)},
    "specPath": str(spec_dir)
}))
          `
        ];

        const { promise } = runPythonSubprocess<{
          success: boolean;
          specId: string;
          specPath: string;
        }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[TEMPLATE_CREATE_SPEC] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to create spec from template' };
        }

        const createResult = JSON.parse(result.stdout.trim()) as {
          success: boolean;
          specId: string;
          specPath: string;
        };

        return { success: true, data: createResult };
      } catch (error) {
        debugError('[TEMPLATE_CREATE_SPEC] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Get template suggestions based on project analysis
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_SUGGEST,
    async (_, projectId: string, taskDescription: string): Promise<IPCResult<string[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[TEMPLATE_SUGGEST] Getting suggestions for:', taskDescription);

        const { pythonPath, env } = await getPythonEnv(project.path);
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json
from pathlib import Path

sys.path.insert(0, ${JSON.stringify(backendDir)})

from spec.templates.library import suggest_templates

project_dir = Path(${JSON.stringify(project.path)})
suggestions = suggest_templates(project_dir, ${JSON.stringify(taskDescription)})

print(json.dumps(suggestions))
          `
        ];

        const { promise } = runPythonSubprocess<{ suggestions: string[] }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[TEMPLATE_SUGGEST] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to get template suggestions' };
        }

        const suggestions = JSON.parse(result.stdout.trim()) as string[];
        return { success: true, data: suggestions };
      } catch (error) {
        debugError('[TEMPLATE_SUGGEST] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  // ─────────────────────────────────────────────────────────────────────────────
  // Custom Template CRUD Operations
  // ─────────────────────────────────────────────────────────────────────────────

  /**
   * Get the custom templates storage file path
   */
  function getCustomTemplatesPath(): string {
    const { app } = require('electron');
    const userDataPath = app.getPath('userData');
    return path.join(userDataPath, 'custom-templates.json');
  }

  /**
   * Load custom templates from storage
   */
  async function loadCustomTemplates(): Promise<import('../../shared/types/template').CustomTemplate[]> {
    const templatesPath = getCustomTemplatesPath();

    try {
      await fsPromises.access(templatesPath);
    } catch {
      // File doesn't exist - return empty array
      return [];
    }

    try {
      const content = await fsPromises.readFile(templatesPath, 'utf-8');
      const raw = JSON.parse(content);

      if (!Array.isArray(raw)) {
        debugError('[loadCustomTemplates] Templates file is not an array, resetting');
        return [];
      }

      // Convert date strings back to Date objects with validation
      return raw.map((t: import('../../shared/types/template').CustomTemplate) => {
        const createdAt = t.createdAt ? new Date(t.createdAt) : undefined;
        const updatedAt = t.updatedAt ? new Date(t.updatedAt) : undefined;

        return {
          ...t,
          createdAt: (createdAt && !isNaN(createdAt.getTime())) ? createdAt : new Date(),
          updatedAt: (updatedAt && !isNaN(updatedAt.getTime())) ? updatedAt : new Date()
        };
      });
    } catch (error) {
      debugError('[loadCustomTemplates] Failed to read/parse templates file:', error);
      return [];
    }
  }

  /**
   * Save custom templates to storage
   */
  async function saveCustomTemplatesToFile(
    templates: import('../../shared/types/template').CustomTemplate[]
  ): Promise<void> {
    const templatesPath = getCustomTemplatesPath();
    const tmpPath = templatesPath + '.tmp';
    await fsPromises.writeFile(tmpPath, JSON.stringify(templates, null, 2), 'utf-8');
    await fsPromises.rename(tmpPath, templatesPath);
  }

  /**
   * Generate a unique ID for a new template
   */
  function generateTemplateId(): string {
    return `custom-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
  }

  /**
   * Validate a custom template
   */
  function validateCustomTemplate(
    template: import('../../shared/types/template').CustomTemplate
  ): string[] {
    const errors: string[] = [];

    // Check required fields
    if (!template.name || template.name.trim() === '') {
      errors.push('Template name is required');
    }

    if (!template.description || template.description.trim() === '') {
      errors.push('Template description is required');
    }

    if (!template.category) {
      errors.push('Template category is required');
    }

    // Validate parameters if present
    if (template.parameters) {
      for (const [paramName, paramConfig] of Object.entries(template.parameters)) {
        if (!paramConfig) continue;
        if (!paramConfig.type || !['str', 'int', 'float', 'bool', 'list', 'dict'].includes(paramConfig.type)) {
          errors.push(`Parameter '${paramName}' has invalid type: ${paramConfig.type}`);
        }
        if (!paramConfig.description) {
          errors.push(`Parameter '${paramName}' is missing description`);
        }
      }
    }

    return errors;
  }

  /**
   * List all custom templates
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_CUSTOM_LIST,
    async (): Promise<IPCResult<import('../../shared/types/template').CustomTemplate[]>> => {
      try {
        debugLog('[TEMPLATE_CUSTOM_LIST] Loading custom templates');

        const templates = await loadCustomTemplates();

        debugLog('[TEMPLATE_CUSTOM_LIST] Returning', templates.length, 'custom templates');
        return { success: true, data: templates };
      } catch (error) {
        debugError('[TEMPLATE_CUSTOM_LIST] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Save a new custom template
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_CUSTOM_SAVE,
    async (
      _,
      template: Omit<import('../../shared/types/template').CustomTemplate, 'id' | 'createdAt' | 'updatedAt'>
    ): Promise<IPCResult<import('../../shared/types/template').CustomTemplate & { validationErrors?: string[] }>> => {
      try {
        debugLog('[TEMPLATE_CUSTOM_SAVE] Saving custom template:', template.name);

        // Validate template
        const validationErrors = validateCustomTemplate(template as import('../../shared/types/template').CustomTemplate);

        if (validationErrors.length > 0) {
          debugLog('[TEMPLATE_CUSTOM_SAVE] Validation errors:', validationErrors);
          return {
            success: false,
            error: 'Template validation failed',
            data: {
              ...(template as any),
              validationErrors
            }
          };
        }

        const templates = await loadCustomTemplates();

        // Check for duplicate names
        const duplicate = templates.find(t => t.name.normalize('NFC').trim().toLowerCase() === template.name.normalize('NFC').trim().toLowerCase());
        if (duplicate) {
          return {
            success: false,
            error: `A template with the name "${template.name}" already exists`,
            data: {
              ...(template as any),
              validationErrors: [`Duplicate template name: ${template.name}`]
            }
          };
        }

        const now = new Date();
        const newTemplate: import('../../shared/types/template').CustomTemplate = {
          ...template,
          id: generateTemplateId(),
          createdAt: now,
          updatedAt: now
        };

        templates.push(newTemplate);
        await saveCustomTemplatesToFile(templates);

        debugLog('[TEMPLATE_CUSTOM_SAVE] Template saved:', newTemplate.id);
        return { success: true, data: newTemplate };
      } catch (error) {
        debugError('[TEMPLATE_CUSTOM_SAVE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Update an existing custom template
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_CUSTOM_UPDATE,
    async (
      _,
      template: import('../../shared/types/template').CustomTemplate
    ): Promise<IPCResult<import('../../shared/types/template').CustomTemplate & { validationErrors?: string[] }>> => {
      try {
        debugLog('[TEMPLATE_CUSTOM_UPDATE] Updating custom template:', template.id);

        // Validate template
        const validationErrors = validateCustomTemplate(template);

        if (validationErrors.length > 0) {
          debugLog('[TEMPLATE_CUSTOM_UPDATE] Validation errors:', validationErrors);
          return {
            success: false,
            error: 'Template validation failed',
            data: {
              ...template,
              validationErrors
            }
          };
        }

        const templates = await loadCustomTemplates();

        // Find the template index
        const index = templates.findIndex(t => t.id === template.id);

        if (index === -1) {
          return {
            success: false,
            error: `Template not found: ${template.id}`,
            data: {
              ...template,
              validationErrors: ['Template ID not found']
            }
          };
        }

        // Check for duplicate names (exclude current template)
        const duplicate = templates.find(
          t => t.id !== template.id && t.name.normalize('NFC').trim().toLowerCase() === template.name.normalize('NFC').trim().toLowerCase()
        );
        if (duplicate) {
          return {
            success: false,
            error: `A template with the name "${template.name}" already exists`,
            data: {
              ...template,
              validationErrors: [`Duplicate template name: ${template.name}`]
            }
          };
        }

        // Update the template
        templates[index] = {
          ...template,
          updatedAt: new Date()
        };

        await saveCustomTemplatesToFile(templates);

        debugLog('[TEMPLATE_CUSTOM_UPDATE] Template updated:', template.id);
        return { success: true, data: templates[index] };
      } catch (error) {
        debugError('[TEMPLATE_CUSTOM_UPDATE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Delete a custom template
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_CUSTOM_DELETE,
    async (_, templateId: string): Promise<IPCResult<void>> => {
      try {
        debugLog('[TEMPLATE_CUSTOM_DELETE] Deleting template:', templateId);

        const templates = await loadCustomTemplates();

        // Filter out the template
        const filteredTemplates = templates.filter(t => t.id !== templateId);

        if (filteredTemplates.length === templates.length) {
          return {
            success: false,
            error: `Template not found: ${templateId}`
          };
        }

        await saveCustomTemplatesToFile(filteredTemplates);

        debugLog('[TEMPLATE_CUSTOM_DELETE] Template deleted:', templateId);
        return { success: true, data: undefined };
      } catch (error) {
        debugError('[TEMPLATE_CUSTOM_DELETE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Export a custom template to JSON string
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_CUSTOM_EXPORT,
    async (_, templateId: string): Promise<IPCResult<string>> => {
      try {
        debugLog('[TEMPLATE_CUSTOM_EXPORT] Exporting template:', templateId);

        const templates = await loadCustomTemplates();
        const template = templates.find(t => t.id === templateId);

        if (!template) {
          return {
            success: false,
            error: `Template not found: ${templateId}`
          };
        }

        // Export as JSON string (for file download)
        const json = JSON.stringify(template, null, 2);

        debugLog('[TEMPLATE_CUSTOM_EXPORT] Template exported:', templateId);
        return { success: true, data: json };
      } catch (error) {
        debugError('[TEMPLATE_CUSTOM_EXPORT] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Import a custom template from JSON string
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_CUSTOM_IMPORT,
    async (
      _,
      jsonData: string
    ): Promise<IPCResult<import('../../shared/types/template').CustomTemplate & { validationErrors?: string[] }>> => {
      try {
        debugLog('[TEMPLATE_CUSTOM_IMPORT] Importing template from JSON');

        // Validate payload size
        if (typeof jsonData !== 'string' || jsonData.length > 256 * 1024) {
          return {
            success: false,
            error: 'Invalid or oversized payload (max 256 KB)'
          };
        }

        // Parse JSON
        const template = JSON.parse(jsonData) as import('../../shared/types/template').CustomTemplate;

        // Validate required fields
        const validationErrors = validateCustomTemplate(template);

        if (validationErrors.length > 0) {
          debugLog('[TEMPLATE_CUSTOM_IMPORT] Validation errors:', validationErrors);
          return {
            success: false,
            error: 'Template validation failed',
            data: {
              ...template,
              validationErrors
            }
          };
        }

        const templates = await loadCustomTemplates();

        // Check for duplicate names
        const duplicate = templates.find(t => t.name.normalize('NFC').trim().toLowerCase() === template.name.normalize('NFC').trim().toLowerCase());
        if (duplicate) {
          return {
            success: false,
            error: `A template with the name "${template.name}" already exists`,
            data: {
              ...template,
              validationErrors: [`Duplicate template name: ${template.name}`]
            }
          };
        }

        // Generate new ID and dates
        const now = new Date();
        const newTemplate: import('../../shared/types/template').CustomTemplate = {
          ...template,
          id: generateTemplateId(),
          createdAt: now,
          updatedAt: now
        };

        templates.push(newTemplate);
        await saveCustomTemplatesToFile(templates);

        debugLog('[TEMPLATE_CUSTOM_IMPORT] Template imported:', newTemplate.id);
        return { success: true, data: newTemplate };
      } catch (error) {
        debugError('[TEMPLATE_CUSTOM_IMPORT] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to parse template JSON'
        };
      }
    }
  );

  /**
   * Test a custom template by generating a preview spec
   */
  ipcMain.handle(
    IPC_CHANNELS.TEMPLATE_CUSTOM_TEST,
    async (
      _,
      templateId: string,
      _testInput: string
    ): Promise<IPCResult<GeneratedSpec>> => {
      try {
        debugLog('[TEMPLATE_CUSTOM_TEST] Testing template:', templateId);

        const templates = await loadCustomTemplates();
        const template = templates.find(t => t.id === templateId);

        if (!template) {
          return {
            success: false,
            error: `Template not found: ${templateId}`
          };
        }

        // For custom templates, we'll generate a simple preview
        // In a real implementation, this would call the backend to render the template
        const tagsStr = template.tags?.join(', ') || 'none';
        const parametersStr = Object.keys(template.parameters || {}).length > 0
          ? JSON.stringify(template.parameters, null, 2)
          : 'No parameters defined';

        const preview: GeneratedSpec = {
          title: template.name,
          description: template.description,
          rationale: `Custom agent template: ${template.name}\n\n**Category:** ${template.category}\n**Tags:** ${tagsStr}\n**Author:** ${template.author || 'Unknown'}`,
          user_stories: [], // Would be populated from template examples
          acceptance_criteria: [], // Would be populated from template
          technical_details: `**Parameters:**\n${parametersStr}`
        };

        debugLog('[TEMPLATE_CUSTOM_TEST] Preview generated');
        return { success: true, data: preview };
      } catch (error) {
        debugError('[TEMPLATE_CUSTOM_TEST] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );
}
