/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useReleaseStore, getUnreleasedVersions, getSelectedVersionInfo, canCreateRelease } from '../release-store';
import type { ReleaseableVersion } from '../../../shared/types';

function makeVersion(overrides: Partial<ReleaseableVersion> = {}): ReleaseableVersion {
  return {
    version: '1.0.0',
    date: '2024-01-01',
    content: '## 1.0.0\n- Feature A',
    isReleased: false,
    ...overrides,
  } as ReleaseableVersion;
}

describe('release-store', () => {
  beforeEach(() => {
    useReleaseStore.getState().reset();
  });

  describe('initial state', () => {
    it('should have correct defaults', () => {
      const state = useReleaseStore.getState();
      expect(state.releaseableVersions).toEqual([]);
      expect(state.isLoadingVersions).toBe(false);
      expect(state.selectedVersion).toBeNull();
      expect(state.preflightStatus).toBeNull();
      expect(state.isRunningPreflight).toBe(false);
      expect(state.createAsDraft).toBe(false);
      expect(state.markAsPrerelease).toBe(false);
      expect(state.releaseProgress).toBeNull();
      expect(state.isCreatingRelease).toBe(false);
      expect(state.lastReleaseResult).toBeNull();
      expect(state.error).toBeNull();
    });
  });

  describe('setSelectedVersion', () => {
    it('should set version and reset preflight/error', () => {
      useReleaseStore.setState({
        preflightStatus: { canRelease: true } as any,
        error: 'old error',
      });

      useReleaseStore.getState().setSelectedVersion('2.0.0');

      const state = useReleaseStore.getState();
      expect(state.selectedVersion).toBe('2.0.0');
      expect(state.preflightStatus).toBeNull();
      expect(state.error).toBeNull();
    });
  });

  describe('release options', () => {
    it('should set createAsDraft', () => {
      useReleaseStore.getState().setCreateAsDraft(true);
      expect(useReleaseStore.getState().createAsDraft).toBe(true);
    });

    it('should set markAsPrerelease', () => {
      useReleaseStore.getState().setMarkAsPrerelease(true);
      expect(useReleaseStore.getState().markAsPrerelease).toBe(true);
    });
  });

  describe('release progress', () => {
    it('should track release progress', () => {
      const progress = { stage: 'tagging' as const, progress: 50, message: 'Creating tag...' };
      useReleaseStore.getState().setReleaseProgress(progress);
      expect(useReleaseStore.getState().releaseProgress).toEqual(progress);
    });

    it('should set last release result', () => {
      const result = { success: true, releaseUrl: 'https://github.com/...' };
      useReleaseStore.getState().setLastReleaseResult(result as any);
      expect(useReleaseStore.getState().lastReleaseResult).toEqual(result);
    });
  });

  describe('reset', () => {
    it('should restore all initial state', () => {
      useReleaseStore.setState({
        releaseableVersions: [makeVersion()],
        selectedVersion: '1.0.0',
        isCreatingRelease: true,
        error: 'error',
        createAsDraft: true,
        markAsPrerelease: true,
      });

      useReleaseStore.getState().reset();

      const state = useReleaseStore.getState();
      expect(state.releaseableVersions).toEqual([]);
      expect(state.selectedVersion).toBeNull();
      expect(state.isCreatingRelease).toBe(false);
      expect(state.error).toBeNull();
      expect(state.createAsDraft).toBe(false);
      expect(state.markAsPrerelease).toBe(false);
    });
  });

  describe('selectors', () => {
    it('getUnreleasedVersions should filter out released versions', () => {
      useReleaseStore.setState({
        releaseableVersions: [
          makeVersion({ version: '1.0.0', isReleased: true }),
          makeVersion({ version: '1.1.0', isReleased: false }),
          makeVersion({ version: '2.0.0', isReleased: false }),
        ],
      });

      const unreleased = getUnreleasedVersions();
      expect(unreleased).toHaveLength(2);
      expect(unreleased.map((v) => v.version)).toEqual(['1.1.0', '2.0.0']);
    });

    it('getSelectedVersionInfo should return matching version', () => {
      useReleaseStore.setState({
        releaseableVersions: [
          makeVersion({ version: '1.0.0' }),
          makeVersion({ version: '2.0.0', content: 'v2 content' }),
        ],
        selectedVersion: '2.0.0',
      });

      const info = getSelectedVersionInfo();
      expect(info?.version).toBe('2.0.0');
      expect(info?.content).toBe('v2 content');
    });

    it('getSelectedVersionInfo should return undefined when no match', () => {
      useReleaseStore.setState({
        releaseableVersions: [makeVersion({ version: '1.0.0' })],
        selectedVersion: '99.0.0',
      });

      expect(getSelectedVersionInfo()).toBeUndefined();
    });

    describe('canCreateRelease', () => {
      it('should return true with valid state', () => {
        useReleaseStore.setState({
          selectedVersion: '1.0.0',
          preflightStatus: { canRelease: true } as any,
          isCreatingRelease: false,
        });
        expect(canCreateRelease()).toBe(true);
      });

      it('should return false when no version selected', () => {
        useReleaseStore.setState({
          selectedVersion: null,
          preflightStatus: { canRelease: true } as any,
          isCreatingRelease: false,
        });
        expect(canCreateRelease()).toBe(false);
      });

      it('should return false when preflight says cannot release', () => {
        useReleaseStore.setState({
          selectedVersion: '1.0.0',
          preflightStatus: { canRelease: false } as any,
          isCreatingRelease: false,
        });
        expect(canCreateRelease()).toBe(false);
      });

      it('should return false when already creating release', () => {
        useReleaseStore.setState({
          selectedVersion: '1.0.0',
          preflightStatus: { canRelease: true } as any,
          isCreatingRelease: true,
        });
        expect(canCreateRelease()).toBe(false);
      });

      it('should return false when no preflight run', () => {
        useReleaseStore.setState({
          selectedVersion: '1.0.0',
          preflightStatus: null,
          isCreatingRelease: false,
        });
        expect(canCreateRelease()).toBe(false);
      });
    });
  });
});
