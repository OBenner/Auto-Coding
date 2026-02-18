import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { isDebugEnabled, debugLog, debugWarn, debugError } from '../debug-logger';

describe('debug-logger', () => {
  const originalEnv = process.env.DEBUG;

  beforeEach(() => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    process.env.DEBUG = originalEnv;
    vi.restoreAllMocks();
  });

  describe('isDebugEnabled', () => {
    it('should return true when DEBUG=true', () => {
      process.env.DEBUG = 'true';
      expect(isDebugEnabled()).toBe(true);
    });

    it('should return false when DEBUG is not set', () => {
      delete process.env.DEBUG;
      expect(isDebugEnabled()).toBe(false);
    });

    it('should return false when DEBUG is other value', () => {
      process.env.DEBUG = 'false';
      expect(isDebugEnabled()).toBe(false);
    });
  });

  describe('debugLog', () => {
    it('should log when debug is enabled', () => {
      process.env.DEBUG = 'true';
      debugLog('test message', 123);
      expect(console.warn).toHaveBeenCalledWith('test message', 123);
    });

    it('should not log when debug is disabled', () => {
      process.env.DEBUG = 'false';
      debugLog('test message');
      expect(console.warn).not.toHaveBeenCalled();
    });
  });

  describe('debugWarn', () => {
    it('should warn when debug is enabled', () => {
      process.env.DEBUG = 'true';
      debugWarn('warning!');
      expect(console.warn).toHaveBeenCalledWith('warning!');
    });

    it('should not warn when debug is disabled', () => {
      delete process.env.DEBUG;
      debugWarn('warning!');
      expect(console.warn).not.toHaveBeenCalled();
    });
  });

  describe('debugError', () => {
    it('should error when debug is enabled', () => {
      process.env.DEBUG = 'true';
      debugError('error!');
      expect(console.error).toHaveBeenCalledWith('error!');
    });

    it('should not error when debug is disabled', () => {
      delete process.env.DEBUG;
      debugError('error!');
      expect(console.error).not.toHaveBeenCalled();
    });
  });
});
