#!/usr/bin/env node
/**
 * Cross-platform backend installer script
 * Handles Python venv creation and dependency installation on Windows/Mac/Linux
 */

const path = require('path');
const { ensurePythonOrExit, createRunHelper, createVenv, installDeps, setupEnvFile } = require('./install-utils');

const appDir = path.join(__dirname, '..', 'apps', 'backend');
const venvDir = path.join(appDir, '.venv');

console.log('Installing Auto Code backend dependencies...\n');

const python = ensurePythonOrExit();
const run = createRunHelper(appDir);

createVenv(run, python, venvDir);
installDeps(run, venvDir, ['requirements.txt', '../../tests/requirements-test.txt']);
setupEnvFile(appDir, ['- Run: claude setup-token']);

console.log('\n✓ Backend installation complete!');
console.log(`  Virtual environment: ${venvDir}`);
console.log('  Runtime dependencies: installed');
console.log('  Test dependencies: installed (pytest, etc.)');
