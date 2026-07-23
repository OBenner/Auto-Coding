/**
 * Pure mapping helpers between the preload Pattern shape and the shared
 * PatternLibrary screen. The backend stores patterns per spec as plain
 * text with a coarse category + confidence bucket, so the mapped card is
 * intentionally sparse (no snippet/tags) — the rich card fields exist for
 * the mockup/Storybook and richer sources. Localized strings (the
 * confidence footer label) stay in the pilot.
 */

import type {
  UiPattern,
  UiPatternFooterStat,
} from '@auto-code/ui';
import type { Pattern } from '../../preload/api/modules/pattern-api';

export interface PatternConfidenceLabels {
  high: string;
  medium: string;
  low: string;
}

/**
 * Map one backend pattern onto the shared card shape. `specId` keeps ids
 * unique (the backend index resets per spec). `footer` carries the
 * confidence bucket when known; the caller supplies its localized wording.
 */
export function mapPatternToUi(
  pattern: Pattern,
  specId: string,
  confidenceLabels?: PatternConfidenceLabels,
): UiPattern {
  const footer: UiPatternFooterStat[] = [];
  if (pattern.confidence != null && confidenceLabels != null) {
    footer.push({ text: confidenceLabels[pattern.confidence] });
  }
  return {
    id: `${specId}#${pattern.index}`,
    // The backend has no gotcha/decision/rule taxonomy — every learned
    // item is a code pattern; category becomes the lang/domain chip.
    kind: 'pattern',
    title: pattern.text,
    lang: pattern.category ?? undefined,
    description: pattern.reasoning || undefined,
    footer: footer.length > 0 ? footer : undefined,
  };
}

/** One spec's pattern list, as returned per-spec by the pattern IPC. */
export interface SpecPatterns {
  specId: string;
  patterns: readonly Pattern[];
}

/**
 * Flatten patterns aggregated across a project's specs into one card list,
 * dropping exact-duplicate texts (the same rule is often re-learned across
 * specs). Order follows the input; the first occurrence wins.
 */
export function aggregatePatterns(
  perSpec: readonly SpecPatterns[],
  confidenceLabels?: PatternConfidenceLabels,
): UiPattern[] {
  const seen = new Set<string>();
  const out: UiPattern[] = [];
  for (const { specId, patterns } of perSpec) {
    for (const pattern of patterns) {
      const dedupeKey = pattern.text.trim().toLowerCase();
      if (seen.has(dedupeKey)) continue;
      seen.add(dedupeKey);
      out.push(mapPatternToUi(pattern, specId, confidenceLabels));
    }
  }
  return out;
}

/** Case-insensitive match over title, lang, description, and tags. */
export function filterPatterns(
  patterns: readonly UiPattern[],
  query: string,
): UiPattern[] {
  const needle = query.trim().toLowerCase();
  if (needle === '') return [...patterns];
  const matches = (field?: string) =>
    field?.toLowerCase().includes(needle) ?? false;
  return patterns.filter(
    (pattern) =>
      matches(pattern.title) ||
      matches(pattern.lang) ||
      matches(pattern.description) ||
      matches(pattern.code) ||
      (pattern.tags ?? []).some((tag) => matches(tag)),
  );
}
