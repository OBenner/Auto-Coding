/**
 * i18n Validation Utilities
 * Detects missing translation keys across language files
 */

import { resources } from './index';

export type TranslationKey = string;
export type TranslationKeySet = Set<TranslationKey>;
export type MissingKeysMap = Record<string, TranslationKeySet>;

/**
 * Recursively extract all translation keys from a nested object
 */
export const extractKeys = (obj: unknown, prefix = ''): TranslationKeySet => {
  const keys = new Set<TranslationKey>();

  if (typeof obj !== 'object' || obj === null) {
    return keys;
  }

  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;

    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      // Nested object - recurse
      const nestedKeys = extractKeys(value, fullKey);
      nestedKeys.forEach((k) => keys.add(k));
    } else {
      // Leaf value - add the key
      keys.add(fullKey);
    }
  }

  return keys;
};

/**
 * Get all translation keys for a specific language and namespace
 */
export const getKeysForNamespace = (
  language: string,
  namespace: string
): TranslationKeySet => {
  if (!(language in resources)) {
    return new Set();
  }

  const langResources = resources[language as keyof typeof resources];
  if (!(namespace in langResources)) {
    return new Set();
  }

  return extractKeys(langResources[namespace as keyof typeof langResources]);
};

/**
 * Find missing translation keys for a language compared to a base language
 */
export const findMissingKeys = (
  targetLanguage: string,
  baseLanguage: string = 'en'
): MissingKeysMap => {
  const missingKeys: MissingKeysMap = {};

  // Return empty result if either language is invalid
  if (!(baseLanguage in resources) || !(targetLanguage in resources)) {
    return missingKeys;
  }

  const baseResources = resources[baseLanguage as keyof typeof resources];
  const namespaces = Object.keys(baseResources);

  for (const namespace of namespaces) {
    const baseKeys = getKeysForNamespace(baseLanguage, namespace);
    const targetKeys = getKeysForNamespace(targetLanguage, namespace);

    const missing = new Set<TranslationKey>();
    baseKeys.forEach((key) => {
      if (!targetKeys.has(key)) {
        missing.add(key);
      }
    });

    if (missing.size > 0) {
      missingKeys[namespace] = missing;
    }
  }

  return missingKeys;
};

/**
 * Check if a language has complete translations (no missing keys)
 */
export const isLanguageComplete = (
  language: string,
  baseLanguage: string = 'en'
): boolean => {
  // Invalid languages are not complete
  if (!(language in resources) || !(baseLanguage in resources)) {
    return false;
  }

  const missingKeys = findMissingKeys(language, baseLanguage);
  return Object.keys(missingKeys).length === 0;
};

/**
 * Get all supported languages from resources
 */
export const getSupportedLanguages = (): string[] => {
  return Object.keys(resources);
};

/**
 * Get all namespaces for a language
 */
export const getNamespaces = (language: string): string[] => {
  if (!(language in resources)) {
    return [];
  }

  return Object.keys(resources[language as keyof typeof resources]);
};

/**
 * Validate all languages and return missing keys report
 */
export const validateTranslations = (): Record<string, MissingKeysMap> => {
  const languages = getSupportedLanguages();
  const baseLanguage = 'en';
  const report: Record<string, MissingKeysMap> = {};

  for (const language of languages) {
    if (language !== baseLanguage) {
      const missing = findMissingKeys(language, baseLanguage);
      if (Object.keys(missing).length > 0) {
        report[language] = missing;
      }
    }
  }

  return report;
};

/**
 * Format missing keys report as human-readable string
 */
export const formatMissingKeysReport = (
  missingKeysMap: MissingKeysMap,
  language: string
): string => {
  const lines: string[] = [`Missing keys in ${language}:`, ''];

  for (const [namespace, keys] of Object.entries(missingKeysMap)) {
    lines.push(`  ${namespace}:`);
    keys.forEach((key) => {
      lines.push(`    - ${key}`);
    });
    lines.push('');
  }

  return lines.join('\n');
};

/**
 * Check if a specific translation key exists
 */
export const hasKey = (
  language: string,
  namespace: string,
  key: string
): boolean => {
  const keys = getKeysForNamespace(language, namespace);
  return keys.has(key);
};
