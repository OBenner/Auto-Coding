import { ipcMain, dialog, app, shell } from 'electron';
import { existsSync, writeFileSync, mkdirSync, statSync, readFileSync } from 'fs';
import { execFileSync } from 'node:child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { is } from '@electron-toolkit/utils';

// ESM-compatible __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
import { IPC_CHANNELS, DEFAULT_APP_SETTINGS, DEFAULT_AGENT_PROFILES } from '../../shared/constants';
import type {
  AppSettings,
  IPCResult,
  SourceEnvConfig,
  SourceEnvCheckResult,
  ProviderSettings,
  AIEngineProvider
} from '../../shared/types';
import { AgentManager } from '../agent';
import type { BrowserWindow } from 'electron';
import { setUpdateChannel, setUpdateChannelWithDowngradeCheck } from '../app-updater';
import { getSettingsPath, readSettingsFile } from '../settings-utils';
import { configureTools, getToolPath, getToolInfo, isPathFromWrongPlatform, preWarmToolCache } from '../cli-tool-manager';
import { parseEnvFile } from './utils';
import { getCurrentOS, isMacOS, isWindows } from '../platform';
import { projectStore } from '../project-store';

const settingsPath = getSettingsPath();

/**
 * Auto-detect the auto-claude source path relative to the app location.
 * Works across platforms (macOS, Windows, Linux) in both dev and production modes.
 */
const detectAutoBuildSourcePath = (): string | null => {
  const possiblePaths: string[] = [];

  // Development mode paths
  if (is.dev) {
    // In dev, __dirname is typically apps/frontend/out/main
    // We need to go up to find apps/backend
    possiblePaths.push(
      path.resolve(__dirname, '..', '..', '..', 'backend'),      // From out/main -> apps/backend
      path.resolve(process.cwd(), 'apps', 'backend')             // From cwd (repo root)
    );
  } else {
    // Production mode paths (packaged app)
    // The backend is bundled as extraResources/backend
    // On all platforms, it should be at process.resourcesPath/backend
    possiblePaths.push(
      path.resolve(process.resourcesPath, 'backend')             // Primary: extraResources/backend
    );
    // Fallback paths for different app structures
    const appPath = app.getAppPath();
    possiblePaths.push(
      path.resolve(appPath, '..', 'backend'),                    // Sibling to asar
      path.resolve(appPath, '..', '..', 'Resources', 'backend')  // macOS bundle structure
    );
  }

  // Add process.cwd() as last resort on all platforms
  possiblePaths.push(path.resolve(process.cwd(), 'apps', 'backend'));

  // Enable debug logging with DEBUG=1
  const debug = process.env.DEBUG === '1' || process.env.DEBUG === 'true';

  if (debug) {
    console.warn('[detectAutoBuildSourcePath] Platform:', getCurrentOS());
    console.warn('[detectAutoBuildSourcePath] Is dev:', is.dev);
    console.warn('[detectAutoBuildSourcePath] __dirname:', __dirname);
    console.warn('[detectAutoBuildSourcePath] app.getAppPath():', app.getAppPath());
    console.warn('[detectAutoBuildSourcePath] process.cwd():', process.cwd());
    console.warn('[detectAutoBuildSourcePath] Checking paths:', possiblePaths);
  }

  for (const p of possiblePaths) {
    // Use runners/spec_runner.py as marker - this is the file actually needed for task execution
    // This prevents matching legacy 'auto-claude/' directories that don't have the runners
    const markerPath = path.join(p, 'runners', 'spec_runner.py');
    const exists = existsSync(p) && existsSync(markerPath);

    if (debug) {
      console.warn(`[detectAutoBuildSourcePath] Checking ${p}: ${exists ? '✓ FOUND' : '✗ not found'}`);
    }

    if (exists) {
      console.warn(`[detectAutoBuildSourcePath] Auto-detected source path: ${p}`);
      return p;
    }
  }

  console.warn('[detectAutoBuildSourcePath] Could not auto-detect Auto Code source path. Please configure manually in settings.');
  console.warn('[detectAutoBuildSourcePath] Set DEBUG=1 environment variable for detailed path checking.');
  return null;
};

/**
 * Apply ProviderSettings fields onto an existing env vars map.
 * Sets or deletes keys based on whether values are truthy.
 */
function applyProviderSettingsToVars(
  vars: Record<string, string>,
  settings: ProviderSettings
): void {
  if (settings.provider !== undefined) {
    vars['AI_ENGINE_PROVIDER'] = settings.provider;
  }
  const keyMap: Array<[keyof ProviderSettings, string]> = [
    ['openaiApiKey', 'OPENAI_API_KEY'],
    ['googleApiKey', 'GOOGLE_API_KEY'],
    ['openrouterApiKey', 'OPENROUTER_API_KEY'],
    ['plannerModel', 'AGENT_MODEL_PLANNER'],
    ['coderModel', 'AGENT_MODEL_CODER'],
    ['qaModel', 'AGENT_MODEL_QA_REVIEWER'],
  ];
  for (const [settingKey, envKey] of keyMap) {
    const value = settings[settingKey];
    if (value !== undefined) {
      if (value) {
        vars[envKey] = value as string;
      } else {
        delete vars[envKey];
      }
    }
  }
}

/**
 * Read existing .env content safely (returns '' if file not found).
 * Avoids TOCTOU by reading directly and catching ENOENT.
 */
function readEnvFileSafe(envPath: string): string {
  try {
    return readFileSync(envPath, 'utf-8');
  } catch (err: unknown) {
    const code = (err as { code?: string }).code;
    if (code === 'ENOENT') {
      return '';
    }
    throw err;
  }
}

/** Generate minimal .env content for a fresh file */
function generateFreshEnvContent(vars: Record<string, string>): string {
  const varLine = (name: string) =>
    vars[name] ? `${name}=${vars[name]}` : `# ${name}=`;
  return `# Multi-Provider Configuration
AI_ENGINE_PROVIDER=${vars['AI_ENGINE_PROVIDER'] || 'claude'}

# Provider API Keys
${varLine('OPENAI_API_KEY')}
${varLine('GOOGLE_API_KEY')}
${varLine('OPENROUTER_API_KEY')}

# Per-Agent Model Configuration
${varLine('AGENT_MODEL_PLANNER')}
${varLine('AGENT_MODEL_CODER')}
${varLine('AGENT_MODEL_QA_REVIEWER')}
`;
}

/** Collect active (non-commented) variable names from parsed lines */
function collectActiveVarNames(lines: string[]): Set<string> {
  const active = new Set<string>();
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const m = trimmed.match(/^([A-Z_]+)=/);
      if (m) active.add(m[1]);
    }
  }
  return active;
}

/** Transform a single line, substituting updated variable values */
function updateEnvLine(
  line: string,
  vars: Record<string, string>,
  activeVars: Set<string>
): string {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith('#')) {
    // Uncomment a commented-out variable if we have a new value and it's not active yet
    const commentMatch = trimmed.match(/^#\s*([A-Z_]+)=/);
    if (commentMatch) {
      const varName = commentMatch[1];
      if (vars[varName] !== undefined && !activeVars.has(varName)) {
        activeVars.add(varName);
        return `${varName}=${vars[varName]}`;
      }
    }
    return line;
  }
  const match = trimmed.match(/^([A-Z_]+)=/);
  if (match && vars[match[1]] !== undefined) {
    return `${match[1]}=${vars[match[1]]}`;
  }
  return line;
}

/**
 * Generate .env file content with updated provider settings
 * Preserves existing file structure and only updates provider-related variables
 */
function generateProviderEnvContent(
  vars: Record<string, string>,
  existingContent: string
): string {
  if (!existingContent) {
    return generateFreshEnvContent(vars);
  }

  const lines = existingContent.split('\n');
  const activeVars = collectActiveVarNames(lines);
  const updatedLines = lines.map(line => updateEnvLine(line, vars, activeVars));

  // Collect all var names that appear (commented or not) in the existing file
  const existingVarNames = new Set(
    lines
      .map(line => { const m = line.trim().match(/^#?\s*([A-Z_]+)=/); return m ? m[1] : null; })
      .filter(Boolean)
  );

  const providerVars = [
    'AI_ENGINE_PROVIDER', 'OPENAI_API_KEY', 'GOOGLE_API_KEY', 'OPENROUTER_API_KEY',
    'AGENT_MODEL_PLANNER', 'AGENT_MODEL_CODER', 'AGENT_MODEL_QA_REVIEWER',
  ];
  const newVars = providerVars.filter(v => !existingVarNames.has(v) && vars[v])
    .map(v => `${v}=${vars[v]}`);

  if (newVars.length > 0) {
    updatedLines.push('', '# Provider Settings (added by UI)', ...newVars);
  }

  return updatedLines.join('\n');
}

/**
 * Register all settings-related IPC handlers
 */
export function registerSettingsHandlers(
  agentManager: AgentManager,
  getMainWindow: () => BrowserWindow | null
): void {
  // ============================================
  // Settings Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_GET,
    async (): Promise<IPCResult<AppSettings>> => {
      // Load settings using shared helper and merge with defaults
      const savedSettings = readSettingsFile();
      const settings: AppSettings = { ...DEFAULT_APP_SETTINGS, ...savedSettings };
      let needsSave = false;

      // Migration: Set agent profile to 'auto' for users who haven't made a selection (one-time)
      // This ensures new users get the optimized 'auto' profile as the default
      // while preserving existing user preferences
      if (!settings._migratedAgentProfileToAuto) {
        // Only set 'auto' if user hasn't made a selection yet
        if (!settings.selectedAgentProfile) {
          settings.selectedAgentProfile = 'auto';
        }
        settings._migratedAgentProfileToAuto = true;
        needsSave = true;
      }

      // Migration: Sync defaultModel with selectedAgentProfile (#414)
      // Fixes bug where defaultModel was stuck at 'opus' regardless of profile selection
      if (!settings._migratedDefaultModelSync) {
        if (settings.selectedAgentProfile) {
          const profile = DEFAULT_AGENT_PROFILES.find(p => p.id === settings.selectedAgentProfile);
          if (profile) {
            settings.defaultModel = profile.model;
          }
        }
        settings._migratedDefaultModelSync = true;
        needsSave = true;
      }

      // Migration: Clear CLI tool paths that are from a different platform
      // Fixes issue where Windows paths persisted on macOS (and vice versa)
      // when settings were synced/transferred between platforms
      // See: https://github.com/OBenner/Auto-Coding/issues/XXX
      const pathFields = ['pythonPath', 'gitPath', 'githubCLIPath', 'claudePath', 'autoBuildPath'] as const;
      for (const field of pathFields) {
        const pathValue = settings[field];
        if (pathValue && isPathFromWrongPlatform(pathValue)) {
          console.warn(
            `[SETTINGS_GET] Clearing ${field} - path from different platform: ${pathValue}`
          );
          delete settings[field];
          needsSave = true;
        }
      }

      // If no manual autoBuildPath is set, try to auto-detect
      if (!settings.autoBuildPath) {
        const detectedPath = detectAutoBuildSourcePath();
        if (detectedPath) {
          settings.autoBuildPath = detectedPath;
        }
      }

      // Persist migration changes
      if (needsSave) {
        try {
          writeFileSync(settingsPath, JSON.stringify(settings, null, 2));
        } catch (error) {
          console.error('[SETTINGS_GET] Failed to persist migration:', error);
          // Continue anyway - settings will be migrated in-memory for this session
        }
      }

      // Configure CLI tools with current settings
      configureTools({
        pythonPath: settings.pythonPath,
        gitPath: settings.gitPath,
        githubCLIPath: settings.githubCLIPath,
        claudePath: settings.claudePath,
      });

      // Re-warm cache asynchronously after configuring (non-blocking)
      preWarmToolCache(['claude']).catch((error) => {
        console.warn('[SETTINGS_GET] Failed to re-warm CLI cache:', error);
      });

      return { success: true, data: settings as AppSettings };
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_SAVE,
    async (_, settings: Partial<AppSettings>): Promise<IPCResult> => {
      try {
        // Load current settings using shared helper
        const savedSettings = readSettingsFile();
        const currentSettings = { ...DEFAULT_APP_SETTINGS, ...savedSettings };
        const newSettings = { ...currentSettings, ...settings };

        // Sync defaultModel when agent profile changes (#414)
        if (settings.selectedAgentProfile) {
          const profile = DEFAULT_AGENT_PROFILES.find(p => p.id === settings.selectedAgentProfile);
          if (profile) {
            newSettings.defaultModel = profile.model;
          }
        }

        writeFileSync(settingsPath, JSON.stringify(newSettings, null, 2));

        // Apply Python path if changed
        if (settings.pythonPath || settings.autoBuildPath) {
          agentManager.configure(settings.pythonPath, settings.autoBuildPath);
        }

        // Configure CLI tools if any paths changed
        if (
          settings.pythonPath !== undefined ||
          settings.gitPath !== undefined ||
          settings.githubCLIPath !== undefined ||
          settings.claudePath !== undefined
        ) {
          configureTools({
            pythonPath: newSettings.pythonPath,
            gitPath: newSettings.gitPath,
            githubCLIPath: newSettings.githubCLIPath,
            claudePath: newSettings.claudePath,
          });

          // Re-warm cache asynchronously after configuring (non-blocking)
          preWarmToolCache(['claude']).catch((error) => {
            console.warn('[SETTINGS_SAVE] Failed to re-warm CLI cache:', error);
          });
        }

        // Update auto-updater channel if betaUpdates setting changed
        if (settings.betaUpdates !== undefined) {
          if (settings.betaUpdates) {
            // Enabling beta updates - just switch channel
            setUpdateChannel('beta');
          } else {
            // Disabling beta updates - switch to stable and check if downgrade is available
            // This will notify the renderer if user is on a prerelease and stable version exists
            setUpdateChannelWithDowngradeCheck('latest', true).catch((err) => {
              console.error('[settings-handlers] Failed to check for stable downgrade:', err);
            });
          }
        }

        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to save settings'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_GET_CLI_TOOLS_INFO,
    async (): Promise<IPCResult<{
      python: ReturnType<typeof getToolInfo>;
      git: ReturnType<typeof getToolInfo>;
      gh: ReturnType<typeof getToolInfo>;
      claude: ReturnType<typeof getToolInfo>;
    }>> => {
      try {
        return {
          success: true,
          data: {
            python: getToolInfo('python'),
            git: getToolInfo('git'),
            gh: getToolInfo('gh'),
            claude: getToolInfo('claude'),
          },
        };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get CLI tools info',
        };
      }
    }
  );

  // ============================================
  // Provider Settings Operations
  // ============================================

  /**
   * Handler: saveProviderSettings
   * Saves multi-model provider configuration to project .env file
   */
  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_SAVE_PROVIDER,
    async (_, projectId: string, settings: ProviderSettings): Promise<IPCResult> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        if (!project.autoBuildPath) {
          return { success: false, error: 'Project not initialized' };
        }

        const envPath = path.join(project.path, project.autoBuildPath, '.env');

        // Read existing .env content (TOCTOU-safe: read directly, catch ENOENT)
        const existingContent = readEnvFileSafe(envPath);

        // Parse existing environment variables
        const existingVars = parseEnvFile(existingContent);

        // Apply provider settings to env vars map
        applyProviderSettingsToVars(existingVars, settings);

        // Generate new .env content preserving structure
        const newContent = generateProviderEnvContent(existingVars, existingContent);

        // Write to file
        writeFileSync(envPath, newContent);

        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to save provider settings'
        };
      }
    }
  );

  /**
   * Handler: loadProviderSettings
   * Loads multi-model provider configuration from project .env file
   */
  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_LOAD_PROVIDER,
    async (_, projectId: string): Promise<IPCResult<ProviderSettings>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        if (!project.autoBuildPath) {
          return { success: false, error: 'Project not initialized' };
        }

        const envPath = path.join(project.path, project.autoBuildPath, '.env');

        // Parse environment variables (TOCTOU-safe: read directly, catch ENOENT)
        const envVars = parseEnvFile(readEnvFileSafe(envPath));

        // Map env vars to ProviderSettings
        const providerSettings: ProviderSettings = {
          provider: (envVars['AI_ENGINE_PROVIDER'] as AIEngineProvider) || 'claude',
          openaiApiKey: envVars['OPENAI_API_KEY'] || '',
          googleApiKey: envVars['GOOGLE_API_KEY'] || '',
          openrouterApiKey: envVars['OPENROUTER_API_KEY'] || '',
          plannerModel: envVars['AGENT_MODEL_PLANNER'] || '',
          coderModel: envVars['AGENT_MODEL_CODER'] || '',
          qaModel: envVars['AGENT_MODEL_QA_REVIEWER'] || ''
        };

        return { success: true, data: providerSettings };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to load provider settings'
        };
      }
    }
  );

  // ============================================
  // Dialog Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.DIALOG_SELECT_DIRECTORY,
    async (): Promise<string | null> => {
      const mainWindow = getMainWindow();
      if (!mainWindow) return null;

      const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory'],
        title: 'Select Project Directory'
      });

      if (result.canceled || result.filePaths.length === 0) {
        return null;
      }

      return result.filePaths[0];
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.DIALOG_CREATE_PROJECT_FOLDER,
    async (
      _,
      location: string,
      name: string,
      initGit: boolean
    ): Promise<IPCResult<{ path: string; name: string; gitInitialized: boolean }>> => {
      try {
        // Validate inputs
        if (!location || !name) {
          return { success: false, error: 'Location and name are required' };
        }

        // Sanitize project name (convert to kebab-case, remove invalid chars)
        const sanitizedName = name
          .toLowerCase()
          .replace(/\s+/g, '-')
          .replace(/[^a-z0-9-_]/g, '')
          .replace(/-+/g, '-')
          .replace(/^-|-$/g, '');

        if (!sanitizedName) {
          return { success: false, error: 'Invalid project name' };
        }

        const projectPath = path.join(location, sanitizedName);

        // Check if folder already exists
        if (existsSync(projectPath)) {
          return { success: false, error: `Folder "${sanitizedName}" already exists at this location` };
        }

        // Create the directory
        mkdirSync(projectPath, { recursive: true });

        // Initialize git if requested
        let gitInitialized = false;
        if (initGit) {
          try {
            execFileSync(getToolPath('git'), ['init'], { cwd: projectPath, stdio: 'ignore' });
            gitInitialized = true;
          } catch {
            // Git init failed, but folder was created - continue without git
            console.warn('Failed to initialize git repository');
          }
        }

        return {
          success: true,
          data: {
            path: projectPath,
            name: sanitizedName,
            gitInitialized
          }
        };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to create project folder'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.DIALOG_GET_DEFAULT_PROJECT_LOCATION,
    async (): Promise<string | null> => {
      try {
        // Return user's home directory + common project folders
        const homeDir = app.getPath('home');
        const commonPaths = [
          path.join(homeDir, 'Projects'),
          path.join(homeDir, 'Developer'),
          path.join(homeDir, 'Code'),
          path.join(homeDir, 'Documents')
        ];

        // Return the first one that exists, or Documents as fallback
        for (const p of commonPaths) {
          if (existsSync(p)) {
            return p;
          }
        }

        return path.join(homeDir, 'Documents');
      } catch {
        return null;
      }
    }
  );

  // ============================================
  // App Info
  // ============================================

  ipcMain.handle(IPC_CHANNELS.APP_VERSION, async (): Promise<string> => {
    // Return the actual bundled version from package.json
    const version = app.getVersion();
    console.log('[settings-handlers] APP_VERSION returning:', version);
    return version;
  });

  // ============================================
  // Shell Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SHELL_OPEN_EXTERNAL,
    async (_, url: string): Promise<void> => {
      // Validate URL scheme to prevent opening dangerous protocols
      try {
        const parsedUrl = new URL(url);
        if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
          console.warn(`[SHELL_OPEN_EXTERNAL] Blocked URL with unsafe protocol: ${parsedUrl.protocol}`);
          throw new Error(`Unsafe URL protocol: ${parsedUrl.protocol}`);
        }
        await shell.openExternal(url);
      } catch (error) {
        if (error instanceof TypeError) {
          // Invalid URL format
          console.warn(`[SHELL_OPEN_EXTERNAL] Invalid URL format: ${url}`);
          throw new Error('Invalid URL format');
        }
        throw error;
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.SHELL_OPEN_TERMINAL,
    async (_, dirPath: string): Promise<IPCResult<void>> => {
      try {
        // Validate dirPath input
        if (!dirPath || typeof dirPath !== 'string' || dirPath.trim() === '') {
          return {
            success: false,
            error: 'Directory path is required and must be a non-empty string'
          };
        }

        // Resolve to absolute path
        const resolvedPath = path.resolve(dirPath);

        // Verify path exists
        if (!existsSync(resolvedPath)) {
          return {
            success: false,
            error: `Directory does not exist: ${resolvedPath}`
          };
        }

        // Verify it's a directory
        try {
          if (!statSync(resolvedPath).isDirectory()) {
            return {
              success: false,
              error: `Path is not a directory: ${resolvedPath}`
            };
          }
        } catch (_statError) {
          return {
            success: false,
            error: `Cannot access path: ${resolvedPath}`
          };
        }

        if (isMacOS()) {
          // macOS: Use execFileSync with argument array to prevent injection
          execFileSync('open', ['-a', 'Terminal', resolvedPath], { stdio: 'ignore' });
        } else if (isWindows()) {
          // Windows: Use cmd.exe directly with argument array
          // /C tells cmd to execute the command and terminate
          // /K keeps the window open after executing cd
          execFileSync('cmd.exe', ['/K', 'cd', '/d', resolvedPath], {
            stdio: 'ignore',
            windowsHide: false,
            shell: false  // Explicitly disable shell to prevent injection
          });
        } else {
          // Linux: Try common terminal emulators with argument arrays
          // Note: xterm uses cwd option to avoid shell injection vulnerabilities
          const terminals: Array<{ cmd: string; args: string[]; useCwd?: boolean }> = [
            { cmd: 'gnome-terminal', args: ['--working-directory', resolvedPath] },
            { cmd: 'konsole', args: ['--workdir', resolvedPath] },
            { cmd: 'xfce4-terminal', args: ['--working-directory', resolvedPath] },
            { cmd: 'xterm', args: ['-e', 'bash'], useCwd: true }
          ];

          let opened = false;
          for (const { cmd, args, useCwd } of terminals) {
            try {
              execFileSync(cmd, args, {
                stdio: 'ignore',
                ...(useCwd ? { cwd: resolvedPath } : {})
              });
              opened = true;
              break;
            } catch {
              // Try next terminal
            }
          }

          if (!opened) {
            return {
              success: false,
              error: 'No supported terminal emulator found. Please install gnome-terminal, konsole, xfce4-terminal, or xterm.'
            };
          }
        }

        return { success: true };
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        return {
          success: false,
          error: `Failed to open terminal: ${errorMsg}`
        };
      }
    }
  );

  // ============================================
  // Auto-Build Source Environment Operations
  // ============================================

  /**
   * Helper to get source .env path from settings
   *
   * In production mode, the .env file is NOT bundled (excluded in electron-builder config).
   * We store the source .env in app userData directory instead, which is writable.
   * The sourcePath points to the bundled backend for reference, but envPath is in userData.
   */
  const getSourceEnvPath = (): {
    sourcePath: string | null;
    envPath: string | null;
    isProduction: boolean;
  } => {
    const savedSettings = readSettingsFile();
    const settings = { ...DEFAULT_APP_SETTINGS, ...savedSettings };

    // Get autoBuildPath from settings or try to auto-detect
    let sourcePath: string | null = settings.autoBuildPath || null;
    if (!sourcePath) {
      sourcePath = detectAutoBuildSourcePath();
    }

    if (!sourcePath) {
      return { sourcePath: null, envPath: null, isProduction: !is.dev };
    }

    // In production, use userData directory for .env since resources may be read-only
    // In development, use the actual source path
    let envPath: string;
    if (is.dev) {
      envPath = path.join(sourcePath, '.env');
    } else {
      // Production: store .env in userData/backend/.env
      const userDataBackendDir = path.join(app.getPath('userData'), 'backend');
      if (!existsSync(userDataBackendDir)) {
        mkdirSync(userDataBackendDir, { recursive: true });
      }
      envPath = path.join(userDataBackendDir, '.env');
    }

    return {
      sourcePath,
      envPath,
      isProduction: !is.dev
    };
  };

  ipcMain.handle(
    IPC_CHANNELS.AUTOBUILD_SOURCE_ENV_GET,
    async (): Promise<IPCResult<SourceEnvConfig>> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        // Load global settings to check for global token fallback
        const savedSettings = readSettingsFile();
        const globalSettings = { ...DEFAULT_APP_SETTINGS, ...savedSettings };

        if (!sourcePath) {
          // Even without source path, check global token
          const globalToken = globalSettings.globalClaudeOAuthToken;
          return {
            success: true,
            data: {
              hasClaudeToken: !!globalToken && globalToken.length > 0,
              claudeOAuthToken: globalToken,
              envExists: false
            }
          };
        }

        const envExists = envPath ? existsSync(envPath) : false;
        let hasClaudeToken = false;
        let claudeOAuthToken: string | undefined;

        // First, check source .env file
        if (envExists && envPath) {
          const content = readFileSync(envPath, 'utf-8');
          const vars = parseEnvFile(content);
          claudeOAuthToken = vars['CLAUDE_CODE_OAUTH_TOKEN'];
          hasClaudeToken = !!claudeOAuthToken && claudeOAuthToken.length > 0;
        }

        // Fallback to global settings if no token in source .env
        if (!hasClaudeToken && globalSettings.globalClaudeOAuthToken) {
          claudeOAuthToken = globalSettings.globalClaudeOAuthToken;
          hasClaudeToken = true;
        }

        return {
          success: true,
          data: {
            hasClaudeToken,
            claudeOAuthToken,
            sourcePath,
            envExists
          }
        };
      } catch (error) {
        // Log the error for debugging in production
        console.error('[AUTOBUILD_SOURCE_ENV_GET] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get source env'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.AUTOBUILD_SOURCE_ENV_UPDATE,
    async (_, config: { claudeOAuthToken?: string }): Promise<IPCResult> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        if (!sourcePath || !envPath) {
          return {
            success: false,
            error: 'Auto-build source path not configured. Please set it in Settings.'
          };
        }

        // Read existing content or start fresh (avoiding TOCTOU race condition)
        let existingVars: Record<string, string> = {};
        try {
          const content = readFileSync(envPath, 'utf-8');
          existingVars = parseEnvFile(content);
        } catch (_readError) {
          // File doesn't exist or can't be read - start with empty vars
          // This is expected for first-time setup
        }

        // Update with new values
        if (config.claudeOAuthToken !== undefined) {
          existingVars['CLAUDE_CODE_OAUTH_TOKEN'] = config.claudeOAuthToken;
        }

        // Generate content
        const lines: string[] = [
          '# Auto Code Framework Environment Variables',
          '# Managed by Auto Code UI',
          '',
          '# Claude Code OAuth Token (REQUIRED)',
          `CLAUDE_CODE_OAUTH_TOKEN=${existingVars['CLAUDE_CODE_OAUTH_TOKEN'] || ''}`,
          ''
        ];

        // Preserve other existing variables
        for (const [key, value] of Object.entries(existingVars)) {
          if (key !== 'CLAUDE_CODE_OAUTH_TOKEN') {
            lines.push(`${key}=${value}`);
          }
        }

        writeFileSync(envPath, lines.join('\n'));

        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to update source env'
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.AUTOBUILD_SOURCE_ENV_CHECK_TOKEN,
    async (): Promise<IPCResult<SourceEnvCheckResult>> => {
      try {
        const { sourcePath, envPath, isProduction } = getSourceEnvPath();

        // Load global settings to check for global token fallback
        const savedSettings = readSettingsFile();
        const globalSettings = { ...DEFAULT_APP_SETTINGS, ...savedSettings };

        // Check global token first as it's the primary method
        const globalToken = globalSettings.globalClaudeOAuthToken;
        const hasGlobalToken = !!globalToken && globalToken.length > 0;

        if (!sourcePath) {
          // In production, no source path is acceptable if global token exists
          if (hasGlobalToken) {
            return {
              success: true,
              data: {
                hasToken: true,
                sourcePath: isProduction ? app.getPath('userData') : undefined
              }
            };
          }
          return {
            success: true,
            data: {
              hasToken: false,
              error: isProduction
                ? 'Please configure Claude OAuth token in Settings > API Configuration'
                : 'Auto-build source path not configured'
            }
          };
        }

        // Check source .env file
        let hasEnvToken = false;
        if (envPath && existsSync(envPath)) {
          const content = readFileSync(envPath, 'utf-8');
          const vars = parseEnvFile(content);
          const token = vars['CLAUDE_CODE_OAUTH_TOKEN'];
          hasEnvToken = !!token && token.length > 0;
        }

        // Token exists if either source .env has it OR global settings has it
        const hasToken = hasEnvToken || hasGlobalToken;

        return {
          success: true,
          data: {
            hasToken,
            sourcePath
          }
        };
      } catch (error) {
        // Log the error for debugging in production
        console.error('[AUTOBUILD_SOURCE_ENV_CHECK_TOKEN] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to check source token'
        };
      }
    }
  );

  // Static model lists per provider (used by getAvailableModels handler)
  const STATIC_PROVIDER_MODELS: Record<string, string[]> = {
    claude: [
      'claude-sonnet-4-5-20250929',
      'claude-opus-4-20250514',
      'claude-haiku-4-5-20251001',
      'claude-3-5-sonnet-20241022',
      'claude-3-5-haiku-20241022',
      'claude-3-opus-20240229',
    ],
    litellm: [
      'gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo',
      'anthropic/claude-3-opus-20240229', 'anthropic/claude-3-sonnet-20240229',
      'anthropic/claude-3-haiku-20240307',
      'gemini/gemini-pro', 'gemini/gemini-1.5-pro', 'gemini/gemini-1.5-flash',
      'gemini/gemini-2.0-flash',
      'ollama/llama3', 'ollama/llama3.1', 'ollama/llama3.2', 'ollama/mistral',
      'ollama/mixtral', 'ollama/codellama', 'ollama/qwen', 'ollama/qwen2',
      'ollama/gemma', 'ollama/gemma2',
    ],
    openrouter: [
      'anthropic/claude-3.5-sonnet', 'anthropic/claude-3-opus',
      'openai/gpt-4-turbo', 'openai/gpt-4o',
      'google/gemini-pro-1.5',
      'meta-llama/llama-3.1-405b-instruct', 'meta-llama/llama-3.1-70b-instruct',
      'mistralai/mixtral-8x7b-instruct',
    ],
  };

  /**
   * Detect available Ollama models by running the Python detector script.
   * Returns IPCResult with models array or an error.
   */
  const fetchOllamaModels = (): IPCResult<{ models: string[] }> => {
    const { sourcePath } = getSourceEnvPath();
    if (!sourcePath) {
      return { success: false, error: 'Auto-build source path not configured. Cannot detect Ollama models.' };
    }
    const scriptPath = path.join(sourcePath, 'ollama_model_detector.py');
    if (!existsSync(scriptPath)) {
      return { success: false, error: 'Ollama model detector script not found' };
    }
    const pythonPath = getToolPath('python');
    if (!pythonPath) {
      return { success: false, error: 'Python not found. Please install Python 3.10 or higher.' };
    }
    const output = execFileSync(pythonPath, [scriptPath, 'list-models'], {
      encoding: 'utf-8',
      timeout: 5000,
    });
    const result = JSON.parse(output);
    if (result.success && result.data?.models) {
      return { success: true, data: { models: result.data.models.map((m: { name: string }) => m.name) } };
    }
    return { success: false, error: result.error || 'Failed to detect Ollama models' };
  };

  // Handler: getAvailableModels - Fetch available models for a provider
  ipcMain.handle(
    IPC_CHANNELS.SETTINGS_GET_AVAILABLE_MODELS,
    async (_, provider: string): Promise<IPCResult<{ models: string[] }>> => {
      try {
        const staticModels = STATIC_PROVIDER_MODELS[provider];
        if (staticModels) {
          return { success: true, data: { models: staticModels } };
        }
        if (provider === 'ollama') {
          try {
            return fetchOllamaModels();
          } catch (err) {
            const message = err instanceof Error ? err.message : 'Unknown error detecting Ollama models';
            console.error('[SETTINGS_GET_AVAILABLE_MODELS] Ollama detection error:', message);
            return { success: false, error: message };
          }
        }
        return { success: false, error: `Unknown provider: ${provider}` };
      } catch (error) {
        console.error('[SETTINGS_GET_AVAILABLE_MODELS] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get available models'
        };
      }
    }
  );

  // ============================================
  // AI Provider Configuration (Backend .env sync)
  // ============================================

  /**
   * Get AI provider configuration from backend .env file
   */
  ipcMain.handle(
    IPC_CHANNELS.PROVIDER_CONFIG_GET,
    async (): Promise<IPCResult<import('../../shared/types').AIProviderConfig>> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        if (!sourcePath || !envPath) {
          return {
            success: false,
            error: 'Auto-build source path not configured. Please set it in Settings.'
          };
        }

        const config: import('../../shared/types').AIProviderConfig = {
          provider: 'claude'
        };

        if (existsSync(envPath)) {
          const content = readFileSync(envPath, 'utf-8');
          const vars = parseEnvFile(content);

          config.provider = (vars['AI_ENGINE_PROVIDER'] || 'claude') as import('../../shared/types').AIEngineProvider;
          config.anthropicApiKey = vars['ANTHROPIC_API_KEY'];
          config.claudeModel = vars['CLAUDE_MODEL'];
          config.openaiApiKey = vars['OPENAI_API_KEY'];
          config.openaiModel = vars['OPENAI_MODEL'];
          config.openaiBaseUrl = vars['OPENAI_BASE_URL'];
          config.googleApiKey = vars['GOOGLE_API_KEY'];
          config.googleModel = vars['GOOGLE_MODEL'];
          config.litellmModel = vars['LITELLM_MODEL'];
          config.litellmApiBase = vars['LITELLM_API_BASE'];
          config.litellmApiKey = vars['LITELLM_API_KEY'];
          config.openrouterApiKey = vars['OPENROUTER_API_KEY'];
          config.openrouterModel = vars['OPENROUTER_MODEL'];
          config.openrouterBaseUrl = vars['OPENROUTER_BASE_URL'];
          config.ollamaModel = vars['OLLAMA_MODEL'];
          config.ollamaBaseUrl = vars['OLLAMA_BASE_URL'];
        }

        return {
          success: true,
          data: config
        };
      } catch (error) {
        console.error('[PROVIDER_CONFIG_GET] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get provider config'
        };
      }
    }
  );

  /**
   * Update AI provider configuration in backend .env file
   */
  ipcMain.handle(
    IPC_CHANNELS.PROVIDER_CONFIG_UPDATE,
    async (_, config: Partial<import('../../shared/types').AIProviderConfig>): Promise<IPCResult> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        if (!sourcePath || !envPath) {
          return {
            success: false,
            error: 'Auto-build source path not configured. Please set it in Settings.'
          };
        }

        let existingVars: Record<string, string> = {};
        try {
          const content = readFileSync(envPath, 'utf-8');
          existingVars = parseEnvFile(content);
        } catch {
          // File doesn't exist yet, start with empty vars
        }

        if (config.provider !== undefined) existingVars['AI_ENGINE_PROVIDER'] = config.provider;
        if (config.anthropicApiKey !== undefined) existingVars['ANTHROPIC_API_KEY'] = config.anthropicApiKey;
        if (config.claudeModel !== undefined) existingVars['CLAUDE_MODEL'] = config.claudeModel;
        if (config.openaiApiKey !== undefined) existingVars['OPENAI_API_KEY'] = config.openaiApiKey;
        if (config.openaiModel !== undefined) existingVars['OPENAI_MODEL'] = config.openaiModel;
        if (config.openaiBaseUrl !== undefined) existingVars['OPENAI_BASE_URL'] = config.openaiBaseUrl;
        if (config.googleApiKey !== undefined) existingVars['GOOGLE_API_KEY'] = config.googleApiKey;
        if (config.googleModel !== undefined) existingVars['GOOGLE_MODEL'] = config.googleModel;
        if (config.litellmModel !== undefined) existingVars['LITELLM_MODEL'] = config.litellmModel;
        if (config.litellmApiBase !== undefined) existingVars['LITELLM_API_BASE'] = config.litellmApiBase;
        if (config.litellmApiKey !== undefined) existingVars['LITELLM_API_KEY'] = config.litellmApiKey;
        if (config.openrouterApiKey !== undefined) existingVars['OPENROUTER_API_KEY'] = config.openrouterApiKey;
        if (config.openrouterModel !== undefined) existingVars['OPENROUTER_MODEL'] = config.openrouterModel;
        if (config.openrouterBaseUrl !== undefined) existingVars['OPENROUTER_BASE_URL'] = config.openrouterBaseUrl;
        if (config.ollamaModel !== undefined) existingVars['OLLAMA_MODEL'] = config.ollamaModel;
        if (config.ollamaBaseUrl !== undefined) existingVars['OLLAMA_BASE_URL'] = config.ollamaBaseUrl;

        const newContent = Object.entries(existingVars)
          .map(([key, value]) => `${key}=${value}`)
          .join('\n');

        writeFileSync(envPath, newContent, 'utf-8');

        return { success: true };
      } catch (error) {
        console.error('[PROVIDER_CONFIG_UPDATE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to update provider config'
        };
      }
    }
  );

  /**
   * Validate AI provider configuration
   */
  ipcMain.handle(
    IPC_CHANNELS.PROVIDER_CONFIG_VALIDATE,
    async (): Promise<IPCResult<import('../../shared/types').ProviderConfigValidation>> => {
      try {
        const { sourcePath, envPath } = getSourceEnvPath();

        if (!sourcePath || !envPath) {
          return {
            success: false,
            error: 'Auto-build source path not configured. Please set it in Settings.'
          };
        }

        const errors: string[] = [];
        const availableProviders: import('../../shared/types').AIEngineProvider[] = [];

        if (existsSync(envPath)) {
          const content = readFileSync(envPath, 'utf-8');
          const vars = parseEnvFile(content);

          const provider = (vars['AI_ENGINE_PROVIDER'] || 'claude') as import('../../shared/types').AIEngineProvider;

          if (vars['ANTHROPIC_API_KEY']) availableProviders.push('claude');
          if (vars['OPENAI_API_KEY']) availableProviders.push('openai');
          if (vars['GOOGLE_API_KEY']) availableProviders.push('google');
          if (vars['LITELLM_MODEL']) availableProviders.push('litellm');
          if (vars['OPENROUTER_API_KEY']) availableProviders.push('openrouter');
          if (vars['OLLAMA_MODEL']) availableProviders.push('ollama');

          switch (provider) {
            case 'claude':
              if (!vars['ANTHROPIC_API_KEY']) errors.push('Claude provider requires ANTHROPIC_API_KEY environment variable');
              break;
            case 'openai':
              if (!vars['OPENAI_API_KEY']) errors.push('OpenAI provider requires OPENAI_API_KEY environment variable');
              break;
            case 'google':
              if (!vars['GOOGLE_API_KEY']) errors.push('Google provider requires GOOGLE_API_KEY environment variable');
              break;
            case 'litellm':
              if (!vars['LITELLM_MODEL']) errors.push('LiteLLM provider requires LITELLM_MODEL environment variable');
              break;
            case 'openrouter':
              if (!vars['OPENROUTER_API_KEY']) errors.push('OpenRouter provider requires OPENROUTER_API_KEY environment variable');
              break;
            case 'ollama':
              if (!vars['OLLAMA_MODEL']) errors.push('Ollama provider requires OLLAMA_MODEL environment variable');
              break;
          }
        } else {
          errors.push('.env file does not exist in backend directory');
        }

        return {
          success: true,
          data: { isValid: errors.length === 0, errors, availableProviders }
        };
      } catch (error) {
        console.error('[PROVIDER_CONFIG_VALIDATE] Error:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to validate provider config'
        };
      }
    }
  );
}
