/**
 * AI Model Pricing Data
 *
 * This file contains pricing information for all supported AI models
 * across multiple providers (Claude, OpenAI, Google Gemini, Ollama).
 *
 * Pricing is per 1M tokens and updated as of February 2026.
 *
 * Sources:
 * - Claude: https://www.anthropic.com/pricing
 * - OpenAI: https://openai.com/api/pricing/
 * - Google Gemini: https://ai.google.dev/gemini-api/docs/pricing
 * - Ollama: Free (local execution)
 */

export type ModelPricing = {
  input: number;   // Cost per 1M input tokens (USD)
  output: number;  // Cost per 1M output tokens (USD)
  provider: 'anthropic' | 'openai' | 'google' | 'ollama' | 'unknown';
};

export type CostEstimate = {
  model: string;
  provider: string;
  estimatedCost: number;
  inputTokens: number;
  outputTokens: number;
  inputCost: number;
  outputCost: number;
  formatted: string;
  pricing: {
    inputPerMillion: number;
    outputPerMillion: number;
  };
};

// ============================================
// SHARED PRICING TIERS (reused across model variants)
// ============================================

/** Helper to define a pricing tier for a provider. */
const tier = (input: number, output: number, provider: ModelPricing['provider']): ModelPricing => ({ input, output, provider });

// Anthropic tiers
const OPUS_PRICING = tier(15.00, 75.00, 'anthropic');
const SONNET_PRICING = tier(3.00, 15.00, 'anthropic');
const HAIKU_PRICING = tier(0.80, 4.00, 'anthropic');

// Ollama: all models run locally at zero cost
const OLLAMA_FREE = tier(0.00, 0.00, 'ollama');

// ============================================
// MODEL PRICING DATABASE (per 1M tokens)
// ============================================
export const MODEL_PRICING: Record<string, ModelPricing> = {
  // Anthropic Claude
  'claude-opus-4-5-20251101': OPUS_PRICING,
  'claude-opus-4-5-20251101-thinking': OPUS_PRICING,
  'claude-3-opus-20240229': OPUS_PRICING,
  'claude-sonnet-4-5-20250929': SONNET_PRICING,
  'claude-sonnet-4-5-20250929-thinking': SONNET_PRICING,
  'claude-3-5-sonnet-20241022': SONNET_PRICING,
  'claude-haiku-4-5-20251001': HAIKU_PRICING,
  'claude-3-5-haiku-20241022': HAIKU_PRICING,

  // OpenAI
  'gpt-4o': tier(2.50, 10.00, 'openai'),
  'gpt-4o-mini': tier(0.15, 0.60, 'openai'),
  'gpt-4-turbo': tier(10.00, 30.00, 'openai'),
  'gpt-4': tier(30.00, 60.00, 'openai'),
  'gpt-3.5-turbo': tier(0.50, 1.50, 'openai'),
  'o1': tier(15.00, 60.00, 'openai'),
  'o1-mini': tier(3.00, 12.00, 'openai'),
  'o3-mini': tier(3.00, 12.00, 'openai'),

  // Google Gemini
  'gemini-2.0-flash': tier(0.10, 0.40, 'google'),
  'gemini-2.0-flash-thinking': tier(0.10, 0.40, 'google'),
  'gemini-1.5-pro': tier(0.15, 0.60, 'google'),
  'gemini-1.5-flash': tier(0.075, 0.30, 'google'),

  // Ollama (local, free)
  'llama2': OLLAMA_FREE,
  'llama3': OLLAMA_FREE,
  'mistral': OLLAMA_FREE,
  'codellama': OLLAMA_FREE,
  'phi': OLLAMA_FREE,
  'gemma': OLLAMA_FREE,
  'qwen': OLLAMA_FREE,
  'deepseek-coder': OLLAMA_FREE,

  // Fallback (Sonnet pricing for unknown models)
  'default': tier(3.00, 15.00, 'unknown'),
};

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Calculate cost for a model operation
 *
 * @param model - Model identifier (e.g., "gpt-4o", "claude-sonnet-4-5-20250929")
 * @param inputTokens - Number of input tokens
 * @param outputTokens - Number of output tokens
 * @returns Cost in USD
 *
 * @example
 * ```ts
 * const cost = calculateCost("gpt-4o", 10000, 2000);
 * // Returns 0.045 = (10000/1M * $2.50) + (2000/1M * $10.00)
 * ```
 */
export function calculateCost(
  model: string,
  inputTokens: number,
  outputTokens: number
): number {
  // Get pricing for model (fallback to default if not found)
  const pricing = MODEL_PRICING[model] ?? MODEL_PRICING['default'];

  // Calculate cost (pricing is per 1M tokens)
  const inputCost = (inputTokens / 1_000_000) * pricing.input;
  const outputCost = (outputTokens / 1_000_000) * pricing.output;

  return inputCost + outputCost;
}

/**
 * Get pricing information for a specific model
 *
 * @param model - Model identifier
 * @returns Pricing object with input, output, and provider
 *
 * @example
 * ```ts
 * const pricing = getModelPricing("gpt-4o");
 * // Returns { input: 2.50, output: 10.00, provider: 'openai' }
 * ```
 */
export function getModelPricing(model: string): ModelPricing {
  return MODEL_PRICING[model] ?? MODEL_PRICING['default'];
}

/**
 * Get all models for a specific provider
 *
 * @param provider - Provider name ("anthropic", "openai", "google", "ollama")
 * @returns Array of model identifiers
 *
 * @example
 * ```ts
 * const models = getProviderModels("openai");
 * // Returns ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', ...]
 * ```
 */
export function getProviderModels(provider: string): string[] {
  return Object.entries(MODEL_PRICING)
    .filter(([model, pricing]) => pricing.provider === provider && model !== 'default')
    .map(([model]) => model);
}

/**
 * Get list of all supported providers
 *
 * @returns Array of provider names
 *
 * @example
 * ```ts
 * const providers = getAllProviders();
 * // Returns ['anthropic', 'google', 'ollama', 'openai']
 * ```
 */
export function getAllProviders(): string[] {
  const providers = new Set<string>();
  Object.values(MODEL_PRICING).forEach(pricing => {
    if (pricing.provider !== 'unknown') {
      providers.add(pricing.provider);
    }
  });
  return Array.from(providers).sort((a, b) => a.localeCompare(b));
}

/**
 * Format cost for display
 *
 * @param cost - Cost in USD
 * @returns Formatted string with 4 decimal places
 *
 * @example
 * ```ts
 * const formatted = formatCost(0.045);
 * // Returns "$0.0450"
 * ```
 */
export function formatCost(cost: number): string {
  return `$${cost.toFixed(4)}`;
}

/**
 * Estimate cost for a session with estimated token usage
 *
 * Useful for showing cost previews before running agents.
 *
 * @param model - Model identifier
 * @param estimatedInputTokens - Estimated input tokens
 * @param estimatedOutputTokens - Estimated output tokens
 * @returns Cost estimate with breakdown
 *
 * @example
 * ```ts
 * const estimate = estimateSessionCost("gpt-4o", 10000, 2000);
 * console.log(estimate.formatted); // "$0.0450"
 * console.log(estimate.estimatedCost); // 0.045
 * ```
 */
export function estimateSessionCost(
  model: string,
  estimatedInputTokens: number,
  estimatedOutputTokens: number
): CostEstimate {
  const pricing = getModelPricing(model);
  const inputCost = (estimatedInputTokens / 1_000_000) * pricing.input;
  const outputCost = (estimatedOutputTokens / 1_000_000) * pricing.output;
  const totalCost = inputCost + outputCost;

  return {
    model,
    provider: pricing.provider,
    estimatedCost: totalCost,
    inputTokens: estimatedInputTokens,
    outputTokens: estimatedOutputTokens,
    inputCost,
    outputCost,
    formatted: formatCost(totalCost),
    pricing: {
      inputPerMillion: pricing.input,
      outputPerMillion: pricing.output,
    },
  };
}

/**
 * Compare costs across multiple models
 *
 * Useful for showing cost comparison UI in settings.
 *
 * @param models - Array of model identifiers to compare
 * @param estimatedInputTokens - Estimated input tokens for comparison
 * @param estimatedOutputTokens - Estimated output tokens for comparison
 * @returns Array of cost estimates sorted by cost (lowest first)
 *
 * @example
 * ```ts
 * const comparison = compareCosts(
 *   ["gpt-4o", "claude-sonnet-4-5-20250929", "gemini-2.0-flash"],
 *   10000,
 *   2000
 * );
 * // Returns estimates sorted by cost: gemini < gpt-4o < claude
 * ```
 */
export function compareCosts(
  models: string[],
  estimatedInputTokens: number,
  estimatedOutputTokens: number
): CostEstimate[] {
  return models
    .map(model => estimateSessionCost(model, estimatedInputTokens, estimatedOutputTokens))
    .sort((a, b) => a.estimatedCost - b.estimatedCost);
}

/**
 * Get the cheapest model from a list
 *
 * @param models - Array of model identifiers
 * @param estimatedInputTokens - Estimated input tokens
 * @param estimatedOutputTokens - Estimated output tokens
 * @returns Model identifier of the cheapest option
 *
 * @example
 * ```ts
 * const cheapest = getCheapestModel(
 *   ["gpt-4o", "claude-sonnet-4-5-20250929"],
 *   10000,
 *   2000
 * );
 * // Returns "gpt-4o" (lower cost than Claude Sonnet)
 * ```
 */
export function getCheapestModel(
  models: string[],
  estimatedInputTokens: number,
  estimatedOutputTokens: number
): string {
  const comparison = compareCosts(models, estimatedInputTokens, estimatedOutputTokens);
  return comparison[0]?.model ?? models[0];
}
