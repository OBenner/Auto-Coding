import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Cpu, Lock, RefreshCw } from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { AgentModelDisplay } from '../model-usage/AgentModelDisplay';
import { ModelLockControl } from '../model-usage/ModelLockControl';
import type { Project } from '../../../shared/types';
import type { ModelLockConfig } from '../../../shared/types/model-usage';

interface ModelUsageSettingsProps {
  project: Project;
}

/**
 * ModelUsageSettings Component
 *
 * Displays model usage information for the project.
 * Shows agent models, their configuration, and lock status.
 * Allows users to view and manage model locks.
 */
export function ModelUsageSettings({ project }: ModelUsageSettingsProps) {
  const { t } = useTranslation(['settings', 'model-usage']);
  const [modelLocks, setModelLocks] = useState<ModelLockConfig>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch model locks on component mount
  useEffect(() => {
    loadModelLocks();
  }, [project.id]);

  const loadModelLocks = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const electronAPI = (window as any).electronAPI;
      if (!electronAPI) {
        throw new Error('Electron API not available');
      }

      const result = await electronAPI.listModelLocks(project.id);
      if (result?.success) {
        setModelLocks(result.data || {});
      } else {
        setError(result?.error || t('model-usage:errors.fetchLocksFailed'));
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLockChange = (agentType: string, isLocked: boolean) => {
    // Refresh the locks after a change
    loadModelLocks();
  };

  // Get default agent models from constants (this could be enhanced to fetch from backend)
  const agentModels: Record<string, string> = {
    // Spec Creation agents
    spec_gatherer: 'sonnet',
    spec_researcher: 'sonnet',
    spec_writer: 'sonnet',
    spec_critic: 'opus',
    spec_discovery: 'sonnet',
    spec_context: 'sonnet',
    spec_validation: 'sonnet',
    spec_compaction: 'sonnet',

    // Build agents
    planner: 'sonnet',
    coder: 'sonnet',

    // Quality Assurance agents
    qa_reviewer: 'sonnet',
    qa_fixer: 'sonnet',

    // Utility agents
    insights: 'sonnet',
    merge_resolver: 'sonnet',
    commit_message: 'haiku',

    // Pull Request agents
    pr_reviewer: 'sonnet',
    pr_orchestrator_parallel: 'sonnet',
    pr_followup_parallel: 'sonnet',

    // Analysis agents
    analysis: 'sonnet',
    batch_analysis: 'sonnet',
    batch_validation: 'sonnet',

    // Roadmap & Ideation agents
    roadmap_discovery: 'sonnet',
    competitor_analysis: 'opus',
    ideation: 'opus',
  };

  return (
    <div className="space-y-6">
      {/* Header with refresh button */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Cpu className="h-4 w-4 text-accent" />
            {t('model-usage:title')}
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            {t('model-usage:description')}
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={loadModelLocks}
          disabled={isLoading}
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-lg border border-border bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {/* Loading state */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12 text-muted-foreground">
          <RefreshCw className="h-6 w-6 animate-spin mr-2" />
          <span className="text-sm">{t('model-usage:loading')}</span>
        </div>
      ) : (
        <>
          {/* Lock summary */}
          <div className="rounded-lg border border-border bg-muted/30 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-foreground flex items-center gap-2">
                <Lock className="h-4 w-4" />
                {t('model-usage:lockedModels')}
              </span>
              <Badge variant="outline">
                {Object.keys(modelLocks.agentModels || {}).length +
                  Object.keys(modelLocks.phaseModels || {}).length}{' '}
                {t('model-usage:locked')}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              {t('model-usage:lockedModelsDescription')}
            </p>
          </div>

          {/* Agent models display */}
          <AgentModelDisplay
            agentModels={agentModels}
            lockedModels={modelLocks.agentModels || {}}
          />
        </>
      )}
    </div>
  );
}
