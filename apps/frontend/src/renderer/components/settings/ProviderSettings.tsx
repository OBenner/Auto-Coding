import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, ChevronDown, ChevronUp, Server, Database, Cloud, Zap, Globe } from 'lucide-react';
import { cn } from '../../lib/utils';
import {
  API_PROVIDER_PRESETS,
  type ApiProviderPreset,
  getModelsForProvider
} from '../../../shared/constants/api-profiles';
import { useSettingsStore, saveSettings } from '../../stores/settings-store';
import { SettingsSection } from './SettingsSection';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '../ui/select';

/**
 * Icon mapping for provider icons
 */
const providerIconMap: Record<string, React.ElementType> = {
  anthropic: Cloud,
  openrouter: Server,
  groq: Zap,
  'glm-global': Globe,
  'glm-cn': Database
};

/**
 * Provider Settings component
 * Displays available AI providers and allows selection
 * Shows models available for each provider
 */
export function ProviderSettings() {
  const { t } = useTranslation('settings');
  const settings = useSettingsStore((state) => state.settings);
  const selectedProviderId = settings.selectedProviderId || 'anthropic';
  const selectedFallbackModelId = settings.fallbackModelId || '';
  const [showProviderDetails, setShowProviderDetails] = useState<Record<string, boolean>>({});

  // Find the selected provider
  const selectedProvider = useMemo(
    () => API_PROVIDER_PRESETS.find(p => p.id === selectedProviderId) || API_PROVIDER_PRESETS[0],
    [selectedProviderId]
  );

  // Get available models for fallback (from selected provider)
  const availableFallbackModels = useMemo(
    () => getModelsForProvider(selectedProviderId),
    [selectedProviderId]
  );

  /**
   * Handle provider selection
   */
  const handleSelectProvider = async (providerId: string) => {
    const provider = API_PROVIDER_PRESETS.find(p => p.id === providerId);
    if (!provider) return;

    const success = await saveSettings({
      selectedProviderId: providerId,
      // Clear fallback model if switching providers
      fallbackModelId: ''
    });
    if (!success) {
      console.error('Failed to save provider selection');
    }
  };

  /**
   * Handle fallback model selection
   */
  const handleSelectFallbackModel = async (modelId: string) => {
    const success = await saveSettings({
      fallbackModelId: modelId
    });
    if (!success) {
      console.error('Failed to save fallback model selection');
    }
  };

  /**
   * Toggle provider details visibility
   */
  const toggleProviderDetails = (providerId: string) => {
    setShowProviderDetails(prev => ({
      ...prev,
      [providerId]: !prev[providerId]
    }));
  };

  /**
   * Get display name for provider
   */
  const getProviderName = (provider: ApiProviderPreset): string => {
    // Use i18n key if available, fallback to ID
    return t(provider.labelKey, { defaultValue: provider.id });
  };

  /**
   * Render a single provider card
   */
  const renderProviderCard = (provider: ApiProviderPreset) => {
    const isSelected = selectedProviderId === provider.id;
    const isExpanded = showProviderDetails[provider.id];
    const Icon = providerIconMap[provider.id] || Server;
    const models = getModelsForProvider(provider.id);

    return (
      <div
        key={provider.id}
        className={cn(
          'relative rounded-lg border transition-all duration-200',
          isSelected
            ? 'border-primary bg-primary/5'
            : 'border-border bg-card'
        )}
      >
        {/* Main card content */}
        <button
          type="button"
          onClick={() => handleSelectProvider(provider.id)}
          className="w-full p-4 text-left"
        >
          {/* Selected indicator */}
          {isSelected && (
            <div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-primary">
              <Check className="h-3 w-3 text-primary-foreground" />
            </div>
          )}

          {/* Provider content */}
          <div className="flex items-start gap-3">
            <div
              className={cn(
                'flex h-10 w-10 items-center justify-center rounded-lg shrink-0',
                isSelected ? 'bg-primary/10' : 'bg-muted'
              )}
            >
              <Icon
                className={cn(
                  'h-5 w-5',
                  isSelected ? 'text-primary' : 'text-muted-foreground'
                )}
              />
            </div>

            <div className="flex-1 min-w-0 pr-6">
              <h3 className="font-medium text-sm text-foreground">
                {getProviderName(provider)}
              </h3>
              <p className="mt-0.5 text-xs text-muted-foreground truncate">
                {provider.baseUrl}
              </p>

              {/* Model count badge */}
              <div className="mt-2 flex flex-wrap gap-1.5">
                <span className="inline-flex items-center rounded bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {models.length} {models.length === 1 ? t('provider.model') : t('provider.models')}
                </span>
                {provider.supportsModelListing && (
                  <span className="inline-flex items-center rounded bg-green-500/10 px-2 py-0.5 text-[10px] font-medium text-green-600 dark:text-green-400">
                    {t('provider.autoDiscovery')}
                  </span>
                )}
              </div>
            </div>
          </div>
        </button>

        {/* Expandable model list */}
        {models.length > 0 && (
          <>
            <button
              type="button"
              onClick={() => toggleProviderDetails(provider.id)}
              className="w-full px-4 py-2 text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center justify-between border-t border-border"
            >
              <span>{isExpanded ? t('provider.hideModels') : t('provider.showModels')}</span>
              {isExpanded ? (
                <ChevronUp className="h-3 w-3" />
              ) : (
                <ChevronDown className="h-3 w-3" />
              )}
            </button>

            {isExpanded && (
              <div className="px-4 py-3 border-t border-border bg-muted/30">
                <div className="space-y-1.5">
                  {models.map(model => (
                    <div
                      key={model.id}
                      className="flex items-start justify-between text-xs"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-foreground">
                          {model.name}
                        </div>
                        {model.description && (
                          <div className="text-muted-foreground text-[10px] mt-0.5">
                            {model.description}
                          </div>
                        )}
                      </div>
                      {model.tier !== 'other' && (
                        <span
                          className={cn(
                            'ml-2 shrink-0 inline-flex items-center rounded px-1.5 py-0.5 text-[9px] font-medium',
                            model.tier === 'opus' && 'bg-purple-500/10 text-purple-600 dark:text-purple-400',
                            model.tier === 'sonnet' && 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
                            model.tier === 'haiku' && 'bg-green-500/10 text-green-600 dark:text-green-400'
                          )}
                        >
                          {model.tier}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  };

  return (
    <SettingsSection
      title={t('provider.title')}
      description={t('provider.description')}
    >
      <div className="space-y-6">
        {/* Provider selector */}
        <div className="space-y-3">
          <Label>{t('provider.selectProvider')}</Label>
          <Select value={selectedProviderId} onValueChange={handleSelectProvider}>
            <SelectTrigger>
              <SelectValue placeholder={t('provider.selectProviderPlaceholder')} />
            </SelectTrigger>
            <SelectContent>
              {API_PROVIDER_PRESETS.map(provider => (
                <SelectItem key={provider.id} value={provider.id}>
                  {getProviderName(provider)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Fallback model selector */}
        <div className="space-y-3">
          <div className="space-y-1">
            <Label>{t('provider.fallbackModel')}</Label>
            <p className="text-xs text-muted-foreground">
              {t('provider.fallbackModelDescription')}
            </p>
          </div>
          <Select value={selectedFallbackModelId} onValueChange={handleSelectFallbackModel}>
            <SelectTrigger>
              <SelectValue placeholder={t('provider.selectFallbackModel')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">{t('provider.noFallback')}</SelectItem>
              {availableFallbackModels.map(model => (
                <SelectItem key={model.id} value={model.id}>
                  {model.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedFallbackModelId && (
            <div className="rounded-lg border border-blue-200 dark:border-blue-900 bg-blue-50 dark:bg-blue-950/30 p-3">
              <p className="text-xs text-blue-900 dark:text-blue-200">
                {t('provider.fallbackInfo')}
              </p>
            </div>
          )}
        </div>

        {/* Provider cards grid */}
        <div className="space-y-3">
          <Label>{t('provider.availableProviders')}</Label>
          <div className="grid gap-3">
            {API_PROVIDER_PRESETS.map(provider => renderProviderCard(provider))}
          </div>
        </div>

        {/* Info about selected provider */}
        {selectedProvider && (
          <div className="rounded-lg border border-border bg-muted/30 p-4">
            <h4 className="text-sm font-medium text-foreground mb-2">
              {t('provider.selectedProvider')}
            </h4>
            <div className="space-y-2 text-xs text-muted-foreground">
              <div>
                <span className="font-medium">{t('provider.name')}:</span>{' '}
                {getProviderName(selectedProvider)}
              </div>
              <div>
                <span className="font-medium">{t('provider.endpoint')}:</span>{' '}
                <code className="text-[10px] bg-background px-1 py-0.5 rounded">
                  {selectedProvider.baseUrl}
                </code>
              </div>
              <div>
                <span className="font-medium">{t('provider.modelsAvailable')}:</span>{' '}
                {getModelsForProvider(selectedProvider.id).length}
              </div>
            </div>
          </div>
        )}
      </div>
    </SettingsSection>
  );
}
