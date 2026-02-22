/**
 * Shared utilities for spec path operations
 *
 * These functions are used by both project-store.ts and crud-handlers.ts
 * to ensure consistent validation and path resolution.
 */
import path from 'path';
import { Dirent, promises as fsPromises } from 'fs';
import { getTaskWorktreeDir } from '../worktree-paths';

/**
 * Validate taskId to prevent path traversal attacks
 * Returns true if taskId is safe to use in path operations
 *
 * @param taskId - The task ID to validate
 * @returns true if the taskId is safe to use in path operations
 */
export function isValidTaskId(taskId: string): boolean {
  // Reject empty, null/undefined, or strings with path traversal characters
  if (!taskId || typeof taskId !== 'string') return false;
  if (taskId.includes('/') || taskId.includes('\\')) return false;
  if (taskId === '.' || taskId === '..') return false;
  if (taskId.includes('\0')) return false; // Null byte injection
  return true;
}

/**
 * Helper to check if a file exists asynchronously
 *
 * @param filePath - The path to check for existence
 * @returns Promise resolving to true if the file/directory exists, false otherwise
 */
export async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fsPromises.access(filePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Helper to read directory contents asynchronously
 *
 * @param dirPath - The directory path to read
 * @returns Promise resolving to array of Dirent objects, or empty array on error
 */
export async function readDirectory(dirPath: string): Promise<Dirent[]> {
  try {
    return await fsPromises.readdir(dirPath, { withFileTypes: true });
  } catch {
    return [];
  }
}

/**
 * Find ALL spec paths for a task, checking main directory and worktrees
 * A task can exist in multiple locations (main + worktree), so return all paths
 *
 * @param projectPath - The root path of the project
 * @param specsBaseDir - The relative path to specs directory (e.g., '.auto-claude/specs')
 * @param taskId - The task/spec ID to find
 * @param logPrefix - Optional prefix for log messages (defaults to '[SpecPathHelpers]')
 * @returns Promise resolving to array of absolute paths where the spec exists
 */
export async function findAllSpecPathsAsync(
  projectPath: string,
  specsBaseDir: string,
  taskId: string,
  logPrefix: string = '[SpecPathHelpers]'
): Promise<string[]> {
  // Validate taskId to prevent path traversal
  if (!isValidTaskId(taskId)) {
    console.error(`${logPrefix} findAllSpecPathsAsync: Invalid taskId rejected: ${taskId}`);
    return [];
  }

  const paths: string[] = [];

  // 1. Check main specs directory
  const mainSpecPath = path.join(projectPath, specsBaseDir, taskId);
  if (await fileExists(mainSpecPath)) {
    paths.push(mainSpecPath);
  }

  // 2. Check worktrees
  const worktreesDir = getTaskWorktreeDir(projectPath);
  if (await fileExists(worktreesDir)) {
    try {
      const worktrees = await readDirectory(worktreesDir);
      for (const worktree of worktrees) {
        if (!worktree.isDirectory()) continue;
        const worktreeSpecPath = path.join(worktreesDir, worktree.name, specsBaseDir, taskId);
        if (await fileExists(worktreeSpecPath)) {
          paths.push(worktreeSpecPath);
        }
      }
    } catch {
      // Ignore errors reading worktrees
    }
  }

  return paths;
}
