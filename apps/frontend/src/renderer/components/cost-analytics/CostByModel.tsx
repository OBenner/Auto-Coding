import { useMemo } from 'react';
import { Cpu, DollarSign, TrendingUp, TrendingDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { Progress } from '../ui/progress';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { cn } from '../../lib/utils';
import type { ModelCostBreakdown } from '../../../shared/types';

interface CostByModelProps {
  modelCosts: ModelCostBreakdown[] | null;
  isLoading?: boolean;
}

/**
 * Format currency value for display
 * @param amount Amount in USD
 * @returns Formatted string (e.g., "$1.23")
 */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
}

/**
 * Format number with thousand separators
 * @param num Number to format
 * @returns Formatted string with commas (e.g., 1,234,567)
 */
function formatNumber(num: number): string {
  return num.toLocaleString('en-US');
}

/**
 * Format tokens in a human-readable format
 * @param tokens Number of tokens
 * @returns Formatted string (e.g., 1.5M, 250K, 10K)
 */
function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) {
    return `${(tokens / 1_000_000).toFixed(1)}M`;
  }
  if (tokens >= 1_000) {
    return `${(tokens / 1_000).toFixed(1)}K`;
  }
  return tokens.toString();
}

/**
 * Get a color class for the progress bar based on model name
 */
function getModelColor(model: string): string {
  if (model.includes('haiku')) {
    return 'bg-emerald-500';
  }
  if (model.includes('sonnet')) {
    return 'bg-blue-500';
  }
  if (model.includes('opus')) {
    return 'bg-purple-500';
  }
  return 'bg-primary';
}

/**
 * Render a single model's cost breakdown card
 */
function ModelCostCard({
  model,
  cost,
  input_tokens,
  output_tokens,
  total_tokens,
  phase_costs,
  percentage,
  t
}: ModelCostBreakdown & {
  percentage: number;
  t: (key: string, options?: Record<string, unknown>) => string;
}) {
  // Extract short model name for display
  const modelDisplayName = model.includes('claude-')
    ? model.replace('claude-', '').replace('-20250929', '').replace('-20250514', '')
    : model;

  return (
    <div
      className={cn(
        'rounded-xl border p-4 transition-all duration-200',
        'bg-secondary/30 hover:bg-secondary/50 hover:shadow-sm'
      )}
    >
      {/* Model Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Cpu className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="text-sm font-medium text-foreground truncate block cursor-help">
                  {modelDisplayName}
                </span>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-xs">
                <p className="text-xs font-mono">{model}</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
        <Badge
          variant="secondary"
          className="text-xs font-mono cursor-help hover:bg-secondary/80 transition-colors flex-shrink-0"
        >
          {percentage.toFixed(1)}%
        </Badge>
      </div>

      {/* Progress Bar */}
      <div className="mb-3">
        <Progress value={percentage} className="h-2" />
      </div>

      {/* Cost and Token Stats */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        {/* Total Cost */}
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <DollarSign className="h-3 w-3" />
            <span>{t('costAnalytics:costByModel.totalCost')}</span>
          </div>
          <span className="text-sm font-semibold font-mono tabular-nums text-foreground">
            {formatCurrency(cost)}
          </span>
        </div>

        {/* Total Tokens */}
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Cpu className="h-3 w-3" />
            <span>{t('costAnalytics:costByModel.totalTokens')}</span>
          </div>
          <span className="text-sm font-semibold font-mono tabular-nums text-foreground">
            {formatTokens(total_tokens)}
          </span>
        </div>
      </div>

      {/* Input/Output Breakdown */}
      <div className="space-y-2 pt-2 border-t border-border/50">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-1.5">
            <TrendingUp className="h-3 w-3 text-muted-foreground" />
            <span className="text-muted-foreground">{t('costAnalytics:costByModel.inputTokens')}</span>
          </div>
          <span className="font-mono tabular-nums text-foreground">
            {formatNumber(input_tokens)}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-1.5">
            <TrendingDown className="h-3 w-3 text-muted-foreground" />
            <span className="text-muted-foreground">{t('costAnalytics:costByModel.outputTokens')}</span>
          </div>
          <span className="font-mono tabular-nums text-foreground">
            {formatNumber(output_tokens)}
          </span>
        </div>
      </div>

      {/* Per-phase breakdown (if available) */}
      {phase_costs && (
        <div className="mt-3 pt-2 border-t border-border/50">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
            <span>{t('costAnalytics:costByModel.perPhase')}</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="text-center p-2 rounded bg-blue-50/50 dark:bg-blue-950/20">
              <div className="text-[10px] text-muted-foreground mb-0.5">
                {t('costAnalytics:costByModel.phases.planning')}
              </div>
              <div className="text-xs font-mono font-medium text-blue-600 dark:text-blue-400">
                {formatCurrency(phase_costs.planning)}
              </div>
            </div>
            <div className="text-center p-2 rounded bg-purple-50/50 dark:bg-purple-950/20">
              <div className="text-[10px] text-muted-foreground mb-0.5">
                {t('costAnalytics:costByModel.phases.coding')}
              </div>
              <div className="text-xs font-mono font-medium text-purple-600 dark:text-purple-400">
                {formatCurrency(phase_costs.coding)}
              </div>
            </div>
            <div className="text-center p-2 rounded bg-green-50/50 dark:bg-green-950/20">
              <div className="text-[10px] text-muted-foreground mb-0.5">
                {t('costAnalytics:costByModel.phases.validation')}
              </div>
              <div className="text-xs font-mono font-medium text-green-600 dark:text-green-400">
                {formatCurrency(phase_costs.validation)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function CostByModel({ modelCosts, isLoading = false }: CostByModelProps) {
  const { t } = useTranslation(['costAnalytics']);

  // Calculate percentages for each model
  const modelsWithPercentage = useMemo(() => {
    if (!modelCosts || modelCosts.length === 0) return [];

    const totalCost = modelCosts.reduce((sum, model) => sum + model.cost, 0);

    return modelCosts
      .map((model) => ({
        ...model,
        percentage: totalCost > 0 ? (model.cost / totalCost) * 100 : 0
      }))
      .sort((a, b) => b.cost - a.cost); // Sort by cost descending
  }, [modelCosts]);

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-3">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="flex flex-col items-center gap-3">
              <Cpu className="h-8 w-8 animate-spin text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                {t('costAnalytics:costByModel.loading')}
              </p>
            </div>
          </div>
        ) : !modelCosts || modelCosts.length === 0 ? (
          <div className="text-center py-12">
            <Cpu className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
            <p className="text-sm font-medium text-muted-foreground mb-1">
              {t('costAnalytics:costByModel.noData')}
            </p>
            <p className="text-xs text-muted-foreground/70">
              {t('costAnalytics:costByModel.noDataHint')}
            </p>
          </div>
        ) : (
          <>
            {/* Summary Header */}
            <div className="text-sm pb-2 border-b border-border/50">
              <span className="font-medium text-foreground flex items-center gap-2">
                <Cpu className="h-4 w-4 text-muted-foreground" />
                {t('costAnalytics:costByModel.title')}
              </span>
              <span className="text-xs text-muted-foreground ml-auto">
                {modelCosts.length} {modelCosts.length === 1 ? 'model' : 'models'}
              </span>
            </div>

            {/* Model Cost Cards */}
            <div className="space-y-3">
              {modelsWithPercentage.map((model) => (
                <ModelCostCard key={model.model} {...model} t={t} />
              ))}
            </div>
          </>
        )}
      </div>
    </ScrollArea>
  );
}
