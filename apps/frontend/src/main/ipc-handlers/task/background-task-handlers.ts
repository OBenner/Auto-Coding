import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult } from '../../../shared/types';
import { BackgroundTaskManager } from '../../agent/background-task-manager';
import { BackgroundTaskState, BackgroundTask, BackgroundTaskStatus } from '../../agent/task-state';
import { AgentManager } from '../../agent';
import { debugLog, debugError } from '../../../shared/utils/debug-logger';

// Singleton instances for background task management
let backgroundTaskState: BackgroundTaskState | null = null;
let backgroundTaskManager: BackgroundTaskManager | null = null;

/**
 * Initialize background task management system
 * @param agentManager - The agent manager instance for accessing process management
 */
function initializeBackgroundTaskManager(agentManager: AgentManager): BackgroundTaskManager {
  if (!backgroundTaskState) {
    backgroundTaskState = new BackgroundTaskState();
    debugLog('[Background Task Handlers] Initialized BackgroundTaskState');
  }

  if (!backgroundTaskManager) {
    // Access the process manager and emitter from agent manager
    // Note: This requires AgentManager to expose these properties
    // For now, we'll create a new instance - this should be refactored to use AgentManager's instances
    const { EventEmitter } = require('events');
    const emitter = new EventEmitter();

    // Forward events to IPC channels
    emitter.on('background-task-created', (taskId: string, task: BackgroundTask) => {
      debugLog('[Background Task Handlers] Task created:', taskId);
      // Event will be sent by the manager's internal handlers
    });

    emitter.on('background-task-started', (taskId: string) => {
      debugLog('[Background Task Handlers] Task started:', taskId);
    });

    emitter.on('background-task-progress', (taskId: string, progress: { output: string; message: string }) => {
      debugLog('[Background Task Handlers] Task progress:', taskId, progress.message);
    });

    emitter.on('background-task-complete', (taskId: string, status: BackgroundTaskStatus, code: number | null) => {
      debugLog('[Background Task Handlers] Task complete:', taskId, status, code);
    });

    emitter.on('background-task-error', (taskId: string, error: string) => {
      debugError('[Background Task Handlers] Task error:', taskId, error);
    });

    // Get process manager from agent manager (cast to any to access private property)
    // This is a temporary solution - AgentManager should expose a public method
    const processManager = (agentManager as any).processManager;

    backgroundTaskManager = new BackgroundTaskManager(
      backgroundTaskState,
      processManager,
      emitter
    );

    debugLog('[Background Task Handlers] Initialized BackgroundTaskManager');
  }

  return backgroundTaskManager;
}

/**
 * Register background task IPC handlers for task status queries
 */
export function registerBackgroundTaskHandlers(agentManager: AgentManager): void {
  debugLog('[Background Task Handlers] Registering IPC handlers');

  /**
   * Start a background task
   * @param taskId - Unique task identifier
   * @param command - Command to execute
   * @param workingDir - Working directory for command execution
   * @param timeout - Timeout in seconds (default: 14400 = 4 hours)
   */
  ipcMain.handle(
    IPC_CHANNELS.BACKGROUND_TASK_START,
    async (
      _,
      taskId: string,
      command: string,
      workingDir: string,
      timeout?: number
    ): Promise<IPCResult<{ taskId: string }>> => {
      debugLog('[IPC] BACKGROUND_TASK_START called:', { taskId, command, workingDir, timeout });

      try {
        const manager = initializeBackgroundTaskManager(agentManager);
        await manager.startTask(taskId, command, workingDir, timeout);

        return {
          success: true,
          data: { taskId }
        };
      } catch (error) {
        debugError('[IPC] BACKGROUND_TASK_START error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
  );

  /**
   * Cancel a running background task
   * @param taskId - Task identifier
   */
  ipcMain.handle(
    IPC_CHANNELS.BACKGROUND_TASK_CANCEL,
    async (_, taskId: string): Promise<IPCResult<void>> => {
      debugLog('[IPC] BACKGROUND_TASK_CANCEL called:', { taskId });

      try {
        const manager = initializeBackgroundTaskManager(agentManager);
        await manager.cancelTask(taskId);

        return { success: true };
      } catch (error) {
        debugError('[IPC] BACKGROUND_TASK_CANCEL error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
  );

  /**
   * Get the status of a background task
   * @param taskId - Task identifier
   */
  ipcMain.handle(
    IPC_CHANNELS.BACKGROUND_TASK_GET_STATUS,
    async (_, taskId: string): Promise<IPCResult<BackgroundTask>> => {
      debugLog('[IPC] BACKGROUND_TASK_GET_STATUS called:', { taskId });

      try {
        const manager = initializeBackgroundTaskManager(agentManager);
        const task = manager.getTaskStatus(taskId);

        if (!task) {
          return {
            success: false,
            error: `Task not found: ${taskId}`
          };
        }

        return {
          success: true,
          data: task
        };
      } catch (error) {
        debugError('[IPC] BACKGROUND_TASK_GET_STATUS error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
  );

  /**
   * Get the output of a background task
   * @param taskId - Task identifier
   */
  ipcMain.handle(
    IPC_CHANNELS.BACKGROUND_TASK_GET_OUTPUT,
    async (_, taskId: string): Promise<IPCResult<{ output: string; error: string | null }>> => {
      debugLog('[IPC] BACKGROUND_TASK_GET_OUTPUT called:', { taskId });

      try {
        const manager = initializeBackgroundTaskManager(agentManager);
        const task = manager.getTaskStatus(taskId);

        if (!task) {
          return {
            success: false,
            error: `Task not found: ${taskId}`
          };
        }

        return {
          success: true,
          data: {
            output: task.output,
            error: task.error
          }
        };
      } catch (error) {
        debugError('[IPC] BACKGROUND_TASK_GET_OUTPUT error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
  );

  /**
   * List all running background tasks
   */
  ipcMain.handle(
    IPC_CHANNELS.BACKGROUND_TASK_LIST_RUNNING,
    async (): Promise<IPCResult<BackgroundTask[]>> => {
      debugLog('[IPC] BACKGROUND_TASK_LIST_RUNNING called');

      try {
        const manager = initializeBackgroundTaskManager(agentManager);
        const tasks = manager.getRunningTasks();

        return {
          success: true,
          data: tasks
        };
      } catch (error) {
        debugError('[IPC] BACKGROUND_TASK_LIST_RUNNING error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
  );

  /**
   * List background tasks by status
   * @param status - Task status to filter by
   */
  ipcMain.handle(
    IPC_CHANNELS.BACKGROUND_TASK_LIST_BY_STATUS,
    async (_, status: BackgroundTaskStatus): Promise<IPCResult<BackgroundTask[]>> => {
      debugLog('[IPC] BACKGROUND_TASK_LIST_BY_STATUS called:', { status });

      try {
        const manager = initializeBackgroundTaskManager(agentManager);
        const tasks = manager.getTasksByStatus(status);

        return {
          success: true,
          data: tasks
        };
      } catch (error) {
        debugError('[IPC] BACKGROUND_TASK_LIST_BY_STATUS error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }
  );

  debugLog('[Background Task Handlers] All IPC handlers registered successfully');
}
