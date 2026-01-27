/**
 * API Client
 *
 * REST API client for communicating with the Auto Claude web backend.
 * Provides methods for task/spec management and agent execution.
 */

import type {
  AgentCancelResponse,
  AgentRunRequest,
  AgentRunResponse,
  AgentStatusResponse,
  ApiConfig,
  ApiError,
  SpecDetail,
  SpecListResponse,
  TaskDetail,
  TaskListResponse,
} from "./types";

/**
 * Default API configuration from environment variables
 */
const DEFAULT_CONFIG: ApiConfig = {
  baseUrl: import.meta.env.VITE_API_URL || "http://localhost:8000",
  wsUrl: import.meta.env.VITE_WS_URL || "ws://localhost:8000",
  timeout: 30000, // 30 seconds
  debug: import.meta.env.VITE_DEBUG === "true",
};

/**
 * API Client for Auto Claude web backend
 */
export class ApiClient {
  private config: ApiConfig;

  constructor(config: Partial<ApiConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.log("ApiClient initialized", this.config);
  }

  /**
   * Internal logging helper
   */
  private log(message: string, ...args: unknown[]): void {
    if (this.config.debug) {
      console.log(`[ApiClient] ${message}`, ...args);
    }
  }

  /**
   * Generic fetch wrapper with error handling
   */
  private async fetch<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.config.baseUrl}${endpoint}`;
    this.log(`Fetching ${options.method || "GET"} ${url}`, options);

    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      this.config.timeout
    );

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      // Handle HTTP errors
      if (!response.ok) {
        const error: ApiError = await response
          .json()
          .catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      // Handle 204 No Content
      if (response.status === 204) {
        return {} as T;
      }

      const data = await response.json();
      this.log(`Response from ${url}:`, data);
      return data;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error) {
        if (error.name === "AbortError") {
          throw new Error(`Request timeout after ${this.config.timeout}ms`);
        }
        throw error;
      }

      throw new Error("Unknown error occurred");
    }
  }

  // ============================================
  // TASK ENDPOINTS
  // ============================================

  /**
   * List all tasks/specs
   */
  async listTasks(): Promise<TaskListResponse> {
    return this.fetch<TaskListResponse>("/api/tasks");
  }

  /**
   * Get detailed information for a specific task
   */
  async getTask(taskId: string): Promise<TaskDetail> {
    return this.fetch<TaskDetail>(`/api/tasks/${taskId}`);
  }

  /**
   * Check task API health
   */
  async checkTasksHealth(): Promise<{ status: string }> {
    return this.fetch<{ status: string }>("/api/tasks/health");
  }

  // ============================================
  // SPEC ENDPOINTS
  // ============================================

  /**
   * List all specs (alias for listTasks)
   */
  async listSpecs(): Promise<SpecListResponse> {
    return this.fetch<SpecListResponse>("/api/specs");
  }

  /**
   * Get detailed information for a specific spec
   */
  async getSpec(specId: string): Promise<SpecDetail> {
    return this.fetch<SpecDetail>(`/api/specs/${specId}`);
  }

  /**
   * Check spec API health
   */
  async checkSpecsHealth(): Promise<{ status: string }> {
    return this.fetch<{ status: string }>("/api/specs/health");
  }

  // ============================================
  // AGENT ENDPOINTS
  // ============================================

  /**
   * Start an agent execution task
   */
  async runAgent(request: AgentRunRequest): Promise<AgentRunResponse> {
    return this.fetch<AgentRunResponse>("/api/agents/run", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  /**
   * Get the status of a running agent task
   */
  async getAgentStatus(taskId: string): Promise<AgentStatusResponse> {
    return this.fetch<AgentStatusResponse>(`/api/agents/status/${taskId}`);
  }

  /**
   * Cancel a running agent task
   */
  async cancelAgent(taskId: string): Promise<AgentCancelResponse> {
    return this.fetch<AgentCancelResponse>(`/api/agents/cancel/${taskId}`, {
      method: "POST",
    });
  }

  /**
   * Check agent API health
   */
  async checkAgentsHealth(): Promise<{ status: string }> {
    return this.fetch<{ status: string }>("/api/agents/health");
  }

  // ============================================
  // AUTH ENDPOINTS
  // ============================================

  /**
   * Verify authentication token
   */
  async verifyAuth(token: string): Promise<{ valid: boolean }> {
    return this.fetch<{ valid: boolean }>("/api/auth/verify", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  /**
   * Get auth system status
   */
  async getAuthStatus(): Promise<{ status: string }> {
    return this.fetch<{ status: string }>("/api/auth/status");
  }

  // ============================================
  // UTILITY METHODS
  // ============================================

  /**
   * Update API configuration
   */
  updateConfig(config: Partial<ApiConfig>): void {
    this.config = { ...this.config, ...config };
    this.log("Config updated", this.config);
  }

  /**
   * Get current configuration
   */
  getConfig(): Readonly<ApiConfig> {
    return { ...this.config };
  }

  /**
   * Health check for all API endpoints
   */
  async healthCheck(): Promise<{
    tasks: boolean;
    specs: boolean;
    agents: boolean;
    auth: boolean;
  }> {
    const results = await Promise.allSettled([
      this.checkTasksHealth(),
      this.checkSpecsHealth(),
      this.checkAgentsHealth(),
      this.getAuthStatus(),
    ]);

    return {
      tasks: results[0].status === "fulfilled",
      specs: results[1].status === "fulfilled",
      agents: results[2].status === "fulfilled",
      auth: results[3].status === "fulfilled",
    };
  }
}

/**
 * Default API client instance
 * Use this for most cases unless you need custom configuration
 */
export const apiClient = new ApiClient();

/**
 * Create a new API client with custom configuration
 */
export function createApiClient(config: Partial<ApiConfig> = {}): ApiClient {
  return new ApiClient(config);
}
