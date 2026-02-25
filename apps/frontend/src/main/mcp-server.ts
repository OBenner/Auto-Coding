/**
 * MCP Server for Electron Frontend
 *
 * This module implements an embedded MCP (Model Context Protocol) server using the official SDK.
 * It provides tools for automated UI testing and AI/LLM interaction with the Electron application.
 *
 * Architecture:
 * - MCP Server runs in the main process
 * - Uses stdio transport (local only, no network exposure)
 * - Implements tools for window management, screenshots, UI interaction, and log reading
 * - Communicates with renderer via IPC bridge for DOM operations
 *
 * Security:
 * - All inputs validated with Zod schemas
 * - Context isolation enforced (no Node.js in renderer)
 * - Rate limiting per tool
 * - Error messages sanitized
 * - Screenshots compressed (< 1MB)
 * - Logs filtered for sensitive data
 *
 * @see MCP_ARCHITECTURE_DESIGN_1.2.md
 * @see SECURITY_REQUIREMENTS_AND_CONTEXT_ISOLATION_1.3.md
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { BrowserWindow, app, ipcMain } from 'electron';

// ============================================================================
// Constants
// ============================================================================

/** MCP server configuration */
const MCP_SERVER_CONFIG = {
  name: 'auto-claude-electron',
  version: '3.0.0'
} as const;

/** Screenshot size limit (1MB for Claude SDK JSON buffer) */
const MAX_SCREENSHOT_SIZE = 1_000_000;

/** Default JPEG quality for screenshots */
const DEFAULT_SCREENSHOT_QUALITY = 60;

/** Maximum log entries to keep in memory */
const MAX_LOG_ENTRIES = 1000;

/** IPC timeout in milliseconds */
const IPC_TIMEOUT = 10000;

/** Rate limit: max calls per tool per window */
const DEFAULT_RATE_LIMIT = 10;

/** Rate limit window in milliseconds */
const RATE_LIMIT_WINDOW = 1000;

/** Maximum message size for IPC (10MB) */
const MAX_IPC_MESSAGE_SIZE = 10_000_000;

/** MCP server startup timeout (ms) */
const MCP_STARTUP_TIMEOUT = 10_000;

// ============================================================================
// Types
// ============================================================================

/** Window information */
interface WindowInfo {
  id: number;
  title: string;
  url: string;
  focused: boolean;
  minimized: boolean;
  maximized: boolean;
  fullscreen: boolean;
  bounds: { x: number; y: number; width: number; height: number };
}

/** Console log entry */
interface LogEntry {
  level: string;
  message: string;
  timestamp: number;
  source: string;
}

/** Command execution result */
interface CommandResult {
  success: boolean;
  result?: unknown;
  error?: string;
}

/** Annotation task data */
interface AnnotationTask {
  id: string;
  element_selector: string;
  annotation_type: string;
  message: string;
  priority: string;
  context?: string;
  timestamp: number;
}

// ============================================================================
// Zod Schemas (Input Validation)
// ============================================================================

/**
 * Schema for take_screenshot tool
 * - windowId: optional positive integer
 * - quality: optional integer 1-100 (default 60)
 */
const takeScreenshotSchema = z.object({
  windowId: z.number().int().positive().max(2147483647).optional(),
  quality: z.number().int().min(1).max(100).optional()
});

/**
 * Schema for send_command tool
 * - command: enum of allowed commands
 * - args: command-specific arguments (strict validation)
 */
const sendCommandSchema = z.object({
  command: z.enum([
    'click_by_text',
    'click_by_selector',
    'fill_input',
    'select_option',
    'send_keyboard_shortcut',
    'navigate_to_hash',
    'get_page_structure',
    'debug_elements',
    'verify_form_state',
    'eval'
  ]),
  args: z
    .object({
      selector: z.string().max(1000).optional(),
      code: z.string().max(10000).optional(),
      text: z.string().max(500).optional(),
      placeholder: z.string().max(200).optional(),
      value: z.string().max(1000).optional(),
      hash: z.string().max(500).optional()
    })
    .strict()
    .optional()
});

/**
 * Schema for read_logs tool
 * - level: optional log level filter
 * - limit: optional integer 1-1000 (default 100)
 * - since: optional timestamp filter
 */
const readLogsSchema = z.object({
  level: z.enum(['debug', 'log', 'info', 'warn', 'error']).optional(),
  limit: z.number().int().min(1).max(1000).optional(),
  since: z.number().optional()
});

/**
 * Schema for create_annotation_task tool
 * - element_selector: CSS selector for element to annotate
 * - annotation_type: Type of annotation (comment, suggestion, issue, question)
 * - message: Annotation message content
 * - priority: Optional priority level (low, medium, high)
 * - context: Optional additional context
 */
const createAnnotationTaskSchema = z.object({
  element_selector: z.string().max(1000),
  annotation_type: z.enum(['comment', 'suggestion', 'issue', 'question']),
  message: z.string().min(1).max(5000),
  priority: z.enum(['low', 'medium', 'high']).optional(),
  context: z.string().max(2000).optional()
});

// ============================================================================
// Log Collector
// ============================================================================

/**
 * Collects console logs from renderer processes
 * - Attaches to all windows (existing and new)
 * - Filters sensitive data (tokens, passwords, API keys)
 * - Limits memory usage (MAX_LOG_ENTRIES)
 */
class LogCollector {
  private logs: LogEntry[] = [];
  // Constrained patterns with limited quantifiers to avoid ReDoS
  private readonly SENSITIVE_PATTERNS = [
    /token["\s:=]+[a-zA-Z0-9\-_]{1,200}/gi,
    /password["\s:=]+.{1,200}/gi,
    /api[_-]?key["\s:=]+[a-zA-Z0-9\-_]{1,200}/gi,
    /secret["\s:=]+.{1,200}/gi,
    /authorization["\s:=]+.{1,200}/gi
  ];

  constructor() {
    this.attachToAllWindows();
  }

  /**
   * Attach to existing windows and listen for new windows
   */
  private attachToAllWindows(): void {
    // Attach to existing windows
    BrowserWindow.getAllWindows().forEach(win => this.attachToWindow(win));

    // Attach to new windows
    app.on('browser-window-created', (_event: Electron.Event, win: Electron.BrowserWindow) => {
      this.attachToWindow(win);
    });
  }

  /**
   * Attach log collector to a specific window
   */
  attachToWindow(win: Electron.BrowserWindow): void {
    win.webContents.on('console-message', (_event: Electron.Event, level: number, message: string, line: number, sourceId: string) => {
      const filtered = this.filterLog(message);

      this.logs.push({
        level: this.getLevelName(level),
        message: filtered,
        timestamp: Date.now(),
        source: `${sourceId}:${line}`
      });

      // Keep only last MAX_LOG_ENTRIES logs
      if (this.logs.length > MAX_LOG_ENTRIES) {
        this.logs.shift();
      }
    });
  }

  /**
   * Get log level name from Electron level number
   */
  private getLevelName(level: number): string {
    const levels = ['debug', 'log', 'info', 'warn', 'error'];
    return levels[level] || 'log';
  }

  /**
   * Filter sensitive information from log messages.
   * Caps input length to prevent ReDoS on very large messages.
   */
  private filterLog(message: string): string {
    // Cap input length to prevent regex performance issues
    const capped = message.length > 10000 ? message.substring(0, 10000) : message;
    let filtered = capped;

    for (const pattern of this.SENSITIVE_PATTERNS) {
      filtered = filtered.replace(pattern, '[REDACTED]');
    }

    return filtered;
  }

  /**
   * Get logs with optional filtering
   */
  getLogs(params: { level?: string; limit?: number; since?: number }): string {
    let filtered = this.logs;

    // Filter by level
    if (params.level) {
      filtered = filtered.filter(log => log.level === params.level);
    }

    // Filter by timestamp
    if (params.since) {
      filtered = filtered.filter(log => log.timestamp >= params.since!);
    }

    // Limit results
    const limit = params.limit ?? 100;
    const sliced = filtered.slice(-limit);

    return JSON.stringify(sliced, null, 2);
  }
}

// ============================================================================
// Rate Limiter
// ============================================================================

/**
 * Rate limiter for MCP tool calls
 * - Prevents DoS via rapid tool calls
 * - Per-tool rate limiting with sliding window
 */
class RateLimiter {
  private calls: Map<string, number[]> = new Map();

  /**
   * Check if tool can be executed (rate limit check)
   * @param toolName - Tool name
   * @param maxCalls - Maximum calls allowed in window
   * @param windowMs - Time window in milliseconds
   * @returns true if allowed, false if rate limit exceeded
   */
  canExecute(toolName: string, maxCalls: number = DEFAULT_RATE_LIMIT, windowMs: number = RATE_LIMIT_WINDOW): boolean {
    const now = Date.now();
    const timestamps = this.calls.get(toolName) || [];

    // Remove old timestamps outside window
    const recent = timestamps.filter(t => now - t < windowMs);

    if (recent.length >= maxCalls) {
      console.warn(`[MCP Security] Rate limit exceeded for ${toolName}`);
      return false;
    }

    recent.push(now);
    this.calls.set(toolName, recent);
    return true;
  }

  /**
   * Reset rate limit for a specific tool or all tools
   */
  reset(toolName?: string): void {
    if (toolName) {
      this.calls.delete(toolName);
    } else {
      this.calls.clear();
    }
  }
}

// ============================================================================
// IPC Bridge
// ============================================================================

/**
 * IPC bridge for communicating with renderer process
 * - Sends commands to renderer via IPC
 * - Handles timeouts with proper listener cleanup
 * - Validates message size using byte length
 */
class IPCBridge {
  /**
   * Execute a command in the renderer process
   * @param command - Command name
   * @param args - Command arguments
   * @returns Command execution result
   */
  async executeCommand(command: string, args: Record<string, unknown> = {}): Promise<CommandResult> {
    const win = BrowserWindow.getFocusedWindow();
    if (!win) {
      return { success: false, error: 'No focused window' };
    }

    // Validate message size using byte length for accuracy
    const json = JSON.stringify({ command, args });
    const dataSize = Buffer.byteLength(json, 'utf8');
    if (dataSize > MAX_IPC_MESSAGE_SIZE) {
      return { success: false, error: `Message too large: ${dataSize} bytes` };
    }

    return new Promise((resolve) => {
      const responseChannel = 'mcp-execute-command-response';

      const handler = (_event: Electron.IpcMainEvent, result: CommandResult) => {
        clearTimeout(timeout);
        resolve(result);
      };

      const timeout = setTimeout(() => {
        // Remove listener on timeout to prevent memory leak
        ipcMain.removeListener(responseChannel, handler);
        resolve({ success: false, error: 'IPC timeout: renderer did not respond' });
      }, IPC_TIMEOUT);

      // Listen for response (once auto-removes after first call)
      ipcMain.once(responseChannel, handler);

      // Send command to renderer
      win.webContents.send('mcp-execute-command', { command, args });
    });
  }
}

// ============================================================================
// Error Sanitization
// ============================================================================

/**
 * Sanitize error messages to prevent information disclosure
 * - Removes file paths
 * - Removes stack traces
 * - Limits length
 */
function sanitizeError(error: unknown): string {
  if (error instanceof Error) {
    // Cap input to prevent regex performance issues on very large messages
    const msg = error.message.length > 2000 ? error.message.substring(0, 2000) : error.message;
    // Strip "at func (...)" stack trace segments (safe: negated classes don't overlap)
    let sanitized = msg.replace(/at [^(]*\([^)]*\)/g, '');
    // Strip file path:line:col references using token replacement to avoid
    // regex backtracking (SonarCloud S5852). Each whitespace-delimited token
    // is checked independently with a simple anchored pattern.
    sanitized = sanitized.replace(/\S+/g, (token) =>
      /\.(js|ts|jsx|tsx):\d+:\d+$/.test(token) ? '' : token
    );
    return sanitized.replace(/ {2,}/g, ' ').trim();
  }

  if (typeof error === 'string') {
    return error.substring(0, 200);
  }

  return 'Unknown error';
}

/**
 * Create a standardized error result for MCP tool responses.
 * Centralizes error formatting to avoid duplication across tool handlers.
 */
function toolErrorResult(error: unknown, extraFields?: Record<string, unknown>): CallToolResult {
  const payload = { ...extraFields, error: sanitizeError(error) };
  return {
    content: [{ type: 'text', text: JSON.stringify(payload) }],
    isError: true
  };
}

// ============================================================================
// Blocked eval patterns
// ============================================================================

/** Patterns blocked in eval commands to prevent code execution escapes */
const BLOCKED_EVAL_PATTERNS = [
  'require(',
  'import(',
  'process.',
  'child_process',
  'global.',
  '__dirname',
  '__filename',
  'Function(',
  'new Function',
  'window.eval',
];

// ============================================================================
// MCP Server Implementation
// ============================================================================

/**
 * Electron MCP Server
 *
 * Main MCP server class that:
 * - Initializes MCP server with stdio transport
 * - Registers all tools
 * - Handles tool execution
 * - Enforces security policies
 */
export class ElectronMCPServer {
  private server: McpServer;
  private logCollector: LogCollector;
  private ipcBridge: IPCBridge;
  private rateLimiter: RateLimiter;
  private startTime: number;

  constructor() {
    this.server = new McpServer(MCP_SERVER_CONFIG);
    this.logCollector = new LogCollector();
    this.ipcBridge = new IPCBridge();
    this.rateLimiter = new RateLimiter();
    this.startTime = Date.now();

    this.registerTools();
  }

  /**
   * Start the MCP server with stdio transport.
   * Includes a startup timeout to prevent hanging.
   */
  async start(): Promise<void> {
    const transport = new StdioServerTransport();

    const connectPromise = this.server.connect(transport);
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error(`MCP server startup timeout (${MCP_STARTUP_TIMEOUT}ms)`)), MCP_STARTUP_TIMEOUT);
    });

    await Promise.race([connectPromise, timeoutPromise]);
    console.log(`[MCP] Server started on stdio (PID: ${process.pid})`);
    console.log('[MCP] Transport: stdio (local only, no network exposure)');
  }

  /**
   * Stop the MCP server and clean up resources.
   */
  async stop(): Promise<void> {
    try {
      await this.server.close();
      console.log('[MCP] Server stopped');
    } catch (error) {
      console.error('[MCP] Error during shutdown:', error);
    }
  }

  /**
   * Register all MCP tools
   */
  private registerTools(): void {
    // Tool 1: get_window_info
    this.server.tool(
      'get_window_info',
      'Get information about all Electron windows',
      {},
      async () => this.getWindowInfo()
    );

    // Tool 2: take_screenshot
    this.server.tool(
      'take_screenshot',
      'Capture screenshot of window (compressed to JPEG, max 1MB)',
      takeScreenshotSchema.shape,
      async (params: z.infer<typeof takeScreenshotSchema>) => this.takeScreenshot(params)
    );

    // Tool 3: send_command
    this.server.tool(
      'send_command',
      'Execute UI interaction command in renderer process',
      sendCommandSchema.shape,
      async (params: z.infer<typeof sendCommandSchema>) => this.sendCommand(params)
    );

    // Tool 4: read_logs
    this.server.tool(
      'read_logs',
      'Read console logs from renderer process (filtered for sensitive data)',
      readLogsSchema.shape,
      async (params: z.infer<typeof readLogsSchema>) => this.readLogs(params)
    );

    // Tool 5: create_annotation_task
    this.server.tool(
      'create_annotation_task',
      'Create an annotation task for UX feedback on UI elements',
      createAnnotationTaskSchema.shape,
      async (params: z.infer<typeof createAnnotationTaskSchema>) => this.createAnnotationTask(params)
    );

    // Tool 6: health_check
    this.server.tool(
      'health_check',
      'Get MCP server health metrics',
      {},
      async () => this.healthCheck()
    );

    console.log('[MCP] Registered 6 tools: get_window_info, take_screenshot, send_command, read_logs, create_annotation_task, health_check');
  }

  /**
   * Tool: get_window_info
   * Returns metadata about all Electron windows
   */
  private async getWindowInfo(): Promise<CallToolResult> {
    try {
      const windows = BrowserWindow.getAllWindows();
      const windowInfo: WindowInfo[] = windows.map(w => ({
        id: w.id,
        title: w.title,
        url: w.webContents.getURL(),
        focused: w.isFocused(),
        minimized: w.isMinimized(),
        maximized: w.isMaximized(),
        fullscreen: w.isFullScreen(),
        bounds: w.getBounds()
      }));

      return {
        content: [{
          type: 'text',
          text: JSON.stringify(windowInfo, null, 2)
        }]
      };
    } catch (error) {
      return toolErrorResult(error);
    }
  }

  /**
   * Tool: take_screenshot
   * Captures screenshot of window, compressed to JPEG.
   * Uses recompressed buffer when initial size exceeds limit.
   */
  private async takeScreenshot(params: z.infer<typeof takeScreenshotSchema>): Promise<CallToolResult> {
    try {
      // Validate input
      const validated = takeScreenshotSchema.parse(params);

      // Rate limit check
      if (!this.rateLimiter.canExecute('take_screenshot', 10, 1000)) {
        throw new Error('Rate limit exceeded for take_screenshot');
      }

      // Get window
      const win = validated.windowId
        ? BrowserWindow.fromId(validated.windowId)
        : BrowserWindow.getFocusedWindow();

      if (!win) {
        throw new Error(`Window not found: ${validated.windowId}`);
      }

      // Capture screenshot
      const image = await win.webContents.capturePage();
      const quality = validated.quality ?? DEFAULT_SCREENSHOT_QUALITY;
      let buffer = image.toJPEG(quality);

      // Validate size and recompress if needed
      if (buffer.length > MAX_SCREENSHOT_SIZE) {
        const compressed = image.toJPEG(40);
        if (compressed.length > MAX_SCREENSHOT_SIZE) {
          throw new Error(`Screenshot too large: ${compressed.length} bytes (max: ${MAX_SCREENSHOT_SIZE})`);
        }
        console.warn(`[MCP] Screenshot ${buffer.length} bytes compressed to ${compressed.length} bytes`);
        buffer = compressed;
      }

      // Verify base64 size stays under limit (~33% larger than raw)
      const base64Size = Math.ceil(buffer.length * 4 / 3);
      if (base64Size > MAX_SCREENSHOT_SIZE) {
        throw new Error(`Screenshot base64 too large: ${base64Size} bytes (max: ${MAX_SCREENSHOT_SIZE})`);
      }

      return {
        content: [{
          type: 'image',
          data: buffer.toString('base64'),
          mimeType: 'image/jpeg'
        }]
      };
    } catch (error) {
      return toolErrorResult(error);
    }
  }

  /**
   * Tool: send_command
   * Sends a command to the renderer process for execution
   */
  private async sendCommand(params: z.infer<typeof sendCommandSchema>): Promise<CallToolResult> {
    try {
      // Validate input
      const validated = sendCommandSchema.parse(params);

      // Rate limit check (eval has stricter limit)
      const limit = validated.command === 'eval' ? 5 : 50;
      if (!this.rateLimiter.canExecute(`send_command:${validated.command}`, limit, 1000)) {
        throw new Error(`Rate limit exceeded for ${validated.command}`);
      }

      // Check for blocked patterns in eval
      if (validated.command === 'eval' && validated.args?.code) {
        for (const pattern of BLOCKED_EVAL_PATTERNS) {
          if (validated.args.code.includes(pattern)) {
            throw new Error(`Blocked pattern: ${pattern}`);
          }
        }
      }

      // Execute command via IPC
      const result = await this.ipcBridge.executeCommand(validated.command, validated.args);

      return {
        content: [{
          type: 'text',
          text: JSON.stringify(result, null, 2)
        }]
      };
    } catch (error) {
      return toolErrorResult(error, { success: false });
    }
  }

  /**
   * Tool: read_logs
   * Reads console logs from renderer process
   */
  private async readLogs(params: z.infer<typeof readLogsSchema>): Promise<CallToolResult> {
    try {
      // Validate input
      const validated = readLogsSchema.parse(params);

      // Rate limit check
      if (!this.rateLimiter.canExecute('read_logs', 20, 1000)) {
        throw new Error('Rate limit exceeded for read_logs');
      }

      // Get logs
      const logs = this.logCollector.getLogs({
        level: validated.level,
        limit: validated.limit,
        since: validated.since
      });

      return {
        content: [{
          type: 'text',
          text: logs
        }]
      };
    } catch (error) {
      return toolErrorResult(error);
    }
  }

  /**
   * Tool: health_check
   * Returns MCP server health metrics
   */
  private async healthCheck(): Promise<CallToolResult> {
    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          status: 'healthy',
          uptime: Date.now() - this.startTime,
          pid: process.pid,
          memory: process.memoryUsage(),
          windows: BrowserWindow.getAllWindows().length,
          version: MCP_SERVER_CONFIG.version
        }, null, 2)
      }]
    };
  }

  /**
   * Tool: create_annotation_task
   * Creates an annotation task for UX feedback on UI elements
   */
  private async createAnnotationTask(params: z.infer<typeof createAnnotationTaskSchema>): Promise<CallToolResult> {
    try {
      // Validate input
      const validated = createAnnotationTaskSchema.parse(params);

      // Rate limit check
      if (!this.rateLimiter.canExecute('create_annotation_task', 20, 1000)) {
        throw new Error('Rate limit exceeded for create_annotation_task');
      }

      // Generate unique task ID
      const taskId = `annotation-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;

      // Create annotation task
      const task: AnnotationTask = {
        id: taskId,
        element_selector: validated.element_selector,
        annotation_type: validated.annotation_type,
        message: validated.message,
        priority: validated.priority ?? 'medium',
        context: validated.context,
        timestamp: Date.now()
      };

      // Send annotation task to renderer via IPC
      const win = BrowserWindow.getFocusedWindow();
      if (win) {
        win.webContents.send('annotation-task-created', task);
      }

      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            success: true,
            task: task
          }, null, 2)
        }]
      };
    } catch (error) {
      return toolErrorResult(error, { success: false });
    }
  }
}

// ============================================================================
// Server Entry Point (for standalone execution)
// ============================================================================

/**
 * Start MCP server if this file is run directly
 * This is used when spawning the MCP server as a separate process
 */
if (process.argv[1]?.endsWith('mcp-server.ts') || process.argv[1]?.endsWith('mcp-server.js')) {
  const server = new ElectronMCPServer();
  server.start().catch((error) => {
    console.error('[MCP] Failed to start server:', error);
    process.exit(1);
  });
}
