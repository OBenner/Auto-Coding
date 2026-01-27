/**
 * File system utilities for ideation operations
 */

import { promises as fsPromises } from 'fs';
import type { RawIdeationData } from './types';

/**
 * Check if a file exists
 */
async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fsPromises.access(filePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Read ideation data from file
 */
export async function readIdeationFile(ideationPath: string): Promise<RawIdeationData | null> {
  if (!(await fileExists(ideationPath))) {
    return null;
  }

  try {
    const content = await fsPromises.readFile(ideationPath, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    throw new Error(
      error instanceof Error ? error.message : 'Failed to read ideation file'
    );
  }
}

/**
 * Write ideation data to file
 */
export async function writeIdeationFile(ideationPath: string, data: RawIdeationData): Promise<void> {
  try {
    await fsPromises.writeFile(ideationPath, JSON.stringify(data, null, 2));
  } catch (error) {
    throw new Error(
      error instanceof Error ? error.message : 'Failed to write ideation file'
    );
  }
}

/**
 * Update timestamp for ideation data
 */
export function updateIdeationTimestamp(data: RawIdeationData): void {
  data.updated_at = new Date().toISOString();
}
