/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useClaudeProfileStore } from '../claude-profile-store';
import type { ClaudeProfile } from '../../../shared/types';

function makeProfile(overrides: Partial<ClaudeProfile> = {}): ClaudeProfile {
  return {
    id: 'profile-1',
    name: 'Default',
    model: 'claude-sonnet-4-5-20250929',
    maxThinkingTokens: 10000,
    ...overrides,
  } as ClaudeProfile;
}

describe('claude-profile-store', () => {
  beforeEach(() => {
    useClaudeProfileStore.setState({
      profiles: [],
      activeProfileId: 'default',
      isLoading: false,
      isSwitching: false,
    });
  });

  describe('initial state', () => {
    it('should have empty profiles and default active profile', () => {
      const state = useClaudeProfileStore.getState();
      expect(state.profiles).toEqual([]);
      expect(state.activeProfileId).toBe('default');
      expect(state.isLoading).toBe(false);
      expect(state.isSwitching).toBe(false);
    });
  });

  describe('setProfiles', () => {
    it('should set profiles and active profile id from settings', () => {
      const profiles = [makeProfile(), makeProfile({ id: 'profile-2', name: 'Custom' })];
      useClaudeProfileStore.getState().setProfiles({
        profiles,
        activeProfileId: 'profile-2',
      });

      const state = useClaudeProfileStore.getState();
      expect(state.profiles).toHaveLength(2);
      expect(state.activeProfileId).toBe('profile-2');
    });
  });

  describe('setActiveProfile', () => {
    it('should update active profile id', () => {
      useClaudeProfileStore.getState().setActiveProfile('profile-3');
      expect(useClaudeProfileStore.getState().activeProfileId).toBe('profile-3');
    });
  });

  describe('addProfile', () => {
    it('should append a new profile', () => {
      const existing = makeProfile({ id: 'p1' });
      useClaudeProfileStore.setState({ profiles: [existing] });

      const newProfile = makeProfile({ id: 'p2', name: 'New' });
      useClaudeProfileStore.getState().addProfile(newProfile);

      const profiles = useClaudeProfileStore.getState().profiles;
      expect(profiles).toHaveLength(2);
      expect(profiles[1].id).toBe('p2');
    });
  });

  describe('updateProfile', () => {
    it('should update an existing profile by id', () => {
      const p1 = makeProfile({ id: 'p1', name: 'Old Name' });
      const p2 = makeProfile({ id: 'p2', name: 'Other' });
      useClaudeProfileStore.setState({ profiles: [p1, p2] });

      const updated = { ...p1, name: 'New Name' };
      useClaudeProfileStore.getState().updateProfile(updated);

      const profiles = useClaudeProfileStore.getState().profiles;
      expect(profiles[0].name).toBe('New Name');
      expect(profiles[1].name).toBe('Other');
    });

    it('should not modify other profiles', () => {
      const p1 = makeProfile({ id: 'p1' });
      const p2 = makeProfile({ id: 'p2', name: 'Unchanged' });
      useClaudeProfileStore.setState({ profiles: [p1, p2] });

      useClaudeProfileStore.getState().updateProfile({ ...p1, name: 'Updated' });
      expect(useClaudeProfileStore.getState().profiles[1].name).toBe('Unchanged');
    });
  });

  describe('removeProfile', () => {
    it('should remove a profile by id', () => {
      const p1 = makeProfile({ id: 'p1' });
      const p2 = makeProfile({ id: 'p2' });
      useClaudeProfileStore.setState({ profiles: [p1, p2] });

      useClaudeProfileStore.getState().removeProfile('p1');

      const profiles = useClaudeProfileStore.getState().profiles;
      expect(profiles).toHaveLength(1);
      expect(profiles[0].id).toBe('p2');
    });

    it('should handle removing non-existent profile', () => {
      const p1 = makeProfile({ id: 'p1' });
      useClaudeProfileStore.setState({ profiles: [p1] });

      useClaudeProfileStore.getState().removeProfile('non-existent');
      expect(useClaudeProfileStore.getState().profiles).toHaveLength(1);
    });
  });

  describe('loading and switching flags', () => {
    it('should set loading state', () => {
      useClaudeProfileStore.getState().setLoading(true);
      expect(useClaudeProfileStore.getState().isLoading).toBe(true);

      useClaudeProfileStore.getState().setLoading(false);
      expect(useClaudeProfileStore.getState().isLoading).toBe(false);
    });

    it('should set switching state', () => {
      useClaudeProfileStore.getState().setSwitching(true);
      expect(useClaudeProfileStore.getState().isSwitching).toBe(true);

      useClaudeProfileStore.getState().setSwitching(false);
      expect(useClaudeProfileStore.getState().isSwitching).toBe(false);
    });
  });
});
