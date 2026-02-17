/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  useRoadmapStore,
  getFeaturesByPhase,
  getFeaturesByPriority,
  getFeatureStats,
} from '../roadmap-store';
import type { Roadmap, RoadmapFeature } from '../../../shared/types';

function makeFeature(overrides: Partial<RoadmapFeature> = {}): RoadmapFeature {
  return {
    id: 'feat-1',
    title: 'Test Feature',
    description: 'A test feature',
    priority: 'high',
    complexity: 'medium',
    status: 'under_review',
    phaseId: 'phase-1',
    source: { provider: 'internal' },
    ...overrides,
  } as RoadmapFeature;
}

function makeRoadmap(features: RoadmapFeature[] = []): Roadmap {
  return {
    id: 'roadmap-1',
    projectId: 'proj-1',
    phases: [
      { id: 'phase-1', name: 'Phase 1', description: 'First phase' },
      { id: 'phase-2', name: 'Phase 2', description: 'Second phase' },
    ],
    features,
    generatedAt: new Date(),
    updatedAt: new Date(),
  } as Roadmap;
}

describe('roadmap-store', () => {
  beforeEach(() => {
    useRoadmapStore.getState().clearRoadmap();
  });

  describe('initial state', () => {
    it('should have correct defaults', () => {
      const state = useRoadmapStore.getState();
      expect(state.roadmap).toBeNull();
      expect(state.competitorAnalysis).toBeNull();
      expect(state.generationStatus.phase).toBe('idle');
      expect(state.currentProjectId).toBeNull();
    });
  });

  describe('setRoadmap', () => {
    it('should set roadmap', () => {
      const roadmap = makeRoadmap([makeFeature()]);
      useRoadmapStore.getState().setRoadmap(roadmap);
      expect(useRoadmapStore.getState().roadmap).toEqual(roadmap);
    });
  });

  describe('updateFeatureStatus', () => {
    it('should update feature status by id', () => {
      const roadmap = makeRoadmap([
        makeFeature({ id: 'f1', status: 'under_review' }),
        makeFeature({ id: 'f2', status: 'under_review' }),
      ]);
      useRoadmapStore.setState({ roadmap });

      useRoadmapStore.getState().updateFeatureStatus('f1', 'in_progress');

      const features = useRoadmapStore.getState().roadmap!.features;
      expect(features[0].status).toBe('in_progress');
      expect(features[1].status).toBe('under_review');
    });

    it('should not modify state when no roadmap exists', () => {
      useRoadmapStore.getState().updateFeatureStatus('f1', 'done');
      expect(useRoadmapStore.getState().roadmap).toBeNull();
    });
  });

  describe('markFeatureDoneBySpecId', () => {
    it('should mark feature as done by linked spec id', () => {
      const roadmap = makeRoadmap([
        makeFeature({ id: 'f1', linkedSpecId: 'spec-1', status: 'in_progress' }),
        makeFeature({ id: 'f2', linkedSpecId: 'spec-2', status: 'in_progress' }),
      ]);
      useRoadmapStore.setState({ roadmap });

      useRoadmapStore.getState().markFeatureDoneBySpecId('spec-1');

      const features = useRoadmapStore.getState().roadmap!.features;
      expect(features[0].status).toBe('done');
      expect(features[1].status).toBe('in_progress');
    });
  });

  describe('updateFeatureLinkedSpec', () => {
    it('should link spec and set status to in_progress', () => {
      const roadmap = makeRoadmap([
        makeFeature({ id: 'f1', status: 'under_review' }),
      ]);
      useRoadmapStore.setState({ roadmap });

      useRoadmapStore.getState().updateFeatureLinkedSpec('f1', 'spec-1');

      const feature = useRoadmapStore.getState().roadmap!.features[0];
      expect(feature.linkedSpecId).toBe('spec-1');
      expect(feature.status).toBe('in_progress');
    });
  });

  describe('deleteFeature', () => {
    it('should remove feature by id', () => {
      const roadmap = makeRoadmap([
        makeFeature({ id: 'f1' }),
        makeFeature({ id: 'f2' }),
      ]);
      useRoadmapStore.setState({ roadmap });

      useRoadmapStore.getState().deleteFeature('f1');

      const features = useRoadmapStore.getState().roadmap!.features;
      expect(features).toHaveLength(1);
      expect(features[0].id).toBe('f2');
    });
  });

  describe('reorderFeatures', () => {
    it('should reorder features within a phase', () => {
      const roadmap = makeRoadmap([
        makeFeature({ id: 'f1', phaseId: 'phase-1' }),
        makeFeature({ id: 'f2', phaseId: 'phase-1' }),
        makeFeature({ id: 'f3', phaseId: 'phase-2' }),
      ]);
      useRoadmapStore.setState({ roadmap });

      useRoadmapStore.getState().reorderFeatures('phase-1', ['f2', 'f1']);

      const features = useRoadmapStore.getState().roadmap!.features;
      // phase-2 features first, then reordered phase-1 features
      expect(features[0].id).toBe('f3');
      expect(features[1].id).toBe('f2');
      expect(features[2].id).toBe('f1');
    });
  });

  describe('updateFeaturePhase', () => {
    it('should move feature to a different phase', () => {
      const roadmap = makeRoadmap([
        makeFeature({ id: 'f1', phaseId: 'phase-1' }),
      ]);
      useRoadmapStore.setState({ roadmap });

      useRoadmapStore.getState().updateFeaturePhase('f1', 'phase-2');

      expect(useRoadmapStore.getState().roadmap!.features[0].phaseId).toBe('phase-2');
    });
  });

  describe('addFeature', () => {
    it('should add feature and return new id', () => {
      const roadmap = makeRoadmap([]);
      useRoadmapStore.setState({ roadmap });

      const newId = useRoadmapStore.getState().addFeature({
        title: 'New Feature',
        description: 'Description',
        priority: 'high',
        complexity: 'low',
        status: 'under_review',
        phaseId: 'phase-1',
        source: { provider: 'internal' },
      } as any);

      expect(newId).toMatch(/^feature-/);
      expect(useRoadmapStore.getState().roadmap!.features).toHaveLength(1);
      expect(useRoadmapStore.getState().roadmap!.features[0].title).toBe('New Feature');
    });
  });

  describe('generationStatus', () => {
    it('should set generation status with timestamps', () => {
      useRoadmapStore.getState().setGenerationStatus({
        phase: 'analyzing',
        progress: 0,
        message: 'Starting...',
      });

      const status = useRoadmapStore.getState().generationStatus;
      expect(status.phase).toBe('analyzing');
      expect(status.startedAt).toBeDefined();
      expect(status.lastActivityAt).toBeDefined();
    });

    it('should clear timestamps when returning to idle', () => {
      useRoadmapStore.getState().setGenerationStatus({
        phase: 'analyzing',
        progress: 0,
        message: 'Starting...',
      });

      useRoadmapStore.getState().setGenerationStatus({
        phase: 'idle',
        progress: 0,
        message: '',
      });

      const status = useRoadmapStore.getState().generationStatus;
      expect(status.startedAt).toBeUndefined();
      expect(status.lastActivityAt).toBeUndefined();
    });
  });

  describe('clearRoadmap', () => {
    it('should reset all state', () => {
      useRoadmapStore.setState({
        roadmap: makeRoadmap([makeFeature()]),
        competitorAnalysis: { competitors: [] } as any,
        generationStatus: { phase: 'analyzing', progress: 50, message: 'test' },
        currentProjectId: 'proj-1',
      });

      useRoadmapStore.getState().clearRoadmap();

      const state = useRoadmapStore.getState();
      expect(state.roadmap).toBeNull();
      expect(state.competitorAnalysis).toBeNull();
      expect(state.generationStatus.phase).toBe('idle');
      expect(state.currentProjectId).toBeNull();
    });
  });

  describe('selectors', () => {
    it('getFeaturesByPhase should filter features by phase', () => {
      const roadmap = makeRoadmap([
        makeFeature({ id: 'f1', phaseId: 'phase-1' }),
        makeFeature({ id: 'f2', phaseId: 'phase-2' }),
        makeFeature({ id: 'f3', phaseId: 'phase-1' }),
      ]);

      const phase1Features = getFeaturesByPhase(roadmap, 'phase-1');
      expect(phase1Features).toHaveLength(2);
      expect(phase1Features.map((f) => f.id)).toEqual(['f1', 'f3']);
    });

    it('getFeaturesByPhase should return empty for null roadmap', () => {
      expect(getFeaturesByPhase(null, 'phase-1')).toEqual([]);
    });

    it('getFeaturesByPriority should filter by priority', () => {
      const roadmap = makeRoadmap([
        makeFeature({ id: 'f1', priority: 'high' }),
        makeFeature({ id: 'f2', priority: 'low' }),
        makeFeature({ id: 'f3', priority: 'high' }),
      ]);

      const highPriority = getFeaturesByPriority(roadmap, 'high');
      expect(highPriority).toHaveLength(2);
    });

    it('getFeatureStats should aggregate feature statistics', () => {
      const roadmap = makeRoadmap([
        makeFeature({ priority: 'high', status: 'under_review', complexity: 'low' }),
        makeFeature({ priority: 'high', status: 'in_progress', complexity: 'medium' }),
        makeFeature({ priority: 'low', status: 'done', complexity: 'low' }),
      ]);

      const stats = getFeatureStats(roadmap);
      expect(stats.total).toBe(3);
      expect(stats.byPriority['high']).toBe(2);
      expect(stats.byPriority['low']).toBe(1);
      expect(stats.byStatus['under_review']).toBe(1);
      expect(stats.byStatus['in_progress']).toBe(1);
      expect(stats.byStatus['done']).toBe(1);
      expect(stats.byComplexity['low']).toBe(2);
      expect(stats.byComplexity['medium']).toBe(1);
    });

    it('getFeatureStats should return empty stats for null roadmap', () => {
      const stats = getFeatureStats(null);
      expect(stats.total).toBe(0);
      expect(stats.byPriority).toEqual({});
      expect(stats.byStatus).toEqual({});
      expect(stats.byComplexity).toEqual({});
    });
  });
});
