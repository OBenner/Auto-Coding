import { useMemo } from 'react';
import {
  AlertTriangle,
  AlertCircle,
  X,
  Clock,
  TrendingDown,
  Bell
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { useQualityStore, type QualityAlert } from '../../stores/quality-store';

interface QualityAlertCardProps {
  alerts?: QualityAlert[];
  isLoading?: boolean;
}

interface AlertItemProps {
  alert: QualityAlert;
  onDismiss: (alertId: string) => void;
}

function AlertItem({ alert, onDismiss }: AlertItemProps) {
  const isCritical = alert.severity === 'critical';
  const Icon = isCritical ? AlertCircle : AlertTriangle;

  const severityStyles = {
    critical: {
      container: 'bg-destructive/10 border-destructive/30',
      icon: 'text-destructive',
      badge: 'bg-destructive/20 text-destructive'
    },
    warning: {
      container: 'bg-warning/10 border-warning/30',
      icon: 'text-warning',
      badge: 'bg-warning/20 text-warning'
    }
  };

  const styles = severityStyles[alert.severity] ?? severityStyles.warning;

  const formatDate = (timestamp: Date | string) => {
    const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
    if (Number.isNaN(date.getTime())) return '';

    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  const formatScore = (score: number) => {
    return `${(score * 100).toFixed(1)}%`;
  };

  return (
    <div className={`p-4 rounded-lg border ${styles.container}`}>
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg ${styles.icon}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="outline" className={styles.badge}>
              {alert.severity.toUpperCase()}
            </Badge>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>{formatDate(alert.timestamp)}</span>
            </div>
          </div>
          <div className="text-sm font-medium text-foreground mb-2">
            {alert.message}
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <TrendingDown className="h-3 w-3" />
              <span>Drop: {alert.quality_drop_percent.toFixed(1)}%</span>
            </div>
            <div>Current: {formatScore(alert.current_score)}</div>
            <div>Baseline: {formatScore(alert.baseline_score)}</div>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onDismiss(alert.id)}
          className="h-8 w-8 p-0 hover:bg-destructive/20"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

export function QualityAlertCard({ alerts: propAlerts, isLoading = false }: QualityAlertCardProps) {
  const storeAlerts = useQualityStore((state) => state.alerts);
  const dismissAlert = useQualityStore((state) => state.dismissAlert);

  // Use prop alerts if provided, otherwise use store alerts
  const allAlerts = propAlerts ?? storeAlerts;

  // Filter for active (non-dismissed) alerts
  const activeAlerts = useMemo(() => {
    return allAlerts.filter((alert) => !alert.dismissed);
  }, [allAlerts]);

  // Sort by severity (critical first) then by timestamp (newest first)
  const sortedAlerts = useMemo(() => {
    return [...activeAlerts].sort((a, b) => {
      // Critical alerts first
      if (a.severity === 'critical' && b.severity !== 'critical') return -1;
      if (a.severity !== 'critical' && b.severity === 'critical') return 1;
      // Then by timestamp (newest first)
      const aDate = a.timestamp instanceof Date ? a.timestamp : new Date(a.timestamp);
      const bDate = b.timestamp instanceof Date ? b.timestamp : new Date(b.timestamp);
      const aTime = Number.isNaN(aDate.getTime()) ? 0 : aDate.getTime();
      const bTime = Number.isNaN(bDate.getTime()) ? 0 : bDate.getTime();
      return bTime - aTime;
    });
  }, [activeAlerts]);

  const criticalCount = sortedAlerts.filter((a) => a.severity === 'critical').length;
  const warningCount = sortedAlerts.filter((a) => a.severity === 'warning').length;

  return (
    <Card className="bg-muted/30 border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Bell className="h-5 w-5 text-accent" />
            Quality Alerts
          </CardTitle>
          {sortedAlerts.length > 0 && (
            <div className="flex items-center gap-2">
              {criticalCount > 0 && (
                <Badge variant="outline" className="bg-destructive/20 text-destructive text-xs">
                  {criticalCount} Critical
                </Badge>
              )}
              {warningCount > 0 && (
                <Badge variant="outline" className="bg-warning/20 text-warning text-xs">
                  {warningCount} Warning
                </Badge>
              )}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Clock className="h-5 w-5 animate-spin mr-2" />
            Loading alerts...
          </div>
        ) : sortedAlerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="p-3 rounded-full bg-success/10 mb-3">
              <Bell className="h-8 w-8 text-success" />
            </div>
            <p className="text-sm font-medium text-foreground">No quality alerts</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              All systems operating within expected quality thresholds
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {sortedAlerts.map((alert) => (
              <AlertItem key={alert.id} alert={alert} onDismiss={dismissAlert} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
