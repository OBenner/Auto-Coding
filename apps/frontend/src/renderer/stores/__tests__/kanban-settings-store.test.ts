/**
 * @vitest-environment jsdom
 */
/**
 * Tests for kanban-settings-store (Zustand)
 * Column preferences, width clamping, collapse/lock, localStorage persistence
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  useKanbanSettingsStore,
  DEFAULT_COLUMN_WIDTH,
  MIN_COLUMN_WIDTH,
  MAX_COLUMN_WIDTH,
  COLLAPSED_COLUMN_WIDTH,
} from '../kanban-settings-store';
import type { ColumnPreferences } from '../kanban-settings-store';
import { TASK_STATUS_COLUMNS } from '../../../shared/constants/task';

describe('kanban-settings-store', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    // Reset store
    useKanbanSettingsStore.setState({ columnPreferences: null });
  });

  afterEach(() => {
    vi.restoreAllMocks();
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
        const prefs = state.columnPreferences![column];
        expect(prefs.width).toBe(DEFAULT_COLUMN_WIDTH);
        expect(prefs.isCollapsed).toBe(false);
        expect(prefs.isLocked).toBe(false);
      }
    });

    it('should not overwrite existing preferences', () => {
      const { initializePreferences, setColumnWidth } = useKanbanSettingsStore.getState();
      initializePreferences();
      setColumnWidth('backlog', 400);

      // Re-initialize should not reset
      useKanbanSettingsStore.getState().initializePreferences();

      expect(useKanbanSettingsStore.getState().columnPreferences!.backlog.width).toBe(400);
    });
  });

  describe('setColumnWidth', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should set column width', () => {
      const { setColumnWidth } = useKanbanSettingsStore.getState();
      setColumnWidth('backlog', 400);

      expect(useKanbanSettingsStore.getState().columnPreferences!.backlog.width).toBe(400);
    });

    it('should clamp width to minimum', () => {
      const { setColumnWidth } = useKanbanSettingsStore.getState();
      setColumnWidth('backlog', 50);

      expect(useKanbanSettingsStore.getState().columnPreferences!.backlog.width).toBe(MIN_COLUMN_WIDTH);
    });

    it('should clamp width to maximum', () => {
      const { setColumnWidth } = useKanbanSettingsStore.getState();
      setColumnWidth('backlog', 1000);

      expect(useKanbanSettingsStore.getState().columnPreferences!.backlog.width).toBe(MAX_COLUMN_WIDTH);
    });

    it('should not change width on locked column', () => {
      const { setColumnWidth, toggleColumnLocked } = useKanbanSettingsStore.getState();
      toggleColumnLocked('backlog');

      setColumnWidth('backlog', 500);

      expect(useKanbanSettingsStore.getState().columnPreferences!.backlog.width).toBe(DEFAULT_COLUMN_WIDTH);
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
      expect(useKanbanSettingsStore.getState().columnPreferences!.queue.isCollapsed).toBe(true);

      useKanbanSettingsStore.getState().toggleColumnCollapsed('queue');
      expect(useKanbanSettingsStore.getState().columnPreferences!.queue.isCollapsed).toBe(false);
    });
  });

  describe('setColumnCollapsed', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should set collapsed state explicitly', () => {
      const { setColumnCollapsed } = useKanbanSettingsStore.getState();

      setColumnCollapsed('in_progress', true);
      expect(useKanbanSettingsStore.getState().columnPreferences!.in_progress.isCollapsed).toBe(true);

      setColumnCollapsed('in_progress', false);
      expect(useKanbanSettingsStore.getState().columnPreferences!.in_progress.isCollapsed).toBe(false);
    });
  });

  describe('toggleColumnLocked', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should toggle locked state', () => {
      const { toggleColumnLocked } = useKanbanSettingsStore.getState();

      toggleColumnLocked('done');
      expect(useKanbanSettingsStore.getState().columnPreferences!.done.isLocked).toBe(true);

      useKanbanSettingsStore.getState().toggleColumnLocked('done');
      expect(useKanbanSettingsStore.getState().columnPreferences!.done.isLocked).toBe(false);
    });
  });

  describe('setColumnLocked', () => {
    beforeEach(() => {
      useKanbanSettingsStore.getState().initializePreferences();
    });

    it('should set locked state explicitly', () => {
      const { setColumnLocked } = useKanbanSettingsStore.getState();

      setColumnLocked('ai_review', true);
      expect(useKanbanSettingsStore.getState().columnPreferences!.ai_review.isLocked).toBe(true);
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
      expect(state.columnPreferences!.backlog.width).toBe(450);
      expect(state.columnPreferences!.done.width).toBe(250);
    });

    it('loadPreferences should use defaults when no stored data', () => {
      useKanbanSettingsStore.setState({ columnPreferences: null });

      useKanbanSettingsStore.getState().loadPreferences('nonexistent-project');

      const state = useKanbanSettingsStore.getState();
      expect(state.columnPreferences).not.toBeNull();
      expect(state.columnPreferences!.backlog.width).toBe(DEFAULT_COLUMN_WIDTH);
    });

    it('loadPreferences should use defaults on invalid stored data', () => {
      localStorage.setItem('kanban-column-prefs-bad', JSON.stringify({ invalid: true }));

      useKanbanSettingsStore.getState().loadPreferences('bad');

      const state = useKanbanSettingsStore.getState();
      expect(state.columnPreferences!.backlog.width).toBe(DEFAULT_COLUMN_WIDTH);
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

      expect(useKanbanSettingsStore.getState().columnPreferences!.backlog.width).toBe(DEFAULT_COLUMN_WIDTH);
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
