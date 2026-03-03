/**
 * Plugin system types for Auto Code
 *
 * This module defines the TypeScript interfaces for the plugin system,
 * mirroring the backend Python implementation for type-safe IPC communication.
 *
 * The plugin system supports three types of plugins:
 * - Agent plugins: Add custom tools and behaviors to AI agents
 * - Integration plugins: Connect to external services via MCP tools
 * - UI plugins: Extend the Electron frontend with custom components
 */

/**
 * Types of plugins supported by Auto Code
 */
export enum PluginType {
  AGENT = 'agent',
  INTEGRATION = 'integration',
  UI = 'ui'
}

/**
 * Permission types for plugin security model
 *
 * Plugins must declare required permissions in their metadata.
 * The permission system validates plugin actions against declared permissions.
 */
export enum PluginPermission {
  READ_FILES = 'read_files',
  WRITE_FILES = 'write_files',
  NETWORK_ACCESS = 'network_access',
  EXECUTE_COMMANDS = 'execute_commands',
  ACCESS_SECRETS = 'access_secrets',
  CREATE_MCP_TOOLS = 'create_mcp_tools'
}

/**
 * Plugin runtime status
 */
export enum PluginStatus {
  LOADED = 'loaded',
  ENABLED = 'enabled',
  DISABLED = 'disabled',
  ERROR = 'error'
}

/**
 * Plugin metadata from plugin.json manifest
 *
 * This information is loaded during plugin discovery and used for
 * validation, display, and permission checks.
 */
export interface PluginMetadata {
  /** Unique plugin identifier (e.g., "hello-world-agent") */
  name: string;
  /** Semantic version string (e.g., "1.0.0") */
  version: string;
  /** Plugin author name or organization */
  author: string;
  /** Human-readable description of plugin functionality */
  description: string;
  /** Type of plugin (agent, integration, or ui) */
  plugin_type: PluginType;
  /** List of permissions the plugin requires */
  required_permissions: PluginPermission[];
  /** List of other plugin names this plugin depends on */
  dependencies: string[];
  /** Optional URL to plugin documentation/repository */
  homepage?: string;
  /** Optional license identifier (e.g., "MIT", "Apache-2.0") */
  license?: string;
}

/**
 * Plugin runtime information
 *
 * Combines metadata with current runtime state for display in UI
 */
export interface PluginInfo {
  /** Plugin metadata from manifest */
  metadata: PluginMetadata;
  /** Current runtime status */
  status: PluginStatus;
  /** Plugin installation directory */
  plugin_dir: string;
  /** Error message if status is ERROR */
  error?: string;
  /** Timestamp when plugin was loaded */
  loaded_at?: Date;
  /** Timestamp when plugin was last enabled */
  enabled_at?: Date;
}

/**
 * Plugin configuration
 *
 * User-provided configuration values for a plugin.
 * Each plugin can define its own config schema.
 */
export interface PluginConfig {
  /** Plugin name */
  plugin_name: string;
  /** Configuration key-value pairs */
  config: Record<string, unknown>;
}

/**
 * Result of plugin installation
 */
export interface PluginInstallResult {
  /** Whether installation succeeded */
  success: boolean;
  /** Installed plugin metadata if successful */
  plugin?: PluginMetadata;
  /** Error message if installation failed */
  error?: string;
}

/**
 * Result of plugin operation (enable/disable/uninstall)
 */
export interface PluginOperationResult {
  /** Whether operation succeeded */
  success: boolean;
  /** Error message if operation failed */
  error?: string;
}

/**
 * Plugin installation source
 */
export interface PluginInstallSource {
  /** Type of installation source */
  type: 'directory' | 'zip' | 'marketplace';
  /** Path to directory or zip file */
  path?: string;
  /** Marketplace plugin ID */
  marketplace_id?: string;
}
