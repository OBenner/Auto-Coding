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
  /** Runtime capability declarations for agent integration */
  capabilities: string[];
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
  /** Plugin affected by the operation */
  plugin_name?: string;
  /** Permission delta emitted by backend when enabling a plugin */
  permission_diff?: PluginPermissionDiff;
}

/**
 * Permission and capability delta before enabling a plugin
 */
export interface PluginPermissionDiff {
  /** Plugin name */
  plugin_name: string;
  /** Full permissions required by the plugin */
  required_permissions: PluginPermission[];
  /** Full capability declarations from the plugin manifest */
  capabilities: string[];
  /** Permissions newly introduced if this plugin is enabled */
  added_permissions: PluginPermission[];
  /** Capabilities newly introduced if this plugin is enabled */
  added_capabilities: string[];
  /** Whether the plugin is already enabled */
  currently_enabled: boolean;
  /** Whether the inspected action would enable the plugin */
  would_enable: boolean;
}

/**
 * Runtime trace event emitted by plugin hooks
 */
export interface PluginTraceEvent {
  /** Plugin that emitted the trace, when present */
  plugin?: string;
  /** Event name, when present */
  event?: string;
  /** Trace JSONL source file */
  source?: string;
  /** Plugin-specific trace details */
  [key: string]: unknown;
}

/**
 * Recent project plugin trace events
 */
export interface PluginTraceResult {
  /** Project trace directory inspected by backend */
  trace_dir: string;
  /** Optional plugin filter used by the request */
  plugin?: string | null;
  /** Recent trace events */
  traces: PluginTraceEvent[];
}

/**
 * Enabled runtime plugin included in a prompt preview.
 */
export interface PluginContextPreviewRuntimePlugin {
  /** Plugin name */
  plugin_name: string;
  /** Plugin type declared by the manifest */
  plugin_type: string;
  /** Capabilities declared by the plugin */
  capabilities: string[];
  /** Whether this plugin contributed prompt text for the preview context */
  contributed: boolean;
}

/**
 * Prompt contribution from an enabled runtime plugin
 */
export interface PluginContextPreviewContribution {
  /** Plugin that contributed prompt text */
  plugin_name: string;
  /** Capabilities declared by the plugin */
  capabilities: string[];
  /** Prompt augmentation text */
  text: string;
}

/**
 * Preview of enabled plugin prompt augmentations for an agent phase
 */
export interface PluginContextPreview {
  /** Agent phase/type used for preview */
  agent_type: string;
  /** Spec directory used to build the context */
  spec_dir: string;
  /** Enabled runtime plugins inspected by the preview */
  runtime_plugins: PluginContextPreviewRuntimePlugin[];
  /** Individual plugin contributions */
  contributions: PluginContextPreviewContribution[];
  /** Final appended prompt preview */
  preview: string;
}

/**
 * Static security diagnostics for a plugin directory
 */
export interface PluginSecurityDiagnostics {
  /** Whether static security checks passed */
  safe: boolean;
  /** Security warnings from backend scanner */
  warnings: string[];
}

/**
 * Plugin health issue emitted by backend diagnostics
 */
export interface PluginHealthIssue {
  /** Severity level for display and automation */
  severity: 'error' | 'warning';
  /** Stable machine-readable issue code */
  code: string;
  /** Human-readable issue message */
  message: string;
  /** Plugin installation directory, when issue is plugin-specific */
  plugin_dir?: string;
  /** Plugin name, when known */
  plugin_name?: string;
  /** Source plugin root */
  source?: 'user' | 'system';
  /** Additional issue-specific data */
  details?: Record<string, unknown>;
}

/**
 * Manifest and static diagnostics for one plugin directory
 */
export interface PluginHealthEntry {
  /** Plugin name from manifest */
  name: string;
  /** Plugin version from manifest */
  version: string;
  /** Plugin type from manifest */
  plugin_type: PluginType;
  /** Whether the manifest came from the user or system plugin directory */
  source: 'user' | 'system';
  /** Plugin installation directory */
  plugin_dir: string;
  /** Manifest validation status */
  manifest_status: 'valid';
  /** Full manifest metadata */
  metadata: PluginMetadata;
  /** Static security scan result */
  security: PluginSecurityDiagnostics;
  /** Issues associated with this plugin */
  issues: PluginHealthIssue[];
}

/**
 * Summary counts for plugin diagnostics
 */
export interface PluginHealthSummary {
  total_entries: number;
  valid_plugins: number;
  invalid_plugins: number;
  security_warnings: number;
  duplicate_names: number;
}

/**
 * Project-scoped plugin diagnostics payload
 */
export interface PluginHealthDiagnostics {
  directories: {
    user_plugins_dir: string;
    system_plugins_dir: string;
  };
  summary: PluginHealthSummary;
  plugins: PluginHealthEntry[];
  issues: PluginHealthIssue[];
}

/**
 * Plugin installation source
 */
export interface PluginInstallSource {
  /** Type of installation source */
  type: 'directory' | 'zip' | 'marketplace' | 'remote';
  /** Path to directory or zip file */
  path?: string;
  /** Marketplace plugin ID */
  marketplace_id?: string;
  /** Remote URL for plugin installation */
  url?: string;
}
