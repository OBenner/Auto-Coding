export function IssueListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={`skeleton-issue-${index}`}
          className="p-3 rounded-lg border border-transparent animate-pulse"
        >
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <div className="h-5 w-16 bg-muted rounded" />
                <div className="h-4 w-8 bg-muted rounded" />
              </div>
              <div className="h-4 w-3/4 bg-muted rounded" />
              <div className="flex items-center gap-3 mt-2">
                <div className="flex items-center gap-1">
                  <div className="h-3 w-3 bg-muted rounded" />
                  <div className="h-3 w-20 bg-muted rounded" />
                </div>
                <div className="flex items-center gap-1">
                  <div className="h-3 w-3 bg-muted rounded" />
                  <div className="h-3 w-6 bg-muted rounded" />
                </div>
                <div className="flex items-center gap-1">
                  <div className="h-3 w-3 bg-muted rounded" />
                  <div className="h-3 w-4 bg-muted rounded" />
                </div>
              </div>
            </div>
            <div className="h-8 w-8 bg-muted rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}
