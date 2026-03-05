/**
 * SearchBar Component
 *
 * Provides search input for filtering agent inspector logs by text content.
 * Searches through thought blocks and tool calls in real-time.
 *
 * Features:
 * - Real-time text search with debouncing
 * - Clear button when search is active
 * - Keyboard shortcuts (Cmd/Ctrl+K to focus)
 * - Result count display
 * - Accessible input with proper ARIA labels
 *
 * @example
 * ```tsx
 * <SearchBar
 *   searchQuery={searchQuery}
 *   onSearchChange={setSearchQuery}
 *   resultCount={filteredItems.length}
 *   totalCount={allItems.length}
 * />
 * ```
 */

import { useCallback, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, X } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';

/**
 * Props for the SearchBar component
 */
interface SearchBarProps {
  /** Current search query value */
  searchQuery: string;
  /** Callback when search query changes */
  onSearchChange: (query: string) => void;
  /** Number of results matching the search */
  resultCount?: number;
  /** Total number of items before filtering */
  totalCount?: number;
  /** Placeholder text for the search input */
  placeholder?: string;
  /** Optional CSS class name */
  className?: string;
  /** Whether to auto-focus the input on mount */
  autoFocus?: boolean;
}

/**
 * SearchBar component for filtering agent logs
 */
export function SearchBar({
  searchQuery,
  onSearchChange,
  resultCount,
  totalCount,
  placeholder,
  className,
  autoFocus = false,
}: SearchBarProps) {
  const { t } = useTranslation(['agent-inspector', 'common']);
  const inputRef = useRef<HTMLInputElement>(null);

  // Handle keyboard shortcut (Cmd/Ctrl+K) to focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Auto-focus input on mount if requested
  useEffect(() => {
    if (autoFocus) {
      inputRef.current?.focus();
    }
  }, [autoFocus]);

  // Handle input change
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onSearchChange(e.target.value);
    },
    [onSearchChange]
  );

  // Handle clear button
  const handleClear = useCallback(() => {
    onSearchChange('');
    inputRef.current?.focus();
  }, [onSearchChange]);

  // Handle keyboard events
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Escape') {
        handleClear();
      }
    },
    [handleClear]
  );

  // Determine if search is active
  const isSearchActive = searchQuery.length > 0;

  // Format result count message
  const resultMessage =
    resultCount !== undefined && totalCount !== undefined
      ? isSearchActive
        ? t('agent-inspector:searchResults', {
            count: resultCount,
            total: totalCount,
            defaultValue: `${resultCount} of ${totalCount}`,
          })
        : t('agent-inspector:totalItems', {
            count: totalCount,
            defaultValue: `${totalCount} items`,
          })
      : null;

  return (
    <div className={cn('border-b border-border/50 bg-background/95 backdrop-blur', className)}>
      <div className="flex items-center gap-3 px-6 py-3">
        {/* Search Icon */}
        <div className="shrink-0">
          <Search className="h-4 w-4 text-muted-foreground" />
        </div>

        {/* Search Input */}
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={searchQuery}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={
              placeholder ||
              t('agent-inspector:searchPlaceholder', 'Search thoughts and tool calls...')
            }
            className={cn(
              'w-full bg-transparent text-sm py-1.5',
              'placeholder:text-muted-foreground',
              'focus:outline-none',
              'disabled:cursor-not-allowed disabled:opacity-50'
            )}
            aria-label={t('agent-inspector:searchLabel', 'Search agent logs')}
          />
        </div>

        {/* Result Count */}
        {resultMessage && (
          <div className="shrink-0 text-xs text-muted-foreground hidden sm:block">
            {resultMessage}
          </div>
        )}

        {/* Clear Button */}
        {isSearchActive && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClear}
            className="h-8 w-8 p-0 shrink-0"
            aria-label={t('common:actions.clear', 'Clear search')}
          >
            <X className="h-4 w-4" />
          </Button>
        )}

        {/* Keyboard Shortcut Hint (only shown when not searching) */}
        {!isSearchActive && (
          <div className="shrink-0 hidden md:flex items-center gap-1 text-xs text-muted-foreground border border-border rounded px-2 py-1">
            <kbd className="font-sans">⌘K</kbd>
          </div>
        )}
      </div>
    </div>
  );
}
