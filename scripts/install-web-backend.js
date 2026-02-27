#!/usr/bin/env node
/**
 * Cross-platform web-backend installer script
 * Handles Python venv creation and dependency installation on Windows/Mac/Linux
 */

const { execSync, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const isWindows = os.platform() === 'win32';
const webBackendDir = path.join(__dirname, '..', 'apps', 'web-backend');
const venvDir = path.join(webBackendDir, '.venv');

console.log('Installing Auto Code web-backend dependencies...\n');

// Helper to run commands
// SECURITY: Commands are constructed from a fixed set of candidates and paths
// (Python launcher variants, venv-local pip). No arbitrary user input is passed here.
function run(cmd, options = {}) {
  console.log(`> ${cmd}`);
  try {
    execSync(cmd, { stdio: 'inherit', cwd: webBackendDir, ...options });
    return true;
  } catch (error) {
    return false;
  }
}

// Find Python 3.12+
// Prefer 3.12 first since it has the most stable wheel support for native packages
function findPython() {
  const candidates = isWindows
    ? ['py -3.12', 'py -3.13', 'py -3.14', 'python3.12', 'python3.13', 'python3.14', 'python3', 'python']
    : ['python3.12', 'python3.13', 'python3.14', 'python3', 'python'];

  for (const cmd of candidates) {
    try {
      // Use shell: true with the full command string to handle entries like 'py -3.12'
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

// Get pip path based on platform
function getPipPath() {
  return isWindows
    ? path.join(venvDir, 'Scripts', 'pip.exe')
    : path.join(venvDir, 'bin', 'pip');
}

// Main installation
async function main() {
  // Check for Python 3.12+
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

  // Create virtual environment (skip if already exists)
  if (fs.existsSync(venvDir)) {
    console.log(`\n✓ Virtual environment already exists at ${venvDir}`);
  } else {
    console.log('\nCreating virtual environment...');
    if (!run(`${python} -m venv .venv`)) {
      console.error('Failed to create virtual environment');
      process.exit(1);
    }
  }

  // Install dependencies (includes test dependencies in web-backend)
  console.log('\nInstalling dependencies...');
  const pip = getPipPath();
  if (!run(`"${pip}" install -r requirements.txt`)) {
    console.error('Failed to install dependencies');
    process.exit(1);
  }

  // Create .env file from .env.example if it doesn't exist
  const envPath = path.join(webBackendDir, '.env');
  const envExamplePath = path.join(webBackendDir, '.env.example');

  if (fs.existsSync(envPath)) {
    console.log('\n✓ .env file already exists');
  } else if (fs.existsSync(envExamplePath)) {
    console.log('\nCreating .env file from .env.example...');
    try {
      fs.copyFileSync(envExamplePath, envPath);
      console.log('✓ Created .env file');
      console.log('  Please configure it with your credentials:');
      console.log(`  - Edit: ${envPath}`);
    } catch (error) {
      console.warn('Warning: Could not create .env file:', error.message);
      console.warn('You will need to manually copy .env.example to .env');
    }
  } else {
    console.warn('\nWarning: .env.example not found. Cannot auto-create .env file.');
    console.warn('Please create a .env file manually if your configuration requires it.');
  }

  console.log('\n✓ Web-backend installation complete!');
  console.log(`  Virtual environment: ${venvDir}`);
  console.log('  Runtime dependencies: installed from requirements.txt');
  console.log('  Test dependencies: installed if listed in requirements.txt');
}

main().catch((err) => {
  console.error('Installation failed:', err);
  process.exit(1);
});
