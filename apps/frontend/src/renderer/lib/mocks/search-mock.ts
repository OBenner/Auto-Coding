/**
 * Mock Search API for browser preview
 */

import type { SearchAPI } from '../../../preload/api/modules/search-api';

export const mockSearchAPI: SearchAPI = {
  searchCode: async () => ({ success: true as const, data: undefined }),
  searchGetStatus: async () => ({
    success: true as const,
    data: {
      project_dir: '/mock/project',
      graphiti_enabled: false,
      graphiti_initialized: false,
      code_relationships_available: false,
      graphiti_search_available: false,
      semantic_search_enabled: false
    }
  }),
  searchSavedList: async () => ({ success: true as const, data: [] }),
  searchSavedGet: async () => ({ success: false as const, error: 'Not implemented' }),
  searchSavedSave: async () => ({ success: false as const, error: 'Not implemented' }),
  searchSavedUpdate: async () => ({ success: false as const, error: 'Not implemented' }),
  searchSavedDelete: async () => ({ success: true as const }),
  searchSavedExport: async () => ({ success: true as const, data: { path: '/mock/export/searches.json', count: 0 } }),
  searchSavedImport: async () => ({ success: false as const, error: 'Not implemented' }),
};
