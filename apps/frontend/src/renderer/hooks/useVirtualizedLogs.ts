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
 * Estimated heights for different item types (in pixels)
 * These are base heights - actual heights may vary dynamically
 */
export const ESTIMATED_HEIGHTS = {
  PHASE_HEADER: 60,           // Phase collapsible header
  LOG_ENTRY_SIMPLE: 32,       // Simple text/info entries
  LOG_ENTRY_TOOL: 40,         // Tool start/end entries
  LOG_ENTRY_ERROR: 48,        // Error entries
  LOG_ENTRY_DETAIL: 150,      // Expanded detail section (additional height)
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
 * Estimates the height of a flattened log item based on its type and content.
 * Used by the virtualizer for smooth scrolling with dynamic heights.
 *
 * @param item - The flattened log item
 * @returns Estimated height in pixels
 */
export function estimateLogItemHeight(item: FlattenedLogItem): number {
  if (item.type === 'phase-header') {
    return ESTIMATED_HEIGHTS.PHASE_HEADER;
  }

  // For log entries, base height depends on entry type
  const entry = item.entry;
  if (!entry) {
    return ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE;
  }

  let baseHeight: number;

  // Adjust base height by entry type
  switch (entry.type) {
    case 'tool_start':
    case 'tool_end':
      baseHeight = ESTIMATED_HEIGHTS.LOG_ENTRY_TOOL;
      break;
    case 'error':
      baseHeight = ESTIMATED_HEIGHTS.LOG_ENTRY_ERROR;
      break;
    case 'success':
    case 'info':
      baseHeight = ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE;
      break;
    default: {
      // Estimate height based on content length (text wraps ~80 chars per line)
      const contentLength = entry.content?.length ?? 0;
      if (contentLength > 200) {
        const estimatedLines = Math.ceil(contentLength / 80);
        baseHeight = Math.max(ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE, estimatedLines * 18 + 12);
      } else {
        baseHeight = ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE;
      }
      break;
    }
  }

  // Add detail section height if expanded
  if (item.isDetailExpanded && entry.detail) {
    // Estimate additional height based on detail content length
    const detailLines = entry.detail.split('\n').length;
    const detailHeight = Math.min(
      Math.max(detailLines * 14 + 20, ESTIMATED_HEIGHTS.LOG_ENTRY_DETAIL),
      300 // Max height for detail section
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
