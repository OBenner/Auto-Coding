/**
 * @vitest-environment jsdom
 */

/**
 * Unit tests for kanban-settings-store filter functionality
 * Tests filter state management, localStorage persistence, and filter reset
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { useKanbanSettingsStore } from '../kanban-settings-store';

describe('KanbanSettingsStore - Filter State Management', () => {
  const TEST_PROJECT_ID = 'test-project-123';

  beforeEach(() => {
    // Reset store state before each test
    useKanbanSettingsStore.setState({
      filters: null,
      columnPreferences: null
    });

    // Clear localStorage
    localStorage.clear();
  });

  afterEach(() => {
    // Clean up localStorage after each test
    localStorage.clear();
  });

  describe('Filter Initialization', () => {
    it('should initialize filters with default values', () => {
      const { initializePreferences } = useKanbanSettingsStore.getState();

      // Initialize preferences
      initializePreferences();

      const { filters } = useKanbanSettingsStore.getState();

      expect(filters).toBeDefined();
      expect(filters?.searchQuery).toBe('');
      expect(filters?.sortBy).toBe('manual');
      expect(filters?.sortOrder).toBe('asc');
    });

    it('should not reinitialize filters if already set', () => {
      const { initializePreferences, setSearchQuery } = useKanbanSettingsStore.getState();

      // Initialize and set a filter
      initializePreferences();
      setSearchQuery('test query');

      // Try to initialize again
      initializePreferences();

      const { filters } = useKanbanSettingsStore.getState();

      // Should keep the previous search query
      expect(filters?.searchQuery).toBe('test query');
    });
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

      // Set initial state
      setSortBy('priority');
      setSearchQuery('authentication');

      const { filters } = useKanbanSettingsStore.getState();

      expect(filters?.searchQuery).toBe('authentication');
      expect(filters?.sortBy).toBe('priority');
      expect(filters?.sortOrder).toBe('asc'); // Should remain unchanged
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

      // Save filters
      setSearchQuery('test task');
      setSortBy('created');
      saveFilters(TEST_PROJECT_ID);

      // Reset state
      useKanbanSettingsStore.setState({ filters: null });

      // Load filters
      loadFilters(TEST_PROJECT_ID);

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('test task');
      expect(filters?.sortBy).toBe('created');
    });

    it('should validate filters before loading', () => {
      // Store invalid data in localStorage
      localStorage.setItem(`kanban-filters-${TEST_PROJECT_ID}`, JSON.stringify({
        searchQuery: 'valid',
        sortBy: 'invalid-sort-mode', // Invalid value
        sortOrder: 'asc'
      }));

      const { loadFilters } = useKanbanSettingsStore.getState();

      // Spy on console.warn to check validation warning
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      loadFilters(TEST_PROJECT_ID);

      // Should fall back to defaults
      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.sortBy).toBe('manual'); // Default value

      // Should have warned about invalid data
      expect(warnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Invalid filters in localStorage')
      );

      warnSpy.mockRestore();
    });

    it('should handle localStorage errors gracefully', () => {
      const { saveFilters } = useKanbanSettingsStore.getState();

      // Mock localStorage.setItem to throw an error
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

      // Restore original localStorage
      localStorage.setItem = originalSetItem;
      errorSpy.mockRestore();
    });

    it('should isolate filters by project ID', () => {
      const { setSearchQuery, setSortBy, saveFilters } = useKanbanSettingsStore.getState();

      // Save filters for project 1
      setSearchQuery('project one');
      setSortBy('priority');
      saveFilters('project-1');

      // Save different filters for project 2
      setSearchQuery('project two');
      setSortBy('created');
      saveFilters('project-2');

      // Load project 1 filters
      useKanbanSettingsStore.getState().loadFilters('project-1');
      let { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('project one');
      expect(filters?.sortBy).toBe('priority');

      // Load project 2 filters
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

      // Set some filters
      setSearchQuery('test query');
      setSortBy('priority');

      // Reset
      resetFilters(TEST_PROJECT_ID);

      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('');
      expect(filters?.sortBy).toBe('manual');
      expect(filters?.sortOrder).toBe('asc');
    });

    it('should remove filters from localStorage on reset', () => {
      const { setSearchQuery, saveFilters, resetFilters } = useKanbanSettingsStore.getState();

      // Save filters
      setSearchQuery('test');
      saveFilters(TEST_PROJECT_ID);

      // Verify saved
      expect(localStorage.getItem(`kanban-filters-${TEST_PROJECT_ID}`)).toBeDefined();

      // Reset
      resetFilters(TEST_PROJECT_ID);

      // Verify removed from localStorage
      expect(localStorage.getItem(`kanban-filters-${TEST_PROJECT_ID}`)).toBeNull();
    });

    it('should handle reset errors gracefully', () => {
      const { resetFilters } = useKanbanSettingsStore.getState();

      // Mock localStorage.removeItem to throw an error
      const originalRemoveItem = localStorage.removeItem;
      localStorage.removeItem = vi.fn(() => {
        throw new Error('Storage error');
      });

      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // Should not throw
      resetFilters(TEST_PROJECT_ID);

      expect(errorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to reset filters'),
        expect.any(Error)
      );

      // Restore original localStorage
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

      // Set initial state
      setSearchQuery('authentication');
      setSortBy('created');

      // Update search query
      setSearchQuery('login');

      const { filters } = useKanbanSettingsStore.getState();

      // Search query updated
      expect(filters?.searchQuery).toBe('login');
      // Sort mode unchanged
      expect(filters?.sortBy).toBe('created');
      // Sort order unchanged
      expect(filters?.sortOrder).toBe('asc');
    });

    it('should persist combined filters correctly', () => {
      const { setSearchQuery, setSortBy, saveFilters, loadFilters } = useKanbanSettingsStore.getState();

      // Set multiple filters
      setSearchQuery('feature request');
      setSortBy('updated');

      // Save
      saveFilters(TEST_PROJECT_ID);

      // Reset state
      useKanbanSettingsStore.setState({ filters: null });

      // Load
      loadFilters(TEST_PROJECT_ID);

      const { filters } = useKanbanSettingsStore.getState();

      expect(filters?.searchQuery).toBe('feature request');
      expect(filters?.sortBy).toBe('updated');
    });
  });

  describe('Edge Cases', () => {
    it('should handle operations when filters are null', () => {
      // Set filters to null (uninitialized state)
      useKanbanSettingsStore.setState({ filters: null });

      const { setSearchQuery, setSortBy } = useKanbanSettingsStore.getState();

      // Operations should not crash
      setSearchQuery('test');
      setSortBy('priority');

      // Filters should remain null (no-op)
      const { filters } = useKanbanSettingsStore.getState();
      expect(filters).toBeNull();
    });

    it('should handle invalid JSON in localStorage', () => {
      // Store invalid JSON
      localStorage.setItem(`kanban-filters-${TEST_PROJECT_ID}`, 'invalid json{');

      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const { loadFilters } = useKanbanSettingsStore.getState();
      loadFilters(TEST_PROJECT_ID);

      // Should fall back to defaults
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

      // No data in localStorage
      loadFilters(TEST_PROJECT_ID);

      // Should create defaults
      const { filters } = useKanbanSettingsStore.getState();
      expect(filters?.searchQuery).toBe('');
      expect(filters?.sortBy).toBe('manual');
    });
  });
});
