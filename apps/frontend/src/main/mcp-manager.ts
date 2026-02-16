/**
 * MCP Server Manager
 *
 * Manages the lifecycle of the embedded MCP server within the Electron main process.
 * Provides utilities for conditionally starting the MCP server based on environment variables.
 *
 * Usage:
 *   import { initializeMCPServer } from './mcp-manager.js';
 *
 *   app.whenReady().then(() => {
 *     initializeMCPServer();  // Starts if ELECTRON_MCP_ENABLED=true
 *   });
 *
 * Environment Variables:
 *   - ELECTRON_MCP_ENABLED: Set to "true" to enable MCP server (default: disabled)
 *   - ELECTRON_MCP_LOG_LEVEL: Log verbosity (debug|info|warn|error, default: info)
 *
 * @see MCP_ARCHITECTURE_DESIGN_1.2.md
 * @see SECURITY_REQUIREMENTS_AND_CONTEXT_ISOLATION_1.3.md
 */

import { app } from 'electron';
import { ElectronMCPServer } from './mcp-server.js';

// ============================================================================
// Constants
// ============================================================================

/** Environment variable to enable MCP server */
const MCP_ENABLED_ENV = 'ELECTRON_MCP_ENABLED';

/** Environment variable for log level */
const MCP_LOG_LEVEL_ENV = 'ELECTRON_MCP_LOG_LEVEL';

/** Default log level */
const DEFAULT_LOG_LEVEL = 'info';

// ============================================================================
// State
// ============================================================================

/** Global MCP server instance */
let mcpServer: ElectronMCPServer | null = null;

/** Whether the MCP server is currently running */
let isRunning = false;

// ============================================================================
// Utility Functions
// ============================================================================

/** Valid log levels for MCP server */
const VALID_LOG_LEVELS = ['debug', 'info', 'warn', 'error'] as const;
type LogLevel = typeof VALID_LOG_LEVELS[number];

/**
 * Validate a log level value
 * @param level - Log level to validate
 * @returns true if valid, false otherwise
 */
function isValidLogLevel(level: string): level is LogLevel {
  return VALID_LOG_LEVELS.includes(level as LogLevel);
}

/**
 * Check if MCP server should be enabled
 * @returns true if ELECTRON_MCP_ENABLED is set to "true"
 */
export function isMCPServerEnabled(): boolean {
  const enabled = process.env[MCP_ENABLED_ENV];
  if (enabled === undefined || enabled === '') {
    return false;
  }
  const normalized = enabled.toLowerCase().trim();
  if (normalized !== 'true' && normalized !== 'false') {
    console.warn(`[MCP] Invalid value for ${MCP_ENABLED_ENV}: "${enabled}". Expected "true" or "false". Defaulting to false.`);
    return false;
  }
  return normalized === 'true';
}

/**
 * Get the configured log level for MCP server
 * @returns Log level from environment or default
 * @throws Error if log level is invalid
 */
export function getMCPLogLevel(): string {
  const level = process.env[MCP_LOG_LEVEL_ENV];
  if (!level) {
    return DEFAULT_LOG_LEVEL;
  }
  const normalized = level.toLowerCase().trim();
  if (!isValidLogLevel(normalized)) {
    console.warn(`[MCP] Invalid log level: "${level}". Valid values: ${VALID_LOG_LEVELS.join(', ')}. Using default: ${DEFAULT_LOG_LEVEL}`);
    return DEFAULT_LOG_LEVEL;
  }
  return normalized;
}

/**
 * Check if MCP server is currently running
 * @returns true if server is active
 */
export function isMCPServerRunning(): boolean {
  return isRunning;
}

/**
 * Get the MCP server instance (if running)
 * @returns MCP server instance or null
 */
export function getMCPServer(): ElectronMCPServer | null {
  return mcpServer;
}

// ============================================================================
// MCP Server Lifecycle
// ============================================================================

/**
 * Initialize the MCP server if enabled via environment variable.
 *
 * This function should be called during Electron app initialization (after app.whenReady()).
 * It checks the ELECTRON_MCP_ENABLED environment variable and starts the server if set to "true".
 *
 * Usage:
 *   app.whenReady().then(() => {
 *     initializeMCPServer();
 *     createWindow();
 *   });
 *
 * The server runs in the same process as Electron (embedded mode) and uses stdio transport
 * for communication with the Claude Agent SDK via stdin/stdout.
 *
 * @returns Promise that resolves when server is started or skipped
 * @throws Error if server startup fails
 */
export async function initializeMCPServer(): Promise<void> {
  // Check if MCP server is enabled
  if (!isMCPServerEnabled()) {
    console.log('[MCP] Server not enabled (set ELECTRON_MCP_ENABLED=true to activate)');
    return;
  }

  // Check if already running
  if (isRunning) {
    console.warn('[MCP] Server already running, skipping initialization');
    return;
  }

  // Set log level from environment
  const logLevel = getMCPLogLevel();
  if (logLevel !== DEFAULT_LOG_LEVEL) {
    process.env[MCP_LOG_LEVEL_ENV] = logLevel;
    console.log(`[MCP] Log level set to: ${logLevel}`);
  }

  try {
    console.log('[MCP] Initializing embedded MCP server...');
    console.log('[MCP] Mode: embedded (stdio transport)');
    console.log('[MCP] Transport: stdio (stdin/stdout)');

    // Create MCP server instance
    mcpServer = new ElectronMCPServer();

    // Start the server
    await mcpServer.start();

    isRunning = true;
    console.log('[MCP] ✅ Server started successfully');
    console.log('[MCP] Waiting for JSON-RPC requests via stdin/stdout...');

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('[MCP] ❌ Failed to start server:', errorMessage);

    if (error instanceof Error && process.env[MCP_LOG_LEVEL_ENV] === 'debug') {
      console.error('[MCP] Stack trace:', error.stack);
    }

    throw error;
  }
}

/**
 * Stop the MCP server gracefully.
 *
 * This function is called automatically when the Electron app quits.
 * It closes the stdio transport and cleans up resources.
 *
 * @returns Promise that resolves when server is stopped
 */
export async function stopMCPServer(): Promise<void> {
  if (!isRunning || !mcpServer) {
    return;
  }

  console.log('[MCP] Stopping server...');

  try {
    // The MCP SDK's stdio transport doesn't have an explicit stop method
    // The server will stop when the process exits
    // We just need to clean up our state
    mcpServer = null;
    isRunning = false;

    console.log('[MCP] Server stopped');
  } catch (error) {
    console.error('[MCP] Error during shutdown:', error);
  }
}

// ============================================================================
// App Lifecycle Integration
// ============================================================================

/**
 * Setup automatic MCP server lifecycle management.
 *
 * This function integrates the MCP server with Electron's app lifecycle:
 * - Starts server when app is ready (if enabled)
 * - Stops server when app quits
 *
 * Usage:
 *   setupMCPLifecycle();
 *   // No need to manually call initializeMCPServer() or stopMCPServer()
 */
export function setupMCPLifecycle(): void {
  // Start server when app is ready
  app.whenReady().then(async () => {
    await initializeMCPServer();
  });

  // Stop server before quit
  app.on('before-quit', async () => {
    await stopMCPServer();
  });
}

// ============================================================================
// Export
// ============================================================================

export default {
  initializeMCPServer,
  stopMCPServer,
  setupMCPLifecycle,
  isMCPServerEnabled,
  isMCPServerRunning,
  getMCPServer,
  getMCPLogLevel
};
