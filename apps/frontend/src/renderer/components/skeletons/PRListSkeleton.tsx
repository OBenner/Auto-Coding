/**
 * PRListSkeleton Component
 *
 * Skeleton loading state for GitHub PR list matching the structure from PRList.tsx:
 * - PR icon
 * - PR number
 * - Branch badge
 * - Status flow dots (3 dots)
 * - PR title
 * - Metadata (author, date, file changes)
 */
export function PRListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="divide-y divide-border">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="w-full p-4 animate-pulse"
        >
          <div className="flex items-start gap-3">
            {/* PR Icon */}
            <div className="h-5 w-5 mt-0.5 bg-muted rounded shrink-0" />

            <div className="flex-1 min-w-0">
              {/* First row: PR number, branch badge, status dots */}
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                {/* PR number */}
                <div className="h-4 w-12 bg-muted rounded" />

                {/* Branch badge */}
                <div className="h-5 w-24 bg-muted rounded" />

                {/* Status dots (3 dots) */}
                <div className="flex items-center gap-1">
                  <div className="h-2 w-2 bg-muted rounded-full" />
                  <div className="h-2 w-2 bg-muted rounded-full" />
                  <div className="h-2 w-2 bg-muted rounded-full" />
                </div>
              </div>

              {/* PR title */}
              <div className="h-4 w-3/4 bg-muted rounded" />

              {/* Metadata row: author, date, file changes */}
              <div className="flex items-center gap-3 mt-2">
                {/* Author */}
                <div className="flex items-center gap-1">
                  <div className="h-3 w-3 bg-muted rounded" />
                  <div className="h-3 w-20 bg-muted rounded" />
                </div>

                {/* Date */}
                <div className="flex items-center gap-1">
                  <div className="h-3 w-3 bg-muted rounded" />
                  <div className="h-3 w-16 bg-muted rounded" />
                </div>

                {/* File changes */}
                <div className="flex items-center gap-1">
                  <div className="h-3 w-3 bg-muted rounded" />
                  <div className="h-3 w-12 bg-muted rounded" />
                </div>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
