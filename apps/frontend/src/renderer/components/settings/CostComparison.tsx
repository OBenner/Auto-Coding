import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { DollarSign, TrendingDown, Zap } from 'lucide-react';
import { cn } from '../../lib/utils';
import {
  MODEL_PRICING,
  getAllProviders,
  getProviderModels,
  formatCost,
  type ModelPricing
} from '../../../shared/constants/model-costs';
import { SettingsSection } from './SettingsSection';

/**
 * Cost Comparison component
 * Displays pricing information for all available AI models
 * Grouped by provider with per-1M-token pricing
 */
export function CostComparison() {
  const { t } = useTranslation('settings');

  // Get all providers and their models
  const providers = useMemo(() => getAllProviders(), []);

  // Find the cheapest model overall
  const cheapestModel = useMemo(() => {
    let cheapest: { model: string; cost: number } | null = null;

    Object.entries(MODEL_PRICING).forEach(([model, pricing]) => {
      if (model === 'default') return;

      // Calculate average cost (input + output) / 2 for comparison
      const avgCost = (pricing.input + pricing.output) / 2;

      if (!cheapest || avgCost < cheapest.cost) {
        cheapest = { model, cost: avgCost };
      }
    });

    return cheapest?.model;
  }, []);

  /**
   * Get provider display name
   */
  const getProviderName = (provider: string): string => {
    const providerNames: Record<string, string> = {
      anthropic: t('costComparison.providers.anthropic'),
      openai: t('costComparison.providers.openai'),
      google: t('costComparison.providers.google'),
      ollama: t('costComparison.providers.ollama')
    };
    return providerNames[provider] || provider;
  };

  /**
   * Get model display name (simplified)
   */
  const getModelDisplayName = (modelId: string): string => {
    // Simplify model names for display
    if (modelId.startsWith('claude-')) {
      const parts = modelId.split('-');
      return `Claude ${parts[1]?.toUpperCase()} ${parts[2] || ''}`.trim();
    }
    if (modelId.startsWith('gpt-')) {
      return modelId.toUpperCase().replace('GPT-', 'GPT-');
    }
    if (modelId.startsWith('gemini-')) {
      return modelId.replace('gemini-', 'Gemini ').replace('-', ' ');
    }
    return modelId;
  };

  /**
   * Render pricing badge
   */
  const renderPricingBadge = (label: string, price: number, isCheapest: boolean = false) => {
    const isFree = price === 0;

    return (
      <div className="flex items-center gap-1.5">
        <span className="text-[10px] text-muted-foreground">{label}:</span>
        <span
          className={cn(
            'inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium',
            isFree && 'bg-green-500/10 text-green-600 dark:text-green-400',
            !isFree && isCheapest && 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
            !isFree && !isCheapest && 'bg-muted text-muted-foreground'
          )}
        >
          {isFree ? t('costComparison.free') : formatCost(price)}
        </span>
      </div>
    );
  };

  /**
   * Render a single model card
   */
  const renderModelCard = (modelId: string, pricing: ModelPricing) => {
    const isCheapest = modelId === cheapestModel;
    const isFree = pricing.input === 0 && pricing.output === 0;

    return (
      <div
        key={modelId}
        className={cn(
          'rounded-lg border p-3 transition-all duration-200',
          isFree && 'border-green-500/20 bg-green-500/5',
          isCheapest && !isFree && 'border-blue-500/20 bg-blue-500/5',
          !isFree && !isCheapest && 'border-border bg-card'
        )}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-medium text-foreground">
                {getModelDisplayName(modelId)}
              </h4>
              {isCheapest && !isFree && (
                <span className="inline-flex items-center rounded bg-blue-500/10 px-1.5 py-0.5 text-[9px] font-medium text-blue-600 dark:text-blue-400">
                  <TrendingDown className="h-2.5 w-2.5 mr-0.5" />
                  {t('costComparison.cheapest')}
                </span>
              )}
              {isFree && (
                <span className="inline-flex items-center rounded bg-green-500/10 px-1.5 py-0.5 text-[9px] font-medium text-green-600 dark:text-green-400">
                  <Zap className="h-2.5 w-2.5 mr-0.5" />
                  {t('costComparison.localFree')}
                </span>
              )}
            </div>

            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
              {renderPricingBadge(t('costComparison.input'), pricing.input, isCheapest)}
              {renderPricingBadge(t('costComparison.output'), pricing.output, isCheapest)}
            </div>
          </div>
        </div>
      </div>
    );
  };

  /**
   * Render provider section
   */
  const renderProviderSection = (provider: string) => {
    const models = getProviderModels(provider);

    if (models.length === 0) return null;

    return (
      <div key={provider} className="space-y-3">
        <div className="flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-foreground">
            {getProviderName(provider)}
          </h3>
          <span className="text-xs text-muted-foreground">
            ({models.length} {models.length === 1 ? t('costComparison.model') : t('costComparison.models')})
          </span>
        </div>

        <div className="grid gap-2">
          {models.map(modelId => {
            const pricing = MODEL_PRICING[modelId];
            if (!pricing) return null;
            return renderModelCard(modelId, pricing);
          })}
        </div>
      </div>
    );
  };

  return (
    <SettingsSection
      title={t('costComparison.title')}
      description={t('costComparison.description')}
    >
      <div className="space-y-6">
        {/* Pricing info banner */}
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
          <div className="flex items-start gap-3">
            <DollarSign className="h-5 w-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-sm font-medium text-foreground">
                {t('costComparison.infoTitle')}
              </h4>
              <p className="text-xs text-muted-foreground">
                {t('costComparison.infoDescription')}
              </p>
            </div>
          </div>
        </div>

        {/* Provider sections */}
        <div className="space-y-6">
          {providers.map(provider => renderProviderSection(provider))}
        </div>

        {/* Pricing notes */}
        <div className="rounded-lg border border-border bg-muted/30 p-4">
          <h4 className="text-xs font-medium text-foreground mb-2">
            {t('costComparison.notesTitle')}
          </h4>
          <ul className="space-y-1 text-[11px] text-muted-foreground">
            <li>• {t('costComparison.note1')}</li>
            <li>• {t('costComparison.note2')}</li>
            <li>• {t('costComparison.note3')}</li>
          </ul>
        </div>
      </div>
    </SettingsSection>
  );
}
