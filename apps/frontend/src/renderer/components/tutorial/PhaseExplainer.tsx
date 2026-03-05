import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '../../lib/utils';
import { PhaseProgressIndicator } from '../PhaseProgressIndicator';
import type { ExecutionPhase, Subtask, TaskLogs } from '../../../shared/types';

interface PhaseExplainerProps {
  phase: ExecutionPhase;
  subtasks: Subtask[];
  explanationText: string;
  phaseLogs?: TaskLogs | null;
  phaseProgress?: number;
  isStuck?: boolean;
  isRunning?: boolean;
  className?: string;
}

/**
 * PhaseExplainer Component
 *
 * Displays what the current phase is doing with real-time progress
 * and explanatory text. Used in the tutorial wizard to help users
 * understand what's happening during each phase of the autonomous build.
 *
 * Features:
 * - Shows PhaseProgressIndicator for visual feedback
 * - Displays phase-specific explanation text
 * - Adapts to different execution phases (planning, coding, QA, etc.)
 * - Supports stuck/interrupted states
 *
 * @example
 * ```tsx
 * <PhaseExplainer
 *   phase="coding"
 *   subtasks={subtasks}
 *   explanationText="The agent is implementing the login form..."
 *   isRunning={true}
 * />
 * ```
 */
export const PhaseExplainer = memo(function PhaseExplainer({
  phase,
  subtasks,
  explanationText,
  phaseLogs,
  phaseProgress,
  isStuck = false,
  isRunning = false,
  className,
}: PhaseExplainerProps) {
  const { t } = useTranslation('tutorial');

  return (
    <div className={cn('space-y-4', className)}>
      {/* Progress indicator */}
      <PhaseProgressIndicator
        phase={phase}
        subtasks={subtasks}
        phaseLogs={phaseLogs}
        phaseProgress={phaseProgress}
        isStuck={isStuck}
        isRunning={isRunning}
      />

      {/* Explanation text */}
      {explanationText && (
        <div className="rounded-lg border bg-card p-4">
          <p className="text-sm text-muted-foreground leading-relaxed">
            {explanationText}
          </p>
        </div>
      )}
    </div>
  );
});
