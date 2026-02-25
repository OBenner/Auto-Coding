/**
 * @deprecated This module has been deprecated. Use `main/platform` instead.
 *
 * All platform-specific logic has been consolidated into `apps/frontend/src/main/platform/`.
 * This file is kept for backward compatibility but will be removed in a future release.
 *
 * Migration guide:
 * - Replace `import { ... } from '../shared/platform'` with `import { ... } from '../main/platform'`
 * - The API is identical, so no code changes are needed beyond the import path
 *
 * Platform abstraction for cross-platform operations.
 *
 * This module provides a centralized way to check the current platform
 * that can be easily mocked in tests. Tests can mock the getCurrentPlatform
 * function to test platform-specific behavior without relying on the
 * actual runtime platform.
 */

/**
 * Supported platform identifiers
 * @deprecated Use types from `main/platform/types` instead
 */
export type Platform = 'win32' | 'darwin' | 'linux' | 'unknown';

/**
 * Get the current platform identifier.
 *
 * In production, this returns the actual Node.js process.platform.
 * In tests, this can be mocked to test platform-specific behavior.
 *
 * @deprecated Use `getCurrentOS()` from `main/platform` instead
 * @returns The current platform identifier
 */
export function getCurrentPlatform(): Platform {
  const p = process.platform;
  if (p === 'win32' || p === 'darwin' || p === 'linux') {
    return p;
  }
  return 'unknown';
}

/**
 * Check if the current platform is Windows.
 *
 * @deprecated Use `isWindows()` from `main/platform` instead
 * @returns true if running on Windows
 */
export function isWindows(): boolean {
  return getCurrentPlatform() === 'win32';
}

/**
 * Check if the current platform is macOS.
 *
 * @deprecated Use `isMacOS()` from `main/platform` instead
 * @returns true if running on macOS
 */
export function isMacOS(): boolean {
  return getCurrentPlatform() === 'darwin';
}

/**
 * Check if the current platform is Linux.
 *
 * @deprecated Use `isLinux()` from `main/platform` instead
 * @returns true if running on Linux
 */
export function isLinux(): boolean {
  return getCurrentPlatform() === 'linux';
}

/**
 * Check if the current platform is Unix-like (macOS or Linux).
 *
 * @deprecated Use `isUnix()` from `main/platform` instead
 * @returns true if running on a Unix-like platform
 */
export function isUnix(): boolean {
  return isMacOS() || isLinux();
}
