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
 * Execute Python script to get productivity analytics
 */
async function executePythonAnalytics(
  projectPath: string,
  scriptName: string,
  args: string[] = []
): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonPath = process.platform === 'win32' ? 'python' : 'python3';
    const scriptPath = path.join(
      projectPath,
      'apps',
      'backend',
      'analysis',
      scriptName
    );

    const proc = spawn(pythonPath, [scriptPath, ...args], {
      cwd: projectPath,
      env: { ...process.env, PYTHONPATH: path.join(projectPath, 'apps', 'backend') },
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
 * Register all productivity analytics-related IPC handlers
 */
export function registerAnalyticsHandlers(): void {
  // ============================================
  // Productivity Analytics Operations
  // ============================================

  /**
   * Get productivity analytics summary
   * Handler: getProductivityAnalytics
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
        // Try to use cached aggregated data first
        const analyticsDir = path.join(project.path, '.auto-claude', 'analytics');
        const summaryFile = path.join(analyticsDir, 'productivity_summary.json');

        // Check if cached file exists and is recent (< 5 minutes old)
        let useCached = false;
        if (await fileExists(summaryFile)) {
          const stats = await fsPromises.stat(summaryFile);
          const fileAge = Date.now() - stats.mtimeMs;
          useCached = fileAge < 5 * 60 * 1000; // 5 minutes
        }

        let summary: ProductivitySummary;

        if (useCached) {
          // Load from cache
          const content = await fsPromises.readFile(summaryFile, 'utf-8');
          summary = JSON.parse(content);
        } else {
          // Call Python backend to aggregate metrics
          const args = [];
          if (startDate) args.push('--start-date', startDate);
          if (endDate) args.push('--end-date', endDate);

          summary = await executePythonAnalytics(
            project.path,
            'productivity_analytics.py',
            ['--get-summary', ...args]
          );

          // Cache the result
          await fsPromises.mkdir(analyticsDir, { recursive: true });
          await fsPromises.writeFile(summaryFile, JSON.stringify(summary, null, 2), 'utf-8');
        }

        return { success: true, data: summary };
      } catch (error) {
        debugError('[Productivity Analytics] Failed to get summary:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          success: false,
          error: `Failed to get productivity summary: ${errorMessage}`,
        };
      }
    }
  );

  /**
   * Get productivity trends over time
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
        // Call Python backend to get trends
        const trends = await executePythonAnalytics(
          project.path,
          'productivity_analytics.py',
          ['--get-trends', '--window-days', String(windowDays), '--granularity', granularity]
        );

        return { success: true, data: trends };
      } catch (error) {
        debugError('[Productivity Analytics] Failed to get trends:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          success: false,
          error: `Failed to get productivity trends: ${errorMessage}`,
        };
      }
    }
  );

  /**
   * Export productivity analytics to file
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
        // Get summary data first
        const summaryResult = await ipcMain.emit(
          IPC_CHANNELS.PRODUCTIVITY_ANALYTICS_GET_SUMMARY,
          null,
          projectId,
          options.filter?.start_date,
          options.filter?.end_date
        );

        // Call Python backend to export
        const args = ['--export', '--format', options.format];

        if (options.output_path) {
          args.push('--output', options.output_path);
        }

        if (options.filter?.start_date) {
          args.push('--start-date', options.filter.start_date);
        }

        if (options.filter?.end_date) {
          args.push('--end-date', options.filter.end_date);
        }

        const result = await executePythonAnalytics(
          project.path,
          'productivity_analytics.py',
          args
        );

        const outputPath = result.output_path || options.output_path;

        return { success: true, data: outputPath };
      } catch (error) {
        debugError('[Productivity Analytics] Failed to export:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          success: false,
          error: `Failed to export productivity analytics: ${errorMessage}`,
        };
      }
    }
  );
}
