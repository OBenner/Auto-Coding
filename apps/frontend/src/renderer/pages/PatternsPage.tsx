import { useState, useEffect } from 'react';
import { Code, RefreshCw, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/button';
import { PatternReview } from '../components/PatternReview';
import { debugLog } from '../../shared/utils/debug-logger';
import type { PatternSuggestion } from '../../shared/types';

interface PatternsPageProps {
  /** Project ID to load patterns for */
  projectId: string;
}

/**
 * PatternsPage Component
 *
 * Displays all learned patterns organized by category.
 * Allows users to review, approve, and deprecate patterns.
 */
export function PatternsPage({ projectId }: PatternsPageProps) {
  const { t } = useTranslation(['patterns', 'common']);
  const [patterns, setPatterns] = useState<PatternSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load patterns for the project
  const loadPatterns = async () => {
    if (!projectId) {
      setPatterns([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      debugLog('Loading patterns for project:', projectId);

      // TODO: Implement IPC call to fetch patterns from backend
      // For now, using mock data to verify the UI renders correctly
      const mockPatterns: PatternSuggestion[] = [
        {
          pattern: 'Use async/await for all asynchronous operations',
          category: 'api-design',
          confidence: 0.92,
          reasoning: 'Consistent async pattern used across 15 API endpoint handlers',
          score: 0.95,
          spec_id: 'spec-001',
          timestamp: new Date().toISOString()
        },
        {
          pattern: 'Wrap external API calls in try-catch with Sentry logging',
          category: 'error-handling',
          confidence: 0.88,
          reasoning: 'Error handling pattern found in 12 service files',
          score: 0.90,
          spec_id: 'spec-002',
          timestamp: new Date().toISOString()
        },
        {
          pattern: 'Use Zustand stores for global state management',
          category: 'state-management',
          confidence: 0.95,
          reasoning: 'Zustand pattern used consistently in 8 store files',
          score: 0.98,
          spec_id: 'spec-003',
          timestamp: new Date().toISOString()
        }
      ];

      setPatterns(mockPatterns);
      debugLog('Loaded patterns:', mockPatterns.length);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load patterns';
      debugLog('Error loading patterns:', message);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  // Load patterns on mount and when project changes
  useEffect(() => {
    loadPatterns();
  }, [projectId]);

  // Handle pattern approval
  const handleApprove = async (pattern: PatternSuggestion) => {
    debugLog('Approving pattern:', pattern);

    try {
      // TODO: Implement IPC call to mark pattern as team standard
      // await window.electronAPI.approvePattern(projectId, pattern);

      // For now, just log the action
      debugLog('Pattern approved as team standard');

      // Reload patterns to reflect updated confidence
      await loadPatterns();
    } catch (err) {
      debugLog('Error approving pattern:', err);
    }
  };

  // Handle pattern deprecation
  const handleDeprecate = async (pattern: PatternSuggestion) => {
    debugLog('Deprecating pattern:', pattern);

    try {
      // TODO: Implement IPC call to mark pattern as deprecated
      // await window.electronAPI.deprecatePattern(projectId, pattern);

      // For now, just log the action
      debugLog('Pattern marked as deprecated');

      // Reload patterns to reflect updated confidence
      await loadPatterns();
    } catch (err) {
      debugLog('Error deprecating pattern:', err);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Code className="h-6 w-6" />
            <div>
              <h1 className="text-2xl font-semibold">{t('patterns:page.title')}</h1>
              <p className="text-sm text-muted-foreground">
                {t('patterns:page.description')}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={loadPatterns}
            disabled={loading}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            {t('patterns:page.refresh')}
          </Button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="mx-6 mt-4">
          <div className="flex items-center gap-3 rounded-md border border-destructive/50 bg-destructive/10 p-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-destructive">{t('patterns:page.errorTitle')}</p>
              <p className="text-xs text-destructive/80">{error}</p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadPatterns}
              className="gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              {t('patterns:page.retry')}
            </Button>
          </div>
        </div>
      )}

      {/* Pattern Review */}
      <div className="flex-1 overflow-hidden">
        <PatternReview
          projectId={projectId}
          patterns={patterns}
          loading={loading}
          onApprove={handleApprove}
          onDeprecate={handleDeprecate}
        />
      </div>
    </div>
  );
}
