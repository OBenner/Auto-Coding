/**
 * @vitest-environment jsdom
 */

/**
 * Tests for Agent Settings Resolution Hook
 *
 * Tests profile resolution, custom overrides, feature settings, and agent-specific settings resolution.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import {
  useResolvedAgentSettings,
  resolveAgentSettings,
  type AgentSettingsSource,
} from '../useResolvedAgentSettings';
import {
  DEFAULT_AGENT_PROFILES,
  DEFAULT_PHASE_MODELS,
  DEFAULT_PHASE_THINKING,
  DEFAULT_FEATURE_MODELS,
  DEFAULT_FEATURE_THINKING,
} from '../../../shared/constants/models';
import type { AppSettings } from '../../../shared/types/settings';

describe('useResolvedAgentSettings', () => {
  let baseSettings: AppSettings;

  beforeEach(() => {
    // Create minimal AppSettings object for testing
    baseSettings = {
      theme: 'system',
      defaultModel: 'claude-sonnet-4-5-20250929',
      defaultThinkingLevel: 'medium',
      showLineNumbers: true,
      showMinimap: true,
      fontSize: 14,
      fontFamily: 'monospace',
      tabSize: 2,
      wordWrap: 'off',
      autoSave: false,
      idePreference: 'vscode',
      terminalPreference: 'system',
    } as AppSettings;
  });

  describe('default profile resolution', () => {
    it('should use default profile when no profile is selected', () => {
      const { result } = renderHook(() => useResolvedAgentSettings(baseSettings));

      const defaultProfile = DEFAULT_AGENT_PROFILES[0]; // First profile is default
      expect(result.current.phaseModels).toEqual(defaultProfile.phaseModels || DEFAULT_PHASE_MODELS);
      expect(result.current.phaseThinking).toEqual(defaultProfile.phaseThinking || DEFAULT_PHASE_THINKING);
    });

    it('should use default profile when selectedAgentProfile is "auto"', () => {
      const settings: AppSettings = {
        ...baseSettings,
        selectedAgentProfile: 'auto',
      };

      const { result } = renderHook(() => useResolvedAgentSettings(settings));

      const autoProfile = DEFAULT_AGENT_PROFILES.find((p) => p.id === 'auto');
      expect(result.current.phaseModels).toEqual(autoProfile?.phaseModels || DEFAULT_PHASE_MODELS);
      expect(result.current.phaseThinking).toEqual(autoProfile?.phaseThinking || DEFAULT_PHASE_THINKING);
    });

    it('should use default profile when selected profile does not exist', () => {
      const settings: AppSettings = {
        ...baseSettings,
        selectedAgentProfile: 'non-existent-profile',
      };

      const { result } = renderHook(() => useResolvedAgentSettings(settings));

      const defaultProfile = DEFAULT_AGENT_PROFILES[0];
      expect(result.current.phaseModels).toEqual(defaultProfile.phaseModels || DEFAULT_PHASE_MODELS);
      expect(result.current.phaseThinking).toEqual(defaultProfile.phaseThinking || DEFAULT_PHASE_THINKING);
    });
  });

  describe('profile selection', () => {
    it('should resolve settings from selected profile', () => {
      // Find a profile other than the default
      const balancedProfile = DEFAULT_AGENT_PROFILES.find((p) => p.id === 'balanced');
      expect(balancedProfile).toBeDefined();

      const settings: AppSettings = {
        ...baseSettings,
        selectedAgentProfile: 'balanced',
      };

      const { result } = renderHook(() => useResolvedAgentSettings(settings));

      expect(result.current.phaseModels).toEqual(balancedProfile?.phaseModels || DEFAULT_PHASE_MODELS);
      expect(result.current.phaseThinking).toEqual(balancedProfile?.phaseThinking || DEFAULT_PHASE_THINKING);
    });

    it('should resolve settings from different profiles', () => {
      for (const profile of DEFAULT_AGENT_PROFILES) {
        const settings: AppSettings = {
          ...baseSettings,
          selectedAgentProfile: profile.id,
        };

        const { result } = renderHook(() => useResolvedAgentSettings(settings));

        expect(result.current.phaseModels).toEqual(profile.phaseModels || DEFAULT_PHASE_MODELS);
        expect(result.current.phaseThinking).toEqual(profile.phaseThinking || DEFAULT_PHASE_THINKING);
      }
    });
  });

  describe('custom overrides', () => {
    it('should prioritize custom phase models over profile defaults', () => {
      const customPhaseModels = {
        spec: 'haiku' as const,
        planning: 'haiku' as const,
        coding: 'haiku' as const,
        qa: 'haiku' as const,
      };

      const settings: AppSettings = {
        ...baseSettings,
        selectedAgentProfile: 'auto',
        customPhaseModels,
      };

      const { result } = renderHook(() => useResolvedAgentSettings(settings));

      expect(result.current.phaseModels).toEqual(customPhaseModels);
    });

    it('should prioritize custom phase thinking over profile defaults', () => {
      const customPhaseThinking = {
        spec: 'ultrathink' as const,
        planning: 'ultrathink' as const,
        coding: 'ultrathink' as const,
        qa: 'ultrathink' as const,
      };

      const settings: AppSettings = {
        ...baseSettings,
        selectedAgentProfile: 'auto',
        customPhaseThinking,
      };

      const { result } = renderHook(() => useResolvedAgentSettings(settings));

      expect(result.current.phaseThinking).toEqual(customPhaseThinking);
    });

    it('should apply both custom models and thinking overrides', () => {
      const customPhaseModels = {
        spec: 'sonnet' as const,
        planning: 'opus' as const,
        coding: 'haiku' as const,
        qa: 'sonnet' as const,
      };

      const customPhaseThinking = {
        spec: 'high' as const,
        planning: 'medium' as const,
        coding: 'low' as const,
        qa: 'none' as const,
      };

      const settings: AppSettings = {
        ...baseSettings,
        selectedAgentProfile: 'balanced',
        customPhaseModels,
        customPhaseThinking,
      };

      const { result } = renderHook(() => useResolvedAgentSettings(settings));

      expect(result.current.phaseModels).toEqual(customPhaseModels);
      expect(result.current.phaseThinking).toEqual(customPhaseThinking);
    });
  });

  describe('feature settings', () => {
    it('should use default feature models when not provided', () => {
      const { result } = renderHook(() => useResolvedAgentSettings(baseSettings));

      expect(result.current.featureModels).toEqual(DEFAULT_FEATURE_MODELS);
      expect(result.current.featureThinking).toEqual(DEFAULT_FEATURE_THINKING);
    });

    it('should use custom feature models when provided', () => {
      const customFeatureModels = {
        insights: 'opus' as const,
        ideation: 'sonnet' as const,
        roadmap: 'haiku' as const,
        githubIssues: 'sonnet' as const,
        githubPrs: 'opus' as const,
        utility: 'haiku' as const,
      };

      const settings: AppSettings = {
        ...baseSettings,
        featureModels: customFeatureModels,
      };

      const { result } = renderHook(() => useResolvedAgentSettings(settings));

      expect(result.current.featureModels).toEqual(customFeatureModels);
    });

    it('should use custom feature thinking when provided', () => {
      const customFeatureThinking = {
        insights: 'high' as const,
        ideation: 'ultrathink' as const,
        roadmap: 'medium' as const,
        githubIssues: 'low' as const,
        githubPrs: 'none' as const,
        utility: 'low' as const,
      };

      const settings: AppSettings = {
        ...baseSettings,
        featureThinking: customFeatureThinking,
      };

      const { result } = renderHook(() => useResolvedAgentSettings(settings));

      expect(result.current.featureThinking).toEqual(customFeatureThinking);
    });
  });

  describe('memoization', () => {
    it('should memoize results when settings do not change', () => {
      const settings: AppSettings = {
        ...baseSettings,
        selectedAgentProfile: 'auto',
      };

      const { result, rerender } = renderHook(() => useResolvedAgentSettings(settings));
      const firstResult = result.current;

      rerender();
      const secondResult = result.current;

      expect(firstResult).toBe(secondResult);
    });

    it('should update when selected profile changes', () => {
      const settings: AppSettings = {
        ...baseSettings,
        selectedAgentProfile: 'auto',
      };

      const { result, rerender } = renderHook(
        ({ settings }) => useResolvedAgentSettings(settings),
        { initialProps: { settings } }
      );
      const firstResult = result.current;

      const updatedSettings: AppSettings = {
        ...baseSettings,
        selectedAgentProfile: 'balanced',
      };

      rerender({ settings: updatedSettings });
      const secondResult = result.current;

      expect(firstResult).not.toBe(secondResult);
    });

    it('should update when custom overrides change', () => {
      const settings: AppSettings = {
        ...baseSettings,
        selectedAgentProfile: 'auto',
      };

      const { result, rerender } = renderHook(
        ({ settings }) => useResolvedAgentSettings(settings),
        { initialProps: { settings } }
      );
      const firstResult = result.current;

      const updatedSettings: AppSettings = {
        ...baseSettings,
        selectedAgentProfile: 'auto',
        customPhaseModels: {
          spec: 'haiku' as const,
          planning: 'haiku' as const,
          coding: 'haiku' as const,
          qa: 'haiku' as const,
        },
      };

      rerender({ settings: updatedSettings });
      const secondResult = result.current;

      expect(firstResult).not.toBe(secondResult);
    });
  });
});

describe('resolveAgentSettings', () => {
  let resolvedSettings: ReturnType<typeof useResolvedAgentSettings>;

  beforeEach(() => {
    // Create a sample resolved settings object
    resolvedSettings = {
      phaseModels: {
        spec: 'opus',
        planning: 'opus',
        coding: 'sonnet',
        qa: 'sonnet',
      },
      phaseThinking: {
        spec: 'high',
        planning: 'medium',
        coding: 'low',
        qa: 'medium',
      },
      featureModels: {
        insights: 'sonnet',
        ideation: 'opus',
        roadmap: 'opus',
        githubIssues: 'opus',
        githubPrs: 'opus',
        utility: 'haiku',
      },
      featureThinking: {
        insights: 'medium',
        ideation: 'high',
        roadmap: 'high',
        githubIssues: 'medium',
        githubPrs: 'medium',
        utility: 'low',
      },
    };
  });

  describe('phase settings source', () => {
    it('should resolve spec phase settings', () => {
      const source: AgentSettingsSource = { type: 'phase', phase: 'spec' };
      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: resolvedSettings.phaseModels.spec,
        thinking: resolvedSettings.phaseThinking.spec,
      });
    });

    it('should resolve planning phase settings', () => {
      const source: AgentSettingsSource = { type: 'phase', phase: 'planning' };
      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: resolvedSettings.phaseModels.planning,
        thinking: resolvedSettings.phaseThinking.planning,
      });
    });

    it('should resolve coding phase settings', () => {
      const source: AgentSettingsSource = { type: 'phase', phase: 'coding' };
      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: resolvedSettings.phaseModels.coding,
        thinking: resolvedSettings.phaseThinking.coding,
      });
    });

    it('should resolve qa phase settings', () => {
      const source: AgentSettingsSource = { type: 'phase', phase: 'qa' };
      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: resolvedSettings.phaseModels.qa,
        thinking: resolvedSettings.phaseThinking.qa,
      });
    });
  });

  describe('feature settings source', () => {
    it('should resolve insights feature settings', () => {
      const source: AgentSettingsSource = { type: 'feature', feature: 'insights' };
      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: resolvedSettings.featureModels.insights,
        thinking: resolvedSettings.featureThinking.insights,
      });
    });

    it('should resolve ideation feature settings', () => {
      const source: AgentSettingsSource = { type: 'feature', feature: 'ideation' };
      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: resolvedSettings.featureModels.ideation,
        thinking: resolvedSettings.featureThinking.ideation,
      });
    });

    it('should resolve roadmap feature settings', () => {
      const source: AgentSettingsSource = { type: 'feature', feature: 'roadmap' };
      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: resolvedSettings.featureModels.roadmap,
        thinking: resolvedSettings.featureThinking.roadmap,
      });
    });

    it('should resolve githubIssues feature settings', () => {
      const source: AgentSettingsSource = { type: 'feature', feature: 'githubIssues' };
      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: resolvedSettings.featureModels.githubIssues,
        thinking: resolvedSettings.featureThinking.githubIssues,
      });
    });

    it('should resolve githubPrs feature settings', () => {
      const source: AgentSettingsSource = { type: 'feature', feature: 'githubPrs' };
      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: resolvedSettings.featureModels.githubPrs,
        thinking: resolvedSettings.featureThinking.githubPrs,
      });
    });

    it('should resolve utility feature settings', () => {
      const source: AgentSettingsSource = { type: 'feature', feature: 'utility' };
      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: resolvedSettings.featureModels.utility,
        thinking: resolvedSettings.featureThinking.utility,
      });
    });
  });

  describe('fixed settings source', () => {
    it('should return fixed model and thinking settings', () => {
      const source: AgentSettingsSource = {
        type: 'fixed',
        model: 'haiku',
        thinking: 'ultrathink',
      };

      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: 'haiku',
        thinking: 'ultrathink',
      });
    });

    it('should ignore resolved settings for fixed source', () => {
      const source: AgentSettingsSource = {
        type: 'fixed',
        model: 'haiku',
        thinking: 'none',
      };

      const result = resolveAgentSettings(source, resolvedSettings);

      expect(result).toEqual({
        model: 'haiku',
        thinking: 'none',
      });
      // Verify it uses the fixed value, not the resolved settings
      expect(result.model).toBe('haiku');
      expect(result.model).not.toBe(resolvedSettings.phaseModels.spec); // spec is 'opus'
    });
  });
});
