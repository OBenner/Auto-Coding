/**
 * Webhook Configuration IPC Handlers
 *
 * IPC handlers for managing webhook configurations, testing webhooks,
 * and retrieving webhook delivery history and statistics.
 */

import { ipcMain } from 'electron';
import { existsSync, readFileSync, writeFileSync, mkdirSync, unlinkSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { getConfiguredPythonPath } from '../python-env-manager';

// ESM-compatible __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import type {
  WebhookConfig,
  WebhookDelivery,
  WebhookDeliveryStats,
  WebhookTestResult,
  WebhookEventTypeMeta,
  WebhookTemplateMeta,
} from '../../shared/types/webhook';

/**
 * Get the webhook configuration directory for a spec
 */
function getWebhookConfigDir(specId: string): string {
  // Webhooks are stored per-spec in the .auto-claude/specs/{specId}/.webhooks/configs directory
  const specDir = path.resolve(process.cwd(), '.auto-claude', 'specs', specId);
  return path.join(specDir, '.webhooks', 'configs');
}

/**
 * Get the webhook delivery directory for a spec
 */
function getWebhookDeliveryDir(specId: string): string {
  const specDir = path.resolve(process.cwd(), '.auto-claude', 'specs', specId);
  return path.join(specDir, '.webhooks', 'deliveries');
}

/**
 * Generate a unique webhook ID
 */
function generateWebhookId(): string {
  return `wh_${Date.now()}_${randomUUID().replace(/-/g, '').substring(0, 8)}`;
}

/**
 * Webhook event type metadata
 */
const WEBHOOK_EVENT_TYPES: WebhookEventTypeMeta[] = [
  {
    value: 'spec_created',
    label: 'Spec Created',
    description: 'When a new spec is created',
    category: 'spec',
  },
  {
    value: 'spec_updated',
    label: 'Spec Updated',
    description: 'When a spec is updated',
    category: 'spec',
  },
  {
    value: 'build_started',
    label: 'Build Started',
    description: 'When a build starts',
    category: 'build',
  },
  {
    value: 'build_completed',
    label: 'Build Completed',
    description: 'When a build completes successfully',
    category: 'build',
  },
  {
    value: 'build_failed',
    label: 'Build Failed',
    description: 'When a build fails',
    category: 'build',
  },
  {
    value: 'qa_passed',
    label: 'QA Passed',
    description: 'When QA validation passes',
    category: 'qa',
  },
  {
    value: 'qa_failed',
    label: 'QA Failed',
    description: 'When QA validation fails',
    category: 'qa',
  },
  {
    value: 'merged',
    label: 'Merged',
    description: 'When a build is merged to main',
    category: 'git',
  },
  {
    value: 'pr_created',
    label: 'PR Created',
    description: 'When a pull request is created',
    category: 'git',
  },
  {
    value: '*',
    label: 'All Events',
    description: 'Subscribe to all webhook events',
    category: 'spec',
  },
];

/**
 * Webhook template metadata
 */
const WEBHOOK_TEMPLATES: WebhookTemplateMeta[] = [
  {
    value: 'generic',
    label: 'Generic JSON',
    description: 'Standard JSON payload format',
  },
  {
    value: 'slack',
    label: 'Slack',
    description: 'Slack incoming webhook format',
    icon: 'slack',
  },
  {
    value: 'discord',
    label: 'Discord',
    description: 'Discord webhook format',
    icon: 'discord',
  },
  {
    value: 'teams',
    label: 'Microsoft Teams',
    description: 'Teams adaptive card format',
    icon: 'microsoft',
  },
  {
    value: 'jira',
    label: 'JIRA',
    description: 'JIRA comment format',
    icon: 'jira',
  },
];

/**
 * Register all webhook-related IPC handlers
 */
export function registerWebhookHandlers(): void {
  // ============================================
  // Webhook Configuration Operations
  // ============================================

  /**
   * List all webhooks for a spec
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_LIST,
    async (_, specId: string): Promise<IPCResult<WebhookConfig[]>> => {
      try {
        const configDir = getWebhookConfigDir(specId);

        if (!existsSync(configDir)) {
          return { success: true, data: [] };
        }

        const webhooks: WebhookConfig[] = [];

        // Read all JSON files in the config directory
        const configFiles = readdirSync(configDir).filter((f: string) => f.endsWith('.json'));

        for (const filename of configFiles) {
          try {
            const filePath = path.join(configDir, filename);
            const content = readFileSync(filePath, 'utf-8');
            const data = JSON.parse(content);
            webhooks.push(data as WebhookConfig);
          } catch {
            // Intentionally ignored: skip malformed config files
            continue;
          }
        }

        return { success: true, data: webhooks };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }
  );

  /**
   * Get a single webhook configuration
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_GET,
    async (_, specId: string, webhookId: string): Promise<IPCResult<WebhookConfig>> => {
      try {
        const configDir = getWebhookConfigDir(specId);
        const configPath = path.join(configDir, `${webhookId}.json`);

        if (!existsSync(configPath)) {
          return {
            success: false,
            error: 'Webhook not found',
          };
        }

        const content = readFileSync(configPath, 'utf-8');
        const webhook = JSON.parse(content) as WebhookConfig;

        return { success: true, data: webhook };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }
  );

  /**
   * Create a new webhook configuration
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_CREATE,
    async (
      _,
      specId: string,
      webhookData: Omit<WebhookConfig, 'webhook_id' | 'created_at' | 'updated_at'>
    ): Promise<IPCResult<WebhookConfig>> => {
      try {
        const configDir = getWebhookConfigDir(specId);
        mkdirSync(configDir, { recursive: true });

        // Validate webhook data
        if (!webhookData.url || !webhookData.name) {
          return {
            success: false,
            error: 'URL and name are required',
          };
        }

        // Validate URL format
        try {
          const url = new URL(webhookData.url);
          if (!['http:', 'https:'].includes(url.protocol)) {
            return {
              success: false,
              error: 'URL must use HTTP or HTTPS protocol',
            };
          }
        } catch {
          return {
            success: false,
            error: 'Invalid URL format',
          };
        }

        // Validate events
        if (!webhookData.events || webhookData.events.length === 0) {
          return {
            success: false,
            error: 'At least one event must be selected',
          };
        }

        // Generate webhook ID and timestamps
        const webhookId = generateWebhookId();
        const now = new Date().toISOString();

        const webhook: WebhookConfig = {
          webhook_id: webhookId,
          ...webhookData,
          created_at: now,
          updated_at: now,
        };

        // Save webhook configuration
        const configPath = path.join(configDir, `${webhookId}.json`);
        writeFileSync(configPath, JSON.stringify(webhook, null, 2), 'utf-8');

        return { success: true, data: webhook };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }
  );

  /**
   * Update an existing webhook configuration
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_UPDATE,
    async (
      _,
      specId: string,
      webhookId: string,
      updates: Partial<WebhookConfig>
    ): Promise<IPCResult<WebhookConfig>> => {
      try {
        const configDir = getWebhookConfigDir(specId);
        const configPath = path.join(configDir, `${webhookId}.json`);

        // Read file directly instead of checking existence first (avoids TOCTOU race)
        let content: string;
        try {
          content = readFileSync(configPath, 'utf-8');
        } catch {
          return {
            success: false,
            error: 'Webhook not found',
          };
        }

        // Load existing webhook
        const existing = JSON.parse(content) as WebhookConfig;

        // Apply updates
        const updated: WebhookConfig = {
          ...existing,
          ...updates,
          webhook_id: webhookId, // Preserve webhook_id
          created_at: existing.created_at, // Preserve created_at
          updated_at: new Date().toISOString(), // Update updated_at
        };

        // Validate URL if changed
        if (updates.url) {
          try {
            const url = new URL(updates.url);
            if (!['http:', 'https:'].includes(url.protocol)) {
              return {
                success: false,
                error: 'URL must use HTTP or HTTPS protocol',
              };
            }
          } catch {
            return {
              success: false,
              error: 'Invalid URL format',
            };
          }
        }

        // Validate events if changed
        if (updates.events?.length === 0) {
          return {
            success: false,
            error: 'At least one event must be selected',
          };
        }

        // Save updated webhook
        writeFileSync(configPath, JSON.stringify(updated, null, 2), 'utf-8');

        return { success: true, data: updated };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }
  );

  /**
   * Delete a webhook configuration
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_DELETE,
    async (_, specId: string, webhookId: string): Promise<IPCResult<{ success: boolean }>> => {
      try {
        const configDir = getWebhookConfigDir(specId);
        const configPath = path.join(configDir, `${webhookId}.json`);

        if (!existsSync(configPath)) {
          return {
            success: false,
            error: 'Webhook not found',
          };
        }

        // Delete webhook configuration
        unlinkSync(configPath);

        return { success: true, data: { success: true } };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }
  );

  // ============================================
  // Webhook Testing
  // ============================================

  /**
   * Test a webhook by sending a test event
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_TEST,
    async (_, specId: string, webhookId: string): Promise<IPCResult<WebhookTestResult>> => {
      try {
        const configDir = getWebhookConfigDir(specId);
        const configPath = path.join(configDir, `${webhookId}.json`);

        if (!existsSync(configPath)) {
          return {
            success: false,
            error: 'Webhook not found',
          };
        }

        // Validate webhook configuration is parseable before testing
        const content = readFileSync(configPath, 'utf-8');
        JSON.parse(content);

        // Send test webhook using Python backend
        const { spawn } = require('node:child_process');
        const specDir = path.resolve(process.cwd(), '.auto-claude', 'specs', specId);
        const pythonPath = getConfiguredPythonPath();

        return new Promise((resolve) => {
          // Pass arguments via sys.argv to avoid string interpolation injection
          const python = spawn(
            pythonPath,
            ['-c', `
import json, sys
from pathlib import Path
from integrations.webhooks.dispatcher import WebhookDispatcher

spec_dir = Path(sys.argv[1])
webhook_id = sys.argv[2]
dispatcher = WebhookDispatcher(spec_dir)
result = dispatcher.test_webhook(webhook_id)
print(json.dumps(result))
`, specDir, webhookId],
            { cwd: path.resolve(process.cwd(), 'apps', 'backend') }
          );

          let stdout = '';
          let stderr = '';

          python.stdout.on('data', (data: Buffer) => {
            stdout += data.toString();
          });

          python.stderr.on('data', (data: Buffer) => {
            stderr += data.toString();
          });

          python.on('close', (code: number) => {
            if (code !== 0) {
              resolve({
                success: false,
                error: `Python process failed: ${stderr || stdout}`,
              });
              return;
            }

            try {
              const result = JSON.parse(stdout.trim());
              resolve({
                success: true,
                data: result as WebhookTestResult,
              });
            } catch {
              // Intentionally ignored: parse error details not needed, stdout is logged
              resolve({
                success: false,
                error: `Failed to parse test result: ${stdout}`,
              });
            }
          });
        });
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }
  );

  // ============================================
  // Webhook Delivery History & Statistics
  // ============================================

  /**
   * Get webhook delivery history
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_GET_DELIVERY_HISTORY,
    async (
      _,
      specId: string,
      options?: { webhookId?: string; event?: string; limit?: number }
    ): Promise<IPCResult<WebhookDelivery[]>> => {
      try {
        const deliveryDir = getWebhookDeliveryDir(specId);

        if (!existsSync(deliveryDir)) {
          return { success: true, data: [] };
        }

        const limit = options?.limit || 100;
        const deliveries: WebhookDelivery[] = [];

        // Read all delivery files
        const files = readdirSync(deliveryDir).filter((f: string) => f.endsWith('.json'));

        for (const filename of files.slice(0, limit)) {
          try {
            const filePath = path.join(deliveryDir, filename);
            const content = readFileSync(filePath, 'utf-8');
            const delivery = JSON.parse(content) as WebhookDelivery;

            // Filter by webhook_id if specified
            if (options?.webhookId && delivery.webhook_id !== options.webhookId) {
              continue;
            }

            // Filter by event if specified
            if (options?.event && delivery.event !== options.event) {
              continue;
            }

            deliveries.push(delivery);
          } catch {
            // Intentionally ignored: skip malformed delivery files
            continue;
          }
        }

        // Sort by created_at descending (newest first)
        deliveries.sort((a, b) => {
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        });

        return { success: true, data: deliveries.slice(0, limit) };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }
  );

  /**
   * Get webhook delivery statistics
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_GET_DELIVERY_STATS,
    async (_, specId: string, webhookId?: string): Promise<IPCResult<WebhookDeliveryStats>> => {
      try {
        const deliveryDir = getWebhookDeliveryDir(specId);

        if (!existsSync(deliveryDir)) {
          return {
            success: true,
            data: {
              total: 0,
              success: 0,
              failed: 0,
              pending: 0,
              success_rate: 0,
              avg_duration_ms: 0,
            },
          };
        }

        const deliveries: WebhookDelivery[] = [];

        // Read all delivery files
        const files = readdirSync(deliveryDir).filter((f: string) => f.endsWith('.json'));

        for (const filename of files) {
          try {
            const filePath = path.join(deliveryDir, filename);
            const content = readFileSync(filePath, 'utf-8');
            const delivery = JSON.parse(content) as WebhookDelivery;

            // Filter by webhook_id if specified
            if (webhookId && delivery.webhook_id !== webhookId) {
              continue;
            }

            deliveries.push(delivery);
          } catch {
            // Intentionally ignored: skip malformed delivery files
            continue;
          }
        }

        // Calculate statistics
        const total = deliveries.length;
        const success = deliveries.filter((d) => d.status === 'success').length;
        const failed = deliveries.filter((d) => d.status === 'failed' || d.status === 'permanent_failure').length;
        const pending = deliveries.filter((d) => d.status === 'pending' || d.status === 'sending').length;
        const success_rate = total > 0 ? (success / total) * 100 : 0;

        // Calculate average duration for successful deliveries
        const successfulDurations = deliveries
          .filter((d) => d.status === 'success' && d.duration_ms !== undefined)
          .map((d) => d.duration_ms!);
        const avg_duration_ms =
          successfulDurations.length > 0
            ? successfulDurations.reduce((sum, d) => sum + d, 0) / successfulDurations.length
            : 0;

        const stats: WebhookDeliveryStats = {
          total,
          success,
          failed,
          pending,
          success_rate: Math.round(success_rate * 100) / 100,
          avg_duration_ms: Math.round(avg_duration_ms),
        };

        return { success: true, data: stats };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : String(error),
        };
      }
    }
  );

  // ============================================
  // Webhook Metadata
  // ============================================

  /**
   * Get all available webhook event types
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_GET_EVENT_TYPES,
    async (): Promise<IPCResult<WebhookEventTypeMeta[]>> => {
      return { success: true, data: WEBHOOK_EVENT_TYPES };
    }
  );

  /**
   * Get all available webhook templates
   */
  ipcMain.handle(
    IPC_CHANNELS.WEBHOOK_GET_TEMPLATES,
    async (): Promise<IPCResult<WebhookTemplateMeta[]>> => {
      return { success: true, data: WEBHOOK_TEMPLATES };
    }
  );
}
