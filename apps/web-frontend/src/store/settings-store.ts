/**
 * Settings Store
 *
 * Manages application settings and preferences for the web frontend.
 * Follows patterns from desktop app stores (settings-store.ts, auth-store.ts).
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ============================================
// TYPES
// ============================================

export interface AppSettings {
  // General Settings
  language: string;
  theme: 'light' | 'dark' | 'system';
  notifications: boolean;

  // API Configuration
  apiUrl: string;
  wsUrl: string;
  timeout: number;

  // Appearance
  compactMode: boolean;
  animations: boolean;

  // Advanced
  debugMode: boolean;
  autoReconnect: boolean;
  cacheEnabled: boolean;
}

const DEFAULT_SETTINGS: AppSettings = {
  // General
  language: 'en',
  theme: 'system',
  notifications: true,

  // API
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  wsUrl: import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws',
  timeout: 30,

  // Appearance
  compactMode: false,
  animations: true,

  // Advanced
  debugMode: false,
  autoReconnect: true,
  cacheEnabled: true,
};

export interface SettingsState {
  settings: AppSettings;
  isLoading: boolean;
  error: string | null;

  // Actions
  updateSettings: (updates: Partial<AppSettings>) => void;
  resetSettings: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

// ============================================
// STORE
// ============================================

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      settings: DEFAULT_SETTINGS,
      isLoading: false,
      error: null,

      updateSettings: (updates) =>
        set((state) => ({
          settings: { ...state.settings, ...updates },
        })),

      resetSettings: () =>
        set({
          settings: { ...DEFAULT_SETTINGS },
        }),

      setLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error }),

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auto-claude-web-settings',
      partialize: (state) => ({ settings: state.settings }),
    }
  )
);

// ============================================
// HELPERS
// ============================================

/**
 * Get current settings
 */
export const getSettings = (): AppSettings => {
  return useSettingsStore.getState().settings;
};

/**
 * Update specific settings
 */
export const updateSettings = (updates: Partial<AppSettings>): void => {
  useSettingsStore.getState().updateSettings(updates);
};

/**
 * Reset all settings to defaults
 */
export const resetSettings = (): void => {
  useSettingsStore.getState().resetSettings();
};
