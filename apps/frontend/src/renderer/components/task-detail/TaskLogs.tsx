import { useState, useRef, useCallback, useMemo } from 'react';
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
  X,
  Lightbulb,
  GitBranch,
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { Task, TaskLogs, TaskLogPhase, TaskPhaseLog, TaskLogEntry, TaskMetadata, DecisionPoint, Alternative } from '../../../shared/types';
import type { PhaseModelConfig, ThinkingLevel, ModelTypeShort } from '../../../shared/types/settings';
import { useVirtualizedLogs } from '../../hooks/useVirtualizedLogs';
import { FeedbackButtons } from '../feedback/FeedbackButtons';
import { getDecisionTypeMeta, getConfidenceMeta } from '../../../shared/constants/decision-meta';
import { entryMatchesFilter, entryMatchesSearch, FILTER_LABELS, type LogFilterType } from './log-utils';

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

export function TaskLogs({
  task,
  phaseLogs,
  isLoadingLogs,
  expandedPhases,
  isStuck,
  logsEndRef,
  logsContainerRef,
  onLogsScroll,
  onTogglePhase
}: TaskLogsProps) {
  const parentRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<LogFilterType>('all');

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
  }, [phaseLogs, filterType]);

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

        return entryMatchesFilter(item.entry, filterType);
      });
    }

    // Apply search query
    if (searchQuery.trim()) {
      items = items.filter(item => {
        if (item.type === 'phase-header') return true;
        if (!item.entry) return false;
        return entryMatchesSearch(item.entry, searchQuery);
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
                      data-index={virtualItem.index}
                      ref={rowVirtualizer.measureElement}
                      style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
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
                            taskId={task.id}
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
  taskId?: string;
}

function PhaseLogSection({ phase, phaseLog, isExpanded, onToggle, isTaskStuck, phaseConfig, taskId }: PhaseLogSectionProps) {
  const Icon = PHASE_ICONS[phase];
  const status = phaseLog?.status || 'pending';
  const hasEntries = (phaseLog?.entries?.length || 0) > 0;

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
    <div className="pb-2">
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
              ({phaseLog?.entries?.length} entries)
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
      {/* Feedback buttons for completed phases (only when expanded) */}
      {status === 'completed' && isExpanded && (
        <div className="mt-2 ml-3">
          <FeedbackButtons
            taskId={taskId}
            agentType={phase}
            outputDescription={`${PHASE_LABELS[phase]} phase output`}
            context={`Phase: ${PHASE_LABELS[phase]}`}
            size="sm"
          />
        </div>
      )}
    </div>
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

  if (entry.type === 'decision' && entry.decision_data) {
    const decision = entry.decision_data as unknown as DecisionPoint;
    const typeMeta = getDecisionTypeMeta(decision.decision_type);
    const confidenceMeta = getConfidenceMeta(decision.confidence_level);
    const TypeIcon = typeMeta.icon;
    const ConfidenceIcon = confidenceMeta.icon;

    return (
      <div className={cn(
        'rounded-lg border bg-card/50',
        decision.requires_review && 'border-amber-500/50 bg-amber-500/5'
      )}>
        {/* Decision Header */}
        <button
          onClick={onToggleExpand}
          className="w-full px-3 py-2 flex items-start gap-2 hover:bg-accent/50 transition-colors"
        >
          {/* Expand/Collapse Icon */}
          <div className="flex-shrink-0 mt-0.5">
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
            )}
          </div>

          {/* Decision Type Icon */}
          <div className="flex-shrink-0">
            <div className={cn('rounded p-1 border', typeMeta.color)}>
              <TypeIcon className="h-3.5 w-3.5" />
            </div>
          </div>

          {/* Decision Content */}
          <div className="flex-1 text-left min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap mb-1">
              <span className="font-medium text-xs">{typeMeta.label}</span>

              {/* Confidence Badge */}
              <Badge variant="outline" className={cn('text-[10px] px-1 py-0', confidenceMeta.color)}>
                <ConfidenceIcon className="mr-1 h-2.5 w-2.5" />
                {confidenceMeta.label} ({Math.round((decision.confidence ?? 0) * 100)}%)
              </Badge>

              {/* Review Required Badge */}
              {decision.requires_review && (
                <Badge variant="outline" className="text-[10px] px-1 py-0 text-amber-500 bg-amber-500/10 border-amber-500/30">
                  <AlertTriangle className="mr-1 h-2.5 w-2.5" />
                  Review
                </Badge>
              )}
            </div>

            <p className="text-xs text-foreground line-clamp-2">
              {decision.chosen_approach}
            </p>

            {/* Show hint about expandable content */}
            {!isExpanded && (
              <p className="text-[10px] text-muted-foreground mt-0.5">
                {decision.alternatives && decision.alternatives.length > 0 && (
                  <span>• {decision.alternatives.length} alternative{decision.alternatives.length !== 1 ? 's' : ''}</span>
                )}
                {decision.reasoning_chain && decision.reasoning_chain.length > 0 && (
                  <span className="ml-2">• {decision.reasoning_chain.length} reasoning step{decision.reasoning_chain.length !== 1 ? 's' : ''}</span>
                )}
              </p>
            )}
          </div>

          {/* Timestamp */}
          <div className="flex-shrink-0 text-[10px] text-muted-foreground">
            {formatTime(decision.timestamp)}
          </div>
        </button>

        {/* Expanded Details */}
        {isExpanded && (
          <div className="px-3 pb-3 space-y-3 border-t">
            {/* Context */}
            {decision.context && (
              <div className="pt-3">
                <h4 className="text-[10px] font-semibold text-muted-foreground uppercase mb-1.5">
                  Context
                </h4>
                <p className="text-xs text-foreground">{decision.context}</p>
              </div>
            )}

            {/* Chosen Approach */}
            <div>
              <h4 className="text-[10px] font-semibold text-muted-foreground uppercase mb-1.5 flex items-center">
                <CheckCircle2 className="mr-1 h-3 w-3 text-green-500" />
                Chosen Approach
              </h4>
              <p className="text-xs text-foreground">{decision.chosen_approach}</p>
            </div>

            {/* Reasoning */}
            {decision.reasoning && (
              <div>
                <h4 className="text-[10px] font-semibold text-muted-foreground uppercase mb-1.5 flex items-center">
                  <Lightbulb className="mr-1 h-3 w-3 text-amber-500" />
                  Reasoning
                </h4>
                <p className="text-xs text-foreground">{decision.reasoning}</p>
              </div>
            )}

            {/* Reasoning Chain */}
            {decision.reasoning_chain && decision.reasoning_chain.length > 0 && (
              <div>
                <h4 className="text-[10px] font-semibold text-muted-foreground uppercase mb-1.5">
                  Reasoning Steps
                </h4>
                <ol className="space-y-1.5">
                  {decision.reasoning_chain.map((step, stepIndex) => (
                    <li key={stepIndex} className="flex gap-1.5 text-xs">
                      <span className="flex-shrink-0 w-4 h-4 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-medium">
                        {stepIndex + 1}
                      </span>
                      <span className="flex-1 text-foreground">{step}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Alternatives */}
            {decision.alternatives && decision.alternatives.length > 0 && (
              <div>
                <h4 className="text-[10px] font-semibold text-muted-foreground uppercase mb-1.5 flex items-center">
                  <GitBranch className="mr-1 h-3 w-3 text-muted-foreground" />
                  Alternatives Considered ({decision.alternatives.length})
                </h4>
                <div className="space-y-2">
                  {decision.alternatives.map((alt, altIndex) => (
                    <DecisionAlternativeCard key={altIndex} alternative={alt} />
                  ))}
                </div>
              </div>
            )}

            {/* Additional Info */}
            <div className="grid grid-cols-2 gap-3 pt-2 border-t">
              {decision.impact && (
                <div>
                  <h4 className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">
                    Impact
                  </h4>
                  <p className="text-xs text-foreground">{decision.impact}</p>
                </div>
              )}

              {decision.reversible !== undefined && (
                <div>
                  <h4 className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">
                    Reversible
                  </h4>
                  <Badge variant="outline" className={cn(
                    'text-[10px] px-1 py-0',
                    decision.reversible
                      ? 'text-green-500 bg-green-500/10 border-green-500/30'
                      : 'text-red-500 bg-red-500/10 border-red-500/30'
                  )}>
                    {decision.reversible ? 'Yes' : 'No'}
                  </Badge>
                </div>
              )}

              {decision.dependencies && decision.dependencies.length > 0 && (
                <div className="col-span-2">
                  <h4 className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">
                    Dependencies
                  </h4>
                  <div className="flex flex-wrap gap-1">
                    {decision.dependencies.map((dep, depIndex) => (
                      <Badge key={depIndex} variant="outline" className="text-[10px] px-1 py-0">
                        {dep}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
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

// Decision Alternative Card Component
function DecisionAlternativeCard({ alternative }: { alternative: Alternative }) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="rounded border bg-card/30 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-2.5 py-1.5 flex items-start gap-1.5 hover:bg-accent/50 transition-colors text-left"
      >
        <div className="flex-shrink-0 mt-0.5">
          {isExpanded ? (
            <ChevronDown className="h-3 w-3 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3 w-3 text-muted-foreground" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <X className="h-3 w-3 text-red-500 flex-shrink-0" />
            <span className="text-xs font-medium text-foreground line-clamp-1">
              {alternative.description}
            </span>
          </div>
          {!isExpanded && (
            <p className="text-[10px] text-muted-foreground line-clamp-1">
              {alternative.rejected_reason}
            </p>
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="px-2.5 pb-2 space-y-1.5 border-t">
          <div className="pt-1.5">
            <h5 className="text-[10px] font-semibold text-muted-foreground uppercase mb-0.5">
              Why Considered
            </h5>
            <p className="text-[10px] text-foreground">{alternative.reasoning}</p>
          </div>

          <div>
            <h5 className="text-[10px] font-semibold text-muted-foreground uppercase mb-0.5">
              Why Rejected
            </h5>
            <p className="text-[10px] text-foreground">{alternative.rejected_reason}</p>
          </div>

          {alternative.confidence_impact && (
            <div>
              <h5 className="text-[10px] font-semibold text-muted-foreground uppercase mb-0.5">
                Confidence Impact
              </h5>
              <p className="text-[10px] text-foreground">{alternative.confidence_impact}</p>
            </div>
          )}

          {alternative.tradeoffs && alternative.tradeoffs.length > 0 && (
            <div>
              <h5 className="text-[10px] font-semibold text-muted-foreground uppercase mb-0.5">
                Tradeoffs
              </h5>
              <ul className="space-y-0.5">
                {alternative.tradeoffs.map((tradeoff, idx) => (
                  <li key={idx} className="text-[10px] text-foreground flex gap-1">
                    <span className="text-muted-foreground">•</span>
                    <span>{tradeoff}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
