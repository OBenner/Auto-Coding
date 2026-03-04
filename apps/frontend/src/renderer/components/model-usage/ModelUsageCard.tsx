import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Cpu, DollarSign, Hash, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import type { AgentMetrics } from '../../../shared/types/model-usage';
import { parseModelId, formatNumber, formatCurrency } from './model-utils';

interface ModelUsageCardProps {
  agent: AgentMetrics;
  showRank?: boolean;
  rank?: number;
}

function StatCard({
  icon: Icon,
  label,
  value,
  variant = 'default'
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  variant?: 'default' | 'success' | 'warning' | 'error';
}) {
  const variantStyles = {
    default: 'bg-accent/10 text-accent',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/10 text-warning',
    error: 'bg-destructive/10 text-destructive'
  };

  return (
    <div className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 border border-border/50">
      <div className={`p-2 rounded-lg ${variantStyles[variant]}`}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-muted-foreground mb-1">{label}</div>
        <div className="text-lg font-semibold text-foreground truncate">{value}</div>
      </div>
    </div>
  );
}

export function ModelUsageCard({ agent, showRank = false, rank }: ModelUsageCardProps) {
  const { t } = useTranslation(['model-usage']);

  const stats = useMemo(() => {
    return {
      totalCalls: agent.total_usage_count,
      totalTokens: agent.total_tokens,
      totalCost: agent.total_cost,
      modelsUsed: Object.keys(agent.models_used).length
    };
  }, [agent]);

  const modelInfo = useMemo(() => {
    return parseModelId(agent.primary_model);
  }, [agent.primary_model]);

  return (
    <Card className="bg-muted/30 border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {showRank && rank !== undefined && (
              <Badge variant="outline" className="text-xs">
                #{rank}
              </Badge>
            )}
            <CardTitle className="text-base font-semibold flex items-center gap-2">
              <Cpu className="h-4 w-4 text-accent" />
              <span className="capitalize">{agent.agent_type.replace(/_/g, ' ')}</span>
            </CardTitle>
          </div>
          <Badge variant="secondary" className="text-xs">
            {stats.modelsUsed} {stats.modelsUsed === 1 ? t('model-usage:card.model') : t('model-usage:card.models')}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {/* Primary Model */}
        <div className="mb-4 p-3 rounded-lg bg-background/50 border border-border/50">
          <p className="text-xs text-muted-foreground mb-1">{t('model-usage:card.preferredModel')}</p>
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold">{modelInfo.name}</p>
            <Badge variant="outline" className="text-xs">
              {modelInfo.version}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-1 truncate">{agent.primary_model}</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            icon={Hash}
            label={t('model-usage:card.apiCalls')}
            value={formatNumber(stats.totalCalls)}
            variant="default"
          />
          <StatCard
            icon={Zap}
            label={t('model-usage:card.totalTokens')}
            value={formatNumber(stats.totalTokens)}
            variant="default"
          />
          <StatCard
            icon={DollarSign}
            label={t('model-usage:card.totalCost')}
            value={formatCurrency(stats.totalCost)}
            variant={stats.totalCost > 10 ? 'warning' : 'success'}
          />
          <StatCard
            icon={Cpu}
            label={t('model-usage:card.modelsUsed')}
            value={stats.modelsUsed}
            variant="default"
          />
        </div>

        {/* Model Breakdown */}
        {Object.keys(agent.models_used).length > 1 && (
          <div className="mt-4 pt-4 border-t border-border/50">
            <p className="text-xs text-muted-foreground mb-2">{t('model-usage:card.modelBreakdown')}</p>
            <div className="space-y-1">
              {Object.entries(agent.models_used)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 3)
                .map(([model, count]) => {
                  const percentage = ((count / agent.total_usage_count) * 100).toFixed(1);
                  return (
                    <div key={model} className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground truncate flex-1 mr-2" title={model}>
                        {model}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">{count} {t('model-usage:card.calls')}</span>
                        <span className="font-medium">{percentage}%</span>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
