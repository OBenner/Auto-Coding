/**
 * @vitest-environment node
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the platform module before importing shell-escape
vi.mock('../../platform', () => ({
  isWindows: vi.fn(() => false),
}));

import {
  escapeShellArg,
  escapeShellPath,
  buildCdCommand,
  escapeShellArgWindows,
  escapeForWindowsDoubleQuote,
  isPathSafe,
  parseFileReferenceDrop,
} from '../shell-escape';
import { isWindows } from '../../platform';

const mockedIsWindows = vi.mocked(isWindows);

describe('shell-escape utilities', () => {
  beforeEach(() => {
    mockedIsWindows.mockReturnValue(false);
  });

  describe('escapeShellArg', () => {
    it('should wrap simple string in single quotes', () => {
      expect(escapeShellArg('hello')).toBe("'hello'");
    });

    it('should wrap string with spaces in single quotes', () => {
      expect(escapeShellArg('hello world')).toBe("'hello world'");
    });

    it('should escape single quotes', () => {
      expect(escapeShellArg("it's")).toBe("'it'\\''s'");
    });

    it('should prevent command substitution', () => {
      expect(escapeShellArg('$(rm -rf /)')).toBe("'$(rm -rf /)'");
    });

    it('should prevent command injection via semicolons', () => {
      expect(escapeShellArg('test"; rm -rf / #')).toBe("'test\"; rm -rf / #'");
    });

    it('should handle empty string', () => {
      expect(escapeShellArg('')).toBe("''");
    });

    it('should prevent backtick command substitution', () => {
      expect(escapeShellArg('`whoami`')).toBe("'`whoami`'");
    });
  });

  describe('escapeShellPath', () => {
    it('should escape path the same as escapeShellArg', () => {
      expect(escapeShellPath('/usr/local/bin')).toBe("'/usr/local/bin'");
    });

    it('should handle paths with spaces', () => {
      expect(escapeShellPath('/path with spaces/file')).toBe("'/path with spaces/file'");
    });
  });

  describe('buildCdCommand (Unix)', () => {
    it('should build cd command with && separator on Unix', () => {
      expect(buildCdCommand('/home/user')).toBe("cd '/home/user' && ");
    });

    it('should return empty string for undefined path', () => {
      expect(buildCdCommand(undefined)).toBe('');
    });

    it('should return empty string for empty path', () => {
      expect(buildCdCommand('')).toBe('');
    });

    it('should escape paths with spaces', () => {
      expect(buildCdCommand('/my path')).toBe("cd '/my path' && ");
    });
  });

  describe('buildCdCommand (Windows)', () => {
    beforeEach(() => {
      mockedIsWindows.mockReturnValue(true);
    });

    it('should use cd /d and double quotes on Windows', () => {
      const result = buildCdCommand('C:\\Users\\test');
      expect(result).toBe('cd /d "C:\\Users\\test" && ');
    });

    it('should use ; separator for PowerShell', () => {
      const result = buildCdCommand('C:\\Users\\test', 'powershell');
      expect(result).toBe('cd /d "C:\\Users\\test"; ');
    });

    it('should use && separator for cmd', () => {
      const result = buildCdCommand('C:\\Users\\test', 'cmd');
      expect(result).toBe('cd /d "C:\\Users\\test" && ');
    });

    it('should escape percent signs in Windows paths', () => {
      const result = buildCdCommand('C:\\%PATH%\\dir');
      expect(result).toContain('%%PATH%%');
    });
  });

  describe('escapeShellArgWindows', () => {
    it('should escape caret (escape char)', () => {
      expect(escapeShellArgWindows('test^value')).toBe('test^^value');
    });

    it('should escape double quotes', () => {
      expect(escapeShellArgWindows('test"value')).toBe('test^"value');
    });

    it('should escape ampersand', () => {
      expect(escapeShellArgWindows('cmd1 & cmd2')).toBe('cmd1 ^& cmd2');
    });

    it('should escape pipe', () => {
      expect(escapeShellArgWindows('cmd1 | cmd2')).toBe('cmd1 ^| cmd2');
    });

    it('should escape < and >', () => {
      expect(escapeShellArgWindows('a < b > c')).toBe('a ^< b ^> c');
    });

    it('should escape percent signs', () => {
      expect(escapeShellArgWindows('%PATH%')).toBe('%%PATH%%');
    });

    it('should remove newlines', () => {
      expect(escapeShellArgWindows('line1\nline2')).toBe('line1line2');
    });

    it('should remove carriage returns', () => {
      expect(escapeShellArgWindows('line1\rline2')).toBe('line1line2');
    });

    it('should handle multiple special chars', () => {
      const result = escapeShellArgWindows('test & "val" | <ok>');
      expect(result).toBe('test ^& ^"val^" ^| ^<ok^>');
    });
  });

  describe('escapeForWindowsDoubleQuote', () => {
    it('should double embedded double quotes', () => {
      expect(escapeForWindowsDoubleQuote('path with "quotes"')).toBe('path with ""quotes""');
    });

    it('should escape percent signs', () => {
      expect(escapeForWindowsDoubleQuote('%PATH%')).toBe('%%PATH%%');
    });

    it('should remove newlines', () => {
      expect(escapeForWindowsDoubleQuote('line1\nline2')).toBe('line1line2');
    });

    it('should NOT escape carets (literal inside double quotes)', () => {
      expect(escapeForWindowsDoubleQuote('test^value')).toBe('test^value');
    });

    it('should NOT escape ampersands (protected by quotes)', () => {
      expect(escapeForWindowsDoubleQuote('Company & Co')).toBe('Company & Co');
    });
  });

  describe('isPathSafe', () => {
    it('should accept normal paths', () => {
      expect(isPathSafe('/home/user/project')).toBe(true);
      expect(isPathSafe('C:\\Users\\project')).toBe(true);
      expect(isPathSafe('./relative/path')).toBe(true);
    });

    it('should reject command substitution $(...)', () => {
      expect(isPathSafe('$(rm -rf /)')).toBe(false);
    });

    it('should reject backticks', () => {
      expect(isPathSafe('`whoami`')).toBe(false);
    });

    it('should reject pipes', () => {
      expect(isPathSafe('/path | cat /etc/passwd')).toBe(false);
    });

    it('should reject semicolons', () => {
      expect(isPathSafe('/path; rm -rf /')).toBe(false);
    });

    it('should reject && operator', () => {
      expect(isPathSafe('/path && echo hacked')).toBe(false);
    });

    it('should reject || operator', () => {
      expect(isPathSafe('/path || echo hacked')).toBe(false);
    });

    it('should reject output redirection', () => {
      expect(isPathSafe('/path > /etc/passwd')).toBe(false);
    });

    it('should reject input redirection', () => {
      expect(isPathSafe('/path < /etc/passwd')).toBe(false);
    });

    it('should reject newlines', () => {
      expect(isPathSafe('/path\nrm -rf /')).toBe(false);
    });

    it('should reject carriage returns', () => {
      expect(isPathSafe('/path\rrm -rf /')).toBe(false);
    });
  });

  describe('parseFileReferenceDrop', () => {
    function createMockDataTransfer(data: string | null): DataTransfer {
      return {
        getData: vi.fn((type: string) => {
          if (type === 'application/json') return data || '';
          return '';
        }),
      } as unknown as DataTransfer;
    }

    it('should parse valid file reference', () => {
      const json = JSON.stringify({
        type: 'file-reference',
        path: '/src/app.ts',
        name: 'app.ts',
        isDirectory: false,
      });
      const dt = createMockDataTransfer(json);
      const result = parseFileReferenceDrop(dt);

      expect(result).toEqual({
        type: 'file-reference',
        path: '/src/app.ts',
        name: 'app.ts',
        isDirectory: false,
      });
    });

    it('should parse directory reference', () => {
      const json = JSON.stringify({
        type: 'file-reference',
        path: '/src/components',
        name: 'components',
        isDirectory: true,
      });
      const dt = createMockDataTransfer(json);
      const result = parseFileReferenceDrop(dt);

      expect(result).not.toBeNull();
      expect(result?.isDirectory).toBe(true);
    });

    it('should return null for empty data', () => {
      const dt = createMockDataTransfer(null);
      expect(parseFileReferenceDrop(dt)).toBeNull();
    });

    it('should return null for invalid JSON', () => {
      const dt = createMockDataTransfer('not json');
      expect(parseFileReferenceDrop(dt)).toBeNull();
    });

    it('should return null for wrong type', () => {
      const json = JSON.stringify({ type: 'text', path: '/foo' });
      const dt = createMockDataTransfer(json);
      expect(parseFileReferenceDrop(dt)).toBeNull();
    });

    it('should return null for missing path', () => {
      const json = JSON.stringify({ type: 'file-reference' });
      const dt = createMockDataTransfer(json);
      expect(parseFileReferenceDrop(dt)).toBeNull();
    });

    it('should return null for empty path', () => {
      const json = JSON.stringify({ type: 'file-reference', path: '' });
      const dt = createMockDataTransfer(json);
      expect(parseFileReferenceDrop(dt)).toBeNull();
    });

    it('should default name to empty string if missing', () => {
      const json = JSON.stringify({ type: 'file-reference', path: '/foo' });
      const dt = createMockDataTransfer(json);
      const result = parseFileReferenceDrop(dt);

      expect(result).not.toBeNull();
      expect(result!.name).toBe('');
    });

    it('should default isDirectory to false if missing', () => {
      const json = JSON.stringify({ type: 'file-reference', path: '/foo' });
      const dt = createMockDataTransfer(json);
      const result = parseFileReferenceDrop(dt);

      expect(result).not.toBeNull();
      expect(result?.isDirectory).toBe(false);
    });
  });
});
