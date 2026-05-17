/**
 * Plugin API - IPC methods for plugin management
 */
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { invokeIpc } from './modules/ipc-utils';
import type {
  PluginInfo,
  PluginOperationResult,
  PluginInstallResult,
  PluginInstallSource,
  PluginHealthDiagnostics
} from '../../main/plugins/types';

export interface PluginAPI {
  /**
   * List all installed plugins
   * @param filter - Optional filter criteria (e.g., { type: 'agent', enabled: true })
   * @returns Promise with array of PluginInfo
   */
  listPlugins: (options: {
    projectPath: string;
    filter?: Record<string, unknown>;
  }) => Promise<{
    success: boolean;
    data?: PluginInfo[];
    error?: string;
  }>;

  /**
   * Inspect plugin directories and manifest health
   * @param projectPath - Project directory path
   * @returns Promise with plugin diagnostics
   */
  getPluginHealth: (projectPath: string) => Promise<{
    success: boolean;
    data?: PluginHealthDiagnostics;
    error?: string;
  }>;

  /**
   * Enable a plugin
   * @param pluginName - Name of the plugin to enable
   * @returns Promise with operation result
   */
  enablePlugin: (pluginName: string, projectPath: string) => Promise<PluginOperationResult>;

  /**
   * Disable a plugin
   * @param pluginName - Name of the plugin to disable
   * @returns Promise with operation result
   */
  disablePlugin: (pluginName: string, projectPath: string) => Promise<PluginOperationResult>;

  /**
   * Install a plugin from a directory, zip file, or marketplace
   * @param source - Plugin installation source
   * @returns Promise with installation result
   */
  installPlugin: (
    source: PluginInstallSource,
    projectPath: string
  ) => Promise<PluginInstallResult>;

  /**
   * Uninstall a plugin
   * @param pluginName - Name of the plugin to uninstall
   * @returns Promise with operation result
   */
  uninstallPlugin: (pluginName: string, projectPath: string) => Promise<PluginOperationResult>;
}

export const createPluginAPI = (): PluginAPI => ({
  listPlugins: ({ projectPath, filter = {} }) =>
    invokeIpc(IPC_CHANNELS.PLUGIN_LIST, { projectPath, filter }),

  getPluginHealth: (projectPath) =>
    invokeIpc(IPC_CHANNELS.PLUGIN_HEALTH, { projectPath }),

  enablePlugin: (pluginName, projectPath) =>
    invokeIpc(IPC_CHANNELS.PLUGIN_ENABLE, { projectPath, pluginName }),

  disablePlugin: (pluginName, projectPath) =>
    invokeIpc(IPC_CHANNELS.PLUGIN_DISABLE, { projectPath, pluginName }),

  installPlugin: (source, projectPath) =>
    invokeIpc(IPC_CHANNELS.PLUGIN_INSTALL, { projectPath, source }),

  uninstallPlugin: (pluginName, projectPath) =>
    invokeIpc(IPC_CHANNELS.PLUGIN_UNINSTALL, { projectPath, pluginName })
});
