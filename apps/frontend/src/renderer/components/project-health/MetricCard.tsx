import * as React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { cn } from '../../lib/utils';

export interface MetricCardProps {
  /** The name/title of the metric */
  title: string;
  /** The primary value to display */
  value: string | number;
  /** Optional description or subtitle */
  description?: string;
  /** Icon component to display */
  icon?: React.ComponentType<{ className?: string }>;
  /** Trend direction for the metric */
  trend?: 'up' | 'down' | 'neutral';
  /** Optional trend value to display (e.g., "+5.2%") */
  trendValue?: string;
  /** Visual variant for color coding */
  variant?: 'default' | 'success' | 'warning' | 'error';
  /** Additional CSS classes */
  className?: string;
}

const variantStyles = {
  default: {
    card: 'border-border/50',
    icon: 'bg-accent/10 text-accent',
    value: 'text-foreground'
  },
  success: {
    card: 'border-success/20',
    icon: 'bg-success/10 text-success',
    value: 'text-success'
  },
  warning: {
    card: 'border-warning/20',
    icon: 'bg-warning/10 text-warning',
    value: 'text-warning'
  },
  error: {
    card: 'border-destructive/20',
    icon: 'bg-destructive/10 text-destructive',
    value: 'text-destructive'
  }
};

const trendStyles = {
  up: 'text-success',
  down: 'text-destructive',
  neutral: 'text-muted-foreground'
};

export const MetricCard = React.forwardRef<HTMLDivElement, MetricCardProps>(
  (
    {
      title,
      value,
      description,
      icon: Icon,
      trend,
      trendValue,
      variant = 'default',
      className,
      ...props
    },
    ref
  ) => {
    const styles = variantStyles[variant];
    const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
    const trendColor = trend ? trendStyles[trend] : undefined;

    return (
      <Card
        ref={ref}
        className={cn(
          'bg-muted/30 transition-all duration-200 hover:shadow-md',
          styles.card,
          className
        )}
        {...props}
      >
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
            {Icon && (
              <div className={cn('p-1.5 rounded-md', styles.icon)}>
                <Icon className="h-4 w-4" />
              </div>
            )}
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-baseline gap-2">
            <div className={cn('text-2xl font-semibold', styles.value)}>
              {value}
            </div>
            {trend && trendValue && (
              <div className={cn('flex items-center gap-1 text-xs', trendColor)}>
                <TrendIcon className="h-3 w-3" />
                <span>{trendValue}</span>
              </div>
            )}
          </div>
          {description && (
            <p className="text-xs text-muted-foreground leading-snug">
              {description}
            </p>
          )}
        </CardContent>
      </Card>
    );
  }
);

MetricCard.displayName = 'MetricCard';
