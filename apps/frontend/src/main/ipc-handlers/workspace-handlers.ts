import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type { Workspace, WorkspaceProject, IPCResult } from '../../shared/types';
import { WorkspaceStore } from '../workspace-store';

// Singleton workspace store instance
let workspaceStore: WorkspaceStore;

/**
 * Get or create the workspace store instance
 */
function getWorkspaceStore(): WorkspaceStore {
  if (!workspaceStore) {
    workspaceStore = new WorkspaceStore();
  }
  return workspaceStore;
}

// ============================================
// Workspace IPC Handlers
// ============================================

/**
 * Get all workspaces
 */
ipcMain.handle(IPC_CHANNELS.WORKSPACE_LIST, async (): Promise<IPCResult<Workspace[]>> => {
  try {
    const store = getWorkspaceStore();
    const workspaces = store.getWorkspaces();
    return { success: true, data: workspaces };
  } catch (error) {
    console.error('[IPC] Failed to list workspaces:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to list workspaces'
    };
  }
});

/**
 * Get workspace by name
 */
ipcMain.handle(
  IPC_CHANNELS.WORKSPACE_GET,
  async (_event, name: string): Promise<IPCResult<Workspace | null>> => {
    try {
      const store = getWorkspaceStore();
      const workspace = store.getWorkspace(name);
      return { success: true, data: workspace || null };
    } catch (error) {
      console.error('[IPC] Failed to get workspace:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get workspace'
      };
    }
  }
);

/**
 * Create a new workspace
 */
ipcMain.handle(
  IPC_CHANNELS.WORKSPACE_CREATE,
  async (_event, name: string, description?: string): Promise<IPCResult<Workspace>> => {
    try {
      const store = getWorkspaceStore();
      const workspace = store.createWorkspace(name, description);
      return { success: true, data: workspace };
    } catch (error) {
      console.error('[IPC] Failed to create workspace:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to create workspace'
      };
    }
  }
);

/**
 * Update a workspace
 */
ipcMain.handle(
  IPC_CHANNELS.WORKSPACE_UPDATE,
  async (_event, workspace: Workspace): Promise<IPCResult<void>> => {
    try {
      const store = getWorkspaceStore();
      store.saveWorkspace(workspace);
      return { success: true, data: undefined };
    } catch (error) {
      console.error('[IPC] Failed to update workspace:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to update workspace'
      };
    }
  }
);

/**
 * Delete a workspace
 */
ipcMain.handle(
  IPC_CHANNELS.WORKSPACE_DELETE,
  async (_event, name: string): Promise<IPCResult<boolean>> => {
    try {
      const store = getWorkspaceStore();
      const removed = store.removeWorkspace(name);
      return { success: true, data: removed };
    } catch (error) {
      console.error('[IPC] Failed to delete workspace:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to delete workspace'
      };
    }
  }
);

/**
 * Rename a workspace
 */
ipcMain.handle(
  IPC_CHANNELS.WORKSPACE_RENAME,
  async (_event, oldName: string, newName: string): Promise<IPCResult<void>> => {
    try {
      const store = getWorkspaceStore();
      store.renameWorkspace(oldName, newName);
      return { success: true, data: undefined };
    } catch (error) {
      console.error('[IPC] Failed to rename workspace:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to rename workspace'
      };
    }
  }
);

/**
 * Add a project to a workspace
 */
ipcMain.handle(
  IPC_CHANNELS.WORKSPACE_ADD_PROJECT,
  async (
    _event,
    workspaceName: string,
    project: Omit<WorkspaceProject, 'enabled' | 'dependencies' | 'tags'> & {
      enabled?: boolean;
      dependencies?: string[];
      tags?: string[];
    }
  ): Promise<IPCResult<void>> => {
    try {
      const store = getWorkspaceStore();
      store.addProject(workspaceName, project);
      return { success: true, data: undefined };
    } catch (error) {
      console.error('[IPC] Failed to add project to workspace:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to add project to workspace'
      };
    }
  }
);

/**
 * Remove a project from a workspace
 */
ipcMain.handle(
  IPC_CHANNELS.WORKSPACE_REMOVE_PROJECT,
  async (_event, workspaceName: string, projectName: string): Promise<IPCResult<boolean>> => {
    try {
      const store = getWorkspaceStore();
      const removed = store.removeProject(workspaceName, projectName);
      return { success: true, data: removed };
    } catch (error) {
      console.error('[IPC] Failed to remove project from workspace:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to remove project from workspace'
      };
    }
  }
);

/**
 * Update a project in a workspace
 */
ipcMain.handle(
  IPC_CHANNELS.WORKSPACE_UPDATE_PROJECT,
  async (
    _event,
    workspaceName: string,
    projectName: string,
    updates: Partial<WorkspaceProject>
  ): Promise<IPCResult<void>> => {
    try {
      const store = getWorkspaceStore();
      store.updateProject(workspaceName, projectName, updates);
      return { success: true, data: undefined };
    } catch (error) {
      console.error('[IPC] Failed to update project in workspace:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to update project in workspace'
      };
    }
  }
);

/**
 * Get build order for projects (topological sort)
 */
ipcMain.handle(
  IPC_CHANNELS.WORKSPACE_GET_BUILD_ORDER,
  async (_event, workspaceName: string): Promise<IPCResult<WorkspaceProject[]>> => {
    try {
      const store = getWorkspaceStore();
      const buildOrder = store.getBuildOrder(workspaceName);
      return { success: true, data: buildOrder };
    } catch (error) {
      console.error('[IPC] Failed to get build order:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get build order'
      };
    }
  }
);

/**
 * Register workspace IPC handlers
 */
export function registerWorkspaceHandlers(): void {
  // Handlers are registered above via ipcMain.handle
  console.warn('[IPC] Workspace handlers registered');
}
