/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  useQuickActionsStore,
  getActionLabel,
  canRepeatAction,
  getTimeAgo,
  type RecentAction,
} from '../quick-actions-store';

describe('quick-actions-store', () => {
  beforeEach(() => {
    useQuickActionsStore.setState({
      recentActions: [],
      isLoading: false,
      error: null,
    });
    localStorage.clear();
  });

  describe('addRecentAction', () => {
    it('should add an action with auto-generated id and timestamp', () => {
      useQuickActionsStore.getState().addRecentAction({
        type: 'create_task',
        label: 'Create Task',
      });
      const actions = useQuickActionsStore.getState().recentActions;
      expect(actions).toHaveLength(1);
      expect(actions[0].type).toBe('create_task');
      expect(actions[0].id).toMatch(/^action-/);
      expect(actions[0].timestamp).toBeInstanceOf(Date);
    });

    it('should add new actions to the beginning', () => {
      useQuickActionsStore.getState().addRecentAction({ type: 'create_task', label: 'First' });
      useQuickActionsStore.getState().addRecentAction({ type: 'start_task', label: 'Second' });
      const actions = useQuickActionsStore.getState().recentActions;
      expect(actions[0].label).toBe('Second');
      expect(actions[1].label).toBe('First');
    });

    it('should limit to 10 actions', () => {
      for (let i = 0; i < 15; i++) {
        useQuickActionsStore.getState().addRecentAction({
          type: 'create_task',
          label: `Task ${i}`,
        });
      }
      expect(useQuickActionsStore.getState().recentActions).toHaveLength(10);
    });

    it('should persist to localStorage', () => {
      useQuickActionsStore.getState().addRecentAction({
        type: 'batch_qa',
        label: 'Batch QA',
        itemCount: 5,
      });
      const stored = JSON.parse(localStorage.getItem('recent-actions')!);
      expect(stored).toHaveLength(1);
      expect(stored[0].type).toBe('batch_qa');
    });
  });

  describe('removeRecentAction', () => {
    it('should remove action by id', () => {
      useQuickActionsStore.getState().addRecentAction({ type: 'create_task', label: 'Task 1' });
      useQuickActionsStore.getState().addRecentAction({ type: 'start_task', label: 'Task 2' });
      const actions = useQuickActionsStore.getState().recentActions;
      useQuickActionsStore.getState().removeRecentAction(actions[0].id);
      expect(useQuickActionsStore.getState().recentActions).toHaveLength(1);
    });
  });

  describe('clearRecentActions', () => {
    it('should clear all actions', () => {
      useQuickActionsStore.getState().addRecentAction({ type: 'create_task', label: 'Task 1' });
      useQuickActionsStore.getState().clearRecentActions();
      expect(useQuickActionsStore.getState().recentActions).toEqual([]);
      expect(localStorage.getItem('recent-actions')).toBeNull();
    });
  });

  describe('loadRecentActions', () => {
    it('should load actions from localStorage', () => {
      const actions = [{
        id: 'action-1',
        type: 'create_task',
        label: 'Task 1',
        timestamp: new Date().toISOString(),
      }];
      localStorage.setItem('recent-actions', JSON.stringify(actions));
      useQuickActionsStore.getState().loadRecentActions();
      const loaded = useQuickActionsStore.getState().recentActions;
      expect(loaded).toHaveLength(1);
      expect(loaded[0].timestamp).toBeInstanceOf(Date);
    });

    it('should handle invalid localStorage data', () => {
      localStorage.setItem('recent-actions', 'invalid');
      useQuickActionsStore.getState().loadRecentActions();
      expect(useQuickActionsStore.getState().recentActions).toEqual([]);
    });

    it('should handle empty localStorage', () => {
      useQuickActionsStore.getState().loadRecentActions();
      expect(useQuickActionsStore.getState().recentActions).toEqual([]);
    });

    it('should reject structurally invalid actions', () => {
      localStorage.setItem('recent-actions', JSON.stringify([{ bad: 'data' }]));
      useQuickActionsStore.getState().loadRecentActions();
      expect(useQuickActionsStore.getState().recentActions).toEqual([]);
    });
  });

  describe('saveRecentActions', () => {
    it('should save current state to localStorage', () => {
      useQuickActionsStore.getState().addRecentAction({ type: 'create_task', label: 'Task 1' });
      const result = useQuickActionsStore.getState().saveRecentActions();
      expect(result).toBe(true);
      expect(localStorage.getItem('recent-actions')).not.toBeNull();
    });
  });

  describe('loading and error state', () => {
    it('should set loading state', () => {
      useQuickActionsStore.getState().setLoading(true);
      expect(useQuickActionsStore.getState().isLoading).toBe(true);
    });

    it('should set error state', () => {
      useQuickActionsStore.getState().setError('Failed');
      expect(useQuickActionsStore.getState().error).toBe('Failed');
    });
  });
});

describe('quick-actions helpers', () => {
  describe('getActionLabel', () => {
    it('should format batch_qa with count', () => {
      expect(getActionLabel({ type: 'batch_qa', itemCount: 5 } as RecentAction))
        .toBe('Batch QA (5 tasks)');
    });

    it('should format batch_qa without count', () => {
      expect(getActionLabel({ type: 'batch_qa' } as RecentAction))
        .toBe('Batch QA');
    });

    it('should format batch_status_update with details', () => {
      expect(getActionLabel({
        type: 'batch_status_update',
        itemCount: 3,
        targetStatus: 'done',
      } as RecentAction)).toBe('Update to done (3 tasks)');
    });

    it('should format create_task with label', () => {
      expect(getActionLabel({ type: 'create_task', label: 'My New Task' } as RecentAction))
        .toBe('My New Task');
    });

    it('should format stop_task', () => {
      expect(getActionLabel({ type: 'stop_task' } as RecentAction))
        .toBe('Stop Task');
    });
  });

  describe('canRepeatAction', () => {
    it('should return true for batch_qa', () => {
      expect(canRepeatAction({ type: 'batch_qa' } as RecentAction)).toBe(true);
    });

    it('should return true for batch_status_update', () => {
      expect(canRepeatAction({ type: 'batch_status_update' } as RecentAction)).toBe(true);
    });

    it('should return true for create_task', () => {
      expect(canRepeatAction({ type: 'create_task' } as RecentAction)).toBe(true);
    });

    it('should return false for start_task', () => {
      expect(canRepeatAction({ type: 'start_task' } as RecentAction)).toBe(false);
    });

    it('should return false for stop_task', () => {
      expect(canRepeatAction({ type: 'stop_task' } as RecentAction)).toBe(false);
    });
  });

  describe('getTimeAgo', () => {
    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date('2025-01-20T12:00:00Z'));
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should return "just now" for < 60 seconds', () => {
      const ts = new Date('2025-01-20T11:59:30Z');
      expect(getTimeAgo(ts)).toBe('just now');
    });

    it('should return minutes ago', () => {
      const ts = new Date('2025-01-20T11:45:00Z');
      expect(getTimeAgo(ts)).toBe('15m ago');
    });

    it('should return hours ago', () => {
      const ts = new Date('2025-01-20T09:00:00Z');
      expect(getTimeAgo(ts)).toBe('3h ago');
    });

    it('should return days ago', () => {
      const ts = new Date('2025-01-18T12:00:00Z');
      expect(getTimeAgo(ts)).toBe('2d ago');
    });

    it('should return formatted date for > 7 days', () => {
      const ts = new Date('2025-01-01T12:00:00Z');
      const result = getTimeAgo(ts);
      // Should be a localized date string, not "Xd ago"
      expect(result).not.toContain('d ago');
    });
  });
});
