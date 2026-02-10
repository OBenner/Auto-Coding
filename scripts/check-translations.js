#!/usr/bin/env node

/**
 * Translation Check Script
 *
 * Validates translation files for completeness and consistency.
 * Helps community contributors ensure translations are properly formatted.
 *
 * Usage:
 *   node scripts/check-translations.js [options]
 *
 * Options:
 *   --lang <code>     Check specific language only (e.g., fr, es, de)
 *   --namespace <ns>  Check specific namespace only (e.g., common, navigation)
 *   --json            Output results in JSON format
 *   --help            Show this help message
 *
 * Examples:
 *   node scripts/check-translations.js                      # Check all translations
 *   node scripts/check-translations.js --lang fr            # Check French only
 *   node scripts/check-translations.js --namespace common   # Check common namespace
 *   node scripts/check-translations.js --json > results.json # Export to JSON
 *
 * Exit Codes:
 *   0 - All checks passed
 *   1 - Errors found (missing keys, invalid JSON, etc.)
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
  dim: '\x1b[2m',
};

function log(message, color = colors.reset) {
  console.log(`${color}${message}${colors.reset}`);
}

function error(message) {
  log(`❌ ${message}`, colors.red);
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

function dim(message) {
  log(message, colors.dim);
}

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    lang: null,
    namespace: null,
    json: false,
    help: false,
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--lang':
        options.lang = args[++i];
        break;
      case '--namespace':
        options.namespace = args[++i];
        break;
      case '--json':
        options.json = true;
        break;
      case '--help':
        options.help = true;
        break;
      default:
        if (args[i].startsWith('--')) {
          error(`Unknown option: ${args[i]}`);
          options.help = true;
        }
    }
  }

  return options;
}

// Show help message
function showHelp() {
  console.log(`
Translation Check Script

Validates translation files for completeness and consistency.
Helps community contributors ensure translations are properly formatted.

Usage:
  node scripts/check-translations.js [options]

Options:
  --lang <code>     Check specific language only (e.g., fr, es, de)
  --namespace <ns>  Check specific namespace only (e.g., common, navigation)
  --json            Output results in JSON format
  --help            Show this help message

Examples:
  node scripts/check-translations.js                      # Check all translations
  node scripts/check-translations.js --lang fr            # Check French only
  node scripts/check-translations.js --namespace common   # Check common namespace
  node scripts/check-translations.js --json > results.json # Export to JSON

Exit Codes:
  0 - All checks passed
  1 - Errors found (missing keys, invalid JSON, etc.)
`);
}

// Get all available languages
function getAvailableLanguages() {
  const localesPath = path.join(__dirname, '..', 'apps', 'frontend', 'src', 'shared', 'i18n', 'locales');

  if (!fs.existsSync(localesPath)) {
    error(`Translation directory not found: ${localesPath}`);
    process.exit(1);
  }

  const languages = fs.readdirSync(localesPath).filter(file => {
    const langPath = path.join(localesPath, file);
    return fs.statSync(langPath).isDirectory();
  });

  return languages.sort();
}

// Get all available namespaces for a language
function getNamespaces(lang) {
  const langPath = path.join(__dirname, '..', 'apps', 'frontend', 'src', 'shared', 'i18n', 'locales', lang);

  if (!fs.existsSync(langPath)) {
    return [];
  }

  const files = fs.readdirSync(langPath).filter(file => file.endsWith('.json'));
  return files.map(file => file.replace('.json', '')).sort();
}

// Read and parse a translation file
function readTranslationFile(lang, namespace) {
  const filePath = path.join(__dirname, '..', 'apps', 'frontend', 'src', 'shared', 'i18n', 'locales', lang, `${namespace}.json`);

  if (!fs.existsSync(filePath)) {
    return null;
  }

  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(content);
  } catch (err) {
    error(`Failed to parse ${filePath}: ${err.message}`);
    return null;
  }
}

// Recursively get all keys from a nested object
function getKeys(obj, prefix = '') {
  const keys = [];

  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;

    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      keys.push(...getKeys(value, fullKey));
    } else {
      keys.push(fullKey);
    }
  }

  return keys.sort();
}

// Check if value is empty (empty string or only whitespace)
function isEmptyValue(value) {
  if (typeof value !== 'string') {
    return false;
  }
  return value.trim().length === 0;
}

// Compare two translation files and find differences
function compareTranslations(baseLang, targetLang, namespace) {
  const baseTranslations = readTranslationFile(baseLang, namespace);
  const targetTranslations = readTranslationFile(targetLang, namespace);

  if (!baseTranslations) {
    error(`Base language (${baseLang}) not found for namespace: ${namespace}`);
    return null;
  }

  if (!targetTranslations) {
    error(`Target language (${targetLang}) not found for namespace: ${namespace}`);
    return null;
  }

  const baseKeys = getKeys(baseTranslations);
  const targetKeys = getKeys(targetTranslations);

  const missingKeys = baseKeys.filter(key => !targetKeys.includes(key));
  const extraKeys = targetKeys.filter(key => !baseKeys.includes(key));

  // Check for empty values
  const emptyValues = [];
  function checkEmpty(obj, prefix = '') {
    for (const [key, value] of Object.entries(obj)) {
      const fullKey = prefix ? `${prefix}.${key}` : key;

      if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        checkEmpty(value, fullKey);
      } else if (isEmptyValue(value)) {
        emptyValues.push(fullKey);
      }
    }
  }
  checkEmpty(targetTranslations);

  return {
    namespace,
    baseLang,
    targetLang,
    baseKeysCount: baseKeys.length,
    targetKeysCount: targetKeys.length,
    missingKeys,
    extraKeys,
    emptyValues,
  };
}

// Format results for terminal output
function formatResults(results, options) {
  let hasErrors = false;

  for (const result of results) {
    if (!result) {
      continue;
    }

    const { namespace, baseLang, targetLang, baseKeysCount, targetKeysCount, missingKeys, extraKeys, emptyValues } = result;

    log(`\n📄 ${namespace}`, colors.cyan);
    dim(`    Base: ${baseLang} (${baseKeysCount} keys) | Target: ${targetLang} (${targetKeysCount} keys)`);

    if (missingKeys.length === 0 && extraKeys.length === 0 && emptyValues.length === 0) {
      success('   ✓ All translations present and valid');
      continue;
    }

    hasErrors = true;

    if (missingKeys.length > 0) {
      error(`   Missing ${missingKeys.length} key(s):`);
      missingKeys.forEach(key => dim(`      - ${key}`));
    }

    if (extraKeys.length > 0) {
      warning(`   Extra ${extraKeys.length} key(s) (not in ${baseLang}):`);
      extraKeys.forEach(key => dim(`      - ${key}`));
    }

    if (emptyValues.length > 0) {
      warning(`   ${emptyValues.length} empty value(s):`);
      emptyValues.forEach(key => dim(`      - ${key}`));
    }
  }

  return hasErrors;
}

// Format results as JSON
function formatJsonResults(results) {
  return results.filter(r => r !== null);
}

// Main function
function main() {
  const options = parseArgs();

  if (options.help) {
    showHelp();
    process.exit(0);
  }

  log('\n🌐 Auto Code Translation Check\n', colors.cyan);

  // Get available languages and namespaces
  const languages = getAvailableLanguages();
  info(`Found ${languages.length} language(s): ${languages.join(', ')}`);

  // Filter languages if specified
  const languagesToCheck = options.lang ? [options.lang] : languages;

  // Collect all namespaces across all languages
  const allNamespaces = new Set();
  languages.forEach(lang => {
    getNamespaces(lang).forEach(ns => allNamespaces.add(ns));
  });

  const namespacesToCheck = options.namespace ? [options.namespace] : Array.from(allNamespaces).sort();

  info(`Checking ${namespacesToCheck.length} namespace(s): ${namespacesToCheck.join(', ')}\n`);

  // Use English as base language for comparison
  const baseLang = 'en';

  if (!languages.includes(baseLang)) {
    error(`Base language (${baseLang}) not found`);
    process.exit(1);
  }

  // Run checks
  const results = [];

  for (const lang of languagesToCheck) {
    if (!languages.includes(lang)) {
      warning(`Language not found: ${lang}`);
      continue;
    }

    if (lang === baseLang) {
      continue; // Skip base language
    }

    for (const namespace of namespacesToCheck) {
      const result = compareTranslations(baseLang, lang, namespace);
      results.push(result);
    }
  }

  // Format and output results
  if (options.json) {
    const jsonResults = formatJsonResults(results);
    console.log(JSON.stringify(jsonResults, null, 2));

    // Check for errors
    const hasErrors = jsonResults.some(r =>
      r && (r.missingKeys.length > 0 || r.emptyValues.length > 0)
    );

    process.exit(hasErrors ? 1 : 0);
  } else {
    const hasErrors = formatResults(results, options);

    log('');
    if (hasErrors) {
      error('Translation check failed. Please fix the issues above.');
      log('\n💡 Tips for contributors:', colors.yellow);
      log('   - Add missing keys to match the English (en) translations', colors.dim);
      log('   - Remove extra keys that don\'t exist in English', colors.dim);
      log('   - Fill in empty values with actual translations', colors.dim);
      log('   - Ensure JSON syntax is valid (use a JSON validator)', colors.dim);
      log('');
      process.exit(1);
    } else {
      success('All translation checks passed!\n');
      process.exit(0);
    }
  }
}

// Run
main();
