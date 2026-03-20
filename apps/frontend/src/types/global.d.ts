/**
 * Global type declarations for Electron API
 */

// Extend Window interface to include electronAPI
declare global {
  interface Window {
    electronAPI: {
      setup: {
        getSetupStatus: () => Promise<{ success: boolean; data?: { needsSetup: boolean; hasEnvFile: boolean; hasSetupMarker: boolean }; error?: string }>;
        markSetupComplete: () => Promise<{ success: boolean; error?: string }>;
        resetSetup: () => Promise<{ success: boolean; error?: string }>;
        checkPython: () => Promise<{ success: boolean; data?: { valid: boolean; version: string; required_version: string; message: string }; error?: string }>;
        getPythonInfo: () => Promise<{ success: boolean; data?: { version: string; path: string }; error?: string }>;
        checkAuth: () => Promise<{ success: boolean; data?: { authenticated: boolean; hasToken: boolean; message: string }; error?: string }>;
        validateGraphiti: (config: { llm_provider: string; embedder_provider: string; api_key?: string; embedding_key?: string; endpoint?: string }) => Promise<{ success: boolean; data?: { valid: boolean; enabled: boolean; llm_provider: string; embedder_provider: string; issues: string[]; warnings: string[]; message: string }; error?: string }>;
        getGraphitiStatus: () => Promise<{ success: boolean; data?: { enabled: boolean; llm_provider: string; embedder_provider: string; configured: boolean }; error?: string }>;
        createEnv: (config: { graphiti_enabled: boolean; llm_provider: string; embedder_provider: string; api_key?: string; embedding_key?: string; endpoint?: string }) => Promise<{ success: boolean; data?: { success: boolean; env_path: string; message: string; created_new: boolean; backed_up: boolean }; error?: string }>;
        envExists: () => Promise<{ success: boolean; data?: { exists: boolean; path: string }; error?: string }>;
        getEnvPath: () => Promise<{ success: boolean; data?: { path: string }; error?: string }>;
        runTest: () => Promise<{ success: boolean; data?: { success: boolean; steps_completed: string[]; steps_failed: string[]; error_message: string | null; summary: string }; error?: string }>;
        getTestInfo: () => Promise<{ success: boolean; data?: { running: boolean; completed: boolean; success: boolean | null; progress: number }; error?: string }>;
      };
    } & {
      [key: string]: any; // Allow other API methods to be accessed
    };
    DEBUG: boolean;
  }
}

export {};