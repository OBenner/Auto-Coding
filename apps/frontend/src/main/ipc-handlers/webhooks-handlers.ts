import { ipcMain } from 'electron';
import { promises as fsPromises } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// ESM-compatible __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

import { IPC_CHANNELS } from '../../shared/constants';
import type {
  IPCResult,
  WebhookConfig,
  WebhookLog,
  WebhookIntegrationStatus,
  WebhookTestResult
} from '../../shared/types';
import { projectStore } from '../project-store';
import { AgentManager } from '../agent';

/**
 * Get the webhooks configuration file path for a project
 */
const getWebhooksConfigPath = (projectPath: string): string => {
  return path.join(projectPath, '.auto-claude', 'webhooks.json');
};

/**
 * Get the webhooks logs file path for a project
 */
const getWebhooksLogsPath = (projectPath: string): string => {
  return path.join(projectPath, '.auto-claude', 'webhook-logs.json');
};

/**
 * Ensure the webhooks configuration directory exists
 */
const ensureWebhooksDir = async (projectPath: string): Promise<void> => {
  const configPath = getWebhooksConfigPath(projectPath);
  const dir = path.dirname(configPath);

  try {
    await fsPromises.access(dir);
  } catch {
    await fsPromises.mkdir(dir, { recursive: true });
  }
};

/**
 * Read webhooks configuration from file
 */
const readWebhooksConfig = async (projectPath: string): Promise<WebhookConfig[]> => {
  const configPath = getWebhooksConfigPath(projectPath);

  try {
    const content = await fsPromises.readFile(configPath, 'utf-8');
    const data = JSON.parse(content);
    return data.webhooks || [];
  } catch {
    // File doesn't exist or is invalid - return empty array
    return [];
  }
};

/**
 * Write webhooks configuration to file
 */
const writeWebhooksConfig = async (
  projectPath: string,
  webhooks: WebhookConfig[]
): Promise<void> => {
  await ensureWebhooksDir(projectPath);
  const configPath = getWebhooksConfigPath(projectPath);
  const content = JSON.stringify({ webhooks, updatedAt: new Date().toISOString() }, null, 2);
  await fsPromises.writeFile(configPath, content, 'utf-8');
};

/**
 * Read webhooks logs from file
 */
const readWebhooksLogs = async (projectPath: string): Promise<WebhookLog[]> => {
  const logsPath = getWebhooksLogsPath(projectPath);

  try {
    const content = await fsPromises.readFile(logsPath, 'utf-8');
    const data = JSON.parse(content);
    return data.logs || [];
  } catch {
    // File doesn't exist or is invalid - return empty array
    return [];
  }
};

/**
 * Generate a unique ID for a webhook config
 */
const generateWebhookId = (): string => {
  return `webhook-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Webhook IPC Handlers
 *
 * This module provides IPC handlers for webhook configuration management:
 * - getWebhookConfig: Retrieve webhook configurations
 * - saveWebhookConfig: Save or update webhook configurations
 * - testWebhookConnection: Test webhook connectivity
 *
 * Register these handlers with the main process to enable webhook configuration
 * from the renderer process.
 */

/**
 * Register all webhook-related IPC handlers
 */
export function registerWebhookHandlers(
  agentManager: AgentManager,
  _getMainWindow: () => BrowserWindow | null
): void {
  // ============================================
  // Webhook Configuration Operations
  // ============================================

  /**
   * Get all webhook configurations for a project
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_GET_CONFIGS,
    async (_, projectId: string): Promise<IPCResult<WebhookConfig[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const webhooks = await readWebhooksConfig(project.path);
        return { success: true, data: webhooks };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get webhook configs'
        };
      }
    }
  );

  /**
   * Get a specific webhook configuration by ID
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_GET_CONFIG,
    async (_, projectId: string, webhookId: string): Promise<IPCResult<WebhookConfig>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const webhooks = await readWebhooksConfig(project.path);
        const webhook = webhooks.find((w) => w.id === webhookId);

        if (!webhook) {
          return { success: false, error: 'Webhook not found' };
        }

        return { success: true, data: webhook };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get webhook config'
        };
      }
    }
  );

  /**
   * Save or update a webhook configuration
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_SAVE_CONFIG,
    async (_, projectId: string, config: Partial<WebhookConfig>): Promise<IPCResult<WebhookConfig>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const webhooks = await readWebhooksConfig(project.path);
        const now = new Date().toISOString();

        if (config.id) {
          // Update existing webhook
          const index = webhooks.findIndex((w) => w.id === config.id);
          if (index === -1) {
            return { success: false, error: 'Webhook not found' };
          }

          // Merge with existing config, preserving certain fields
          webhooks[index] = {
            ...webhooks[index],
            ...config,
            updated_at: now
          } as WebhookConfig;

          await writeWebhooksConfig(project.path, webhooks);
          return { success: true, data: webhooks[index] };
        } else {
          // Create new webhook
          const newWebhook: WebhookConfig = {
            id: generateWebhookId(),
            name: config.name || 'Unnamed Webhook',
            type: config.type || 'outgoing',
            integration: config.integration || 'slack',
            url: config.url,
            path: config.path,
            auth: config.auth || {
              auth_type: 'none',
              signature_algorithm: 'hmac_sha256'
            },
            events: config.events || [],
            enabled: config.enabled ?? true,
            retry_config: config.retry_config || {
              max_retries: 3,
              retry_delay_seconds: 5,
              backoff_multiplier: 2,
              retry_on_status_codes: [429, 500, 502, 503, 504]
            },
            description: config.description,
            created_at: now,
            updated_at: now,
            custom_event_filter: config.custom_event_filter,
            payload_template: config.payload_template
          };

          webhooks.push(newWebhook);
          await writeWebhooksConfig(project.path, webhooks);
          return { success: true, data: newWebhook };
        }
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to save webhook config'
        };
      }
    }
  );

  /**
   * Delete a webhook configuration
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_DELETE_CONFIG,
    async (_, projectId: string, webhookId: string): Promise<IPCResult<void>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const webhooks = await readWebhooksConfig(project.path);
        const filtered = webhooks.filter((w) => w.id !== webhookId);

        if (filtered.length === webhooks.length) {
          return { success: false, error: 'Webhook not found' };
        }

        await writeWebhooksConfig(project.path, filtered);
        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to delete webhook config'
        };
      }
    }
  );

  /**
   * Enable a webhook configuration
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_ENABLE_CONFIG,
    async (_, projectId: string, webhookId: string): Promise<IPCResult<WebhookConfig>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const webhooks = await readWebhooksConfig(project.path);
        const webhook = webhooks.find((w) => w.id === webhookId);

        if (!webhook) {
          return { success: false, error: 'Webhook not found' };
        }

        webhook.enabled = true;
        webhook.updated_at = new Date().toISOString();

        await writeWebhooksConfig(project.path, webhooks);
        return { success: true, data: webhook };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to enable webhook'
        };
      }
    }
  );

  /**
   * Disable a webhook configuration
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_DISABLE_CONFIG,
    async (_, projectId: string, webhookId: string): Promise<IPCResult<WebhookConfig>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const webhooks = await readWebhooksConfig(project.path);
        const webhook = webhooks.find((w) => w.id === webhookId);

        if (!webhook) {
          return { success: false, error: 'Webhook not found' };
        }

        webhook.enabled = false;
        webhook.updated_at = new Date().toISOString();

        await writeWebhooksConfig(project.path, webhooks);
        return { success: true, data: webhook };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to disable webhook'
        };
      }
    }
  );

  // ============================================
  // Webhook Testing Operations
  // ============================================

  /**
   * Test a webhook connection by sending a test event
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_TEST_CONNECTION,
    async (
      _,
      projectId: string,
      config: WebhookConfig
    ): Promise<IPCResult<WebhookTestResult>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return {
            success: false,
            error: 'Project not found',
            data: {
              success: false,
              integration: config.integration,
              message: 'Project not found'
            }
          };
        }

        // Import axios dynamically to avoid startup overhead
        const axios = (await import('axios')).default;

        // Get webhook server port from environment (default to 8080)
        const webhookPort = process.env.WEBHOOK_PORT || '8080';
        const webhookUrl = `http://127.0.0.1:${webhookPort}/api/webhooks/test`;

        // Call backend webhook test endpoint
        const response = await axios.post(
          webhookUrl,
          {
            webhook_id: config.id,
            project_dir: project.path
          },
          {
            timeout: 10000, // 10 second timeout
            headers: {
              'Content-Type': 'application/json'
            }
          }
        );

        // Return result from backend
        return {
          success: true,
          data: {
            success: response.data.success,
            integration: config.integration,
            message: response.data.message || 'Test completed',
            timestamp: new Date().toISOString()
          }
        };
      } catch (error: any) {
        // Handle errors (axios errors, connection refused, etc.)
        const errorMsg = error.response?.data?.detail ||
                         error.message ||
                         'Failed to test webhook';

        return {
          success: true, // IPC succeeded
          data: {
            success: false,
            integration: config.integration,
            message: errorMsg,
            error: errorMsg,
            timestamp: new Date().toISOString()
          }
        };
      }
    }
  );

  // ============================================
  // Webhook Logs Operations
  // ============================================

  /**
   * Get webhook logs for a project
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_GET_LOGS,
    async (
      _,
      projectId: string,
      limit?: number
    ): Promise<IPCResult<WebhookLog[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        let logs = await readWebhooksLogs(project.path);

        // Sort by created_at descending (newest first)
        logs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

        // Apply limit if specified
        if (limit && limit > 0) {
          logs = logs.slice(0, limit);
        }

        return { success: true, data: logs };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get webhook logs'
        };
      }
    }
  );

  // ============================================
  // Webhook Integration Status
  // ============================================

  /**
   * Get the connection status of all webhook integrations
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_GET_INTEGRATION_STATUS,
    async (_, projectId: string): Promise<IPCResult<WebhookIntegrationStatus[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const webhooks = await readWebhooksConfig(project.path);

        // Group by integration type
        const integrationMap = new Map<string, WebhookIntegrationStatus>();

        for (const webhook of webhooks) {
          const existing = integrationMap.get(webhook.integration);

          if (existing) {
            // Update status if this webhook is enabled
            if (webhook.enabled) {
              existing.enabled = true;
            }
          } else {
            integrationMap.set(webhook.integration, {
              integration: webhook.integration,
              connected: webhook.enabled && !!webhook.url,
              enabled: webhook.enabled,
              last_tested: undefined,
              error: undefined
            });
          }
        }

        // Convert to array and add integration types that have no configs
        const allIntegrations: Array<'slack' | 'discord' | 'teams' | 'jira' | 'github' | 'gitlab' | 'generic'> = [
          'slack',
          'discord',
          'teams',
          'jira',
          'github',
          'gitlab',
          'generic'
        ];

        const result: WebhookIntegrationStatus[] = allIntegrations.map((integration) => {
          return (
            integrationMap.get(integration) || {
              integration,
              connected: false,
              enabled: false
            }
          );
        });

        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get integration status'
        };
      }
    }
  );
}
