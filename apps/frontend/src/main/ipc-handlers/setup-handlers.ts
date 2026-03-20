/**
 * Setup Wizard IPC Handlers
 *
 * IPC handlers for the first-run setup wizard that guides users through
 * initial Auto Code configuration (Python validation, authentication,
 * Graphiti setup, .env creation, and hello-world test).
 */

import { ipcMain } from 'electron';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { is } from '@electron-toolkit/utils';

// ESM-compatible __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

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
// Helper Functions
// ============================================

/**
 * Get the path to the Python backend
 */
function getBackendPythonPath(): string {
  // In production, use the bundled Python from PythonEnvManager
  // In development, use the system Python from the virtual environment
  if (is.dev) {
    // Development: use .venv Python
    const backendDir = path.resolve(__dirname, '../../backend');
    const venvPython = path.join(backendDir, '.venv', 'bin', 'python');
    const venvPythonWin = path.join(backendDir, '.venv', 'Scripts', 'python.exe');

    // Try Unix path first, then Windows
    if (require('fs').existsSync(venvPython)) {
      return venvPython;
    } else if (require('fs').existsSync(venvPythonWin)) {
      return venvPythonWin;
    }

    // Fallback to system Python
    return 'python';
  }

  // Production: Python path will be set by PythonEnvManager
  return 'python';
}

/**
 * Run a Python script from the backend setup module
 */
async function runSetupScript(scriptName: string, args: string[] = []): Promise<any> {
  const pythonPath = getBackendPythonPath();
  const backendDir = path.resolve(__dirname, '../../backend');
  const scriptPath = path.join(backendDir, 'setup', scriptName);

  return new Promise((resolve, reject) => {
    const pythonProcess = spawn(pythonPath, [scriptPath, ...args], {
      cwd: backendDir,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    });

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(stdout.trim());
          resolve(result);
        } catch {
          // If output is not JSON, return as-is
          resolve(stdout.trim());
        }
      } else {
        reject(new Error(stderr || `Script exited with code ${code}`));
      }
    });

    pythonProcess.on('error', (error) => {
      reject(error);
    });
  });
}

/**
 * Run a Python function from the backend setup module
 */
async function runSetupFunction(moduleName: string, functionName: string, args: any[] = []): Promise<any> {
  const pythonPath = getBackendPythonPath();
  const backendDir = path.resolve(__dirname, '../../backend');

  // Create a Python script that imports and calls the function
  const script = `
import sys
import json
sys.path.insert(0, ${JSON.stringify(backendDir)})

try:
    from setup.${moduleName} import ${functionName}
    result = ${functionName}(${args.map(arg => JSON.stringify(arg)).join(', ')})
    print(json.dumps(result))
except Exception as e:
    import traceback
    print(json.dumps({"error": str(e), "traceback": traceback.format_exc()}), file=sys.stderr)
    sys.exit(1)
`;

  return new Promise((resolve, reject) => {
    const pythonProcess = spawn(pythonPath, ['-c', script], {
      cwd: backendDir,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    });

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(stdout.trim());
          resolve(result);
        } catch {
          reject(new Error(`Failed to parse output: ${stdout}`));
        }
      } else {
        try {
          const errorJson = JSON.parse(stderr.trim());
          reject(new Error(errorJson.error || errorJson.traceback));
        } catch {
          reject(new Error(stderr || `Script exited with code ${code}`));
        }
      }
    });

    pythonProcess.on('error', (error) => {
      reject(error);
    });
  });
}

// ============================================
// IPC Handlers Registration
// ============================================

/**
 * Register all setup wizard IPC handlers
 */
export function registerSetupHandlers(): void {
  // ============================================
  // Setup Status Handlers
  // ============================================

  /**
   * Check if setup is needed (first run detection)
   * Channel: setup:get-status
   */
  ipcMain.handle(
    'setup:get-status',
    async (): Promise<{ success: boolean; data?: SetupStatusResult; error?: string }> => {
      try {
        const result = await runSetupFunction('first_run_detector', 'detect_first_run');

        return {
          success: true,
          data: {
            needsSetup: result === true,
            hasEnvFile: false, // Will be determined by Python
            hasSetupMarker: false // Will be determined by Python
          }
        };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to check setup status'
        };
      }
    }
  );

  /**
   * Mark setup as complete
   * Channel: setup:mark-complete
   */
  ipcMain.handle(
    'setup:mark-complete',
    async (): Promise<{ success: boolean; error?: string }> => {
      try {
        await runSetupFunction('first_run_detector', 'mark_setup_complete');
        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to mark setup complete'
        };
      }
    }
  );

  /**
   * Reset setup status (for testing/reconfiguration)
   * Channel: setup:reset
   */
  ipcMain.handle(
    'setup:reset',
    async (): Promise<{ success: boolean; error?: string }> => {
      try {
        await runSetupFunction('first_run_detector', 'reset_first_run');
        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to reset setup status'
        };
      }
    }
  );

  // ============================================
  // Python Validation Handlers
  // ============================================

  /**
   * Validate Python version
   * Channel: setup:check-python
   */
  ipcMain.handle(
    'setup:check-python',
    async (): Promise<{ success: boolean; data?: PythonValidationResult; error?: string }> => {
      try {
        const result = await runSetupFunction('python_validator', 'validate_python_version');
        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to validate Python version'
        };
      }
    }
  );

  /**
   * Get detailed Python info
   * Channel: setup:get-python-info
   */
  ipcMain.handle(
    'setup:get-python-info',
    async (): Promise<{ success: boolean; data?: any; error?: string }> => {
      try {
        const result = await runSetupFunction('python_validator', 'get_python_info');
        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get Python info'
        };
      }
    }
  );

  // ============================================
  // Authentication Handlers
  // ============================================

  /**
   * Check Claude OAuth authentication status
   * Channel: setup:check-auth
   */
  ipcMain.handle(
    'setup:check-auth',
    async (): Promise<{ success: boolean; data?: AuthValidationResult; error?: string }> => {
      try {
        // Check if OAuth token exists by calling get_oauth_token
        const result = await runSetupFunction('auth_checker', 'check_oauth_token');

        return {
          success: true,
          data: {
            authenticated: result?.authenticated || false,
            hasToken: result?.hasToken || false,
            message: result?.message || 'Authentication status unknown'
          }
        };
      } catch (error) {
        // If auth_checker module doesn't exist, provide a fallback response
        return {
          success: true,
          data: {
            authenticated: false,
            hasToken: false,
            message: 'Authentication check not available - please complete OAuth setup'
          }
        };
      }
    }
  );

  // ============================================
  // Graphiti Validation Handlers
  // ============================================

  /**
   * Validate Graphiti configuration
   * Channel: setup:validate-graphiti
   */
  ipcMain.handle(
    'setup:validate-graphiti',
    async (): Promise<{ success: boolean; data?: GraphitiValidationResult; error?: string }> => {
      try {
        const result = await runSetupFunction('graphiti_validator', 'validate_graphiti_config');
        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to validate Graphiti configuration'
        };
      }
    }
  );

  /**
   * Get Graphiti status
   * Channel: setup:get-graphiti-status
   */
  ipcMain.handle(
    'setup:get-graphiti-status',
    async (): Promise<{ success: boolean; data?: any; error?: string }> => {
      try {
        const result = await runSetupFunction('graphiti_validator', 'get_graphiti_status');
        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get Graphiti status'
        };
      }
    }
  );

  // ============================================
  // .env File Handlers
  // ============================================

  /**
   * Create .env file with provided configuration
   * Channel: setup:create-env
   */
  ipcMain.handle(
    'setup:create-env',
    async (_event, config: Record<string, any>): Promise<{ success: boolean; data?: EnvCreationResult; error?: string }> => {
      try {
        const result = await runSetupFunction('env_creator', 'create_env_file', [config, true, true]);
        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to create .env file'
        };
      }
    }
  );

  /**
   * Check if .env file exists
   * Channel: setup:env-exists
   */
  ipcMain.handle(
    'setup:env-exists',
    async (): Promise<{ success: boolean; data?: { exists: boolean }; error?: string }> => {
      try {
        const result = await runSetupFunction('env_creator', 'env_exists');
        return { success: true, data: { exists: result === true } };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to check .env file'
        };
      }
    }
  );

  /**
   * Get path to .env file
   * Channel: setup:get-env-path
   */
  ipcMain.handle(
    'setup:get-env-path',
    async (): Promise<{ success: boolean; data?: { path: string }; error?: string }> => {
      try {
        const result = await runSetupFunction('env_creator', 'get_env_path');
        return { success: true, data: { path: result } };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get .env path'
        };
      }
    }
  );

  // ============================================
  // Hello-World Test Handlers
  // ============================================

  /**
   * Run hello-world test to verify setup
   * Channel: setup:run-test
   */
  ipcMain.handle(
    'setup:run-test',
    async (): Promise<{ success: boolean; data?: HelloWorldTestResult; error?: string }> => {
      try {
        const result = await runSetupFunction('hello_world_runner', 'run_hello_world_test');
        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to run hello-world test'
        };
      }
    }
  );

  /**
   * Get hello-world test info
   * Channel: setup:get-test-info
   */
  ipcMain.handle(
    'setup:get-test-info',
    async (): Promise<{ success: boolean; data?: any; error?: string }> => {
      try {
        const result = await runSetupFunction('hello_world_runner', 'get_test_info');
        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get test info'
        };
      }
    }
  );

  console.log('[Setup Handlers] All setup wizard IPC handlers registered');
}

// Re-export for type usage
export type {
  SetupStatusResult,
  PythonValidationResult,
  AuthValidationResult,
  GraphitiValidationResult,
  EnvCreationResult,
  HelloWorldTestResult
};
