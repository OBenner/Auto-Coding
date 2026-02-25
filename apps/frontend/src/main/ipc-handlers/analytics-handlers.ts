import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type {
  IPCResult,
  ProductivitySummary,
  ProductivityTrendPoint,
  ProductivityAnalyticsExportOptions,
} from '../../shared/types';
import { promises as fsPromises } from 'fs';
import path from 'path';
import { projectStore } from '../project-store';
import { debugError } from '../../shared/utils/debug-logger';
import { spawn } from 'child_process';
import { parsePythonCommand } from '../python-detector';
import { getConfiguredPythonPath } from '../python-env-manager';
import { getAugmentedEnv } from '../env-utils';

// =============================================================================
// Native spec reading — no Python subprocess needed for summary/trends
// =============================================================================

interface SpecMetrics {
  spec_id: string;
  spec_name: string;
  workflow_type: string;
  complexity: string;
  status: string;
  created_at: string | null;
  completed_at: string | null;
  duration_seconds: number;
  total_subtasks: number;
  completed_subtasks: number;
  failed_subtasks: number;
  qa_iterations: number;
  qa_status: string;
  unique_sessions: number;
}

function parseTimestamp(ts: string | null | undefined): Date | null {
  if (!ts) return null;
  try {
    const d = new Date(ts);
    return isNaN(d.getTime()) ? null : d;
  } catch {
    return null;
  }
}

function countUniqueSessions(plan: Record<string, any>): number {
  const ids = new Set<string>();
  for (const phase of plan.phases ?? []) {
    for (const subtask of phase.subtasks ?? []) {
      if (subtask.session_id) ids.add(subtask.session_id);
    }
  }
  return ids.size;
}

function estimateTimeSaved(m: SpecMetrics): number {
  // Only estimate savings for specs with real build times.
  // When duration_seconds <= 0 (no created_at timestamp), AI time is unknown,
  // so counting the full manual estimate would inflate the total.
  if (m.duration_seconds <= 0) return 0;

  const perSubtask: Record<string, number> = { simple: 0.5, standard: 1.5, complex: 3.0 };
  const manual = m.completed_subtasks * (perSubtask[m.complexity] ?? 1.5);
  const ai = m.duration_seconds / 3600;
  return Math.max(0, manual - ai);
}

async function extractSpecMetrics(specDir: string): Promise<SpecMetrics | null> {
  const planFile = path.join(specDir, 'implementation_plan.json');
  try {
    const raw = await fsPromises.readFile(planFile, 'utf-8');
    const plan = JSON.parse(raw);

    const specId = path.basename(specDir);
    const specName: string = plan.feature ?? specId;
    const workflowType: string = plan.workflow_type ?? 'feature';

    let totalSubtasks = 0;
    let completedSubtasks = 0;
    let failedSubtasks = 0;
    let hasInProgress = false;

    for (const phase of plan.phases ?? []) {
      for (const subtask of phase.subtasks ?? []) {
        totalSubtasks++;
        const st = subtask.status ?? 'pending';
        if (st === 'completed') completedSubtasks++;
        else if (st === 'failed') failedSubtasks++;
        else if (st === 'in_progress') hasInProgress = true;
      }
    }

    const complexity = totalSubtasks <= 3 ? 'simple' : totalSubtasks >= 10 ? 'complex' : 'standard';

    const planStatus: string = plan.status ?? 'pending';
    let status: string;
    if (planStatus === 'completed' || planStatus === 'done' || (totalSubtasks > 0 && completedSubtasks === totalSubtasks)) {
      status = 'completed';
    } else if (completedSubtasks > 0 || hasInProgress) {
      status = 'in_progress';
    } else {
      status = 'pending';
    }

    const createdAt = parseTimestamp(plan.created_at);
    const updatedAt = parseTimestamp(plan.updated_at);

    let completedAt: Date | null = null;
    let durationSeconds = 0;
    if (createdAt) {
      if (status === 'completed' && updatedAt) {
        completedAt = updatedAt;
        durationSeconds = (completedAt.getTime() - createdAt.getTime()) / 1000;
      } else if (status === 'in_progress') {
        durationSeconds = (Date.now() - createdAt.getTime()) / 1000;
      }
    }

    const qaSignoff = plan.qa_signoff ?? {};
    const qaIterations: number = qaSignoff.qa_session ?? 0;
    const qaStatus: string = qaSignoff.status ?? 'pending';
    const uniqueSessions = countUniqueSessions(plan);

    return {
      spec_id: specId,
      spec_name: specName,
      workflow_type: workflowType,
      complexity,
      status,
      created_at: createdAt?.toISOString() ?? null,
      completed_at: completedAt?.toISOString() ?? null,
      duration_seconds: durationSeconds,
      total_subtasks: totalSubtasks,
      completed_subtasks: completedSubtasks,
      failed_subtasks: failedSubtasks,
      qa_iterations: qaIterations,
      qa_status: qaStatus,
      unique_sessions: uniqueSessions,
    };
  } catch {
    return null;
  }
}

function isCompleted(m: SpecMetrics): boolean {
  return m.status === 'completed' || (
    m.total_subtasks > 0 &&
    m.completed_subtasks === m.total_subtasks &&
    m.qa_status === 'approved'
  );
}

async function aggregateSummary(
  projectPath: string,
  startDate?: string,
  endDate?: string
): Promise<ProductivitySummary> {
  const specsDir = path.join(projectPath, '.auto-claude', 'specs');
  const now = new Date().toISOString();
  const empty: ProductivitySummary = {
    period_start: startDate ?? now,
    period_end: endDate ?? now,
    total_specs: 0,
    completed_specs: 0,
    in_progress_specs: 0,
    failed_specs: 0,
    total_time_saved_hours: 0,
    total_build_time_hours: 0,
    average_success_rate: 0,
    first_attempt_success_rate: 0,
    specs_by_type: {},
    specs_by_complexity: {},
    average_subtasks_per_spec: 0,
    average_qa_iterations: 0,
    total_subtasks_completed: 0,
    specs: [],
  };

  let entries: string[];
  try {
    entries = await fsPromises.readdir(specsDir);
  } catch {
    return empty;
  }

  const startMs = startDate ? new Date(startDate).getTime() : -Infinity;
  const endMs = endDate ? new Date(endDate).getTime() : Infinity;

  const allSpecs: SpecMetrics[] = [];

  for (const entry of entries) {
    const specDir = path.join(specsDir, entry);
    const stat = await fsPromises.stat(specDir).catch(() => null);
    if (!stat?.isDirectory()) continue;

    const m = await extractSpecMetrics(specDir);
    if (!m) continue;

    // Date filter
    if (m.created_at) {
      const ts = new Date(m.created_at).getTime();
      if (ts < startMs || ts > endMs) continue;
    }

    allSpecs.push(m);
  }

  if (allSpecs.length === 0) return empty;

  const dates = allSpecs.map(s => s.created_at).filter(Boolean) as string[];
  const periodStart = startDate ?? (dates.length > 0 ? dates.reduce((a, b) => a < b ? a : b) : now);
  const periodEnd = endDate ?? (dates.length > 0 ? dates.reduce((a, b) => a > b ? a : b) : now);

  const completed = allSpecs.filter(isCompleted);
  const inProgress = allSpecs.filter(s => s.status === 'in_progress');
  const failed = allSpecs.filter(s => s.status === 'failed');

  const totalTimeSaved = allSpecs.reduce((sum, s) => sum + estimateTimeSaved(s), 0);
  const totalBuildTime = allSpecs.reduce((sum, s) => sum + s.duration_seconds / 3600, 0);

  const firstAttempt = completed.filter(s => s.qa_iterations <= 1).length;
  const firstAttemptRate = completed.length > 0 ? firstAttempt / completed.length : 0;
  const avgSuccess = allSpecs.length > 0 ? completed.length / allSpecs.length : 0;

  const byType: Record<string, number> = {};
  const byComplexity: Record<string, number> = {};
  for (const s of allSpecs) {
    byType[s.workflow_type] = (byType[s.workflow_type] ?? 0) + 1;
    byComplexity[s.complexity] = (byComplexity[s.complexity] ?? 0) + 1;
  }

  const totalSubtasksCompleted = allSpecs.reduce((sum, s) => sum + s.completed_subtasks, 0);
  const avgSubtasks = allSpecs.length > 0 ? totalSubtasksCompleted / allSpecs.length : 0;
  const totalQa = allSpecs.reduce((sum, s) => sum + s.qa_iterations, 0);
  const avgQa = completed.length > 0 ? totalQa / completed.length : 0;

  return {
    period_start: periodStart,
    period_end: periodEnd,
    total_specs: allSpecs.length,
    completed_specs: completed.length,
    in_progress_specs: inProgress.length,
    failed_specs: failed.length,
    total_time_saved_hours: Math.round(totalTimeSaved * 100) / 100,
    total_build_time_hours: Math.round(totalBuildTime * 100) / 100,
    average_success_rate: Math.round(avgSuccess * 1000) / 1000,
    first_attempt_success_rate: Math.round(firstAttemptRate * 1000) / 1000,
    specs_by_type: byType,
    specs_by_complexity: byComplexity,
    average_subtasks_per_spec: Math.round(avgSubtasks * 10) / 10,
    average_qa_iterations: Math.round(avgQa * 10) / 10,
    total_subtasks_completed: totalSubtasksCompleted,
    specs: allSpecs,
  };
}

async function aggregateTrends(
  projectPath: string,
  windowDays: number,
  granularity: string
): Promise<ProductivityTrendPoint[]> {
  const endDate = new Date();
  const startDate = new Date(endDate.getTime() - windowDays * 24 * 60 * 60 * 1000);

  const summary = await aggregateSummary(
    projectPath,
    startDate.toISOString(),
    endDate.toISOString()
  );

  const periodMs =
    granularity === 'weekly' ? 7 * 24 * 60 * 60 * 1000 :
    granularity === 'monthly' ? 30 * 24 * 60 * 60 * 1000 :
    24 * 60 * 60 * 1000; // daily

  const trends: ProductivityTrendPoint[] = [];
  let cur = startDate.getTime();

  while (cur <= endDate.getTime()) {
    const periodEnd = cur + periodMs;
    const periodSpecs = (summary.specs as SpecMetrics[]).filter(s => {
      if (!s.created_at) return false;
      const ts = new Date(s.created_at).getTime();
      return ts >= cur && ts < periodEnd;
    });

    if (periodSpecs.length > 0) {
      const completed = periodSpecs.filter(isCompleted).length;
      const timeSaved = periodSpecs.reduce((sum, s) => sum + estimateTimeSaved(s), 0);
      trends.push({
        date: new Date(cur).toISOString(),
        total_specs: periodSpecs.length,
        completed_specs: completed,
        time_saved_hours: Math.round(timeSaved * 100) / 100,
        success_rate: Math.round((completed / periodSpecs.length) * 1000) / 1000,
      });
    }

    cur = periodEnd;
  }

  return trends;
}

// =============================================================================
// Python fallback for export only
// =============================================================================

const PYTHON_TIMEOUT_MS = 30_000;

async function executePythonAnalytics(
  projectPath: string,
  scriptName: string,
  args: string[] = []
): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonCmd = getConfiguredPythonPath();
    const [pythonCommand, pythonBaseArgs] = parsePythonCommand(pythonCmd);
    const scriptPath = path.join(projectPath, 'apps', 'backend', 'analysis', scriptName);

    const proc = spawn(pythonCommand, [...pythonBaseArgs, scriptPath, ...args], {
      cwd: projectPath,
      env: getAugmentedEnv(),
    });

    let stdout = '';
    let stderr = '';
    let settled = false;

    const settle = (fn: () => void) => { if (!settled) { settled = true; fn(); } };

    const timer = setTimeout(() => {
      settle(() => { proc.kill(); reject(new Error('Python analytics timed out')); });
    }, PYTHON_TIMEOUT_MS);

    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });

    proc.on('close', (code) => {
      clearTimeout(timer);
      settle(() => {
        if (code !== 0) { reject(new Error(`Python failed (exit ${code}): ${stderr.slice(0, 500)}`)); return; }
        try { resolve(JSON.parse(stdout)); } catch (e) { reject(new Error(`Parse error: ${e}`)); }
      });
    });

    proc.on('error', (error) => {
      clearTimeout(timer);
      settle(() => { reject(new Error(`Spawn error: ${error.message}`)); });
    });
  });
}

// =============================================================================
// IPC Handlers
// =============================================================================

export function registerAnalyticsHandlers(): void {

  /**
   * Get productivity analytics summary — reads spec JSON files directly
   */
  ipcMain.handle(
    IPC_CHANNELS.PRODUCTIVITY_ANALYTICS_GET_SUMMARY,
    async (
      _,
      projectId: string,
      startDate?: string,
      endDate?: string
    ): Promise<IPCResult<ProductivitySummary>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        const summary = await aggregateSummary(project.path, startDate, endDate);
        return { success: true, data: summary };
      } catch (error) {
        debugError('[Productivity Analytics] Failed to get summary:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to get productivity summary: ${errorMessage}` };
      }
    }
  );

  /**
   * Get productivity trends over time — reads spec JSON files directly
   */
  ipcMain.handle(
    IPC_CHANNELS.PRODUCTIVITY_ANALYTICS_GET_TRENDS,
    async (
      _,
      projectId: string,
      windowDays: number = 30,
      granularity: string = 'daily'
    ): Promise<IPCResult<ProductivityTrendPoint[]>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        const trends = await aggregateTrends(project.path, windowDays, granularity);
        return { success: true, data: trends };
      } catch (error) {
        debugError('[Productivity Analytics] Failed to get trends:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to get productivity trends: ${errorMessage}` };
      }
    }
  );

  /**
   * Export productivity analytics to file (still uses Python for CSV generation)
   */
  ipcMain.handle(
    IPC_CHANNELS.PRODUCTIVITY_ANALYTICS_EXPORT,
    async (
      _,
      projectId: string,
      options: ProductivityAnalyticsExportOptions
    ): Promise<IPCResult<string>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        const args = ['--export', '--format', options.format];
        if (options.output_path) args.push('--output', options.output_path);
        if (options.filter?.start_date) args.push('--start-date', options.filter.start_date);
        if (options.filter?.end_date) args.push('--end-date', options.filter.end_date);

        const result = await executePythonAnalytics(project.path, 'productivity_analytics.py', args);

        let outputPath: string | undefined;
        if (typeof result === 'string') outputPath = result;
        else if (result?.output_path) outputPath = result.output_path;
        else outputPath = options.output_path;

        if (!outputPath) throw new Error('No output path returned');
        return { success: true, data: outputPath };
      } catch (error) {
        debugError('[Productivity Analytics] Failed to export:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to export: ${errorMessage}` };
      }
    }
  );
}
