/**
 * Locale-Aware Formatting Utilities
 *
 * Provides utilities for formatting dates, numbers, and currency
 * according to the current locale from i18n.
 *
 * @example
 * ```tsx
 * import { formatDate, formatNumber, formatCurrency } from '@/shared/i18n/formatters';
 * import { useTranslation } from 'react-i18next';
 *
 * function MyComponent() {
 *   const { i18n } = useTranslation();
 *   const formatted = formatDate('2024-01-15', i18n.language);
 *   return <div>{formatted}</div>;
 * }
 * ```
 */

import i18n from './index';

/**
 * Format a date string according to the specified locale
 *
 * @param dateString - ISO date string or timestamp to format
 * @param locale - Locale code (e.g., 'en-US', 'fr-FR'). Defaults to current i18n language
 * @param options - Intl.DateTimeFormatOptions for custom formatting
 * @returns Formatted date string, or original string if invalid
 *
 * @example
 * formatDate('2024-01-15T10:30:00Z', 'en-US')
 * // Returns: "1/15/2024, 10:30:00 AM"
 *
 * @example
 * formatDate('2024-01-15T10:30:00Z', 'fr-FR')
 * // Returns: "15/01/2024 à 10:30:00"
 */
export function formatDate(
  dateString: string,
  locale?: string,
  options?: Intl.DateTimeFormatOptions
): string {
  if (!dateString) return '';

  try {
    const date = new Date(dateString);

    // Handle invalid dates
    if (Number.isNaN(date.getTime())) return dateString;

    // Use provided locale or current i18n language
    const targetLocale = locale || i18n.language;

    // Default options match the pattern from context/utils.ts
    const defaultOptions: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    };

    return date.toLocaleString(targetLocale, options || defaultOptions);
  } catch {
    // Return original string on any error
    return dateString;
  }
}

/**
 * Format a date to a short date-only string (no time)
 *
 * @param dateString - ISO date string to format
 * @param locale - Locale code. Defaults to current i18n language
 * @returns Formatted date string, or original string if invalid
 *
 * @example
 * formatDateShort('2024-01-15', 'en-US')
 * // Returns: "Jan 15, 2024"
 *
 * @example
 * formatDateShort('2024-01-15', 'fr-FR')
 * // Returns: "15 janv. 2024"
 */
export function formatDateShort(
  dateString: string,
  locale?: string
): string {
  return formatDate(dateString, locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Format a date to a time-only string (no date)
 *
 * @param dateString - ISO date string to format
 * @param locale - Locale code. Defaults to current i18n language
 * @returns Formatted time string, or original string if invalid
 *
 * @example
 * formatTime('2024-01-15T10:30:00Z', 'en-US')
 * // Returns: "10:30 AM"
 *
 * @example
 * formatTime('2024-01-15T14:30:00Z', 'fr-FR')
 * // Returns: "14:30"
 */
export function formatTime(dateString: string, locale?: string): string {
  return formatDate(dateString, locale, {
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * Format a date as a relative time string (e.g., "2 hours ago")
 *
 * @param dateString - ISO date string to format
 * @param locale - Locale code. Defaults to current i18n language
 * @returns Relative time string, or original string if invalid
 *
 * @example
 * formatRelativeTime('2024-01-15T10:00:00Z', 'en-US')
 * // Returns something like: "2 hours ago" (depending on current time)
 */
export function formatRelativeTime(dateString: string, locale?: string): string {
  if (!dateString) return '';

  try {
    const date = new Date(dateString);

    // Handle invalid dates
    if (Number.isNaN(date.getTime())) return dateString;

    const targetLocale = locale || i18n.language;
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    const rtf = new Intl.RelativeTimeFormat(targetLocale, { numeric: 'auto' });

    if (diffSecs < 60) {
      return rtf.format(-diffSecs, 'second');
    } else if (diffMins < 60) {
      return rtf.format(-diffMins, 'minute');
    } else if (diffHours < 24) {
      return rtf.format(-diffHours, 'hour');
    } else if (diffDays < 7) {
      return rtf.format(-diffDays, 'day');
    } else {
      // Fall back to absolute date for older dates
      return formatDateShort(dateString, targetLocale);
    }
  } catch {
    return dateString;
  }
}

/**
 * Format a number according to the specified locale
 *
 * @param value - Number to format
 * @param locale - Locale code. Defaults to current i18n language
 * @param options - Intl.NumberFormatOptions for custom formatting
 * @returns Formatted number string, or '0' if invalid
 *
 * @example
 * formatNumber(1234567.89, 'en-US')
 * // Returns: "1,234,567.89"
 *
 * @example
 * formatNumber(1234567.89, 'fr-FR')
 * // Returns: "1 234 567,89"
 */
export function formatNumber(
  value: number,
  locale?: string,
  options?: Intl.NumberFormatOptions
): string {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0';

  try {
    const targetLocale = locale || i18n.language;
    return new Intl.NumberFormat(targetLocale, options).format(value);
  } catch {
    // Fallback to basic string conversion
    return value.toString();
  }
}

/**
 * Format a number as a percentage
 *
 * @param value - Number between 0 and 1 to format as percentage
 * @param locale - Locale code. Defaults to current i18n language
 * @param options - Additional Intl.NumberFormatOptions
 * @returns Formatted percentage string, or '0%' if invalid
 *
 * @example
 * formatPercent(0.856, 'en-US')
 * // Returns: "85.6%"
 *
 * @example
 * formatPercent(0.856, 'fr-FR')
 * // Returns: "85,6 %"
 */
export function formatPercent(
  value: number,
  locale?: string,
  options?: Intl.NumberFormatOptions
): string {
  return formatNumber(value, locale, {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
    ...options
  });
}

/**
 * Format a number as currency
 *
 * @param value - Number to format as currency
 * @param currencyCode - ISO 4217 currency code (e.g., 'USD', 'EUR')
 * @param locale - Locale code. Defaults to current i18n language
 * @param options - Additional Intl.NumberFormatOptions
 * @returns Formatted currency string, or '$0' if invalid
 *
 * @example
 * formatCurrency(1234.56, 'USD', 'en-US')
 * // Returns: "$1,234.56"
 *
 * @example
 * formatCurrency(1234.56, 'EUR', 'fr-FR')
 * // Returns: "1 234,56 €"
 *
 * @example
 * formatCurrency(1234.56, 'JPY', 'ja-JP')
 * // Returns: "￥1,235" (JPY uses no decimal places by default)
 */
export function formatCurrency(
  value: number,
  currencyCode: string,
  locale?: string,
  options?: Intl.NumberFormatOptions
): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return `${currencyCode}0`;
  }

  try {
    const targetLocale = locale || i18n.language;
    return new Intl.NumberFormat(targetLocale, {
      style: 'currency',
      currency: currencyCode,
      ...options
    }).format(value);
  } catch {
    // Fallback to basic formatting
    return `${currencyCode}${value.toFixed(2)}`;
  }
}

/**
 * Format a file size in bytes to human-readable format
 *
 * @param bytes - Number of bytes
 * @param locale - Locale code. Defaults to current i18n language
 * @returns Formatted file size string (e.g., "1.5 MB")
 *
 * @example
 * formatFileSize(1536, 'en-US')
 * // Returns: "1.5 KB"
 *
 * @example
 * formatFileSize(1536, 'fr-FR')
 * // Returns: "1,5 Ko"
 */
export function formatFileSize(bytes: number, locale?: string): string {
  if (typeof bytes !== 'number' || Number.isNaN(bytes) || bytes < 0) return '0 B';

  const targetLocale = locale || i18n.language;
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  // Localize the unit names based on locale
  const getUnitSymbol = (unit: string, loc: string): string => {
    // French uses Ko, Mo, Go, To instead of KB, MB, GB, TB
    if (loc.startsWith('fr')) {
      const frenchUnits: Record<string, string> = {
        'B': 'o',
        'KB': 'Ko',
        'MB': 'Mo',
        'GB': 'Go',
        'TB': 'To'
      };
      return frenchUnits[unit] || unit;
    }
    return unit;
  };

  const formattedSize = formatNumber(size, targetLocale, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1
  });
  const unit = getUnitSymbol(units[unitIndex], targetLocale);

  return `${formattedSize} ${unit}`;
}

/**
 * Format a list of items as a conjunction (e.g., "A, B, and C")
 *
 * @param items - Array of strings to format
 * @param locale - Locale code. Defaults to current i18n language
 * @returns Formatted list string
 *
 * @example
 * formatList(['Apple', 'Banana', 'Cherry'], 'en-US')
 * // Returns: "Apple, Banana, and Cherry"
 *
 * @example
 * formatList(['Pomme', 'Banane', 'Cerise'], 'fr-FR')
 * // Returns: "Pomme, Banane et Cerise"
 */
export function formatList(items: string[], locale?: string): string {
  if (!items || items.length === 0) return '';
  if (items.length === 1) return items[0];

  try {
    const targetLocale = locale || i18n.language;

    // Check if Intl.ListFormat is available (ES2020+)
    if (typeof Intl !== 'undefined' && 'ListFormat' in Intl) {
      return new (Intl as any).ListFormat(targetLocale, {
        style: 'long',
        type: 'conjunction'
      }).format(items);
    }

    // Fallback for older browsers/environments
    if (targetLocale.startsWith('fr')) {
      // French: "A, B et C"
      return items.length === 2
        ? items.join(' et ')
        : `${items.slice(0, -1).join(', ')} et ${items[items.length - 1]}`;
    }

    // English default: "A, B, and C"
    return items.length === 2
      ? items.join(' and ')
      : `${items.slice(0, -1).join(', ')}, and ${items[items.length - 1]}`;
  } catch {
    // Final fallback to comma-separated list
    return items.join(', ');
  }
}
