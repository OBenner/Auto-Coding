import { useMemo, useState, useCallback } from 'react';
import type { TaskLogs, TaskLogPhase, TaskLogEntry, TaskPhaseLog } from '../../shared/types';

/**
 * Type of flattened item for virtualized rendering
 */
export type FlattenedLogItemType = 'phase-header' | 'log-entry';

/**
 * A flattened representation of a log item for virtualized rendering.
 * Can represent either a phase header or a log entry.
 */
export interface FlattenedLogItem {
  /** Unique key for React rendering */
  key: string;
  /** Type of item (phase header or log entry) */
  type: FlattenedLogItemType;
  /** Phase this item belongs to */
  phase: TaskLogPhase;
  /** Phase data (only for phase headers) */
  phaseLog?: TaskPhaseLog;
  /** Whether phase is expanded (only for phase headers) */
  isPhaseExpanded?: boolean;
  /** Log entry data (only for log entries) */
  entry?: TaskLogEntry;
  /** Index within phase's entries array (only for log entries) */
  entryIndex?: number;
  /** Whether this log entry's detail is expanded */
  isDetailExpanded?: boolean;
}

/**
 * Configuration for height estimation calculations
 */
const HEIGHT_CONFIG = {
  PHASE_HEADER: 60,           // Phase collapsible header
  BASE_ENTRY_HEIGHT: 32,      // Base height for single-line log entry
  TOOL_ENTRY_HEIGHT: 40,      // Base height for tool entries
  ERROR_ENTRY_HEIGHT: 48,     // Base height for error entries
  LINE_HEIGHT_NORMAL: 18,     // Pixels per line for normal content
  LINE_HEIGHT_COMPACT: 16,    // Pixels per line for compact/error content
  CHARS_PER_LINE_NORMAL: 85,  // Estimated chars per line for content
  CHARS_PER_LINE_TOOL: 40,    // Estimated chars per line for tool names
  CHARS_PER_LINE_DETAIL: 90,  // Estimated chars per line for detail sections
  DETAIL_MIN_HEIGHT: 50,      // Minimum detail section height
  DETAIL_MAX_HEIGHT: 400,     // Maximum detail section height
} as const;

/**
 * Estimated heights for different item types (in pixels)
 * Legacy export for backwards compatibility
 */
export const ESTIMATED_HEIGHTS = {
  PHASE_HEADER: HEIGHT_CONFIG.PHASE_HEADER,
  LOG_ENTRY_SIMPLE: HEIGHT_CONFIG.BASE_ENTRY_HEIGHT,
  LOG_ENTRY_TOOL: HEIGHT_CONFIG.TOOL_ENTRY_HEIGHT,
  LOG_ENTRY_ERROR: HEIGHT_CONFIG.ERROR_ENTRY_HEIGHT,
  LOG_ENTRY_DETAIL: HEIGHT_CONFIG.DETAIL_MIN_HEIGHT,
} as const;

/**
 * Flattens phase-based logs into a flat array suitable for virtualized rendering.
 * Only includes items that should be visible (i.e., entries whose phase is expanded).
 *
 * @param phaseLogs - The phase-based task logs
 * @param expandedPhases - Set of phases that are currently expanded
 * @param expandedDetails - Map of expanded detail entries (key: "phase:entryIndex")
 * @returns An array of FlattenedLogItem objects in display order
 */
export function flattenLogs(
  phaseLogs: TaskLogs | null,
  expandedPhases: Set<TaskLogPhase>,
  expandedDetails: Map<string, boolean>
): FlattenedLogItem[] {
  if (!phaseLogs) {
    return [];
  }

  const result: FlattenedLogItem[] = [];
  const phases: TaskLogPhase[] = ['planning', 'coding', 'validation'];

  for (const phase of phases) {
    const phaseLog = phaseLogs.phases[phase];
    const isPhaseExpanded = expandedPhases.has(phase);

    // Add phase header
    result.push({
      key: `phase-${phase}`,
      type: 'phase-header',
      phase,
      phaseLog,
      isPhaseExpanded,
    });

    // If phase is expanded, add its entries
    if (isPhaseExpanded && phaseLog?.entries) {
      phaseLog.entries.forEach((entry, index) => {
        const detailKey = `${phase}:${index}`;
        const isDetailExpanded = expandedDetails.get(detailKey) ?? false;

        result.push({
          key: `${phase}-entry-${index}`,
          type: 'log-entry',
          phase,
          entry,
          entryIndex: index,
          isDetailExpanded,
        });
      });
    }
  }

  return result;
}

/**
 * Calculates the number of lines needed to display text content,
 * accounting for both explicit newlines and text wrapping.
 *
 * @param text - The text content to measure
 * @param charsPerLine - Estimated characters per line before wrapping
 * @returns Total number of lines needed
 */
function calculateTextLines(text: string, charsPerLine: number): number {
  if (!text) {
    return 0;
  }

  // Split by explicit newlines first
  const explicitLines = text.split('\n');
  let totalLines = 0;

  for (const line of explicitLines) {
    // Estimate how many wrapped lines this explicit line will create
    const wrappedLines = Math.ceil(Math.max(0, line.length) / charsPerLine);
    totalLines += Math.max(1, wrappedLines);
  }

  return totalLines;
}

/**
 * Estimates the height of a flattened log item based on its type and content.
 * Used by the virtualizer for smooth scrolling with dynamic heights.
 *
 * This function considers:
 * - Entry type (different base heights)
 * - Content text length and wrapping
 * - Tool name length for tool entries
 * - Detail section size when expanded
 *
 * @param item - The flattened log item
 * @returns Estimated height in pixels
 */
export function estimateLogItemHeight(item: FlattenedLogItem): number {
  if (item.type === 'phase-header') {
    return HEIGHT_CONFIG.PHASE_HEADER;
  }

  const entry = item.entry;
  if (!entry) {
    return HEIGHT_CONFIG.BASE_ENTRY_HEIGHT;
  }

  // Determine base height and line height based on entry type
  let baseHeight: number;
  let lineHeight: number;

  switch (entry.type) {
    case 'tool_start':
    case 'tool_end':
      baseHeight = HEIGHT_CONFIG.TOOL_ENTRY_HEIGHT;
      lineHeight = HEIGHT_CONFIG.LINE_HEIGHT_NORMAL;

      // Add height for tool name if it exists and might wrap
      if (entry.tool_name) {
        const toolLines = calculateTextLines(
          entry.tool_name,
          HEIGHT_CONFIG.CHARS_PER_LINE_TOOL
        );
        if (toolLines > 1) {
          baseHeight += (toolLines - 1) * lineHeight;
        }
      }
      break;

    case 'error':
      baseHeight = HEIGHT_CONFIG.ERROR_ENTRY_HEIGHT;
      lineHeight = HEIGHT_CONFIG.LINE_HEIGHT_COMPACT;
      break;

    case 'success':
    case 'info':
    default:
      baseHeight = HEIGHT_CONFIG.BASE_ENTRY_HEIGHT;
      lineHeight = HEIGHT_CONFIG.LINE_HEIGHT_NORMAL;
      break;
  }

  // Add height for content text if it wraps to multiple lines
  if (entry.content) {
    const contentLines = calculateTextLines(
      entry.content,
      HEIGHT_CONFIG.CHARS_PER_LINE_NORMAL
    );
    if (contentLines > 1) {
      baseHeight += (contentLines - 1) * lineHeight;
    }
  }

  // Add detail section height if expanded
  if (item.isDetailExpanded && entry.detail) {
    const detailLines = calculateTextLines(
      entry.detail,
      HEIGHT_CONFIG.CHARS_PER_LINE_DETAIL
    );
    const detailHeight = Math.min(
      Math.max(
        detailLines * HEIGHT_CONFIG.LINE_HEIGHT_NORMAL + 20,
        HEIGHT_CONFIG.DETAIL_MIN_HEIGHT
      ),
      HEIGHT_CONFIG.DETAIL_MAX_HEIGHT
    );
    baseHeight += detailHeight;
  }

  return baseHeight;
}

/**
 * Hook that provides a flattened, virtualization-ready list of visible log items.
 * Handles both phase expansion (external state) and detail expansion (internal state).
 *
 * @param phaseLogs - The phase-based task logs
 * @param expandedPhases - Set of phases that are currently expanded (managed by parent)
 * @returns Object containing the flattened items array and helper functions
 */
export function useVirtualizedLogs(
  phaseLogs: TaskLogs | null,
  expandedPhases: Set<TaskLogPhase>
) {
  // Track which log entry details are expanded
  // Key format: "phase:entryIndex" (e.g., "coding:5")
  const [expandedDetails, setExpandedDetails] = useState<Map<string, boolean>>(new Map());

  // Toggle a log entry's detail expansion
  const toggleDetail = useCallback((phase: TaskLogPhase, entryIndex: number) => {
    setExpandedDetails((prev) => {
      const next = new Map(prev);
      const key = `${phase}:${entryIndex}`;
      next.set(key, !prev.get(key));
      return next;
    });
  }, []);

  // Collapse all details when phases change
  const collapseAllDetails = useCallback(() => {
    setExpandedDetails(new Map());
  }, []);

  // Compute the flattened list of visible items
  const flattenedItems = useMemo(() => {
    return flattenLogs(phaseLogs, expandedPhases, expandedDetails);
  }, [phaseLogs, expandedPhases, expandedDetails]);

  // Create a height estimator function for use with react-virtual
  const estimateSize = useCallback(
    (index: number) => {
      const item = flattenedItems[index];
      if (!item) {
        return ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE;
      }
      return estimateLogItemHeight(item);
    },
    [flattenedItems]
  );

  return {
    /** Flattened array of visible items for virtualized rendering */
    flattenedItems,
    /** Total count of visible items */
    count: flattenedItems.length,
    /** Toggle a log entry's detail expansion */
    toggleDetail,
    /** Collapse all expanded details */
    collapseAllDetails,
    /** Height estimator function for react-virtual */
    estimateSize,
    /** Whether we have any logs */
    hasLogs: !!phaseLogs,
  };
}
