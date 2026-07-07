/**
 * Ordering for the model-usage "Cost by phase" breakdown.
 *
 * The backend keys `cost_by_phase` by execution phase (see
 * apps/backend/core/token_stats.py / save_token_stats callers). We render the
 * phases in pipeline order, with any unrecognized keys ('unknown', future
 * phases) appended alphabetically so nothing is silently dropped.
 */

export interface PhaseCost {
  phase: string;
  cost: number;
}

/** Canonical pipeline order of known phases. */
export const PHASE_ORDER: readonly string[] = [
  'planning',
  'coding',
  'test_generation',
  'validation',
  'performance_profiling',
];

/**
 * Turn a `cost_by_phase` map into an ordered list, dropping non-positive
 * entries. Known phases come first in pipeline order; unknown keys follow,
 * sorted alphabetically.
 */
export function orderPhaseCosts(
  costByPhase: Record<string, number> | undefined | null,
): PhaseCost[] {
  if (!costByPhase) return [];
  const entries = Object.entries(costByPhase).filter(
    ([, cost]) => Number.isFinite(cost) && cost > 0,
  );
  entries.sort(([a], [b]) => {
    const ia = PHASE_ORDER.indexOf(a);
    const ib = PHASE_ORDER.indexOf(b);
    if (ia !== -1 && ib !== -1) return ia - ib;
    if (ia !== -1) return -1;
    if (ib !== -1) return 1;
    return a.localeCompare(b);
  });
  return entries.map(([phase, cost]) => ({ phase, cost }));
}
