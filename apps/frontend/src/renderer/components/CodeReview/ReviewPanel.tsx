import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Shield, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';

interface ReviewFinding {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: 'security' | 'performance' | 'style' | 'bestPractices';
  message: string;
  file?: string;
  line?: number;
}

interface ReviewPanelProps {
  status?: 'idle' | 'analyzing' | 'complete' | 'failed';
  findings?: ReviewFinding[];
  onRunReview?: () => void;
  onViewFindings?: () => void;
}

// Custom comparator for React.memo - compares status, findings content, and callbacks
function reviewPanelPropsAreEqual(prevProps: ReviewPanelProps, nextProps: ReviewPanelProps): boolean {
  if (
    prevProps.status !== nextProps.status ||
    prevProps.onRunReview !== nextProps.onRunReview ||
    prevProps.onViewFindings !== nextProps.onViewFindings
  ) {
    return false;
  }
  const prevFindings = prevProps.findings ?? [];
  const nextFindings = nextProps.findings ?? [];
  if (prevFindings.length !== nextFindings.length) return false;
  // Shallow compare finding ids to detect content changes
  return prevFindings.every((f, i) => f.id === nextFindings[i].id);
}

export const ReviewPanel = memo(function ReviewPanel({
  status = 'idle',
  findings = [],
  onRunReview,
  onViewFindings
}: ReviewPanelProps) {
  const { t } = useTranslation(['codeReview', 'common']);

  const isAnalyzing = status === 'analyzing';
  const isComplete = status === 'complete';
  const findingsCount = findings.length;

  const getSeverityColor = (severity: ReviewFinding['severity']) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'high':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
      case 'medium':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
      case 'low':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      default:
        return 'bg-muted text-muted-foreground border-border';
    }
  };

  const getStatusIcon = () => {
    if (isAnalyzing) {
      return <Loader2 className="h-5 w-5 animate-spin text-primary" />;
    }
    if (isComplete && findingsCount === 0) {
      return <CheckCircle className="h-5 w-5 text-green-400" />;
    }
    if (isComplete && findingsCount > 0) {
      return <AlertTriangle className="h-5 w-5 text-warning" />;
    }
    return <Shield className="h-5 w-5 text-muted-foreground" />;
  };

  const getStatusLabel = () => {
    if (isAnalyzing) {
      return t('codeReview:reviewInProgress');
    }
    if (isComplete) {
      return t('codeReview:reviewComplete');
    }
    return t('codeReview:status.idle');
  };

  return (
    <Card className="card-surface">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {getStatusIcon()}
            <h3 className="font-semibold text-sm text-foreground">
              {t('codeReview:title')}
            </h3>
          </div>
          <Badge
            variant={isAnalyzing ? 'info' : isComplete ? 'success' : 'secondary'}
            className="text-[10px] px-1.5 py-0.5"
          >
            {getStatusLabel()}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        {/* Empty state */}
        {status === 'idle' && findingsCount === 0 && (
          <div className="py-6 text-center">
            <p className="text-sm text-muted-foreground mb-4">
              {t('codeReview:empty.description')}
            </p>
            {onRunReview && (
              <Button
                variant="default"
                size="sm"
                onClick={onRunReview}
              >
                <Shield className="mr-1.5 h-3 w-3" />
                {t('codeReview:runReview')}
              </Button>
            )}
          </div>
        )}

        {/* Analyzing state */}
        {isAnalyzing && (
          <div className="py-6 text-center">
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              {t('codeReview:status.analyzing')}
            </p>
          </div>
        )}

        {/* Complete state with findings */}
        {isComplete && findingsCount > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {t('codeReview:findingsCount', { count: findingsCount })}
              </span>
              {onViewFindings && (
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 px-2.5"
                  onClick={onViewFindings}
                >
                  {t('codeReview:actions.viewFindings')}
                </Button>
              )}
            </div>

            {/* Findings summary */}
            <div className="flex flex-wrap gap-1.5">
              {findings.slice(0, 3).map((finding) => (
                <Badge
                  key={finding.id}
                  variant="outline"
                  className={cn('text-[10px] px-1.5 py-0.5', getSeverityColor(finding.severity))}
                >
                  {t(`codeReview:severity.${finding.severity}`)}
                </Badge>
              ))}
              {findingsCount > 3 && (
                <Badge
                  variant="outline"
                  className="text-[10px] px-1.5 py-0.5 bg-muted text-muted-foreground border-border"
                >
                  +{findingsCount - 3}
                </Badge>
              )}
            </div>
          </div>
        )}

        {/* Complete state with no findings */}
        {isComplete && findingsCount === 0 && (
          <div className="py-4 text-center">
            <CheckCircle className="h-8 w-8 text-green-400 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">
              {t('codeReview:noFindings')}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}, reviewPanelPropsAreEqual);
