/**
 * Mock implementation for settings and app info operations
 */

import { DEFAULT_APP_SETTINGS } from '../../../shared/constants';

export const settingsMock = {
  // Settings
  getSettings: async () => ({
    success: true,
    data: DEFAULT_APP_SETTINGS
  }),

  saveSettings: async () => ({ success: true }),

  // Sentry error reporting
  notifySentryStateChanged: (_enabled: boolean) => {
    console.warn('[browser-mock] notifySentryStateChanged called');
  },
  getSentryDsn: async () => '',  // No DSN in browser mode
  getSentryConfig: async () => ({ dsn: '', tracesSampleRate: 0, profilesSampleRate: 0 }),

  getCliToolsInfo: async () => ({
    success: true,
    data: {
      python: { found: false, source: 'fallback' as const, message: 'Not available in browser mode' },
      git: { found: false, source: 'fallback' as const, message: 'Not available in browser mode' },
      gh: { found: false, source: 'fallback' as const, message: 'Not available in browser mode' },
      claude: { found: false, source: 'fallback' as const, message: 'Not available in browser mode' }
    }
  }),

  // AI Provider Configuration (mock - no backend in browser mode)
  getProviderConfig: async () => ({
    success: true,
    data: {
      provider: 'claude' as const,
      anthropicApiKey: undefined,
      claudeModel: undefined,
      openaiApiKey: undefined,
      googleApiKey: undefined,
      openrouterApiKey: undefined,
      zhipuaiApiKey: undefined,
      zhipuaiModel: undefined,
      plannerModel: undefined,
      coderModel: undefined,
      qaModel: undefined,
    }
  }),
  updateProviderConfig: async () => ({ success: true }),
  validateProviderConfig: async () => ({
    success: true,
    data: {
      isValid: true,
      errors: [],
      availableProviders: [
        'claude' as const,
        'openai' as const,
        'google' as const,
        'litellm' as const,
        'openrouter' as const,
        'zhipuai' as const,
        'ollama' as const
      ]
    }
  }),

  // App Info
  getAppVersion: async () => '0.1.0-browser',

  // App Update Operations (mock - no updates in browser mode)
  checkAppUpdate: async () => ({ success: true, data: null }),
  downloadAppUpdate: async () => ({ success: true }),
  downloadStableUpdate: async () => ({ success: true }),
  installAppUpdate: () => { console.warn('[browser-mock] installAppUpdate called'); },
  getDownloadedAppUpdate: async () => ({ success: true, data: null }),

  // App Update Event Listeners (no-op in browser mode)
  onAppUpdateAvailable: () => () => {},
  onAppUpdateDownloaded: () => () => {},
  onAppUpdateProgress: () => () => {},
  onAppUpdateStableDowngrade: () => () => {}
};
