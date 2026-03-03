import { ipcMain } from 'electron';
import { readFile } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult, TaskTokenStats } from '../../shared/types';

/**
 * Register all token statistics IPC handlers
 */
export function registerTokenStatsHandlers(): void {
  // ============================================
  // Token Statistics Operations
  // ============================================

  /**
   * Get token statistics for a task from token_stats.json in spec directory
   */
  ipcMain.handle(
    IPC_CHANNELS.TASK_TOKEN_STATS_GET,
    async (_, projectPath: string, specId: string): Promise<IPCResult<TaskTokenStats | null>> => {
      try {
        // Validate inputs
        if (!projectPath || !specId) {
          return { success: false, error: 'Project path and spec ID are required' };
        }

        // Construct path to token_stats.json
        const tokenStatsPath = path.join(projectPath, '.auto-claude', 'specs', specId, 'token_stats.json');

        // Check if file exists
        if (!existsSync(tokenStatsPath)) {
          // Not an error - token stats file may not exist yet for tasks that haven't run
          return { success: true, data: null };
        }

        // Read and parse token stats file
        const content = await readFile(tokenStatsPath, 'utf-8');
        const tokenStats = JSON.parse(content) as TaskTokenStats;

        return { success: true, data: tokenStats };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to read token statistics'
        };
      }
    }
  );
}
