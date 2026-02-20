import { Skeleton } from './ui/skeleton';
import { Card, CardContent, CardHeader } from './ui/card';

/**
 * AppLoading component
 * Shows a loading skeleton while the app is initializing
 * Matches the structure of the main app layout
 */
export function AppLoading() {

  return (
    <div className="min-h-screen bg-background">
      {/* Loading message */}
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardHeader>
            <div className="space-y-2">
              <Skeleton className="h-6 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-2/3" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
