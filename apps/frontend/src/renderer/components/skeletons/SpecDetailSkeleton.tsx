import { Card } from '../ui/card';

interface SpecDetailSkeletonProps {
  /** Number of phase skeletons to render */
  phaseCount?: number;
  /** Whether to show description placeholder */
  showDescription?: boolean;
}

/**
 * Skeleton loader for SpecDetail/TaskOverview implementation plan
 * Matches the structure: section header, phases, subtasks, metadata
 */
export function SpecDetailSkeleton({ phaseCount = 3, showDescription = true }: SpecDetailSkeletonProps) {
  return (
    <div className="p-5 space-y-5 animate-pulse">
      {/* Section Header */}
      <div className="mb-4">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 bg-muted rounded" />
          <div className="h-5 w-48 bg-muted rounded" />
        </div>
      </div>

      {/* Optional Description */}
      {showDescription && (
        <div className="mb-4">
          <div className="h-4 w-full bg-muted rounded" />
          <div className="h-4 w-2/3 bg-muted rounded mt-2" />
        </div>
      )}

      {/* Phases */}
      <div className="space-y-2">
        {Array.from({ length: phaseCount }).map((_, phaseIndex) => (
          <Card
            key={phaseIndex}
            className="border border-border rounded-lg"
          >
            {/* Phase Header */}
            <div className="px-4 py-3 flex items-center gap-3">
              {/* Chevron placeholder */}
              <div className="h-4 w-4 bg-muted rounded shrink-0" />

              {/* Status icon placeholder */}
              <div className="h-4 w-4 bg-muted rounded-full shrink-0" />

              {/* Phase title and badge */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <div className="h-4 w-40 bg-muted rounded" />
                  <div className="h-5 w-20 bg-muted rounded-md" />
                </div>

                {/* Progress text */}
                <div className="h-3 w-24 bg-muted rounded" />
              </div>
            </div>

            {/* Subtasks (simulate expanded phase) */}
            <div className="px-4 pb-3 space-y-2">
              {/* Separator */}
              <div className="h-px w-full bg-border" />

              {/* Subtask items */}
              {Array.from({ length: 3 + (phaseIndex % 2) }).map((_, subtaskIndex) => (
                <div
                  key={subtaskIndex}
                  className="flex items-start gap-3 p-2"
                >
                  {/* Status badge placeholder */}
                  <div className="h-5 w-16 bg-muted rounded-md shrink-0 mt-0.5" />

                  {/* Subtask content */}
                  <div className="flex-1 min-w-0 space-y-1">
                    {/* Subtask description */}
                    <div className="h-4 w-full bg-muted rounded" />
                    {/* Verification text (optional) */}
                    {subtaskIndex % 2 === 0 && (
                      <div className="h-3 w-32 bg-muted rounded" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      {/* QA Report Section (skeleton) */}
      <div className="space-y-3 pt-4">
        {/* QA Report header */}
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 bg-muted rounded" />
          <div className="h-5 w-24 bg-muted rounded" />
        </div>

        {/* QA content lines */}
        <div className="space-y-2 pl-5">
          <div className="h-4 w-full bg-muted rounded" />
          <div className="h-4 w-5/6 bg-muted rounded" />
          <div className="h-4 w-4/6 bg-muted rounded" />
          <div className="h-4 w-3/4 bg-muted rounded" />
        </div>
      </div>
    </div>
  );
}
