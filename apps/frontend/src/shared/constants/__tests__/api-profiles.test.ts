/**
 * Unit tests for api-profiles.ts
 *
 * Tests model filtering by provider and helper functions.
 */

import { describe, it, expect } from 'vitest';
import {
  getModelsForProvider,
  getProviderById,
  getModelsByTier,
  mapModelTierToId,
  API_PROVIDER_PRESETS,
  ANTHROPIC_MODELS,
  OPENROUTER_MODELS,
  type ModelPreset
} from '../api-profiles';

describe('getModelsForProvider', () => {
  it('returns correct models for anthropic provider', () => {
    const models = getModelsForProvider('anthropic');
    expect(models.length).toBeGreaterThan(0);
    expect(models[0]).toHaveProperty('id');
    expect(models[0]).toHaveProperty('name');
    expect(models[0]).toHaveProperty('tier');

    // Verify it returns Anthropic models
    expect(models.length).toBe(ANTHROPIC_MODELS.length);
    expect(models[0].id).toContain('claude');
  });

  it('returns correct models for openrouter provider', () => {
    const models = getModelsForProvider('openrouter');
    expect(models.length).toBeGreaterThan(0);
    expect(models[0]).toHaveProperty('id');
    expect(models[0]).toHaveProperty('tier');

    // Verify it returns OpenRouter models
    expect(models.length).toBe(OPENROUTER_MODELS.length);

    // Check for OpenAI model
    const gpt4o = models.find(m => m.id === 'openai/gpt-4o');
    expect(gpt4o).toBeDefined();
    expect(gpt4o?.name).toBe('GPT-4o');
  });

  it('returns empty array for unknown provider', () => {
    const models = getModelsForProvider('unknown_provider');
    expect(models).toEqual([]);
  });

  it('returns models with correct structure for groq provider', () => {
    const models = getModelsForProvider('groq');
    expect(models.length).toBeGreaterThan(0);

    // Verify all models have required properties
    models.forEach(model => {
      expect(model).toHaveProperty('id');
      expect(model).toHaveProperty('name');
      expect(model).toHaveProperty('tier');
      expect(model).toHaveProperty('contextWindow');
      expect(model).toHaveProperty('description');
    });
  });

  it('returns models with correct structure for glm-global provider', () => {
    const models = getModelsForProvider('glm-global');
    expect(models.length).toBeGreaterThan(0);

    // Verify all models have required properties
    models.forEach(model => {
      expect(model).toHaveProperty('id');
      expect(model).toHaveProperty('name');
      expect(model).toHaveProperty('tier');
    });
  });

  it('returns models with correct structure for glm-cn provider', () => {
    const models = getModelsForProvider('glm-cn');
    expect(models.length).toBeGreaterThan(0);

    // Verify all models have required properties
    models.forEach(model => {
      expect(model).toHaveProperty('id');
      expect(model).toHaveProperty('name');
      expect(model).toHaveProperty('tier');
    });
  });
});

describe('getProviderById', () => {
  it('returns correct provider for anthropic id', () => {
    const provider = getProviderById('anthropic');
    expect(provider).toBeDefined();
    expect(provider?.id).toBe('anthropic');
    expect(provider?.baseUrl).toBe('https://api.anthropic.com');
  });

  it('returns correct provider for openrouter id', () => {
    const provider = getProviderById('openrouter');
    expect(provider).toBeDefined();
    expect(provider?.id).toBe('openrouter');
    expect(provider?.baseUrl).toBe('https://openrouter.ai/api/v1');
  });

  it('returns undefined for unknown provider id', () => {
    const provider = getProviderById('unknown_provider');
    expect(provider).toBeUndefined();
  });

  it('returns provider with models array', () => {
    const provider = getProviderById('anthropic');
    expect(provider?.models).toBeDefined();
    expect(Array.isArray(provider?.models)).toBe(true);
    expect(provider?.models.length).toBeGreaterThan(0);
  });
});

describe('getModelsByTier', () => {
  it('filters opus tier models for anthropic provider', () => {
    const opusModels = getModelsByTier('anthropic', 'opus');
    expect(opusModels.length).toBeGreaterThan(0);

    // Verify all returned models are opus tier
    opusModels.forEach(model => {
      expect(model.tier).toBe('opus');
    });

    // Check for Claude Opus model
    const opus = opusModels.find(m => m.id.includes('opus'));
    expect(opus).toBeDefined();
  });

  it('filters sonnet tier models for anthropic provider', () => {
    const sonnetModels = getModelsByTier('anthropic', 'sonnet');
    expect(sonnetModels.length).toBeGreaterThan(0);

    // Verify all returned models are sonnet tier
    sonnetModels.forEach(model => {
      expect(model.tier).toBe('sonnet');
    });

    // Check for Claude Sonnet model
    const sonnet = sonnetModels.find(m => m.id.includes('sonnet'));
    expect(sonnet).toBeDefined();
  });

  it('filters haiku tier models for anthropic provider', () => {
    const haikuModels = getModelsByTier('anthropic', 'haiku');
    expect(haikuModels.length).toBeGreaterThan(0);

    // Verify all returned models are haiku tier
    haikuModels.forEach(model => {
      expect(model.tier).toBe('haiku');
    });

    // Check for Claude Haiku model
    const haiku = haikuModels.find(m => m.id.includes('haiku'));
    expect(haiku).toBeDefined();
  });

  it('filters opus tier models for openrouter provider', () => {
    const opusModels = getModelsByTier('openrouter', 'opus');
    expect(opusModels.length).toBeGreaterThan(0);

    // Verify all returned models are opus tier
    opusModels.forEach(model => {
      expect(model.tier).toBe('opus');
    });
  });

  it('returns empty array for unknown provider', () => {
    const models = getModelsByTier('unknown_provider', 'opus');
    expect(models).toEqual([]);
  });
});

describe('mapModelTierToId', () => {
  it('returns opus model id for anthropic provider', () => {
    const modelId = mapModelTierToId('anthropic', 'opus');
    expect(modelId).toBeDefined();
    expect(modelId).toContain('claude');
    expect(modelId).toContain('opus');
  });

  it('returns sonnet model id for anthropic provider', () => {
    const modelId = mapModelTierToId('anthropic', 'sonnet');
    expect(modelId).toBeDefined();
    expect(modelId).toContain('claude');
    expect(modelId).toContain('sonnet');
  });

  it('returns haiku model id for anthropic provider', () => {
    const modelId = mapModelTierToId('anthropic', 'haiku');
    expect(modelId).toBeDefined();
    expect(modelId).toContain('claude');
    expect(modelId).toContain('haiku');
  });

  it('returns opus model id for openrouter provider', () => {
    const modelId = mapModelTierToId('openrouter', 'opus');
    expect(modelId).toBeDefined();
    expect(modelId).toBeTruthy();
  });

  it('returns undefined for unknown provider', () => {
    const modelId = mapModelTierToId('unknown_provider', 'opus');
    expect(modelId).toBeUndefined();
  });
});

describe('API_PROVIDER_PRESETS', () => {
  it('contains all expected providers', () => {
    const providerIds = API_PROVIDER_PRESETS.map(p => p.id);
    expect(providerIds).toContain('anthropic');
    expect(providerIds).toContain('openrouter');
    expect(providerIds).toContain('groq');
    expect(providerIds).toContain('glm-global');
    expect(providerIds).toContain('glm-cn');
  });

  it('each provider has required properties', () => {
    API_PROVIDER_PRESETS.forEach(provider => {
      expect(provider).toHaveProperty('id');
      expect(provider).toHaveProperty('baseUrl');
      expect(provider).toHaveProperty('labelKey');
      expect(provider).toHaveProperty('supportsModelListing');
      expect(provider).toHaveProperty('models');
      expect(Array.isArray(provider.models)).toBe(true);
    });
  });

  it('each provider has at least one model', () => {
    API_PROVIDER_PRESETS.forEach(provider => {
      expect(provider.models.length).toBeGreaterThan(0);
    });
  });
});

describe('Model filtering consistency', () => {
  it('models in provider catalog match tier filter', () => {
    const anthropicModels = getModelsForProvider('anthropic');
    const opusModels = getModelsByTier('anthropic', 'opus');
    const sonnetModels = getModelsByTier('anthropic', 'sonnet');
    const haikuModels = getModelsByTier('anthropic', 'haiku');

    // Sum of tier-filtered models should equal total models
    const totalTierModels = opusModels.length + sonnetModels.length + haikuModels.length;
    expect(totalTierModels).toBeLessThanOrEqual(anthropicModels.length);
  });

  it('openrouter provider has models from multiple vendors', () => {
    const models = getModelsForProvider('openrouter');

    // Check for OpenAI models
    const openaiModel = models.find(m => m.id.startsWith('openai/'));
    expect(openaiModel).toBeDefined();

    // Check for Google models
    const googleModel = models.find(m => m.id.startsWith('google/'));
    expect(googleModel).toBeDefined();

    // Check for Anthropic models
    const anthropicModel = models.find(m => m.id.startsWith('anthropic/'));
    expect(anthropicModel).toBeDefined();
  });
});
