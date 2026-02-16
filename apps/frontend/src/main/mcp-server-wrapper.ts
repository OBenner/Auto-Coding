/**
 * MCP Server Wrapper
 *
 * Standalone entry point for spawning the MCP server as a separate process.
 * This wrapper is invoked by the Claude Agent SDK via stdio transport.
 *
 * Architecture:
 * Backend Python → spawns this wrapper → stdio transport → MCP Server
 *
 * Usage:
 *   node mcp-server-wrapper.js
 *
 * Environment Variables:
 *   - ELECTRON_MCP_LOG_LEVEL: Log verbosity (debug|info|warn|error)
 *   - ELECTRON_MCP_TIMEOUT: Server startup timeout in ms (default: 5000)
 *
 * @see MCP_ARCHITECTURE_DESIGN_1.2.md - Transport Layer section
 * @see mcp-server.ts - Core MCP server implementation
 */

import { ElectronMCPServer } from './mcp-server.js';

// ============================================================================
// Constants
// ============================================================================

/** Default log level */
const DEFAULT_LOG_LEVEL = 'info';

/** Default server startup timeout in milliseconds */
const DEFAULT_STARTUP_TIMEOUT = 5000;

/** Log prefix for all messages */
const LOG_PREFIX = '[MCP-Wrapper]';

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Get log level from environment or default
 */
function getLogLevel(): string {
  const level = process.env.ELECTRON_MCP_LOG_LEVEL;
  const validLevels = ['debug', 'info', 'warn', 'error'];

  if (level && !validLevels.includes(level.toLowerCase())) {
    log('warn', `Invalid log level: "${level}". Valid values: ${validLevels.join(', ')}. Using default: ${DEFAULT_LOG_LEVEL}`);
    return DEFAULT_LOG_LEVEL;
  }

  return level || DEFAULT_LOG_LEVEL;
}

/**
 * Get server startup timeout from environment or default
 */
function getStartupTimeout(): number {
  const timeoutStr = process.env.ELECTRON_MCP_TIMEOUT;
  if (!timeoutStr) {
    return DEFAULT_STARTUP_TIMEOUT;
  }

  const timeout = parseInt(timeoutStr, 10);
  if (isNaN(timeout) || timeout < 1000) {
    log('warn', `Invalid timeout: "${timeoutStr}". Using default: ${DEFAULT_STARTUP_TIMEOUT}ms`);
    return DEFAULT_STARTUP_TIMEOUT;
  }

  return timeout;
}

/**
 * Log message with level filtering
 */
function log(level: string, message: string, ...args: any[]): void {
  const currentLevel = getLogLevel();
  const levels = ['debug', 'info', 'warn', 'error'];

  // Only log if level is >= current level
  if (levels.indexOf(level) >= levels.indexOf(currentLevel)) {
    const timestamp = new Date().toISOString();
    const formattedMessage = `${timestamp} ${LOG_PREFIX} [${level.toUpperCase()}] ${message}`;

    switch (level) {
      case 'error':
        console.error(formattedMessage, ...args);
        break;
      case 'warn':
        console.warn(formattedMessage, ...args);
        break;
      default:
        console.log(formattedMessage, ...args);
    }
  }
}

/**
 * Handle uncaught errors
 */
function handleError(error: Error): void {
  log('error', 'Fatal error:', error.message);

  if (getLogLevel() === 'debug') {
    console.error(error.stack);
  }

  process.exit(1);
}

/**
 * Handle shutdown signals
 */
function setupShutdownHandlers(server: ElectronMCPServer): void {
  const shutdown = async (signal: string) => {
    log('info', `Received ${signal}, shutting down gracefully...`);

    // Give stdio buffers time to flush
    setTimeout(() => {
      log('info', 'MCP server shutdown complete');
      process.exit(0);
    }, 100);
  };

  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));

  // Handle stdin close (parent process died)
  process.stdin.on('close', () => {
    log('warn', 'Parent process closed stdin, shutting down...');
    process.exit(0);
  });
}

// ============================================================================
// Main Execution
// ============================================================================

/**
 * Main entry point for MCP server wrapper
 */
async function main(): Promise<void> {
  log('info', `Starting MCP server wrapper (PID: ${process.pid})`);
  log('debug', 'Node version:', process.version);
  log('debug', 'Working directory:', process.cwd());
  log('debug', 'Arguments:', process.argv);
  log('debug', 'Environment:', {
    ELECTRON_MCP_LOG_LEVEL: process.env.ELECTRON_MCP_LOG_LEVEL,
    ELECTRON_MCP_TIMEOUT: process.env.ELECTRON_MCP_TIMEOUT
  });

  try {
    // Create MCP server instance
    log('info', 'Creating ElectronMCPServer instance...');
    const server = new ElectronMCPServer();

    // Setup graceful shutdown handlers
    setupShutdownHandlers(server);

    // Start server with timeout
    const timeout = getStartupTimeout();
    log('info', `Starting MCP server (timeout: ${timeout}ms)...`);

    const startupPromise = server.start();
    const timeoutPromise = new Promise<void>((_, reject) => {
      setTimeout(() => reject(new Error(`Server startup timeout (${timeout}ms)`)), timeout);
    });

    await Promise.race([startupPromise, timeoutPromise]);

    log('info', '✅ MCP server started successfully on stdio transport');
    log('info', 'Waiting for MCP requests via stdin/stdout...');

    // Keep process alive - stdio transport handles communication
    // The process will exit when:
    // 1. Parent process closes stdin (handled by setupShutdownHandlers)
    // 2. Shutdown signal received (SIGINT/SIGTERM)
    // 3. Uncaught error occurs (handled by global handlers)

  } catch (error) {
    if (error instanceof Error) {
      handleError(error);
    } else {
      handleError(new Error(String(error)));
    }
  }
}

// ============================================================================
// Global Error Handlers
// ============================================================================

process.on('uncaughtException', (error: Error) => {
  log('error', 'Uncaught exception:', error.message);
  if (getLogLevel() === 'debug') {
    console.error(error.stack);
  }
  process.exit(1);
});

process.on('unhandledRejection', (reason: unknown) => {
  const message = reason instanceof Error ? reason.message : String(reason);
  log('error', 'Unhandled promise rejection:', message);
  if (reason instanceof Error && getLogLevel() === 'debug') {
    console.error(reason.stack);
  }
  process.exit(1);
});

// ============================================================================
// Start Wrapper
// ============================================================================

// Check if this file is being run directly
const isMainModule =
  process.argv[1]?.endsWith('mcp-server-wrapper.ts') ||
  process.argv[1]?.endsWith('mcp-server-wrapper.js') ||
  process.argv[1]?.endsWith('mcp-server-wrapper');

if (isMainModule) {
  log('debug', 'MCP server wrapper starting as main module...');
  main().catch((error) => {
    console.error('[MCP-Wrapper] Fatal error in main():', error);
    process.exit(1);
  });
}

// Export for testing
export { main, log, ElectronMCPServer };
