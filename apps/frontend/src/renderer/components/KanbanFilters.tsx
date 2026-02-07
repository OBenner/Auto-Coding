/**
 * KanbanFilters - Filter controls for the Kanban board
 *
 * Provides search functionality and sorting options for filtering tasks
 * displayed on the Kanban board. Filter state is persisted per project
 * in localStorage via the kanban-settings-store.
 *
 * Features:
 * - Search input for filtering tasks by title/description
 * - Real-time filter application
 * - Filter state persistence per project
 *
 * @example
 * ```tsx
 * <KanbanFilters projectId={projectId} />
 * ```
 */
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Search } from 'lucide-react';
import { Input } from './ui/input';
import { useKanbanSettingsStore } from '../stores/kanban-settings-store';

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
  const loadFilters = useKanbanSettingsStore((state) => state.loadFilters);
  const saveFilters = useKanbanSettingsStore((state) => state.saveFilters);

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
    </div>
  );
}
