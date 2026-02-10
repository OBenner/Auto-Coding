import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import { execFile } from 'child_process';
import { promisify } from 'util';
import { IPC_CHANNELS, getSpecsDir } from '../../../shared/constants';
import type { IPCResult } from '../../../shared/types';
import { projectStore } from '../../project-store';
import { findPythonCommand, parsePythonCommand } from '../../python-detector';

const execFileAsync = promisify(execFile);

/**
 * Escape a string for safe embedding in Python string literals
 */
function escapePythonString(str: string): string {
  return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

/**
 * Run an inline Python script and return stdout
 */
async function runPythonScript(cwd: string, script: string): Promise<string> {
  const pythonCmd = findPythonCommand() || 'python';
  const [command, baseArgs] = parsePythonCommand(pythonCmd);

  const { stdout } = await execFileAsync(command, [...baseArgs, '-c', script], {
    cwd,
    timeout: 30000,
  });

  return stdout.trim();
}

/**
 * Build the sys.path setup preamble for inline Python scripts
 */
function buildPythonPreamble(backendPath: string): string {
  return `
import sys
import json
from pathlib import Path

backend_path = Path('${escapePythonString(backendPath)}')
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
`.trim();
}

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

  const preamble = buildPythonPreamble(project.autoBuildPath);
  const specDirExpr = specId ? `Path('${escapePythonString(getSpecsDir(project.autoBuildPath))}') / '${escapePythonString(specId)}'` : 'None';

  const script = `
${preamble}

from api.context_viewer import get_context_stats

spec_dir = ${specDirExpr}
stats = get_context_stats(spec_dir)
print(json.dumps(stats))
`.trim();

  const output = await runPythonScript(project.path, script);
  return JSON.parse(output);
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

  const preamble = buildPythonPreamble(project.autoBuildPath);
  const specDirExpr = specId ? `Path('${escapePythonString(getSpecsDir(project.autoBuildPath))}') / '${escapePythonString(specId)}'` : 'None';

  const script = `
${preamble}

from api.context_viewer import get_token_breakdown

spec_dir = ${specDirExpr}
breakdown = get_token_breakdown(spec_dir)
print(json.dumps(breakdown))
`.trim();

  const output = await runPythonScript(project.path, script);
  return JSON.parse(output);
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

  const preamble = buildPythonPreamble(project.autoBuildPath);
  const taskArg = task ? `'${escapePythonString(task)}'` : 'None';

  const script = `
${preamble}

from api.context_viewer import get_prioritization_scores

project_dir = Path('${escapePythonString(project.path)}')
task = ${taskArg}
scores = get_prioritization_scores(project_dir, task)
print(json.dumps(scores))
`.trim();

  const output = await runPythonScript(project.path, script);
  return JSON.parse(output);
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

  const preamble = buildPythonPreamble(project.autoBuildPath);

  const script = `
${preamble}

from api.context_viewer import get_optimization_report

spec_dir = Path('${escapePythonString(getSpecsDir(project.autoBuildPath))}') / '${escapePythonString(specId)}'
report = get_optimization_report(spec_dir)
print(json.dumps(report))
`.trim();

  const output = await runPythonScript(project.path, script);
  return JSON.parse(output);
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

  const preamble = buildPythonPreamble(project.autoBuildPath);

  const script = `
${preamble}

from api.context_viewer import export_context_snapshot

spec_dir = Path('${escapePythonString(getSpecsDir(project.autoBuildPath))}') / '${escapePythonString(specId)}'
snapshot = export_context_snapshot(spec_dir)
print(json.dumps(snapshot))
`.trim();

  const output = await runPythonScript(project.path, script);
  return JSON.parse(output);
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
