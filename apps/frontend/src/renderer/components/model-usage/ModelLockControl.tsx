import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Lock, Unlock, Loader2 } from 'lucide-react';
import { Switch } from '../ui/switch';
import { Label } from '../ui/label';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';

interface ModelLockControlProps {
  /**
   * Agent type to lock/unlock
   */
  agentType: string;
  /**
   * Current model ID for this agent
   */
  modelId: string;
  /**
   * Whether the model is currently locked
   */
  isLocked: boolean;
  /**
   * Current project ID
   */
  projectId: string;
  /**
   * Callback when lock state changes
   */
  onLockChange?: (agentType: string, isLocked: boolean) => void;
  /**
   * Display label for the agent (e.g., "Coder", "Planner")
   */
  label?: string;
  /**
   * Compact mode - minimal UI for inline display
   */
  compact?: boolean;
}

function LockStatusIcon({ isUpdating, isLocked }: { isUpdating: boolean; isLocked: boolean }) {
  if (isUpdating) return <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />;
  if (isLocked) return <Lock className="h-4 w-4 text-primary" />;
  return <Unlock className="h-4 w-4 text-muted-foreground" />;
}

/**
 * ModelLockControl Component
 *
 * Provides lock/unlock functionality for agent models.
 * Allows users to pin specific model versions to prevent automatic upgrades.
 */
export function ModelLockControl({
  agentType,
  modelId,
  isLocked,
  projectId,
  onLockChange,
  label,
  compact = false
}: ModelLockControlProps) {
  const { t } = useTranslation(['model-usage', 'common']);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Format agent type for display
  const displayLabel = label || agentType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  const handleLockToggle = async (checked: boolean) => {
    if (isUpdating) return;

    setIsUpdating(true);
    setError(null);

    try {
      const electronAPI = (window as any).electronAPI;
      if (!electronAPI) {
        throw new Error('Electron API not available');
      }

      let result;
      if (checked) {
        // Lock the agent model
        result = await electronAPI.lockAgentModel(projectId, agentType, modelId);
      } else {
        // Unlock the agent model
        result = await electronAPI.unlockAgentModel(projectId, agentType);
      }

      if (result?.success) {
        onLockChange?.(agentType, checked);
      } else {
        setError(result?.error || t('model-usage:errors.lockOperationFailed'));
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(errorMessage);
    } finally {
      setIsUpdating(false);
    }
  };

  if (compact) {
    // Compact mode - just the switch with tooltip
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2">
              <LockStatusIcon isUpdating={isUpdating} isLocked={isLocked} />
              <Switch
                checked={isLocked}
                onCheckedChange={handleLockToggle}
                disabled={isUpdating}
                aria-label={`${displayLabel} model lock`}
              />
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>
              {isLocked
                ? t('model-usage:unlockModel', { agent: displayLabel })
                : t('model-usage:lockModel', { agent: displayLabel })}
            </p>
            {isLocked && (
              <p className="text-xs text-muted-foreground mt-1">
                {t('model-usage:lockedTo', { model: modelId })}
              </p>
            )}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // Full mode - label, description, and switch
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-2">
        <LockStatusIcon isUpdating={isUpdating} isLocked={isLocked} />

        <div className="space-y-0.5">
          <Label className="font-normal text-foreground">
            {displayLabel}
          </Label>
          {isLocked && (
            <p className="text-xs text-muted-foreground">
              {t('model-usage:lockedTo', { model: modelId })}
            </p>
          )}
          {error && (
            <p className="text-xs text-destructive">
              {error}
            </p>
          )}
        </div>
      </div>

      <Switch
        checked={isLocked}
        onCheckedChange={handleLockToggle}
        disabled={isUpdating}
        aria-label={`${displayLabel} model lock`}
      />
    </div>
  );
}
