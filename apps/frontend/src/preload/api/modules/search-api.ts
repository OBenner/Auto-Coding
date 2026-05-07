import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult } from '../../../shared/types';
import { invokeIpc } from './ipc-utils';

/**
 * Saved search type
 */
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
 * Search status type
 */
export interface SearchStatus {
  project_dir: string;
  graphiti_enabled: boolean;
  graphiti_initialized: boolean;
  code_relationships_available: boolean;
  graphiti_search_available: boolean;
  semantic_search_enabled: boolean;
}

/**
 * Search API operations
 */
export interface SearchAPI {
  /** Perform code search */
  searchCode: (
    projectId: string,
    query: string,
    searchType?: string,
    options?: {
      limit?: number;
      entity_type?: string;
    }
  ) => Promise<IPCResult<unknown>>;

  /** Get search system status */
  searchGetStatus: (
    projectId: string
  ) => Promise<IPCResult<SearchStatus>>;

  /** List all saved searches */
  searchSavedList: (
    projectId: string
  ) => Promise<IPCResult<SavedSearch[]>>;

  /** Get a specific saved search */
  searchSavedGet: (
    projectId: string,
    name: string
  ) => Promise<IPCResult<SavedSearch>>;

  /** Save a search */
  searchSavedSave: (
    projectId: string,
    search: Omit<SavedSearch, 'created_at' | 'last_used'>
  ) => Promise<IPCResult<SavedSearch>>;

  /** Update a saved search */
  searchSavedUpdate: (
    projectId: string,
    name: string,
    updates: Partial<Omit<SavedSearch, 'name' | 'created_at'>>
  ) => Promise<IPCResult<SavedSearch>>;

  /** Delete a saved search */
  searchSavedDelete: (
    projectId: string,
    name: string
  ) => Promise<IPCResult<void>>;

  /** Export saved searches */
  searchSavedExport: (
    projectId: string,
    outputPath?: string
  ) => Promise<IPCResult<{ path: string; count: number }>>;

  /** Import saved searches */
  searchSavedImport: (
    projectId: string,
    inputPath: string,
    mergeStrategy?: 'error' | 'skip' | 'overwrite'
  ) => Promise<IPCResult<{ count: number }>>;
}

/**
 * Creates the Search API implementation
 */
export const createSearchAPI = (): SearchAPI => ({
  searchCode: (
    projectId: string,
    query: string,
    searchType = 'unified',
    options = {}
  ): Promise<IPCResult<unknown>> =>
    invokeIpc(IPC_CHANNELS.SEARCH_CODE, projectId, query, searchType, options),

  searchGetStatus: (
    projectId: string
  ): Promise<IPCResult<SearchStatus>> =>
    invokeIpc(IPC_CHANNELS.SEARCH_GET_STATUS, projectId),

  searchSavedList: (
    projectId: string
  ): Promise<IPCResult<SavedSearch[]>> =>
    invokeIpc(IPC_CHANNELS.SEARCH_SAVED_LIST, projectId),

  searchSavedGet: (
    projectId: string,
    name: string
  ): Promise<IPCResult<SavedSearch>> =>
    invokeIpc(IPC_CHANNELS.SEARCH_SAVED_GET, projectId, name),

  searchSavedSave: (
    projectId: string,
    search: Omit<SavedSearch, 'created_at' | 'last_used'>
  ): Promise<IPCResult<SavedSearch>> =>
    invokeIpc(IPC_CHANNELS.SEARCH_SAVED_SAVE, projectId, search),

  searchSavedUpdate: (
    projectId: string,
    name: string,
    updates: Partial<Omit<SavedSearch, 'name' | 'created_at'>>
  ): Promise<IPCResult<SavedSearch>> =>
    invokeIpc(IPC_CHANNELS.SEARCH_SAVED_UPDATE, projectId, name, updates),

  searchSavedDelete: (
    projectId: string,
    name: string
  ): Promise<IPCResult<void>> =>
    invokeIpc(IPC_CHANNELS.SEARCH_SAVED_DELETE, projectId, name),

  searchSavedExport: (
    projectId: string,
    outputPath?: string
  ): Promise<IPCResult<{ path: string; count: number }>> =>
    invokeIpc(IPC_CHANNELS.SEARCH_SAVED_EXPORT, projectId, outputPath),

  searchSavedImport: (
    projectId: string,
    inputPath: string,
    mergeStrategy: 'error' | 'skip' | 'overwrite' = 'error'
  ): Promise<IPCResult<{ count: number }>> =>
    invokeIpc(IPC_CHANNELS.SEARCH_SAVED_IMPORT, projectId, inputPath, mergeStrategy)
});
