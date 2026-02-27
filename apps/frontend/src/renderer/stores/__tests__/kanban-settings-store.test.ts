/**
 * @vitest-environment jsdom
 */

/**
 * Tests for kanban-settings-store (Zustand)
 * Column preferences, width clamping, collapse/lock, localStorage persistence,
 * filter state management, and filter reset
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  useKanbanSettingsStore,
  DEFAULT_COLUMN_WIDTH,
  MIN_COLUMN_WIDTH,
  MAX_COLUMN_WIDTH,
  COLLAPSED_COLUMN_WIDTH,
} from '../kanban-settings-store';
import { TASK_STATUS_COLUMNS } from '../../../shared/constants/task';

describe('kanban-settings-store', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // Reset store
    useKanbanSettingsStore.setState({ columnPreferences: null, filters: null });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  describe('initial state', () => {
    it('should have null columnPreferences initially', () => {
      expect(useKanbanSettingsStore.getState().columnPreferences).toBeNull();
    });
  });

  describe('initializePreferences', () => {
    it('should create default preferences for all columns', () => {
      const { initializePreferences } = useKanbanSettingsStore.getState();
      initializePreferences();

      const state = useKanbanSettingsStore.getState();
      expect(state.columnPreferences).not.toBeNull();

      for (const column of TASK_STATUS_COLUMNS) {
        const prefs = state.columnPreferences?.[column];
        expect(prefs?.width).toBe(DEFAULT_COLUMN_WIDTH);
        expect(prefs?.isCollapsed).toBe(false);
        expect(prefs?.isLocked).toBe(false);
      }
    });

    it('should not overwrite existing preferences', () => {
      const { initializePreferences, setColumnWidth } = useKanbanSettingsStore.getState();
      initializePreferences();
      setColumnWidth('backlog', 400);

      // Re-initialize should not reset
      useKanbanSettingsStore.getState().initializePreferences();

      expect(useKanbanSettingsStore.getState().columnPreferences?.backlog.width).toBe(400);
    });

    it('should initialize filters with default values', () => {
      const { initializePreferences } = useKanbanSettingsStore.getState();
      initializePreferences();

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters).toBeDefined();
      expect(filters?.searchQuery).toBe('');
      expect(filters?.sortBy).toBe('manual');
      expect(filters?.sortOrder).toBe('asc');
    });

    it('should not reinitialize filters if already set', () => {
      const { initializePreferences, setSearchQuery } = useKanbanSettingsStore.getState();
      initializePreferences();
      setSearchQuery('test query');

      // Try to initialize again
      initializePreferences();

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('test query');
    });
  });

  describe('setColumnWidth', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should set column width', () => {
      const { setColumnWidth } = useKanbanSettingsStore.getState();
      setColumnWidth('backlog', 400);

      expect(useKanbanSettingsStore.getState().columnPreferences?.backlog.width).toBe(400);
    });

    it('should clamp width to minimum', () => {
      const { setColumnWidth } = useKanbanSettingsStore.getState();
      setColumnWidth('backlog', 50);

      expect(useKanbanSettingsStore.getState().columnPreferences?.backlog.width).toBe(MIN_COLUMN_WIDTH);
    });

    it('should clamp width to maximum', () => {
      const { setColumnWidth } = useKanbanSettingsStore.getState();
      setColumnWidth('backlog', 1000);

      expect(useKanbanSettingsStore.getState().columnPreferences?.backlog.width).toBe(MAX_COLUMN_WIDTH);
    });

    it('should not change width on locked column', () => {
      const { setColumnWidth, toggleColumnLocked } = useKanbanSettingsStore.getState();
      toggleColumnLocked('backlog');

      setColumnWidth('backlog', 500);

      expect(useKanbanSettingsStore.getState().columnPreferences?.backlog.width).toBe(DEFAULT_COLUMN_WIDTH);
    });

    it('should do nothing if preferences not initialized', () => {
      useKanbanSettingsStore.setState({ columnPreferences: null });
      const { setColumnWidth } = useKanbanSettingsStore.getState();

      // Should not throw
      setColumnWidth('backlog', 400);
      expect(useKanbanSettingsStore.getState().columnPreferences).toBeNull();
    });
  });

  describe('toggleColumnCollapsed', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should toggle collapsed state', () => {
      const { toggleColumnCollapsed } = useKanbanSettingsStore.getState();

      toggleColumnCollapsed('queue');
      expect(useKanbanSettingsStore.getState().columnPreferences?.queue.isCollapsed).toBe(true);

      useKanbanSettingsStore.getState().toggleColumnCollapsed('queue');
      expect(useKanbanSettingsStore.getState().columnPreferences?.queue.isCollapsed).toBe(false);
    });
  });

  describe('setColumnCollapsed', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should set collapsed state explicitly', () => {
      const { setColumnCollapsed } = useKanbanSettingsStore.getState();

      setColumnCollapsed('in_progress', true);
      expect(useKanbanSettingsStore.getState().columnPreferences?.in_progress.isCollapsed).toBe(true);

      setColumnCollapsed('in_progress', false);
      expect(useKanbanSettingsStore.getState().columnPreferences?.in_progress.isCollapsed).toBe(false);
    });
  });

  describe('toggleColumnLocked', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should toggle locked state', () => {
      const { toggleColumnLocked } = useKanbanSettingsStore.getState();

      toggleColumnLocked('done');
      expect(useKanbanSettingsStore.getState().columnPreferences?.done.isLocked).toBe(true);

      useKanbanSettingsStore.getState().toggleColumnLocked('done');
      expect(useKanbanSettingsStore.getState().columnPreferences?.done.isLocked).toBe(false);
    });
  });

  describe('setColumnLocked', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should set locked state explicitly', () => {
      const { setColumnLocked } = useKanbanSettingsStore.getState();

      setColumnLocked('ai_review', true);
      expect(useKanbanSettingsStore.getState().columnPreferences?.ai_review.isLocked).toBe(true);
    });
  });

  describe('localStorage persistence', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('savePreferences should persist to localStorage', () => {
      const { setColumnWidth, savePreferences } = useKanbanSettingsStore.getState();
      setColumnWidth('backlog', 450);

      const result = savePreferences('project-1');

      expect(result).toBe(true);
      const stored = localStorage.getItem('kanban-column-prefs-project-1');
      expect(stored).not.toBeNull();
      const parsed = JSON.parse(stored!);
      expect(parsed.backlog.width).toBe(450);
    });

    it('loadPreferences should restore from localStorage', () => {
      const { setColumnWidth, savePreferences } = useKanbanSettingsStore.getState();
      setColumnWidth('backlog', 450);
      setColumnWidth('done', 250);
      savePreferences('project-1');

      // Reset store
      useKanbanSettingsStore.setState({ columnPreferences: null });

      // Load
      useKanbanSettingsStore.getState().loadPreferences('project-1');

      const state = useKanbanSettingsStore.getState();
      expect(state.columnPreferences?.backlog.width).toBe(450);
      expect(state.columnPreferences?.done.width).toBe(250);
    });

    it('loadPreferences should use defaults when no stored data', () => {
      useKanbanSettingsStore.setState({ columnPreferences: null });

      useKanbanSettingsStore.getState().loadPreferences('nonexistent-project');

      const state = useKanbanSettingsStore.getState();
      expect(state.columnPreferences).not.toBeNull();
      expect(state.columnPreferences?.backlog.width).toBe(DEFAULT_COLUMN_WIDTH);
    });

    it('loadPreferences should use defaults on invalid stored data', () => {
      localStorage.setItem('kanban-column-prefs-bad', JSON.stringify({ invalid: true }));

      useKanbanSettingsStore.getState().loadPreferences('bad');

      const state = useKanbanSettingsStore.getState();
      expect(state.columnPreferences?.backlog.width).toBe(DEFAULT_COLUMN_WIDTH);
    });

    it('loadPreferences should use defaults on corrupt JSON', () => {
      localStorage.setItem('kanban-column-prefs-corrupt', 'not-json');

      useKanbanSettingsStore.getState().loadPreferences('corrupt');

      const state = useKanbanSettingsStore.getState();
      expect(state.columnPreferences).not.toBeNull();
    });

    it('savePreferences should return false when no preferences', () => {
      useKanbanSettingsStore.setState({ columnPreferences: null });

      const result = useKanbanSettingsStore.getState().savePreferences('project-1');
      expect(result).toBe(false);
    });
  });

  describe('resetPreferences', () => {
    it('should reset to defaults and clear localStorage', () => {
      useKanbanSettingsStore.getState().initializePreferences();
      useKanbanSettingsStore.getState().setColumnWidth('backlog', 500);
      useKanbanSettingsStore.getState().savePreferences('project-1');

      useKanbanSettingsStore.getState().resetPreferences('project-1');

      expect(useKanbanSettingsStore.getState().columnPreferences?.backlog.width).toBe(DEFAULT_COLUMN_WIDTH);
      expect(localStorage.getItem('kanban-column-prefs-project-1')).toBeNull();
    });
  });

  describe('getColumnPreferences', () => {
    it('should return column preferences', () => {
      useKanbanSettingsStore.getState().initializePreferences();

      const prefs = useKanbanSettingsStore.getState().getColumnPreferences('backlog');
      expect(prefs.width).toBe(DEFAULT_COLUMN_WIDTH);
      expect(prefs.isCollapsed).toBe(false);
      expect(prefs.isLocked).toBe(false);
    });

    it('should return defaults when not initialized', () => {
      const prefs = useKanbanSettingsStore.getState().getColumnPreferences('backlog');
      expect(prefs.width).toBe(DEFAULT_COLUMN_WIDTH);
      expect(prefs.isCollapsed).toBe(false);
      expect(prefs.isLocked).toBe(false);
    });
  });

  describe('constants', () => {
    it('should export correct constant values', () => {
      expect(DEFAULT_COLUMN_WIDTH).toBe(320);
      expect(MIN_COLUMN_WIDTH).toBe(180);
      expect(MAX_COLUMN_WIDTH).toBe(600);
      expect(COLLAPSED_COLUMN_WIDTH).toBe(48);
    });
  });
});

describe('KanbanSettingsStore - Filter State Management', () => {
  const TEST_PROJECT_ID = 'test-project-123';

  beforeEach(() => {
    useKanbanSettingsStore.setState({
      filters: null,
      columnPreferences: null
    });
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('Search Filter', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should set search query', () => {
      const { setSearchQuery } = useKanbanSettingsStore.getState();

      setSearchQuery('bug fix');

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('bug fix');
    });

    it('should update search query without affecting other filters', () => {
      const { setSearchQuery, setSortBy } = useKanbanSettingsStore.getState();

      setSortBy('priority');
      setSearchQuery('authentication');

      const { filters } = useKanbanSettingsStore.getState();

      expect(filters?.searchQuery).toBe('authentication');
      expect(filters?.sortBy).toBe('priority');
      expect(filters?.sortOrder).toBe('asc');
    });

    it('should handle empty search query', () => {
      const { setSearchQuery } = useKanbanSettingsStore.getState();

      setSearchQuery('test');
      setSearchQuery('');

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('');
    });

    it('should clear search query on reset', () => {
      const { setSearchQuery, resetFilters } = useKanbanSettingsStore.getState();

      setSearchQuery('important task');
      resetFilters(TEST_PROJECT_ID);

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('');
    });
  });

  describe('Sort Mode', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should set sort mode to priority', () => {
      const { setSortBy } = useKanbanSettingsStore.getState();

      setSortBy('priority');

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.sortBy).toBe('priority');
    });

    it('should set sort mode to created date', () => {
      const { setSortBy } = useKanbanSettingsStore.getState();

      setSortBy('created');

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.sortBy).toBe('created');
    });

    it('should set sort mode to updated date', () => {
      const { setSortBy } = useKanbanSettingsStore.getState();

      setSortBy('updated');

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.sortBy).toBe('updated');
    });

    it('should default to manual sort', () => {
      const { initializePreferences } = useKanbanSettingsStore.getState();

      initializePreferences();

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.sortBy).toBe('manual');
    });

    it('should update sort mode without affecting other filters', () => {
      const { setSearchQuery, setSortBy } = useKanbanSettingsStore.getState();

      setSearchQuery('test query');
      setSortBy('priority');

      const { filters } = useKanbanSettingsStore.getState();

      expect(filters?.sortBy).toBe('priority');
      expect(filters?.searchQuery).toBe('test query');
    });
  });

  describe('Filter Persistence', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should save filters to localStorage with project ID', () => {
      const { setSearchQuery, setSortBy, saveFilters } = useKanbanSettingsStore.getState();

      setSearchQuery('important');
      setSortBy('priority');

      const success = saveFilters(TEST_PROJECT_ID);

      expect(success).toBe(true);

      const stored = localStorage.getItem(`kanban-filters-${TEST_PROJECT_ID}`);
      expect(stored).toBeDefined();

      const parsed = JSON.parse(stored!);
      expect(parsed.searchQuery).toBe('important');
      expect(parsed.sortBy).toBe('priority');
    });

    it('should load filters from localStorage', () => {
      const { setSearchQuery, setSortBy, saveFilters, loadFilters } = useKanbanSettingsStore.getState();

      setSearchQuery('test task');
      setSortBy('created');
      saveFilters(TEST_PROJECT_ID);

      useKanbanSettingsStore.setState({ filters: null });

      loadFilters(TEST_PROJECT_ID);

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('test task');
      expect(filters?.sortBy).toBe('created');
    });

    it('should validate filters before loading', () => {
      localStorage.setItem(`kanban-filters-${TEST_PROJECT_ID}`, JSON.stringify({
        searchQuery: 'valid',
        sortBy: 'invalid-sort-mode',
        sortOrder: 'asc'
      }));

      const { loadFilters } = useKanbanSettingsStore.getState();

      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      loadFilters(TEST_PROJECT_ID);

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.sortBy).toBe('manual');

      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Invalid filters in localStorage')
      );

      warnSpy.mockRestore();
    });

    it('should handle localStorage errors gracefully', () => {
      const { saveFilters } = useKanbanSettingsStore.getState();

      const originalSetItem = localStorage.setItem;
      localStorage.setItem = vi.fn(() => {
        throw new Error('Storage quota exceeded');
      });

      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const success = saveFilters(TEST_PROJECT_ID);

      expect(success).toBe(false);
      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to save filters'),
        expect.any(Error)
      );

      localStorage.setItem = originalSetItem;
      errorSpy.mockRestore();
    });

    it('should isolate filters by project ID', () => {
      const { setSearchQuery, setSortBy, saveFilters } = useKanbanSettingsStore.getState();

      setSearchQuery('project one');
      setSortBy('priority');
      saveFilters('project-1');

      setSearchQuery('project two');
      setSortBy('created');
      saveFilters('project-2');

      useKanbanSettingsStore.getState().loadFilters('project-1');
      let { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('project one');
      expect(filters?.sortBy).toBe('priority');

      useKanbanSettingsStore.getState().loadFilters('project-2');
      filters = useKanbanSettingsStore.getState().filters;
      expect(filters?.searchQuery).toBe('project two');
      expect(filters?.sortBy).toBe('created');
    });
  });

  describe('Filter Reset', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should reset filters to defaults', () => {
      const { setSearchQuery, setSortBy, resetFilters } = useKanbanSettingsStore.getState();

      setSearchQuery('test query');
      setSortBy('priority');

      resetFilters(TEST_PROJECT_ID);

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('');
      expect(filters?.sortBy).toBe('manual');
      expect(filters?.sortOrder).toBe('asc');
    });

    it('should remove filters from localStorage on reset', () => {
      const { setSearchQuery, saveFilters, resetFilters } = useKanbanSettingsStore.getState();

      setSearchQuery('test');
      saveFilters(TEST_PROJECT_ID);

      expect(localStorage.getItem(`kanban-filters-${TEST_PROJECT_ID}`)).toBeDefined();

      resetFilters(TEST_PROJECT_ID);

      expect(localStorage.getItem(`kanban-filters-${TEST_PROJECT_ID}`)).toBeNull();
    });

    it('should handle reset errors gracefully', () => {
      const { resetFilters } = useKanbanSettingsStore.getState();

      const originalRemoveItem = localStorage.removeItem;
      localStorage.removeItem = vi.fn(() => {
        throw new Error('Storage error');
      });

      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      resetFilters(TEST_PROJECT_ID);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to reset filters'),
        expect.any(Error)
      );

      localStorage.removeItem = originalRemoveItem;
      errorSpy.mockRestore();
    });
  });

  describe('Multi-Filter Combination', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should combine search and sort filters', () => {
      const { setSearchQuery, setSortBy } = useKanbanSettingsStore.getState();

      setSearchQuery('bug');
      setSortBy('priority');

      const { filters } = useKanbanSettingsStore.getState();

      expect(filters?.searchQuery).toBe('bug');
      expect(filters?.sortBy).toBe('priority');
    });

    it('should maintain all filter values when updating one', () => {
      const { setSearchQuery, setSortBy } = useKanbanSettingsStore.getState();

      setSearchQuery('authentication');
      setSortBy('created');

      setSearchQuery('login');

      const { filters } = useKanbanSettingsStore.getState();

      expect(filters?.searchQuery).toBe('login');
      expect(filters?.sortBy).toBe('created');
      expect(filters?.sortOrder).toBe('asc');
    });

    it('should persist combined filters correctly', () => {
      const { setSearchQuery, setSortBy, saveFilters, loadFilters } = useKanbanSettingsStore.getState();

      setSearchQuery('feature request');
      setSortBy('updated');

      saveFilters(TEST_PROJECT_ID);

      useKanbanSettingsStore.setState({ filters: null });

      loadFilters(TEST_PROJECT_ID);

      const { filters } = useKanbanSettingsStore.getState();

      expect(filters?.searchQuery).toBe('feature request');
      expect(filters?.sortBy).toBe('updated');
    });
  });

  describe('Edge Cases', () => {
    it('should handle operations when filters are null', () => {
      useKanbanSettingsStore.setState({ filters: null });

      const { setSearchQuery, setSortBy } = useKanbanSettingsStore.getState();

      setSearchQuery('test');
      setSortBy('priority');

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters).toBeNull();
    });

    it('should handle invalid JSON in localStorage', () => {
      localStorage.setItem(`kanban-filters-${TEST_PROJECT_ID}`, 'invalid json{');

      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const { loadFilters } = useKanbanSettingsStore.getState();
      loadFilters(TEST_PROJECT_ID);

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.sortBy).toBe('manual');

      errorSpy.mockRestore();
    });

    it('should handle saveFilters when filters are null', () => {
      useKanbanSettingsStore.setState({ filters: null });

      const { saveFilters } = useKanbanSettingsStore.getState();
      const success = saveFilters(TEST_PROJECT_ID);

      expect(success).toBe(false);
    });

    it('should handle loadFilters with no stored data', () => {
      const { loadFilters } = useKanbanSettingsStore.getState();

      loadFilters(TEST_PROJECT_ID);

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('');
      expect(filters?.sortBy).toBe('manual');
    });
  });
});
