/**
 * @vitest-environment node
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  hasHardcodedText,
  localizeUsageWindowLabel,
  formatTimeRemaining,
  formatTimeRemainingSimple,
} from '../format-time';

describe('format-time utilities', () => {
  describe('hasHardcodedText', () => {
    it('should return true for undefined', () => {
      expect(hasHardcodedText(undefined)).toBe(true);
    });

    it('should return true for null', () => {
      expect(hasHardcodedText(null)).toBe(true);
    });

    it('should return true for empty string', () => {
      expect(hasHardcodedText('')).toBe(true);
    });

    it('should return true for whitespace-only string', () => {
      expect(hasHardcodedText('   ')).toBe(true);
    });

    it('should return true for "Unknown"', () => {
      expect(hasHardcodedText('Unknown')).toBe(true);
    });

    it('should return true for "Expired"', () => {
      expect(hasHardcodedText('Expired')).toBe(true);
    });

    it('should return false for normal text', () => {
      expect(hasHardcodedText('Resets in 2h')).toBe(false);
    });

    it('should return true for "Unknown" with whitespace', () => {
      expect(hasHardcodedText('  Unknown  ')).toBe(true);
    });
  });

  describe('localizeUsageWindowLabel', () => {
    const mockT = vi.fn((key: string) => {
      const translations: Record<string, string> = {
        'common:usage.window5Hour': '5-hour window',
        'common:usage.window7Day': '7-day window',
        'common:usage.window5HoursQuota': '5 Hours Quota',
        'common:usage.windowMonthlyToolsQuota': 'Monthly Tools Quota',
        'common:usage.sessionDefault': 'Current session',
      };
      return translations[key] || key;
    });

    beforeEach(() => {
      mockT.mockClear();
    });

    it('should return default for undefined label', () => {
      const result = localizeUsageWindowLabel(undefined, mockT);
      expect(result).toBe('Current session');
    });

    it('should translate new-format keys (with colon)', () => {
      const result = localizeUsageWindowLabel('common:usage.window5Hour', mockT);
      expect(result).toBe('5-hour window');
    });

    it('should return default for untranslated key (with colon)', () => {
      const result = localizeUsageWindowLabel('common:usage.unknown', mockT);
      expect(result).toBe('Current session');
    });

    it('should map legacy "5-hour window" string', () => {
      const result = localizeUsageWindowLabel('5-hour window', mockT);
      expect(result).toBe('5-hour window');
    });

    it('should map legacy "7-day window" string', () => {
      const result = localizeUsageWindowLabel('7-day window', mockT);
      expect(result).toBe('7-day window');
    });

    it('should return default for unknown legacy label', () => {
      const result = localizeUsageWindowLabel('Unknown Label', mockT);
      expect(result).toBe('Current session');
    });

    it('should use custom default key', () => {
      const customT = vi.fn((key: string) => {
        if (key === 'custom:default') return 'Custom Default';
        return key;
      });
      const result = localizeUsageWindowLabel(undefined, customT, 'custom:default');
      expect(result).toBe('Custom Default');
    });
  });

  describe('formatTimeRemaining', () => {
    const mockT = vi.fn((key: string, params?: Record<string, unknown>) => {
      if (key === 'common:usage.resetsInHours') {
        return `${params?.hours}h ${params?.minutes}m`;
      }
      if (key === 'common:usage.resetsInDays') {
        return `${params?.days}d ${params?.hours}h`;
      }
      return key;
    });

    beforeEach(() => {
      mockT.mockClear();
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should return undefined for undefined timestamp', () => {
      expect(formatTimeRemaining(undefined, mockT)).toBeUndefined();
    });

    it('should return undefined for invalid date', () => {
      expect(formatTimeRemaining('not-a-date', mockT)).toBeUndefined();
    });

    it('should return undefined for past dates', () => {
      vi.setSystemTime(new Date('2025-01-20T15:00:00Z'));
      expect(formatTimeRemaining('2025-01-20T14:00:00Z', mockT)).toBeUndefined();
    });

    it('should format hours and minutes for < 24h', () => {
      vi.setSystemTime(new Date('2025-01-20T12:00:00Z'));
      const result = formatTimeRemaining('2025-01-20T14:30:00Z', mockT);
      expect(result).toBe('2h 30m');
    });

    it('should format days and hours for >= 24h', () => {
      vi.setSystemTime(new Date('2025-01-20T12:00:00Z'));
      const result = formatTimeRemaining('2025-01-23T17:00:00Z', mockT);
      expect(result).toBe('3d 5h');
    });

    it('should use custom translation keys', () => {
      vi.setSystemTime(new Date('2025-01-20T12:00:00Z'));
      formatTimeRemaining('2025-01-20T14:30:00Z', mockT, {
        hoursKey: 'custom:hours',
      });
      expect(mockT).toHaveBeenCalledWith('custom:hours', expect.any(Object));
    });
  });

  describe('formatTimeRemainingSimple', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should return "Unknown" for undefined', () => {
      expect(formatTimeRemainingSimple(undefined)).toBe('Unknown');
    });

    it('should return "Unknown" for invalid date', () => {
      expect(formatTimeRemainingSimple('not-a-date')).toBe('Unknown');
    });

    it('should return "Expired" for past dates', () => {
      vi.setSystemTime(new Date('2025-01-20T15:00:00Z'));
      expect(formatTimeRemainingSimple('2025-01-20T14:00:00Z')).toBe('Expired');
    });

    it('should format as Xh Ym for < 24h', () => {
      vi.setSystemTime(new Date('2025-01-20T12:00:00Z'));
      expect(formatTimeRemainingSimple('2025-01-20T14:30:00Z')).toBe('2h 30m');
    });

    it('should format as Xd Yh for >= 24h', () => {
      vi.setSystemTime(new Date('2025-01-20T12:00:00Z'));
      expect(formatTimeRemainingSimple('2025-01-23T17:00:00Z')).toBe('3d 5h');
    });

    it('should handle 0h 0m', () => {
      vi.setSystemTime(new Date('2025-01-20T12:00:00Z'));
      expect(formatTimeRemainingSimple('2025-01-20T12:00:30Z')).toBe('0h 0m');
    });
  });
});
