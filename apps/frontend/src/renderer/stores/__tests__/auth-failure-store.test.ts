/**
 * @vitest-environment jsdom
 */
/**
 * Tests for auth-failure-store (Zustand)
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthFailureStore } from '../auth-failure-store';
import type { AuthFailureInfo } from '../../../shared/types';

// Test data
const testAuthFailureInfo: AuthFailureInfo = {
  profileId: 'profile-123',
  profileName: 'Production API',
  failureType: 'invalid',
  message: 'API key is invalid or expired',
  originalError: 'Authentication failed: 401 Unauthorized',
  detectedAt: new Date('2024-01-01T12:00:00Z')
};

const testAuthFailureMinimal: AuthFailureInfo = {
  profileId: 'profile-456',
  failureType: 'missing',
  message: 'API key not found',
  detectedAt: new Date('2024-01-01T12:00:00Z')
};

describe('auth-failure-store', () => {
  beforeEach(() => {
    // Reset store to initial state
    useAuthFailureStore.setState({
      isModalOpen: false,
      authFailureInfo: null,
      hasPendingAuthFailure: false
    });
  });

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useAuthFailureStore.getState();

      expect(state.isModalOpen).toBe(false);
      expect(state.authFailureInfo).toBeNull();
      expect(state.hasPendingAuthFailure).toBe(false);
    });
  });

  describe('showAuthFailureModal', () => {
    it('should open modal and set auth failure info with all fields', () => {
      const { showAuthFailureModal } = useAuthFailureStore.getState();

      showAuthFailureModal(testAuthFailureInfo);

      const state = useAuthFailureStore.getState();
      expect(state.isModalOpen).toBe(true);
      expect(state.authFailureInfo).toEqual(testAuthFailureInfo);
      expect(state.hasPendingAuthFailure).toBe(true);
    });

    it('should handle minimal auth failure info', () => {
      const { showAuthFailureModal } = useAuthFailureStore.getState();

      showAuthFailureModal(testAuthFailureMinimal);

      const state = useAuthFailureStore.getState();
      expect(state.isModalOpen).toBe(true);
      expect(state.authFailureInfo).toEqual(testAuthFailureMinimal);
      expect(state.hasPendingAuthFailure).toBe(true);
    });

    it('should update existing failure info when called again', () => {
      const { showAuthFailureModal } = useAuthFailureStore.getState();

      // First failure
      showAuthFailureModal(testAuthFailureInfo);
      expect(useAuthFailureStore.getState().authFailureInfo?.profileId).toBe('profile-123');

      // Second failure overwrites first
      showAuthFailureModal(testAuthFailureMinimal);
      const state = useAuthFailureStore.getState();
      expect(state.authFailureInfo?.profileId).toBe('profile-456');
      expect(state.isModalOpen).toBe(true);
      expect(state.hasPendingAuthFailure).toBe(true);
    });

    it('should handle all failure types', () => {
      const { showAuthFailureModal } = useAuthFailureStore.getState();

      const failureTypes: Array<AuthFailureInfo['failureType']> = ['missing', 'invalid', 'expired', 'unknown'];

      failureTypes.forEach((failureType) => {
        const failureInfo: AuthFailureInfo = {
          profileId: `profile-${failureType}`,
          failureType,
          message: `Test ${failureType} failure`,
          detectedAt: new Date('2024-01-01T12:00:00Z')
        };

        showAuthFailureModal(failureInfo);

        const state = useAuthFailureStore.getState();
        expect(state.authFailureInfo?.failureType).toBe(failureType);
        expect(state.isModalOpen).toBe(true);
        expect(state.hasPendingAuthFailure).toBe(true);
      });
    });
  });

  describe('hideAuthFailureModal', () => {
    it('should close modal but keep failure info', () => {
      const { showAuthFailureModal, hideAuthFailureModal } = useAuthFailureStore.getState();

      // First show the modal
      showAuthFailureModal(testAuthFailureInfo);
      expect(useAuthFailureStore.getState().isModalOpen).toBe(true);

      // Then hide it
      hideAuthFailureModal();

      const state = useAuthFailureStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.authFailureInfo).toEqual(testAuthFailureInfo);
      expect(state.hasPendingAuthFailure).toBe(true);
    });

    it('should be idempotent when called multiple times', () => {
      const { showAuthFailureModal, hideAuthFailureModal } = useAuthFailureStore.getState();

      showAuthFailureModal(testAuthFailureInfo);
      hideAuthFailureModal();
      hideAuthFailureModal();
      hideAuthFailureModal();

      const state = useAuthFailureStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.authFailureInfo).toEqual(testAuthFailureInfo);
      expect(state.hasPendingAuthFailure).toBe(true);
    });

    it('should work even when modal is not open', () => {
      const { hideAuthFailureModal } = useAuthFailureStore.getState();

      hideAuthFailureModal();

      const state = useAuthFailureStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.authFailureInfo).toBeNull();
      expect(state.hasPendingAuthFailure).toBe(false);
    });
  });

  describe('clearAuthFailure', () => {
    it('should clear all auth failure state', () => {
      const { showAuthFailureModal, clearAuthFailure } = useAuthFailureStore.getState();

      // First show the modal
      showAuthFailureModal(testAuthFailureInfo);
      expect(useAuthFailureStore.getState().isModalOpen).toBe(true);
      expect(useAuthFailureStore.getState().authFailureInfo).not.toBeNull();
      expect(useAuthFailureStore.getState().hasPendingAuthFailure).toBe(true);

      // Then clear everything
      clearAuthFailure();

      const state = useAuthFailureStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.authFailureInfo).toBeNull();
      expect(state.hasPendingAuthFailure).toBe(false);
    });

    it('should be idempotent when called multiple times', () => {
      const { showAuthFailureModal, clearAuthFailure } = useAuthFailureStore.getState();

      showAuthFailureModal(testAuthFailureInfo);
      clearAuthFailure();
      clearAuthFailure();
      clearAuthFailure();

      const state = useAuthFailureStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.authFailureInfo).toBeNull();
      expect(state.hasPendingAuthFailure).toBe(false);
    });

    it('should work even when no failure is present', () => {
      const { clearAuthFailure } = useAuthFailureStore.getState();

      clearAuthFailure();

      const state = useAuthFailureStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.authFailureInfo).toBeNull();
      expect(state.hasPendingAuthFailure).toBe(false);
    });
  });

  describe('workflow scenarios', () => {
    it('should handle show -> hide -> show workflow', () => {
      const { showAuthFailureModal, hideAuthFailureModal } = useAuthFailureStore.getState();

      // Show first failure
      showAuthFailureModal(testAuthFailureInfo);
      expect(useAuthFailureStore.getState().isModalOpen).toBe(true);

      // Hide modal
      hideAuthFailureModal();
      expect(useAuthFailureStore.getState().isModalOpen).toBe(false);
      expect(useAuthFailureStore.getState().authFailureInfo).toEqual(testAuthFailureInfo);

      // Show modal again (user can see the same failure info again)
      showAuthFailureModal(testAuthFailureInfo);
      const state = useAuthFailureStore.getState();
      expect(state.isModalOpen).toBe(true);
      expect(state.authFailureInfo).toEqual(testAuthFailureInfo);
      expect(state.hasPendingAuthFailure).toBe(true);
    });

    it('should handle show -> hide -> clear workflow', () => {
      const { showAuthFailureModal, hideAuthFailureModal, clearAuthFailure } = useAuthFailureStore.getState();

      // Show failure
      showAuthFailureModal(testAuthFailureInfo);
      expect(useAuthFailureStore.getState().isModalOpen).toBe(true);

      // Hide modal (failure still pending)
      hideAuthFailureModal();
      expect(useAuthFailureStore.getState().isModalOpen).toBe(false);
      expect(useAuthFailureStore.getState().hasPendingAuthFailure).toBe(true);

      // Clear failure (user resolved the issue)
      clearAuthFailure();
      const state = useAuthFailureStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.authFailureInfo).toBeNull();
      expect(state.hasPendingAuthFailure).toBe(false);
    });

    it('should handle show -> clear without hide', () => {
      const { showAuthFailureModal, clearAuthFailure } = useAuthFailureStore.getState();

      // Show failure
      showAuthFailureModal(testAuthFailureInfo);
      expect(useAuthFailureStore.getState().isModalOpen).toBe(true);

      // Clear directly without hiding first
      clearAuthFailure();
      const state = useAuthFailureStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.authFailureInfo).toBeNull();
      expect(state.hasPendingAuthFailure).toBe(false);
    });

    it('should preserve pending status when hiding modal', () => {
      const { showAuthFailureModal, hideAuthFailureModal } = useAuthFailureStore.getState();

      showAuthFailureModal(testAuthFailureInfo);
      hideAuthFailureModal();

      const state = useAuthFailureStore.getState();
      // This allows the UI to show a badge/indicator that there's an unresolved auth failure
      expect(state.hasPendingAuthFailure).toBe(true);
      expect(state.authFailureInfo).not.toBeNull();
    });
  });
});
