import type { TaskLogEntry, TaskLogPhase, TaskLogs } from '../../../shared/types';

/**
 * Filter type for log entries
 */
export type LogFilterType = 'all' | 'errors' | 'tools' | 'info' | 'decisions';

/**
 * Check if a log entry matches the current filter type
 */
export function entryMatchesFilter(entry: TaskLogEntry | undefined, filter: LogFilterType): boolean {
  if (filter === 'all') return true;
  if (!entry) return false;
  switch (filter) {
    case 'errors':
      return entry.type === 'error';
    case 'tools':
      return entry.type === 'tool_start' || entry.type === 'tool_end';
    case 'info':
      return entry.type === 'info' || entry.type === 'success' ||
             entry.type === 'text' || entry.type === 'phase_start' || entry.type === 'phase_end';
    case 'decisions':
      return entry.type === 'decision';
    default:
      return true;
  }
}

/**
 * Check if a log entry matches a search query.
 * Searches across content, detail, tool_name, and tool_input fields.
 */
export function entryMatchesSearch(entry: TaskLogEntry | undefined, query: string): boolean {
  if (!entry || !query.trim()) return true;

  const lowerQuery = query.toLowerCase();

  if (entry.content?.toLowerCase().includes(lowerQuery)) return true;
  if (entry.detail?.toLowerCase().includes(lowerQuery)) return true;
  if (entry.tool_name?.toLowerCase().includes(lowerQuery)) return true;
  if (entry.tool_input?.toLowerCase().includes(lowerQuery)) return true;

  return false;
}

/**
 * Compute which phases have entries matching the given filter type.
 */
export function computePhasesWithMatchingEntries(
  phaseLogs: TaskLogs | null,
  filter: LogFilterType
): Set<TaskLogPhase> {
  const phases = new Set<TaskLogPhase>();
  if (!phaseLogs || filter === 'all') return phases;

  const phaseKeys: TaskLogPhase[] = ['planning', 'coding', 'validation'];
  for (const phase of phaseKeys) {
    const phaseLog = phaseLogs.phases[phase];
    if (phaseLog?.entries?.some(entry => entryMatchesFilter(entry, filter))) {
      phases.add(phase);
    }
  }
  return phases;
}

/**
 * Calculate total log count across all phases.
 */
export function calculateTotalLogCount(phaseLogs: TaskLogs | null): number {
  if (!phaseLogs) return 0;
  return Object.values(phaseLogs.phases).reduce(
    (sum, phase) => sum + (phase?.entries?.length || 0),
    0
  );
}

/**
 * Labels for filter buttons
 */
export const FILTER_LABELS: Record<LogFilterType, string> = {
  all: 'All',
  errors: 'Errors',
  tools: 'Tools',
  info: 'Info',
  decisions: 'Decisions'
};
