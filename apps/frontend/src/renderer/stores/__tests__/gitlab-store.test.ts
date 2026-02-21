/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useGitLabStore } from '../gitlab-store';
import type { GitLabIssue } from '../../../shared/types';

function makeIssue(overrides: Partial<GitLabIssue> = {}): GitLabIssue {
  return {
    iid: 1,
    title: 'Test Issue',
    description: 'Description',
    state: 'opened',
    labels: [],
    author: { name: 'user', username: 'user', avatar_url: '' },
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    web_url: 'https://gitlab.com/issues/1',
    ...overrides,
  } as GitLabIssue;
}

describe('gitlab-store', () => {
  beforeEach(() => {
    useGitLabStore.getState().clearIssues();
  });

  describe('initial state', () => {
    it('should have correct initial values', () => {
      const state = useGitLabStore.getState();
      expect(state.issues).toEqual([]);
      expect(state.syncStatus).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
      expect(state.selectedIssueIid).toBeNull();
      expect(state.filterState).toBe('opened');
      expect(state.investigationStatus.phase).toBe('idle');
      expect(state.lastInvestigationResult).toBeNull();
    });
  });

  describe('setIssues', () => {
    it('should set issues and clear error', () => {
      useGitLabStore.setState({ error: 'old error' });
      const issues = [makeIssue({ iid: 1 }), makeIssue({ iid: 2 })];

      useGitLabStore.getState().setIssues(issues);

      expect(useGitLabStore.getState().issues).toHaveLength(2);
      expect(useGitLabStore.getState().error).toBeNull();
    });
  });

  describe('addIssue', () => {
    it('should add new issue at the beginning', () => {
      useGitLabStore.setState({ issues: [makeIssue({ iid: 1 })] });

      useGitLabStore.getState().addIssue(makeIssue({ iid: 2, title: 'New' }));

      const issues = useGitLabStore.getState().issues;
      expect(issues).toHaveLength(2);
      expect(issues[0].iid).toBe(2);
    });

    it('should replace existing issue with same iid', () => {
      useGitLabStore.setState({
        issues: [makeIssue({ iid: 1, title: 'Old' })],
      });

      useGitLabStore.getState().addIssue(makeIssue({ iid: 1, title: 'Updated' }));

      const issues = useGitLabStore.getState().issues;
      expect(issues).toHaveLength(1);
      expect(issues[0].title).toBe('Updated');
    });
  });

  describe('updateIssue', () => {
    it('should update issue fields by iid', () => {
      useGitLabStore.setState({
        issues: [makeIssue({ iid: 1, title: 'Original' })],
      });

      useGitLabStore.getState().updateIssue(1, { title: 'Updated' });

      expect(useGitLabStore.getState().issues[0].title).toBe('Updated');
    });

    it('should not affect other issues', () => {
      useGitLabStore.setState({
        issues: [
          makeIssue({ iid: 1, title: 'First' }),
          makeIssue({ iid: 2, title: 'Second' }),
        ],
      });

      useGitLabStore.getState().updateIssue(1, { title: 'Changed' });

      expect(useGitLabStore.getState().issues[1].title).toBe('Second');
    });
  });

  describe('selectIssue', () => {
    it('should set selected issue iid', () => {
      useGitLabStore.getState().selectIssue(5);
      expect(useGitLabStore.getState().selectedIssueIid).toBe(5);
    });

    it('should allow deselection with null', () => {
      useGitLabStore.getState().selectIssue(5);
      useGitLabStore.getState().selectIssue(null);
      expect(useGitLabStore.getState().selectedIssueIid).toBeNull();
    });
  });

  describe('setFilterState', () => {
    it('should update filter state', () => {
      useGitLabStore.getState().setFilterState('closed');
      expect(useGitLabStore.getState().filterState).toBe('closed');
    });
  });

  describe('setError', () => {
    it('should set error and clear loading', () => {
      useGitLabStore.setState({ isLoading: true });
      useGitLabStore.getState().setError('Something broke');

      expect(useGitLabStore.getState().error).toBe('Something broke');
      expect(useGitLabStore.getState().isLoading).toBe(false);
    });
  });

  describe('investigation state', () => {
    it('should set investigation status', () => {
      const status = { phase: 'fetching' as const, issueIid: 1, progress: 50, message: 'Analyzing...' };
      useGitLabStore.getState().setInvestigationStatus(status);
      expect(useGitLabStore.getState().investigationStatus).toEqual(status);
    });

    it('should set investigation result', () => {
      const result = { summary: 'Found the bug', suggestions: [] };
      useGitLabStore.getState().setInvestigationResult(result as any);
      expect(useGitLabStore.getState().lastInvestigationResult).toEqual(result);
    });
  });

  describe('clearIssues', () => {
    it('should reset all state', () => {
      useGitLabStore.setState({
        issues: [makeIssue()],
        syncStatus: { connected: true } as any,
        selectedIssueIid: 1,
        error: 'error',
        investigationStatus: { phase: 'fetching', progress: 50, message: 'test' } as any,
        lastInvestigationResult: { summary: 'test' } as any,
      });

      useGitLabStore.getState().clearIssues();

      const state = useGitLabStore.getState();
      expect(state.issues).toEqual([]);
      expect(state.syncStatus).toBeNull();
      expect(state.selectedIssueIid).toBeNull();
      expect(state.error).toBeNull();
      expect(state.investigationStatus.phase).toBe('idle');
      expect(state.lastInvestigationResult).toBeNull();
    });
  });

  describe('selectors', () => {
    it('getSelectedIssue should return issue matching selectedIssueIid', () => {
      const issue = makeIssue({ iid: 5, title: 'Selected' });
      useGitLabStore.setState({
        issues: [makeIssue({ iid: 1 }), issue, makeIssue({ iid: 10 })],
        selectedIssueIid: 5,
      });

      expect(useGitLabStore.getState().getSelectedIssue()?.title).toBe('Selected');
    });

    it('getSelectedIssue should return null when no match', () => {
      useGitLabStore.setState({ issues: [makeIssue({ iid: 1 })], selectedIssueIid: 99 });
      expect(useGitLabStore.getState().getSelectedIssue()).toBeNull();
    });

    it('getFilteredIssues should filter by state', () => {
      useGitLabStore.setState({
        issues: [
          makeIssue({ iid: 1, state: 'opened' }),
          makeIssue({ iid: 2, state: 'closed' }),
          makeIssue({ iid: 3, state: 'opened' }),
        ],
        filterState: 'opened',
      });

      const filtered = useGitLabStore.getState().getFilteredIssues();
      expect(filtered).toHaveLength(2);
      expect(filtered.every((i) => i.state === 'opened')).toBe(true);
    });

    it('getFilteredIssues should return all when filter is "all"', () => {
      useGitLabStore.setState({
        issues: [
          makeIssue({ iid: 1, state: 'opened' }),
          makeIssue({ iid: 2, state: 'closed' }),
        ],
        filterState: 'all',
      });

      expect(useGitLabStore.getState().getFilteredIssues()).toHaveLength(2);
    });

    it('getOpenIssuesCount should count only opened issues', () => {
      useGitLabStore.setState({
        issues: [
          makeIssue({ iid: 1, state: 'opened' }),
          makeIssue({ iid: 2, state: 'closed' }),
          makeIssue({ iid: 3, state: 'opened' }),
        ],
      });

      expect(useGitLabStore.getState().getOpenIssuesCount()).toBe(2);
    });
  });
});
