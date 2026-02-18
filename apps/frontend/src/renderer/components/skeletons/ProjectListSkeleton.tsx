/**
 * ProjectListSkeleton
 *
 * Skeleton loading state for project list in WelcomeScreen.
 * Matches the structure of project list items with folder icon, name, path, and time.
 */

export function ProjectListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="p-2">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className="w-full flex items-center gap-3 rounded-lg px-3 py-3 animate-pulse"
        >
          {/* Folder icon placeholder */}
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted shrink-0" />

          {/* Content area */}
          <div className="flex-1 min-w-0 space-y-2">
            {/* Project name and badge */}
            <div className="flex items-center gap-2">
              <div className="h-4 w-32 bg-muted rounded" />
              {/* Show badge on some items (like the real list) */}
              {index % 3 === 0 && (
                <div className="h-4 w-16 bg-muted rounded-full" />
              )}
            </div>
            {/* Project path */}
            <div className="h-3 w-48 bg-muted rounded" />
          </div>

          {/* Time placeholder */}
          <div className="h-3 w-16 bg-muted rounded shrink-0" />
        </div>
      ))}
    </div>
  );
}
