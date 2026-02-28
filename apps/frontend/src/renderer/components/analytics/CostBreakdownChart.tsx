/**
 * Cost Breakdown Chart - Shows cost breakdown by AI provider
 *
 * Displays cost distribution across different AI providers (Claude, OpenAI, Google, Ollama)
 * with horizontal bar chart visualization and detailed breakdowns.
 */

import React from 'react';
import { motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { DollarSign, TrendingUp, Zap } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface ProviderCost {
  provider: string;
  cost: number;
  modelBreakdown: {
    model: string;
    cost: number;
    inputTokens: number;
    outputTokens: number;
  }[];
}

export interface CostBreakdownChartProps {
  providerCosts: ProviderCost[];
  totalCost: number;
  className?: string;
}

// Provider color configuration
const PROVIDER_COLORS: Record<string, { color: string; bgColor: string; icon: string }> = {
  claude: {
    color: 'bg-purple-500',
    bgColor: 'bg-purple-500/10',
    icon: '🤖'
  },
  openai: {
    color: 'bg-green-500',
    bgColor: 'bg-green-500/10',
    icon: '🔷'
  },
  google: {
    color: 'bg-blue-500',
    bgColor: 'bg-blue-500/10',
    icon: '🔍'
  },
  ollama: {
    color: 'bg-amber-500',
    bgColor: 'bg-amber-500/10',
    icon: '🦙'
  },
  default: {
    color: 'bg-muted-foreground',
    bgColor: 'bg-muted',
    icon: '💡'
  },
};

/**
 * Get provider display name with proper capitalization
 */
const getProviderName = (provider: string): string => {
  const names: Record<string, string> = {
    claude: 'Claude (Anthropic)',
    openai: 'OpenAI',
    google: 'Google Gemini',
    ollama: 'Ollama (Local)',
  };
  return names[provider.toLowerCase()] || provider;
};

/**
 * Format dollar amount with proper precision
 */
const formatCost = (cost: number): string => {
  if (cost === 0) return '$0.00';
  if (cost < 0.01) return '<$0.01';
  return `$${cost.toFixed(2)}`;
};

/**
 * Format large numbers with compact notation
 */
const formatTokens = (tokens: number): string => {
  if (tokens >= 1_000_000) {
    return `${(tokens / 1_000_000).toFixed(1)}M`;
  }
  if (tokens >= 1_000) {
    return `${(tokens / 1_000).toFixed(1)}K`;
  }
  return tokens.toString();
};

export const CostBreakdownChart: React.FC<CostBreakdownChartProps> = ({
  providerCosts,
  totalCost,
  className,
}) => {
  const { t } = useTranslation(['common']);

  // Sort providers by cost (descending)
  const sortedProviders = [...providerCosts].sort((a, b) => b.cost - a.cost);

  // If no costs, show empty state
  if (totalCost === 0 || sortedProviders.length === 0) {
    return (
      <div className={cn('p-4 rounded-lg border bg-card', className)}>
        <div className="flex items-center gap-2 mb-3">
          <DollarSign className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">{t('common:cost.breakdown')}</h3>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
          <Zap className="h-8 w-8 mb-2 opacity-50" />
          <p className="text-sm">{t('common:cost.noCosts')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('p-4 rounded-lg border bg-card', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">{t('common:cost.breakdown')}</h3>
        </div>
        <div className="flex items-center gap-1 text-sm">
          <TrendingUp className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="font-semibold">{formatCost(totalCost)}</span>
          <span className="text-muted-foreground text-xs ml-1">{t('common:cost.total')}</span>
        </div>
      </div>

      {/* Provider cost bars */}
      <div className="space-y-3">
        {sortedProviders.map((providerCost, index) => {
          const percentage = (providerCost.cost / totalCost) * 100;
          const colors = PROVIDER_COLORS[providerCost.provider.toLowerCase()] || PROVIDER_COLORS.default;

          return (
            <div key={providerCost.provider} className="space-y-1.5">
              {/* Provider header */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-base" aria-hidden="true">
                    {colors.icon}
                  </span>
                  <span className="text-xs font-medium text-foreground">
                    {getProviderName(providerCost.provider)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">
                    {percentage.toFixed(1)}%
                  </span>
                  <span className="text-xs font-semibold tabular-nums">
                    {formatCost(providerCost.cost)}
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                <motion.div
                  className={cn('h-full rounded-full', colors.color)}
                  initial={{ width: 0 }}
                  animate={{ width: `${percentage}%` }}
                  transition={{
                    duration: 0.8,
                    delay: index * 0.1,
                    ease: 'easeOut',
                  }}
                />
              </div>

              {/* Model breakdown (if multiple models) */}
              {providerCost.modelBreakdown.length > 1 && (
                <div className="pl-8 space-y-1 mt-2">
                  {providerCost.modelBreakdown
                    .sort((a, b) => b.cost - a.cost)
                    .map((model) => {
                      const modelPercentage = providerCost.cost > 0
                        ? (model.cost / providerCost.cost) * 100
                        : 0;
                      return (
                        <div
                          key={model.model}
                          className="flex items-center justify-between text-[10px]"
                        >
                          <span className="text-muted-foreground truncate max-w-[150px]">
                            {model.model}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className="text-muted-foreground/70">
                              {formatTokens(model.inputTokens + model.outputTokens)} tokens
                            </span>
                            <span className="text-muted-foreground">
                              {modelPercentage.toFixed(0)}%
                            </span>
                            <span className="font-medium tabular-nums min-w-[45px] text-right">
                              {formatCost(model.cost)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                </div>
              )}

              {/* Single model token info */}
              {providerCost.modelBreakdown.length === 1 && (
                <div className="pl-8 text-[10px] text-muted-foreground">
                  {formatTokens(
                    providerCost.modelBreakdown[0].inputTokens +
                      providerCost.modelBreakdown[0].outputTokens
                  )}{' '}
                  tokens
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer note for zero-cost providers */}
      {sortedProviders.some((p) => p.provider.toLowerCase() === 'ollama' && p.cost === 0) && (
        <div className="mt-4 pt-3 border-t">
          <p className="text-[10px] text-muted-foreground flex items-center gap-1">
            <Zap className="h-3 w-3" />
            {t('common:cost.localModelsNote')}
          </p>
        </div>
      )}
    </div>
  );
};
