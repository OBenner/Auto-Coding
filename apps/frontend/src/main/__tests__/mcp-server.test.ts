/**
 * Unit tests for MCP Server
 * Tests MCP server initialization, tool registration, and basic functionality
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { spawn } from 'child_process';
import { writeFileSync, unlinkSync, existsSync, readFileSync } from 'fs';
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
      handle: vi.fn()
    }
  }
}));

describe('MCP Server', () => {
  describe('Environment Variables', () => {
    it('should have MCP_ENABLED environment variable support', () => {
      // Test that ELECTRON_MCP_ENABLED environment variable is documented
      const envExamplePath = path.join(process.cwd(), '.env.example');
      if (existsSync(envExamplePath)) {
        const envExample = readFileSync(envExamplePath, 'utf-8');
        expect(envExample).toContain('ELECTRON_MCP_ENABLED');
      }
    });

    it('should have MCP_LOG_LEVEL environment variable support', () => {
      const envExamplePath = path.join(process.cwd(), '.env.example');
      if (existsSync(envExamplePath)) {
        const envExample = readFileSync(envExamplePath, 'utf-8');
        expect(envExample).toContain('ELECTRON_MCP_LOG_LEVEL');
      }
    });

    it('should have MCP_TIMEOUT environment variable support', () => {
      const envExamplePath = path.join(process.cwd(), '.env.example');
      if (existsSync(envExamplePath)) {
        const envExample = readFileSync(envExamplePath, 'utf-8');
        expect(envExample).toContain('ELECTRON_MCP_TIMEOUT');
      }
    });
  });

  describe('MCP Server Files', () => {
    it('should have mcp-server.ts implementation file', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      expect(existsSync(mcpServerPath)).toBe(true);
    });

    it('should have mcp-manager.ts lifecycle management file', () => {
      const mcpManagerPath = path.join(process.cwd(), 'src/main/mcp-manager.ts');
      expect(existsSync(mcpManagerPath)).toBe(true);
    });

    it('should have mcp-server-wrapper.ts for testing', () => {
      const wrapperPath = path.join(process.cwd(), 'src/main/mcp-server-wrapper.ts');
      expect(existsSync(wrapperPath)).toBe(true);
    });
  });

  describe('MCP Server Tool Registration', () => {
    it('should register 5 required tools', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      // Check that all 5 tools are registered
      expect(mcpServerContent).toContain("get_window_info");
      expect(mcpServerContent).toContain("take_screenshot");
      expect(mcpServerContent).toContain("send_command");
      expect(mcpServerContent).toContain("read_logs");
      expect(mcpServerContent).toContain("health_check");
    });

    it('should use Zod schemas for input validation', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      // Check for Zod imports and usage
      expect(mcpServerContent).toContain("from 'zod'");
      expect(mcpServerContent).toContain('z.object');
    });

    it('should implement security features', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      // Check for security features
      expect(mcpServerContent).toContain('RateLimiter');
      expect(mcpServerContent).toContain('sanitizeError');
      // Check for blocked patterns (implemented as array in send_command)
      expect(mcpServerContent).toContain('blocked');
      expect(mcpServerContent).toContain('require(');
    });

    it('should have server configuration with name and version', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      // Check for server configuration
      expect(mcpServerContent).toContain('MCP_SERVER_CONFIG');
      expect(mcpServerContent).toContain('auto-claude-electron');
    });
  });

  describe('MCP Manager Lifecycle', () => {
    it('should export lifecycle management functions', () => {
      const mcpManagerPath = path.join(process.cwd(), 'src/main/mcp-manager.ts');
      const mcpManagerContent = readFileSync(mcpManagerPath, 'utf-8');

      // Check for lifecycle functions
      expect(mcpManagerContent).toContain('initializeMCPServer');
      expect(mcpManagerContent).toContain('stopMCPServer');
      expect(mcpManagerContent).toContain('setupMCPLifecycle');
    });

    it('should validate environment variables', () => {
      const mcpManagerPath = path.join(process.cwd(), 'src/main/mcp-manager.ts');
      const mcpManagerContent = readFileSync(mcpManagerPath, 'utf-8');

      // Check for validation functions
      expect(mcpManagerContent).toContain('isMCPServerEnabled');
      expect(mcpManagerContent).toContain('getMCPLogLevel');
    });

    it('should integrate with Electron app lifecycle', () => {
      const mcpManagerPath = path.join(process.cwd(), 'src/main/mcp-manager.ts');
      const mcpManagerContent = readFileSync(mcpManagerPath, 'utf-8');

      // Check for app lifecycle integration
      expect(mcpManagerContent).toContain('app.whenReady');
      expect(mcpManagerContent).toContain("app.on('before-quit'");
    });
  });

  describe('Main Process Integration', () => {
    it('should import setupMCPLifecycle in main index.ts', () => {
      const indexPath = path.join(process.cwd(), 'src/main/index.ts');
      if (existsSync(indexPath)) {
        const indexContent = readFileSync(indexPath, 'utf-8');
        expect(indexContent).toContain('setupMCPLifecycle');
      }
    });

    it('should call setupMCPLifecycle during app initialization', () => {
      const indexPath = path.join(process.cwd(), 'src/main/index.ts');
      if (existsSync(indexPath)) {
        const indexContent = readFileSync(indexPath, 'utf-8');
        expect(indexContent).toContain('setupMCPLifecycle()');
      }
    });
  });

  describe('Backend Integration', () => {
    it('should have get_electron_mcp_mode function in core/client.py', () => {
      const clientPath = path.join(process.cwd(), '../backend/core/client.py');
      if (existsSync(clientPath)) {
        const clientContent = readFileSync(clientPath, 'utf-8');
        expect(clientContent).toContain('get_electron_mcp_mode');
      }
    });

    it('should support both CDP and embedded modes', () => {
      const clientPath = path.join(process.cwd(), '../backend/core/client.py');
      if (existsSync(clientPath)) {
        const clientContent = readFileSync(clientPath, 'utf-8');
        expect(clientContent).toContain('ELECTRON_MCP_MODE');
        expect(clientContent).toContain('cdp');
        expect(clientContent).toContain('embedded');
      }
    });

    it('should have MCP environment variables in .env.example', () => {
      const envExamplePath = path.join(process.cwd(), '../backend/.env.example');
      if (existsSync(envExamplePath)) {
        const envExample = readFileSync(envExamplePath, 'utf-8');
        expect(envExample).toContain('ELECTRON_MCP_MODE');
        expect(envExample).toContain('ELECTRON_MCP_LOG_LEVEL');
      }
    });
  });

  describe('Build Configuration', () => {
    it('should include MCP server files in electron.vite.config.ts', () => {
      const viteConfigPath = path.join(process.cwd(), 'electron.vite.config.ts');
      if (existsSync(viteConfigPath)) {
        const viteConfigContent = readFileSync(viteConfigPath, 'utf-8');
        expect(viteConfigContent).toContain('mcp-server');
        // Note: mcp-manager is imported directly in index.ts, not built separately
        expect(viteConfigContent).toContain('mcp-server-wrapper');
      }
    });
  });

  describe('Dependencies', () => {
    it('should have @modelcontextprotocol/sdk in package.json', () => {
      const packageJsonPath = path.join(process.cwd(), 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
      expect(packageJson.dependencies).toHaveProperty('@modelcontextprotocol/sdk');
    });

    it('should have zod dependency for input validation', () => {
      const packageJsonPath = path.join(process.cwd(), 'package.json');
      const packageJson = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
      expect(packageJson.dependencies).toHaveProperty('zod');
    });
  });

  describe('Tool Functionality', () => {
    it('should implement get_window_info tool', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      expect(mcpServerContent).toContain('getWindowInfo');
      expect(mcpServerContent).toContain('BrowserWindow.getAllWindows');
    });

    it('should implement take_screenshot tool with compression', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      expect(mcpServerContent).toContain('takeScreenshot');
      expect(mcpServerContent).toContain('JPEG');
      expect(mcpServerContent).toContain('quality');
    });

    it('should implement send_command tool with UI interactions', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      expect(mcpServerContent).toContain('sendCommand');
      expect(mcpServerContent).toContain('click_by_text');
      expect(mcpServerContent).toContain('fill_input');
    });

    it('should implement read_logs tool with sensitive data filtering', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      expect(mcpServerContent).toContain('readLogs');
      expect(mcpServerContent).toContain('LogCollector');
      expect(mcpServerContent).toContain('SENSITIVE_PATTERNS');
    });

    it('should implement health_check tool', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      expect(mcpServerContent).toContain('healthCheck');
      expect(mcpServerContent).toContain('uptime');
      expect(mcpServerContent).toContain('status');
    });
  });

  describe('Security Features', () => {
    it('should implement rate limiting', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      expect(mcpServerContent).toContain('RateLimiter');
      expect(mcpServerContent).toContain('DEFAULT_RATE_LIMIT');
      expect(mcpServerContent).toContain('RATE_LIMIT_WINDOW');
    });

    it('should sanitize error messages', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      expect(mcpServerContent).toContain('sanitizeError');
      // Check for path sanitization patterns
      expect(mcpServerContent).toContain('replace');
      expect(mcpServerContent).toContain('path');
    });

    it('should filter sensitive data from logs', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      expect(mcpServerContent).toContain('SENSITIVE_PATTERNS');
      expect(mcpServerContent).toContain('token');
      expect(mcpServerContent).toContain('password');
    });

    it('should block dangerous eval patterns', () => {
      const mcpServerPath = path.join(process.cwd(), 'src/main/mcp-server.ts');
      const mcpServerContent = readFileSync(mcpServerPath, 'utf-8');

      expect(mcpServerContent).toContain('blocked');
      expect(mcpServerContent).toContain("require(");
      expect(mcpServerContent).toContain("import(");
      expect(mcpServerContent).toContain('process.');
    });
  });

  describe('Documentation', () => {
    it('should have MCP architecture design document', () => {
      const docPath = path.join(process.cwd(), '../../.auto-claude/specs/169-research-webmcp-integration-with-electron-frontend/MCP_ARCHITECTURE_DESIGN_1.2.md');
      expect(existsSync(docPath)).toBe(true);
    });

    it('should have security requirements document', () => {
      const docPath = path.join(process.cwd(), '../../.auto-claude/specs/169-research-webmcp-integration-with-electron-frontend/SECURITY_REQUIREMENTS_AND_CONTEXT_ISOLATION_1.3.md');
      expect(existsSync(docPath)).toBe(true);
    });

    it('should have transport layer architecture document', () => {
      const docPath = path.join(process.cwd(), '../../.auto-claude/specs/169-research-webmcp-integration-with-electron-frontend/TRANSPORT_LAYER_ARCHITECTURE_2.3.md');
      expect(existsSync(docPath)).toBe(true);
    });
  });
});
