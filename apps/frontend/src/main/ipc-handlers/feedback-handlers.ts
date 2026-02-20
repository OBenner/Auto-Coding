/**
 * Feedback IPC Handlers
 *
 * Handles user feedback submission for adaptive agent learning.
 * Records accept/reject/modify feedback to preference profiles.
 *
 * Feedback types:
 * - accepted: User accepted the agent's output without changes
 * - rejected: User rejected the agent's output entirely
 * - modified: User modified the agent's output before accepting
 */

import { ipcMain, app } from 'electron';
import { spawn } from 'child_process';
import * as path from 'path';
import { fileURLToPath } from 'url';
import * as fs from 'fs';
import type { BrowserWindow } from 'electron';

// ESM-compatible __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import { parsePythonCommand } from '../python-detector';
import { getConfiguredPythonPath, pythonEnvManager } from '../python-env-manager';

/**
 * Feedback submission request from renderer process
 */
interface FeedbackRequest {
  feedbackType: 'accepted' | 'rejected' | 'modified';
  taskId?: string;
  agentType?: string;
  taskDescription?: string;
  context?: string;
  specDir?: string;  // Optional: backend can infer from working directory
  projectDir?: string;  // Optional: backend can infer from working directory
}

/**
 * Feedback submission result
 */
interface FeedbackResult {
  recorded: boolean;
  message?: string;
  reason?: string;
}

/**
 * Execute the feedback_recorder.py Python script to record feedback.
 * Spawns a subprocess to run the feedback recording with a 30-second timeout.
 *
 * @async
 * @param {FeedbackRequest} request - Feedback data from renderer
 * @returns {Promise<IPCResult<FeedbackResult>>} Result with success flag and data/error
 */
async function executeFeedbackRecorder(
  request: FeedbackRequest
): Promise<IPCResult<FeedbackResult>> {
  // Guard: don't spawn Python if env isn't ready yet (prevents ENOENT -4058 errors)
  if (!pythonEnvManager.isEnvReady()) {
    console.warn('[Feedback] Python env not ready, skipping feedback recording');
    return {
      success: false,
      error: 'Python environment is not ready yet. Feedback will not be recorded.'
    };
  }


  // Use configured Python path (venv if ready, otherwise bundled/system)
  const pythonCmd = getConfiguredPythonPath();

  // Find the feedback_recorder.py script
  const possiblePaths = [
    // Packaged app paths (check FIRST for packaged builds)
    ...(app.isPackaged
      ? [path.join(process.resourcesPath, 'backend', 'feedback_recorder.py')]
      : []),
    // Development paths
    path.resolve(__dirname, '..', '..', '..', 'backend', 'feedback_recorder.py'),
    path.resolve(process.cwd(), 'apps', 'backend', 'feedback_recorder.py')
  ];

  let scriptPath: string | null = null;
  for (const p of possiblePaths) {
    if (fs.existsSync(p)) {
      scriptPath = p;
      break;
    }
  }

  if (!scriptPath) {
    console.error('[Feedback] feedback_recorder.py script not found. Searched paths:', possiblePaths);
    return {
      success: false,
      error: 'feedback_recorder.py script not found'
    };
  }

  console.log('[Feedback] Recording feedback:', request.feedbackType, 'for agent:', request.agentType);

  const [pythonExe, baseArgs] = parsePythonCommand(pythonCmd);
  const args = [...baseArgs, scriptPath];

  // Build command-line arguments from request
  if (request.feedbackType) {
    args.push('--feedback-type', request.feedbackType);
  }
  if (request.agentType) {
    args.push('--agent-type', request.agentType);
  }
  if (request.taskDescription) {
    args.push('--task-description', request.taskDescription);
  }
  if (request.context) {
    args.push('--context', request.context);
  }
  if (request.specDir) {
    args.push('--spec-dir', request.specDir);
  }
  if (request.projectDir) {
    args.push('--project-dir', request.projectDir);
  }

  return new Promise((resolve) => {
    let resolved = false;
    const proc = spawn(pythonExe, args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      timeout: 30000, // 30 second timeout
      // Use sanitized Python environment to prevent PYTHONHOME contamination
      env: pythonEnvManager.getPythonEnv(),
    });

    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    const timeoutId = setTimeout(() => {
      if (!resolved) {
        resolved = true;
        // Graceful shutdown: SIGTERM first, then force kill after grace period
        try {
          proc.kill('SIGTERM');
        } catch {
          // Ignore errors from already-exited processes
        }
        setTimeout(() => {
          try {
            proc.kill('SIGKILL');
          } catch {
            // Ignore
          }
        }, 2_000);
        resolve({
          success: false,
          error: 'Feedback recording timeout (30s)'
        });
      }
    }, 30000);

    proc.on('close', (code) => {
      if (resolved) return;
      resolved = true;
      clearTimeout(timeoutId);

      if (code === 0 && stdout) {
        try {
          const result = JSON.parse(stdout);
          if (result.success) {
            console.log('[Feedback] Recorded successfully:', result.message);
            resolve({
              success: true,
              data: {
                recorded: true,
                message: result.message || 'Feedback recorded successfully'
              }
            });
          } else {
            console.error('[Feedback] Recording failed:', result.error);
            resolve({
              success: false,
              data: {
                recorded: false,
                reason: result.error || 'Failed to save feedback to memory'
              },
              error: result.error || 'Failed to record feedback'
            });
          }
        } catch (e) {
          console.error('[Feedback] Invalid JSON response:', stdout);
          resolve({
            success: false,
            error: `Invalid response from feedback recorder: ${stdout}`
          });
        }
      } else {
        console.error('[Feedback] Script failed with code:', code, 'stderr:', stderr);
        resolve({
          success: false,
          error: stderr || `Feedback recorder exited with code ${code}`
        });
      }
    });

    proc.on('error', (err) => {
      if (resolved) return;
      resolved = true;
      clearTimeout(timeoutId);
      console.error('[Feedback] Process error:', err);
      resolve({
        success: false,
        error: err.message
      });
    });
  });
}

/**
 * Register all feedback-related IPC handlers.
 *
 * @param {() => BrowserWindow | null} getMainWindow - Function to get the main window
 */
export function registerFeedbackHandlers(
  getMainWindow: () => BrowserWindow | null
): void {
  // Submit feedback for adaptive agent learning
  ipcMain.handle(
    IPC_CHANNELS.FEEDBACK_SUBMIT,
    async (
      _,
      request: FeedbackRequest
    ): Promise<IPCResult<FeedbackResult>> => {
      try {
        console.log('[Feedback] Received feedback submission:', {
          type: request.feedbackType,
          agent: request.agentType,
          task: request.taskDescription?.substring(0, 50) // Log first 50 chars
        });

        // Validate feedback type
        const validTypes = ['accepted', 'rejected', 'modified'];
        if (!request.feedbackType || !validTypes.includes(request.feedbackType)) {
          return {
            success: false,
            error: `Invalid feedback type: ${request.feedbackType}. Must be one of: ${validTypes.join(', ')}`
          };
        }

        // Validate required fields
        if (!request.agentType) {
          return {
            success: false,
            error: 'agentType is required'
          };
        }

        if (!request.taskDescription) {
          return {
            success: false,
            error: 'taskDescription is required'
          };
        }

        // Execute feedback recorder script
        const result = await executeFeedbackRecorder(request);

        return result;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        console.error('[Feedback] Failed to submit feedback:', error);
        return {
          success: false,
          error: errorMessage
        };
      }
    }
  );

  console.log('[Feedback] IPC handlers registered');
}
