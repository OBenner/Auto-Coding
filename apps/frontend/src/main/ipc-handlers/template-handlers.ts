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
async function getPythonEnv(projectPath: string): Promise<{ pythonPath: string; env: Record<string, string> }> {
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
}
