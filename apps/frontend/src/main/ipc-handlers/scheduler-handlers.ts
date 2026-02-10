/**
 * Scheduler IPC Handlers
 * =====================
 *
 * IPC handlers for scheduling builds and managing the build queue.
 * Integrates with the backend scheduler CLI commands.
 */

import { ipcMain, BrowserWindow } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import type {
  ScheduledBuild,
  SchedulePriority,
  BuildStatus,
  SchedulerStatus
} from '../../shared/types/scheduler';
import { spawn } from 'child_process';
import path from 'path';
import { existsSync, readFileSync } from 'fs';
import { projectStore } from '../project-store';
import { getIsolatedGitEnv } from '../utils/git-isolation';

/**
 * Find task and project by task ID
 * Reuses shared utility from task handlers
 */
async function findTaskAndProject(taskId: string): Promise<{
  task: import('../../shared/types').Task | null;
  project: import('../../shared/types').Project | null;
}> {
  const projects = projectStore.getProjects();

  for (const project of projects) {
    const tasks = projectStore.getTasks(project.id);
    const task = tasks.find(t => t.id === taskId);

    if (task) {
      return { task, project };
    }
  }

  return { task: null, project: null };
}

/**
 * Get Python path and auto-build source path
 */
function getPythonEnvironment(): {
  pythonPath: string;
  autoBuildSource: string | null;
} {
  // Get Python path from environment or use python3
  const pythonPath = process.env.PYTHON_PATH || 'python3';

  // Get auto-build source from environment
  const autoBuildSource = process.env.AUTO_BUILD_SOURCE || null;

  return { pythonPath, autoBuildSource };
}

/**
 * Execute a scheduler CLI command asynchronously
 * Uses spawn instead of spawnSync to avoid blocking the Electron main thread
 */
function executeSchedulerCommand(
  projectPath: string,
  args: string[]
): Promise<{ success: boolean; stdout: string; stderr: string; code: number | null }> {
  const { pythonPath, autoBuildSource } = getPythonEnvironment();

  if (!autoBuildSource) {
    return Promise.resolve({
      success: false,
      stdout: '',
      stderr: 'Auto-build source path not configured',
      code: -1
    });
  }

  const runpyPath = path.join(autoBuildSource, 'run.py');

  if (!existsSync(runpyPath)) {
    return Promise.resolve({
      success: false,
      stdout: '',
      stderr: `run.py not found at ${runpyPath}`,
      code: -1
    });
  }

  return new Promise((resolve) => {
    try {
      const child = spawn(
        pythonPath,
        [runpyPath, ...args],
        {
          cwd: projectPath,
          env: { ...process.env, ...getIsolatedGitEnv() },
          timeout: 30000
        }
      );

      let stdout = '';
      let stderr = '';

      child.stdout.on('data', (data) => { stdout += data.toString(); });
      child.stderr.on('data', (data) => { stderr += data.toString(); });

      child.on('close', (code) => {
        resolve({
          success: code === 0,
          stdout,
          stderr,
          code
        });
      });

      child.on('error', (error) => {
        resolve({
          success: false,
          stdout,
          stderr: error.message,
          code: -1
        });
      });
    } catch (error) {
      resolve({
        success: false,
        stdout: '',
        stderr: error instanceof Error ? error.message : String(error),
        code: -1
      });
    }
  });
}

/**
 * Read scheduled builds from storage
 */
function getScheduledBuilds(projectPath: string): ScheduledBuild[] {
  const schedulerPath = path.join(projectPath, '.auto-claude', 'scheduler', 'schedule.json');

  if (!existsSync(schedulerPath)) {
    return [];
  }

  try {
    const content = readFileSync(schedulerPath, 'utf-8');
    const data = JSON.parse(content);
    return data.builds || [];
  } catch (error) {
    console.error('[Scheduler] Failed to read builds:', error);
    return [];
  }
}

/**
 * Register scheduler IPC handlers
 */
export function registerSchedulerHandlers(
  getMainWindow: () => BrowserWindow | null
): void {
  /**
   * Schedule a build for a specific task
   */
  ipcMain.handle(
    IPC_CHANNELS.SCHEDULER_SCHEDULE_BUILD,
    async (
      _,
      taskId: string,
      scheduledTime: string | null,
      priority: SchedulePriority,
      dependencies: string[] = []
    ): Promise<IPCResult<{ buildId: string }>> => {
      const { task, project } = await findTaskAndProject(taskId);

      if (!task || !project) {
        return { success: false, error: 'Task or project not found' };
      }

      // Build CLI arguments
      const args = ['schedule', task.specId, '--priority', priority];

      if (scheduledTime) {
        args.push('--time', scheduledTime);
      }

      if (dependencies.length > 0) {
        args.push('--dependencies', ...dependencies);
      }

      // Execute schedule command
      const result = await executeSchedulerCommand(project.path, args);

      if (!result.success) {
        return {
          success: false,
          error: result.stderr || 'Failed to schedule build'
        };
      }

      // Parse output to get build ID (extract from CLI output or read from storage)
      const builds = getScheduledBuilds(project.path);
      const latestBuild = builds[builds.length - 1]; // Get most recent

      if (!latestBuild) {
        return {
          success: false,
          error: 'Build scheduled but could not retrieve build ID'
        };
      }

      // Notify renderer
      const mainWindow = getMainWindow();
      if (mainWindow) {
        mainWindow.webContents.send(
          IPC_CHANNELS.SCHEDULER_BUILD_SCHEDULED,
          project.id,
          latestBuild
        );
      }

      return {
        success: true,
        data: { buildId: latestBuild.id }
      };
    }
  );

  /**
   * Get scheduler status and queue
   */
  ipcMain.handle(
    IPC_CHANNELS.SCHEDULER_GET_STATUS,
    async (_, projectId: string): Promise<IPCResult<SchedulerStatus>> => {
      const project = projectStore.getProjects().find(p => p.id === projectId);

      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      // Execute status command
      const result = await executeSchedulerCommand(
        project.path,
        ['schedule', '--status']
      );

      if (!result.success) {
        return {
          success: false,
          error: result.stderr || 'Failed to get scheduler status'
        };
      }

      // Parse builds from storage
      const builds = getScheduledBuilds(project.path);

      // Calculate status summary
      const byStatus: Record<BuildStatus, number> = {
        pending: 0,
        queued: 0,
        running: 0,
        completed: 0,
        failed: 0,
        cancelled: 0,
        retrying: 0
      };

      builds.forEach(build => {
        byStatus[build.status]++;
      });

      const status: SchedulerStatus = {
        schedulerRunning: true, // TODO: Parse from CLI output
        totalBuilds: builds.length,
        byStatus,
        builds,
        nextBuild: builds.find(b =>
          b.status === 'pending' || b.status === 'queued'
        ) || null
      };

      return {
        success: true,
        data: status
      };
    }
  );

  /**
   * Cancel a scheduled build
   */
  ipcMain.handle(
    IPC_CHANNELS.SCHEDULER_CANCEL_BUILD,
    async (_, buildId: string, projectId: string): Promise<IPCResult> => {
      const project = projectStore.getProjects().find(p => p.id === projectId);

      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      // Execute cancel command
      const result = await executeSchedulerCommand(
        project.path,
        ['schedule', '--cancel', buildId]
      );

      if (!result.success) {
        return {
          success: false,
          error: result.stderr || 'Failed to cancel build'
        };
      }

      // Notify renderer
      const mainWindow = getMainWindow();
      if (mainWindow) {
        mainWindow.webContents.send(
          IPC_CHANNELS.SCHEDULER_BUILD_CANCELLED,
          projectId,
          buildId
        );
      }

      return { success: true };
    }
  );

  /**
   * Start the scheduler service
   */
  ipcMain.handle(
    IPC_CHANNELS.SCHEDULER_START,
    async (_, projectId: string): Promise<IPCResult> => {
      const project = projectStore.getProjects().find(p => p.id === projectId);

      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      // Execute start command
      const result = await executeSchedulerCommand(
        project.path,
        ['schedule', '--start']
      );

      if (!result.success) {
        return {
          success: false,
          error: result.stderr || 'Failed to start scheduler'
        };
      }

      // Notify renderer
      const mainWindow = getMainWindow();
      if (mainWindow) {
        mainWindow.webContents.send(
          IPC_CHANNELS.SCHEDULER_STATUS_CHANGED,
          projectId,
          true
        );
      }

      return { success: true };
    }
  );

  /**
   * Stop the scheduler service
   */
  ipcMain.handle(
    IPC_CHANNELS.SCHEDULER_STOP,
    async (_, projectId: string): Promise<IPCResult> => {
      const project = projectStore.getProjects().find(p => p.id === projectId);

      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      // Execute stop command
      const result = await executeSchedulerCommand(
        project.path,
        ['schedule', '--stop']
      );

      if (!result.success) {
        return {
          success: false,
          error: result.stderr || 'Failed to stop scheduler'
        };
      }

      // Notify renderer
      const mainWindow = getMainWindow();
      if (mainWindow) {
        mainWindow.webContents.send(
          IPC_CHANNELS.SCHEDULER_STATUS_CHANGED,
          projectId,
          false
        );
      }

      return { success: true };
    }
  );

  /**
   * Get scheduled builds for a project
   */
  ipcMain.handle(
    IPC_CHANNELS.SCHEDULER_GET_BUILDS,
    async (_, projectId: string): Promise<IPCResult<ScheduledBuild[]>> => {
      const project = projectStore.getProjects().find(p => p.id === projectId);

      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      const builds = getScheduledBuilds(project.path);

      return {
        success: true,
        data: builds
      };
    }
  );
}
