/**
 * Setup Wizard API
 *
 * Exposes IPC handlers for the first-run setup wizard through the preload API.
 */

import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants/ipc';

// ============================================
// Types
// ============================================

interface SetupStatusResult {
  needsSetup: boolean;
  hasEnvFile: boolean;
  hasSetupMarker: boolean;
}

interface PythonValidationResult {
  valid: boolean;
  version: string;
  required_version: string;
  message: string;
}

interface AuthValidationResult {
  authenticated: boolean;
  hasToken: boolean;
  message: string;
}

interface GraphitiValidationResult {
  valid: boolean;
  enabled: boolean;
  llm_provider: string;
  embedder_provider: string;
  issues: string[];
  warnings: string[];
  message: string;
}

interface EnvCreationResult {
  success: boolean;
  env_path: string;
  message: string;
  created_new: boolean;
  backed_up: boolean;
}

interface HelloWorldTestResult {
  success: boolean;
  steps_completed: string[];
  steps_failed: string[];
  error_message: string | null;
  summary: string;
}

// ============================================
// SetupAPI Interface
// ============================================

export interface SetupAPI {
  /**
   * Check if setup is needed
   * Returns setup status including whether .env and setup marker exist
   */
  getSetupStatus: () => Promise<{ success: boolean; data?: SetupStatusResult; error?: string }>;

  /**
   * Mark setup as complete
   * Creates the setup marker file to prevent auto-launch on future runs
   */
  markSetupComplete: () => Promise<{ success: boolean; error?: string }>;

  /**
   * Reset setup status (for testing/reconfiguration)
   * Removes the setup marker file to re-enable setup wizard
   */
  resetSetup: () => Promise<{ success: boolean; error?: string }>;

  /**
   * Check Python version
   * Validates that Python 3.12+ is installed
   */
  checkPython: () => Promise<{ success: boolean; data?: PythonValidationResult; error?: string }>;

  /**
   * Get Python information
   * Returns detailed Python version and path information
   */
  getPythonInfo: () => Promise<{ success: boolean; data?: { version: string; path: string }; error?: string }>;

  /**
   * Check Claude SDK authentication status
   * Validates that Claude OAuth token is present in keychain
   */
  checkAuth: () => Promise<{ success: boolean; data?: AuthValidationResult; error?: string }>;

  /**
   * Validate Graphiti configuration
   * Tests Graphiti provider settings and API keys
   */
  validateGraphiti: (config: {
    llm_provider: string;
    embedder_provider: string;
    api_key?: string;
    embedding_key?: string;
    endpoint?: string;
  }) => Promise<{ success: boolean; data?: GraphitiValidationResult; error?: string }>;

  /**
   * Get Graphiti status
   * Returns current Graphiti configuration and status
   */
  getGraphitiStatus: () => Promise<{
    success: boolean;
    data?: {
      enabled: boolean;
      llm_provider: string;
      embedder_provider: string;
      configured: boolean;
    };
    error?: string;
  }>;

  /**
   * Create .env file with provided configuration
   * Generates .env file from user inputs in the wizard
   */
  createEnv: (config: {
    graphiti_enabled: boolean;
    llm_provider: string;
    embedder_provider: string;
    api_key?: string;
    embedding_key?: string;
    endpoint?: string;
  }) => Promise<{ success: boolean; data?: EnvCreationResult; error?: string }>;

  /**
   * Check if .env file exists
   * Returns whether .env file is present in backend directory
   */
  envExists: () => Promise<{ success: boolean; data?: { exists: boolean; path: string }; error?: string }>;

  /**
   * Get .env file path
   * Returns the path to the .env file
   */
  getEnvPath: () => Promise<{ success: boolean; data?: { path: string }; error?: string }>;

  /**
   * Run hello-world test
   * Executes a minimal test spec to verify setup
   */
  runTest: () => Promise<{ success: boolean; data?: HelloWorldTestResult; error?: string }>;

  /**
   * Get test information
   * Returns status and progress of running test
   */
  getTestInfo: () => Promise<{
    success: boolean;
    data?: {
      running: boolean;
      completed: boolean;
      success: boolean | null;
      progress: number;
    };
    error?: string;
  }>;
}

// ============================================
// SetupAPI Implementation
// ============================================

export const createSetupAPI = (): SetupAPI => ({
  getSetupStatus: async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_GET_STATUS);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to check setup status'
      };
    }
  },

  markSetupComplete: async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_MARK_COMPLETE);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to mark setup complete'
      };
    }
  },

  resetSetup: async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_RESET);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to reset setup'
      };
    }
  },

  checkPython: async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_CHECK_PYTHON);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to check Python version'
      };
    }
  },

  getPythonInfo: async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_GET_PYTHON_INFO);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get Python information'
      };
    }
  },

  checkAuth: async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_CHECK_AUTH);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to check authentication status'
      };
    }
  },

  validateGraphiti: async (config) => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_VALIDATE_GRAPHITI, config);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to validate Graphiti configuration'
      };
    }
  },

  getGraphitiStatus: async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_GET_GRAPHITI_STATUS);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get Graphiti status'
      };
    }
  },

  createEnv: async (config) => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_CREATE_ENV, config);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to create .env file'
      };
    }
  },

  envExists: async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_ENV_EXISTS);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to check .env file'
      };
    }
  },

  getEnvPath: async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_GET_ENV_PATH);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get .env path'
      };
    }
  },

  runTest: async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_RUN_TEST);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to run test'
      };
    }
  },

  getTestInfo: async () => {
    try {
      const result = await ipcRenderer.invoke(IPC_CHANNELS.SETUP_GET_TEST_INFO);
      return result;
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to get test information'
      };
    }
  }
});
