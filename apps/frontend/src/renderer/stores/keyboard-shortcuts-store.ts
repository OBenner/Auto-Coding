import { create } from 'zustand';
import type { KeyboardShortcutAction, KeyCombination } from '../../shared/types/settings';
import { DEFAULT_KEYBOARD_SHORTCUTS } from '../../shared/types/settings';

const KEYBOARD_SHORTCUTS_KEY = 'keyboard-shortcuts';

interface KeyboardShortcutsState {
  shortcuts: Record<KeyboardShortcutAction, KeyCombination>;
  isLoading: boolean;
  error: string | null;

  // Actions
  setShortcuts: (shortcuts: Record<KeyboardShortcutAction, KeyCombination>) => void;
  updateShortcut: (action: KeyboardShortcutAction, keyCombination: KeyCombination) => void;
  resetToDefaults: () => void;
  getShortcut: (action: KeyboardShortcutAction) => KeyCombination;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  loadShortcuts: () => void;
  saveShortcuts: () => boolean;
}

/**
 * Validate keyboard shortcut data structure
 * Returns true if valid, false if invalid
 */
function validateShortcuts(shortcuts: unknown): shortcuts is Record<KeyboardShortcutAction, KeyCombination> {
  if (!shortcuts || typeof shortcuts !== 'object' || Array.isArray(shortcuts)) {
    return false;
  }

  // Check that all required actions exist
  const requiredActions: KeyboardShortcutAction[] = [
    'commandPalette',
    'quickActions',
    'createTask',
    'batchQA',
    'batchStatusUpdate'
  ];

  for (const action of requiredActions) {
    if (!(action in shortcuts) || typeof shortcuts[action as keyof typeof shortcuts] !== 'string') {
      return false;
    }
  }

  return true;
}

/**
 * Get the formatted key combination for display
 * Converts "Cmd+K" to "⌘K" on macOS, "Ctrl+K" on Windows/Linux
 */
export function formatKeyCombination(keyCombination: KeyCombination): string {
  const isMac = typeof window !== 'undefined' && window.navigator.platform.includes('Mac');

  return keyCombination
    .replace(/\+/g, isMac ? '' : '+')
    .replace('Cmd', isMac ? '⌘' : 'Ctrl')
    .replace('Ctrl', isMac ? '⌘' : 'Ctrl')
    .replace('Shift', isMac ? '⇧' : 'Shift')
    .replace('Alt', isMac ? '⌥' : 'Alt')
    .replace('Meta', isMac ? '⌘' : 'Win');
}

/**
 * Parse a keyboard event into a key combination string
 * Handles platform differences (Cmd vs Ctrl)
 */
export function parseKeyboardEvent(event: KeyboardEvent): KeyCombination {
  const parts: string[] = [];

  if (event.metaKey) parts.push('Cmd');
  if (event.ctrlKey) parts.push('Ctrl');
  if (event.shiftKey) parts.push('Shift');
  if (event.altKey) parts.push('Alt');

  // Handle special keys
  const key = event.key;
  if (key === ' ') {
    parts.push('Space');
  } else if (key.length === 1) {
    // Single character key (letter, number, symbol)
    parts.push(key.toUpperCase());
  } else {
    // Special key name (Escape, Enter, etc.)
    parts.push(key);
  }

  return parts.join('+');
}

/**
 * Check if a keyboard event matches a key combination
 */
export function matchesKeyCombination(event: KeyboardEvent, keyCombination: KeyCombination): boolean {
  const eventCombination = parseKeyboardEvent(event);
  return eventCombination === keyCombination;
}

export const useKeyboardShortcutsStore = create<KeyboardShortcutsState>((set, get) => ({
  shortcuts: DEFAULT_KEYBOARD_SHORTCUTS,
  isLoading: false,
  error: null,

  setShortcuts: (shortcuts) => set({ shortcuts }),

  updateShortcut: (action, keyCombination) =>
    set((state) => ({
      shortcuts: {
        ...state.shortcuts,
        [action]: keyCombination
      }
    })),

  resetToDefaults: () => {
    set({ shortcuts: DEFAULT_KEYBOARD_SHORTCUTS });
    // Save to localStorage after reset
    try {
      localStorage.setItem(KEYBOARD_SHORTCUTS_KEY, JSON.stringify(DEFAULT_KEYBOARD_SHORTCUTS));
    } catch (error) {
      console.error('[KeyboardShortcutsStore] Failed to save defaults to localStorage:', error);
    }
  },

  getShortcut: (action) => {
    const state = get();
    return state.shortcuts[action] || DEFAULT_KEYBOARD_SHORTCUTS[action];
  },

  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error }),

  loadShortcuts: () => {
    try {
      const stored = localStorage.getItem(KEYBOARD_SHORTCUTS_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (validateShortcuts(parsed)) {
          set({ shortcuts: parsed });
        } else {
          console.warn('[KeyboardShortcutsStore] Invalid shortcuts in localStorage, using defaults');
          set({ shortcuts: DEFAULT_KEYBOARD_SHORTCUTS });
        }
      } else {
        set({ shortcuts: DEFAULT_KEYBOARD_SHORTCUTS });
      }
    } catch (error) {
      console.error('[KeyboardShortcutsStore] Failed to load shortcuts from localStorage:', error);
      set({ shortcuts: DEFAULT_KEYBOARD_SHORTCUTS, error: 'Failed to load keyboard shortcuts' });
    }
  },

  saveShortcuts: () => {
    try {
      const state = get();
      localStorage.setItem(KEYBOARD_SHORTCUTS_KEY, JSON.stringify(state.shortcuts));
      return true;
    } catch (error) {
      console.error('[KeyboardShortcutsStore] Failed to save shortcuts to localStorage:', error);
      set({ error: 'Failed to save keyboard shortcuts' });
      return false;
    }
  }
}));

/**
 * Initialize keyboard shortcuts store
 * Loads shortcuts from localStorage on app startup
 */
export function initializeKeyboardShortcuts(): void {
  useKeyboardShortcutsStore.getState().loadShortcuts();
}

/**
 * Register a keyboard shortcut handler
 * Returns a cleanup function to remove the listener
 */
export function registerKeyboardShortcut(
  action: KeyboardShortcutAction,
  handler: (event: KeyboardEvent) => void,
  options?: { preventDefault?: boolean }
): () => void {
  const handleKeyDown = (event: KeyboardEvent) => {
    const store = useKeyboardShortcutsStore.getState();
    const keyCombination = store.getShortcut(action);

    if (matchesKeyCombination(event, keyCombination)) {
      if (options?.preventDefault !== false) {
        event.preventDefault();
      }
      handler(event);
    }
  };

  window.addEventListener('keydown', handleKeyDown);

  // Return cleanup function
  return () => {
    window.removeEventListener('keydown', handleKeyDown);
  };
}

/**
 * Batch register multiple keyboard shortcuts
 * Returns a cleanup function to remove all listeners
 */
export function registerKeyboardShortcuts(
  shortcuts: Partial<Record<KeyboardShortcutAction, (event: KeyboardEvent) => void>>,
  options?: { preventDefault?: boolean }
): () => void {
  const cleanupFunctions: Array<() => void> = [];

  for (const [action, handler] of Object.entries(shortcuts)) {
    if (handler) {
      const cleanup = registerKeyboardShortcut(
        action as KeyboardShortcutAction,
        handler,
        options
      );
      cleanupFunctions.push(cleanup);
    }
  }

  // Return cleanup function that removes all listeners
  return () => {
    for (const cleanup of cleanupFunctions) {
      cleanup();
    }
  };
}
