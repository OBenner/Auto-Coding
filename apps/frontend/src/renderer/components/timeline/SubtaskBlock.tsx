/**
 * SubtaskBlock component for timeline visualization
 *
 * Renders individual subtasks as colored blocks within phase swim lanes.
 * Displays status-based styling, time tracking, and supports click interactions.
 */

import { memo, useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';
import { Clock, AlertCircle, CheckCircle2, Loader2, Hourglass, TrendingUp, TrendingDown, ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';
import type {
  TimelineSubtask,
  TimelineColorScheme,
  SubtaskLayout,
  TimelineAgentType,
} from './types';
import { DEFAULT_TIMELINE_COLORS } from './types';

interface SubtaskBlockProps {
  /** Subtask data to render */
  subtask: TimelineSubtask;
  /** Calculated layout for positioning */
  layout: SubtaskLayout;
  /** Current subtask ID (for highlighting) */
  currentSubtaskId?: string;
  /** Color scheme override */
  colors?: TimelineColorScheme;
  /** Agent type for this subtask (inherited from phase) */
  agentType?: TimelineAgentType;
  /** Whether animations are enabled */
  enableAnimations?: boolean;
  /** Whether to show time estimates */
  showTimeEstimates?: boolean;
  /** Click handler for subtask interaction */
  onClick?: (subtask: TimelineSubtask) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Map agent type to color scheme key
 */
function getAgentColorKey(agentType?: TimelineAgentType): keyof TimelineColorScheme {
  if (!agentType) return 'inactive';
  if (agentType === 'planner') return 'planner';
  if (agentType === 'coder') return 'coder';
  if (agentType === 'qa') return 'qa';
  return 'inactive';
}

/**
 * Get subtask status for color coding
 */
function getSubtaskStatus(subtask: TimelineSubtask): 'pending' | 'in_progress' | 'completed' | 'failed' {
  if (subtask.status === 'completed') return 'completed';
  if (subtask.status === 'failed') return 'failed';
  if (subtask.status === 'in_progress') return 'in_progress';
  return 'pending';
}

/**
 * Format time in seconds to human-readable format
 */
function formatTime(seconds?: number): string {
  if (!seconds || seconds === 0) return '--';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
}

/**
 * Calculate time variance for visual indicators
 * Returns 'over' if actual > estimate, 'under' if actual < estimate, null otherwise
 */
function getTimeVariance(
  actual?: number,
  estimated?: number
): 'over' | 'under' | null {
  if (actual === undefined || estimated === undefined || estimated === 0) {
    return null;
  }
  const ratio = actual / estimated;
  // Consider over if 10% or more over estimate
  if (ratio > 1.1) return 'over';
  // Consider under if 10% or more under estimate
  if (ratio < 0.9) return 'under';
  return null;
}

/**
 * Get CSS class for time variance color
 */
function getTimeColorClass(timeVariance: 'over' | 'under' | null): string {
  if (timeVariance === 'over') return 'text-destructive';
  if (timeVariance === 'under') return 'text-green-600 dark:text-green-400';
  return 'text-muted-foreground';
}

/**
 * SubtaskBlock renders a colored block for a timeline subtask
 * Shows status-based colors, time tracking, and click interaction
 */
export const SubtaskBlock = memo(function SubtaskBlock({
  subtask,
  layout,
  currentSubtaskId,
  colors = DEFAULT_TIMELINE_COLORS,
  agentType,
  enableAnimations = true,
  showTimeEstimates = true,
  onClick,
  className,
}: SubtaskBlockProps) {
  const { t } = useTranslation('timeline');

  // Expanded state for detail panel
  const [expanded, setExpanded] = useState(false);

  // Get color scheme based on agent type and status
  const colorKey = getAgentColorKey(agentType);
  const subtaskStatus = getSubtaskStatus(subtask);
  const isCurrent = subtask.id === currentSubtaskId;

  // Select color scheme based on status
  let colorScheme = colors[colorKey];
  if (subtaskStatus === 'failed') {
    colorScheme = colors.error;
  } else if (subtaskStatus === 'completed') {
    colorScheme = colors[colorKey]; // Use agent color for completed
  } else if (subtaskStatus === 'pending') {
    colorScheme = colors.inactive;
  }

  // Handle click event - toggle expanded state
  const handleClick = useCallback((_e?: React.MouseEvent | React.KeyboardEvent) => {
    // Distinguish click from drag - only expand if block is rendered
    if (layout.width > 0) {
      setExpanded(prev => !prev);
      onClick?.(subtask);
    }
  }, [subtask, onClick, layout.width]);

  // Calculate time variance for visual indicator
  const timeVariance = useMemo(() => {
    return getTimeVariance(subtask.actualTime, subtask.estimatedTime);
  }, [subtask.actualTime, subtask.estimatedTime]);

  // Memoize time display
  const timeDisplay = useMemo(() => {
    if (!showTimeEstimates) return null;

    const estimated = formatTime(subtask.estimatedTime);
    const actual = formatTime(subtask.actualTime);

    // Show actual time if available, otherwise show estimate
    const displayTime = subtask.actualTime !== undefined ? actual : estimated;
    const showBoth = subtask.actualTime !== undefined && subtask.estimatedTime !== undefined;

    // Determine color based on time variance
    const timeColorClass = getTimeColorClass(timeVariance);

    return (
      <div className="flex items-center gap-1.5 text-[10px]">
        <Clock className={cn('h-2.5 w-2.5', timeColorClass)} />
        {showBoth ? (
          <span className="flex items-center gap-1 text-[9px]">
            <span className={cn('font-medium', timeColorClass)}>{actual}</span>
            <span className="text-muted-foreground/60">/</span>
            <span className="text-muted-foreground/80">{estimated}</span>
            {timeVariance && (
              <span className={cn('flex items-center', timeColorClass)}>
                {timeVariance === 'over' ? (
                  <TrendingUp className="h-2.5 w-2.5" />
                ) : (
                  <TrendingDown className="h-2.5 w-2.5" />
                )}
              </span>
            )}
          </span>
        ) : (
          <span className={timeColorClass}>{displayTime}</span>
        )}
      </div>
    );
  }, [showTimeEstimates, subtask.estimatedTime, subtask.actualTime, timeVariance]);

  // Status icon
  const statusIcon = useMemo(() => {
    switch (subtaskStatus) {
      case 'completed':
        return <CheckCircle2 className={cn('h-3 w-3', colorScheme.text)} />;
      case 'failed':
        return <AlertCircle className={cn('h-3 w-3', colors.error.text)} />;
      case 'in_progress':
        return <Loader2 className={cn('h-3 w-3 animate-spin', colorScheme.text)} />;
      case 'pending':
      default:
        return <Hourglass className={cn('h-3 w-3', colors.inactive.text)} />;
    }
  }, [subtaskStatus, colorScheme, colors]);

  // Subtask description (truncated)
  const truncatedDescription = useMemo(() => {
    if (!subtask.description) return null;
    const maxLen = 60;
    return subtask.description.length > maxLen
      ? `${subtask.description.slice(0, maxLen)}...`
      : subtask.description;
  }, [subtask.description]);

  // Detail panel content (shown when expanded)
  const detailPanel = expanded && (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="mt-2 p-3 bg-background/50 rounded border border-border text-xs space-y-2"
    >
      {/* Full description */}
      <div>
        <div className="font-semibold text-foreground mb-1">{t('detail.description')}</div>
        <div className="text-muted-foreground">{subtask.description}</div>
      </div>

      {/* Files to create */}
      {subtask.filesToCreate && subtask.filesToCreate.length > 0 && (
        <div>
          <div className="font-semibold text-foreground mb-1">{t('detail.filesToCreate')}</div>
          <ul className="list-disc list-inside text-muted-foreground">
            {subtask.filesToCreate.map((file) => (
              <li key={file} className="font-mono text-[10px]">{file}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Files to modify */}
      {subtask.filesToModify && subtask.filesToModify.length > 0 && (
        <div>
          <div className="font-semibold text-foreground mb-1">{t('detail.filesToModify')}</div>
          <ul className="list-disc list-inside text-muted-foreground">
            {subtask.filesToModify.map((file) => (
              <li key={file} className="font-mono text-[10px]">{file}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Verification steps */}
      {subtask.verification && (
        <div>
          <div className="font-semibold text-foreground mb-1">{t('detail.verification')}</div>
          <div className="text-muted-foreground font-mono text-[10px]">
            {subtask.verification.run || subtask.verification.scenario || subtask.verification.type}
          </div>
        </div>
      )}

      {/* Notes */}
      {subtask.notes && (
        <div>
          <div className="font-semibold text-foreground mb-1">{t('detail.notes')}</div>
          <div className="text-muted-foreground">{subtask.notes}</div>
        </div>
      )}
    </motion.div>
  );

  // Expand icon (chevron that rotates)
  const expandIcon = (
    <motion.div
      animate={{ rotate: expanded ? 180 : 0 }}
      transition={{ duration: 0.2 }}
      className="ml-auto"
    >
      <ChevronDown className="h-3 w-3" />
    </motion.div>
  );

  return (
    <motion.div
      className={cn(
        'absolute rounded border shadow-sm',
        expanded ? 'overflow-visible' : 'overflow-hidden',
        'hover:shadow-md transition-shadow',
        onClick && 'cursor-pointer',
        isCurrent && 'ring-2 ring-ring ring-offset-1',
        className
      )}
      style={{
        left: layout.x,
        top: layout.y,
        width: layout.width,
        minHeight: layout.height,
        zIndex: expanded ? layout.zIndex + 10 : layout.zIndex,
      }}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{
        delay: enableAnimations ? subtask.displayIndex * 0.03 : 0,
        duration: 0.2,
      }}
      onClick={handleClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-label={t('subtaskAriaLabel', {
        description: subtask.description || subtask.id,
        status: t(`status.${subtaskStatus}`),
      })}
    >
      {/* Background with status-based color */}
      <div
        className={cn(
          'absolute inset-0 transition-colors',
          subtaskStatus === 'completed' ? colorScheme.background : 'bg-background',
          subtaskStatus === 'in_progress' && colorScheme.background,
          subtaskStatus === 'failed' && colors.error.background,
          subtaskStatus === 'pending' && colors.inactive.background
        )}
      />

      {/* Status indicator bar (left side) */}
      <div
        className={cn(
          'absolute left-0 top-0 bottom-0 w-1',
          subtaskStatus === 'completed' && colorScheme.primary,
          subtaskStatus === 'in_progress' && colorScheme.primary,
          subtaskStatus === 'failed' && colors.error.primary,
          subtaskStatus === 'pending' && colors.inactive.primary
        )}
      />

      {/* Content container */}
      <div className="relative h-full flex flex-col p-2">
        {/* Header with status icon and subtask ID */}
        <div className="flex items-center gap-1.5 mb-1">
          {statusIcon}
          <span
            className={cn(
              'text-[9px] font-medium uppercase tracking-wide',
              colorScheme.text
            )}
          >
            {subtask.id}
          </span>

          {/* Expand/collapse icon */}
          {expandIcon}

          {/* Current indicator (pulsing dot) */}
          {isCurrent && enableAnimations && (
            <motion.div
              className={cn('h-1.5 w-1.5 rounded-full', colorScheme.primary)}
              animate={{
                scale: [1, 1.5, 1],
                opacity: [1, 0.5, 1],
              }}
              transition={{
                duration: 1.2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          )}
        </div>

        {/* Subtask description (truncated) */}
        {truncatedDescription && (
          <div className="flex-1 min-w-0 mb-1">
            <p className="text-[10px] text-foreground line-clamp-2 leading-tight">
              {truncatedDescription}
            </p>
          </div>
        )}

        {/* Footer with time display */}
        {timeDisplay && (
          <div className="mt-auto pt-1 border-t border-border/50">
            {timeDisplay}
          </div>
        )}

        {/* Detail panel (expandable) */}
        {detailPanel}
      </div>

      {/* Hover effect overlay */}
      <motion.div
        className="absolute inset-0 bg-foreground/5 opacity-0 hover:opacity-100 transition-opacity pointer-events-none"
        whileHover={{ opacity: 0.08 }}
      />

      {/* Status badge overlay (for failed state) */}
      {subtaskStatus === 'failed' && (
        <div className="absolute top-1 right-1">
          <div className={cn(
            'h-2 w-2 rounded-full',
            colors.error.primary
          )} />
        </div>
      )}
    </motion.div>
  );
});
