import { create } from 'zustand';
import type { TaskStatus } from '../../shared/types';

const RECENT_ACTIONS_KEY = 'recent-actions';

/**
 * Recent action entry
 */
export interface RecentAction {
  /** Unique identifier for this action instance */
  id: string;
  /** Type of action performed */
  type: 'batch_qa' | 'batch_status_update' | 'create_task' | 'start_task' | 'stop_task';
  /** Display label for the action */
  label: string;
  /** Timestamp when the action was performed */
  timestamp: Date;
  /** Number of items affected (for batch operations) */
  itemCount?: number;
  /** Target status (for status updates) */
  targetStatus?: TaskStatus;
  /** Project ID where the action was performed */
  projectId?: string;
}

interface QuickActionsState {
  recentActions: RecentAction[];
  isLoading: boolean;
  error: string | null;

  // Actions
  addRecentAction: (action: Omit<RecentAction, 'id' | 'timestamp'>) => void;
  clearRecentActions: () => void;
  removeRecentAction: (actionId: string) => void;
  getRecentActions: () => RecentAction[];
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  loadRecentActions: () => void;
  saveRecentActions: () => boolean;
}

/**
 * Maximum number of recent actions to store
 */
const MAX_RECENT_ACTIONS = 10;

/**
 * Validate recent actions data structure
 */
function validateRecentActions(data: unknown): data is RecentAction[] {
  if (!Array.isArray(data)) {
    return false;
  }

  return data.every((item): item is RecentAction => {
    if (!item || typeof item !== 'object') {
      return false;
    }

    const action = item as RecentAction;
    return (
      typeof action.id === 'string' &&
      typeof action.type === 'string' &&
      typeof action.label === 'string' &&
      typeof action.timestamp === 'string' &&
      (action.itemCount === undefined || typeof action.itemCount === 'number') &&
      (action.targetStatus === undefined || typeof action.targetStatus === 'string') &&
      (action.projectId === undefined || typeof action.projectId === 'string')
    );
  });
}

/**
 * Convert stored data to RecentAction objects (convert timestamp strings to Dates)
 */
function hydrateRecentActions(data: RecentAction[]): RecentAction[] {
  return data.map(action => ({
    ...action,
    timestamp: new Date(action.timestamp)
  }));
}

/**
 * Prepare recent actions for storage (convert Dates to ISO strings)
 */
function prepareForStorage(actions: RecentAction[]): RecentAction[] {
  return actions.map(action => ({
    ...action,
    timestamp: action.timestamp.toISOString() as unknown as Date
  })) as unknown as RecentAction[];
}

export const useQuickActionsStore = create<QuickActionsState>((set, get) => ({
  recentActions: [],
  isLoading: false,
  error: null,

  addRecentAction: (action) =>
    set((state) => {
      const newAction: RecentAction = {
        ...action,
        id: `action-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date()
      };

      // Add to beginning of array, keep only MAX_RECENT_ACTIONS
      const updatedActions = [newAction, ...state.recentActions].slice(0, MAX_RECENT_ACTIONS);

      // Save to localStorage
      try {
        localStorage.setItem(RECENT_ACTIONS_KEY, JSON.stringify(prepareForStorage(updatedActions)));
      } catch (error) {
        console.error('[QuickActionsStore] Failed to save recent actions:', error);
      }

      return { recentActions: updatedActions };
    }),

  clearRecentActions: () => {
    set({ recentActions: [] });
    try {
      localStorage.removeItem(RECENT_ACTIONS_KEY);
    } catch (error) {
      console.error('[QuickActionsStore] Failed to clear recent actions:', error);
    }
  },

  removeRecentAction: (actionId) =>
    set((state) => {
      const updatedActions = state.recentActions.filter(a => a.id !== actionId);

      try {
        localStorage.setItem(RECENT_ACTIONS_KEY, JSON.stringify(prepareForStorage(updatedActions)));
      } catch (error) {
        console.error('[QuickActionsStore] Failed to save after removal:', error);
      }

      return { recentActions: updatedActions };
    }),

  getRecentActions: () => {
    return get().recentActions;
  },

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  loadRecentActions: () => {
    try {
      const stored = localStorage.getItem(RECENT_ACTIONS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);

        if (validateRecentActions(parsed)) {
          const hydrated = hydrateRecentActions(parsed);
          set({ recentActions: hydrated });
        } else {
          console.warn('[QuickActionsStore] Invalid recent actions data, resetting to empty');
          set({ recentActions: [] });
        }
      } else {
        set({ recentActions: [] });
      }
    } catch (error) {
      console.error('[QuickActionsStore] Failed to load recent actions:', error);
      set({ recentActions: [] });
    }
  },

  saveRecentActions: () => {
    try {
      const state = get();
      localStorage.setItem(RECENT_ACTIONS_KEY, JSON.stringify(prepareForStorage(state.recentActions)));
      return true;
    } catch (error) {
      console.error('[QuickActionsStore] Failed to save recent actions:', error);
      return false;
    }
  }
}));

/**
 * Helper function to get formatted action label (without i18n)
 * Note: i18n should be handled by the component
 */
export function getActionLabel(action: RecentAction): string {
  switch (action.type) {
    case 'batch_qa':
      return action.itemCount
        ? `Batch QA (${action.itemCount} tasks)`
        : 'Batch QA';
    case 'batch_status_update':
      return action.itemCount && action.targetStatus
        ? `Update to ${action.targetStatus} (${action.itemCount} tasks)`
        : 'Batch Status Update';
    case 'create_task':
      return action.label || 'Create Task';
    case 'start_task':
      return action.label || 'Start Task';
    case 'stop_task':
      return 'Stop Task';
    default:
      return action.label;
  }
}

/**
 * Helper function to check if an action can be repeated
 */
export function canRepeatAction(action: RecentAction): boolean {
  // Batch operations and task creation can be repeated
  return ['batch_qa', 'batch_status_update', 'create_task'].includes(action.type);
}

/**
 * Helper function to get time ago string
 */
export function getTimeAgo(timestamp: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - timestamp.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) {
    return 'just now';
  } else if (diffMins < 60) {
    return `${diffMins}m ago`;
  } else if (diffHours < 24) {
    return `${diffHours}h ago`;
  } else if (diffDays < 7) {
    return `${diffDays}d ago`;
  } else {
    return timestamp.toLocaleDateString();
  }
}
