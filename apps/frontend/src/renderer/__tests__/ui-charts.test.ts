/**
 * Tests for the @auto-code/ui chart-geometry helpers (Sparkline / LineChart).
 * libs/ui has no CI test runner, so the pure math is exercised here.
 */

import { describe, expect, it } from 'vitest';
import { barPercent, pointsToArea, seriesToPoints } from '@auto-code/ui';

describe('seriesToPoints', () => {
  it('spreads points evenly across the width and inverts Y', () => {
    const parsed = seriesToPoints([0, 1, 2], 200, 100, 0)
      .split(' ')
      .map((p) => p.split(',').map(Number));
    expect(parsed.map(([x]) => x)).toEqual([0, 100, 200]);
    // min sits at the bottom, max at the top (SVG origin is top-left).
    expect(parsed[0][1]).toBe(100);
    expect(parsed[2][1]).toBe(0);
    expect(parsed[1][1]).toBe(50);
  });

  it('centers a flat series vertically', () => {
    for (const p of seriesToPoints([5, 5, 5], 100, 40, 0).split(' ')) {
      expect(Number(p.split(',')[1])).toBe(20);
    }
  });

  it('applies vertical padding so the line never touches the edges', () => {
    const ys = seriesToPoints([0, 10], 100, 100, 10)
      .split(' ')
      .map((p) => Number(p.split(',')[1]));
    expect(Math.max(...ys)).toBe(90);
    expect(Math.min(...ys)).toBe(10);
  });

  it('returns an empty string for an empty series', () => {
    expect(seriesToPoints([], 100, 40)).toBe('');
  });

  it('places a single point at the horizontal center', () => {
    expect(seriesToPoints([7], 100, 40, 0)).toBe('50,20');
  });
});

describe('pointsToArea', () => {
  it('closes the line down to the baseline corners', () => {
    expect(pointsToArea('0,10 100,0', 100, 40)).toBe('0,10 100,0 100,40 0,40');
  });

  it('returns an empty string when there are no points', () => {
    expect(pointsToArea('', 100, 40)).toBe('');
  });
});

describe('barPercent', () => {
  it('returns the value share of the scale, clamped to 0-100', () => {
    expect(barPercent(26, 26)).toBe(100);
    expect(barPercent(13, 26)).toBe(50);
    expect(barPercent(1, 26)).toBeCloseTo(3.85, 2);
    expect(barPercent(40, 26)).toBe(100);
  });

  it('yields 0 for non-positive value or scale', () => {
    expect(barPercent(0, 26)).toBe(0);
    expect(barPercent(-5, 26)).toBe(0);
    expect(barPercent(5, 0)).toBe(0);
    expect(barPercent(Number.NaN, 26)).toBe(0);
  });
});
