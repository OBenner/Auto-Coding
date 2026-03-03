import {
  AlertTriangle,
  FileCode,
  GitMerge,
  TrendingUp,
  Clock,
  AlertCircle
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { ScrollArea } from '../ui/scroll-area';
import type { ConflictPattern, MergeConflictSeverity } from '../../../shared/types/merge-analytics';

interface ConflictPatternsViewProps {
  patterns: ConflictPattern[];
  isLoading?: boolean;
  limit?: number;
}

// Severity color mapping
const SEVERITY_COLORS: Record<MergeConflictSeverity, string> = {
  none: 'text-muted-foreground',
  low: 'text-blue-500',
  medium: 'text-warning',
  high: 'text-orange-500',
  critical: 'text-destructive'
};

const SEVERITY_BG_COLORS: Record<MergeConflictSeverity, string> = {
  none: 'bg-muted/50',
  low: 'bg-blue-500/10 border-blue-500/30',
  medium: 'bg-warning/10 border-warning/30',
  high: 'bg-orange-500/10 border-orange-500/30',
  critical: 'bg-destructive/10 border-destructive/30'
};

interface ConflictPatternItemProps {
  pattern: ConflictPattern;
}

function ConflictPatternItem({ pattern }: ConflictPatternItemProps) {
  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return 'Unknown';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <div className={`rounded-lg border p-4 ${SEVERITY_BG_COLORS[pattern.severity]}`}>
      {/* Header: File Path and Severity */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <FileCode className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="text-sm font-mono text-foreground truncate" title={pattern.file_path}>
            {pattern.file_path}
          </span>
        </div>
        <Badge variant="outline" className={SEVERITY_COLORS[pattern.severity]}>
          {pattern.severity}
        </Badge>
      </div>

      {/* Location */}
      <div className="mb-3">
        <h4 className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
          <AlertCircle className="h-3 w-3" />
          Location
        </h4>
        <p className="text-sm text-foreground font-mono bg-background/50 px-2 py-1 rounded">
          {pattern.location}
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="text-center p-2 rounded bg-background/30">
          <div className={`text-lg font-semibold ${SEVERITY_COLORS[pattern.severity]}`}>
            {pattern.occurrence_count}
          </div>
          <div className="text-xs text-muted-foreground">Occurrences</div>
        </div>
        <div className="text-center p-2 rounded bg-background/30">
          <div className="text-lg font-semibold text-accent">
            {pattern.tasks_involved.length}
          </div>
          <div className="text-xs text-muted-foreground">Tasks</div>
        </div>
      </div>

      {/* Tasks Involved */}
      {pattern.tasks_involved.length > 0 && (
        <div className="mb-3">
          <h4 className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
            <GitMerge className="h-3 w-3" />
            Tasks Involved
          </h4>
          <div className="flex flex-wrap gap-1">
            {pattern.tasks_involved.map((task, i) => (
              /* biome-ignore lint/suspicious/noArrayIndexKey: String items without unique IDs */
              <Badge key={i} variant="secondary" className="text-xs">
                {task}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Last Seen */}
      {pattern.last_seen && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          Last seen: {formatDate(pattern.last_seen)}
        </div>
      )}
    </div>
  );
}

export function ConflictPatternsView({ patterns, isLoading = false, limit = 10 }: ConflictPatternsViewProps) {
  // Sort patterns by occurrence count (descending) and limit
  const displayPatterns = patterns
    .slice()
    .sort((a, b) => b.occurrence_count - a.occurrence_count)
    .slice(0, limit);

  const hasData = displayPatterns.length > 0;

  return (
    <Card className="bg-muted/30 border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-warning" />
            Conflict Patterns
          </CardTitle>
          {hasData && (
            <Badge variant="outline" className="text-xs">
              Top {displayPatterns.length}
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Recurring conflicts detected across merge operations
        </p>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Clock className="h-5 w-5 animate-spin mr-2" />
            Loading conflict patterns...
          </div>
        ) : !hasData ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <TrendingUp className="h-12 w-12 text-success/50 mb-3" />
            <p className="text-sm text-muted-foreground">No conflict patterns detected</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              This is good! Your merges are conflict-free.
            </p>
          </div>
        ) : (
          <ScrollArea className="h-[500px] pr-4">
            <div className="space-y-3">
              {displayPatterns.map((pattern, index) => (
                <ConflictPatternItem key={`${pattern.file_path}-${pattern.location}-${index}`} pattern={pattern} />
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
