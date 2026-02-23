/**
 * API Provider Presets and Model Catalogs
 *
 * This file contains predefined configurations for AI providers
 * including their API endpoints and available models.
 */

export type ModelPreset = {
  id: string;           // Model ID used in API calls
  name: string;         // Human-readable name
  tier: 'opus' | 'sonnet' | 'haiku' | 'other';  // Model tier for profile mapping
  contextWindow?: number;  // Context window size
  description?: string;
};

export type ApiProviderPreset = {
  id: string;
  baseUrl: string;
  labelKey: string;
  supportsModelListing: boolean;  // Whether /v1/models endpoint works
  models: ModelPreset[];          // Predefined models for this provider
};

// ============================================
// Anthropic Models (Direct API)
// ============================================
export const ANTHROPIC_MODELS: ModelPreset[] = [
  { id: 'claude-opus-4-6', name: 'Claude Opus 4.6', tier: 'opus', contextWindow: 200000, description: 'Most capable model for complex tasks' },
  { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6', tier: 'sonnet', contextWindow: 200000, description: 'Balanced performance and speed' },
  { id: 'claude-haiku-4-5-20251001', name: 'Claude Haiku 4.5', tier: 'haiku', contextWindow: 200000, description: 'Fastest model for simple tasks' },
  // Legacy models
  { id: 'claude-opus-4-5-20251101', name: 'Claude Opus 4.5', tier: 'opus', contextWindow: 200000, description: 'Previous generation Opus' },
  { id: 'claude-sonnet-4-5-20250929', name: 'Claude Sonnet 4.5', tier: 'sonnet', contextWindow: 200000, description: 'Previous generation Sonnet' },
];

// ============================================
// OpenRouter Models (via OpenRouter API)
// ============================================
export const OPENROUTER_MODELS: ModelPreset[] = [
  // Anthropic via OpenRouter
  { id: 'anthropic/claude-opus-4', name: 'Claude Opus 4', tier: 'opus', contextWindow: 200000, description: 'Anthropic Claude Opus via OpenRouter' },
  { id: 'anthropic/claude-sonnet-4', name: 'Claude Sonnet 4', tier: 'sonnet', contextWindow: 200000, description: 'Anthropic Claude Sonnet via OpenRouter' },
  { id: 'anthropic/claude-haiku-4', name: 'Claude Haiku 4', tier: 'haiku', contextWindow: 200000, description: 'Anthropic Claude Haiku via OpenRouter' },
  { id: 'anthropic/claude-3.5-sonnet', name: 'Claude 3.5 Sonnet', tier: 'sonnet', contextWindow: 200000, description: 'Previous gen Sonnet via OpenRouter' },
  // OpenAI via OpenRouter
  { id: 'openai/gpt-5.2', name: 'GPT-5.2', tier: 'opus', contextWindow: 128000, description: 'OpenAI GPT-5.2 Thinking' },
  { id: 'openai/gpt-4o', name: 'GPT-4o', tier: 'sonnet', contextWindow: 128000, description: 'OpenAI GPT-4o multimodal' },
  { id: 'openai/o3', name: 'O3', tier: 'opus', contextWindow: 200000, description: 'OpenAI O3 reasoning' },
  { id: 'openai/o4-mini', name: 'O4 Mini', tier: 'sonnet', contextWindow: 200000, description: 'OpenAI O4 Mini reasoning' },
  // Google via OpenRouter
  { id: 'google/gemini-2.5-pro', name: 'Gemini 2.5 Pro', tier: 'opus', contextWindow: 1000000, description: 'Google Gemini 2.5 Pro' },
  { id: 'google/gemini-2.5-flash', name: 'Gemini 2.5 Flash', tier: 'sonnet', contextWindow: 1000000, description: 'Google Gemini 2.5 Flash' },
  // Meta via OpenRouter
  { id: 'meta-llama/llama-3.3-70b-instruct', name: 'Llama 3.3 70B', tier: 'sonnet', contextWindow: 128000, description: 'Meta Llama 3.3 70B Instruct' },
  { id: 'meta-llama/llama-3.1-405b-instruct', name: 'Llama 3.1 405B', tier: 'opus', contextWindow: 128000, description: 'Meta Llama 3.1 405B (largest open)' },
  // DeepSeek via OpenRouter
  { id: 'deepseek/deepseek-r1', name: 'DeepSeek R1', tier: 'opus', contextWindow: 64000, description: 'DeepSeek R1 reasoning model' },
  { id: 'deepseek/deepseek-chat', name: 'DeepSeek Chat', tier: 'sonnet', contextWindow: 64000, description: 'DeepSeek Chat' },
  // Mistral via OpenRouter
  { id: 'mistralai/mistral-large-2411', name: 'Mistral Large', tier: 'opus', contextWindow: 128000, description: 'Mistral Large 2411' },
  { id: 'mistralai/mistral-small-2503', name: 'Mistral Small', tier: 'haiku', contextWindow: 32000, description: 'Mistral Small 2503' },
  // Qwen via OpenRouter
  { id: 'qwen/qwen-2.5-72b-instruct', name: 'Qwen 2.5 72B', tier: 'sonnet', contextWindow: 128000, description: 'Alibaba Qwen 2.5 72B' },
];

// ============================================
// Groq Models (Fast inference)
// ============================================
export const GROQ_MODELS: ModelPreset[] = [
  { id: 'llama-3.3-70b-versatile', name: 'Llama 3.3 70B', tier: 'sonnet', contextWindow: 128000, description: 'Meta Llama 3.3 70B on Groq' },
  { id: 'llama-3.1-8b-instant', name: 'Llama 3.1 8B', tier: 'haiku', contextWindow: 128000, description: 'Meta Llama 3.1 8B (fastest)' },
  { id: 'mixtral-8x7b-32768', name: 'Mixtral 8x7B', tier: 'sonnet', contextWindow: 32768, description: 'Mistral Mixtral MoE' },
  { id: 'gemma2-9b-it', name: 'Gemma 2 9B', tier: 'haiku', contextWindow: 8192, description: 'Google Gemma 2 9B' },
];

// ============================================
// GLM Models (Zhipu AI)
// ============================================
export const GLM_MODELS: ModelPreset[] = [
  { id: 'glm-5-plus', name: 'GLM-5 Plus', tier: 'opus', contextWindow: 128000, description: 'Zhipu GLM-5 Plus (latest)' },
  { id: 'glm-5', name: 'GLM-5', tier: 'sonnet', contextWindow: 128000, description: 'Zhipu GLM-5' },
  { id: 'glm-5-flash', name: 'GLM-5 Flash', tier: 'haiku', contextWindow: 128000, description: 'Zhipu GLM-5 Flash (fast)' },
  { id: 'glm-4-plus', name: 'GLM-4 Plus', tier: 'opus', contextWindow: 128000, description: 'Zhipu GLM-4 Plus (legacy)' },
];

// ============================================
// OpenAI Models (Direct API)
// ============================================
export const OPENAI_MODELS: ModelPreset[] = [
  { id: 'gpt-5.2', name: 'GPT-5.2', tier: 'opus', contextWindow: 128000, description: 'Latest GPT-5.2 Thinking model' },
  { id: 'gpt-5.2-pro', name: 'GPT-5.2 Pro', tier: 'opus', contextWindow: 128000, description: 'GPT-5.2 Pro for complex tasks' },
  { id: 'gpt-5', name: 'GPT-5', tier: 'opus', contextWindow: 128000, description: 'GPT-5 base model' },
  { id: 'gpt-5-mini', name: 'GPT-5 Mini', tier: 'haiku', contextWindow: 128000, description: 'GPT-5 compact model' },
  { id: 'gpt-4o', name: 'GPT-4o', tier: 'sonnet', contextWindow: 128000, description: 'GPT-4o multimodal' },
  { id: 'gpt-4o-mini', name: 'GPT-4o Mini', tier: 'haiku', contextWindow: 128000, description: 'GPT-4o Mini (fast)' },
  { id: 'o4-mini', name: 'O4 Mini', tier: 'sonnet', contextWindow: 200000, description: 'Fast reasoning model' },
  { id: 'o3', name: 'O3', tier: 'opus', contextWindow: 200000, description: 'Advanced reasoning model' },
  { id: 'o3-pro', name: 'O3 Pro', tier: 'opus', contextWindow: 200000, description: 'Most capable reasoning model' },
  { id: 'o3-mini', name: 'O3 Mini', tier: 'sonnet', contextWindow: 200000, description: 'Efficient reasoning model' },
];

// ============================================
// Ollama Models (Local)
// ============================================
export const OLLAMA_MODELS: ModelPreset[] = [
  { id: 'llama3.3', name: 'Llama 3.3', tier: 'opus', contextWindow: 128000, description: 'Meta Llama 3.3 (local)' },
  { id: 'llama3.1', name: 'Llama 3.1', tier: 'sonnet', contextWindow: 128000, description: 'Meta Llama 3.1 (local)' },
  { id: 'deepseek-r1', name: 'DeepSeek R1', tier: 'opus', contextWindow: 64000, description: 'DeepSeek R1 reasoning (local)' },
  { id: 'deepseek-r1:7b', name: 'DeepSeek R1 7B', tier: 'sonnet', contextWindow: 64000, description: 'DeepSeek R1 7B (local)' },
  { id: 'qwen2.5', name: 'Qwen 2.5', tier: 'sonnet', contextWindow: 128000, description: 'Alibaba Qwen 2.5 (local)' },
  { id: 'qwen2.5-coder', name: 'Qwen 2.5 Coder', tier: 'sonnet', contextWindow: 128000, description: 'Qwen 2.5 Coder (local)' },
  { id: 'codellama', name: 'CodeLlama', tier: 'sonnet', contextWindow: 16000, description: 'Meta CodeLlama (local)' },
  { id: 'mistral', name: 'Mistral', tier: 'sonnet', contextWindow: 32000, description: 'Mistral 7B (local)' },
  { id: 'phi4', name: 'Phi-4', tier: 'haiku', contextWindow: 16000, description: 'Microsoft Phi-4 (local)' },
  { id: 'gemma2', name: 'Gemma 2', tier: 'haiku', contextWindow: 8192, description: 'Google Gemma 2 (local)' },
];

// ============================================
// Provider Presets with Model Catalogs
// ============================================
export const API_PROVIDER_PRESETS: readonly ApiProviderPreset[] = [
  {
    id: 'anthropic',
    baseUrl: 'https://api.anthropic.com',
    labelKey: 'settings:apiProfiles.presets.anthropic',
    supportsModelListing: true,
    models: ANTHROPIC_MODELS
  },
  {
    id: 'openai',
    baseUrl: 'https://api.openai.com/v1',
    labelKey: 'settings:apiProfiles.presets.openai',
    supportsModelListing: true,
    models: OPENAI_MODELS
  },
  {
    id: 'openrouter',
    baseUrl: 'https://openrouter.ai/api/v1',
    labelKey: 'settings:apiProfiles.presets.openrouter',
    supportsModelListing: false,  // OpenRouter doesn't support /v1/models
    models: OPENROUTER_MODELS
  },
  {
    id: 'groq',
    baseUrl: 'https://api.groq.com/openai/v1',
    labelKey: 'settings:apiProfiles.presets.groq',
    supportsModelListing: true,
    models: GROQ_MODELS
  },
  {
    id: 'glm-global',
    baseUrl: 'https://api.z.ai/api/anthropic',
    labelKey: 'settings:apiProfiles.presets.glmGlobal',
    supportsModelListing: false,
    models: GLM_MODELS
  },
  {
    id: 'glm-cn',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    labelKey: 'settings:apiProfiles.presets.glmChina',
    supportsModelListing: false,
    models: GLM_MODELS
  },
  {
    id: 'ollama',
    baseUrl: 'http://localhost:11434/v1',
    labelKey: 'settings:apiProfiles.presets.ollama',
    supportsModelListing: true,
    models: OLLAMA_MODELS
  }
];

// ============================================
// Helper Functions
// ============================================

/**
 * Get provider by ID
 */
export function getProviderById(providerId: string): ApiProviderPreset | undefined {
  return API_PROVIDER_PRESETS.find(p => p.id === providerId);
}

/**
 * Get provider by base URL
 */
export function getProviderByBaseUrl(baseUrl: string): ApiProviderPreset | undefined {
  const normalizedUrl = baseUrl.replace(/\/$/, '').toLowerCase();
  return API_PROVIDER_PRESETS.find(p =>
    p.baseUrl.toLowerCase() === normalizedUrl
  );
}

/**
 * Get models for a provider
 */
export function getModelsForProvider(providerId: string): ModelPreset[] {
  const provider = getProviderById(providerId);
  return provider?.models ?? [];
}

/**
 * Get models by tier for a provider
 */
export function getModelsByTier(providerId: string, tier: ModelPreset['tier']): ModelPreset[] {
  return getModelsForProvider(providerId).filter(m => m.tier === tier);
}

/**
 * Map internal model shorthand (opus/sonnet/haiku) to actual model ID for provider
 */
export function mapModelTierToId(providerId: string, tier: 'opus' | 'sonnet' | 'haiku'): string | undefined {
  const models = getModelsByTier(providerId, tier);
  return models[0]?.id;  // Return first match as default
}
