/**
 * API Client Unit Tests
 *
 * Comprehensive tests for the ApiClient class covering:
 * - Constructor and configuration
 * - All endpoint methods (tasks, specs, agents, auth)
 * - Error handling (timeouts, HTTP errors, network errors)
 * - Edge cases (204 No Content, custom headers)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ApiClient, createApiClient } from './client';
import type {
  TaskListResponse,
  TaskDetail,
  SpecListResponse,
  SpecDetail,
  AgentRunRequest,
  AgentRunResponse,
  AgentStatusResponse,
  AgentCancelResponse,
} from './types';

// Mock fetch globally
const mockFetch = vi.fn();
const originalFetch = globalThis.fetch;

describe('ApiClient', () => {
  let client: ApiClient;

  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Install mock fetch
    globalThis.fetch = mockFetch;

    // Create client with test config
    client = new ApiClient({
      baseUrl: 'http://test-api.local',
      wsUrl: 'ws://test-api.local',
      timeout: 5000,
      debug: false,
    });
  });

  afterEach(() => {
    // Restore original fetch
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  // ============================================
  // CONSTRUCTOR & CONFIGURATION TESTS
  // ============================================

  describe('Constructor', () => {
    it('should initialize with default config', () => {
      const defaultClient = new ApiClient();
      const config = defaultClient.getConfig();

      expect(config.baseUrl).toBeDefined();
      expect(config.wsUrl).toBeDefined();
      expect(config.timeout).toBe(30000);
    });

    it('should merge custom config with defaults', () => {
      const customClient = new ApiClient({
        baseUrl: 'http://custom.local',
        timeout: 10000,
      });
      const config = customClient.getConfig();

      expect(config.baseUrl).toBe('http://custom.local');
      expect(config.timeout).toBe(10000);
      expect(config.wsUrl).toBeDefined(); // Should still have default
    });

    it('should not log when debug is false', () => {
      const consoleSpy = vi.spyOn(console, 'log');
      const silentClient = new ApiClient({ debug: false });
      expect(silentClient).toBeDefined();

      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should log when debug is true', () => {
      const consoleSpy = vi.spyOn(console, 'log');
      const verboseClient = new ApiClient({ debug: true });
      expect(verboseClient).toBeDefined();

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('[ApiClient] ApiClient initialized'),
        expect.any(Object)
      );
    });
  });

  describe('updateConfig', () => {
    it('should update configuration', () => {
      client.updateConfig({ baseUrl: 'http://new-api.local' });
      const config = client.getConfig();

      expect(config.baseUrl).toBe('http://new-api.local');
    });

    it('should merge partial config updates', () => {
      const originalConfig = client.getConfig();
      client.updateConfig({ timeout: 15000 });
      const newConfig = client.getConfig();

      expect(newConfig.timeout).toBe(15000);
      expect(newConfig.baseUrl).toBe(originalConfig.baseUrl);
      expect(newConfig.wsUrl).toBe(originalConfig.wsUrl);
    });
  });

  describe('getConfig', () => {
    it('should return a copy of config', () => {
      const config1 = client.getConfig();
      const config2 = client.getConfig();

      expect(config1).toEqual(config2);
      expect(config1).not.toBe(config2); // Different objects
    });
  });

  // ============================================
  // TASK ENDPOINT TESTS
  // ============================================

  describe('listTasks', () => {
    it('should fetch task list successfully', async () => {
      const mockResponse: TaskListResponse = {
        tasks: [
          {
            number: '001',
            name: 'test-task',
            folder: 'test',
            status: 'pending',
            progress: '0/10',
            has_build: false,
          },
        ],
        total: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.listTasks();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/tasks',
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getTask', () => {
    it('should fetch task detail successfully', async () => {
      const mockResponse: TaskDetail = {
        number: '001',
        name: 'test-task',
        folder: 'test',
        status: 'pending',
        progress: {
          completed: 0,
          in_progress: 0,
          pending: 10,
          failed: 0,
          total: 10,
          percentage: 0,
        },
        has_build: false,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.getTask('001');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/tasks/001',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('checkTasksHealth', () => {
    it('should check tasks health successfully', async () => {
      const mockResponse = { status: 'healthy' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.checkTasksHealth();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/tasks/health',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  // ============================================
  // SPEC ENDPOINT TESTS
  // ============================================

  describe('listSpecs', () => {
    it('should fetch spec list successfully', async () => {
      const mockResponse: SpecListResponse = {
        specs: [
          {
            number: '001',
            name: 'test-spec',
            folder: 'test',
            status: 'pending',
            progress: '0/10',
            has_build: false,
          },
        ],
        total: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.listSpecs();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/specs',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getSpec', () => {
    it('should fetch spec detail successfully', async () => {
      const mockResponse: SpecDetail = {
        number: '001',
        name: 'test-spec',
        folder: 'test',
        status: 'pending',
        progress: {
          completed: 5,
          in_progress: 1,
          pending: 4,
          failed: 0,
          total: 10,
          percentage: 50,
        },
        has_build: true,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.getSpec('001');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/specs/001',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('checkSpecsHealth', () => {
    it('should check specs health successfully', async () => {
      const mockResponse = { status: 'healthy' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.checkSpecsHealth();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/specs/health',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  // ============================================
  // AGENT ENDPOINT TESTS
  // ============================================

  describe('runAgent', () => {
    it('should start agent execution successfully', async () => {
      const request: AgentRunRequest = {
        spec_id: '001',
        agent_type: 'coder',
        model: 'claude-sonnet-4-5-20250929',
        verbose: true,
      };

      const mockResponse: AgentRunResponse = {
        task_id: 'task-123',
        spec_id: '001',
        agent_type: 'coder',
        status: 'started',
        message: 'Agent started successfully',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.runAgent(request);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/agents/run',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(request),
        })
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('getAgentStatus', () => {
    it('should get agent status successfully', async () => {
      const mockResponse: AgentStatusResponse = {
        task_id: 'task-123',
        status: 'running',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.getAgentStatus('task-123');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/agents/status/task-123',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });

    it('should handle completed agent status', async () => {
      const mockResponse: AgentStatusResponse = {
        task_id: 'task-123',
        status: 'completed',
        result: { success: true },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.getAgentStatus('task-123');

      expect(result.status).toBe('completed');
      expect(result.result).toEqual({ success: true });
    });

    it('should handle failed agent status', async () => {
      const mockResponse: AgentStatusResponse = {
        task_id: 'task-123',
        status: 'failed',
        error: 'Something went wrong',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.getAgentStatus('task-123');

      expect(result.status).toBe('failed');
      expect(result.error).toBe('Something went wrong');
    });
  });

  describe('cancelAgent', () => {
    it('should cancel agent successfully', async () => {
      const mockResponse: AgentCancelResponse = {
        task_id: 'task-123',
        cancelled: true,
        message: 'Agent cancelled successfully',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.cancelAgent('task-123');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/agents/cancel/task-123',
        expect.objectContaining({
          method: 'POST',
        })
      );
      expect(result).toEqual(mockResponse);
    });
  });

  describe('checkAgentsHealth', () => {
    it('should check agents health successfully', async () => {
      const mockResponse = { status: 'healthy' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.checkAgentsHealth();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/agents/health',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  // ============================================
  // AUTH ENDPOINT TESTS
  // ============================================

  describe('verifyAuth', () => {
    it('should verify auth token successfully', async () => {
      const mockResponse = { valid: true };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.verifyAuth('test-token');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/auth/verify',
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should return invalid for expired token', async () => {
      const mockResponse = { valid: false };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.verifyAuth('expired-token');

      expect(result.valid).toBe(false);
    });
  });

  describe('getAuthStatus', () => {
    it('should get auth status successfully', async () => {
      const mockResponse = { status: 'authenticated' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockResponse,
      });

      const result = await client.getAuthStatus();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/auth/status',
        expect.any(Object)
      );
      expect(result).toEqual(mockResponse);
    });
  });

  // ============================================
  // HEALTH CHECK TESTS
  // ============================================

  describe('healthCheck', () => {
    it('should check all endpoints and return status', async () => {
      // Mock all health endpoints as successful
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ status: 'authenticated' }),
        });

      const result = await client.healthCheck();

      expect(result).toEqual({
        tasks: true,
        specs: true,
        agents: true,
        auth: true,
      });
    });

    it('should handle mixed health check results', async () => {
      // Mock tasks as healthy, specs as failing, agents as healthy, auth as failing
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        })
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ status: 'healthy' }),
        })
        .mockRejectedValueOnce(new Error('Auth failed'));

      const result = await client.healthCheck();

      expect(result).toEqual({
        tasks: true,
        specs: false,
        agents: true,
        auth: false,
      });
    });

    it('should handle all endpoints failing', async () => {
      mockFetch
        .mockRejectedValueOnce(new Error('Error 1'))
        .mockRejectedValueOnce(new Error('Error 2'))
        .mockRejectedValueOnce(new Error('Error 3'))
        .mockRejectedValueOnce(new Error('Error 4'));

      const result = await client.healthCheck();

      expect(result).toEqual({
        tasks: false,
        specs: false,
        agents: false,
        auth: false,
      });
    });
  });

  // ============================================
  // ERROR HANDLING TESTS
  // ============================================

  describe('Error Handling', () => {
    it('should handle HTTP 404 error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ detail: 'Task not found' }),
      });

      await expect(client.getTask('999')).rejects.toThrow('Task not found');
    });

    it('should handle HTTP 500 error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ detail: 'Server error' }),
      });

      await expect(client.listTasks()).rejects.toThrow('Server error');
    });

    it('should handle error response without detail', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        json: async () => ({}),
      });

      await expect(client.listTasks()).rejects.toThrow('HTTP 400: Bad Request');
    });

    it('should handle JSON parse error in error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      await expect(client.listTasks()).rejects.toThrow('Service Unavailable');
    });

    it('should handle network error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network failure'));

      await expect(client.listTasks()).rejects.toThrow('Network failure');
    });

    it('should handle abort error (timeout)', async () => {
      mockFetch.mockRejectedValueOnce(
        Object.assign(new Error('The operation was aborted'), { name: 'AbortError' })
      );

      await expect(client.listTasks()).rejects.toThrow('Request timeout after 5000ms');
    });

    it('should handle unknown error type', async () => {
      mockFetch.mockRejectedValueOnce('Unknown error string');

      await expect(client.listTasks()).rejects.toThrow('Unknown error occurred');
    });

    it('should clear timeout on successful request', async () => {
      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ tasks: [], total: 0 }),
      });

      await client.listTasks();

      expect(clearTimeoutSpy).toHaveBeenCalled();
    });

    it('should clear timeout on error', async () => {
      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(client.listTasks()).rejects.toThrow();
      expect(clearTimeoutSpy).toHaveBeenCalled();
    });
  });

  // ============================================
  // EDGE CASE TESTS
  // ============================================

  describe('Edge Cases', () => {
    it('should handle 204 No Content response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const result = await client.cancelAgent('task-123');

      expect(result).toEqual({});
    });

    it('should include custom headers in requests', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ valid: true }),
      });

      await client.verifyAuth('token');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            Authorization: 'Bearer token',
          }),
        })
      );
    });

    it('should use correct HTTP methods', async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({}),
      });

      // GET request (default)
      await client.listTasks();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.not.objectContaining({ method: expect.any(String) })
      );

      // POST request
      await client.runAgent({
        spec_id: '001',
        agent_type: 'coder',
      });
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ method: 'POST' })
      );
    });

    it('should properly encode URL paths', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'running' }),
      });

      await client.getAgentStatus('task-with-special-chars');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://test-api.local/api/agents/status/task-with-special-chars',
        expect.any(Object)
      );
    });
  });

  // ============================================
  // FACTORY FUNCTION TESTS
  // ============================================

  describe('createApiClient', () => {
    it('should create a new client instance', () => {
      const newClient = createApiClient({
        baseUrl: 'http://factory-test.local',
      });

      expect(newClient).toBeInstanceOf(ApiClient);
      expect(newClient.getConfig().baseUrl).toBe('http://factory-test.local');
    });

    it('should create client with default config', () => {
      const newClient = createApiClient();

      expect(newClient).toBeInstanceOf(ApiClient);
      expect(newClient.getConfig()).toBeDefined();
    });
  });
});
