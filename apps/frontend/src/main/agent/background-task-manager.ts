import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { EventEmitter } from 'events';
import { BackgroundTaskState, BackgroundTask, BackgroundTaskStatus } from './task-state';
import { AgentProcessManager } from './agent-process';
import { debugLog, debugError } from '../../shared/utils/debug-logger';
import { stripAnsiCodes } from '../../shared/utils/ansi-sanitizer';
import { parsePythonCommand } from '../python-detector';
import { pythonEnvManager } from '../python-env-manager';

/** Maximum length for status messages displayed in progress UI */
const STATUS_MESSAGE_MAX_LENGTH = 200;

/**
 * Formats a raw log line for display as a status message.
 * Strips ANSI escape codes, extracts the first line, and truncates to max length.
 *
 * @param log - Raw log output from backend process
 * @returns Formatted status message safe for UI display
 */
function formatStatusMessage(log: string): string {
  if (!log) return '';
  return stripAnsiCodes(log.trim()).split('\n')[0].substring(0, STATUS_MESSAGE_MAX_LENGTH);
}

/**
 * Background task lifecycle management for long-running commands
 *
 * Manages the execution of background tasks via backend Python processes,
 * including task state tracking, output streaming, cancellation, and error handling.
 */
export class BackgroundTaskManager {
  private state: BackgroundTaskState;
  private processManager: AgentProcessManager;
  private emitter: EventEmitter;
  private processes: Map<string, ChildProcess> = new Map();

  constructor(state: BackgroundTaskState, processManager: AgentProcessManager, emitter: EventEmitter) {
    this.state = state;
    this.processManager = processManager;
    this.emitter = emitter;
  }

  /**
   * Ensure Python environment is ready before spawning processes.
   * Prevents the race condition where execution starts before dependencies are installed,
   * which would cause it to fall back to system Python and fail with ModuleNotFoundError.
   *
   * Delegates to AgentProcessManager.ensurePythonEnvReady() for the actual initialization.
   *
   * @param taskId - The task ID for error event emission
   * @returns true if environment is ready, false if initialization failed (error already emitted)
   */
  private async ensurePythonEnvReady(taskId: string): Promise<boolean> {
    const status = await this.processManager.ensurePythonEnvReady('BackgroundTaskManager');
    if (!status.ready) {
      this.emitter.emit(
        'background-task-error',
        taskId,
        `Python environment not ready: ${status.error || 'initialization failed'}`
      );
      return false;
    }
    return true;
  }

  /**
   * Start a background task
   *
   * @param taskId - Unique task identifier
   * @param command - Command to execute
   * @param workingDir - Working directory for command execution
   * @param timeout - Timeout in seconds (default: 14400 = 4 hours)
   * @returns Promise that resolves when task is started
   */
  async startTask(taskId: string, command: string, workingDir: string, timeout: number = 14400): Promise<void> {
    debugLog('[Background Task Manager] Starting task:', { taskId, command, workingDir, timeout });

    // Check Python environment readiness
    if (!(await this.ensurePythonEnvReady(taskId))) {
      return;
    }

    const autoBuildSource = await this.processManager.getAutoBuildSourcePath();
    if (!autoBuildSource) {
      debugError('[Background Task Manager] Auto-build source path not found');
      this.emitter.emit(
        'background-task-error',
        taskId,
        'Auto-build source path not found. Please configure it in App Settings.'
      );
      return;
    }

    // Create task metadata
    const task: BackgroundTask = {
      id: taskId,
      command,
      workingDir,
      status: 'pending',
      createdAt: new Date().toISOString(),
      startedAt: null,
      completedAt: null,
      timeout,
      output: '',
      error: null,
      exitCode: null,
      pid: null
    };

    // Add to state
    this.state.addTask(taskId, task);

    // Emit task-created event
    this.emitter.emit('background-task-created', taskId, task);

    // Get Python environment
    const { pythonPath, pythonArgs } = await parsePythonCommand(autoBuildSource);
    const venvPath = pythonEnvManager.getVenvPath(autoBuildSource);

    // Prepare MCP tools script path
    const mcpToolsPath = path.join(autoBuildSource, 'agents', 'tools_pkg', 'tools', 'background_task.py');

    // Build command to execute background task via Python
    const args = [
      ...pythonArgs,
      '-c',
      `
import sys
import json
sys.path.insert(0, '${autoBuildSource.replace(/\\/g, '\\\\')}')
from agents.tools_pkg.tools.background_task import BackgroundTaskManager
from pathlib import Path

manager = BackgroundTaskManager(Path('${workingDir.replace(/\\/g, '\\\\')}'), Path('${workingDir.replace(/\\/g, '\\\\')}'))
import asyncio
task_id = asyncio.run(manager.start_task('''${command.replace(/'/g, "\\'")}''', timeout=${timeout}, working_dir='${workingDir.replace(/\\/g, '\\\\')}'))
print(json.dumps({'task_id': task_id}))
      `.trim()
    ];

    // Spawn Python process
    const proc = spawn(pythonPath, args, {
      cwd: workingDir,
      env: {
        ...process.env,
        PYTHONPATH: autoBuildSource,
        VIRTUAL_ENV: venvPath
      },
      shell: false
    });

    // Store process
    this.processes.set(taskId, proc);

    // Update task state to running
    this.state.updateTask(taskId, {
      status: 'running',
      startedAt: new Date().toISOString(),
      pid: proc.pid || null
    });

    // Emit task-started event
    this.emitter.emit('background-task-started', taskId);

    // Handle stdout
    proc.stdout?.on('data', (data: Buffer) => {
      const output = data.toString('utf-8');
      debugLog('[Background Task Manager] Task output:', { taskId, output });

      // Append output to task
      const task = this.state.getTask(taskId);
      if (task) {
        const updatedOutput = task.output + output;
        this.state.updateTask(taskId, { output: updatedOutput });

        // Emit progress event
        this.emitter.emit('background-task-progress', taskId, {
          output: updatedOutput,
          message: formatStatusMessage(output)
        });
      }
    });

    // Handle stderr
    proc.stderr?.on('data', (data: Buffer) => {
      const error = data.toString('utf-8');
      debugError('[Background Task Manager] Task error:', { taskId, error });

      // Append error to task
      const task = this.state.getTask(taskId);
      if (task) {
        const updatedError = (task.error || '') + error;
        this.state.updateTask(taskId, { error: updatedError });

        // Emit error event
        this.emitter.emit('background-task-error', taskId, formatStatusMessage(error));
      }
    });

    // Handle process exit
    proc.on('exit', (code: number | null) => {
      debugLog('[Background Task Manager] Task exited:', { taskId, code });

      // Determine status based on exit code
      const status: BackgroundTaskStatus = code === 0 ? 'completed' : code === null ? 'cancelled' : 'failed';

      // Update task state
      this.state.updateTask(taskId, {
        status,
        completedAt: new Date().toISOString(),
        exitCode: code
      });

      // Clean up process reference
      this.processes.delete(taskId);

      // Emit completion event
      this.emitter.emit('background-task-complete', taskId, status, code);
    });

    // Handle process errors
    proc.on('error', (err: Error) => {
      debugError('[Background Task Manager] Task process error:', { taskId, error: err });

      // Update task state to failed
      this.state.updateTask(taskId, {
        status: 'failed',
        completedAt: new Date().toISOString(),
        error: (this.state.getTask(taskId)?.error || '') + `\nProcess error: ${err.message}`
      });

      // Clean up process reference
      this.processes.delete(taskId);

      // Emit error event
      this.emitter.emit('background-task-error', taskId, `Process error: ${err.message}`);
    });
  }

  /**
   * Cancel a running background task
   *
   * @param taskId - Task identifier
   * @returns Promise that resolves when task is cancelled
   */
  async cancelTask(taskId: string): Promise<void> {
    debugLog('[Background Task Manager] Cancelling task:', { taskId });

    const proc = this.processes.get(taskId);
    if (!proc) {
      debugError('[Background Task Manager] Task process not found:', { taskId });
      this.emitter.emit('background-task-error', taskId, 'Task process not found');
      return;
    }

    // Send SIGTERM to gracefully terminate
    proc.kill('SIGTERM');

    // Wait for process to exit (with timeout)
    const timeoutMs = 5000; // 5 seconds
    const startTime = Date.now();

    return new Promise((resolve) => {
      const checkInterval = setInterval(() => {
        if (!this.processes.has(taskId)) {
          // Process exited
          clearInterval(checkInterval);
          resolve();
        } else if (Date.now() - startTime > timeoutMs) {
          // Timeout - force kill
          debugLog('[Background Task Manager] Force killing task after timeout:', { taskId });
          proc.kill('SIGKILL');
          clearInterval(checkInterval);
          resolve();
        }
      }, 100);
    });
  }

  /**
   * Get the status of a background task
   *
   * @param taskId - Task identifier
   * @returns Task metadata or undefined if not found
   */
  getTaskStatus(taskId: string): BackgroundTask | undefined {
    return this.state.getTask(taskId);
  }

  /**
   * Get all running tasks
   *
   * @returns Array of running tasks
   */
  getRunningTasks(): BackgroundTask[] {
    return this.state.getRunningTasks();
  }

  /**
   * Get all tasks by status
   *
   * @param status - Task status to filter by
   * @returns Array of tasks with the specified status
   */
  getTasksByStatus(status: BackgroundTaskStatus): BackgroundTask[] {
    return this.state.getTasksByStatus(status);
  }

  /**
   * Check if a task is running
   *
   * @param taskId - Task identifier
   * @returns true if task is running, false otherwise
   */
  isTaskRunning(taskId: string): boolean {
    const task = this.state.getTask(taskId);
    return task?.status === 'running';
  }

  /**
   * Clean up completed/failed/cancelled tasks older than specified age
   *
   * @param maxAgeMs - Maximum age in milliseconds (default: 1 hour)
   */
  cleanupOldTasks(maxAgeMs: number = 3600000): void {
    const now = Date.now();
    const tasksToDelete: string[] = [];

    for (const taskId of this.state.getAllTaskIds()) {
      const task = this.state.getTask(taskId);
      if (!task || task.status === 'running') {
        continue;
      }

      const completedAt = task.completedAt ? new Date(task.completedAt).getTime() : 0;
      if (now - completedAt > maxAgeMs) {
        tasksToDelete.push(taskId);
      }
    }

    for (const taskId of tasksToDelete) {
      this.state.deleteTask(taskId);
      debugLog('[Background Task Manager] Cleaned up old task:', { taskId });
    }
  }

  /**
   * Stop all running tasks
   *
   * @returns Promise that resolves when all tasks are stopped
   */
  async stopAllTasks(): Promise<void> {
    const runningTasks = this.state.getRunningTasks();
    const cancelPromises = runningTasks.map((task) => this.cancelTask(task.id));
    await Promise.all(cancelPromises);
  }
}
