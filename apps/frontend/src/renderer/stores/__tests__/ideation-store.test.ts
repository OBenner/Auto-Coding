/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  useIdeationStore,
  getIdeasByType,
  getIdeasByStatus,
  getActiveIdeas,
  getArchivedIdeas,
  getIdeationSummary,
  isCodeImprovementIdea,
  isUIUXIdea,
} from '../ideation-store';
import type { Idea, IdeationSession, IdeationType } from '../../../shared/types';

// Mock constants
vi.mock('../../../shared/constants', () => ({
  DEFAULT_IDEATION_CONFIG: {
    enabledTypes: ['code_improvements', 'ui_ux_improvements'],
    includeRoadmapContext: true,
    includeKanbanContext: true,
    maxIdeasPerType: 5,
  },
}));

function makeIdea(overrides: Record<string, unknown> = {}): Idea {
  return {
    id: 'idea-1',
    title: 'Test Idea',
    description: 'A test idea',
    rationale: 'Test rationale',
    type: 'code_improvements',
    status: 'draft',
    createdAt: new Date(),
    buildsUpon: [],
    estimatedEffort: 'medium',
    affectedFiles: [],
    existingPatterns: [],
    ...overrides,
  } as unknown as Idea;
}

function makeSession(ideas: Idea[] = []): IdeationSession {
  return {
    id: 'session-1',
    projectId: 'proj-1',
    config: {
      enabledTypes: ['code_improvements', 'ui_ux_improvements'] as IdeationType[],
      includeRoadmapContext: true,
      includeKanbanContext: true,
      maxIdeasPerType: 5,
    },
    ideas,
    projectContext: { existingFeatures: [], techStack: [], plannedFeatures: [] },
    generatedAt: new Date(),
    updatedAt: new Date(),
  };
}

describe('ideation-store', () => {
  beforeEach(() => {
    useIdeationStore.setState({
      currentProjectId: null,
      session: null,
      generationStatus: { phase: 'idle', progress: 0, message: '' },
      config: {
        enabledTypes: ['code_improvements', 'ui_ux_improvements'] as IdeationType[],
        includeRoadmapContext: true,
        includeKanbanContext: true,
        maxIdeasPerType: 5,
      },
      logs: [],
      typeStates: {
        code_improvements: 'pending',
        ui_ux_improvements: 'pending',
        documentation_gaps: 'pending',
        security_hardening: 'pending',
        performance_optimizations: 'pending',
        code_quality: 'pending',
      },
      selectedIds: new Set<string>(),
      isGenerating: false,
    });
  });

  describe('setCurrentProjectId', () => {
    it('should clear state when switching projects', () => {
      useIdeationStore.setState({
        currentProjectId: 'proj-1',
        session: makeSession([makeIdea()]),
        isGenerating: true,
        logs: ['log1'],
      });

      useIdeationStore.getState().setCurrentProjectId('proj-2');

      const state = useIdeationStore.getState();
      expect(state.currentProjectId).toBe('proj-2');
      expect(state.session).toBeNull();
      expect(state.isGenerating).toBe(false);
      expect(state.logs).toEqual([]);
    });

    it('should not clear state when same project', () => {
      const session = makeSession([makeIdea()]);
      useIdeationStore.setState({
        currentProjectId: 'proj-1',
        session,
      });

      useIdeationStore.getState().setCurrentProjectId('proj-1');
      expect(useIdeationStore.getState().session).toEqual(session);
    });
  });

  describe('setConfig', () => {
    it('should merge partial config', () => {
      useIdeationStore.getState().setConfig({ maxIdeasPerType: 10 });
      const config = useIdeationStore.getState().config;
      expect(config.maxIdeasPerType).toBe(10);
      expect(config.includeRoadmapContext).toBe(true); // unchanged
    });
  });

  describe('idea status management', () => {
    const session = makeSession([
      makeIdea({ id: 'i1', status: 'draft' }),
      makeIdea({ id: 'i2', status: 'draft' }),
    ]);

    it('should update idea status', () => {
      useIdeationStore.setState({ session });
      useIdeationStore.getState().updateIdeaStatus('i1', 'selected');

      const ideas = useIdeationStore.getState().session!.ideas;
      expect(ideas[0].status).toBe('selected');
      expect(ideas[1].status).toBe('draft');
    });

    it('should dismiss idea', () => {
      useIdeationStore.setState({ session });
      useIdeationStore.getState().dismissIdea('i1');

      expect(useIdeationStore.getState().session!.ideas[0].status).toBe('dismissed');
    });

    it('should archive idea', () => {
      useIdeationStore.setState({ session });
      useIdeationStore.getState().archiveIdea('i1');

      expect(useIdeationStore.getState().session!.ideas[0].status).toBe('archived');
    });

    it('should set idea task id and archive it', () => {
      useIdeationStore.setState({ session });
      useIdeationStore.getState().setIdeaTaskId('i1', 'task-1');

      const idea = useIdeationStore.getState().session!.ideas[0];
      expect(idea.taskId).toBe('task-1');
      expect(idea.status).toBe('archived');
    });

    it('should not modify state when no session', () => {
      useIdeationStore.getState().updateIdeaStatus('i1', 'selected');
      expect(useIdeationStore.getState().session).toBeNull();
    });
  });

  describe('dismissAllIdeas', () => {
    it('should dismiss all active ideas but keep dismissed/converted/archived', () => {
      const session = makeSession([
        makeIdea({ id: 'i1', status: 'draft' }),
        makeIdea({ id: 'i2', status: 'dismissed' }),
        makeIdea({ id: 'i3', status: 'converted' }),
        makeIdea({ id: 'i4', status: 'archived' }),
        makeIdea({ id: 'i5', status: 'selected' }),
      ]);
      useIdeationStore.setState({ session });

      useIdeationStore.getState().dismissAllIdeas();

      const ideas = useIdeationStore.getState().session!.ideas;
      expect(ideas[0].status).toBe('dismissed'); // was draft -> dismissed
      expect(ideas[1].status).toBe('dismissed'); // already dismissed
      expect(ideas[2].status).toBe('converted'); // unchanged
      expect(ideas[3].status).toBe('archived'); // unchanged
      expect(ideas[4].status).toBe('dismissed'); // was selected -> dismissed
    });
  });

  describe('deleteIdea', () => {
    it('should remove idea from session', () => {
      const session = makeSession([makeIdea({ id: 'i1' }), makeIdea({ id: 'i2' })]);
      useIdeationStore.setState({ session });

      useIdeationStore.getState().deleteIdea('i1');

      expect(useIdeationStore.getState().session!.ideas).toHaveLength(1);
      expect(useIdeationStore.getState().session!.ideas[0].id).toBe('i2');
    });

    it('should remove idea from selection', () => {
      const session = makeSession([makeIdea({ id: 'i1' })]);
      useIdeationStore.setState({ session, selectedIds: new Set(['i1']) });

      useIdeationStore.getState().deleteIdea('i1');

      expect(useIdeationStore.getState().selectedIds.has('i1')).toBe(false);
    });
  });

  describe('deleteMultipleIdeas', () => {
    it('should remove multiple ideas and clear their selection', () => {
      const session = makeSession([
        makeIdea({ id: 'i1' }),
        makeIdea({ id: 'i2' }),
        makeIdea({ id: 'i3' }),
      ]);
      useIdeationStore.setState({
        session,
        selectedIds: new Set(['i1', 'i2', 'i3']),
      });

      useIdeationStore.getState().deleteMultipleIdeas(['i1', 'i3']);

      expect(useIdeationStore.getState().session!.ideas).toHaveLength(1);
      expect(useIdeationStore.getState().session!.ideas[0].id).toBe('i2');
      expect(useIdeationStore.getState().selectedIds.has('i1')).toBe(false);
      expect(useIdeationStore.getState().selectedIds.has('i3')).toBe(false);
      expect(useIdeationStore.getState().selectedIds.has('i2')).toBe(true);
    });
  });

  describe('selection actions', () => {
    it('should toggle idea selection', () => {
      useIdeationStore.getState().toggleSelectIdea('i1');
      expect(useIdeationStore.getState().selectedIds.has('i1')).toBe(true);

      useIdeationStore.getState().toggleSelectIdea('i1');
      expect(useIdeationStore.getState().selectedIds.has('i1')).toBe(false);
    });

    it('should select all ideas', () => {
      useIdeationStore.getState().selectAllIdeas(['i1', 'i2', 'i3']);
      expect(useIdeationStore.getState().selectedIds.size).toBe(3);
    });

    it('should clear selection', () => {
      useIdeationStore.setState({ selectedIds: new Set(['i1', 'i2']) });
      useIdeationStore.getState().clearSelection();
      expect(useIdeationStore.getState().selectedIds.size).toBe(0);
    });
  });

  describe('logs', () => {
    it('should add logs and keep last 100', () => {
      for (let i = 0; i < 105; i++) {
        useIdeationStore.getState().addLog(`log-${i}`);
      }
      expect(useIdeationStore.getState().logs).toHaveLength(100);
      expect(useIdeationStore.getState().logs[0]).toBe('log-5');
    });

    it('should clear logs', () => {
      useIdeationStore.setState({ logs: ['a', 'b'] });
      useIdeationStore.getState().clearLogs();
      expect(useIdeationStore.getState().logs).toEqual([]);
    });
  });

  describe('type states', () => {
    it('should initialize type states for enabled types', () => {
      useIdeationStore.getState().initializeTypeStates([
        'code_improvements',
        'security_hardening',
      ] as IdeationType[]);

      const typeStates = useIdeationStore.getState().typeStates;
      expect(typeStates.code_improvements).toBe('generating');
      expect(typeStates.security_hardening).toBe('generating');
      expect(typeStates.ui_ux_improvements).toBe('pending');
    });

    it('should set individual type state', () => {
      useIdeationStore.getState().setTypeState('code_improvements', 'completed');
      expect(useIdeationStore.getState().typeStates.code_improvements).toBe('completed');
    });

    it('should reset generating types', () => {
      useIdeationStore.setState({
        typeStates: {
          code_improvements: 'generating',
          ui_ux_improvements: 'completed',
          documentation_gaps: 'generating',
          security_hardening: 'pending',
          performance_optimizations: 'pending',
          code_quality: 'pending',
        },
      });

      useIdeationStore.getState().resetGeneratingTypes('failed');

      const typeStates = useIdeationStore.getState().typeStates;
      expect(typeStates.code_improvements).toBe('failed');
      expect(typeStates.ui_ux_improvements).toBe('completed'); // unchanged
      expect(typeStates.documentation_gaps).toBe('failed');
      expect(typeStates.security_hardening).toBe('pending'); // unchanged
    });
  });

  describe('addIdeasForType', () => {
    it('should create session if none exists', () => {
      const ideas = [makeIdea({ id: 'i1', type: 'code_improvements' })];
      useIdeationStore.getState().addIdeasForType('code_improvements', ideas);

      expect(useIdeationStore.getState().session).not.toBeNull();
      expect(useIdeationStore.getState().session!.ideas).toHaveLength(1);
      expect(useIdeationStore.getState().typeStates.code_improvements).toBe('completed');
    });

    it('should replace ideas of the same type in existing session', () => {
      const session = makeSession([
        makeIdea({ id: 'old1', type: 'code_improvements' }),
        makeIdea({ id: 'keep1', type: 'ui_ux_improvements' }),
      ]);
      useIdeationStore.setState({ session });

      const newIdeas = [makeIdea({ id: 'new1', type: 'code_improvements' })];
      useIdeationStore.getState().addIdeasForType('code_improvements', newIdeas);

      const ideas = useIdeationStore.getState().session!.ideas;
      expect(ideas).toHaveLength(2);
      expect(ideas.find((i) => i.id === 'old1')).toBeUndefined();
      expect(ideas.find((i) => i.id === 'keep1')).toBeDefined();
      expect(ideas.find((i) => i.id === 'new1')).toBeDefined();
    });
  });

  describe('clearSession', () => {
    it('should reset session-related state', () => {
      useIdeationStore.setState({
        session: makeSession([makeIdea()]),
        generationStatus: { phase: 'complete', progress: 100, message: 'Done' },
        selectedIds: new Set(['i1']),
      });

      useIdeationStore.getState().clearSession();

      const state = useIdeationStore.getState();
      expect(state.session).toBeNull();
      expect(state.generationStatus.phase).toBe('idle');
      expect(state.selectedIds.size).toBe(0);
    });
  });

  describe('selectors', () => {
    const session = makeSession([
      makeIdea({ id: 'i1', type: 'code_improvements', status: 'draft' }),
      makeIdea({ id: 'i2', type: 'ui_ux_improvements', status: 'dismissed' }),
      makeIdea({ id: 'i3', type: 'code_improvements', status: 'archived' }),
      makeIdea({ id: 'i4', type: 'ui_ux_improvements', status: 'selected' }),
    ]);

    it('getIdeasByType should filter by type', () => {
      const ideas = getIdeasByType(session, 'code_improvements');
      expect(ideas).toHaveLength(2);
    });

    it('getIdeasByType should return empty for null session', () => {
      expect(getIdeasByType(null, 'code_improvements')).toEqual([]);
    });

    it('getIdeasByStatus should filter by status', () => {
      const ideas = getIdeasByStatus(session, 'dismissed');
      expect(ideas).toHaveLength(1);
      expect(ideas[0].id).toBe('i2');
    });

    it('getActiveIdeas should exclude dismissed and archived', () => {
      const active = getActiveIdeas(session);
      expect(active).toHaveLength(2);
      expect(active.map((i) => i.id)).toEqual(['i1', 'i4']);
    });

    it('getArchivedIdeas should return only archived', () => {
      const archived = getArchivedIdeas(session);
      expect(archived).toHaveLength(1);
      expect(archived[0].id).toBe('i3');
    });

    it('getIdeationSummary should calculate stats from active ideas', () => {
      const summary = getIdeationSummary(session);
      expect(summary.totalIdeas).toBe(2); // only active (new, starred)
      expect(summary.byType['code_improvements']).toBe(1);
      expect(summary.byType['ui_ux_improvements']).toBe(1);
      expect(summary.byStatus['draft']).toBe(1);
      expect(summary.byStatus['selected']).toBe(1);
    });

    it('getIdeationSummary should handle null session', () => {
      const summary = getIdeationSummary(null);
      expect(summary.totalIdeas).toBe(0);
    });

    it('type guards should work correctly', () => {
      const codeIdea = makeIdea({ type: 'code_improvements' });
      const uiIdea = makeIdea({ type: 'ui_ux_improvements' });

      expect(isCodeImprovementIdea(codeIdea)).toBe(true);
      expect(isCodeImprovementIdea(uiIdea)).toBe(false);
      expect(isUIUXIdea(uiIdea)).toBe(true);
      expect(isUIUXIdea(codeIdea)).toBe(false);
    });
  });
});
