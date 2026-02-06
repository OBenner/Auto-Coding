/**
 * Plugin API - IPC methods for plugin management
 */
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { invokeIpc } from './modules/ipc-utils';
import type {
  PluginInfo,
  PluginOperationResult,
  PluginInstallResult,
  PluginInstallSource
} from '../../main/plugins/types';

export interface PluginAPI {
  /**
   * List all installed plugins
   * @param filter - Optional filter criteria (e.g., { type: 'agent', enabled: true })
   * @returns Promise with array of PluginInfo
   */
  listPlugins: (filter?: Record<string, unknown>) => Promise<{
    success: boolean;
    data?: PluginInfo[];
    error?: string;
  }>;

  /**
   * Enable a plugin
   * @param pluginName - Name of the plugin to enable
   * @returns Promise with operation result
   */
  enablePlugin: (pluginName: string) => Promise<PluginOperationResult>;

  /**
   * Disable a plugin
   * @param pluginName - Name of the plugin to disable
   * @returns Promise with operation result
   */
  disablePlugin: (pluginName: string) => Promise<PluginOperationResult>;

  /**
   * Install a plugin from a directory, zip file, or marketplace
   * @param source - Plugin installation source
   * @returns Promise with installation result
   */
  installPlugin: (source: PluginInstallSource) => Promise<PluginInstallResult>;

  /**
   * Uninstall a plugin
   * @param pluginName - Name of the plugin to uninstall
   * @returns Promise with operation result
   */
  uninstallPlugin: (pluginName: string) => Promise<PluginOperationResult>;
}

export const createPluginAPI = (): PluginAPI => ({
  listPlugins: (filter = {}) =>
    invokeIpc(IPC_CHANNELS.PLUGIN_LIST, { filter }),

  enablePlugin: (pluginName) =>
    invokeIpc(IPC_CHANNELS.PLUGIN_ENABLE, { plugin_name: pluginName }),

  disablePlugin: (pluginName) =>
    invokeIpc(IPC_CHANNELS.PLUGIN_DISABLE, { plugin_name: pluginName }),

  installPlugin: (source) =>
    invokeIpc(IPC_CHANNELS.PLUGIN_INSTALL, source),

  uninstallPlugin: (pluginName) =>
    invokeIpc(IPC_CHANNELS.PLUGIN_UNINSTALL, { plugin_name: pluginName })
});
