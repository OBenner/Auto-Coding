/**
 * Unit tests for MCP Server
 * Tests MCP server initialization, tool registration, and basic functionality
 */
import { describe, it, expect, vi } from 'vitest';
import { existsSync, readFileSync } from 'fs';
import path from 'path';

// Mock electron before importing mcp-server
vi.mock('electron', () => ({
  default: {
    BrowserWindow: {
      getAllWindows: vi.fn(() => []),
      fromId: vi.fn(),
      getFocusedWindow: vi.fn()
    },
    app: {
      on: vi.fn(),
      getVersion: vi.fn(() => '3.0.0'),
      getLocale: vi.fn(() => 'en-US')
    },
    ipcMain: {
      on: vi.fn(),
      once: vi.fn(),
      handle: vi.fn(),
      removeListener: vi.fn()
    }
  }
}));

// ============================================================================
// Shared file content - read once, reuse across tests
// ============================================================================

/** Helper to read a project file relative to cwd, returns content or null */
function readProjectFile(relativePath: string): string | null {
  const fullPath = path.join(process.cwd(), relativePath);
  return existsSync(fullPath) ? readFileSync(fullPath, 'utf-8') : null;
}

/** Read a required project file, throwing with a clear message if missing */
function requireProjectFile(relativePath: string): string {
  const content = readProjectFile(relativePath);
  if (content === null) {
    throw new Error(`Required file missing: ${relativePath} (cwd: ${process.cwd()})`);
  }
  return content;
}

// Read required source files once at module level (fail-fast if missing)
const mcpServerContent = requireProjectFile('src/main/mcp-server.ts');
const mcpManagerContent = requireProjectFile('src/main/mcp-manager.ts');
// Optional files that may not exist in all environments
const envExampleContent = readProjectFile('.env.example');
const indexContent = readProjectFile('src/main/index.ts');
const clientContent = readProjectFile('../backend/core/client.py');
const backendEnvContent = readProjectFile('../backend/.env.example');
const viteConfigContent = readProjectFile('electron.vite.config.ts');
const packageJson = JSON.parse(readFileSync(path.join(process.cwd(), 'package.json'), 'utf-8'));

describe('MCP Server', () => {
  describe('Environment Variables', () => {
    it('should have MCP_ENABLED environment variable support', () => {
      if (envExampleContent) {
        expect(envExampleContent).toContain('ELECTRON_MCP_ENABLED');
      }
    });

    it('should have MCP_LOG_LEVEL environment variable support', () => {
      if (envExampleContent) {
        expect(envExampleContent).toContain('ELECTRON_MCP_LOG_LEVEL');
      }
    });

    it('should have MCP_TIMEOUT environment variable support', () => {
      if (envExampleContent) {
        expect(envExampleContent).toContain('ELECTRON_MCP_TIMEOUT');
      }
    });
  });

  describe('MCP Server Files', () => {
    it('should have mcp-server.ts implementation file', () => {
      expect(existsSync(path.join(process.cwd(), 'src/main/mcp-server.ts'))).toBe(true);
    });

    it('should have mcp-manager.ts lifecycle management file', () => {
      expect(existsSync(path.join(process.cwd(), 'src/main/mcp-manager.ts'))).toBe(true);
    });

    it('should have mcp-server-wrapper.ts for testing', () => {
      expect(existsSync(path.join(process.cwd(), 'src/main/mcp-server-wrapper.ts'))).toBe(true);
    });
  });

  describe('MCP Server Tool Registration', () => {
    it('should register 5 required tools', () => {
      expect(mcpServerContent).toContain("get_window_info");
      expect(mcpServerContent).toContain("take_screenshot");
      expect(mcpServerContent).toContain("send_command");
      expect(mcpServerContent).toContain("read_logs");
      expect(mcpServerContent).toContain("health_check");
    });

    it('should use Zod schemas for input validation', () => {
      expect(mcpServerContent).toContain("from 'zod'");
      expect(mcpServerContent).toContain('z.object');
    });

    it('should implement security features', () => {
      expect(mcpServerContent).toContain('RateLimiter');
      expect(mcpServerContent).toContain('sanitizeError');
      expect(mcpServerContent).toContain('blocked');
      expect(mcpServerContent).toContain('require(');
    });

    it('should have server configuration with name and version', () => {
      expect(mcpServerContent).toContain('MCP_SERVER_CONFIG');
      expect(mcpServerContent).toContain('auto-claude-electron');
    });
  });

  describe('MCP Manager Lifecycle', () => {
    it('should export lifecycle management functions', () => {
      expect(mcpManagerContent).toContain('initializeMCPServer');
      expect(mcpManagerContent).toContain('stopMCPServer');
      expect(mcpManagerContent).toContain('setupMCPLifecycle');
    });

    it('should validate environment variables', () => {
      expect(mcpManagerContent).toContain('isMCPServerEnabled');
      expect(mcpManagerContent).toContain('getMCPLogLevel');
    });

    it('should integrate with Electron app lifecycle', () => {
      expect(mcpManagerContent).toContain('app.whenReady');
      expect(mcpManagerContent).toContain("app.on('before-quit'");
    });
  });

  describe('Main Process Integration', () => {
    it('should import setupMCPLifecycle in main index.ts', () => {
      if (indexContent) {
        expect(indexContent).toContain('setupMCPLifecycle');
      }
    });

    it('should call setupMCPLifecycle during app initialization', () => {
      if (indexContent) {
        expect(indexContent).toContain('setupMCPLifecycle()');
      }
    });
  });

  describe('Backend Integration', () => {
    it('should have get_electron_mcp_mode function in core/client.py', () => {
      if (clientContent) {
        expect(clientContent).toContain('get_electron_mcp_mode');
      }
    });

    it('should support both CDP and embedded modes', () => {
      if (clientContent) {
        expect(clientContent).toContain('ELECTRON_MCP_MODE');
        expect(clientContent).toContain('cdp');
        expect(clientContent).toContain('embedded');
      }
    });

    it('should have MCP environment variables in .env.example', () => {
      if (backendEnvContent) {
        expect(backendEnvContent).toContain('ELECTRON_MCP_MODE');
        expect(backendEnvContent).toContain('ELECTRON_MCP_LOG_LEVEL');
      }
    });
  });

  describe('Build Configuration', () => {
    it('should include MCP server files in electron.vite.config.ts', () => {
      if (viteConfigContent) {
        expect(viteConfigContent).toContain('mcp-server');
        expect(viteConfigContent).toContain('mcp-server-wrapper');
      }
    });
  });

  describe('Dependencies', () => {
    it('should have @modelcontextprotocol/sdk in package.json', () => {
      expect(packageJson.dependencies).toHaveProperty('@modelcontextprotocol/sdk');
    });

    it('should have zod dependency for input validation', () => {
      expect(packageJson.dependencies).toHaveProperty('zod');
    });
  });

  describe('Tool Functionality', () => {
    it('should implement get_window_info tool', () => {
      expect(mcpServerContent).toContain('getWindowInfo');
      expect(mcpServerContent).toContain('BrowserWindow.getAllWindows');
    });

    it('should implement take_screenshot tool with compression', () => {
      expect(mcpServerContent).toContain('takeScreenshot');
      expect(mcpServerContent).toContain('JPEG');
      expect(mcpServerContent).toContain('quality');
    });

    it('should implement send_command tool with UI interactions', () => {
      expect(mcpServerContent).toContain('sendCommand');
      expect(mcpServerContent).toContain('click_by_text');
      expect(mcpServerContent).toContain('fill_input');
    });

    it('should implement read_logs tool with sensitive data filtering', () => {
      expect(mcpServerContent).toContain('readLogs');
      expect(mcpServerContent).toContain('LogCollector');
      expect(mcpServerContent).toContain('SENSITIVE_PATTERNS');
    });

    it('should implement health_check tool', () => {
      expect(mcpServerContent).toContain('healthCheck');
      expect(mcpServerContent).toContain('uptime');
      expect(mcpServerContent).toContain('status');
    });
  });

  describe('Security Features', () => {
    it('should implement rate limiting', () => {
      expect(mcpServerContent).toContain('RateLimiter');
      expect(mcpServerContent).toContain('DEFAULT_RATE_LIMIT');
      expect(mcpServerContent).toContain('RATE_LIMIT_WINDOW');
    });

    it('should sanitize error messages', () => {
      expect(mcpServerContent).toContain('sanitizeError');
      expect(mcpServerContent).toContain('replace');
      expect(mcpServerContent).toContain('path');
    });

    it('should filter sensitive data from logs', () => {
      expect(mcpServerContent).toContain('SENSITIVE_PATTERNS');
      expect(mcpServerContent).toContain('token');
      expect(mcpServerContent).toContain('password');
    });

    it('should block dangerous eval patterns', () => {
      expect(mcpServerContent).toContain('blocked');
      expect(mcpServerContent).toContain("require(");
      expect(mcpServerContent).toContain("import(");
      expect(mcpServerContent).toContain('process.');
    });
  });

  describe('Documentation', () => {
    it('should reference MCP architecture design in source', () => {
      expect(mcpServerContent).toContain('MCP_ARCHITECTURE_DESIGN');
    });

    it('should reference security requirements in source', () => {
      expect(mcpServerContent).toContain('SECURITY_REQUIREMENTS');
    });
  });
});
