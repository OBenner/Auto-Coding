import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import path from 'path';
import { promises as fsPromises } from 'fs';
import { IPC_CHANNELS } from '../../shared/constants';
import type { IPCResult } from '../../shared/types';
import { projectStore } from '../project-store';

/**
 * Search result types
 */

export interface UnifiedSearchResult {
  files: Array<{
    file_path: string;
    score: number;
    matches: string[];
  }>;
  purpose: Array<{
    entity_name: string;
    entity_type: string;
    purpose: string;
    file_path: string;
    lineno: string | number;
    score: number;
  }>;
  patterns: Array<{
    content: string;
    score: number;
    type: string;
    category?: string;
  }>;
  total: number;
}

export interface PurposeSearchResult {
  entity_name: string;
  entity_type: string;
  purpose: string;
  file_path: string;
  lineno: string | number;
  score: number;
}

export interface PatternSearchResult {
  content: string;
  score: number;
  type: string;
  category?: string;
}

export interface CallerCalleeResult {
  caller?: string;
  callee?: string;
  file_path: string;
  lineno: string | number;
  call_type: string;
}

export interface SearchStatus {
  project_dir: string;
  graphiti_enabled: boolean;
  graphiti_initialized: boolean;
  code_relationships_available: boolean;
  graphiti_search_available: boolean;
  semantic_search_enabled: boolean;
}

export interface SavedSearch {
  name: string;
  query: string;
  search_type: string;
  filters: Record<string, unknown>;
  created_at: string;
  last_used: string | null;
  description: string | null;
  tags: string[];
}

/**
 * Helper: Look up a project by ID, returning an error result if not found.
 */
function getProjectOrFail(projectId: string): { success: false; error: string } | { success: true; project: { path: string } } {
  const project = projectStore.getProject(projectId);
  if (!project) {
    return { success: false, error: 'Project not found' };
  }
  return { success: true, project };
}

/**
 * Helper: Extract a human-readable message from an unknown error value.
 */
function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

/**
 * Helper: Run a Python CLI script inside a project and return its stdout.
 */
function runPythonCli(projectPath: string, args: string[], errorPrefix: string): Promise<string> {
  const { spawn } = require('child_process');

  const pythonCmd = path.join(projectPath, 'apps', 'backend', '.venv', 'bin', 'python');
  const searchScript = path.join(projectPath, 'apps', 'backend', 'cli', 'search_commands.py');

  return new Promise<string>((resolve, reject) => {
    let stdout = '';
    let stderr = '';

    const proc = spawn(pythonCmd, [searchScript, ...args], {
      cwd: projectPath,
      env: process.env,
    });

    proc.stdout?.on('data', (data: Buffer) => {
      stdout += data.toString();
    });

    proc.stderr?.on('data', (data: Buffer) => {
      stderr += data.toString();
    });

    proc.on('close', (code: number) => {
      if (code === 0) {
        resolve(stdout);
      } else {
        reject(new Error(`${errorPrefix} failed with code ${code}: ${stderr}`));
      }
    });

    proc.on('error', (err: Error) => {
      reject(err);
    });
  });
}

/**
 * Helper: Get the path to the saved searches JSON file for a project.
 */
function savedSearchesPath(projectPath: string): string {
  return path.join(projectPath, '.auto-claude', 'saved_searches.json');
}

/**
 * Helper: Load the saved searches data from disk, returning a default if the file doesn't exist.
 */
async function loadSavedSearchesData(filePath: string): Promise<{ searches: SavedSearch[] }> {
  if (!(await fileExists(filePath))) {
    return { searches: [] };
  }
  const content = await fsPromises.readFile(filePath, 'utf-8');
  return JSON.parse(content);
}

/**
 * Helper: Write saved searches data to disk, creating parent directories if needed.
 */
async function writeSavedSearchesData(filePath: string, data: { searches: SavedSearch[] }): Promise<void> {
  await fsPromises.mkdir(path.dirname(filePath), { recursive: true });
  await fsPromises.writeFile(filePath, JSON.stringify(data, null, 2), 'utf-8');
}

/**
 * Helper: Wrap an IPC handler body with project lookup and error handling.
 */
async function withProject<T>(
  projectId: string,
  fallbackError: string,
  handler: (project: { path: string }) => Promise<IPCResult<T>>,
): Promise<IPCResult<T>> {
  const lookup = getProjectOrFail(projectId);
  if (!lookup.success) {
    return lookup;
  }
  try {
    return await handler(lookup.project);
  } catch (error) {
    return { success: false, error: errorMessage(error, fallbackError) };
  }
}

/**
 * Register search handlers
 */
export function registerSearchHandlers(
  _getMainWindow: () => BrowserWindow | null
): void {
  // Perform code search
  ipcMain.handle(
    IPC_CHANNELS.SEARCH_CODE,
    async (
      _,
      projectId: string,
      query: string,
      searchType: string = 'unified',
      options: {
        limit?: number;
        entity_type?: string;
      } = {}
    ): Promise<IPCResult<UnifiedSearchResult | PurposeSearchResult[] | PatternSearchResult[] | CallerCalleeResult[]>> => {
      return withProject(projectId, 'Search failed', async (project) => {
        const args = [
          '--project-dir', project.path,
          '--search', query,
          '--search-type', searchType,
        ];

        if (options.limit) {
          args.push('--search-limit', options.limit.toString());
        }

        if (options.entity_type) {
          args.push('--search-entity-type', options.entity_type);
        }

        const result = await runPythonCli(project.path, args, 'Search');
        const searchResults = JSON.parse(result);

        return { success: true, data: searchResults };
      });
    }
  );

  // Get search system status
  ipcMain.handle(
    IPC_CHANNELS.SEARCH_GET_STATUS,
    async (_, projectId: string): Promise<IPCResult<SearchStatus>> => {
      return withProject(projectId, 'Failed to get search status', async (project) => {
        const result = await runPythonCli(
          project.path,
          ['--project-dir', project.path, '--search-status'],
          'Status check',
        );
        const status = JSON.parse(result);
        return { success: true, data: status };
      });
    }
  );

  // List saved searches
  ipcMain.handle(
    IPC_CHANNELS.SEARCH_SAVED_LIST,
    async (_, projectId: string): Promise<IPCResult<SavedSearch[]>> => {
      return withProject(projectId, 'Failed to list saved searches', async (project) => {
        const filePath = savedSearchesPath(project.path);
        const data = await loadSavedSearchesData(filePath);
        return { success: true, data: data.searches };
      });
    }
  );

  // Get a specific saved search
  ipcMain.handle(
    IPC_CHANNELS.SEARCH_SAVED_GET,
    async (_, projectId: string, name: string): Promise<IPCResult<SavedSearch>> => {
      return withProject(projectId, 'Failed to get saved search', async (project) => {
        const filePath = savedSearchesPath(project.path);

        if (!(await fileExists(filePath))) {
          return { success: false, error: 'Saved search not found' };
        }

        const data = await loadSavedSearchesData(filePath);
        const search = data.searches.find((s) => s.name === name);

        if (!search) {
          return { success: false, error: 'Saved search not found' };
        }

        return { success: true, data: search };
      });
    }
  );

  // Save a search
  ipcMain.handle(
    IPC_CHANNELS.SEARCH_SAVED_SAVE,
    async (
      _,
      projectId: string,
      search: Omit<SavedSearch, 'created_at' | 'last_used'>
    ): Promise<IPCResult<SavedSearch>> => {
      return withProject(projectId, 'Failed to save search', async (project) => {
        const filePath = savedSearchesPath(project.path);
        const data = await loadSavedSearchesData(filePath);

        // Check if search already exists
        const existingIndex = data.searches.findIndex((s) => s.name === search.name);

        const now = new Date().toISOString();
        const newSearch: SavedSearch = {
          ...search,
          created_at: existingIndex >= 0 ? data.searches[existingIndex].created_at : now,
          last_used: now,
        };

        if (existingIndex >= 0) {
          data.searches[existingIndex] = newSearch;
        } else {
          data.searches.push(newSearch);
        }

        await writeSavedSearchesData(filePath, data);

        return { success: true, data: newSearch };
      });
    }
  );

  // Update a saved search
  ipcMain.handle(
    IPC_CHANNELS.SEARCH_SAVED_UPDATE,
    async (
      _,
      projectId: string,
      name: string,
      updates: Partial<Omit<SavedSearch, 'name' | 'created_at'>>
    ): Promise<IPCResult<SavedSearch>> => {
      return withProject(projectId, 'Failed to update saved search', async (project) => {
        const filePath = savedSearchesPath(project.path);

        if (!(await fileExists(filePath))) {
          return { success: false, error: 'Saved search not found' };
        }

        const data = await loadSavedSearchesData(filePath);
        const index = data.searches.findIndex((s) => s.name === name);

        if (index < 0) {
          return { success: false, error: 'Saved search not found' };
        }

        // Update search
        data.searches[index] = {
          ...data.searches[index],
          ...updates,
          last_used: new Date().toISOString(),
        };

        await fsPromises.writeFile(filePath, JSON.stringify(data, null, 2), 'utf-8');

        return { success: true, data: data.searches[index] };
      });
    }
  );

  // Delete a saved search
  ipcMain.handle(
    IPC_CHANNELS.SEARCH_SAVED_DELETE,
    async (_, projectId: string, name: string): Promise<IPCResult<void>> => {
      return withProject(projectId, 'Failed to delete saved search', async (project) => {
        const filePath = savedSearchesPath(project.path);

        if (!(await fileExists(filePath))) {
          return { success: false, error: 'Saved search not found' };
        }

        const data = await loadSavedSearchesData(filePath);
        const index = data.searches.findIndex((s) => s.name === name);

        if (index < 0) {
          return { success: false, error: 'Saved search not found' };
        }

        data.searches.splice(index, 1);

        await fsPromises.writeFile(filePath, JSON.stringify(data, null, 2), 'utf-8');

        return { success: true };
      });
    }
  );

  // Export saved searches
  ipcMain.handle(
    IPC_CHANNELS.SEARCH_SAVED_EXPORT,
    async (
      _,
      projectId: string,
      outputPath?: string
    ): Promise<IPCResult<{ path: string; count: number }>> => {
      return withProject(projectId, 'Failed to export saved searches', async (project) => {
        const filePath = savedSearchesPath(project.path);

        if (!(await fileExists(filePath))) {
          return { success: false, error: 'No saved searches to export' };
        }

        const data = await loadSavedSearchesData(filePath);

        const exportPath = outputPath || path.join(project.path, 'saved_searches_export.json');

        await fsPromises.writeFile(exportPath, JSON.stringify({
          exported_at: new Date().toISOString(),
          count: data.searches.length,
          searches: data.searches,
        }, null, 2), 'utf-8');

        return {
          success: true,
          data: {
            path: exportPath,
            count: data.searches.length,
          },
        };
      });
    }
  );

  // Import saved searches
  ipcMain.handle(
    IPC_CHANNELS.SEARCH_SAVED_IMPORT,
    async (
      _,
      projectId: string,
      inputPath: string,
      mergeStrategy: 'error' | 'skip' | 'overwrite' = 'error'
    ): Promise<IPCResult<{ count: number }>> => {
      return withProject(projectId, 'Failed to import saved searches', async (project) => {
        const filePath = savedSearchesPath(project.path);

        // Load import file
        const importContent = await fsPromises.readFile(inputPath, 'utf-8');
        const importData = JSON.parse(importContent);

        if (!importData.searches) {
          return { success: false, error: 'Invalid import file format' };
        }

        // Load existing searches
        const data = await loadSavedSearchesData(filePath);

        let importedCount = 0;

        for (const search of importData.searches) {
          const existingIndex = data.searches.findIndex((s) => s.name === search.name);

          if (existingIndex >= 0) {
            if (mergeStrategy === 'error') {
              return { success: false, error: `Search '${search.name}' already exists` };
            } else if (mergeStrategy === 'skip') {
              continue;
            }
            // 'overwrite': proceed with import
          }

          if (existingIndex >= 0) {
            data.searches[existingIndex] = search;
          } else {
            data.searches.push(search);
          }

          importedCount++;
        }

        await writeSavedSearchesData(filePath, data);

        return { success: true, data: { count: importedCount } };
      });
    }
  );
}

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
