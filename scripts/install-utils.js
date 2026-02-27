#!/usr/bin/env node
/**
 * Shared utilities for backend installer scripts.
 * Centralises Python discovery, venv creation, dependency installation,
 * and .env bootstrapping so that each installer is a thin wrapper.
 */

const { execSync, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const isWindows = os.platform() === 'win32';

// ---------------------------------------------------------------------------
// Python discovery
// ---------------------------------------------------------------------------

/**
 * Find a Python 3.12+ interpreter.
 * Prefers explicit 3.12 candidates for best wheel compatibility.
 * @returns {string|null} command string or null if nothing found
 */
function findPython() {
  const candidates = isWindows
    ? ['py -3.12', 'py -3.13', 'py -3.14', 'python3.12', 'python3.13', 'python3.14', 'python3', 'python']
    : ['python3.12', 'python3.13', 'python3.14', 'python3', 'python'];

  for (const cmd of candidates) {
    try {
      // SECURITY: cmd values come exclusively from the hardcoded candidates
      // array above — no user input is interpolated into the command string.
      const result = spawnSync(cmd, ['--version'], {
        encoding: 'utf8',
        shell: true,
      });

      if (result.status === 0) {
        // Some platforms write version to stderr instead of stdout
        const output = result.stdout || result.stderr || '';
        const versionMatch = output.match(/Python (\d+)\.(\d+)/);
        if (versionMatch) {
          const major = parseInt(versionMatch[1], 10);
          const minor = parseInt(versionMatch[2], 10);
          if (major === 3 && minor >= 12) {
            console.log(`Found Python 3.12+: ${cmd} -> ${output.trim()}`);
            return cmd;
          }
        }
      }
    } catch {
      // Continue to next candidate
    }
  }
  return null;
}

/**
 * Find Python 3.12+ or exit with a helpful error message.
 * @returns {string} python command
 */
function ensurePythonOrExit() {
  const python = findPython();
  if (!python) {
    console.error('\nError: Python 3.12+ is required but not found.');
    console.error('Please install Python 3.12 or higher:');
    if (isWindows) {
      console.error('  winget install Python.Python.3.12');
    } else if (os.platform() === 'darwin') {
      console.error('  brew install python@3.12');
    } else {
      console.error('  sudo apt install python3.12 python3.12-venv');
    }
    process.exit(1);
  }
  return python;
}

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

/**
 * Get platform-specific pip path inside a venv.
 * @param {string} venvDir absolute path to the .venv directory
 * @returns {string}
 */
function getPipPath(venvDir) {
  return isWindows
    ? path.join(venvDir, 'Scripts', 'pip.exe')
    : path.join(venvDir, 'bin', 'pip');
}

// ---------------------------------------------------------------------------
// Command runner
// ---------------------------------------------------------------------------

/**
 * Create a run() helper bound to a working directory.
 *
 * SECURITY: All commands executed through this helper are constructed from a
 * fixed set of candidates and deterministic paths (Python launcher variants,
 * venv-local pip, uv). No arbitrary user input is interpolated into command
 * strings.
 *
 * @param {string} cwd working directory for commands
 * @returns {(cmd: string, options?: object) => boolean}
 */
function createRunHelper(cwd) {
  return function run(cmd, options = {}) {
    console.log(`> ${cmd}`);
    try {
      // SECURITY: All callers pass fixed command strings (uv, python, pip)
      // built from deterministic paths — no user input is interpolated.
      execSync(cmd, { stdio: 'inherit', cwd, ...options });
      return true;
    } catch {
      return false;
    }
  };
}

// ---------------------------------------------------------------------------
// Venv creation
// ---------------------------------------------------------------------------

/**
 * Create a virtual environment (idempotent — skips if it already exists).
 * Tries `uv venv` first (repo standard), falls back to `python -m venv`.
 *
 * @param {(cmd: string, options?: object) => boolean} run
 * @param {string} python  python command string
 * @param {string} venvDir absolute path to target .venv
 */
function createVenv(run, python, venvDir) {
  if (fs.existsSync(venvDir)) {
    console.log(`\n✓ Virtual environment already exists at ${venvDir}`);
    return;
  }

  console.log(`\nCreating virtual environment at ${venvDir}...`);
  // Prefer uv (repo standard per CLAUDE.md), fall back to python -m venv
  if (!run(`uv venv "${venvDir}"`)) {
    console.log('  uv not available, falling back to python -m venv...');
    if (!run(`${python} -m venv "${venvDir}"`)) {
      console.error(`Failed to create virtual environment at ${venvDir}`);
      process.exit(1);
    }
  }
}

// ---------------------------------------------------------------------------
// Dependency installation
// ---------------------------------------------------------------------------

/**
 * Install Python packages from one or more requirements files.
 * Tries `uv pip` first (repo standard), falls back to the venv pip.
 *
 * @param {(cmd: string, options?: object) => boolean} run
 * @param {string} venvDir absolute path to .venv
 * @param {string[]} requirementsFiles paths relative to cwd
 */
function installDeps(run, venvDir, requirementsFiles) {
  for (const reqFile of requirementsFiles) {
    console.log(`\nInstalling from ${reqFile}...`);
    if (!run(`uv pip install -r ${reqFile}`)) {
      console.log('  uv pip not available, falling back to venv pip...');
      const pip = getPipPath(venvDir);
      if (!run(`"${pip}" install -r ${reqFile}`)) {
        console.error(`Failed to install dependencies from ${reqFile}`);
        process.exit(1);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// .env bootstrapping
// ---------------------------------------------------------------------------

/**
 * Copy .env.example → .env if .env does not already exist.
 *
 * @param {string} appDir directory containing .env.example
 * @param {string[]} [extraMessages] additional lines printed after creation
 */
function setupEnvFile(appDir, extraMessages) {
  const envPath = path.join(appDir, '.env');
  const envExamplePath = path.join(appDir, '.env.example');

  if (fs.existsSync(envPath)) {
    console.log('\n✓ .env file already exists');
  } else if (fs.existsSync(envExamplePath)) {
    console.log('\nCreating .env file from .env.example...');
    try {
      fs.copyFileSync(envExamplePath, envPath);
      console.log('✓ Created .env file');
      console.log('  Please configure it with your credentials:');
      if (extraMessages) {
        for (const msg of extraMessages) {
          console.log(`  ${msg}`);
        }
      }
      console.log(`  - Edit: ${envPath}`);
    } catch (error) {
      console.warn('Warning: Could not create .env file:', error.message);
      console.warn('You will need to manually copy .env.example to .env');
    }
  } else {
    console.warn('\nWarning: .env.example not found. Cannot auto-create .env file.');
    console.warn('Please create a .env file manually if your configuration requires it.');
  }
}

module.exports = {
  findPython,
  ensurePythonOrExit,
  getPipPath,
  createRunHelper,
  createVenv,
  installDeps,
  setupEnvFile,
};
