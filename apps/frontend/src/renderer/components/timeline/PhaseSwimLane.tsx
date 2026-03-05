/**
 * PhaseSwimLane component for timeline visualization
 *
 * Renders individual phase swim lanes with color-coded backgrounds,
 * phase labels, progress indicators, and click handling.
 */

import { memo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';
import { cn } from '../../lib/utils';
import type {
  TimelinePhase,
  TimelineColorScheme,
  PhaseLayout,
  PhaseProgressData,
  TimelineAgentType,
} from './types';
import { DEFAULT_TIMELINE_COLORS } from './types';

interface PhaseSwimLaneProps {
  /** Phase data to render */
  phase: TimelinePhase;
  /** Calculated layout for positioning */
  layout: PhaseLayout;
  /** Current progress data for this phase */
  progress?: PhaseProgressData;
  /** Color scheme override */
  colors?: TimelineColorScheme;
  /** Whether animations are enabled */
  enableAnimations?: boolean;
  /** Click handler for phase interaction */
  onClick?: (phase: TimelinePhase) => void;
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
 * Get phase status for color coding
 */
function getPhaseStatus(
  phase: TimelinePhase,
  progress?: PhaseProgressData
): 'active' | 'complete' | 'pending' | 'error' {
  if (progress?.status === 'failed') return 'error';
  if (progress?.status === 'complete') return 'complete';
  if (progress?.status && progress.status !== 'idle') return 'active';
  return 'pending';
}

/**
 * PhaseSwimLane renders a horizontal swim lane for a timeline phase
 * Shows phase name, agent-based color coding, and progress information
 */
export const PhaseSwimLane = memo(function PhaseSwimLane({
  phase,
  layout,
  progress,
  colors = DEFAULT_TIMELINE_COLORS,
  enableAnimations = true,
  onClick,
  className,
}: PhaseSwimLaneProps) {
  const { t } = useTranslation('tasks');

  // Get color scheme based on agent type and status
  const colorKey = getAgentColorKey(phase.agentType);
  const phaseStatus = getPhaseStatus(phase, progress);
  const colorScheme = phaseStatus === 'error' ? colors.error : colors[colorKey];

  // Handle click event
  const handleClick = useCallback(() => {
    onClick?.(phase);
  }, [phase, onClick]);

  // Calculate progress percentage
  const progressPercent = progress?.progress ?? 0;

  // Determine if phase is currently active
  const isActive = phaseStatus === 'active';

  return (
    <motion.div
      className={cn(
        'absolute border-b border-border/50',
        'hover:border-border/80 transition-colors',
        onClick && 'cursor-pointer',
        className
      )}
      style={{
        top: layout.y,
        left: 0,
        width: '100%',
        height: layout.height,
      }}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{
        delay: enableAnimations ? phase.displayIndex * 0.05 : 0,
        duration: 0.3,
      }}
      onClick={handleClick}
      role="button"
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          handleClick();
        }
      }}
      aria-label={`${phase.name} phase`}
    >
      {/* Background with agent-based color */}
      <div
        className={cn(
          'absolute inset-0 rounded transition-colors',
          colorScheme.background
        )}
      />

      {/* Progress bar overlay (shows completion percentage) */}
      {progress && progressPercent > 0 && (
        <motion.div
          className={cn(
            'absolute left-0 top-0 bottom-0 opacity-20',
            colorScheme.primary
          )}
          initial={{ width: 0 }}
          animate={{ width: `${progressPercent}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      )}

      {/* Left border indicator (shows active/inactive state) */}
      <div
        className={cn(
          'absolute left-0 top-0 bottom-0 w-1 rounded-l',
          isActive && colorScheme.primary,
          !isActive && 'bg-border'
        )}
      />

      {/* Phase label and metadata */}
      <div
        className={cn(
          'absolute left-3 top-1/2 -translate-y-1/2',
          'flex items-center gap-2'
        )}
      >
        {/* Phase number badge */}
        <div
          className={cn(
            'flex items-center justify-center',
            'h-5 w-5 rounded text-[10px] font-semibold',
            'bg-background/80 backdrop-blur-sm',
            colorScheme.text,
            'border border-border/50'
          )}
        >
          {phase.phase}
        </div>

        {/* Phase name */}
        <span
          className={cn(
            'text-xs font-medium',
            colorScheme.text
          )}
        >
          {phase.name}
        </span>

        {/* Active indicator (pulsing dot) */}
        {isActive && enableAnimations && (
          <motion.div
            className={cn('h-2 w-2 rounded-full', colorScheme.primary)}
            animate={{
              scale: [1, 1.3, 1],
              opacity: [1, 0.6, 1],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}

        {/* Subtask progress info */}
        {progress && progress.totalCount > 0 && (
          <span className="text-[10px] text-muted-foreground ml-1">
            {progress.completedCount}/{progress.totalCount}
          </span>
        )}
      </div>

      {/* Phase type badge (agent type) */}
      <div
        className={cn(
          'absolute right-3 top-1/2 -translate-y-1/2',
          'px-2 py-0.5 rounded text-[9px] font-medium uppercase tracking-wide',
          'bg-background/60 backdrop-blur-sm border border-border/50',
          colorScheme.text
        )}
      >
        {phase.agentType || 'unknown'}
      </div>

      {/* Hover effect overlay */}
      <motion.div
        className="absolute inset-0 bg-foreground/5 opacity-0 hover:opacity-100 transition-opacity rounded pointer-events-none"
        whileHover={{ opacity: 0.05 }}
      />
    </motion.div>
  );
});
