import { useMemo, useState, useCallback, useEffect, useRef } from 'react';
import type {
  TaskLogs,
  TaskLogPhase,
  TaskLogEntry,
  LogFilterState,
  LogSearchResult,
  LogSearchState,
} from '../../shared/types';

/**
 * Default debounce delay in milliseconds
 */
const DEFAULT_DEBOUNCE_DELAY = 300;

/**
 * Searches a log entry for the given query string.
 * Returns match information if found, null otherwise.
 *
 * @param entry - The log entry to search
 * @param query - The search query (case-insensitive)
 * @param phase - The phase this entry belongs to
 * @param entryIndex - The index of this entry within its phase
 * @returns LogSearchResult if match found, null otherwise
 */
function searchLogEntry(
  entry: TaskLogEntry,
  query: string,
  phase: TaskLogPhase,
  entryIndex: number
): LogSearchResult | null {
  if (!query) {
    return null;
  }

  const lowerQuery = query.toLowerCase();

  // Search in content
  if (entry.content?.toLowerCase().includes(lowerQuery)) {
    return {
      phase,
      entryIndex,
      matchType: 'content',
      matchText: entry.content,
    };
  }

  // Search in tool name
  if (entry.tool_name?.toLowerCase().includes(lowerQuery)) {
    return {
      phase,
      entryIndex,
      matchType: 'tool_name',
      matchText: entry.tool_name,
    };
  }

  // Search in tool input
  if (entry.tool_input?.toLowerCase().includes(lowerQuery)) {
    return {
      phase,
      entryIndex,
      matchType: 'tool_input',
      matchText: entry.tool_input,
    };
  }

  // Search in detail
  if (entry.detail?.toLowerCase().includes(lowerQuery)) {
    return {
      phase,
      entryIndex,
      matchType: 'detail',
      matchText: entry.detail,
    };
  }

  return null;
}

/**
 * Checks if a log entry passes the current filter criteria.
 *
 * @param entry - The log entry to check
 * @param filter - The filter state
 * @returns true if entry should be included, false otherwise
 */
function passesFilter(entry: TaskLogEntry, filter: LogFilterState): boolean {
  // Filter by phase (empty array = all phases)
  if (filter.phases.length > 0 && !filter.phases.includes(entry.phase)) {
    return false;
  }

  // Filter by entry type (empty array = all types)
  if (filter.entryTypes.length > 0 && !filter.entryTypes.includes(entry.type)) {
    return false;
  }

  // Filter by tool (empty array = all tools)
  if (
    filter.tools.length > 0 &&
    entry.tool_name &&
    !filter.tools.includes(entry.tool_name)
  ) {
    return false;
  }

  // Filter tool output visibility
  if (!filter.showToolOutput) {
    if (entry.type === 'tool_start' || entry.type === 'tool_end') {
      return false;
    }
  }

  return true;
}

/**
 * Performs search across all log entries with filtering.
 *
 * @param phaseLogs - The phase-based task logs
 * @param filter - The filter state including search query
 * @returns Array of search results
 */
function performSearch(
  phaseLogs: TaskLogs | null,
  filter: LogFilterState
): LogSearchResult[] {
  if (!phaseLogs || !filter.searchQuery) {
    return [];
  }

  const results: LogSearchResult[] = [];
  const phases: TaskLogPhase[] = ['planning', 'coding', 'validation'];

  for (const phase of phases) {
    const phaseLog = phaseLogs.phases[phase];
    if (!phaseLog?.entries) {
      continue;
    }

    phaseLog.entries.forEach((entry, index) => {
      // First check if entry passes filter criteria
      if (!passesFilter(entry, filter)) {
        return;
      }

      // Then check if it matches the search query
      const match = searchLogEntry(entry, filter.searchQuery, phase, index);
      if (match) {
        results.push(match);
      }
    });
  }

  return results;
}

/**
 * Hook that provides debounced search functionality for task logs.
 * Searches across all log entries with support for filtering by phase, type, and tool.
 *
 * @param phaseLogs - The phase-based task logs
 * @param filter - The filter state including search query
 * @param debounceDelay - Optional debounce delay in milliseconds (default: 300ms)
 * @returns LogSearchState with search results and navigation functions
 */
export function useLogSearch(
  phaseLogs: TaskLogs | null,
  filter: LogFilterState,
  debounceDelay: number = DEFAULT_DEBOUNCE_DELAY
): LogSearchState & {
  nextResult: () => void;
  previousResult: () => void;
  goToResult: (index: number) => void;
  clearSearch: () => void;
} {
  // Track debounced query separately from filter.searchQuery
  const [debouncedQuery, setDebouncedQuery] = useState(filter.searchQuery);
  const [isSearching, setIsSearching] = useState(false);
  const [currentResultIndex, setCurrentResultIndex] = useState(0);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Debounce the search query
  useEffect(() => {
    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set searching state immediately when query changes
    if (filter.searchQuery !== debouncedQuery) {
      setIsSearching(true);
    }

    // Set new timer
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedQuery(filter.searchQuery);
      setIsSearching(false);
      setCurrentResultIndex(0); // Reset to first result on new search
    }, debounceDelay);

    // Cleanup on unmount
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [filter.searchQuery, debouncedQuery, debounceDelay]);

  // Perform search with debounced query
  const results = useMemo(() => {
    // Create filter with debounced query for search
    const searchFilter: LogFilterState = {
      ...filter,
      searchQuery: debouncedQuery,
    };
    return performSearch(phaseLogs, searchFilter);
  }, [phaseLogs, filter, debouncedQuery]);

  // Navigate to next result
  const nextResult = useCallback(() => {
    if (results.length === 0) {
      return;
    }
    setCurrentResultIndex((prev) => (prev + 1) % results.length);
  }, [results.length]);

  // Navigate to previous result
  const previousResult = useCallback(() => {
    if (results.length === 0) {
      return;
    }
    setCurrentResultIndex((prev) => (prev - 1 + results.length) % results.length);
  }, [results.length]);

  // Navigate to specific result
  const goToResult = useCallback(
    (index: number) => {
      if (index >= 0 && index < results.length) {
        setCurrentResultIndex(index);
      }
    },
    [results.length]
  );

  // Clear search and reset state
  const clearSearch = useCallback(() => {
    setDebouncedQuery('');
    setCurrentResultIndex(0);
    setIsSearching(false);
  }, []);

  return {
    query: debouncedQuery,
    results,
    currentResultIndex,
    isSearching,
    nextResult,
    previousResult,
    goToResult,
    clearSearch,
  };
}
