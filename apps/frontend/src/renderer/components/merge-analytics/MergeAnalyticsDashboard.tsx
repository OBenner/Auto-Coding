import { useState, useEffect, useCallback } from 'react';
import { Download, Loader2, RefreshCw, BarChart3, FileText } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { useToast } from '../../hooks/use-toast';
import { MergeAnalyticsSummaryCard } from './MergeAnalyticsSummaryCard';
import { MergeHistoryList } from './MergeHistoryList';
import { ConflictPatternsView } from './ConflictPatternsView';
import type {
  MergeAnalytics,
  MergeOperationRecord,
  ConflictPattern,
  MergeAnalyticsExportOptions
} from '../../../shared/types/merge-analytics';

interface MergeAnalyticsDashboardProps {
  projectId: string;
}

export function MergeAnalyticsDashboard({ projectId }: MergeAnalyticsDashboardProps) {
  const { toast } = useToast();

  // State
  const [analytics, setAnalytics] = useState<MergeAnalytics | null>(null);
  const [operations, setOperations] = useState<MergeOperationRecord[]>([]);
  const [patterns, setPatterns] = useState<ConflictPattern[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [selectedOperationId, setSelectedOperationId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<'all' | 'success' | 'failed'>('all');

  // Load all analytics data
  const loadAnalyticsData = useCallback(async (showRefreshToast = false) => {
    try {
      const loadingState = showRefreshToast ? setIsRefreshing : setIsLoading;
      loadingState(true);

      // Load summary analytics
      const summaryResult = await window.electronAPI.getMergeSummary(projectId);
      if (summaryResult.success && summaryResult.data) {
        setAnalytics(summaryResult.data);
      } else {
        console.error('Failed to load merge summary:', summaryResult.error);
      }

      // Load operation history
      const historyResult = await window.electronAPI.getMergeHistory(projectId);
      if (historyResult.success && historyResult.data) {
        setOperations(historyResult.data);
      } else {
        console.error('Failed to load merge history:', historyResult.error);
      }

      // Load conflict patterns
      const patternsResult = await window.electronAPI.getConflictPatterns(projectId, 10);
      if (patternsResult.success && patternsResult.data) {
        setPatterns(patternsResult.data);
      } else {
        console.error('Failed to load conflict patterns:', patternsResult.error);
      }

      if (showRefreshToast) {
        toast({
          title: 'Analytics Refreshed',
          description: 'Merge analytics data has been updated.',
        });
      }
    } catch (error) {
      console.error('Error loading analytics data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load merge analytics data.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [projectId, toast]);

  // Initial load
  useEffect(() => {
    loadAnalyticsData();
  }, [loadAnalyticsData]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadAnalyticsData(true);
  }, [loadAnalyticsData]);

  // Handle export
  const handleExport = useCallback(async (format: 'json' | 'csv') => {
    try {
      setIsExporting(true);

      const options: MergeAnalyticsExportOptions = {
        format,
        filter: {
          success_only: statusFilter === 'success' ? true : undefined,
          failed_only: statusFilter === 'failed' ? true : undefined,
        },
      };

      const result = await window.electronAPI.exportMergeAnalytics(projectId, options);

      if (result.success && result.data) {
        toast({
          title: 'Export Successful',
          description: `Analytics exported to ${result.data.path}`,
        });
      } else {
        toast({
          title: 'Export Failed',
          description: result.error || 'Failed to export analytics',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Error exporting analytics:', error);
      toast({
        title: 'Export Error',
        description: 'An error occurred while exporting analytics.',
        variant: 'destructive',
      });
    } finally {
      setIsExporting(false);
    }
  }, [projectId, statusFilter, toast]);

  // Handle operation selection
  const handleSelectOperation = useCallback((operation: MergeOperationRecord) => {
    setSelectedOperationId(operation.operation_id);
  }, []);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading merge analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BarChart3 className="h-6 w-6 text-accent" />
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Merge Analytics</h1>
              <p className="text-sm text-muted-foreground">
                Track and analyze merge operations across your project
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('json')}
              disabled={isExporting}
            >
              <FileText className="h-4 w-4 mr-2" />
              Export JSON
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('csv')}
              disabled={isExporting}
            >
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {/* Summary Card */}
          <MergeAnalyticsSummaryCard
            analytics={analytics}
            isLoading={isRefreshing}
          />

          {/* Two-column layout for History and Patterns */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Merge History */}
            <div className="bg-muted/30 border border-border/50 rounded-lg overflow-hidden">
              <MergeHistoryList
                operations={operations}
                isLoading={isRefreshing}
                selectedOperationId={selectedOperationId}
                onSelectOperation={handleSelectOperation}
                onRefresh={handleRefresh}
                statusFilter={statusFilter}
                onStatusFilterChange={setStatusFilter}
              />
            </div>

            {/* Conflict Patterns */}
            <ConflictPatternsView
              patterns={patterns}
              isLoading={isRefreshing}
              limit={10}
            />
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
