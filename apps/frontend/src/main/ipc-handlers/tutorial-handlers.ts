import { ipcMain, BrowserWindow } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import { spawn } from 'child_process';
import type { ChildProcess } from 'child_process';
import { projectStore } from '../project-store';
import { debugError } from '../../shared/utils/debug-logger';
import { parsePythonCommand } from '../python-detector';
import { getConfiguredPythonPath } from '../python-env-manager';
import { getAugmentedEnv } from '../env-utils';
import path from 'path';

// =============================================================================
// Tutorial Runner State Management
// =============================================================================

interface TutorialSession {
  process: ChildProcess;
  projectPath: string;
  startTime: Date;
  status: 'running' | 'completed' | 'cancelled' | 'failed';
  currentPhase: string | null;
}

// Global tutorial session (only one tutorial can run at a time)
let tutorialSession: TutorialSession | null = null;

// =============================================================================
// Tutorial IPC Handlers
// =============================================================================

/**
 * Start tutorial runner
 * Spawns Python tutorial_runner.py process and streams events back to renderer
 */
function registerTutorialStartHandler(getMainWindow: () => BrowserWindow | null): void {
  ipcMain.handle(IPC_CHANNELS.TUTORIAL_START, async (_event, projectPath: string): Promise<IPCResult<{ sessionStarted: boolean }>> => {
    try {
      // Check if tutorial is already running
      if (tutorialSession && tutorialSession.status === 'running') {
        return {
          success: false,
          error: 'Tutorial is already running. Please complete or cancel the current tutorial first.',
        };
      }

      // Validate project path
      if (!projectPath) {
        return {
          success: false,
          error: 'Project path is required',
        };
      }

      // Get configured Python path
      const pythonPath = getConfiguredPythonPath();
      const backendPath = path.join(projectPath, 'apps', 'backend');
      const tutorialRunnerPath = path.join(backendPath, 'tutorial', 'tutorial_runner_cli.py');

      // Create Python command
      const [pythonCommand, pythonBaseArgs] = parsePythonCommand(pythonPath);
      const args = [...pythonBaseArgs, tutorialRunnerPath, '--project-dir', projectPath, '--json-events'];

      // Spawn Python process
      const env = getAugmentedEnv();
      const pythonProcess = spawn(pythonCommand, args, {
        cwd: backendPath,
        env,
        stdio: ['ignore', 'pipe', 'pipe'],
      });

      // Initialize tutorial session
      tutorialSession = {
        process: pythonProcess,
        projectPath,
        startTime: new Date(),
        status: 'running',
        currentPhase: null,
      };

      const mainWindow = getMainWindow();

      // Handle stdout (JSON events)
      pythonProcess.stdout?.on('data', (data: Buffer) => {
        const output = data.toString().trim();
        const lines = output.split('\n');

        for (const line of lines) {
          if (!line.trim()) continue;

          try {
            // Parse JSON event
            const event = JSON.parse(line);

            // Update session state
            if (event.type === 'phase_start') {
              if (tutorialSession) {
                tutorialSession.currentPhase = event.phase;
              }
              mainWindow?.webContents.send(IPC_CHANNELS.TUTORIAL_PHASE_START, event);
            } else if (event.type === 'phase_progress') {
              mainWindow?.webContents.send(IPC_CHANNELS.TUTORIAL_PHASE_PROGRESS, event);
            } else if (event.type === 'phase_complete') {
              mainWindow?.webContents.send(IPC_CHANNELS.TUTORIAL_PHASE_COMPLETE, event);
            } else if (event.type === 'complete') {
              if (tutorialSession) {
                tutorialSession.status = 'completed';
              }
              mainWindow?.webContents.send(IPC_CHANNELS.TUTORIAL_COMPLETE, event);
            } else if (event.type === 'error') {
              if (tutorialSession) {
                tutorialSession.status = 'failed';
              }
              mainWindow?.webContents.send(IPC_CHANNELS.TUTORIAL_ERROR, event);
            }
          } catch (err) {
            // Non-JSON output, likely debug logs - ignore
            console.debug('[Tutorial] Python output:', line);
          }
        }
      });

      // Handle stderr (errors)
      pythonProcess.stderr?.on('data', (data: Buffer) => {
        const errorOutput = data.toString().trim();
        debugError('[Tutorial] Python stderr:', errorOutput);

        // Send error event to renderer
        mainWindow?.webContents.send(IPC_CHANNELS.TUTORIAL_ERROR, {
          type: 'error',
          message: errorOutput,
        });
      });

      // Handle process exit
      pythonProcess.on('close', (code: number | null) => {
        console.debug(`[Tutorial] Python process exited with code ${code}`);

        if (tutorialSession) {
          if (code === 0 && tutorialSession.status === 'running') {
            tutorialSession.status = 'completed';
          } else if (code !== 0 && tutorialSession.status === 'running') {
            tutorialSession.status = 'failed';
            mainWindow?.webContents.send(IPC_CHANNELS.TUTORIAL_ERROR, {
              type: 'error',
              message: `Tutorial process exited with code ${code}`,
            });
          }
        }
      });

      return {
        success: true,
        data: { sessionStarted: true },
      };
    } catch (error) {
      debugError('[Tutorial] Start error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to start tutorial',
      };
    }
  });
}

/**
 * Get tutorial status
 * Returns current status of the tutorial runner
 */
function registerTutorialGetStatusHandler(): void {
  ipcMain.handle(IPC_CHANNELS.TUTORIAL_GET_STATUS, async (): Promise<IPCResult<{
    isRunning: boolean;
    status: string | null;
    currentPhase: string | null;
    projectPath: string | null;
  }>> => {
    try {
      if (!tutorialSession) {
        return {
          success: true,
          data: {
            isRunning: false,
            status: null,
            currentPhase: null,
            projectPath: null,
          },
        };
      }

      return {
        success: true,
        data: {
          isRunning: tutorialSession.status === 'running',
          status: tutorialSession.status,
          currentPhase: tutorialSession.currentPhase,
          projectPath: tutorialSession.projectPath,
        },
      };
    } catch (error) {
      debugError('[Tutorial] Get status error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get tutorial status',
      };
    }
  });
}

/**
 * Cancel tutorial
 * Kills the tutorial runner process
 */
function registerTutorialCancelHandler(getMainWindow: () => BrowserWindow | null): void {
  ipcMain.handle(IPC_CHANNELS.TUTORIAL_CANCEL, async (): Promise<IPCResult<{ cancelled: boolean }>> => {
    try {
      if (!tutorialSession || tutorialSession.status !== 'running') {
        return {
          success: false,
          error: 'No tutorial is currently running',
        };
      }

      // Kill Python process
      tutorialSession.process.kill('SIGTERM');
      tutorialSession.status = 'cancelled';

      // Notify renderer
      const mainWindow = getMainWindow();
      mainWindow?.webContents.send(IPC_CHANNELS.TUTORIAL_ERROR, {
        type: 'cancelled',
        message: 'Tutorial cancelled by user',
      });

      // Clean up session after a delay (to allow process to exit cleanly)
      setTimeout(() => {
        tutorialSession = null;
      }, 1000);

      return {
        success: true,
        data: { cancelled: true },
      };
    } catch (error) {
      debugError('[Tutorial] Cancel error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to cancel tutorial',
      };
    }
  });
}

// =============================================================================
// Registration Function
// =============================================================================

/**
 * Register all tutorial IPC handlers
 */
export function registerTutorialHandlers(getMainWindow: () => BrowserWindow | null): void {
  registerTutorialStartHandler(getMainWindow);
  registerTutorialGetStatusHandler();
  registerTutorialCancelHandler(getMainWindow);

  console.warn('[IPC] Tutorial handlers registered');
}
