/**
 * Shared constants and utilities for Insights provider selection.
 *
 * Centralizes the mapping between Insights provider IDs and API provider IDs,
 * as well as the provider option definitions used across UI components.
 */
import type { InsightsProvider } from '../types';
import type { TFunction } from 'i18next';

/**
 * Map Insights provider IDs to API provider IDs used in api-profiles.ts
 */
export const INSIGHTS_TO_API_PROVIDER: Record<InsightsProvider, string> = {
  claude: 'anthropic',
  litellm: 'litellm',
  openrouter: 'openrouter',
  openai: 'openai',
  ollama: 'ollama'
};

export interface InsightsProviderOption {
  id: InsightsProvider;
  label: string;
  description: string;
}

/**
 * Build the list of Insights provider options with i18n labels.
 */
export function getInsightsProviderOptions(t: TFunction): InsightsProviderOption[] {
  return [
    { id: 'claude', label: t('dialogs:customModel.providers.claude'), description: t('dialogs:customModel.providers.claudeDesc') },
    { id: 'openai', label: t('dialogs:customModel.providers.openai'), description: t('dialogs:customModel.providers.openaiDesc') },
    { id: 'ollama', label: t('dialogs:customModel.providers.ollama'), description: t('dialogs:customModel.providers.ollamaDesc') },
    { id: 'litellm', label: t('dialogs:customModel.providers.litellm'), description: t('dialogs:customModel.providers.litellmDesc') },
    { id: 'openrouter', label: t('dialogs:customModel.providers.openrouter'), description: t('dialogs:customModel.providers.openrouterDesc') }
  ];
}
