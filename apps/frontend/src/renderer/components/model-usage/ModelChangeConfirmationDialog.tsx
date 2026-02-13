import { useTranslation } from 'react-i18next';
import { AlertTriangle, Loader2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/alert-dialog';
import { Badge } from '../ui/badge';

interface ModelChangeConfirmationDialogProps {
  open: boolean;
  agentType: string;
  agentLabel?: string;
  currentModel: string;
  newModel: string;
  reason?: string;
  isChanging: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
}

/**
 * Parse model ID to get display name and version
 */
function parseModelId(modelId: string): { name: string; version: string } {
  // Check if it's a tier shorthand (opus, sonnet, haiku)
  if (['opus', 'sonnet', 'haiku'].includes(modelId)) {
    const names: Record<string, string> = {
      opus: 'Opus',
      sonnet: 'Sonnet',
      haiku: 'Haiku'
    };
    return {
      name: names[modelId] || modelId,
      version: 'Default'
    };
  }

  // Parse full model ID
  // e.g., "claude-sonnet-4-5-20250929" -> { name: "Sonnet", version: "4.5" }
  const parts = modelId.split('-');
  const tier = parts[1] || 'unknown';
  const version = parts.slice(2, 5).join('.').replace(/\.+/g, '.');

  const tierNames: Record<string, string> = {
    sonnet: 'Sonnet',
    opus: 'Opus',
    haiku: 'Haiku'
  };

  return {
    name: tierNames[tier] || tier,
    version: version || 'Latest'
  };
}

/**
 * ModelChangeConfirmationDialog Component
 *
 * Confirmation dialog for explicit model changes.
 * Requires user approval before changing agent models to prevent silent downgrades.
 */
export function ModelChangeConfirmationDialog({
  open,
  agentType,
  agentLabel,
  currentModel,
  newModel,
  reason,
  isChanging,
  onOpenChange,
  onConfirm
}: ModelChangeConfirmationDialogProps) {
  const { t } = useTranslation(['model-usage', 'common']);

  // Format agent type for display
  const displayLabel = agentLabel || agentType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  const currentModelInfo = parseModelId(currentModel);
  const newModelInfo = parseModelId(newModel);

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            {t('model-usage:changeConfirmation.title')}
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="text-sm text-muted-foreground space-y-4">
              <p>
                {t('model-usage:changeConfirmation.description', {
                  agent: displayLabel
                })}
              </p>

              {/* Model comparison */}
              <div className="grid grid-cols-2 gap-4 my-4">
                {/* Current model */}
                <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">
                    {t('model-usage:changeConfirmation.currentModel')}
                  </p>
                  <p className="text-lg font-semibold text-foreground">
                    {currentModelInfo.name}
                  </p>
                  <Badge variant="outline" className="text-xs">
                    v{currentModelInfo.version}
                  </Badge>
                  <p className="text-[10px] text-muted-foreground truncate" title={currentModel}>
                    {currentModel}
                  </p>
                </div>

                {/* New model */}
                <div className="bg-primary/10 border border-primary/20 rounded-lg p-4 space-y-2">
                  <p className="text-xs font-medium text-primary">
                    {t('model-usage:changeConfirmation.newModel')}
                  </p>
                  <p className="text-lg font-semibold text-primary">
                    {newModelInfo.name}
                  </p>
                  <Badge variant="default" className="text-xs bg-primary text-primary-foreground">
                    v{newModelInfo.version}
                  </Badge>
                  <p className="text-[10px] text-muted-foreground truncate" title={newModel}>
                    {newModel}
                  </p>
                </div>
              </div>

              {/* Reason for change */}
              {reason && (
                <div className="bg-muted/30 rounded-lg p-3">
                  <p className="text-xs font-medium text-muted-foreground mb-1">
                    {t('model-usage:changeConfirmation.reasonLabel')}
                  </p>
                  <p className="text-sm text-foreground">{reason}</p>
                </div>
              )}

              {/* Warning */}
              <p className="text-amber-600 dark:text-amber-500 text-xs">
                {t('model-usage:changeConfirmation.warning')}
              </p>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isChanging}>
            {t('model-usage:changeConfirmation.cancel')}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault();
              onConfirm();
            }}
            disabled={isChanging}
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {isChanging ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('model-usage:changeConfirmation.changing')}
              </>
            ) : (
              t('model-usage:changeConfirmation.confirm')
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
