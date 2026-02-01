/**
 * ChangelogSkeleton Component
 *
 * Skeleton loading state for changelog entries with two layout variants:
 *
 * 1. TaskCard (grid layout):
 *    - Checkbox
 *    - Title
 *    - Description (2 lines)
 *    - Badges (Has Specs)
 *    - Completion date
 *
 * 2. CommitCard (list layout):
 *    - Commit icon
 *    - Commit message
 *    - Hash
 *    - Author, date, file count
 */

interface ChangelogSkeletonProps {
  count?: number;
  variant?: 'task' | 'commit';
}

export function ChangelogSkeleton({ count = 5, variant = 'task' }: ChangelogSkeletonProps) {
  if (variant === 'task') {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: count }).map((_, index) => (
          <div
            key={`skeleton-task-${index}`}
            className="flex flex-col rounded-lg border border-border p-4 animate-pulse"
          >
            <div className="flex items-start gap-3">
              {/* Checkbox */}
              <div className="h-4 w-4 mt-1 bg-muted rounded shrink-0" />

              <div className="flex-1 min-w-0">
                {/* Title */}
                <div className="h-4 w-3/4 bg-muted rounded" />

                {/* Description (2 lines) */}
                <div className="mt-2 space-y-1">
                  <div className="h-3 w-full bg-muted rounded" />
                  <div className="h-3 w-2/3 bg-muted rounded" />
                </div>

                {/* Badges and date */}
                <div className="flex items-center gap-2 mt-3">
                  {/* Badge */}
                  <div className="h-5 w-20 bg-muted rounded" />
                  {/* Date */}
                  <div className="h-3 w-16 bg-muted rounded" />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Commit variant
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={`skeleton-commit-${index}`}
          className="flex items-start gap-3 rounded-lg border border-border p-3 bg-background animate-pulse"
        >
          {/* Commit icon */}
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted shrink-0" />

          <div className="flex-1 min-w-0">
            {/* Commit message and hash */}
            <div className="flex items-start justify-between gap-2">
              {/* Message */}
              <div className="h-4 w-2/3 bg-muted rounded" />
              {/* Hash */}
              <div className="h-3 w-16 bg-muted rounded shrink-0" />
            </div>

            {/* Metadata: author, date, file count */}
            <div className="flex items-center gap-3 mt-2">
              {/* Author */}
              <div className="h-3 w-20 bg-muted rounded" />
              {/* Date */}
              <div className="h-3 w-16 bg-muted rounded" />
              {/* File count */}
              <div className="h-3 w-12 bg-muted rounded" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
