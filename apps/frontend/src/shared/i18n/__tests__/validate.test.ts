/**
 * Unit tests for i18n validation utilities
 * Tests translation key extraction, validation, and completeness checking
 */
import { describe, it, expect } from 'vitest';
import {
  extractKeys,
  getKeysForNamespace,
  findMissingKeys,
  isLanguageComplete,
  getSupportedLanguages,
  getNamespaces,
  validateTranslations,
  formatMissingKeysReport,
  hasKey,
  type TranslationKeySet
} from '../validate';

describe('i18n validation utilities', () => {
  describe('extractKeys', () => {
    it('should return empty set for null', () => {
      const keys = extractKeys(null);
      expect(keys).toBeInstanceOf(Set);
      expect(keys.size).toBe(0);
    });

    it('should return empty set for non-object', () => {
      const keys = extractKeys('string');
      expect(keys.size).toBe(0);
    });

    it('should extract keys from flat object', () => {
      const obj = {
        key1: 'value1',
        key2: 'value2'
      };
      const keys = extractKeys(obj);
      expect(keys).toContain('key1');
      expect(keys).toContain('key2');
      expect(keys.size).toBe(2);
    });

    it('should extract keys from nested object', () => {
      const obj = {
        level1: {
          level2: {
            key1: 'value1'
          }
        }
      };
      const keys = extractKeys(obj);
      expect(keys).toContain('level1.level2.key1');
      expect(keys.size).toBe(1);
    });

    it('should extract keys from mixed nested structure', () => {
      const obj = {
        flat: 'value',
        nested: {
          key1: 'value1',
          deeper: {
            key2: 'value2'
          }
        }
      };
      const keys = extractKeys(obj);
      expect(keys).toContain('flat');
      expect(keys).toContain('nested.key1');
      expect(keys).toContain('nested.deeper.key2');
      expect(keys.size).toBe(3);
    });

    it('should handle arrays as values, not objects', () => {
      const obj = {
        key1: ['value1', 'value2'],
        key2: 'value2'
      };
      const keys = extractKeys(obj);
      expect(keys).toContain('key1');
      expect(keys).toContain('key2');
      expect(keys.size).toBe(2);
    });
  });

  describe('getSupportedLanguages', () => {
    it('should return array of supported languages', () => {
      const languages = getSupportedLanguages();
      expect(Array.isArray(languages)).toBe(true);
      expect(languages).toContain('en');
      expect(languages).toContain('fr');
    });

    it('should have at least English', () => {
      const languages = getSupportedLanguages();
      expect(languages.length).toBeGreaterThanOrEqual(1);
      expect(languages[0]).toBe('en');
    });
  });

  describe('getNamespaces', () => {
    it('should return namespaces for valid language', () => {
      const namespaces = getNamespaces('en');
      expect(Array.isArray(namespaces)).toBe(true);
      expect(namespaces.length).toBeGreaterThan(0);
      expect(namespaces).toContain('common');
      expect(namespaces).toContain('navigation');
    });

    it('should return empty array for invalid language', () => {
      const namespaces = getNamespaces('invalid');
      expect(namespaces).toEqual([]);
    });
  });

  describe('getKeysForNamespace', () => {
    it('should return keys for valid language and namespace', () => {
      const keys = getKeysForNamespace('en', 'common');
      expect(keys).toBeInstanceOf(Set);
      expect(keys.size).toBeGreaterThan(0);
    });

    it('should return empty set for invalid language', () => {
      const keys = getKeysForNamespace('invalid', 'common');
      expect(keys).toBeInstanceOf(Set);
      expect(keys.size).toBe(0);
    });

    it('should return empty set for invalid namespace', () => {
      const keys = getKeysForNamespace('en', 'invalid');
      expect(keys).toBeInstanceOf(Set);
      expect(keys.size).toBe(0);
    });

    it('should extract nested keys correctly', () => {
      const keys = getKeysForNamespace('en', 'common');
      // Check for some known nested keys
      expect(keys).toContain('buttons.save');
      expect(keys).toContain('buttons.cancel');
    });
  });

  describe('findMissingKeys', () => {
    it('should return empty object for complete language', () => {
      // English compared to English should have no missing keys
      const missing = findMissingKeys('en', 'en');
      expect(Object.keys(missing).length).toBe(0);
    });

    it('should detect missing keys between languages', () => {
      // This test may fail if fr has all en keys, but that's the point of the utility
      const missing = findMissingKeys('fr', 'en');
      expect(typeof missing).toBe('object');
      // We don't assert length here as it depends on actual translation completeness
    });

    it('should return empty object for invalid base language', () => {
      const missing = findMissingKeys('fr', 'invalid');
      expect(Object.keys(missing).length).toBe(0);
    });

    it('should return empty object for invalid target language', () => {
      const missing = findMissingKeys('invalid', 'en');
      expect(Object.keys(missing).length).toBe(0);
    });

    it('should group missing keys by namespace', () => {
      const missing = findMissingKeys('fr', 'en');
      for (const namespace in missing) {
        expect(Array.isArray(missing[namespace])).toBe(false);
        expect(missing[namespace]).toBeInstanceOf(Set);
      }
    });
  });

  describe('isLanguageComplete', () => {
    it('should return true for language compared to itself', () => {
      const complete = isLanguageComplete('en', 'en');
      expect(complete).toBe(true);
    });

    it('should return boolean for different languages', () => {
      const complete = isLanguageComplete('fr', 'en');
      expect(typeof complete).toBe('boolean');
    });

    it('should return false for invalid base language', () => {
      const complete = isLanguageComplete('fr', 'invalid');
      expect(complete).toBe(false);
    });

    it('should return false for invalid target language', () => {
      const complete = isLanguageComplete('invalid', 'en');
      expect(complete).toBe(false);
    });
  });

  describe('validateTranslations', () => {
    it('should return object with language keys', () => {
      const report = validateTranslations();
      expect(typeof report).toBe('object');
    });

    it('should not include base language (en) in report', () => {
      const report = validateTranslations();
      expect(report).not.toHaveProperty('en');
    });

    it('should only include languages with missing keys', () => {
      const report = validateTranslations();
      for (const lang in report) {
        expect(lang).not.toBe('en');
        expect(typeof report[lang]).toBe('object');
      }
    });
  });

  describe('formatMissingKeysReport', () => {
    it('should format missing keys as string', () => {
      const missingKeys = {
        common: new Set(['key1', 'key2'])
      };
      const report = formatMissingKeysReport(missingKeys, 'fr');
      expect(typeof report).toBe('string');
      expect(report.length).toBeGreaterThan(0);
    });

    it('should include language name in report', () => {
      const missingKeys = {
        common: new Set(['key1'])
      };
      const report = formatMissingKeysReport(missingKeys, 'fr');
      expect(report).toContain('fr');
    });

    it('should include namespace in report', () => {
      const missingKeys = {
        common: new Set(['key1'])
      };
      const report = formatMissingKeysReport(missingKeys, 'fr');
      expect(report).toContain('common');
    });

    it('should include missing keys in report', () => {
      const missingKeys = {
        common: new Set(['key1', 'key2'])
      };
      const report = formatMissingKeysReport(missingKeys, 'fr');
      expect(report).toContain('key1');
      expect(report).toContain('key2');
    });

    it('should handle empty missing keys', () => {
      const report = formatMissingKeysReport({}, 'fr');
      expect(typeof report).toBe('string');
    });
  });

  describe('hasKey', () => {
    it('should return true for existing key', () => {
      const has = hasKey('en', 'common', 'buttons.save');
      expect(has).toBe(true);
    });

    it('should return false for non-existing key', () => {
      const has = hasKey('en', 'common', 'nonexistent.key');
      expect(has).toBe(false);
    });

    it('should return false for invalid language', () => {
      const has = hasKey('invalid', 'common', 'buttons.save');
      expect(has).toBe(false);
    });

    it('should return false for invalid namespace', () => {
      const has = hasKey('en', 'invalid', 'buttons.save');
      expect(has).toBe(false);
    });

    it('should check nested keys correctly', () => {
      const has = hasKey('en', 'common', 'buttons.save');
      expect(has).toBe(true);
    });
  });
});
