/**
 * Mock implementation for settings and app info operations
 */

import { DEFAULT_APP_SETTINGS } from '../../../shared/constants';

const noopUnsubscribe = () => {
  // Browser mode has no Electron event stream to unsubscribe from.
};

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
  testProviderConfig: async () => ({
    success: true,
    data: {
      success: true,
      provider: 'claude' as const,
      model: 'claude-sonnet-4-5-20250929',
      runtimeMode: 'analysis_only',
      message: 'Provider smoke check passed',
      responseExcerpt: 'Browser mock provider is reachable.'
    }
  }),
  getProviderRuntimeDiagnostics: async () => ({
    success: true,
    data: {
      runtime_fallback_matrix: [
        {
          provider: 'claude' as const,
          phase: 'coding',
          requested_mode: 'full_autonomous' as const,
          fail_fast_selected_mode: 'full_autonomous' as const,
          fallback_selected_mode: 'full_autonomous' as const,
          fallback_applied: false,
          fallback_reason: 'compatible',
          missing_capabilities: [],
          compatible_fallbacks: [],
          runner_candidate_ids_by_mode: {
            full_autonomous: ['claude-sdk']
          },
          selected_mode_runner_candidates: ['claude-sdk']
        }
      ],
      mcp_bridge_plan_matrix: [
        {
          provider: 'claude' as const,
          runtime_mode: 'full_autonomous' as const,
          strategy: 'native',
          available: true,
          status: 'ready',
          action_required: 'none',
          recommended_runtime_path: 'native',
          available_servers: ['context7', 'graphiti'],
          unavailable_servers: [],
          native_required_servers: [],
          local_bridge_required_servers: [],
          external_bridge_required_servers: [],
          external_bridge_ready_servers: [],
          unsupported_servers: [],
          bridged_servers: []
        }
      ],
      external_mcp_server_health: [
        {
          server: 'context7',
          display_name: 'Context7',
          bridgeable: true,
          client_enabled: false,
          server_enabled: true,
          configured: true,
          status: 'client_disabled',
          reason: 'Set AUTO_CODE_EXTERNAL_MCP_CLIENT=true to prepare external MCP connections.',
          transport: 'stdio',
          command: 'npx',
          args: ['-y', '@upstash/context7-mcp'],
          url: null,
          enabled_env: 'CONTEXT7_ENABLED',
          required_env: [],
          missing_env: [],
          concrete_servers: []
        }
      ],
      runtime_subagent_matrix: [
        {
          provider: 'claude',
          runtime_mode: 'full_autonomous',
          strategy: 'native',
          available: true,
          reason: 'claude/full_autonomous exposes native runtime subagents.',
          required_capabilities: ['text_completion'],
          missing_capabilities: [],
          available_capabilities: ['text_completion', 'subagents'],
          max_attempts: 1,
          merge_policy: 'read_only',
          artifact_support: true
        }
      ],
      recommendations: {}
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
  onAppUpdateAvailable: () => noopUnsubscribe,
  onAppUpdateDownloaded: () => noopUnsubscribe,
  onAppUpdateProgress: () => noopUnsubscribe,
  onAppUpdateStableDowngrade: () => noopUnsubscribe
};
