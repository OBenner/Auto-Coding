import { Check } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface TutorialPhase {
  id: string;
  label: string;
  completed: boolean;
}

interface ProgressTimelineProps {
  currentPhase: number;
  phases: TutorialPhase[];
}

/**
 * Vertical timeline component for tutorial progress.
 * Displays phases (Spec → Plan → Code → QA) with visual states
 * for completed, current, and upcoming phases.
 */
export function ProgressTimeline({ currentPhase, phases }: ProgressTimelineProps) {
  return (
    <div className="flex flex-col items-start">
      {phases.map((phase, index) => {
        const isCompleted = phase.completed;
        const isCurrent = index === currentPhase;
        const isUpcoming = index > currentPhase;

        return (
          <div key={phase.id} className="flex items-start">
            <div className="flex flex-col items-center">
              {/* Phase indicator circle */}
              <div
                className={cn(
                  'flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-semibold transition-all duration-200',
                  isCompleted && 'border-primary bg-primary text-primary-foreground',
                  isCurrent && !isCompleted && 'border-primary bg-background text-primary',
                  isUpcoming && 'border-muted-foreground/40 bg-background text-muted-foreground'
                )}
              >
                {isCompleted ? (
                  <Check className="h-5 w-5" />
                ) : (
                  <span>{index + 1}</span>
                )}
              </div>

              {/* Connecting line (not after last phase) */}
              {index < phases.length - 1 && (
                <div
                  className={cn(
                    'my-2 h-12 w-0.5 transition-colors duration-200',
                    phase.completed ? 'bg-primary' : 'bg-muted-foreground/40'
                  )}
                />
              )}
            </div>

            {/* Phase label to the right of circle */}
            <div className="ml-4 flex items-center h-10">
              <span
                className={cn(
                  'text-sm font-medium',
                  isCompleted && 'text-primary',
                  isCurrent && !isCompleted && 'text-primary',
                  isUpcoming && 'text-muted-foreground'
                )}
              >
                {phase.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
