import { useState, useEffect } from 'react';
import { Search, RefreshCw, AlertCircle, Bookmark } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/button';
import { SearchBar } from '../components/code-search/SearchBar';
import { SearchResults, type SearchResultData } from '../components/code-search/SearchResults';
import { SavedSearches, type SavedSearch } from '../components/code-search/SavedSearches';
import { debugLog } from '../../shared/utils/debug-logger';

interface CodeSearchPageProps {
  /** Project ID to perform code search for */
  projectId: string;
}

/**
 * CodeSearchPage Component
 *
 * Provides semantic code search functionality across the project codebase.
 * Allows users to search for code patterns, functions, classes, and more using natural language queries.
 * Integrates with Graphiti memory for semantic understanding.
 */
export function CodeSearchPage({ projectId }: CodeSearchPageProps) {
  const { t } = useTranslation(['code-search', 'common']);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResultData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchType, setSearchType] = useState<'unified' | 'purpose' | 'patterns' | 'callers' | 'callees'>('unified');
  const [showSavedSearches, setShowSavedSearches] = useState(false);

  // Perform code search
  const performSearch = async (query: string) => {
    if (!query.trim()) {
      setSearchResults(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      debugLog('Performing code search for project:', projectId, 'query:', query, 'type:', searchType);

      if (!window.electronAPI?.search.searchCode) {
        throw new Error('electronAPI.search.searchCode is not available');
      }

      const result = await window.electronAPI.search.searchCode(
        projectId,
        query,
        searchType,
        { limit: 50 }
      );

      if (result.success && result.data) {
        setSearchResults(result.data as SearchResultData);
        debugLog('Search results received:', result.data);
      } else {
        throw new Error(result.error || 'Failed to perform code search');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to perform code search';
      debugLog('Error during code search:', message);
      setError(message);
      setSearchResults(null);
    } finally {
      setLoading(false);
    }
  };

  // Handle search submission
  const handleSearch = () => {
    performSearch(searchQuery);
  };

  // Handle search query change
  const handleSearchChange = (query: string) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setSearchResults(null);
    }
  };

  // Handle saved search execution
  const handleRunSavedSearch = async (search: SavedSearch) => {
    debugLog('Running saved search:', search);
    setSearchQuery(search.query);
    setSearchType(search.search_type as typeof searchType);
    await performSearch(search.query);
    setShowSavedSearches(false);
  };

  // Load initial state on mount
  useEffect(() => {
    debugLog('Code search page mounted for project:', projectId);
  }, [projectId]);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Search className="h-6 w-6" />
            <div>
              <h1 className="text-2xl font-semibold">{t('code-search:page.title')}</h1>
              <p className="text-sm text-muted-foreground">
                {t('code-search:page.description')}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={showSavedSearches ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowSavedSearches(!showSavedSearches)}
              className="gap-2"
            >
              <Bookmark className="h-4 w-4" />
              {showSavedSearches ? t('code-search:page.hideSaved') : t('code-search:page.showSaved')}
            </Button>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="mx-6 mt-4">
          <div className="flex items-center gap-3 rounded-md border border-destructive/50 bg-destructive/10 p-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-destructive">{t('code-search:page.errorTitle')}</p>
              <p className="text-xs text-destructive/80">{error}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => performSearch(searchQuery)}
              className="gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              {t('code-search:page.retry')}
            </Button>
          </div>
        </div>
      )}

      {/* Main Content */}
      {showSavedSearches ? (
        <div className="flex-1 overflow-hidden">
          <SavedSearches
            projectId={projectId}
            onRunSearch={handleRunSavedSearch}
          />
        </div>
      ) : (
        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Search Bar */}
          <div className="border-b border-border px-6 py-4">
            <div className="flex gap-3">
              <div className="flex-1">
                <SearchBar
                  searchQuery={searchQuery}
                  onSearchChange={handleSearchChange}
                  placeholder={t('code-search:page.placeholder')}
                />
              </div>
              <Button
                onClick={handleSearch}
                disabled={loading || !searchQuery.trim()}
                className="gap-2"
              >
                <Search className="h-4 w-4" />
                {t('code-search:page.search')}
              </Button>
            </div>

            {/* Search Type Selector */}
            <div className="flex items-center gap-2 mt-3">
              <span className="text-xs text-muted-foreground">
                {t('code-search:page.searchType')}:
              </span>
              <div className="flex gap-1">
                {(['unified', 'purpose', 'patterns', 'callers', 'callees'] as const).map((type) => (
                  <Button
                    key={type}
                    variant={searchType === type ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setSearchType(type)}
                    className="text-xs"
                  >
                    {t(`code-search:searchTypes.${type}`)}
                  </Button>
                ))}
              </div>
            </div>
          </div>

          {/* Search Results */}
          <div className="flex-1 overflow-hidden p-6">
            <SearchResults
              results={searchResults}
              isLoading={loading}
              searchType={searchType}
              searchQuery={searchQuery}
            />
          </div>
        </div>
      )}
    </div>
  );
}
