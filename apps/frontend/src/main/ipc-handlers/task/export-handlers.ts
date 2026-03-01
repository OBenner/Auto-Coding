import { ipcMain, app, shell } from 'electron';
import { existsSync, readdirSync } from 'fs';
import path from 'path';
import AdmZip from 'adm-zip';
import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult } from '../../../shared/types';
import { projectStore } from '../../project-store';

/**
 * Register task export handlers
 */
export function registerTaskExportHandlers(): void {
  /**
   * Export task as ZIP archive
   */
  ipcMain.handle(
    IPC_CHANNELS.TASK_EXPORT,
    async (_, projectId: string, taskId: string): Promise<IPCResult<string>> => {
      console.warn('[IPC] TASK_EXPORT called with projectId:', projectId, 'taskId:', taskId);

      try {
        // Get project to find spec directory
        const project = await projectStore.getProject(projectId);
        if (!project) {
          console.error('[IPC] TASK_EXPORT failed: Project not found');
          return { success: false, error: 'Project not found' };
        }

        // Find task to get spec directory
        const tasks = await projectStore.getTasks(projectId);
        const task = tasks.find(t => t.id === taskId || t.specId === taskId);
        if (!task) {
          console.error('[IPC] TASK_EXPORT failed: Task not found');
          return { success: false, error: 'Task not found' };
        }

        // Determine spec directory path
        const specDir = path.join(project.path, '.auto-claude', 'specs', taskId);
        if (!existsSync(specDir)) {
          console.error('[IPC] TASK_EXPORT failed: Spec directory not found:', specDir);
          return { success: false, error: 'Spec directory not found' };
        }

        // Create ZIP archive
        const zip = new AdmZip();

        // Add all files from spec directory to ZIP
        const addDirectoryToZip = (dirPath: string, zipPath: string = '') => {
          const entries = readdirSync(dirPath, { withFileTypes: true });

          for (const entry of entries) {
            const fullPath = path.join(dirPath, entry.name);
            const entryZipPath = zipPath ? path.join(zipPath, entry.name) : entry.name;

            if (entry.isDirectory()) {
              // Recursively add directory contents
              addDirectoryToZip(fullPath, entryZipPath);
            } else {
              // Add file to ZIP
              zip.addLocalFile(fullPath, zipPath);
            }
          }
        };

        addDirectoryToZip(specDir);

        // Generate filename with task name
        const sanitizedTaskId = taskId.replace(/[^a-zA-Z0-9-_]/g, '_');
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
        const zipFilename = `spec-${sanitizedTaskId}-${timestamp}.zip`;

        // Save to user's downloads folder
        const downloadsPath = app.getPath('downloads');
        const zipPath = path.join(downloadsPath, zipFilename);

        // Write ZIP file
        zip.writeZip(zipPath);

        console.warn('[IPC] TASK_EXPORT success: ZIP created at', zipPath);

        // Show file in folder
        shell.showItemInFolder(zipPath);

        return { success: true, data: zipPath };
      } catch (error) {
        console.error('[IPC] TASK_EXPORT failed:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to export task'
        };
      }
    }
  );
}
