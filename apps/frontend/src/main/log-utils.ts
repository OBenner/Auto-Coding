/**
 * Log sanitization utility to prevent log injection attacks.
 *
 * Strips control characters (ASCII 0x00-0x1F and 0x7F) from values
 * before they are interpolated into log messages, and truncates to
 * a maximum length to prevent log flooding.
 */

// biome-ignore lint/suspicious/noControlCharactersInRegex: Intentional - stripping control characters to prevent log injection
const CONTROL_CHARS = /[\x00-\x1f\x7f]/g;

/**
 * Sanitize a value for safe inclusion in log output.
 *
 * Converts the value to a string, removes ASCII control characters
 * (which could be used for log injection / terminal escape attacks),
 * and truncates to `maxLen` characters.
 */
export function sanitizeForLog(value: unknown, maxLen = 200): string {
  return String(value).replace(CONTROL_CHARS, '').slice(0, maxLen);
}
