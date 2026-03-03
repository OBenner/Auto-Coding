/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { reducer } from '../use-toast';

// The reducer is exported and testable without React rendering
type ToasterToast = {
  id: string;
  title?: string;
  open?: boolean;
};

type State = {
  toasts: ToasterToast[];
};

describe('use-toast reducer', () => {
  let initialState: State;

  beforeEach(() => {
    initialState = { toasts: [] };
  });

  describe('ADD_TOAST', () => {
    it('should add a toast to the list', () => {
      const toast = { id: '1', title: 'Hello' } as ToasterToast;
      const result = reducer(initialState, {
        type: 'ADD_TOAST',
        toast: toast as any,
      });

      expect(result.toasts).toHaveLength(1);
      expect(result.toasts[0].id).toBe('1');
      expect(result.toasts[0].title).toBe('Hello');
    });

    it('should replace existing toast when limit is reached (TOAST_LIMIT=1)', () => {
      const state: State = {
        toasts: [{ id: '1', title: 'First' } as ToasterToast],
      };

      const result = reducer(state, {
        type: 'ADD_TOAST',
        toast: { id: '2', title: 'Second' } as any,
      });

      // TOAST_LIMIT is 1, new toast prepended then sliced to 1
      expect(result.toasts).toHaveLength(1);
      expect(result.toasts[0].id).toBe('2');
    });
  });

  describe('UPDATE_TOAST', () => {
    it('should update matching toast', () => {
      const state: State = {
        toasts: [{ id: '1', title: 'Original' } as ToasterToast],
      };

      const result = reducer(state, {
        type: 'UPDATE_TOAST',
        toast: { id: '1', title: 'Updated' },
      });

      expect(result.toasts[0].title).toBe('Updated');
    });

    it('should not modify non-matching toasts', () => {
      const state: State = {
        toasts: [{ id: '1', title: 'Keep' } as ToasterToast],
      };

      const result = reducer(state, {
        type: 'UPDATE_TOAST',
        toast: { id: '999', title: 'Changed' },
      });

      expect(result.toasts[0].title).toBe('Keep');
    });
  });

  describe('DISMISS_TOAST', () => {
    it('should set open to false for specific toast', () => {
      const state: State = {
        toasts: [{ id: '1', title: 'Test', open: true } as ToasterToast],
      };

      const result = reducer(state, {
        type: 'DISMISS_TOAST',
        toastId: '1',
      });

      expect(result.toasts[0].open).toBe(false);
    });

    it('should dismiss all toasts when no toastId', () => {
      const state: State = {
        toasts: [
          { id: '1', open: true } as ToasterToast,
        ],
      };

      const result = reducer(state, {
        type: 'DISMISS_TOAST',
        toastId: undefined,
      });

      expect(result.toasts.every((t) => t.open === false)).toBe(true);
    });
  });

  describe('REMOVE_TOAST', () => {
    it('should remove specific toast', () => {
      const state: State = {
        toasts: [{ id: '1' } as ToasterToast],
      };

      const result = reducer(state, {
        type: 'REMOVE_TOAST',
        toastId: '1',
      });

      expect(result.toasts).toHaveLength(0);
    });

    it('should remove all toasts when no toastId', () => {
      const state: State = {
        toasts: [
          { id: '1' } as ToasterToast,
          { id: '2' } as ToasterToast,
        ],
      };

      const result = reducer(state, {
        type: 'REMOVE_TOAST',
        toastId: undefined,
      });

      expect(result.toasts).toEqual([]);
    });

    it('should not affect other toasts', () => {
      const state: State = {
        toasts: [
          { id: '1' } as ToasterToast,
          { id: '2' } as ToasterToast,
        ],
      };

      const result = reducer(state, {
        type: 'REMOVE_TOAST',
        toastId: '1',
      });

      expect(result.toasts).toHaveLength(1);
      expect(result.toasts[0].id).toBe('2');
    });
  });
});
