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
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import {
  PluginInfo,
  PluginMetadata,
  PluginPermission,
  PluginStatus,
  PluginType,
  PluginInstallResult,
  PluginOperationResult,
  PluginInstallSource,
  PluginHealthDiagnostics,
  PluginPermissionDiff,
  PluginTraceResult,
  PluginContextPreview
} from './types';
import { getConfiguredPythonPath } from '../python-env-manager';
import { joinPaths, normalizePath } from '../platform';
import { getEffectiveSourcePath } from '../updater/path-resolver';
import { logger } from '../app-logger';

interface PluginListPayload {
  projectPath?: string;
  filter?: {
    pluginType?: PluginType;
    type?: PluginType;
    enabledOnly?: boolean;
    enabled?: boolean;
  };
}

interface PluginNamePayload {
  projectPath?: string;
  pluginName?: string;
  plugin_name?: string;
}

interface PluginInstallPayload {
  projectPath?: string;
  source?: PluginInstallSource;
}

interface PluginHealthPayload {
  projectPath?: string;
}

interface PluginTracePayload {
  projectPath?: string;
  pluginName?: string;
  plugin_name?: string;
  limit?: number;
}

interface PluginPreviewContextPayload {
  projectPath?: string;
  agentType?: string;
  agent_type?: string;
  specDir?: string;
  spec_dir?: string;
  task?: string;
  files?: string[];
  file?: string | string[];
}

/**
 * Execute a Python plugin management command
 *
 * @param projectPath - Project directory path
 * @param command - Command to execute (list, enable, disable, install, uninstall)
 * @param args - Command arguments
 * @returns Command output as JSON
 */
function runPluginCliCommand(
  projectPath: string,
  command: string,
  args: string[] = []
): unknown {
  try {
    const pythonPath = getConfiguredPythonPath();
    const sourcePath = getEffectiveSourcePath();
    const pluginCliPath = joinPaths(sourcePath, 'apps', 'backend', 'plugins', 'cli.py');

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

function resolvePluginProjectPath(projectPath?: string): string {
  if (!projectPath) {
    throw new Error('Project path is required for plugin operations');
  }
  return normalizePath(projectPath);
}

function normalizePluginName(payload: string | PluginNamePayload): string {
  if (typeof payload === 'string') {
    return payload;
  }
  const pluginName = payload.pluginName || payload.plugin_name;
  if (!pluginName) {
    throw new Error('Plugin name is required');
  }
  return pluginName;
}

function normalizeOptionalPluginName(payload: PluginTracePayload): string | undefined {
  return payload.pluginName || payload.plugin_name;
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
      required_permissions: metadata.required_permissions as PluginPermission[],
      capabilities: (metadata.capabilities as string[]) || [],
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
export function registerPluginHandlers(): void {
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
      payload: PluginListPayload = {}
    ): Promise<IPCResult<PluginInfo[]>> => {
      try {
        const projectPath = resolvePluginProjectPath(payload.projectPath);
        const filter = payload.filter || {};
        const pluginType = filter.pluginType || filter.type;
        const enabledOnly = Boolean(filter.enabledOnly || filter.enabled);

        logger.info('[Plugin] Listing plugins', { pluginType, enabledOnly });

        const args: string[] = ['--json'];
        if (pluginType) {
          args.push('--type', pluginType);
        }
        if (enabledOnly) {
          args.push('--enabled-only');
        }

        const result = runPluginCliCommand(projectPath, 'list', args);
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
  // Plugin Health
  // ============================================

  /**
   * Inspect plugin directories, manifests, and static diagnostics
   */
  ipcMain.handle(
    IPC_CHANNELS.PLUGIN_HEALTH,
    async (
      _,
      payload: PluginHealthPayload = {}
    ): Promise<IPCResult<PluginHealthDiagnostics>> => {
      try {
        const projectPath = resolvePluginProjectPath(payload.projectPath);
        logger.info('[Plugin] Inspecting plugin health');

        const result = runPluginCliCommand(projectPath, 'health', ['--json']);
        const diagnostics = (result as { diagnostics: PluginHealthDiagnostics }).diagnostics;

        logger.info('[Plugin] Plugin health inspection completed');
        return { success: true, data: diagnostics };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        logger.error('[Plugin] Health inspection failed:', error);
        return { success: false, error: errorMessage };
      }
    }
  );

  // ============================================
  // Plugin Permission Diff
  // ============================================

  /**
   * Preview permission and capability changes before enabling a plugin
   */
  ipcMain.handle(
    IPC_CHANNELS.PLUGIN_PERMISSION_DIFF,
    async (
      _,
      payload: PluginNamePayload
    ): Promise<IPCResult<PluginPermissionDiff>> => {
      try {
        const projectPath = resolvePluginProjectPath(payload.projectPath);
        const pluginName = normalizePluginName(payload);
        logger.info('[Plugin] Inspecting permission diff:', pluginName);

        const result = runPluginCliCommand(projectPath, 'permission-diff', [
          '--json',
          pluginName
        ]) as { permission_diff: PluginPermissionDiff };

        return { success: true, data: result.permission_diff };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        logger.error('[Plugin] Permission diff failed:', error);
        return { success: false, error: errorMessage };
      }
    }
  );

  // ============================================
  // Plugin Traces
  // ============================================

  /**
   * Read recent project plugin trace events
   */
  ipcMain.handle(
    IPC_CHANNELS.PLUGIN_TRACES,
    async (
      _,
      payload: PluginTracePayload = {}
    ): Promise<IPCResult<PluginTraceResult>> => {
      try {
        const projectPath = resolvePluginProjectPath(payload.projectPath);
        const pluginName = normalizeOptionalPluginName(payload);
        const args: string[] = ['--json'];
        if (pluginName) {
          args.push('--plugin', pluginName);
        }
        if (payload.limit !== undefined) {
          args.push('--limit', String(payload.limit));
        }

        logger.info('[Plugin] Reading plugin traces', { pluginName, limit: payload.limit });
        const result = runPluginCliCommand(projectPath, 'traces', args) as PluginTraceResult;

        return {
          success: true,
          data: {
            trace_dir: result.trace_dir,
            plugin: result.plugin,
            traces: result.traces || []
          }
        };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        logger.error('[Plugin] Trace read failed:', error);
        return { success: false, error: errorMessage };
      }
    }
  );

  // ============================================
  // Plugin Prompt Preview
  // ============================================

  /**
   * Preview enabled plugin prompt augmentations for an agent phase
   */
  ipcMain.handle(
    IPC_CHANNELS.PLUGIN_PREVIEW_CONTEXT,
    async (
      _,
      payload: PluginPreviewContextPayload = {}
    ): Promise<IPCResult<PluginContextPreview>> => {
      try {
        const projectPath = resolvePluginProjectPath(payload.projectPath);
        const agentType = payload.agentType || payload.agent_type || 'coder';
        const specDir = payload.specDir || payload.spec_dir;
        const rawFiles = payload.files || payload.file || [];
        const files = Array.isArray(rawFiles) ? rawFiles : [rawFiles];

        const args: string[] = ['--json', '--agent-type', agentType];
        if (specDir) {
          args.push('--spec-dir', specDir);
        }
        if (payload.task) {
          args.push('--task', payload.task);
        }
        for (const file of files) {
          if (file) {
            args.push('--file', file);
          }
        }

        logger.info('[Plugin] Previewing plugin context', { agentType });
        const result = runPluginCliCommand(
          projectPath,
          'preview-context',
          args
        ) as PluginContextPreview;

        return {
          success: true,
          data: {
            agent_type: result.agent_type,
            spec_dir: result.spec_dir,
            runtime_plugins: result.runtime_plugins || [],
            contributions: result.contributions || [],
            preview: result.preview || ''
          }
        };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        logger.error('[Plugin] Context preview failed:', error);
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
    async (
      _,
      payload: string | PluginNamePayload
    ): Promise<IPCResult<PluginOperationResult>> => {
      try {
        const projectPath = resolvePluginProjectPath(
          typeof payload === 'string' ? undefined : payload.projectPath
        );
        const pluginName = normalizePluginName(payload);
        logger.info('[Plugin] Enabling plugin:', pluginName);

        const result = runPluginCliCommand(projectPath, 'enable', [
          '--json',
          pluginName
        ]) as PluginOperationResult;

        logger.info('[Plugin] Plugin enabled successfully:', pluginName);
        return {
          success: true,
          data: {
            success: true,
            plugin_name: result.plugin_name || pluginName,
            permission_diff: result.permission_diff
          }
        };
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
    async (
      _,
      payload: string | PluginNamePayload
    ): Promise<IPCResult<PluginOperationResult>> => {
      try {
        const projectPath = resolvePluginProjectPath(
          typeof payload === 'string' ? undefined : payload.projectPath
        );
        const pluginName = normalizePluginName(payload);
        logger.info('[Plugin] Disabling plugin:', pluginName);

        runPluginCliCommand(projectPath, 'disable', ['--json', pluginName]);

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
    async (
      _,
      payload: PluginInstallSource | PluginInstallPayload
    ): Promise<IPCResult<PluginInstallResult>> => {
      try {
        const projectPath = resolvePluginProjectPath(
          'source' in payload ? payload.projectPath : undefined
        );
        const source = ('source' in payload ? payload.source : payload) as
          | PluginInstallSource
          | undefined;
        if (!source) {
          throw new Error('Invalid plugin installation source');
        }
        logger.info('[Plugin] Installing plugin:', source);

        const args: string[] = ['--json'];

        if (source.type === 'directory' && source.path) {
          args.push('--path', source.path);
        } else if (source.type === 'remote' && source.url) {
          args.push('--url', source.url);
        } else {
          throw new Error('Invalid plugin installation source');
        }

        const result = runPluginCliCommand(projectPath, 'install', args);
        const data = result as { success: boolean; plugin?: Record<string, unknown>; error?: string };

        if (data.success && data.plugin) {
          const metadata = data.plugin as unknown as PluginMetadata;
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
    async (
      _,
      payload: string | PluginNamePayload
    ): Promise<IPCResult<PluginOperationResult>> => {
      try {
        const projectPath = resolvePluginProjectPath(
          typeof payload === 'string' ? undefined : payload.projectPath
        );
        const pluginName = normalizePluginName(payload);
        logger.info('[Plugin] Uninstalling plugin:', pluginName);

        runPluginCliCommand(projectPath, 'uninstall', ['--json', pluginName]);

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

  logger.info('[Plugin] Plugin IPC handlers registered');
}
