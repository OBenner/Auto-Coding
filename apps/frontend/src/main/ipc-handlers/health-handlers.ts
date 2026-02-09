/**
 * Project Health IPC Handlers
 *
 * Provides IPC handlers for retrieving project health metrics and status.
 * Calls Python backend's health_analyzer module for comprehensive health data.
 */

import { ipcMain, app } from 'electron';
import { spawn } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult, ProjectHealth, ProjectHealthSummary } from '../../shared/types';
import { projectStore } from '../project-store';
import { debugError } from '../../shared/utils/debug-logger';
import { parsePythonCommand } from '../python-detector';
import { getConfiguredPythonPath, pythonEnvManager } from '../python-env-manager';

/**
 * Execute the Python health_analyzer module to get project health data.
 *
 * @param command - The command to execute ('get_project_health' or 'get_health_summary')
 * @param projectPath - Path to the project directory
 * @param specDir - Optional path to the spec directory
 * @returns Promise<{success, data?, error?}>
 */
async function executeHealthAnalyzer(
  command: 'get_project_health' | 'get_health_summary',
  projectPath: string,
  specDir?: string
): Promise<{ success: boolean; data?: unknown; error?: string }> {
  // Use configured Python path
  const pythonCmd = getConfiguredPythonPath();

  // Find the health_analyzer.py script
  const possiblePaths = [
    // Packaged app paths (check FIRST for packaged builds)
    ...(app.isPackaged
      ? [path.join(process.resourcesPath, 'backend', 'analysis', 'health_analyzer.py')]
      : []),
    // Development paths
    path.resolve(__dirname, '..', '..', '..', '..', 'backend', 'analysis', 'health_analyzer.py'),
    path.resolve(process.cwd(), 'apps', 'backend', 'analysis', 'health_analyzer.py')
  ];

  let scriptPath: string | null = null;
  for (const p of possiblePaths) {
    if (fs.existsSync(p)) {
      scriptPath = p;
      break;
    }
  }

  if (!scriptPath) {
    if (process.env.DEBUG) {
      debugError('[HealthAnalyzer] health_analyzer.py script not found. Searched paths:', possiblePaths);
    }
    return { success: false, error: 'health_analyzer.py script not found' };
  }

  if (process.env.DEBUG) {
    console.log('[HealthAnalyzer] Using script at:', scriptPath);
  }

  // Build Python command to execute the module function
  const [pythonExe, baseArgs] = parsePythonCommand(pythonCmd);
  const args = [
    ...baseArgs,
    '-c',
    `
import sys
import json
sys.path.insert(0, '${path.dirname(scriptPath).replace(/\\/g, '\\\\')}')
from health_analyzer import ${command}

project_dir = r'${projectPath.replace(/\\/g, '\\\\')}'
spec_dir = ${specDir ? `r'${specDir.replace(/\\/g, '\\\\')}'` : 'None'}

try:
    result = ${command}(project_dir, spec_dir)
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({"error": str(e)}), file=sys.stderr)
    sys.exit(1)
`.trim()
  ];

  return new Promise((resolve) => {
    let resolved = false;
    const proc = spawn(pythonExe, args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      env: pythonEnvManager.getPythonEnv(),
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    // Timeout after 30 seconds
    const timeoutId = setTimeout(() => {
      if (!resolved) {
        resolved = true;
        proc.kill();
        resolve({ success: false, error: 'Health analysis timeout (30s)' });
      }
    }, 30000);

    proc.on('close', (code) => {
      if (resolved) return;
      resolved = true;
      clearTimeout(timeoutId);

      if (code === 0 && stdout) {
        try {
          const data = JSON.parse(stdout);
          if (data.error) {
            resolve({ success: false, error: data.error });
          } else {
            resolve({ success: true, data });
          }
        } catch (e) {
          resolve({ success: false, error: `Invalid JSON output: ${stdout}` });
        }
      } else {
        const errorMsg = stderr || stdout || `Process exited with code ${code}`;
        resolve({ success: false, error: errorMsg });
      }
    });

    proc.on('error', (err) => {
      if (resolved) return;
      resolved = true;
      clearTimeout(timeoutId);
      resolve({ success: false, error: err.message });
    });
  });
}

/**
 * Register all project health-related IPC handlers
 */
export function registerHealthHandlers(): void {
  // ============================================
  // Project Health Operations
  // ============================================

  /**
   * Get comprehensive project health data
   */
  ipcMain.handle(
    IPC_CHANNELS.HEALTH_GET_PROJECT_HEALTH,
    async (_, projectId: string): Promise<IPCResult<ProjectHealth>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Get spec directory (if exists)
        const specDir = path.join(project.path, '.auto-claude', 'specs');
        const specDirExists = fs.existsSync(specDir);

        // Execute Python health analyzer
        const result = await executeHealthAnalyzer(
          'get_project_health',
          project.path,
          specDirExists ? specDir : undefined
        );

        if (!result.success) {
          return { success: false, error: result.error || 'Failed to get project health' };
        }

        return { success: true, data: result.data as ProjectHealth };
      } catch (error) {
        debugError('[Health] Failed to get project health:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to get project health: ${errorMessage}` };
      }
    }
  );

  /**
   * Get condensed health summary for quick display
   */
  ipcMain.handle(
    IPC_CHANNELS.HEALTH_GET_SUMMARY,
    async (_, projectId: string): Promise<IPCResult<ProjectHealthSummary>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Get spec directory (if exists)
        const specDir = path.join(project.path, '.auto-claude', 'specs');
        const specDirExists = fs.existsSync(specDir);

        // Execute Python health analyzer
        const result = await executeHealthAnalyzer(
          'get_health_summary',
          project.path,
          specDirExists ? specDir : undefined
        );

        if (!result.success) {
          return { success: false, error: result.error || 'Failed to get health summary' };
        }

        return { success: true, data: result.data as ProjectHealthSummary };
      } catch (error) {
        debugError('[Health] Failed to get health summary:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to get health summary: ${errorMessage}` };
      }
    }
  );
}
