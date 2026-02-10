/**
 * Internationalization constants
 * Available languages, display labels, and RTL configuration
 */

export type SupportedLanguage = 'en' | 'fr' | 'ar' | 'he';

export interface LanguageConfig {
  value: SupportedLanguage;
  label: string;
  nativeLabel: string;
  isRTL: boolean;
}

export const AVAILABLE_LANGUAGES: LanguageConfig[] = [
  { value: 'en', label: 'English', nativeLabel: 'English', isRTL: false },
  { value: 'fr', label: 'French', nativeLabel: 'Français', isRTL: false },
  { value: 'ar', label: 'Arabic', nativeLabel: 'العربية', isRTL: true },
  { value: 'he', label: 'Hebrew', nativeLabel: 'עברית', isRTL: true }
];

export const DEFAULT_LANGUAGE: SupportedLanguage = 'en';

/**
 * Get RTL configuration for a specific language
 * @param language - The language code to check
 * @returns Whether the language is RTL (right-to-left)
 */
export function isRTL(language: SupportedLanguage): boolean {
  const langConfig = AVAILABLE_LANGUAGES.find(lang => lang.value === language);
  return langConfig?.isRTL ?? false;
}

/**
 * Get language configuration by language code
 * @param language - The language code
 * @returns Language configuration object or undefined if not found
 */
export function getLanguageConfig(language: SupportedLanguage): LanguageConfig | undefined {
  return AVAILABLE_LANGUAGES.find(lang => lang.value === language);
}
