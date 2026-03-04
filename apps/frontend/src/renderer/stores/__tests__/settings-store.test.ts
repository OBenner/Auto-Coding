/**
 * @vitest-environment jsdom
 */
/**
 * Tests for settings store (Zustand)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useSettingsStore, loadSettings, saveSettings, loadProfiles } from '../settings-store';
import type { AppSettings } from '../../../shared/types';
import type { APIProfile, ProfileFormData, TestConnectionResult, ModelInfo } from '@shared/types/profile';
import { DEFAULT_APP_SETTINGS } from '../../../shared/constants';

// Mock toast
vi.mock('../../hooks/use-toast', () => ({
  toast: vi.fn()
}));

// Mock sentry
vi.mock('../../lib/sentry', () => ({
  markSettingsLoaded: vi.fn()
}));

// Test data
const testSettings: AppSettings = {
  ...DEFAULT_APP_SETTINGS,
  globalClaudeOAuthToken: 'test-token-123',
  autoBuildPath: '/test/path',
  onboardingCompleted: true,
  agentVerbosity: 'normal',
  agentRiskTolerance: 'balanced',
  agentProjectType: 'established',
  agentCodingStyle: {},
  agentUserInstructions: [],
};

const testProfiles: APIProfile[] = [
  {
    id: 'profile-1',
    name: 'Production API',
    baseUrl: 'https://api.anthropic.com',
    apiKey: 'sk-ant-prod-key-1234',
    models: { default: 'claude-sonnet-4-5-20250929' },
    createdAt: Date.now(),
    updatedAt: Date.now()
  },
  {
    id: 'profile-2',
    name: 'Development API',
    baseUrl: 'https://dev-api.example.com/v1',
    apiKey: 'sk-ant-test-key-5678',
    models: undefined,
    createdAt: Date.now(),
    updatedAt: Date.now()
  }
];

const testProfileFormData: ProfileFormData = {
  name: 'New Profile',
  baseUrl: 'https://new-api.example.com',
  apiKey: 'sk-new-key-9999',
  models: undefined
};

const testModelInfo: ModelInfo[] = [
  {
    id: 'claude-sonnet-4-5-20250929',
    display_name: 'Claude 4.5 Sonnet'
  },
  {
    id: 'claude-opus-4-20250514',
    display_name: 'Claude 4 Opus'
  }
];

describe('settings-store', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store to initial state
    useSettingsStore.setState({
      settings: DEFAULT_APP_SETTINGS as AppSettings,
      isLoading: true,
      error: null,
      profiles: [],
      activeProfileId: null,
      profilesLoading: false,
      profilesError: null,
      isTestingConnection: false,
      testConnectionResult: null,
      modelsLoading: false,
      modelsError: null,
      discoveredModels: new Map<string, ModelInfo[]>()
    });

    // Mock window.electronAPI
    (window as unknown as { electronAPI: unknown }).electronAPI = {
      getSettings: vi.fn().mockResolvedValue({ success: true, data: testSettings }),
      saveSettings: vi.fn().mockResolvedValue({ success: true }),
      getAPIProfiles: vi.fn().mockResolvedValue({
        success: true,
        data: { profiles: testProfiles, activeProfileId: 'profile-1' }
      }),
      saveAPIProfile: vi.fn().mockResolvedValue({
        success: true,
        data: { ...testProfileFormData, id: 'new-profile-id', createdAt: Date.now(), updatedAt: Date.now() }
      }),
      updateAPIProfile: vi.fn().mockResolvedValue({
        success: true,
        data: testProfiles[0]
      }),
      deleteAPIProfile: vi.fn().mockResolvedValue({ success: true }),
      setActiveAPIProfile: vi.fn().mockResolvedValue({ success: true }),
      testConnection: vi.fn().mockResolvedValue({
        success: true,
        data: { success: true, message: 'Connection successful' }
      }),
      discoverModels: vi.fn().mockResolvedValue({
        success: true,
        data: { models: testModelInfo }
      })
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useSettingsStore.getState();

      expect(state.settings).toEqual(DEFAULT_APP_SETTINGS);
      expect(state.isLoading).toBe(true);
      expect(state.error).toBeNull();
      expect(state.profiles).toEqual([]);
      expect(state.activeProfileId).toBeNull();
      expect(state.profilesLoading).toBe(false);
      expect(state.profilesError).toBeNull();
      expect(state.isTestingConnection).toBe(false);
      expect(state.testConnectionResult).toBeNull();
      expect(state.modelsLoading).toBe(false);
      expect(state.modelsError).toBeNull();
      expect(state.discoveredModels).toBeInstanceOf(Map);
      expect(state.discoveredModels.size).toBe(0);
    });
  });

  describe('setSettings', () => {
    it('should update settings', () => {
      const { setSettings } = useSettingsStore.getState();

      setSettings(testSettings);

      const state = useSettingsStore.getState();
      expect(state.settings).toEqual(testSettings);
    });
  });

  describe('updateSettings', () => {
    it('should merge partial settings updates', () => {
      const { setSettings, updateSettings } = useSettingsStore.getState();

      setSettings(testSettings);
      updateSettings({ onboardingCompleted: false });

      const state = useSettingsStore.getState();
      expect(state.settings.onboardingCompleted).toBe(false);
      expect(state.settings.globalClaudeOAuthToken).toBe('test-token-123');
    });

    it('should preserve existing settings when updating', () => {
      const { updateSettings } = useSettingsStore.getState();

      const initialState = useSettingsStore.getState();
      const initialTheme = initialState.settings.theme;
      const initialAutoUpdate = initialState.settings.autoUpdateAutoBuild;

      updateSettings({ autoBuildPath: '/new/path' });

      const state = useSettingsStore.getState();
      expect(state.settings.autoBuildPath).toBe('/new/path');
      // Verify other settings are preserved
      expect(state.settings.theme).toBe(initialTheme);
      expect(state.settings.autoUpdateAutoBuild).toBe(initialAutoUpdate);
    });
  });

  describe('setLoading', () => {
    it('should update loading state', () => {
      const { setLoading } = useSettingsStore.getState();

      setLoading(false);
      expect(useSettingsStore.getState().isLoading).toBe(false);

      setLoading(true);
      expect(useSettingsStore.getState().isLoading).toBe(true);
    });
  });

  describe('setError', () => {
    it('should set error message', () => {
      const { setError } = useSettingsStore.getState();

      setError('Test error');
      expect(useSettingsStore.getState().error).toBe('Test error');
    });

    it('should clear error when set to null', () => {
      const { setError } = useSettingsStore.getState();

      setError('Test error');
      setError(null);
      expect(useSettingsStore.getState().error).toBeNull();
    });
  });

  describe('setProfiles', () => {
    it('should update profiles and activeProfileId', () => {
      const { setProfiles } = useSettingsStore.getState();

      setProfiles(testProfiles, 'profile-1');

      const state = useSettingsStore.getState();
      expect(state.profiles).toEqual(testProfiles);
      expect(state.activeProfileId).toBe('profile-1');
    });

    it('should allow null activeProfileId', () => {
      const { setProfiles } = useSettingsStore.getState();

      setProfiles(testProfiles, null);

      const state = useSettingsStore.getState();
      expect(state.profiles).toEqual(testProfiles);
      expect(state.activeProfileId).toBeNull();
    });
  });

  describe('setProfilesLoading', () => {
    it('should update profiles loading state', () => {
      const { setProfilesLoading } = useSettingsStore.getState();

      setProfilesLoading(true);
      expect(useSettingsStore.getState().profilesLoading).toBe(true);

      setProfilesLoading(false);
      expect(useSettingsStore.getState().profilesLoading).toBe(false);
    });
  });

  describe('setProfilesError', () => {
    it('should set profiles error message', () => {
      const { setProfilesError } = useSettingsStore.getState();

      setProfilesError('Profile error');
      expect(useSettingsStore.getState().profilesError).toBe('Profile error');
    });

    it('should clear profiles error when set to null', () => {
      const { setProfilesError } = useSettingsStore.getState();

      setProfilesError('Profile error');
      setProfilesError(null);
      expect(useSettingsStore.getState().profilesError).toBeNull();
    });
  });

  describe('saveProfile', () => {
    it('should save profile and refresh profiles list', async () => {
      const { saveProfile } = useSettingsStore.getState();

      const result = await saveProfile(testProfileFormData);

      expect(result).toBe(true);
      expect(window.electronAPI.saveAPIProfile).toHaveBeenCalledWith(testProfileFormData);
      expect(window.electronAPI.getAPIProfiles).toHaveBeenCalled();

      const state = useSettingsStore.getState();
      expect(state.profiles).toEqual(testProfiles);
      expect(state.activeProfileId).toBe('profile-1');
      expect(state.profilesLoading).toBe(false);
    });

    it('should set loading state during save', async () => {
      const { saveProfile } = useSettingsStore.getState();

      // Start the save operation
      const savePromise = saveProfile(testProfileFormData);

      // Check loading state is true
      expect(useSettingsStore.getState().profilesLoading).toBe(true);

      await savePromise;

      // Check loading state is false after completion
      expect(useSettingsStore.getState().profilesLoading).toBe(false);
    });

    it('should handle save failure', async () => {
      vi.mocked(window.electronAPI.saveAPIProfile).mockResolvedValue({
        success: false,
        error: 'Failed to save'
      });

      const { saveProfile } = useSettingsStore.getState();
      const result = await saveProfile(testProfileFormData);

      expect(result).toBe(false);
      const state = useSettingsStore.getState();
      expect(state.profilesError).toBe('Failed to save');
      expect(state.profilesLoading).toBe(false);
    });

    it('should handle save exception', async () => {
      vi.mocked(window.electronAPI.saveAPIProfile).mockRejectedValue(new Error('Network error'));

      const { saveProfile } = useSettingsStore.getState();
      const result = await saveProfile(testProfileFormData);

      expect(result).toBe(false);
      const state = useSettingsStore.getState();
      expect(state.profilesError).toBe('Network error');
      expect(state.profilesLoading).toBe(false);
    });

    it('should fallback to local update if profile refresh fails', async () => {
      const savedProfile = { ...testProfileFormData, id: 'new-profile-id', createdAt: Date.now(), updatedAt: Date.now() };
      vi.mocked(window.electronAPI.saveAPIProfile).mockResolvedValue({
        success: true,
        data: savedProfile
      });
      vi.mocked(window.electronAPI.getAPIProfiles).mockResolvedValue({
        success: false,
        error: 'Failed to fetch profiles'
      });

      const { saveProfile } = useSettingsStore.getState();
      const result = await saveProfile(testProfileFormData);

      expect(result).toBe(true);
      const state = useSettingsStore.getState();
      expect(state.profiles).toContainEqual(savedProfile);
      expect(state.profilesLoading).toBe(false);
    });
  });

  describe('updateProfile', () => {
    it('should update existing profile', async () => {
      const { setProfiles, updateProfile } = useSettingsStore.getState();
      setProfiles(testProfiles, 'profile-1');

      const updatedProfile = { ...testProfiles[0], name: 'Updated Name' };
      vi.mocked(window.electronAPI.updateAPIProfile).mockResolvedValue({
        success: true,
        data: updatedProfile
      });

      const result = await updateProfile(updatedProfile);

      expect(result).toBe(true);
      expect(window.electronAPI.updateAPIProfile).toHaveBeenCalledWith(updatedProfile);

      const state = useSettingsStore.getState();
      expect(state.profiles.find(p => p.id === 'profile-1')?.name).toBe('Updated Name');
      expect(state.profilesLoading).toBe(false);
    });

    it('should handle update failure', async () => {
      vi.mocked(window.electronAPI.updateAPIProfile).mockResolvedValue({
        success: false,
        error: 'Update failed'
      });

      const { updateProfile } = useSettingsStore.getState();
      const result = await updateProfile(testProfiles[0]);

      expect(result).toBe(false);
      const state = useSettingsStore.getState();
      expect(state.profilesError).toBe('Update failed');
      expect(state.profilesLoading).toBe(false);
    });

    it('should handle update exception', async () => {
      vi.mocked(window.electronAPI.updateAPIProfile).mockRejectedValue(new Error('Network error'));

      const { updateProfile } = useSettingsStore.getState();
      const result = await updateProfile(testProfiles[0]);

      expect(result).toBe(false);
      const state = useSettingsStore.getState();
      expect(state.profilesError).toBe('Network error');
    });
  });

  describe('deleteProfile', () => {
    it('should delete profile from list', async () => {
      const { setProfiles, deleteProfile } = useSettingsStore.getState();
      setProfiles(testProfiles, 'profile-1');

      const result = await deleteProfile('profile-2');

      expect(result).toBe(true);
      expect(window.electronAPI.deleteAPIProfile).toHaveBeenCalledWith('profile-2');

      const state = useSettingsStore.getState();
      expect(state.profiles).toHaveLength(1);
      expect(state.profiles[0].id).toBe('profile-1');
      expect(state.activeProfileId).toBe('profile-1');
    });

    it('should clear activeProfileId when deleting active profile', async () => {
      const { setProfiles, deleteProfile } = useSettingsStore.getState();
      setProfiles(testProfiles, 'profile-1');

      const result = await deleteProfile('profile-1');

      expect(result).toBe(true);
      const state = useSettingsStore.getState();
      expect(state.activeProfileId).toBeNull();
    });

    it('should handle delete failure', async () => {
      vi.mocked(window.electronAPI.deleteAPIProfile).mockResolvedValue({
        success: false,
        error: 'Delete failed'
      });

      const { deleteProfile } = useSettingsStore.getState();
      const result = await deleteProfile('profile-1');

      expect(result).toBe(false);
      const state = useSettingsStore.getState();
      expect(state.profilesError).toBe('Delete failed');
    });

    it('should handle delete exception', async () => {
      vi.mocked(window.electronAPI.deleteAPIProfile).mockRejectedValue(new Error('Network error'));

      const { deleteProfile } = useSettingsStore.getState();
      const result = await deleteProfile('profile-1');

      expect(result).toBe(false);
      const state = useSettingsStore.getState();
      expect(state.profilesError).toBe('Network error');
    });
  });

  describe('setActiveProfile', () => {
    it('should set active profile', async () => {
      const { setActiveProfile } = useSettingsStore.getState();

      const result = await setActiveProfile('profile-1');

      expect(result).toBe(true);
      expect(window.electronAPI.setActiveAPIProfile).toHaveBeenCalledWith('profile-1');
      expect(useSettingsStore.getState().activeProfileId).toBe('profile-1');
    });

    it('should allow setting null to use OAuth', async () => {
      const { setActiveProfile } = useSettingsStore.getState();

      const result = await setActiveProfile(null);

      expect(result).toBe(true);
      expect(window.electronAPI.setActiveAPIProfile).toHaveBeenCalledWith(null);
      expect(useSettingsStore.getState().activeProfileId).toBeNull();
    });

    it('should handle setActiveProfile failure', async () => {
      vi.mocked(window.electronAPI.setActiveAPIProfile).mockResolvedValue({
        success: false,
        error: 'Failed to set active profile'
      });

      const { setActiveProfile } = useSettingsStore.getState();
      const result = await setActiveProfile('profile-1');

      expect(result).toBe(false);
      const state = useSettingsStore.getState();
      expect(state.profilesError).toBe('Failed to set active profile');
    });

    it('should handle setActiveProfile exception', async () => {
      vi.mocked(window.electronAPI.setActiveAPIProfile).mockRejectedValue(new Error('Network error'));

      const { setActiveProfile } = useSettingsStore.getState();
      const result = await setActiveProfile('profile-1');

      expect(result).toBe(false);
      const state = useSettingsStore.getState();
      expect(state.profilesError).toBe('Network error');
    });
  });

  describe('testConnection', () => {
    it('should test connection successfully', async () => {
      const { testConnection } = useSettingsStore.getState();

      const result = await testConnection('https://api.anthropic.com', 'sk-test-key');

      expect(result).toEqual({ success: true, message: 'Connection successful' });
      expect(window.electronAPI.testConnection).toHaveBeenCalledWith('https://api.anthropic.com', 'sk-test-key', undefined);

      const state = useSettingsStore.getState();
      expect(state.testConnectionResult).toEqual({ success: true, message: 'Connection successful' });
      expect(state.isTestingConnection).toBe(false);
    });

    it('should handle connection test failure', async () => {
      const failureResult: TestConnectionResult = {
        success: false,
        errorType: 'network',
        message: 'Connection failed'
      };

      vi.mocked(window.electronAPI.testConnection).mockResolvedValue({
        success: true,
        data: failureResult
      });

      const { testConnection } = useSettingsStore.getState();
      const result = await testConnection('https://api.example.com', 'sk-bad-key');

      expect(result).toEqual(failureResult);
      const state = useSettingsStore.getState();
      expect(state.testConnectionResult).toEqual(failureResult);
    });

    it('should handle IPC error during connection test', async () => {
      vi.mocked(window.electronAPI.testConnection).mockResolvedValue({
        success: false,
        error: 'IPC error'
      });

      const { testConnection } = useSettingsStore.getState();
      const result = await testConnection('https://api.example.com', 'sk-key');

      expect(result).toMatchObject({
        success: false,
        errorType: 'unknown',
        message: 'IPC error'
      });
    });

    it('should handle connection test exception', async () => {
      vi.mocked(window.electronAPI.testConnection).mockRejectedValue(new Error('Network error'));

      const { testConnection } = useSettingsStore.getState();
      const result = await testConnection('https://api.example.com', 'sk-key');

      expect(result).toMatchObject({
        success: false,
        errorType: 'unknown',
        message: 'Network error'
      });
    });

    it('should pass abort signal to testConnection', async () => {
      const { testConnection } = useSettingsStore.getState();
      const abortController = new AbortController();

      await testConnection('https://api.anthropic.com', 'sk-test-key', abortController.signal);

      expect(window.electronAPI.testConnection).toHaveBeenCalledWith(
        'https://api.anthropic.com',
        'sk-test-key',
        abortController.signal
      );
    });
  });

  describe('discoverModels', () => {
    it('should discover models successfully', async () => {
      const { discoverModels } = useSettingsStore.getState();

      const result = await discoverModels('https://api.anthropic.com', 'sk-test-key');

      expect(result).toEqual(testModelInfo);
      expect(window.electronAPI.discoverModels).toHaveBeenCalledWith('https://api.anthropic.com', 'sk-test-key', undefined);

      const state = useSettingsStore.getState();
      expect(state.modelsLoading).toBe(false);
      expect(state.discoveredModels.size).toBe(1);
    });

    it('should cache discovered models', async () => {
      const { discoverModels } = useSettingsStore.getState();

      // First call - should fetch from API
      const result1 = await discoverModels('https://api.anthropic.com', 'sk-test-key-1234');
      expect(window.electronAPI.discoverModels).toHaveBeenCalledTimes(1);

      // Second call with same credentials - should use cache
      const result2 = await discoverModels('https://api.anthropic.com', 'sk-test-key-1234');
      expect(window.electronAPI.discoverModels).toHaveBeenCalledTimes(1); // Still 1, not 2

      expect(result1).toEqual(result2);
    });

    it('should fetch new models for different credentials', async () => {
      const { discoverModels } = useSettingsStore.getState();

      await discoverModels('https://api.anthropic.com', 'sk-test-key-1234');
      expect(window.electronAPI.discoverModels).toHaveBeenCalledTimes(1);

      // Different API key - should fetch again
      await discoverModels('https://api.anthropic.com', 'sk-test-key-5678');
      expect(window.electronAPI.discoverModels).toHaveBeenCalledTimes(2);
    });

    it('should handle model discovery failure', async () => {
      vi.mocked(window.electronAPI.discoverModels).mockResolvedValue({
        success: false,
        error: 'Failed to discover models'
      });

      const { discoverModels } = useSettingsStore.getState();
      const result = await discoverModels('https://api.example.com', 'sk-key');

      expect(result).toBeNull();
      const state = useSettingsStore.getState();
      expect(state.modelsError).toBe('Failed to discover models');
      expect(state.modelsLoading).toBe(false);
    });

    it('should handle model discovery exception', async () => {
      vi.mocked(window.electronAPI.discoverModels).mockRejectedValue(new Error('Network error'));

      const { discoverModels } = useSettingsStore.getState();
      const result = await discoverModels('https://api.example.com', 'sk-key');

      expect(result).toBeNull();
      const state = useSettingsStore.getState();
      expect(state.modelsError).toBe('Network error');
    });

    it('should pass abort signal to discoverModels', async () => {
      const { discoverModels } = useSettingsStore.getState();
      const abortController = new AbortController();

      await discoverModels('https://api.anthropic.com', 'sk-test-key', abortController.signal);

      expect(window.electronAPI.discoverModels).toHaveBeenCalledWith(
        'https://api.anthropic.com',
        'sk-test-key',
        abortController.signal
      );
    });
  });

  describe('loadSettings', () => {
    it('should load settings from electronAPI', async () => {
      await loadSettings();

      expect(window.electronAPI.getSettings).toHaveBeenCalled();

      const state = useSettingsStore.getState();
      // migrateAgentPreferences adds default agent preference fields
      expect(state.settings).toEqual({
        ...testSettings,
        agentVerbosity: 'normal',
        agentRiskTolerance: 'balanced',
        agentProjectType: 'established',
        agentCodingStyle: {},
        agentUserInstructions: [],
      });
      expect(state.isLoading).toBe(false);
    });

    it('should handle settings load failure', async () => {
      vi.mocked(window.electronAPI.getSettings).mockResolvedValue({
        success: false,
        error: 'Failed to load'
      });

      await loadSettings();

      const state = useSettingsStore.getState();
      expect(state.isLoading).toBe(false);
      // Settings should remain at default when load fails
      expect(state.settings).toEqual(DEFAULT_APP_SETTINGS);
    });

    it('should handle settings load exception', async () => {
      vi.mocked(window.electronAPI.getSettings).mockRejectedValue(new Error('Network error'));

      await loadSettings();

      const state = useSettingsStore.getState();
      expect(state.error).toBe('Network error');
      expect(state.isLoading).toBe(false);
    });

    it('should migrate onboardingCompleted for existing users with OAuth token', async () => {
      const settingsWithoutOnboarding = {
        ...testSettings,
        onboardingCompleted: undefined
      };

      vi.mocked(window.electronAPI.getSettings).mockResolvedValue({
        success: true,
        data: settingsWithoutOnboarding as AppSettings
      });

      await loadSettings();

      const state = useSettingsStore.getState();
      expect(state.settings.onboardingCompleted).toBe(true);
      expect(window.electronAPI.saveSettings).toHaveBeenCalledWith(
        expect.objectContaining({ onboardingCompleted: true })
      );
    });

    it('should migrate onboardingCompleted for existing users with autoBuildPath', async () => {
      const settingsWithoutOnboarding = {
        ...DEFAULT_APP_SETTINGS,
        globalClaudeOAuthToken: '',
        autoBuildPath: '/test/path',
        onboardingCompleted: undefined
      };

      vi.mocked(window.electronAPI.getSettings).mockResolvedValue({
        success: true,
        data: settingsWithoutOnboarding as AppSettings
      });

      await loadSettings();

      const state = useSettingsStore.getState();
      expect(state.settings.onboardingCompleted).toBe(true);
      // Both onboarding and agent preference migrations are persisted
      expect(window.electronAPI.saveSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          onboardingCompleted: true,
          agentVerbosity: 'normal',
          agentRiskTolerance: 'balanced',
          agentProjectType: 'established',
          agentCodingStyle: {},
          agentUserInstructions: [],
        })
      );
    });

    it('should set onboardingCompleted to false for new users', async () => {
      const newUserSettings = {
        ...DEFAULT_APP_SETTINGS,
        globalClaudeOAuthToken: '',
        autoBuildPath: '',
        onboardingCompleted: undefined
      };

      vi.mocked(window.electronAPI.getSettings).mockResolvedValue({
        success: true,
        data: newUserSettings as AppSettings
      });

      await loadSettings();

      const state = useSettingsStore.getState();
      expect(state.settings.onboardingCompleted).toBe(false);
      // Both onboarding and agent preference migrations are persisted
      expect(window.electronAPI.saveSettings).toHaveBeenCalledWith(
        expect.objectContaining({
          onboardingCompleted: false,
          agentVerbosity: 'normal',
          agentRiskTolerance: 'balanced',
          agentProjectType: 'established',
          agentCodingStyle: {},
          agentUserInstructions: [],
        })
      );
    });

    it('should not migrate if onboardingCompleted is already set', async () => {
      await loadSettings();

      const state = useSettingsStore.getState();
      expect(state.settings.onboardingCompleted).toBe(true);
      expect(window.electronAPI.saveSettings).not.toHaveBeenCalled();
    });
  });

  describe('saveSettings', () => {
    it('should save settings via electronAPI', async () => {
      const updates = { autoBuildPath: '/new/path' };

      const result = await saveSettings(updates);

      expect(result).toBe(true);
      expect(window.electronAPI.saveSettings).toHaveBeenCalledWith(updates);

      const state = useSettingsStore.getState();
      expect(state.settings.autoBuildPath).toBe('/new/path');
    });

    it('should handle save failure', async () => {
      vi.mocked(window.electronAPI.saveSettings).mockResolvedValue({
        success: false,
        error: 'Failed to save'
      });

      const result = await saveSettings({ autoBuildPath: '/new/path' });

      expect(result).toBe(false);
    });

    it('should handle save exception', async () => {
      vi.mocked(window.electronAPI.saveSettings).mockRejectedValue(new Error('Network error'));

      const result = await saveSettings({ autoBuildPath: '/new/path' });

      expect(result).toBe(false);
    });
  });

  describe('loadProfiles', () => {
    it('should load profiles from electronAPI', async () => {
      await loadProfiles();

      expect(window.electronAPI.getAPIProfiles).toHaveBeenCalled();

      const state = useSettingsStore.getState();
      expect(state.profiles).toEqual(testProfiles);
      expect(state.activeProfileId).toBe('profile-1');
      expect(state.profilesLoading).toBe(false);
    });

    it('should handle profiles load failure', async () => {
      vi.mocked(window.electronAPI.getAPIProfiles).mockResolvedValue({
        success: false,
        error: 'Failed to load profiles'
      });

      await loadProfiles();

      const state = useSettingsStore.getState();
      expect(state.profilesLoading).toBe(false);
      expect(state.profiles).toEqual([]); // Should remain empty
    });

    it('should handle profiles load exception', async () => {
      vi.mocked(window.electronAPI.getAPIProfiles).mockRejectedValue(new Error('Network error'));

      await loadProfiles();

      const state = useSettingsStore.getState();
      expect(state.profilesError).toBe('Network error');
      expect(state.profilesLoading).toBe(false);
    });
  });
});
