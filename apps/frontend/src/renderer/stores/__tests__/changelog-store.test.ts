/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useChangelogStore, getSelectedTasks, getTasksWithSpecs, canGenerate, canSave } from '../changelog-store';
import type { ChangelogTask } from '../../../shared/types';

// Mock settings store
vi.mock('../settings-store', () => ({
  useSettingsStore: {
    getState: () => ({
      settings: {
        changelogFormat: 'keep-a-changelog',
        changelogAudience: 'user-facing',
        changelogEmojiLevel: 'none',
      },
    }),
  },
  saveSettings: vi.fn(),
}));

function makeTask(overrides: Partial<ChangelogTask> = {}): ChangelogTask {
  return {
    id: 'task-1',
    title: 'Test Task',
    status: 'done',
    hasSpecs: true,
    ...overrides,
  } as ChangelogTask;
}

describe('changelog-store', () => {
  beforeEach(() => {
    useChangelogStore.getState().reset();
  });

  describe('initial state', () => {
    it('should have correct defaults', () => {
      const state = useChangelogStore.getState();
      expect(state.doneTasks).toEqual([]);
      expect(state.selectedTaskIds).toEqual([]);
      expect(state.sourceMode).toBe('tasks');
      expect(state.format).toBe('keep-a-changelog');
      expect(state.audience).toBe('user-facing');
      expect(state.emojiLevel).toBe('none');
      expect(state.version).toBe('1.0.0');
      expect(state.isGenerating).toBe(false);
      expect(state.error).toBeNull();
      expect(state.gitHistoryType).toBe('recent');
      expect(state.gitHistoryCount).toBe(25);
      expect(state.includeMergeCommits).toBe(false);
    });
  });

  describe('task selection', () => {
    it('should toggle task selection on', () => {
      useChangelogStore.getState().toggleTaskSelection('task-1');
      expect(useChangelogStore.getState().selectedTaskIds).toContain('task-1');
    });

    it('should toggle task selection off', () => {
      useChangelogStore.setState({ selectedTaskIds: ['task-1'] });
      useChangelogStore.getState().toggleTaskSelection('task-1');
      expect(useChangelogStore.getState().selectedTaskIds).not.toContain('task-1');
    });

    it('should select all tasks', () => {
      const tasks = [makeTask({ id: 't1' }), makeTask({ id: 't2' }), makeTask({ id: 't3' })];
      useChangelogStore.setState({ doneTasks: tasks });

      useChangelogStore.getState().selectAllTasks();
      expect(useChangelogStore.getState().selectedTaskIds).toEqual(['t1', 't2', 't3']);
    });

    it('should deselect all tasks', () => {
      useChangelogStore.setState({ selectedTaskIds: ['t1', 't2'] });
      useChangelogStore.getState().deselectAllTasks();
      expect(useChangelogStore.getState().selectedTaskIds).toEqual([]);
    });
  });

  describe('setExistingChangelog', () => {
    it('should auto-suggest bumped version when lastVersion exists', () => {
      useChangelogStore.getState().setExistingChangelog({
        lastVersion: '2.3.4',
        content: '# Changelog',
        filePath: '/CHANGELOG.md',
      } as any);

      expect(useChangelogStore.getState().version).toBe('2.3.5');
    });

    it('should handle missing lastVersion', () => {
      useChangelogStore.setState({ version: '1.0.0' });
      useChangelogStore.getState().setExistingChangelog({
        content: '# Changelog',
        filePath: '/CHANGELOG.md',
      } as any);

      expect(useChangelogStore.getState().version).toBe('1.0.0');
    });

    it('should handle null changelog', () => {
      useChangelogStore.getState().setExistingChangelog(null);
      expect(useChangelogStore.getState().existingChangelog).toBeNull();
    });
  });

  describe('source mode', () => {
    it('should set source mode and clear preview commits', () => {
      useChangelogStore.setState({
        previewCommits: [{ hash: 'abc' }] as any,
        error: 'old error',
      });

      useChangelogStore.getState().setSourceMode('git-history');

      expect(useChangelogStore.getState().sourceMode).toBe('git-history');
      expect(useChangelogStore.getState().previewCommits).toEqual([]);
      expect(useChangelogStore.getState().error).toBeNull();
    });
  });

  describe('git data actions', () => {
    it('should set default branch and auto-set base branch if empty', () => {
      useChangelogStore.setState({ baseBranch: '' });
      useChangelogStore.getState().setDefaultBranch('main');

      expect(useChangelogStore.getState().defaultBranch).toBe('main');
      expect(useChangelogStore.getState().baseBranch).toBe('main');
    });

    it('should not override existing base branch', () => {
      useChangelogStore.setState({ baseBranch: 'develop' });
      useChangelogStore.getState().setDefaultBranch('main');

      expect(useChangelogStore.getState().baseBranch).toBe('develop');
    });

    it('should clear preview commits when changing git history type', () => {
      useChangelogStore.setState({ previewCommits: [{ hash: 'abc' }] as any });
      useChangelogStore.getState().setGitHistoryType('since-date');

      expect(useChangelogStore.getState().gitHistoryType).toBe('since-date');
      expect(useChangelogStore.getState().previewCommits).toEqual([]);
    });

    it('should clear preview commits when changing branches', () => {
      useChangelogStore.setState({ previewCommits: [{ hash: 'abc' }] as any });
      useChangelogStore.getState().setBaseBranch('develop');
      expect(useChangelogStore.getState().previewCommits).toEqual([]);

      useChangelogStore.setState({ previewCommits: [{ hash: 'abc' }] as any });
      useChangelogStore.getState().setCompareBranch('feature');
      expect(useChangelogStore.getState().previewCommits).toEqual([]);
    });
  });

  describe('generation config', () => {
    it('should set custom instructions', () => {
      useChangelogStore.getState().setCustomInstructions('Focus on breaking changes');
      expect(useChangelogStore.getState().customInstructions).toBe('Focus on breaking changes');
    });

    it('should initialize from settings', () => {
      useChangelogStore.getState().initializeFromSettings();
      const state = useChangelogStore.getState();
      expect(state.format).toBe('keep-a-changelog');
      expect(state.audience).toBe('user-facing');
      expect(state.emojiLevel).toBe('none');
    });
  });

  describe('generation state', () => {
    it('should track generation progress', () => {
      const progress = { stage: 'loading_specs' as const, progress: 50, message: 'Loading...' };
      useChangelogStore.getState().setGenerationProgress(progress);
      expect(useChangelogStore.getState().generationProgress).toEqual(progress);
    });

    it('should set generated changelog', () => {
      useChangelogStore.getState().setGeneratedChangelog('# v1.0.0\n- Feature A');
      expect(useChangelogStore.getState().generatedChangelog).toBe('# v1.0.0\n- Feature A');
    });

    it('should set error', () => {
      useChangelogStore.getState().setError('Generation failed');
      expect(useChangelogStore.getState().error).toBe('Generation failed');
    });
  });

  describe('reset', () => {
    it('should restore initial state', () => {
      useChangelogStore.setState({
        doneTasks: [makeTask()],
        selectedTaskIds: ['task-1'],
        sourceMode: 'git-history',
        generatedChangelog: 'some content',
        isGenerating: true,
        error: 'error',
      });

      useChangelogStore.getState().reset();

      const state = useChangelogStore.getState();
      expect(state.doneTasks).toEqual([]);
      expect(state.selectedTaskIds).toEqual([]);
      expect(state.sourceMode).toBe('tasks');
      expect(state.generatedChangelog).toBe('');
      expect(state.isGenerating).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('selectors', () => {
    it('getSelectedTasks should return only selected tasks', () => {
      useChangelogStore.setState({
        doneTasks: [makeTask({ id: 't1' }), makeTask({ id: 't2' }), makeTask({ id: 't3' })],
        selectedTaskIds: ['t1', 't3'],
      });

      const selected = getSelectedTasks();
      expect(selected).toHaveLength(2);
      expect(selected.map((t) => t.id)).toEqual(['t1', 't3']);
    });

    it('getTasksWithSpecs should filter tasks with specs', () => {
      useChangelogStore.setState({
        doneTasks: [
          makeTask({ id: 't1', hasSpecs: true }),
          makeTask({ id: 't2', hasSpecs: false }),
        ],
      });

      const withSpecs = getTasksWithSpecs();
      expect(withSpecs).toHaveLength(1);
      expect(withSpecs[0].id).toBe('t1');
    });

    describe('canGenerate', () => {
      it('should return false when generating', () => {
        useChangelogStore.setState({ isGenerating: true, selectedTaskIds: ['t1'] });
        expect(canGenerate()).toBe(false);
      });

      it('should return true for tasks mode with selected tasks', () => {
        useChangelogStore.setState({
          sourceMode: 'tasks',
          selectedTaskIds: ['t1'],
          isGenerating: false,
        });
        expect(canGenerate()).toBe(true);
      });

      it('should return false for tasks mode with no selected tasks', () => {
        useChangelogStore.setState({
          sourceMode: 'tasks',
          selectedTaskIds: [],
          isGenerating: false,
        });
        expect(canGenerate()).toBe(false);
      });

      it('should return true for git-history mode with commits', () => {
        useChangelogStore.setState({
          sourceMode: 'git-history',
          previewCommits: [{ hash: 'abc' }] as any,
          isGenerating: false,
        });
        expect(canGenerate()).toBe(true);
      });

      it('should return true for branch-diff mode with valid branches and commits', () => {
        useChangelogStore.setState({
          sourceMode: 'branch-diff',
          baseBranch: 'main',
          compareBranch: 'feature',
          previewCommits: [{ hash: 'abc' }] as any,
          isGenerating: false,
        });
        expect(canGenerate()).toBe(true);
      });

      it('should return false for branch-diff when branches are same', () => {
        useChangelogStore.setState({
          sourceMode: 'branch-diff',
          baseBranch: 'main',
          compareBranch: 'main',
          previewCommits: [{ hash: 'abc' }] as any,
          isGenerating: false,
        });
        expect(canGenerate()).toBe(false);
      });
    });

    describe('canSave', () => {
      it('should return true when changelog exists and not generating', () => {
        useChangelogStore.setState({
          generatedChangelog: '# Changelog',
          isGenerating: false,
        });
        expect(canSave()).toBe(true);
      });

      it('should return false when no changelog', () => {
        useChangelogStore.setState({ generatedChangelog: '', isGenerating: false });
        expect(canSave()).toBe(false);
      });

      it('should return false when generating', () => {
        useChangelogStore.setState({
          generatedChangelog: '# Changelog',
          isGenerating: true,
        });
        expect(canSave()).toBe(false);
      });
    });
  });
});
