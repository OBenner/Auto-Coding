/**
 * Platform-Specific Path Resolvers
 *
 * Handles detection of tool paths across platforms.
 * Each tool has a dedicated resolver function.
 */

import * as path from 'path';
import * as os from 'os';
import { existsSync, readdirSync } from 'fs';
import { access, constants } from 'fs/promises';
import { execFileSync, execFile } from 'child_process';
import { promisify } from 'util';
import { isWindows, isMacOS, getHomebrewPath, joinPaths, getExecutableExtension } from './index';

const execFileAsync = promisify(execFile);

/**
 * Resolve Claude CLI executable path
 *
 * Searches in platform-specific installation directories:
 * - Windows: Program Files, AppData, npm
 * - macOS: Homebrew, /usr/local/bin
 * - Linux: ~/.local/bin, /usr/bin
 */
export function getClaudeExecutablePath(): string[] {
  const homeDir = os.homedir();
  const paths: string[] = [];

  if (isWindows()) {
    // Note: path.join('C:', 'foo') produces 'C:foo' (relative to C: drive), not 'C:\foo'
    // We must use 'C:\\' or raw paths like 'C:\\Program Files' to get absolute paths
    paths.push(
      joinPaths(homeDir, 'AppData', 'Local', 'Programs', 'claude', `claude${getExecutableExtension()}`),
      joinPaths(homeDir, 'AppData', 'Roaming', 'npm', 'claude.cmd'),
      joinPaths(homeDir, '.local', 'bin', `claude${getExecutableExtension()}`),
      joinPaths('C:\\Program Files', 'Claude', `claude${getExecutableExtension()}`),
      joinPaths('C:\\Program Files (x86)', 'Claude', `claude${getExecutableExtension()}`)
    );
  } else {
    paths.push(
      joinPaths(homeDir, '.local', 'bin', 'claude'),
      joinPaths(homeDir, 'bin', 'claude')
    );

    // Add Homebrew paths on macOS
    if (isMacOS()) {
      const brewPath = getHomebrewPath();
      if (brewPath) {
        paths.push(joinPaths(brewPath, 'claude'));
      }
    }
  }

  return paths;
}

/**
 * Resolve Python executable path
 *
 * Returns command arguments as sequences so callers can pass each entry
 * directly to spawn/exec or use cmd[0] for executable lookup.
 *
 * Returns platform-specific command variations:
 * - Windows: ["py", "-3"], ["python"], ["python3"], ["py"]
 * - Unix: ["python3"], ["python"]
 */
export function getPythonCommands(): string[][] {
  if (isWindows()) {
    return [['py', '-3'], ['python'], ['python3'], ['py']];
  }
  return [['python3'], ['python']];
}

/**
 * Expand a directory pattern like "Python3*" by scanning the parent directory
 * Returns matching directory paths or empty array if none found
 */
function expandDirPattern(parentDir: string, pattern: string): string[] {
  if (!existsSync(parentDir)) {
    return [];
  }

  try {
    // Convert glob pattern to regex (only support simple * wildcard)
    const regexPattern = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$', 'i');
    const entries = readdirSync(parentDir, { withFileTypes: true });

    return entries
      .filter((entry) => entry.isDirectory() && regexPattern.test(entry.name))
      .map((entry) => joinPaths(parentDir, entry.name));
  } catch {
    return [];
  }
}

/**
 * Resolve Python installation paths
 *
 * Returns actual existing directory paths (expands glob patterns on Windows)
 */
export function getPythonPaths(): string[] {
  const homeDir = os.homedir();
  const paths: string[] = [];

  if (isWindows()) {
    // User-local Python installation
    const userPythonPath = joinPaths(homeDir, 'AppData', 'Local', 'Programs', 'Python');
    if (existsSync(userPythonPath)) {
      paths.push(userPythonPath);
    }

    // System Python installations (expand Python3* patterns)
    const programFiles = process.env.ProgramFiles || 'C:\\Program Files';
    const programFilesX86 = process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)';

    paths.push(...expandDirPattern(programFiles, 'Python3*'));
    paths.push(...expandDirPattern(programFilesX86, 'Python3*'));
  } else if (isMacOS()) {
    const brewPath = getHomebrewPath();
    if (brewPath) {
      paths.push(brewPath);
    }
  }

  return paths;
}

/**
 * Resolve Git executable path
 */
export function getGitExecutablePath(): string {
  if (isWindows()) {
    // Git for Windows installs to standard locations
    const candidates = [
      joinPaths('C:\\Program Files', 'Git', 'bin', 'git.exe'),
      joinPaths('C:\\Program Files (x86)', 'Git', 'bin', 'git.exe'),
      joinPaths(os.homedir(), 'AppData', 'Local', 'Programs', 'Git', 'bin', 'git.exe')
    ];

    for (const candidate of candidates) {
      if (existsSync(candidate)) {
        return candidate;
      }
    }
  }

  return 'git';
}

/**
 * Resolve Node.js executable path
 */
export function getNodeExecutablePath(): string {
  if (isWindows()) {
    return 'node.exe';
  }
  return 'node';
}

/**
 * Resolve npm executable path
 */
export function getNpmExecutablePath(): string {
  if (isWindows()) {
    return 'npm.cmd';
  }
  return 'npm';
}

/**
 * Get all Windows shell paths for terminal selection
 *
 * Returns a map of shell types to their possible installation paths.
 * Only applies to Windows; returns empty object for other platforms.
 */
export function getWindowsShellPaths(): Record<string, string[]> {
  if (!isWindows()) {
    return {};
  }

  const systemRoot = process.env.SystemRoot || 'C:\\Windows';

  // Note: path.join('C:', 'foo') produces 'C:foo' (relative to C: drive), not 'C:\foo'
  // We must use 'C:\\' or raw paths like 'C:\\Program Files' to get absolute paths
  return {
    powershell: [
      path.join('C:\\Program Files', 'PowerShell', '7', 'pwsh.exe'),
      path.join(systemRoot, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
    ],
    windowsterminal: [
      path.join('C:\\Program Files', 'WindowsApps', 'Microsoft.WindowsTerminal_*', 'WindowsTerminal.exe')
    ],
    cmd: [
      path.join(systemRoot, 'System32', 'cmd.exe')
    ],
    gitbash: [
      path.join('C:\\Program Files', 'Git', 'bin', 'bash.exe'),
      path.join('C:\\Program Files (x86)', 'Git', 'bin', 'bash.exe')
    ],
    cygwin: [
      path.join('C:\\cygwin64', 'bin', 'bash.exe')
    ],
    msys2: [
      path.join('C:\\msys64', 'usr', 'bin', 'bash.exe')
    ],
    wsl: [
      path.join(systemRoot, 'System32', 'wsl.exe')
    ]
  };
}

/**
 * Expand Windows environment variables in a path
 *
 * Replaces patterns like %PROGRAMFILES% with actual values.
 * Only applies to Windows; returns original path for other platforms.
 */
export function expandWindowsEnvVars(pathPattern: string): string {
  if (!isWindows()) {
    return pathPattern;
  }

  const homeDir = os.homedir();
  const envVars: Record<string, string | undefined> = {
    '%PROGRAMFILES%': process.env.ProgramFiles || 'C:\\Program Files',
    '%PROGRAMFILES(X86)%': process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)',
    '%LOCALAPPDATA%': process.env.LOCALAPPDATA || path.join(homeDir, 'AppData', 'Local'),
    '%APPDATA%': process.env.APPDATA || path.join(homeDir, 'AppData', 'Roaming'),
    '%USERPROFILE%': process.env.USERPROFILE || homeDir,
    '%SYSTEMROOT%': process.env.SystemRoot || 'C:\\Windows',
    '%TEMP%': process.env.TEMP || process.env.TMP || path.join(homeDir, 'AppData', 'Local', 'Temp'),
    '%TMP%': process.env.TMP || process.env.TEMP || path.join(homeDir, 'AppData', 'Local', 'Temp')
  };

  let expanded = pathPattern;
  for (const [pattern, value] of Object.entries(envVars)) {
    // Only replace if we have a valid value (skip replacement if empty)
    if (value) {
      expanded = expanded.replace(new RegExp(pattern, 'gi'), value);
    }
  }

  return expanded;
}

/**
 * Resolve Ollama executable paths
 *
 * Returns platform-specific paths where Ollama may be installed:
 * - Windows: LocalAppData, Program Files
 * - macOS: Homebrew paths, /usr/local/bin
 * - Linux: /usr/local/bin, /usr/bin, ~/.local/bin
 */
export function getOllamaExecutablePaths(): string[] {
  const homeDir = os.homedir();
  const paths: string[] = [];

  if (isWindows()) {
    const localAppData = process.env.LOCALAPPDATA || joinPaths(homeDir, 'AppData', 'Local');
    paths.push(
      joinPaths(localAppData, 'Programs', 'Ollama', 'ollama.exe'),
      joinPaths(localAppData, 'Ollama', 'ollama.exe'),
      joinPaths('C:\\Program Files', 'Ollama', 'ollama.exe'),
      joinPaths('C:\\Program Files (x86)', 'Ollama', 'ollama.exe')
    );
  } else if (isMacOS()) {
    paths.push(
      '/usr/local/bin/ollama',
      '/opt/homebrew/bin/ollama',
      joinPaths(homeDir, '.local', 'bin', 'ollama')
    );
  } else {
    // Linux
    paths.push(
      '/usr/local/bin/ollama',
      '/usr/bin/ollama',
      joinPaths(homeDir, '.local', 'bin', 'ollama')
    );
  }

  return paths;
}

/**
 * Get the platform-specific install command for Ollama
 *
 * Windows: Uses winget (Windows Package Manager)
 * macOS: Uses Homebrew
 * Linux: Uses official install script
 */
export function getOllamaInstallCommand(): string {
  if (isWindows()) {
    return 'winget install --id Ollama.Ollama --accept-source-agreements';
  } else if (isMacOS()) {
    return 'brew install ollama';
  } else {
    return 'curl -fsSL https://ollama.com/install.sh | sh';
  }
}

/**
 * Get the command to find executables in PATH
 *
 * Windows: where.exe
 * Unix: which
 */
export function getWhichCommand(): string {
  return isWindows() ? 'where.exe' : 'which';
}

/**
 * Get Windows-specific installation paths for a tool
 *
 * @param toolName - Name of the tool (e.g., 'claude', 'python')
 * @param subPath - Optional subdirectory within Program Files
 */
export function getWindowsToolPath(toolName: string, subPath?: string): string[] {
  if (!isWindows()) {
    return [];
  }

  const homeDir = os.homedir();
  const programFiles = process.env.ProgramFiles || 'C:\\Program Files';
  const programFilesX86 = process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)';
  const appData = process.env.LOCALAPPDATA || path.join(homeDir, 'AppData', 'Local');

  const paths: string[] = [];

  // Program Files locations
  if (subPath) {
    paths.push(
      path.join(programFiles, subPath),
      path.join(programFilesX86, subPath)
    );
  } else {
    paths.push(
      path.join(programFiles, toolName),
      path.join(programFilesX86, toolName)
    );
  }

  // AppData location
  paths.push(path.join(appData, toolName));

  // Roaming AppData (for npm)
  const roamingAppData = process.env.APPDATA || path.join(homeDir, 'AppData', 'Roaming');
  paths.push(path.join(roamingAppData, 'npm'));

  return paths;
}

/**
 * Windows Tool Paths Configuration
 *
 * Defines search patterns for Windows executable detection.
 * Used by getWindowsExecutablePaths() for systematic tool discovery.
 */
export interface WindowsToolPaths {
  toolName: string;
  executable: string;
  patterns: string[];
}

/**
 * Git for Windows standard installation patterns
 */
export const WINDOWS_GIT_PATHS: WindowsToolPaths = {
  toolName: 'Git',
  executable: 'git.exe',
  patterns: [
    '%PROGRAMFILES%\\Git\\cmd',
    '%PROGRAMFILES(X86)%\\Git\\cmd',
    '%LOCALAPPDATA%\\Programs\\Git\\cmd',
    '%USERPROFILE%\\scoop\\apps\\git\\current\\cmd',
    '%PROGRAMFILES%\\Git\\bin',
    '%PROGRAMFILES(X86)%\\Git\\bin',
    '%PROGRAMFILES%\\Git\\mingw64\\bin',
  ],
};

/**
 * Validate path for security
 *
 * Rejects paths containing shell metacharacters, environment variables,
 * or directory traversal patterns that could be exploited.
 *
 * @param pathStr - Path to validate
 * @returns true if path is safe, false otherwise
 */
export function isSecurePath(pathStr: string): boolean {
  const dangerousPatterns = [
    /[;&|`${}[\]<>!"^]/,  // Shell metacharacters (parentheses removed - safe when quoted)
    /%[^%]+%/,              // Windows environment variable expansion (e.g., %PATH%)
    /\.\.\//,               // Unix directory traversal
    /\.\.\\/,               // Windows directory traversal
    /[\r\n]/,               // Newlines (command injection)
  ];

  for (const pattern of dangerousPatterns) {
    if (pattern.test(pathStr)) {
      return false;
    }
  }

  return true;
}

/**
 * Expand Windows environment variables in a path pattern
 *
 * Similar to expandWindowsEnvVars() but returns null if expansion fails,
 * making it suitable for validation scenarios.
 *
 * @param pathPattern - Path with %VAR% placeholders
 * @returns Expanded path or null if variables cannot be resolved
 */
export function expandWindowsPath(pathPattern: string): string | null {
  const envVars: Record<string, string | undefined> = {
    '%PROGRAMFILES%': process.env.ProgramFiles || 'C:\\Program Files',
    '%PROGRAMFILES(X86)%': process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)',
    '%LOCALAPPDATA%': process.env.LOCALAPPDATA,
    '%APPDATA%': process.env.APPDATA,
    '%USERPROFILE%': process.env.USERPROFILE || os.homedir(),
  };

  let expandedPath = pathPattern;

  for (const [placeholder, value] of Object.entries(envVars)) {
    if (expandedPath.includes(placeholder)) {
      if (!value) {
        return null;
      }
      expandedPath = expandedPath.replace(placeholder, value);
    }
  }

  // Verify no unexpanded placeholders remain (indicates unknown variable)
  if (/%[^%]+%/.test(expandedPath)) {
    return null;
  }

  // Normalize the path (resolve double backslashes, etc.)
  return path.normalize(expandedPath);
}

/**
 * Get Windows executable paths from pattern-based configuration
 *
 * Searches for executables in Windows-specific installation directories
 * by expanding environment variable patterns and validating paths.
 *
 * @param toolPaths - Tool configuration with search patterns
 * @param logPrefix - Prefix for console logging
 * @returns Array of valid executable paths found
 */
export function getWindowsExecutablePaths(
  toolPaths: WindowsToolPaths,
  logPrefix: string = '[Windows Paths]'
): string[] {
  // Only run on Windows
  if (!isWindows()) {
    return [];
  }

  const validPaths: string[] = [];

  for (const pattern of toolPaths.patterns) {
    const expandedDir = expandWindowsPath(pattern);

    if (!expandedDir) {
      continue;
    }

    const fullPath = path.join(expandedDir, toolPaths.executable);

    // Security validation - reject potentially dangerous paths
    if (!isSecurePath(fullPath)) {
      continue;
    }

    if (existsSync(fullPath)) {
      validPaths.push(fullPath);
    }
  }

  return validPaths;
}

/**
 * Async version of getWindowsExecutablePaths
 *
 * Use this in async contexts to avoid blocking the main process.
 *
 * @param toolPaths - Tool configuration with search patterns
 * @param logPrefix - Prefix for console logging
 * @returns Promise resolving to array of valid executable paths
 */
export async function getWindowsExecutablePathsAsync(
  toolPaths: WindowsToolPaths,
  logPrefix: string = '[Windows Paths]'
): Promise<string[]> {
  // Only run on Windows
  if (!isWindows()) {
    return [];
  }

  const validPaths: string[] = [];

  for (const pattern of toolPaths.patterns) {
    const expandedDir = expandWindowsPath(pattern);

    if (!expandedDir) {
      continue;
    }

    const fullPath = path.join(expandedDir, toolPaths.executable);

    // Security validation - reject potentially dangerous paths
    if (!isSecurePath(fullPath)) {
      continue;
    }

    try {
      await access(fullPath, constants.F_OK);
      validPaths.push(fullPath);
    } catch {
      // File doesn't exist, skip
    }
  }

  return validPaths;
}

/**
 * Find a Windows executable using the `where` command
 *
 * This is the most reliable method as it searches:
 * - All directories in PATH
 * - App Paths registry entries
 * - Current directory
 *
 * Works regardless of where the tool is installed (custom paths, different drives, etc.)
 *
 * @param executable - The executable name (e.g., 'git', 'gh', 'python')
 * @param logPrefix - Prefix for console logging
 * @returns The full path to the executable, or null if not found
 */
export function findWindowsExecutableViaWhere(
  executable: string,
  logPrefix: string = '[Windows Where]'
): string | null {
  if (!isWindows()) {
    return null;
  }

  // Security: Only allow simple executable names (alphanumeric, dash, underscore, dot)
  if (!/^[\w.-]+$/.test(executable)) {
    return null;
  }

  try {
    // Use 'where' command to find the executable
    // where.exe is a built-in Windows command that finds executables
    const result = execFileSync('where.exe', [executable], {
      encoding: 'utf-8',
      timeout: 5000,
      windowsHide: true,
    }).trim();

    // 'where' returns multiple paths separated by newlines if found in multiple locations
    // Prefer paths with .cmd or .exe extensions (executable files)
    const paths = result.split(/\r?\n/).filter(p => p.trim());

    if (paths.length > 0) {
      // Prefer .cmd, .bat, or .exe extensions, otherwise take first path
      const foundPath = (paths.find(p => /\.(cmd|bat|exe)$/i.test(p)) || paths[0]).trim();

      // Validate the path exists and is secure
      if (existsSync(foundPath) && isSecurePath(foundPath)) {
        return foundPath;
      }
    }

    return null;
  } catch {
    // 'where' returns exit code 1 if not found, which throws an error
    return null;
  }
}

/**
 * Async version of findWindowsExecutableViaWhere
 *
 * Use this in async contexts to avoid blocking the main process.
 *
 * Find a Windows executable using the `where` command.
 * This is the most reliable method as it searches:
 * - All directories in PATH
 * - App Paths registry entries
 * - Current directory
 *
 * Works regardless of where the tool is installed (custom paths, different drives, etc.)
 *
 * @param executable - The executable name (e.g., 'git', 'gh', 'python')
 * @param logPrefix - Prefix for console logging
 * @returns Promise resolving to the full path or null if not found
 */
export async function findWindowsExecutableViaWhereAsync(
  executable: string,
  logPrefix: string = '[Windows Where]'
): Promise<string | null> {
  if (!isWindows()) {
    return null;
  }

  // Security: Only allow simple executable names (alphanumeric, dash, underscore, dot)
  if (!/^[\w.-]+$/.test(executable)) {
    return null;
  }

  try {
    // Use 'where' command to find the executable
    // where.exe is a built-in Windows command that finds executables
    const { stdout } = await execFileAsync('where.exe', [executable], {
      encoding: 'utf-8',
      timeout: 5000,
      windowsHide: true,
    });

    // 'where' returns multiple paths separated by newlines if found in multiple locations
    // Prefer paths with .cmd, .bat, or .exe extensions (executable files)
    const paths = stdout.trim().split(/\r?\n/).filter(p => p.trim());

    if (paths.length > 0) {
      // Prefer .cmd, .bat, or .exe extensions, otherwise take first path
      const foundPath = (paths.find(p => /\.(cmd|bat|exe)$/i.test(p)) || paths[0]).trim();

      // Validate the path exists and is secure
      try {
        await access(foundPath, constants.F_OK);
        if (isSecurePath(foundPath)) {
          return foundPath;
        }
      } catch {
        // Path doesn't exist
      }
    }

    return null;
  } catch {
    // 'where' returns exit code 1 if not found, which throws an error
    return null;
  }
}
