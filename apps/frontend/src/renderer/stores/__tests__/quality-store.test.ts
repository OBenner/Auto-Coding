/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import {
  useQualityStore,
  getActiveAlerts,
  getFilteredScores,
  type QualityScore,
  type QualityAlert,
  type QualitySummary,
  type QualityByAgentType,
} from '../quality-store';

function createMockScore(overrides: Partial<QualityScore> = {}): QualityScore {
  return {
    session_id: 'session-1',
    spec_id: 'spec-1',
    agent_type: 'coder',
    timestamp: new Date('2025-01-20T12:00:00Z'),
    test_pass_rate: 0.9,
    acceptance_criteria_met: 0.85,
    user_approval_rate: 1.0,
    iteration: 1,
    total_tests: 10,
    passed_tests: 9,
    total_criteria: 5,
    met_criteria: 4,
    user_approved: true,
    composite_score: 0.9,
    is_high_quality: true,
    is_low_quality: false,
    ...overrides,
  };
}

function createMockAlert(overrides: Partial<QualityAlert> = {}): QualityAlert {
  return {
    id: `alert-${Math.random().toString(36).substr(2, 5)}`,
    spec_id: 'spec-1',
    timestamp: new Date(),
    severity: 'warning',
    message: 'Quality dropped 15%',
    quality_drop_percent: 15,
    current_score: 0.7,
    baseline_score: 0.85,
    dismissed: false,
    ...overrides,
  };
}

describe('quality-store', () => {
  beforeEach(() => {
    useQualityStore.getState().reset();
  });

  describe('initial state', () => {
    it('should start with empty state', () => {
      const state = useQualityStore.getState();
      expect(state.scores).toEqual([]);
      expect(state.trend).toBeNull();
      expect(state.summary).toBeNull();
      expect(state.byAgentType).toBeNull();
      expect(state.alerts).toEqual([]);
      expect(state.isLoadingScores).toBe(false);
      expect(state.isLoadingTrend).toBe(false);
      expect(state.isLoadingSummary).toBe(false);
    });
  });

  describe('scores management', () => {
    it('should set scores', () => {
      const scores = [createMockScore(), createMockScore({ session_id: 'session-2' })];
      useQualityStore.getState().setScores(scores);
      expect(useQualityStore.getState().scores).toHaveLength(2);
    });

    it('should add a score', () => {
      useQualityStore.getState().addScore(createMockScore());
      useQualityStore.getState().addScore(createMockScore({ session_id: 'session-2' }));
      expect(useQualityStore.getState().scores).toHaveLength(2);
    });
  });

  describe('trend and summary', () => {
    it('should set trend', () => {
      useQualityStore.getState().setTrend({
        spec_id: 'spec-1',
        trend_direction: 'improving',
        average_score: 0.85,
      } as any);
      expect(useQualityStore.getState().trend?.trend_direction).toBe('improving');
    });

    it('should set summary', () => {
      const summary: QualitySummary = {
        total_sessions: 10,
        average_quality: 0.85,
        current_quality: 0.9,
        baseline_quality: 0.8,
        trend_direction: 'improving',
        quality_drop_percent: 0,
        alert_active: false,
        high_quality_sessions: 8,
        low_quality_sessions: 1,
      };
      useQualityStore.getState().setSummary(summary);
      expect(useQualityStore.getState().summary?.total_sessions).toBe(10);
    });

    it('should set by agent type', () => {
      const byAgentType: QualityByAgentType = {
        coder: { average_quality: 0.9, session_count: 5, trend: 'improving' },
        planner: { average_quality: 0.85, session_count: 3, trend: 'stable' },
      };
      useQualityStore.getState().setByAgentType(byAgentType);
      expect(useQualityStore.getState().byAgentType?.coder.average_quality).toBe(0.9);
    });
  });

  describe('alerts', () => {
    it('should set alerts', () => {
      const alerts = [createMockAlert({ id: 'a1' }), createMockAlert({ id: 'a2' })];
      useQualityStore.getState().setAlerts(alerts);
      expect(useQualityStore.getState().alerts).toHaveLength(2);
    });

    it('should add an alert', () => {
      useQualityStore.getState().addAlert(createMockAlert({ id: 'a1' }));
      useQualityStore.getState().addAlert(createMockAlert({ id: 'a2' }));
      expect(useQualityStore.getState().alerts).toHaveLength(2);
    });

    it('should dismiss an alert', () => {
      useQualityStore.getState().setAlerts([
        createMockAlert({ id: 'a1', dismissed: false }),
        createMockAlert({ id: 'a2', dismissed: false }),
      ]);
      useQualityStore.getState().dismissAlert('a1');
      const alerts = useQualityStore.getState().alerts;
      expect(alerts.find(a => a.id === 'a1')?.dismissed).toBe(true);
      expect(alerts.find(a => a.id === 'a2')?.dismissed).toBe(false);
    });
  });

  describe('loading states', () => {
    it('should set loading scores', () => {
      useQualityStore.getState().setLoadingScores(true);
      expect(useQualityStore.getState().isLoadingScores).toBe(true);
    });

    it('should set loading trend', () => {
      useQualityStore.getState().setLoadingTrend(true);
      expect(useQualityStore.getState().isLoadingTrend).toBe(true);
    });

    it('should set loading summary', () => {
      useQualityStore.getState().setLoadingSummary(true);
      expect(useQualityStore.getState().isLoadingSummary).toBe(true);
    });
  });

  describe('filters', () => {
    it('should set selected spec id', () => {
      useQualityStore.getState().setSelectedSpecId('spec-42');
      expect(useQualityStore.getState().selectedSpecId).toBe('spec-42');
    });

    it('should set selected agent type', () => {
      useQualityStore.getState().setSelectedAgentType('coder');
      expect(useQualityStore.getState().selectedAgentType).toBe('coder');
    });

    it('should set date range filters', () => {
      const start = new Date('2025-01-01');
      const end = new Date('2025-01-31');
      useQualityStore.getState().setFilterStartDate(start);
      useQualityStore.getState().setFilterEndDate(end);
      expect(useQualityStore.getState().filterStartDate).toEqual(start);
      expect(useQualityStore.getState().filterEndDate).toEqual(end);
    });

    it('should clear all filters', () => {
      useQualityStore.getState().setSelectedSpecId('spec-1');
      useQualityStore.getState().setSelectedAgentType('coder');
      useQualityStore.getState().setFilterStartDate(new Date());
      useQualityStore.getState().clearFilters();
      const state = useQualityStore.getState();
      expect(state.selectedSpecId).toBeNull();
      expect(state.selectedAgentType).toBeNull();
      expect(state.filterStartDate).toBeNull();
      expect(state.filterEndDate).toBeNull();
    });
  });

  describe('reset', () => {
    it('should reset all state', () => {
      useQualityStore.getState().setScores([createMockScore()]);
      useQualityStore.getState().addAlert(createMockAlert());
      useQualityStore.getState().setSelectedSpecId('spec-1');
      useQualityStore.getState().reset();
      const state = useQualityStore.getState();
      expect(state.scores).toEqual([]);
      expect(state.alerts).toEqual([]);
      expect(state.selectedSpecId).toBeNull();
    });
  });
});

describe('quality-store helpers', () => {
  beforeEach(() => {
    useQualityStore.getState().reset();
  });

  describe('getActiveAlerts', () => {
    it('should return only non-dismissed alerts', () => {
      useQualityStore.getState().setAlerts([
        createMockAlert({ id: 'a1', dismissed: false }),
        createMockAlert({ id: 'a2', dismissed: true }),
        createMockAlert({ id: 'a3', dismissed: false }),
      ]);
      const active = getActiveAlerts();
      expect(active).toHaveLength(2);
      expect(active.map(a => a.id)).toEqual(['a1', 'a3']);
    });

    it('should return empty array when all dismissed', () => {
      useQualityStore.getState().setAlerts([
        createMockAlert({ dismissed: true }),
      ]);
      expect(getActiveAlerts()).toEqual([]);
    });
  });

  describe('getFilteredScores', () => {
    it('should return all scores when no filters', () => {
      useQualityStore.getState().setScores([
        createMockScore({ agent_type: 'coder' }),
        createMockScore({ agent_type: 'planner' }),
      ]);
      expect(getFilteredScores()).toHaveLength(2);
    });

    it('should filter by agent type', () => {
      useQualityStore.getState().setScores([
        createMockScore({ agent_type: 'coder' }),
        createMockScore({ agent_type: 'planner' }),
        createMockScore({ agent_type: 'coder' }),
      ]);
      useQualityStore.getState().setSelectedAgentType('coder');
      expect(getFilteredScores()).toHaveLength(2);
    });

    it('should filter by start date', () => {
      useQualityStore.getState().setScores([
        createMockScore({ timestamp: new Date('2025-01-10') }),
        createMockScore({ timestamp: new Date('2025-01-20') }),
        createMockScore({ timestamp: new Date('2025-01-25') }),
      ]);
      useQualityStore.getState().setFilterStartDate(new Date('2025-01-15'));
      expect(getFilteredScores()).toHaveLength(2);
    });

    it('should filter by end date', () => {
      useQualityStore.getState().setScores([
        createMockScore({ timestamp: new Date('2025-01-10') }),
        createMockScore({ timestamp: new Date('2025-01-20') }),
        createMockScore({ timestamp: new Date('2025-01-25') }),
      ]);
      useQualityStore.getState().setFilterEndDate(new Date('2025-01-20'));
      expect(getFilteredScores()).toHaveLength(2);
    });

    it('should combine multiple filters', () => {
      useQualityStore.getState().setScores([
        createMockScore({ agent_type: 'coder', timestamp: new Date('2025-01-10') }),
        createMockScore({ agent_type: 'planner', timestamp: new Date('2025-01-20') }),
        createMockScore({ agent_type: 'coder', timestamp: new Date('2025-01-25') }),
      ]);
      useQualityStore.getState().setSelectedAgentType('coder');
      useQualityStore.getState().setFilterStartDate(new Date('2025-01-15'));
      expect(getFilteredScores()).toHaveLength(1);
    });
  });
});
