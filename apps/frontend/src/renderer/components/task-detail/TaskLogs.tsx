import { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import {
  Terminal,
  Loader2,
  Pencil,
  FileCode,
  FlaskConical,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  FileText,
  Search,
  FolderSearch,
  Wrench,
  Info,
  Brain,
  Cpu,
  X
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { Task, TaskLogs, TaskLogPhase, TaskPhaseLog, TaskLogEntry, TaskMetadata } from '../../../shared/types';
import type { PhaseModelConfig, PhaseThinkingConfig, ThinkingLevel, ModelTypeShort } from '../../../shared/types/settings';
import { useVirtualizedLogs } from '../../hooks/useVirtualizedLogs';

interface TaskLogsProps {
  task: Task;
  phaseLogs: TaskLogs | null;
  isLoadingLogs: boolean;
  expandedPhases: Set<TaskLogPhase>;
  isStuck: boolean;
  logsEndRef: React.RefObject<HTMLDivElement | null>;
  logsContainerRef: React.RefObject<HTMLDivElement | null>;
  onLogsScroll: (e: React.UIEvent<HTMLDivElement>) => void;
  onTogglePhase: (phase: TaskLogPhase) => void;
  shouldAutoScroll: boolean;
}

const PHASE_LABELS: Record<TaskLogPhase, string> = {
  planning: 'Planning',
  coding: 'Coding',
  validation: 'Validation'
};

const PHASE_ICONS: Record<TaskLogPhase, typeof Pencil> = {
  planning: Pencil,
  coding: FileCode,
  validation: FlaskConical
};

const PHASE_COLORS: Record<TaskLogPhase, string> = {
  planning: 'text-amber-500 bg-amber-500/10 border-amber-500/30',
  coding: 'text-info bg-info/10 border-info/30',
  validation: 'text-purple-500 bg-purple-500/10 border-purple-500/30'
};

// Map log phases to config phase keys
// Note: 'planning' log phase covers both spec creation and implementation planning
const LOG_PHASE_TO_CONFIG_PHASE: Record<TaskLogPhase, keyof PhaseModelConfig> = {
  planning: 'spec',  // Planning log phase primarily shows spec creation
  coding: 'coding',
  validation: 'qa'
};

// Short labels for models
const MODEL_SHORT_LABELS: Record<ModelTypeShort, string> = {
  opus: 'Opus',
  sonnet: 'Sonnet',
  haiku: 'Haiku'
};

// Short labels for thinking levels
const THINKING_SHORT_LABELS: Record<ThinkingLevel, string> = {
  none: 'None',
  low: 'Low',
  medium: 'Med',
  high: 'High',
  ultrathink: 'Ultra'
};

// Helper to get model and thinking info for a log phase
function getPhaseConfig(
  metadata: TaskMetadata | undefined,
  logPhase: TaskLogPhase
): { model: string; thinking: string } | null {
  if (!metadata) return null;

  const configPhase = LOG_PHASE_TO_CONFIG_PHASE[logPhase];

  // Auto profile with per-phase config
  if (metadata.isAutoProfile && metadata.phaseModels && metadata.phaseThinking) {
    const model = metadata.phaseModels[configPhase];
    const thinking = metadata.phaseThinking[configPhase];
    return {
      model: MODEL_SHORT_LABELS[model] || model,
      thinking: THINKING_SHORT_LABELS[thinking] || thinking
    };
  }

  // Non-auto profile with single model/thinking
  if (metadata.model && metadata.thinkingLevel) {
    return {
      model: MODEL_SHORT_LABELS[metadata.model] || metadata.model,
      thinking: THINKING_SHORT_LABELS[metadata.thinkingLevel] || metadata.thinkingLevel
    };
  }

  return null;
}

// Number of items to render outside the visible area for smoother scrolling
const OVERSCAN = 5;

// Filter types
type LogFilterType = 'all' | 'errors' | 'tools' | 'info';

const FILTER_LABELS: Record<LogFilterType, string> = {
  all: 'All',
  errors: 'Errors',
  tools: 'Tools',
  info: 'Info'
};

export function TaskLogs({
  task,
  phaseLogs,
  isLoadingLogs,
  expandedPhases,
  isStuck,
  logsEndRef,
  logsContainerRef,
  onLogsScroll,
  onTogglePhase,
  shouldAutoScroll
}: TaskLogsProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<LogFilterType>('all');

  // Performance measurement
  const renderStartTime = useMemo(() => performance.now(), []);
  const previousLogCountRef = useRef(0);
  const performanceMetricsRef = useRef({
    initialRender: 0,
    filterChanges: [] as Array<{ filter: LogFilterType; time: number; itemCount: number }>,
    logUpdates: [] as Array<{ logCount: number; time: number }>
  });

  // Helper function to check if an entry matches the current filter
  const entryMatchesFilter = useCallback((entry: TaskLogEntry | undefined, filter: LogFilterType): boolean => {
    if (!entry || filter === 'all') return true;
    switch (filter) {
      case 'errors':
        return entry.type === 'error';
      case 'tools':
        return entry.type === 'tool_start' || entry.type === 'tool_end';
      case 'info':
        return entry.type === 'info' || entry.type === 'success' ||
               entry.type === 'text' || entry.type === 'phase_start' || entry.type === 'phase_end';
      default:
        return true;
    }
  }, []);

  // Compute which phases have matching entries for current filter
  const phasesWithMatchingEntries = useMemo(() => {
    const phases = new Set<TaskLogPhase>();
    if (!phaseLogs || filterType === 'all') return phases;

    const phaseKeys: TaskLogPhase[] = ['planning', 'coding', 'validation'];
    for (const phase of phaseKeys) {
      const phaseLog = phaseLogs.phases[phase];
      if (phaseLog?.entries?.some(entry => entryMatchesFilter(entry, filterType))) {
        phases.add(phase);
      }
    }
    return phases;
  }, [phaseLogs, filterType, entryMatchesFilter]);

  // Effective expanded phases: union of user-expanded and filter-matched phases
  const effectiveExpandedPhases = useMemo(() => {
    if (filterType === 'all') return expandedPhases;
    const combined = new Set(expandedPhases);
    phasesWithMatchingEntries.forEach(phase => combined.add(phase));
    return combined;
  }, [expandedPhases, phasesWithMatchingEntries, filterType]);

  const {
    flattenedItems,
    count,
    toggleDetail,
    estimateSize,
    hasLogs
  } = useVirtualizedLogs(phaseLogs, effectiveExpandedPhases);

  // Filter items based on search query and filter type
  const filteredItems = useMemo(() => {
    let items = flattenedItems;

    // Apply filter type
    if (filterType !== 'all') {
      items = items.filter(item => {
        // Always show phase headers
        if (item.type === 'phase-header') return true;

        // Filter log entries
        const entry = item.entry;
        if (!entry) return false;

        switch (filterType) {
          case 'errors':
            return entry.type === 'error';
          case 'tools':
            return entry.type === 'tool_start' || entry.type === 'tool_end';
          case 'info':
            // Info filter includes: info, success, text, phase_start, phase_end
            return entry.type === 'info' || entry.type === 'success' ||
                   entry.type === 'text' || entry.type === 'phase_start' || entry.type === 'phase_end';
          default:
            return true;
        }
      });
    }

    // Apply search query
    if (searchQuery.trim()) {
      const lowerQuery = searchQuery.toLowerCase();
      items = items.filter(item => {
        // Always show phase headers
        if (item.type === 'phase-header') return true;

        // Search in log entries
        const entry = item.entry;
        if (!entry) return false;

        // Search in content
        if (entry.content?.toLowerCase().includes(lowerQuery)) return true;

        // Search in detail
        if (entry.detail?.toLowerCase().includes(lowerQuery)) return true;

        // Search in tool name
        if (entry.tool_name?.toLowerCase().includes(lowerQuery)) return true;

        // Search in tool input
        if (entry.tool_input?.toLowerCase().includes(lowerQuery)) return true;

        return false;
      });
    }

    return items;
  }, [flattenedItems, searchQuery, filterType]);

  // Set up the virtualizer with filtered items
  const rowVirtualizer = useVirtualizer({
    count: filteredItems.length,
    getScrollElement: () => parentRef.current,
    estimateSize,
    overscan: OVERSCAN,
  });

  // Auto-scroll to bottom when new logs arrive for active tasks
  useEffect(() => {
    if (shouldAutoScroll && filteredItems.length > 0) {
      // Scroll to the last item using the virtualizer's scrollToIndex
      // This is more efficient than scrollIntoView for virtualized lists
      rowVirtualizer.scrollToIndex(filteredItems.length - 1, {
        align: 'end',
        behavior: 'smooth',
      });
    }
  }, [shouldAutoScroll, filteredItems.length, rowVirtualizer]);

  // Create toggle handler for phase headers
  const createPhaseToggleHandler = useCallback(
    (phase: TaskLogPhase) => {
      return () => onTogglePhase(phase);
    },
    [onTogglePhase]
  );

  // Create toggle handler for log entry details
  const createDetailToggleHandler = useCallback(
    (phase: TaskLogPhase, entryIndex: number) => {
      return () => toggleDetail(phase, entryIndex);
    },
    [toggleDetail]
  );

  // Calculate total log count across all phases
  const totalLogCount = useMemo(() => {
    if (!phaseLogs) return 0;
    return Object.values(phaseLogs.phases).reduce(
      (sum, phase) => sum + (phase?.entries?.length || 0),
      0
    );
  }, [phaseLogs]);

  // Performance: Measure initial render when logs load
  useEffect(() => {
    if (phaseLogs && totalLogCount > 0) {
      const renderEndTime = performance.now();
      const initialRenderTime = renderEndTime - renderStartTime;

      performanceMetricsRef.current.initialRender = initialRenderTime;

      // Log performance metrics to console for verification
      console.group('📊 TaskLogs Performance Metrics');
      console.log(`Initial Render: ${initialRenderTime.toFixed(2)}ms`);
      console.log(`Total Log Entries: ${totalLogCount}`);
      console.log(`Flattened Items: ${flattenedItems.length}`);
      console.log(`Filtered Items: ${filteredItems.length}`);
      console.log(`Performance Target: <100ms ${initialRenderTime < 100 ? '✅ PASS' : '❌ FAIL'}`);
      console.groupEnd();

      // Track for log update measurements
      previousLogCountRef.current = totalLogCount;
    }
  }, [phaseLogs, totalLogCount, flattenedItems.length, filteredItems.length, renderStartTime]);

  // Performance: Measure render time when logs update
  useEffect(() => {
    if (phaseLogs && totalLogCount > 0 && previousLogCountRef.current > 0) {
      const updateStartTime = performance.now();

      // Use requestAnimationFrame to measure after React completes rendering
      requestAnimationFrame(() => {
        const updateEndTime = performance.now();
        const updateTime = updateEndTime - updateStartTime;

        performanceMetricsRef.current.logUpdates.push({
          logCount: totalLogCount,
          time: updateTime
        });

        console.log(`🔄 TaskLogs Update: ${totalLogCount} entries rendered in ${updateTime.toFixed(2)}ms`);

        previousLogCountRef.current = totalLogCount;
      });
    }
  }, [phaseLogs, totalLogCount]);

  // Performance: Measure filter change performance
  useEffect(() => {
    if (phaseLogs && totalLogCount > 0) {
      const filterStartTime = performance.now();

      // Use requestAnimationFrame to measure after React completes rendering
      requestAnimationFrame(() => {
        const filterEndTime = performance.now();
        const filterTime = filterEndTime - filterStartTime;

        performanceMetricsRef.current.filterChanges.push({
          filter: filterType,
          time: filterTime,
          itemCount: filteredItems.length
        });

        console.log(`🔍 Filter Change (${filterType}): ${filteredItems.length} items rendered in ${filterTime.toFixed(2)}ms`);
      });
    }
  }, [filterType, filteredItems.length, phaseLogs, totalLogCount]);

  // Expose performance metrics to window for debugging (development only)
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      (window as any).__taskLogsPerformance = performanceMetricsRef.current;
    }
  }, []);

  if (isLoadingLogs) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Fallback to legacy raw logs if no phase logs exist
  if (!phaseLogs && task.logs && task.logs.length > 0) {
    return (
      <div
        ref={logsContainerRef}
        className="h-full overflow-y-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent"
        onScroll={onLogsScroll}
      >
        <div className="p-4">
          <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap break-all">
            {task.logs.join('')}
            <div ref={logsEndRef} />
          </pre>
        </div>
      </div>
    );
  }

  // Empty state
  if (!hasLogs || count === 0) {
    return (
      <div className="text-center text-sm text-muted-foreground py-8">
        <Terminal className="mx-auto mb-2 h-8 w-8 opacity-50" />
        <p>No logs yet</p>
        <p className="text-xs mt-1">Logs will appear here when the task runs</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Search and Filter Controls */}
      <div className="flex-shrink-0 p-3 border-b border-border bg-background/50">
        <div className="flex items-center gap-2">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search logs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={cn(
                'w-full h-8 pl-8 pr-8 text-xs rounded-md',
                'bg-secondary/50 border border-border',
                'focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent',
                'placeholder:text-muted-foreground'
              )}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Filter Buttons */}
          <div className="flex items-center gap-1">
            {(Object.keys(FILTER_LABELS) as LogFilterType[]).map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={cn(
                  'px-2.5 py-1 text-xs rounded-md transition-colors',
                  filterType === type
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary/50 text-muted-foreground hover:bg-secondary hover:text-foreground'
                )}
              >
                {FILTER_LABELS[type]}
              </button>
            ))}
          </div>
        </div>

        {/* Active filters indicator */}
        {(searchQuery || filterType !== 'all') && (
          <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
            <span>
              Showing {filteredItems.length} of {flattenedItems.length} items
            </span>
            {filterType !== 'all' && (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                {FILTER_LABELS[filterType]}
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Logs List */}
      <div
        ref={parentRef}
        className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent"
        onScroll={onLogsScroll}
      >
        <div className="p-4">
          {filteredItems.length === 0 ? (
            <div className="text-center text-sm text-muted-foreground py-8">
              <Search className="mx-auto mb-2 h-8 w-8 opacity-50" />
              <p>No matching logs</p>
              <p className="text-xs mt-1">Try adjusting your search or filter</p>
            </div>
          ) : (
            <>
              {/* The large inner element to hold all of the items */}
              <div
                style={{
                  height: `${rowVirtualizer.getTotalSize()}px`,
                  width: '100%',
                  position: 'relative',
                }}
              >
                {/* Only the visible items in the virtualizer */}
                {rowVirtualizer.getVirtualItems().map((virtualItem) => {
                  const item = filteredItems[virtualItem.index];
                  if (!item) return null;

                  return (
                    <div
                      key={item.key}
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: `${virtualItem.size}px`,
                        transform: `translateY(${virtualItem.start}px)`,
                      }}
                    >
                      {item.type === 'phase-header' ? (
                        <div className="pb-2">
                          <PhaseLogSection
                            phase={item.phase}
                            phaseLog={item.phaseLog || null}
                            isExpanded={item.isPhaseExpanded || false}
                            onToggle={createPhaseToggleHandler(item.phase)}
                            isTaskStuck={isStuck}
                            phaseConfig={getPhaseConfig(task.metadata, item.phase)}
                          />
                        </div>
                      ) : (
                        item.entry && (
                          <div className="ml-6 border-l-2 border-border pl-4 py-1">
                            <LogEntry
                              entry={item.entry}
                              isExpanded={item.isDetailExpanded || false}
                              onToggleExpand={createDetailToggleHandler(item.phase, item.entryIndex || 0)}
                            />
                          </div>
                        )
                      )}
                    </div>
                  );
                })}
              </div>
              <div ref={logsEndRef} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// Phase Log Section Component
interface PhaseLogSectionProps {
  phase: TaskLogPhase;
  phaseLog: TaskPhaseLog | null;
  isExpanded: boolean;
  onToggle: () => void;
  isTaskStuck?: boolean;
  phaseConfig?: { model: string; thinking: string } | null;
}

function PhaseLogSection({ phase, phaseLog, isExpanded, onToggle, isTaskStuck, phaseConfig }: PhaseLogSectionProps) {
  const Icon = PHASE_ICONS[phase];
  const status = phaseLog?.status || 'pending';
  const hasEntries = (phaseLog?.entries.length || 0) > 0;

  const getStatusBadge = () => {
    switch (status) {
      case 'active':
        if (isTaskStuck) {
          return (
            <Badge variant="outline" className="text-xs bg-warning/10 text-warning border-warning/30 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              Interrupted
            </Badge>
          );
        }
        return (
          <Badge variant="outline" className="text-xs bg-info/10 text-info border-info/30 flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            Running
          </Badge>
        );
      case 'completed':
        return (
          <Badge variant="outline" className="text-xs bg-success/10 text-success border-success/30 flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            Complete
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="outline" className="text-xs bg-destructive/10 text-destructive border-destructive/30 flex items-center gap-1">
            <XCircle className="h-3 w-3" />
            Failed
          </Badge>
        );
      default:
        return (
          <Badge variant="secondary" className="text-xs text-muted-foreground">
            Pending
          </Badge>
        );
    }
  };

  const isInterrupted = isTaskStuck && status === 'active';

  return (
    <button
      onClick={onToggle}
      className={cn(
        'w-full flex items-center justify-between p-3 rounded-lg border transition-colors',
        'hover:bg-secondary/50',
        status === 'active' && !isInterrupted && PHASE_COLORS[phase],
        isInterrupted && 'border-warning/30 bg-warning/5',
        status === 'completed' && 'border-success/30 bg-success/5',
        status === 'failed' && 'border-destructive/30 bg-destructive/5',
        status === 'pending' && 'border-border bg-secondary/30'
      )}
    >
      <div className="flex items-center gap-2">
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
        <Icon className={cn('h-4 w-4', isInterrupted ? 'text-warning' : status === 'active' ? PHASE_COLORS[phase].split(' ')[0] : 'text-muted-foreground')} />
        <span className="font-medium text-sm">{PHASE_LABELS[phase]}</span>
        {hasEntries && (
          <span className="text-xs text-muted-foreground">
            ({phaseLog?.entries.length} entries)
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        {/* Model and thinking level indicator */}
        {phaseConfig && (
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <div className="flex items-center gap-0.5" title={`Model: ${phaseConfig.model}`}>
              <Cpu className="h-3 w-3" />
              <span>{phaseConfig.model}</span>
            </div>
            <span className="text-muted-foreground/50">|</span>
            <div className="flex items-center gap-0.5" title={`Thinking: ${phaseConfig.thinking}`}>
              <Brain className="h-3 w-3" />
              <span>{phaseConfig.thinking}</span>
            </div>
          </div>
        )}
        {getStatusBadge()}
      </div>
    </button>
  );
}

// Log Entry Component
interface LogEntryProps {
  entry: TaskLogEntry;
  isExpanded: boolean;
  onToggleExpand: () => void;
}

function LogEntry({ entry, isExpanded, onToggleExpand }: LogEntryProps) {
  const hasDetail = Boolean(entry.detail);

  const getToolInfo = (toolName: string) => {
    switch (toolName) {
      case 'Read':
        return { icon: FileText, label: 'Reading', color: 'text-blue-500 bg-blue-500/10' };
      case 'Glob':
        return { icon: FolderSearch, label: 'Searching files', color: 'text-amber-500 bg-amber-500/10' };
      case 'Grep':
        return { icon: Search, label: 'Searching code', color: 'text-green-500 bg-green-500/10' };
      case 'Edit':
        return { icon: Pencil, label: 'Editing', color: 'text-purple-500 bg-purple-500/10' };
      case 'Write':
        return { icon: FileCode, label: 'Writing', color: 'text-cyan-500 bg-cyan-500/10' };
      case 'Bash':
        return { icon: Terminal, label: 'Running', color: 'text-orange-500 bg-orange-500/10' };
      default:
        return { icon: Wrench, label: toolName, color: 'text-muted-foreground bg-muted' };
    }
  };

  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return '';
    }
  };

  const SubphaseBadge = () => {
    if (!entry.subphase) return null;
    return (
      <Badge variant="outline" className="text-[9px] px-1 py-0 ml-1 text-muted-foreground border-muted-foreground/30">
        {entry.subphase}
      </Badge>
    );
  };

  if (entry.type === 'tool_start' && entry.tool_name) {
    const { icon: Icon, label, color } = getToolInfo(entry.tool_name);
    return (
      <div className="flex flex-col min-w-0">
        <div className={cn('flex items-center gap-2 rounded-md px-2 py-1 text-xs min-w-0 overflow-hidden', color)}>
          <Icon className="h-3 w-3 animate-pulse shrink-0" />
          <span className="font-medium shrink-0">{label}</span>
          {entry.tool_input && (
            <span className="text-muted-foreground break-words min-w-0 flex-1" title={entry.tool_input}>
              {entry.tool_input}
            </span>
          )}
          <SubphaseBadge />
        </div>
      </div>
    );
  }

  if (entry.type === 'tool_end' && entry.tool_name) {
    const { icon: Icon, color } = getToolInfo(entry.tool_name);
    return (
      <div className="flex flex-col min-w-0">
        <div className="flex items-center gap-2 min-w-0">
          <div className={cn('flex items-center gap-2 rounded-md px-2 py-1 text-xs shrink-0 overflow-hidden', color, 'opacity-60')}>
            <Icon className="h-3 w-3" />
            <CheckCircle2 className="h-3 w-3 text-success" />
            <span className="text-muted-foreground">Done</span>
          </div>
          {hasDetail && (
            <button
              onClick={onToggleExpand}
              className={cn(
                'flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded shrink-0',
                'text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors',
                isExpanded && 'bg-secondary/50'
              )}
            >
              {isExpanded ? (
                <>
                  <ChevronDown className="h-2.5 w-2.5" />
                  <span>Hide output</span>
                </>
              ) : (
                <>
                  <ChevronRight className="h-2.5 w-2.5" />
                  <span>Show output</span>
                </>
              )}
            </button>
          )}
        </div>
        {hasDetail && isExpanded && (
          <div className="mt-1.5 ml-4 p-2 bg-secondary/30 rounded-md border border-border/50 overflow-hidden">
            <pre className="text-[10px] text-muted-foreground whitespace-pre-wrap break-words font-mono max-h-[300px] overflow-y-auto">
              {entry.detail}
            </pre>
          </div>
        )}
      </div>
    );
  }

  if (entry.type === 'error') {
    return (
      <div className="flex flex-col min-w-0">
        <div className="flex items-start gap-2 text-xs text-destructive bg-destructive/10 rounded-md px-2 py-1 min-w-0">
          <XCircle className="h-3 w-3 mt-0.5 shrink-0" />
          <span className="break-words min-w-0 flex-1 overflow-hidden">{entry.content}</span>
          <div className="flex items-center gap-1 shrink-0">
            <SubphaseBadge />
            {hasDetail && (
              <button
                onClick={onToggleExpand}
                className={cn(
                  'flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded',
                  'text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors',
                  isExpanded && 'bg-secondary/50'
                )}
              >
                {isExpanded ? <ChevronDown className="h-2.5 w-2.5" /> : <ChevronRight className="h-2.5 w-2.5" />}
              </button>
            )}
          </div>
        </div>
        {hasDetail && isExpanded && (
          <div className="mt-1.5 ml-4 p-2 bg-destructive/5 rounded-md border border-destructive/20 overflow-hidden">
            <pre className="text-[10px] text-destructive/80 whitespace-pre-wrap break-words font-mono max-h-[300px] overflow-y-auto">
              {entry.detail}
            </pre>
          </div>
        )}
      </div>
    );
  }

  if (entry.type === 'success') {
    return (
      <div className="flex items-start gap-2 text-xs text-success bg-success/10 rounded-md px-2 py-1 min-w-0">
        <CheckCircle2 className="h-3 w-3 mt-0.5 shrink-0" />
        <span className="break-words min-w-0 flex-1 overflow-hidden">{entry.content}</span>
        <SubphaseBadge />
      </div>
    );
  }

  if (entry.type === 'info') {
    return (
      <div className="flex items-start gap-2 text-xs text-info bg-info/10 rounded-md px-2 py-1 min-w-0">
        <Info className="h-3 w-3 mt-0.5 shrink-0" />
        <span className="break-words min-w-0 flex-1 overflow-hidden">{entry.content}</span>
        <SubphaseBadge />
      </div>
    );
  }

  // Default text entry
  return (
    <div className="flex flex-col min-w-0">
      <div className="flex items-start gap-2 text-xs text-muted-foreground py-0.5 min-w-0">
        <span className="text-[10px] text-muted-foreground/60 tabular-nums shrink-0">
          {formatTime(entry.timestamp)}
        </span>
        <span className="break-words whitespace-pre-wrap min-w-0 flex-1 overflow-hidden">{entry.content}</span>
        <div className="flex items-center gap-1 shrink-0">
          <SubphaseBadge />
          {hasDetail && (
            <button
              onClick={onToggleExpand}
              className={cn(
                'flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded',
                'text-muted-foreground hover:text-foreground hover:bg-secondary/50 transition-colors',
                isExpanded && 'bg-secondary/50'
              )}
            >
              {isExpanded ? (
                <>
                  <ChevronDown className="h-2.5 w-2.5" />
                  <span>Less</span>
                </>
              ) : (
                <>
                  <ChevronRight className="h-2.5 w-2.5" />
                  <span>More</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>
      {hasDetail && isExpanded && (
        <div className="mt-1.5 ml-12 p-2 bg-secondary/30 rounded-md border border-border/50 overflow-hidden">
          <pre className="text-[10px] text-muted-foreground whitespace-pre-wrap break-words font-mono max-h-[300px] overflow-y-auto">
            {entry.detail}
          </pre>
        </div>
      )}
    </div>
  );
}
