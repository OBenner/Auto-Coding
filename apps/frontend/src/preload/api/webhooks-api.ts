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
  getWebhookConfigs: (projectId: string) => Promise<IPCResult<WebhookConfig[]>>;
  getWebhookConfig: (projectId: string, id: string) => Promise<IPCResult<WebhookConfig>>;
  saveWebhookConfig: (projectId: string, config: Partial<WebhookConfig> & { id?: string }) => Promise<IPCResult<WebhookConfig>>;
  deleteWebhookConfig: (projectId: string, id: string) => Promise<IPCResult>;

  // Webhook operations
  testConnection: (projectId: string, config: WebhookConfig) => Promise<IPCResult<WebhookTestResult>>;
  enableConfig: (projectId: string, id: string) => Promise<IPCResult>;
  disableConfig: (projectId: string, id: string) => Promise<IPCResult>;

  // Webhook logs and status
  getLogs: (projectId: string, webhookId: string, limit?: number) => Promise<IPCResult<WebhookLog[]>>;
  getIntegrationStatus: (projectId: string, integration: string) => Promise<IPCResult<WebhookIntegrationStatus>>;
}

export const createWebhooksAPI = (): WebhooksAPI => ({
  // Webhook configuration management
  getWebhookConfigs: (projectId: string): Promise<IPCResult<WebhookConfig[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_GET_CONFIGS, projectId),

  getWebhookConfig: (projectId: string, id: string): Promise<IPCResult<WebhookConfig>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_GET_CONFIG, projectId, id),

  saveWebhookConfig: (projectId: string, config: Partial<WebhookConfig> & { id?: string }): Promise<IPCResult<WebhookConfig>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_SAVE_CONFIG, projectId, config),

  deleteWebhookConfig: (projectId: string, id: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_DELETE_CONFIG, projectId, id),

  // Webhook operations
  testConnection: (projectId: string, config: WebhookConfig): Promise<IPCResult<WebhookTestResult>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_TEST_CONNECTION, projectId, config),

  enableConfig: (projectId: string, id: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_ENABLE_CONFIG, projectId, id),

  disableConfig: (projectId: string, id: string): Promise<IPCResult> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_DISABLE_CONFIG, projectId, id),

  // Webhook logs and status
  getLogs: (projectId: string, webhookId: string, limit?: number): Promise<IPCResult<WebhookLog[]>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_GET_LOGS, projectId, webhookId, limit),

  getIntegrationStatus: (projectId: string, integration: string): Promise<IPCResult<WebhookIntegrationStatus>> =>
    ipcRenderer.invoke(IPC_CHANNELS.WEBHOOK_GET_INTEGRATION_STATUS, projectId, integration)
});
