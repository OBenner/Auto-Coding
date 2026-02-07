import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import path from 'path';
import { IPC_CHANNELS, getSpecsDir } from '../../../shared/constants';
import type { IPCResult } from '../../../shared/types';
import { projectStore } from '../../project-store';
import { runPythonSubprocess } from '../github/utils/subprocess-runner';
import { parsePythonCommand } from '../../python-detector';

/**
 * Get context window statistics
 */
async function getContextStats(
  projectId: string,
  specId?: string
): Promise<any> {
  const project = projectStore.getProject(projectId);
  if (!project) {
    throw new Error('Project not found');
  }

  const pythonCmd = await parsePythonCommand(project.path);
  const args = [
    '-c',
    `
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path('${project.autoBuildPath.replace(/\\/g, '\\\\')}')
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from api.context_viewer import get_context_stats

spec_dir = ${specId ? `Path('${getSpecsDir()}') / '${specId}'` : 'None'}
stats = get_context_stats(spec_dir)
print(json.dumps(stats))
`.trim()
  ];

  const result = await runPythonSubprocess({
    pythonCmd,
    args,
    cwd: project.path,
    timeout: 30000
  });

  if (result.code !== 0) {
    throw new Error(`Failed to get context stats: ${result.stderr}`);
  }

  return JSON.parse(result.stdout.trim());
}

/**
 * Get token usage breakdown by file and category
 */
async function getTokenBreakdown(
  projectId: string,
  specId?: string
): Promise<any> {
  const project = projectStore.getProject(projectId);
  if (!project) {
    throw new Error('Project not found');
  }

  const pythonCmd = await parsePythonCommand(project.path);
  const args = [
    '-c',
    `
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path('${project.autoBuildPath.replace(/\\/g, '\\\\')}')
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from api.context_viewer import get_token_breakdown

spec_dir = ${specId ? `Path('${getSpecsDir()}') / '${specId}'` : 'None'}
breakdown = get_token_breakdown(spec_dir)
print(json.dumps(breakdown))
`.trim()
  ];

  const result = await runPythonSubprocess({
    pythonCmd,
    args,
    cwd: project.path,
    timeout: 30000
  });

  if (result.code !== 0) {
    throw new Error(`Failed to get token breakdown: ${result.stderr}`);
  }

  return JSON.parse(result.stdout.trim());
}

/**
 * Get file prioritization scores
 */
async function getPrioritizationScores(
  projectId: string,
  task?: string
): Promise<any> {
  const project = projectStore.getProject(projectId);
  if (!project) {
    throw new Error('Project not found');
  }

  const pythonCmd = await parsePythonCommand(project.path);
  const taskArg = task ? `'${task.replace(/'/g, "\\'")}'` : 'None';
  const args = [
    '-c',
    `
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path('${project.autoBuildPath.replace(/\\/g, '\\\\')}')
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from api.context_viewer import get_prioritization_scores

project_dir = Path('${project.path.replace(/\\/g, '\\\\')}')
task = ${taskArg}
scores = get_prioritization_scores(project_dir, task)
print(json.dumps(scores))
`.trim()
  ];

  const result = await runPythonSubprocess({
    pythonCmd,
    args,
    cwd: project.path,
    timeout: 30000
  });

  if (result.code !== 0) {
    throw new Error(`Failed to get prioritization scores: ${result.stderr}`);
  }

  return JSON.parse(result.stdout.trim());
}

/**
 * Get optimization effectiveness report
 */
async function getOptimizationReport(
  projectId: string,
  specId: string
): Promise<any> {
  const project = projectStore.getProject(projectId);
  if (!project) {
    throw new Error('Project not found');
  }

  const pythonCmd = await parsePythonCommand(project.path);
  const args = [
    '-c',
    `
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path('${project.autoBuildPath.replace(/\\/g, '\\\\')}')
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from api.context_viewer import get_optimization_report

spec_dir = Path('${getSpecsDir()}') / '${specId}'
report = get_optimization_report(spec_dir)
print(json.dumps(report))
`.trim()
  ];

  const result = await runPythonSubprocess({
    pythonCmd,
    args,
    cwd: project.path,
    timeout: 30000
  });

  if (result.code !== 0) {
    throw new Error(`Failed to get optimization report: ${result.stderr}`);
  }

  return JSON.parse(result.stdout.trim());
}

/**
 * Export complete context snapshot
 */
async function exportContextSnapshot(
  projectId: string,
  specId: string
): Promise<any> {
  const project = projectStore.getProject(projectId);
  if (!project) {
    throw new Error('Project not found');
  }

  const pythonCmd = await parsePythonCommand(project.path);
  const args = [
    '-c',
    `
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path('${project.autoBuildPath.replace(/\\/g, '\\\\')}')
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from api.context_viewer import export_context_snapshot

spec_dir = Path('${getSpecsDir()}') / '${specId}'
snapshot = export_context_snapshot(spec_dir)
print(json.dumps(snapshot))
`.trim()
  ];

  const result = await runPythonSubprocess({
    pythonCmd,
    args,
    cwd: project.path,
    timeout: 30000
  });

  if (result.code !== 0) {
    throw new Error(`Failed to export context snapshot: ${result.stderr}`);
  }

  return JSON.parse(result.stdout.trim());
}

/**
 * Register context viewer IPC handlers
 */
export function registerContextViewerHandlers(
  _getMainWindow: () => BrowserWindow | null
): void {
  // Get context statistics
  ipcMain.handle(
    IPC_CHANNELS.CONTEXT_GET_STATS,
    async (_, projectId: string, specId?: string): Promise<IPCResult<any>> => {
      try {
        const stats = await getContextStats(projectId, specId);
        return { success: true, data: stats };
      } catch (error: any) {
        return { success: false, error: error.message };
      }
    }
  );

  // Get token breakdown
  ipcMain.handle(
    IPC_CHANNELS.CONTEXT_GET_TOKEN_BREAKDOWN,
    async (_, projectId: string, specId?: string): Promise<IPCResult<any>> => {
      try {
        const breakdown = await getTokenBreakdown(projectId, specId);
        return { success: true, data: breakdown };
      } catch (error: any) {
        return { success: false, error: error.message };
      }
    }
  );

  // Get prioritization scores
  ipcMain.handle(
    IPC_CHANNELS.CONTEXT_GET_PRIORITIZATION_SCORES,
    async (_, projectId: string, task?: string): Promise<IPCResult<any>> => {
      try {
        const scores = await getPrioritizationScores(projectId, task);
        return { success: true, data: scores };
      } catch (error: any) {
        return { success: false, error: error.message };
      }
    }
  );

  // Get optimization report
  ipcMain.handle(
    IPC_CHANNELS.CONTEXT_GET_OPTIMIZATION_REPORT,
    async (_, projectId: string, specId: string): Promise<IPCResult<any>> => {
      try {
        const report = await getOptimizationReport(projectId, specId);
        return { success: true, data: report };
      } catch (error: any) {
        return { success: false, error: error.message };
      }
    }
  );

  // Export context snapshot
  ipcMain.handle(
    IPC_CHANNELS.CONTEXT_EXPORT_SNAPSHOT,
    async (_, projectId: string, specId: string): Promise<IPCResult<any>> => {
      try {
        const snapshot = await exportContextSnapshot(projectId, specId);
        return { success: true, data: snapshot };
      } catch (error: any) {
        return { success: false, error: error.message };
      }
    }
  );
}
