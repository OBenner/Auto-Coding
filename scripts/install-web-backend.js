#!/usr/bin/env node
/**
 * Cross-platform web-backend installer script
 * Handles Python venv creation and dependency installation on Windows/Mac/Linux
 */

const path = require('path');
const { ensurePythonOrExit, createRunHelper, createVenv, installDeps, setupEnvFile } = require('./install-utils');

const appDir = path.join(__dirname, '..', 'apps', 'web-backend');
const venvDir = path.join(appDir, '.venv');

console.log('Installing Auto Code web-backend dependencies...\n');

const python = ensurePythonOrExit();
const run = createRunHelper(appDir);

createVenv(run, python, venvDir);
installDeps(run, venvDir, ['requirements.txt']);
setupEnvFile(appDir);

console.log('\n✓ Web-backend installation complete!');
console.log(`  Virtual environment: ${venvDir}`);
console.log('  Runtime dependencies: installed from requirements.txt');
