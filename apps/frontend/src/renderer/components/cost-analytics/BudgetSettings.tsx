/**
 * BudgetSettings - Cost budget and alert configuration
 *
 * Allows users to set monthly API cost budgets and configure
 * alert thresholds for budget notifications.
 *
 * Features:
 * - Monthly budget input (USD)
 * - Alert threshold percentage (warn when approaching limit)
 * - Current spending display
 * - Budget remaining calculation
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { DollarSign, AlertTriangle, Save, Loader2 } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { SettingsSection } from '../settings/SettingsSection';
import { useToast } from '../../hooks/use-toast';
import { cn } from '../../lib/utils';

interface BudgetConfig {
  monthlyBudget: number;  // USD
  alertThreshold: number;  // Percentage (0-100)
}

interface BudgetData {
  currentSpending: number;
  budgetRemaining: number;
  percentageUsed: number;
}

interface BudgetSettingsProps {
  isOpen?: boolean;
}

/**
 * Budget settings component for cost tracking
 */
export function BudgetSettings({ isOpen }: BudgetSettingsProps) {
  const { t } = useTranslation('costAnalytics');
  const { toast } = useToast();

  // Form state
  const [monthlyBudget, setMonthlyBudget] = useState<number>(100);
  const [alertThreshold, setAlertThreshold] = useState<number>(80);
  const [isSaving, setIsSaving] = useState(false);

  // Budget data (current spending, etc.)
  const [budgetData, setBudgetData] = useState<BudgetData | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);

  // Load saved budget settings
  useEffect(() => {
    if (isOpen) {
      loadBudgetSettings();
      loadBudgetData();
    }
  }, [isOpen]);

  const loadBudgetSettings = async () => {
    try {
      setIsLoadingData(true);
      // In a real implementation, this would load from electronAPI
      // For now, using defaults
      const result = await window.electronAPI.getBudgetSettings?.();
      if (result?.success && result.data) {
        setMonthlyBudget(result.data.monthlyBudget || 100);
        setAlertThreshold(result.data.alertThreshold || 80);
      }
    } catch (err) {
      console.warn('[BudgetSettings] Failed to load budget settings:', err);
    } finally {
      setIsLoadingData(false);
    }
  };

  const loadBudgetData = async () => {
    try {
      // In a real implementation, this would load current spending data
      const result = await window.electronAPI.getBudgetData?.();
      if (result?.success && result.data) {
        setBudgetData(result.data);
      }
    } catch (err) {
      console.warn('[BudgetSettings] Failed to load budget data:', err);
    }
  };

  const handleSave = async () => {
    if (!monthlyBudget || monthlyBudget <= 0) {
      toast({
        variant: 'destructive',
        title: t('budget.validation.invalidBudget'),
        description: t('budget.validation.invalidBudgetDescription'),
      });
      return;
    }

    if (!alertThreshold || alertThreshold < 0 || alertThreshold > 100) {
      toast({
        variant: 'destructive',
        title: t('budget.validation.invalidThreshold'),
        description: t('budget.validation.invalidThresholdDescription'),
      });
      return;
    }

    setIsSaving(true);
    try {
      const config: BudgetConfig = {
        monthlyBudget,
        alertThreshold,
      };

      // In a real implementation, this would save to electronAPI
      const result = await window.electronAPI.setBudgetSettings?.(config);

      if (result?.success) {
        toast({
          title: t('budget.saved'),
          description: t('budget.savedDescription'),
        });
        // Reload budget data to show updated calculations
        await loadBudgetData();
      } else {
        throw new Error(result?.error || 'Save failed');
      }
    } catch (err) {
      console.error('[BudgetSettings] Failed to save budget settings:', err);
      toast({
        variant: 'destructive',
        title: t('budget.saveFailed'),
        description: t('budget.saveFailedDescription'),
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Calculate budget status
  const getBudgetStatus = () => {
    if (!budgetData || !monthlyBudget) return null;

    const percentage = budgetData.percentageUsed;
    if (percentage >= 100) {
      return { status: 'exceeded', color: 'text-destructive' };
    } else if (percentage >= alertThreshold) {
      return { status: 'warning', color: 'text-orange-500' };
    } else if (percentage >= 50) {
      return { status: 'moderate', color: 'text-yellow-500' };
    }
    return { status: 'healthy', color: 'text-green-500' };
  };

  const budgetStatus = getBudgetStatus();

  return (
    <SettingsSection
      title={t('budget.title')}
      description={t('budget.description')}
    >
      <div className="space-y-6">
        {/* Budget Status Display */}
        {budgetData && !isLoadingData && (
          <div className={cn(
            "rounded-lg border p-4 space-y-3",
            budgetStatus?.status === 'exceeded' ? "border-destructive/50 bg-destructive/5" :
            budgetStatus?.status === 'warning' ? "border-orange-500/50 bg-orange-500/5" :
            "border-green-500/50 bg-green-500/5"
          )}>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{t('budget.currentSpending')}</span>
              <span className="text-lg font-bold font-mono">
                ${budgetData.currentSpending.toFixed(2)}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{t('budget.budgetRemaining')}</span>
              <span className={cn("text-lg font-bold font-mono", budgetStatus?.color)}>
                ${budgetData.budgetRemaining.toFixed(2)}
              </span>
            </div>

            {budgetStatus?.status === 'exceeded' && (
              <div className="flex items-center gap-2 text-destructive text-sm">
                <AlertTriangle className="h-4 w-4" />
                <span className="font-medium">{t('budget.budgetExceeded')}</span>
              </div>
            )}

            {budgetStatus?.status === 'warning' && (
              <div className="flex items-center gap-2 text-orange-500 text-sm">
                <AlertTriangle className="h-4 w-4" />
                <span>
                  {t('budget.alertMessage', { percentage: Math.round(budgetData.percentageUsed) })}
                </span>
              </div>
            )}
          </div>
        )}

        {isLoadingData && (
          <div className="flex items-center justify-center p-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Budget Configuration */}
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="monthly-budget" className="text-sm font-medium text-foreground">
              {t('budget.monthlyBudget')}
            </Label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                id="monthly-budget"
                type="number"
                min="0"
                step="0.01"
                className="pl-8 font-mono"
                value={monthlyBudget}
                onChange={(e) => setMonthlyBudget(parseFloat(e.target.value) || 0)}
                disabled={isSaving || isLoadingData}
                placeholder="100.00"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {t('budget.monthlyBudgetHelp')}
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="alert-threshold" className="text-sm font-medium text-foreground">
                {t('budget.alertThreshold')}
              </Label>
              <span className="text-sm font-mono text-muted-foreground">{alertThreshold}%</span>
            </div>
            <input
              id="alert-threshold"
              type="range"
              min="50"
              max="100"
              step="5"
              value={alertThreshold}
              onChange={(e) => setAlertThreshold(parseInt(e.target.value, 10))}
              disabled={isSaving || isLoadingData}
              className="w-full"
              aria-describedby="alert-threshold-description"
            />
            <p id="alert-threshold-description" className="text-xs text-muted-foreground">
              {t('budget.alertThresholdHelp')}
            </p>
          </div>

          <div className="flex items-center justify-end pt-2">
            <Button
              onClick={handleSave}
              disabled={isSaving || isLoadingData}
              className="gap-2"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('budget.saving')}
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  {t('budget.save')}
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </SettingsSection>
  );
}
