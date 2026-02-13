import { useMemo } from 'react';
import {
  DollarSign,
  CreditCard,
  TrendingUp,
  TrendingDown,
  Minus,
  Target,
  Coins
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import type { CostSummary } from '../../../shared/types/task';

interface CostSummaryCardProps {
  costData: CostSummary | null;
  isLoading?: boolean;
}

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  variant?: 'default' | 'success' | 'warning' | 'error';
}

function StatCard({ icon: Icon, label, value, trend, trendValue, variant = 'default' }: StatCardProps) {
  const variantStyles = {
    default: 'bg-accent/10 text-accent',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/10 text-warning',
    error: 'bg-destructive/10 text-destructive'
  };

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-success' : trend === 'down' ? 'text-destructive' : 'text-muted-foreground';

  return (
    <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/30 border border-border/50">
      <div className={`p-2 rounded-lg ${variantStyles[variant]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-muted-foreground mb-1">{label}</div>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-semibold text-foreground">{value}</div>
          {trend && trendValue && (
            <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
              <TrendIcon className="h-3 w-3" />
              <span>{trendValue}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) {
    return `${(tokens / 1_000_000).toFixed(1)}M`;
  }
  if (tokens >= 1_000) {
    return `${(tokens / 1_000).toFixed(1)}K`;
  }
  return tokens.toString();
}

export function CostSummaryCard({ costData, isLoading = false }: CostSummaryCardProps) {
  const stats = useMemo(() => {
    if (!costData) {
      return {
        totalCost: 0,
        planningCost: 0,
        codingCost: 0,
        validationCost: 0,
        totalTokens: 0,
        modelCount: 0
      };
    }

    return {
      totalCost: costData.total_cost,
      planningCost: costData.planning_cost,
      codingCost: costData.coding_cost,
      validationCost: costData.validation_cost,
      totalTokens: costData.total_tokens,
      modelCount: costData.model_costs?.length || 0
    };
  }, [costData]);

  const hasData = costData && costData.total_cost >= 0;

  return (
    <Card className="bg-muted/30 border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Target className="h-5 w-5 text-accent" />
            Cost Summary
          </CardTitle>
          {hasData && stats.modelCount > 0 && (
            <Badge variant="outline" className="text-xs">
              {stats.modelCount} {stats.modelCount === 1 ? 'model' : 'models'}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Coins className="h-5 w-5 animate-spin mr-2" />
            Loading cost data...
          </div>
        ) : !hasData ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <DollarSign className="h-12 w-12 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">No cost data recorded yet</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Cost analytics will appear here after your first agent session
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              icon={DollarSign}
              label="Total Cost"
              value={formatCurrency(stats.totalCost)}
              variant={stats.totalCost > 0 ? 'default' : 'default'}
            />
            <StatCard
              icon={CreditCard}
              label="Planning"
              value={formatCurrency(stats.planningCost)}
              variant={stats.planningCost > 0 ? 'default' : 'default'}
            />
            <StatCard
              icon={TrendingUp}
              label="Coding"
              value={formatCurrency(stats.codingCost)}
              variant={stats.codingCost > 0 ? 'success' : 'default'}
            />
            <StatCard
              icon={Coins}
              label="Total Tokens"
              value={formatTokens(stats.totalTokens)}
              variant="default"
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
