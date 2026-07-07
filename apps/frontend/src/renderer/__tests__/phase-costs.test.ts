/**
 * Tests for orderPhaseCosts (P5.T3): ordering the model-usage
 * "Cost by phase" breakdown for display.
 */

import { describe, expect, it } from 'vitest';
import { orderPhaseCosts } from '../lib/phase-costs';

describe('orderPhaseCosts', () => {
  it('returns [] for empty, null, or undefined input', () => {
    expect(orderPhaseCosts({})).toEqual([]);
    expect(orderPhaseCosts(null)).toEqual([]);
    expect(orderPhaseCosts(undefined)).toEqual([]);
  });

  it('orders known phases by pipeline order regardless of input order', () => {
    const result = orderPhaseCosts({
      validation: 0.5,
      planning: 1,
      coding: 2,
    });
    expect(result.map((p) => p.phase)).toEqual([
      'planning',
      'coding',
      'validation',
    ]);
  });

  it('drops zero and negative costs', () => {
    const result = orderPhaseCosts({
      planning: 0,
      coding: 1.25,
      validation: -3,
    });
    expect(result).toEqual([{ phase: 'coding', cost: 1.25 }]);
  });

  it('appends unknown phases after known ones, sorted alphabetically', () => {
    const result = orderPhaseCosts({
      zeta: 1,
      coding: 2,
      unknown: 3,
      planning: 4,
    });
    expect(result.map((p) => p.phase)).toEqual([
      'planning',
      'coding',
      'unknown',
      'zeta',
    ]);
  });

  it('ignores non-finite costs', () => {
    const result = orderPhaseCosts({
      planning: Number.NaN,
      coding: Number.POSITIVE_INFINITY,
      validation: 0.99,
    });
    expect(result).toEqual([{ phase: 'validation', cost: 0.99 }]);
  });
});
