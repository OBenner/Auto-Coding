/**
 * Plugin IPC Handlers
 *
 * This module provides IPC handlers for plugin management operations:
 * - Listing plugins (with optional filtering by type and status)
 * - Enabling/disabling plugins
 * - Installing plugins from local files or directories
 * - Uninstalling plugins
 *
 * All operations interact with the backend Python plugin system via CLI commands.
 */

import { ipcMain } from 'electron';
import { execFileSync } from 'child_process';
import path from 'path';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import {
  PluginInfo,
  PluginMetadata,
  PluginStatus,
  PluginType,
  PluginInstallResult,
  PluginOperationResult,
  PluginInstallSource
} from './types';
import { getConfiguredPythonPath } from '../python-env-manager';
import { getEffectiveSourcePath } from '../updater/path-resolver';
import { logger } from '../app-logger';

/**
 * Execute a Python plugin management command
 *
 * @param projectPath - Project directory path
 * @param command - Command to execute (list, enable, disable, install, uninstall)
 * @param args - Command arguments
 * @returns Command output as JSON
 */
function executePluginCommand(
  projectPath: string,
  command: string,
  args: string[] = []
): unknown {
  try {
    const pythonPath = getConfiguredPythonPath(projectPath);
    const sourcePath = getEffectiveSourcePath();
    const pluginCliPath = path.join(sourcePath, 'apps', 'backend', 'plugins', 'cli.py');

    const fullArgs = [pluginCliPath, command, ...args];

    logger.info(`[Plugin] Executing command: ${command} with args:`, args);

    const output = execFileSync(pythonPath, fullArgs, {
      cwd: projectPath,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 30000 // 30 second timeout
    });

    return JSON.parse(output.trim());
  } catch (error) {
    logger.error(`[Plugin] Command failed: ${command}`, error);

    // Try to extract error message from stderr
    if (error instanceof Error && 'stderr' in error) {
      const stderr = (error as { stderr?: Buffer }).stderr;
      if (stderr) {
        const errorMessage = stderr.toString('utf-8').trim();
        if (errorMessage) {
          throw new Error(errorMessage);
        }
      }
    }

    throw error;
  }
}

/**
 * Convert backend plugin data to frontend PluginInfo format
 */
function parsePluginInfo(data: Record<string, unknown>): PluginInfo {
  const metadata = data.metadata as Record<string, unknown>;

  return {
    metadata: {
      name: metadata.name as string,
      version: metadata.version as string,
      author: metadata.author as string,
      description: metadata.description as string,
      plugin_type: metadata.plugin_type as PluginType,
      required_permissions: metadata.required_permissions as string[],
      dependencies: (metadata.dependencies as string[]) || [],
      homepage: metadata.homepage as string | undefined,
      license: metadata.license as string | undefined
    },
    status: data.status as PluginStatus,
    plugin_dir: data.plugin_dir as string,
    error: data.error as string | undefined,
    loaded_at: data.loaded_at ? new Date(data.loaded_at as string) : undefined,
    enabled_at: data.enabled_at ? new Date(data.enabled_at as string) : undefined
  };
}

/**
 * Register all plugin-related IPC handlers
 */
export function registerPluginHandlers(projectId: string): void {
  // ============================================
  // Plugin List
  // ============================================

  /**
   * List all plugins with optional filtering
   *
   * @param pluginType - Optional filter by plugin type
   * @param enabledOnly - If true, only return enabled plugins
   */
  ipcMain.handle(
    IPC_CHANNELS.PLUGIN_LIST,
    async (
      _,
      pluginType?: PluginType,
      enabledOnly = false
    ): Promise<IPCResult<PluginInfo[]>> => {
      try {
        logger.info('[Plugin] Listing plugins', { pluginType, enabledOnly });

        const args: string[] = [];
        if (pluginType) {
          args.push('--type', pluginType);
        }
        if (enabledOnly) {
          args.push('--enabled-only');
        }

        const result = executePluginCommand(projectId, 'list', args);
        const plugins = (result as { plugins: Record<string, unknown>[] }).plugins;

        const pluginInfos = plugins.map(parsePluginInfo);

        logger.info(`[Plugin] Found ${pluginInfos.length} plugins`);
        return { success: true, data: pluginInfos };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        logger.error('[Plugin] List failed:', error);
        return { success: false, error: errorMessage };
      }
    }
  );

  // ============================================
  // Plugin Enable
  // ============================================

  /**
   * Enable a plugin
   *
   * @param pluginName - Name of the plugin to enable
   */
  ipcMain.handle(
    IPC_CHANNELS.PLUGIN_ENABLE,
    async (_, pluginName: string): Promise<IPCResult<PluginOperationResult>> => {
      try {
        logger.info('[Plugin] Enabling plugin:', pluginName);

        executePluginCommand(projectId, 'enable', [pluginName]);

        logger.info('[Plugin] Plugin enabled successfully:', pluginName);
        return { success: true, data: { success: true } };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        logger.error('[Plugin] Enable failed:', error);
        return {
          success: false,
          error: errorMessage,
          data: { success: false, error: errorMessage }
        };
      }
    }
  );

  // ============================================
  // Plugin Disable
  // ============================================

  /**
   * Disable a plugin
   *
   * @param pluginName - Name of the plugin to disable
   */
  ipcMain.handle(
    IPC_CHANNELS.PLUGIN_DISABLE,
    async (_, pluginName: string): Promise<IPCResult<PluginOperationResult>> => {
      try {
        logger.info('[Plugin] Disabling plugin:', pluginName);

        executePluginCommand(projectId, 'disable', [pluginName]);

        logger.info('[Plugin] Plugin disabled successfully:', pluginName);
        return { success: true, data: { success: true } };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        logger.error('[Plugin] Disable failed:', error);
        return {
          success: false,
          error: errorMessage,
          data: { success: false, error: errorMessage }
        };
      }
    }
  );

  // ============================================
  // Plugin Install
  // ============================================

  /**
   * Install a plugin from a local directory or zip file
   *
   * @param source - Plugin installation source
   */
  ipcMain.handle(
    IPC_CHANNELS.PLUGIN_INSTALL,
    async (_, source: PluginInstallSource): Promise<IPCResult<PluginInstallResult>> => {
      try {
        logger.info('[Plugin] Installing plugin:', source);

        const args: string[] = [];

        if (source.type === 'directory' && source.path) {
          args.push('--from-directory', source.path);
        } else if (source.type === 'zip' && source.path) {
          args.push('--from-zip', source.path);
        } else if (source.type === 'marketplace' && source.marketplace_id) {
          args.push('--from-marketplace', source.marketplace_id);
        } else {
          throw new Error('Invalid plugin installation source');
        }

        const result = executePluginCommand(projectId, 'install', args);
        const data = result as { success: boolean; plugin?: Record<string, unknown>; error?: string };

        if (data.success && data.plugin) {
          const metadata = data.plugin as PluginMetadata;
          logger.info('[Plugin] Plugin installed successfully:', metadata.name);
          return {
            success: true,
            data: { success: true, plugin: metadata }
          };
        } else {
          throw new Error(data.error || 'Installation failed');
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        logger.error('[Plugin] Install failed:', error);
        return {
          success: false,
          error: errorMessage,
          data: { success: false, error: errorMessage }
        };
      }
    }
  );

  // ============================================
  // Plugin Uninstall
  // ============================================

  /**
   * Uninstall a plugin
   *
   * @param pluginName - Name of the plugin to uninstall
   */
  ipcMain.handle(
    IPC_CHANNELS.PLUGIN_UNINSTALL,
    async (_, pluginName: string): Promise<IPCResult<PluginOperationResult>> => {
      try {
        logger.info('[Plugin] Uninstalling plugin:', pluginName);

        executePluginCommand(projectId, 'uninstall', [pluginName]);

        logger.info('[Plugin] Plugin uninstalled successfully:', pluginName);
        return { success: true, data: { success: true } };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        logger.error('[Plugin] Uninstall failed:', error);
        return {
          success: false,
          error: errorMessage,
          data: { success: false, error: errorMessage }
        };
      }
    }
  );

  logger.info('[Plugin] Plugin IPC handlers registered for project:', projectId);
}
