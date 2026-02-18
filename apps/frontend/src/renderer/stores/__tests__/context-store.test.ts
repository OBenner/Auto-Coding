/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useContextStore } from '../context-store';

describe('context-store', () => {
  beforeEach(() => {
    useContextStore.getState().clearAll();
  });

  describe('initial state', () => {
    it('should have clean initial state', () => {
      const state = useContextStore.getState();
      expect(state.projectIndex).toBeNull();
      expect(state.indexLoading).toBe(false);
      expect(state.indexError).toBeNull();
      expect(state.memoryStatus).toBeNull();
      expect(state.memoryState).toBeNull();
      expect(state.memoryLoading).toBe(false);
      expect(state.memoryError).toBeNull();
      expect(state.recentMemories).toEqual([]);
      expect(state.memoriesLoading).toBe(false);
      expect(state.searchResults).toEqual([]);
      expect(state.searchLoading).toBe(false);
      expect(state.searchQuery).toBe('');
    });
  });

  describe('project index actions', () => {
    it('should set project index', () => {
      const mockIndex = { languages: ['typescript'], frameworks: ['react'] };
      useContextStore.getState().setProjectIndex(mockIndex as any);
      expect(useContextStore.getState().projectIndex).toEqual(mockIndex);
    });

    it('should set index loading', () => {
      useContextStore.getState().setIndexLoading(true);
      expect(useContextStore.getState().indexLoading).toBe(true);
    });

    it('should set index error', () => {
      useContextStore.getState().setIndexError('Failed to load');
      expect(useContextStore.getState().indexError).toBe('Failed to load');
    });
  });

  describe('memory actions', () => {
    it('should set memory status', () => {
      const status = { isEnabled: true, nodeCount: 5 };
      useContextStore.getState().setMemoryStatus(status as any);
      expect(useContextStore.getState().memoryStatus).toEqual(status);
    });

    it('should set memory state', () => {
      const memState = { isInitialized: true };
      useContextStore.getState().setMemoryState(memState as any);
      expect(useContextStore.getState().memoryState).toEqual(memState);
    });

    it('should set memory loading and error', () => {
      useContextStore.getState().setMemoryLoading(true);
      expect(useContextStore.getState().memoryLoading).toBe(true);

      useContextStore.getState().setMemoryError('connection failed');
      expect(useContextStore.getState().memoryError).toBe('connection failed');
    });

    it('should set recent memories', () => {
      const memories = [{ id: 'm1', content: 'test memory' }];
      useContextStore.getState().setRecentMemories(memories as any);
      expect(useContextStore.getState().recentMemories).toEqual(memories);
    });

    it('should set memories loading', () => {
      useContextStore.getState().setMemoriesLoading(true);
      expect(useContextStore.getState().memoriesLoading).toBe(true);
    });
  });

  describe('search actions', () => {
    it('should set search results', () => {
      const results = [{ type: 'memory', content: 'found' }];
      useContextStore.getState().setSearchResults(results as any);
      expect(useContextStore.getState().searchResults).toEqual(results);
    });

    it('should set search loading', () => {
      useContextStore.getState().setSearchLoading(true);
      expect(useContextStore.getState().searchLoading).toBe(true);
    });

    it('should set search query', () => {
      useContextStore.getState().setSearchQuery('test query');
      expect(useContextStore.getState().searchQuery).toBe('test query');
    });
  });

  describe('clearAll', () => {
    it('should reset all state to initial values', () => {
      // Set various state
      useContextStore.setState({
        projectIndex: { languages: [] } as any,
        indexLoading: true,
        indexError: 'error',
        memoryStatus: { isEnabled: true } as any,
        memoryState: { isInitialized: true } as any,
        memoryLoading: true,
        memoryError: 'mem error',
        recentMemories: [{ id: 'm1' }] as any,
        memoriesLoading: true,
        searchResults: [{ type: 'test' }] as any,
        searchLoading: true,
        searchQuery: 'query',
      });

      useContextStore.getState().clearAll();

      const state = useContextStore.getState();
      expect(state.projectIndex).toBeNull();
      expect(state.indexLoading).toBe(false);
      expect(state.indexError).toBeNull();
      expect(state.memoryStatus).toBeNull();
      expect(state.memoryState).toBeNull();
      expect(state.memoryLoading).toBe(false);
      expect(state.memoryError).toBeNull();
      expect(state.recentMemories).toEqual([]);
      expect(state.memoriesLoading).toBe(false);
      expect(state.searchResults).toEqual([]);
      expect(state.searchLoading).toBe(false);
      expect(state.searchQuery).toBe('');
    });
  });
});
