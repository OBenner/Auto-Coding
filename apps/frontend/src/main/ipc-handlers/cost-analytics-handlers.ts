import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type {
  IPCResult,
  CostSummary,
  CostTrendPoint,
} from '../../shared/types';
import { promises as fsPromises } from 'fs';
import path from 'path';
import { projectStore } from '../project-store';
import { debugError } from '../../shared/utils/debug-logger';
import { spawn } from 'child_process';
import { parsePythonCommand } from '../python-detector';
import { getConfiguredPythonPath } from '../python-env-manager';
import { getAugmentedEnv } from '../env-utils';

/**
 * Helper to check if a file exists asynchronously
 */
async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fsPromises.access(filePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Execute Python script to get cost analytics
 */
async function executePythonCostAnalytics(
  projectPath: string,
  scriptName: string,
  args: string[] = []
): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonCmd = getConfiguredPythonPath();
    const [pythonCommand, pythonBaseArgs] = parsePythonCommand(pythonCmd);
    const scriptPath = path.join(
      projectPath,
      'apps',
      'backend',
      'analysis',
      scriptName
    );

    const proc = spawn(pythonCommand, [...pythonBaseArgs, scriptPath, ...args], {
      cwd: projectPath,
      env: getAugmentedEnv(),
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Python script failed: ${stderr}`));
        return;
      }

      try {
        const result = JSON.parse(stdout);
        resolve(result);
      } catch (error) {
        reject(new Error(`Failed to parse Python output: ${error}`));
      }
    });

    proc.on('error', (error) => {
      reject(new Error(`Failed to spawn Python process: ${error.message}`));
    });
  });
}

/**
 * Register all cost analytics-related IPC handlers
 */
export function registerCostHandlers(): void {
  // ============================================
  // Cost Analytics Operations
  // ============================================

  /**
   * Get cost analytics summary
   * Handler: getCostSummary
   */
  ipcMain.handle(
    'costAnalytics:getSummary',
    async (
      _,
      projectId: string,
      startDate?: string,
      endDate?: string
    ): Promise<IPCResult<CostSummary>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Try to use cached aggregated data first
        const analyticsDir = path.join(project.path, '.auto-claude', 'analytics');

        // Include date filters in cache key to avoid returning stale results
        const cacheKeyParts = ['cost_summary'];
        if (startDate) cacheKeyParts.push(`from_${startDate}`);
        if (endDate) cacheKeyParts.push(`to_${endDate}`);
        const summaryFile = path.join(analyticsDir, `${cacheKeyParts.join('__')}.json`);

        // Check if cached file exists and is recent (< 5 minutes old)
        let useCached = false;
        if (await fileExists(summaryFile)) {
          const stats = await fsPromises.stat(summaryFile);
          const fileAge = Date.now() - stats.mtimeMs;
          useCached = fileAge < 5 * 60 * 1000; // 5 minutes
        }

        let summary: CostSummary;

        if (useCached) {
          // Load from cache
          const content = await fsPromises.readFile(summaryFile, 'utf-8');
          summary = JSON.parse(content);
        } else {
          // Call Python backend to aggregate metrics
          const args = ['--get-summary'];
          if (startDate) args.push('--start-date', startDate);
          if (endDate) args.push('--end-date', endDate);

          summary = await executePythonCostAnalytics(
            project.path,
            'cost_analytics.py',
            args
          );

          // Cache the result
          await fsPromises.mkdir(analyticsDir, { recursive: true });
          await fsPromises.writeFile(summaryFile, JSON.stringify(summary, null, 2), 'utf-8');
        }

        return { success: true, data: summary };
      } catch (error) {
        debugError('[Cost Analytics] Failed to get summary:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          success: false,
          error: `Failed to get cost summary: ${errorMessage}`,
        };
      }
    }
  );

  /**
   * Get cost trends over time
   */
  ipcMain.handle(
    'costAnalytics:getTrends',
    async (
      _,
      projectId: string,
      windowDays: number = 30,
      granularity: string = 'daily'
    ): Promise<IPCResult<CostTrendPoint[]>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Call Python backend to get trends
        const trends = await executePythonCostAnalytics(
          project.path,
          'cost_analytics.py',
          ['--get-trends', '--window-days', String(windowDays), '--granularity', granularity]
        );

        return { success: true, data: trends };
      } catch (error) {
        debugError('[Cost Analytics] Failed to get trends:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          success: false,
          error: `Failed to get cost trends: ${errorMessage}`,
        };
      }
    }
  );

  /**
   * Export cost analytics to file
   */
  ipcMain.handle(
    'costAnalytics:export',
    async (
      _,
      projectId: string,
      format: 'json' | 'csv',
      outputPath?: string,
      startDate?: string,
      endDate?: string
    ): Promise<IPCResult<string>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Build Python command arguments
        const args = ['--export', '--format', format];

        if (outputPath) {
          args.push('--output', outputPath);
        }

        if (startDate) {
          args.push('--start-date', startDate);
        }

        if (endDate) {
          args.push('--end-date', endDate);
        }

        // Call Python backend to export
        const result = await executePythonCostAnalytics(
          project.path,
          'cost_analytics.py',
          args
        );

        // Extract output path - handle both string and object shapes from Python
        let filePath: string | undefined;
        if (typeof result === 'string') {
          filePath = result;
        } else if (result && typeof result.output_path === 'string') {
          filePath = result.output_path;
        } else {
          filePath = outputPath;
        }

        if (!filePath) {
          throw new Error('No output path returned from export operation');
        }

        return { success: true, data: filePath };
      } catch (error) {
        debugError('[Cost Analytics] Failed to export:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          success: false,
          error: `Failed to export cost analytics: ${errorMessage}`,
        };
      }
    }
  );
}
