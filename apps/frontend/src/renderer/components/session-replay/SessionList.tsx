/**
 * SessionList Component
 *
 * Lists sessions with search and filter functionality.
 * Displays sessions with metadata and allows filtering by status and search query.
 */

import { useState, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, CheckCircle2, Loader2, X, Filter } from 'lucide-react';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Separator } from '../ui/separator';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
} from '../ui/dropdown-menu';
import { cn } from '../lib/utils';
import { SessionCard } from './SessionCard';
import type {
  SessionMetadata,
  SessionFilterState,
  SessionStatusFilter,
} from '../../../shared/types';

interface SessionListProps {
  /** Array of sessions to display */
  sessions: SessionMetadata[];
  /** Whether sessions are being loaded */
  isLoading?: boolean;
  /** Callback when a session is clicked */
  onSessionClick?: (session: SessionMetadata) => void;
  /** Callback when filters change */
  onFiltersChange?: (filters: SessionFilterState) => void;
}

/**
 * Status options for filtering
 */
const STATUS_OPTIONS: Array<{
  value: SessionStatusFilter;
  labelKey: string;
  icon: typeof CheckCircle2 | typeof Loader2;
  color: string;
  bgColor: string;
}> = [
  {
    value: 'completed',
    labelKey: 'sessionList.statusCompleted',
    icon: CheckCircle2,
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/20'
  },
  {
    value: 'in-progress',
    labelKey: 'sessionList.statusInProgress',
    icon: Loader2,
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/20'
  },
];

/**
 * FilterDropdown component for status selection
 */
function FilterDropdown<T extends string>({
  title,
  icon: Icon,
  items,
  selected,
  onChange,
  renderItem,
}: {
  title: string;
  icon: typeof Filter;
  items: T[];
  selected: T[];
  onChange: (selected: T[]) => void;
  renderItem?: (item: T) => React.ReactNode;
}) {
  const { t } = useTranslation('session-replay');

  const toggleItem = useCallback((item: T) => {
    if (selected.includes(item)) {
      onChange(selected.filter((s) => s !== item));
    } else {
      onChange([...selected, item]);
    }
  }, [selected, onChange]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn(
            "h-8 justify-start border-dashed bg-transparent",
            selected.length > 0 && "border-solid bg-accent/50"
          )}
        >
          <Icon className="mr-2 h-4 w-4 text-muted-foreground" />
          <span>{title}</span>
          {selected.length > 0 && (
            <Badge variant="secondary" className="ml-2 rounded-sm px-1 font-normal">
              {selected.length}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[200px] p-1">
        {items.map((item) => {
          const isSelected = selected.includes(item);
          return (
            <DropdownMenuItem
              key={item}
              onClick={() => toggleItem(item)}
              className={cn(
                "cursor-pointer",
                isSelected && "bg-accent/50"
              )}
            >
              {renderItem ? renderItem(item) : item}
            </DropdownMenuItem>
          );
        })}
        {selected.length > 0 && (
          <>
            <Separator className="my-1" />
            <DropdownMenuItem
              onClick={() => onChange([])}
              className="cursor-pointer text-destructive focus:text-destructive"
            >
              {t('sessionList.clearFilters')}
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/**
 * Main SessionList component
 */
export function SessionList({
  sessions,
  isLoading = false,
  onSessionClick,
  onFiltersChange,
}: SessionListProps) {
  const { t } = useTranslation('session-replay');

  // Filter state
  const [filters, setFilters] = useState<SessionFilterState>({
    searchQuery: '',
    status: [],
  });

  // Update filters when they change
  const updateFilters = useCallback((newFilters: SessionFilterState) => {
    setFilters(newFilters);
    onFiltersChange?.(newFilters);
  }, [onFiltersChange]);

  // Handle search query change
  const handleSearchChange = useCallback((query: string) => {
    updateFilters({ ...filters, searchQuery: query });
  }, [filters, updateFilters]);

  // Handle status filter change
  const handleStatusChange = useCallback((statuses: SessionStatusFilter[]) => {
    updateFilters({ ...filters, status: statuses });
  }, [filters, updateFilters]);

  // Clear all filters
  const handleClearFilters = useCallback(() => {
    updateFilters({ searchQuery: '', status: [] });
  }, [updateFilters]);

  // Filter sessions based on current filters
  const filteredSessions = useMemo(() => {
    return sessions.filter((session) => {
      // Filter by search query
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const matchesSessionId = session.session_id.toLowerCase().includes(query);
        const matchesSubtasks = session.subtasks.some((st) =>
          st.toLowerCase().includes(query)
        );
        if (!matchesSessionId && !matchesSubtasks) {
          return false;
        }
      }

      // Filter by status
      if (filters.status.length > 0) {
        const isCompleted = session.completed_at !== null;
        const matchesStatus =
          (isCompleted && filters.status.includes('completed')) ||
          (!isCompleted && filters.status.includes('in-progress'));
        if (!matchesStatus) {
          return false;
        }
      }

      return true;
    });
  }, [sessions, filters]);

  // Check if there are active filters
  const hasActiveFilters = useMemo(() => {
    return filters.searchQuery.length > 0 || filters.status.length > 0;
  }, [filters]);

  // Get status option by value
  const getStatusOption = (value: SessionStatusFilter) =>
    STATUS_OPTIONS.find((opt) => opt.value === value);

  return (
    <div className="flex flex-col h-full">
      {/* Filter Bar */}
      <div className="px-4 py-2 border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center gap-2 h-9">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={t('sessionList.searchPlaceholder')}
              value={filters.searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="h-8 pl-9 bg-background/50 focus:bg-background transition-colors"
            />
            {filters.searchQuery && (
              <button
                type="button"
                onClick={() => handleSearchChange('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={t('sessionList.clearSearch')}
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>

          <Separator orientation="vertical" className="h-5 mx-1" />

          {/* Status Filter */}
          <FilterDropdown
            title={t('sessionList.allStatuses')}
            icon={Filter}
            items={STATUS_OPTIONS.map((opt) => opt.value)}
            selected={filters.status}
            onChange={handleStatusChange}
            renderItem={(status) => {
              const option = getStatusOption(status);
              if (!option) return null;
              const Icon = option.icon;
              return (
                <div className="flex items-center gap-2">
                  <div className={cn("p-1 rounded-full", option.bgColor)}>
                    <Icon className={cn("h-3 w-3", option.color)} />
                  </div>
                  <span className="text-sm">{t(option.labelKey)}</span>
                </div>
              );
            }}
          />

          {/* Reset All */}
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearFilters}
              className="h-8 px-2 lg:px-3 text-muted-foreground hover:text-foreground ml-auto"
            >
              <span className="hidden lg:inline mr-2">{t('sessionList.reset')}</span>
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Session List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
        {isLoading ? (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin mr-2" />
            <span>{t('sessionList.loading')}</span>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="text-muted-foreground mb-2">
              {hasActiveFilters
                ? t('sessionList.noResultsFound')
                : t('sessionList.noSessions')}
            </div>
            {!hasActiveFilters && (
              <div className="text-sm text-muted-foreground">
                {t('sessionList.noSessionsDescription')}
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredSessions.map((session) => (
              <SessionCard
                key={session.session_id}
                session={session}
                onClick={onSessionClick ? () => onSessionClick(session) : undefined}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
