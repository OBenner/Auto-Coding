/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  useKeyboardShortcutsStore,
  formatKeyCombination,
  parseKeyboardEvent,
  matchesKeyCombination,
} from '../keyboard-shortcuts-store';
import { DEFAULT_KEYBOARD_SHORTCUTS } from '../../../shared/types/settings';

describe('keyboard-shortcuts-store', () => {
  beforeEach(() => {
    useKeyboardShortcutsStore.setState({
      shortcuts: { ...DEFAULT_KEYBOARD_SHORTCUTS },
      isLoading: false,
      error: null,
    });
    localStorage.clear();
  });

  describe('initial state', () => {
    it('should start with default shortcuts', () => {
      const state = useKeyboardShortcutsStore.getState();
      expect(state.shortcuts.commandPalette).toBe('Cmd+K');
      expect(state.shortcuts.quickActions).toBe('Cmd+.');
      expect(state.shortcuts.createTask).toBe('Cmd+N');
      expect(state.shortcuts.batchQA).toBe('Cmd+Shift+Q');
      expect(state.shortcuts.batchStatusUpdate).toBe('Cmd+Shift+S');
    });
  });

  describe('updateShortcut', () => {
    it('should update a single shortcut', () => {
      useKeyboardShortcutsStore.getState().updateShortcut('commandPalette', 'Ctrl+P');
      expect(useKeyboardShortcutsStore.getState().shortcuts.commandPalette).toBe('Ctrl+P');
    });

    it('should not affect other shortcuts', () => {
      useKeyboardShortcutsStore.getState().updateShortcut('commandPalette', 'Ctrl+P');
      expect(useKeyboardShortcutsStore.getState().shortcuts.quickActions).toBe('Cmd+.');
    });
  });

  describe('resetToDefaults', () => {
    it('should reset all shortcuts to defaults', () => {
      useKeyboardShortcutsStore.getState().updateShortcut('commandPalette', 'Ctrl+P');
      useKeyboardShortcutsStore.getState().updateShortcut('createTask', 'Alt+N');
      useKeyboardShortcutsStore.getState().resetToDefaults();
      expect(useKeyboardShortcutsStore.getState().shortcuts).toEqual(DEFAULT_KEYBOARD_SHORTCUTS);
    });

    it('should save defaults to localStorage', () => {
      useKeyboardShortcutsStore.getState().resetToDefaults();
      const stored = JSON.parse(localStorage.getItem('keyboard-shortcuts')!);
      expect(stored.commandPalette).toBe('Cmd+K');
    });
  });

  describe('getShortcut', () => {
    it('should return shortcut for existing action', () => {
      expect(useKeyboardShortcutsStore.getState().getShortcut('commandPalette')).toBe('Cmd+K');
    });

    it('should return default for unset action', () => {
      useKeyboardShortcutsStore.setState({ shortcuts: {} as any });
      // Should fall back to DEFAULT_KEYBOARD_SHORTCUTS
      expect(useKeyboardShortcutsStore.getState().getShortcut('commandPalette')).toBe('Cmd+K');
    });
  });

  describe('localStorage persistence', () => {
    it('should load shortcuts from localStorage', () => {
      localStorage.setItem('keyboard-shortcuts', JSON.stringify({
        commandPalette: 'Ctrl+P',
        quickActions: 'Ctrl+.',
        createTask: 'Ctrl+N',
        batchQA: 'Ctrl+Shift+Q',
        batchStatusUpdate: 'Ctrl+Shift+S',
      }));
      useKeyboardShortcutsStore.getState().loadShortcuts();
      expect(useKeyboardShortcutsStore.getState().shortcuts.commandPalette).toBe('Ctrl+P');
    });

    it('should use defaults for invalid localStorage data', () => {
      localStorage.setItem('keyboard-shortcuts', 'invalid json');
      useKeyboardShortcutsStore.getState().loadShortcuts();
      expect(useKeyboardShortcutsStore.getState().shortcuts).toEqual(DEFAULT_KEYBOARD_SHORTCUTS);
      expect(useKeyboardShortcutsStore.getState().error).toBe('Failed to load keyboard shortcuts');
    });

    it('should use defaults for incomplete data', () => {
      localStorage.setItem('keyboard-shortcuts', JSON.stringify({ commandPalette: 'Ctrl+P' }));
      useKeyboardShortcutsStore.getState().loadShortcuts();
      // Missing required actions → validation fails
      expect(useKeyboardShortcutsStore.getState().shortcuts).toEqual(DEFAULT_KEYBOARD_SHORTCUTS);
    });

    it('should save shortcuts to localStorage', () => {
      useKeyboardShortcutsStore.getState().updateShortcut('commandPalette', 'Ctrl+P');
      const result = useKeyboardShortcutsStore.getState().saveShortcuts();
      expect(result).toBe(true);
      const stored = JSON.parse(localStorage.getItem('keyboard-shortcuts')!);
      expect(stored.commandPalette).toBe('Ctrl+P');
    });
  });

  describe('loading and error state', () => {
    it('should set loading state', () => {
      useKeyboardShortcutsStore.getState().setLoading(true);
      expect(useKeyboardShortcutsStore.getState().isLoading).toBe(true);
    });

    it('should set error state', () => {
      useKeyboardShortcutsStore.getState().setError('Something went wrong');
      expect(useKeyboardShortcutsStore.getState().error).toBe('Something went wrong');
    });
  });
});

describe('keyboard shortcut utilities', () => {
  describe('formatKeyCombination', () => {
    it('should format for non-Mac (default in jsdom)', () => {
      // jsdom doesn't have Mac platform
      expect(formatKeyCombination('Cmd+K')).toBe('Ctrl+K');
    });

    it('should replace Shift', () => {
      const result = formatKeyCombination('Cmd+Shift+Q');
      expect(result).toContain('Shift');
    });
  });

  describe('parseKeyboardEvent', () => {
    function createKeyEvent(overrides: Partial<KeyboardEvent> = {}): KeyboardEvent {
      return {
        metaKey: false,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        key: 'a',
        ...overrides,
      } as KeyboardEvent;
    }

    it('should parse simple key', () => {
      expect(parseKeyboardEvent(createKeyEvent({ key: 'k' }))).toBe('K');
    });

    it('should parse Ctrl+key', () => {
      expect(parseKeyboardEvent(createKeyEvent({ ctrlKey: true, key: 'k' }))).toBe('Ctrl+K');
    });

    it('should parse Cmd+key', () => {
      expect(parseKeyboardEvent(createKeyEvent({ metaKey: true, key: 'k' }))).toBe('Cmd+K');
    });

    it('should parse Shift+key', () => {
      expect(parseKeyboardEvent(createKeyEvent({ shiftKey: true, key: 'q' }))).toBe('Shift+Q');
    });

    it('should parse Alt+key', () => {
      expect(parseKeyboardEvent(createKeyEvent({ altKey: true, key: 'n' }))).toBe('Alt+N');
    });

    it('should parse multi-modifier combo', () => {
      expect(parseKeyboardEvent(createKeyEvent({
        ctrlKey: true,
        shiftKey: true,
        key: 'q',
      }))).toBe('Ctrl+Shift+Q');
    });

    it('should handle space key', () => {
      expect(parseKeyboardEvent(createKeyEvent({ key: ' ' }))).toBe('Space');
    });

    it('should handle special keys (Escape, Enter)', () => {
      expect(parseKeyboardEvent(createKeyEvent({ key: 'Escape' }))).toBe('Escape');
      expect(parseKeyboardEvent(createKeyEvent({ key: 'Enter' }))).toBe('Enter');
    });
  });

  describe('matchesKeyCombination', () => {
    it('should match when event matches combination', () => {
      const event = {
        metaKey: true,
        ctrlKey: false,
        shiftKey: false,
        altKey: false,
        key: 'k',
      } as KeyboardEvent;
      expect(matchesKeyCombination(event, 'Cmd+K')).toBe(true);
    });

    it('should not match when event does not match', () => {
      const event = {
        metaKey: false,
        ctrlKey: true,
        shiftKey: false,
        altKey: false,
        key: 'k',
      } as KeyboardEvent;
      expect(matchesKeyCombination(event, 'Cmd+K')).toBe(false);
    });
  });
});
