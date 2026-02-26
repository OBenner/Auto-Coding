import { describe, it, expect } from 'vitest';
import { maskUserPaths, processEvent, PRODUCTION_TRACE_SAMPLE_RATE } from '../sentry-privacy';
import type { SentryErrorEvent } from '../sentry-privacy';

describe('sentry-privacy', () => {
  describe('maskUserPaths', () => {
    it('should mask macOS user paths', () => {
      expect(maskUserPaths('/Users/johndoe/projects/app/index.ts')).toBe(
        '/Users/***/projects/app/index.ts'
      );
    });

    it('should mask macOS user paths at end of string', () => {
      expect(maskUserPaths('/Users/johndoe')).toBe('/Users/***');
    });

    it('should mask Windows user paths', () => {
      expect(maskUserPaths('C:\\Users\\johndoe\\Documents\\app\\main.ts')).toBe(
        'C:\\Users\\***\\Documents\\app\\main.ts'
      );
    });

    it('should mask Windows user paths at end of string', () => {
      expect(maskUserPaths('C:\\Users\\johndoe')).toBe('C:\\Users\\***');
    });

    it('should mask Windows paths case-insensitively', () => {
      expect(maskUserPaths('d:\\Users\\admin\\file.txt')).toBe(
        'd:\\Users\\***\\file.txt'
      );
    });

    it('should mask Linux user paths', () => {
      expect(maskUserPaths('/home/ubuntu/workspace/file.py')).toBe(
        '/home/***/workspace/file.py'
      );
    });

    it('should mask Linux user paths at end of string', () => {
      expect(maskUserPaths('/home/ubuntu')).toBe('/home/***');
    });

    it('should mask multiple paths in one string', () => {
      const text = 'Error at /Users/alice/app.js, see /home/bob/logs/err.log';
      expect(maskUserPaths(text)).toBe(
        'Error at /Users/***/app.js, see /home/***/logs/err.log'
      );
    });

    it('should return empty/falsy strings unchanged', () => {
      expect(maskUserPaths('')).toBe('');
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      expect(maskUserPaths(null as any)).toBe(null);
    });

    it('should not modify strings without user paths', () => {
      expect(maskUserPaths('no paths here')).toBe('no paths here');
      expect(maskUserPaths('/usr/local/bin/node')).toBe('/usr/local/bin/node');
    });
  });

  describe('processEvent', () => {
    it('should mask paths in exception stack traces', () => {
      const event: SentryErrorEvent = {
        exception: {
          values: [
            {
              stacktrace: {
                frames: [
                  {
                    filename: '/Users/dev/project/src/app.ts',
                    abs_path: '/Users/dev/project/src/app.ts',
                  },
                ],
              },
              value: 'Error in /Users/dev/project/src/app.ts',
            },
          ],
        },
      };

      const result = processEvent(event);

      const frame = result.exception!.values![0].stacktrace!.frames![0];
      expect(frame.filename).toBe('/Users/***/project/src/app.ts');
      expect(frame.abs_path).toBe('/Users/***/project/src/app.ts');
      expect(result.exception!.values![0].value).toBe(
        'Error in /Users/***/project/src/app.ts'
      );
    });

    it('should mask paths in breadcrumbs', () => {
      const event: SentryErrorEvent = {
        breadcrumbs: [
          {
            message: 'Loading /home/user/config.json',
            data: { path: '/home/user/config.json', nested: { file: '/home/user/log.txt' } },
          },
        ],
      };

      const result = processEvent(event);

      expect(result.breadcrumbs![0].message).toBe('Loading /home/***/config.json');
      expect(result.breadcrumbs![0].data!.path).toBe('/home/***/config.json');
      expect((result.breadcrumbs![0].data!.nested as Record<string, string>).file).toBe(
        '/home/***/log.txt'
      );
    });

    it('should mask paths in top-level message', () => {
      const event: SentryErrorEvent = {
        message: 'Failed to read C:\\Users\\admin\\Desktop\\file.txt',
      };

      const result = processEvent(event);
      expect(result.message).toBe('Failed to read C:\\Users\\***\\Desktop\\file.txt');
    });

    it('should mask paths in tags', () => {
      const event: SentryErrorEvent = {
        tags: {
          projectPath: '/Users/dev/myproject',
          version: '1.0.0',
        },
      };

      const result = processEvent(event);
      expect(result.tags!.projectPath).toBe('/Users/***/myproject');
      expect(result.tags!.version).toBe('1.0.0');
    });

    it('should mask paths in contexts recursively', () => {
      const event: SentryErrorEvent = {
        contexts: {
          app: { dir: '/Users/dev/app', version: '2.0' },
          nullCtx: null,
        },
      };

      const result = processEvent(event);
      expect((result.contexts!.app as Record<string, unknown>).dir).toBe('/Users/***/app');
      expect(result.contexts!.nullCtx).toBeNull();
    });

    it('should mask paths in extra data', () => {
      const event: SentryErrorEvent = {
        extra: {
          logFile: '/home/user/app.log',
          count: 42,
        },
      };

      const result = processEvent(event);
      expect(result.extra!.logFile).toBe('/home/***/app.log');
      expect(result.extra!.count).toBe(42);
    });

    it('should clear user info entirely', () => {
      const event: SentryErrorEvent = {
        user: { id: '123', email: 'user@example.com', username: 'johndoe' },
      };

      const result = processEvent(event);
      expect(result.user).toEqual({});
    });

    it('should mask paths in request data', () => {
      const event: SentryErrorEvent = {
        request: {
          url: 'file:///Users/dev/project/index.html',
          headers: {
            referer: 'file:///Users/dev/project/main.html',
          },
          data: { path: '/home/user/data.json' },
        },
      };

      const result = processEvent(event);
      expect(result.request!.url).toBe('file:///Users/***/project/index.html');
      expect(result.request!.headers!.referer).toBe(
        'file:///Users/***/project/main.html'
      );
      expect((result.request!.data as Record<string, string>).path).toBe(
        '/home/***/data.json'
      );
    });

    it('should handle event with no fields gracefully', () => {
      const event: SentryErrorEvent = {};
      const result = processEvent(event);
      expect(result).toEqual({});
    });

    it('should handle event with empty exception values', () => {
      const event: SentryErrorEvent = {
        exception: { values: [] },
        breadcrumbs: [],
      };
      const result = processEvent(event);
      expect(result.exception!.values).toEqual([]);
    });
  });

  describe('PRODUCTION_TRACE_SAMPLE_RATE', () => {
    it('should be 0.1', () => {
      expect(PRODUCTION_TRACE_SAMPLE_RATE).toBe(0.1);
    });
  });
});
