import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { isRTL, type SupportedLanguage } from '../../shared/constants/i18n';

export interface RTLInfo {
  /** Whether the current language is right-to-left */
  isRTL: boolean;
  /** Text direction for CSS: 'ltr' or 'rtl' */
  direction: 'ltr' | 'rtl';
  /** Current language code */
  language: string;
}

/**
 * Hook to manage RTL (right-to-left) language support.
 *
 * Provides information about text direction for the current language
 * and automatically updates the document's dir attribute.
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { isRTL, direction } = useRTL();
 *
 *   return (
 *     <div dir={direction}>
 *       {isRTL ? <ArrowLeft /> : <ArrowRight />}
 *     </div>
 *   );
 * }
 * ```
 *
 * @returns RTLInfo object containing isRTL, direction, and language
 */
export function useRTL(): RTLInfo {
  const { i18n } = useTranslation();
  const currentLanguage = i18n.language as SupportedLanguage;

  // Check if current language is RTL
  const isRTLLanguage = isRTL(currentLanguage);
  const direction: 'ltr' | 'rtl' = isRTLLanguage ? 'rtl' : 'ltr';

  // Update document dir attribute when language changes
  useEffect(() => {
    const updateDocumentDirection = () => {
      const lang = i18n.language as SupportedLanguage;
      const rtl = isRTL(lang);
      const dir = rtl ? 'rtl' : 'ltr';

      // Set dir attribute on document element
      if (document.documentElement.getAttribute('dir') !== dir) {
        document.documentElement.setAttribute('dir', dir);

        // Debug logging in development
        if (window.DEBUG) {
          console.warn(`[RTL] Document direction updated: ${dir} (language: ${lang})`);
        }
      }
    };

    // Update direction on mount and when language changes
    updateDocumentDirection();

    // Listen for language changes
    const handleLanguageChange = (lng: string) => {
      if (window.DEBUG) {
        console.warn(`[RTL] Language changed: ${lng}`);
      }
      updateDocumentDirection();
    };

    i18n.on('languageChanged', handleLanguageChange);

    // Cleanup listener on unmount
    return () => {
      i18n.off('languageChanged', handleLanguageChange);
    };
  }, [i18n]);

  return {
    isRTL: isRTLLanguage,
    direction,
    language: currentLanguage
  };
}

/**
 * Hook to get RTL info without side effects.
 * Use this if you only need to read RTL state and don't want
 * the document dir attribute to be managed automatically.
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const rtl = useRTLInfo();
 *   return <span style={{ textAlign: rtl.isRTL ? 'right' : 'left' }}>Text</span>;
 * }
 * ```
 *
 * @returns RTLInfo object containing isRTL, direction, and language
 */
export function useRTLInfo(): RTLInfo {
  const { i18n } = useTranslation();
  const currentLanguage = i18n.language as SupportedLanguage;
  const isRTLLanguage = isRTL(currentLanguage);
  const direction: 'ltr' | 'rtl' = isRTLLanguage ? 'rtl' : 'ltr';

  return {
    isRTL: isRTLLanguage,
    direction,
    language: currentLanguage
  };
}
