/**
 * Shared constants and utilities for Insights provider selection.
 *
 * Centralizes the mapping between Insights provider IDs and API provider IDs,
 * as well as the provider option definitions used across UI components.
 */
import type { InsightsProvider, ModelType } from '../types';
import type { TFunction } from 'i18next';
import { AVAILABLE_MODELS } from './index';
import { getModelsForProvider } from './api-profiles';

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

/**
 * Get provider-specific model label for a model tier.
 * Used by both InsightsModelSelector and CustomModelModal.
 */
export function getModelLabelForProvider(modelTier: ModelType, providerId: InsightsProvider): string {
  // LiteLLM doesn't have predefined models, use generic labels
  if (providerId === 'litellm') {
    return AVAILABLE_MODELS.find(m => m.value === modelTier)?.label || modelTier;
  }

  const apiProviderId = INSIGHTS_TO_API_PROVIDER[providerId];
  const models = getModelsForProvider(apiProviderId);
  const model = models.find(m => m.tier === modelTier);

  if (model) {
    return model.name;
  }

  // Fallback to generic label
  return AVAILABLE_MODELS.find(m => m.value === modelTier)?.label || modelTier;
}

/**
 * Get available models for a provider, mapped to the select component format.
 * Used by both InsightsModelSelector and CustomModelModal.
 */
export function getAvailableModelsForProvider(providerId: InsightsProvider) {
  if (providerId === 'litellm') {
    return AVAILABLE_MODELS;
  }

  const apiProviderId = INSIGHTS_TO_API_PROVIDER[providerId];
  const models = getModelsForProvider(apiProviderId);
  const tieredModels = models.filter(m => m.tier === 'opus' || m.tier === 'sonnet' || m.tier === 'haiku');

  return tieredModels.map(m => ({
    value: m.tier as ModelType,
    label: m.name,
    description: m.description
  }));
}
