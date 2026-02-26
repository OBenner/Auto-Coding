/**
 * Filesystem Utilities Module
 *
 * Provides utility functions for filesystem operations with
 * proper support for XDG Base Directory paths and sandboxed
 * environments (AppImage, Flatpak, Snap).
 */

import * as fs from 'fs';
import { promises as fsPromises } from 'fs';
import * as path from 'path';
import { getAppPath, isImmutableEnvironment, getMemoriesDir } from './config-paths';

/**
 * Ensure a directory exists, creating it if necessary
 *
 * @param dirPath - The path to the directory
 * @returns true if directory exists or was created, false on error
 */
export function ensureDir(dirPath: string): boolean {
  try {
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
    }
    return true;
  } catch (error) {
    console.error(`[fs-utils] Failed to create directory ${dirPath}:`, error);
    return false;
  }
}

/**
 * Ensure the application data directories exist
 * Creates config, data, cache, and memories directories
 */
export function ensureAppDirectories(): void {
  const dirs = [
    getAppPath('config'),
    getAppPath('data'),
    getAppPath('cache'),
    getMemoriesDir(),
  ];

  for (const dir of dirs) {
    ensureDir(dir);
  }
}

/**
 * Get a writable path for a file
 * If the original path is not writable, falls back to XDG data directory
 *
 * @param originalPath - The preferred path for the file
 * @param filename - The filename (used for fallback path)
 * @returns A writable path for the file
 */
export function getWritablePath(originalPath: string, filename: string): string {
  // Check if we can write to the original path
  const dir = path.dirname(originalPath);

  try {
    if (fs.existsSync(dir)) {
      // Try to write a test file
      const testFile = path.join(dir, `.write-test-${Date.now()}`);
      fs.writeFileSync(testFile, '');
      // Cleanup test file - ignore errors (e.g., file locked on Windows)
      try { fs.unlinkSync(testFile); } catch { /* ignore cleanup failure */ }
      return originalPath;
    } else {
      // Try to create the directory
      fs.mkdirSync(dir, { recursive: true });
      return originalPath;
    }
  } catch {
    // Fall back to XDG data directory
    if (isImmutableEnvironment()) {
      const fallbackDir = getAppPath('data');
      ensureDir(fallbackDir);
      console.warn(`[fs-utils] Falling back to XDG path for ${filename}: ${fallbackDir}`);
      return path.join(fallbackDir, filename);
    }
    // Non-immutable environment - just return original and let caller handle error
    return originalPath;
  }
}

/**
 * Safe write file that handles immutable filesystems
 * Falls back to XDG paths if the target is not writable
 *
 * @param filePath - The target file path
 * @param content - The content to write
 * @returns The actual path where the file was written
 * @throws Error if write fails (with context about the attempted path)
 */
export function safeWriteFile(filePath: string, content: string): string {
  const filename = path.basename(filePath);
  const writablePath = getWritablePath(filePath, filename);

  try {
    atomicWriteFileSync(writablePath, content, 'utf-8');
    return writablePath;
  } catch (error) {
    console.error(`[fs-utils] Failed to write file ${writablePath}:`, error);
    throw error;
  }
}

/**
 * Read a file, checking both original and XDG fallback locations
 *
 * @param originalPath - The expected file path
 * @returns The file content or null if not found or on error
 */
export function safeReadFile(originalPath: string): string | null {
  // Try original path first
  try {
    if (fs.existsSync(originalPath)) {
      return fs.readFileSync(originalPath, 'utf-8');
    }
  } catch (error) {
    console.error(`[fs-utils] Failed to read file ${originalPath}:`, error);
    // Fall through to try XDG fallback
  }

  // Try XDG fallback path
  if (isImmutableEnvironment()) {
    const filename = path.basename(originalPath);
    const fallbackPath = path.join(getAppPath('data'), filename);
    try {
      if (fs.existsSync(fallbackPath)) {
        return fs.readFileSync(fallbackPath, 'utf-8');
      }
    } catch (error) {
      console.error(`[fs-utils] Failed to read fallback file ${fallbackPath}:`, error);
    }
  }

  return null;
}

/**
 * Write a file atomically by writing to a temp file first, then renaming.
 * This prevents 0-byte corruption if the process crashes mid-write.
 *
 * @param filePath - The target file path
 * @param content - The content to write
 * @param encoding - File encoding (default: 'utf-8')
 */
export function atomicWriteFileSync(filePath: string, content: string, encoding: BufferEncoding = 'utf-8'): void {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  const uniqueSuffix = `${process.pid}-${Date.now()}`;
  const tmpPath = path.join(dir, `${path.basename(filePath)}.${uniqueSuffix}.tmp`);

  try {
    fs.writeFileSync(tmpPath, content, encoding);

    // On Windows, file watchers/antivirus can briefly lock files, causing EPERM on rename.
    // Retry with exponential backoff (100ms, 200ms, 400ms).
    let lastErr: unknown;
    for (let attempt = 0; attempt < 4; attempt++) {
      try {
        fs.renameSync(tmpPath, filePath);
        return; // Success
      } catch (renameErr) {
        const code = (renameErr as NodeJS.ErrnoException).code;
        if ((code === 'EPERM' || code === 'EACCES') && attempt < 3) {
          lastErr = renameErr;
          // Synchronous sleep via Atomics for retry delay
          const delay = 100 * 2 ** attempt;
          Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, delay);
          continue;
        }
        throw renameErr;
      }
    }
    throw lastErr;
  } catch (err) {
    try {
      if (fs.existsSync(tmpPath)) fs.unlinkSync(tmpPath);
    } catch { /* ignore cleanup */ }
    throw err;
  }
}

/**
 * Write a file atomically (async version).
 * Writes to a uniquely-named temp file first, then renames to prevent
 * 0-byte corruption and concurrent-write collisions.
 *
 * @param filePath - The target file path
 * @param content - The content to write
 * @param encoding - File encoding (default: 'utf-8')
 */
export async function atomicWriteFile(filePath: string, content: string, encoding: BufferEncoding = 'utf-8'): Promise<void> {
  const dir = path.dirname(filePath);
  await fsPromises.mkdir(dir, { recursive: true });

  const uniqueSuffix = `${process.pid}-${Date.now()}`;
  const tmpPath = path.join(dir, `${path.basename(filePath)}.${uniqueSuffix}.tmp`);

  try {
    await fsPromises.writeFile(tmpPath, content, encoding);
    await fsPromises.rename(tmpPath, filePath);
  } catch (err) {
    try { await fsPromises.unlink(tmpPath); } catch { /* ignore cleanup */ }
    throw err;
  }
}
