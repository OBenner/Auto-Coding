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
 * Validation result for a Python installation.
 */
export interface PythonValidation {
  valid: boolean;
  version?: string;
  message: string;
}

/**
 * Find the first valid Homebrew Python installation.
 * Checks common Homebrew paths for Python 3, including versioned installations.
 * Prioritizes newer Python versions (3.14, 3.13, 3.12, 3.11, 3.10).
 *
 * Note: This list should be updated when new Python versions are released.
 * Check for specific versions first to ensure we find the latest available version.
 *
 * @param validateFn - Function to validate a Python path and return validation result
 * @param logPrefix - Prefix for log messages (e.g., '[Python]', '[CLI Tools]')
 * @returns The path to Homebrew Python, or null if not found
 */
export function findHomebrewPython(
  validateFn: (pythonPath: string) => PythonValidation,
  logPrefix: string
): string | null {
  const homebrewDirs = [
    '/opt/homebrew/bin',  // Apple Silicon (M1/M2/M3)
    '/usr/local/bin'      // Intel Mac
  ];

  // Check for specific Python versions first (newest to oldest), then fall back to generic python3.
  // This ensures we find the latest available version that meets our requirements.
  const pythonNames = [
    'python3.14',
    'python3.13',
    'python3.12',
    'python3.11',
    'python3.10',
    'python3',
  ];

  for (const dir of homebrewDirs) {
    for (const name of pythonNames) {
      const pythonPath = path.join(dir, name);
      if (existsSync(pythonPath)) {
        try {
          // Validate that this Python meets version requirements
          const validation = validateFn(pythonPath);
          if (validation.valid) {
            console.log(`${logPrefix} Found valid Homebrew Python: ${pythonPath} (${validation.version})`);
            return pythonPath;
          } else {
            console.warn(`${logPrefix} ${pythonPath} rejected: ${validation.message}`);
          }
        } catch (error) {
          // Version check failed (e.g., timeout, permission issue), try next candidate
          console.warn(`${logPrefix} Failed to validate ${pythonPath}: ${error}`);
        }
      }
    }
  }

  console.log(`${logPrefix} No valid Homebrew Python found in ${homebrewDirs.join(', ')}`);
  return null;
}

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
 * Configuration for Claude CLI detection paths
 */
export interface ClaudeDetectionPaths {
  /** Homebrew paths for macOS (Apple Silicon and Intel) */
  homebrewPaths: string[];
  /** Platform-specific standard installation paths */
  platformPaths: string[];
  /** Path to NVM versions directory for Node.js-installed Claude */
  nvmVersionsDir: string;
}

/**
 * Get all candidate paths for Claude CLI detection.
 *
 * Returns platform-specific paths where Claude CLI might be installed.
 * This pure function consolidates path configuration used by both sync
 * and async detection methods.
 *
 * Note: This is the single source of truth for CLI detection paths.
 * The Python backend relies on the Claude Agent SDK's bundled CLI,
 * so it no longer needs its own path detection logic.
 *
 * @param homeDir - User's home directory (from os.homedir())
 * @returns Object containing homebrew, platform, and NVM paths
 *
 * @example
 * const paths = getClaudeDetectionPaths('/Users/john');
 * // On macOS: { homebrewPaths: ['/opt/homebrew/bin/claude', ...], ... }
 */
export function getClaudeDetectionPaths(homeDir: string): ClaudeDetectionPaths {
  const homebrewPaths = [
    '/opt/homebrew/bin/claude', // Apple Silicon
    '/usr/local/bin/claude',    // Intel Mac
  ];

  const platformPaths = isWindows()
    ? [
        joinPaths(homeDir, 'AppData', 'Local', 'Programs', 'claude', `claude${getExecutableExtension()}`),
        joinPaths(homeDir, 'AppData', 'Roaming', 'npm', 'claude.cmd'),
        joinPaths(homeDir, '.local', 'bin', `claude${getExecutableExtension()}`),
        'C:\\Program Files\\Claude\\claude.exe',
        'C:\\Program Files (x86)\\Claude\\claude.exe',
      ]
    : [
        joinPaths(homeDir, '.local', 'bin', 'claude'),
        joinPaths(homeDir, 'bin', 'claude'),
      ];

  const nvmVersionsDir = joinPaths(homeDir, '.nvm', 'versions', 'node');

  return { homebrewPaths, platformPaths, nvmVersionsDir };
}

/**
 * Sort NVM version directories by semantic version (newest first).
 *
 * Filters entries to only include directories starting with 'v' (version directories)
 * and sorts them in descending order so the newest Node.js version is checked first.
 *
 * @param entries - Directory entries from readdir with { name, isDirectory() }
 * @returns Array of version directory names sorted newest first
 *
 * @example
 * const entries = [
 *   { name: 'v18.0.0', isDirectory: () => true },
 *   { name: 'v20.0.0', isDirectory: () => true },
 *   { name: '.DS_Store', isDirectory: () => false },
 * ];
 * sortNvmVersionDirs(entries); // ['v20.0.0', 'v18.0.0']
 */
export function sortNvmVersionDirs(
  entries: Array<{ name: string; isDirectory(): boolean }>
): string[] {
  // Regex to match valid semver directories: v20.0.0, v18.17.1, etc.
  // This prevents NaN from malformed versions (e.g., v20.abc.1) breaking sort
  const semverRegex = /^v\d+\.\d+\.\d+$/;

  return entries
    .filter((entry) => entry.isDirectory() && semverRegex.test(entry.name))
    .sort((a, b) => {
      // Parse version numbers: v20.0.0 -> [20, 0, 0]
      const vA = a.name.slice(1).split('.').map(Number);
      const vB = b.name.slice(1).split('.').map(Number);
      // Compare major, minor, patch in order (descending)
      for (let i = 0; i < 3; i++) {
        const diff = (vB[i] ?? 0) - (vA[i] ?? 0);
        if (diff !== 0) return diff;
      }
      return 0;
    })
    .map((entry) => entry.name);
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
    gitbashLauncher: [
      path.join('C:\\Program Files', 'Git', 'git-bash.exe'),
      path.join('C:\\Program Files (x86)', 'Git', 'git-bash.exe')
    ],
    conemu: [
      path.join('C:\\Program Files', 'ConEmu', 'ConEmu64.exe'),
      path.join('C:\\Program Files (x86)', 'ConEmu', 'ConEmu.exe')
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
 * Get PowerShell executable path for Windows
 *
 * Searches for PowerShell installations in order of preference:
 * 1. PowerShell 7+ (pwsh.exe) - Modern cross-platform PowerShell
 * 2. Windows PowerShell (powershell.exe) - Built-in legacy version
 *
 * @returns Array of candidate PowerShell paths to check
 */
export function getPowerShellExecutablePath(): string[] {
  if (!isWindows()) {
    return [];
  }

  const homeDir = os.homedir();
  const programFiles = process.env.ProgramFiles || 'C:\\Program Files';
  const systemRoot = process.env.SystemRoot || 'C:\\Windows';

  return [
    path.join(programFiles, 'PowerShell', '7', 'pwsh.exe'),
    path.join(homeDir, 'AppData', 'Local', 'Microsoft', 'WindowsApps', 'pwsh.exe'),
    path.join(systemRoot, 'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe'),
  ];
}

/**
 * Editor/IDE configuration type for detection
 */
export interface EditorConfig {
  name: string;
  paths: Record<string, string[]>;
  commands: Record<string, string>;
}

/**
 * Get editor and IDE detection configuration
 *
 * Returns comprehensive path mappings for 40+ IDEs and text editors across
 * all platforms. This centralizes all hardcoded editor paths into a single
 * source of truth for the platform abstraction layer.
 *
 * @returns Record mapping editor IDs to their detection configuration
 */
export function getEditorDetectionConfig(): Record<string, EditorConfig> {
  return {
    // Microsoft/VS Code Ecosystem
    vscode: {
      name: 'Visual Studio Code',
      paths: {
        darwin: ['/Applications/Visual Studio Code.app'],
        win32: [
          'C:\\Program Files\\Microsoft VS Code\\Code.exe',
          'C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe'
        ],
        linux: ['/usr/share/code', '/snap/bin/code', '/usr/bin/code']
      },
      commands: { darwin: 'code', win32: 'code.cmd', linux: 'code' }
    },
    visualstudio: {
      name: 'Visual Studio',
      paths: {
        darwin: [],
        win32: [
          'C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\Common7\\IDE\\devenv.exe',
          'C:\\Program Files\\Microsoft Visual Studio\\2022\\Professional\\Common7\\IDE\\devenv.exe',
          'C:\\Program Files\\Microsoft Visual Studio\\2022\\Enterprise\\Common7\\IDE\\devenv.exe'
        ],
        linux: []
      },
      commands: { darwin: '', win32: 'devenv', linux: '' }
    },
    vscodium: {
      name: 'VSCodium',
      paths: {
        darwin: ['/Applications/VSCodium.app'],
        win32: ['C:\\Program Files\\VSCodium\\VSCodium.exe', 'C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\VSCodium\\VSCodium.exe'],
        linux: ['/usr/bin/codium', '/snap/bin/codium']
      },
      commands: { darwin: 'codium', win32: 'codium', linux: 'codium' }
    },
    // AI-Powered Editors
    cursor: {
      name: 'Cursor',
      paths: {
        darwin: ['/Applications/Cursor.app'],
        win32: ['C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\cursor\\Cursor.exe'],
        linux: ['/usr/bin/cursor', '/opt/Cursor/cursor']
      },
      commands: { darwin: 'cursor', win32: 'cursor.cmd', linux: 'cursor' }
    },
    windsurf: {
      name: 'Windsurf',
      paths: {
        darwin: ['/Applications/Windsurf.app'],
        win32: ['C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Windsurf\\Windsurf.exe'],
        linux: ['/usr/bin/windsurf', '/opt/Windsurf/windsurf']
      },
      commands: { darwin: 'windsurf', win32: 'windsurf.cmd', linux: 'windsurf' }
    },
    zed: {
      name: 'Zed',
      paths: {
        darwin: ['/Applications/Zed.app'],
        win32: [],
        linux: ['/usr/bin/zed', '~/.local/bin/zed']
      },
      commands: { darwin: 'zed', win32: '', linux: 'zed' }
    },
    void: {
      name: 'Void',
      paths: {
        darwin: ['/Applications/Void.app'],
        win32: ['C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Void\\Void.exe'],
        linux: ['/usr/bin/void']
      },
      commands: { darwin: 'void', win32: 'void', linux: 'void' }
    },
    // JetBrains IDEs
    intellij: {
      name: 'IntelliJ IDEA',
      paths: {
        darwin: ['/Applications/IntelliJ IDEA.app', '/Applications/IntelliJ IDEA CE.app'],
        win32: ['C:\\Program Files\\JetBrains\\IntelliJ IDEA*\\bin\\idea64.exe'],
        linux: ['/usr/bin/idea', '/snap/bin/intellij-idea-ultimate', '/snap/bin/intellij-idea-community']
      },
      commands: { darwin: 'idea', win32: 'idea64.exe', linux: 'idea' }
    },
    pycharm: {
      name: 'PyCharm',
      paths: {
        darwin: ['/Applications/PyCharm.app', '/Applications/PyCharm CE.app'],
        win32: ['C:\\Program Files\\JetBrains\\PyCharm*\\bin\\pycharm64.exe'],
        linux: ['/usr/bin/pycharm', '/snap/bin/pycharm-professional', '/snap/bin/pycharm-community']
      },
      commands: { darwin: 'pycharm', win32: 'pycharm64.exe', linux: 'pycharm' }
    },
    webstorm: {
      name: 'WebStorm',
      paths: {
        darwin: ['/Applications/WebStorm.app'],
        win32: ['C:\\Program Files\\JetBrains\\WebStorm*\\bin\\webstorm64.exe'],
        linux: ['/usr/bin/webstorm', '/snap/bin/webstorm']
      },
      commands: { darwin: 'webstorm', win32: 'webstorm64.exe', linux: 'webstorm' }
    },
    phpstorm: {
      name: 'PhpStorm',
      paths: {
        darwin: ['/Applications/PhpStorm.app'],
        win32: ['C:\\Program Files\\JetBrains\\PhpStorm*\\bin\\phpstorm64.exe'],
        linux: ['/usr/bin/phpstorm', '/snap/bin/phpstorm']
      },
      commands: { darwin: 'phpstorm', win32: 'phpstorm64.exe', linux: 'phpstorm' }
    },
    rubymine: {
      name: 'RubyMine',
      paths: {
        darwin: ['/Applications/RubyMine.app'],
        win32: ['C:\\Program Files\\JetBrains\\RubyMine*\\bin\\rubymine64.exe'],
        linux: ['/usr/bin/rubymine', '/snap/bin/rubymine']
      },
      commands: { darwin: 'rubymine', win32: 'rubymine64.exe', linux: 'rubymine' }
    },
    goland: {
      name: 'GoLand',
      paths: {
        darwin: ['/Applications/GoLand.app'],
        win32: ['C:\\Program Files\\JetBrains\\GoLand*\\bin\\goland64.exe'],
        linux: ['/usr/bin/goland', '/snap/bin/goland']
      },
      commands: { darwin: 'goland', win32: 'goland64.exe', linux: 'goland' }
    },
    clion: {
      name: 'CLion',
      paths: {
        darwin: ['/Applications/CLion.app'],
        win32: ['C:\\Program Files\\JetBrains\\CLion*\\bin\\clion64.exe'],
        linux: ['/usr/bin/clion', '/snap/bin/clion']
      },
      commands: { darwin: 'clion', win32: 'clion64.exe', linux: 'clion' }
    },
    rider: {
      name: 'Rider',
      paths: {
        darwin: ['/Applications/Rider.app'],
        win32: ['C:\\Program Files\\JetBrains\\Rider*\\bin\\rider64.exe'],
        linux: ['/usr/bin/rider', '/snap/bin/rider']
      },
      commands: { darwin: 'rider', win32: 'rider64.exe', linux: 'rider' }
    },
    datagrip: {
      name: 'DataGrip',
      paths: {
        darwin: ['/Applications/DataGrip.app'],
        win32: ['C:\\Program Files\\JetBrains\\DataGrip*\\bin\\datagrip64.exe'],
        linux: ['/usr/bin/datagrip', '/snap/bin/datagrip']
      },
      commands: { darwin: 'datagrip', win32: 'datagrip64.exe', linux: 'datagrip' }
    },
    fleet: {
      name: 'Fleet',
      paths: {
        darwin: ['/Applications/Fleet.app'],
        win32: ['C:\\Users\\%USERNAME%\\AppData\\Local\\JetBrains\\Toolbox\\apps\\Fleet\\ch-0\\*\\Fleet.exe'],
        linux: ['~/.local/share/JetBrains/Toolbox/apps/Fleet/ch-0/*/fleet']
      },
      commands: { darwin: 'fleet', win32: 'fleet', linux: 'fleet' }
    },
    androidstudio: {
      name: 'Android Studio',
      paths: {
        darwin: ['/Applications/Android Studio.app'],
        win32: ['C:\\Program Files\\Android\\Android Studio\\bin\\studio64.exe'],
        linux: ['/usr/bin/android-studio', '/snap/bin/android-studio', '/opt/android-studio/bin/studio.sh']
      },
      commands: { darwin: 'studio', win32: 'studio64.exe', linux: 'android-studio' }
    },
    rustrover: {
      name: 'RustRover',
      paths: {
        darwin: ['/Applications/RustRover.app'],
        win32: ['C:\\Program Files\\JetBrains\\RustRover*\\bin\\rustrover64.exe'],
        linux: ['/usr/bin/rustrover', '/snap/bin/rustrover']
      },
      commands: { darwin: 'rustrover', win32: 'rustrover64.exe', linux: 'rustrover' }
    },
    // Classic Text Editors
    sublime: {
      name: 'Sublime Text',
      paths: {
        darwin: ['/Applications/Sublime Text.app'],
        win32: ['C:\\Program Files\\Sublime Text\\subl.exe', 'C:\\Program Files\\Sublime Text 3\\subl.exe'],
        linux: ['/usr/bin/subl', '/snap/bin/subl']
      },
      commands: { darwin: 'subl', win32: 'subl.exe', linux: 'subl' }
    },
    vim: {
      name: 'Vim',
      paths: {
        darwin: ['/usr/bin/vim'],
        win32: ['C:\\Program Files\\Vim\\vim*\\vim.exe'],
        linux: ['/usr/bin/vim']
      },
      commands: { darwin: 'vim', win32: 'vim', linux: 'vim' }
    },
    neovim: {
      name: 'Neovim',
      paths: {
        darwin: ['/usr/local/bin/nvim', '/opt/homebrew/bin/nvim'],
        win32: ['C:\\Program Files\\Neovim\\bin\\nvim.exe'],
        linux: ['/usr/bin/nvim', '/snap/bin/nvim']
      },
      commands: { darwin: 'nvim', win32: 'nvim', linux: 'nvim' }
    },
    emacs: {
      name: 'Emacs',
      paths: {
        darwin: ['/Applications/Emacs.app', '/usr/local/bin/emacs', '/opt/homebrew/bin/emacs'],
        win32: ['C:\\Program Files\\Emacs\\bin\\emacs.exe'],
        linux: ['/usr/bin/emacs', '/snap/bin/emacs']
      },
      commands: { darwin: 'emacs', win32: 'emacs', linux: 'emacs' }
    },
    nano: {
      name: 'GNU Nano',
      paths: {
        darwin: ['/usr/bin/nano'],
        win32: [],
        linux: ['/usr/bin/nano']
      },
      commands: { darwin: 'nano', win32: '', linux: 'nano' }
    },
    helix: {
      name: 'Helix',
      paths: {
        darwin: ['/opt/homebrew/bin/hx', '/usr/local/bin/hx'],
        win32: ['C:\\Program Files\\Helix\\hx.exe'],
        linux: ['/usr/bin/hx', '~/.cargo/bin/hx']
      },
      commands: { darwin: 'hx', win32: 'hx', linux: 'hx' }
    },
    // Platform-Specific IDEs
    xcode: {
      name: 'Xcode',
      paths: {
        darwin: ['/Applications/Xcode.app'],
        win32: [],
        linux: []
      },
      commands: { darwin: 'xcode', win32: '', linux: '' }
    },
    eclipse: {
      name: 'Eclipse',
      paths: {
        darwin: ['/Applications/Eclipse.app'],
        win32: ['C:\\eclipse\\eclipse.exe', 'C:\\Program Files\\Eclipse\\eclipse.exe'],
        linux: ['/usr/bin/eclipse', '/snap/bin/eclipse']
      },
      commands: { darwin: 'eclipse', win32: 'eclipse', linux: 'eclipse' }
    },
    netbeans: {
      name: 'NetBeans',
      paths: {
        darwin: ['/Applications/NetBeans.app', '/Applications/Apache NetBeans.app'],
        win32: ['C:\\Program Files\\NetBeans*\\bin\\netbeans64.exe'],
        linux: ['/usr/bin/netbeans', '/snap/bin/netbeans']
      },
      commands: { darwin: 'netbeans', win32: 'netbeans64.exe', linux: 'netbeans' }
    },
    // macOS Editors
    nova: {
      name: 'Nova',
      paths: {
        darwin: ['/Applications/Nova.app'],
        win32: [],
        linux: []
      },
      commands: { darwin: 'nova', win32: '', linux: '' }
    },
    bbedit: {
      name: 'BBEdit',
      paths: {
        darwin: ['/Applications/BBEdit.app'],
        win32: [],
        linux: []
      },
      commands: { darwin: 'bbedit', win32: '', linux: '' }
    },
    textmate: {
      name: 'TextMate',
      paths: {
        darwin: ['/Applications/TextMate.app'],
        win32: [],
        linux: []
      },
      commands: { darwin: 'mate', win32: '', linux: '' }
    },
    // Windows Editors
    notepadpp: {
      name: 'Notepad++',
      paths: {
        darwin: [],
        win32: ['C:\\Program Files\\Notepad++\\notepad++.exe', 'C:\\Program Files (x86)\\Notepad++\\notepad++.exe'],
        linux: []
      },
      commands: { darwin: '', win32: 'notepad++', linux: '' }
    },
    // Linux Editors
    kate: {
      name: 'Kate',
      paths: {
        darwin: [],
        win32: [],
        linux: ['/usr/bin/kate', '/snap/bin/kate']
      },
      commands: { darwin: '', win32: '', linux: 'kate' }
    },
    gedit: {
      name: 'gedit',
      paths: {
        darwin: [],
        win32: [],
        linux: ['/usr/bin/gedit', '/snap/bin/gedit']
      },
      commands: { darwin: '', win32: '', linux: 'gedit' }
    },
    geany: {
      name: 'Geany',
      paths: {
        darwin: [],
        win32: [],
        linux: ['/usr/bin/geany']
      },
      commands: { darwin: '', win32: '', linux: 'geany' }
    },
    lapce: {
      name: 'Lapce',
      paths: {
        darwin: ['/Applications/Lapce.app'],
        win32: ['C:\\Users\\%USERNAME%\\AppData\\Local\\lapce\\Lapce.exe'],
        linux: ['/usr/bin/lapce', '~/.cargo/bin/lapce']
      },
      commands: { darwin: 'lapce', win32: 'lapce', linux: 'lapce' }
    },
    custom: {
      name: 'Custom IDE',
      paths: { darwin: [], win32: [], linux: [] },
      commands: { darwin: '', win32: '', linux: '' }
    }
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
 * Validate path for security (canonical implementation)
 *
 * Rejects paths containing shell metacharacters, environment variables,
 * directory traversal patterns, or control characters that could be exploited.
 *
 * @param pathStr - Path to validate
 * @returns true if path is safe, false otherwise
 */
export function isSecurePath(pathStr: string): boolean {
  // Reject empty or whitespace-only strings
  if (!pathStr || !pathStr.trim()) return false;

  const dangerousPatterns = [
    /[;&|`${}[\]<>!"^]/,   // Shell metacharacters (parentheses removed - safe when quoted)
    /%[^%]+%/,              // Windows environment variable expansion (e.g., %PATH%)
    /\.\.\//,               // Unix directory traversal
    /\.\.\\/,               // Windows directory traversal
    // biome-ignore lint/suspicious/noControlCharactersInRegex: Intentionally matching control characters for security validation
    /[\r\n\x00]/,           // Newlines (command injection), null bytes (path truncation)
  ];

  for (const pattern of dangerousPatterns) {
    if (pattern.test(pathStr)) {
      return false;
    }
  }

  // On Windows, validate executable names additionally
  if (isWindows()) {
    const basename = path.basename(pathStr, getExecutableExtension());
    // Allow only alphanumeric, dots, hyphens, and underscores in the name
    return /^[\w.-]+$/.test(basename);
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
  // Reuse expandWindowsEnvVars for the actual expansion
  const expandedPath = expandWindowsEnvVars(pathPattern);

  // Check if any required variables couldn't be resolved (still contain %VAR% patterns)
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
/**
 * Expand and validate Windows tool paths, returning candidate paths.
 * Shared logic for both sync and async versions.
 */
function resolveWindowsToolCandidates(toolPaths: WindowsToolPaths): string[] {
  if (!isWindows()) return [];

  const candidates: string[] = [];
  for (const pattern of toolPaths.patterns) {
    const expandedDir = expandWindowsPath(pattern);
    if (!expandedDir) continue;

    const fullPath = path.join(expandedDir, toolPaths.executable);
    if (isSecurePath(fullPath)) {
      candidates.push(fullPath);
    }
  }
  return candidates;
}

export function getWindowsExecutablePaths(
  toolPaths: WindowsToolPaths,
  _logPrefix: string = '[Windows Paths]'
): string[] {
  return resolveWindowsToolCandidates(toolPaths).filter(p => existsSync(p));
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
  _logPrefix: string = '[Windows Paths]'
): Promise<string[]> {
  const candidates = resolveWindowsToolCandidates(toolPaths);
  const validPaths: string[] = [];

  for (const fullPath of candidates) {
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
 * Get macOS Homebrew detection paths for a given executable.
 * Returns paths where the tool might be installed via Homebrew on macOS.
 */
function getHomebrewDetectionPaths(executable: string): string[] {
  if (!isMacOS()) return [];
  return [
    `/opt/homebrew/bin/${executable}`, // Apple Silicon
    `/usr/local/bin/${executable}`,    // Intel Mac
  ];
}

/**
 * Get Git detection paths for macOS Homebrew installations
 *
 * @returns Array of Git executable paths to check
 */
export function getGitDetectionPaths(): string[] {
  return getHomebrewDetectionPaths('git');
}

/**
 * Get GitHub CLI detection paths for macOS Homebrew installations
 *
 * @returns Array of gh executable paths to check
 */
export function getGitHubCLIDetectionPaths(): string[] {
  return getHomebrewDetectionPaths('gh');
}

/**
 * Get common binary directories for PATH augmentation
 *
 * Returns platform-specific directories where commonly used tools are installed.
 * These are locations that should be added to PATH to ensure tools are available.
 *
 * @returns Record mapping platform names to arrays of binary directory paths
 */
export function getCommonBinPaths(): Record<string, string[]> {
  return {
    darwin: [
      '/opt/homebrew/bin',      // Apple Silicon Homebrew
      '/usr/local/bin',         // Intel Homebrew / system
      '/usr/local/share/dotnet', // .NET SDK
      '/opt/homebrew/sbin',     // Apple Silicon Homebrew sbin
      '/usr/local/sbin',        // Intel Homebrew sbin
      '~/.local/bin',           // User-local binaries (Claude CLI)
      '~/.dotnet/tools',        // .NET global tools
    ],
    linux: [
      '/usr/local/bin',
      '/usr/bin',               // System binaries (Python, etc.)
      '/snap/bin',              // Snap packages
      '~/.local/bin',           // User-local binaries
      '~/.dotnet/tools',        // .NET global tools
      '/usr/sbin',              // System admin binaries
    ],
    win32: [
      // Windows usually handles PATH better, but we can add common locations
      'C:\\Program Files\\Git\\cmd',
      'C:\\Program Files\\GitHub CLI',
      // Node.js and npm paths - critical for packaged Electron apps that don't inherit full PATH
      'C:\\Program Files\\nodejs',                  // Standard Node.js installer (64-bit)
      'C:\\Program Files (x86)\\nodejs',            // 32-bit Node.js on 64-bit Windows
      '~\\AppData\\Local\\Programs\\nodejs',        // NVM for Windows / user install
      '~\\AppData\\Roaming\\npm',                   // npm global scripts (claude.cmd lives here)
      '~\\scoop\\apps\\nodejs\\current',            // Scoop package manager
      'C:\\ProgramData\\chocolatey\\bin',           // Chocolatey package manager
    ],
  };
}

/**
 * Select the best executable path from 'where' command output.
 * Prefers .cmd/.bat/.exe extensions, validates path security.
 */
function selectBestWherePath(rawOutput: string): string | null {
  const paths = rawOutput.trim().split(/\r?\n/).filter(p => p.trim());
  if (paths.length === 0) return null;

  const foundPath = (paths.find(p => /\.(cmd|bat|exe)$/i.test(p)) || paths[0]).trim();
  return isSecurePath(foundPath) ? foundPath : null;
}

export function findWindowsExecutableViaWhere(
  executable: string,
  _logPrefix: string = '[Windows Where]'
): string | null {
  if (!isWindows()) return null;
  if (!/^[\w.-]+$/.test(executable)) return null;

  try {
    const result = execFileSync('where.exe', [executable], {
      encoding: 'utf-8',
      timeout: 5000,
      windowsHide: true,
    }).trim();

    const foundPath = selectBestWherePath(result);
    return foundPath && existsSync(foundPath) ? foundPath : null;
  } catch {
    return null;
  }
}

/**
 * Async version of findWindowsExecutableViaWhere
 *
 * Use this in async contexts to avoid blocking the main process.
 *
 * @param executable - The executable name (e.g., 'git', 'gh', 'python')
 * @param logPrefix - Prefix for console logging
 * @returns Promise resolving to the full path or null if not found
 */
export async function findWindowsExecutableViaWhereAsync(
  executable: string,
  _logPrefix: string = '[Windows Where]'
): Promise<string | null> {
  if (!isWindows()) return null;
  if (!/^[\w.-]+$/.test(executable)) return null;

  try {
    const { stdout } = await execFileAsync('where.exe', [executable], {
      encoding: 'utf-8',
      timeout: 5000,
      windowsHide: true,
    });

    const foundPath = selectBestWherePath(stdout);
    if (!foundPath) return null;

    try {
      await access(foundPath, constants.F_OK);
      return foundPath;
    } catch {
      return null;
    }
  } catch {
    return null;
  }
}
