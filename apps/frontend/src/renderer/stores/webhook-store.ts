import { create } from 'zustand';
import type {
  WebhookConfig,
  WebhookDelivery,
  WebhookDeliveryStats,
  WebhookTestResult,
  WebhookEventTypeMeta,
  WebhookTemplateMeta,
} from '../../shared/types/webhook';
import { toast } from '../hooks/use-toast';

interface WebhookState {
  // Webhook configurations state
  webhooks: WebhookConfig[];
  webhooksLoading: boolean;
  webhooksError: string | null;
  activeSpecId: string | null;

  // Webhook delivery history state
  deliveries: WebhookDelivery[];
  deliveriesLoading: boolean;
  deliveriesError: string | null;

  // Webhook statistics state
  stats: WebhookDeliveryStats | null;
  statsLoading: boolean;
  statsError: string | null;

  // Test webhook state
  isTestingWebhook: boolean;
  testResult: WebhookTestResult | null;

  // Event types and templates metadata
  eventTypes: WebhookEventTypeMeta[];
  templates: WebhookTemplateMeta[];

  // Actions
  setActiveSpecId: (specId: string | null) => void;
  setWebhooks: (webhooks: WebhookConfig[]) => void;
  setWebhooksLoading: (loading: boolean) => void;
  setWebhooksError: (error: string | null) => void;

  // Webhook CRUD operations
  saveWebhook: (specId: string, webhook: Omit<WebhookConfig, 'webhook_id' | 'created_at' | 'updated_at'>) => Promise<WebhookConfig | null>;
  updateWebhook: (specId: string, webhookId: string, updates: Partial<WebhookConfig>) => Promise<WebhookConfig | null>;
  deleteWebhook: (specId: string, webhookId: string) => Promise<boolean>;
  testWebhook: (specId: string, webhookId: string) => Promise<WebhookTestResult | null>;

  // Delivery history and statistics
  setDeliveries: (deliveries: WebhookDelivery[]) => void;
  setDeliveriesLoading: (loading: boolean) => void;
  setDeliveriesError: (error: string | null) => void;
  loadDeliveryHistory: (specId: string, options?: { webhookId?: string; event?: string; limit?: number }) => Promise<void>;

  setStats: (stats: WebhookDeliveryStats | null) => void;
  setStatsLoading: (loading: boolean) => void;
  setStatsError: (error: string | null) => void;
  loadDeliveryStats: (specId: string, webhookId?: string) => Promise<void>;

  // Metadata
  setEventTypes: (eventTypes: WebhookEventTypeMeta[]) => void;
  setTemplates: (templates: WebhookTemplateMeta[]) => void;
  loadEventTypes: () => Promise<void>;
  loadTemplates: () => Promise<void>;
}

export const useWebhookStore = create<WebhookState>((set, get) => ({
  // Initial state
  webhooks: [],
  webhooksLoading: false,
  webhooksError: null,
  activeSpecId: null,

  deliveries: [],
  deliveriesLoading: false,
  deliveriesError: null,

  stats: null,
  statsLoading: false,
  statsError: null,

  isTestingWebhook: false,
  testResult: null,

  eventTypes: [],
  templates: [],

  setActiveSpecId: (specId) => set({ activeSpecId: specId }),

  setWebhooks: (webhooks) => set({ webhooks }),

  setWebhooksLoading: (webhooksLoading) => set({ webhooksLoading }),

  setWebhooksError: (webhooksError) => set({ webhooksError }),

  saveWebhook: async (
    specId: string,
    webhook: Omit<WebhookConfig, 'webhook_id' | 'created_at' | 'updated_at'>
  ): Promise<WebhookConfig | null> => {
    set({ webhooksLoading: true, webhooksError: null });
    try {
      const result = await window.electronAPI.createWebhook(specId, webhook);
      if (result.success && result.data) {
        const savedWebhook = result.data;
        // Add webhook to local state
        set((state) => ({
          webhooks: [...state.webhooks, savedWebhook],
          webhooksLoading: false
        }));

        // TODO: Use i18n translation keys
        // Note: Zustand stores can't use useTranslation() hook - need to pass t() or use i18n.t()
        toast({
          title: 'Webhook created',
          description: `"${savedWebhook.name}" has been configured successfully.`
        });

        return savedWebhook;
      }
      set({
        webhooksError: result.error || 'Failed to create webhook',
        webhooksLoading: false
      });
      // TODO: Use i18n translation keys
      toast({
        variant: 'destructive',
        title: 'Failed to create webhook',
        description: result.error || 'An unknown error occurred'
      });
      return null;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create webhook';
      set({
        webhooksError: errorMessage,
        webhooksLoading: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to create webhook',
        description: errorMessage
      });
      return null;
    }
  },

  updateWebhook: async (
    specId: string,
    webhookId: string,
    updates: Partial<WebhookConfig>
  ): Promise<WebhookConfig | null> => {
    set({ webhooksLoading: true, webhooksError: null });
    try {
      const result = await window.electronAPI.updateWebhook(specId, webhookId, updates);
      if (result.success && result.data) {
        const updatedWebhook = result.data;
        set((state) => ({
          webhooks: state.webhooks.map((w) =>
            w.webhook_id === updatedWebhook.webhook_id ? updatedWebhook : w
          ),
          webhooksLoading: false
        }));

        // TODO: Use i18n translation keys
        toast({
          title: 'Webhook updated',
          description: `"${updatedWebhook.name}" has been updated successfully.`
        });

        return updatedWebhook;
      }
      set({
        webhooksError: result.error || 'Failed to update webhook',
        webhooksLoading: false
      });
      // TODO: Use i18n translation keys
      toast({
        variant: 'destructive',
        title: 'Failed to update webhook',
        description: result.error || 'An unknown error occurred'
      });
      return null;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update webhook';
      set({
        webhooksError: errorMessage,
        webhooksLoading: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to update webhook',
        description: errorMessage
      });
      return null;
    }
  },

  deleteWebhook: async (specId: string, webhookId: string): Promise<boolean> => {
    set({ webhooksLoading: true, webhooksError: null });
    try {
      const result = await window.electronAPI.deleteWebhook(specId, webhookId);
      if (result.success) {
        set((state) => ({
          webhooks: state.webhooks.filter((w) => w.webhook_id !== webhookId),
          webhooksLoading: false
        }));

        // TODO: Use i18n translation keys
        toast({
          title: 'Webhook deleted',
          description: 'The webhook has been removed.'
        });

        return true;
      }
      set({
        webhooksError: result.error || 'Failed to delete webhook',
        webhooksLoading: false
      });
      // TODO: Use i18n translation keys
      toast({
        variant: 'destructive',
        title: 'Failed to delete webhook',
        description: result.error || 'An unknown error occurred'
      });
      return false;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete webhook';
      set({
        webhooksError: errorMessage,
        webhooksLoading: false
      });
      toast({
        variant: 'destructive',
        title: 'Failed to delete webhook',
        description: errorMessage
      });
      return false;
    }
  },

  testWebhook: async (specId: string, webhookId: string): Promise<WebhookTestResult | null> => {
    set({ isTestingWebhook: true, testResult: null });
    try {
      const result = await window.electronAPI.testWebhook(specId, webhookId);

      if (result.success && result.data) {
        set({ testResult: result.data, isTestingWebhook: false });

        if (result.data.success) {
          // TODO: Use i18n translation keys
          toast({
            title: 'Webhook test successful',
            description: result.data.message || 'Test event delivered successfully'
          });
        } else {
          // TODO: Use i18n translation keys
          toast({
            variant: 'destructive',
            title: 'Webhook test failed',
            description: result.data.message || result.data.error || 'Test delivery failed'
          });
        }

        return result.data;
      }

      // Error from IPC layer
      const errorResult: WebhookTestResult = {
        success: false,
        message: result.error || 'Failed to test webhook'
      };
      set({ testResult: errorResult, isTestingWebhook: false });
      // TODO: Use i18n translation keys
      toast({
        variant: 'destructive',
        title: 'Webhook test failed',
        description: result.error || 'Failed to test webhook'
      });
      return errorResult;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to test webhook';
      const errorResult: WebhookTestResult = {
        success: false,
        message: errorMessage
      };
      set({ testResult: errorResult, isTestingWebhook: false });
      // TODO: Use i18n translation keys
      toast({
        variant: 'destructive',
        title: 'Webhook test failed',
        description: errorMessage
      });
      return errorResult;
    }
  },

  // Delivery history and statistics
  setDeliveries: (deliveries) => set({ deliveries }),

  setDeliveriesLoading: (deliveriesLoading) => set({ deliveriesLoading }),

  setDeliveriesError: (deliveriesError) => set({ deliveriesError }),

  loadDeliveryHistory: async (specId: string, options?: { webhookId?: string; event?: string; limit?: number }): Promise<void> => {
    set({ deliveriesLoading: true, deliveriesError: null });
    try {
      const result = await window.electronAPI.getWebhookDeliveryHistory(specId, options);
      if (result.success && result.data) {
        set({ deliveries: result.data, deliveriesLoading: false });
      } else {
        set({
          deliveriesError: result.error || 'Failed to load delivery history',
          deliveriesLoading: false
        });
      }
    } catch (error) {
      set({
        deliveriesError: error instanceof Error ? error.message : 'Failed to load delivery history',
        deliveriesLoading: false
      });
    }
  },

  setStats: (stats) => set({ stats }),

  setStatsLoading: (statsLoading) => set({ statsLoading }),

  setStatsError: (statsError) => set({ statsError }),

  loadDeliveryStats: async (specId: string, webhookId?: string): Promise<void> => {
    set({ statsLoading: true, statsError: null });
    try {
      const result = await window.electronAPI.getWebhookDeliveryStats(specId, webhookId);
      if (result.success && result.data) {
        set({ stats: result.data, statsLoading: false });
      } else {
        set({
          statsError: result.error || 'Failed to load delivery statistics',
          statsLoading: false
        });
      }
    } catch (error) {
      set({
        statsError: error instanceof Error ? error.message : 'Failed to load delivery statistics',
        statsLoading: false
      });
    }
  },

  // Metadata
  setEventTypes: (eventTypes) => set({ eventTypes }),

  setTemplates: (templates) => set({ templates }),

  loadEventTypes: async (): Promise<void> => {
    try {
      const result = await window.electronAPI.getWebhookEventTypes();
      if (result.success && result.data) {
        set({ eventTypes: result.data });
      }
    } catch (error) {
      // Silently fail - metadata is not critical
      console.error('Failed to load webhook event types:', error);
    }
  },

  loadTemplates: async (): Promise<void> => {
    try {
      const result = await window.electronAPI.getWebhookTemplates();
      if (result.success && result.data) {
        set({ templates: result.data });
      }
    } catch (error) {
      // Silently fail - metadata is not critical
      console.error('Failed to load webhook templates:', error);
    }
  }
}));

/**
 * Load webhooks for a spec
 */
export async function loadWebhooks(specId: string): Promise<void> {
  const store = useWebhookStore.getState();
  store.setActiveSpecId(specId);
  store.setWebhooksLoading(true);

  try {
    const result = await window.electronAPI.listWebhooks(specId);
    if (result.success && result.data) {
      store.setWebhooks(result.data);
    }
  } catch (error) {
    store.setWebhooksError(error instanceof Error ? error.message : 'Failed to load webhooks');
  } finally {
    store.setWebhooksLoading(false);
  }
}

/**
 * Load webhook metadata (event types and templates)
 */
export async function loadWebhookMetadata(): Promise<void> {
  const store = useWebhookStore.getState();

  // Load event types and templates in parallel
  await Promise.all([
    store.loadEventTypes(),
    store.loadTemplates()
  ]);
}
