/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useRateLimitStore } from '../rate-limit-store';

describe('rate-limit-store', () => {
  beforeEach(() => {
    useRateLimitStore.setState({
      isModalOpen: false,
      rateLimitInfo: null,
      isSDKModalOpen: false,
      sdkRateLimitInfo: null,
      hasPendingRateLimit: false,
      pendingRateLimitType: null,
    });
  });

  describe('initial state', () => {
    it('should start with all modals closed', () => {
      const state = useRateLimitStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.isSDKModalOpen).toBe(false);
      expect(state.hasPendingRateLimit).toBe(false);
      expect(state.pendingRateLimitType).toBeNull();
    });
  });

  describe('terminal rate limit modal', () => {
    const mockInfo = {
      type: 'rate_limit' as const,
      message: 'Rate limited',
      retryAfter: 60,
    };

    it('should show terminal rate limit modal', () => {
      useRateLimitStore.getState().showRateLimitModal(mockInfo as any);
      const state = useRateLimitStore.getState();
      expect(state.isModalOpen).toBe(true);
      expect(state.rateLimitInfo).toEqual(mockInfo);
      expect(state.hasPendingRateLimit).toBe(true);
      expect(state.pendingRateLimitType).toBe('terminal');
    });

    it('should hide modal but keep pending state', () => {
      useRateLimitStore.getState().showRateLimitModal(mockInfo as any);
      useRateLimitStore.getState().hideRateLimitModal();
      const state = useRateLimitStore.getState();
      expect(state.isModalOpen).toBe(false);
      expect(state.hasPendingRateLimit).toBe(true);
      expect(state.rateLimitInfo).toEqual(mockInfo);
    });
  });

  describe('SDK rate limit modal', () => {
    const mockSDKInfo = {
      type: 'sdk_rate_limit' as const,
      message: 'SDK rate limited',
      retryAfter: 120,
    };

    it('should show SDK rate limit modal', () => {
      useRateLimitStore.getState().showSDKRateLimitModal(mockSDKInfo as any);
      const state = useRateLimitStore.getState();
      expect(state.isSDKModalOpen).toBe(true);
      expect(state.sdkRateLimitInfo).toEqual(mockSDKInfo);
      expect(state.hasPendingRateLimit).toBe(true);
      expect(state.pendingRateLimitType).toBe('sdk');
    });

    it('should hide SDK modal but keep pending state', () => {
      useRateLimitStore.getState().showSDKRateLimitModal(mockSDKInfo as any);
      useRateLimitStore.getState().hideSDKRateLimitModal();
      const state = useRateLimitStore.getState();
      expect(state.isSDKModalOpen).toBe(false);
      expect(state.hasPendingRateLimit).toBe(true);
    });
  });

  describe('reopenRateLimitModal', () => {
    it('should reopen terminal modal', () => {
      const mockInfo = { type: 'rate_limit', message: 'Rate limited' };
      useRateLimitStore.getState().showRateLimitModal(mockInfo as any);
      useRateLimitStore.getState().hideRateLimitModal();
      expect(useRateLimitStore.getState().isModalOpen).toBe(false);

      useRateLimitStore.getState().reopenRateLimitModal();
      expect(useRateLimitStore.getState().isModalOpen).toBe(true);
    });

    it('should reopen SDK modal', () => {
      const mockSDKInfo = { type: 'sdk_rate_limit', message: 'SDK rate limited' };
      useRateLimitStore.getState().showSDKRateLimitModal(mockSDKInfo as any);
      useRateLimitStore.getState().hideSDKRateLimitModal();
      expect(useRateLimitStore.getState().isSDKModalOpen).toBe(false);

      useRateLimitStore.getState().reopenRateLimitModal();
      expect(useRateLimitStore.getState().isSDKModalOpen).toBe(true);
    });

    it('should do nothing if no pending rate limit', () => {
      useRateLimitStore.getState().reopenRateLimitModal();
      expect(useRateLimitStore.getState().isModalOpen).toBe(false);
      expect(useRateLimitStore.getState().isSDKModalOpen).toBe(false);
    });
  });

  describe('clearPendingRateLimit', () => {
    it('should clear all pending state', () => {
      useRateLimitStore.getState().showRateLimitModal({ type: 'rate_limit', message: 'rl' } as any);
      useRateLimitStore.getState().clearPendingRateLimit();
      const state = useRateLimitStore.getState();
      expect(state.hasPendingRateLimit).toBe(false);
      expect(state.pendingRateLimitType).toBeNull();
      expect(state.rateLimitInfo).toBeNull();
      expect(state.sdkRateLimitInfo).toBeNull();
    });
  });
});
