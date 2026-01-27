import { Activity, TrendingUp, TrendingDown, BarChart3 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { cn } from '../../lib/utils';
import type { Task, PhaseTokenStats } from '../../../shared/types';

interface TokenStatsDisplayProps {
  task: Task;
}

/**
 * Format number with thousand separators for readability
 * @param num Number to format
 * @returns Formatted string with commas (e.g., 1,234,567)
 */
function formatNumber(num: number): string {
  return num.toLocaleString('en-US');
}

/**
 * Get phase display color based on phase name
 */
function getPhaseColor(phase: 'planning' | 'coding' | 'validation'): string {
  switch (phase) {
    case 'planning':
      return 'text-blue-600 dark:text-blue-400';
    case 'coding':
      return 'text-purple-600 dark:text-purple-400';
    case 'validation':
      return 'text-green-600 dark:text-green-400';
    default:
      return 'text-foreground';
  }
}

/**
 * Get phase icon component
 */
function getPhaseIcon(phase: 'planning' | 'coding' | 'validation') {
  const className = "h-4 w-4";
  switch (phase) {
    case 'planning':
      return <BarChart3 className={cn(className, 'text-blue-600 dark:text-blue-400')} />;
    case 'coding':
      return <Activity className={cn(className, 'text-purple-600 dark:text-purple-400')} />;
    case 'validation':
      return <Activity className={cn(className, 'text-green-600 dark:text-green-400')} />;
  }
}

/**
 * Render a single phase's token statistics
 */
function PhaseTokenDisplay({ phase, stats, t }: { phase: 'planning' | 'coding' | 'validation'; stats: PhaseTokenStats; t: any }) {
  const phaseName = t(`tasks:tokenStats.phases.${phase}`);

  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-secondary/30 p-3 transition-all duration-200 hover:bg-secondary/50'
      )}
    >
      <div className="flex items-start gap-2">
        {getPhaseIcon(phase)}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-2">
            <span className={cn('text-sm font-medium', getPhaseColor(phase))}>
              {phaseName}
            </span>
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge variant="secondary" className="text-xs font-mono cursor-help">
                  {formatNumber(stats.totalTokens)}
                </Badge>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p className="text-xs">{t('tasks:tokenStats.tokensUsed', { count: stats.totalTokens })}</p>
              </TooltipContent>
            </Tooltip>
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3 text-muted-foreground" />
                <span className="text-muted-foreground">{t('tasks:tokenStats.inputTokens')}</span>
              </div>
              <span className="font-mono tabular-nums text-foreground">
                {formatNumber(stats.inputTokens)}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1">
                <TrendingDown className="h-3 w-3 text-muted-foreground" />
                <span className="text-muted-foreground">{t('tasks:tokenStats.outputTokens')}</span>
              </div>
              <span className="font-mono tabular-nums text-foreground">
                {formatNumber(stats.outputTokens)}
              </span>
            </div>
            {stats.sessionCount > 0 && (
              <div className="pt-1 border-t border-border/50">
                <span className="text-[10px] text-muted-foreground">
                  {t('tasks:tokenStats.sessionCount', { count: stats.sessionCount })}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function TokenStatsDisplay({ task }: TokenStatsDisplayProps) {
  const { t } = useTranslation(['tasks']);
  const tokenStats = task.tokenStats;

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-3">
        {!tokenStats ? (
          <div className="text-center py-12">
            <Activity className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
            <p className="text-sm font-medium text-muted-foreground mb-1">
              {t('tasks:tokenStats.noStats')}
            </p>
            <p className="text-xs text-muted-foreground/70">
              {t('tasks:tokenStats.noStatsHint')}
            </p>
          </div>
        ) : (
          <>
            {/* Total summary */}
            <div className="flex items-center justify-between text-sm pb-2 border-b border-border/50">
              <span className="font-medium text-foreground">{t('tasks:tokenStats.totalTokens')}</span>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="font-mono tabular-nums font-medium text-foreground cursor-default">
                    {formatNumber(tokenStats.totalTokens)}
                  </span>
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  <div className="text-xs space-y-1">
                    <p>{t('tasks:tokenStats.inputTokens')}: {formatNumber(tokenStats.totalInputTokens)}</p>
                    <p>{t('tasks:tokenStats.outputTokens')}: {formatNumber(tokenStats.totalOutputTokens)}</p>
                  </div>
                </TooltipContent>
              </Tooltip>
            </div>

            {/* Per-phase breakdown */}
            {tokenStats.phases.planning && (
              <PhaseTokenDisplay
                phase="planning"
                stats={tokenStats.phases.planning}
                t={t}
              />
            )}
            {tokenStats.phases.coding && (
              <PhaseTokenDisplay
                phase="coding"
                stats={tokenStats.phases.coding}
                t={t}
              />
            )}
            {tokenStats.phases.validation && (
              <PhaseTokenDisplay
                phase="validation"
                stats={tokenStats.phases.validation}
                t={t}
              />
            )}
          </>
        )}
      </div>
    </ScrollArea>
  );
}
