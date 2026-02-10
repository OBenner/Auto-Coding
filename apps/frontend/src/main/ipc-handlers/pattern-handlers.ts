/**
 * Pattern IPC handlers
 *
 * Handlers for codebase pattern learning operations including listing patterns,
 * getting pattern details, approving, overriding, and deleting patterns.
 */

import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import path from 'path';
import { projectStore } from '../project-store';
import { runPythonSubprocess } from './github/utils/subprocess-runner';
import { getRunnerEnv } from './github/utils/runner-env';
import { debugLog, debugError } from '../../shared/utils/debug-logger';

/**
 * Pattern information returned from backend
 */
export interface Pattern {
  index: number;
  text: string;
  category?: string;
  confidence?: number;
  reasoning?: string;
}

/**
 * Pattern category type
 */
export type PatternCategory = 'naming-conventions' | 'error-handling' | 'code-organization';

/**
 * Helper to get the backend directory path
 */
function getBackendDir(): string {
  // The backend is at apps/backend/ from the project root
  const projectRoot = path.resolve(__dirname, '../../../..');
  return path.join(projectRoot, 'apps', 'backend');
}

/**
 * Helper to get Python executable path and environment
 */
async function getPythonEnv(): Promise<{ pythonPath: string; env: Record<string, string> }> {
  const env = await getRunnerEnv();
  const pythonPath = 'python';

  return {
    pythonPath,
    env
  };
}

/**
 * Helper to get spec directory path from project
 */
function getSpecDir(projectPath: string, specId: string): string {
  return path.join(projectPath, '.auto-claude', 'specs', specId);
}

/**
 * Register pattern-related IPC handlers
 */
export function registerPatternHandlers(): void {
  /**
   * List all learned patterns, optionally filtered by category
   */
  ipcMain.handle(
    IPC_CHANNELS.PATTERN_LIST,
    async (
      _,
      projectId: string,
      specId: string,
      category?: PatternCategory
    ): Promise<IPCResult<Pattern[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[PATTERN_LIST] Listing patterns for spec:', specId, 'category:', category);

        const { pythonPath, env } = await getPythonEnv();
        const backendDir = getBackendDir();
        const specDir = getSpecDir(project.path, specId);

        // Build Python script to list patterns
        const args = [
          '-c',
          `
import sys
import json
from pathlib import Path

sys.path.insert(0, ${JSON.stringify(backendDir)})

from cli.pattern_commands import list_patterns
from memory.patterns import load_patterns

spec_dir = Path(${JSON.stringify(specDir)})
category = ${JSON.stringify(category || null)}

# Load patterns from file-based memory
patterns = load_patterns(spec_dir)

# Format patterns with index and metadata
formatted_patterns = []
for i, pattern in enumerate(patterns, 1):
    formatted_patterns.append({
        'index': i,
        'text': pattern
    })

print(json.dumps({'patterns': formatted_patterns}))
          `
        ];

        const { promise } = runPythonSubprocess<{ patterns: Pattern[] }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[PATTERN_LIST] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to list patterns' };
        }

        const data = JSON.parse(result.stdout.trim()) as { patterns: Pattern[] };
        debugLog('[PATTERN_LIST] Returning', data.patterns.length, 'patterns');

        return { success: true, data: data.patterns };
      } catch (error) {
        debugError('[PATTERN_LIST] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Get available pattern categories
   */
  ipcMain.handle(
    IPC_CHANNELS.PATTERN_GET_CATEGORIES,
    async (): Promise<IPCResult<PatternCategory[]>> => {
      try {
        debugLog('[PATTERN_GET_CATEGORIES] Getting pattern categories');

        const { pythonPath, env } = await getPythonEnv();
        const backendDir = getBackendDir();

        const args = [
          '-c',
          `
import sys
import json

sys.path.insert(0, ${JSON.stringify(backendDir)})

from integrations.graphiti.pattern_categorizer import get_pattern_categories

categories = get_pattern_categories()
print(json.dumps({'categories': categories}))
          `
        ];

        const { promise } = runPythonSubprocess<{ categories: PatternCategory[] }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[PATTERN_GET_CATEGORIES] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to get categories' };
        }

        const data = JSON.parse(result.stdout.trim()) as { categories: PatternCategory[] };
        debugLog('[PATTERN_GET_CATEGORIES] Returning', data.categories.length, 'categories');

        return { success: true, data: data.categories };
      } catch (error) {
        debugError('[PATTERN_GET_CATEGORIES] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Get detailed information about a specific pattern
   */
  ipcMain.handle(
    IPC_CHANNELS.PATTERN_GET_DETAILS,
    async (
      _,
      projectId: string,
      specId: string,
      patternIndex: number
    ): Promise<IPCResult<Pattern>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[PATTERN_GET_DETAILS] Getting pattern details:', patternIndex);

        const { pythonPath, env } = await getPythonEnv();
        const backendDir = getBackendDir();
        const specDir = getSpecDir(project.path, specId);

        const args = [
          '-c',
          `
import sys
import json
from pathlib import Path

sys.path.insert(0, ${JSON.stringify(backendDir)})

from memory.patterns import load_patterns

spec_dir = Path(${JSON.stringify(specDir)})
pattern_index = ${patternIndex}

patterns = load_patterns(spec_dir)

if pattern_index < 1 or pattern_index > len(patterns):
    print(json.dumps({'error': 'Pattern index out of range'}))
    sys.exit(1)

pattern = patterns[pattern_index - 1]

result = {
    'index': pattern_index,
    'text': pattern
}

print(json.dumps(result))
          `
        ];

        const { promise } = runPythonSubprocess<Pattern>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[PATTERN_GET_DETAILS] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to get pattern details' };
        }

        const pattern = JSON.parse(result.stdout.trim()) as Pattern;
        debugLog('[PATTERN_GET_DETAILS] Returning pattern:', pattern.index);

        return { success: true, data: pattern };
      } catch (error) {
        debugError('[PATTERN_GET_DETAILS] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Approve a pattern (mark as user-approved)
   */
  ipcMain.handle(
    IPC_CHANNELS.PATTERN_APPROVE,
    async (
      _,
      projectId: string,
      specId: string,
      patternIndex: number
    ): Promise<IPCResult<void>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[PATTERN_APPROVE] Approving pattern:', patternIndex);

        const { pythonPath, env } = await getPythonEnv();
        const backendDir = getBackendDir();
        const specDir = getSpecDir(project.path, specId);

        const args = [
          '-c',
          `
import sys
from pathlib import Path

sys.path.insert(0, ${JSON.stringify(backendDir)})

from cli.pattern_commands import approve_pattern

spec_dir = Path(${JSON.stringify(specDir)})
pattern_index = ${patternIndex}

try:
    approve_pattern(spec_dir, pattern_index)
    print('{"success": true}')
except Exception as e:
    print(f'{{"error": "{str(e)}"}}')
    sys.exit(1)
          `
        ];

        const { promise } = runPythonSubprocess<{ success: boolean }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[PATTERN_APPROVE] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to approve pattern' };
        }

        debugLog('[PATTERN_APPROVE] Pattern approved successfully');
        return { success: true, data: undefined };
      } catch (error) {
        debugError('[PATTERN_APPROVE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Override a pattern with new text
   */
  ipcMain.handle(
    IPC_CHANNELS.PATTERN_OVERRIDE,
    async (
      _,
      projectId: string,
      specId: string,
      patternIndex: number,
      newText: string
    ): Promise<IPCResult<void>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[PATTERN_OVERRIDE] Overriding pattern:', patternIndex);

        const { pythonPath, env } = await getPythonEnv();
        const backendDir = getBackendDir();
        const specDir = getSpecDir(project.path, specId);

        const args = [
          '-c',
          `
import sys
from pathlib import Path

sys.path.insert(0, ${JSON.stringify(backendDir)})

from cli.pattern_commands import override_pattern

spec_dir = Path(${JSON.stringify(specDir)})
pattern_index = ${patternIndex}
new_text = ${JSON.stringify(newText)}

try:
    override_pattern(spec_dir, pattern_index, new_text)
    print('{"success": true}')
except Exception as e:
    print(f'{{"error": "{str(e)}"}}')
    sys.exit(1)
          `
        ];

        const { promise } = runPythonSubprocess<{ success: boolean }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[PATTERN_OVERRIDE] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to override pattern' };
        }

        debugLog('[PATTERN_OVERRIDE] Pattern overridden successfully');
        return { success: true, data: undefined };
      } catch (error) {
        debugError('[PATTERN_OVERRIDE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Delete a pattern
   */
  ipcMain.handle(
    IPC_CHANNELS.PATTERN_DELETE,
    async (
      _,
      projectId: string,
      specId: string,
      patternIndex: number
    ): Promise<IPCResult<void>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        debugLog('[PATTERN_DELETE] Deleting pattern:', patternIndex);

        const { pythonPath, env } = await getPythonEnv();
        const backendDir = getBackendDir();
        const specDir = getSpecDir(project.path, specId);

        const args = [
          '-c',
          `
import sys
from pathlib import Path

sys.path.insert(0, ${JSON.stringify(backendDir)})

from cli.pattern_commands import delete_pattern

spec_dir = Path(${JSON.stringify(specDir)})
pattern_index = ${patternIndex}

try:
    delete_pattern(spec_dir, pattern_index)
    print('{"success": true}')
except Exception as e:
    print(f'{{"error": "{str(e)}"}}')
    sys.exit(1)
          `
        ];

        const { promise } = runPythonSubprocess<{ success: boolean }>({
          pythonPath,
          args,
          cwd: backendDir,
          env
        });

        const result = await promise;

        if (!result.success || result.exitCode !== 0) {
          debugError('[PATTERN_DELETE] Python subprocess failed:', result.error);
          return { success: false, error: result.error || 'Failed to delete pattern' };
        }

        debugLog('[PATTERN_DELETE] Pattern deleted successfully');
        return { success: true, data: undefined };
      } catch (error) {
        debugError('[PATTERN_DELETE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  debugLog('[Pattern Handlers] All pattern IPC handlers registered');
}
