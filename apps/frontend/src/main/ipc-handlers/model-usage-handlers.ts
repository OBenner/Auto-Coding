import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type {
  IPCResult,
  ModelUsageSummary,
  ModelUsageTrendPoint,
  ModelMetrics,
  AgentMetrics,
  ModelUsageExportOptions,
  ModelLockConfig,
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
 * Execute a Python script and return the result.
 *
 * @param projectPath - Project root directory
 * @param scriptRelPath - Script path relative to projectPath (e.g., "apps/backend/analysis/model_usage_analytics.py")
 * @param args - Additional arguments passed to the script
 * @param parseJson - Whether to parse stdout as JSON (default: true). Set to false for scripts that output plain text.
 */
async function executePythonScript(
  projectPath: string,
  scriptRelPath: string,
  args: string[] = [],
  parseJson = true,
  timeoutMs = 60_000
): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonCmd = getConfiguredPythonPath();
    const [pythonCommand, pythonBaseArgs] = parsePythonCommand(pythonCmd);
    const scriptPath = path.join(projectPath, ...scriptRelPath.split('/'));

    const proc = spawn(pythonCommand, [...pythonBaseArgs, scriptPath, ...args], {
      cwd: projectPath,
      env: getAugmentedEnv(),
    });

    const timer = setTimeout(() => {
      proc.kill();
      reject(new Error(`Python script timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    proc.on('close', (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        reject(new Error(`Python script failed (code ${code}): ${stderr || stdout}`));
        return;
      }

      if (parseJson) {
        try {
          resolve(JSON.parse(stdout));
        } catch (error) {
          reject(new Error(`Failed to parse Python output: ${error}`));
        }
      } else {
        resolve({ success: true, output: stdout });
      }
    });

    proc.on('error', (error) => {
      reject(new Error(`Failed to spawn Python process: ${error.message}`));
    });
  });
}

/**
 * Register all model usage-related IPC handlers
 */
export function registerModelUsageHandlers(): void {
  // ============================================
  // Model Usage Analytics Operations
  // ============================================

  /**
   * Get model usage summary
   * Handler: getModelUsageSummary
   */
  ipcMain.handle(
    IPC_CHANNELS.MODEL_USAGE_GET_SUMMARY,
    async (
      _,
      projectId: string,
      startDate?: string,
      endDate?: string
    ): Promise<IPCResult<ModelUsageSummary>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Try to use cached aggregated data first
        const analyticsDir = path.join(project.path, '.auto-claude', 'analytics');

        // Include date filters in cache key to avoid returning stale results
        // Sanitize inputs to prevent path traversal attacks
        const sanitize = (v: string): string => v.replace(/[^a-zA-Z0-9._:-]/g, '_');
        const cacheKeyParts = ['model_usage_summary'];
        if (startDate) cacheKeyParts.push(`from_${sanitize(startDate)}`);
        if (endDate) cacheKeyParts.push(`to_${sanitize(endDate)}`);
        const summaryFile = path.join(analyticsDir, `${cacheKeyParts.join('__')}.json`);

        // Check if cached file exists and is recent (< 5 minutes old)
        let useCached = false;
        if (await fileExists(summaryFile)) {
          const stats = await fsPromises.stat(summaryFile);
          const fileAge = Date.now() - stats.mtimeMs;
          useCached = fileAge < 5 * 60 * 1000; // 5 minutes
        }

        let summary: ModelUsageSummary;

        if (useCached) {
          // Load from cache
          const content = await fsPromises.readFile(summaryFile, 'utf-8');
          summary = JSON.parse(content);
        } else {
          // Call Python backend to aggregate metrics
          const args = ['--get-summary'];
          if (startDate) args.push('--start-date', startDate);
          if (endDate) args.push('--end-date', endDate);

          summary = await executePythonScript(
            project.path,
            'apps/backend/analysis/model_usage_analytics.py',
            args
          );

          // Cache the result
          await fsPromises.mkdir(analyticsDir, { recursive: true });
          await fsPromises.writeFile(summaryFile, JSON.stringify(summary, null, 2), 'utf-8');
        }

        return { success: true, data: summary };
      } catch (error) {
        debugError('[Model Usage] Failed to get summary:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          success: false,
          error: `Failed to get model usage summary: ${errorMessage}`,
        };
      }
    }
  );

  /**
   * Get model usage trends over time
   */
  ipcMain.handle(
    IPC_CHANNELS.MODEL_USAGE_GET_TRENDS,
    async (
      _,
      projectId: string,
      windowDays: number = 30,
      granularity: string = 'daily'
    ): Promise<IPCResult<ModelUsageTrendPoint[]>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Call Python backend to get trends
        const trends = await executePythonScript(
          project.path,
          'apps/backend/analysis/model_usage_analytics.py',
          ['--get-trends', '--window-days', String(windowDays), '--granularity', granularity]
        );

        return { success: true, data: trends };
      } catch (error) {
        debugError('[Model Usage] Failed to get trends:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          success: false,
          error: `Failed to get model usage trends: ${errorMessage}`,
        };
      }
    }
  );

  // Helper to run an analytics script command for a project
  async function runAnalyticsCommand<T>(
    projectId: string,
    args: string[],
    errorLabel: string
  ): Promise<IPCResult<T>> {
    const project = projectStore.getProject(projectId);
    if (!project) {
      return { success: false, error: 'Project not found' };
    }

    try {
      const data = await executePythonScript(
        project.path,
        'apps/backend/analysis/model_usage_analytics.py',
        args
      );
      return { success: true, data };
    } catch (error) {
      debugError(`[Model Usage] ${errorLabel}:`, error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      return { success: false, error: `${errorLabel}: ${errorMessage}` };
    }
  }

  /**
   * Get metrics for a specific model
   */
  ipcMain.handle(
    IPC_CHANNELS.MODEL_USAGE_GET_MODEL_METRICS,
    async (_, projectId: string, model: string, startDate?: string, endDate?: string): Promise<IPCResult<ModelMetrics>> => {
      const args = ['--get-model-metrics', '--model', model];
      if (startDate) args.push('--start-date', startDate);
      if (endDate) args.push('--end-date', endDate);
      return runAnalyticsCommand(projectId, args, 'Failed to get model metrics');
    }
  );

  /**
   * Get metrics for a specific agent
   */
  ipcMain.handle(
    IPC_CHANNELS.MODEL_USAGE_GET_AGENT_METRICS,
    async (_, projectId: string, agentType: string, startDate?: string, endDate?: string): Promise<IPCResult<AgentMetrics>> => {
      const args = ['--get-agent-metrics', '--agent-type', agentType];
      if (startDate) args.push('--start-date', startDate);
      if (endDate) args.push('--end-date', endDate);
      return runAnalyticsCommand(projectId, args, 'Failed to get agent metrics');
    }
  );

  /**
   * Export model usage data to file
   */
  ipcMain.handle(
    IPC_CHANNELS.MODEL_USAGE_EXPORT,
    async (
      _,
      projectId: string,
      options: ModelUsageExportOptions
    ): Promise<IPCResult<string>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        const args = ['--export', '--format', options.format];

        if (options.filter) {
          if (options.filter.start_date) {
            args.push('--start-date', options.filter.start_date);
          }
          if (options.filter.end_date) {
            args.push('--end-date', options.filter.end_date);
          }
          if (options.filter.model) {
            args.push('--model', options.filter.model);
          }
          if (options.filter.agent_type) {
            args.push('--agent-type', options.filter.agent_type);
          }
        }

        if (options.output_path) {
          args.push('--output', options.output_path);
        }

        const result = await executePythonScript(
          project.path,
          'apps/backend/analysis/model_usage_analytics.py',
          args
        );

        return { success: true, data: result.output_path };
      } catch (error) {
        debugError('[Model Usage] Failed to export data:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          success: false,
          error: `Failed to export model usage data: ${errorMessage}`,
        };
      }
    }
  );

  // ============================================
  // Model Lock Operations
  // ============================================

  /**
   * List all model locks for a project
   */
  ipcMain.handle(
    IPC_CHANNELS.MODEL_LOCK_LIST,
    async (_, projectId: string): Promise<IPCResult<ModelLockConfig>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Read model_locks.json from project's .auto-claude directory
        const locksPath = path.join(project.path, '.auto-claude', 'model_locks.json');

        if (!(await fileExists(locksPath))) {
          // No locks configured
          return { success: true, data: { phaseModels: {}, agentModels: {} } };
        }

        const content = await fsPromises.readFile(locksPath, 'utf-8');
        const locks: ModelLockConfig = JSON.parse(content);

        return { success: true, data: locks };
      } catch (error) {
        debugError('[Model Lock] Failed to list locks:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          success: false,
          error: `Failed to list model locks: ${errorMessage}`,
        };
      }
    }
  );

  // Helper to run a model lock manager command for a project
  async function runLockCommand(
    projectId: string,
    commandArgs: string[],
    errorLabel: string
  ): Promise<IPCResult<{ success: boolean }>> {
    const project = projectStore.getProject(projectId);
    if (!project) {
      return { success: false, error: 'Project not found' };
    }

    try {
      const specDir = path.join(project.path, '.auto-claude', 'specs', projectId);
      await executePythonScript(
        project.path,
        'apps/backend/scripts/model_locks_manager.py',
        [...commandArgs.slice(0, 1), specDir, ...commandArgs.slice(1)],
        false
      );
      return { success: true, data: { success: true } };
    } catch (error) {
      debugError(`[Model Lock] ${errorLabel}:`, error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      return { success: false, error: `${errorLabel}: ${errorMessage}` };
    }
  }

  ipcMain.handle(IPC_CHANNELS.MODEL_LOCK_PHASE, async (_, projectId: string, phase: string, modelId: string) =>
    runLockCommand(projectId, ['lock-phase', phase, modelId], 'Failed to lock phase')
  );

  ipcMain.handle(IPC_CHANNELS.MODEL_LOCK_AGENT, async (_, projectId: string, agentType: string, modelId: string) =>
    runLockCommand(projectId, ['lock-agent', agentType, modelId], 'Failed to lock agent')
  );

  ipcMain.handle(IPC_CHANNELS.MODEL_UNLOCK_PHASE, async (_, projectId: string, phase: string) =>
    runLockCommand(projectId, ['unlock-phase', phase], 'Failed to unlock phase')
  );

  ipcMain.handle(IPC_CHANNELS.MODEL_UNLOCK_AGENT, async (_, projectId: string, agentType: string) =>
    runLockCommand(projectId, ['unlock-agent', agentType], 'Failed to unlock agent')
  );

  ipcMain.handle(IPC_CHANNELS.MODEL_LOCK_CLEAR, async (_, projectId: string) =>
    runLockCommand(projectId, ['clear'], 'Failed to clear locks')
  );
}
