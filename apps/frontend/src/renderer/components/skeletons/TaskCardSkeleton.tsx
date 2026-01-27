import { Card, CardContent } from '../ui/card';

interface TaskCardSkeletonProps {
  /** Number of skeleton cards to render */
  count?: number;
  /** Whether to show selection checkbox placeholder */
  showCheckbox?: boolean;
}

/**
 * Skeleton loader for TaskCard component
 * Matches the structure: badges, title, progress indicator, metadata
 */
export function TaskCardSkeleton({ count = 1, showCheckbox = false }: TaskCardSkeletonProps) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <Card
          key={index}
          className="group cursor-default transition-all duration-200 hover:shadow-lg hover:border-primary/30 animate-pulse"
        >
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              {/* Optional checkbox placeholder */}
              {showCheckbox && (
                <div className="flex-shrink-0 pt-1">
                  <div className="h-4 w-4 bg-muted rounded border-2 border-muted-foreground/20" />
                </div>
              )}

              {/* Main content area */}
              <div className="flex-1 min-w-0 space-y-3">
                {/* Top badges section */}
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="h-5 w-16 bg-muted rounded-md" />
                  <div className="h-5 w-20 bg-muted rounded-md" />
                  <div className="h-5 w-14 bg-muted rounded-md" />
                  <div className="h-5 w-18 bg-muted rounded-md" />
                </div>

                {/* Title */}
                <div className="space-y-2">
                  <div className="h-5 w-3/4 bg-muted rounded" />
                </div>

                {/* Description (optional, shown ~70% of the time) */}
                {index % 3 !== 0 && (
                  <div className="h-4 w-full bg-muted rounded" />
                )}

                {/* Progress indicator section (mimics PhaseProgressIndicator) */}
                <div className="space-y-1.5 pt-1">
                  {/* Progress label and percentage */}
                  <div className="flex items-center justify-between">
                    <div className="h-3 w-16 bg-muted rounded" />
                    <div className="h-3 w-8 bg-muted rounded" />
                  </div>

                  {/* Progress bar */}
                  <div className="relative h-1.5 w-full bg-border rounded-full overflow-hidden">
                    <div className="absolute inset-0 h-full w-1/2 bg-muted rounded-full" />
                  </div>

                  {/* Subtask dots indicator */}
                  <div className="flex gap-1.5 mt-2">
                    {Array.from({ length: 6 }).map((_, dotIndex) => (
                      <div
                        key={dotIndex}
                        className="h-2 w-2 bg-muted rounded-full"
                      />
                    ))}
                    <div className="h-2 w-4 bg-muted rounded-full" />
                  </div>

                  {/* Phase steps indicator */}
                  <div className="flex items-center gap-1 mt-2">
                    <div className="h-4 w-12 bg-muted rounded" />
                    <div className="h-px w-2 bg-muted" />
                    <div className="h-4 w-12 bg-muted rounded" />
                    <div className="h-px w-2 bg-muted" />
                    <div className="h-4 w-8 bg-muted rounded" />
                  </div>
                </div>

                {/* Footer metadata */}
                <div className="flex items-center gap-3 text-xs text-muted-foreground pt-1">
                  <div className="h-3 w-20 bg-muted rounded" />
                  <div className="h-3 w-16 bg-muted rounded" />
                  {/* PR link placeholder (shown ~30% of the time) */}
                  {index % 3 === 0 && (
                    <div className="h-3 w-24 bg-muted rounded" />
                  )}
                </div>
              </div>

              {/* Action buttons area */}
              <div className="flex-shrink-0 flex items-start gap-2">
                {/* Start/Stop button placeholder */}
                <div className="h-8 w-8 bg-muted rounded-md" />
                {/* Menu button placeholder */}
                <div className="h-8 w-8 bg-muted rounded-md" />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </>
  );
}
