/**
 * Pattern IPC handlers
 *
 * Handlers for codebase pattern learning operations including listing patterns,
 * getting pattern details, approving, overriding, and deleting patterns.
 */

import { existsSync } from 'fs';
import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import { projectStore } from '../project-store';
import { joinPaths } from '../platform';
import { runPythonSubprocess } from './github/utils/subprocess-runner';
import { getRunnerEnv } from './github/utils/runner-env';
import { debugLog, debugError } from '../../shared/utils/debug-logger';

/**
 * Pattern information returned from backend (Python subprocess)
 */
interface BackendPattern {
  index: number;
  text: string;
  category?: string;
  confidence?: number;  // Backend returns 0.0-1.0
  reasoning?: string;
}

/**
 * Pattern information returned to frontend (with converted types)
 */
export interface Pattern {
  index: number;
  id: string;
  text: string;
  category?: string;
  confidence?: 'high' | 'medium' | 'low';
  reasoning?: string;
}

/**
 * Pattern category type
 */
export type PatternCategory = 'naming-conventions' | 'error-handling' | 'code-organization';

/**
 * Helper to get the backend directory path.
 *
 * Checks BACKEND_DIR env var first, then tries several ancestor depths
 * (dev vs production builds may nest __dirname differently).
 */
function getBackendDir(): string {
  // Allow explicit override via environment variable
  const envDir = process.env.BACKEND_DIR;
  if (envDir && existsSync(envDir)) {
    return envDir;
  }

  // Try multiple candidate ancestor depths (dev and prod builds differ)
  const depths = [4, 3, 5];
  for (const depth of depths) {
    const segments = Array(depth).fill('..');
    const candidate = joinPaths(__dirname, ...segments, 'apps', 'backend');
    if (existsSync(candidate)) {
      return candidate;
    }
  }

  // Fallback to original computed path
  const projectRoot = joinPaths(__dirname, '..', '..', '..', '..');
  return joinPaths(projectRoot, 'apps', 'backend');
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
  return joinPaths(projectPath, '.auto-claude', 'specs', specId);
}

/**
 * Safely parse JSON from subprocess stdout, extracting the last non-empty line
 * (Python may emit import warnings or other output before the actual JSON).
 */
function parseSubprocessJson<T>(stdout: string): T {
  const trimmed = stdout.trim();
  const lines = trimmed.split('\n');
  const lastLine = lines[lines.length - 1].trim();
  return JSON.parse(lastLine) as T;
}

/**
 * Convert numeric confidence (0.0-1.0 from backend) to string ('high'/'medium'/'low' for frontend)
 */
function confidenceToString(confidence: number | undefined): 'high' | 'medium' | 'low' | undefined {
  if (confidence === undefined) return undefined;
  if (confidence >= 0.8) return 'high';
  if (confidence >= 0.5) return 'medium';
  return 'low';
}

/**
 * Convert a backend pattern to a frontend Pattern with id and string confidence.
 */
function toFrontendPattern(p: BackendPattern): Pattern {
  return {
    index: p.index,
    id: String(p.index),
    text: p.text,
    category: p.category,
    confidence: p.confidence !== undefined ? confidenceToString(p.confidence) : undefined,
    reasoning: p.reasoning
  };
}

/**
 * Run a Python inline script in the backend directory and return parsed JSON output.
 *
 * Centralises the boilerplate shared by every pattern handler:
 * getPythonEnv → runPythonSubprocess → check exit code → parseSubprocessJson.
 */
async function runPatternScript<T>(
  pythonCode: string,
  label: string
): Promise<T> {
  const { pythonPath, env } = await getPythonEnv();
  const backendDir = getBackendDir();

  const { promise } = runPythonSubprocess<T>({
    pythonPath,
    args: ['-c', pythonCode],
    cwd: backendDir,
    env
  });

  const result = await promise;

  if (!result.success || result.exitCode !== 0) {
    debugError(`[${label}] Python subprocess failed:`, result.error);
    throw new Error(result.error || `Failed to ${label}`);
  }

  return parseSubprocessJson<T>(result.stdout);
}

/**
 * Build a Python inline script that imports sys, json, Path and sets sys.path.
 */
function pyPreamble(backendDir: string, extraImports: string = ''): string {
  return `
import sys
import json
from pathlib import Path

sys.path.insert(0, ${JSON.stringify(backendDir)})
${extraImports}`;
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

        const backendDir = getBackendDir();
        const specDir = getSpecDir(project.path, specId);

        const pythonCode = `${pyPreamble(backendDir, 'from memory.patterns import load_patterns')}
spec_dir = Path(${JSON.stringify(specDir)})
category_filter = ${JSON.stringify(category || null)}
patterns = load_patterns(spec_dir)
formatted_patterns = []
for i, pattern in enumerate(patterns, 1):
    text = pattern.split(" [category: ")[0] if " [category: " in pattern else pattern
    cat = None
    if " [category: " in pattern:
        cat = pattern.split(" [category: ")[1].split("]")[0]
    if category_filter is None or cat == category_filter:
        formatted_patterns.append({'index': i, 'text': text, 'category': cat})
print(json.dumps({'patterns': formatted_patterns}))
`;
        const data = await runPatternScript<{ patterns: BackendPattern[] }>(pythonCode, 'PATTERN_LIST');
        debugLog('[PATTERN_LIST] Returning', data.patterns.length, 'patterns');

        return { success: true, data: data.patterns.map(toFrontendPattern) };
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

        const backendDir = getBackendDir();
        const pythonCode = `${pyPreamble(backendDir, 'from integrations.graphiti.pattern_categorizer import get_pattern_categories')}
categories = get_pattern_categories()
print(json.dumps({'categories': categories}))
`;
        const data = await runPatternScript<{ categories: PatternCategory[] }>(pythonCode, 'PATTERN_GET_CATEGORIES');
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

        const backendDir = getBackendDir();
        const specDir = getSpecDir(project.path, specId);

        const pythonCode = `${pyPreamble(backendDir, 'from memory.patterns import load_patterns')}
spec_dir = Path(${JSON.stringify(specDir)})
pattern_index = ${patternIndex}
patterns = load_patterns(spec_dir)
if pattern_index < 1 or pattern_index > len(patterns):
    print(json.dumps({'error': 'Pattern index out of range'}))
    sys.exit(1)
pattern = patterns[pattern_index - 1]
print(json.dumps({'index': pattern_index, 'text': pattern}))
`;
        const data = await runPatternScript<BackendPattern>(pythonCode, 'PATTERN_GET_DETAILS');
        debugLog('[PATTERN_GET_DETAILS] Returning pattern:', data.index);

        return { success: true, data: toFrontendPattern(data) };
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

        const backendDir = getBackendDir();
        const specDir = getSpecDir(project.path, specId);

        const pythonCode = `${pyPreamble(backendDir, 'from cli.pattern_commands import approve_pattern')}
spec_dir = Path(${JSON.stringify(specDir)})
try:
    approve_pattern(spec_dir, ${patternIndex})
    print(json.dumps({"success": True}))
except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
`;
        await runPatternScript<{ success: boolean }>(pythonCode, 'PATTERN_APPROVE');
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

        const backendDir = getBackendDir();
        const specDir = getSpecDir(project.path, specId);

        const pythonCode = `${pyPreamble(backendDir, 'from cli.pattern_commands import override_pattern')}
spec_dir = Path(${JSON.stringify(specDir)})
new_text = ${JSON.stringify(newText)}
try:
    override_pattern(spec_dir, ${patternIndex}, new_text)
    print(json.dumps({"success": True}))
except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
`;
        await runPatternScript<{ success: boolean }>(pythonCode, 'PATTERN_OVERRIDE');
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

        const backendDir = getBackendDir();
        const specDir = getSpecDir(project.path, specId);

        const pythonCode = `${pyPreamble(backendDir, 'from cli.pattern_commands import delete_pattern')}
spec_dir = Path(${JSON.stringify(specDir)})
try:
    delete_pattern(spec_dir, ${patternIndex})
    print(json.dumps({"success": True}))
except Exception as e:
    print(json.dumps({"error": str(e)}))
    sys.exit(1)
`;
        await runPatternScript<{ success: boolean }>(pythonCode, 'PATTERN_DELETE');
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
