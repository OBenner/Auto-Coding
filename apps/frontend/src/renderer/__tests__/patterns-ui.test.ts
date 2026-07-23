/**
 * Tests for the Pattern → PatternLibrary mapping helpers.
 */

import { describe, expect, it } from 'vitest';
import {
  aggregatePatterns,
  filterPatterns,
  mapPatternToUi,
} from '../lib/patterns-ui';
import type { Pattern } from '../../preload/api/modules/pattern-api';

const LABELS = { high: 'high confidence', medium: 'medium confidence', low: 'low confidence' };

function makePattern(overrides: Partial<Pattern> = {}): Pattern {
  return {
    index: 1,
    id: '1',
    text: 'Prefer typed nav config from a string-literal union',
    category: 'code-organization',
    confidence: 'high',
    reasoning: 'A typo then fails at compile time.',
    ...overrides,
  };
}

describe('mapPatternToUi', () => {
  it('maps a backend pattern onto a sparse card with a spec-qualified id', () => {
    const ui = mapPatternToUi(makePattern(), '001-auth', LABELS);
    expect(ui).toEqual({
      id: '001-auth#1',
      kind: 'pattern',
      title: 'Prefer typed nav config from a string-literal union',
      lang: 'code-organization',
      description: 'A typo then fails at compile time.',
      footer: [{ text: 'high confidence' }],
    });
  });

  it('omits the confidence footer and empty description when unknown', () => {
    const ui = mapPatternToUi(
      makePattern({ confidence: undefined, reasoning: '', category: undefined }),
      '002',
      LABELS,
    );
    expect(ui.footer).toBeUndefined();
    expect(ui.description).toBeUndefined();
    expect(ui.lang).toBeUndefined();
  });

  it('drops the footer when no confidence labels are supplied', () => {
    expect(mapPatternToUi(makePattern(), '003').footer).toBeUndefined();
  });
});

describe('aggregatePatterns', () => {
  it('flattens per-spec patterns and dedupes identical texts, first wins', () => {
    const shared = makePattern({ text: 'Branches stay local until pushed' });
    const result = aggregatePatterns(
      [
        { specId: '001', patterns: [makePattern({ index: 1, text: 'A' }), shared] },
        { specId: '002', patterns: [{ ...shared, index: 5 }, makePattern({ index: 2, text: 'B' })] },
      ],
      LABELS,
    );
    expect(result.map((p) => p.title)).toEqual([
      'A',
      'Branches stay local until pushed',
      'B',
    ]);
    // The deduped entry keeps the first spec's id.
    expect(result[1].id).toBe('001#1');
  });

  it('returns an empty list for no specs', () => {
    expect(aggregatePatterns([])).toEqual([]);
    expect(aggregatePatterns([{ specId: '001', patterns: [] }])).toEqual([]);
  });

  it('is case- and whitespace-insensitive when deduping', () => {
    const result = aggregatePatterns([
      { specId: '001', patterns: [makePattern({ text: 'Same Rule' })] },
      { specId: '002', patterns: [makePattern({ text: '  same rule ' })] },
    ]);
    expect(result).toHaveLength(1);
  });
});

describe('filterPatterns', () => {
  const patterns = [
    mapPatternToUi(makePattern({ index: 1, text: 'Typed nav config', category: 'code-organization' }), 's1', LABELS),
    mapPatternToUi(makePattern({ index: 2, text: 'Retry with backoff', category: 'error-handling', reasoning: 'exponential jitter' }), 's1', LABELS),
  ];

  it('matches title, lang, and description, case-insensitively', () => {
    expect(filterPatterns(patterns, 'NAV').map((p) => p.title)).toEqual(['Typed nav config']);
    expect(filterPatterns(patterns, 'error-handling').map((p) => p.title)).toEqual(['Retry with backoff']);
    expect(filterPatterns(patterns, 'jitter').map((p) => p.title)).toEqual(['Retry with backoff']);
    expect(filterPatterns(patterns, 'zzz')).toEqual([]);
  });

  it('returns everything for a blank query', () => {
    expect(filterPatterns(patterns, '  ')).toHaveLength(2);
  });
});
