import { useCallback } from 'react';
import { Calendar, RefreshCw } from 'lucide-react';
import { Button } from '../ui/button';

export type TimeRange = 'all' | '7d' | '30d' | '90d';

const TIME_RANGE_DAYS: Record<TimeRange, number> = {
  '7d': 7,
  '30d': 30,
  '90d': 90,
  all: 365,
};

export function getDaysFromTimeRange(timeRange: TimeRange): number {
  return TIME_RANGE_DAYS[timeRange] ?? 30;
}

export function useTimeRangeDays(timeRange: TimeRange) {
  return useCallback(() => getDaysFromTimeRange(timeRange), [timeRange]);
}

interface TimeRangeFilterProps {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}

export function TimeRangeFilter({ value, onChange }: TimeRangeFilterProps) {
  return (
    <div className="flex items-center gap-1 border border-border rounded-md p-1">
      {(['7d', '30d', '90d'] as const).map((range) => (
        <Button
          key={range}
          variant={value === range ? 'default' : 'ghost'}
          size="sm"
          onClick={() => onChange(range)}
          className="h-7"
        >
          <Calendar className="h-3 w-3 mr-1" />
          {range}
        </Button>
      ))}
      <Button
        variant={value === 'all' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onChange('all')}
        className="h-7"
      >
        All
      </Button>
    </div>
  );
}

interface RefreshButtonProps {
  onClick: () => void;
  isRefreshing: boolean;
}

export function RefreshButton({ onClick, isRefreshing }: RefreshButtonProps) {
  return (
    <Button variant="outline" size="sm" onClick={onClick} disabled={isRefreshing}>
      <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
      Refresh
    </Button>
  );
}

interface LoadingSpinnerProps {
  message: string;
}

export function LoadingSpinner({ message }: LoadingSpinnerProps) {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent" />
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>
    </div>
  );
}

interface EmptyStateProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}

export function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center h-[60vh] text-center">
      <Icon className="h-16 w-16 text-muted-foreground/50 mb-4" />
      <h2 className="text-xl font-semibold text-foreground mb-2">{title}</h2>
      <p className="text-sm text-muted-foreground max-w-md">{description}</p>
    </div>
  );
}
