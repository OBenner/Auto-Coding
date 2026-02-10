import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type {
  IPCResult,
  WebhookConfig,
  WebhookLog,
  WebhookIntegrationStatus,
  WebhookTestResult
} from '../../shared/types';

export interface WebhooksAPI {
  // Webhook configuration management
  getWebhookConfigs: () => Promise<IPCResult<WebhookConfig[]>>;
  getWebhookConfig: (id: string) => Promise<IPCResult<WebhookConfig>>;
  saveWebhookConfig: (config: Partial<WebhookConfig> & { id?: string }) => Promise<IPCResult<WebhookConfig>>;
  deleteWebhookConfig: (id: string) => Promise<IPCResult>;

  // Webhook operations
  testConnection: (id: string) => Promise<IPCResult<WebhookTestResult>>;
  enableConfig: (id: string) => Promise<IPCResult>;
  disableConfig: (id: string) => Promise<IPCResult>;

  // Webhook logs and status
  getLogs: (webhookId: string, limit?: number) => Promise<IPCResult<WebhookLog[]>>;
  getIntegrationStatus: (integration: string) => Promise<IPCResult<WebhookIntegrationStatus>>;
}

export const createWebhooksAPI = (): WebhooksAPI => ({
  // Webhook configuration management
  getWebhookConfigs: (): Promise<IPCResult<WebhookConfig[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_GET_CONFIGS),

  getWebhookConfig: (id: string): Promise<IPCResult<WebhookConfig>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_GET_CONFIG, id),

  saveWebhookConfig: (config: Partial<WebhookConfig> & { id?: string }): Promise<IPCResult<WebhookConfig>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_SAVE_CONFIG, config),

  deleteWebhookConfig: (id: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_DELETE_CONFIG, id),

  // Webhook operations
  testConnection: (id: string): Promise<IPCResult<WebhookTestResult>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_TEST_CONNECTION, id),

  enableConfig: (id: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_ENABLE_CONFIG, id),

  disableConfig: (id: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_DISABLE_CONFIG, id),

  // Webhook logs and status
  getLogs: (webhookId: string, limit?: number): Promise<IPCResult<WebhookLog[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_GET_LOGS, webhookId, limit),

  getIntegrationStatus: (integration: string): Promise<IPCResult<WebhookIntegrationStatus>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_GET_INTEGRATION_STATUS, integration)
});
