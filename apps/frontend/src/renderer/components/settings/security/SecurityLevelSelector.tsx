/**
 * SecurityLevelSelector - Security level preset selection component
 *
 * A dropdown component for selecting security level presets:
 * - Paranoid: Maximum security, minimal permissions
 * - Standard: Balanced security, recommended for most users
 * - Permissive: Minimal restrictions, use with caution
 *
 * Features:
 * - Visual selection with icons and descriptions
 * - Warning dialog for permissive mode
 * - Internationalized labels and descriptions
 * - Disabled state support
 * - Consistent with project's select component patterns
 */
import { useState } from 'react';
import { Shield, ShieldCheck, ShieldAlert, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../../ui/alert-dialog';
import { cn } from '../../../lib/utils';
import type { SecurityLevel } from '@shared/types/security';

interface SecurityLevelSelectorProps {
  /** Currently selected security level */
  value: SecurityLevel;
  /** Callback when security level is selected */
  onChange: (level: SecurityLevel) => void;
  /** Disabled state */
  disabled?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Security level configuration
 */
const SECURITY_LEVELS = [
  {
    value: 'paranoid' as SecurityLevel,
    icon: ShieldAlert,
    translationKey: 'paranoid',
    color: 'text-red-500',
  },
  {
    value: 'standard' as SecurityLevel,
    icon: ShieldCheck,
    translationKey: 'standard',
    color: 'text-blue-500',
  },
  {
    value: 'permissive' as SecurityLevel,
    icon: Shield,
    translationKey: 'permissive',
    color: 'text-orange-500',
  },
];

/**
 * SecurityLevelSelector Component
 *
 * @example
 * ```tsx
 * <SecurityLevelSelector
 *   value="standard"
 *   onChange={(level) => setSecurityLevel(level)}
 * />
 * ```
 */
export function SecurityLevelSelector({
  value,
  onChange,
  disabled = false,
  className
}: SecurityLevelSelectorProps) {
  const { t } = useTranslation(['security']);
  const [showPermissiveWarning, setShowPermissiveWarning] = useState(false);
  const [pendingLevel, setPendingLevel] = useState<SecurityLevel | null>(null);

  /**
   * Handle security level selection.
   * Shows warning dialog if switching to permissive mode.
   */
  const handleSelectLevel = (selectedLevel: SecurityLevel) => {
    // If switching to permissive mode, show warning
    if (selectedLevel === 'permissive' && value !== 'permissive') {
      setPendingLevel(selectedLevel);
      setShowPermissiveWarning(true);
    } else {
      // Direct change for other levels
      onChange(selectedLevel);
    }
  };

  /**
   * Confirm permissive mode selection
   */
  const handleConfirmPermissive = () => {
    if (pendingLevel) {
      onChange(pendingLevel);
    }
    setShowPermissiveWarning(false);
    setPendingLevel(null);
  };

  /**
   * Cancel permissive mode selection
   */
  const handleCancelPermissive = () => {
    setShowPermissiveWarning(false);
    setPendingLevel(null);
  };

  const currentLevel = SECURITY_LEVELS.find(level => level.value === value);
  const CurrentIcon = currentLevel?.icon || Shield;

  return (
    <>
      <Select
        value={value}
        onValueChange={handleSelectLevel}
        disabled={disabled}
      >
        <SelectTrigger
          className={cn('w-full', className)}
          data-testid="security-level-select"
        >
          <div className="flex items-center gap-2">
            <CurrentIcon className={cn('h-4 w-4', currentLevel?.color)} />
            <SelectValue />
          </div>
        </SelectTrigger>
        <SelectContent>
          {SECURITY_LEVELS.map((level) => {
            const Icon = level.icon;
            return (
              <SelectItem
                key={level.value}
                value={level.value}
                data-testid={`security-level-option-${level.value}`}
              >
                <div className="flex items-start gap-2">
                  <Icon className={cn('h-4 w-4 mt-0.5', level.color)} />
                  <div className="flex-1">
                    <div className="font-medium">
                      {t(`security:levels.${level.translationKey}.name`)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {t(`security:levels.${level.translationKey}.description`)}
                    </div>
                  </div>
                </div>
              </SelectItem>
            );
          })}
        </SelectContent>
      </Select>

      {/* Permissive mode warning dialog */}
      <AlertDialog open={showPermissiveWarning} onOpenChange={setShowPermissiveWarning}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-500" />
              <AlertDialogTitle>
                {t('security:warnings.dialogTitle')}
              </AlertDialogTitle>
            </div>
            <AlertDialogDescription className="pt-2">
              {t('security:warnings.permissiveLevel')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancelPermissive}>
              {t('common:cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmPermissive}
              className="bg-orange-500 hover:bg-orange-600"
            >
              {t('security:warnings.confirmRisk')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
