import { Card, CardContent, CardHeader } from '../ui/card';

interface PatternSuggestionsSkeletonProps {
  /** Number of pattern cards to render */
  count?: number;
  /** Whether to show header section */
  showHeader?: boolean;
}

/**
 * Skeleton loader for PatternSuggestions in CreateSpecView
 * Matches the structure: header with badges, pattern cards with category badges,
 * confidence levels, pattern text, action buttons, and expandable details
 */
export function PatternSuggestionsSkeleton({
  count = 3,
  showHeader = true
}: PatternSuggestionsSkeletonProps) {
  return (
    <div className="space-y-4 animate-pulse">
      {/* Header Section */}
      {showHeader && (
        <div className="flex items-start justify-between">
          <div className="flex-1 space-y-2">
            {/* Title with icon */}
            <div className="flex items-center gap-2">
              <div className="h-5 w-5 bg-muted rounded" />
              <div className="h-6 w-48 bg-muted rounded" />
            </div>
            {/* Subtitle */}
            <div className="h-4 w-80 bg-muted rounded" />
          </div>
          {/* Summary badges */}
          <div className="flex items-center gap-2">
            <div className="h-6 w-24 bg-muted rounded-md" />
            <div className="h-6 w-20 bg-muted rounded-md" />
            <div className="h-6 w-22 bg-muted rounded-md" />
          </div>
        </div>
      )}

      {/* Pattern Cards */}
      <div className="space-y-3">
        {Array.from({ length: count }).map((_, index) => (
          <Card key={index} className="border">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-3">
                {/* Main content area */}
                <div className="flex-1 space-y-2">
                  {/* Category Badge and Confidence Level */}
                  <div className="flex items-center gap-2">
                    <div className="h-5 w-32 bg-muted rounded-md" />
                    <div className="h-4 w-20 bg-muted rounded" />
                  </div>

                  {/* Pattern Text Lines */}
                  <div className="space-y-1.5">
                    <div className="h-4 w-full bg-muted rounded" />
                    <div className="h-4 w-5/6 bg-muted rounded" />
                    {index % 2 === 0 && (
                      <div className="h-4 w-4/6 bg-muted rounded" />
                    )}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-1">
                  <div className="h-8 w-8 bg-muted rounded-md" />
                  <div className="h-8 w-8 bg-muted rounded-md" />
                  <div className="h-8 w-8 bg-muted rounded-md" />
                </div>
              </div>
            </CardHeader>

            <CardContent className="pt-0">
              {/* Expandable Details Section */}
              <div className="mt-3 space-y-2">
                {/* "Show details" button placeholder */}
                <div className="h-4 w-24 bg-muted rounded" />

                {/* Details content (simulate expanded state ~50% of the time) */}
                {index % 2 === 0 && (
                  <div className="mt-3 space-y-2 text-xs">
                    {/* Reasoning line */}
                    <div className="flex items-start gap-2">
                      <div className="h-3 w-16 bg-muted rounded" />
                      <div className="h-3 w-full bg-muted rounded" />
                    </div>

                    {/* Metadata row */}
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <div className="h-3 w-14 bg-muted rounded" />
                        <div className="h-3 w-8 bg-muted rounded" />
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="h-3 w-10 bg-muted rounded" />
                        <div className="h-3 w-16 bg-muted rounded" />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
