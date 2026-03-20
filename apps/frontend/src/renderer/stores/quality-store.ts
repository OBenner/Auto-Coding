import { create } from 'zustand';

// ============================================
// Quality Types (matching backend models)
// ============================================

export interface QualityScore {
  session_id: string;
  spec_id: string;
  agent_type: string; // planner, coder, qa_reviewer, qa_fixer
  timestamp: Date;

  // Quality components (0.0 to 1.0)
  test_pass_rate: number;
  acceptance_criteria_met: number;
  user_approval_rate: number;

  // Session context
  subtask_id?: string;
  phase?: string;
  iteration: number;

  // Metadata
  total_tests: number;
  passed_tests: number;
  total_criteria: number;
  met_criteria: number;
  user_approved: boolean;

  // Code coverage
  coverage_percent: number;
  lines_covered: number;
  lines_total: number;

  // Computed
  composite_score: number;
  is_high_quality: boolean;
  is_low_quality: boolean;
}

export interface QualityTrend {
  spec_id: string;
  period_start: Date;
  period_end: Date;

  // Scores over time
  scores: QualityScore[];

  // Baseline metrics
  baseline_score: number;
  baseline_calculated: boolean;

  // Trend analysis
  average_score: number;
  current_score: number;
  trend_direction: 'improving' | 'stable' | 'degrading';
  degradation_detected: boolean;

  // Alert configuration
  alert_threshold_percent: number;
  minimum_sessions_for_trend: number;

  // Computed
  total_sessions: number;
  quality_drop_percent: number;
  should_alert: boolean;
}

export interface QualitySummary {
  total_sessions: number;
  average_quality: number;
  current_quality: number;
  baseline_quality: number;
  trend_direction: 'improving' | 'stable' | 'degrading';
  quality_drop_percent: number;
  alert_active: boolean;
  high_quality_sessions: number;
  low_quality_sessions: number;
}

export interface QualityByAgentType {
  [agentType: string]: {
    average_quality: number;
    session_count: number;
    trend: 'improving' | 'stable' | 'degrading' | 'insufficient_data';
  };
}

export interface QualityAlert {
  id: string;
  spec_id: string;
  timestamp: Date;
  severity: 'warning' | 'critical';
  message: string;
  quality_drop_percent: number;
  current_score: number;
  baseline_score: number;
  dismissed: boolean;
}

// ============================================
// Quality Store State
// ============================================

interface QualityState {
  // Data
  scores: QualityScore[];
  trend: QualityTrend | null;
  summary: QualitySummary | null;
  byAgentType: QualityByAgentType | null;
  alerts: QualityAlert[];

  // UI State
  isLoadingScores: boolean;
  isLoadingTrend: boolean;
  isLoadingSummary: boolean;
  selectedSpecId: string | null;
  selectedAgentType: string | null;

  // Filters
  filterStartDate: Date | null;
  filterEndDate: Date | null;

  // Actions
  setScores: (scores: QualityScore[]) => void;
  addScore: (score: QualityScore) => void;
  setTrend: (trend: QualityTrend | null) => void;
  setSummary: (summary: QualitySummary | null) => void;
  setByAgentType: (byAgentType: QualityByAgentType | null) => void;
  setAlerts: (alerts: QualityAlert[]) => void;
  addAlert: (alert: QualityAlert) => void;
  dismissAlert: (alertId: string) => void;
  setLoadingScores: (loading: boolean) => void;
  setLoadingTrend: (loading: boolean) => void;
  setLoadingSummary: (loading: boolean) => void;
  setSelectedSpecId: (specId: string | null) => void;
  setSelectedAgentType: (agentType: string | null) => void;
  setFilterStartDate: (date: Date | null) => void;
  setFilterEndDate: (date: Date | null) => void;
  clearFilters: () => void;
  reset: () => void;
}

const initialState = {
  scores: [],
  trend: null,
  summary: null,
  byAgentType: null,
  alerts: [],
  isLoadingScores: false,
  isLoadingTrend: false,
  isLoadingSummary: false,
  selectedSpecId: null,
  selectedAgentType: null,
  filterStartDate: null,
  filterEndDate: null
};

export const useQualityStore = create<QualityState>((set) => ({
  ...initialState,

  // Data actions
  setScores: (scores) => set({ scores }),

  addScore: (score) =>
    set((state) => ({
      scores: [...state.scores, score]
    })),

  setTrend: (trend) => set({ trend }),

  setSummary: (summary) => set({ summary }),

  setByAgentType: (byAgentType) => set({ byAgentType }),

  setAlerts: (alerts) => set({ alerts }),

  addAlert: (alert) =>
    set((state) => ({
      alerts: [...state.alerts, alert]
    })),

  dismissAlert: (alertId) =>
    set((state) => ({
      alerts: state.alerts.map((alert) =>
        alert.id === alertId ? { ...alert, dismissed: true } : alert
      )
    })),

  // Loading actions
  setLoadingScores: (loading) => set({ isLoadingScores: loading }),

  setLoadingTrend: (loading) => set({ isLoadingTrend: loading }),

  setLoadingSummary: (loading) => set({ isLoadingSummary: loading }),

  // Filter actions
  setSelectedSpecId: (specId) => set({ selectedSpecId: specId }),

  setSelectedAgentType: (agentType) => set({ selectedAgentType: agentType }),

  setFilterStartDate: (date) => set({ filterStartDate: date }),

  setFilterEndDate: (date) => set({ filterEndDate: date }),

  clearFilters: () =>
    set({
      selectedSpecId: null,
      selectedAgentType: null,
      filterStartDate: null,
      filterEndDate: null
    }),

  reset: () => set(() => ({ ...initialState }))
}));

// ============================================
// Helper Functions
// ============================================

/**
 * Load quality scores for a spec
 * TODO: Implement IPC call when backend integration is ready
 */
export async function loadQualityScores(specId: string): Promise<void> {
  const store = useQualityStore.getState();
  store.setLoadingScores(true);

  try {
    // TODO: Call IPC to get quality scores from backend
    // const scores = await window.electronAPI.getQualityScores(specId);
    // const parsedScores = scores.map((score) => ({
    //   ...score,
    //   timestamp: new Date(score.timestamp)
    // }));
    // store.setScores(parsedScores);

    // For now, return empty array until IPC is implemented
    store.setScores([]);
  } catch (error) {
    console.error('Failed to load quality scores:', error);
    store.setScores([]);
  } finally {
    store.setLoadingScores(false);
  }
}

/**
 * Load quality trend analysis for a spec
 * TODO: Implement IPC call when backend integration is ready
 */
export async function loadQualityTrend(specId: string): Promise<void> {
  const store = useQualityStore.getState();
  store.setLoadingTrend(true);

  try {
    // TODO: Call IPC to get quality trend from backend
    // const trend = await window.electronAPI.getQualityTrend(specId);
    // For now, return null until IPC is implemented
    const trend: any = null;

    if (trend) {
      // Convert ISO strings to Date objects
      const parsedTrend: QualityTrend = {
        ...trend,
        period_start: new Date(trend.period_start),
        period_end: new Date(trend.period_end),
        scores: trend.scores.map((score: any) => ({
          ...score,
          timestamp: new Date(score.timestamp)
        }))
      };

      store.setTrend(parsedTrend);

      // Check if alert should be triggered
      const currentState = useQualityStore.getState();
      if (parsedTrend.should_alert && !currentState.alerts.some((a: QualityAlert) => a.spec_id === specId)) {
        const alert: QualityAlert = {
          id: `alert-${specId}-${Date.now()}`,
          spec_id: specId,
          timestamp: new Date(),
          severity: parsedTrend.quality_drop_percent >= 20 ? 'critical' : 'warning',
          message: `Quality dropped ${parsedTrend.quality_drop_percent.toFixed(1)}% below baseline`,
          quality_drop_percent: parsedTrend.quality_drop_percent,
          current_score: parsedTrend.current_score,
          baseline_score: parsedTrend.baseline_score,
          dismissed: false
        };
        store.addAlert(alert);
      }
    } else {
      store.setTrend(null);
    }
  } catch (error) {
    console.error('Failed to load quality trend:', error);
    store.setTrend(null);
  } finally {
    store.setLoadingTrend(false);
  }
}

/**
 * Load quality summary for a spec
 * TODO: Implement IPC call when backend integration is ready
 */
export async function loadQualitySummary(specId: string): Promise<void> {
  const store = useQualityStore.getState();
  store.setLoadingSummary(true);

  try {
    // TODO: Call IPC to get quality summary from backend
    // const summary = await window.electronAPI.getQualitySummary(specId);
    // For now, return null until IPC is implemented
    const summary: QualitySummary | null = null;

    store.setSummary(summary);
  } catch (error) {
    console.error('Failed to load quality summary:', error);
    store.setSummary(null);
  } finally {
    store.setLoadingSummary(false);
  }
}

/**
 * Load quality metrics by agent type for a spec
 * TODO: Implement IPC call when backend integration is ready
 */
export async function loadQualityByAgentType(specId: string): Promise<void> {
  try {
    // TODO: Call IPC to get quality by agent type from backend
    // const byAgentType = await window.electronAPI.getQualityByAgentType(specId);
    // For now, return null until IPC is implemented
    const byAgentType: QualityByAgentType | null = null;

    useQualityStore.getState().setByAgentType(byAgentType);
  } catch (error) {
    console.error('Failed to load quality by agent type:', error);
    useQualityStore.getState().setByAgentType(null);
  }
}

/**
 * Load all quality data for a spec
 */
export async function loadAllQualityData(specId: string): Promise<void> {
  // Load all quality data in parallel
  await Promise.all([
    loadQualityScores(specId),
    loadQualityTrend(specId),
    loadQualitySummary(specId),
    loadQualityByAgentType(specId)
  ]);
}

/**
 * Get active (non-dismissed) alerts
 */
export function getActiveAlerts(): QualityAlert[] {
  return useQualityStore.getState().alerts.filter((alert) => !alert.dismissed);
}

/**
 * Get filtered scores based on current filters
 */
export function getFilteredScores(): QualityScore[] {
  const state = useQualityStore.getState();
  let filtered = state.scores;

  // Filter by agent type
  if (state.selectedAgentType) {
    filtered = filtered.filter((score) => score.agent_type === state.selectedAgentType);
  }

  // Filter by date range
  if (state.filterStartDate) {
    filtered = filtered.filter((score) => score.timestamp >= state.filterStartDate!);
  }

  if (state.filterEndDate) {
    filtered = filtered.filter((score) => score.timestamp <= state.filterEndDate!);
  }

  return filtered;
}
