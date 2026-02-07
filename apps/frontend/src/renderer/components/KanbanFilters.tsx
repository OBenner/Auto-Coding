/**
 * KanbanFilters - Filter controls for the Kanban board
 *
 * Provides search functionality and sorting options for filtering tasks
 * displayed on the Kanban board. Filter state is persisted per project
 * in localStorage via the kanban-settings-store.
 *
 * Features:
 * - Search input for filtering tasks by title/description
 * - Sort mode dropdown (manual, priority, created, updated)
 * - Real-time filter application
 * - Filter state persistence per project
 *
 * @example
 * ```tsx
 * <KanbanFilters projectId={projectId} />
 * ```
 */
import { useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X, ArrowUpIcon, ArrowDownIcon } from 'lucide-react';
import { Input } from './ui/input';
import { Button } from './ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from './ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from './ui/tooltip';
import { useKanbanSettingsStore } from '../stores/kanban-settings-store';
import type { SortMode } from '../stores/kanban-settings-store';

/**
 * Props for the KanbanFilters component
 */
interface KanbanFiltersProps {
  /** Project ID for loading/saving filter preferences */
  projectId: string | undefined;
}

export function KanbanFilters({ projectId }: KanbanFiltersProps) {
  const { t } = useTranslation('kanban');

  // Kanban settings store for filter state
  const filters = useKanbanSettingsStore((state) => state.filters);
  const initializePreferences = useKanbanSettingsStore((state) => state.initializePreferences);
  const setSearchQuery = useKanbanSettingsStore((state) => state.setSearchQuery);
  const setSortBy = useKanbanSettingsStore((state) => state.setSortBy);
  const setSortOrder = useKanbanSettingsStore((state) => state.setSortOrder);
  const loadFilters = useKanbanSettingsStore((state) => state.loadFilters);
  const saveFilters = useKanbanSettingsStore((state) => state.saveFilters);
  const resetFilters = useKanbanSettingsStore((state) => state.resetFilters);

  // Initialize filters on mount
  useEffect(() => {
    initializePreferences();
  }, [initializePreferences]);

  // Load filters when project changes
  useEffect(() => {
    if (projectId) {
      loadFilters(projectId);
    }
  }, [projectId, loadFilters]);

  // Handle search input change
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const query = event.target.value;
    setSearchQuery(query);

    // Save filters to localStorage after a short debounce
    if (projectId) {
      // Use setTimeout to debounce saves during rapid typing
      const timeoutId = setTimeout(() => {
        saveFilters(projectId);
      }, 300);

      // Cleanup function to clear timeout
      return () => clearTimeout(timeoutId);
    }
  };

  // Handle sort mode change
  const handleSortChange = (value: SortMode) => {
    setSortBy(value);

    // Save filters to localStorage immediately
    if (projectId) {
      saveFilters(projectId);
    }
  };

  // Calculate active filter count
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters?.searchQuery && filters.searchQuery.trim() !== '') {
      count++;
    }
    if (filters?.sortBy && filters.sortBy !== 'manual') {
      count++;
    }
    return count;
  }, [filters?.searchQuery, filters?.sortBy]);

  // Handle clear filters
  const handleClearFilters = () => {
    if (!projectId) return;

    // Reset filters to defaults
    resetFilters(projectId);

    // Save the cleared state to localStorage
    saveFilters(projectId);
  };

  return (
    <div className="flex items-center gap-3 px-6 py-3 border-b border-border/50">
      {/* Search input */}
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        <Input
          type="text"
          placeholder={t('filters.searchPlaceholder')}
          value={filters?.searchQuery ?? ''}
          onChange={handleSearchChange}
          className="pl-9 h-9"
          aria-label={t('filters.searchAriaLabel')}
        />
      </div>

      {/* Sort mode dropdown */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground whitespace-nowrap">
          {t('filters.sortByLabel')}:
        </span>
        <Select
          value={filters?.sortBy ?? 'manual'}
          onValueChange={handleSortChange}
        >
          <SelectTrigger className="w-[180px] h-9">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="manual">
              {t('filters.sortModes.manual')}
            </SelectItem>
            <SelectItem value="priority">
              {t('filters.sortModes.priority')}
            </SelectItem>
            <SelectItem value="created">
              {t('filters.sortModes.created')}
            </SelectItem>
            <SelectItem value="updated">
              {t('filters.sortModes.updated')}
            </SelectItem>
          </SelectContent>
        </Select>

        {/* Sort order toggle (only show when not manual) */}
        {filters?.sortBy !== 'manual' && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  const newOrder = filters?.sortOrder === 'asc' ? 'desc' : 'asc';
                  setSortOrder(newOrder);
                  if (projectId) {
                    saveFilters(projectId);
                  }
                }}
                className="h-9 w-9 p-0"
                aria-label={t('filters.sortOrderToggle')}
              >
                {filters?.sortOrder === 'asc' ? (
                  <ArrowUpIcon className="h-4 w-4" />
                ) : (
                  <ArrowDownIcon className="h-4 w-4" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {filters?.sortOrder === 'asc'
                ? t('filters.sortOrder.ascending')
                : t('filters.sortOrder.descending')
              }
            </TooltipContent>
          </Tooltip>
        )}
      </div>

      {/* Clear Filters button with active filter count badge */}
      {activeFilterCount > 0 && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClearFilters}
          className="h-9 gap-2"
          aria-label={t('filters.clearFiltersAriaLabel')}
        >
          <X className="h-4 w-4" />
          <span>{t('filters.clearFilters')}</span>
          <span className="inline-flex items-center justify-center h-5 min-w-5 px-1.5 text-xs font-medium rounded-full bg-primary/10 text-primary">
            {activeFilterCount}
          </span>
        </Button>
      )}
    </div>
  );
}
