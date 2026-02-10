#!/usr/bin/env node

/**
 * Translation Validation Script
 *
 * Validates that all translation locale files have complete and matching keys.
 * This ensures that no translations are missing when adding new features.
 *
 * Usage:
 *   node scripts/validate-translations.js
 *
 * What it checks:
 *   - All locale files (en, fr, es, de, etc.) have the same translation keys
 *   - No missing keys in any locale
 *   - Reports missing keys with file paths
 *
 * Exit codes:
 *   - 0: All translations are complete
 *   - 1: Missing translations found
 *
 * Integration:
 *   - Run as part of CI/CD pipeline
 *   - Run before committing changes
 *   - Add to package.json: "validate:translations": "node scripts/validate-translations.js"
 */

const fs = require('fs');
const path = require('path');

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m',
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function error(message) {
  log(`❌ Error: ${message}`, colors.red);
  process.exit(1);
}

function success(message) {
  log(`✅ ${message}`, colors.green);
}

function info(message) {
  log(`ℹ️  ${message}`, colors.cyan);
}

function warning(message) {
  log(`⚠️  ${message}`, colors.yellow);
}

// Recursively extract all keys from a nested object
function extractKeys(obj, prefix = '') {
  const keys = [];

  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;

    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      // Recursively extract keys from nested objects
      keys.push(...extractKeys(value, fullKey));
    } else {
      keys.push(fullKey);
    }
  }

  return keys.sort();
}

// Read all JSON files in a locale directory and merge their keys
function readLocaleKeys(localeDir) {
  if (!fs.existsSync(localeDir)) {
    return [];
  }

  const keys = new Set();
  const files = fs.readdirSync(localeDir).filter(f => f.endsWith('.json'));

  for (const file of files) {
    const filePath = path.join(localeDir, file);
    try {
      const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      const fileKeys = extractKeys(content);

      // Add namespace prefix (filename without .json)
      const namespace = path.basename(file, '.json');
      for (const key of fileKeys) {
        keys.add(`${namespace}:${key}`);
      }
    } catch (err) {
      warning(`Failed to parse ${filePath}: ${err.message}`);
    }
  }

  return Array.from(keys).sort();
}

// Find missing keys in target locale compared to reference locale
function findMissingKeys(referenceKeys, targetKeys) {
  const referenceSet = new Set(referenceKeys);
  const missing = [];

  for (const key of referenceKeys) {
    if (!targetKeys.includes(key)) {
      missing.push(key);
    }
  }

  return missing.sort();
}

// Find extra keys in target locale that don't exist in reference
function findExtraKeys(referenceKeys, targetKeys) {
  const targetSet = new Set(targetKeys);
  const extra = [];

  for (const key of targetKeys) {
    if (!referenceKeys.includes(key)) {
      extra.push(key);
    }
  }

  return extra.sort();
}

// Format missing keys report
function formatMissingKeys(locale, missingKeys, extraKeys) {
  if (missingKeys.length === 0 && extraKeys.length === 0) {
    return null;
  }

  const lines = [];

  if (missingKeys.length > 0) {
    lines.push(log(`\n  📝 Missing keys (${missingKeys.length}):`, colors.yellow));
    for (const key of missingKeys) {
      lines.push(log(`    - ${key}`, colors.reset));
    }
  }

  if (extraKeys.length > 0) {
    lines.push(log(`\n  ➕ Extra keys (${extraKeys.length}):`, colors.cyan));
    for (const key of extraKeys) {
      lines.push(log(`    + ${key}`, colors.reset));
    }
  }

  return lines;
}

// Main function
function main() {
  log('\n🔍 Translation Validation\n', colors.cyan);

  // Define paths
  const localesDir = path.join(__dirname, '..', 'src', 'shared', 'i18n', 'locales');
  const referenceLocale = 'en';

  // Check if locales directory exists
  if (!fs.existsSync(localesDir)) {
    error(`Locales directory not found at ${localesDir}`);
  }

  // Get all locale directories
  const locales = fs.readdirSync(localesDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);

  if (locales.length === 0) {
    error('No locale directories found');
  }

  info(`Found ${locales.length} locales: ${locales.join(', ')}`);

  // Read reference locale keys
  const referenceDir = path.join(localesDir, referenceLocale);
  if (!fs.existsSync(referenceDir)) {
    error(`Reference locale '${referenceLocale}' not found`);
  }

  const referenceKeys = readLocaleKeys(referenceDir);
  info(`Reference locale '${referenceLocale}' has ${referenceKeys.length} translation keys`);

  // Validate each locale
  let hasErrors = false;
  const results = [];

  for (const locale of locales) {
    if (locale === referenceLocale) {
      continue; // Skip reference locale
    }

    const localeDir = path.join(localesDir, locale);
    const localeKeys = readLocaleKeys(localeDir);

    const missingKeys = findMissingKeys(referenceKeys, localeKeys);
    const extraKeys = findExtraKeys(referenceKeys, localeKeys);

    if (missingKeys.length > 0 || extraKeys.length > 0) {
      hasErrors = true;
      results.push({
        locale,
        missingKeys,
        extraKeys,
        totalKeys: localeKeys.length
      });
    } else {
      success(`Locale '${locale}': All ${referenceKeys.length} keys present ✓`);
    }
  }

  // Print summary
  if (hasErrors) {
    log('\n❌ Translation validation failed!\n', colors.red);

    for (const result of results) {
      log(`🌍 Locale: ${result.locale} (${result.totalKeys} keys)`, colors.magenta);

      if (result.missingKeys.length > 0) {
        log(`\n  Missing ${result.missingKeys.length} keys:`, colors.yellow);
        for (const key of result.missingKeys) {
          log(`    - ${key}`, colors.reset);
        }
      }

      if (result.extraKeys.length > 0) {
        log(`\n  Has ${result.extraKeys.length} extra keys:`, colors.cyan);
        for (const key of result.extraKeys) {
          log(`    + ${key}`, colors.reset);
        }
      }

      log(''); // Empty line between locales
    }

    log('💡 To fix:', colors.cyan);
    log('   1. Add missing keys to the locale files', colors.reset);
    log('   2. Remove extra keys if they are obsolete', colors.reset);
    log('   3. Re-run this script to verify\n', colors.reset);

    process.exit(1);
  } else {
    success('All translations are complete! 🎉\n');
    process.exit(0);
  }
}

// Run main function
main();
